#!/usr/bin/env python3
"""
agent_session_sync.py — Project Continuity Protocol (PCP) v1 의 Safe-Sync 실행기 (v1.1).

목적: 모든 AI/에이전트가 작업 시작 시 "git pull 먼저"를 '안전하게' 수행한다.
무지성 pull 금지 — dirty 트리(미커밋 변경)에서는 fetch + report만 하고, clean 트리에서만 rebase.

설계 정본: .agent/knowledge/20260614_PROJECT_CONTINUITY_PROTOCOL_v1.md
레지스트리:  .agent/policies/project_continuity_registry.json

사용:
  python scripts/agent_session_sync.py <project_path>       # 단일 프로젝트 동기화 (기본 dry-run)
  python scripts/agent_session_sync.py --all                # 레지스트리 전체 상태 보고
  python scripts/agent_session_sync.py --scan               # 미등록 git repo 탐지 ("우연한 미추적" 차단)
  python scripts/agent_session_sync.py <path> --apply       # 실제 동기화 (clean이면 rebase, dirty면 report-only)
  python scripts/agent_session_sync.py <path> --apply --autostash  # dirty 시 stash→rebase→pop (충돌이면 복원·중단)
  python scripts/agent_session_sync.py <path> --init-repo   # 로컬 git 생성 + .gitignore (리모트/push 없음, owner-gate 무관)

안전 불변식:
  - dirty 트리에 git pull / reset --hard / clean 절대 실행 안 함
  - remote BLOCKLIST(neogenesislab/etribe)는 모든 동기화 거부. 비-allowlist는 sync 허용·push만 게이트.
  - never/vault(track) 프로젝트는 리모트 동기화·init 모두 스킵
  - 미커밋 변경 폐기 절대 금지 (autostash 충돌 시 stash 보존)
  - 기본 dry-run — --apply / --init-repo 없이는 어떤 git 변경도 하지 않음
  - --init-repo는 로컬 전용(리모트 미생성·미푸시). 외부 액션 0, 가역.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

try:  # 콘솔 인코딩 강제 (Windows cp949 mojibake 방지)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SBU_ROOT = os.path.dirname(HERE)
REGISTRY = os.path.join(SBU_ROOT, ".agent", "policies", "project_continuity_registry.json")
LEDGER = os.path.join(SBU_ROOT, ".agent", "shared-brain", "continuity-ledger.jsonl")

GITIGNORE_BASE = [
    "# PCP v1 auto-generated — 민감/임시 자산 제외 (절대 푸시 금지)",
    ".env", ".env.*", "*.key", "*.pem", "*.p12", "credentials*",
    "*service-account*.json", "gcal_token.json", "*token*.json",
    "_secrets/", "secrets/", "personal/",
    "node_modules/", ".next/", "dist/", "out/", "build/",
    "__pycache__/", "*.pyc", ".venv/", "venv/",
    ".DS_Store", "Thumbs.db", "*.log", "dump.rdb", "*.pid",
]


def load_registry():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def git(args, cwd, check=False):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                           timeout=300, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:  # noqa
        return 99, "", str(e)


def is_git(path):
    """worktree/submodule 대응: .git 이 디렉토리 OR 파일이어도 git."""
    if os.path.exists(os.path.join(path, ".git")):
        return True
    rc, out, _ = git(["rev-parse", "--is-inside-work-tree"], path)
    return rc == 0 and out == "true"


def remote_url(path):
    rc, out, _ = git(["remote", "get-url", "origin"], path)
    return out if rc == 0 else None


def remote_safety(reg, url):
    """(sync_ok, push_ok, reason). BLOCKLIST만 sync 거부. 비-allowlist는 sync 허용·push 차단."""
    if not url:
        return True, False, "no-remote"
    for bad in reg.get("remote_blocklist", []):
        if bad and bad in url:
            return False, False, "BLOCKLIST:" + bad
    if any(a in url for a in reg.get("remote_allowlist", [])):
        return True, True, "allowlist"
    return True, False, "non-allowlist(sync-ok/push-gated)"


def dirty_count(path):
    rc, out, _ = git(["status", "--porcelain"], path)
    if rc != 0:
        return None
    return len([ln for ln in out.splitlines() if ln.strip()])


def upstream_delta(path):
    rc, _, _ = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], path)
    if rc != 0:
        return None, None
    rc, out, _ = git(["rev-list", "--left-right", "--count", "@{u}...HEAD"], path)
    if rc != 0:
        return None, None
    try:
        behind, ahead = out.split()
        return int(behind), int(ahead)
    except Exception:  # noqa
        return None, None


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def log_ledger(entry):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    entry = dict(entry)
    entry["ts"] = now_iso()
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def find_project(reg, path_arg):
    root = reg.get("workspace_root", "D:/00.test")
    norm = os.path.normpath(os.path.abspath(path_arg)).replace("\\", "/")
    best = None
    for proj in reg["projects"]:
        full = os.path.normpath(os.path.join(root, proj["path"])).replace("\\", "/")
        if norm == full or norm.startswith(full + "/"):
            if best is None or len(proj["path"]) > len(best["path"]):
                best = proj  # 가장 깊은(구체적) 매칭 우선
    if best:
        return best
    rootn = os.path.normpath(root).replace("\\", "/")
    rel = norm[len(rootn) + 1:] if norm.startswith(rootn) else norm
    return {"path": rel, "tier": None, "track": "UNREGISTERED",
            "note": "레지스트리 미등록 — PCP 위반. 먼저 등록하라."}


def write_gitignore(full, reg):
    lines = list(GITIGNORE_BASE)
    path = os.path.join(full, ".gitignore")
    existing = ""
    if os.path.exists(path):
        existing = open(path, encoding="utf-8", errors="replace").read()
    add = [ln for ln in lines if ln not in existing]
    if add:
        with open(path, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n".join(add) + "\n")
    return len(add)


def init_repo(reg, proj, root, apply=False):
    res = {"path": proj["path"], "track": proj.get("track"), "tier": proj.get("tier"),
           "action": None, "detail": None, "safe": True}
    track = proj.get("track")
    if track in ("never", "vault"):
        res.update(action="REFUSED", detail="민감 자산(track=%s) — 저장소 생성 금지" % track, safe=False)
        return res
    full = os.path.normpath(os.path.join(root, proj["path"]))
    if not os.path.isdir(full):
        res.update(action="MISSING", detail="경로 없음", safe=False)
        return res
    if is_git(full):
        res.update(action="ALREADY_GIT", detail="이미 git — init 불필요")
        return res
    if not apply:
        res.update(action="WOULD_INIT", detail="[dry-run] 로컬 git init + .gitignore + 초기커밋 예정 (리모트/push 없음)")
        return res
    n = write_gitignore(full, reg)  # 반드시 add 전에 작성 → 민감파일 제외
    rc, _, err = git(["init", "-b", "main"], full)
    if rc != 0:
        res.update(action="INIT_FAIL", detail=err, safe=False)
        return res
    git(["add", "-A"], full)
    rc, _, err = git(["commit", "-m", "chore(pcp): initial local snapshot"], full)
    if rc != 0:
        res.update(action="COMMIT_FAIL", detail="(빈 트리 또는 user.* 미설정 가능) " + err, safe=False)
        return res
    res.update(action="INITIALIZED",
               detail="로컬 git 생성 완료(.gitignore +%d, 리모트/push 없음 — owner가 private repo 생성·연결만 하면 됨)" % n)
    return res


def sync_one(reg, proj, root, apply=False, autostash=False):
    res = {"path": proj["path"], "track": proj.get("track"), "tier": proj.get("tier"),
           "action": None, "detail": None, "safe": True}
    track = proj.get("track")

    if track == "UNREGISTERED":
        res.update(action="REGISTER_FIRST", detail="레지스트리 미등록 — 작업 전 분류 등록 필요", safe=False)
        return res
    if track in ("never", "vault"):
        res.update(action="SKIP", detail="track=%s (리모트 동기화 제외, 로컬 전용)" % track)
        return res
    if track == "review":
        res.update(action="NEEDS_CLASSIFY", detail="분류 미정 — tier/track 확정 필요")
        return res
    if track == "dedupe":
        res.update(action="DEDUPE", detail="중복 경로 — canonical 하나만 유지(정리 대상)")
        return res

    full = os.path.normpath(os.path.join(root, proj["path"]))
    if not os.path.isdir(full):
        res.update(action="MISSING", detail="경로 없음", safe=False)
        return res
    if not is_git(full):
        if track == "needs_repo":
            res.update(action="NEEDS_REPO", detail="git 아님 — --init-repo로 로컬 생성 가능 (리모트는 owner G2)")
        else:
            res.update(action="NOGIT", detail="git 아님")
        return res

    url = remote_url(full)
    sync_ok, push_ok, why = remote_safety(reg, url)
    res["push_ok"] = push_ok
    res["remote"] = url
    if not sync_ok:
        res.update(action="REMOTE_REFUSED", detail="리모트 차단(%s): %s" % (why, url), safe=False)
        return res

    dc = dirty_count(full)
    behind, ahead = upstream_delta(full)
    res["dirty"], res["behind"], res["ahead"] = dc, behind, ahead

    if apply:
        git(["fetch", "--prune", "origin"], full)
        behind, ahead = upstream_delta(full)
        res["behind"], res["ahead"] = behind, ahead

    if behind is None:
        res.update(action="NO_UPSTREAM", detail="upstream 미설정 — fetch만 가능 (dirty=%s)" % dc)
        return res
    if behind == 0:
        res.update(action="UP_TO_DATE", detail="최신 (ahead=%s, dirty=%s)" % (ahead, dc))
        return res

    if dc and dc > 0:
        if not autostash:
            res.update(action="REPORT_ONLY",
                       detail="dirty(%s) + behind(%s) — 안전상 동기화 보류. commit/stash 후 재실행 또는 --autostash" % (dc, behind))
            return res
        if not apply:
            res.update(action="WOULD_AUTOSTASH",
                       detail="[dry-run] dirty(%s) → stash→rebase %s→pop 예정" % (dc, behind))
            return res
        rc, _, err = git(["stash", "push", "-u", "-m", "PCP-autostash"], full)
        if rc != 0:
            res.update(action="STASH_FAIL", detail="stash 실패: " + err, safe=False)
            return res
        rc, _, err = git(["pull", "--rebase", "origin"], full)
        if rc != 0:
            git(["rebase", "--abort"], full)
            git(["stash", "pop"], full)
            res.update(action="REBASE_ABORTED",
                       detail="rebase 충돌 → 중단·복원(stash pop) 완료. 수동 해결 필요: " + err, safe=False)
            return res
        rc, _, err = git(["stash", "pop"], full)
        if rc != 0:
            res.update(action="STASH_CONFLICT",
                       detail="rebase 성공·stash pop 충돌 — stash 보존(소실 없음). 수동 머지 필요", safe=False)
            return res
        res.update(action="AUTOSTASH_SYNCED", detail="dirty 보존 + %s 커밋 rebase 완료" % behind)
        return res

    if not apply:
        res.update(action="WOULD_REBASE", detail="[dry-run] clean → rebase %s 커밋 예정" % behind)
        return res
    rc, _, err = git(["pull", "--rebase", "origin"], full)
    if rc != 0:
        git(["rebase", "--abort"], full)
        res.update(action="REBASE_ABORTED", detail="충돌 → 중단·원복: " + err, safe=False)
        return res
    res.update(action="REBASED", detail="clean + %s 커밋 rebase 완료" % behind)
    return res


def scan_unregistered(reg, root):
    """root 1~2단계 아래에서 git repo를 찾아 registry 등록 여부 대조."""
    registered = set(os.path.normpath(os.path.join(root, p["path"])).replace("\\", "/")
                     for p in reg["projects"])
    found = []
    cand = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isdir(p) and not name.startswith("."):
            cand.append(p)
            sub = os.path.join(root, name)
            if os.path.isdir(sub):
                for n2 in sorted(os.listdir(sub)):
                    pp = os.path.join(sub, n2)
                    if os.path.isdir(pp):
                        cand.append(pp)
    for p in cand:
        if is_git(p):
            norm = os.path.normpath(p).replace("\\", "/")
            if norm not in registered:
                found.append(os.path.relpath(p, root).replace("\\", "/"))
    return found


def main():
    ap = argparse.ArgumentParser(description="PCP v1 Safe-Sync (v1.1)")
    ap.add_argument("path", nargs="?", help="프로젝트 경로 (절대 또는 D:/00.test 상대)")
    ap.add_argument("--all", action="store_true", help="레지스트리 전체 상태 보고")
    ap.add_argument("--scan", action="store_true", help="미등록 git repo 탐지")
    ap.add_argument("--apply", action="store_true", help="실제 동기화 (기본 dry-run)")
    ap.add_argument("--autostash", action="store_true", help="dirty 시 stash→rebase→pop")
    ap.add_argument("--init-repo", dest="init", action="store_true", help="로컬 git 생성(+gitignore, 리모트 없음)")
    args = ap.parse_args()

    reg = load_registry()
    root = reg.get("workspace_root", "D:/00.test")

    if args.scan:
        found = scan_unregistered(reg, root)
        if not found:
            print("SCAN: 미등록 git repo 없음 ✅ (모든 git이 registry에 등록됨)")
        else:
            print("SCAN: 미등록 git repo %d개 — registry 등록 필요 (PCP 위반):" % len(found))
            for f in found:
                print("  -", f)
        log_ledger({"mode": "scan", "unregistered": found})
        return 0 if not found else 3

    if args.all:
        print("%-40s %-4s %-16s %s" % ("PROJECT", "TIER", "ACTION", "DETAIL"))
        print("-" * 104)
        for proj in reg["projects"]:
            res = sync_one(reg, proj, root, apply=args.apply, autostash=args.autostash)
            flag = "" if res["safe"] else "  [!]"
            print("%-40.40s %-4s %-16s %s%s" % (res["path"], str(res.get("tier")),
                                                str(res["action"]), res["detail"], flag))
            log_ledger({"mode": "all", "apply": args.apply, **res})
        return 0

    if not args.path:
        ap.error("프로젝트 경로 또는 --all/--scan 필요")

    proj = find_project(reg, args.path)
    if args.init:
        res = init_repo(reg, proj, root, apply=args.apply)
    else:
        res = sync_one(reg, proj, root, apply=args.apply, autostash=args.autostash)
    log_ledger({"mode": "init" if args.init else "single", "apply": args.apply, **res})
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["safe"] else 2


if __name__ == "__main__":
    sys.exit(main())
