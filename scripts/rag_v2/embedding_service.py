"""scripts/rag_v2/embedding_service.py
sol01 GPU 임베딩 서비스 — KURE-v1 (한국어) 상시 상주 + ColQwen2-2B INT4 fallback.

부록: .agent/knowledge/rag-master/02_architecture.md §Embedding Plane
실행:
    # sol01 (Windows)
    set NEO_RAG_GPU_GUARD=4096   # MB 여유 임계
    python scripts/rag_v2/embedding_service.py --port 7702

의존성:
    pip install fastapi uvicorn sentence-transformers torch
    pip install pynvml          # GPU VRAM 모니터링 (Windows + NVIDIA)
    # ColQwen2 fallback은 별도 cli에서 가져와 lazy load
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger("rag_v2.embedding")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")


# ==========================
# Lazy global state
# ==========================
_kure_model = None
_colqwen_model = None
_lock_path = None


def _get_kure():
    """KURE-v1 lazy load (BGE-M3 base, 한국어 retrieval)."""
    global _kure_model
    if _kure_model is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        logger.info("KURE-v1 로드 시작 (~2.4GB VRAM)")
        _kure_model = SentenceTransformer(
            "nlpai-lab/KURE-v1",
            device="cuda" if _has_cuda() else "cpu",
        )
        logger.info("KURE-v1 로드 완료. device=%s", _kure_model.device)
    return _kure_model


def _get_colqwen2_int4():
    """ColQwen2-2B INT4 fallback (mac-studio offline 시)."""
    global _colqwen_model
    if _colqwen_model is None:
        try:
            # ColQwen2 INT4 quant은 별도 weight 필요. 스캐폴드만.
            logger.warning(
                "ColQwen2-2B INT4 로드는 스캐폴드 단계 — Phase 4에서 실제 구현. "
                "현재는 mac-studio MLX(:7703)로 라우팅 권장."
            )
            return None
        except Exception as e:
            logger.error("ColQwen2-2B 로드 실패: %s", e)
            return None
    return _colqwen_model


def _has_cuda() -> bool:
    try:
        import torch  # type: ignore
        return torch.cuda.is_available()
    except ImportError:
        return False


def _gpu_free_mb() -> int:
    """sol01 GPU free VRAM (MB). pynvml 미설치 시 -1 반환 (체크 비활성)."""
    try:
        from pynvml import (  # type: ignore
            nvmlInit, nvmlDeviceGetHandleByIndex,
            nvmlDeviceGetMemoryInfo, nvmlShutdown,
        )
        nvmlInit()
        h = nvmlDeviceGetHandleByIndex(0)
        info = nvmlDeviceGetMemoryInfo(h)
        nvmlShutdown()
        return info.free // (1024 * 1024)
    except Exception:
        return -1


def _gpu_guard_ok(min_mb: int) -> bool:
    free = _gpu_free_mb()
    if free < 0:
        return True  # pynvml 없으면 통과 (sol01 외 환경)
    return free >= min_mb


@asynccontextmanager
async def lifespan(app):
    """Startup: KURE 즉시 로드 (상시 상주)."""
    logger.info("Embedding service startup")
    if _has_cuda():
        logger.info("CUDA 사용 가능. GPU free VRAM: %d MB", _gpu_free_mb())
    else:
        logger.warning("CUDA 미사용 — CPU 추론으로 fallback (느림 ~5x).")
    _ = _get_kure()
    yield
    logger.info("Embedding service shutdown")


def create_app():
    from fastapi import FastAPI, HTTPException  # type: ignore
    from pydantic import BaseModel  # type: ignore
    from fastapi import Body  # type: ignore

    app = FastAPI(title="Neo Genesis RAG v2 Embedding (sol01)", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "cuda": _has_cuda(),
            "gpu_free_mb": _gpu_free_mb(),
            "kure_loaded": _kure_model is not None,
            "colqwen_loaded": _colqwen_model is not None,
        }

    @app.post("/embed")
    def embed(req: dict = Body(...)):
        texts = req.get("texts") or []
        model_name = req.get("model", "kure-v1")
        if not texts or not isinstance(texts, list):
            raise HTTPException(400, "empty or invalid 'texts' list")

        gpu_min = int(os.environ.get("NEO_RAG_GPU_GUARD", "4096"))

        if model_name == "kure-v1":
            if not _gpu_guard_ok(gpu_min):
                raise HTTPException(
                    503,
                    f"GPU guard: free VRAM < {gpu_min}MB. ComfyUI 활성 가능. ysh-server CPU fallback 사용 권장.",
                )
            model = _get_kure()
            embs = model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return {
                "embeddings": embs.tolist(),
                "model": "kure-v1",
                "dim": len(embs[0]) if len(embs) else 0,
                "device": str(model.device),
            }

        if model_name == "colqwen2-2b-int4":
            model = _get_colqwen2_int4()
            if model is None:
                raise HTTPException(
                    503,
                    "ColQwen2-2B INT4 미구현 (Phase 4). mac-studio MLX(:7703)로 라우팅 권장.",
                )
            raise HTTPException(501, "ColQwen2 fallback Phase 4 도입 예정")

        raise HTTPException(400, f"unknown model: {model_name}")

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7702)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import uvicorn  # type: ignore
    except ImportError:
        logger.error("pip install fastapi uvicorn sentence-transformers torch pynvml")
        return 2

    uvicorn.run(
        "scripts.rag_v2.embedding_service:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
