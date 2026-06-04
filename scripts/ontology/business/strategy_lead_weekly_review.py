"""Neo Genesis -- Strategy Lead Weekly Review (Monday 10:05 KST cron).

ontology state 를 종합해서 owner 가 매주 월요일 받는 strategic review 생성.

기존 (handoff/active-tasks) 의 Weekly Progress Review 박제 패턴을 자동화:
- 지난 7일 commits / decisions / actionrun 누적
- KPI snapshot (current vs target)
- Burn rate + runway 변화
- W0 / NeurIPS 등 deadline 시점 압박도
- Stop/Go gate 판정
- 다음 주 우선순위 권고

산출: .agent/shared-brain/weekly-review/<YYYY-MM-DD>.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
META_DIR = REPO_ROOT / ".agent" / "ontology"
OUT_DIR = REPO_ROOT / ".agent" / "shared-brain" / "weekly-review"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def section_burn_runway(biz_nodes: list[dict]) -> str:
    agg = next((n for n in biz_nodes
                if n.get("rdf_type") == "biz:MonthlyCost"
                and n.get("category") == "_aggregate"), None)
    monthly = agg.get("monthly_usd_estimate", 0) if agg else 0
    buckets = [n for n in biz_nodes
               if n.get("rdf_type") == "biz:MonthlyCost"
               and n.get("category") != "_aggregate"]
    lines = [
        "### 💸 Burn rate & Runway",
        "",
        f"- **월 baseline**: ${monthly} / 연 ${monthly*12}",
        f"- **Runway** (1000만~8000만 자본): {round(7500/monthly,1) if monthly else 'N/A'}~{round(60000/monthly,1) if monthly else 'N/A'}개월",
        "",
        "**비용 분포**:",
    ]
    for b in sorted(buckets, key=lambda x: -x.get("monthly_usd_estimate", 0))[:5]:
        lines.append(f"- {b.get('label')}: ${b.get('monthly_usd_estimate')}/월")
    lines.append("")
    return "\n".join(lines)


def section_deadlines(biz_nodes: list[dict]) -> str:
    today = dt.date.today()
    items = []

    for n in biz_nodes:
        if n.get("rdf_type") == "biz:TemporalEvent" and n.get("target_date"):
            try:
                d = dt.date.fromisoformat(n["target_date"])
                days = (d - today).days
                if -7 <= days <= 90:
                    items.append((days, n.get("kind"), n.get("label"), n.get("impact_note", "")[:80]))
            except Exception:
                pass

    for n in biz_nodes:
        if n.get("rdf_type") == "biz:ExternalSignal" and n.get("kind") == "conference_deadline":
            try:
                d = dt.date.fromisoformat(n["deadline_date"])
                days = (d - today).days
                if -7 <= days <= 90:
                    items.append((days, "conference", n.get("label"),
                                  n.get("rationale", "")[:80]))
            except Exception:
                pass

    items.sort()
    lines = ["### 📅 향후 90일 deadlines + 시점 압박", ""]
    if not items:
        lines.append("- (none)")
    for days, kind, label, note in items[:10]:
        tag = "🚨" if days <= 7 else ("⏳" if days <= 30 else "🗓️")
        lines.append(f"- {tag} **D{days:+d}** [{kind}] {label}")
        if note:
            lines.append(f"  → {note}")
    lines.append("")
    return "\n".join(lines)


def section_decisions_week(biz_nodes: list[dict]) -> str:
    """Last 7 days G1/G2 박제 (decided_at 기준)."""
    week_ago = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    decisions = [n for n in biz_nodes
                 if n.get("rdf_type") == "biz:Decision"
                 and n.get("decided_at", "1900-01-01") >= week_ago]
    g1 = [d for d in decisions if d.get("g_level") == "G1"]
    g2 = [d for d in decisions if d.get("g_level") == "G2"]

    lines = [
        "### 🧠 지난 7일 의사결정",
        "",
        f"- G1 자율 박제: **{len(g1)}건**",
        f"- G2 owner 결정: **{len(g2)}건**",
        f"- ratio: {round(len(g1) / max(len(g2),1), 2)}",
        "",
    ]
    if g1:
        lines.append("**최근 G1 자율 결정 (Strategy Lead)**:")
        for d in g1[:10]:
            lines.append(f"- {d.get('g_id', '?')}: {d.get('label','')[:80]}")
        lines.append("")
    return "\n".join(lines)


def section_kpis(biz_nodes: list[dict]) -> str:
    kpis = [n for n in biz_nodes if n.get("rdf_type") == "biz:KPI"]
    lines = ["### 📊 KPI snapshot", ""]
    if not kpis:
        lines.append("- (no KPI nodes)")
    for k in kpis:
        product = k.get("product", "?").split("/")[-1]
        metric = k.get("metric_name")
        target = k.get("target_value")
        current = k.get("current_value", "**미집계** (kpi_fetch.py 가 GA4/GSC creds 추가 시 활성)")
        observed = k.get("current_value_observed_at", "-")[:10]
        lines.append(f"- **{product} / {metric}** — target: {target} | current: {current} (관측 {observed})")
    lines.append("")
    return "\n".join(lines)


def section_market_signals(biz_nodes: list[dict]) -> str:
    signals = [n for n in biz_nodes
               if n.get("rdf_type") == "biz:ExternalSignal"
               and n.get("kind") == "market"]
    lines = ["### 📈 시장 신호 (D2 ETF 결정 지표)", ""]
    if not signals:
        lines.append("- (no market data — external_signal_fetcher 미실행)")
    for s in signals:
        label = s.get("label", "?")
        close = s.get("latest_close", "?")
        pct = s.get("pct_change_1d", "?")
        arrow = "↑" if isinstance(pct, (int, float)) and pct > 0 else ("↓" if isinstance(pct, (int, float)) and pct < 0 else "→")
        lines.append(f"- {label}: {close:.2f} ({arrow} {pct}%) — {s.get('rationale','')}")
    lines.append("")
    return "\n".join(lines)


def section_risk(biz_nodes: list[dict]) -> str:
    risks = [n for n in biz_nodes
             if n.get("rdf_type") == "biz:Risk"
             and n.get("status") in ("active", "monitoring")
             and n.get("severity") == "P0"]
    lines = ["### ⚠️  활성 P0 위험", ""]
    if not risks:
        lines.append("- (none)")
    for r in risks:
        lines.append(f"- **{r.get('label')}** ({r.get('kind')}) — {r.get('status')}")
        lines.append(f"  → {r.get('description', '')[:120]}")
    lines.append("")
    return "\n".join(lines)


def section_stop_go(biz_nodes: list[dict]) -> str:
    """Stop/Go gate 판정 — 다음 주 핵심 결정 후보."""
    today = dt.date.today()
    next_actions = []

    # W0 launch D-27 check
    w0 = next((n for n in biz_nodes
               if n.get("rdf_type") == "biz:TemporalEvent"
               and "koreanllm-w0" in n.get("label", "").lower()), None)
    if w0 and w0.get("target_date"):
        d = (dt.date.fromisoformat(w0["target_date"]) - today).days
        if d <= 30:
            next_actions.append(f"🚨 **koreanllm.org W0 launch D-{d}** — Cloudflare bind + DNS + dashboard ready 확인 필수")

    # NeurIPS deadline check
    nips = next((n for n in biz_nodes
                 if n.get("rdf_type") == "biz:ExternalSignal"
                 and "NeurIPS" in n.get("label", "")), None)
    if nips:
        d = nips.get("days_until", 999)
        if 0 <= d <= 14:
            next_actions.append(f"🚨 **NeurIPS submission D-{d}** — 단, blind review HOLD 박제됐으면 본 venue 가능 여부 owner 결정")

    # G1 velocity
    g1 = sum(1 for n in biz_nodes if n.get("rdf_type") == "biz:Decision" and n.get("g_level") == "G1")
    g2 = sum(1 for n in biz_nodes if n.get("rdf_type") == "biz:Decision" and n.get("g_level") == "G2")
    if g1 / max(g2, 1) < 3:
        next_actions.append(f"📉 **G1 자율 비율 낮음** (G1={g1} / G2={g2}, ratio {round(g1/max(g2,1),2)}) — AI 가 G1 박제 권한 충분히 활용 못 함 가능")

    lines = ["### 🚦 Stop/Go gate (다음 주 핵심)", ""]
    if not next_actions:
        lines.append("- ✅ 임박한 critical action 없음 — daily_maintain 자율 가동만 유지")
    for action in next_actions:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def generate_review() -> str:
    biz_nodes = load_jsonl(BIZ_DIR / "nodes.jsonl")
    meta_nodes = load_jsonl(META_DIR / "nodes.jsonl")

    today = dt.date.today()
    parts = [
        f"# 📅 Weekly Progress Review — {today.isoformat()} (자동 생성)",
        "",
        f"> Strategy Lead automation (ontology-driven). Source: 198+ business nodes / 337+ meta nodes / AuraDB synced.",
        f"> 매주 월요일 10:05 KST cron 자동.",
        "",
        f"## 🔢 Ontology state",
        f"- meta: {len(meta_nodes)} nodes",
        f"- biz: {len(biz_nodes)} nodes ({len({n.get('rdf_type') for n in biz_nodes})} classes)",
        "",
        section_burn_runway(biz_nodes),
        section_deadlines(biz_nodes),
        section_decisions_week(biz_nodes),
        section_kpis(biz_nodes),
        section_market_signals(biz_nodes),
        section_risk(biz_nodes),
        section_stop_go(biz_nodes),
        "---",
        "",
        f"👤 Strategy Lead Claude Opus 4.7 (ontology-driven 자동 생성, {now_iso()})",
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of saving")
    args = parser.parse_args()

    review = generate_review()
    if args.stdout or args.dry_run:
        print(review)
        if args.dry_run:
            return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{dt.date.today().isoformat()}.md"
    out_path.write_text(review, encoding="utf-8")
    print(f"[OK] weekly review -> {out_path}", file=sys.stderr)

    # Self-record as ActionRun
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "ontology"))
        from auto_record import record_action  # type: ignore
        record_action(
            kind="heartbeat",
            agent_id="neo://agent/strategy-lead-weekly-review",
            affected=[],
            meta={"output_path": str(out_path), "review_date": dt.date.today().isoformat()},
            label=f"weekly_review {dt.date.today().isoformat()}",
        )
    except Exception as e:
        print(f"[WARN] ActionRun audit failed: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
