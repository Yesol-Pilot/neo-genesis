"""Neo Genesis Ontology v0.4 -- SBU-scoped vector index.

Per DESIGN §14 v0.4 진입 게이트: SBU 별 vector index (kott / toolpick / ur-wrong 등).

Implementation:
- Primary: TF-IDF + Korean character n-grams (sklearn, no network)
- Optional: KURE-v1 embedding (when service alive @ desktop-sol01:7702)
- Optional: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (~470MB)

Index per SBU (Project{kind:sbu}):
- Vector matrix: (n_artifacts, n_features) — TF-IDF
- Metadata: artifact_id, path, title
- Saved to: .agent/ontology/vector_index/<sbu_slug>/{vectors.npz, meta.json}

Usage:
    python scripts/ontology/vector_index.py --rebuild [--sbu kott]
    python scripts/ontology/vector_index.py --query "정기구독 비용" --sbu kott --top-k 3
    python scripts/ontology/vector_index.py --query "페르소나 dispatcher" --top-k 5  # global
    python scripts/ontology/vector_index.py --list-sbus
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

KURE_BASE_URL = os.environ.get("KURE_BASE_URL", "http://desktop-sol01:7702")
KURE_EMBED_DIM = 1024


def kure_available() -> bool:
    """Check if KURE-v1 service is reachable (1.5s timeout)."""
    try:
        req = urllib.request.Request(f"{KURE_BASE_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def kure_embed(texts: list[str]) -> list[list[float]] | None:
    """Batch embed via KURE-v1 service. Returns None if service down."""
    try:
        data = json.dumps({"texts": texts}).encode("utf-8")
        req = urllib.request.Request(
            f"{KURE_BASE_URL}/embed",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("embeddings")
    except Exception as e:
        print(f"[WARN] KURE embed failed: {e}", file=sys.stderr)
        return None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
except ImportError as e:
    print(f"[ERROR] {e}. Run: pip install scikit-learn numpy")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
INDEX_DIR = ONTOLOGY_DIR / "vector_index"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def get_artifact_text(node: dict) -> str:
    """Extract text from Artifact node for vectorization.

    Reads actual file content (capped) if path exists; falls back to metadata.
    """
    path = node.get("path", "")
    label = node.get("label", "")
    title = node.get("title", "")
    text_parts = [label, title]
    if path and not path.startswith("external://") and not path.startswith("~"):
        file_path = REPO_ROOT / path
        if file_path.exists() and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                text_parts.append(content[:5000])  # cap 5KB per file
            except Exception:
                pass
    return "\n".join(p for p in text_parts if p)


def collect_sbu_artifacts() -> dict[str, list[dict]]:
    """Group Artifacts by their owning SBU Project (via owned_by edge).

    Artifacts without owned_by edge are bucketed into 'unowned'.
    """
    nodes = load_jsonl(NODES_PATH)
    edges = load_jsonl(EDGES_PATH)

    # Build node lookup
    node_by_id = {n["id"]: n for n in nodes}

    # Find owned_by edges: Artifact -> Project
    artifact_to_project: dict[str, str] = {}
    for e in edges:
        if e["type"] != "owned_by":
            continue
        src = e["from"]
        tgt = e["to"]
        if src not in node_by_id or tgt not in node_by_id:
            continue
        if node_by_id[src].get("rdf_type") != "Artifact":
            continue
        if node_by_id[tgt].get("rdf_type") != "Project":
            continue
        artifact_to_project[src] = tgt

    # Group artifacts by Project label (= SBU slug)
    sbu_artifacts: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        if n.get("rdf_type") != "Artifact":
            continue
        project_id = artifact_to_project.get(n["id"])
        if project_id:
            sbu_slug = node_by_id[project_id].get("label", "unknown")
        else:
            sbu_slug = "unowned"
        sbu_artifacts[sbu_slug].append(n)

    return sbu_artifacts


def build_index_for_sbu(sbu_slug: str, artifacts: list[dict],
                        prefer_kure: bool = True) -> dict[str, Any]:
    """Build vector index for one SBU.

    v0.5: KURE-v1 1024-dim embedding 우선 시도, 실패 시 TF-IDF char_wb fallback.
    Returns stats dict.
    """
    if not artifacts:
        return {"sbu": sbu_slug, "n_artifacts": 0, "status": "skip_empty"}

    texts = [get_artifact_text(a) for a in artifacts]
    metas = [{
        "id": a["id"],
        "path": a.get("path", ""),
        "title": a.get("title", a.get("label", "")),
        "kind": a.get("kind", "?"),
    } for a in artifacts]

    out_dir = INDEX_DIR / sbu_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # v0.5: KURE-v1 우선 시도
    if prefer_kure and kure_available():
        embeddings = kure_embed(texts)
        if embeddings and len(embeddings) == len(texts):
            try:
                matrix = np.array(embeddings, dtype=np.float32)  # dense (n, 1024)
                np.savez_compressed(out_dir / "matrix.npz", embeddings=matrix)
                (out_dir / "meta.json").write_text(
                    json.dumps({
                        "sbu_slug": sbu_slug,
                        "n_artifacts": len(artifacts),
                        "n_features": KURE_EMBED_DIM,
                        "vectorizer_type": "kure-v1",
                        "kure_endpoint": KURE_BASE_URL,
                        "items": metas,
                    }, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                # Remove old TF-IDF artifacts if any
                pkl = out_dir / "vectorizer.pkl"
                if pkl.exists():
                    pkl.unlink()
                return {
                    "sbu": sbu_slug,
                    "n_artifacts": len(artifacts),
                    "n_features": KURE_EMBED_DIM,
                    "matrix_shape": list(matrix.shape),
                    "status": "indexed_kure",
                    "vectorizer": "kure-v1",
                }
            except Exception as e:
                print(f"[WARN] KURE save failed for {sbu_slug}: {e}", file=sys.stderr)

    # Fallback: TF-IDF with character n-grams (Korean morphology friendly)
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=10000,
        min_df=1,
        max_df=0.95,
    )
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError as e:
        return {"sbu": sbu_slug, "n_artifacts": len(artifacts), "status": "fit_failed", "error": str(e)}

    from scipy.sparse import save_npz
    save_npz(out_dir / "matrix.npz", matrix)
    with (out_dir / "vectorizer.pkl").open("wb") as f:
        pickle.dump(vectorizer, f)

    (out_dir / "meta.json").write_text(
        json.dumps({
            "sbu_slug": sbu_slug,
            "n_artifacts": len(artifacts),
            "n_features": matrix.shape[1],
            "vectorizer_type": "tfidf_char_wb_2-4",
            "items": metas,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "sbu": sbu_slug,
        "n_artifacts": len(artifacts),
        "n_features": matrix.shape[1],
        "matrix_shape": list(matrix.shape),
        "status": "indexed_tfidf_fallback",
        "vectorizer": "tfidf_char_wb_2-4",
        "kure_attempted": prefer_kure,
        "kure_available": kure_available() if prefer_kure else None,
    }


def query_sbu_index(sbu_slug: str, query: str, top_k: int = 5) -> dict[str, Any]:
    """Query a single SBU's vector index (KURE or TF-IDF auto-detect)."""
    sbu_dir = INDEX_DIR / sbu_slug
    if not sbu_dir.exists():
        return {"error": f"SBU index not found: {sbu_slug}", "sbu": sbu_slug}

    meta = json.loads((sbu_dir / "meta.json").read_text(encoding="utf-8"))
    vec_type = meta.get("vectorizer_type", "tfidf_char_wb_2-4")

    if vec_type == "kure-v1":
        # KURE-v1: dense embeddings, query via service
        embeddings = kure_embed([query])
        if not embeddings:
            return {"sbu": sbu_slug, "error": "KURE service unavailable for query"}
        q_vec = np.array(embeddings[0], dtype=np.float32)
        loaded = np.load(sbu_dir / "matrix.npz")
        matrix = loaded["embeddings"]  # (n, 1024)
        # Cosine similarity (assuming KURE returns normalized)
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_vec)
        sims = (matrix @ q_vec) / np.maximum(norms, 1e-9)
    else:
        # TF-IDF: sparse vectorizer
        from scipy.sparse import load_npz
        matrix = load_npz(sbu_dir / "matrix.npz")
        with (sbu_dir / "vectorizer.pkl").open("rb") as f:
            vectorizer = pickle.load(f)
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, matrix).flatten()

    top_indices = np.argsort(-sims)[:top_k]
    results = []
    for idx in top_indices:
        if sims[idx] <= 0:
            continue
        item = meta["items"][int(idx)].copy()
        item["similarity"] = round(float(sims[idx]), 4)
        results.append(item)

    return {
        "sbu": sbu_slug,
        "query": query,
        "vectorizer": vec_type,
        "top_k": top_k,
        "matches": results,
    }


