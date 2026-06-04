"""High-availability job and lease orchestration for AiNo TikTok publishing.

This module coordinates generation, browser-upload preparation, scheduling
evidence, and monitoring across the Neo Genesis device fleet. It does not
attempt to bypass TikTok security checks and it does not click a final post
button by itself; upload execution is delegated to upload_automation.py.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import shlex
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[2]
CONFIG_DIR = PACKAGE_DIR / "config"
DEFAULT_OUTPUT_DIR = REPO_DIR / "output" / "tiktok_aino"
CONFIG_PATH = CONFIG_DIR / "ha_strategy.json"
LOCK_FILENAME = "state.lock"
JOBS_FILENAME = "jobs.json"
LEASES_FILENAME = "leases.json"
NODES_FILENAME = "nodes.json"
EVENTS_FILENAME = "events.jsonl"
DEFAULT_OPERATION_STATUSES = {
    "generate": ["planned"],
    "upload": ["generated", "upload_retry"],
    "monitor": ["scheduled", "published"],
}


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


HA_STRATEGY = _load_config()


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _iso(value: dt.datetime | None = None) -> str:
    return (value or _now_utc()).isoformat()


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def upload_result_confirms_scheduled(result: dict[str, Any]) -> bool:
    verification = result.get("schedule_verification")
    if not isinstance(verification, dict):
        return False
    return bool(
        result.get("ok")
        and result.get("schedule_click_performed")
        and verification.get("ok")
        and verification.get("contains_topic") is not False
        and verification.get("contains_time") is not False
    )


def _stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _repo_relative_or_absolute(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_DIR / path


def default_state_dir() -> Path:
    configured = os.environ.get("AINO_HA_STATE_DIR") or str(HA_STRATEGY.get("local_state_dir", "output/tiktok_aino_ha_state"))
    return _repo_relative_or_absolute(configured)


def default_artifact_cache_dir() -> Path:
    configured = os.environ.get("AINO_ARTIFACT_CACHE_DIR") or str(
        HA_STRATEGY.get("artifact_cache_dir", "output/tiktok_aino_worker_cache")
    )
    return _repo_relative_or_absolute(configured)


def default_node_id() -> str:
    configured = os.environ.get("AINO_NODE_ID")
    if configured:
        return configured
    hostname = socket.gethostname().lower()
    for node in HA_STRATEGY.get("nodes", []):
        node_id = str(node.get("node_id", ""))
        if node_id and node_id.lower() in hostname:
            return node_id
    if "desktop-home" in hostname:
        return "desktop-home"
    return hostname or platform.node() or "unknown-node"


def _terminal_statuses() -> set[str]:
    return {str(item) for item in HA_STRATEGY.get("terminal_statuses", [])}


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _operation_ttl(operation: str) -> int:
    ttls = HA_STRATEGY.get("lease_ttl_seconds", {})
    return _safe_int(ttls.get(operation), 900) if isinstance(ttls, dict) else 900


def _operation_max_attempts(operation: str) -> int:
    attempts = HA_STRATEGY.get("max_attempts", {})
    return _safe_int(attempts.get(operation), 3) if isinstance(attempts, dict) else 3


def _operation_lead_hours(operation: str) -> int:
    key = f"{operation}_claim_lead_hours"
    return _safe_int(HA_STRATEGY.get(key), 168)


def _upload_past_grace_hours() -> int:
    return _safe_int(HA_STRATEGY.get("upload_past_grace_hours"), 24)


def _plan_enforces_future_slots(plan: dict[str, Any]) -> bool:
    return bool(plan.get("created_at") or plan.get("timezone") or plan.get("mode"))


def _job_has_explicit_publish_time(job: dict[str, Any]) -> bool:
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    if payload.get("has_planned_publish_at") is True:
        return True
    slot = payload.get("slot") if isinstance(payload.get("slot"), dict) else {}
    return bool(
        job.get("publish_at_local")
        and (
            slot.get("publish_at_local")
            or job.get("planned_publish_at_local")
            or job.get("kind") == "publish_slot"
        )
    )


def _planned_time_is_past(value: str | None) -> bool:
    planned = _parse_iso(value)
    return bool(planned and planned <= _now_utc())


def _slot_enqueue_blockers(slot: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _plan_enforces_future_slots(plan) and _planned_time_is_past(str(slot.get("publish_at_local") or "")):
        blockers.append("publish_time_in_past")
    if slot.get("ready_for_generation") is not True:
        blockers.append("slot_not_ready_for_generation")
    return blockers


def _monitor_cadence_hours() -> list[int]:
    raw = HA_STRATEGY.get("monitor_cadence_hours", [24])
    if not isinstance(raw, list):
        return [24]
    values = sorted({_safe_int(item, 0) for item in raw if _safe_int(item, 0) > 0})
    return values or [24]


def _monitor_completed_windows(job: dict[str, Any]) -> list[int]:
    candidates: list[Any] = []
    if isinstance(job.get("monitor_windows_completed"), list):
        candidates.extend(job["monitor_windows_completed"])
    evidence = job.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("monitor_windows_completed"), list):
        candidates.extend(evidence["monitor_windows_completed"])
    return sorted({_safe_int(item, -1) for item in candidates if _safe_int(item, -1) >= 0})


def _monitor_reference_time(job: dict[str, Any]) -> dt.datetime | None:
    evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    keys = [
        "published_at",
        "scheduled_at",
        "publish_at_local",
        "planned_publish_at_local",
        "updated_at",
        "created_at",
    ]
    for key in keys:
        value = job.get(key)
        if not value and isinstance(evidence, dict):
            value = evidence.get(key)
        parsed = _parse_iso(str(value or ""))
        if parsed:
            return parsed
    return None


def _monitor_next_due_at(job: dict[str, Any], *, now: dt.datetime | None = None) -> dt.datetime | None:
    explicit = _parse_iso(str(job.get("next_monitor_at") or ""))
    if explicit:
        return explicit
    evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    explicit_evidence = _parse_iso(str(evidence.get("next_monitor_at") or "")) if isinstance(evidence, dict) else None
    if explicit_evidence:
        return explicit_evidence
    base = _monitor_reference_time(job)
    if base is None:
        return None
    completed = set(_monitor_completed_windows(job))
    for hour in _monitor_cadence_hours():
        if hour not in completed:
            return base + dt.timedelta(hours=hour)
    return None


def _monitor_due_window(job: dict[str, Any], *, now: dt.datetime | None = None) -> tuple[int | None, dt.datetime | None, dt.datetime | None]:
    active_now = now or _now_utc()
    base = _monitor_reference_time(job)
    if base is None:
        return None, None, None
    completed = set(_monitor_completed_windows(job))
    pending = [hour for hour in _monitor_cadence_hours() if hour not in completed]
    for hour in pending:
        due_at = base + dt.timedelta(hours=hour)
        if due_at <= active_now:
            remaining = [candidate for candidate in pending if candidate != hour]
            next_due = base + dt.timedelta(hours=remaining[0]) if remaining else None
            return hour, due_at, next_due
        return None, due_at, due_at
    return None, None, None


def _state_defaults() -> dict[str, Any]:
    return {
        JOBS_FILENAME: {"schema_version": 1, "jobs": {}},
        LEASES_FILENAME: {"schema_version": 1, "leases": {}},
        NODES_FILENAME: {"schema_version": 1, "nodes": {}},
    }


class FileStateStore:
    """Small JSON state store with an atomic lock.

    The store is intentionally file-based so it can live on the active control
    workstation and later be moved to a verified replacement host without
    requiring a new database. The lock is safe for one filesystem; remote
    workers should call this script on the control-tower filesystem instead of
    editing copies.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in _state_defaults().items():
            path = self.state_dir / filename
            if not path.exists():
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @contextlib.contextmanager
    def locked(self, *, timeout_seconds: int = 15, lock_ttl_seconds: int = 60) -> Iterator[None]:
        lock_path = self.state_dir / LOCK_FILENAME
        deadline = time.time() + timeout_seconds
        token = f"{os.getpid()}-{uuid.uuid4().hex}"
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    file.write(json.dumps({"token": token, "created_at": _iso(), "expires_at": _iso(_now_utc() + dt.timedelta(seconds=lock_ttl_seconds))}))
                break
            except FileExistsError:
                if self._lock_expired(lock_path):
                    with contextlib.suppress(FileNotFoundError):
                        lock_path.unlink()
                    continue
                if time.time() >= deadline:
                    raise TimeoutError(f"Timed out waiting for HA state lock: {lock_path}")
                time.sleep(0.2)
        try:
            yield
        finally:
            with contextlib.suppress(FileNotFoundError):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                if data.get("token") == token:
                    lock_path.unlink()

    @staticmethod
    def _lock_expired(lock_path: Path) -> bool:
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            return True
        expires_at = _parse_iso(str(data.get("expires_at", "")))
        return bool(expires_at and expires_at <= _now_utc())

    def read(self, filename: str) -> dict[str, Any]:
        path = self.state_dir / filename
        if not path.exists():
            return dict(_state_defaults().get(filename, {}))
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError(f"HA state file must contain an object: {path}")
        return data

    def write(self, filename: str, data: dict[str, Any]) -> None:
        path = self.state_dir / filename
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def append_event(self, event: dict[str, Any]) -> None:
        event = {"created_at": _iso(), **event}
        path = self.state_dir / EVENTS_FILENAME
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")


