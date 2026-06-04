#!/usr/bin/env python3
"""Master control utility for the Neo Genesis agent runtime fleet.

Runs from desktop-home and manages the SSH-reachable runtime baseline.
Use --target primary for desktop-home, ysh-server, and the company PC.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = ROOT / ".agent" / "shared-brain" / "device_inventory.json"
ARCHIVE_PATHS = [
    ".agent",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "infra/agent-runtime",
    "scripts/fleet_master_control.py",
    "scripts/sync_agent_context.py",
    "scripts/tiktok_aino_ha_worker.ps1",
    "scripts/tiktok_aino_ha_worker.sh",
    "scripts/persona",
    "src/core/tiktok_aino",
    "scripts/run_claude_hooks_golden.py",
    "scripts/run_sora_adversarial.py",
    "tests/core/test_tiktok_aino_ha_publisher.py",
    "tests/hooks_golden",
    "tests/sora_adversarial",
]
ARCHIVE_EXCLUDED_SUFFIXES = (".pyc", ".pyo")
ARCHIVE_EXCLUDED_NAMES = {".env", ".env.local", "credential_audit.jsonl"}
ARCHIVE_EXCLUDED_PARTS = {"__pycache__", ".git", "secrets"}


def _run(args: list[str], *, timeout: int = 120, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _check(args: list[str], *, timeout: int = 120, cwd: Path | None = None) -> str:
    proc = _run(args, timeout=timeout, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
        )
    return proc.stdout


def _load_inventory() -> list[dict[str, Any]]:
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return [d for d in data["devices"] if d.get("connection")]


def _targets(devices: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    if target == "all":
        return devices
    if target in {"primary", "core"}:
        selected = [d for d in devices if d.get("priorityTier") == "primary"]
        if selected:
            return sorted(selected, key=lambda d: d.get("priorityRank", 999))
    if target == "secondary":
        selected = [d for d in devices if d.get("priorityTier") == "secondary"]
        if selected:
            return sorted(selected, key=lambda d: d.get("priorityRank", 999))
    selected = [d for d in devices if d["id"] == target or d["hostname"] == target]
    if not selected:
        known = ", ".join(["all", "primary", "secondary", *[d["id"] for d in devices]])
        raise SystemExit(f"unknown target: {target}; known: {known}")
    return selected


def _ps(script: str) -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"


def _ssh_windows(host: str, script: str, timeout: int = 180) -> str:
    return _check(["ssh", host, _ps(script)], timeout=timeout)


def _ssh_unix(host: str, script: str, timeout: int = 180) -> str:
    return _check(["ssh", host, f"bash -lc {shlex.quote(script)}"], timeout=timeout)


def _ssh_target(device: dict[str, Any]) -> str:
    return str(device.get("sshTarget") or device["hostname"])


def _device_exec(device: dict[str, Any], script: str, timeout: int = 180) -> str:
    if device["connection"] == "local":
        proc = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
        return proc.stdout
    if device["platform"] == "windows":
        return _ssh_windows(_ssh_target(device), script, timeout=timeout)
    return _ssh_unix(_ssh_target(device), script, timeout=timeout)


def _head_revision() -> tuple[str, str]:
    commit = _check(["git", "rev-parse", "--short=12", "HEAD"]).strip()
    ssot = _check(["git", "show", "HEAD:infra/agent-runtime/SSOT_REVISION.txt"]).strip()
    return commit, ssot


def _worktree_revision() -> tuple[str, str]:
    head = _check(["git", "rev-parse", "--short=12", "HEAD"]).strip()
    ssot = (ROOT / "infra" / "agent-runtime" / "SSOT_REVISION.txt").read_text(encoding="utf-8").strip()
    return f"worktree-{head}-{ssot[:12]}", ssot


def _dirty_archive_paths() -> list[str]:
    proc = _run(["git", "status", "--porcelain", "--", *ARCHIVE_PATHS], timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _archive_excluded(path: str) -> bool:
    parts = set(Path(path).parts)
    name = Path(path).name
    if parts & ARCHIVE_EXCLUDED_PARTS:
        return True
    if name in ARCHIVE_EXCLUDED_NAMES or path.startswith(".env."):
        return True
    return path.endswith(ARCHIVE_EXCLUDED_SUFFIXES) or name.endswith(".key") or name.endswith(".pem")


def _worktree_archive_files() -> list[str]:
    proc = _run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *ARCHIVE_PATHS], timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    files = []
    for item in proc.stdout.split("\0"):
        rel = item.strip()
        if not rel or _archive_excluded(rel):
            continue
        if (ROOT / rel).is_file():
            files.append(rel)
    return sorted(set(files))


def _make_archive(commit: str) -> Path:
    archive = Path(tempfile.gettempdir()) / f"neo-genesis-runtime-{commit}.tar"
    if archive.exists():
        archive.unlink()
    _check(["git", "archive", "--format=tar", f"--output={archive}", "HEAD", *ARCHIVE_PATHS], timeout=120)
    return archive


def _make_worktree_archive(label: str) -> Path:
    archive = Path(tempfile.gettempdir()) / f"neo-genesis-runtime-{label}.tar"
    if archive.exists():
        archive.unlink()
    files = _worktree_archive_files()
    if not files:
        raise RuntimeError("worktree archive would be empty")
    with tarfile.open(archive, "w") as tar:
        for rel in files:
            tar.add(ROOT / rel, arcname=rel, recursive=False)
    return archive


def status(devices: list[dict[str, Any]], target: str) -> int:
    for device in _targets(devices, target):
        print(f"\n== {device['id']} ==")
        try:
            if device["platform"] == "windows":
                script = r"""
