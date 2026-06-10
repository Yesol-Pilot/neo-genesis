import json
from types import SimpleNamespace

from src.core.tiktok_aino import pipeline, render_editorial_batch, render_editorial_canary


def _bundle():
    scenes = [
        {
            "role": role,
            "hook_text": f"Hook {index}",
            "narration": f"Narration {index}. Leave a comment with your evidence.",
            "visual_override": {
                "location": f"location {index}",
                "camera": f"camera {index}",
                "palette": f"palette {index}",
                "anchors": [f"anchor {index}", "source folder"],
                "treatment_id": f"treatment_{index}",
                "concrete_scene": f"cinematic scene {index}",
                "render_style": "cinematic_subtitle",
            },
        }
        for index, role in enumerate(
            [
                "thumbnail",
                "context",
                "opposing_frame",
                "why_now",
                "public_cost",
                "comment_trigger",
                "share_line",
                "fairness",
                "cta",
            ],
            start=1,
        )
    ]
    return {
        "batch_id": "test_batch",
        "items": [
            {
                "item_id": "test_item",
                "title": "Source backed test topic",
                "angle": "A fact-backed angle for a civic explainer.",
                "post_title": "One clean test title",
                "caption": "This is a source-backed caption with enough context for upload validation.",
                "pinned_comment": "What is your evidence-backed interpretation?",
                "hashtags": ["test", "aino"],
                "sources": [
                    {
                        "source_id": "src1",
                        "title": "Source 1",
                        "url": "https://example.com/one",
                        "note": "primary source",
                    },
                    {
                        "source_id": "src2",
                        "title": "Source 2",
                        "url": "https://example.com/two",
                        "note": "secondary source",
                    },
                ],
                "claims": [
                    {"text": "Claim one is backed.", "source_ids": ["src1"], "risk": "low"},
                    {"text": "Claim two is backed.", "source_ids": ["src1", "src2"], "risk": "medium"},
                ],
                "scenes": scenes,
            }
        ],
    }


def test_visual_override_payload_is_parsed():
    scene_row = _bundle()["items"][0]["scenes"][0]
    scene = render_editorial_batch._scene_from_row(scene_row, 1)
    override = pipeline._parse_scene_visual_override(scene)

    assert override["location"] == "location 1"
    assert override["treatment_id"] == "treatment_1"
    assert override["render_style"] == "cinematic_subtitle"
    assert pipeline._visual_override_scene_text(scene, override) == "cinematic scene 1"


