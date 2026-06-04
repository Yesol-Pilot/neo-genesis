"""Neo Genesis -- daily attention digest engine.

Ontology state → "오늘 owner 가 봐야 할 것" 자동 생성.

Per "AI-native company operating on ontology" 본질:
- 그래프 state 를 매일 분석
- 시간 의존 / 임계값 / 리스크 / 기여 변화 surface
- owner 의 다음 한 줄 결정 후보 박제

Logic categories:
1. URGENT — D-7 이내 deadline / blocker (W0 launch / NeurIPS submit / capital review)
2. RISK — P0 risk active state (blind-review-hold / W0-readiness / personal-leak)
3. BURN — monthly cost trajectory vs. runway
4. CAPABILITY GAP — Tier S 가동 필요한데 미할당 / fallback
5. AGENT CONTRIBUTION — 본 주 agent contribution skew (특정 agent 집중도 too high/low)
6. PRODUCT STAGE — 'idea' / 'paused' Product 의 next action
7. DECISION VELOCITY — G1 박제 빈도 (자율 판단 활성도)

Usage:
    python scripts/ontology/business/daily_digest.py [--json] [--save-as-decision]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
META_DIR = REPO_ROOT / ".agent" / "ontology"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_date(d: str | None) -> dt.date | None:
    if not d:
        return None
    try:
        return dt.datetime.strptime(d[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def days_until(target: dt.date) -> int:
    return (target - dt.date.today()).days


def section_urgent(biz_nodes: list[dict]) -> list[dict]:
    """D-7 이내 deadline events."""
    items = []
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:TemporalEvent":
            continue
        if n.get("status") not in ("scheduled", "tentative", "active"):
            continue
        target = parse_date(n.get("target_date"))
        if not target:
            continue
        days = days_until(target)
        if days <= 30:  # D-30 이내 surface
            items.append({
                "label": n.get("label"),
                "kind": n.get("kind"),
                "target_date": n.get("target_date"),
                "days_until": days,
                "impact": n.get("impact_note"),
            })
    items.sort(key=lambda x: x["days_until"])
    return items


def section_risk(biz_nodes: list[dict]) -> list[dict]:
    """P0/P1 active risks."""
    items = []
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:Risk":
            continue
        if n.get("status") not in ("active", "monitoring"):
            continue
        if n.get("severity") not in ("P0", "P1"):
            continue
        items.append({
            "label": n.get("label"),
            "severity": n.get("severity"),
            "kind": n.get("kind"),
            "status": n.get("status"),
            "description": n.get("description"),
        })
    items.sort(key=lambda x: (x["severity"], x["label"]))
    return items


def section_burn(biz_nodes: list[dict]) -> dict[str, Any]:
    """Monthly burn rate + runway — provenance + caveat 명시."""
    agg = next((n for n in biz_nodes
                if n.get("rdf_type") == "biz:MonthlyCost"
                and n.get("category") == "_aggregate"), None)
    if not agg:
        return {"status": "no_aggregate_cost_found"}
    monthly = agg.get("monthly_usd_estimate", 0)
    provenance = agg.get("provenance", "unknown")
    is_estimate = provenance != "observed_from_live_source"
    cons_runway_months = round(7500 / monthly, 1) if monthly else None
    opt_runway_months = round(60000 / monthly, 1) if monthly else None
    return {
        "monthly_burn_usd": monthly,
        "is_estimate": is_estimate,
        "provenance": provenance,
        "monthly_burn_usd_per_year": monthly * 12,
        "runway_months_conservative_1000man": cons_runway_months,
        "runway_months_optimistic_8000man": opt_runway_months,
        "caveat": ("⚠️ 본 burn 은 추정. 실 invoice 0. 의사결정 시 owner 가 신용카드 / 구독 영수증 fact-check 필수."
                   if is_estimate else "observed from live invoices"),
    }


def section_capability_gap(biz_nodes: list[dict]) -> list[dict]:
    """W0 D-27 에 필요한 Tier S capability 식별."""
    # Hard-coded: W0 launch 가동 필요 domain (AI-native operating requirement)
    w0_required_domains = {"research", "orchestration", "data_pm", "sre"}
    available = []
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:Capability":
            continue
        if n.get("tier") != "S":
            continue
        if n.get("domain") in w0_required_domains:
            available.append({
                "label": n.get("label"),
                "domain": n.get("domain"),
                "evidence": n.get("evidence_note", "")[:80],
            })
    covered_domains = {a["domain"] for a in available}
    missing = w0_required_domains - covered_domains
    return {
        "w0_required_domains": sorted(w0_required_domains),
        "covered_by_tier_s": available,
        "missing_domains": sorted(missing),
    }


def section_product_attention(biz_nodes: list[dict]) -> list[dict]:
    """'idea' / 'paused' Product — next action 후보."""
    items = []
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:Product":
            continue
        if n.get("stage") in ("idea", "paused"):
            items.append({
                "slug": n.get("slug"),
                "stage": n.get("stage"),
                "kind": n.get("kind"),
                "label": n.get("label"),
                "suggested_action": (
                    "W0 launch (D-27) — 자율 가동 plan 검증" if n.get("slug") == "koreanllm"
                    else "stage transition 결정 — owner G2"
                ),
            })
    return items


def section_decision_velocity(biz_nodes: list[dict]) -> dict[str, Any]:
    """G1 박제 빈도 — 누적 + last 7-day 두 view 분리.

    Cold honest 정정: 직전 ratio 6.67 은 본 세션 박제 누적이지, 실 historical
    velocity 가 아님. 시간 window 분리로 self-attestation 회피.
    """
    today = dt.date.today()
    week_ago = today - dt.timedelta(days=7)
    week_ago_iso = week_ago.isoformat()

    def in_window(n: dict) -> bool:
        d = n.get("decided_at", "1900-01-01")
        return d >= week_ago_iso

    decisions = [n for n in biz_nodes if n.get("rdf_type") == "biz:Decision"]
    g1_total = sum(1 for n in decisions if n.get("g_level") == "G1")
    g2_total = sum(1 for n in decisions if n.get("g_level") == "G2")
    g1_7d = sum(1 for n in decisions if n.get("g_level") == "G1" and in_window(n))
    g2_7d = sum(1 for n in decisions if n.get("g_level") == "G2" and in_window(n))

    return {
        "all_time": {
            "g1": g1_total,
            "g2": g2_total,
            "ratio": round(g1_total / max(g2_total, 1), 2),
        },
        "last_7_days": {
            "g1": g1_7d,
            "g2": g2_7d,
            "ratio": round(g1_7d / max(g2_7d, 1), 2),
        },
        "caveat": "all_time = ontology 자체 박제 (session-local). last_7_days = 시점 의존. real velocity 측정은 ActionRun audit log (kind:ontology_mutation, decision-related) 기반 별도 분석 필요.",
    }


def section_decision_outcomes(biz_nodes: list[dict]) -> dict[str, Any]:
    """Decision outcome tracker 결과 surfacing.

    AI-native learning loop: 박제만 하지 말고 outcome 검증 + 결과 노출.
    """
    decisions = [n for n in biz_nodes if n.get("rdf_type") == "biz:Decision"]
    if not decisions:
        return {"status": "no_decisions"}

    by_status = {"validated": [], "failed": [], "unmeasurable": [], "pending": []}
    for d in decisions:
        st = d.get("outcome_status", "pending")
        if st not in by_status:
            by_status[st] = []
        by_status[st].append({
            "g_id": d.get("g_id"),
            "label": d.get("label", "")[:60],
            "evidence": d.get("outcome_evidence", "")[:120],
            "checks": f"{d.get('outcome_checks_pass', '?')}/{d.get('outcome_checks_total', '?')}",
        })

    total = len(decisions)
    validated = len(by_status["validated"])
    failed = len(by_status["failed"])
    unmeasurable = len(by_status["unmeasurable"])
    coverage = round((validated + failed) / total * 100, 1) if total else 0
    success_rate = round(validated / max(validated + failed, 1) * 100, 1)

    return {
        "total": total,
        "validated": validated,
        "failed": failed,
        "unmeasurable": unmeasurable,
        "coverage_pct": coverage,
        "success_rate_pct": success_rate,
        "failed_decisions": by_status["failed"][:5],
        "unmeasurable_decisions": by_status["unmeasurable"][:5],
        "validated_sample": by_status["validated"][:3],
    }


def section_workflows_ready(biz_nodes: list[dict]) -> list[dict]:
    """Executable Workflow nodes whose precondition match — actuation candidates."""
    import datetime as _dt
    today = _dt.date.today()
    context = {
        "blog_published_this_month": 0,
        "last_review_age_days": 7,
    }
    safe_globals = {"__builtins__": {}}
    safe_locals = {"today": today, "now": _dt.datetime.now(), **context}

    ready = []
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:Workflow":
            continue
        cmd = n.get("executable_command")
        if not cmd:
            continue
        precond = n.get("precondition")
        triggered = True
        if precond:
            try:
                triggered = bool(eval(precond, safe_globals, safe_locals))
            except Exception:
                triggered = False
        if triggered:
            ready.append({
                "workflow": n.get("label"),
                "id": n["id"],
                "kind": n.get("kind"),
                "command": cmd,
                "precondition": precond or "(always)",
                "note": n.get("note", "")[:80],
            })
    return ready


def section_agent_load_balance(biz_nodes: list[dict]) -> dict[str, Any]:
    """Agent × Product contribution — observed 우선."""
    by_agent_observed: dict[str, int] = {}
    by_agent_hardcoded: dict[str, int] = {}
    for n in biz_nodes:
        if n.get("rdf_type") != "biz:AgentContribution":
            continue
        a = n.get("agent")
        if not a:
            continue
        agent_slug = a.split("/")[-1]
        if n.get("provenance") == "observed_from_live_source":
            count = n.get("audit_action_count", 1)
            by_agent_observed[agent_slug] = by_agent_observed.get(agent_slug, 0) + count
        else:
            by_agent_hardcoded[agent_slug] = by_agent_hardcoded.get(agent_slug, 0) + 1

    has_observed = bool(by_agent_observed)
    primary = by_agent_observed if has_observed else by_agent_hardcoded
    total = sum(primary.values()) or 1
    return {
        "source": "observed_from_live_source" if has_observed else "hardcoded_estimate",
        "contributions_by_agent": {
            a: round(c / total * 100, 1)
            for a, c in sorted(primary.items(), key=lambda x: -x[1])
        },
        "observed_action_count": sum(by_agent_observed.values()),
        "hardcoded_count": sum(by_agent_hardcoded.values()),
        "interpretation": (
            "ActionRun audit log 기반 실 측정 (cron 누적 시 더 정확)" if has_observed
            else "hardcoded estimate (audit log fallback)"
        ),
    }


def section_outcome_stability(biz_nodes: list[dict]) -> dict[str, Any]:
    """Outcome timeline — status change 추적."""
    snapshots = [n for n in biz_nodes if n.get("rdf_type") == "biz:OutcomeSnapshot"]
    if not snapshots:
        return {"status": "no_snapshots_yet"}
    by_decision: dict[str, list[dict]] = {}
    for s in snapshots:
        g = s.get("g_id")
        if not g:
            continue
        by_decision.setdefault(g, []).append(s)

    stable_count = 0
    unstable_count = 0
    recent_changes = []
    for g, snaps in by_decision.items():
        snaps.sort(key=lambda s: s.get("snapshot_date", ""))
        statuses = [s.get("status") for s in snaps]
        if len(set(statuses)) <= 1:
            stable_count += 1
        else:
            unstable_count += 1
            recent_changes.append({
                "g_id": g,
                "statuses_history": statuses[-3:],
                "snapshot_count": len(snaps),
            })

    return {
        "total_decisions_tracked": len(by_decision),
        "stable": stable_count,
        "unstable": unstable_count,
        "total_snapshots": len(snapshots),
        "recent_status_changes": recent_changes[:5],
    }


def generate_digest(json_output: bool = False) -> dict[str, Any]:
    biz_nodes = load_jsonl(BIZ_DIR / "nodes.jsonl")
    meta_nodes = load_jsonl(META_DIR / "nodes.jsonl")

    digest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "ontology_state": {
            "meta_nodes": len(meta_nodes),
            "biz_nodes": len(biz_nodes),
            "biz_classes": len({n.get("rdf_type") for n in biz_nodes}),
        },
        "urgent_d30": section_urgent(biz_nodes),
        "active_risks": section_risk(biz_nodes),
        "burn_runway": section_burn(biz_nodes),
        "w0_capability_gap": section_capability_gap(biz_nodes),
        "product_attention": section_product_attention(biz_nodes),
        "decision_velocity": section_decision_velocity(biz_nodes),
        "decision_outcomes": section_decision_outcomes(biz_nodes),
        "outcome_stability": section_outcome_stability(biz_nodes),
        "agent_load_balance": section_agent_load_balance(biz_nodes),
        "workflows_ready": section_workflows_ready(biz_nodes),
    }
    return digest


def format_human(digest: dict[str, Any]) -> str:
    """한국어 owner-friendly 형식."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"Neo Genesis Daily Digest — {digest['generated_at'][:10]}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"📊 Ontology state: meta={digest['ontology_state']['meta_nodes']} / biz={digest['ontology_state']['biz_nodes']} ({digest['ontology_state']['biz_classes']} classes)")
    lines.append("")

    # URGENT
    lines.append("🔴 URGENT (D-30 이내 deadline)")
    if digest["urgent_d30"]:
        for u in digest["urgent_d30"]:
            d = u["days_until"]
            tag = "🚨" if d <= 7 else "⏳"
            lines.append(f"  {tag} D-{d} ({u['target_date']}) [{u['kind']}] {u['label']}")
            lines.append(f"     → {u['impact']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # RISK
    lines.append("⚠️  ACTIVE RISKS (P0/P1)")
    for r in digest["active_risks"][:5]:
        lines.append(f"  [{r['severity']}] {r['label']} ({r['kind']}) — {r['status']}")
        lines.append(f"     → {r['description'][:100]}")
    lines.append("")

    # BURN
    br = digest["burn_runway"]
    if br.get("monthly_burn_usd"):
        tag = " (추정)" if br.get("is_estimate") else " (관측)"
        lines.append(f"💸 BURN RATE{tag}")
        lines.append(f"  월 ${br['monthly_burn_usd']} / 연 ${br['monthly_burn_usd_per_year']}")
        lines.append(f"  Runway: 1000만 자본 = {br['runway_months_conservative_1000man']}개월 / 8000만 자본 = {br['runway_months_optimistic_8000man']}개월")
        if br.get("is_estimate"):
            lines.append(f"  {br.get('caveat','')}")
        lines.append("")

    # W0 CAPABILITY GAP
    cg = digest["w0_capability_gap"]
    lines.append("🎯 W0 LAUNCH CAPABILITY (Tier S 매칭)")
    lines.append(f"  필요 도메인: {cg['w0_required_domains']}")
    lines.append(f"  Tier S 커버: {len(cg['covered_by_tier_s'])}건")
    if cg["missing_domains"]:
        lines.append(f"  🚨 MISSING: {cg['missing_domains']}")
    else:
        lines.append("  ✅ 모든 도메인 커버됨")
    lines.append("")

    # PRODUCT ATTENTION
    lines.append("📦 PRODUCT — stage transition 후보")
    for p in digest["product_attention"]:
        lines.append(f"  [{p['stage']}] {p['slug']} → {p['suggested_action']}")
    lines.append("")

    # DECISION VELOCITY
    dv = digest["decision_velocity"]
    lines.append("🧠 DECISION VELOCITY")
    lines.append(f"  all-time: G1={dv['all_time']['g1']} / G2={dv['all_time']['g2']} (ratio {dv['all_time']['ratio']})")
    lines.append(f"  last 7d:  G1={dv['last_7_days']['g1']} / G2={dv['last_7_days']['g2']} (ratio {dv['last_7_days']['ratio']})")
    lines.append(f"  caveat: {dv['caveat'][:120]}")
    lines.append("")

    # DECISION OUTCOMES (learning loop)
    out = digest.get("decision_outcomes", {})
    if out.get("total"):
        lines.append("🎯 DECISION OUTCOMES (learning loop)")
        lines.append(f"  total: {out['total']} | validated: {out['validated']} | failed: {out['failed']} | unmeasurable: {out['unmeasurable']}")
        lines.append(f"  coverage: {out['coverage_pct']}% | success rate: {out['success_rate_pct']}%")
        if out.get("failed_decisions"):
            lines.append("  ⚠️ FAILED decisions:")
            for d in out["failed_decisions"]:
                lines.append(f"    - {d['g_id']}: {d['label']} ({d['checks']}) → {d['evidence']}")
        if out.get("unmeasurable") > 0:
            lines.append(f"  ℹ️ {out['unmeasurable']}건 outcome rule 미박제 — 측정 rule 작성 필요")
        lines.append("")

    # OUTCOME STABILITY (timeline)
    os = digest.get("outcome_stability", {})
    if os.get("total_decisions_tracked"):
        lines.append("📈 OUTCOME STABILITY (timeline)")
        lines.append(f"  tracked: {os['total_decisions_tracked']} | stable: {os['stable']} | unstable: {os['unstable']} | snapshots: {os['total_snapshots']}")
        if os.get("recent_status_changes"):
            lines.append("  recent status changes:")
            for c in os["recent_status_changes"]:
                lines.append(f"    - {c['g_id']}: {' → '.join(c['statuses_history'])}")
        lines.append("")

    # AGENT LOAD
    al = digest["agent_load_balance"]
    src_tag = "🔴 observed" if al.get("source") == "observed_from_live_source" else "🟡 hardcoded"
    lines.append(f"🤖 AGENT LOAD BALANCE ({src_tag})")
    for a, pct in list(al["contributions_by_agent"].items())[:5]:
        lines.append(f"  {a:35s} {pct}%")
    if al.get("observed_action_count"):
        lines.append(f"  → audit_action_count total: {al['observed_action_count']}")
    lines.append("")

    # WORKFLOWS READY
    wfr = digest.get("workflows_ready", [])
    lines.append(f"⚙️  WORKFLOWS READY ({len(wfr)} executable)")
    for w in wfr[:8]:
        lines.append(f"  • {w['workflow']:30s} → {w['command'][:60]}")
        if w.get("precondition") and w["precondition"] != "(always)":
            lines.append(f"    cond: {w['precondition']}")
    lines.append("")
    lines.append("  실행: python scripts/ontology/business/workflow_runner.py --run <id>")
    lines.append("       또는 --run-all-ready (precondition match 만)")
    lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def save_digest_as_decision_action(digest: dict[str, Any]) -> None:
    """매일 digest 를 ActionRun 으로 ontology 자체에 박제."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "ontology"))
        from auto_record import record_action  # type: ignore
        record_action(
            kind="heartbeat",
            agent_id="neo://agent/ontology-daily-digest",
            affected=[],
            meta={
                "digest_summary": {
                    "urgent_count": len(digest["urgent_d30"]),
                    "active_risks_count": len(digest["active_risks"]),
                    "monthly_burn_usd": digest["burn_runway"].get("monthly_burn_usd"),
                    "w0_missing_domains": digest["w0_capability_gap"]["missing_domains"],
                },
            },
            label=f"daily_digest {digest['generated_at'][:10]}",
        )
    except Exception as e:
        print(f"[WARN] save digest as ActionRun failed: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save-as-decision", action="store_true",
                        help="Also record ActionRun for audit trail")
    args = parser.parse_args()

    digest = generate_digest()
    if args.json:
        print(json.dumps(digest, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_human(digest))

    # Persist
    digest_path = BIZ_DIR / "daily_digest_last.json"
    digest_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n[saved] {digest_path}", file=sys.stderr)

    if args.save_as_decision:
        save_digest_as_decision_action(digest)

    return 0


if __name__ == "__main__":
    sys.exit(main())