def _job_history(job: dict[str, Any], event: str, **details: Any) -> None:
    history = job.setdefault("history", [])
    if isinstance(history, list):
        history.append({"at": _iso(), "event": event, **details})


@contextlib.contextmanager
def _temporary_env(name: str, value: str | None) -> Iterator[None]:
    previous = os.environ.get(name)
    if value is not None:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _job_id_from_parts(publish_at_local: str, content_format: str, topic: str) -> str:
    del topic
    day_minute = publish_at_local.replace("-", "").replace(":", "").replace("+", "_").replace("T", "_")[:18]
    return f"leftaino_{day_minute}_{content_format}"


def _normalized_content_text(*parts: Any) -> str:
    text = " ".join(str(part or "") for part in parts)
    text = re.sub(r"\s+", "", text.casefold())
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def _content_fingerprint(*parts: Any) -> str:
    normalized = _normalized_content_text(*parts)
    return _stable_hash(normalized or "empty-content", length=16)


def _duplicate_guard_enabled() -> bool:
    guard = HA_STRATEGY.get("duplicate_guard", {})
    return not isinstance(guard, dict) or bool(guard.get("enabled", True))


def _duplicate_guard_statuses() -> set[str]:
    guard = HA_STRATEGY.get("duplicate_guard", {})
    if not isinstance(guard, dict):
        return {"planned", "generated", "upload_retry", "uploading", "scheduled", "published"}
    raw = guard.get("active_statuses", [])
    if not isinstance(raw, list):
        return {"planned", "generated", "upload_retry", "uploading", "scheduled", "published"}
    return {str(item) for item in raw if str(item).strip()}


def _job_content_fingerprint(job: dict[str, Any]) -> str:
    existing = str(job.get("content_fingerprint") or "")
    if existing:
        return existing
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    slot = payload.get("slot") if isinstance(payload.get("slot"), dict) else {}
    script = payload.get("script") if isinstance(payload.get("script"), dict) else {}
    return _content_fingerprint(
        job.get("topic"),
        slot.get("post_title"),
        script.get("post_title"),
        script.get("caption"),
    )


def _find_duplicate_job(jobs: dict[str, Any], job: dict[str, Any]) -> dict[str, Any] | None:
    if not _duplicate_guard_enabled():
        return None
    fingerprint = _job_content_fingerprint(job)
    statuses = _duplicate_guard_statuses()
    for existing in jobs.values():
        if not isinstance(existing, dict):
            continue
        if existing.get("job_id") == job.get("job_id"):
            continue
        if str(existing.get("status") or "") not in statuses:
            continue
        if _job_content_fingerprint(existing) == fingerprint:
            return existing
    return None


def _job_from_slot(slot: dict[str, Any], plan_path: Path, slot_index: int) -> dict[str, Any]:
    publish_at = str(slot.get("publish_at_local", ""))
    content_format = str(slot.get("format") or "auto")
    topic = str(slot.get("topic") or slot.get("post_title") or "planned-topic")
    job_id = _job_id_from_parts(publish_at, content_format, topic)
    return {
        "job_id": job_id,
        "kind": "publish_slot",
        "status": "planned",
        "channel": "leftaino",
        "publish_at_local": publish_at,
        "format": content_format,
        "topic": topic,
        "content_fingerprint": _content_fingerprint(topic, slot.get("post_title"), slot.get("caption")),
        "priority": _safe_int(slot.get("quality_score"), 0),
        "attempts": {},
        "payload": {
            "plan_path": str(plan_path),
            "slot_index": slot_index,
            "slot": slot,
        },
        "created_at": _iso(),
        "updated_at": _iso(),
        "history": [{"at": _iso(), "event": "planned_from_schedule"}],
    }


def _job_from_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest.get("artifacts"), dict) else {}
    script = manifest.get("script", {}) if isinstance(manifest.get("script"), dict) else {}
    format_plan = manifest.get("format_plan", {}) if isinstance(manifest.get("format_plan"), dict) else {}
    from src.core.tiktok_aino import pipeline

    validation = pipeline.validate_manifest_for_upload(manifest)
    job_status = "generated" if validation.get("publish_ready") else "needs_revision"
    run_id = str(manifest.get("run_id") or manifest_path.parent.name)
    publish_at = str(manifest.get("planned_publish_at_local") or "")
    has_planned_publish_at = bool(publish_at)
    content_format = str(format_plan.get("format_id") or manifest.get("content_format") or "auto")
    topic = str(manifest.get("topic", {}).get("title") if isinstance(manifest.get("topic"), dict) else "") or str(script.get("post_title") or run_id)
    if not publish_at:
        publish_at = _iso()
    job_id = _job_id_from_parts(publish_at, content_format, topic)
    return {
        "job_id": job_id,
        "kind": "publish_slot",
        "status": job_status,
        "channel": "leftaino",
        "publish_at_local": publish_at,
        "format": content_format,
        "topic": topic,
        "content_fingerprint": _content_fingerprint(
            topic,
            script.get("post_title"),
            script.get("caption"),
            script.get("post_body"),
            script.get("pinned_comment"),
        ),
        "priority": _safe_int(manifest.get("quality", {}).get("publish_ready_score") if isinstance(manifest.get("quality"), dict) else 0, 0),
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "run_dir": str(manifest_path.parent),
        "mp4_path": str(artifacts.get("mp4", "")),
        "artifact_node": default_node_id(),
        "schedule_status": manifest.get("schedule_status"),
        "attempts": {},
        "payload": {
            "manifest_status": manifest.get("status"),
            "upload_validation": validation,
            "has_planned_publish_at": has_planned_publish_at,
        },
        "created_at": _iso(),
        "updated_at": _iso(),
        "history": [{"at": _iso(), "event": "generated_manifest_enqueued"}],
    }


def _refresh_planned_job(existing: dict[str, Any], job: dict[str, Any], *, plan_path: Path) -> dict[str, Any]:
    preserved = {
        **existing,
        **{key: value for key, value in job.items() if key not in {"attempts", "created_at", "history", "status"}},
    }
    preserved["status"] = existing.get("status", "planned")
    preserved["attempts"] = existing.get("attempts", {})
    preserved["created_at"] = existing.get("created_at", job.get("created_at"))
    preserved["updated_at"] = _iso()
    _job_history(preserved, "plan_refreshed", plan_path=str(plan_path))
    return preserved


def heartbeat(state_dir: Path, *, node_id: str, capabilities: list[str] | None = None) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    payload = {
        "node_id": node_id,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "capabilities": capabilities or [],
        "last_seen_at": _iso(),
    }
    with store.locked():
        nodes = store.read(NODES_FILENAME)
        existing = nodes.setdefault("nodes", {}).get(node_id, {})
        existing_caps = existing.get("capabilities", []) if isinstance(existing, dict) else []
        payload["capabilities"] = sorted({*list(existing_caps or []), *(capabilities or [])})
        nodes.setdefault("nodes", {})[node_id] = payload
        store.write(NODES_FILENAME, nodes)
        store.append_event({"event": "node_heartbeat", "node_id": node_id, "capabilities": capabilities or []})
    return payload


