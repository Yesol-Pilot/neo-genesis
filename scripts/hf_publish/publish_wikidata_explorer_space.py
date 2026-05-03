"""
HuggingFace Spaces publish — Wikidata Knowledge Graph Explorer (Gradio)

Source data : live Wikidata Query Service (https://query.wikidata.org/sparql)
              13 Q-IDs, 395 statements (Neo Genesis parent + founder + 11 SBUs)
Target Space: huggingface.co/spaces/neogenesislab/wikidata-knowledge-graph-explorer

Layout uploaded to the Space repo:
    README.md          Space metadata (YAML frontmatter for HF Spaces)
    app.py             Gradio interface — browse, detail, graph, about
    requirements.txt   gradio + pandas + plotly + requests + networkx
    .gitattributes     text auto

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_wikidata_explorer_space.py
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
SPACE_ID = "neogenesislab/wikidata-knowledge-graph-explorer"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


# ---------------------------------------------------------------------------
# Space artifacts
# ---------------------------------------------------------------------------

APP_PY = '''"""
Wikidata Knowledge Graph Explorer
=================================

Live, interactive visualization of the Neo Genesis knowledge graph on Wikidata:
13 entities (parent + founder + 11 SBUs) with 395 statements across 21+ properties.

Data is queried from the live Wikidata Query Service (SPARQL) on cold start
and cached for 5 minutes. No paid APIs.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any

import gradio as gr
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "Neo-Genesis-Knowledge-Graph-Explorer/1.0 (+https://neogenesis.app)"

# 13 Q-IDs (registered 2026-04-27 via BotPassword + wbeditentity API)
QIDS = [
    "Q139569680",  # Neo Genesis (parent)
    "Q139569708",  # Yesol Heo (founder)
    "Q139569710",  # UR WRONG
    "Q139569711",  # ToolPick
    "Q139569712",  # ReviewLab
    "Q139569715",  # K-OTT
    "Q139569716",  # WhyLab
    "Q139569718",  # EthicaAI
    "Q139569720",  # FinStack
    "Q139569724",  # AIForge
    "Q139569725",  # SellKit
    "Q139569726",  # DeployStack
    "Q139569727",  # CraftDesk
]

# Friendly entity name fallback (used if SPARQL labels are missing)
ENTITY_NAMES = {
    "Q139569680": ("Neo Genesis", "네오제네시스"),
    "Q139569708": ("Yesol Heo", "허예솔"),
    "Q139569710": ("UR WRONG", "유알롱"),
    "Q139569711": ("ToolPick", "툴픽"),
    "Q139569712": ("ReviewLab", "리뷰랩"),
    "Q139569715": ("K-OTT", "케이오티티"),
    "Q139569716": ("WhyLab", "와이랩"),
    "Q139569718": ("EthicaAI", "에티카AI"),
    "Q139569720": ("FinStack", "핀스택"),
    "Q139569724": ("AIForge", "에이아이포지"),
    "Q139569725": ("SellKit", "셀킷"),
    "Q139569726": ("DeployStack", "디플로이스택"),
    "Q139569727": ("CraftDesk", "크래프트데스크"),
}

# Property friendly names
PROPERTY_NAMES = {
    "P31": "instance of",
    "P159": "headquarters location",
    "P17": "country",
    "P571": "inception date",
    "P856": "official website",
    "P1830": "owner of",
    "P127": "owned by",
    "P361": "part of",
    "P1813": "short name",
    "P1448": "official name",
    "P3320": "board member",
    "P1056": "product or material",
    "P137": "operator",
    "P1451": "motto",
    "P21": "sex or gender",
    "P27": "country of citizenship",
    "P176": "manufacturer",
    "P136": "genre",
    "P452": "industry",
    "P407": "language of work",
    "P106": "occupation",
    "P112": "founder",
    "P1813": "short name",
    "P2002": "Twitter username",
    "P2013": "Facebook username",
    "P2037": "GitHub username",
    "P2003": "Instagram username",
    "P973": "described at URL",
    "P2888": "exact match",
    "P2860": "cites work",
}


def _sparql(query: str, timeout: int = 30) -> dict[str, Any]:
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Data loaders (cached 5 minutes)
# ---------------------------------------------------------------------------

