"""scripts/rag_v2/rerank_service.py
sol01 Cross-encoder Reranker — BGE Reranker v2-m3 (자체 호스팅, 한국어 강).

부록: .agent/knowledge/rag-master/02_architecture.md §Embedding Plane
실행:
    python scripts/rag_v2/rerank_service.py --port 7704

의존성:
    pip install fastapi uvicorn FlagEmbedding torch
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import asynccontextmanager

logger = logging.getLogger("rag_v2.rerank")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")


_reranker = None


def _get_reranker():
    """BGE Reranker v2-m3 lazy load (~2GB VRAM)."""
    global _reranker
    if _reranker is None:
        try:
            from FlagEmbedding import FlagReranker  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "FlagEmbedding 필요: pip install FlagEmbedding torch"
            ) from e
        logger.info("BGE Reranker v2-m3 로드 시작 (~2GB VRAM)")
        _reranker = FlagReranker(
            "BAAI/bge-reranker-v2-m3",
            use_fp16=True,
            cache_dir=os.environ.get("HF_HOME"),
        )
        logger.info("BGE Reranker v2-m3 로드 완료")
    return _reranker


@asynccontextmanager
async def lifespan(app):
    logger.info("Reranker service startup")
    _ = _get_reranker()
    yield
    logger.info("Reranker service shutdown")


def create_app():
    from fastapi import Body, FastAPI, HTTPException  # type: ignore
    from pydantic import BaseModel  # type: ignore

    app = FastAPI(title="Neo Genesis RAG v2 Reranker (sol01 BGE-v2-m3)", lifespan=lifespan)


    @app.get("/health")
    def health():
        return {"status": "ok", "loaded": _reranker is not None}

    @app.post("/rerank")
    def rerank(req: dict = Body(...)):
        query = req.get("query", "")
        candidates = req.get("candidates") or []
        top_k = int(req.get("top_k", 10))
        normalize = bool(req.get("normalize", True))
        if not query or not candidates:
            raise HTTPException(400, "empty query or candidates")
        if top_k <= 0:
            raise HTTPException(400, "top_k must be > 0")

        reranker = _get_reranker()
        pairs = [[query, c] for c in candidates]
        scores = reranker.compute_score(pairs, normalize=normalize)

        # numpy / list 모두 처리
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        if not isinstance(scores, list):
            scores = [float(scores)]

        # 정렬
        indexed = sorted(
            enumerate(scores),
            key=lambda x: -x[1],
        )[:top_k]

        return {
            "ranked_indices": [i for i, _ in indexed],
            "scores": [s for _, s in indexed],
            "model": "bge-reranker-v2-m3",
        }

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7704)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import uvicorn  # type: ignore
    except ImportError:
        logger.error("pip install fastapi uvicorn FlagEmbedding torch")
        return 2

    uvicorn.run(
        "scripts.rag_v2.rerank_service:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
