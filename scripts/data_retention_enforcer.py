#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W9.T1 Data Retention Enforcer — PIPA 21조 (보존기간 만료) 자동 처리.

Master:    20260428_SORA_ENTERPRISE_GRADE_MASTER_v1.md (W9)
Policy:    .agent/policies/pipa_data_retention.yaml (data_categories.retention_days)
Decision:  D9 — Telegram 180일 / audit 3년 / RAG 5년 / personal 동의 기반

cron: 0 4 * * *  (매일 04:00 KST, ysh-server crontab)

Usage:
  python scripts/data_retention_enforcer.py [--dry-run] [--category <name>]
  --dry-run: 실 삭제 안 함, 영향 범위만 보고
  --category: 특정 카테고리만 처리 (없으면 전체 auto_purge=true 카테고리 모두)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("neo.scripts.data_retention")

POLICY_PATHS = [
    Path("/app/.agent/policies/pipa_data_retention.yaml"),
    Path("D:/00.test/neo-genesis/.agent/policies/pipa_data_retention.yaml"),
    Path(__file__).resolve().parent.parent / ".agent/policies/pipa_data_retention.yaml",
]
AUDIT_LOG = Path("/app/data/logs/data_retention_audit.jsonl")
AUDIT_LOG_HOST = Path("D:/00.test/neo-genesis/data/logs/data_retention_audit.jsonl")


@dataclass
class RetentionResult:
    category: str
    action: str  # purge / archive / skip / error
    count: int = 0
    dry_run: bool = False
    error: Optional[str] = None
    detail: str = ""


def _load_policy() -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.error("PyYAML required: pip install pyyaml")
        sys.exit(2)
    for p in POLICY_PATHS:
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("pipa_data_retention.yaml not found")


def _audit_log(result: RetentionResult) -> None:
    """audit log 기록 (PIPA 입증용 영구 보존)."""
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "category": result.category,
        "action": result.action,
        "count": result.count,
        "dry_run": result.dry_run,
        "error": result.error,
        "detail": result.detail,
    }
    target = AUDIT_LOG if AUDIT_LOG.parent.exists() else AUDIT_LOG_HOST
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── 카테고리별 처리 ──

def _purge_jsonl(path: Path, retention_days: int, dry_run: bool, max_purge: int) -> RetentionResult:
    """JSONL 파일에서 retention_days 초과한 row 삭제."""
    if not path.exists():
        return RetentionResult(category=str(path.name), action="skip",
                               detail=f"file not found: {path}")
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    kept, purged = [], 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line_s = line.strip()
            if not line_s:
                continue
            try:
                row = json.loads(line_s)
                ts_str = row.get("ts") or row.get("timestamp") or row.get("time") or ""
                # ISO 8601 parsing
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if ts_naive < cutoff:
                    purged += 1
                    if purged > max_purge:
                        # safety stop
                        kept.extend([line])
                        break
                    continue
                kept.append(line)
            except Exception:
                # 파싱 실패한 라인은 그대로 보존
                kept.append(line)

    if not dry_run and purged > 0:
        path.write_text("".join(kept), encoding="utf-8")
    return RetentionResult(
        category=str(path.name),
        action="purge",
        count=purged,
        dry_run=dry_run,
        detail=f"cutoff={cutoff.isoformat()}, kept={len(kept)}",
    )


def _purge_glob(pattern: str, retention_days: int, dry_run: bool) -> RetentionResult:
    """Glob 패턴 매칭 파일 중 mtime 이 retention 초과한 파일 삭제."""
    import glob
    cutoff_ts = time.time() - retention_days * 86400
    matched = glob.glob(pattern)
    purged = 0
    for fpath in matched:
        try:
            if os.path.getmtime(fpath) < cutoff_ts:
                if not dry_run:
                    os.unlink(fpath)
                purged += 1
        except OSError:
            continue
    return RetentionResult(
        category=pattern,
        action="purge",
        count=purged,
        dry_run=dry_run,
        detail=f"matched={len(matched)} pattern={pattern}",
    )


