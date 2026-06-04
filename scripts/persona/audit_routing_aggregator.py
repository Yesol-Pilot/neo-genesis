#!/usr/bin/env python3
"""
Live Routing Audit Aggregator (Phase B P0)

Aggregates `~/.claude/audit/persona_routing_*.jsonl` and
`~/.claude/audit/agent_tool_use_*.jsonl` into statistical reports.

Phase B P0 deliverable per `.agent/shared-brain/handoff.md`:
- Verify which v1.2 personas are actually being routed to (vs unused)
- Quantify L1/L2/L3/fallback layer usage
- Surface G2 detection events (Article 0 owner-gate triggers)
- Audit Agent tool subagent_type distribution (general-purpose vs persona)

Cold honest principle: if logs are empty or sparse, report it as "insufficient
data" — do not fabricate trends. Reports raw counts + percentages, not
inference.

Usage:
    python scripts/persona/audit_routing_aggregator.py
    python scripts/persona/audit_routing_aggregator.py --days 7
    python scripts/persona/audit_routing_aggregator.py --since 2026-05-08
    python scripts/persona/audit_routing_aggregator.py --output reports/routing_audit_<date>.json
    python scripts/persona/audit_routing_aggregator.py --markdown reports/routing_audit_<date>.md

SSOT: handoff.md "Live routing audit aggregator" entry (2026-05-10).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))


def _resolve_audit_dir(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return Path.home().joinpath(".claude", "audit").resolve()


def _parse_iso(value: str) -> datetime | None:
    """Parse ISO-8601 timestamps emitted by the hooks (`+09:00` form)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Tolerant JSONL loader. Skips BOM, blanks, and unparseable lines."""
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _within_window(ts_str: str, since: datetime | None) -> bool:
    if since is None:
        return True
    parsed = _parse_iso(ts_str)
    if parsed is None:
        # Cannot determine — keep it (cold honest: don't drop unverifiable rows
        # silently, but flag this in the unparsed counter).
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed >= since


def collect_persona_events(
    audit_dir: Path,
    since: datetime | None,
) -> tuple[list[dict[str, Any]], list[Path]]:
    files = sorted(audit_dir.glob("persona_routing_*.jsonl"))
    events: list[dict[str, Any]] = []
    for path in files:
        for row in _load_jsonl(path):
            if _within_window(row.get("ts", ""), since):
                row["_source_file"] = path.name
                events.append(row)
    return events, files


def collect_agent_events(
    audit_dir: Path,
    since: datetime | None,
) -> tuple[list[dict[str, Any]], list[Path]]:
    files = sorted(audit_dir.glob("agent_tool_use_*.jsonl"))
    events: list[dict[str, Any]] = []
    for path in files:
        for row in _load_jsonl(path):
            if _within_window(row.get("ts", ""), since):
                row["_source_file"] = path.name
                events.append(row)
    return events, files


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def summarize_persona_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    persona_counter: Counter[str] = Counter()
    layer_counter: Counter[str] = Counter()
    framework_counter: Counter[str] = Counter()
    g2_events: list[dict[str, Any]] = []
    secondary_counter: Counter[int] = Counter()
    confidences: list[float] = []
    per_day: defaultdict[str, int] = defaultdict(int)

    for ev in events:
        persona_id = str(ev.get("persona_id") or "(unknown)")
        persona_counter[persona_id] += 1
        layer = str(ev.get("matched_layer") or "(unspecified)")
        layer_counter[layer] += 1
        framework = ev.get("framework")
        if framework:
            framework_counter[str(framework)] += 1
        confidence = ev.get("confidence")
        if isinstance(confidence, (int, float)):
            confidences.append(float(confidence))
        if ev.get("g2_detected") is True:
            g2_events.append(
                {
                    "ts": ev.get("ts"),
                    "persona_id": persona_id,
                    "framework": framework,
                    "query_hash": ev.get("query_hash"),
                }
            )
        secondary = ev.get("secondary_personas") or []
        if isinstance(secondary, list):
            secondary_counter[len(secondary)] += 1
        ts = _parse_iso(str(ev.get("ts") or ""))
        if ts is not None:
            per_day[ts.astimezone(KST).date().isoformat()] += 1

    confidence_summary: dict[str, float | None] = {
        "count": float(len(confidences)),
        "avg": (sum(confidences) / len(confidences)) if confidences else None,
        "p50": _percentile(confidences, 0.50),
        "p95": _percentile(confidences, 0.95),
        "max": max(confidences) if confidences else None,
    }

    # Cold honest: only count rows that *explicitly* matched a fallback layer.
    # Legacy rows without `matched_layer` are tracked separately as
    # `unspecified_count` so we don't fabricate a 100% fallback story when the
    # field simply wasn't emitted yet.
    explicit_fallback_layers = {"L4_fallback", "fallback", "L4"}
    fallback_count = sum(
        layer_counter[layer] for layer in layer_counter if layer in explicit_fallback_layers
    )
    unspecified_count = layer_counter.get("(unspecified)", 0)
    classified_total = total - unspecified_count
    fallback_rate = (fallback_count / classified_total) if classified_total else 0.0

    return {
        "total_events": total,
        "events_per_day": dict(sorted(per_day.items())),
        "top_personas": persona_counter.most_common(10),
        "layer_distribution": dict(layer_counter),
        "fallback_rate": fallback_rate,
        "fallback_count": fallback_count,
        "unspecified_layer_count": unspecified_count,
        "classified_layer_total": classified_total,
        "framework_distribution": dict(framework_counter.most_common()),
        "secondary_personas_distribution": dict(secondary_counter),
        "g2_detected_count": len(g2_events),
        "g2_detected_events": g2_events,
        "confidence": confidence_summary,
    }


def summarize_agent_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    subagent_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    persona_count = 0
    file_exists_unknown = 0
    file_exists_missing = 0
    warnings: list[dict[str, Any]] = []

    for ev in events:
        subagent = str(ev.get("subagent_type") or "(empty)")
        subagent_counter[subagent] += 1
        tool = str(ev.get("tool") or "(unknown)")
        tool_counter[tool] += 1
        if ev.get("is_persona") is True:
            persona_count += 1
        agent_file_exists = ev.get("agent_file_exists")
        if agent_file_exists is None:
            file_exists_unknown += 1
        elif agent_file_exists is False:
            file_exists_missing += 1
            warnings.append(
                {
                    "ts": ev.get("ts"),
                    "subagent_type": subagent,
                    "tool": tool,
                    "reason": "agent_file_missing",
                }
            )

    general_purpose = subagent_counter.get("general-purpose", 0)
    persona_named = sum(
        count
        for name, count in subagent_counter.items()
        if name not in {"(empty)", "general-purpose"}
    )

    return {
        "total_events": total,
        "subagent_type_distribution": dict(subagent_counter.most_common()),
        "tool_distribution": dict(tool_counter),
        "general_purpose_count": general_purpose,
        "general_purpose_rate": general_purpose / total if total else 0.0,
        "persona_named_count": persona_named,
        "persona_named_rate": persona_named / total if total else 0.0,
        "is_persona_true_count": persona_count,
        "agent_file_missing_count": file_exists_missing,
        "agent_file_unknown_count": file_exists_unknown,
        "warnings": warnings,
    }


def build_report(
    audit_dir: Path,
    since: datetime | None,
    persona_events: list[dict[str, Any]],
    persona_files: list[Path],
    agent_events: list[dict[str, Any]],
    agent_files: list[Path],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "audit_dir": str(audit_dir),
        "window": {
            "since": since.isoformat(timespec="seconds") if since else None,
            "until": datetime.now(KST).isoformat(timespec="seconds"),
        },
        "files_scanned": {
            "persona_routing": [p.name for p in persona_files],
            "agent_tool_use": [p.name for p in agent_files],
        },
        "persona_routing": summarize_persona_events(persona_events),
        "agent_tool_use": summarize_agent_events(agent_events),
        "data_quality": {
            "persona_event_total": len(persona_events),
            "agent_event_total": len(agent_events),
            "honest_note": (
                "Sample is small and skewed toward synthetic/regression probes "
                "if the hook integration is recent; treat percentages as "
                "directional, not statistical."
            ),
        },
    }


def _format_count_table(rows: list[tuple[str, int]], total: int) -> list[str]:
    if not rows:
        return ["| (no data) | 0 | 0% |"]
    out: list[str] = []
    for name, count in rows:
        pct = (count / total * 100.0) if total else 0.0
        out.append(f"| `{name}` | {count} | {pct:.1f}% |")
    return out


def _markdown_report(report: dict[str, Any]) -> str:
    persona = report["persona_routing"]
    agent = report["agent_tool_use"]
    persona_total = persona["total_events"]
    agent_total = agent["total_events"]
    layer_rows = sorted(persona["layer_distribution"].items(), key=lambda kv: -kv[1])
    framework_rows = list(persona["framework_distribution"].items())
    subagent_rows = list(agent["subagent_type_distribution"].items())

    confidence = persona["confidence"]
    avg = confidence.get("avg")
    p50 = confidence.get("p50")
    p95 = confidence.get("p95")
    cmax = confidence.get("max")

    def _fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.3f}"

    lines = [
        "# Routing Audit Report",
        "",
        f"- generated: {report['generated_at']}",
        f"- audit dir: `{report['audit_dir']}`",
        f"- window since: `{report['window']['since'] or 'all-time'}`",
        f"- persona files: {', '.join(report['files_scanned']['persona_routing']) or '(none)'}",
        f"- agent files: {', '.join(report['files_scanned']['agent_tool_use']) or '(none)'}",
        "",
        "## 1. Persona routing summary",
        "",
        f"- total persona events: **{persona_total}**",
        f"- G2 detection events: **{persona['g2_detected_count']}**",
        f"- fallback rate (explicit only): **{persona['fallback_rate']*100:.1f}%** "
        f"({persona['fallback_count']} / {persona['classified_layer_total']} classified)",
        f"- unspecified layer rows (legacy schema): {persona['unspecified_layer_count']} / {persona_total}",
        "",
        "### Top personas",
        "",
        "| persona_id | count | share |",
        "| --- | ---: | ---: |",
    ]
    lines.extend(_format_count_table(persona["top_personas"], persona_total))

    lines.extend(
        [
            "",
            "### Layer distribution",
            "",
            "| matched_layer | count | share |",
            "| --- | ---: | ---: |",
        ]
    )
    lines.extend(_format_count_table(layer_rows, persona_total))

    lines.extend(
        [
            "",
            "### Confidence",
            "",
            f"- avg: {_fmt(avg)} / p50: {_fmt(p50)} / p95: {_fmt(p95)} / max: {_fmt(cmax)}",
            "",
            "### G2 detected events",
            "",
        ]
    )
    if persona["g2_detected_events"]:
        lines.append("| ts | persona_id | framework | query_hash |")
        lines.append("| --- | --- | --- | --- |")
        for ev in persona["g2_detected_events"]:
            qhash = (ev.get("query_hash") or "")[:12]
            lines.append(
                f"| `{ev.get('ts','?')}` | `{ev.get('persona_id','?')}` "
                f"| `{ev.get('framework','-')}` | `{qhash}` |"
            )
    else:
        lines.append("- (none in window)")

    lines.extend(
        [
            "",
            "### Framework distribution",
            "",
            "| framework | count | share |",
            "| --- | ---: | ---: |",
        ]
    )
    lines.extend(_format_count_table(framework_rows, persona_total))

    lines.extend(
        [
            "",
            "## 2. Agent tool usage",
            "",
            f"- total agent tool events: **{agent_total}**",
            f"- general-purpose share: **{agent['general_purpose_rate']*100:.1f}%** "
            f"({agent['general_purpose_count']} / {agent_total})",
            f"- persona-named subagent share: **{agent['persona_named_rate']*100:.1f}%** "
            f"({agent['persona_named_count']} / {agent_total})",
            f"- agent_file missing warnings: {agent['agent_file_missing_count']}",
            "",
            "### subagent_type distribution",
            "",
            "| subagent_type | count | share |",
            "| --- | ---: | ---: |",
        ]
    )
    lines.extend(_format_count_table(subagent_rows, agent_total))

    if agent["warnings"]:
        lines.extend(
            [
                "",
                "### Warnings (agent_file missing or unknown)",
                "",
                "| ts | subagent_type | tool | reason |",
                "| --- | --- | --- | --- |",
            ]
        )
        for warn in agent["warnings"][:25]:
            lines.append(
                f"| `{warn.get('ts','?')}` | `{warn.get('subagent_type','?')}` "
                f"| `{warn.get('tool','?')}` | {warn.get('reason','?')} |"
            )

    lines.extend(
        [
            "",
            "## 3. Honest data note",
            "",
            f"- persona events scanned: {persona_total}",
            f"- agent events scanned: {agent_total}",
            f"- {report['data_quality']['honest_note']}",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_since(args: argparse.Namespace) -> datetime | None:
    now = datetime.now(KST)
    if args.since:
        try:
            parsed = datetime.fromisoformat(args.since)
        except ValueError:
            sys.stderr.write(f"--since '{args.since}' is not ISO-8601; ignoring\n")
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=KST)
        return parsed
    if args.days is not None and args.days > 0:
        return now - timedelta(days=args.days)
    return None


def _write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate Claude Code routing/agent audit logs."
    )
    parser.add_argument(
        "--audit-dir",
        default=None,
        help="Override audit directory (default: ~/.claude/audit).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Restrict to events within the last N days (KST).",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO-8601 lower bound (e.g. 2026-05-08 or 2026-05-08T09:00).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Write Markdown report to this path.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Emit the JSON report to stdout (default when no output is given).",
    )
    args = parser.parse_args(argv)

    audit_dir = _resolve_audit_dir(args.audit_dir)
    if not audit_dir.exists():
        sys.stderr.write(
            f"audit dir not found: {audit_dir}\n"
            "expected ~/.claude/audit (Claude Code hooks must be wired). "
            "If hooks were installed in a different location, pass --audit-dir.\n"
        )
        return 2

    since = _resolve_since(args)
    persona_events, persona_files = collect_persona_events(audit_dir, since)
    agent_events, agent_files = collect_agent_events(audit_dir, since)

    report = build_report(
        audit_dir=audit_dir,
        since=since,
        persona_events=persona_events,
        persona_files=persona_files,
        agent_events=agent_events,
        agent_files=agent_files,
    )

    json_blob = json.dumps(report, ensure_ascii=False, indent=2)
    md_blob = _markdown_report(report)

    if args.output:
        _write_output(Path(args.output).resolve(), json_blob + "\n")
    if args.markdown:
        _write_output(Path(args.markdown).resolve(), md_blob + "\n")

    if args.print_json or (not args.output and not args.markdown):
        sys.stdout.write(json_blob + "\n")

    if persona_events == [] and agent_events == []:
        sys.stderr.write(
            "[note] no events in window - hook integration may be recent or "
            "the time window is too narrow.\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
