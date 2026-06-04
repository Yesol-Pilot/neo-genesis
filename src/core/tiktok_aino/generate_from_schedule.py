"""Generate AiNo TikTok content packages from a rolling schedule plan.

This module creates local media packages only. It does not upload, schedule,
or publish anything on TikTok.
"""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import json
import os
from pathlib import Path
import re
from typing import Any

from src.core.tiktok_aino import pipeline
from src.core.tiktok_aino import schedule_planner


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"schedule plan must be a JSON object: {path}")
    return data


def _source_from_row(row: dict[str, Any], index: int) -> pipeline.Source:
    return pipeline.Source(
        source_id=str(row.get("source_id") or f"schedule_source_{index:02d}"),
        title=str(row.get("title", "")).strip(),
        url=str(row.get("url", "")).strip(),
        note=str(row.get("note", "")).strip(),
    )


def _claim_from_row(row: dict[str, Any], fallback_source_ids: list[str]) -> pipeline.Claim:
    source_ids = row.get("source_ids")
    if not isinstance(source_ids, list):
        source_ids = fallback_source_ids
    return pipeline.Claim(
        text=str(row.get("text", "")).strip(),
        source_ids=[str(source_id) for source_id in source_ids if str(source_id).strip()],
        risk=str(row.get("risk", "medium")),
    )


def _claims_aligned_to_topic(title: str, claims: list[pipeline.Claim]) -> list[pipeline.Claim]:
    aligned: list[pipeline.Claim] = []
    for index, claim in enumerate(claims):
        if index == 0:
            aligned.append(claim)
            continue
        if (
            pipeline._has_specific_topic_overlap(title, claim.text)
            and pipeline._topic_overlap_score(title, claim.text) >= 6
        ):
            aligned.append(claim)
    return aligned


def _source_supports_topic(title: str, source: pipeline.Source) -> bool:
    source_text = f"{source.title} {source.note}"
    return (
        pipeline._has_specific_topic_overlap(title, source_text)
        and pipeline._topic_overlap_score(title, source_text) >= 5
    )


def _topic_from_slot(slot: dict[str, Any], index: int) -> tuple[pipeline.TopicCandidate, dict[str, pipeline.Source]]:
    source_rows = slot.get("sources", [])
    sources = {
        source.source_id: source
        for source in (
            _source_from_row(row, row_index)
            for row_index, row in enumerate(source_rows, start=1)
            if isinstance(row, dict)
        )
    }
    source_ids = list(sources)
    topic_row = slot.get("topic_candidate")
    if isinstance(topic_row, dict):
        claim_rows = topic_row.get("claims", [])
        claims = [
            _claim_from_row(row, source_ids)
            for row in claim_rows
            if isinstance(row, dict) and str(row.get("text", "")).strip()
        ]
        if not claims:
            claims = [_fallback_claim(slot, source_ids)]
        title = str(topic_row.get("title") or slot.get("topic", "")).strip()
        claims = _claims_aligned_to_topic(title, claims)
        aligned_source_ids = sorted({source_id for claim in claims for source_id in claim.source_ids})
        candidate_source_ids = [
            str(source_id)
            for source_id in (topic_row.get("source_ids") or [])
            if str(source_id).strip()
        ]
        support_source_ids = [
            source_id
            for source_id in [*source_ids, *candidate_source_ids]
            if source_id in sources
            and (source_id in aligned_source_ids or _source_supports_topic(title, sources[source_id]))
        ]
        retained_source_ids = list(dict.fromkeys([*aligned_source_ids, *support_source_ids]))
        if retained_source_ids:
            sources = {source_id: source for source_id, source in sources.items() if source_id in retained_source_ids}
        if len(retained_source_ids) > len(aligned_source_ids):
            claims.append(
                pipeline.Claim(
                    text=f"보조 출처까지 같은 쟁점으로 묶어 확인합니다: {title}",
                    source_ids=retained_source_ids,
                    risk="medium",
                )
            )
        return (
            pipeline.TopicCandidate(
                title=title,
                angle=str(topic_row.get("angle") or pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("angle", "")).strip(),
                slot=str(topic_row.get("slot") or pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("slot", "")).strip(),
                target_duration_sec=int(
                    topic_row.get("target_duration_sec")
                    or pipeline._strategy_int(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY, "target_duration_sec", 75)
                ),
                claims=claims,
                source_ids=retained_source_ids,
            ),
            sources,
        )

    title = str(slot.get("topic", "")).strip() or f"planned topic {index}"
    return (
        pipeline.TopicCandidate(
            title=title,
            angle=str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("angle", "")).strip(),
            slot=str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("slot", "")).strip(),
            target_duration_sec=pipeline._strategy_int(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY, "target_duration_sec", 75),
            claims=[_fallback_claim(slot, source_ids)],
            source_ids=source_ids,
        ),
        sources,
    )


