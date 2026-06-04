import datetime as dt
import importlib
import json
from pathlib import Path

from src.core.tiktok_aino import ha_publisher, monitoring, pipeline


def _gate(passed: bool = True) -> pipeline.GateResult:
    return pipeline.GateResult(passed=passed, score=92 if passed else 40)


def _readability(passed: bool = True) -> pipeline.ReadabilityResult:
    return pipeline.ReadabilityResult(
        passed=passed,
        checks={"mobile_text": passed},
        max_on_screen_chars=54,
        max_narration_chars=92,
        issues=[] if passed else ["mobile_text_too_long"],
    )


def _quality(passed: bool = True, score: int = 91) -> pipeline.PublishQualityResult:
    return pipeline.PublishQualityResult(
        passed=passed,
        selected_variant="test_variant",
        publish_ready_score=score,
        scores={"overall": score},
        blockers=[] if passed else ["publish_quality_not_passed"],
    )


def _valid_upload_manifest(mp4: Path, run_id: str = "leftaino_20260514_181016") -> dict:
    scenes = [
        {
            "scene_id": index,
            "body": f"Readable Korean-style body placeholder {index}",
            "on_screen_text": f"Readable card text {index}",
        }
        for index in range(1, 10)
    ]
    return {
        "run_id": run_id,
        "status": "publish_ready",
        "planned_publish_at_local": "2026-05-15T08:10:00+09:00",
        "schedule_status": "planned_not_scheduled",
        "format_plan": {"format_id": "growth_short"},
        "script": {
            "title": "AiNo verification",
            "post_title": "Readable post title",
            "caption": "Readable caption #news",
            "post_body": "Readable post body",
            "pinned_comment": "Readable pinned comment",
            "narration": "Readable narration for a generated short.",
            "hashtags": ["news", "politics"],
            "scenes": scenes,
        },
        "gate": {"passed": True},
        "readability": {"passed": True},
        "review": {"passed": True},
        "quality": {"passed": True, "publish_ready_score": 92},
        "audio_asset": {"provider": "elevenlabs", "status": "generated"},
        "mobile_visual_passed": True,
        "mobile_visual_checks": [
            {"passed": True, "text_render_passed": True, "preview_path": f"scene_{index}.png"}
            for index in range(1, 10)
        ],
        "synced_duration_matches_format": True,
        "fact_pack": {"gate_passed": True},
        "risk_flags": {"gate_passed": True},
        "source_card": {"gate_passed": True},
        "reference_fit": {"gate_passed": True},
        "angle_brief": {"gate_passed": True},
        "storyboard_brief": {"gate_passed": True},
        "tts_performance_plan": {"gate_passed": True},
        "artifacts": {
            "mp4": str(mp4),
            "fact_pack": "fact_pack.json",
            "risk_flags": "risk_flags.json",
            "source_card": "source_card.json",
            "reference_fit": "reference_fit.json",
            "angle_brief": "angle_brief.json",
            "storyboard_brief": "storyboard_brief.json",
            "tts_performance_plan": "tts_performance_plan.json",
        },
    }


def test_bridge_enriches_studio_metrics_payload() -> None:
    local_bridge = importlib.import_module("src.core.tiktok_aino.extension.local_bridge")
    payload = {
        "run_id": "leftaino_20260514_181016",
        "url": "https://www.tiktok.com/tiktokstudio/content",
        "title": "TikTok Studio",
        "textSample": ("Views 1,234\nLikes 56\nComments 7\nShares 3\nAverage watch time 43\n" * 20),
        "metricNodes": ["Views 1,234", "Likes 56", "Comments 7", "Shares 3", "Average watch time 43"],
    }

    enriched = local_bridge.enrich_metrics_payload(payload)

    assert enriched["schema_version"] == "studio_metrics_capture_v2"
    assert enriched["capture_quality"]["ok"] is True
    assert enriched["normalizedMetrics"]["views"] == 1234
    assert "views" in enriched["capture_quality"]["normalized_metric_keys"]
    assert "missing_run_id" not in enriched["warnings"]