$target = if ($env:COMPUTERNAME -eq 'DESKTOP-HOME') { 'D:\00.test\neo-genesis' } else { Join-Path $env:USERPROFILE 'neo-genesis-runtime' }
$codex = Join-Path $env:USERPROFILE '.codex\AGENTS.md'
Write-Output "computer=$env:COMPUTERNAME"
Write-Output "user=$env:USERNAME"
Write-Output "runtime=$target"
Write-Output "runtimeExists=$(Test-Path -LiteralPath $target)"
if (Test-Path -LiteralPath (Join-Path $target 'infra\agent-runtime\SSOT_REVISION.txt')) {
  Write-Output "runtimeSsot=$(Get-Content -LiteralPath (Join-Path $target 'infra\agent-runtime\SSOT_REVISION.txt'))"
}
if (Test-Path -LiteralPath $codex) {
  $m = Select-String -Path $codex -Pattern 'ssotRevision' | Select-Object -First 1
  Write-Output "codexGlobal=$($m.Line)"
}
"""
            else:
                script = """
target=/home/ysh/neo-genesis-runtime
echo computer=$(hostname)
echo user=$(whoami)
echo runtime=$target
test -d "$target" && echo runtimeExists=True || echo runtimeExists=False
test -f "$target/infra/agent-runtime/SSOT_REVISION.txt" && echo runtimeSsot=$(cat "$target/infra/agent-runtime/SSOT_REVISION.txt")
test -f "$HOME/.codex/AGENTS.md" && grep -m1 ssotRevision "$HOME/.codex/AGENTS.md" | sed 's/^/codexGlobal=/'
"""
            print(_device_exec(device, script, timeout=60).strip())
        except Exception as exc:
            print(f"ERROR: {exc}")
    return 0


def verify(devices: list[dict[str, Any]], target: str) -> int:
    failed = False
    for device in _targets(devices, target):
        print(f"\n== verify {device['id']} ==")
        try:
            if device["platform"] == "windows":
                script = r"""
$target = if ($env:COMPUTERNAME -eq 'DESKTOP-HOME') { 'D:\00.test\neo-genesis' } else { Join-Path $env:USERPROFILE 'neo-genesis-runtime' }
Set-Location -LiteralPath $target
Get-Content -LiteralPath 'infra\agent-runtime\SSOT_REVISION.txt'
python scripts\persona\constitutional_injector.py --validate-all | Select-Object -First 3
python scripts\run_sora_adversarial.py --suite tests\sora_adversarial\persona_v1.json --contract-only | Select-String -Pattern 'Total:'
python scripts\persona\dispatcher.py --query 'production deploy' | Select-String -Pattern 'persona_id|g2_detected'
"""
            else:
                script = """
