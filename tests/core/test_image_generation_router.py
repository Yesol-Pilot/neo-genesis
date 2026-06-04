# -*- coding: utf-8 -*-
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.llm.image_generation_router import ImageRoutingRequest, route_image_generation


def test_public_social_card_can_route_to_gamma_when_ui_is_allowed():
    route = route_image_generation(
        ImageRoutingRequest(output_kind="social", allow_gamma_ui=True),
    )

    assert route.provider == "gamma_api"
    assert route.model == "flux-kontext-fast"
    assert route.ui_history is True


def test_gamma_ui_hidden_routes_away_from_gamma():
    route = route_image_generation(
        ImageRoutingRequest(needs_gamma_ui_hidden=True, allow_gamma_ui=True),
    )

    assert route.provider == "codex_cli"
    assert "gamma_api" in route.blocked_providers
    assert route.ui_history is False


def test_sensitive_work_routes_local_even_if_gamma_allowed():
    route = route_image_generation(
        ImageRoutingRequest(sensitivity="private", allow_gamma_ui=True),
    )

    assert route.provider == "local_comfyui"
    assert route.external_api is False
    assert "gamma_api" in route.blocked_providers


def test_company_safe_internal_work_can_route_to_gamma():
    route = route_image_generation(
        ImageRoutingRequest(sensitivity="internal", output_kind="social", allow_gamma_ui=True),
    )

    assert route.provider == "gamma_api"
    assert route.ui_history is True


def test_not_company_safe_routes_local():
    route = route_image_generation(
        ImageRoutingRequest(company_safe=False, allow_gamma_ui=True),
    )

    assert route.provider == "local_comfyui"
    assert "gamma_api" in route.blocked_providers


def test_text_heavy_gamma_advanced_routes_to_gemini_image_model_inside_gamma():
    route = route_image_generation(
        ImageRoutingRequest(
            output_kind="social",
            allow_gamma_ui=True,
            needs_text_rendering=True,
            budget_tier="advanced",
        ),
    )

    assert route.provider == "gamma_api"
    assert route.model == "gemini-3-pro-image"


def test_vector_gamma_routes_to_recraft_svg():
    route = route_image_generation(
        ImageRoutingRequest(
            output_kind="image",
            allow_gamma_ui=True,
            needs_vector=True,
            budget_tier="premium",
        ),
    )

    assert route.provider == "gamma_api"
    assert route.model == "recraft-v4-svg"


def test_no_external_api_forces_local():
    route = route_image_generation(
        ImageRoutingRequest(allow_external_api=False, allow_gamma_ui=True),
    )

    assert route.provider == "local_comfyui"
    assert route.external_api is False
