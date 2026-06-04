"""Neo Genesis Ontology v0.5 -- LangChain text-to-Cypher QA chain.

Per RESEARCH §10 + DESIGN §14 (v0.4 RAG 결합). LangChain `GraphCypherQAChain`
+ AuraDB Bolt 통합. 자연어 query → Cypher 생성 → AuraDB 실행 → Korean 답변.

LLM 선택 (env var `NEO_LLM_PROVIDER`):
- `anthropic` (default): claude-3-5-sonnet via langchain-anthropic + ANTHROPIC_API_KEY
- `openai`: gpt-4o via langchain-openai + OPENAI_API_KEY
- `ollama`: local llama via langchain-ollama (no API cost, 별도 ollama serve 필요)
- `mock`: 인증 우회 — chain 객체만 검증, 실 호출 안 함

CypherBench (Edge et al. 2024) 기준 Claude 3.5 Sonnet text-to-Cypher EX 61.58%
(SPARQL 3.3% 대비 18x). 향후 LLM 업그레이드 시 동일 인터페이스 유지.

Usage:
    # 환경변수
    export NEO4J_BOLT_URI=neo4j+s://...
    export NEO4J_USER=neo4j
    export NEO4J_PASSWORD=...
    export NEO_LLM_PROVIDER=mock  # 또는 anthropic / openai / ollama
    export ANTHROPIC_API_KEY=...  # if anthropic

    python scripts/ontology/langchain_qa.py --query "ysh-server 에 있는 모든 service 는?"
    python scripts/ontology/langchain_qa.py --schema  # 스키마만 print (Cypher prompt 검증)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_graph():
    """Connect to AuraDB / Neo4j via langchain_neo4j.Neo4jGraph."""
    try:
        from langchain_neo4j import Neo4jGraph
    except ImportError:
        print("[ERROR] pip install langchain-neo4j")
        sys.exit(2)

    bolt = os.environ.get("NEO4J_BOLT_URI") or os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"
    password = os.environ.get("NEO4J_PASSWORD")
    if not bolt or not password:
        print("[ERROR] NEO4J_BOLT_URI + NEO4J_PASSWORD env vars required")
        sys.exit(2)
    return Neo4jGraph(url=bolt, username=user, password=password)


def get_llm():
    """Instantiate LLM per NEO_LLM_PROVIDER env var."""
    provider = os.environ.get("NEO_LLM_PROVIDER", "mock").lower()

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            print("[ERROR] pip install langchain-anthropic")
            sys.exit(2)
        model = os.environ.get("NEO_LLM_MODEL", "claude-3-5-sonnet-20241022")
        return ChatAnthropic(model=model, temperature=0)

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            print("[ERROR] pip install langchain-openai")
            sys.exit(2)
        model = os.environ.get("NEO_LLM_MODEL", "gpt-4o")
        return ChatOpenAI(model=model, temperature=0)

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            print("[ERROR] pip install langchain-ollama")
            sys.exit(2)
        model = os.environ.get("NEO_LLM_MODEL", "qwen2.5-coder:14b")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model=model, base_url=base_url, temperature=0)

    if provider == "mock":
        # FakeListLLM — chain 객체 wiring 검증용
        try:
            from langchain_community.llms.fake import FakeListLLM
        except ImportError:
            try:
                from langchain_core.language_models.fake import FakeListLLM
            except ImportError:
                # Fallback: simple LLM stub
                from langchain_core.language_models.fake_chat_models import FakeListChatModel
                return FakeListChatModel(responses=[
                    "MATCH (s:Service)-[:DEPLOYED_TO]->(d:Device {hostname: 'ysh-server'}) RETURN s.name AS name, s.status AS status",
                    "ysh-server 에는 quant-bot-live, sora-live 등 8개 Service 가 있습니다.",
                ])
        return FakeListLLM(responses=[
            "MATCH (s:Service)-[:DEPLOYED_TO]->(d:Device {hostname: 'ysh-server'}) RETURN s.name, s.status",
            "Mock response: 8 services on ysh-server.",
        ])

    print(f"[ERROR] Unknown NEO_LLM_PROVIDER: {provider}")
    sys.exit(2)


def build_chain(graph, llm, verbose: bool = False):
    """Build GraphCypherQAChain with safety constraints."""
    try:
        from langchain_neo4j import GraphCypherQAChain
    except ImportError:
        print("[ERROR] pip install langchain-neo4j")
        sys.exit(2)

    return GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=verbose,
        return_intermediate_steps=True,
        # Markings enforcement: 본 PoC 는 graph-level (Cypher result 후 filter 미적용)
        # v0.5 P1 hook: post-process to drop personal-forbidden / restricted markings
        allow_dangerous_requests=True,  # PoC; v1.0 에서 read-only LLM 보장
    )


def print_schema(graph) -> None:
    """LLM 에 주입되는 schema 출력 — Cypher prompt quality 검증용."""
    print("=== Neo4j Graph Schema (LLM context) ===")
    print(graph.schema)
    print()


def query(graph, llm, question: str, verbose: bool = False) -> dict:
    """Run text-to-Cypher chain."""
    chain = build_chain(graph, llm, verbose=verbose)
    result = chain.invoke({"query": question})
    return {
        "question": question,
        "answer": result.get("result"),
        "cypher": (result.get("intermediate_steps") or [{}])[0].get("query"),
        "raw_cypher_result": (result.get("intermediate_steps") or [{}, {}])[1].get("context") if len(result.get("intermediate_steps", [])) > 1 else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="자연어 query")
    parser.add_argument("--schema", action="store_true", help="Print schema only")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--list-providers", action="store_true",
                        help="List available LLM providers")
    args = parser.parse_args()

    if args.list_providers:
        print(json.dumps({
            "providers": {
                "anthropic": "claude-3-5-sonnet (default model, EX 61.58% on CypherBench)",
                "openai": "gpt-4o",
                "ollama": "local llama / qwen (no API cost)",
                "mock": "FakeListLLM — chain wiring 검증용, 실 호출 없음",
            },
            "env_vars": ["NEO4J_BOLT_URI", "NEO4J_PASSWORD", "NEO_LLM_PROVIDER",
                         "NEO_LLM_MODEL (optional)", "ANTHROPIC_API_KEY / OPENAI_API_KEY"],
        }, indent=2, ensure_ascii=False))
        return 0

    graph = get_graph()

    if args.schema:
        print_schema(graph)
        return 0

    if not args.query:
        parser.print_help()
        return 1

    try:
        llm = get_llm()
        result = query(graph, llm, args.query, verbose=args.verbose)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)[:500], "type": type(e).__name__},
                         indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