def enqueue_plan(state_dir: Path, plan_path: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    slots = [slot for slot in plan.get("slots", []) if isinstance(slot, dict) and slot.get("ready_for_generation")]
    store = FileStateStore(state_dir)
    created: list[str] = []
    refreshed: list[str] = []
    unchanged: list[str] = []
    blocked: list[dict[str, str]] = []
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        jobs = jobs_doc.setdefault("jobs", {})
        for index, slot in enumerate(slots, start=1):
            job = _job_from_slot(slot, plan_path, index)
            enqueue_blockers = _slot_enqueue_blockers(slot, plan)
            if enqueue_blockers:
                blocked.append(
                    {
                        "job_id": job["job_id"],
                        "reason": "enqueue_plan_gate_failed",
                        "blockers": ",".join(enqueue_blockers),
                    }
                )
                store.append_event(
                    {
                        "event": "job_blocked",
                        "job_id": job["job_id"],
                        "source": "plan",
                        "reason": "enqueue_plan_gate_failed",
                        "blockers": enqueue_blockers,
                    }
                )
                continue
            existing = jobs.get(job["job_id"])
            if existing and existing.get("status") in _terminal_statuses():
                unchanged.append(job["job_id"])
                continue
            if existing:
                existing_payload = existing.get("payload") if isinstance(existing.get("payload"), dict) else {}
                existing_plan_path = str(existing_payload.get("plan_path") or "")
                should_refresh_plan = (
                    existing.get("status") == "planned"
                    and (
                        _job_content_fingerprint(existing) != _job_content_fingerprint(job)
                        or existing_plan_path != str(plan_path)
                    )
                )
                if should_refresh_plan:
                    jobs[job["job_id"]] = _refresh_planned_job(existing, job, plan_path=plan_path)
                    refreshed.append(job["job_id"])
                    store.append_event({"event": "job_refreshed", "job_id": job["job_id"], "source": "plan"})
                else:
                    unchanged.append(job["job_id"])
                continue
            duplicate = _find_duplicate_job(jobs, job)
            if duplicate:
                blocked.append(
                    {
                        "job_id": job["job_id"],
                        "reason": "duplicate_content",
                        "duplicate_job_id": str(duplicate.get("job_id") or ""),
                        "duplicate_run_id": str(duplicate.get("run_id") or ""),
                    }
                )
                store.append_event(
                    {
                        "event": "job_blocked",
                        "job_id": job["job_id"],
                        "source": "plan",
                        "reason": "duplicate_content",
                        "duplicate_job_id": duplicate.get("job_id"),
                    }
                )
                continue
            jobs[job["job_id"]] = job
            created.append(job["job_id"])
            store.append_event({"event": "job_enqueued", "job_id": job["job_id"], "source": "plan"})
        jobs_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
    return {
        "created": created,
        "refreshed": refreshed,
        "unchanged": unchanged,
        "blocked": blocked,
        "plan_path": str(plan_path),
        "ready_slots": len(slots),
    }


def enqueue_manifest(state_dir: Path, manifest_path: Path) -> dict[str, Any]:
    job = _job_from_manifest(manifest_path)
    enqueue_blockers: list[str] = []
    if job.get("status") != "generated":
        enqueue_blockers.append("manifest_not_publish_ready")
    if _job_has_explicit_publish_time(job) and _planned_time_is_past(str(job.get("publish_at_local") or "")):
        enqueue_blockers.append("publish_time_in_past")
    if enqueue_blockers:
        return {
            "created": False,
            "blocked": True,
            "reason": "enqueue_manifest_gate_failed",
            "blockers": enqueue_blockers,
            "job_id": job["job_id"],
            "run_id": job.get("run_id"),
            "status": job.get("status") or "blocked",
        }
    store = FileStateStore(state_dir)
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        jobs = jobs_doc.setdefault("jobs", {})
        existing = jobs.get(job["job_id"])
        if existing and existing.get("status") in _terminal_statuses():
            return {"created": False, "unchanged": True, "job_id": job["job_id"], "status": existing.get("status")}
        if existing:
            preserved = {**existing, **{k: v for k, v in job.items() if k not in {"created_at", "history", "attempts"}}}
            preserved["attempts"] = existing.get("attempts", {})
            _job_history(preserved, "manifest_refreshed", manifest_path=str(manifest_path))
            jobs[job["job_id"]] = preserved
            created = False
        else:
            duplicate = _find_duplicate_job(jobs, job)
            if duplicate:
                store.append_event(
                    {
                        "event": "job_blocked",
                        "job_id": job["job_id"],
                        "source": "manifest",
                        "reason": "duplicate_content",
                        "duplicate_job_id": duplicate.get("job_id"),
                        "duplicate_run_id": duplicate.get("run_id"),
                    }
                )
                return {
                    "created": False,
                    "blocked": True,
                    "reason": "duplicate_content",
                    "job_id": job["job_id"],
                    "duplicate_job_id": duplicate.get("job_id"),
                    "duplicate_run_id": duplicate.get("run_id"),
                    "status": "blocked",
                }
            jobs[job["job_id"]] = job
            created = True
        jobs_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.append_event({"event": "job_enqueued", "job_id": job["job_id"], "source": "manifest", "created": created})
    return {"created": created, "job_id": job["job_id"], "status": job["status"]}


def reclaim_stale_leases(state_dir: Path) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    reclaimed: list[str] = []
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        jobs = jobs_doc.setdefault("jobs", {})
        leases = leases_doc.setdefault("leases", {})
        for lease_id, lease in list(leases.items()):
            if lease.get("status") != "active":
                continue
            expires_at = _parse_iso(str(lease.get("expires_at", "")))
            if not expires_at or expires_at > _now_utc():
                continue
            lease["status"] = "expired"
            lease["expired_at"] = _iso()
            job = jobs.get(str(lease.get("job_id")))
            if isinstance(job, dict) and job.get("status") not in _terminal_statuses():
                job["status"] = str(lease.get("previous_status") or "planned")
                job["lease_id"] = None
                job["claimed_by"] = None
                job["updated_at"] = _iso()
                _job_history(job, "lease_expired_reclaimed", lease_id=lease_id, previous_status=lease.get("previous_status"))
            reclaimed.append(lease_id)
            store.append_event({"event": "lease_expired", "lease_id": lease_id, "job_id": lease.get("job_id")})
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
    return {"reclaimed": reclaimed, "count": len(reclaimed)}


def release_node_leases(state_dir: Path, *, node_id: str, operation: str | None = None) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    released: list[str] = []
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        jobs = jobs_doc.setdefault("jobs", {})
        for lease_id, lease in leases_doc.setdefault("leases", {}).items():
            if lease.get("status") != "active" or lease.get("node_id") != node_id:
                continue
            if operation and lease.get("operation") != operation:
                continue
            lease["status"] = "released"
            lease["released_at"] = _iso()
            job = jobs.get(str(lease.get("job_id")))
            if isinstance(job, dict) and job.get("status") not in _terminal_statuses():
                job["status"] = str(lease.get("previous_status") or "planned")
                job["lease_id"] = None
                job["claimed_by"] = None
                job["updated_at"] = _iso()
                _job_history(job, "node_lease_released", lease_id=lease_id, node_id=node_id, operation=lease.get("operation"))
            released.append(lease_id)
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
    return {"released": released, "count": len(released), "node_id": node_id, "operation": operation}


def _job_claimable(job: dict[str, Any], operation: str, *, lead_hours: int) -> bool:
    if job.get("status") not in DEFAULT_OPERATION_STATUSES.get(operation, []):
        return False
    if operation != "monitor" and job.get("status") in _terminal_statuses():
        return False
    if operation == "monitor":
        next_due = _monitor_next_due_at(job)
        return bool(next_due and next_due <= _now_utc())
    publish_at = _parse_iso(str(job.get("publish_at_local", "")))
    if publish_at and publish_at > _now_utc() + dt.timedelta(hours=lead_hours):
        return False
    if operation == "upload" and _job_has_explicit_publish_time(job) and publish_at and publish_at <= _now_utc():
        return False
    return True


def claim_next_job(state_dir: Path, *, node_id: str, operation: str, lead_hours: int | None = None) -> dict[str, Any]:
    if os.environ.get(str(HA_STRATEGY.get("kill_switch_env", "AINO_HA_ENABLED")), "true").lower() in {"0", "false", "off", "no"}:
        return {"ok": False, "reason": "ha_disabled_by_env"}
    if operation not in DEFAULT_OPERATION_STATUSES:
        raise ValueError(f"unknown operation: {operation}")
    reclaim_stale_leases(state_dir)
    store = FileStateStore(state_dir)
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        jobs = jobs_doc.setdefault("jobs", {})
        active_same_node = [
            lease
            for lease in leases_doc.setdefault("leases", {}).values()
            if isinstance(lease, dict)
            and lease.get("status") == "active"
            and lease.get("node_id") == node_id
            and lease.get("operation") == operation
        ]
        if active_same_node:
            return {"ok": False, "reason": "node_already_has_active_lease", "operation": operation, "lease": active_same_node[0]}
        lead = _operation_lead_hours(operation) if lead_hours is None else lead_hours
        candidates = [
            job
            for job in jobs.values()
            if isinstance(job, dict) and _job_claimable(job, operation, lead_hours=lead)
        ]
        candidates.sort(
            key=lambda item: (
                str(item.get("publish_at_local") or ""),
                -_safe_int(item.get("priority"), 0),
                str(item.get("job_id") or ""),
            )
        )
        if not candidates:
            return {"ok": False, "reason": "no_claimable_job", "operation": operation}
        job = candidates[0]
        job_id = str(job["job_id"])
        previous_status = str(job.get("status") or "")
        lease_id = f"{operation}_{node_id}_{_now_utc():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}"
        expires_at = _now_utc() + dt.timedelta(seconds=_operation_ttl(operation))
        attempts = job.setdefault("attempts", {})
        attempts[operation] = _safe_int(attempts.get(operation), 0) + 1
        job["status"] = {"generate": "generating", "upload": "uploading", "monitor": "monitoring"}[operation]
        job["claimed_by"] = node_id
        job["lease_id"] = lease_id
        job["updated_at"] = _iso()
        _job_history(job, "claimed", operation=operation, node_id=node_id, lease_id=lease_id)
        leases_doc.setdefault("leases", {})[lease_id] = {
            "lease_id": lease_id,
            "job_id": job_id,
            "operation": operation,
            "node_id": node_id,
            "status": "active",
            "previous_status": previous_status,
            "created_at": _iso(),
            "heartbeat_at": _iso(),
            "expires_at": _iso(expires_at),
        }
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
        store.append_event({"event": "job_claimed", "job_id": job_id, "operation": operation, "node_id": node_id, "lease_id": lease_id})
        return {"ok": True, "job": job, "lease": leases_doc["leases"][lease_id]}


def preview_next_job(state_dir: Path, *, node_id: str, operation: str, lead_hours: int | None = None) -> dict[str, Any]:
    if os.environ.get(str(HA_STRATEGY.get("kill_switch_env", "AINO_HA_ENABLED")), "true").lower() in {"0", "false", "off", "no"}:
        return {"ok": False, "reason": "ha_disabled_by_env"}
    if operation not in DEFAULT_OPERATION_STATUSES:
        raise ValueError(f"unknown operation: {operation}")
    store = FileStateStore(state_dir)
    jobs_doc = store.read(JOBS_FILENAME)
    leases_doc = store.read(LEASES_FILENAME)
    active_same_node = [
        lease
        for lease in leases_doc.setdefault("leases", {}).values()
        if isinstance(lease, dict)
        and lease.get("status") == "active"
        and lease.get("node_id") == node_id
        and lease.get("operation") == operation
    ]
    if active_same_node:
        return {"ok": False, "reason": "node_already_has_active_lease", "operation": operation, "lease": active_same_node[0]}
    lead = _operation_lead_hours(operation) if lead_hours is None else lead_hours
    candidates = [
        job
        for job in jobs_doc.setdefault("jobs", {}).values()
        if isinstance(job, dict) and _job_claimable(job, operation, lead_hours=lead)
    ]
    candidates.sort(
        key=lambda item: (
            str(item.get("publish_at_local") or ""),
            -_safe_int(item.get("priority"), 0),
            str(item.get("job_id") or ""),
        )
    )
    if not candidates:
        return {"ok": False, "reason": "no_claimable_job", "operation": operation}
    return {
        "ok": True,
        "job": candidates[0],
        "lease": {
            "operation": operation,
            "node_id": node_id,
            "status": "dry_run_preview",
            "previous_status": candidates[0].get("status"),
        },
    }


def lease_heartbeat(state_dir: Path, *, lease_id: str, node_id: str) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    with store.locked():
        leases_doc = store.read(LEASES_FILENAME)
        lease = leases_doc.setdefault("leases", {}).get(lease_id)
        if not isinstance(lease, dict):
            return {"ok": False, "reason": "lease_not_found"}
        if lease.get("node_id") != node_id:
            return {"ok": False, "reason": "lease_owner_mismatch"}
        lease["heartbeat_at"] = _iso()
        lease["expires_at"] = _iso(_now_utc() + dt.timedelta(seconds=_operation_ttl(str(lease.get("operation")))))
        leases_doc["updated_at"] = _iso()
        store.write(LEASES_FILENAME, leases_doc)
    return {"ok": True, "lease_id": lease_id, "expires_at": lease["expires_at"]}


def complete_lease(state_dir: Path, *, lease_id: str, node_id: str, status: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    evidence = evidence or {}
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        leases = leases_doc.setdefault("leases", {})
        lease = leases.get(lease_id)
        if not isinstance(lease, dict):
            return {"ok": False, "reason": "lease_not_found"}
        if lease.get("node_id") != node_id:
            return {"ok": False, "reason": "lease_owner_mismatch"}
        jobs = jobs_doc.setdefault("jobs", {})
        job = jobs.get(str(lease.get("job_id")))
        if not isinstance(job, dict):
            return {"ok": False, "reason": "job_not_found"}
        lease["status"] = "completed"
        lease["completed_at"] = _iso()
        lease["completion_status"] = status
        job["status"] = status
        job["lease_id"] = None
        job["claimed_by"] = None
        job["updated_at"] = _iso()
        if status in {"generated", "scheduled", "published", "upload_prepared"}:
            job.pop("last_error", None)
        if evidence:
            job.setdefault("evidence", {}).update(evidence)
            for key in (
                "run_id",
                "manifest_path",
                "run_dir",
                "mp4_path",
                "artifact_node",
                "schedule_status",
                "published_url",
                "next_monitor_at",
                "last_monitor_at",
                "monitor_windows_completed",
                "performance_report_path",
                "performance_dashboard_path",
                "performance_feedback_path",
                "performance_feedback_latest_path",
            ):
                if key in evidence and evidence[key]:
                    job[key] = evidence[key]
        _job_history(job, "completed", lease_id=lease_id, status=status, evidence=evidence)
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
        store.append_event({"event": "job_completed", "job_id": job.get("job_id"), "lease_id": lease_id, "status": status})
    return {"ok": True, "lease_id": lease_id, "status": status}


def fail_lease(state_dir: Path, *, lease_id: str, node_id: str, error: str) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        lease = leases_doc.setdefault("leases", {}).get(lease_id)
        if not isinstance(lease, dict):
            return {"ok": False, "reason": "lease_not_found"}
        if lease.get("node_id") != node_id:
            return {"ok": False, "reason": "lease_owner_mismatch"}
        job = jobs_doc.setdefault("jobs", {}).get(str(lease.get("job_id")))
        if not isinstance(job, dict):
            return {"ok": False, "reason": "job_not_found"}
        operation = str(lease.get("operation"))
        attempts = _safe_int(job.get("attempts", {}).get(operation) if isinstance(job.get("attempts"), dict) else 0, 0)
        retryable = attempts < _operation_max_attempts(operation)
        job["status"] = str(lease.get("previous_status") or "planned") if retryable else "blocked"
        job["lease_id"] = None
        job["claimed_by"] = None
        job["last_error"] = error[:1000]
        job["updated_at"] = _iso()
        lease["status"] = "failed"
        lease["failed_at"] = _iso()
        lease["error"] = error[:1000]
        _job_history(job, "failed", lease_id=lease_id, operation=operation, retryable=retryable, error=error[:1000])
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
        store.append_event({"event": "job_failed", "job_id": job.get("job_id"), "operation": operation, "retryable": retryable})
    return {"ok": True, "retryable": retryable, "status": job["status"]}


def defer_lease(state_dir: Path, *, lease_id: str, node_id: str, reason: str) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    with store.locked():
        jobs_doc = store.read(JOBS_FILENAME)
        leases_doc = store.read(LEASES_FILENAME)
        lease = leases_doc.setdefault("leases", {}).get(lease_id)
        if not isinstance(lease, dict):
            return {"ok": False, "reason": "lease_not_found"}
        if lease.get("node_id") != node_id:
            return {"ok": False, "reason": "lease_owner_mismatch"}
        job = jobs_doc.setdefault("jobs", {}).get(str(lease.get("job_id")))
        if not isinstance(job, dict):
            return {"ok": False, "reason": "job_not_found"}
        operation = str(lease.get("operation"))
        attempts = job.setdefault("attempts", {})
        if isinstance(attempts, dict):
            attempts[operation] = max(0, _safe_int(attempts.get(operation), 0) - 1)
        job["status"] = str(lease.get("previous_status") or "planned")
        job["lease_id"] = None
        job["claimed_by"] = None
        job["last_error"] = reason[:1000]
        job["updated_at"] = _iso()
        lease["status"] = "deferred"
        lease["deferred_at"] = _iso()
        lease["reason"] = reason[:1000]
        _job_history(job, "deferred", lease_id=lease_id, operation=operation, reason=reason[:1000])
        jobs_doc["updated_at"] = _iso()
        leases_doc["updated_at"] = _iso()
        store.write(JOBS_FILENAME, jobs_doc)
        store.write(LEASES_FILENAME, leases_doc)
        store.append_event({"event": "job_deferred", "job_id": job.get("job_id"), "operation": operation})
    return {"ok": True, "status": job["status"]}


def _generate_for_job(job: dict[str, Any], *, output_dir: Path, image_mode: str, real_image_limit: int) -> dict[str, Any]:
    from src.core.tiktok_aino import generate_from_schedule, pipeline

    payload = job.get("payload", {}) if isinstance(job.get("payload"), dict) else {}
    slot = payload.get("slot")
    if not isinstance(slot, dict):
        plan_path = Path(str(payload.get("plan_path", "")))
        slot_index = _safe_int(payload.get("slot_index"), 0)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        slot = plan["slots"][slot_index - 1]
    slot_index = _safe_int(payload.get("slot_index"), 1)
    topic, sources = generate_from_schedule._topic_from_slot(slot, slot_index)
    slot_discovery = slot.get("topic_discovery") if isinstance(slot.get("topic_discovery"), dict) else {}
    result = pipeline.run_for_topic(
        topic,
        sources,
        output_dir=output_dir,
        image_mode=image_mode,
        real_image_limit=real_image_limit,
        content_format=str(slot.get("format") or "auto"),
        topic_discovery={
            **slot_discovery,
            "mode": "ha_publisher",
            "job_id": job.get("job_id"),
            "plan_path": str(payload.get("plan_path") or ""),
            "slot_index": slot_index,
            "slot_publish_at_local": slot.get("publish_at_local"),
        },
        planned_publish_at_local=str(slot.get("publish_at_local", "")),
    )
    manifest_path = Path(result.artifacts.manifest_json)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = pipeline.validate_manifest_for_upload(manifest)
    review = manifest.get("review", {}) if isinstance(manifest.get("review"), dict) else {}
    quality = manifest.get("quality", {}) if isinstance(manifest.get("quality"), dict) else {}
    return {
        "run_id": result.run_id,
        "manifest_path": str(manifest_path),
        "run_dir": str(manifest_path.parent),
        "mp4_path": result.artifacts.mp4,
        "artifact_node": default_node_id(),
        "manifest_status": validation["status"],
        "raw_manifest_status": manifest.get("status"),
        "upload_validation": validation,
        "schedule_status": manifest.get("schedule_status"),
        "quality_score": result.quality.publish_ready_score,
        "review": result.review.recommendation,
        "review_blockers": review.get("blockers", []),
        "quality_blockers": quality.get("blockers", []),
    }


def materialize_artifacts(job: dict[str, Any], *, cache_dir: Path, control_ssh: str | None = None) -> dict[str, Any]:
    manifest_path = Path(str(job.get("manifest_path", "")))
    if manifest_path.exists():
        return {"ok": True, "manifest_path": str(manifest_path), "source": "local"}
    run_dir = str(job.get("run_dir") or "")
    if not run_dir:
        return {"ok": False, "reason": "missing_run_dir"}
    control_ssh = control_ssh or str(HA_STRATEGY.get("control_tower", {}).get("ssh_target", ""))
    if not control_ssh:
        return {"ok": False, "reason": "missing_control_ssh"}
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_dir = cache_dir / Path(run_dir).name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    remote = f"{control_ssh}:{run_dir.rstrip('/')}/"
    proc = subprocess.run(["scp", "-q", "-r", remote, str(target_dir)], text=True, capture_output=True, timeout=300)
    if proc.returncode != 0:
        return {"ok": False, "reason": "scp_failed", "stderr": proc.stderr[-1000:]}
    local_manifest = target_dir / "manifest.json"
    return {"ok": local_manifest.exists(), "manifest_path": str(local_manifest), "source": "scp", "cache_dir": str(target_dir)}


def apply_upload_metadata_override(manifest_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("payload", {}) if isinstance(job.get("payload"), dict) else {}
    slot = payload.get("slot", {}) if isinstance(payload.get("slot"), dict) else {}
    overrides = {
        key: slot.get(key)
        for key in ("caption", "post_title", "hashtags")
        if slot.get(key)
    }
    if not overrides:
        return {"ok": True, "overridden": False, "reason": "no_slot_metadata"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "overridden": False, "reason": f"manifest_read_failed:{type(exc).__name__}:{exc}"}
    script = manifest.setdefault("script", {})
    if not isinstance(script, dict):
        script = {}
        manifest["script"] = script
    for key, value in overrides.items():
        script[key] = value
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "overridden": True, "keys": sorted(overrides)}


def _monitor_output_dirs(job: dict[str, Any], output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for key in ("run_dir", "manifest_path"):
        value = str(job.get(key) or "")
        if not value:
            continue
        path = Path(value)
        if key == "manifest_path":
            path = path.parent
        if path.exists():
            paths.append(path.parent if path.name.startswith("leftaino_") else path)
    paths.extend(
        [
            output_dir,
            DEFAULT_OUTPUT_DIR,
            REPO_DIR / "output" / "tiktok_aino_scheduled_packages",
            REPO_DIR / "output" / "tiktok_aino_performance_reports",
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def build_monitor_evidence(job: dict[str, Any], *, previous_status: str, output_dir: Path) -> dict[str, Any]:
    from src.core.tiktok_aino import monitoring, pipeline

    now = _now_utc()
    due_hour, due_at, next_due_at = _monitor_due_window(job, now=now)
    completed = set(_monitor_completed_windows(job))
    if due_hour is not None:
        completed.add(due_hour)
    base = _monitor_reference_time(job)
    if next_due_at is None and base is not None:
        for hour in _monitor_cadence_hours():
            if hour not in completed:
                next_due_at = base + dt.timedelta(hours=hour)
                break

    run_id = str(job.get("run_id") or "").strip() or None
    report_dir = pipeline.DEFAULT_PERFORMANCE_REPORT_DIR
    summary = monitoring.analyze_performance(
        output_dirs=_monitor_output_dirs(job, output_dir),
        run_id=run_id,
        output_dir=report_dir,
    )
    analyses = summary.get("analyses", []) if isinstance(summary.get("analyses"), list) else []
    first_analysis = analyses[0] if analyses and isinstance(analyses[0], dict) else {}
    all_windows_complete = next_due_at is None and bool(completed)
    evidence = {
        "monitor_checked_at": _iso(now),
        "last_monitor_at": _iso(now),
        "monitor_window_hour": due_hour,
        "monitor_window_due_at": _iso(due_at) if due_at else None,
        "monitor_windows_completed": sorted(completed),
        "next_monitor_at": _iso(next_due_at) if next_due_at else None,
        "monitor_cadence_hours": _monitor_cadence_hours(),
        "monitor_previous_status": previous_status,
        "monitor_completed": all_windows_complete,
        "performance_status": first_analysis.get("status"),
        "performance_score": first_analysis.get("score"),
        "performance_diagnoses": first_analysis.get("diagnoses", []),
        "performance_actions": first_analysis.get("actions", []),
        "performance_report_path": summary.get("path"),
        "performance_dashboard_path": summary.get("dashboard_path"),
        "performance_feedback_path": summary.get("performance_feedback_path"),
        "performance_feedback_latest_path": summary.get("performance_feedback_latest_path"),
        "performance_status_counts": summary.get("status_counts", {}),
    }
    return {key: value for key, value in evidence.items() if value is not None}


def _ssh_json(control_ssh: str, remote_command: str, *, timeout: int = 300) -> dict[str, Any]:
    proc = subprocess.run(
        ["ssh", control_ssh, remote_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        return {"ok": False, "reason": "ssh_failed", "returncode": proc.returncode, "stderr": proc.stderr[-1200:]}
    text = proc.stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "remote_json_parse_failed", "stdout": text[-1200:]}


def _remote_ha_command(
    *,
    control_runtime_dir: str,
    control_state_dir: str,
    control_python: str,
    args: list[str],
) -> str:
    parts = [
        "cd",
        shlex.quote(control_runtime_dir),
        "&&",
        shlex.quote(control_python),
        "-m",
        "src.core.tiktok_aino.ha_publisher",
        "--state-dir",
        shlex.quote(control_state_dir),
        *[shlex.quote(part) for part in args],
    ]
    return " ".join(parts)


def remote_upload_once(
    *,
    node_id: str,
    control_ssh: str | None = None,
    control_runtime_dir: str | None = None,
    control_state_dir: str | None = None,
    control_python: str | None = None,
    cache_dir: Path | None = None,
    upload_mode: str | None = None,
    chrome_profile_dir: Path | None = None,
    chrome_cdp_port: int = 9222,
    lead_hours: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    control = HA_STRATEGY.get("control_tower", {}) if isinstance(HA_STRATEGY.get("control_tower"), dict) else {}
    remote_enabled = str(os.environ.get("AINO_REMOTE_UPLOAD_ENABLED", control.get("remote_enabled", ""))).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    control_ssh = control_ssh or str(control.get("ssh_target") or "")
    if not remote_enabled or not control_ssh:
        return {"ok": False, "claimed": False, "reason": "remote_control_disabled"}
    control_runtime_dir = control_runtime_dir or str(control.get("runtime_dir") or "")
    control_state_dir = control_state_dir or str(control.get("state_dir") or "")
    control_python = control_python or os.environ.get("AINO_CONTROL_PYTHON") or "python"
    if not control_runtime_dir or not control_state_dir:
        return {"ok": False, "claimed": False, "reason": "remote_control_config_incomplete"}
    mode = upload_mode or os.environ.get("AINO_UPLOAD_MODE") or str(HA_STRATEGY.get("default_upload_mode", "prepare"))
    gate_enabled = os.environ.get(str(HA_STRATEGY.get("posting_gate_env", "AINO_UPLOAD_AUTOMATION_ENABLED")), "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    claim_args = ["--node-id", node_id, "claim", "--operation", "upload"]
    if lead_hours is not None:
        claim_args.extend(["--lead-hours", str(lead_hours)])
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_claim_via": control_ssh,
            "node_id": node_id,
            "mode": mode,
            "posting_gate_enabled": gate_enabled,
        }
    if mode in {"schedule", "publish"} and not gate_enabled:
        return {"ok": False, "reason": "posting_gate_env_not_enabled_before_claim", "claimed": False}
    claim = _ssh_json(
        control_ssh,
        _remote_ha_command(
            control_runtime_dir=control_runtime_dir,
            control_state_dir=control_state_dir,
            control_python=control_python,
            args=claim_args,
        ),
    )
    if not claim.get("ok"):
        return {"ok": False, "claimed": False, "claim": claim}
    lease = claim["lease"]
    job = claim["job"]
    materialized = materialize_artifacts(job, cache_dir=cache_dir or default_artifact_cache_dir(), control_ssh=control_ssh)
    if not materialized.get("ok"):
        fail_remote_lease(control_ssh, control_runtime_dir, control_state_dir, control_python, node_id, lease["lease_id"], json.dumps(materialized, ensure_ascii=False))
        return {"ok": False, "claimed": True, "materialized": materialized}
    metadata_override = apply_upload_metadata_override(Path(str(materialized["manifest_path"])), job)
    if not metadata_override.get("ok"):
        fail_remote_lease(control_ssh, control_runtime_dir, control_state_dir, control_python, node_id, lease["lease_id"], json.dumps(metadata_override, ensure_ascii=False))
        return {"ok": False, "claimed": True, "metadata_override": metadata_override}
    from src.core.tiktok_aino import pipeline, upload_automation

    manifest_path = Path(str(materialized["manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = pipeline.validate_manifest_for_upload(manifest)
    if not validation["upload_ready"] or (mode in {"schedule", "publish"} and not validation["publish_ready"]):
        complete_remote_lease(
            control_ssh,
            control_runtime_dir,
            control_state_dir,
            control_python,
            node_id,
            lease["lease_id"],
            "needs_revision",
            {"reason": "manifest_failed_final_upload_gate", "validation": validation, "local_manifest_path": str(manifest_path)},
        )
        return {"ok": False, "claimed": True, "status": "needs_revision", "validation": validation}

    try:
        upload_result = upload_automation.prepare_upload(
            manifest_path,
            mode=mode,
            port=chrome_cdp_port,
            profile_dir=chrome_profile_dir or upload_automation._default_profile_dir(),
            dry_run=False,
        )
    except Exception as exc:
        upload_result = {"ok": False, "reason": "upload_automation_exception", "error": f"{type(exc).__name__}: {exc}"}
        fail_remote_lease(control_ssh, control_runtime_dir, control_state_dir, control_python, node_id, lease["lease_id"], json.dumps(upload_result, ensure_ascii=False))
        return {"ok": False, "claimed": True, "upload_result": upload_result}
    if upload_result.get("needs_login") or upload_result.get("blocker") == "login_required":
        reason = json.dumps(upload_result, ensure_ascii=False)
        defer_remote_lease(control_ssh, control_runtime_dir, control_state_dir, control_python, node_id, lease["lease_id"], reason)
        return {"ok": False, "claimed": True, "paused": True, "reason": "upload_browser_login_required", "upload_result": upload_result}
    if upload_result.get("blocked") or not upload_result.get("ok"):
        fail_remote_lease(control_ssh, control_runtime_dir, control_state_dir, control_python, node_id, lease["lease_id"], json.dumps(upload_result, ensure_ascii=False))
        return {"ok": False, "claimed": True, "upload_result": upload_result}
    if mode == "publish" and upload_result.get("final_click_performed"):
        status = "published"
    elif mode == "schedule" and upload_result_confirms_scheduled(upload_result):
        status = "scheduled"
    else:
        status = "upload_prepared"
    complete = complete_remote_lease(
        control_ssh,
        control_runtime_dir,
        control_state_dir,
        control_python,
        node_id,
        lease["lease_id"],
        status,
        {
            "upload_result": upload_result,
            "published_url": upload_result.get("published_url"),
            "scheduled_at": upload_result.get("scheduled_at"),
            "local_manifest_path": materialized["manifest_path"],
        },
    )
    return {"ok": bool(complete.get("ok")), "claimed": True, "status": status, "complete": complete, "upload_result": upload_result}


def remote_batch_upload(
    *,
    node_id: str,
    upload_mode: str = "schedule",
    max_count: int | None = None,
    dry_run: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    max_items = max_count or _safe_int(HA_STRATEGY.get("batch_schedule_max_count"), 27)
    results: list[dict[str, Any]] = []
    for _ in range(max(1, max_items)):
        result = remote_upload_once(node_id=node_id, upload_mode=upload_mode, dry_run=dry_run, **kwargs)
        results.append(result)
        if dry_run or not result.get("ok"):
            break
        if not result.get("claimed"):
            break
    scheduled = sum(1 for result in results if result.get("status") == "scheduled")
    published = sum(1 for result in results if result.get("status") == "published")
    prepared = sum(1 for result in results if result.get("status") == "upload_prepared")
    return {
        "ok": all(result.get("ok") for result in results if result.get("claimed")) if results else True,
        "mode": upload_mode,
        "attempted": len(results),
        "scheduled": scheduled,
        "published": published,
        "prepared": prepared,
        "results": results,
    }


def complete_remote_lease(
    control_ssh: str,
    control_runtime_dir: str,
    control_state_dir: str,
    control_python: str,
    node_id: str,
    lease_id: str,
    status: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return _ssh_json(
        control_ssh,
        _remote_ha_command(
            control_runtime_dir=control_runtime_dir,
            control_state_dir=control_state_dir,
            control_python=control_python,
            args=[
                "--node-id",
                node_id,
                "complete",
                "--lease-id",
                lease_id,
                "--status",
                status,
                "--evidence-json",
                json.dumps(evidence, ensure_ascii=False),
            ],
        ),
    )


def fail_remote_lease(
    control_ssh: str,
    control_runtime_dir: str,
    control_state_dir: str,
    control_python: str,
    node_id: str,
    lease_id: str,
    error: str,
) -> dict[str, Any]:
    return _ssh_json(
        control_ssh,
        _remote_ha_command(
            control_runtime_dir=control_runtime_dir,
            control_state_dir=control_state_dir,
            control_python=control_python,
            args=["--node-id", node_id, "fail", "--lease-id", lease_id, "--error", error],
        ),
    )


def defer_remote_lease(
    control_ssh: str,
    control_runtime_dir: str,
    control_state_dir: str,
    control_python: str,
    node_id: str,
    lease_id: str,
    reason: str,
) -> dict[str, Any]:
    return _ssh_json(
        control_ssh,
        _remote_ha_command(
            control_runtime_dir=control_runtime_dir,
            control_state_dir=control_state_dir,
            control_python=control_python,
            args=["--node-id", node_id, "defer", "--lease-id", lease_id, "--reason", reason],
        ),
    )


def worker_once(
    state_dir: Path,
    *,
    node_id: str,
    operation: str,
    output_dir: Path,
    image_mode: str = "auto",
    real_image_limit: int = 9,
    upload_mode: str | None = None,
    chrome_profile_dir: Path | None = None,
    chrome_cdp_port: int = 9222,
    privacy_mode: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if dry_run:
        claim_preview = preview_next_job(state_dir, node_id=node_id, operation=operation)
        return {"ok": bool(claim_preview.get("ok")), "dry_run": True, "claim": claim_preview}
    claim = claim_next_job(state_dir, node_id=node_id, operation=operation)
    if not claim.get("ok"):
        return claim
    lease = claim["lease"]
    job = claim["job"]
    try:
        if operation == "generate":
            with _temporary_env("AINO_PRIVACY_MODE", privacy_mode):
                evidence = _generate_for_job(job, output_dir=output_dir, image_mode=image_mode, real_image_limit=real_image_limit)
            next_status = "generated" if evidence.get("manifest_status") == "publish_ready" else "needs_revision"
            return complete_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, status=next_status, evidence=evidence)
        if operation == "upload":
            materialized = materialize_artifacts(job, cache_dir=default_artifact_cache_dir())
            if not materialized.get("ok"):
                return fail_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, error=json.dumps(materialized, ensure_ascii=False))
            metadata_override = apply_upload_metadata_override(Path(str(materialized["manifest_path"])), job)
            if not metadata_override.get("ok"):
                return fail_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, error=json.dumps(metadata_override, ensure_ascii=False))
            from src.core.tiktok_aino import pipeline, upload_automation

            mode = upload_mode or os.environ.get("AINO_UPLOAD_MODE") or str(HA_STRATEGY.get("default_upload_mode", "prepare"))
            manifest_path = Path(str(materialized["manifest_path"]))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validation = pipeline.validate_manifest_for_upload(manifest)
            if not validation["upload_ready"] or (mode in {"schedule", "publish"} and not validation["publish_ready"]):
                return complete_lease(
                    state_dir,
                    lease_id=lease["lease_id"],
                    node_id=node_id,
                    status="needs_revision",
                    evidence={
                        "reason": "manifest_failed_final_upload_gate",
                        "validation": validation,
                        "local_manifest_path": str(manifest_path),
                    },
                )
            result = upload_automation.prepare_upload(
                manifest_path,
                mode=mode,
                port=chrome_cdp_port,
                profile_dir=chrome_profile_dir or upload_automation._default_profile_dir(),
                dry_run=False,
            )
            if result.get("needs_login") or result.get("blocker") == "login_required":
                return defer_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, reason=json.dumps(result, ensure_ascii=False))
            if result.get("blocked") or not result.get("ok"):
                return fail_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, error=json.dumps(result, ensure_ascii=False))
            if mode == "schedule" and upload_result_confirms_scheduled(result):
                return complete_lease(
                    state_dir,
                    lease_id=lease["lease_id"],
                    node_id=node_id,
                    status="scheduled",
                    evidence={"upload_result": result, "scheduled_at": result.get("scheduled_at"), "artifact_node": job.get("artifact_node")},
                )
            if mode == "publish" and result.get("final_click_performed"):
                return complete_lease(
                    state_dir,
                    lease_id=lease["lease_id"],
                    node_id=node_id,
                    status="published",
                    evidence={"upload_result": result, "published_url": result.get("published_url"), "artifact_node": job.get("artifact_node")},
                )
            if mode == "prepare":
                return complete_lease(
                    state_dir,
                    lease_id=lease["lease_id"],
                    node_id=node_id,
                    status="upload_prepared",
                    evidence={"upload_result": result, "artifact_node": job.get("artifact_node")},
                )
            return fail_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, error=json.dumps(result, ensure_ascii=False))
        if operation == "monitor":
            previous_status = str(lease.get("previous_status") or "published")
            evidence = build_monitor_evidence(job, previous_status=previous_status, output_dir=output_dir)
            next_status = "monitoring_complete" if evidence.get("monitor_completed") else previous_status
            return complete_lease(
                state_dir,
                lease_id=lease["lease_id"],
                node_id=node_id,
                status=next_status,
                evidence=evidence,
            )
    except Exception as exc:
        return fail_lease(state_dir, lease_id=lease["lease_id"], node_id=node_id, error=f"{type(exc).__name__}: {exc}")
    raise ValueError(f"unsupported operation: {operation}")


def controller_once(state_dir: Path, *, days: int | None = None, plan_path: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    from src.core.tiktok_aino import schedule_planner

    if dry_run and not plan_path:
        return {"ok": True, "dry_run": True, "would_build_plan_days": days or HA_STRATEGY.get("rolling_plan_days")}
    if plan_path is None:
        plan_result = schedule_planner.build_rolling_plan(days=days or _safe_int(HA_STRATEGY.get("rolling_plan_days"), 7))
        plan_path = Path(str(plan_result["path"]))
    enqueue = enqueue_plan(state_dir, plan_path)
    reclaim = reclaim_stale_leases(state_dir)
    return {"ok": True, "plan_path": str(plan_path), "enqueue": enqueue, "reclaim": reclaim}


def status_summary(state_dir: Path) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    jobs_doc = store.read(JOBS_FILENAME)
    leases_doc = store.read(LEASES_FILENAME)
    nodes_doc = store.read(NODES_FILENAME)
    counts: dict[str, int] = {}
    for job in jobs_doc.get("jobs", {}).values():
        if isinstance(job, dict):
            status = str(job.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
    active_leases = [
        lease for lease in leases_doc.get("leases", {}).values() if isinstance(lease, dict) and lease.get("status") == "active"
    ]
    return {
        "ok": True,
        "state_dir": str(state_dir),
        "job_counts": counts,
        "active_lease_count": len(active_leases),
        "nodes": nodes_doc.get("nodes", {}),
        "updated_at": _iso(),
    }


def audit_state(state_dir: Path) -> dict[str, Any]:
    store = FileStateStore(state_dir)
    jobs_doc = store.read(JOBS_FILENAME)
    leases_doc = store.read(LEASES_FILENAME)
    jobs = [job for job in jobs_doc.get("jobs", {}).values() if isinstance(job, dict)]
    leases = [lease for lease in leases_doc.get("leases", {}).values() if isinstance(lease, dict)]
    counts: dict[str, int] = {}
    terminal_upload_statuses = {"expired", "scheduled", "published", "monitoring_complete"}
    pending_upload_statuses = {"generated", "upload_retry", "uploading"}
    stale_upload_jobs: list[dict[str, Any]] = []
    non_publish_ready_jobs: list[dict[str, Any]] = []
    claimable_upload_jobs: list[dict[str, Any]] = []
    pending_upload_jobs: list[dict[str, Any]] = []
    for job in jobs:
        status = str(job.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        publish_at = str(job.get("publish_at_local") or "")
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        validation = payload.get("upload_validation") if isinstance(payload.get("upload_validation"), dict) else {}
        if status in pending_upload_statuses:
            pending_upload_jobs.append(job)
        if status not in terminal_upload_statuses and _job_has_explicit_publish_time(job) and _planned_time_is_past(publish_at):
            stale_upload_jobs.append(
                {
                    "job_id": job.get("job_id"),
                    "run_id": job.get("run_id"),
                    "status": status,
                    "publish_at_local": publish_at,
                    "topic": job.get("topic"),
                }
            )
        if status in {"generated", "upload_retry"} and validation and validation.get("publish_ready") is not True:
            non_publish_ready_jobs.append(
                {
                    "job_id": job.get("job_id"),
                    "run_id": job.get("run_id"),
                    "status": status,
                    "blockers": validation.get("blockers", []),
                }
            )
        if _job_claimable(job, "upload", lead_hours=_operation_lead_hours("upload")):
            claimable_upload_jobs.append(
                {
                    "job_id": job.get("job_id"),
                    "run_id": job.get("run_id"),
                    "publish_at_local": publish_at,
                    "topic": job.get("topic"),
                }
            )
    active_leases = [lease for lease in leases if lease.get("status") == "active"]
    posting_gate_env = str(HA_STRATEGY.get("posting_gate_env", "AINO_UPLOAD_AUTOMATION_ENABLED"))
    posting_gate_enabled = os.environ.get(posting_gate_env, "").lower() in {"1", "true", "yes", "on"}
    issues: list[str] = []
    if not posting_gate_enabled:
        issues.append("posting_gate_disabled")
    if stale_upload_jobs:
        issues.append("stale_upload_jobs_present")
    if non_publish_ready_jobs:
        issues.append("non_publish_ready_upload_jobs_present")
    if active_leases:
        issues.append("active_leases_present")
    if pending_upload_jobs and not claimable_upload_jobs:
        issues.append("no_claimable_upload_jobs")
    return {
        "ok": not issues,
        "state_dir": str(state_dir),
        "job_counts": counts,
        "posting_gate_env": posting_gate_env,
        "posting_gate_enabled": posting_gate_enabled,
        "claimable_upload_count": len(claimable_upload_jobs),
        "claimable_upload_jobs": claimable_upload_jobs[:12],
        "pending_upload_count": len(pending_upload_jobs),
        "stale_upload_count": len(stale_upload_jobs),
        "stale_upload_jobs": stale_upload_jobs[:12],
        "non_publish_ready_upload_count": len(non_publish_ready_jobs),
        "non_publish_ready_upload_jobs": non_publish_ready_jobs[:12],
        "active_lease_count": len(active_leases),
        "issues": issues,
        "updated_at": _iso(),
    }


def _json_print(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="AiNo TikTok HA publisher coordinator.")
    parser.add_argument("--state-dir", type=Path, default=default_state_dir())
    parser.add_argument("--node-id", default=default_node_id())
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("audit")
    hb = sub.add_parser("heartbeat")
    hb.add_argument("--capability", action="append", default=[])
    reclaim = sub.add_parser("reclaim")
    del reclaim
    release = sub.add_parser("release-node-leases")
    release.add_argument("--operation", choices=sorted(DEFAULT_OPERATION_STATUSES))
    ep = sub.add_parser("enqueue-plan")
    ep.add_argument("--plan", type=Path, required=True)
    em = sub.add_parser("enqueue-manifest")
    em.add_argument("--manifest", type=Path, required=True)
    claim = sub.add_parser("claim")
    claim.add_argument("--operation", choices=sorted(DEFAULT_OPERATION_STATUSES), required=True)
    claim.add_argument("--lead-hours", type=int)
    comp = sub.add_parser("complete")
    comp.add_argument("--lease-id", required=True)
    comp.add_argument("--status", required=True)
    comp.add_argument("--evidence-json")
    fail = sub.add_parser("fail")
    fail.add_argument("--lease-id", required=True)
    fail.add_argument("--error", required=True)
    defer = sub.add_parser("defer")
    defer.add_argument("--lease-id", required=True)
    defer.add_argument("--reason", required=True)
    ctrl = sub.add_parser("controller-once")
    ctrl.add_argument("--days", type=int)
    ctrl.add_argument("--plan", type=Path)
    ctrl.add_argument("--dry-run", action="store_true")
    worker = sub.add_parser("worker-once")
    worker.add_argument("--operation", choices=sorted(DEFAULT_OPERATION_STATUSES), required=True)
    worker.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "scheduled_packages")
    worker.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    worker.add_argument("--real-image-limit", type=int, default=9)
    worker.add_argument("--upload-mode", choices=["prepare", "schedule", "publish"], default=None)
    worker.add_argument("--chrome-profile-dir", type=Path)
    worker.add_argument("--chrome-cdp-port", type=int, default=9222)
    worker.add_argument("--privacy-mode", choices=["local_only", "cloud_explicit"], default=None)
    worker.add_argument("--dry-run", action="store_true")
    mat = sub.add_parser("materialize")
    mat.add_argument("--job-id", required=True)
    mat.add_argument("--cache-dir", type=Path, default=default_artifact_cache_dir())
    remote = sub.add_parser("remote-upload-once")
    remote.add_argument("--control-ssh")
    remote.add_argument("--control-runtime-dir")
    remote.add_argument("--control-state-dir")
    remote.add_argument("--control-python")
    remote.add_argument("--cache-dir", type=Path, default=default_artifact_cache_dir())
    remote.add_argument("--upload-mode", choices=["prepare", "schedule", "publish"], default=None)
    remote.add_argument("--chrome-profile-dir", type=Path)
    remote.add_argument("--chrome-cdp-port", type=int, default=9222)
    remote.add_argument("--lead-hours", type=int)
    remote.add_argument("--dry-run", action="store_true")
    batch = sub.add_parser("remote-batch-upload")
    batch.add_argument("--control-ssh")
    batch.add_argument("--control-runtime-dir")
    batch.add_argument("--control-state-dir")
    batch.add_argument("--control-python")
    batch.add_argument("--cache-dir", type=Path, default=default_artifact_cache_dir())
    batch.add_argument("--upload-mode", choices=["schedule", "publish"], default="schedule")
    batch.add_argument("--max-count", type=int)
    batch.add_argument("--chrome-profile-dir", type=Path)
    batch.add_argument("--chrome-cdp-port", type=int, default=9222)
    batch.add_argument("--lead-hours", type=int)
    batch.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.cmd == "status":
        _json_print(status_summary(args.state_dir))
    elif args.cmd == "audit":
        _json_print(audit_state(args.state_dir))
    elif args.cmd == "heartbeat":
        _json_print(heartbeat(args.state_dir, node_id=args.node_id, capabilities=args.capability))
    elif args.cmd == "reclaim":
        _json_print(reclaim_stale_leases(args.state_dir))
    elif args.cmd == "release-node-leases":
        _json_print(release_node_leases(args.state_dir, node_id=args.node_id, operation=args.operation))
    elif args.cmd == "enqueue-plan":
        _json_print(enqueue_plan(args.state_dir, args.plan))
    elif args.cmd == "enqueue-manifest":
        _json_print(enqueue_manifest(args.state_dir, args.manifest))
    elif args.cmd == "claim":
        _json_print(claim_next_job(args.state_dir, node_id=args.node_id, operation=args.operation, lead_hours=args.lead_hours))
    elif args.cmd == "complete":
        evidence = json.loads(args.evidence_json) if args.evidence_json else {}
        _json_print(complete_lease(args.state_dir, lease_id=args.lease_id, node_id=args.node_id, status=args.status, evidence=evidence))
    elif args.cmd == "fail":
        _json_print(fail_lease(args.state_dir, lease_id=args.lease_id, node_id=args.node_id, error=args.error))
    elif args.cmd == "defer":
        _json_print(defer_lease(args.state_dir, lease_id=args.lease_id, node_id=args.node_id, reason=args.reason))
    elif args.cmd == "controller-once":
        _json_print(controller_once(args.state_dir, days=args.days, plan_path=args.plan, dry_run=args.dry_run))
    elif args.cmd == "worker-once":
        _json_print(
            worker_once(
                args.state_dir,
                node_id=args.node_id,
                operation=args.operation,
                output_dir=args.output_dir,
                image_mode=args.image_mode,
                real_image_limit=args.real_image_limit,
                upload_mode=args.upload_mode,
                chrome_profile_dir=args.chrome_profile_dir,
                chrome_cdp_port=args.chrome_cdp_port,
                privacy_mode=args.privacy_mode,
                dry_run=args.dry_run,
            )
        )
    elif args.cmd == "materialize":
        jobs = FileStateStore(args.state_dir).read(JOBS_FILENAME).get("jobs", {})
        job = jobs.get(args.job_id)
        if not isinstance(job, dict):
            _json_print({"ok": False, "reason": "job_not_found", "job_id": args.job_id})
            return 2
        _json_print(materialize_artifacts(job, cache_dir=args.cache_dir))
    elif args.cmd == "remote-upload-once":
        _json_print(
            remote_upload_once(
                node_id=args.node_id,
                control_ssh=args.control_ssh,
                control_runtime_dir=args.control_runtime_dir,
                control_state_dir=args.control_state_dir,
                control_python=args.control_python,
                cache_dir=args.cache_dir,
                upload_mode=args.upload_mode,
                chrome_profile_dir=args.chrome_profile_dir,
                chrome_cdp_port=args.chrome_cdp_port,
                lead_hours=args.lead_hours,
                dry_run=args.dry_run,
            )
        )
    elif args.cmd == "remote-batch-upload":
        _json_print(
            remote_batch_upload(
                node_id=args.node_id,
                control_ssh=args.control_ssh,
                control_runtime_dir=args.control_runtime_dir,
                control_state_dir=args.control_state_dir,
                control_python=args.control_python,
                cache_dir=args.cache_dir,
                upload_mode=args.upload_mode,
                max_count=args.max_count,
                chrome_profile_dir=args.chrome_profile_dir,
                chrome_cdp_port=args.chrome_cdp_port,
                lead_hours=args.lead_hours,
                dry_run=args.dry_run,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
