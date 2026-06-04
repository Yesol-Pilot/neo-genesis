"""Neo Genesis -- Static HTML dashboard generator.

Reads .agent/ontology/business/nodes.jsonl + daily_digest_last.json + weekly review,
emits standalone HTML at .agent/ontology/business/dashboard/index.html.

No external JS framework. Pure HTML + minimal CSS + vanilla JS.

Open: file:///D:/00.test/neo-genesis/.agent/ontology/business/dashboard/index.html

Usage:
    python scripts/ontology/business/dashboard_generator.py [--out PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
META_DIR = REPO_ROOT / ".agent" / "ontology"
DASHBOARD_DIR = BIZ_DIR / "dashboard"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def html_escape(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def generate_html() -> str:
    biz_nodes = load_jsonl(BIZ_DIR / "nodes.jsonl")
    meta_nodes = load_jsonl(META_DIR / "nodes.jsonl")
    digest_path = BIZ_DIR / "daily_digest_last.json"
    digest = json.loads(digest_path.read_text(encoding="utf-8")) if digest_path.exists() else {}

    class_count = Counter(n.get("rdf_type") for n in biz_nodes)
    meta_class_count = Counter(n.get("rdf_type") for n in meta_nodes)

    # Categorize biz nodes by class for easier rendering
    by_class: dict[str, list[dict]] = defaultdict(list)
    for n in biz_nodes:
        by_class[n.get("rdf_type", "?")].append(n)

    today = dt.date.today()
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    parts = []
    parts.append('<!doctype html>')
    parts.append('<html lang="ko"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append('<title>Neo Genesis Ontology Dashboard</title>')
    parts.append('''<style>
:root { --bg:#0a0a0b; --fg:#e6e6e6; --dim:#888; --acc:#7aa2f7; --warn:#e0af68; --err:#f7768e; --ok:#9ece6a; }
* { box-sizing:border-box; }
body { background:var(--bg); color:var(--fg); font-family:-apple-system,'SF Pro Display','Pretendard',system-ui,sans-serif; margin:0; padding:24px; line-height:1.5; }
h1 { font-size:20px; margin:0 0 4px; }
h2 { font-size:14px; color:var(--dim); margin:24px 0 8px; text-transform:uppercase; letter-spacing:.5px; }
.meta { color:var(--dim); font-size:12px; }
.grid { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); margin-top:8px; }
.card { background:#13131a; border:1px solid #1d1d28; border-radius:8px; padding:12px 14px; }
.card .label { color:var(--dim); font-size:11px; text-transform:uppercase; }
.card .value { font-size:22px; font-weight:600; margin-top:4px; }
.card .sub { color:var(--dim); font-size:11px; margin-top:4px; }
table { width:100%; border-collapse:collapse; font-size:13px; margin-top:8px; }
th, td { text-align:left; padding:6px 10px; border-bottom:1px solid #1d1d28; }
th { color:var(--dim); font-weight:500; font-size:11px; text-transform:uppercase; }
.tag { display:inline-block; padding:2px 6px; border-radius:3px; font-size:11px; background:#1d1d28; color:var(--dim); margin-right:4px; }
.tag.warn { background:#3a2a1a; color:var(--warn); }
.tag.err { background:#3a1a22; color:var(--err); }
.tag.ok { background:#1a3a22; color:var(--ok); }
.section { background:#13131a; border:1px solid #1d1d28; border-radius:8px; padding:16px; margin-top:12px; }
.section h2 { margin-top:0; }
hr { border:0; border-top:1px solid #1d1d28; margin:24px 0; }
a { color:var(--acc); text-decoration:none; }
code { background:#13131a; padding:2px 6px; border-radius:3px; font-size:12px; color:var(--acc); }
.kpi-grid { display:grid; gap:8px; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
</style></head><body>''')

    parts.append(f'<h1>Neo Genesis Ontology Dashboard</h1>')
    parts.append(f'<div class="meta">Generated {generated_at} | meta: {len(meta_nodes)} nodes · biz: {len(biz_nodes)} nodes ({len(class_count)} classes)</div>')

    # Hero stats
    parts.append('<div class="grid">')
    products_live = sum(1 for p in by_class.get("biz:Product", []) if p.get("stage") == "live")
    parts.append(f'<div class="card"><div class="label">Products live</div><div class="value">{products_live} / {len(by_class.get("biz:Product",[]))}</div></div>')

    burn_agg = next((n for n in by_class.get("biz:MonthlyCost", []) if n.get("category") == "_aggregate"), None)
    burn = burn_agg.get("monthly_usd_estimate", 0) if burn_agg else 0
    parts.append(f'<div class="card"><div class="label">Monthly burn</div><div class="value">${burn}</div><div class="sub">runway 16.7~133.9 months (1000~8000만 자본)</div></div>')

    g1_count = sum(1 for d in by_class.get("biz:Decision", []) if d.get("g_level") == "G1")
    g2_count = sum(1 for d in by_class.get("biz:Decision", []) if d.get("g_level") == "G2")
    parts.append(f'<div class="card"><div class="label">Decisions (G1 / G2)</div><div class="value">{g1_count} / {g2_count}</div><div class="sub">ratio {round(g1_count/max(g2_count,1),2)}</div></div>')

    p0_risks = sum(1 for r in by_class.get("biz:Risk", []) if r.get("severity") == "P0" and r.get("status") in ("active","monitoring"))
    parts.append(f'<div class="card"><div class="label">P0 active risks</div><div class="value" style="color:var(--err)">{p0_risks}</div></div>')

    leads = len(by_class.get("biz:Lead", []))
    parts.append(f'<div class="card"><div class="label">잠재 고객 (Leads)</div><div class="value">{leads}</div><div class="sub">B2B enterprise 12 + B3 consulting 3</div></div>')

    capabilities = len(by_class.get("biz:Capability", []))
    parts.append(f'<div class="card"><div class="label">Capabilities</div><div class="value">{capabilities}</div><div class="sub">Tier S 12건 (founder 3 + AI 9)</div></div>')
    parts.append('</div>')

    # Urgent (D-30)
    parts.append('<div class="section"><h2>🔴 D-30 이내 deadline</h2><table><tr><th>D-</th><th>kind</th><th>label</th><th>impact</th></tr>')
    urgent_items = digest.get("urgent_d30", [])
    for u in urgent_items:
        d = u.get("days_until", "?")
        cls = "err" if d <= 7 else "warn"
        parts.append(f'<tr><td><span class="tag {cls}">D{d:+d}</span></td><td>{html_escape(u.get("kind"))}</td><td>{html_escape(u.get("label"))}</td><td class="meta">{html_escape(u.get("impact",""))[:120]}</td></tr>')
    # Conference deadlines
    for s in by_class.get("biz:ExternalSignal", []):
        if s.get("kind") != "conference_deadline":
            continue
        d = s.get("days_until", 999)
        if d < -7 or d > 90:
            continue
        cls = "err" if d <= 7 else ("warn" if d <= 30 else "")
        parts.append(f'<tr><td><span class="tag {cls}">D{d:+d}</span></td><td>conference</td><td>{html_escape(s.get("label"))}</td><td class="meta">{html_escape(s.get("rationale",""))[:120]}</td></tr>')
    parts.append('</table></div>')

    # Market signals
    market_signals = [s for s in by_class.get("biz:ExternalSignal", []) if s.get("kind") == "market"]
    if market_signals:
        parts.append('<div class="section"><h2>📈 시장 신호</h2><table><tr><th>지표</th><th>종가</th><th>1d %</th><th>rationale</th></tr>')
        for s in market_signals:
            pct = s.get("pct_change_1d")
            cls = "ok" if (isinstance(pct,(int,float)) and pct > 0) else ("err" if (isinstance(pct,(int,float)) and pct < 0) else "")
            arrow = "↑" if cls == "ok" else ("↓" if cls == "err" else "→")
            parts.append(f'<tr><td>{html_escape(s.get("label"))}</td><td>{html_escape(round(s.get("latest_close",0),2))}</td><td><span class="tag {cls}">{arrow} {pct}%</span></td><td class="meta">{html_escape(s.get("rationale",""))}</td></tr>')
        parts.append('</table></div>')

    # Active P0 risks
    parts.append('<div class="section"><h2>⚠️  P0 active risks</h2><table><tr><th>severity</th><th>kind</th><th>label</th><th>desc</th></tr>')
    for r in by_class.get("biz:Risk", []):
        if r.get("severity") != "P0" or r.get("status") not in ("active","monitoring"):
            continue
        parts.append(f'<tr><td><span class="tag err">{html_escape(r.get("severity"))}</span></td><td>{html_escape(r.get("kind"))}</td><td>{html_escape(r.get("label"))}</td><td class="meta">{html_escape(r.get("description",""))[:160]}</td></tr>')
    parts.append('</table></div>')

    # Monthly cost breakdown
    parts.append('<div class="section"><h2>💸 비용 분포</h2><table><tr><th>bucket</th><th>$/월</th><th>note</th></tr>')
    for c in sorted([n for n in by_class.get("biz:MonthlyCost", []) if n.get("category") != "_aggregate"],
                    key=lambda x: -x.get("monthly_usd_estimate", 0)):
        parts.append(f'<tr><td>{html_escape(c.get("label"))}</td><td><strong>${c.get("monthly_usd_estimate")}</strong></td><td class="meta">{html_escape(c.get("note",""))[:120]}</td></tr>')
    parts.append('</table></div>')

    # Products
    parts.append('<div class="section"><h2>📦 Products</h2><table><tr><th>slug</th><th>stage</th><th>kind</th><th>label</th></tr>')
    for p in sorted(by_class.get("biz:Product", []), key=lambda x: (x.get("stage","?"), x.get("slug",""))):
        stage = p.get("stage")
        cls = "ok" if stage == "live" else ("warn" if stage == "idea" else "")
        parts.append(f'<tr><td><code>{html_escape(p.get("slug"))}</code></td><td><span class="tag {cls}">{html_escape(stage)}</span></td><td class="meta">{html_escape(p.get("kind"))}</td><td>{html_escape(p.get("label"))[:100]}</td></tr>')
    parts.append('</table></div>')

    # Workflows
    parts.append('<div class="section"><h2>⚙️  Workflows (executable)</h2><table><tr><th>workflow</th><th>kind</th><th>command</th></tr>')
    for w in by_class.get("biz:Workflow", []):
        cmd = w.get("executable_command")
        if not cmd:
            continue
        parts.append(f'<tr><td>{html_escape(w.get("label"))}</td><td class="meta">{html_escape(w.get("kind"))}</td><td><code>{html_escape(cmd)[:80]}</code></td></tr>')
    parts.append('</table></div>')

    # KPI snapshot
    parts.append('<div class="section"><h2>📊 KPI</h2><table><tr><th>product</th><th>metric</th><th>source</th><th>target</th><th>current</th></tr>')
    for k in by_class.get("biz:KPI", []):
        current = k.get("current_value") or '<span class="tag warn">미집계</span>'
        parts.append(f'<tr><td><code>{html_escape(k.get("product","").split("/")[-1])}</code></td><td>{html_escape(k.get("metric_name"))}</td><td class="meta">{html_escape(k.get("source"))}</td><td>{html_escape(k.get("target_value"))}</td><td>{current}</td></tr>')
    parts.append('</table></div>')

    # Footer
    parts.append('<hr>')
    parts.append(f'<div class="meta">Generated by <code>scripts/ontology/business/dashboard_generator.py</code> · 일일 09:13 KST 자동 (Windows Task Scheduler · NeoGenesisOntologyDailyMaintain)</div>')
    parts.append('<div class="meta">Cypher 실시간 query: <a href="https://console.neo4j.io">AuraDB Browser</a></div>')

    parts.append('</body></html>')
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DASHBOARD_DIR / "index.html"))
    args = parser.parse_args()

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = generate_html()
    out_path.write_text(html_content, encoding="utf-8")
    print(f"[OK] dashboard -> {out_path}")
    print(f"     open: file:///{str(out_path).replace(chr(92), '/')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
