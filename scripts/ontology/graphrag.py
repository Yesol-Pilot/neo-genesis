"""Neo Genesis Ontology v0.3 -- nano-graphrag PoC.

LightRAG / Microsoft GraphRAG 의 핵심 아이디어를 우리 규모에 맞게 단순화:
1. nodes.jsonl + edges.jsonl 을 networkx Graph 로 로드
2. Louvain community detection 으로 의미적 cluster 추출
3. 각 community 의 cluster summary 생성 (한국어, rule-based)
4. .agent/ontology/communities.json 으로 저장

LLM 미사용 (RAG v0.4 전 단계, "structural Graph RAG"):
- entity 는 이미 추출됨 (Artifact / Service / Agent 등)
- relationship 도 이미 박제됨 (17 관계)
- LightRAG 의 dual-level (low entity + high concept) 중 high concept = community summary

Usage:
    python scripts/ontology/graphrag.py [--resolution 1.0] [--seed 42]
    python scripts/ontology/graphrag.py --query "ToolPick 관련 자산"
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import networkx as nx
    from networkx.algorithms.community import louvain_communities
except ImportError as e:
    print(f"[ERROR] {e}. Run: pip install networkx")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
COMMUNITIES_PATH = ONTOLOGY_DIR / "communities.json"


def load_graph() -> tuple[nx.Graph, dict[str, dict]]:
    """Load nodes + edges into undirected NetworkX graph (community detection은
    undirected가 더 안정)."""
    G = nx.Graph()
    node_meta = {}

    if NODES_PATH.exists():
        for line in NODES_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            n = json.loads(line)
            G.add_node(n["id"])
            node_meta[n["id"]] = n

    if EDGES_PATH.exists():
        for line in EDGES_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            G.add_edge(e["from"], e["to"], type=e["type"])

    return G, node_meta


def summarize_community(community: set[str], node_meta: dict[str, dict], G: nx.Graph) -> dict[str, Any]:
    """Generate Korean cluster summary (rule-based, no LLM)."""
    members = [node_meta[nid] for nid in community if nid in node_meta]
    if not members:
        return {"size": 0, "summary": "(empty)"}

    # rdf_type breakdown
    type_count = Counter(m["rdf_type"] for m in members)

    # Sample labels by rdf_type
    by_type: dict[str, list[str]] = defaultdict(list)
    for m in members:
        by_type[m["rdf_type"]].append(m.get("label", m.get("path", m["id"]))[:40])

    # Find dominant edge types within this community
    edge_types = Counter()
    for u, v, data in G.subgraph(community).edges(data=True):
        edge_types[data.get("type", "?")] += 1

    # Generate Korean narrative
    primary_type = type_count.most_common(1)[0][0] if type_count else "?"
    size = len(members)

    narrative_parts = [f"{size}개 객체 cluster (주력: {primary_type})"]
    if primary_type == "Artifact":
        kinds = Counter(m.get("kind", "?") for m in members if m["rdf_type"] == "Artifact")
        narrative_parts.append(f"  Artifact 분포: {dict(kinds.most_common(3))}")
    if primary_type == "Project":
        stages = Counter(m.get("stage", "?") for m in members if m["rdf_type"] == "Project")
        narrative_parts.append(f"  Project stage: {dict(stages.most_common())}")
    if primary_type == "Agent":
        kinds = Counter(m.get("agent_kind", "?") for m in members if m["rdf_type"] == "Agent")
        narrative_parts.append(f"  Agent 분류: {dict(kinds.most_common())}")
    if edge_types:
        narrative_parts.append(f"  주요 관계: {dict(edge_types.most_common(3))}")

    narrative = "\n".join(narrative_parts)

    return {
        "size": size,
        "rdf_type_distribution": dict(type_count),
        "sample_labels_by_type": {k: v[:5] for k, v in by_type.items()},
        "edge_type_distribution": dict(edge_types),
        "summary": narrative,
        "member_ids": sorted(community),
    }


def build_communities(resolution: float = 1.0, seed: int = 42) -> dict[str, Any]:
    """Run Louvain community detection and generate cluster summaries."""
    G, node_meta = load_graph()
    print(f"Graph loaded: {G.number_of_nodes()} nodes / {G.number_of_edges()} edges", file=sys.stderr)

    # Detect communities
    communities = louvain_communities(G, resolution=resolution, seed=seed)
    print(f"Detected {len(communities)} communities", file=sys.stderr)

    # Summarize each
    summaries = []
    for i, comm in enumerate(sorted(communities, key=lambda c: -len(c))):
        s = summarize_community(comm, node_meta, G)
        s["community_id"] = f"neo://community/c{i:03d}"
        s["rank"] = i
        summaries.append(s)

    result = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "algorithm": "louvain",
        "resolution": resolution,
        "seed": seed,
        "graph_stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "communities": len(communities),
        },
        "communities": summaries,
    }
    return result


def hipporag_query(seed_uris: list[str], top_k: int = 10,
                   damping: float = 0.5) -> dict[str, Any]:
    """HippoRAG-style multi-hop reasoning via Personalized PageRank.

    Reference: Jimenez Gutierrez et al. 2024 (NeurIPS'24), arXiv:2405.14831.
    Neurobiologically inspired: hippocampal indexing. PPR scores all nodes
    based on proximity to seed nodes via graph topology.

    For "A1 알파 실패 근본 원인은?" style multi-hop questions, this single
    retrieval step explores depth N along Agent → Task → Artifact → Decision
    chains automatically.

    Args:
        seed_uris: List of node URIs to seed PPR (relevance anchors).
        top_k: Number of top-ranked nodes to return.
        damping: PPR damping factor (0.0~1.0). Higher = more local exploration.
    """
    G, node_meta = load_graph()
    if G.number_of_nodes() == 0:
        return {"error": "graph empty"}

    # Build personalization vector (1.0 for seeds, 0.0 for others)
    valid_seeds = [s for s in seed_uris if s in G.nodes]
    if not valid_seeds:
        return {
            "error": "no valid seeds in graph",
            "requested_seeds": seed_uris,
            "available_sample": list(G.nodes())[:5],
        }
    personalization = {n: 0.0 for n in G.nodes()}
    for s in valid_seeds:
        personalization[s] = 1.0 / len(valid_seeds)

    # Run Personalized PageRank
    pr = nx.pagerank(G, alpha=damping, personalization=personalization, max_iter=100)

    # Rank
    ranked = sorted(pr.items(), key=lambda kv: -kv[1])
    top = []
    for nid, score in ranked[:top_k]:
        meta = node_meta.get(nid, {})
        top.append({
            "id": nid,
            "rdf_type": meta.get("rdf_type", "?"),
            "label": meta.get("label", meta.get("path", "?"))[:60],
            "ppr_score": round(score, 6),
            "is_seed": nid in valid_seeds,
        })

    return {
        "seeds": valid_seeds,
        "damping": damping,
        "top_k": top_k,
        "results": top,
    }


def lightrag_dual_level(query: str, top_k: int = 5) -> dict[str, Any]:
    """LightRAG dual-level retrieval (structural variant, no LLM).

    Reference: Guo et al. 2024, arXiv:2410.05779.

    Low-level: entity-specific match (substring on label/path).
    High-level: concept match (community summary substring + edge type pattern).

    Returns merged top_k from both levels.
    """
    if not COMMUNITIES_PATH.exists():
        return {"error": "communities.json not found. Run --rebuild first."}
    data = json.loads(COMMUNITIES_PATH.read_text(encoding="utf-8"))
    G, node_meta = load_graph()

    q_lower = query.lower()

    # Low-level: scan nodes
    low_level = []
    for nid, meta in node_meta.items():
        label = meta.get("label", "")
        path = meta.get("path", "")
        title = meta.get("title", "")
        target = f"{label} {path} {title}".lower()
        if q_lower in target:
            low_level.append({
                "level": "low",
                "id": nid,
                "rdf_type": meta.get("rdf_type", "?"),
                "label": label[:60] or path[:60],
            })
            if len(low_level) >= top_k * 2:
                break

    # High-level: scan community summaries
    high_level = []
    for c in data["communities"]:
        summary_text = c["summary"].lower()
        if q_lower in summary_text:
            high_level.append({
                "level": "high",
                "community_id": c["community_id"],
                "size": c["size"],
                "summary_line1": c["summary"].split("\n")[0],
                "rdf_type_distribution": c["rdf_type_distribution"],
            })

    # Edge-type pattern match (e.g. "depends_on" query → all depends_on subgraph)
    edge_matches = []
    for u, v, data_e in G.edges(data=True):
        if q_lower in data_e.get("type", "").lower():
            edge_matches.append({
                "from": u,
                "type": data_e["type"],
                "to": v,
            })
            if len(edge_matches) >= top_k:
                break

    return {
        "query": query,
        "low_level_count": len(low_level),
        "high_level_count": len(high_level),
        "edge_match_count": len(edge_matches),
        "low_level": low_level[:top_k],
        "high_level": high_level[:top_k],
        "edge_pattern_matches": edge_matches[:top_k],
    }


def query_communities(query: str, top_k: int = 3) -> dict[str, Any]:
    """Find communities containing nodes whose label/path matches the query (substring).

    This is the "high-level concept query" in LightRAG dual-level pattern.
    For real graph RAG, would use embedding similarity (KURE-v1 v0.4).
    """
    if not COMMUNITIES_PATH.exists():
        return {"error": "communities.json not found. Run --rebuild first."}
    data = json.loads(COMMUNITIES_PATH.read_text(encoding="utf-8"))

    query_lower = query.lower()
    matches = []
    for c in data["communities"]:
        score = 0
        sample_hits = []
        for type_labels in c["sample_labels_by_type"].values():
            for lbl in type_labels:
                if query_lower in lbl.lower():
                    score += 1
                    sample_hits.append(lbl)
        if score > 0:
            matches.append({
                "community_id": c["community_id"],
                "rank": c["rank"],
                "size": c["size"],
                "score": score,
                "matched_samples": sample_hits[:5],
                "summary": c["summary"],
            })
    matches.sort(key=lambda m: -m["score"])
    return {
        "query": query,
        "top_k": top_k,
        "matches": matches[:top_k],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Run community detection and save")
    parser.add_argument("--query", help="Query communities by substring match")
    parser.add_argument("--resolution", type=float, default=1.0,
                        help="Louvain resolution parameter (higher = more communities)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--summary", action="store_true",
                        help="Print summary of existing communities.json")
    parser.add_argument("--hipporag", nargs="+", metavar="SEED_URI",
                        help="HippoRAG PPR multi-hop from seed URIs")
    parser.add_argument("--damping", type=float, default=0.5,
                        help="PPR damping factor (HippoRAG)")
    parser.add_argument("--dual-level", metavar="QUERY",
                        help="LightRAG dual-level retrieval (low entity + high concept)")
    args = parser.parse_args()

    if args.hipporag:
        result = hipporag_query(args.hipporag, top_k=args.top_k, damping=args.damping)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.dual_level:
        result = lightrag_dual_level(args.dual_level, top_k=args.top_k)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.rebuild or (not COMMUNITIES_PATH.exists() and not args.query):
        result = build_communities(resolution=args.resolution, seed=args.seed)
        COMMUNITIES_PATH.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Print a compact summary
        print(json.dumps({
            "generated_at": result["generated_at"],
            "graph_stats": result["graph_stats"],
            "community_sizes": [c["size"] for c in result["communities"]],
            "top_3_summaries": [
                {"community_id": c["community_id"], "size": c["size"],
                 "summary": c["summary"]}
                for c in result["communities"][:3]
            ],
        }, indent=2, ensure_ascii=False))
        print(f"\n[OK] communities.json -> {COMMUNITIES_PATH}", file=sys.stderr)
        return 0

    if args.summary:
        if not COMMUNITIES_PATH.exists():
            print("[ERROR] communities.json not found. Run --rebuild first.")
            return 2
        data = json.loads(COMMUNITIES_PATH.read_text(encoding="utf-8"))
        compact = {
            "generated_at": data["generated_at"],
            "graph_stats": data["graph_stats"],
            "communities": [
                {"community_id": c["community_id"], "size": c["size"],
                 "rdf_type_distribution": c["rdf_type_distribution"],
                 "summary_line1": c["summary"].split("\n")[0]}
                for c in data["communities"]
            ],
        }
        print(json.dumps(compact, indent=2, ensure_ascii=False))
        return 0

    if args.query:
        result = query_communities(args.query, top_k=args.top_k)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
