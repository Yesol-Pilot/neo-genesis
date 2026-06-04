import datetime as dt
import io
import json
import os

from src.core.tiktok_aino import generate_from_schedule, ha_publisher, monitoring, pipeline, schedule_planner, upload_automation
from src.core.tiktok_aino.pipeline import _preprocess_korean_tts, _scene_card_duration, _trim_letterbox

from PIL import Image, ImageDraw


def test_runtime_env_loader_reads_repo_env_without_overriding(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "REPO_DIR", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ELEVENLABS_MODEL_ID", "already-set")
    (tmp_path / ".env.local").write_text(
        "OPENAI_API_KEY=from-local\nELEVENLABS_MODEL_ID=from-file\nQUOTED_VALUE=\"quoted\"\n",
        encoding="utf-8",
    )

    pipeline._load_runtime_env_files()

    assert os.environ["OPENAI_API_KEY"] == "from-local"
    assert os.environ["ELEVENLABS_MODEL_ID"] == "already-set"
    assert os.environ["QUOTED_VALUE"] == "quoted"


def _hot_candidate_value(key: str, fallback: str = "") -> str:
    return str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get(key, fallback))


def _configured_hot_claim(publisher: str, title: str, source_id: str) -> pipeline.Claim:
    return pipeline.Claim(
        pipeline._format_prompt_template(
            _hot_candidate_value("claim_text_template"),
            {"publisher": publisher, "title": title},
        ),
        [source_id],
    )


def _configured_hot_scene(index: int) -> dict:
    return pipeline.HOT_TOPIC_SCRIPT_STRATEGY["scenes"][index]


def test_schedule_generator_selects_ready_slots_by_date() -> None:
    plan = {
        "slots": [
            {"publish_at_local": "2026-05-13T08:10:00+09:00", "ready_for_generation": True},
            {"publish_at_local": "2026-05-13T19:30:00+09:00", "ready_for_generation": False},
            {"publish_at_local": "2026-05-14T08:10:00+09:00", "ready_for_generation": True},
        ]
    }

    selected = generate_from_schedule._selected_slots(
        plan,
        target_date="2026-05-13",
        limit=3,
        include_not_ready=False,
    )

    assert len(selected) == 1
    assert selected[0]["publish_at_local"].startswith("2026-05-13")


def test_format_upload_slots_match_account_dayparts() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    configured_slots = [row["slot"] for row in style["daily_slots"]]

    assert configured_slots == ["08:10", "11:20", "19:30"]
    assert pipeline.FORMAT_SPECS["growth_short"].upload_slot == configured_slots[0]
    assert pipeline.FORMAT_SPECS["reward_deep"].upload_slot == configured_slots[1]
    assert pipeline.FORMAT_SPECS["debate_followup"].upload_slot == configured_slots[2]


def test_schedule_generator_rebuilds_topic_with_sources() -> None:
    slot = {
        "topic": "planned issue",
        "sources": [{"source_id": "s1", "title": "publisher: planned issue", "url": "https://example.com", "note": "note"}],
        "topic_candidate": {
            "title": "planned issue",
            "angle": "accountable framing",
            "slot": "hot issue",
            "target_duration_sec": 75,
            "claims": [{"text": "reported claim", "source_ids": ["s1"], "risk": "medium"}],
            "source_ids": ["s1"],
        },
    }

    topic, sources = generate_from_schedule._topic_from_slot(slot, 1)

    assert topic.title == "planned issue"
    assert topic.claims[0].text == "reported claim"
    assert list(sources) == ["s1"]


def test_schedule_topic_filters_same_query_but_unrelated_support_claims() -> None:
    slot = {
        "topic": "“교복 대신 의류바우처”…송영기, 거제교육연대와 정책 협약",
        "sources": [
            {"source_id": "hot_news_plan_09", "title": "거제타임즈: 교복 대신 의류바우처"},
            {"source_id": "hot_news_plan_09_support_02", "title": "v.daum.net: 신경호 교육감 정책"},
        ],
        "topic_candidate": {
            "title": "“교복 대신 의류바우처”…송영기, 거제교육연대와 정책 협약",
            "angle": "최근 보도 검증",
            "slot": "hot discovery",
            "target_duration_sec": 75,
            "claims": [
                {
                    "text": "거제타임즈 보도 제목 기준: “교복 대신 의류바우처”…송영기, 거제교육연대와 정책 협약",
                    "source_ids": ["hot_news_plan_09"],
                    "risk": "medium",
                },
                {
                    "text": "v.daum.net 보도 제목 기준: 신경호 강원도교육감 후보 교권 정책 발표",
                    "source_ids": ["hot_news_plan_09_support_02"],
                    "risk": "medium",
                },
            ],
            "source_ids": ["hot_news_plan_09", "hot_news_plan_09_support_02"],
        },
    }

    topic, sources = generate_from_schedule._topic_from_slot(slot, 1)

    assert len(topic.claims) == 1
    assert topic.source_ids == ["hot_news_plan_09"]
    assert list(sources) == ["hot_news_plan_09"]


def test_visual_beats_use_controlled_motion_by_default() -> None:
    scenes = [
        pipeline.Scene(1, 8, "Hook", "Body text long enough for cards.", "visual", "Hook text"),
        pipeline.Scene(2, 8, "CTA", "Question body text long enough?", "visual", "Question text"),
    ]
    beats = pipeline.build_visual_beats(scenes, pipeline.FORMAT_SPECS["growth_short"])
    summary = pipeline._visual_motion_summary(beats)

    assert beats
    assert not summary["all_static_hold"]
    assert summary["camera_motion_count"] > 0
    assert max(abs(beat.pan_x) for beat in beats) <= 40
    assert max(beat.zoom_end for beat in beats) <= 1.08


def test_schedule_feedback_adjusts_candidate_scores() -> None:
    rows = [
        {"title": "김건희 의혹 후속", "query": "김건희", "publisher": "A", "score": 100},
        {"title": "노동 인권 쟁점", "query": "노동 인권", "publisher": "B", "score": 95},
    ]
    feedback = {
        "enabled": True,
        "term_scores": {"김건희": -20, "노동": 15},
        "format_scores": {},
    }

    adjusted = schedule_planner._apply_feedback_to_candidates(rows, feedback)

    assert adjusted[0]["title"] == "노동 인권 쟁점"
    assert adjusted[0]["feedback_adjustment"] == 15
    assert adjusted[1]["feedback_adjustment"] == -20


def test_schedule_planner_print_json_falls_back_to_utf8(monkeypatch) -> None:
    class Cp949Stdout:
        def __init__(self) -> None:
            self.buffer = io.BytesIO()

        def write(self, _text: str) -> int:
            raise UnicodeEncodeError("cp949", "⋯", 0, 1, "illegal multibyte sequence")

        def flush(self) -> None:
            pass

    stdout = Cp949Stdout()
    monkeypatch.setattr(schedule_planner.sys, "stdout", stdout)

    schedule_planner._print_json({"title": "계획 ⋯"})

    assert "계획 ⋯".encode("utf-8") in stdout.buffer.getvalue()


def test_schedule_feedback_reads_performance_feedback_artifact(tmp_path) -> None:
    artifact = {
        "version": "performance_feedback_v1",
        "sample_count": 3,
        "feedback": {
            "term_scores": {"노동": 15},
            "format_scores": {"reward_deep": 8, "growth_short": -4},
            "visual_scores": {"role:evidence": 4},
            "positive_terms": ["노동"],
            "negative_terms": [],
            "notes": ["test"],
            "sample_count": 3,
        },
    }
    path = tmp_path / "performance_feedback.json"
    path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")

    feedback = schedule_planner._load_performance_feedback(path)

    assert feedback["enabled"] is True
    assert feedback["term_scores"]["노동"] == 15
    assert feedback["format_scores"]["reward_deep"] == 8
    assert schedule_planner._format_sequence_from_feedback(feedback)[0] == "reward_deep"


def test_studio_feedback_suppresses_recent_weak_template_terms() -> None:
    rows = [
        monitoring.StudioContentRow(
            title="나는 이재명을 처음엔 좋아하지 않았다. #대통령 #이재명 #정치 #진보 #대선",
            created_at_text="2025년 4월 20일 오전 8:18",
            privacy="모두",
            views=35000,
            likes=5190,
            comments=914,
            duration_sec=63,
            pinned=True,
        ),
        monitoring.StudioContentRow(
            title="이 이슈, 왜 지금? 기록으로 다시 보기 평택시 미래기술학교 교육생 모집 사안입니다. 핵심은 교육 보도에서 반복된 쟁점입니다.",
            created_at_text="5월 17일 오전 8:10",
            privacy="모두",
            views=84,
            likes=0,
            comments=0,
            duration_sec=64,
            pinned=False,
        ),
    ]

    feedback = monitoring.build_account_reference_feedback(rows)

    assert "이재명" in feedback["positive_terms"]
    assert "이슈" in feedback["negative_terms"]
    assert feedback["term_scores"]["이슈"] < 0
    assert feedback["weak_sample_count"] == 1


def test_schedule_excludes_scheduled_and_weak_report_rows(tmp_path) -> None:
    report = {
        "scheduled_rows": [
            {"title": "예약된 정치 이슈", "views": 0, "likes": 0, "comments": 0},
        ],
        "top_rows": [
            {"title": "최근 저성과 정치 이슈", "views": 120, "likes": 1, "comments": 0},
            {"title": "성과 좋은 정치 이슈", "views": 10000, "likes": 100, "comments": 50},
        ],
    }
    path = tmp_path / "performance_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    exclusions = schedule_planner._performance_report_exclusions(path)

    assert "예약된 정치 이슈" in exclusions
    assert "최근 저성과 정치 이슈" in exclusions
    assert "성과 좋은 정치 이슈" not in exclusions


def test_schedule_suppresses_negative_feedback_topics() -> None:
    feedback = {
        "enabled": True,
        "term_scores": {"이슈": -14, "기록": -14},
        "negative_terms": ["이슈", "기록"],
    }

    assert schedule_planner._is_suppressed_by_feedback("이 이슈, 왜 지금? 기록으로 다시 보기", feedback)
    assert not schedule_planner._is_suppressed_by_feedback("윤석열 특검 책임 기준", feedback)


def test_hot_hook_fallback_uses_topic_specific_term() -> None:
    first = pipeline._hot_hook_headline("집값은 잡고 거래는 살려야 한다 이재명 정부의 부동산 딜레마")
    second = pipeline._hot_hook_headline("세월호보다 늦은 제주항공 참사 대응 왜 이재명 정부는 더딘가")

    assert first != second
    assert "이 이슈" not in first
    assert "이 이슈" not in second


