# -*- coding: utf-8 -*-
"""메모리/RAG/그래프 관련 도구 — Phase 1-1 모듈화"""
import json
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MEMORY_DIR = PROJECT_ROOT / "src" / "core" / "data" / "assistant_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("neo.jarvis")

# AssistantMemory 싱글턴
# Brain Worker(별도 프로세스)에서도 독립 초기화 가능하도록 직접 생성
_memory = None

def _get_memory():
    global _memory
    if _memory is None:
        try:
            # 봇 프로세스: 공유 싱글턴 우선 사용
            from src.core.neo_assistant_bot import _memory as bot_memory
            if bot_memory is not None:
                _memory = bot_memory
                return _memory
        except Exception:
            pass
        # Brain Worker 프로세스: 독립 초기화
        try:
            from src.core.sora_engine import AssistantMemory
            _memory = AssistantMemory(MEMORY_DIR)
        except Exception:
            from src.core.memory.assistant_memory import AssistantMemory
            _memory = AssistantMemory(MEMORY_DIR)
    return _memory


def save_to_memory(category: str, content: str) -> str:
    """중요한 정보를 장기 기억에 저장합니다.

    Args:
        category: 카테고리 (fact, preference, todo, note)
        content: 저장할 내용
    """
    _get_memory().add_fact(f"[{category}] {content}", source="user_instruction")
    return json.dumps({"status": "saved", "content": content[:100]})


def recall_from_memory(query: str) -> str:
    """장기 기억에서 관련 정보를 검색합니다.

    Args:
        query: 검색 키워드
    """
    results = _get_memory().search_facts(query)
    if not results:
        return json.dumps({"results": [], "message": "관련 기억 없음"})
    return json.dumps({
        "results": [{"fact": r["fact"], "ts": r["ts"]} for r in results[-10:]],
    }, ensure_ascii=False)


def graph_add_knowledge(subject: str, relation: str, obj: str,
                         subject_type: str = "concept",
                         object_type: str = "concept") -> str:
    """지식 그래프에 관계를 추가합니다. (주어 --[관계]--> 목적어)

    Args:
        subject: 주어 (예: 허예솔, 소라, NEO GENESIS)
        relation: 관계 (예: manages, owns, prefers, uses, created)
        obj: 목적어 (예: UR WRONG, 커피, Python)
        subject_type: 주어 유형 (person, project, ai_agent, concept, tool)
        object_type: 목적어 유형
    """
    try:
        from src.core.memory.graph_memory import get_graph
        g = get_graph()
        rel = g.add_relation(subject, relation, obj, subject_type, object_type)
        stats = g.get_stats()
        return json.dumps({
            "status": "added",
            "triple": f"{subject} --[{relation}]--> {obj}",
            "graph_stats": stats,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def graph_search(query: str, mode: str = "entity") -> str:
    """지식 그래프를 검색합니다.

    Args:
        query: 검색 키워드
        mode: 검색 모드 — entity(엔티티 검색), neighbor(관계 탐색), timeline(변경 이력)
    """
    try:
        from src.core.memory.graph_memory import get_graph
        g = get_graph()

        if mode == "neighbor":
            result = g.get_neighbors(query)
        elif mode == "timeline":
            result = {"entity": query, "timeline": g.get_timeline(query)}
        else:
            entities = g.search_entities(query)
            result = {
                "query": query,
                "matched": len(entities),
                "entities": [
                    {"name": e.name, "type": e.entity_type,
                     "attributes": e.attributes, "valid_at": e.valid_at}
                    for e in entities
                ],
            }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def graph_status() -> str:
    """지식 그래프의 현재 상태(엔티티, 관계, 에피소드 수)를 반환합니다."""
    try:
        from src.core.memory.graph_memory import get_graph
        g = get_graph()
        return json.dumps(g.get_stats(), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def rag_index(directory: str, incremental: bool = True) -> str:
    """PC 디렉토리를 인덱싱합니다.
    크롤링 → 파싱 → 청킹 → 벡터 저장.
    증분 모드에서는 변경된 파일만 처리합니다.

    Args:
        directory: 인덱싱할 디렉토리 경로
        incremental: 증분 인덱싱 여부 (기본 True)
    """
    try:
        from src.core.rag_engine import get_rag_engine
        engine = get_rag_engine()
        result = engine.index_directory(directory, incremental=incremental)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def rag_search(query: str, n_results: int = 5,
               file_filter: str = "",
               backend: str = "") -> str:
    """저장된 지식에서 시맨틱 검색합니다.
    자연어 질문 → 관련 코드/문서 검색.

    Args:
        query: 검색할 질문
        n_results: 반환할 결과 수 (기본 5)
        file_filter: 파일 확장자 필터 (예: ".py")
        backend: 'chroma' | 'qdrant' | '' (기본: env RAG_BACKEND or chroma).
                 'qdrant' 이면 RAG v2 분산 인프라 (ysh-server:6333) 사용.
    """
    try:
        from src.core.rag_engine import get_rag_engine
        import os as _os
        engine = get_rag_engine()
        filt = file_filter if file_filter else None
        # backend 우선순위: 명시 > env(RAG_BACKEND) > engine default(chroma)
        b = (backend or _os.environ.get("RAG_BACKEND", "")).lower() or None
        results = engine.search(query, n_results=n_results, file_filter=filt, backend=b)
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def rag_status() -> str:
    """RAG 인덱스 상태를 확인합니다.
    총 문서 수, 인덱싱된 파일 수, 임베딩 모델 등.
    """
    try:
        from src.core.rag_engine import get_rag_engine
        engine = get_rag_engine()
        return json.dumps(engine.get_status(), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


TOOLS = [
    save_to_memory,
    recall_from_memory,
    graph_add_knowledge,
    graph_search,
    graph_status,
    rag_index,
    rag_search,
    rag_status,
]
