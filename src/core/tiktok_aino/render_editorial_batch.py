"""Render source-backed Editorial OS batches through the AiNo media pipeline.

The input is a data file, not a code template. This keeps weekly production
topics, scripts, sources, and scene visuals reviewable before expensive media
generation runs. The module never enqueues or uploads to TikTok.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.core.tiktok_aino import pipeline, privacy


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"bundle must be a JSON object: {path}")
    return data


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _source_map(item: dict[str, Any]) -> dict[str, pipeline.Source]:
    sources: dict[str, pipeline.Source] = {}
    for row in _as_list(item.get("sources")):
        if not isinstance(row, dict):
            continue
        source_id = _clean_text(row.get("source_id"))
        if not source_id:
            continue
        sources[source_id] = pipeline.Source(
            source_id=source_id,
            title=_clean_text(row.get("title")) or source_id,
            url=_clean_text(row.get("url")),
            note=_clean_text(row.get("note")),
        )
    if not sources:
        raise ValueError(f"item {item.get('item_id')} has no sources")
    return sources


def _claims(item: dict[str, Any]) -> list[pipeline.Claim]:
    claims: list[pipeline.Claim] = []
    for row in _as_list(item.get("claims")):
        if not isinstance(row, dict):
            continue
        text = _clean_text(row.get("text"))
        source_ids = [_clean_text(value) for value in _as_list(row.get("source_ids")) if _clean_text(value)]
        if text and source_ids:
            claims.append(pipeline.Claim(text=text, source_ids=source_ids, risk=_clean_text(row.get("risk")) or "low"))
    if not claims:
        raise ValueError(f"item {item.get('item_id')} has no source-backed claims")
    return claims


def _topic_from_item(item: dict[str, Any], sources: dict[str, pipeline.Source]) -> pipeline.TopicCandidate:
    return pipeline.TopicCandidate(
        title=_clean_text(item.get("title")) or _clean_text(item.get("post_title")),
        angle=_clean_text(item.get("angle")),
        slot=_clean_text(item.get("slot")) or "weekly_editorial_batch",
        target_duration_sec=int(item.get("target_duration_sec") or 72),
        claims=_claims(item),
        source_ids=list(sources.keys()),
    )


def _visual_payload(scene: dict[str, Any]) -> str:
    visual = scene.get("visual_override")
    if isinstance(visual, dict):
        return f"{pipeline.VISUAL_OVERRIDE_PREFIX}{json.dumps(visual, ensure_ascii=False, sort_keys=True)}"
    return _clean_text(scene.get("visual"))


def _scene_from_row(row: dict[str, Any], index: int) -> pipeline.Scene:
    return pipeline.Scene(
        scene_id=index,
        duration_sec=int(row.get("duration_sec") or 8),
        title=_clean_text(row.get("role")) or "beat",
        body=_clean_text(row.get("narration")),
        visual=_visual_payload(row),
        on_screen_text=_clean_text(row.get("hook_text")),
    )


def _script_from_item(item: dict[str, Any]) -> pipeline.ScriptPackage:
    scenes = [
        _scene_from_row(row, index)
        for index, row in enumerate(_as_list(item.get("scenes")), start=1)
        if isinstance(row, dict)
    ]
    if len(scenes) < 9:
        raise ValueError(f"item {item.get('item_id')} must define at least 9 scenes")
    source_ids = [_clean_text(row.get("source_id")) for row in _as_list(item.get("sources")) if isinstance(row, dict)]
    return pipeline.ScriptPackage(
        title=_clean_text(item.get("post_title")) or _clean_text(item.get("title")),
        caption=_clean_text(item.get("caption")),
        hashtags=[_clean_text(value) for value in _as_list(item.get("hashtags")) if _clean_text(value)],
        post_title=_clean_text(item.get("post_title")) or _clean_text(item.get("title")),
        post_body=_clean_text(item.get("caption")),
        pinned_comment=_clean_text(item.get("pinned_comment")),
        narration="\n".join(scene.body for scene in scenes),
        scenes=scenes,
        target_duration_sec=sum(scene.duration_sec for scene in scenes),
        sources=[source_id for source_id in source_ids if source_id],
        disclosure=_clean_text(item.get("disclosure")) or "Generated image/video/audio disclosure required.",
        variant_id=_clean_text(item.get("variant_id")) or f"editorial_batch:{_clean_text(item.get('item_id'))}",
    )


def _topic_discovery(bundle: dict[str, Any], item: dict[str, Any], script: pipeline.ScriptPackage) -> dict[str, Any]:
    scene_roles = [scene.title for scene in script.scenes]
    return {
        "mode": "editorial_batch",
        "bundle_id": _clean_text(bundle.get("batch_id")),
        "item_id": _clean_text(item.get("item_id")),
        "research_notes": item.get("research_notes") if isinstance(item.get("research_notes"), dict) else {},
        "content_signature": {
            "topic_signature": _clean_text(item.get("topic_signature")) or _clean_text(item.get("item_id")),
            "script_structure": scene_roles,
            "first_frame_signature": script.scenes[0].on_screen_text if script.scenes else "",
            "cta_type": _clean_text(item.get("cta_type")) or "comment_split",
        },
        "deep_research_report": {
            "research_mode": "source_backed_weekly_bundle",
            "selected_topic_id": _clean_text(item.get("item_id")),
            "selected_research_question": _clean_text(item.get("core_question")),
            "counterpoint_focus": _clean_text(item.get("counterpoint_focus")),
            "comment_trigger": _clean_text(item.get("comment_question")),
            "source_requirements": item.get("source_requirements") or [],
            "visual_mandates": [
                "Use scene-specific realistic cinematic visuals.",
                "Do not use real politician likenesses, party logos, fake official documents, or fake news UI.",
                "For cinematic_subtitle scenes, keep generated images free of readable text and render Korean subtitles in the video layer.",
            ],
        },
    }


def _manifest_visual_signature(manifest: dict[str, Any]) -> dict[str, Any]:
    visual_assets = [asset for asset in manifest.get("visual_assets", []) if isinstance(asset, dict)]
    briefs = [asset.get("visual_brief") for asset in visual_assets if isinstance(asset.get("visual_brief"), dict)]
    return {
        "scene_count": len(briefs),
        "unique_locations": len({str(brief.get("location") or "") for brief in briefs}),
        "unique_treatments": len({str(brief.get("treatment_id") or "") for brief in briefs}),
        "first_frame_key": str(briefs[0].get("treatment_id") or "") if briefs else "",
        "providers": sorted({str(asset.get("provider") or "") for asset in visual_assets}),
        "statuses": sorted({str(asset.get("status") or "") for asset in visual_assets}),
    }


def _load_reused_visual_assets(path: Path | None) -> list[pipeline.VisualAsset] | None:
    if path is None:
        return None
    assets_path = path if path.name == "visual_assets.json" else path / "visual_assets.json"
    rows = json.loads(assets_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"visual assets file must be a non-empty list: {assets_path}")
    assets: list[pipeline.VisualAsset] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        assets.append(
            pipeline.VisualAsset(
                scene_id=int(row.get("scene_id") or 0),
                provider=_clean_text(row.get("provider")) or "reused",
                status=_clean_text(row.get("status")) or "generated",
                path=_clean_text(row.get("path")) or None,
                prompt=_clean_text(row.get("prompt")),
                visual_brief=row.get("visual_brief") if isinstance(row.get("visual_brief"), dict) else {},
                visual_quality=row.get("visual_quality") if isinstance(row.get("visual_quality"), dict) else {},
                notes=[_clean_text(value) for value in _as_list(row.get("notes")) if _clean_text(value)] + ["reused_visual_asset"],
            )
        )
    if not assets:
        raise ValueError(f"no reusable visual assets found: {assets_path}")
    return assets


def _batch_quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    titles = [_clean_text(item.get("post_title")) for item in results if _clean_text(item.get("post_title"))]
    first_frames = [
        _clean_text((item.get("visual_signature") or {}).get("first_frame_key"))
        for item in results
        if isinstance(item.get("visual_signature"), dict)
    ]
    duplicate_titles = sorted({title for title in titles if titles.count(title) > 1})
    duplicate_first_frames = sorted({key for key in first_frames if key and first_frames.count(key) > 1})
    blocked = [item for item in results if item.get("status") not in {"publish_ready", "selected"}]
    return {
        "ok": not duplicate_titles and not duplicate_first_frames and not blocked,
        "duplicate_titles": duplicate_titles,
        "duplicate_first_frames": duplicate_first_frames,
        "blocked_count": len(blocked),
        "publish_ready_count": sum(1 for item in results if item.get("status") == "publish_ready"),
        "selected_count": sum(1 for item in results if item.get("status") == "selected"),
    }


def render_batch(
    bundle_path: Path,
    *,
    output_dir: Path,
    image_mode: str,
    real_image_limit: int | None,
    privacy_mode: str,
    content_format: str,
    limit: int,
    dry_run: bool,
    item_ids: list[str] | None = None,
    reuse_visual_assets_from: Path | None = None,
) -> dict[str, Any]:
    pipeline._load_env_files()
    os.environ["AINO_PRIVACY_MODE"] = privacy.normalize_mode(privacy_mode)
    os.environ.setdefault("ELEVENLABS_ENABLE_LOGGING", "false")

    bundle = _read_json(bundle_path)
    items = [item for item in _as_list(bundle.get("items")) if isinstance(item, dict)]
    requested_ids = {_clean_text(item_id) for item_id in (item_ids or []) if _clean_text(item_id)}
    if requested_ids:
        items = [item for item in items if _clean_text(item.get("item_id")) in requested_ids]
    if limit > 0:
        items = items[:limit]
    reused_visual_assets = _load_reused_visual_assets(reuse_visual_assets_from)
    if reused_visual_assets is not None and len(items) != 1:
        raise ValueError("reuse_visual_assets_from requires exactly one selected bundle item")

    results: list[dict[str, Any]] = []
    for item in items:
        sources = _source_map(item)
        topic = _topic_from_item(item, sources)
        script = _script_from_item(item)
        result_row: dict[str, Any] = {
            "item_id": _clean_text(item.get("item_id")),
            "publish_at_local": _clean_text(item.get("publish_at_local")),
            "format": _clean_text(item.get("format")) or content_format,
            "topic": topic.title,
            "post_title": script.post_title,
            "dry_run": dry_run,
        }
        if dry_run:
            result_row.update(
                {
                    "status": "selected",
                    "scene_count": len(script.scenes),
                    "source_count": len(sources),
                    "claim_count": len(topic.claims),
                    "scene_roles": [scene.title for scene in script.scenes],
                }
            )
            results.append(result_row)
            continue

        render_result = pipeline.run_for_topic(
            topic,
            sources,
            output_dir=output_dir,
            image_mode=image_mode,
            real_image_limit=real_image_limit,
            content_format=_clean_text(item.get("format")) or content_format,
            topic_discovery=_topic_discovery(bundle, item, script),
            planned_publish_at_local=_clean_text(item.get("publish_at_local")),
            script_override=script,
            visual_assets_override=reused_visual_assets,
        )
        manifest_path = Path(render_result.artifacts.manifest_json)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result_row.update(
            {
                "run_id": render_result.run_id,
                "status": render_result.status,
                "quality_score": render_result.quality.publish_ready_score,
                "review": render_result.review.recommendation,
                "blockers": render_result.review.blockers + render_result.quality.blockers,
                "manifest": render_result.artifacts.manifest_json,
                "mp4": render_result.artifacts.mp4,
                "mobile_preview_storyboard": render_result.artifacts.mobile_preview_storyboard,
                "report_html": render_result.artifacts.report_html,
                "upload_validation": pipeline.validate_manifest_for_upload(manifest),
                "visual_signature": _manifest_visual_signature(manifest),
                "visual_quality": manifest.get("visual_quality"),
                "layout_quality": manifest.get("layout_quality"),
            }
        )
        results.append(result_row)

    summary = {
        "ok": _batch_quality(results)["ok"],
        "bundle_path": str(bundle_path),
        "output_dir": str(output_dir),
        "batch_id": _clean_text(bundle.get("batch_id")),
        "dry_run": dry_run,
        "reuse_visual_assets_from": str(reuse_visual_assets_from) if reuse_visual_assets_from else "",
        "requested_count": len(items),
        "results": results,
        "batch_quality": _batch_quality(results),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "editorial_batch_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a source-backed AiNo editorial batch.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR / "editorial_batch_renders")
    parser.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    parser.add_argument("--real-image-limit", type=int, default=pipeline.default_real_image_limit_from_env())
    parser.add_argument(
        "--privacy-mode",
        choices=[privacy.LOCAL_ONLY, privacy.CLOUD_EXPLICIT],
        default=privacy.CLOUD_EXPLICIT,
    )
    parser.add_argument(
        "--format",
        choices=["evidence_briefing_75", "growth_short", "reward_deep", "debate_followup"],
        default="debate_followup",
        dest="content_format",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--item-id", action="append", default=[])
    parser.add_argument("--reuse-visual-assets-from", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    summary = render_batch(
        args.bundle,
        output_dir=args.output_dir,
        image_mode=args.image_mode,
        real_image_limit=None if args.real_image_limit is None else max(0, args.real_image_limit),
        privacy_mode=args.privacy_mode,
        content_format=args.content_format,
        limit=max(0, args.limit),
        dry_run=args.dry_run,
        item_ids=args.item_id,
        reuse_visual_assets_from=args.reuse_visual_assets_from,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