def test_image_budget_blocks_paid_generation_before_quality_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AINO_PRIVACY_MODE", "cloud_explicit")
    decision = pipeline.decide_image_budget(
        output_dir=tmp_path,
        image_mode="auto",
        real_image_limit=9,
        gate=_gate(True),
        readability=_readability(True),
        quality=_quality(False, 74),
    )

    assert decision.allowed_external_generation is False
    assert decision.effective_image_mode == "local"
    assert decision.effective_real_image_limit == 0
    assert "publish_quality_not_passed" in decision.reasons


def test_image_budget_caps_remaining_daily_paid_images(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AINO_PRIVACY_MODE", "cloud_explicit")
    run_dir = tmp_path / "leftaino_20260514_181016"
    run_dir.mkdir()
    used_assets = [
        {"provider": "codex_cli", "status": "generated", "scene_id": index}
        for index in range(1, 27)
    ]
    (run_dir / "visual_assets.json").write_text(json.dumps(used_assets), encoding="utf-8")

    decision = pipeline.decide_image_budget(
        output_dir=tmp_path,
        image_mode="auto",
        real_image_limit=9,
        gate=_gate(True),
        readability=_readability(True),
        quality=_quality(True, 91),
    )

    assert decision.allowed_external_generation is True
    assert decision.daily_real_images_used == 26
    assert decision.effective_real_image_limit == 1


def test_monitor_worker_runs_due_window_and_sets_next_monitor(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports"
    monkeypatch.setattr(pipeline, "DEFAULT_PERFORMANCE_REPORT_DIR", report_dir)
    run_id = "leftaino_20260514_181016"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    mp4 = run_dir / "preview_1080x1920.mp4"
    mp4.write_bytes(b"fake")
    manifest = _valid_upload_manifest(mp4, run_id=run_id)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    metrics_dir = tmp_path / "studio_metrics"
    metrics_dir.mkdir()
    metrics_payload = {
        "run_id": run_id,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "metrics": {"views": 900, "likes": 90, "comments": 12, "shares": 7, "average_watch_time_sec": 42},
    }
    (metrics_dir / "studio_metrics_test.jsonl").write_text(json.dumps(metrics_payload) + "\n", encoding="utf-8")

    state_dir = tmp_path / "state"
    ha_publisher.enqueue_manifest(state_dir, run_dir / "manifest.json")
    jobs_path = state_dir / ha_publisher.JOBS_FILENAME
    jobs_doc = json.loads(jobs_path.read_text(encoding="utf-8"))
    job = next(iter(jobs_doc["jobs"].values()))
    job["status"] = "published"
    job["publish_at_local"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)).isoformat()
    jobs_path.write_text(json.dumps(jobs_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    result = ha_publisher.worker_once(
        state_dir,
        node_id="desktop-home",
        operation="monitor",
        output_dir=tmp_path,
    )
    updated_jobs = json.loads(jobs_path.read_text(encoding="utf-8"))["jobs"]
    updated_job = next(iter(updated_jobs.values()))
    second_claim = ha_publisher.claim_next_job(state_dir, node_id="desktop-home", operation="monitor")

    assert result["ok"] is True
    assert updated_job["status"] == "monitoring_complete"
    assert updated_job["monitor_windows_completed"] == [24]
    assert not updated_job.get("next_monitor_at")
    assert Path(updated_job["performance_report_path"]).exists()
    assert second_claim["ok"] is False


def test_empty_feedback_does_not_overwrite_meaningful_latest(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    latest_path = output_dir / "performance_feedback.json"
    latest_path.write_text(
        json.dumps(
            {
                "version": "performance_feedback_v1",
                "sample_count": 9,
                "topic_keywords": ["이재명"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "feedback": {
            "sample_count": 0,
            "term_scores": {},
            "format_scores": {},
            "visual_scores": {},
            "positive_terms": [],
            "negative_terms": [],
            "positive_visual_patterns": [],
            "negative_visual_patterns": [],
            "notes": [],
        }
    }

    paths = monitoring.write_performance_feedback_artifacts(output_dir, summary)
    preserved = json.loads(latest_path.read_text(encoding="utf-8"))
    stamped = json.loads(Path(paths["performance_feedback_path"]).read_text(encoding="utf-8"))

    assert preserved["sample_count"] == 9
    assert stamped["sample_count"] == 0