def test_cinematic_subtitle_visual_override_disables_diegetic_text():
    scene_row = _bundle()["items"][0]["scenes"][0]
    scene = render_editorial_batch._scene_from_row(scene_row, 1)
    topic = pipeline.TopicCandidate(
        title="선거 프레임 논쟁",
        angle="실제 상황 묘사와 자막형 렌더 테스트",
        slot="test",
        target_duration_sec=72,
        claims=[],
        source_ids=[],
    )

    brief = pipeline._build_visual_brief(topic, scene, 0, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.render_style == "cinematic_subtitle"
    assert brief.diegetic_text == ""
    assert "No readable in-image text" in brief.diegetic_text_directive
    assert "Render style: cinematic subtitle plate" in prompt
    assert "Mandatory text-prop foreground" not in prompt
    assert not any("paper card" in anchor.casefold() for anchor in brief.visual_anchor)


def test_render_batch_dry_run_writes_summary(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "renders"

    summary = render_editorial_batch.render_batch(
        bundle_path,
        output_dir=output_dir,
        image_mode="local",
        real_image_limit=0,
        privacy_mode="local_only",
        content_format="debate_followup",
        limit=0,
        dry_run=True,
    )

    assert summary["ok"] is True
    assert summary["requested_count"] == 1
    assert summary["results"][0]["status"] == "selected"
    assert summary["results"][0]["scene_count"] == 9
    assert (output_dir / "editorial_batch_summary.json").exists()


def test_render_batch_can_filter_item_ids(tmp_path):
    bundle = _bundle()
    second = dict(bundle["items"][0])
    second["item_id"] = "other_item"
    second["post_title"] = "Other clean title"
    bundle["items"].append(second)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    summary = render_editorial_batch.render_batch(
        bundle_path,
        output_dir=tmp_path / "filtered",
        image_mode="local",
        real_image_limit=0,
        privacy_mode="local_only",
        content_format="debate_followup",
        limit=0,
        dry_run=True,
        item_ids=["other_item"],
    )

    assert summary["requested_count"] == 1
    assert summary["results"][0]["item_id"] == "other_item"


def test_load_reused_visual_assets_from_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    image_path = tmp_path / "scene.png"
    image_path.write_bytes(b"fake")
    (run_dir / "visual_assets.json").write_text(
        json.dumps(
            [
                {
                    "scene_id": 1,
                    "provider": "codex_cli",
                    "status": "generated",
                    "path": str(image_path),
                    "prompt": "prompt",
                    "visual_brief": {"render_style": "cinematic_subtitle"},
                    "visual_quality": {"score": 100},
                    "notes": ["generated"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assets = render_editorial_batch._load_reused_visual_assets(run_dir)

    assert assets is not None
    assert assets[0].scene_id == 1
    assert assets[0].provider == "codex_cli"
    assert assets[0].visual_brief["render_style"] == "cinematic_subtitle"
    assert "reused_visual_asset" in assets[0].notes


def test_render_canary_reuses_visual_assets_from_existing_run(tmp_path, monkeypatch):
    reuse_dir = tmp_path / "existing_run"
    reuse_dir.mkdir()
    manifest_path = tmp_path / "new_run" / "manifest.json"
    fake_assets = [
        pipeline.VisualAsset(
            scene_id=1,
            provider="codex_cli",
            status="generated",
            path=str(tmp_path / "scene_01.png"),
            prompt="prompt",
            visual_brief={"render_style": "cinematic_subtitle"},
            visual_quality={"score": 100},
            notes=["reused_visual_asset"],
        )
    ]
    captured: dict[str, object] = {}

    def fake_load_reused_visual_assets(path):
        captured["reuse_path"] = path
        return fake_assets

    def fake_run_for_topic(*_args, **kwargs):
        captured["visual_assets_override"] = kwargs.get("visual_assets_override")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "audio_asset": {"provider": "elevenlabs", "status": "generated"},
                    "layout_quality": {"passed": True},
                    "visual_quality": {"passed": True},
                    "quality": {"passed": True},
                    "review": {"passed": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            status="publish_ready",
            run_id="test_run",
            artifacts=SimpleNamespace(
                manifest_json=str(manifest_path),
                mp4=str(manifest_path.parent / "preview.mp4"),
                report_html=str(manifest_path.parent / "report.html"),
                mobile_preview_storyboard=str(manifest_path.parent / "storyboard.png"),
            ),
        )

    monkeypatch.setattr(render_editorial_batch, "_load_reused_visual_assets", fake_load_reused_visual_assets)
    monkeypatch.setattr(render_editorial_canary.pipeline, "run_for_topic", fake_run_for_topic)
    monkeypatch.setattr(render_editorial_canary.pipeline, "validate_manifest_for_upload", lambda _manifest: {"blockers": []})

    summary = render_editorial_canary.render_canary(
        output_dir=tmp_path / "renders",
        image_mode="auto",
        real_image_limit=0,
        privacy_mode="local_only",
        content_format="reward_deep",
        reuse_visual_assets_from=reuse_dir,
    )

    assert captured["reuse_path"] == reuse_dir
    assert captured["visual_assets_override"] is fake_assets
    assert summary["ok"] is True
    assert summary["reuse_visual_assets_from"] == str(reuse_dir)


def test_script_override_metadata_preserves_source_backed_caption_and_tags():
    script = pipeline.ScriptPackage(
        title="이재명 취임 1년, 165분 기자회견",
        caption=(
            "165분 기자회견을 두고 평가는 갈렸습니다. 같은 장면을 서로 다르게 읽는 이유를 봅니다. "
            "팔로우하면 다음 기자회견 여론 흐름도 이어갑니다."
        ),
        hashtags=["이재명", "취임1주년", "기자회견", "여론조사", "민주당", "국민의힘", "정치뉴스", "시사"],
        post_title="165분 기자회견, 숫자가 아니라 장면이 갈랐다",
        post_body="165분 기자회견을 같은 장면, 다른 해석의 구조로 봅니다.",
        pinned_comment="소통인가요, 홍보쇼인가요? 팔로우하면 다음 흐름도 이어갑니다.",
        narration="테스트 내레이션입니다.",
        scenes=[
            pipeline.Scene(
                scene_id=index,
                duration_sec=8,
                title="scene",
                body="장면 설명입니다. 팔로우하면 다음 흐름도 이어갑니다." if index == 9 else "장면 설명입니다.",
                visual="visual",
                on_screen_text=f"장면 {index}",
            )
            for index in range(1, 10)
        ],
        target_duration_sec=72,
        sources=["src1"],
        disclosure="generated disclosure",
        variant_id="editorial_batch:test",
    )
    topic = pipeline.TopicCandidate(
        title="이재명 취임 1년, 165분 기자회견이 갈라놓은 것",
        angle="165분 즉문즉답과 여론조사 반응을 본다.",
        slot="live_issue",
        target_duration_sec=72,
        claims=[pipeline.Claim(text="165분 기자회견 보도", source_ids=["src1"], risk="low")],
        source_ids=["src1"],
    )
    sources = {"src1": pipeline.Source(source_id="src1", title="source", url="https://example.com", note="note")}

    enriched = pipeline._enrich_post_metadata(script, topic, sources, preserve_existing=True)

    assert "165분 기자회견을 두고 평가는 갈렸습니다" in enriched.caption
    assert "검찰개혁" not in enriched.caption
    assert "검찰개혁" not in enriched.hashtags
    assert enriched.hashtags == script.hashtags
    assert enriched.post_title == script.post_title
    assert "댓글" in enriched.pinned_comment

    selected, _gate, _readability, _quality = pipeline.select_publish_script(
        [script],
        topic,
        sources,
        preserve_existing_metadata=True,
    )

    assert "165분 기자회견을 두고 평가는 갈렸습니다" in selected.caption
    assert "검찰개혁" not in selected.caption
    assert "검찰개혁" not in selected.hashtags
    assert selected.hashtags == script.hashtags
    assert "댓글" in selected.pinned_comment