def _bucket(seconds: int = 300) -> int:
    """Cache bucket key — increments every ``seconds``."""
    return int(time.time() // seconds)


@lru_cache(maxsize=4)
def load_entities(_cache: int) -> pd.DataFrame:
    """Browse view: 13 entities with labels and statement counts."""
    values = " ".join(f"wd:{q}" for q in QIDS)
    query = f"""
    SELECT ?item ?itemLabel ?itemLabel_ko ?type ?typeLabel ?statementCount WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel)='en') }}
      OPTIONAL {{ ?item rdfs:label ?itemLabel_ko FILTER(LANG(?itemLabel_ko)='ko') }}
      OPTIONAL {{ ?item wdt:P31 ?type . ?type rdfs:label ?typeLabel FILTER(LANG(?typeLabel)='en') }}
      {{
        SELECT ?item (COUNT(?statement) AS ?statementCount) WHERE {{
          ?item ?p ?statement .
          FILTER(STRSTARTS(STR(?p), "http://www.wikidata.org/prop/P"))
        }}
        GROUP BY ?item
      }}
    }}
    """
    try:
        data = _sparql(query)
    except Exception as e:
        print(f"WARN: load_entities SPARQL failed: {e}")
        return _fallback_entities()

    rows = []
    seen = set()
    for b in data.get("results", {}).get("bindings", []):
        qid = b["item"]["value"].split("/")[-1]
        if qid in seen:
            continue
        seen.add(qid)
        en = b.get("itemLabel", {}).get("value", "")
        ko = b.get("itemLabel_ko", {}).get("value", "")
        type_label = b.get("typeLabel", {}).get("value", "")
        sc = int(b.get("statementCount", {}).get("value", 0))
        if not en and qid in ENTITY_NAMES:
            en = ENTITY_NAMES[qid][0]
        if not ko and qid in ENTITY_NAMES:
            ko = ENTITY_NAMES[qid][1]
        rows.append({
            "Q-ID": qid,
            "Label (en)": en,
            "Label (ko)": ko,
            "Type": type_label or "—",
            "Statements": sc,
            "URL": f"https://www.wikidata.org/wiki/{qid}",
        })
    rows.sort(key=lambda r: -r["Statements"])
    return pd.DataFrame(rows)


def _fallback_entities() -> pd.DataFrame:
    """Static fallback if SPARQL endpoint is rate-limited."""
    rows = []
    for qid in QIDS:
        en, ko = ENTITY_NAMES.get(qid, ("", ""))
        rows.append({
            "Q-ID": qid,
            "Label (en)": en,
            "Label (ko)": ko,
            "Type": "—",
            "Statements": 0,
            "URL": f"https://www.wikidata.org/wiki/{qid}",
        })
    return pd.DataFrame(rows)


@lru_cache(maxsize=64)
def load_entity_detail(qid: str, _cache: int) -> list[dict[str, str]]:
    """Detail view: all statements for a given Q-ID, grouped by property."""
    query = f"""
    SELECT ?prop ?propLabel ?value ?valueLabel WHERE {{
      wd:{qid} ?p ?statement .
      ?prop wikibase:directClaim ?p .
      ?statement ?ps ?value .
      ?prop wikibase:claim ?ps .
      OPTIONAL {{ ?prop rdfs:label ?propLabel FILTER(LANG(?propLabel)='en') }}
      OPTIONAL {{ ?value rdfs:label ?valueLabel FILTER(LANG(?valueLabel)='en') }}
    }}
    ORDER BY ?prop
    """
    try:
        data = _sparql(query)
    except Exception as e:
        print(f"WARN: load_entity_detail({qid}) SPARQL failed: {e}")
        return []

    rows = []
    for b in data.get("results", {}).get("bindings", []):
        prop_uri = b["prop"]["value"]
        prop_id = prop_uri.split("/")[-1]
        prop_label = b.get("propLabel", {}).get("value", "") or PROPERTY_NAMES.get(prop_id, prop_id)
        val = b["value"]
        val_uri = val.get("value", "")
        if val_uri.startswith("http://www.wikidata.org/entity/Q"):
            val_qid = val_uri.split("/")[-1]
            val_label = b.get("valueLabel", {}).get("value", "") or val_qid
            display = f"[{val_label}](https://www.wikidata.org/wiki/{val_qid})"
        elif val_uri.startswith("http://") or val_uri.startswith("https://"):
            display = f"[{val_uri}]({val_uri})"
        else:
            display = val_uri
        rows.append({
            "property_id": prop_id,
            "property": prop_label,
            "value": display,
        })
    return rows


@lru_cache(maxsize=4)
def load_relations(_cache: int) -> list[tuple[str, str, str]]:
    """Graph view: P112/P361/P1830/P127 relationships among the 13 entities."""
    values = " ".join(f"wd:{q}" for q in QIDS)
    query = f"""
    SELECT ?source ?prop ?target WHERE {{
      VALUES ?source {{ {values} }}
      VALUES ?target {{ {values} }}
      VALUES ?prop {{ wdt:P112 wdt:P361 wdt:P1830 wdt:P127 wdt:P3320 }}
      ?source ?prop ?target .
    }}
    """
    try:
        data = _sparql(query)
    except Exception as e:
        print(f"WARN: load_relations SPARQL failed: {e}")
        return _fallback_relations()

    edges = []
    seen = set()
    for b in data.get("results", {}).get("bindings", []):
        src = b["source"]["value"].split("/")[-1]
        tgt = b["target"]["value"].split("/")[-1]
        prop = b["prop"]["value"].split("/")[-1]
        # SPARQL endpoint sometimes returns wdt:* form; normalize to P-id
        prop = prop.replace("statement/", "")
        key = (src, prop, tgt)
        if key in seen:
            continue
        seen.add(key)
        edges.append(key)
    if not edges:
        return _fallback_relations()
    return edges


def _fallback_relations() -> list[tuple[str, str, str]]:
    """Heuristic: parent -> founder, parent -> all SBUs (P1830 owner of)."""
    parent = "Q139569680"
    founder = "Q139569708"
    sbus = [q for q in QIDS if q not in (parent, founder)]
    edges = [(parent, "P112", founder)]
    edges += [(parent, "P1830", s) for s in sbus]
    return edges


# ---------------------------------------------------------------------------
# Tab 1: Browse
# ---------------------------------------------------------------------------
def view_entities() -> pd.DataFrame:
    return load_entities(_bucket())


# ---------------------------------------------------------------------------
# Tab 2: Entity Detail
# ---------------------------------------------------------------------------
def entity_detail_md(qid: str) -> str:
    if not qid:
        return "_Pick a Q-ID from the dropdown to see all statements._"
    qid = qid.strip().split()[0] if " " in qid else qid.strip()
    if not qid.startswith("Q"):
        return f"_Invalid Q-ID: `{qid}`. Expected something like `Q139569680`._"

    rows = load_entity_detail(qid, _bucket())
    if not rows:
        return (
            f"_No statements found for [{qid}](https://www.wikidata.org/wiki/{qid}). "
            f"This may be a transient SPARQL cache miss — try again in a few seconds._"
        )

    # Group by property
    grouped: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        grouped.setdefault(r["property"], []).append(r)

    en, ko = ENTITY_NAMES.get(qid, ("", ""))
    parts = [f"## [{qid}](https://www.wikidata.org/wiki/{qid}) — {en} / {ko}"]
    parts.append(f"")
    parts.append(f"**{len(rows)} statements** across **{len(grouped)} properties**.")
    parts.append("")

    for prop_label in sorted(grouped.keys()):
        prop_rows = grouped[prop_label]
        prop_id = prop_rows[0]["property_id"]
        parts.append(
            f"### [{prop_id}](https://www.wikidata.org/wiki/Property:{prop_id}) — {prop_label}"
        )
        for pr in prop_rows:
            parts.append(f"- {pr['value']}")
        parts.append("")
    return "\\n".join(parts)


def qid_choices() -> list[str]:
    """Return human-friendly Q-ID dropdown choices."""
    df = load_entities(_bucket())
    out = []
    for _, row in df.iterrows():
        qid = row["Q-ID"]
        en = row["Label (en)"] or ""
        out.append(f"{qid}  ({en})")
    return out


# ---------------------------------------------------------------------------
# Tab 3: Graph View
# ---------------------------------------------------------------------------
def build_graph_figure() -> go.Figure:
    edges = load_relations(_bucket())
    G = nx.DiGraph()
    for q in QIDS:
        en, ko = ENTITY_NAMES.get(q, (q, q))
        G.add_node(q, label=en, label_ko=ko)
    for src, prop, tgt in edges:
        G.add_edge(src, tgt, prop=prop)

    # Spring layout with parent at center
    pos = nx.spring_layout(G, k=2.5, iterations=80, seed=42)

    # Pin parent + founder positions for readability
    if "Q139569680" in pos:
        pos["Q139569680"] = (0, 0)
    if "Q139569708" in pos:
        pos["Q139569708"] = (1.5, 0.8)

    edge_x, edge_y = [], []
    for src, tgt in G.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, node_text, node_hover, node_size, node_color = [], [], [], [], [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        en = G.nodes[n].get("label", n)
        ko = G.nodes[n].get("label_ko", "")
        node_text.append(en)
        in_deg = G.in_degree(n)
        out_deg = G.out_degree(n)
        node_hover.append(
            f"<b>{en}</b> / {ko}<br>"
            f"Q-ID: {n}<br>"
            f"In: {in_deg} | Out: {out_deg}<br>"
            f"<a href='https://www.wikidata.org/wiki/{n}'>wikidata.org/wiki/{n}</a>"
        )
        if n == "Q139569680":
            node_size.append(45)
            node_color.append("#dc2626")  # red — parent
        elif n == "Q139569708":
            node_size.append(35)
            node_color.append("#7c3aed")  # purple — founder
        else:
            node_size.append(25)
            node_color.append("#2563eb")  # blue — SBUs

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=11, color="#1f2937"),
        hoverinfo="text",
        hovertext=node_hover,
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(width=2, color="white"),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"Neo Genesis Knowledge Graph — {len(G.nodes)} entities, {len(G.edges)} P112/P361/P1830/P127/P3320 edges",
                x=0.5,
                xanchor="center",
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=620,
            plot_bgcolor="white",
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Tab 4: About
# ---------------------------------------------------------------------------

ABOUT_MD = """
### What is this?

A live, interactive explorer for the **Neo Genesis Wikidata knowledge graph** —
13 entities representing the Neo Genesis parent organization, its founder, and
11 production AI business units (SBUs).

### The 13 Q-IDs

| Q-ID | Entity | Type |
|---|---|---|
| [Q139569680](https://www.wikidata.org/wiki/Q139569680) | **Neo Genesis** | parent organization |
| [Q139569708](https://www.wikidata.org/wiki/Q139569708) | **Yesol Heo** | founder (P112) |
| [Q139569710](https://www.wikidata.org/wiki/Q139569710) | UR WRONG | SBU (social) |
| [Q139569711](https://www.wikidata.org/wiki/Q139569711) | ToolPick | SBU (business) |
| [Q139569712](https://www.wikidata.org/wiki/Q139569712) | ReviewLab | SBU (business) |
| [Q139569715](https://www.wikidata.org/wiki/Q139569715) | K-OTT | SBU (entertainment) |
| [Q139569716](https://www.wikidata.org/wiki/Q139569716) | WhyLab | SBU (research) |
| [Q139569718](https://www.wikidata.org/wiki/Q139569718) | EthicaAI | SBU (educational) |
| [Q139569720](https://www.wikidata.org/wiki/Q139569720) | FinStack | SBU (finance) |
| [Q139569724](https://www.wikidata.org/wiki/Q139569724) | AIForge | SBU (business) |
| [Q139569725](https://www.wikidata.org/wiki/Q139569725) | SellKit | SBU (business) |
| [Q139569726](https://www.wikidata.org/wiki/Q139569726) | DeployStack | SBU (developer) |
| [Q139569727](https://www.wikidata.org/wiki/Q139569727) | CraftDesk | SBU (design) |

All entities were registered on **2026-04-27** via BotPassword + the Wikidata
`wbeditentity` API directly (account: `Neogenesislab`). Total: **395 statements**
across 21+ properties (P31 instance-of, P159 HQ, P571 inception, P856 website,
P112 founder, P1830 owner-of, P3320 board member, etc.).

### sameAs cross-linking

Each Q-ID is mirrored in the Neo Genesis homepage Schema.org JSON-LD via
`Organization.sameAs` and per-SBU `SoftwareApplication.sameAs` arrays. This
gives AI search engines (ChatGPT, Perplexity, Gemini, Copilot) a stable
identifier graph to ground retrieval and citations.

### Data source

This Space queries the **live** [Wikidata Query Service](https://query.wikidata.org/sparql)
on cold start, with results cached for 5 minutes via `functools.lru_cache`. No
paid APIs, no static snapshot — the graph reflects whatever is currently public
on Wikidata. If WDQS is rate-limiting, a static fallback (parent ↔ founder ↔
11 SBUs) is shown instead.

### Resources

- **Neo Genesis homepage**: [neogenesis.app](https://neogenesis.app)
- **Operator (HuggingFace)**: [neogenesislab](https://huggingface.co/neogenesislab)
- **Datasets** (6):
  - [korean-rag-ssot-golden-50](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [ethicaai-mixed-safe-evidence](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
  - [whylab-gemini-2-5-docker-validation](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation)
  - [sbu-pseo-effects-2026-04](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04)
  - [korean-llm-citation-baseline-2026](https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026)
  - [cross-agent-review-queue-2026](https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026)
- **Companion Spaces**:
  - [korean-rag-ssot-golden-50-explorer](https://huggingface.co/spaces/neogenesislab/korean-rag-ssot-golden-50-explorer)
  - [cross-agent-review-queue-explorer](https://huggingface.co/spaces/neogenesislab/cross-agent-review-queue-explorer)

### License

- App code: **MIT**
- Data: **CC0** (Wikidata is public domain)
"""


# ---------------------------------------------------------------------------
# Gradio app
# ---------------------------------------------------------------------------

INTRO_MD = """
# Wikidata Knowledge Graph Explorer

Live, interactive view of the **Neo Genesis** knowledge graph on Wikidata —
13 entities (parent organization + founder + 11 SBUs) with **395 statements**
across 21+ properties.

Data is queried from the live [Wikidata Query Service](https://query.wikidata.org/sparql)
on cold start (cached 5 min). No paid APIs.

- **Wikidata parent**: [Q139569680](https://www.wikidata.org/wiki/Q139569680)
- **Founder**: [Yesol Heo / Q139569708](https://www.wikidata.org/wiki/Q139569708)
- **Operator**: [neogenesislab](https://huggingface.co/neogenesislab)
"""


with gr.Blocks(title="Wikidata Knowledge Graph Explorer", theme=gr.themes.Soft()) as demo:
    gr.Markdown(INTRO_MD)

    with gr.Tab("Browse"):
        gr.Markdown(
            "All **13 entities** sorted by statement count. Click a Q-ID column "
            "value to copy it, then paste into the **Entity Detail** tab."
        )
        browse_table = gr.DataFrame(
            value=view_entities(),
            label="Neo Genesis entity registry (live from Wikidata)",
            wrap=True,
            interactive=False,
        )
        refresh_btn = gr.Button("Refresh from Wikidata", variant="secondary")
        refresh_btn.click(view_entities, outputs=browse_table)

    with gr.Tab("Entity Detail"):
        gr.Markdown(
            "Pick a Q-ID to see **all statements** grouped by property "
            "(P31, P159, P571, P856, P112, P1830, etc.). External URLs and "
            "linked Q-items render as clickable Markdown links."
        )
        with gr.Row():
            qid_dd = gr.Dropdown(
                choices=qid_choices(),
                value=qid_choices()[0] if qid_choices() else "",
                label="Q-ID",
                scale=4,
            )
            view_btn = gr.Button("Show statements", variant="primary", scale=1)
        detail_md = gr.Markdown(entity_detail_md(QIDS[0]))
        view_btn.click(entity_detail_md, inputs=qid_dd, outputs=detail_md)
        qid_dd.change(entity_detail_md, inputs=qid_dd, outputs=detail_md)

    with gr.Tab("Graph View"):
        gr.Markdown(
            "Force-directed layout of P112 (founder), P361 (part of), P1830 "
            "(owner of), P127 (owned by), and P3320 (board member) "
            "relationships across the 13 entities. Hover any node to see "
            "in/out degree and a Wikidata link."
        )
        graph_plot = gr.Plot(value=build_graph_figure())
        graph_refresh = gr.Button("Re-query Wikidata", variant="secondary")
        graph_refresh.click(build_graph_figure, outputs=graph_plot)

    with gr.Tab("About"):
        gr.Markdown(ABOUT_MD)


if __name__ == "__main__":
    demo.queue().launch()
'''

REQUIREMENTS_TXT = """gradio==5.9.1
pandas>=2.0
plotly>=5.20
requests>=2.31
networkx>=3.0
"""

GITATTRIBUTES = "* text=auto eol=lf\n"


def build_space_readme() -> str:
    yaml_front = """---
title: Wikidata Knowledge Graph Explorer
emoji: 🌐
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: mit
short_description: 13 entities, 395 Wikidata statements live.
tags:
- knowledge-graph
- wikidata
- sparql
- semantic-web
- linked-data
- neo-genesis
---
"""
    body = """
# Wikidata Knowledge Graph Explorer

A Gradio UI to browse, inspect, and visualize the **Neo Genesis** knowledge graph
on Wikidata: 13 entities (parent organization + founder + 11 SBUs) with **395
statements** across 21+ properties.

Data is queried from the live [Wikidata Query Service](https://query.wikidata.org/sparql)
at cold start, cached 5 min via `functools.lru_cache`. No paid APIs.

## Tabs
1. **Browse** — table of all 13 entities sorted by statement count, with EN/KO labels and Wikidata links.
2. **Entity Detail** — pick a Q-ID, see all statements grouped by property (P31, P159, P571, P856, P112, P1830, P3320, etc.).
3. **Graph View** — force-directed networkx + plotly visualization of P112 / P361 / P1830 / P127 / P3320 relationships.
4. **About** — Q-ID registry, sameAs cross-linking explanation, and links back to neogenesis.app + 6 HF datasets + 2 companion Spaces.

## The 13 Q-IDs
- [Q139569680](https://www.wikidata.org/wiki/Q139569680) — Neo Genesis (parent)
- [Q139569708](https://www.wikidata.org/wiki/Q139569708) — Yesol Heo (founder, P112)
- Q139569710 / 711 / 712 / 715 / 716 / 718 / 720 / 724 / 725 / 726 / 727 — 11 SBUs

All registered 2026-04-27 via BotPassword + `wbeditentity` API directly.

## Stack
- `gradio==5.9.1` (Python 3.13 native)
- `pandas` + `plotly` (browse + graph)
- `networkx` (force-directed layout)
- `requests` / `urllib` (SPARQL queries)

## License
- App code: **MIT** (this Space)
- Data: **CC0** (Wikidata is public domain)

## Operator
- [neogenesis.app](https://neogenesis.app)
- HuggingFace: [neogenesislab](https://huggingface.co/neogenesislab)
"""
    return yaml_front + body


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    # Quick sanity check that the live SPARQL endpoint is reachable.
    try:
        import urllib.request
        import urllib.parse
        q = "SELECT ?item WHERE { VALUES ?item { wd:Q139569680 } }"
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
            {"query": q, "format": "json"}
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Neo-Genesis-Knowledge-Graph-Explorer/1.0 (+https://neogenesis.app)",
                "Accept": "application/sparql-results+json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"OK: SPARQL endpoint reachable ({resp.status})")
    except Exception as exc:
        print(f"WARN: could not pre-validate SPARQL endpoint: {exc}")

    readme = build_space_readme()
    print(f"prepared README.md ({len(readme):,} bytes)")
    print(f"prepared app.py ({len(APP_PY):,} bytes)")
    print(f"prepared requirements.txt ({len(REQUIREMENTS_TXT):,} bytes)")
    print(f"prepared .gitattributes ({len(GITATTRIBUTES):,} bytes)")

    from huggingface_hub import HfApi

    api = HfApi(token=token)

    print(f"create_repo {SPACE_ID} (space, gradio, public)")
    api.create_repo(
        repo_id=SPACE_ID,
        repo_type="space",
        space_sdk="gradio",
        exist_ok=True,
        private=False,
    )

    uploads = [
        ("README.md", readme),
        ("app.py", APP_PY),
        ("requirements.txt", REQUIREMENTS_TXT),
        (".gitattributes", GITATTRIBUTES),
    ]

    for path_in_repo, content in uploads:
        print(f"upload {path_in_repo} ({len(content):,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=SPACE_ID,
            repo_type="space",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/spaces/{SPACE_ID}"
    print()
    print("PUBLISHED:", url)

    # Best-effort runtime status check
    try:
        info = api.space_info(repo_id=SPACE_ID)
        runtime = getattr(info, "runtime", None)
        stage = getattr(runtime, "stage", None) if runtime else None
        hardware = getattr(runtime, "hardware", None) if runtime else None
        print(f"runtime.stage = {stage}")
        print(f"runtime.hardware = {hardware}")
    except Exception as exc:
        print(f"(non-fatal) space_info() not yet available: {exc}")

    # Live HTTP HEAD verification
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"HEAD {url} -> {resp.status}")
    except Exception as exc:
        print(f"(non-fatal) HEAD check failed: {exc}")

    # Poll runtime stage until RUNNING (max 5 attempts, 30s each)
    print("polling runtime stage (max 5 x 30s)...")
    for attempt in range(1, 6):
        time.sleep(30)
        try:
            info = api.space_info(repo_id=SPACE_ID)
            runtime = getattr(info, "runtime", None)
            stage = getattr(runtime, "stage", None) if runtime else None
            print(f"  attempt {attempt}: runtime.stage = {stage}")
            if stage == "RUNNING":
                print("Space is RUNNING")
                break
            if stage in ("BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"):
                print(f"BUILD/RUNTIME ERROR detected at attempt {attempt}: stage={stage}")
                break
        except Exception as exc:
            print(f"  attempt {attempt}: space_info error: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
