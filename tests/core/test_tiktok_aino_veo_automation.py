import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from src.core.tiktok_aino import veo_automation


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (576, 1024), "#4a5568").save(path)


def _write_manifest(tmp_path: Path) -> Path:
    image_path = tmp_path / "visual_assets" / "scene_01_cinematic.png"
    _write_png(image_path)
    manifest = {
        "topic": {"title": "public accountability issue"},
        "script": {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "Hook",
                    "visual": "courthouse corridor with a sealed folder",
                }
            ]
        },
        "visual_assets": [
            {
                "scene_id": 1,
                "provider": "test",
                "status": "generated",
                "path": str(image_path),
                "prompt": "test prompt",
                "visual_brief": {
                    "role": "hook",
                    "location": "courthouse corridor",
                    "camera": "slow documentary push-in",
                    "palette": "cold gray with restrained red reflection",
                    "visual_intent": "make the civic question feel immediate",
                    "visual_anchor": ["sealed folder", "press cameras", "hard doorway shadow"],
                    "safety_constraints": ["no readable text", "no identifiable person", "no party logos"],
                },
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_estimate_cost_uses_current_pricing_table() -> None:
    pricing = veo_automation.load_pricing()

    cost = veo_automation.estimate_cost_usd(
        pricing=pricing,
        model_id="veo-3.1-fast-generate-001",
        resolution="1080p",
        generate_audio=False,
        duration_seconds=4,
        sample_count=2,
        scene_count=1,
    )

    assert cost == 0.8


def test_build_scene_request_uses_image_to_video_body(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    config = veo_automation.VeoRunConfig(
        manifest_path=manifest,
        scene_ids=[1],
        output_dir=tmp_path / "out",
        state_dir=tmp_path / "state",
        project_id="demo-project",
        location="us-central1",
        model_id="veo-3.1-generate-001",
        storage_uri="gs://demo-bucket/veo/",
        aspect_ratio="9:16",
        resolution="1080p",
        duration_seconds=4,
        sample_count=1,
        generate_audio=False,
        person_generation="allow_adult",
        enhance_prompt=True,
        seed=42,
        run_cap_usd=2.0,
        monthly_cap_usd=90.0,
        allow_paid=False,
        enable_api=False,
        poll_timeout_sec=60,
        poll_interval_sec=5,
        dry_run=True,
    )

    requests = veo_automation.build_scene_requests(config)

    assert len(requests) == 1
    body = requests[0].request_body
    assert body["parameters"]["durationSeconds"] == 4
    assert body["parameters"]["aspectRatio"] == "9:16"
    assert "generateAudio" not in body["parameters"]
    assert "bytesBase64Encoded" in body["instances"][0]["image"]
    assert "courthouse corridor" in requests[0].prompt


def test_receipt_room_placeholder_blocks_paid_veo_generation(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["receipt_room"] = {
        "generation_ready": False,
        "generation_blockers": ["storyboard_placeholder_keyframe"],
    }
    manifest.write_text(json.dumps(data), encoding="utf-8")
    config = veo_automation.VeoRunConfig(
        manifest_path=manifest,
        scene_ids=[1],
        output_dir=tmp_path / "out",
        state_dir=tmp_path / "state",
        project_id="demo-project",
        location="us-central1",
        model_id="veo-3.1-fast-generate-001",
        storage_uri="gs://demo-bucket/veo/",
        aspect_ratio="9:16",
        resolution="1080p",
        duration_seconds=8,
        sample_count=1,
        generate_audio=False,
        person_generation="allow_adult",
        enhance_prompt=True,
        seed=None,
        run_cap_usd=1.0,
        monthly_cap_usd=90.0,
        allow_paid=True,
        enable_api=False,
        poll_timeout_sec=60,
        poll_interval_sec=5,
        dry_run=False,
        privacy_mode="cloud_explicit",
    )

    try:
        veo_automation.build_scene_requests(config)
    except RuntimeError as exc:
        assert "not approved for paid Veo generation" in str(exc)
        assert "storyboard_placeholder_keyframe" in str(exc)
    else:
        raise AssertionError("Receipt Room placeholder manifest should block paid generation")


def test_local_only_privacy_blocks_paid_veo_generation(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    config = veo_automation.VeoRunConfig(
        manifest_path=manifest,
        scene_ids=[1],
        output_dir=tmp_path / "out",
        state_dir=tmp_path / "state",
        project_id="demo-project",
        location="us-central1",
        model_id="veo-3.1-fast-generate-001",
        storage_uri="gs://demo-bucket/veo/",
        aspect_ratio="9:16",
        resolution="1080p",
        duration_seconds=8,
        sample_count=1,
        generate_audio=False,
        person_generation="allow_adult",
        enhance_prompt=True,
        seed=None,
        run_cap_usd=1.0,
        monthly_cap_usd=90.0,
        allow_paid=True,
        enable_api=False,
        poll_timeout_sec=60,
        poll_interval_sec=5,
        dry_run=False,
        privacy_mode="local_only",
    )

    try:
        veo_automation.build_scene_requests(config)
    except RuntimeError as exc:
        assert "local-only privacy mode" in str(exc)
        assert "provider-side" in str(exc)
    else:
        raise AssertionError("local-only privacy mode should block paid Veo generation")


def _write_video(path: Path, *, moving: bool) -> None:
    frames = []
    for index in range(24):
        frame = np.zeros((256, 144, 3), dtype=np.uint8)
        frame[:, :] = (38, 46, 56)
        x = 24 + (index * 4 if moving else 0)
        frame[90:170, x : x + 52, :] = (210, 220, 230)
        frames.append(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, frames, fps=24)


def test_quality_gate_blocks_static_video(tmp_path: Path) -> None:
    video = tmp_path / "static.mp4"
    _write_video(video, moving=False)

    report = veo_automation.analyze_video_quality(
        video,
        output_dir=tmp_path / "qa",
        expected_duration_sec=1,
    )

    assert not report.passed
    assert "motion_below_threshold" in report.blockers


def test_quality_gate_accepts_moving_video(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    _write_video(video, moving=True)

    report = veo_automation.analyze_video_quality(
        video,
        output_dir=tmp_path / "qa",
        expected_duration_sec=1,
    )

    assert report.passed
    assert report.metrics["motion_pixel_ratio_max"] > 0
