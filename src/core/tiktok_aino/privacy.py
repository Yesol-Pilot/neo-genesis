"""Privacy mode helpers for TikTok AiNo media generation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

LOCAL_ONLY = "local_only"
CLOUD_EXPLICIT = "cloud_explicit"

_LOCAL_ONLY_ALIASES = {"local", "local-only", "local_only", "offline", "private"}
_CLOUD_EXPLICIT_ALIASES = {"cloud", "cloud-explicit", "cloud_explicit", "external"}


def normalize_mode(value: str | None) -> str:
    normalized = (value or "").strip().strip('"').strip("'").lower()
    if normalized in _CLOUD_EXPLICIT_ALIASES:
        return CLOUD_EXPLICIT
    if normalized in _LOCAL_ONLY_ALIASES:
        return LOCAL_ONLY
    return LOCAL_ONLY


def current_mode(env: Mapping[str, str] | None = None) -> str:
    source = env or os.environ
    return normalize_mode(source.get("AINO_PRIVACY_MODE"))


def is_local_only(mode: str | None = None, env: Mapping[str, str] | None = None) -> bool:
    if mode is not None:
        return normalize_mode(mode) == LOCAL_ONLY
    return current_mode(env) == LOCAL_ONLY


def cloud_generation_allowed(mode: str | None = None, env: Mapping[str, str] | None = None) -> bool:
    return not is_local_only(mode=mode, env=env)


def assert_cloud_generation_allowed(provider: str, *, mode: str | None = None) -> None:
    if cloud_generation_allowed(mode=mode):
        return
    raise RuntimeError(
        f"{provider} cloud generation blocked by AINO_PRIVACY_MODE=local_only; "
        "set AINO_PRIVACY_MODE=cloud_explicit only when provider-side records are acceptable."
    )


def manifest_record(mode: str | None = None) -> dict[str, Any]:
    effective_mode = normalize_mode(mode) if mode is not None else current_mode()
    local_only = effective_mode == LOCAL_ONLY
    return {
        "mode": effective_mode,
        "local_artifacts_only": local_only,
        "cloud_generation_allowed": not local_only,
        "policy": (
            "No external image, voice, or video generation providers may be called in local_only mode. "
            "Generated artifacts, manifests, QA files, and reports stay on the local filesystem."
            if local_only
            else "Cloud generation is explicitly allowed for this run; provider-side request, billing, abuse, or service logs may exist."
        ),
    }