def _fallback_claim(slot: dict[str, Any], source_ids: list[str]) -> pipeline.Claim:
    claim_template = str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("claim_text_template", ""))
    topic = str(slot.get("topic", "")).strip()
    source_title = ""
    if source_ids:
        source_title = source_ids[0]
    text = pipeline._format_prompt_template(
        claim_template,
        {"publisher": source_title, "title": topic, "query": ""},
    ).strip() or topic
    return pipeline.Claim(text=text, source_ids=source_ids, risk="medium")


def _slot_date(slot: dict[str, Any]) -> str:
    publish_at = str(slot.get("publish_at_local", ""))
    return publish_at[:10]


def _slot_is_future(slot: dict[str, Any]) -> bool:
    publish_at = str(slot.get("publish_at_local") or "")
    if not publish_at:
        return False
    try:
        parsed = dt.datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc) > dt.datetime.now(dt.timezone.utc)


def _plan_enforces_future_slots(plan: dict[str, Any]) -> bool:
    return bool(plan.get("created_at") or plan.get("timezone") or plan.get("mode"))


def _selected_slots(
    plan: dict[str, Any],
    *,
    target_date: str | None,
    limit: int,
    include_not_ready: bool,
) -> list[dict[str, Any]]:
    slots = [slot for slot in plan.get("slots", []) if isinstance(slot, dict)]
    if target_date:
        slots = [slot for slot in slots if _slot_date(slot) == target_date]
    if _plan_enforces_future_slots(plan):
        slots = [slot for slot in slots if _slot_is_future(slot)]
    if not include_not_ready:
        slots = [slot for slot in slots if slot.get("ready_for_generation")]
    if limit > 0:
        slots = slots[:limit]
    return slots


