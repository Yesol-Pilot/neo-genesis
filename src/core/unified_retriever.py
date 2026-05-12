# -*- coding: utf-8 -*-
"""
소라(Sora) 통합 검색 파사드 — Phase 1-2

그래프 메모리 + RAG + KI + 키워드 메모리를 단일 인터페이스로 통합합니다.
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("neo.jarvis")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class RetrievalChunk:
    """검색 결과 단위"""
    content: str
    source: str        # "graph" | "rag" | "ki" | "memory"
    score: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """통합 검색 결과"""
    chunks: list[RetrievalChunk] = field(default_factory=list)
    user_profile: str = ""
    query: str = ""

    def as_text(self, max_chars: int = 3000) -> str:
        """프롬프트 주입용 텍스트로 변환"""
        lines = []
        total = 0
        for c in self.chunks:
            line = f"[{c.source}] {c.content}"
            if total + len(line) > max_chars:
                break
            lines.append(line)
            total += len(line)
        return "\n".join(lines)


class UnifiedRetriever:
    """그래프 + RAG + KI + 키워드 메모리를 단일 인터페이스로 통합"""

    def __init__(self):
        self._graph = None
        self._rag = None
        self._memory = None

    def _lazy_graph(self):
        if self._graph is None:
            try:
                from src.core.memory.graph_memory import get_graph
                self._graph = get_graph()
            except Exception as e:
                logger.warning(f"[UnifiedRetriever] GraphMemory 로드 실패: {e}")
        return self._graph

    def _lazy_rag(self):
        if self._rag is None:
            try:
                from src.core.rag_engine import get_rag_engine
                self._rag = get_rag_engine()
            except Exception as e:
                logger.warning(f"[UnifiedRetriever] RAGEngine 로드 실패: {e}")
        return self._rag

    def _lazy_memory(self):
        if self._memory is None:
            try:
                from src.core.neo_assistant_bot import _memory
                self._memory = _memory
            except Exception as e:
                logger.warning(f"[UnifiedRetriever] Memory 로드 실패: {e}")
        return self._memory

    # ── 검색 API ──

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """모든 소스에서 검색 → 점수 융합 → 중복 제거"""
        chunks: list[RetrievalChunk] = []

        # 1. 그래프 메모리 (엔티티 + 이웃)
        chunks.extend(self._search_graph(query))

        # 2. RAG 시맨틱 검색
        chunks.extend(self._search_rag(query, top_k))

        # 3. 키워드 메모리 (학습된 사실)
        chunks.extend(self._search_memory(query))

        # 중복 제거 + 점수 내림차순 정렬
        seen = set()
        unique = []
        for c in sorted(chunks, key=lambda x: x.score, reverse=True):
            key = c.content[:100]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return RetrievalResult(
            chunks=unique[:top_k],
            query=query,
        )

    def get_user_profile(self) -> str:
        """허예솔 엔티티 중심 1홉 그래프 → 자연어 프로필.

        2026-05-12 P0: 'str' object has no attribute 'get' 영구 fix.
        graph.get_neighbors() 가 dict/list/str 다양한 형태 반환 가능 → isinstance 가드.
        """
        g = self._lazy_graph()
        if not g:
            return ""
        try:
            neighbors = g.get_neighbors("허예솔", depth=1)
            if not neighbors:
                return ""
            if not isinstance(neighbors, dict):
                logger.debug(
                    "[UnifiedRetriever] neighbors not dict (type=%s) — skip",
                    type(neighbors).__name__,
                )
                return ""

            lines = []
            relations = neighbors.get("relations", [])
            if isinstance(relations, list):
                for rel in relations:
                    if not isinstance(rel, dict):
                        continue
                    src = rel.get("source", "")
                    tgt = rel.get("target", "")
                    rtype = rel.get("relation", "")
                    lines.append(f"- {src} → {rtype} → {tgt}")

            entity = neighbors.get("entity", {})
            if isinstance(entity, dict):
                attrs = entity.get("attributes", {})
                if isinstance(attrs, dict):
                    for k, v in attrs.items():
                        lines.append(f"- {k}: {v}")

            return "\n".join(lines)
        except Exception as e:
            logger.debug(f"[UnifiedRetriever] 프로필 로드 graceful skip: {e}")
            return ""

    def get_system_context(self) -> dict:
        """환경변수 + 헬스 + PC 정보 → 구조화 딕셔너리"""
        ctx = {}

        # 환경변수 상태
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            env_status = {}
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_status[key] = "✅" if val.strip() else "❌"
            ctx["env"] = env_status

        # 헬스 상태
        hf = PROJECT_ROOT / "src" / "core" / "data" / "health_state.json"
        if hf.exists():
            try:
                ctx["health"] = json.loads(hf.read_text(encoding="utf-8"))
            except Exception:
                pass

        return ctx

    # ── 내부 검색 메서드 ──

    def _search_graph(self, query: str) -> list[RetrievalChunk]:
        g = self._lazy_graph()
        if not g:
            return []
        try:
            entities = g.search_entities(query, top_k=3)
            chunks = []
            for e in entities:
                content = f"{e.name} ({e.entity_type})"
                if e.attributes:
                    content += " — " + ", ".join(f"{k}: {v}" for k, v in e.attributes.items())
                chunks.append(RetrievalChunk(
                    content=content,
                    source="graph",
                    score=0.8,
                    metadata={"entity_id": e.id},
                ))
            return chunks
        except Exception:
            return []

    def _search_rag(self, query: str, top_k: int) -> list[RetrievalChunk]:
        rag = self._lazy_rag()
        if not rag:
            return []
        try:
            results = rag.search(query, n_results=top_k)
            chunks = []
            if isinstance(results, dict):
                for doc in results.get("results", []):
                    chunks.append(RetrievalChunk(
                        content=doc.get("content", "")[:500],
                        source="rag",
                        score=doc.get("score", 0.5),
                        metadata={"file": doc.get("file", "")},
                    ))
            return chunks
        except Exception:
            return []

    def _search_memory(self, query: str) -> list[RetrievalChunk]:
        mem = self._lazy_memory()
        if not mem:
            return []
        try:
            results = mem.search_facts(query)
            chunks = []
            for r in results[-5:]:
                chunks.append(RetrievalChunk(
                    content=r.get("fact", "") if isinstance(r, dict) else str(r),
                    source="memory",
                    score=0.6,
                ))
            return chunks
        except Exception:
            return []


# ── 싱글턴 ──

_retriever: Optional[UnifiedRetriever] = None

def get_unified_retriever() -> UnifiedRetriever:
    global _retriever
    if _retriever is None:
        _retriever = UnifiedRetriever()
    return _retriever
