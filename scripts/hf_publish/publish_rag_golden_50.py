"""
HuggingFace Datasets publish — Korean RAG SSOT Golden 50

Source : tests/rag_golden/ssot_korean_v2.json (50 tasks, supersedes v1)
Target : huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50

Layout:
    README.md          dataset card with YAML frontmatter (bilingual ko + en)
    data/tasks.jsonl   50 tasks one per line (HF Datasets viewer auto-recognizes)
    metadata.json      benchmark-level meta (name / version / metrics / etc.)

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_rag_golden_50.py
"""
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests" / "rag_golden" / "ssot_korean_v2.json"
ENV_LOCAL = ROOT / ".env.local"
REPO_ID = "neogenesislab/korean-rag-ssot-golden-50"


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


def build_readme(meta: dict) -> str:
    """Bilingual dataset card with YAML frontmatter optimized for HF Datasets viewer + GEO."""
    n = len(meta["tasks"])
    cats = meta.get("category_distribution", {})
    cat_rows = "\n".join(f"| `{c}` | {v} |" for c, v in cats.items())
    thresholds = meta.get("metrics", {}).get("thresholds", {})
    primary = meta.get("metrics", {}).get("primary", "")
    metric_rows = "\n".join(
        f"| `{name}`{' (primary)' if name == primary else ''} | {threshold} |"
        for name, threshold in thresholds.items()
    )
    yaml_front = f"""---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- question-answering
- text-retrieval
tags:
- rag
- korean
- evaluation
- llm-as-judge
- retrieval-augmented-generation
- governance
- security
- agent-evaluation
size_categories:
- n<1K
pretty_name: Korean RAG SSOT Golden 50 (Neo Genesis)
configs:
- config_name: default
  data_files:
  - split: train
    path: data/tasks.jsonl
---
"""
    body = f"""
# Korean RAG SSOT Golden 50 (Neo Genesis)

> A Korean-language **retrieval-augmented generation evaluation set** of {n} hand-curated tasks built by **[Neo Genesis](https://neogenesis.app)** for stress-testing real-world RAG agents on agent governance, autonomous trading, and security/PII redaction scenarios.

## Why this dataset exists

Most Korean RAG benchmarks evaluate factual QA over Wikipedia-style corpora.
Production agent systems instead need to retrieve from **operational SSOT** (Single Source of Truth) repositories — design docs, runbooks, code, incident logs, policy YAML — where the answer is grounded in human-authored governance text rather than encyclopedic facts.

This benchmark was extracted from Neo Genesis' live SSOT (`/.agent/`) used to operate **11 production AI business units** (UR WRONG, ToolPick, ReviewLab, K-OTT, WhyLab, EthicaAI, FinStack, AIForge, SellKit, DeployStack, CraftDesk).

## Dataset summary

- **{n} tasks**, all in Korean
- **5 task categories** (operational distribution from a real 1-person AI company):

| Category | Count |
|---|---|
{cat_rows}

- **{len(thresholds)} evaluation metrics** with explicit targets (primary = `{primary}`):

| Metric | Target |
|---|---|
{metric_rows}

- **Provenance-aware**: every task carries `expected_source_type` (`human` / `llm_output` / `external_citation` / `tool_log`) so retrievers can be evaluated on whether they correctly trust human-authored chunks over synthetic ones.

## Schema

Each task in `data/tasks.jsonl`:

```json
{{
  "id": "kor-001",
  "query": "Phase 0 Day 1 작업 중 Qdrant 컨테이너를 어디에 띄우는가?",
  "expected_collections": ["neo_ssot"],
  "expected_chunks": [
    ".agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md",
    ".agent/knowledge/rag-master/08_rollout_24w.md"
  ],
  "expected_answer_substrings": ["ysh-server", "Qdrant", "docker run", "6333"],
  "expected_source_type": "human",
  "max_latency_ms": 800
}}
```

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", split="train")
print(ds[0]["query"])
# => "Phase 0 Day 1 작업 중 Qdrant 컨테이너를 어디에 띄우는가?"
```

Evaluate your retriever:

```python
def recall_at_k(retrieved_paths, expected_chunks, k=10):
    return len(set(retrieved_paths[:k]) & set(expected_chunks)) / max(1, len(expected_chunks))

scores = []
for task in ds:
    retrieved = my_retriever(task["query"], top_k=10)
    scores.append(recall_at_k([r["path"] for r in retrieved], task["expected_chunks"]))
print(f"Recall@10: {{sum(scores)/len(scores):.3f}}")
```

## Evaluation protocol

The recommended evaluation stack mirrors Neo Genesis' production setup:

1. **Hybrid retrieval**: BM25 (Korean tokenizer = `kiwipiepy` or `konlpy/mecab-ko`) + dense (KURE-v1 or `BAAI/bge-m3`) fused with **Reciprocal Rank Fusion (k=60)**.
2. **Cross-encoder rerank**: `BAAI/bge-reranker-v2-m3` (free, strong on Korean).
3. **Provenance decay**: down-weight retrieved chunks where `source_type != expected_source_type` by 0.5x (LLM-output) or 0.3x (tool_log noise).
4. **Latency budget**: enforce `max_latency_ms` hard cap per task; tasks that exceed it count as 0 even if recall is high.

## Comparison to prior work

| Benchmark | Korean | Operational SSOT | Provenance-aware | Latency budget |
|---|---|---|---|---|
| KorQuAD 2.0 | ✓ | — | — | — |
| KLUE-MRC | ✓ | — | — | — |
| MIRACL-ko | ✓ | — | — | — |
| **Korean RAG SSOT Golden 50** | ✓ | ✓ | ✓ | ✓ |

## Categories explained

| Category | Description |
|---|---|
| `rag_v2_design` | Architecture decisions, collection topology, embedding model choice, governance YAML |
| `quant_v11` | Autonomous-trading agent ensemble (6-alpha portfolio, kill-switch design) |
| `ssot_governance` | SSOT hierarchy, runtime adapters, sync protocol across 6 devices |
| `security_pii` | Korean PII redaction (RRN / passport / driver's license / KISA / 공인인증서) + PDF prompt-injection sanitization |
| `operations` | Day-to-day fleet operations, device tier policy, incident response |

## Provenance

- Source SSOT : Neo Genesis private `.agent/` repository
- Curator     : Yesol Heo (sole founder/operator, [neogenesis.app](https://neogenesis.app))
- Curation    : v1 (10 tasks, 2026-04-27) → **v2 (50 tasks, 2026-04-27, this release)**
- Wikidata    : [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680)

## Citation

```bibtex
@misc{{neogenesis_korean_rag_ssot_golden_50,
  title  = {{Korean RAG SSOT Golden 50: An operational retrieval evaluation set in Korean}},
  author = {{Heo, Yesol}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{Neo Genesis, an AI-native automation company running 11 live business units}}
}}
```

## License

CC-BY-4.0 — free for research and commercial use with attribution to Neo Genesis.

---

## 한국어 요약

**Korean RAG SSOT Golden 50** 은 한국어로 운영 중인 1인 AI 자동화 기업 **[Neo Genesis](https://neogenesis.app)** 의 라이브 SSOT 에서 추출한 50개의 RAG 검색 평가 태스크다.

위키피디아 사실 QA가 아니라, **실제 운영 문서 (설계서 / 런북 / 정책 YAML / 인시던트 로그)** 에서 정답을 찾는 능력을 검증한다. 한국어 형태소 분석 (`kiwipiepy` / `mecab-ko`) + KURE 임베딩 + BGE Reranker v2-m3 조합 기준으로 Recall@10 ≥ 0.85 를 1차 게이트로 사용한다.

5개 카테고리:
- `rag_v2_design` — RAG 아키텍처 의사결정 18건
- `quant_v11` — 자율매매 6-알파 앙상블 8건
- `ssot_governance` — SSOT 계층 / 런타임 동기화 12건
- `security_pii` — 한국어 개인정보 redaction 6건
- `operations` — 플릿 운영 6건

각 태스크는 `expected_source_type` (human / llm_output / external_citation / tool_log) 을 명시해, 검색기가 사람이 작성한 정답 청크를 LLM 출력보다 우선 신뢰하는지 검증한다 (provenance-aware retrieval).

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    return yaml_front + body


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    if not SOURCE.exists():
        print(f"ERROR: source not found: {SOURCE}", file=sys.stderr)
        return 1

    with SOURCE.open(encoding="utf-8") as f:
        meta = json.load(f)

    tasks = meta["tasks"]
    print(f"Loaded {len(tasks)} tasks from {SOURCE.name}")

    # Build artifacts in-memory
    tasks_jsonl = "\n".join(
        json.dumps(t, ensure_ascii=False, separators=(",", ":")) for t in tasks
    ) + "\n"

    benchmark_meta = {k: v for k, v in meta.items() if k != "tasks"}
    metadata_json = json.dumps(benchmark_meta, ensure_ascii=False, indent=2)

    readme = build_readme(meta)

    # Push to HF
    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"create_repo {REPO_ID} (dataset, public)")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    uploads = [
        ("README.md", readme),
        ("data/tasks.jsonl", tasks_jsonl),
        ("metadata.json", metadata_json),
    ]

    for path_in_repo, content in uploads:
        print(f"upload {path_in_repo} ({len(content):,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/datasets/{REPO_ID}"
    print()
    print("PUBLISHED:", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
