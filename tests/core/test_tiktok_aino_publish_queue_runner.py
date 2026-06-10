import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.core.tiktok_aino import publish_queue_runner


def _write_queue(tmp_path: Path, *, planned_at: str | None = None) -> Path:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    mp4 = tmp_path / "preview_1080x1920_upload_safe.mp4"
    mp4.write_bytes(b"video")
    future = planned_at or (
        dt.datetime.now(ZoneInfo("Asia/Seoul")) + dt.timedelta(days=1)
    ).replace(microsecond=0).isoformat()
    queue = {
        "version": "aino_publish_queue_v1",
        "timezone": "Asia/Seoul",
        "posting_boundary": {
            "tiktok_upload_performed": False,
            "tiktok_schedule_click_performed": False,
            "public_posting_allowed_without_explicit_owner_instruction": False,
        },
        "queue": [
            {
                "priority": 1,
                "run_id": "leftaino_test",
                "post_title": "test title",
                "planned_publish_at_local": future,
                "manifest_path": str(manifest),
                "upload_safe_mp4": str(mp4),
                "upload_ready": True,
                "publish_ready": True,
            }
        ],
    }
    queue_path = tmp_path / "publish_queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    return queue_path


def test_publish_queue_dry_run_invokes_upload_dry_run(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path)
    calls = []

    def fake_prepare_upload(manifest_path, **kwargs):
        calls.append((manifest_path, kwargs))
        return {"ok": True, "dry_run": kwargs["dry_run"], "job": {"run_id": "leftaino_test"}}

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fake_prepare_upload)

    result = publish_queue_runner.run_publish_queue(queue_path, mode="dry-run", write_report=False)

    assert result["ok"] is True
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    assert len(calls) == 1
    assert calls[0][1]["mode"] == "dry-run"
    assert calls[0][1]["dry_run"] is True


def test_publish_queue_blocks_external_mode_without_confirmation(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path)

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("external mode must not call upload automation without confirmation")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.run_publish_queue(queue_path, mode="schedule", write_report=False)

    assert result["ok"] is False
    assert result["results"][0]["reason"] == "external_action_confirmation_required"
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False


def test_publish_queue_blocks_external_mode_without_owner_instruction(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path)

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("external mode must not call upload automation without owner instruction")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.run_publish_queue(
        queue_path,
        mode="schedule",
        confirm_external_action=True,
        write_report=False,
    )

    assert result["ok"] is False
    assert result["owner_instruction_required"] is True
    assert result["owner_instruction_valid"] is False
    assert result["results"][0]["reason"] == "explicit_owner_instruction_required"
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False


def test_publish_queue_external_mode_accepts_explicit_owner_instruction(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path)
    calls = []

    def fake_prepare_upload(manifest_path, **kwargs):
        calls.append((manifest_path, kwargs))
        return {"ok": True, "dry_run": kwargs["dry_run"], "job": {"run_id": "leftaino_test"}}

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fake_prepare_upload)

    result = publish_queue_runner.run_publish_queue(
        queue_path,
        mode="schedule",
        confirm_external_action=True,
        owner_instruction="owner explicitly requested schedule upload post in current session",
        write_report=False,
    )

    assert result["ok"] is True
    assert result["external_action_confirmed"] is True
    assert result["owner_instruction_valid"] is True
    assert len(calls) == 1
    assert calls[0][1]["mode"] == "schedule"
    assert calls[0][1]["dry_run"] is False


def test_publish_queue_blocks_past_slots_by_default(tmp_path, monkeypatch):
    past = (
        dt.datetime.now(ZoneInfo("Asia/Seoul")) - dt.timedelta(days=1)
    ).replace(microsecond=0).isoformat()
    queue_path = _write_queue(tmp_path, planned_at=past)

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("past slot must fail before upload automation")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.run_publish_queue(queue_path, mode="dry-run", write_report=False)

    assert result["ok"] is False
    assert result["results"][0]["reason"] == "queue_row_validation_failed"
    assert "planned_publish_at_local_in_past" in result["results"][0]["validation_issues"]