def query_global(query: str, top_k: int = 5) -> dict[str, Any]:
    """Query across all SBU indexes; merge top-k by similarity."""
    all_results = []
    for sbu_dir in INDEX_DIR.iterdir() if INDEX_DIR.exists() else []:
        if not sbu_dir.is_dir():
            continue
        r = query_sbu_index(sbu_dir.name, query, top_k=top_k)
        for m in r.get("matches", []):
            m["sbu"] = sbu_dir.name
            all_results.append(m)

    all_results.sort(key=lambda m: -m["similarity"])
    return {
        "query": query,
        "scope": "global",
        "top_k": top_k,
        "matches": all_results[:top_k],
    }


def list_sbus() -> dict[str, Any]:
    """List all available SBU indexes."""
    if not INDEX_DIR.exists():
        return {"sbus": [], "note": "vector_index/ dir not yet created"}
    sbus = []
    for d in sorted(INDEX_DIR.iterdir()):
        if d.is_dir() and (d / "meta.json").exists():
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            sbus.append({
                "sbu": d.name,
                "n_artifacts": meta["n_artifacts"],
                "n_features": meta["n_features"],
            })
    return {"sbus": sbus, "total": len(sbus)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild all (or one with --sbu) indexes")
    parser.add_argument("--sbu", help="Target SBU slug (kott / toolpick / etc.)")
    parser.add_argument("--query", help="Query text")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--list-sbus", action="store_true")
    args = parser.parse_args()

    if args.list_sbus:
        print(json.dumps(list_sbus(), indent=2, ensure_ascii=False))
        return 0

    if args.rebuild:
        sbu_artifacts = collect_sbu_artifacts()
        if args.sbu:
            if args.sbu not in sbu_artifacts:
                print(f"[ERROR] SBU '{args.sbu}' not found. Available: {list(sbu_artifacts.keys())}")
                return 2
            stats = build_index_for_sbu(args.sbu, sbu_artifacts[args.sbu])
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            all_stats = []
            for sbu, items in sorted(sbu_artifacts.items()):
                stats = build_index_for_sbu(sbu, items)
                all_stats.append(stats)
            print(json.dumps({"rebuilt": all_stats}, indent=2, ensure_ascii=False))
        return 0

    if args.query:
        if args.sbu:
            print(json.dumps(query_sbu_index(args.sbu, args.query, args.top_k),
                             indent=2, ensure_ascii=False))
        else:
            print(json.dumps(query_global(args.query, args.top_k),
                             indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
