"""
SSOT Tier Classification — .agent/ 디렉토리의 모든 파일을 4-tier 로 자동 분류.

Tier 정의:
  1 CRITICAL — 매 세션 자동 적재 (규칙 / live state / active section)
  2 IMPORTANT — 필요 시 lazy load (장기 메모리 / policy / runbook)
  3 REFERENCE — RAG 또는 명시 Read (deep research / persona body)
  4 ARCHIVE — 보존 only, 미적재 (30일+ stale / 완료 / backup)

분류 신호 (우선순위 순):
  - tier_overrides: 화이트리스트 (NEO_MASTER_RULES → Tier 1)
  - path patterns: backups/eval-runs/JSONL/claude-checkpoints → Tier 4
  - age: 30일+ 미수정 + reference 0건 → Tier 4 후보
  - size: 100KB+ 단일 파일 → split 권고 (active-tasks/daily-log/handoff)
  - 확장자: persona/policy/yaml → tier 2

출력:
  - .agent/registries/tier_classification.yaml
  - stdout: tier 별 카운트 + 토큰 추정 + ROI

비용 추정:
  - 1 char ≈ 0.25 tokens (영어), 0.5 tokens (한국어 mix)
  - Opus 4.7 input: $15/M tokens
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# ---- Configuration --------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / ".agent"
OUTPUT_YAML = AGENT_DIR / "registries" / "tier_classification.yaml"

# Hard overrides — path glob → tier
TIER_1_PATHS = {
    "NEO_MASTER_RULES.md",
    "shared-brain/status.json",
    "shared-brain/handoff.md",          # split: recent-7d → tier 1, rest → tier 4
    "shared-brain/active-tasks.md",     # split: active section → tier 1, completed → tier 4
    "shared-brain/cross-agent-review.md",  # split: active → tier 1, completed → tier 4
    "shared-brain/device_inventory.json",  # fleet live state
    "shared-brain/device_heartbeats.json", # fleet live state
}

# Hard overrides — explicit Tier 4 (append-only logs / hashes / live tracking but no LLM value)
TIER_4_EXPLICIT_PATHS = {
    "shared-brain/daily-log.md",     # 271KB append-only, 사후 분석용 RAG 만
    ".bible_hash",                   # auto-generated 16 byte hash
}

TIER_2_PATHS_PREFIX = (
    "knowledge/AGENT_SHARED_MEMORY.md",
    "knowledge/AGENT_RUNTIME_OPTIMIZATION.md",
    "knowledge/CLAUDE_COLLABORATION.md",
    "knowledge/OWNER_PROFILE.md",
    "knowledge/MASTER_CREDENTIAL_ACCESS_STANDARD.md",
    "contracts/",
    "policies/",
    "runbooks/",
    "BIBLE.md",
)

TIER_3_PATHS_PREFIX = (
    "knowledge/agent-environment/",
    "knowledge/rag-master/",
    "knowledge/security/",
    "knowledge/wikipedia-drafts/",
    "knowledge/wikidata-entities/",
    "knowledge/persona-research/",
    "knowledge/reports/",
    "knowledge/cross-publish/",
    "knowledge/external-api-catalog/",
    "knowledge/awesome-list-prs/",
    "knowledge/paperswithcode-submissions/",
    "personas/tier-",      # persona body
    "personas/_schema/",
    "personas/dispatcher/",
    "personas/INDEX.md",
    "skills/",
    "schemas/",
    "registries/",
    "workflows/",
    "migrations/",
)

TIER_4_PATH_REGEX = re.compile(
    r"(backups-ssot-merge-|eval-runs/|claude-checkpoints/|rollback/|\.jsonl$)"
)

# Files > THRESHOLD_SIZE that are append-only logs → split candidate
SPLIT_CANDIDATE_NAMES = {
    "active-tasks.md",
    "daily-log.md",
    "handoff.md",
    "cross-agent-review.md",
}

# Token estimation:
# Empirical observation: mixed Korean+English markdown ≈ 0.4 tokens/char (Anthropic tokenizer)
TOKENS_PER_CHAR = 0.4

# Opus 4.7 input pricing
USD_PER_M_INPUT_TOKENS = 15.0


# ---- Data classes ---------------------------------------------------------


@dataclass
class FileEntry:
    path: str                 # relative to .agent/
    size_bytes: int
    last_modified_ts: float
    age_days: float
    tier: int                 # 1..4
    tier_reason: str
    is_split_candidate: bool = False
    notes: str = ""
    estimated_tokens: int = 0


@dataclass
class ClassificationReport:
    generated_at: str
    repo_root: str
    agent_root: str
    total_files: int
    total_bytes: int
    estimated_tokens_total: int
    tier_counts: dict[int, int] = field(default_factory=dict)
    tier_bytes: dict[int, int] = field(default_factory=dict)
    tier_tokens: dict[int, int] = field(default_factory=dict)
    split_candidates: list[str] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)

    def to_yaml_str(self) -> str:
        """Hand-rolled YAML (no PyYAML dependency)."""
        lines: list[str] = []
        lines.append(f"generated_at: '{self.generated_at}'")
        lines.append(f"repo_root: '{self.repo_root}'")
        lines.append(f"agent_root: '{self.agent_root}'")
        lines.append(f"total_files: {self.total_files}")
        lines.append(f"total_bytes: {self.total_bytes}")
        lines.append(f"estimated_tokens_total: {self.estimated_tokens_total}")

        lines.append("tier_counts:")
        for t in sorted(self.tier_counts):
            lines.append(f"  {t}: {self.tier_counts[t]}")
        lines.append("tier_bytes:")
        for t in sorted(self.tier_bytes):
            lines.append(f"  {t}: {self.tier_bytes[t]}")
        lines.append("tier_tokens:")
        for t in sorted(self.tier_tokens):
            lines.append(f"  {t}: {self.tier_tokens[t]}")

        lines.append("split_candidates:")
        for s in self.split_candidates:
            lines.append(f"  - '{s}'")

        lines.append("files:")
        for f in sorted(self.files, key=lambda x: (x.tier, -x.size_bytes)):
            lines.append(f"  - path: '{f.path}'")
            lines.append(f"    size_bytes: {f.size_bytes}")
            lines.append(f"    age_days: {f.age_days:.1f}")
            lines.append(f"    tier: {f.tier}")
            tier_reason_escaped = f.tier_reason.replace("'", "''")
            lines.append(f"    tier_reason: '{tier_reason_escaped}'")
            lines.append(f"    is_split_candidate: {str(f.is_split_candidate).lower()}")
            lines.append(f"    estimated_tokens: {f.estimated_tokens}")
            if f.notes:
                notes_escaped = f.notes.replace("'", "''")
                lines.append(f"    notes: '{notes_escaped}'")
        return "\n".join(lines) + "\n"


# ---- Classification logic -------------------------------------------------


def classify_file(rel_path: str, size_bytes: int, age_days: float) -> tuple[int, str, bool, str]:
    """
    Returns (tier, reason, is_split_candidate, notes).
    """
    name = os.path.basename(rel_path)
    rel_posix = rel_path.replace("\\", "/")

    # ---- Tier 4 — archive patterns first ----
    if TIER_4_PATH_REGEX.search(rel_posix):
        return 4, "archive_path_pattern", False, ""

    # ---- Tier 4 — explicit path overrides ----
    if rel_posix in TIER_4_EXPLICIT_PATHS:
        return 4, "tier4_explicit_override", False, "append-only / auto-generated, LLM 적재 가치 0"

    # ---- Tier 1 — hardcoded critical SSOT ----
    if rel_posix in TIER_1_PATHS:
        is_split = name in SPLIT_CANDIDATE_NAMES and size_bytes > 50_000
        notes = (
            "split: recent/active section → tier 1, older → tier 4"
            if is_split
            else ""
        )
        return 1, "tier1_critical_ssot", is_split, notes

    # ---- Tier 2 — hardcoded important paths ----
    for prefix in TIER_2_PATHS_PREFIX:
        if rel_posix == prefix or rel_posix.startswith(prefix):
            return 2, "tier2_important_path", False, "lazy load 권장 (CLAUDE.md @import 제거)"

    # ---- Tier 3 — hardcoded reference paths ----
    for prefix in TIER_3_PATHS_PREFIX:
        if rel_posix.startswith(prefix):
            tier = 3
            reason = "tier3_reference_path"
            notes = ""
            # 추가 demotion: 90일+ stale 이면 tier 4
            if age_days > 90:
                tier = 4
                reason = "tier3_path_but_stale_90d"
                notes = f"마지막 수정 {age_days:.0f}일 전, archive 후보"
            return tier, reason, False, notes

    # ---- Heuristics for unmatched files ----
    # Append-only logs / jsonl 외 흔치 않은 케이스
    if size_bytes > 200_000:
        # 매우 큰 파일은 검증 필요
        return 3, "default_large_file", True, f"size {size_bytes // 1024}KB — 분할 검토 권고"

    if age_days > 60:
        return 4, "default_stale_60d", False, f"{age_days:.0f}일 미수정, archive 후보"

    return 3, "default_unclassified", False, "분류 패턴 미매칭 — 수동 검토 권고"


def scan(agent_dir: Path) -> ClassificationReport:
    now = time.time()
    files: list[FileEntry] = []
    total_bytes = 0
    total_tokens = 0
    tier_counts: dict[int, int] = defaultdict(int)
    tier_bytes: dict[int, int] = defaultdict(int)
    tier_tokens: dict[int, int] = defaultdict(int)
    split_candidates: list[str] = []

    for p in agent_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(agent_dir).as_posix()
        try:
            stat = p.stat()
        except OSError:
            continue
        size = stat.st_size
        mtime = stat.st_mtime
        age_days = (now - mtime) / 86400.0

        tier, reason, is_split, notes = classify_file(rel, size, age_days)

        # token 추정 — 텍스트 파일만
        if p.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt", ".toml", ".jsonl"}:
            est_tokens = int(size * TOKENS_PER_CHAR)
        else:
            est_tokens = 0

        entry = FileEntry(
            path=rel,
            size_bytes=size,
            last_modified_ts=mtime,
            age_days=age_days,
            tier=tier,
            tier_reason=reason,
            is_split_candidate=is_split,
            notes=notes,
            estimated_tokens=est_tokens,
        )
        files.append(entry)

        total_bytes += size
        total_tokens += est_tokens
        tier_counts[tier] += 1
        tier_bytes[tier] += size
        tier_tokens[tier] += est_tokens
        if is_split:
            split_candidates.append(rel)

    return ClassificationReport(
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        repo_root=str(REPO_ROOT),
        agent_root=str(agent_dir),
        total_files=len(files),
        total_bytes=total_bytes,
        estimated_tokens_total=total_tokens,
        tier_counts=dict(tier_counts),
        tier_bytes=dict(tier_bytes),
        tier_tokens=dict(tier_tokens),
        split_candidates=split_candidates,
        files=files,
    )


# ---- ROI calc -------------------------------------------------------------


def print_summary(report: ClassificationReport) -> None:
    print(f"=== SSOT Tier Classification ===")
    print(f"Generated: {report.generated_at}")
    print(f"Total files: {report.total_files}")
    print(f"Total bytes: {report.total_bytes:,} ({report.total_bytes / 1024 / 1024:.2f} MB)")
    print(f"Estimated tokens (full scan): {report.estimated_tokens_total:,}")
    print()
    print(f"{'Tier':<6}{'Count':>8}{'Bytes':>14}{'Tokens':>12}")
    for t in sorted(report.tier_counts):
        label = {1: "1 CRIT", 2: "2 IMP", 3: "3 REF", 4: "4 ARCH"}[t]
        print(
            f"{label:<6}{report.tier_counts[t]:>8}"
            f"{report.tier_bytes[t]:>14,}{report.tier_tokens[t]:>12,}"
        )
    print()
    print("---- ROI (세션당 적재 토큰 / 비용) ----")
    # Baseline: 현재 import chain 이 tier 1 + tier 2 전부 자동 적재 가정
    current_auto = report.tier_tokens.get(1, 0) + report.tier_tokens.get(2, 0)
    # 권고: tier 1 만 자동 (split 후 active section 만, conservative 50%)
    tier1_split_fraction = 0.30  # active section 만 = 전체의 ~30%
    recommended_auto = int(
        report.tier_tokens.get(1, 0) * tier1_split_fraction
        # tier 2 는 lazy load 로 0
    )
    delta = current_auto - recommended_auto
    cost_per_session_now = current_auto / 1_000_000 * USD_PER_M_INPUT_TOKENS
    cost_per_session_after = recommended_auto / 1_000_000 * USD_PER_M_INPUT_TOKENS
    cost_delta = cost_per_session_now - cost_per_session_after
    print(f"현 자동 적재 추정 (tier 1+2 sum): {current_auto:,} tokens / ${cost_per_session_now:.3f}/세션")
    print(
        f"권고 자동 적재 (tier 1 split 30%): "
        f"{recommended_auto:,} tokens / ${cost_per_session_after:.3f}/세션"
    )
    print(f"세션당 절감: {delta:,} tokens / ${cost_delta:.3f}")
    print(f"월 30세션 추정 절감: ${cost_delta * 30:.2f}")
    print()
    print(f"Split candidates ({len(report.split_candidates)}):")
    for s in report.split_candidates:
        print(f"  - {s}")


# ---- Entry point ----------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify .agent SSOT files into 4 tiers")
    parser.add_argument(
        "--agent-dir",
        type=Path,
        default=AGENT_DIR,
        help="Path to .agent directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_YAML,
        help="Output YAML path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also emit JSON next to YAML",
    )
    args = parser.parse_args()

    if not args.agent_dir.is_dir():
        print(f"ERROR: {args.agent_dir} not found", file=sys.stderr)
        return 1

    report = scan(args.agent_dir)
    print_summary(report)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.to_yaml_str(), encoding="utf-8")
    print(f"\nYAML written → {args.output}")

    if args.json:
        json_path = args.output.with_suffix(".json")
        payload = {
            "generated_at": report.generated_at,
            "repo_root": report.repo_root,
            "agent_root": report.agent_root,
            "total_files": report.total_files,
            "total_bytes": report.total_bytes,
            "estimated_tokens_total": report.estimated_tokens_total,
            "tier_counts": report.tier_counts,
            "tier_bytes": report.tier_bytes,
            "tier_tokens": report.tier_tokens,
            "split_candidates": report.split_candidates,
            "files": [asdict(f) for f in report.files],
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON written → {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
