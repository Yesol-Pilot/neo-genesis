from __future__ import annotations

import json

from src.core.tiktok_aino import editorial_os_v2, pipeline


def test_canary_package_passes_research_level_quality_gate(tmp_path) -> None:
    package = editorial_os_v2.build_canary_package(seed="election_12_4")

    assert package.qa_report["ok"] is True
    assert package.qa_report["blockers"] == []
    assert len(package.scenes) >= 9
    assert package.qa_report["metrics"]["unique_locations"] >= 6
    assert package.qa_report["metrics"]["unique_cameras"] >= 6
    assert package.qa_report["metrics"]["unique_props"] >= 7
    assert package.qa_report["metrics"]["unique_layouts"] >= 5
    assert package.qa_report["metrics"]["unique_treatments"] >= 5
    assert all(critic.passed for critic in package.critics)

    artifacts = editorial_os_v2.write_canary_package(package, tmp_path)
    qa = json.loads((tmp_path / "qa_report.json").read_text(encoding="utf-8"))

    assert qa["ok"] is True
    assert "content_signature" in artifacts
    assert (tmp_path / "canary_storyboard.md").exists()


def test_recent_visual_signature_overlap_blocks_repetition() -> None:
    package = editorial_os_v2.build_canary_package(seed="election_12_4")
    repeated = editorial_os_v2.build_canary_package(
        seed="election_12_4",
        recent_signatures=[package.signature.__dict__],
    )

    policy = next(critic for critic in repeated.critics if critic.critic == "policy")

    assert repeated.qa_report["ok"] is False
    assert policy.passed is False
    assert "recent_visual_signature_overlap:1" in policy.blockers


def test_diegetic_text_is_short_and_present_for_all_scenes() -> None:
    package = editorial_os_v2.build_canary_package(seed="election_12_4")

    assert all(scene.diegetic_text.strip() for scene in package.scenes)
    assert max(len(scene.diegetic_text) for scene in package.scenes) <= editorial_os_v2.MAX_DIEGETIC_TEXT_CHARS


def _scene(scene_id: int) -> pipeline.Scene:
    return pipeline.Scene(
        scene_id=scene_id,
        duration_sec=7,
        title=f"scene {scene_id}",
        body=f"body {scene_id}",
        visual=f"visual {scene_id}",
        on_screen_text=f"headline {scene_id}",
    )


def _native_asset(scene_id: int, *, location: str, camera: str, prop: str, treatment: str) -> pipeline.VisualAsset:
    return pipeline.VisualAsset(
        scene_id=scene_id,
        provider="codex_cli",
        status="generated",
        path=f"scene_{scene_id}.png",
        prompt="Controlled in-image text",
        visual_brief={
            "role": "evidence" if scene_id not in {1, 9} else ("hook" if scene_id == 1 else "cta"),
            "location": location,
            "camera": camera,
            "foreground_prop": prop,
            "treatment_id": treatment,
            "diegetic_text": f"텍스트{scene_id}",
        },
    )


def test_native_image_text_layout_gate_rejects_repeated_visual_signature() -> None:
    scenes = [_scene(index) for index in range(1, 10)]
    assets = {
        scene.scene_id: _native_asset(
            scene.scene_id,
            location="same dark hallway",
            camera="same low angle",
            prop="same paper card",
            treatment="same_tableau",
        )
        for scene in scenes
    }

    quality = pipeline._card_layout_quality(scenes, assets)

    assert quality["passed"] is False
    assert quality["mode"] == "native_image_text_scene_signature"
    assert quality["visual_signature_unique_count"] < quality["required_unique_count"]


def test_native_image_text_layout_gate_accepts_scene_signature_variety() -> None:
    scenes = [_scene(index) for index in range(1, 10)]
    assets = {
        scene.scene_id: _native_asset(
            scene.scene_id,
            location=f"location {scene.scene_id}",
            camera=f"camera {scene.scene_id}",
            prop=f"prop {scene.scene_id}",
            treatment=f"treatment {scene.scene_id}",
        )
        for scene in scenes
    }

    quality = pipeline._card_layout_quality(scenes, assets)

    assert quality["passed"] is True
    assert quality["mode"] == "native_image_text_scene_signature"
    assert quality["unique_count"] >= quality["required_unique_count"]