cd /home/ysh/neo-genesis-runtime
cat infra/agent-runtime/SSOT_REVISION.txt
python3 scripts/persona/constitutional_injector.py --validate-all | head -3
python3 scripts/run_sora_adversarial.py --suite tests/sora_adversarial/persona_v1.json --contract-only | grep 'Total:'
python3 scripts/persona/dispatcher.py --query 'production deploy' | grep -E 'persona_id|g2_detected'
"""
            print(_device_exec(device, script, timeout=180).strip())
        except Exception as exc:
            failed = True
            print(f"ERROR: {exc}")
    return 1 if failed else 0


def deploy(
    devices: list[dict[str, Any]],
    target: str,
    allow_dirty_head: bool = False,
    from_worktree: bool = False,
) -> int:
    if from_worktree:
        commit, ssot = _worktree_revision()
        archive = _make_worktree_archive(commit)
    else:
        dirty = _dirty_archive_paths()
        if dirty and not allow_dirty_head:
            print("refusing deploy: runtime archive paths have uncommitted or untracked changes")
            print("deploy uses git HEAD, so this would ship a stale runtime snapshot.")
            print("commit or clean the runtime changes first, use --from-worktree, or pass --allow-dirty-head to intentionally deploy HEAD.")
            for line in dirty[:40]:
                print(line)
            if len(dirty) > 40:
                print(f"... {len(dirty) - 40} more")
            return 2
        commit, ssot = _head_revision()
        archive = _make_archive(commit)
    failed = False
    for device in _targets(devices, target):
        print(f"\n== deploy {device['id']} commit={commit} ssot={ssot} ==")
        try:
            if device["connection"] == "local":
                codex = Path(os.environ["USERPROFILE"]) / ".codex" / "AGENTS.md"
                codex.parent.mkdir(parents=True, exist_ok=True)
                if codex.exists():
                    backup = codex.with_name(codex.name + f".bak-{commit}")
                    backup.write_bytes(codex.read_bytes())
                if from_worktree:
                    codex.write_bytes((ROOT / "AGENTS.md").read_bytes())
                else:
                    codex.write_bytes(_check(["git", "show", "HEAD:AGENTS.md"]).encode("utf-8"))
                print(f"updated {codex}")
                continue

            if device["platform"] == "windows":
                remote_archive = f"neo-genesis-runtime-{commit}.tar"
                _check(["scp", str(archive), f"{_ssh_target(device)}:{remote_archive}"], timeout=120)
                script = rf"""