def test_schedule_plan_generation_uses_hot_topic_script() -> None:
    style = {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"}
    topic = pipeline.TopicCandidate(
        title="윤석열 계엄 정당화 메시지, 특검은 왜 다시 불렀나",
        angle="특검 소환 쟁점",
        slot="curated",
        target_duration_sec=75,
        claims=[
            pipeline.Claim(
                "특검은 윤석열 전 대통령에게 계엄 정당화 외교 메시지 의혹으로 출석을 통보했다.",
                ["curated_source"],
            )
        ],
        source_ids=["curated_source"],
    )

    script = pipeline.generate_script(topic, style, {"mode": "rolling_schedule_plan"})
    variants = pipeline.generate_script_variants(topic, style, {"mode": "rolling_schedule_plan"})

    assert script.variant_id == "hot_issue_check"
    assert [variant.variant_id for variant in variants] == ["hot_issue_check"]
    assert "아이들 교실" not in script.post_title
    assert "윤석열" in script.post_title or "특검" in script.post_title


def test_lightweight_research_scores_today_memory_and_hate_topics_high() -> None:
    row = {
        "title": "이 대통령, 노무현 추도식 조롱 논란에 일베식 사이트 폐쇄·징벌배상 검토",
        "publisher": "연합뉴스",
        "query": "노무현 추도식 일베",
        "score": 92,
        "published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    research = schedule_planner._lightweight_research_for_row(row)
    components = research["score_components"]

    assert components["progressive_reaction"] >= 80
    assert components["narrative_clarity"] >= 70
    assert "progressive_reaction_weak" not in research["production_risks"]
    assert "댓글로 유도" not in research["comment_trigger"]


def test_lightweight_research_adjustment_can_promote_strong_left_audience_topic() -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    rows = [
        {
            "title": "시청 업무협약 설명회 개최",
            "publisher": "지역신문",
            "query": "한국 정치",
            "score": 95,
            "published_at": now,
        },
        {
            "title": "노무현 추도식 조롱 논란, 혐오 조장 사이트 책임 검토",
            "publisher": "MBC",
            "query": "노무현 추도식 일베",
            "score": 70,
            "published_at": now,
        },
    ]

    adjusted = schedule_planner._apply_feedback_to_candidates(rows, {"enabled": False}, {"deep_research_report": {}})

    assert adjusted[0]["title"].startswith("노무현 추도식")
    assert adjusted[0]["deep_research_adjustment"] > 0


def test_hot_topic_script_builds_case_specific_court_brief() -> None:
    style = {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"}
    title = "'한덕수 재판 위증' 윤석열, 28일 1심 선고…구형은 징역 2년"
    topic = pipeline.TopicCandidate(
        title=title,
        angle=_hot_candidate_value("angle"),
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[
            _configured_hot_claim("연합뉴스", title, "hot_news_01"),
            _configured_hot_claim("이데일리", "특검, 윤석열 위증 혐의 징역 2년 선고 요청", "hot_news_02"),
        ],
        source_ids=["hot_news_01", "hot_news_02"],
    )
    sources = {
        "hot_news_01": pipeline.Source("hot_news_01", f"연합뉴스: {title}", "https://example.com/1", "test"),
        "hot_news_02": pipeline.Source(
            "hot_news_02",
            "이데일리: 특검, 윤석열 위증 혐의 징역 2년 선고 요청",
            "https://example.com/2",
            "test",
        ),
    }

    script = pipeline.apply_content_format(
        pipeline.generate_script(topic, style, {"mode": "rolling_schedule_plan"}),
        pipeline.FORMAT_SPECS["growth_short"],
        topic=topic,
        sources=sources,
    )
    scene_text = " ".join(scene.body for scene in script.scenes)
    quality = pipeline._score_script_quality(
        script,
        pipeline.check_policy(topic, script, sources, pipeline.FORMAT_SPECS["growth_short"]),
        pipeline.check_readability(script, pipeline.FORMAT_SPECS["growth_short"]),
        topic,
        sources,
        pipeline.FORMAT_SPECS["growth_short"],
    )

    assert "위증" in scene_text
    assert "구형" in scene_text
    assert "선고" in scene_text
    assert scene_text.count("전말과 근거를 나눠 봅니다") < 2
    assert "댓글로 유도" not in scene_text
    assert "위증" in script.hashtags
    assert "법원" in script.hashtags
    assert "김건희" not in script.hashtags
    assert "공천개입" not in script.hashtags
    assert not any(blocker.startswith("topic_anchor_terms_missing") for blocker in quality.blockers)


def test_hot_topic_script_uses_provocative_but_safe_debate_prompt() -> None:
    style = {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"}
    title = "이재명 대통령 \"일베 등 혐오 조장 사이트 폐쇄 및 징벌 공론화 필요\""
    topic = pipeline.TopicCandidate(
        title=title,
        angle=_hot_candidate_value("angle"),
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[
            _configured_hot_claim("연합뉴스", title, "hot_news_01"),
            _configured_hot_claim("MBC", "노무현 추도식 조롱 논란 뒤 혐오표현 제재 공론화", "hot_news_02"),
        ],
        source_ids=["hot_news_01", "hot_news_02"],
    )
    sources = {
        "hot_news_01": pipeline.Source("hot_news_01", f"연합뉴스: {title}", "https://example.com/1", "test"),
        "hot_news_02": pipeline.Source(
            "hot_news_02",
            "MBC: 노무현 추도식 조롱 논란 뒤 혐오표현 제재 공론화",
            "https://example.com/2",
            "test",
        ),
    }

    script = pipeline.apply_content_format(
        pipeline.generate_script(topic, style, {"mode": "rolling_schedule_plan"}),
        pipeline.FORMAT_SPECS["growth_short"],
        topic=topic,
        sources=sources,
    )
    full_text = pipeline._script_full_text(script)
    gate = pipeline.check_policy(topic, script, sources, pipeline.FORMAT_SPECS["growth_short"])

    assert "표현의 자유" in full_text
    assert "혐오 방치" in full_text
    assert "어디에 서나요" in full_text
    assert "반론·공유도 받습니다" in script.pinned_comment
    assert gate.passed
    assert not pipeline._contains_any(full_text, pipeline.UNSAFE_PROVOCATION_TERMS)


def test_fact_angle_storyboard_are_required_before_production() -> None:
    sources = {
        "s1": pipeline.Source("s1", "연합뉴스: 김건희 특검 수사 무마 의혹 입건", "https://example.com/1", "공개 보도"),
        "s2": pipeline.Source("s2", "한겨레: 계엄 관여 의혹 수사 속도", "https://example.com/2", "지원 보도"),
    }
    topic = pipeline.TopicCandidate(
        title="김건희 수사 무마 의혹 입건, 특검은 어디까지 보나",
        angle="특검 수사 쟁점",
        slot="hot",
        target_duration_sec=75,
        claims=[
            pipeline.Claim("연합뉴스 보도 기준: 특검이 수사 무마 의혹 관련 인물을 입건했다.", ["s1"], "medium"),
            pipeline.Claim("한겨레 보도 기준: 계엄 관여 의혹 수사도 함께 속도를 내고 있다.", ["s2"], "medium"),
        ],
        source_ids=["s1", "s2"],
    )
    topic_discovery = {
        "deep_research_report": {
            "selected_topic_id": "topic_1",
            "topic_candidates": [
                {
                    "topic_id": "topic_1",
                    "research_question": "무엇이 확인됐고 어떤 책임선이 남았나?",
                    "counterpoint_focus": "보도된 주장과 확정 사실의 경계",
                    "comment_trigger": "1 전말 2 근거 3 책임 중 어디를 먼저 봐야 하나요?",
                    "follower_promise": "후속 수사와 책임선을 계속 추적합니다.",
                }
            ],
        }
    }
    format_plan = pipeline.FORMAT_SPECS["reward_deep"]
    editorial_plan = pipeline.build_editorial_plan(topic, sources, format_plan, topic_discovery)

    fact_pack = pipeline.build_fact_pack(topic, sources, format_plan, topic_discovery)
    risk_flags = pipeline.build_risk_flags(topic, fact_pack, format_plan)
    source_card = pipeline.build_source_card(topic, sources, fact_pack)
    reference_fit = pipeline.build_reference_fit(topic, format_plan, fact_pack, source_card)
    angle_brief = pipeline.build_angle_brief(topic, fact_pack, editorial_plan, format_plan, topic_discovery)
    enriched_discovery = {
        **topic_discovery,
        "fact_pack": pipeline.asdict(fact_pack),
        "risk_flags": pipeline.asdict(risk_flags),
        "source_card": pipeline.asdict(source_card),
        "reference_fit": pipeline.asdict(reference_fit),
        "angle_brief": pipeline.asdict(angle_brief),
    }
    script = pipeline.apply_content_format(
        pipeline.generate_script(topic, {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"}, enriched_discovery),
        format_plan,
        topic=topic,
        sources=sources,
    )
    storyboard_brief = pipeline.build_storyboard_brief(topic, script, fact_pack, angle_brief, format_plan)
    tts_performance = pipeline.build_tts_performance_plan(script, angle_brief)

    assert fact_pack.gate_passed
    assert fact_pack.reported_claims[0].item_type == "reported_claim"
    assert risk_flags.gate_passed
    assert risk_flags.aigc.requires_label is True
    assert source_card.gate_passed
    assert source_card.source_url == "https://example.com/1"
    assert reference_fit.gate_passed
    assert reference_fit.selected_pattern_ids
    assert reference_fit.selected_hook_ids
    assert reference_fit.selected_scene_type_ids
    assert angle_brief.gate_passed
    assert "책임" in angle_brief.comment_question
    assert storyboard_brief.gate_passed
    assert all(scene.evidence_item_ids for scene in storyboard_brief.scenes)
    assert tts_performance.gate_passed


def test_upload_validation_blocks_missing_quality_workflow_artifacts(tmp_path) -> None:
    mp4 = tmp_path / "preview.mp4"
    mp4.write_bytes(b"fake")
    manifest = {
        "gate": {"passed": True},
        "readability": {"passed": True},
        "review": {"passed": True},
        "quality": {"passed": True},
        "audio_asset": {"provider": "elevenlabs", "status": "generated"},
        "mobile_visual_passed": True,
        "mobile_visual_checks": [{"passed": True, "text_render_passed": True}],
        "synced_duration_matches_format": True,
        "script": {
            "title": "검수 가능한 정치 뉴스",
            "caption": "검수 가능한 정치 뉴스 캡션",
            "post_title": "검수 가능한 정치 뉴스",
            "post_body": "검수 가능한 본문",
            "pinned_comment": "댓글로 기준을 남겨 주세요",
            "narration": "검수 가능한 한국어 내레이션입니다",
            "hashtags": ["정치", "뉴스"],
            "scenes": [
                {"scene_id": index, "body": "검수 가능한 한국어 본문입니다", "on_screen_text": "검수 카드 문구"}
                for index in range(1, 10)
            ],
        },
        "artifacts": {"mp4": str(mp4)},
    }

    validation = pipeline.validate_manifest_for_upload(manifest)

    assert validation["upload_ready"] is False
    assert "fact_pack_artifact_missing" in validation["technical_blockers"]
    assert "risk_flags_artifact_missing" in validation["technical_blockers"]
    assert "source_card_artifact_missing" in validation["technical_blockers"]
    assert "reference_fit_artifact_missing" in validation["technical_blockers"]
    assert "angle_brief_not_passed" in validation["technical_blockers"]


def test_hot_topic_script_avoids_bad_particles_for_question_titles() -> None:
    topic = pipeline.TopicCandidate(
        title="정청래 테러 모의 제보, 정치폭력은 누구에게 이익인가",
        angle="정치폭력 제보와 신변보호 쟁점",
        slot="curated",
        target_duration_sec=82,
        claims=[
            pipeline.Claim(
                "민주당은 정청래 대표를 겨냥한 테러 모의 제보를 이유로 경찰 수사와 신변보호를 요청했다.",
                ["curated_source"],
            )
        ],
        source_ids=["curated_source"],
    )

    script = pipeline.generate_script(
        topic,
        {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"},
        {"mode": "rolling_schedule_plan"},
    )

    assert script.title == "정치폭력, 누가 이익 보나?"
    assert "인가은" not in script.narration
    assert "누구에게 이익인가에서" not in script.narration


def test_recent_generated_titles_scan_all_tiktok_output_manifests(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "REPO_DIR", tmp_path)
    run_dir = tmp_path / "output" / "tiktok_aino_deep_research_smoke" / "leftaino_20260517_101010"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "topic": {"title": "중복 방지용 정치 이슈"},
                "script": {"post_title": "중복 방지용 제목"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    titles = schedule_planner._recent_generated_titles()

    assert "중복 방지용 정치 이슈" in titles
    assert "중복 방지용 제목" in titles


def test_duplicate_topic_blocks_configured_issue_anchors() -> None:
    assert schedule_planner._is_duplicate_topic(
        "국민의힘 5·18 반대론, 선거용인가 민주주의 기준인가",
        ["5·18 헌법 빈손, 누가 민주주의 방파제를 막았나"],
    )
    assert not schedule_planner._is_duplicate_topic(
        "김건희 관저 의혹, 21그램과 예산 전용 어디까지 왔나",
        ["윤석열 계엄 정당화 메시지, 특검은 왜 다시 불렀나"],
    )


def test_schedule_plan_does_not_fallback_to_default_topic_when_candidates_exhausted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "_load_json", lambda _path: {})
    monkeypatch.setattr(pipeline, "discover_hot_topic", lambda _style: ({}, {}, {"candidates": []}))
    monkeypatch.setattr(schedule_planner, "_load_performance_feedback", lambda _path: {"enabled": False})

    result = schedule_planner.build_rolling_plan(days=1, output_dir=tmp_path)

    assert result["ready_count"] == 0
    assert len(result["slots"]) == 3
    assert all(slot["topic"] == "" for slot in result["slots"])
    assert all("candidate_pool_exhausted" in slot["blockers"] for slot in result["slots"])


def test_schedule_plan_uses_lightweight_research_when_deep_research_missing(tmp_path, monkeypatch) -> None:
    topic_title = "김건희 특검 책임 기준"
    discovery = {
        "candidates": [
            {
                "title": topic_title,
                "publisher": "연합뉴스",
                "url": "https://news.example/1",
                "published_at": "2026-05-21T00:00:00+00:00",
                "query": "김건희 특검",
                "score": 180,
            }
        ]
    }
    script = pipeline.ScriptPackage(
        title=topic_title,
        caption="caption",
        hashtags=["정치"],
        post_title=topic_title,
        post_body="body",
        pinned_comment="comment",
        narration="narration",
        scenes=[pipeline.Scene(1, 8, "Hook", "본문", "visual", "화면")],
        target_duration_sec=70,
        sources=["hot_news_plan_01"],
        disclosure="해당 이미지는 생성된 이미지입니다.",
        variant_id="test",
    )
    monkeypatch.setattr(pipeline, "_load_json", lambda _path: {})
    monkeypatch.setattr(pipeline, "discover_hot_topic", lambda _style: ({}, {}, discovery))
    monkeypatch.setattr(schedule_planner, "_load_performance_feedback", lambda _path: {"enabled": False})
    monkeypatch.setattr(schedule_planner, "_recent_generated_titles", lambda: [])
    monkeypatch.setattr(schedule_planner, "_format_sequence_from_feedback", lambda _feedback: ["growth_short"])
    monkeypatch.setattr(schedule_planner, "_strict_topic_blockers", lambda **_kwargs: [])
    monkeypatch.setattr(pipeline, "generate_script", lambda *_args, **_kwargs: script)
    monkeypatch.setattr(pipeline, "apply_content_format", lambda generated, *_args, **_kwargs: generated)
    monkeypatch.setattr(
        pipeline,
        "select_publish_script",
        lambda _scripts, _topic, _sources, _plan: (
            script,
            pipeline.GateResult(True, 100),
            pipeline.ReadabilityResult(True, {}, 12, 60),
            pipeline.PublishQualityResult(True, "test", 92, {}, [], []),
        ),
    )
    monkeypatch.setattr(pipeline, "_publisher_is_trusted", lambda _publisher: True)

    result = schedule_planner.build_rolling_plan(days=1, output_dir=tmp_path)

    assert result["ready_count"] == 1
    assert result["slots"][0]["topic"] == topic_title
    assert result["slots"][0]["ready_for_generation"] is True
    assert result["slots"][0]["blockers"] == []
    assert result["slots"][0]["warnings"] == []
    assert result["slots"][0]["topic_discovery"]["deep_research_report"]["research_mode"] == "schedule_lightweight_research"


def test_hot_topic_template_keeps_late_scene_visual_roles_diverse() -> None:
    topic = pipeline.TopicCandidate(
        title="정청래 테러 모의 제보, 정치폭력은 누구에게 이익인가",
        angle="정당 대표 신변보호와 정치폭력 제보를 기준별로 정리",
        slot="curated",
        target_duration_sec=82,
        claims=[],
        source_ids=[],
    )
    script = pipeline.generate_script(
        topic,
        {"disclosure_policy": "해당 이미지는 생성된 이미지입니다"},
        {"mode": "rolling_schedule_plan"},
    )

    roles = [brief.role for brief in pipeline.build_visual_briefs(topic, script.scenes)]

    assert roles[4] == "responsibility"
    assert roles[6] == "verification"
    assert roles[7] == "criteria"
    assert roles.count("responsibility") == 1


def test_keyword_plan_and_format_route_use_performance_feedback() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    boosted_seed = str(pipeline.KEYWORD_SEED_BASKETS[1]["seeds"][1])
    suppressed_seed = str(pipeline.KEYWORD_SEED_BASKETS[1]["seeds"][0])
    modifier = str(pipeline.KEYWORD_SEED_BASKETS[1]["modifiers"][0])
    seed_items = [
        pipeline.HotTopicItem(
            title=f"{boosted_seed} {modifier} 국회 감사 쟁점",
            publisher="KBS",
            url="https://news.example/labor",
            published_at=now,
            query=boosted_seed,
            score=80,
        ),
        pipeline.HotTopicItem(
            title=f"{suppressed_seed} {modifier} 쟁점",
            publisher="KBS",
            url="https://news.example/other",
            published_at=now,
            query=suppressed_seed,
            score=85,
        ),
    ]
    feedback = {
        "enabled": True,
        "path": "test",
        "sample_count": 4,
        "term_scores": {boosted_seed: 25, suppressed_seed: -20},
        "format_scores": {"debate_followup": 12, "reward_deep": -2},
    }

    keyword_plan = pipeline.build_keyword_plan(seed_items, performance_feedback=feedback)
    topic = pipeline.TopicCandidate(
        title=f"{boosted_seed} {modifier} 국회 감사 쟁점",
        angle="최근 보도 기준 검증",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[
            pipeline.Claim("claim one", ["s1"], "low"),
            pipeline.Claim("claim two", ["s2"], "low"),
            pipeline.Claim("claim three", ["s3"], "low"),
        ],
        source_ids=["s1", "s2", "s3"],
    )
    format_plan = pipeline.route_content_format(topic, "auto", performance_feedback=feedback)

    assert keyword_plan.selected_keywords[0].keyword != suppressed_seed
    assert any("performance_feedback" in note for note in keyword_plan.scoring_notes)
    assert format_plan.format_id == "debate_followup"
    assert "performance feedback" in format_plan.selection_reason


def test_reward_deep_format_reframes_script_for_one_minute_explainer() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = {
        "s1": pipeline.Source("s1", "source one", "https://example.com/1", "note"),
        "s2": pipeline.Source("s2", "source two", "https://example.com/2", "note"),
    }
    topic = pipeline.TopicCandidate(
        title="김건희 의혹 후속 쟁점",
        angle="기록 기준 검증",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[
            pipeline.Claim("첫 번째 보도 기준입니다.", ["s1"], "medium"),
            pipeline.Claim("두 번째 보도 기준입니다.", ["s2"], "medium"),
        ],
        source_ids=["s1", "s2"],
    )

    script = pipeline.apply_content_format(
        pipeline.generate_script(topic, style),
        pipeline.FORMAT_SPECS["reward_deep"],
        topic=topic,
        sources=sources,
    )

    assert "reward_optimized" in script.variant_id
    assert 65 <= script.target_duration_sec <= 95
    assert 9 <= len(script.scenes) <= 12
    assert "1분" in script.scenes[0].body
    assert "1분 이상" in script.post_body
    assert "전말" in script.pinned_comment
    assert "근거" in script.pinned_comment
    assert "1 전말 2 근거 3 책임" in script.scenes[-1].on_screen_text


def test_auto_format_prefers_evidence_briefing_for_sourced_civic_issue() -> None:
    topic = pipeline.TopicCandidate(
        title="국회 공개 문서로 본 책임 기준",
        angle="공익 해설",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[
            pipeline.Claim("국회 회의록 기준 첫 번째 쟁점입니다.", ["s1"], "low"),
            pipeline.Claim("법원 공개 자료 기준 두 번째 쟁점입니다.", ["s2"], "low"),
        ],
        source_ids=["s1", "s2"],
    )

    plan = pipeline.route_content_format(topic, "auto")

    assert plan.format_id == "evidence_briefing_75"
    assert 60 <= plan.target_duration_min_sec <= plan.target_duration_max_sec <= 80


def test_monitoring_normalizes_studio_metric_text() -> None:
    payload = {
        "textSample": "Video views 1.2K Likes 88 Comments 9 Shares 7 Average watch time 18s Watched full video 31%",
        "metricNodes": ["New followers 3"],
    }

    metrics = monitoring.normalize_metrics(payload)

    assert metrics["views"] == 1200
    assert metrics["likes"] == 88
    assert metrics["comments"] == 9
    assert metrics["shares"] == 7
    assert metrics["average_watch_time_sec"] == 18
    assert metrics["completion_rate"] == 0.31
    assert metrics["followers_gained"] == 3


def test_monitoring_parses_studio_content_rows_for_account_references() -> None:
    text = """01:09
대한민국 역대 대통령을 다시 평가해봤습니다. 민주주의와 사람을 위한 정치 #김대중 #노무현
고정됨
2025년 4월 26일 오후 7:02
모두
116K
2,057
330
01:04
노동 이슈, 왜 커졌나? 기록으로 다시 보기 노동안전보건 정책 과제
5월 14일 오후 12:07
모두
0
0
0"""

    rows = monitoring.parse_studio_content_rows(text)
    feedback = monitoring.build_account_reference_feedback(rows)

    assert len(rows) == 2
    assert rows[0].pinned
    assert rows[0].views == 116000
    assert feedback["sample_count"] == 1
    assert "민주주의" in feedback["positive_terms"]


def test_monitoring_generates_response_actions_for_low_retention(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "run_id": "leftaino_20260512_181016",
        "created_at": "2026-05-12T09:00:00+00:00",
        "synced_duration_sec": 45,
    }
    manifest_path.write_text("{}", encoding="utf-8")
    snapshot = monitoring.MetricSnapshot(
        run_id="leftaino_20260512_181016",
        captured_at="2026-05-12T10:00:00+00:00",
        metrics={
            "views": 120,
            "likes": 4,
            "comments": 0,
            "shares": 0,
            "average_watch_time_sec": 8,
            "completion_rate": 0.12,
        },
        source_path=str(tmp_path / "studio_metrics.jsonl"),
    )

    analysis = monitoring.analyze_run("leftaino_20260512_181016", manifest_path, manifest, snapshot)

    assert analysis.status == "respond"
    assert "views_lt_threshold" in analysis.diagnoses
    assert "average_watch_ratio_lt_threshold" in analysis.diagnoses
    assert any("첫 3초" in action for action in analysis.actions)


def test_monitoring_writes_performance_feedback_artifact(tmp_path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    manifest = {
        "run_id": "leftaino_20260512_181016",
        "created_at": "2026-05-12T09:00:00+00:00",
        "synced_duration_sec": 70,
        "format_plan": {"format_id": "reward_deep"},
        "topic": {"title": "민주주의 책임 검증", "angle": "근거 기준"},
        "script": {"post_title": "민주주의 책임", "hashtags": ["민주주의", "책임"]},
        "visual_plan": {
            "scenes": [
                {"visual_role": "evidence", "issue_type": "civic_fact_check"},
            ]
        },
        "visual_motion": {"all_static_hold": True},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    metrics_path = tmp_path / "studio_metrics_test.jsonl"
    metrics_path.write_text(
        json.dumps(
            {
                "run_id": "leftaino_20260512_181016",
                "captured_at": "2026-05-12T12:00:00+00:00",
                "metrics": {
                    "views": 5000,
                    "likes": 500,
                    "comments": 60,
                    "shares": 40,
                    "saves": 20,
                    "average_watch_time_sec": 45,
                    "completion_rate": 0.42,
                    "followers_gained": 8,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    summary = monitoring.analyze_performance(output_dirs=[tmp_path], output_dir=report_dir)
    feedback_path = report_dir / "performance_feedback.json"
    feedback = json.loads(feedback_path.read_text(encoding="utf-8"))

    assert summary["performance_feedback_latest_path"] == str(feedback_path)
    assert feedback["version"] == "performance_feedback_v1"
    assert feedback["sample_count"] == 1
    assert any(row["keyword"] == "민주주의" for row in feedback["feedback"]["keyword_adjustments"])
    assert any(row["format"] == "reward_deep" for row in feedback["feedback"]["format_adjustments"])
    assert any(row["pattern"] == "role:evidence" for row in feedback["feedback"]["visual_adjustments"])


def test_monitoring_reuses_recent_duplicate_performance_report(tmp_path) -> None:
    run_dir = tmp_path / "leftaino_20260512_181016"
    run_dir.mkdir()
    manifest = {
        "run_id": "leftaino_20260512_181016",
        "created_at": "2026-05-12T09:00:00+00:00",
        "synced_duration_sec": 70,
        "script": {"post_title": "정치 이슈 검수 제목", "hashtags": ["정치"]},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "studio_metrics_test.jsonl").write_text(
        json.dumps(
            {
                "run_id": "leftaino_20260512_181016",
                "captured_at": "2026-05-12T12:00:00+00:00",
                "metrics": {"views": 5000, "likes": 500, "comments": 60},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    first = monitoring.analyze_performance(output_dirs=[tmp_path], output_dir=report_dir)
    second = monitoring.analyze_performance(output_dirs=[tmp_path], output_dir=report_dir)

    assert second["path"] == first["path"]
    assert second["reused_existing_report"] is True
    assert len(list(report_dir.glob("performance_report_*.json"))) == 1


def test_monitoring_reuses_recent_duplicate_studio_snapshot_report(tmp_path) -> None:
    snapshot_path = tmp_path / "studio_snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "combined": """01:09
대한민국 역대 대통령을 다시 평가해봤습니다. 민주주의와 사람을 위한 정치 #김대중 #노무현
고정됨
2025년 4월 26일 오후 7:02
모두
116K
2,057
330"""
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    first = monitoring.analyze_studio_snapshot(snapshot_path, output_dir=report_dir)
    second = monitoring.analyze_studio_snapshot(snapshot_path, output_dir=report_dir)

    assert second["path"] == first["path"]
    assert second["reused_existing_report"] is True
    assert len(list(report_dir.glob("performance_report_*.json"))) == 1


def test_hot_topic_scoring_blocks_low_growth_admin_topics() -> None:
    published = dt.datetime.now(dt.timezone.utc)
    admin_score = pipeline._score_hot_topic("평택시 미래기술학교 반도체 공정 장비 과정 교육생 모집", "연합뉴스", published)
    conflict_score = pipeline._score_hot_topic("검찰개혁 특검 의혹 국회 공방", "연합뉴스", published)

    assert pipeline.is_low_growth_topic("평택시 미래기술학교 반도체 공정 장비 과정 교육생 모집")
    assert not pipeline.is_low_growth_topic("검찰개혁 특검 의혹 국회 공방")
    assert conflict_score > admin_score


def test_korean_tts_preprocess_expands_common_shortform() -> None:
    result = _preprocess_korean_tts(
        "올바른 AiNo는 2026.05.11 오전 7:30에 18~49세에게 12% 변화를 설명합니다. @leftaino"
    )
    spoken = result.text.replace("\n", " ")

    assert "올바른 아이노" in spoken
    assert "이천이십육년 오월 십일일" in spoken
    assert "일곱 시 삼십 분" in spoken
    assert "십팔 세에서 사십구 세" in spoken
    assert "십이 퍼센트" in spoken
    assert "레프트 아이노 계정" in spoken
    assert result.metrics["digit_count"] == 0


def test_korean_tts_preprocess_reads_counter_units() -> None:
    result = _preprocess_korean_tts("9장 카드, 3개 플랫폼, 10초 분량, 1위 후보")

    assert "아홉 장" in result.text
    assert "세 개" in result.text
    assert "십 초" in result.text
    assert "첫 번째 후보" in result.text
    assert result.metrics["digit_count"] == 0


def test_scene_card_duration_uses_audio_length_with_minimum_hold() -> None:
    assert _scene_card_duration(2.1, 9) == 7
    assert _scene_card_duration(7.2, 8) == 8
    assert _scene_card_duration(10.6, 8) == 12


def test_publish_quality_selects_highest_ready_variant() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = pipeline.load_sources()
    topic = pipeline.collect_topic(style)
    variants = pipeline.generate_script_variants(topic, style)

    script, gate, readability, quality = pipeline.select_publish_script(variants, topic, sources)

    assert script.variant_id == "strong_hook"
    assert gate.passed
    assert readability.passed
    assert quality.passed
    assert quality.publish_ready_score >= 85
    assert len(quality.variant_scores) >= 3
    assert quality.scores["hook_strength"] >= 80
    assert quality.scores["safe_provocation"] >= 70
    assert quality.scores["search_value"] >= 80
    assert quality.scores["comment_trigger"] >= 80


def test_trim_letterbox_removes_blank_generated_bars() -> None:
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 25, 100, 75), fill=(35, 50, 60))

    trimmed = _trim_letterbox(image)

    assert trimmed.height < image.height
    assert trimmed.height >= 45


def test_auto_format_routes_sourced_topic_to_evidence_briefing_candidate() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    topic = pipeline.collect_topic(style)

    plan = pipeline.route_content_format(topic)

    assert plan.format_id == "evidence_briefing_75"
    assert plan.reward_eligible
    assert plan.target_duration_min_sec >= 60


def test_growth_short_format_does_not_require_rewards_duration() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = pipeline.load_sources()
    topic = pipeline.collect_topic(style)
    plan = pipeline.FORMAT_SPECS["growth_short"]
    script = pipeline.apply_content_format(pipeline.generate_script_variants(topic, style)[0], plan)

    gate = pipeline.check_policy(topic, script, sources, plan)
    readability = pipeline.check_readability(script, plan)

    assert plan.target_duration_min_sec <= script.target_duration_sec <= plan.target_duration_max_sec
    assert plan.scene_count_min <= len(script.scenes) <= plan.scene_count_max
    assert max(len(scene.body) for scene in script.scenes) <= pipeline.FORMAT_BODY_TEXT_MAX_CHARS["growth_short"]
    assert gate.checks["duration_over_60s_for_rewards"]
    assert gate.passed
    assert readability.passed


def test_reward_deep_format_keeps_one_minute_plus_shape() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = pipeline.load_sources()
    topic = pipeline.collect_topic(style)
    plan = pipeline.FORMAT_SPECS["reward_deep"]
    variants = [pipeline.apply_content_format(script, plan) for script in pipeline.generate_script_variants(topic, style)]

    script, gate, readability, quality = pipeline.select_publish_script(variants, topic, sources, plan)

    assert plan.target_duration_min_sec <= script.target_duration_sec <= plan.target_duration_max_sec
    assert plan.scene_count_min <= len(script.scenes) <= plan.scene_count_max
    assert gate.checks["duration_over_60s_for_rewards"]
    assert gate.passed
    assert readability.passed
    assert quality.passed


def test_visual_beats_meet_format_density_and_scene_durations() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    topic = pipeline.collect_topic(style)
    plan = pipeline.FORMAT_SPECS["reward_deep"]
    script = pipeline.apply_content_format(pipeline.generate_script_variants(topic, style)[0], plan)

    beats = pipeline.build_visual_beats(script.scenes, plan)
    summary = pipeline._visual_motion_summary(beats)

    assert len(beats) >= plan.min_visual_beats
    assert summary["camera_motion_count"] > 0
    assert max(abs(beat.pan_x) for beat in beats) <= 40
    assert min(beat.zoom_start for beat in beats) >= 1.0
    assert max(beat.zoom_end for beat in beats) <= 1.08
    for scene in script.scenes:
        duration = sum(beat.duration_sec for beat in beats if beat.scene_id == scene.scene_id)
        assert abs(duration - scene.duration_sec) <= 0.02


def test_render_beat_frame_keeps_static_still_pixels_unchanged() -> None:
    image = Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#101820")
    beat = pipeline.VisualBeat(
        scene_id=1,
        beat_id=1,
        start_sec=0,
        duration_sec=8,
        zoom_start=1.0,
        zoom_end=1.0,
        pan_x=0,
        pan_y=0,
        overlay="hold",
    )

    first = pipeline._render_beat_frame(image, beat, 0.0)
    last = pipeline._render_beat_frame(image, beat, 1.0)

    assert first.tobytes() == last.tobytes()


def test_mobile_typography_gate_uses_readable_scaled_font_sizes() -> None:
    assert pipeline._scaled_mobile_px(pipeline.HEADLINE_FONT_MIN) >= 19
    assert pipeline._scaled_mobile_px(pipeline.BODY_FONT_MIN) >= 14
    assert pipeline.TEXT_SAFE_LEFT >= 104
    assert pipeline.CANVAS_WIDTH - pipeline.TEXT_SAFE_RIGHT >= 104
    assert pipeline.TEXT_SAFE_RIGHT <= pipeline.TIKTOK_RIGHT_RAIL_LEFT
    assert pipeline.CRITICAL_TEXT_BOTTOM <= pipeline.TIKTOK_BOTTOM_UI_TOP

    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    topic = pipeline.collect_topic(style)
    plan = pipeline.FORMAT_SPECS["reward_deep"]
    script = pipeline.apply_content_format(pipeline.generate_script_variants(topic, style)[0], plan)
    readability = pipeline.check_readability(script, plan)

    assert readability.checks["body_text_under_mobile_limit"]
    assert readability.checks["headline_mobile_font_at_least_19px"]
    assert readability.checks["body_mobile_font_at_least_14px"]
    assert readability.checks["critical_text_horizontal_margin_104px"]


def test_scene_copy_normalizer_compresses_long_text_and_expands_short_text() -> None:
    long_scene = pipeline.Scene(
        1,
        8,
        "Long",
        "첫 번째 문장이 너무 길어서 모바일 화면에서 네 줄 이상으로 밀릴 수 있습니다. 두 번째 문장도 이어지면 본문 박스를 넘깁니다. 세 번째 문장은 버려야 합니다.",
        "empty classroom",
        "이 제목은 모바일 화면에서 너무 길어서 반드시 압축되어야 하는 문장입니다",
    )
    short_scene = pipeline.Scene(2, 8, "Short", "확인.", "empty classroom", "왜")

    compact = pipeline._normalize_scene_copy(long_scene, is_first=True)
    compact_growth = pipeline._normalize_scene_copy(
        long_scene,
        plan=pipeline.FORMAT_SPECS["growth_short"],
        is_first=True,
    )
    expanded = pipeline._normalize_scene_copy(short_scene, is_last=True)

    assert len(compact.on_screen_text) <= 34
    assert len(compact.body) <= pipeline.BODY_TEXT_MAX_CHARS_MOBILE
    assert len(compact_growth.body) <= pipeline.FORMAT_BODY_TEXT_MAX_CHARS["growth_short"]
    assert len(expanded.on_screen_text) >= pipeline.HEADLINE_MIN_CHARS
    assert len(expanded.body) >= pipeline.BODY_TEXT_MIN_CHARS_MOBILE
    assert "댓글" in expanded.body


def test_mobile_overlay_preview_artifact_checks_tiktok_ui_safe_zones(tmp_path) -> None:
    scene = pipeline.Scene(
        1,
        8,
        "Preview",
        "본문은 모바일 화면에서도 충분히 읽혀야 합니다. 오른쪽 버튼과 하단 캡션을 피합니다.",
        "empty classroom",
        "모바일 가독성 확인",
    )
    image = Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#101820")

    storyboard, checks_path, checks = pipeline._write_mobile_previews([image], [scene], tmp_path)

    assert storyboard.exists()
    assert checks_path.exists()
    assert checks[0].passed
    with Image.open(tmp_path / "mobile_previews" / "scene_01_tiktok_mobile.png") as preview:
        assert preview.size == (pipeline.MOBILE_PREVIEW_WIDTH, pipeline.MOBILE_PREVIEW_HEIGHT)


def test_hot_topic_score_prefers_recent_civic_sources() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc)

    recent_score = pipeline._score_hot_topic(
        "국회 교육 정책 검증 논란",
        "연합뉴스",
        now - pipeline.dt.timedelta(hours=2),
    )
    stale_score = pipeline._score_hot_topic(
        "[사설] 연예계 소식 정리",
        "개인블로그",
        now - pipeline.dt.timedelta(hours=60),
    )

    assert recent_score > stale_score + 30


def test_hot_topic_score_penalizes_unknown_sources() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc)
    trusted_score = pipeline._score_hot_topic(
        "National Assembly education policy check controversy",
        "MBC",
        now - pipeline.dt.timedelta(hours=1),
    )
    unknown_score = pipeline._score_hot_topic(
        "National Assembly education policy check controversy",
        "Unknown Local Outlet",
        now - pipeline.dt.timedelta(hours=1),
    )

    assert trusted_score > unknown_score + 25


def test_hot_topic_cluster_scoring_tracks_core_public_issue_keywords() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc)
    clusters = pipeline._matched_trend_clusters("이재명 더불어민주당 검찰개혁 입법 논란")
    cluster_ids = {row["cluster_id"] for row in clusters}
    clustered_score = pipeline._score_hot_topic(
        "이재명 더불어민주당 검찰개혁 입법 논란",
        "한겨레",
        now - pipeline.dt.timedelta(hours=2),
    )
    generic_score = pipeline._score_hot_topic(
        "국회 정책 논란",
        "한겨레",
        now - pipeline.dt.timedelta(hours=2),
    )

    assert "democratic_governance" in cluster_ids
    assert clustered_score > generic_score


def test_keyword_plan_expands_queries_from_recent_news_signals() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    seed_items = [
        pipeline.HotTopicItem(
            title="윤석열 관저 이전 의혹 감사원 압수수색 본격 수사",
            publisher="KBS",
            url="https://news.example/1",
            published_at=now,
            query="특검",
            score=100,
        ),
        pipeline.HotTopicItem(
            title="더불어민주당 검찰개혁 입법 논란 국회 공방",
            publisher="한겨레",
            url="https://news.example/2",
            published_at=now,
            query="국회",
            score=95,
        ),
    ]

    plan = pipeline.build_keyword_plan(seed_items)
    selected = {candidate.keyword for candidate in plan.selected_keywords}
    expanded_queries = set(plan.expanded_queries)

    assert {"관저 이전", "감사원 압수수색"} & selected
    assert plan.selected_keywords[0].keyword not in {"의혹", "특검", "수사", "논란"}
    assert any(query.startswith(("관저 이전", "감사원 압수수색")) for query in expanded_queries)
    assert any(candidate.support_count >= 1 for candidate in plan.selected_keywords)
    assert plan.scoring_notes


def test_signal_snapshot_keeps_raw_items_and_detected_terms() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    seed_items = [
        pipeline.HotTopicItem(
            title="윤석열 관저 이전 의혹 감사원 압수수색",
            publisher="KBS",
            url="https://news.example/1",
            published_at=now,
            query="특검",
            score=100,
        )
    ]

    snapshot = pipeline.build_signal_snapshot(seed_items)

    assert snapshot.version == "signal_collection_v1"
    assert snapshot.item_count == 1
    assert snapshot.raw_items[0]["title"] == seed_items[0].title
    assert "윤석열" in snapshot.detected_terms["seed_terms"]
    assert "압수수색" in snapshot.detected_terms["high_intent_terms"]
    assert snapshot.base_queries == pipeline.KEYWORD_BASE_QUERIES


def test_topic_and_editorial_plans_explain_selection_and_angle() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    items = [
        pipeline.HotTopicItem(
            title="종합특검 윤석열 관저 이전 의혹 감사원 압수수색",
            publisher="미디어오늘",
            url="https://news.example/1",
            published_at=now,
            query="감사원 압수수색",
            score=110,
        ),
        pipeline.HotTopicItem(
            title="종합특검 감사원 압수수색 관저 이전 위법 감사 의혹",
            publisher="한겨레",
            url="https://news.example/2",
            published_at=now,
            query="관저 이전",
            score=100,
        ),
    ]
    keyword_plan = pipeline.build_keyword_plan(items)
    topic_pool = pipeline.build_topic_pool(items, keyword_plan)
    topic_plan = pipeline.build_topic_plan(items[0], [items[1]], topic_pool, keyword_plan)
    sources = {
        "hot_news_01": pipeline.Source("hot_news_01", "미디어오늘: 종합특검", "https://news.example/1", "test"),
        "hot_news_02": pipeline.Source("hot_news_02", "한겨레: 종합특검", "https://news.example/2", "test"),
    }
    topic = pipeline.TopicCandidate(
        title=items[0].title,
        angle="최근 48시간 보도량 기준",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[_configured_hot_claim("미디어오늘", items[0].title, "hot_news_01")],
        source_ids=["hot_news_01", "hot_news_02"],
    )
    editorial_plan = pipeline.build_editorial_plan(
        topic,
        sources,
        pipeline.FORMAT_SPECS["reward_deep"],
        {"topic_plan": pipeline.asdict(topic_plan)},
    )

    assert topic_pool.candidates
    assert topic_plan.selected_topic_id == "topic_001"
    assert topic_plan.support_count == 2
    assert "감사원 압수수색" in topic_plan.selection_reason or "관저 이전" in topic_plan.selection_reason
    assert editorial_plan.angle_id == "timeline_explainer"
    assert "전말" in editorial_plan.must_include
    assert "범죄 확정 표현" in editorial_plan.must_avoid


def test_deep_research_report_prefers_storyworthy_reference_fit() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    snapshot = pipeline.SignalSnapshot(
        version="signal_collection_v1",
        collected_at=now,
        sources=["google_news_rss"],
        base_queries=["정치"],
        item_count=2,
        raw_items=[],
        detected_terms={},
        risk_terms=[],
    )
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["정치"],
        expanded_queries=["김건희 특검", "국회 정책"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="김건희 특검",
                basket_id="entity_issue",
                intent="search",
                score=90,
                support_count=2,
                matched_seeds=["김건희"],
                matched_modifiers=["특검"],
                matched_high_intent_terms=["특검"],
                risk_terms=[],
                source_queries=["김건희 특검"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )
    topic_pool = pipeline.TopicPool(
        version="topic_pool_v1",
        candidates=[
            pipeline.TopicPoolCandidate(
                topic_id="topic_001",
                title="국회 정책 설명회 개최, 여야 참석",
                query="국회 정책",
                publisher="KBS",
                url="https://news.example/generic",
                published_at=now,
                keywords=[],
                support_count=3,
                risk="low",
                format_hint="growth_short",
                score=96,
                score_components={
                    "recency_heat": 96,
                    "source_support": 88,
                    "search_value": 50,
                    "policy_safety": 92,
                },
            ),
            pipeline.TopicPoolCandidate(
                topic_id="topic_002",
                title="김건희 공천개입 의혹 특검 압수수색, 무혐의 논란 재점화",
                query="김건희 특검",
                publisher="MBC",
                url="https://news.example/story",
                published_at=now,
                keywords=["김건희 특검"],
                support_count=2,
                risk="medium",
                format_hint="reward_deep",
                score=88,
                score_components={
                    "recency_heat": 88,
                    "source_support": 74,
                    "search_value": 86,
                    "policy_safety": 74,
                },
            ),
        ],
    )
    topic_plan = pipeline.TopicPlan(
        version="topic_plan_v1",
        selected_topic_id="topic_001",
        selected_title="국회 정책 설명회 개최, 여야 참석",
        selection_reason="raw heat winner",
        scores={"recency": 96},
        support_count=3,
        keywords=[],
        blocked_candidates=[],
    )

    report = pipeline.build_deep_research_report(snapshot, keyword_plan, topic_pool, topic_plan)

    assert report.version == "deep_research_v1"
    assert report.selected_topic_id == "topic_002"
    assert report.selected_archetype_id == "receipts_then_missing_answer"
    assert report.topic_candidates[0].score_components["reference_fit"] >= 80
    assert report.topic_candidates[0].score_components["cinematic_sceneability"] >= 70
    assert any(row["label"] == "Creator Rewards" for row in report.official_platform_constraints)
    assert report.visual_mandates


def test_keywords_for_topic_title_does_not_leak_unrelated_global_keyword() -> None:
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["정치"],
        expanded_queries=["윤석열 특검"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="윤석열 특검",
                basket_id="entity_issue",
                intent="search",
                score=90,
                support_count=2,
                matched_seeds=["윤석열"],
                matched_modifiers=["특검"],
                matched_high_intent_terms=["특검"],
                risk_terms=[],
                source_queries=["윤석열 특검"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )

    keywords = pipeline._keywords_for_topic_title("이재명 노동권과 기업 경영권 발언 논쟁", keyword_plan)

    assert "윤석열 특검" not in keywords


def test_deep_research_prefers_progressive_memory_accountability_topic() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    snapshot = pipeline.SignalSnapshot(
        version="signal_collection_v1",
        collected_at=now,
        sources=["google_news_rss"],
        base_queries=["5·18"],
        item_count=2,
        raw_items=[],
        detected_terms={},
        risk_terms=[],
    )
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["5·18"],
        expanded_queries=["5·18 민주주의 계엄 내란 책임"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="5·18 민주주의 계엄 내란 책임",
                basket_id="democratic_memory",
                intent="search",
                score=96,
                support_count=3,
                matched_seeds=["5·18", "광주"],
                matched_modifiers=["책임"],
                matched_high_intent_terms=["내란"],
                risk_terms=[],
                source_queries=["5·18"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )
    topic_pool = pipeline.TopicPool(
        version="topic_pool_v1",
        candidates=[
            pipeline.TopicPoolCandidate(
                topic_id="topic_001",
                title="국회 정책 설명회 개최, 여야 참석",
                query="국회 정책",
                publisher="KBS",
                url="https://news.example/generic",
                published_at=now,
                keywords=[],
                support_count=3,
                risk="low",
                format_hint="growth_short",
                score=96,
                score_components={
                    "recency_heat": 96,
                    "source_support": 88,
                    "search_value": 50,
                    "policy_safety": 92,
                },
            ),
            pipeline.TopicPoolCandidate(
                topic_id="topic_002",
                title="5월 18일 5·18 광주 기념식서 국민의힘 민주주의 발언, 계엄 내란 책임 공방",
                query="5·18 민주주의 계엄 내란 책임",
                publisher="MBC",
                url="https://news.example/memory",
                published_at=now,
                keywords=["5·18 민주주의 계엄 내란 책임"],
                support_count=3,
                risk="medium",
                format_hint="reward_deep",
                score=88,
                score_components={
                    "recency_heat": 88,
                    "source_support": 84,
                    "search_value": 92,
                    "policy_safety": 74,
                },
            ),
        ],
    )
    topic_plan = pipeline.TopicPlan(
        version="topic_plan_v1",
        selected_topic_id="topic_001",
        selected_title="국회 정책 설명회 개최, 여야 참석",
        selection_reason="raw heat winner",
        scores={"recency": 96},
        support_count=3,
        keywords=[],
        blocked_candidates=[],
    )

    report = pipeline.build_deep_research_report(snapshot, keyword_plan, topic_pool, topic_plan)

    assert report.selected_topic_id == "topic_002"
    assert report.selected_archetype_id == "democratic_memory_accountability"
    assert report.topic_candidates[0].score_components["progressive_reaction"] >= 90
    assert report.topic_candidates[0].score_components["today_relevance"] >= 90


def test_deep_research_demotes_friendly_memory_summary_below_accountability_frame() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    snapshot = pipeline.SignalSnapshot(
        version="signal_collection_v1",
        collected_at=now,
        sources=["google_news_rss"],
        base_queries=["5·18"],
        item_count=2,
        raw_items=[],
        detected_terms={},
        risk_terms=[],
    )
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["5·18"],
        expanded_queries=["5·18 국민의힘 계엄 내란 책임"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="5·18 국민의힘 계엄 내란 책임",
                basket_id="democratic_memory",
                intent="search",
                score=96,
                support_count=3,
                matched_seeds=["5·18", "국민의힘"],
                matched_modifiers=["책임"],
                matched_high_intent_terms=["내란"],
                risk_terms=[],
                source_queries=["5·18"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )
    topic_pool = pipeline.TopicPool(
        version="topic_pool_v1",
        candidates=[
            pipeline.TopicPoolCandidate(
                topic_id="topic_001",
                title="李 대통령 5월 18일 5·18 광주 정신 국가가 끝까지 책임 발언",
                query="5·18 국민의힘 계엄 내란 책임",
                publisher="KBS",
                url="https://news.example/friendly",
                published_at=now,
                keywords=[],
                support_count=3,
                risk="low",
                format_hint="reward_deep",
                score=96,
                score_components={
                    "recency_heat": 96,
                    "source_support": 88,
                    "search_value": 70,
                    "policy_safety": 92,
                },
            ),
            pipeline.TopicPoolCandidate(
                topic_id="topic_002",
                title="5월 18일 5·18 광주 앞 국민의힘 민주주의 발언, 계엄 내란 책임 공방",
                query="5·18 국민의힘 계엄 내란 책임",
                publisher="MBC",
                url="https://news.example/accountability",
                published_at=now,
                keywords=["5·18 국민의힘 계엄 내란 책임"],
                support_count=3,
                risk="medium",
                format_hint="reward_deep",
                score=90,
                score_components={
                    "recency_heat": 90,
                    "source_support": 84,
                    "search_value": 94,
                    "policy_safety": 74,
                },
            ),
        ],
    )
    topic_plan = pipeline.TopicPlan(
        version="topic_plan_v1",
        selected_topic_id="topic_001",
        selected_title=topic_pool.candidates[0].title,
        selection_reason="raw heat winner",
        scores={"recency": 96},
        support_count=3,
        keywords=[],
        blocked_candidates=[],
    )

    report = pipeline.build_deep_research_report(snapshot, keyword_plan, topic_pool, topic_plan)

    assert report.selected_topic_id == "topic_002"
    assert report.topic_candidates[0].score_components["progressive_reaction"] > report.topic_candidates[1].score_components["progressive_reaction"]


def test_deep_research_question_uses_title_keyword_not_unrelated_global_keyword() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["정치"],
        expanded_queries=["윤석열 특검"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="윤석열 특검",
                basket_id="entity_issue",
                intent="search",
                score=90,
                support_count=2,
                matched_seeds=["윤석열"],
                matched_modifiers=["특검"],
                matched_high_intent_terms=["특검"],
                risk_terms=[],
                source_queries=["윤석열 특검"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )
    topic_title = "이재명 노동권과 기업 경영권 발언 논쟁"
    topic_pool = pipeline.TopicPool(
        version="topic_pool_v1",
        candidates=[
            pipeline.TopicPoolCandidate(
                topic_id="topic_001",
                title=topic_title,
                query="이재명 노동권",
                publisher="KBS",
                url="https://news.example/labor",
                published_at=now,
                keywords=pipeline._keywords_for_topic_title(topic_title, keyword_plan),
                support_count=2,
                risk="low",
                format_hint="growth_short",
                score=82,
                score_components={
                    "recency_heat": 82,
                    "source_support": 74,
                    "search_value": 45,
                    "policy_safety": 92,
                },
            )
        ],
    )
    snapshot = pipeline.SignalSnapshot(
        version="signal_collection_v1",
        collected_at=now,
        sources=["google_news_rss"],
        base_queries=["정치"],
        item_count=1,
        raw_items=[],
        detected_terms={},
        risk_terms=[],
    )
    topic_plan = pipeline.TopicPlan(
        version="topic_plan_v1",
        selected_topic_id="topic_001",
        selected_title=topic_title,
        selection_reason="test",
        scores={"recency": 82},
        support_count=2,
        keywords=[],
        blocked_candidates=[],
    )

    report = pipeline.build_deep_research_report(snapshot, keyword_plan, topic_pool, topic_plan)

    assert "윤석열 특검" not in report.selected_research_question


def test_hot_topic_script_uses_deep_research_brief_values() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    keyword_plan = pipeline.KeywordPlan(
        version="keyword_research_v1",
        base_queries=["정치"],
        expanded_queries=["김건희 특검"],
        selected_keywords=[
            pipeline.KeywordCandidate(
                keyword="김건희 특검",
                basket_id="entity_issue",
                intent="search",
                score=90,
                support_count=2,
                matched_seeds=["김건희"],
                matched_modifiers=["특검"],
                matched_high_intent_terms=["특검"],
                risk_terms=[],
                source_queries=["김건희 특검"],
                rationale=["test"],
            )
        ],
        rejected_keywords=[],
        scoring_notes=[],
    )
    topic_pool = pipeline.TopicPool(
        version="topic_pool_v1",
        candidates=[
            pipeline.TopicPoolCandidate(
                topic_id="topic_001",
                title="김건희 공천개입 의혹 특검 압수수색, 무혐의 논란 재점화",
                query="김건희 특검",
                publisher="MBC",
                url="https://news.example/story",
                published_at=now,
                keywords=["김건희 특검"],
                support_count=2,
                risk="medium",
                format_hint="reward_deep",
                score=88,
                score_components={
                    "recency_heat": 88,
                    "source_support": 74,
                    "search_value": 86,
                    "policy_safety": 74,
                },
            )
        ],
    )
    snapshot = pipeline.SignalSnapshot(
        version="signal_collection_v1",
        collected_at=now,
        sources=["google_news_rss"],
        base_queries=["정치"],
        item_count=1,
        raw_items=[],
        detected_terms={},
        risk_terms=[],
    )
    topic_plan = pipeline.TopicPlan(
        version="topic_plan_v1",
        selected_topic_id="topic_001",
        selected_title=topic_pool.candidates[0].title,
        selection_reason="test",
        scores={"recency": 88},
        support_count=2,
        keywords=["김건희 특검"],
        blocked_candidates=[],
    )
    report = pipeline.build_deep_research_report(snapshot, keyword_plan, topic_pool, topic_plan)
    topic = pipeline.TopicCandidate(
        title=topic_pool.candidates[0].title,
        angle=report.selected_archetype_label,
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )

    script = pipeline.generate_script(
        topic,
        {"disclosure_policy": "해당 이미지는 생성된 이미지입니다."},
        topic_discovery={"deep_research_report": pipeline.asdict(report)},
    )

    assert report.selected_research_question in script.narration
    assert report.topic_candidates[0].comment_trigger in script.narration
    assert report.topic_candidates[0].counterpoint_focus in script.narration


def test_selected_script_and_visual_plan_preserve_lineage() -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열 관저 이전 의혹 감사원 압수수색",
        angle="최근 48시간 공개 보도 기준으로 검증",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[_configured_hot_claim("KBS", "윤석열 관저 이전 의혹 감사원 압수수색", "hot_news_01")],
        source_ids=["hot_news_01"],
    )
    sources = {
        "hot_news_01": pipeline.Source(
            "hot_news_01",
            "KBS: 윤석열 관저 이전 의혹 감사원 압수수색",
            "https://news.example/1",
            "test dynamic source",
        )
    }
    scenes = [
        pipeline.Scene(1, 8, "Hook", "특검 수사 전말을 1분 안에 봅니다.", "visual", "특검, 48시간 전말"),
        pipeline.Scene(2, 8, "CTA", "댓글로 기준을 남겨주세요.", "visual", "1 전말 2 근거 3 책임"),
    ]
    script = pipeline.ScriptPackage(
        title="특검, 48시간 전말",
        caption="caption",
        hashtags=["정치"],
        post_title="post",
        post_body="body",
        pinned_comment="comment",
        narration="narration",
        scenes=scenes,
        target_duration_sec=70,
        sources=["hot_news_01"],
        disclosure="해당 이미지는 생성된 이미지입니다.",
        variant_id="test_variant",
    )
    gate = pipeline.GateResult(True, 98)
    readability = pipeline.ReadabilityResult(True, {}, 12, 40)
    quality = pipeline.PublishQualityResult(
        True,
        "test_variant",
        91,
        {"hook_strength": 90, "search_value": 88},
    )
    selected = pipeline.build_selected_script_plan(
        script,
        gate,
        readability,
        quality,
        pipeline.FORMAT_SPECS["reward_deep"],
    )
    content_plan = pipeline.build_content_plan(topic, script, sources, pipeline.FORMAT_SPECS["reward_deep"])
    brief = pipeline.build_visual_briefs(topic, scenes)[0]
    visual_assets = [
        pipeline.VisualAsset(
            scene_id=1,
            provider="codex_cli",
            status="generated",
            path="scene_01.png",
            prompt="cinematic prompt",
            visual_brief=pipeline.asdict(brief),
        )
    ]
    visual_plan = pipeline.build_visual_plan(content_plan, visual_assets)

    assert selected.variant_id == "test_variant"
    assert selected.script["title"] == script.title
    assert selected.publish_ready_score == 91
    assert visual_plan.scene_count == 2
    assert visual_plan.scenes[0].prompt_basis == "content_plan.image_need"
    assert visual_plan.scenes[0].asset_provider == "codex_cli"
    assert visual_plan.scenes[0].prompt_lineage["generated_prompt"] == "cinematic prompt"


def test_tts_plan_preserves_scene_text_and_publish_provider_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ELEVENLABS_ENABLE_LOGGING", raising=False)
    scene_text_path = tmp_path / "scene_01.txt"
    scene_lint_path = tmp_path / "scene_01_lint.json"
    combined_lint_path = tmp_path / "narration_tts_lint.json"
    scene_text_path.write_text("첫 장면은 숫자 하나를 자연스럽게 읽습니다.", encoding="utf-8")
    scene_lint_path.write_text(
        json.dumps({"warnings": ["long_sentence_count"], "replacements": ["1->하나"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    combined_lint_path.write_text(
        json.dumps({"warnings": ["scene_01:long_sentence_count"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    script = pipeline.ScriptPackage(
        title="테스트",
        caption="caption",
        hashtags=["테스트"],
        post_title="post",
        post_body="body",
        pinned_comment="comment",
        narration="narration",
        scenes=[pipeline.Scene(1, 8, "Hook", "원문 1", "visual", "화면")],
        target_duration_sec=8,
        sources=[],
        disclosure="생성 이미지입니다.",
        variant_id="test",
    )
    audio = pipeline.AudioAsset(
        provider="scene_audio_preview",
        status="fallback",
        path=str(tmp_path / "narration.wav"),
        lint_path=str(combined_lint_path),
        scene_timings=[
            {
                "scene_id": 1,
                "card_duration_sec": 8,
                "audio_duration_sec": 6.2,
                "tts_text_path": str(scene_text_path),
                "lint_path": str(scene_lint_path),
                "provider": "windows_system_speech",
                "status": "fallback",
            }
        ],
    )

    plan = pipeline.build_tts_plan(script, audio)

    assert plan.version == "tts_plan_v1"
    assert plan.provider == "elevenlabs"
    assert plan.actual_provider == "scene_audio_preview"
    assert plan.publish_candidate is False
    assert plan.enable_logging is False
    assert plan.voice == "Anna Kim"
    assert plan.scene_texts[0].tts_text == "첫 장면은 숫자 하나를 자연스럽게 읽습니다."
    assert plan.scene_texts[0].card_duration_sec == 8
    assert "scene_01:long_sentence_count" in plan.warnings


def test_render_manifest_and_upload_plan_document_blockers(tmp_path) -> None:
    mp4 = tmp_path / "preview_1080x1920.mp4"
    video_only = tmp_path / "preview_video_only.mp4"
    storyboard = tmp_path / "storyboard.png"
    mobile_storyboard = tmp_path / "mobile_preview_storyboard.png"
    mobile_checks = tmp_path / "mobile_visual_checks.json"
    frames_dir = tmp_path / "frames"
    scene = pipeline.Scene(1, 8, "Hook", "본문", "visual", "화면")
    audio = pipeline.AudioAsset("scene_audio_preview", "fallback", str(tmp_path / "narration.wav"))
    gate = pipeline.GateResult(True, 97)
    readability = pipeline.ReadabilityResult(True, {}, 10, 20)
    review = pipeline.ContentReview(True, "upload_candidate", {"overall": 88})
    quality = pipeline.PublishQualityResult(True, "test", 91, {"hook_strength": 90})
    visual_quality = pipeline.VisualQualityResult(True, {"diversity": 92})
    beats = [
        pipeline.VisualBeat(
            scene_id=1,
            beat_id=1,
            start_sec=0.0,
            duration_sec=8.0,
            zoom_start=1.0,
            zoom_end=1.0,
            pan_x=0,
            pan_y=0,
            overlay="hold",
        )
    ]

    render_manifest = pipeline.build_render_manifest(
        run_id="leftaino_test",
        render_scenes=[scene],
        visual_beats=beats,
        mp4_path=mp4,
        video_only_path=video_only,
        storyboard_path=storyboard,
        mobile_storyboard_path=mobile_storyboard,
        mobile_checks_path=mobile_checks,
        frames_dir=frames_dir,
        gate=gate,
        readability=readability,
        review=review,
        quality=quality,
        audio_asset=audio,
        visual_quality=visual_quality,
        synced_duration_matches_format=True,
        mobile_visual_passed=True,
    )
    validation = {
        "publish_ready": False,
        "status": "needs_revision",
        "blockers": ["elevenlabs_audio_not_generated"],
    }
    upload_plan = pipeline.build_upload_plan(
        run_id="leftaino_test",
        script=pipeline.ScriptPackage(
            title="테스트",
            caption="caption",
            hashtags=["테스트"],
            post_title="post",
            post_body="body",
            pinned_comment="comment",
            narration="narration",
            scenes=[scene],
            target_duration_sec=8,
            sources=[],
            disclosure="생성 이미지입니다.",
            variant_id="test",
        ),
        format_plan=pipeline.FORMAT_SPECS["reward_deep"],
        validation=validation,
        mp4_path=mp4,
        planned_publish_at_local="2026-05-15T08:10:00+09:00",
    )

    assert render_manifest.target_size == "1080x1920"
    assert render_manifest.fps == 30
    assert render_manifest.codec == "libx264"
    assert render_manifest.video_bitrate == "10M"
    assert render_manifest.static_hold_images is True
    assert render_manifest.gates["audio_publish_candidate"] is False
    assert upload_plan.version == "upload_plan_v1"
    assert upload_plan.status == "blocked"
    assert upload_plan.schedule_time_local == "2026-05-15T08:10:00+09:00"
    assert upload_plan.blockers == ["elevenlabs_audio_not_generated"]


def test_write_mp4_uses_upload_quality_30fps(tmp_path) -> None:
    output = tmp_path / "preview_1080x1920.mp4"
    image = Image.new("RGB", (180, 320), "#101820")
    scene = pipeline.Scene(1, 1, "Hook", "body", "visual", "headline")

    pipeline._write_mp4([image], [scene], output)

    reader = pipeline.imageio.get_reader(str(output))
    try:
        meta = reader.get_meta_data()
        frame_count = reader.count_frames()
    finally:
        reader.close()
    assert round(float(meta["fps"])) == 30
    assert frame_count == 30


def test_studio_schedule_verification_requires_topic_and_time() -> None:
    job = {
        "post_title": "정치폭력, 누가 이익 보나?",
        "caption": "정청래 테러 모의 제보를 민주주의 안전 기준으로 다시 봅니다. 해당 이미지는 생성된 이미지입니다.",
        "planned_publish_at_local": "2026-05-18T19:30:00+09:00",
    }

    assert "정치폭력" in upload_automation._verification_needles(job)
    assert "5월 18일 오후 7:30" in upload_automation._studio_time_needles(job["planned_publish_at_local"])
    assert upload_automation._caption_has_aigc_disclosure(job["caption"])
    assert "해당 이미지는 생성된 이미지입니다" in upload_automation._caption_with_aigc_disclosure("본문만 있는 캡션")


def test_ha_publisher_does_not_mark_scheduled_without_studio_visibility() -> None:
    click_only = {
        "ok": False,
        "schedule_click_performed": True,
        "schedule_verification": {"ok": False, "contains_topic": False, "contains_time": False},
    }
    verified = {
        "ok": True,
        "schedule_click_performed": True,
        "schedule_verification": {"ok": True, "contains_topic": True, "contains_time": True},
    }

    assert not ha_publisher.upload_result_confirms_scheduled(click_only)
    assert ha_publisher.upload_result_confirms_scheduled(verified)


def test_content_plan_maps_script_beats_to_image_requirements() -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열 김건희 국민의힘 특검 압수수색 쟁점",
        angle="최근 48시간 공개 보도 기준으로 검증",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[_configured_hot_claim("연합뉴스", "특검 압수수색 쟁점", "hot_news_01")],
        source_ids=["hot_news_01"],
    )
    sources = {
        "hot_news_01": pipeline.Source(
            "hot_news_01",
            "연합뉴스: 특검 압수수색 쟁점",
            "https://news.google.com/",
            "test dynamic source",
        )
    }
    scenes = [
        pipeline.Scene(1, 8, "Hook", "특검 수사 전말을 1분 안에 봅니다.", "visual", "특검, 48시간 전말"),
        pipeline.Scene(2, 8, "What Happened", "무슨 일이 있었는지 순서부터 정리합니다.", "visual", "무슨 일이 있었나"),
        pipeline.Scene(3, 8, "Conflict Point", "갈라지는 기준 세 가지를 확인합니다.", "visual", "갈라지는 기준"),
        pipeline.Scene(4, 8, "Receipt", "확인된 근거와 비어 있는 근거를 분리합니다.", "visual", "확인된 근거"),
        pipeline.Scene(5, 8, "Responsibility", "누가 설명해야 하는지 책임 라인을 봅니다.", "visual", "책임 라인"),
        pipeline.Scene(6, 8, "Missing Line", "단정 전에 남은 빈칸을 확인합니다.", "visual", "남은 빈칸"),
        pipeline.Scene(7, 8, "Counterpoint", "반론과 확인된 사실을 분리합니다.", "visual", "반론 분리"),
        pipeline.Scene(8, 8, "Why It Matters", "왜 시민에게 중요한지 정리합니다.", "visual", "왜 중요한가"),
        pipeline.Scene(9, 8, "CTA", "댓글로 기준을 남겨주세요.", "visual", "1 전말 2 근거 3 책임"),
    ]
    script = pipeline.ScriptPackage(
        title="특검, 48시간 전말",
        caption="caption",
        hashtags=["정치", "특검"],
        post_title="post title",
        post_body="post body",
        pinned_comment="comment",
        narration="narration",
        scenes=scenes,
        target_duration_sec=72,
        sources=["hot_news_01"],
        disclosure="해당 이미지는 생성된 이미지입니다.",
        variant_id="test",
    )

    plan = pipeline.build_content_plan(
        topic,
        script,
        sources,
        pipeline.FORMAT_SPECS["reward_deep"],
        topic_discovery={
            "selected": {"score": 120, "publisher": "연합뉴스"},
            "selected_trend_clusters": pipeline._matched_trend_clusters(topic.title),
        },
    )

    assert len(plan.image_plan) == len(scenes)
    assert plan.format_id == "reward_deep"
    assert any(row["cluster_id"] == "power_accountability" for row in plan.trend_clusters)
    assert plan.image_plan[0].image_need
    assert plan.image_plan[0].source_ids == ["hot_news_01"]
    assert "실존 인물" in " ".join(plan.risk_controls)
    assert len({row.visual_role for row in plan.image_plan}) >= 6


def test_tiktok_aino_strategy_uses_config_ssot() -> None:
    hot_config = pipeline._load_strategy_config("hot_topic_strategy.json")
    visual_config = pipeline._load_strategy_config("visual_strategy.json")
    quality_config = pipeline._load_strategy_config("publish_quality_strategy.json")
    script_config = pipeline._load_strategy_config("script_strategy.json")
    tts_config = pipeline._load_strategy_config("tts_strategy.json")
    planning_config = pipeline._load_strategy_config("planning_strategy.json")
    keyword_config = pipeline._load_strategy_config("keyword_strategy.json")
    editorial_config = pipeline._load_strategy_config("editorial_strategy.json")

    assert pipeline.HOT_TOPIC_QUERIES == hot_config["queries"]
    assert pipeline.HOT_TOPIC_CANDIDATE_STRATEGY == hot_config["topic_candidate"]
    assert pipeline.HOT_TOPIC_TREND_CLUSTERS == hot_config["trend_clusters"]
    assert pipeline.HOT_HOOK_FALLBACK_HEADLINE == hot_config["fallback_hook_headline"]
    assert pipeline.PLANNING_STRATEGY == planning_config
    assert pipeline.PLANNING_NARRATIVE_ARCS == planning_config["narrative_arc_by_format"]
    assert pipeline.KEYWORD_STRATEGY == keyword_config
    assert pipeline.KEYWORD_BASE_QUERIES == keyword_config["base_queries"]
    assert pipeline.EDITORIAL_STRATEGY == editorial_config
    assert pipeline.EDITORIAL_ANGLE_RULES == editorial_config["angle_rules"]
    assert pipeline.VISUAL_ROLE_PROFILES == visual_config["role_profiles"]
    assert pipeline.VISUAL_DRAMA_PRINCIPLES == visual_config["drama_principles"]
    assert pipeline.VISUAL_ROLE_INTENSITY_BEATS == visual_config["role_intensity_beats"]
    assert pipeline.VISUAL_QUALITY_MINIMUMS == visual_config["quality_minimums"]
    assert pipeline.SCRIPT_QUALITY_WEIGHTS == quality_config["script_quality"]["weights"]
    assert pipeline.POST_METADATA_STRATEGY == script_config["post_metadata"]
    assert pipeline.HOT_TOPIC_SCRIPT_STRATEGY == script_config["hot_topic_script"]
    assert pipeline.DEFAULT_SCRIPT_STRATEGY == script_config["default_script"]
    assert pipeline.SCRIPT_VARIANT_STRATEGY == script_config["variants"]
    assert pipeline.SINO_DIGITS == tts_config["sino_digits"]
    assert pipeline.TTS_HASHTAG_PREFIX == tts_config["hashtag_prefix"]


def test_post_metadata_expands_caption_and_hashtags_without_ellipsis() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 관련 김영선·명태균 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[
            _configured_hot_claim(
                "연합뉴스",
                "윤석열·김건희 공천개입 의혹 관련 김영선·명태균 항소심 시작",
                "hot_news_01",
            )
        ],
        source_ids=["hot_news_01"],
    )
    sources = {
        "hot_news_01": pipeline.Source(
            "hot_news_01",
            "연합뉴스: 윤석열·김건희 공천개입 의혹 관련 김영선·명태균 항소심 시작",
            "https://news.google.com/",
            "test dynamic source",
        )
    }
    plan = pipeline.FORMAT_SPECS["growth_short"]
    script = pipeline.apply_content_format(pipeline.generate_script(topic, style), plan, topic=topic, sources=sources)
    checks = pipeline._metadata_checks(script)

    assert all(checks.values())
    assert "..." not in script.caption
    assert "김영..." not in script.caption
    assert "공천개입" in script.caption
    assert "김건희" in script.hashtags
    assert "올바른AiNo" in script.hashtags


def test_post_metadata_hashtags_do_not_leak_from_supporting_sources() -> None:
    topic = pipeline.TopicCandidate(
        title="국민의힘 스타벅스 5·18 논란 민주주의 훼손",
        angle="민주주의 기억과 책임 기준",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[
            pipeline.Claim(
                text="지원 보도에는 경찰 수사와 검찰 특검이라는 별도 쟁점도 섞여 있다.",
                source_ids=["hot_news_02"],
            )
        ],
        source_ids=["hot_news_02"],
    )
    sources = {
        "hot_news_02": pipeline.Source(
            "hot_news_02",
            "경찰 수사와 검찰 특검 관련 별도 기사",
            "https://news.google.com/",
            "support source should not dominate metadata hashtags",
        )
    }

    tags = pipeline._metadata_hashtags(topic, sources, ["정치", "사회이슈", "올바른AiNo"])

    assert "경찰" not in tags
    assert "검찰" not in tags
    assert "민주주의" in tags
    assert "국민의힘" in tags


def test_mobile_visual_checks_fail_when_text_box_overflows(tmp_path) -> None:
    preview = tmp_path / "scene_01_tiktok_mobile.png"
    preview.write_bytes(b"not-an-image-but-path-exists")
    scene = pipeline.Scene(
        1,
        9,
        "Overflow",
        "이 문장은 모바일 카드 본문 박스 안에서 잘리면 안 되는지 확인하기 위한 매우 긴 문장입니다. "
        "검수는 오른쪽 버튼 영역과 하단 UI만 보는 것이 아니라 실제 텍스트 박스 내부 줄 수와 높이까지 확인해야 합니다. "
        "넘치면 업로드 후보가 아니라 수정 대상으로 내려가야 합니다.",
        "visual",
        "아주 긴 제목도 박스 안에서 줄 수 제한을 지켜야 합니다",
    )

    checks = pipeline._mobile_visual_checks([scene], [preview])

    assert checks[0].text_box_overflow is True
    assert checks[0].body_fits_box is False
    assert checks[0].text_panel_coverage_pct <= pipeline.MAX_TEXT_PANEL_COVERAGE_PCT
    assert checks[0].passed is False


def test_scene_image_uses_native_generated_text_without_overlay(tmp_path) -> None:
    source = tmp_path / "native_text.png"
    Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#ffffff").save(source)
    scene = pipeline.Scene(
        1,
        9,
        "Hook",
        "Body that would be drawn if overlay mode were still active.",
        "visual",
        "Native image headline",
    )
    asset = pipeline.VisualAsset(
        scene_id=1,
        provider="codex_cli",
        status="generated",
        path=str(source),
        prompt="test prompt",
        visual_brief={"role": "hook", "issue_type": "education", "diegetic_text": "Native image headline"},
    )

    image = pipeline._scene_image(scene, 0, 1, asset, pipeline._font(30), pipeline._font(24), "올바른 AiNo")

    assert image.getpixel((pipeline.TEXT_SAFE_LEFT, 82)) == (255, 255, 255)
    assert image.getpixel((180, 1220)) == (255, 255, 255)


def test_mobile_visual_checks_native_generated_text_skips_overlay_layout(tmp_path) -> None:
    preview = tmp_path / "scene_01.png"
    Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#ffffff").save(preview)
    scene = pipeline.Scene(
        1,
        9,
        "Hook",
        "Body",
        "visual",
        "Native image headline",
    )
    asset = pipeline.VisualAsset(
        scene_id=1,
        provider="codex_cli",
        status="generated",
        path=str(preview),
        prompt="test prompt",
        visual_brief={"role": "hook", "issue_type": "education", "diegetic_text": "Native image headline"},
    )

    checks = pipeline._mobile_visual_checks([scene], [preview], {1: asset})

    assert checks[0].layout_id == "native_image_text"
    assert checks[0].text_panel_coverage_pct == 0.0
    assert checks[0].headline_mobile_px == 0.0
    assert checks[0].body_mobile_px == 0.0
    assert checks[0].passed is True


def test_card_layout_ids_vary_by_scene_role() -> None:
    scenes = [
        pipeline.Scene(index + 1, 7, f"scene {index + 1}", "Short body for mobile readability.", "visual", "Short headline")
        for index in range(7)
    ]
    roles = ["hook", "why_now", "evidence", "criteria", "responsibility", "verification", "cta"]
    assets = {
        scene.scene_id: pipeline.VisualAsset(
            scene_id=scene.scene_id,
            provider="local",
            status="generated",
            path=None,
            prompt="layout test",
            visual_brief={"role": role},
        )
        for scene, role in zip(scenes, roles)
    }

    quality = pipeline._card_layout_quality(scenes, assets)

    assert quality["passed"] is True
    assert quality["unique_count"] >= 5
    assert quality["layout_ids"][0] == "impact_cover"
    assert quality["layout_ids"][-1] == "choice_stack"


def test_scene_text_layout_check_uses_distinct_geometry_by_layout() -> None:
    scene = pipeline.Scene(
        1,
        7,
        "Layout",
        "Evidence is summarized in a compact mobile readable sentence.",
        "visual",
        "Why this frame matters",
    )

    hook_layout = pipeline._scene_text_layout_check(scene, 0, total=7, role="hook")
    criteria_layout = pipeline._scene_text_layout_check(scene, 3, total=7, role="criteria")

    assert hook_layout["layout_id"] == "impact_cover"
    assert criteria_layout["layout_id"] == "side_rule"
    assert hook_layout["panel_box"] != criteria_layout["panel_box"]
    assert hook_layout["headline_box"][1] != criteria_layout["headline_box"][1]
    assert hook_layout["text_box_overflow"] is False
    assert criteria_layout["text_box_overflow"] is False
    assert hook_layout["text_panel_coverage_pct"] <= pipeline.MAX_TEXT_PANEL_COVERAGE_PCT
    assert criteria_layout["text_panel_coverage_pct"] <= pipeline.MAX_TEXT_PANEL_COVERAGE_PCT


def test_cinematic_prompt_uses_controlled_diegetic_text_without_text_ban() -> None:
    topic = pipeline.TopicCandidate(
        title="\ub9ac\ubc15\uc2a4\ucfe8 \ud64d\ubcf4 \uc601\uc0c1 \uad50\uc721 \ub17c\ub780",
        angle="\uad50\uc2e4\uc5d0\uc11c \ubb34\uc5c7\uc744 \ubcf4\uc544\uc57c \ud558\ub294\uc9c0",
        slot="test",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )
    scene = pipeline.Scene(
        1,
        9,
        "\ud6c5",
        "\ub204\uac00 \uc774\ub4e4\uc744 \uad50\uc2e4\ub85c \ubcf4\ub0c8\uc2b5\ub2c8\uae4c.",
        "after-hours classroom doorway",
        "\ub204, \uc65c \uac08\ub9ac\ub098?",
    )

    brief = pipeline._build_visual_brief(topic, scene, 0, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.diegetic_text == "\ub204, \uc65c \uac08\ub9ac\ub098?"
    assert "Mandatory text-prop foreground" in prompt
    assert "Controlled in-image text" in prompt
    assert '"\ub204, \uc65c \uac08\ub9ac\ub098?"' in prompt
    assert not any("no readable text" in item.lower() for item in brief.safety_constraints)
    assert "Do not invent any other readable text" in prompt


def test_diegetic_text_is_shortened_for_image_generation() -> None:
    scene = pipeline.Scene(
        1,
        9,
        "Long",
        "body",
        "visual",
        "\uc774 \ubb38\uc7a5\uc740 \uc774\ubbf8\uc9c0 \uc18d \uc18c\ud488\uc5d0 \ub4e4\uc5b4\uac00\uae30\uc5d0\ub294 \ub108\ubb34 \uae41 \ud14d\uc2a4\ud2b8\uc785\ub2c8\ub2e4",
    )

    text = pipeline._diegetic_text_for_scene(scene)

    assert len(text) <= pipeline.VISUAL_DIEGETIC_TEXT_MAX_CHARS
    assert "..." not in text


def test_topic_priority_issue_prevents_generic_frame_scene_drift() -> None:
    frame_issue = pipeline._select_visual_issue_type(
        "\ub9ac\ubc15\uc2a4\ucfe8 \uad50\uc2e4 \uad50\uc721 \ub17c\ub780",
        "\uc774 \uc774\uc288\ub294 \ub204\uac00 \ud504\ub808\uc784\uc744 \uac00\uc838\uac00\ub290\ub0d0\uc758 \ubb38\uc81c\uc785\ub2c8\ub2e4.",
    )
    polling_issue = pipeline._select_visual_issue_type(
        "\ub9ac\ubc15\uc2a4\ucfe8 \uad50\uc2e4 \uad50\uc721 \ub17c\ub780",
        "\ubc29\uc2ec\ud558\uba74 \ub0ae\uc740 \uacb0\uc9d1\ub3c4 \ub192\uc740 \ud22c\ud45c\uc728 \uc55e\uc5d0\uc11c \ud754\ub4e4\ub9bd\ub2c8\ub2e4.",
    )

    assert frame_issue == "education"
    assert polling_issue == "education"


def test_card_layout_quality_diversifies_repeated_middle_roles() -> None:
    scenes = [
        pipeline.Scene(index + 1, 7, f"scene {index + 1}", "Short body.", "visual", "Short headline")
        for index in range(7)
    ]
    assets = {
        scene.scene_id: pipeline.VisualAsset(
            scene_id=scene.scene_id,
            provider="local",
            status="generated",
            path=None,
            prompt="layout test",
            visual_brief={"role": "evidence"},
        )
        for scene in scenes
    }

    quality = pipeline._card_layout_quality(scenes, assets)

    assert quality["passed"] is True
    assert quality["unique_count"] >= quality["required_unique_count"]
    assert quality["max_repeat_count"] <= 2
    assert not quality["adjacent_repeats"]


def test_hot_topic_supporting_sources_stay_in_selected_cluster() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    selected = pipeline.HotTopicItem(
        title="Kim Geonhee prosecution no charge dispute",
        publisher="MBC",
        url="https://news.example/1",
        published_at=now,
        query="politics",
        score=90,
    )
    same_cluster = pipeline.HotTopicItem(
        title="Kim Geonhee no charge decision sparks accountability question",
        publisher="KBS",
        url="https://news.example/2",
        published_at=now,
        query="politics",
        score=80,
    )
    unrelated = pipeline.HotTopicItem(
        title="Education labor candidate announces local policy alliance",
        publisher="MBC",
        url="https://news.example/3",
        published_at=now,
        query="education",
        score=85,
    )

    support = pipeline._select_supporting_hot_topics(selected, [selected, unrelated, same_cluster])

    assert same_cluster in support
    assert unrelated not in support


def test_hot_topic_supporting_sources_do_not_cross_kim_geonhee_subissues() -> None:
    now = pipeline.dt.datetime.now(pipeline.dt.timezone.utc).isoformat()
    selected = pipeline.HotTopicItem(
        title="윤석열 김건희 공천개입 의혹 관련 김영선 명태균 항소심 시작",
        publisher="한겨레",
        url="https://news.example/1",
        published_at=now,
        query="김건희 윤석열 의혹",
        score=115,
    )
    same_subissue = pipeline.HotTopicItem(
        title="김영선 명태균 공천개입 의혹 항소심 쟁점 정리",
        publisher="경향신문",
        url="https://news.example/2",
        published_at=now,
        query="김건희 윤석열 의혹",
        score=88,
    )
    different_subissue = pipeline.HotTopicItem(
        title="경찰 선상파티 의혹 김건희 무혐의 실무 책임자 송치",
        publisher="연합뉴스",
        url="https://news.example/3",
        published_at=now,
        query="김건희 윤석열 의혹",
        score=106,
    )

    support = pipeline._select_supporting_hot_topics(selected, [selected, different_subissue, same_subissue])

    assert same_subissue in support
    assert different_subissue not in support


def test_hot_topic_script_uses_dynamic_sources_and_evidence_briefing_format() -> None:
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = {
        "hot_news_01": pipeline.Source(
            "hot_news_01",
            "연합뉴스: 국회 교육 정책 검증 논란",
            "https://news.google.com/",
            "test dynamic source",
        ),
        "hot_news_02": pipeline.Source(
            "hot_news_02",
            "경향신문: 시민단체 정책 검증 요구",
            "https://news.google.com/",
            "test dynamic source",
        ),
    }
    topic = pipeline.TopicCandidate(
        title="국회 교육 정책 검증 논란",
        angle=_hot_candidate_value("angle"),
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[
            _configured_hot_claim("연합뉴스", "국회 교육 정책 검증 논란", "hot_news_01"),
            _configured_hot_claim("경향신문", "시민단체 정책 검증 요구", "hot_news_02"),
        ],
        source_ids=["hot_news_01", "hot_news_02"],
    )

    plan = pipeline.route_content_format(topic)
    script = pipeline.apply_content_format(pipeline.generate_script(topic, style), plan)
    gate = pipeline.check_policy(topic, script, sources, plan)
    readability = pipeline.check_readability(script, plan)

    assert plan.format_id == "evidence_briefing_75"
    assert script.variant_id.startswith("hot_issue_check:evidence")
    assert set(script.sources) == {"hot_news_01", "hot_news_02"}
    assert gate.passed
    assert readability.passed


def test_hot_hook_headline_tightens_kim_geonhee_no_charge_topic() -> None:
    assert pipeline._hot_hook_headline("경찰, 김건희 선상파티 의혹 무혐의·관계자 송치") == "무혐의면 끝인가?"


def test_hot_hook_headline_uses_reference_based_formats() -> None:
    assert pipeline._hot_hook_headline("김건희 특검 구형 공방") == "특검, 48시간 전말"
    assert pipeline._hot_hook_headline("정치권 팩트체크 없이 가짜뉴스 언급") == "오해와 진실만 보자"
    assert pipeline._hot_hook_headline("대통령실 일주일 침묵 논란") == "왜 침묵했나?"
    assert pipeline._hot_hook_headline("검찰개혁 특검 의혹 국회 공방") == "검찰개혁, 48시간 전말"


def test_publish_quality_blocks_bland_low_search_content() -> None:
    topic = pipeline.TopicCandidate(
        title="김건희 무혐의 송치 논란",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=40,
        claims=[_configured_hot_claim("연합뉴스", "김건희 무혐의 송치 논란", "hot_news_01")],
        source_ids=["hot_news_01"],
    )
    sources = {
        "hot_news_01": pipeline.Source(
            "hot_news_01",
            "연합뉴스: 김건희 무혐의 송치 논란",
            "https://news.google.com/",
            "test dynamic source",
        )
    }
    scenes = [
        pipeline.Scene(
            index + 1,
            8,
            f"Scene {index + 1}",
            "오늘 이야기를 차분히 보겠습니다. 댓글로 어떤 기준이 필요한지 남겨주세요."
            if index in {4, 8}
            else "오늘 이야기를 차분히 보겠습니다. 댓글로 의견을 남겨주세요.",
            "bland placeholder background",
            "어떻게 볼까요?" if index in {4, 8} else "오늘 이야기 정리",
        )
        for index in range(9)
    ]
    script = pipeline.ScriptPackage(
        title="오늘 이야기",
        caption="오늘 이야기를 정리합니다. #사회",
        hashtags=["사회", "정리"],
        post_title="오늘 이야기",
        post_body="오늘 이야기를 정리합니다.",
        pinned_comment="댓글로 의견을 남겨주세요.",
        narration="\n".join(scene.body for scene in scenes),
        scenes=scenes,
        target_duration_sec=72,
        sources=["hot_news_01"],
        disclosure="AI-generated content disclosure required",
        variant_id="bland",
    )
    plan = pipeline.FORMAT_SPECS["growth_short"]
    gate = pipeline.check_policy(topic, script, sources, plan)
    readability = pipeline.check_readability(script, plan)
    quality = pipeline._score_script_quality(script, gate, readability, topic, sources, plan)

    assert gate.passed
    assert readability.passed
    assert not quality.passed
    assert quality.scores["safe_provocation"] < 70
    assert quality.scores["search_value"] < 72
    assert quality.blockers


def test_transition_frame_keeps_video_canvas_and_changes_pixels() -> None:
    previous = Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#111820")
    current = Image.new("RGB", (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT), "#f0f4f8")

    frame = pipeline._transition_frame(previous, current, 0.5, "wipe")

    assert frame.size == (pipeline.CANVAS_WIDTH, pipeline.CANVAS_HEIGHT)
    assert frame.getpixel((pipeline.CANVAS_WIDTH // 4, 40)) != previous.getpixel((0, 0))
    assert frame.getpixel((pipeline.CANVAS_WIDTH - 20, 40)) == previous.getpixel((0, 0))


def test_visual_brief_ties_scene_image_to_topic_and_card_text() -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(
            1,
            8,
            "Hot Hook",
            "김건희 의혹, 끝난 걸까? 여러 보도에서 반복된 쟁점을 기록으로만 보겠습니다.",
            "sealed file",
            "김건희 의혹, 끝난 걸까?",
        ),
        pipeline.Scene(
            2,
            8,
            "Check",
            "경찰, 선상파티 의혹 김건희 무혐의. 확인된 것과 남은 쟁점을 나눠 봅니다.",
            "police review desk",
            "확인된 것만 남기기",
        ),
        pipeline.Scene(
            3,
            8,
            "CTA",
            str(_configured_hot_scene(8)["body"]),
            "editor desk",
            "댓글로 기준을 남겨주세요",
        ),
    ]

    briefs = pipeline.build_visual_briefs(topic, scenes)
    prompt = pipeline._build_cinematic_prompt(scenes[1], briefs[1])

    assert briefs[0].role == "hook"
    assert briefs[0].issue_type == "court_case"
    assert "김건희" in briefs[0].relevance_terms
    assert briefs[1].issue_type == "investigation"
    assert any("file" in anchor or "evidence" in anchor for anchor in briefs[1].visual_anchor)
    assert "Supporting visual anchors" in prompt
    cinematic_lines = pipeline._load_strategy_config("visual_strategy.json")["prompting"]["cinematic"]["lines"]
    for template_line in cinematic_lines:
        prefix = str(template_line).split("{", 1)[0].strip()
        if prefix:
            assert prefix in prompt


def test_visual_role_detection_keeps_reward_deep_scenes_diverse() -> None:
    topic = pipeline.TopicCandidate(
        title="종합특검, 대통령 집무실 이전 봐주기 의혹 감사원 압수수색",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 9, "Hot Hook", "특검, 48시간 전말", "visual", "특검, 48시간 전말"),
        pipeline.Scene(2, 9, "What Happened", "도화선을 봅니다.", "visual", "무슨 일이 있었나"),
        pipeline.Scene(3, 9, "Conflict Point", "갈라지는 지점입니다.", "visual", "출처를 나눠 보기"),
        pipeline.Scene(4, 8, "Receipt", "근거를 봅니다.", "visual", "근거가 남긴 것"),
        pipeline.Scene(5, 8, "Missing Line", "빈칸을 봅니다.", "visual", "사실, 주장, 책임"),
        pipeline.Scene(6, 8, "Check", "확인합니다.", "visual", "확인된 것만 남기기"),
        pipeline.Scene(7, 8, "Counterpoint", "반론 가능성을 남깁니다.", "visual", "단정 전에 볼 것"),
        pipeline.Scene(8, 8, "Responsibility Review", "책임 기준을 봅니다.", "visual", "책임 기준 남기기"),
        pipeline.Scene(9, 8, "CTA", "댓글로 남깁니다.", "visual", "1 전말 2 근거 3 책임"),
    ]

    roles = [brief.role for brief in pipeline.build_visual_briefs(topic, scenes)]
    issues = [brief.issue_type for brief in pipeline.build_visual_briefs(topic, scenes)]

    assert roles == [
        "hook",
        "why_now",
        "criteria",
        "evidence",
        "responsibility",
        "verification",
        "responsibility",
        "responsibility",
        "cta",
    ]
    assert "investigation" in issues
    assert len(set(roles)) >= 6


def test_repeated_visual_roles_get_repeat_variants() -> None:
    topic = pipeline.TopicCandidate(
        title="종합특검 계엄 책임 쟁점",
        angle="확인된 보도와 반론을 분리",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 9, "Hot Hook", "계엄 책임을 봅니다.", "visual", "계엄 책임"),
        pipeline.Scene(2, 8, "Check", "확인된 보도와 반론을 분리합니다.", "visual", "반론까지 분리"),
        pipeline.Scene(3, 8, "Check Again", "단정 전에 다시 확인합니다.", "visual", "단정 전 체크"),
    ]

    briefs = pipeline.build_visual_briefs(topic, scenes)

    assert briefs[1].role == "verification"
    assert briefs[2].role == "verification"
    assert briefs[1].location != briefs[2].location
    assert "verification_repeat_1" in briefs[2].diversity_tags
    assert any("archive counter" in anchor or "stamp pad" in anchor for anchor in briefs[2].visual_anchor)


def test_repeated_evidence_and_cta_roles_get_distinct_visual_variants() -> None:
    topic = pipeline.TopicCandidate(
        title="늘봄학교 정치교육 의혹",
        angle="교실로 들어온 외부 교육 쟁점을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 9, "Hard Hook", "처음 질문을 봅니다.", "classroom doorway", "누가 교실로 들어왔나"),
        pipeline.Scene(2, 9, "Receipt", "첫 번째 근거를 봅니다.", "source table", "출처를 나눠 보기"),
        pipeline.Scene(3, 9, "Receipt Again", "두 번째 근거를 봅니다.", "archive counter", "두 번째 출처"),
        pipeline.Scene(4, 8, "Parent Concern", "학부모 우려를 봅니다.", "rainy school entrance", "학부모들의 우려"),
        pipeline.Scene(5, 8, "CTA", "댓글로 남깁니다.", "editor desk", "책임 기준 남기기"),
        pipeline.Scene(6, 8, "CTA Again", "다시 댓글로 남깁니다.", "classroom doorway", "1 전말 2 근거 3 책임"),
    ]

    briefs = pipeline.build_visual_briefs(topic, scenes)

    assert "evidence_repeat_1" in briefs[2].diversity_tags
    assert "evidence_repeat_2" in briefs[3].diversity_tags
    assert any("archive counter" in anchor for anchor in briefs[2].visual_anchor)
    assert any("rainy anonymous school entrance" in anchor for anchor in briefs[3].visual_anchor)
    assert "cta_repeat_1" in briefs[5].diversity_tags
    assert any("open classroom doorway" in anchor for anchor in briefs[5].visual_anchor)


def test_visual_quality_gate_scores_specific_briefs_above_threshold() -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 8, "Hot Hook", "김건희 의혹, 끝난 걸까?", "sealed file", "김건희 의혹, 끝난 걸까?"),
        pipeline.Scene(2, 8, "Why Now", "윤석열·김건희 공천개입 의혹 관련 항소심 시작", "courthouse", "오늘 왜 뜨거운가"),
        pipeline.Scene(3, 8, "Check", "경찰, 선상파티 의혹 김건희 무혐의", "police review", "확인된 것만 남기기"),
    ]
    assets = []
    for index, scene in enumerate(scenes):
        brief = pipeline._build_visual_brief(topic, scene, index, len(scenes))
        assets.append(
            pipeline.VisualAsset(
                scene_id=scene.scene_id,
                provider="codex_cli",
                status="generated",
                path="x.png",
                prompt=pipeline._build_cinematic_prompt(scene, brief),
                visual_brief=pipeline.asdict(brief),
            )
        )

    result = pipeline.check_visual_quality(assets, scenes)

    assert result.passed
    assert result.scores["topic_relevance"] >= 80
    assert result.scores["scene_relevance"] >= 78
    assert result.scores["visual_metaphor"] >= 80
    assert result.scores["scene_visual_metaphor"] >= 80
    assert result.scores["visual_variety"] >= 75
    assert result.scores["documentary_realism"] >= 90
    assert result.scores["foreground_tension"] >= 90
    assert result.scores["thumbnail_drama"] >= 90


def test_actual_visual_diversity_blocks_identical_generated_images(tmp_path) -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 8, "Hot Hook", "김건희 의혹, 끝난 걸까?", "sealed file", "김건희 의혹, 끝난 걸까?"),
        pipeline.Scene(2, 8, "Why Now", "윤석열·김건희 공천개입 의혹 관련 항소심 시작", "newsroom desk", "오늘 왜 뜨거운가"),
        pipeline.Scene(3, 8, "Check", "경찰, 선상파티 의혹 김건희 무혐의", "police review", "확인된 것만 남기기"),
    ]
    image_path = tmp_path / "same.png"
    Image.new("RGB", (256, 384), "#202832").save(image_path)
    assets = []
    for index, scene in enumerate(scenes):
        brief = pipeline._build_visual_brief(topic, scene, index, len(scenes))
        copied = tmp_path / f"same_{index}.png"
        Image.open(image_path).save(copied)
        assets.append(
            pipeline.VisualAsset(
                scene_id=scene.scene_id,
                provider="codex_cli",
                status="generated",
                path=str(copied),
                prompt=pipeline._build_cinematic_prompt(scene, brief),
                visual_brief=pipeline.asdict(brief),
            )
        )

    result = pipeline.check_visual_quality(assets, scenes)

    assert not result.passed
    assert result.scores["actual_visual_diversity"] < 78
    assert any(blocker.startswith("actual_visual_diversity_below_80") for blocker in result.blockers)


def test_actual_visual_diversity_blocks_same_palette_scene_variants(tmp_path) -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 8, "Hot Hook", "김건희 의혹, 끝난 걸까?", "sealed file", "김건희 의혹, 끝난 걸까?"),
        pipeline.Scene(2, 8, "Why Now", "오늘 같은 쟁점이 반복됐습니다.", "newsroom desk", "오늘 왜 뜨거운가"),
        pipeline.Scene(3, 8, "Check", "확인된 것만 남겨야 합니다.", "review desk", "확인된 것만 남기기"),
    ]
    assets = []
    for index, scene in enumerate(scenes):
        image_path = tmp_path / f"same_palette_{index}.png"
        image = Image.new("RGB", (256, 384), "#202832")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20 + index * 18, 90, 180 + index * 12, 220), fill="#303a44")
        draw.line((30, 260 + index * 12, 220, 300 + index * 8), fill="#4a5561", width=8)
        image.save(image_path)
        brief = pipeline._build_visual_brief(topic, scene, index, len(scenes))
        assets.append(
            pipeline.VisualAsset(
                scene_id=scene.scene_id,
                provider="codex_cli",
                status="generated",
                path=str(image_path),
                prompt=pipeline._build_cinematic_prompt(scene, brief),
                visual_brief=pipeline.asdict(brief),
            )
        )

    result = pipeline.check_visual_quality(assets, scenes)

    assert not result.passed
    assert result.scores["actual_palette_diversity"] < 78
    assert any(blocker.startswith("actual_palette_diversity_below_78") for blocker in result.blockers)


def test_cta_visual_brief_does_not_reuse_courthouse_corridor() -> None:
    topic = pipeline.TopicCandidate(
        title="윤석열·김건희 공천개입 의혹 항소심 시작",
        angle="최근 보도 반복 쟁점 검증",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        6,
        7,
        "CTA",
        str(_configured_hot_scene(8)["body"]),
        "editing desk with comment cards",
        "댓글로 기준을 남겨주세요",
    )
    brief = pipeline._build_visual_brief(topic, scene, 5, 6)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.role == "cta"
    assert brief.location.startswith("investigative video editor desk prepared for viewer comments")
    assert "courthouse corridor" not in " ".join(brief.visual_anchor)
    assert "Scene uniqueness" in prompt
    assert "CTA must look like an editor desk" in prompt
    assert "courthouse corridor" not in pipeline._hot_visual_for_text(topic.title, "cta")


def test_visual_prompt_uses_topic_context_without_prior_issue_leakage() -> None:
    topic = pipeline.TopicCandidate(
        title="평택시 미래기술학교 반도체 공정 장비 과정 교육생 모집",
        angle="교육과 일자리 정책을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    values = pipeline._template_values_for_topic(
        topic,
        title="평택시 미래기술학교 교육생 모집",
        hook_headline="무엇을 봐야 할까?",
        hashtags=["교육", "일자리"],
    )
    scene = pipeline._configured_hot_scene(_configured_hot_scene(5), topic, values)
    brief = pipeline._build_visual_brief(topic, scene, 5, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.issue_type == "education"
    assert "South Korean classroom or education office after hours" in brief.location
    assert "반도체" in brief.relevance_terms
    assert "교육생" in brief.relevance_terms
    assert "harbor" not in prompt.lower()
    assert "선상파티" not in prompt


def test_visual_prompt_prioritizes_issue_anchors_for_hook_cards() -> None:
    topic = pipeline.TopicCandidate(
        title="늘봄학교 정치교육 의혹",
        angle="교실로 들어온 외부 교육 쟁점을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        1,
        9,
        "Hard Hook",
        "누가 아이들 교실로 들어왔는지 먼저 봅니다.",
        "empty elementary classroom after hours with blank folders",
        "누가 교실로 들어왔나",
    )
    brief = pipeline._build_visual_brief(topic, scene, 0, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.role == "hook"
    assert brief.issue_type == "education"
    assert "South Korean classroom or education office after hours" in brief.location
    assert any("classroom" in anchor or "student desks" in anchor for anchor in brief.visual_anchor)
    assert "Scene-specific priority" in prompt


def test_visual_prompt_adds_treatment_and_action_for_more_dynamic_images() -> None:
    topic = pipeline.TopicCandidate(
        title="늘봄학교 정치교육 의혹",
        angle="교실로 들어온 외부 교육 쟁점을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        2,
        9,
        "Receipt",
        "확인된 출처와 남은 빈칸을 나눕니다.",
        "hands separating blank source packets in a classroom office",
        "출처를 나눠 보기",
    )
    brief = pipeline._build_visual_brief(topic, scene, 1, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert brief.treatment_id
    assert brief.visual_treatment
    assert brief.action_beat
    assert "Visual treatment:" in prompt
    assert "Action beat:" in prompt
    assert "Concrete scene directive:" in prompt
    assert brief.concrete_scene
    assert "Treatment override:" in prompt
    assert "Character/satire rule:" in prompt
    assert "Liveliness rule:" in prompt
    assert "Original visual context:" in prompt
    assert "Create this concrete scene first" in prompt


def test_visual_prompt_uses_concrete_topic_scene_before_symbolic_anchors() -> None:
    topic = pipeline.TopicCandidate(
        title="국민의힘 스타벅스 5·18 논란 민주주의 훼손",
        angle="민주주의 기억과 책임 기준",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        1,
        9,
        "Hot Hook",
        "5·18 앞에서 빠진 책임선을 봅니다.",
        "blank folders and microphones",
        "5·18 앞에서 빠진 책임은?",
    )

    brief = pipeline._build_visual_brief(topic, scene, 0, 9)
    prompt = pipeline._build_cinematic_prompt(scene, brief)

    assert "memorial-plaza" in brief.concrete_scene
    assert "coffee cup" in brief.concrete_scene
    assert "Concrete scene directive:" in prompt
    assert "Literal-scene rule:" in prompt
    assert prompt.index("Concrete scene directive:") < prompt.index("Supporting visual anchors")


def test_visual_topic_scene_pack_uses_polling_context_before_generic_desks() -> None:
    topic = pipeline.TopicCandidate(
        title="\uc9c0\uc9c0\uc728 60% \uc5ec\ub860\uc870\uc0ac \ubbfc\uc8fc 45 \uad6d\ud798 20 \ubcf4\uc218 \uacb0\uc9d1",
        angle="\uc120\uac70 \uc9c0\ud615\uc740 \uc22b\uc790\ubcf4\ub2e4 \ud22c\ud45c\uc728\uacfc \uc9c0\uc5ed \uc774\ud0c8\uc744 \ubd10\uc57c \ud55c\ub2e4",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scenes = [
        pipeline.Scene(1, 9, "Hot Hook", "\uc22b\uc790\uac00 \ud070\ub370 \uc65c \ubd88\uc548\ud55c\uc9c0 \ubd05\ub2c8\ub2e4.", "generic folder desk", "\uc9c0\uc9c0\uc728, \uc65c \ubd88\uc548\ud558\uc9c0?"),
        pipeline.Scene(2, 9, "Receipt", "\uc815\ub9d0 \ubd10\uc57c \ud560 \uac74 \uacb0\uc9d1\uacfc \uc774\ud0c8\uc785\ub2c8\ub2e4.", "editor desk", "\uacb0\uc9d1\uacfc \uc774\ud0c8"),
    ]

    briefs = pipeline.build_visual_briefs(topic, scenes)

    assert {brief.issue_type for brief in briefs} == {"polling_election"}
    assert "polling" in briefs[0].concrete_scene
    assert "regional map" in briefs[0].concrete_scene
    assert pipeline.VISUAL_DEFAULT_CONCRETE_SCENE not in [brief.concrete_scene for brief in briefs]
    assert any("polling" in anchor or "survey" in anchor for anchor in briefs[0].visual_anchor)


def test_visual_topic_scene_pack_uses_party_strategy_without_real_likeness() -> None:
    topic = pipeline.TopicCandidate(
        title="\uc774\uc7ac\uba85 \ubbfc\uc8fc\ub2f9 \uad6d\ubbfc\uc758\ud798 \ubcf4\uc218 \uc804\ub7b5 \ub17c\uc7c1",
        angle="\uc2e4\uc874 \uc5bc\uad74\uc774 \uc544\ub2c8\ub77c \uc775\uba85 \uc815\uce58 \uc804\ub7b5 \uc7a5\uba74\uc73c\ub85c \ud45c\ud604\ud55c\ub2e4",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=75,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        1,
        9,
        "Hot Hook",
        "\ub204\uac00 \ud504\ub808\uc784\uc744 \uba39\uc5ec \ub123\ub294\uc9c0 \ubd05\ub2c8\ub2e4.",
        "generic newsroom desk",
        "\ub204\uac00 \uba39\uc5ec \ub123\ub098?",
    )

    brief = pipeline._build_visual_brief(topic, scene, 0, 9)

    assert brief.issue_type == "party_strategy"
    assert "party-strategy room" in brief.concrete_scene
    assert "no real faces" in brief.concrete_scene
    assert "no real politician likeness" in brief.safety_constraints


def test_visual_quality_blocks_non_generic_default_concrete_scene(tmp_path) -> None:
    scene = pipeline.Scene(1, 9, "Hot Hook", "\uc9c0\uc9c0\uc728 \uc774\uc288", "generic desk", "\uc9c0\uc9c0\uc728 \uc774\uc288")
    image_path = tmp_path / "visual.png"
    Image.new("RGB", (256, 384), "#203040").save(image_path)
    asset = pipeline.VisualAsset(
        scene_id=scene.scene_id,
        provider="codex_cli",
        status="generated",
        path=str(image_path),
        prompt="not a generic office, one dominant foreground object, Foreground tension, Thumbnail drama, first-second, 35mm documentary lens, real-world moment, plausible real-world moment, negative space, no real politician likeness",
        visual_brief={
            "issue_type": "polling_election",
            "role": "hook",
            "location": "polling analysis room",
            "palette": "cool monitor blue",
            "concrete_scene": pipeline.VISUAL_DEFAULT_CONCRETE_SCENE,
            "visual_anchor": ["polling call-center desks", "blank regional election map wall"],
            "relevance_terms": ["\uc9c0\uc9c0\uc728", "\uc5ec\ub860\uc870\uc0ac"],
        },
    )

    result = pipeline.check_visual_quality([asset], [scene])

    assert any(blocker.startswith("topic_specific_concrete_scene_missing:1") for blocker in result.blockers)


def test_visual_role_title_priority_preserves_card_variety() -> None:
    topic = pipeline.TopicCandidate(
        title="평택시 미래기술학교 반도체 공정 장비 과정 교육생 모집",
        angle="교육과 일자리 정책을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        7,
        8,
        "Question",
        "여기서 필요한 건 빠른 분노가 아니라 정확한 기준입니다.",
        "accountability room",
        "어디까지 확인할까요?",
    )
    brief = pipeline._build_visual_brief(topic, scene, 6, 9)

    assert brief.role == "responsibility"


def test_second_source_card_stays_evidence_despite_criteria_words() -> None:
    topic = pipeline.TopicCandidate(
        title="평택시 미래기술학교 반도체 공정 장비 과정 교육생 모집",
        angle="교육과 일자리 정책을 기록 기준으로 확인",
        slot=_hot_candidate_value("slot"),
        target_duration_sec=45,
        claims=[],
        source_ids=["hot_news_01"],
    )
    scene = pipeline.Scene(
        3,
        9,
        "Second Source",
        "두 번째로 볼 지점은 누가 말했는지가 아니라 어떤 기준을 남겼는지입니다.",
        "source table",
        "두 번째 확인 지점",
    )
    brief = pipeline._build_visual_brief(topic, scene, 2, 9)

    assert brief.role == "evidence"


def test_hot_visual_prompt_requires_active_foreground_drama() -> None:
    prompt = pipeline._hot_visual_for_text("源嫄댄씗 怨듭쿇媛쒖엯 ?섑샊", "hook")
    visual_config = pipeline._load_strategy_config("visual_strategy.json")
    hot_prompting = visual_config["prompting"]["hot_visual"]

    assert hot_prompting["composition"] in prompt
    assert hot_prompting["texture"] in prompt
    assert hot_prompting["policy_safety"] in prompt
    assert visual_config["role_intensity_beats"]["hook"] in prompt
    assert visual_config["role_profiles"]["hook"]["anchors"][3] in prompt


def test_visual_prompt_language_is_config_owned_not_pipeline_hardcoded() -> None:
    source = pipeline.Path(pipeline.__file__).read_text(encoding="utf-8")
    visual_config = pipeline._load_strategy_config("visual_strategy.json")
    prompt_config = visual_config["prompting"]
    forbidden_values = [
        prompt_config["hot_visual"]["base"],
        prompt_config["hot_visual"]["composition"],
        prompt_config["cinematic"]["lines"][0],
        prompt_config["cinematic"]["lines"][18],
        prompt_config["codex_cli"]["style"],
        visual_config["role_intensity_beats"]["hook"],
    ]

    for value in forbidden_values:
        assert value not in source


def test_script_generation_language_is_config_owned_not_pipeline_hardcoded() -> None:
    source = pipeline.Path(pipeline.__file__).read_text(encoding="utf-8")
    hot_config = pipeline._load_strategy_config("hot_topic_strategy.json")
    script_config = pipeline._load_strategy_config("script_strategy.json")
    forbidden_values = [
        hot_config["topic_candidate"]["claim_text_template"],
        hot_config["topic_candidate"]["angle"],
        script_config["hot_topic_script"]["caption_template"],
        script_config["hot_topic_script"]["pinned_comment"],
        script_config["hot_topic_script"]["scenes"][0]["body_template"],
        script_config["default_topic"]["title"],
        script_config["default_script"]["caption"],
        script_config["default_script"]["scenes"][0]["body"],
        script_config["variants"]["strong_hook"]["script_updates"]["caption"],
        script_config["copy_normalization"]["last_body_append"],
    ]

    for value in forbidden_values:
        assert value not in source