def test_rollover_past_slots_writes_next_local_slot_without_external_action(tmp_path):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-09T08:10:00+09:00")
    output_path = tmp_path / "rolled_queue.json"
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    result = publish_queue_runner.rollover_publish_queue(
        queue_path,
        output_path=output_path,
        now=now,
    )

    assert result["ok"] is True
    assert result["changed"] is True
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    rolled = json.loads(output_path.read_text(encoding="utf-8"))
    assert rolled["queue"][0]["planned_publish_at_local"] == "2026-06-09T19:30:00+09:00"
    assert rolled["queue"][0]["rollover_from_local"] == "2026-06-09T08:10:00+09:00"
    assert rolled["posting_boundary"]["tiktok_upload_performed"] is False
    assert rolled["posting_boundary"]["tiktok_schedule_click_performed"] is False
    assert (
        rolled["posting_boundary"]["public_posting_allowed_without_explicit_owner_instruction"]
        is False
    )


def test_rollover_multiple_past_slots_preserves_priority_order(tmp_path):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-09T08:10:00+09:00")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    second = dict(queue["queue"][0])
    second["priority"] = 2
    second["run_id"] = "leftaino_test_2"
    second["post_title"] = "test title 2"
    second["planned_publish_at_local"] = "2026-06-09T11:20:00+09:00"
    queue["queue"].append(second)
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "rolled_queue.json"
    now = dt.datetime(2026, 6, 9, 19, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    result = publish_queue_runner.rollover_publish_queue(
        queue_path,
        output_path=output_path,
        now=now,
    )

    assert result["changed"] is True
    assert [change["run_id"] for change in result["changes"]] == [
        "leftaino_test",
        "leftaino_test_2",
    ]
    rolled = json.loads(output_path.read_text(encoding="utf-8"))
    assert [row["planned_publish_at_local"] for row in rolled["queue"]] == [
        "2026-06-10T08:10:00+09:00",
        "2026-06-10T11:20:00+09:00",
    ]


def test_audit_marks_queue_ready_without_external_action(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-10T08:10:00+09:00")
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("audit must not call upload automation")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.audit_publish_queue(
        queue_path,
        now=now,
        write_report=False,
    )

    assert result["ok"] is True
    assert result["ready_to_schedule_after_explicit_owner_instruction"] is True
    assert result["rollover_required"] is False
    assert result["next_action"] == "await_explicit_owner_upload_schedule_post_instruction"
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    assert result["performance_measurement_performed"] is False


def test_audit_requires_rollover_for_too_close_slot(tmp_path):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-09T19:00:00+09:00")
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    result = publish_queue_runner.audit_publish_queue(
        queue_path,
        now=now,
        lead_minutes=30,
        write_report=False,
    )

    assert result["ready_to_schedule_after_explicit_owner_instruction"] is False
    assert result["rollover_required"] is True
    assert result["next_action"] == "run_rollover_past_slots"
    assert result["results"][0]["slot_status"] == "too_close"
    assert "planned_publish_at_local_too_close" in result["results"][0]["validation_issues"]


def test_packet_ready_queue_contains_safe_and_guarded_external_commands(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-10T08:10:00+09:00")
    output_path = tmp_path / "packet.json"
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("packet must not call upload automation")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.create_execution_packet(
        queue_path,
        output_path=output_path,
        now=now,
    )

    assert result["ok"] is True
    assert result["local_only"] is True
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    assert result["audit"]["ready_to_schedule_after_explicit_owner_instruction"] is True
    assert any("--mode dry-run" in command for command in result["commands"]["safe_local_now"])
    external = result["commands"]["external_after_explicit_owner_instruction"]
    assert external["requires_explicit_owner_instruction"] is True
    assert external["requires_owner_instruction_arg"] is True
    assert "--confirm-external-action" in external["schedule"]
    assert "--owner-instruction" in external["schedule"]
    assert output_path.exists()
    assert output_path.with_suffix(".md").exists()


def test_packet_too_close_queue_recommends_rollover(tmp_path):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-09T19:00:00+09:00")
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    result = publish_queue_runner.create_execution_packet(
        queue_path,
        now=now,
        lead_minutes=30,
        write_output=False,
    )

    assert result["audit"]["rollover_required"] is True
    assert result["audit"]["next_action"] == "run_rollover_past_slots"
    assert any("--rollover-past-slots" in command for command in result["commands"]["safe_local_now"])
    assert result["rules"]["do_not_run_external_command_from_continuation_prompt"] is True


def test_manual_handoff_writes_local_only_html_without_upload_automation(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-10T08:10:00+09:00")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["queue"][0]["caption"] = "do not leak full caption into handoff"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "handoff.json"
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    def fail_prepare_upload(*args, **kwargs):
        raise AssertionError("manual handoff must not call upload automation")

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fail_prepare_upload)

    result = publish_queue_runner.create_manual_handoff(
        queue_path,
        output_path=output_path,
        now=now,
    )

    html_path = output_path.with_suffix(".html")
    assert result["ok"] is True
    assert result["status"] == "local_review_only_no_platform_action"
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    assert result["public_posting_performed"] is False
    assert result["rules"]["no_external_browser_automation"] is True
    assert result["rows"][0]["caption_present"] is True
    assert "caption" not in result["rows"][0]
    assert output_path.exists()
    assert html_path.exists()
    assert "do not leak full caption" not in output_path.read_text(encoding="utf-8")
    assert "do not leak full caption" not in html_path.read_text(encoding="utf-8")


def test_preflight_ready_queue_writes_packet_and_runs_dry_run(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-10T08:10:00+09:00")
    output_path = tmp_path / "preflight.json"
    now = dt.datetime(2026, 6, 9, 18, 45, tzinfo=ZoneInfo("Asia/Seoul"))
    calls = []

    def fake_prepare_upload(manifest_path, **kwargs):
        calls.append((manifest_path, kwargs))
        return {"ok": True, "dry_run": kwargs["dry_run"], "job": {"run_id": "leftaino_test"}}

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fake_prepare_upload)

    result = publish_queue_runner.run_preflight(
        queue_path,
        output_path=output_path,
        now=now,
    )

    assert result["ok"] is True
    assert result["rollover_applied"] is False
    assert result["final_queue_path"] == str(queue_path.resolve())
    assert result["dry_run_ok"] is True
    assert result["tiktok_upload_performed"] is False
    assert result["schedule_click_performed"] is False
    assert len(calls) == 1
    assert calls[0][1]["dry_run"] is True
    assert output_path.exists()
    assert output_path.with_suffix(".md").exists()
    assert Path(result["packet_path"]).exists()


def test_preflight_rolls_over_past_queue_before_packet(tmp_path, monkeypatch):
    queue_path = _write_queue(tmp_path, planned_at="2026-06-09T08:10:00+09:00")
    output_path = tmp_path / "preflight.json"
    now = dt.datetime(2026, 6, 9, 19, 45, tzinfo=ZoneInfo("Asia/Seoul"))

    def fake_prepare_upload(manifest_path, **kwargs):
        return {"ok": True, "dry_run": kwargs["dry_run"], "job": {"run_id": "leftaino_test"}}

    monkeypatch.setattr(publish_queue_runner.upload_automation, "prepare_upload", fake_prepare_upload)

    result = publish_queue_runner.run_preflight(
        queue_path,
        output_path=output_path,
        now=now,
    )

    assert result["ok"] is True
    assert result["rollover_applied"] is True
    assert result["rollover_queue_path"] is not None
    assert result["final_queue_path"] == result["rollover_queue_path"]
    assert result["final_audit"]["ready_to_schedule_after_explicit_owner_instruction"] is True
    assert result["dry_run_ok"] is True
    rolled = json.loads(Path(result["rollover_queue_path"]).read_text(encoding="utf-8"))
    assert rolled["queue"][0]["planned_publish_at_local"] == "2026-06-10T08:10:00+09:00"
