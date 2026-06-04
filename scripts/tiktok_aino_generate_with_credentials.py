#!/usr/bin/env python
"""Run TikTok AiNo schedule generation after loading local credentials."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOADER_PATH = ROOT / "infra" / "agent-runtime" / "credential_loader.py"


def _load_credentials() -> None:
    spec = importlib.util.spec_from_file_location("credential_loader", LOADER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"credential loader not found: {LOADER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_credentials(verbose=False)


def main() -> int:
    _load_credentials()
    from src.core.tiktok_aino.generate_from_schedule import main as schedule_main

    return int(schedule_main())


if __name__ == "__main__":
    raise SystemExit(main())
