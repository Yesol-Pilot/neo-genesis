"""
archive_ssot.py — SSOT archive tool (Phase 1 skeleton)

Status: Phase 1 design — DRY-RUN ONLY. --execute is intentionally blocked
        until Phase 2 implementation lands. See SKELETON.md for full design.

Master design: .agent/knowledge/20260512_AGENT_DIR_OPTIMIZATION_MASTER_v1.md
Implementation guide: scripts/agent/archive_ssot.py.SKELETON.md
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Force UTF-8 stdout on Windows (cp949 default chokes on emoji in SSOT)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

KST = timezone(timedelta(hours=9))

DEFAULT_ROOT = Path("D:/00.test/neo-genesis")
SHARED_BRAIN = "Path('.agent/shared-brain')"  # rel to root

# Files in scope (Phase 1 dry-run preview)
TARGET_FILES = [
    "active-tasks.md",
    "handoff.md",
    "cross-agent-review.md",
]


@dataclass
class ArchiveCandidate:
    file: str
    block_id: str  # heading or anchor
    line_start: int
    line_end: int
    kb: float
    age_days: int
    rule: str  # R1 / R2 / R3
    reason: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Archive stale SSOT entries (Phase 1 skeleton)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview only (Phase 1 supported)")
    mode.add_argument("--execute", action="store_true", help="Apply changes (Phase 2 only, blocked here)")
    mode.add_argument("--rollback", type=str, metavar="TIMESTAMP", help="Restore from backup (Phase 2 only)")
    mode.add_argument("--stats", action="store_true", help="Read-only stats")
    p.add_argument("--confirm", action="store_true", help="Required for --execute")
    p.add_argument(
        "--target-file",
        type=str,
        choices=TARGET_FILES + ["all"],
        default="all",
    )
    p.add_argument("--age-days", type=int, default=30, help="Archive entries older than N days (min 7)")
    p.add_argument("--weekly", action="store_true", help="cron mode (Phase 4 only)")
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Repo root")
    return p.parse_args()


def safety_check(args: argparse.Namespace) -> None:
    """Enforce safety guards before any work."""
    if args.age_days < 7:
        sys.stderr.write(
            f"[ABORT] age-days must be >= 7 (got {args.age_days}). "
            "7-day recent window is a hard safety floor.\n"
        )
        sys.exit(4)
    if args.execute and not args.confirm:
        sys.stderr.write(
            "[ABORT] --execute requires --confirm. Phase 1 skeleton blocks --execute regardless.\n"
        )
        sys.exit(4)
    if args.execute or args.rollback:
        sys.stderr.write(
            "[ABORT] Phase 1 skeleton: --execute and --rollback are not yet implemented. "
            "See scripts/agent/archive_ssot.py.SKELETON.md for the implementation plan, "
            "and .agent/knowledge/20260512_AGENT_DIR_OPTIMIZATION_MASTER_v1.md "
            "for the migration phases.\n"
        )
        sys.exit(2)


def collect_files(root: Path, target: str) -> list[Path]:
    base = root / ".agent" / "shared-brain"
    if target == "all":
        return [base / f for f in TARGET_FILES if (base / f).exists()]
    return [base / target] if (base / target).exists() else []


def extract_dates(text: str) -> list[datetime]:
    """Heuristic: pull YYYY-MM-DD patterns. Returns sorted ascending."""
    pattern = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
    out: list[datetime] = []
    for m in pattern.finditer(text):
        y, mo, d = (int(x) for x in m.groups())
        try:
            out.append(datetime(y, mo, d, tzinfo=KST))
        except ValueError:
            continue
    out.sort()
    return out


def is_block_archivable(block_text: str, age_cutoff: datetime, file_kind: str) -> tuple[bool, str]:
    """
    Heuristic per-file rules (Phase 1 conservative).
    Returns (archivable, reason).
    """
    # Active markers — never archive
    if "[ ]" in block_text:
        return False, "has [ ] unchecked"
    if any(
        marker in block_text
        for marker in ["📅 Weekly", "🟣 Strategy Lead", "📅 Weekly Progress Review", "## Active"]
    ):
        return False, "operational marker"

    dates = extract_dates(block_text)
    if not dates:
        return False, "no parseable date (safety: keep)"

    newest = dates[-1]
    if newest >= age_cutoff:
        return False, f"newest date {newest.date()} within window"

    if file_kind == "active-tasks.md":
        if "[x]" not in block_text:
            return False, "no [x] completion marker"
        return True, f"R1 [x] completed, newest={newest.date()}"
    if file_kind == "handoff.md":
        return True, f"R2 age >= {age_cutoff.date()}, newest={newest.date()}"
    if file_kind == "cross-agent-review.md":
        if not re.search(r"result:\s*(new_signal|no_new_signal|failed)", block_text):
            return False, "no resolved result"
        return True, f"R3 resolved CCR, newest={newest.date()}"
    return False, "unknown file kind"


def split_blocks(text: str, file_kind: str) -> list[tuple[int, int, str]]:
    """
    Split text into blocks by heading boundaries.
    Returns list of (line_start, line_end, block_text).
    Conservative: h2/h3 for active-tasks/handoff, '- [x] ' bullet for ccr.
    """
    lines = text.splitlines(keepends=True)
    blocks: list[tuple[int, int, str]] = []

    if file_kind == "cross-agent-review.md":
        # Block = consecutive lines starting with '- [x]' bullet + its indented continuation
        start = None
        for i, line in enumerate(lines):
            if re.match(r"- \[[ x]\] `ccr-", line):
                if start is not None:
                    blocks.append((start, i, "".join(lines[start:i])))
                start = i
        if start is not None:
            blocks.append((start, len(lines), "".join(lines[start:])))
        return blocks

    # active-tasks / handoff: split on ## or ### heading
    heading_re = re.compile(r"^(#{2,3})\s+")
    start = 0
    for i, line in enumerate(lines):
        if heading_re.match(line) and i > start:
            blocks.append((start, i, "".join(lines[start:i])))
            start = i
    if start < len(lines):
        blocks.append((start, len(lines), "".join(lines[start:])))
    return blocks


def first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("- ["):
            return stripped[:120]
    return "(no heading)"


def analyze(path: Path, age_days: int) -> list[ArchiveCandidate]:
    file_kind = path.name
    text = path.read_text(encoding="utf-8")
    age_cutoff = datetime.now(KST) - timedelta(days=age_days)
    candidates: list[ArchiveCandidate] = []
    for start, end, block in split_blocks(text, file_kind):
        archivable, reason = is_block_archivable(block, age_cutoff, file_kind)
        if not archivable:
            continue
        dates = extract_dates(block)
        newest = dates[-1] if dates else datetime.now(KST)
        age = (datetime.now(KST) - newest).days
        rule = {"active-tasks.md": "R1", "handoff.md": "R2", "cross-agent-review.md": "R3"}[file_kind]
        candidates.append(
            ArchiveCandidate(
                file=file_kind,
                block_id=first_heading(block),
                line_start=start + 1,
                line_end=end,
                kb=len(block.encode("utf-8")) / 1024,
                age_days=age,
                rule=rule,
                reason=reason,
            )
        )
    return candidates


def emit_dry_run(files: list[Path], age_days: int) -> int:
    total_candidates = 0
    total_kb_reducible = 0.0

    print(f"[DRY-RUN] age-days={age_days}, target files={[f.name for f in files]}")
    print(f"[DRY-RUN] now (KST) = {datetime.now(KST).isoformat()}")
    print()

    for path in files:
        if not path.exists():
            print(f"[skip] {path.name} not found")
            continue
        size_kb = path.stat().st_size / 1024
        candidates = analyze(path, age_days)
        print(f"--- {path.name} ({size_kb:.1f} KB) ---")
        if not candidates:
            print("  no candidates")
            print()
            continue
        kb = sum(c.kb for c in candidates)
        by_rule: dict[str, int] = {}
        for c in candidates:
            by_rule[c.rule] = by_rule.get(c.rule, 0) + 1
        reduction_pct = (kb / size_kb * 100) if size_kb > 0 else 0
        print(f"  candidates: {len(candidates)} blocks ({kb:.1f} KB)")
        print(f"  by rule: {by_rule}")
        print(f"  after archive: {(size_kb - kb):.1f} KB ({reduction_pct:.0f}% reducible)")
        print("  sample blocks:")
        for c in candidates[:5]:
            print(f"    L{c.line_start:>5}  age={c.age_days:>3}d  {c.rule}  {c.block_id[:80]}")
        if len(candidates) > 5:
            print(f"    ... and {len(candidates) - 5} more")
        print()
        total_candidates += len(candidates)
        total_kb_reducible += kb

    print("[SUMMARY]")
    print(f"  total candidates: {total_candidates}")
    print(f"  total reducible: {total_kb_reducible:.1f} KB")
    print(f"  next step: see scripts/agent/archive_ssot.py.SKELETON.md for --execute implementation")
    return 0 if total_candidates > 0 else 1


def emit_stats(files: list[Path]) -> int:
    print("[STATS]")
    for path in files:
        if not path.exists():
            continue
        size_kb = path.stat().st_size / 1024
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {path.name}: {size_kb:.1f} KB, {line_count} lines")
    return 0


def main() -> int:
    args = parse_args()
    safety_check(args)
    files = collect_files(args.root, args.target_file)
    if not files:
        sys.stderr.write(f"[ERR] no target files found under {args.root / '.agent/shared-brain'}\n")
        return 1
    if args.stats:
        return emit_stats(files)
    if args.dry_run:
        return emit_dry_run(files, args.age_days)
    return 2  # unreachable (safety_check covers it)


if __name__ == "__main__":
    sys.exit(main())