def _purge_assistant_memory(path_str: str, retention_days: int, dry_run: bool) -> RetentionResult:
    """assistant_memory.json 의 conversations 배열에서 ts 초과한 entry 삭제."""
    path = Path(path_str)
    if not path.exists():
        return RetentionResult(category="telegram_messages", action="skip",
                               detail=f"file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return RetentionResult(category="telegram_messages", action="error",
                               error=str(e)[:100])

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    convs = data.get("conversations") or []
    kept, purged = [], 0
    for c in convs:
        try:
            ts = datetime.fromisoformat((c.get("ts") or "").replace("Z", "+00:00"))
            ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
            if ts_naive < cutoff:
                purged += 1
                continue
        except Exception:
            pass
        kept.append(c)

    if not dry_run and purged > 0:
        data["conversations"] = kept
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return RetentionResult(
        category="telegram_messages",
        action="purge",
        count=purged,
        dry_run=dry_run,
        detail=f"cutoff={cutoff.isoformat()}, kept={len(kept)}",
    )


def process_category(name: str, spec: dict, dry_run: bool, max_purge: int) -> RetentionResult:
    """단일 category 처리."""
    if not spec.get("auto_purge", False):
        return RetentionResult(category=name, action="skip",
                               detail="auto_purge=false (manual only)")
    retention_days = spec.get("retention_days", 0)
    if retention_days <= 0:
        return RetentionResult(category=name, action="skip",
                               detail="retention_days<=0 (infinite)")
    location = spec.get("location", "")
    if not location:
        return RetentionResult(category=name, action="skip", detail="no location")

    if name == "telegram_messages":
        return _purge_assistant_memory(location, retention_days, dry_run)
    if "*" in location:
        return _purge_glob(location, retention_days, dry_run)
    if location.endswith(".jsonl") or location.endswith(".log"):
        return _purge_jsonl(Path(location), retention_days, dry_run, max_purge)
    # 기본 — 디렉토리면 mtime 기반 file purge
    p = Path(location)
    if p.is_dir():
        return _purge_glob(str(p) + "/*", retention_days, dry_run)
    return RetentionResult(category=name, action="skip",
                           detail=f"unsupported location format: {location}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="PIPA Data Retention Enforcer (W9.T1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="영향 범위만 보고, 실 삭제 X")
    parser.add_argument("--category", type=str, default=None,
                        help="특정 카테고리만 처리 (없으면 auto_purge 카테고리 모두)")
    args = parser.parse_args(argv)

    policy = _load_policy()
    enforcement = policy.get("enforcement", {})
    if args.dry_run is False:
        # policy 의 dry_run_default 우선
        args.dry_run = enforcement.get("dry_run_default", False)
    max_purge = enforcement.get("safety", {}).get("max_purge_per_run", 1000)

    categories = policy.get("data_categories", {})
    target_cats = [args.category] if args.category else list(categories.keys())

    print(f"=== Data Retention Enforcer (W9.T1) ===")
    print(f"  dry_run: {args.dry_run}")
    print(f"  max_purge_per_run: {max_purge}")
    print(f"  categories: {len(target_cats)}")
    print()

    results = []
    for name in target_cats:
        spec = categories.get(name)
        if not spec:
            print(f"  ⚠️  unknown category: {name}")
            continue
        try:
            r = process_category(name, spec, args.dry_run, max_purge)
        except Exception as e:
            r = RetentionResult(category=name, action="error", error=str(e)[:200])
        marker = {"purge": "🗑️ ", "skip": "⊘ ", "error": "💥 ", "archive": "📦 "}.get(r.action, "? ")
        print(f"  {marker}{name:25} action={r.action:8} count={r.count:5} {r.detail}")
        if r.error:
            print(f"     error: {r.error}")
        _audit_log(r)
        results.append(r)

    total_purged = sum(r.count for r in results if r.action == "purge")
    print(f"\n=== Summary: {total_purged} rows purged across {len(results)} categories ===")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sys.exit(main(sys.argv[1:]))
