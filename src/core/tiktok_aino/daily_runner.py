"""Run the AiNo TikTok daily content plan.

This runner creates content packages only. It does not upload to TikTok.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.core.tiktok_aino import pipeline


DAILY_FORMATS = ["growth_short", "reward_deep", "debate_followup"]


def _run_format(args: argparse.Namespace, content_format: str) -> dict[str, object]:
    result = pipeline.run_once(
        output_dir=args.output_dir,
        image_mode=args.image_mode,
        real_image_limit=args.real_image_limit,
        content_format=content_format,
        topic_mode=args.topic_mode,
    )
    manifest = json.loads(Path(result.artifacts.manifest_json).read_text(encoding="utf-8"))
    return {
        "run_id": result.run_id,
        "status": result.status,
        "format": result.format_plan.format_id,
        "topic_mode": args.topic_mode,
        "topic": result.topic.title,
        "topic_discovery": manifest.get("topic_discovery"),
        "objective": result.format_plan.objective,
        "upload_slot": result.format_plan.upload_slot,
        "target_duration_sec": result.script.target_duration_sec,
        "scene_count": len(result.script.scenes),
        "visual_beat_count": len(manifest["visual_beats"]),
        "audio_provider": result.artifacts.audio_provider,
        "audio_status": result.artifacts.audio_status,
        "quality_score": result.quality.publish_ready_score,
        "review": result.review.recommendation,
        "blockers": result.review.blockers + result.quality.blockers,
        "mp4": result.artifacts.mp4,
        "storyboard": result.artifacts.storyboard,
        "manifest": result.artifacts.manifest_json,
        "report_html": result.artifacts.report_html,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the AiNo TikTok daily content plan.")
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR)
    parser.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    parser.add_argument("--real-image-limit", type=int, default=9)
    parser.add_argument("--topic-mode", choices=["static", "hot"], default="static")
    parser.add_argument("--slot", choices=[*DAILY_FORMATS, "all"], default="all")
    args = parser.parse_args()

    formats = DAILY_FORMATS if args.slot == "all" else [args.slot]
    results = [_run_format(args, content_format) for content_format in formats]
    summary = {
        "ok": all(item["status"] == "publish_ready" for item in results),
        "count": len(results),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
