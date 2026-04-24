# -*- coding: utf-8 -*-
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_script(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_wsl_redis_bootstrap_requires_authentication():
    script = _read_script("scripts/start_daemon.ps1")

    assert "--protected-mode no" not in script
    assert "requirepass $REDIS_PASSWORD" in script
    assert "SORA_REDIS_PASSWORD" in script
    assert "redis://:{0}@{1}:{2}/0" in script
    assert '"redis://localhost:$RedisPort/0"' not in script
    assert "Format-RedisUrlForLog" in script
    assert '__REDIS_PASSWORD__' not in script


def test_daemon_startup_does_not_treat_broad_scan_as_healthy_runtime():
    script = _read_script("scripts/start_daemon.ps1")

    assert "function Stop-ProcessRobust" in script
    assert "function Get-HealthyManagedPid" in script
    assert "Daemon already running via live process scan" not in script
    assert "Cleaning unmanaged daemon processes before startup" in script


def test_daily_ai_ops_pipeline_has_exclusive_lock_and_cleanup():
    script = _read_script("scripts/run_ai_ops_brief_pipeline.ps1")

    assert "param(" in script
    assert "[switch]$SkipTelegram" in script
    assert "daily_ai_ops_brief.lock" in script
    assert "[System.IO.FileMode]::CreateNew" in script
    assert "ai_ops_brief_skipped=lock_exists" in script
    assert '"--skip-telegram"' in script
    assert "finally" in script
    assert "Remove-Item $LockPath" in script


def test_daily_ai_ops_task_registration_ignores_overlapping_runs():
    script = _read_script("scripts/register_ai_ops_brief_task.ps1")

    assert "-MultipleInstances IgnoreNew" in script
    assert "run_ai_ops_brief_pipeline.ps1" in script
    assert "-SkipTelegram" not in script
