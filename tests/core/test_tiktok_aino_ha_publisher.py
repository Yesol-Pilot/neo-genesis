import datetime as dt
import json
import os
from pathlib import Path
from types import SimpleNamespace

from src.core.tiktok_aino import ha_publisher, pipeline, upload_automation


def _write_plan(path: Path, publish_at: str, topic: str = "테스트 정치 이슈") -> None:
    plan = {
        "slots": [
            {
                "publish_at_local": publish_at,
                "format": "growth_short",
                "topic": topic,
                "post_title": "테스트 제목",
                "quality_score": 91,
                "ready_for_generation": True,
                "sources": [],
                "topic_candidate": {
                    "title": topic,
                    "angle": "검증",
                    "slot": "hot",
                    "target_duration_sec": 75,
                    "claims": [{"text": "테스트 주장", "source_ids": [], "risk": "medium"}],
                    "source_ids": [],
                },
            }
        ]
    }
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")


def _valid_upload_manifest(mp4: Path) -> dict:
    planned_publish_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
    scenes = [
        {
            "scene_id": index,
            "body": f"검수 가능한 한국어 본문입니다 {index}",
            "on_screen_text": f"한국어 카드 문구 {index}",
        }
        for index in range(1, 10)
    ]
    return {
        "run_id": "leftaino_20260512_181016",
        "status": "publish_ready",
        "planned_publish_at_local": planned_publish_at,
        "schedule_status": "planned_not_scheduled",
        "format_plan": {"format_id": "growth_short"},
        "script": {
            "title": "올바른 AiNo 검수",
            "post_title": "정치 이슈 검수 제목",
            "caption": "정치 이슈를 차분하게 짚는 한국어 캡션입니다",
            "post_body": "댓글로 의견을 남겨 주세요",
            "pinned_comment": "다음 검수 포인트도 팔로우해 주세요",
            "narration": "한국어 음성 대본이 자연스럽게 이어집니다",
            "hashtags": ["정치", "뉴스"],
            "scenes": scenes,
        },
        "gate": {"passed": True},
        "readability": {"passed": True},
        "review": {"passed": True},
        "quality": {"passed": True, "publish_ready_score": 92},
        "audio_asset": {
            "provider": "elevenlabs",
            "status": "generated",
            "notes": ["elevenlabs_history_final_deleted=0;elevenlabs_history_final_remaining_first_page=0"],
        },
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
        "tts_plan": {"provider": "elevenlabs", "actual_provider": "elevenlabs", "enable_logging": False, "publish_candidate": True},
        "artifacts": {
            "mp4": str(mp4),
            "fact_pack": "fact_pack.json",
            "risk_flags": "risk_flags.json",
            "source_card": "source_card.json",
            "reference_fit": "reference_fit.json",
            "angle_brief": "angle_brief.json",
            "storyboard_brief": "storyboard_brief.json",
            "tts_performance_plan": "tts_performance_plan.json",
            "tts_plan": "tts_plan.json",
        },
    }


def test_enqueue_plan_is_idempotent(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, "2026-05-15T08:10:00+09:00")

    first = ha_publisher.enqueue_plan(tmp_path / "state", plan_path)
    second = ha_publisher.enqueue_plan(tmp_path / "state", plan_path)

    assert len(first["created"]) == 1
    assert second["created"] == []
    assert second["refreshed"] == []
    assert len(second["unchanged"]) == 1


def test_enqueue_plan_refreshes_existing_planned_slot_when_topic_changes(tmp_path: Path) -> None:
    publish_at = "2026-05-15T08:10:00+09:00"
    first_path = tmp_path / "plan_first.json"
    second_path = tmp_path / "plan_second.json"
    state_dir = tmp_path / "state"
    _write_plan(first_path, publish_at, topic="first hot topic")
    _write_plan(second_path, publish_at, topic="second sharper topic")

    first = ha_publisher.enqueue_plan(state_dir, first_path)
    second = ha_publisher.enqueue_plan(state_dir, second_path)
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]
    job = jobs[first["created"][0]]

    assert second["created"] == []
    assert second["refreshed"] == [first["created"][0]]
    assert second["unchanged"] == []
    assert job["topic"] == "second sharper topic"
    assert job["payload"]["plan_path"] == str(second_path)
    assert job["history"][-1]["event"] == "plan_refreshed"


def test_enqueue_plan_refreshes_existing_planned_slot_when_plan_path_changes(tmp_path: Path) -> None:
    publish_at = "2026-05-15T08:10:00+09:00"
    first_path = tmp_path / "plan_first.json"
    second_path = tmp_path / "plan_second.json"
    state_dir = tmp_path / "state"
    _write_plan(first_path, publish_at, topic="same hot topic")
    _write_plan(second_path, publish_at, topic="same hot topic")

    first = ha_publisher.enqueue_plan(state_dir, first_path)
    second = ha_publisher.enqueue_plan(state_dir, second_path)
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]
    job = jobs[first["created"][0]]

    assert second["created"] == []
    assert second["refreshed"] == [first["created"][0]]
    assert second["unchanged"] == []
    assert job["payload"]["plan_path"] == str(second_path)


