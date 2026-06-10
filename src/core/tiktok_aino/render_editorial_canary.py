"""Render one Editorial OS v2 canary through the existing media pipeline.

This creates local media artifacts only. It never enqueues or uploads to TikTok.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.core.tiktok_aino import editorial_os_v2, pipeline, privacy, render_editorial_batch


CANARY_SOURCE_ROWS = [
    {
        "source_id": "nec_stats",
        "title": "중앙선거관리위원회 선거통계시스템",
        "url": "https://info.nec.go.kr/",
        "note": "제9회 전국동시지방선거 개표/당선인 공식 확인 경로",
    },
    {
        "source_id": "ytn_result_20260604",
        "title": "YTN: 민주, 12대 4 판정승",
        "url": "https://www.ytn.co.kr/_cs/_ln_0101_202606041340199129_005.html",
        "note": "6·3 지방선거 광역단체장 16곳 중 민주당 12곳, 국민의힘 4곳 보도",
    },
    {
        "source_id": "sbs_result_20260604",
        "title": "SBS: 민주 12대 국민의힘 4",
        "url": "https://news.sbs.co.kr/news/endPage.do?cooper=GSTAND&news_id=N1008595681&plink=RSSLINK",
        "note": "광역단체장 12대4와 서울시장 결과를 함께 보도",
    },
    {
        "source_id": "hani_analysis_20260604",
        "title": "한겨레: 12 대 4, 선거 결과 총평",
        "url": "https://www.hani.co.kr/arti/politics/politics_general/1261922.html",
        "note": "12대4 결과의 정치적 해석과 승패 원인 분석",
    },
]


CANARY_SCENE_BODIES = [
    "선거가 끝나면 프레임 싸움이 시작됩니다. 그런데 이번 숫자는 변명보다 차갑습니다.",
    "핵심은 누가 웃었냐가 아닙니다. 어떤 설명이 더 이상 통하지 않았냐입니다.",
    "졌지만 잘 싸웠다는 말은 위로가 될 수 있어도, 책임을 대신하진 못합니다.",
    "숨은 지지층, 언론 탓, 프레임 탓. 시민은 결국 생활과 책임으로 판단합니다.",
    "장바구니와 월급명세서는 정치권의 방어 논리를 오래 기다려주지 않습니다.",
    "진보는 심판, 반대편은 과장이라 말합니다. 바로 여기서 댓글 논쟁이 붙습니다.",
    "결과를 축제로만 쓰면 금방 식습니다. 책임의 언어로 바뀔 때 공유가 생깁니다.",
    "숫자 하나로 모든 걸 설명할 수는 없습니다. 그래서 원자료와 반론을 함께 봅니다.",
    "당신은 이 결과를 실력 차로 봅니까, 심판 여론으로 봅니까. 근거로 댓글에 붙어봅시다.",
]


def build_canary_sources() -> dict[str, pipeline.Source]:
    return {
        row["source_id"]: pipeline.Source(
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"],
            note=row["note"],
        )
        for row in CANARY_SOURCE_ROWS
    }


def build_canary_topic(package: editorial_os_v2.EditorialCanaryPackage) -> pipeline.TopicCandidate:
    source_ids = [row["source_id"] for row in CANARY_SOURCE_ROWS]
    return pipeline.TopicCandidate(
        title=package.brief.post_title,
        angle=package.brief.thesis,
        slot="editorial_canary",
        target_duration_sec=75,
        claims=[
            pipeline.Claim(
                text="6·3 지방선거 광역단체장 결과는 16곳 중 더불어민주당 12곳, 국민의힘 4곳으로 보도됐다.",
                source_ids=["nec_stats", "ytn_result_20260604", "sbs_result_20260604"],
                risk="low",
            ),
            pipeline.Claim(
                text="서울시장 결과와 12대4 전체 성적표가 동시에 해석 쟁점으로 남았다.",
                source_ids=["ytn_result_20260604", "sbs_result_20260604", "hani_analysis_20260604"],
                risk="medium",
            ),
            pipeline.Claim(
                text="결과 해석은 승패 자랑보다 책임론과 프레임 경쟁을 분리해서 봐야 한다.",
                source_ids=["hani_analysis_20260604", "ytn_result_20260604"],
                risk="medium",
            ),
        ],
        source_ids=source_ids,
    )


def build_canary_script(package: editorial_os_v2.EditorialCanaryPackage) -> pipeline.ScriptPackage:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    caption = (
        "6·3 지방선거 광역단체장 결과는 12대4였습니다. 그런데 핵심은 숫자 자랑이 아니라, "
        "'졌잘싸'라는 방어 프레임이 왜 민심 앞에서 약해졌는지입니다. 서울 결과와 전체 성적표를 "
        "같이 놓고, 책임론과 반론을 분리해 봅니다. 여러분은 실력 차라고 보나요, 심판론이라고 보나요?"
    )
    pinned_comment = (
        "댓글로 붙어봅시다. 실력 차 vs 심판론, 어느 쪽인가요? 근거 있는 반박은 공유하고, "
        "다음 검증도 팔로우로 이어가겠습니다."
    )
    scenes: list[pipeline.Scene] = []
    for index, scene in enumerate(package.scenes):
        scenes.append(
            pipeline.Scene(
                scene_id=scene.scene_id,
                duration_sec=8,
                title=scene.role,
                body=CANARY_SCENE_BODIES[index],
                visual=scene.visual_prompt,
                on_screen_text=scene.hook_text,
            )
        )
    return pipeline.ScriptPackage(
        title=package.brief.post_title,
        caption=caption,
        hashtags=package.brief.hashtags,
        post_title=package.brief.post_title,
        post_body=caption,
        pinned_comment=pinned_comment,
        narration="\n".join(scene.body for scene in scenes),
        scenes=scenes,
        target_duration_sec=sum(scene.duration_sec for scene in scenes),
        sources=[row["source_id"] for row in CANARY_SOURCE_ROWS],
        disclosure=style.get("disclosure_policy", "AI-generated visual/audio disclosure required."),
        variant_id="editorial_os_v2_canary:script_override:reference_v3",
    )


def build_canary_topic_discovery(package: editorial_os_v2.EditorialCanaryPackage) -> dict[str, Any]:
    issue = package.brief.issue
    return {
        "mode": "editorial_os_v2_canary",
        "editorial_os_v2": asdict(package),
        "content_signature": asdict(package.signature),
        "deep_research_report": {
            "research_mode": "editorial_os_v2_canary",
            "selected_topic_id": issue.candidate_id,
            "selected_archetype_label": "public-interest election result explainer",
            "selected_research_question": issue.core_question,
            "topic_candidates": [
                {
                    "topic_id": issue.candidate_id,
                    "title": issue.title,
                    "matched_archetype_label": "public-interest election result explainer",
                    "research_question": issue.core_question,
                    "counterpoint_focus": issue.opposing_trigger,
                    "comment_trigger": issue.comment_question,
                    "follower_promise": issue.public_interest_angle,
                }
            ],
            "visual_mandates": [
                "Use scene-specific realistic cinematic visuals.",
                "Avoid real politician likenesses, party logos, fake official documents, and fake news UI.",
                "Use concise in-image text only as generated diegetic text.",
            ],
            "source_requirements": issue.source_requirements,
            "risk_notes": issue.risk_notes,
        },
    }


def render_canary(
    *,
    output_dir: Path,
    image_mode: str,
    real_image_limit: int | None,
    privacy_mode: str,
    content_format: str,
    reuse_visual_assets_from: Path | None = None,
) -> dict[str, Any]:
    pipeline._load_env_files()
    os.environ["AINO_PRIVACY_MODE"] = privacy.normalize_mode(privacy_mode)
    os.environ.setdefault("ELEVENLABS_ENABLE_LOGGING", "false")
    package = editorial_os_v2.build_canary_package(seed="election_12_4")
    sources = build_canary_sources()
    topic = build_canary_topic(package)
    script = build_canary_script(package)
    reused_visual_assets = render_editorial_batch._load_reused_visual_assets(reuse_visual_assets_from)
    result = pipeline.run_for_topic(
        topic,
        sources,
        output_dir=output_dir,
        image_mode=image_mode,
        real_image_limit=real_image_limit,
        content_format=content_format,
        topic_discovery=build_canary_topic_discovery(package),
        script_override=script,
        visual_assets_override=reused_visual_assets,
    )
    manifest_path = Path(result.artifacts.manifest_json)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    upload_validation = pipeline.validate_manifest_for_upload(manifest)
    summary = {
        "ok": result.status in {"publish_ready", "upload_ready"},
        "run_id": result.run_id,
        "status": result.status,
        "reuse_visual_assets_from": str(reuse_visual_assets_from) if reuse_visual_assets_from else "",
        "manifest_path": str(manifest_path),
        "mp4": result.artifacts.mp4,
        "report_html": result.artifacts.report_html,
        "mobile_preview_storyboard": result.artifacts.mobile_preview_storyboard,
        "audio_provider": manifest.get("audio_asset", {}).get("provider"),
        "audio_status": manifest.get("audio_asset", {}).get("status"),
        "layout_quality": manifest.get("layout_quality"),
        "visual_quality": manifest.get("visual_quality"),
        "quality": manifest.get("quality"),
        "review": manifest.get("review"),
        "upload_validation": upload_validation,
    }
    summary_path = manifest_path.parent / "editorial_canary_render_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render one Editorial OS v2 canary through AiNo pipeline.")
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR / "editorial_canary_renders")
    parser.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    parser.add_argument("--real-image-limit", type=int, default=pipeline.default_real_image_limit_from_env())
    parser.add_argument("--reuse-visual-assets-from", type=Path, default=None)
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
    args = parser.parse_args(argv)
    summary = render_canary(
        output_dir=args.output_dir,
        image_mode=args.image_mode,
        real_image_limit=None if args.real_image_limit is None else max(0, args.real_image_limit),
        privacy_mode=args.privacy_mode,
        content_format=args.content_format,
        reuse_visual_assets_from=args.reuse_visual_assets_from,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