def generate_from_plan(
    plan_path: Path,
    *,
    output_dir: Path = pipeline.DEFAULT_OUTPUT_DIR / "scheduled_packages",
    target_date: str | None = None,
    limit: int = 3,
    include_not_ready: bool = False,
    image_mode: str = "auto",
    real_image_limit: int = 9,
    dry_run: bool = False,
) -> dict[str, Any]:
    plan = _read_json(plan_path)
    selected = _selected_slots(
        plan,
        target_date=target_date or str(plan.get("start_day", "")) or None,
        limit=limit,
        include_not_ready=include_not_ready,
    )
    results: list[dict[str, Any]] = []
    for index, slot in enumerate(selected, start=1):
        topic, sources = _topic_from_slot(slot, index)
        content_format = str(slot.get("format") or "auto")
        item: dict[str, Any] = {
            "slot": index,
            "publish_at_local": slot.get("publish_at_local"),
            "format": content_format,
            "topic": topic.title,
            "dry_run": dry_run,
        }
        if dry_run:
            item["status"] = "selected"
            results.append(item)
            continue
        slot_discovery = slot.get("topic_discovery") if isinstance(slot.get("topic_discovery"), dict) else {}
        result = pipeline.run_for_topic(
            topic,
            sources,
            output_dir=output_dir,
            image_mode=image_mode,
            real_image_limit=real_image_limit,
            content_format=content_format,
            topic_discovery={
                **slot_discovery,
                "mode": "rolling_schedule_plan",
                "plan_path": str(plan_path),
                "slot_publish_at_local": slot.get("publish_at_local"),
            },
            planned_publish_at_local=str(slot.get("publish_at_local", "")),
        )
        manifest = json.loads(Path(result.artifacts.manifest_json).read_text(encoding="utf-8"))
        item.update(
            {
                "run_id": result.run_id,
                "status": result.status,
                "quality_score": result.quality.publish_ready_score,
                "review": result.review.recommendation,
                "blockers": result.review.blockers + result.quality.blockers,
                "caption": result.script.caption,
                "post_title": result.script.post_title,
                "scene_headlines": [scene.on_screen_text for scene in result.script.scenes],
                "hashtags": result.script.hashtags,
                "mp4": result.artifacts.mp4,
                "manifest": result.artifacts.manifest_json,
                "report_html": result.artifacts.report_html,
                "schedule_status": manifest.get("schedule_status"),
            }
        )
        results.append(item)

    title_counts = Counter(
        str(item.get("post_title") or "").strip()
        for item in results
        if str(item.get("post_title") or "").strip()
    )
    duplicate_post_titles = sorted(title for title, count in title_counts.items() if count > 1)
    generic_post_title_issues = [
        {"run_id": str(item.get("run_id") or ""), "post_title": title, "issue": "generic_short_question_title"}
        for item in results
        for title in [str(item.get("post_title") or "").strip()]
        if title in {"검찰 발언, 기록은?", "김건희 수사, 빈칸은?", "조국 낙선, 원인은?"}
        or bool(re.search(r"^(검찰|김건희|조국).{0,8}(기록은|빈칸은|원인은)\?$", title))
    ]
    generic_caption_issues = [
        {"run_id": str(item.get("run_id") or ""), "issue": "generic_repeated_caption"}
        for item in results
        for caption in [str(item.get("caption") or "")]
        if "핵심은 누가 이겼냐가 아니라" in caption or "확인된 보도와 반론을 같이 놓고 봅니다" in caption
    ]
    scene_headline_issues: list[dict[str, str]] = []
    banned_scene_fragments = ["핵심 체크", "핵심 기준", " 체크", "포인트"]
    for item in results:
        run_id = str(item.get("run_id") or "")
        headlines = [str(value or "").strip() for value in item.get("scene_headlines") or []]
        seen_headlines: dict[str, int] = {}
        for index, headline in enumerate(headlines, start=1):
            compact = "".join(headline.split())
            for fragment in banned_scene_fragments:
                if fragment in headline:
                    scene_headline_issues.append(
                        {"run_id": run_id, "scene": str(index), "issue": f"generic_headline:{fragment}"}
                    )
            if compact in seen_headlines:
                scene_headline_issues.append(
                    {
                        "run_id": run_id,
                        "scene": str(index),
                        "issue": f"duplicate_of_scene_{seen_headlines[compact]}",
                    }
                )
            elif compact:
                seen_headlines[compact] = index
    base_ok = all(item.get("status") in {"publish_ready", "selected"} for item in results)
    batch_quality_ok = (
        not duplicate_post_titles
        and not generic_post_title_issues
        and not generic_caption_issues
        and not scene_headline_issues
    )
    summary = {
        "ok": base_ok and batch_quality_ok,
        "plan_path": str(plan_path),
        "target_date": target_date or plan.get("start_day"),
        "selected_count": len(selected),
        "generated_count": sum(1 for item in results if item.get("status") == "publish_ready"),
        "dry_run": dry_run,
        "batch_quality": {
            "ok": batch_quality_ok,
            "unique_post_title_count": len(title_counts),
            "duplicate_post_titles": duplicate_post_titles,
            "generic_post_title_issues": generic_post_title_issues,
            "generic_caption_issues": generic_caption_issues,
            "scene_headline_issues": scene_headline_issues,
        },
        "results": results,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AiNo TikTok packages from a rolling schedule plan.")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR / "scheduled_packages")
    parser.add_argument("--date", dest="target_date")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--include-not-ready", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    parser.add_argument("--real-image-limit", type=int, default=int(os.environ.get("AINO_REAL_IMAGE_LIMIT", "9")))
    args = parser.parse_args()

    plan_path = args.plan
    if plan_path is None:
        plan_result = schedule_planner.build_rolling_plan(days=max(1, args.days))
        plan_path = Path(str(plan_result["path"]))
    summary = generate_from_plan(
        plan_path,
        output_dir=args.output_dir,
        target_date=args.target_date,
        limit=max(0, args.limit),
        include_not_ready=args.include_not_ready,
        image_mode=args.image_mode,
        real_image_limit=max(0, args.real_image_limit),
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