$ErrorActionPreference = 'Stop'
$Rev = '{commit}'
$Archive = Join-Path $env:USERPROFILE 'neo-genesis-runtime-{commit}.tar'
$Target = Join-Path $env:USERPROFILE 'neo-genesis-runtime'
$Stamp = Get-Date -Format yyyyMMddHHmmss
if (!(Test-Path -LiteralPath $Archive)) {{ throw "Archive missing: $Archive" }}
if (Test-Path -LiteralPath $Target) {{ Rename-Item -LiteralPath $Target -NewName "neo-genesis-runtime.bak-$Rev-$Stamp" }}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
tar -xf $Archive -C $Target
python -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {{ python -m pip install PyYAML==6.0.3 }}
$codexDir = Join-Path $env:USERPROFILE '.codex'
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$geminiDir = Join-Path $env:USERPROFILE '.gemini'
New-Item -ItemType Directory -Force -Path $codexDir,$claudeDir,$geminiDir | Out-Null
$codex = Join-Path $codexDir 'AGENTS.md'
$claude = Join-Path $claudeDir 'CLAUDE.md'
$gemini = Join-Path $geminiDir 'GEMINI.md'
foreach ($f in @($codex,$claude,$gemini)) {{ if (Test-Path -LiteralPath $f) {{ Copy-Item -LiteralPath $f -Destination "$f.bak-$Stamp" -Force }} }}
Copy-Item -LiteralPath (Join-Path $Target 'AGENTS.md') -Destination $codex -Force
$targetSlash = $Target.Replace('\','/')
Set-Content -LiteralPath $claude -Encoding UTF8 -Value @('<!-- generated: device-rollout-install -->', '# Neo Genesis Claude Global Adapter', '', "@$targetSlash/CLAUDE.md")
Set-Content -LiteralPath $gemini -Encoding UTF8 -Value @('<!-- generated: device-rollout-install -->', '# Neo Genesis Gemini Global Adapter', '', "@$targetSlash/GEMINI.md")
Write-Output "deployed=$Rev"
Get-Content -LiteralPath (Join-Path $Target 'infra\agent-runtime\SSOT_REVISION.txt')
"""
                print(_ssh_windows(_ssh_target(device), script, timeout=240).strip())
            else:
                remote_archive = f"/tmp/neo-genesis-runtime-{commit}.tar"
                _check(["scp", str(archive), f"{_ssh_target(device)}:{remote_archive}"], timeout=120)
                script = f"""
set -euo pipefail
target=/home/ysh/neo-genesis-runtime
archive={shlex.quote(remote_archive)}
rev={shlex.quote(commit)}
backup="/home/ysh/neo-genesis-runtime.agent-bak-${{rev}}-$(date +%Y%m%d%H%M%S)"
mkdir -p "$backup"
cd "$target"
existing=""
for p in .agent AGENTS.md CLAUDE.md GEMINI.md infra/agent-runtime scripts/sync_agent_context.py scripts/persona scripts/run_claude_hooks_golden.py scripts/run_sora_adversarial.py tests/hooks_golden tests/sora_adversarial; do
  if [ -e "$p" ]; then existing="$existing $p"; fi
done
if [ -n "$existing" ]; then tar -cf "$backup/agent-runtime-before.tar" $existing; fi
rm -rf .agent infra/agent-runtime scripts/persona tests/hooks_golden tests/sora_adversarial
rm -f AGENTS.md CLAUDE.md GEMINI.md scripts/sync_agent_context.py scripts/run_claude_hooks_golden.py scripts/run_sora_adversarial.py
mkdir -p scripts tests infra
tar -xf "$archive" -C "$target"
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p "$HOME/.codex" "$HOME/.claude" "$HOME/.gemini"
for f in "$HOME/.codex/AGENTS.md" "$HOME/.claude/CLAUDE.md" "$HOME/.gemini/GEMINI.md"; do
  if [ -f "$f" ]; then cp "$f" "${{f}}.bak-${{stamp}}"; fi
done
cp "$target/AGENTS.md" "$HOME/.codex/AGENTS.md"
printf '<!-- generated: device-rollout-install -->\\n# Neo Genesis Claude Global Adapter\\n\\n@/home/ysh/neo-genesis-runtime/CLAUDE.md\\n' > "$HOME/.claude/CLAUDE.md"
printf '<!-- generated: device-rollout-install -->\\n# Neo Genesis Gemini Global Adapter\\n\\n@/home/ysh/neo-genesis-runtime/GEMINI.md\\n' > "$HOME/.gemini/GEMINI.md"
echo deployed=$rev
cat "$target/infra/agent-runtime/SSOT_REVISION.txt"
"""
                print(_ssh_unix(_ssh_target(device), script, timeout=240).strip())
        except Exception as exc:
            failed = True
            print(f"ERROR: {exc}")
    return 1 if failed else 0


def run_remote(devices: list[dict[str, Any]], target: str, command: str) -> int:
    failed = False
    for device in _targets(devices, target):
        print(f"\n== run {device['id']} ==")
        try:
            print(_device_exec(device, command, timeout=180).strip())
        except Exception as exc:
            failed = True
            print(f"ERROR: {exc}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Control Neo Genesis fleet devices from desktop-home")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("status", "verify", "deploy"):
        p = sub.add_parser(name)
        p.add_argument("--target", default="all")
        if name == "deploy":
            p.add_argument("--allow-dirty-head", action="store_true")
            p.add_argument("--from-worktree", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("--target", required=True)
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if platform.system().lower() != "windows":
        print("warning: this tool is intended to run from desktop-home", file=sys.stderr)

    devices = _load_inventory()
    if args.cmd == "status":
        return status(devices, args.target)
    if args.cmd == "verify":
        return verify(devices, args.target)
    if args.cmd == "deploy":
        return deploy(devices, args.target, allow_dirty_head=args.allow_dirty_head, from_worktree=args.from_worktree)
    if args.cmd == "run":
        if not args.command:
            raise SystemExit("run requires a command")
        return run_remote(devices, args.target, " ".join(args.command))
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
