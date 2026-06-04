"""Deterministic image-generation provider routing.

This module only chooses a route. It performs no network calls and does not
read credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).with_name("image_generation_routing.json")
SENSITIVE_LEVELS = {"sensitive", "private", "legal", "finance", "credential", "personal", "adult"}


@dataclass(frozen=True)
class ImageRoutingRequest:
    purpose: str = "general"
    sensitivity: str = "public"
    output_kind: str = "image"
    allow_external_api: bool = True
    allow_gamma_ui: bool = False
    company_safe: bool = True
    needs_gamma_ui_hidden: bool = False
    needs_text_rendering: bool = False
    needs_vector: bool = False
    needs_photorealism: bool = False
    needs_high_quality: bool = False
    budget_tier: str = "standard"
    prefer_provider: str | None = None


@dataclass(frozen=True)
class ImageRoute:
    provider: str
    model: str | None
    external_api: bool
    ui_history: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    blocked_providers: tuple[str, ...] = field(default_factory=tuple)


def load_image_routing_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def route_image_generation(
    request: ImageRoutingRequest,
    config: dict[str, Any] | None = None,
) -> ImageRoute:
    cfg = config or load_image_routing_config()
    providers = cfg.get("providers", {})
    reasons: list[str] = []
    blocked: list[str] = []

    sensitivity = request.sensitivity.strip().lower() or "public"
    budget = request.budget_tier.strip().lower() or "standard"

    if not request.company_safe:
        blocked.append("gamma_api")
        return _route(providers, "local_comfyui", None, ["not_company_safe_routes_local", *reasons], blocked)

    if sensitivity in SENSITIVE_LEVELS:
        blocked.append("gamma_api")
        return _route(providers, "local_comfyui", None, ["sensitivity_routes_local", *reasons], blocked)

    if request.needs_gamma_ui_hidden:
        blocked.append("gamma_api")
        if request.allow_external_api:
            provider = "gemini_api" if request.needs_text_rendering else "codex_cli"
            return _route(providers, provider, None, ["gamma_ui_hidden", "non_gamma_external_allowed"], blocked)
        return _route(providers, "local_comfyui", None, ["gamma_ui_hidden", "external_api_disabled"], blocked)

    if not request.allow_external_api:
        blocked.extend(["gamma_api", "gemini_api", "codex_cli"])
        return _route(providers, "local_comfyui", None, ["external_api_disabled"], blocked)

    if request.prefer_provider and request.prefer_provider != "gamma_api":
        return _route(providers, request.prefer_provider, None, ["preferred_provider"], blocked)

    if request.allow_gamma_ui and request.output_kind in {"image", "card", "social"}:
        model_key = _select_gamma_model_key(request, budget)
        model_info = providers.get("gamma_api", {}).get("models", {}).get(model_key, {})
        return _route(
            providers,
            "gamma_api",
            str(model_info.get("model") or ""),
            ["gamma_ui_allowed", f"gamma_model_key:{model_key}"],
            blocked,
        )

    blocked.append("gamma_api")
    provider = "gemini_api" if request.needs_text_rendering else "codex_cli"
    return _route(providers, provider, None, ["gamma_ui_not_allowed", "direct_non_gamma_route"], blocked)


def _select_gamma_model_key(request: ImageRoutingRequest, budget: str) -> str:
    if request.needs_vector:
        return "vector"
    if request.needs_high_quality and budget in {"ultra", "high", "max"}:
        return "final_high"
    if request.needs_photorealism:
        return "photo_quality" if budget in {"advanced", "premium", "ultra", "high"} else "photo_fast"
    if request.needs_text_rendering:
        return "text_quality" if budget in {"advanced", "premium", "ultra", "high"} else "text_low_cost"
    return "fast_preview" if budget in {"low", "standard"} else "fast_general"


def _route(
    providers: dict[str, Any],
    provider: str,
    model: str | None,
    reasons: list[str],
    blocked: list[str],
) -> ImageRoute:
    meta = providers.get(provider, {})
    return ImageRoute(
        provider=provider,
        model=model or None,
        external_api=bool(meta.get("external_api", False)),
        ui_history=bool(meta.get("ui_history", False)),
        reasons=tuple(reasons),
        blocked_providers=tuple(dict.fromkeys(blocked)),
    )
