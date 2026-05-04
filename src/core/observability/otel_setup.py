# -*- coding: utf-8 -*-
"""Sora Enterprise OpenTelemetry Setup — W2.T1 P0 starter.

Master: 20260428_SORA_ENTERPRISE_GRADE_MASTER_v1.md (W2)
Decisions: 20260428_SORA_ENTERPRISE_DECISIONS_v1.md (D6 자체 호스팅 + Loki/Tempo/Grafana, $0)

설계 원칙:
1. **Graceful degradation**: OTel SDK 미가용 시 no-op fallback (sora 본체 동작 영향 0)
2. **단일 trace_id**: 기존 `tracer.py` 의 contextvar trace_id 와 OTel trace context 매핑
3. **Sampling**: P0 starter 는 100% (Week 3 Tempo 가동 후 10% sampling 으로 조정)
4. **Critical path span**: process() / _route_to_X / _local_llm.chat / tool call / hook lifecycle
5. **Owner override**: `OTEL_DISABLED=1` env 로 즉시 비활성화 (CONSTITUTION Article 0)

Author: Claude Opus 4.7 (Sora Dev Lead) — 2026-04-28
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

logger = logging.getLogger("neo.observability.otel")

# ── OTel SDK lazy import (graceful degradation) ────────────────────
_OTEL_AVAILABLE = False
_otel_trace = None
_otel_TracerProvider = None
_otel_BatchSpanProcessor = None
_otel_ConsoleSpanExporter = None
_otel_Resource = None
_otel_SERVICE_NAME = None

try:
    from opentelemetry import trace as _otel_trace  # type: ignore
    from opentelemetry.sdk.resources import Resource as _otel_Resource  # type: ignore
    from opentelemetry.sdk.resources import SERVICE_NAME as _otel_SERVICE_NAME  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider as _otel_TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import (  # type: ignore
        BatchSpanProcessor as _otel_BatchSpanProcessor,
        ConsoleSpanExporter as _otel_ConsoleSpanExporter,
    )

    _OTEL_AVAILABLE = True
    logger.info("[otel] SDK available")
except ImportError as exc:
    logger.warning("[otel] SDK unavailable, using no-op fallback: %s", exc)


# ── Configuration ─────────────────────────────────────────────────
def _is_disabled() -> bool:
    """Owner override 또는 env 로 OTel 비활성화."""
    return os.getenv("OTEL_DISABLED", "").lower() in ("1", "true", "yes")


def _service_name() -> str:
    return os.getenv("OTEL_SERVICE_NAME", "sora-engine")


def _otlp_endpoint() -> Optional[str]:
    """OTLP collector endpoint (Tempo). W2.T5 통합.

    1. OTEL_EXPORTER_OTLP_ENDPOINT env 우선
    2. fallback: docker bridge gateway 172.17.0.1:4317 자동 시도 (host 의 Tempo 도달)
    3. 어느 것도 reachable 안 하면 ConsoleSpanExporter 만 사용
    """
    env_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if env_endpoint:
        return env_endpoint
    # Auto-discover: docker bridge gateway 의 Tempo 도달 시도 (1초 timeout)
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        result = s.connect_ex(("172.17.0.1", 4317))
        s.close()
        if result == 0:
            logger.info("[otel] auto-discovered OTLP endpoint: http://172.17.0.1:4317")
            return "http://172.17.0.1:4317"
    except Exception:
        pass
    return None


def _sampling_rate() -> float:
    """Sampling rate 0.0~1.0. P0 starter = 1.0, Tempo 가동 후 0.1 권장."""
    try:
        return float(os.getenv("OTEL_SAMPLING_RATE", "1.0"))
    except ValueError:
        return 1.0


# ── Initialization ────────────────────────────────────────────────
_initialized = False
_tracer = None


def init_tracer() -> Any:
    """OTel TracerProvider 초기화. 1회만 실행.

    Returns:
        Tracer instance (OTel 사용) 또는 NoopTracer (fallback)
    """
    global _initialized, _tracer
    if _initialized:
        return _tracer

    if _is_disabled():
        logger.info("[otel] disabled by env, using no-op tracer")
        _tracer = _NoopTracer()
        _initialized = True
        return _tracer

    if not _OTEL_AVAILABLE:
        logger.warning("[otel] SDK unavailable, using no-op tracer")
        _tracer = _NoopTracer()
        _initialized = True
        return _tracer

    try:
        # Resource 정의 (service name)
        resource = _otel_Resource.create({
            _otel_SERVICE_NAME: _service_name(),
            "service.version": os.getenv("SORA_VERSION", "v5.19"),
            "deployment.environment": os.getenv("DEPLOY_ENV", "production"),
        })

        # TracerProvider 등록
        provider = _otel_TracerProvider(resource=resource)

        # OTLP exporter (Week 3+ Tempo 가동 시)
        # 2026-04-29: ConsoleSpanExporter 가 brain.log 를 모든 span 으로 오염시키던 문제 fix.
        # OTLP 우선 시도 → 가용 시 Console 비활성 / 미가용 시만 fallback 으로 Console.
        otlp = _otlp_endpoint()
        otlp_enabled = False
        if otlp:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
                    OTLPSpanExporter,
                )
                provider.add_span_processor(
                    _otel_BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp))
                )
                logger.info("[otel] OTLP exporter enabled: %s", otlp)
                otlp_enabled = True
            except ImportError:
                logger.warning("[otel] OTLP exporter package not installed, using Console fallback")

        # Console exporter — OTLP 미가용 시만, 또는 OTEL_CONSOLE_EXPORTER=1 강제 시.
        force_console = os.getenv("OTEL_CONSOLE_EXPORTER", "").lower() in ("1", "true", "yes")
        if not otlp_enabled or force_console:
            provider.add_span_processor(
                _otel_BatchSpanProcessor(_otel_ConsoleSpanExporter())
            )
            logger.info("[otel] Console exporter enabled (otlp_enabled=%s, force=%s)", otlp_enabled, force_console)
        else:
            logger.info("[otel] Console exporter disabled (OTLP exporter is primary)")

        _otel_trace.set_tracer_provider(provider)
        _tracer = _otel_trace.get_tracer(_service_name())
        logger.info("[otel] tracer initialized: service=%s sampling=%s", _service_name(), _sampling_rate())
    except Exception as exc:
        logger.exception("[otel] init failed, using no-op fallback: %s", exc)
        _tracer = _NoopTracer()

    _initialized = True
    return _tracer


def get_tracer() -> Any:
    """Tracer 반환 (lazy init)."""
    if not _initialized:
        init_tracer()
    return _tracer


# ── No-op fallback ────────────────────────────────────────────────
class _NoopSpan:
    """OTel 미가용 시 no-op span."""

    def __init__(self, name: str):
        self.name = name

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any, description: Optional[str] = None) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _NoopTracer:
    """OTel 미가용 시 no-op tracer."""

    def start_as_current_span(self, name: str, **kwargs) -> _NoopSpan:
        return _NoopSpan(name)

    def start_span(self, name: str, **kwargs) -> _NoopSpan:
        return _NoopSpan(name)


# ── Convenience: span context manager ─────────────────────────────
@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """`with span("op_name", k=v): ...` 스타일 헬퍼.

    OTel 가용 시 실제 span, 아니면 no-op. Critical path 의 추적 비용 0 보장.

    Example:
        with span("sora.process", user_id="yesol", source="telegram"):
            result = await engine.process(text)
    """
    tracer = get_tracer()
    sp = tracer.start_as_current_span(name)
    if hasattr(sp, "__enter__"):
        with sp as active:
            for k, v in attributes.items():
                try:
                    active.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
                except Exception:
                    pass
            try:
                yield active
            except Exception as exc:
                try:
                    active.record_exception(exc)
                except Exception:
                    pass
                raise
    else:
        # no-op tracer
        yield _NoopSpan(name)


# ── Trace ID 통합 (기존 tracer.py 의 contextvar 와 매핑) ────────────
def get_current_trace_id() -> str:
    """현재 활성 OTel span 의 trace_id (16자 hex). OTel 미가용 시 빈 문자열."""
    if not _OTEL_AVAILABLE or _tracer is None or isinstance(_tracer, _NoopTracer):
        return ""
    try:
        span_ctx = _otel_trace.get_current_span().get_span_context()
        if span_ctx.is_valid:
            return format(span_ctx.trace_id, "016x")[:16]
    except Exception:
        pass
    return ""


# ── Smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(f"OTel available: {_OTEL_AVAILABLE}")
    print(f"OTel disabled: {_is_disabled()}")
    print(f"Service name: {_service_name()}")
    print(f"Sampling rate: {_sampling_rate()}")

    tracer = init_tracer()
    print(f"Tracer type: {type(tracer).__name__}")

    with span("sora.smoke_test", test_id=42, source="otel_setup_main") as sp:
        print(f"Active span trace_id: {get_current_trace_id()}")
        with span("sora.smoke_test.child", child_idx=1):
            print("inside child span")

    print("OK")