def test_generate_worker_preserves_slot_topic_discovery(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    run_dir = tmp_path / "generated" / "leftaino_test"
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "manifest.json"
    mp4_path = run_dir / "preview_1080x1920.mp4"
    mp4_path.write_bytes(b"fake")
    manifest_path.write_text(
        json.dumps({"status": "publish_ready", "review": {"blockers": []}, "quality": {"blockers": []}}, ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_run_for_topic(*_args, **kwargs):
        captured["topic_discovery"] = kwargs["topic_discovery"]
        return SimpleNamespace(
            run_id="leftaino_test",
            artifacts=SimpleNamespace(manifest_json=str(manifest_path), mp4=str(mp4_path)),
            quality=SimpleNamespace(publish_ready_score=91),
            review=SimpleNamespace(recommendation="publish"),
        )

    monkeypatch.setattr(pipeline, "run_for_topic", fake_run_for_topic)
    monkeypatch.setattr(pipeline, "validate_manifest_for_upload", lambda _manifest: {"status": "publish_ready"})
    slot_discovery = {
        "mode": "rolling_schedule_plan",
        "deep_research_report": {
            "research_mode": "schedule_lightweight_research",
            "selected_research_question": "what changed?",
        },
        "visual_mandates": ["use distinct scenes"],
    }
    job = {
        "job_id": "leftaino_20260515_081000_09_growth_short",
        "payload": {
            "plan_path": str(tmp_path / "plan.json"),
            "slot_index": 1,
            "slot": {
                "publish_at_local": "2026-05-15T08:10:00+09:00",
                "format": "growth_short",
                "topic": "worker topic",
                "topic_discovery": slot_discovery,
                "sources": [],
            },
        },
    }

    evidence = ha_publisher._generate_for_job(job, output_dir=tmp_path / "generated", image_mode="local", real_image_limit=0)
    topic_discovery = captured["topic_discovery"]

    assert evidence["manifest_status"] == "publish_ready"
    assert isinstance(topic_discovery, dict)
    assert topic_discovery["mode"] == "ha_publisher"
    assert topic_discovery["deep_research_report"] == slot_discovery["deep_research_report"]
    assert topic_discovery["visual_mandates"] == slot_discovery["visual_mandates"]
    assert topic_discovery["slot_index"] == 1


def test_claim_uses_single_active_lease(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat())
    state_dir = tmp_path / "state"
    ha_publisher.enqueue_plan(state_dir, plan_path)

    first = ha_publisher.claim_next_job(state_dir, node_id="desktop-home", operation="generate", lead_hours=24)
    second = ha_publisher.claim_next_job(state_dir, node_id="etribe-yesol", operation="generate", lead_hours=24)

    assert first["ok"] is True
    assert second["ok"] is False
    assert second["reason"] == "no_claimable_job"


def test_worker_dry_run_does_not_claim_or_increment_attempts(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat())
    state_dir = tmp_path / "state"
    ha_publisher.enqueue_plan(state_dir, plan_path)

    result = ha_publisher.worker_once(
        state_dir,
        node_id="desktop-home",
        operation="generate",
        output_dir=tmp_path / "generated",
        dry_run=True,
    )
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]
    leases = json.loads((state_dir / ha_publisher.LEASES_FILENAME).read_text(encoding="utf-8"))["leases"]
    job = next(iter(jobs.values()))

    assert result["ok"] is True
    assert result["claim"]["ok"] is True
    assert job["status"] == "planned"
    assert job["attempts"] == {}
    assert leases == {}


def test_worker_generate_can_set_cloud_privacy_mode(tmp_path: Path, monkeypatch) -> None:
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat())
    state_dir = tmp_path / "state"
    captured: dict[str, str | None] = {}
    monkeypatch.delenv("AINO_PRIVACY_MODE", raising=False)
    ha_publisher.enqueue_plan(state_dir, plan_path)

    def fake_generate(*_args, **_kwargs):
        captured["privacy_mode"] = os.environ.get("AINO_PRIVACY_MODE")
        return {"manifest_status": "publish_ready", "run_id": "run", "manifest_path": "manifest.json"}

    monkeypatch.setattr(ha_publisher, "_generate_for_job", fake_generate)

    result = ha_publisher.worker_once(
        state_dir,
        node_id="desktop-home",
        operation="generate",
        output_dir=tmp_path / "generated",
        privacy_mode="cloud_explicit",
    )

    assert result["ok"] is True
    assert result["status"] == "generated"
    assert captured["privacy_mode"] == "cloud_explicit"
    assert "AINO_PRIVACY_MODE" not in os.environ


def test_expired_lease_reclaims_job_for_failover(tmp_path: Path, monkeypatch) -> None:
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat())
    state_dir = tmp_path / "state"
    ha_publisher.enqueue_plan(state_dir, plan_path)
    first = ha_publisher.claim_next_job(state_dir, node_id="desktop-home", operation="generate", lead_hours=24)
    lease_id = first["lease"]["lease_id"]

    leases_path = state_dir / ha_publisher.LEASES_FILENAME
    leases = json.loads(leases_path.read_text(encoding="utf-8"))
    leases["leases"][lease_id]["expires_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)).isoformat()
    leases_path.write_text(json.dumps(leases, ensure_ascii=False), encoding="utf-8")

    reclaimed = ha_publisher.reclaim_stale_leases(state_dir)
    second = ha_publisher.claim_next_job(state_dir, node_id="etribe-yesol", operation="generate", lead_hours=24)

    assert reclaimed["count"] == 1
    assert second["ok"] is True
    assert second["lease"]["node_id"] == "etribe-yesol"


def test_enqueue_manifest_creates_upload_job(tmp_path: Path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    mp4 = run_dir / "preview_1080x1920.mp4"
    mp4.write_bytes(b"fake")
    manifest = _valid_upload_manifest(mp4)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    result = ha_publisher.enqueue_manifest(tmp_path / "state", manifest_path)
    claim = ha_publisher.claim_next_job(tmp_path / "state", node_id="desktop-home", operation="upload", lead_hours=48)

    assert result["created"] is True
    assert result["status"] == "generated"
    assert claim["ok"] is True
    assert claim["job"]["run_id"] == "leftaino_20260512_181016"


def test_enqueue_manifest_blocks_duplicate_content_across_schedule_slots(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    first_dir = tmp_path / "leftaino_20260512_181016"
    second_dir = tmp_path / "leftaino_20260512_191016"
    first_dir.mkdir()
    second_dir.mkdir()
    first_mp4 = first_dir / "preview_1080x1920.mp4"
    second_mp4 = second_dir / "preview_1080x1920.mp4"
    first_mp4.write_bytes(b"fake")
    second_mp4.write_bytes(b"fake")
    first_manifest = _valid_upload_manifest(first_mp4)
    second_manifest = _valid_upload_manifest(second_mp4)
    second_manifest["run_id"] = "leftaino_20260512_191016"
    second_manifest["planned_publish_at_local"] = (
        dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
    ).isoformat()
    first_path = first_dir / "manifest.json"
    second_path = second_dir / "manifest.json"
    first_path.write_text(json.dumps(first_manifest, ensure_ascii=False), encoding="utf-8")
    second_path.write_text(json.dumps(second_manifest, ensure_ascii=False), encoding="utf-8")

    first = ha_publisher.enqueue_manifest(state_dir, first_path)
    second = ha_publisher.enqueue_manifest(state_dir, second_path)
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]

    assert first["created"] is True
    assert second["blocked"] is True
    assert second["reason"] == "duplicate_content"
    assert len(jobs) == 1


def test_enqueue_manifest_blocks_duplicate_visual_signature_even_when_title_changes(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    first_dir = tmp_path / "leftaino_20260512_181016"
    second_dir = tmp_path / "leftaino_20260512_201016"
    first_dir.mkdir()
    second_dir.mkdir()
    first_mp4 = first_dir / "preview_1080x1920.mp4"
    second_mp4 = second_dir / "preview_1080x1920.mp4"
    first_mp4.write_bytes(b"fake")
    second_mp4.write_bytes(b"fake")
    visual_assets = [
        {
            "scene_id": index,
            "provider": "codex_cli",
            "status": "generated",
            "path": f"scene_{index}.png",
            "prompt": "Controlled in-image text",
            "visual_brief": {
                "role": "evidence",
                "location": "same hallway",
                "camera": "same low angle",
                "foreground_prop": "same paper card",
                "treatment_id": "same_tableau",
                "diegetic_text": f"card {index}",
            },
        }
        for index in range(1, 10)
    ]
    first_manifest = _valid_upload_manifest(first_mp4)
    second_manifest = _valid_upload_manifest(second_mp4)
    first_manifest["visual_assets"] = visual_assets
    second_manifest["visual_assets"] = visual_assets
    first_manifest["layout_quality"] = {
        "mode": "native_image_text_scene_signature",
        "layout_ids": [f"same-layout-{index}" for index in range(1, 10)],
        "unique_count": 9,
    }
    second_manifest["layout_quality"] = first_manifest["layout_quality"]
    second_manifest["run_id"] = "leftaino_20260512_201016"
    second_manifest["planned_publish_at_local"] = (
        dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
    ).isoformat()
    second_manifest["script"]["post_title"] = f"{second_manifest['script']['post_title']} 2"
    second_manifest["script"]["caption"] = f"{second_manifest['script']['caption']} 2"
    second_manifest["script"]["post_body"] = f"{second_manifest['script']['post_body']} 2"
    first_path = first_dir / "manifest.json"
    second_path = second_dir / "manifest.json"
    first_path.write_text(json.dumps(first_manifest, ensure_ascii=False), encoding="utf-8")
    second_path.write_text(json.dumps(second_manifest, ensure_ascii=False), encoding="utf-8")

    first = ha_publisher.enqueue_manifest(state_dir, first_path)
    second = ha_publisher.enqueue_manifest(state_dir, second_path)
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]

    assert first["created"] is True
    assert second["blocked"] is True
    assert second["reason"] == "duplicate_content"
    assert len(jobs) == 1


def test_enqueue_plan_blocks_duplicate_topics_in_same_plan(tmp_path: Path) -> None:
    publish_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    plan = {
        "slots": [
            {
                "publish_at_local": publish_at.isoformat(),
                "format": "growth_short",
                "topic": "같은 정치 이슈",
                "post_title": "같은 정치 이슈",
                "quality_score": 91,
                "ready_for_generation": True,
            },
            {
                "publish_at_local": (publish_at + dt.timedelta(hours=4)).isoformat(),
                "format": "growth_short",
                "topic": "같은 정치 이슈",
                "post_title": "같은 정치 이슈",
                "quality_score": 91,
                "ready_for_generation": True,
            },
        ]
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    result = ha_publisher.enqueue_plan(tmp_path / "state", plan_path)

    assert len(result["created"]) == 1
    assert len(result["blocked"]) == 1
    assert result["blocked"][0]["reason"] == "duplicate_content"


def test_defer_upload_lease_restores_job_without_attempt_penalty(tmp_path: Path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    mp4 = run_dir / "preview_1080x1920.mp4"
    mp4.write_bytes(b"fake")
    manifest = _valid_upload_manifest(mp4)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    state_dir = tmp_path / "state"
    ha_publisher.enqueue_manifest(state_dir, manifest_path)
    claim = ha_publisher.claim_next_job(state_dir, node_id="desktop-home", operation="upload", lead_hours=48)

    result = ha_publisher.defer_lease(state_dir, lease_id=claim["lease"]["lease_id"], node_id="desktop-home", reason="login_required")
    jobs = json.loads((state_dir / ha_publisher.JOBS_FILENAME).read_text(encoding="utf-8"))["jobs"]
    job = jobs[claim["job"]["job_id"]]

    assert result["ok"] is True
    assert job["status"] == "generated"
    assert job["attempts"]["upload"] == 0


def test_enqueue_manifest_marks_incomplete_visual_review_as_revision(tmp_path: Path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    mp4 = run_dir / "preview_1080x1920.mp4"
    mp4.write_bytes(b"fake")
    manifest = _valid_upload_manifest(mp4)
    manifest["mobile_visual_checks"][0].pop("text_render_passed")
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    result = ha_publisher.enqueue_manifest(tmp_path / "state", manifest_path)
    claim = ha_publisher.claim_next_job(tmp_path / "state", node_id="desktop-home", operation="upload", lead_hours=48)

    assert result["status"] == "needs_revision"
    assert claim["ok"] is False
    assert claim["reason"] == "no_claimable_job"


def test_upload_automation_blocks_manifest_without_final_visual_gate(tmp_path: Path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    mp4 = run_dir / "preview_1080x1920.mp4"
    mp4.write_bytes(b"fake")
    manifest = _valid_upload_manifest(mp4)
    manifest["mobile_visual_checks"][0]["text_render_passed"] = False
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    job = upload_automation.build_upload_job(manifest_path)

    assert job["ok"] is False
    assert job["reason"] == "manifest_not_upload_ready"
    assert "mobile_visual_check_1_text_render_not_passed" in job["validation"]["blockers"]


def test_apply_upload_metadata_override_uses_clean_slot_text(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"script": {"caption": "bad", "post_title": "bad", "hashtags": ["bad"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    job = {
        "payload": {
            "slot": {
                "caption": "정치 이슈를 짚는 한국어 캡션 #정치",
                "post_title": "검수 가능한 한국어 제목",
                "hashtags": ["정치", "뉴스"],
            }
        }
    }

    result = ha_publisher.apply_upload_metadata_override(manifest_path, job)
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["overridden"] is True
    assert updated["script"]["caption"] == "정치 이슈를 짚는 한국어 캡션 #정치"
    assert updated["script"]["hashtags"] == ["정치", "뉴스"]
