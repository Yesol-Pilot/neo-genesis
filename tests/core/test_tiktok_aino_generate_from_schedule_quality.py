from __future__ import annotations

from src.core.tiktok_aino import generate_from_schedule, pipeline, schedule_planner


def _manifest(location: str, camera: str, prop: str, treatment: str) -> dict:
    return {
        "layout_quality": {
            "mode": "native_image_text_scene_signature",
            "layout_ids": [f"layout-{index}" for index in range(1, 10)],
            "unique_count": 9,
        },
        "visual_assets": [
            {
                "scene_id": index,
                "visual_brief": {
                    "role": "evidence",
                    "location": location,
                    "camera": camera,
                    "foreground_prop": prop,
                    "treatment_id": treatment,
                    "diegetic_text": f"card {index}",
                },
            }
            for index in range(1, 10)
        ],
    }


def test_manifest_visual_signature_exposes_repeated_scene_language() -> None:
    signature = generate_from_schedule._manifest_visual_signature(
        _manifest("same hallway", "same low angle", "same paper", "same tableau")
    )

    assert signature["scene_count"] == 9
    assert signature["unique_locations"] == 1
    assert signature["unique_cameras"] == 1
    assert signature["unique_props"] == 1
    assert signature["layout_unique_count"] == 9


def test_batch_visual_signature_issues_block_repeated_thumbnail_language() -> None:
    signature = generate_from_schedule._manifest_visual_signature(
        _manifest("same hallway", "same low angle", "same paper", "same tableau")
    )
    results = [
        {"run_id": "run_a", "visual_signature": signature},
        {"run_id": "run_b", "visual_signature": signature},
    ]

    issues = generate_from_schedule._batch_visual_signature_issues(results)
    issue_codes = {issue["issue"] for issue in issues}

    assert "intra_post_location_repetition" in issue_codes
    assert "intra_post_camera_repetition" in issue_codes
    assert "intra_post_prop_repetition" in issue_codes
    assert "intra_post_treatment_repetition" in issue_codes
    assert "cross_post_first_frame_duplicate" in issue_codes


def test_generate_from_plan_all_days_selects_more_than_start_day(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        """
{
  "start_day": "2026-06-08",
  "slots": [
    {"publish_at_local": "2026-06-08T08:10:00+09:00", "ready_for_generation": true},
    {"publish_at_local": "2026-06-08T11:20:00+09:00", "ready_for_generation": true},
    {"publish_at_local": "2026-06-09T08:10:00+09:00", "ready_for_generation": true}
  ]
}
""",
        encoding="utf-8",
    )

    first_day = generate_from_schedule.generate_from_plan(plan_path, dry_run=True, limit=9)
    all_days = generate_from_schedule.generate_from_plan(plan_path, dry_run=True, limit=9, all_days=True)

    assert first_day["target_date"] == "2026-06-08"
    assert first_day["selected_count"] == 2
    assert all_days["target_date"] == "all"
    assert all_days["selected_count"] == 3


def test_upload_validation_blocks_broken_question_mark_script_metadata(tmp_path) -> None:
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
        "fact_pack": {"gate_passed": True},
        "risk_flags": {"gate_passed": True},
        "source_card": {"gate_passed": True},
        "reference_fit": {"gate_passed": True},
        "angle_brief": {"gate_passed": True},
        "storyboard_brief": {"gate_passed": True},
        "tts_performance_plan": {"gate_passed": True},
        "script": {
            "title": "?? vs ??, ?? ?????",
            "caption": "?? vs ??, ?? ??? ?? ? ?????.",
            "post_title": "?? vs ??, ?? ?????",
            "post_body": "??? ??? 1?? ??? ??? ? ??? ?? ??.",
            "pinned_comment": "1 ??? ??, 2 ??? ??, 3 ? ?? ?.",
            "narration": "정상 한국어 내레이션입니다.",
            "hashtags": ["??", "????"],
            "scenes": [
                {"scene_id": index, "body": "검수 가능한 한국어 본문입니다", "on_screen_text": "검수 카드 문구"}
                for index in range(1, 10)
            ],
        },
        "artifacts": {
            "mp4": str(mp4),
            "fact_pack": "fact_pack.json",
            "risk_flags": "risk_flags.json",
            "source_card": "source_card.json",
            "reference_fit": "reference_fit.json",
            "angle_brief": "angle_brief.json",
            "storyboard_brief": "storyboard_brief.json",
            "tts_performance_plan": "tts_performance_plan.json",
        },
    }

    validation = pipeline.validate_manifest_for_upload(manifest)

    assert validation["upload_ready"] is False
    assert "script.title:korean_text_missing" in validation["technical_blockers"]
    assert "script.caption:question_mark_noise" in validation["technical_blockers"]
    assert "script.hashtags:korean_text_missing" in validation["technical_blockers"]


def test_contrasting_fates_reference_metadata_uses_short_comment_caption() -> None:
    topic = pipeline.TopicCandidate(
        title="엇갈린 운명: 이재명은 1주년 비전, 윤석열은 특검 조사",
        angle="비전과 책임선 대비",
        slot="curated",
        target_duration_sec=87,
        claims=[pipeline.Claim("이재명 대통령은 취임 1주년 기자회견에서 4대 국정목표를 제시했다.", ["source"])],
        source_ids=["source"],
    )
    fact_item = pipeline.FactPackItem(
        fact_id="f1",
        item_type="confirmed",
        text="이재명 대통령은 취임 1주년 기자회견에서 4대 국정목표를 제시했다.",
        source_ids=["source"],
        confidence="high",
        risk="low",
        usage_guidance="confirmed fact",
    )
    fact_pack = pipeline.FactPack(
        version="fact_pack_v1",
        topic_title=topic.title,
        generated_at="2026-06-08T00:00:00+09:00",
        source_count=1,
        trusted_source_count=1,
        source_roles={},
        confirmed_facts=[fact_item],
        reported_claims=[],
        counterpoints=[],
        unanswered_questions=[],
        risk_phrases_to_avoid=[],
        gate_passed=True,
    )
    angle_brief = pipeline.AngleBrief(
        version="angle_brief_v1",
        topic_title=topic.title,
        format_id="reward_deep",
        viewer_promise="비전과 책임선을 대비한다.",
        one_sentence_thesis="비전과 책임선을 대비한다.",
        audience_emotion="논쟁",
        share_reason="댓글이 갈릴 장면입니다.",
        comment_question="당신은 어느 장면인가요?",
        follow_reason="후속 흐름까지 추적합니다.",
        safe_provocation="비전과 책임선이 부딪힌 장면입니다.",
        forbidden_angle="확정되지 않은 혐의 단정",
        source_fact_ids=["f1"],
        gate_passed=True,
    )

    profile = pipeline._reference_post_metadata_profile("비전 vs 특검, 누가 불편한가?", topic, fact_pack, angle_brief)

    assert "같은 주간에 나온 두 장면" in profile["caption_body"]
    assert "1 비전의 시간" in profile["caption_body"]
    assert "해당 이미지는 생성 이미지입니다" in profile["caption_body"]
    assert "숫자와 해석을 분리합니다" not in profile["caption_body"]
    assert len(profile["caption_body"]) <= 240


def test_schedule_topic_candidate_reframes_raw_partisan_headline() -> None:
    row = {
        "title": "최보윤 국민의힘 대변인, 선관위 개혁·방탄특검 저지 촉구",
        "publisher": "브레이크뉴스",
        "url": "https://example.com/source",
        "query": "국민의힘 선관위 특검",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }
    support = [
        {
            "title": "선관위 질타한 민주당, 국민의힘 재선거 주장엔 정치공세",
            "publisher": "경향신문",
            "url": "https://example.com/support",
            "query": "국민의힘 선관위 특검",
            "published_at": "2026-06-07T00:00:00+00:00",
            "score": 90,
        }
    ]

    topic, sources = schedule_planner._topic_from_candidate(row, 1, support)

    assert topic.title == "선관위 특검론, 책임 규명인가 정치공세인가?"
    assert "책임 규명" in topic.angle
    assert "최보윤 국민의힘 대변인" in topic.claims[0].text
    assert "최보윤 국민의힘 대변인" in sources["hot_news_plan_01"].title
    assert "framing_rule=election_admin_frame:special_probe" in sources["hot_news_plan_01"].note


def test_schedule_framing_prefers_primary_topic_over_supporting_rows() -> None:
    row = {
        "title": "이재명 대통령, 친일 반민족 행위자 재산 조사해 환수",
        "publisher": "한경매거진",
        "url": "https://example.com/source",
        "query": "이재명 책임",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }
    support = [
        {
            "title": "선관위 투표용지 부족 사태 파장에 책임 물어야",
            "publisher": "한겨레",
            "url": "https://example.com/support",
            "query": "이재명 책임",
            "published_at": "2026-06-07T00:00:00+00:00",
            "score": 90,
        }
    ]

    topic, sources = schedule_planner._topic_from_candidate(row, 2, support)

    assert topic.title == "친일 부당재산 환수, 왜 다시 꺼냈나?"
    assert "선관위" not in topic.title
    assert "역사 책임" in topic.angle
    assert "framing_rule=pro_japan_asset_recovery:asset_recovery" in sources["hot_news_plan_02"].note


def test_schedule_framing_selects_specific_rule_over_generic_special_prosecutor() -> None:
    row = {
        "title": "국정조사 필요 한목소리 냈지만 여 원 구성부터 야 특검해야",
        "publisher": "KBS",
        "url": "https://example.com/source",
        "query": "특검",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }

    topic, sources = schedule_planner._topic_from_candidate(row, 3, [])

    assert topic.title == "국정조사와 특검, 책임 규명은 어디서 갈리나?"
    assert "책임 규명 경로" in topic.angle
    assert "framing_rule=national_investigation_vs_special_prosecutor:both_paths" in sources["hot_news_plan_03"].note


def test_schedule_supporting_rows_keep_same_admin_issue_for_trusted_primary() -> None:
    row = {
        "title": "유정복 인천시장 투표용지 부족 이 대통령 사과 선관위 해체",
        "publisher": "연합뉴스",
        "url": "https://example.com/source",
        "query": "이재명 책임",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }
    support = {
        "title": "이 대통령 선거 관리 허점 책임 물어야 선관위 질타",
        "publisher": "한겨레",
        "url": "https://example.com/support",
        "query": "선거 대선",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 90,
    }

    assert schedule_planner._supporting_rows(row, [row, support]) == [support]


def test_schedule_supporting_rows_reject_actor_only_issue_overlap() -> None:
    row = {
        "title": "이재명 대통령 친일 반민족 행위자 재산 조사해 환수",
        "publisher": "한경매거진",
        "url": "https://example.com/source",
        "query": "이재명 책임",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }
    unrelated = {
        "title": "선관위 투표용지 부족 사태 파장에 이재명 대통령 책임 물어야",
        "publisher": "한국NGO신문",
        "url": "https://example.com/support",
        "query": "이재명 책임",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 90,
    }

    assert schedule_planner._supporting_rows(row, [row, unrelated]) == []


def test_schedule_supporting_rows_reject_untrusted_special_probe_without_same_variant() -> None:
    row = {
        "title": "최보윤 국민의힘 대변인 선관위 개혁 방탄특검 저지 촉구",
        "publisher": "브레이크뉴스",
        "url": "https://example.com/source",
        "query": "선관위 특검",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 100,
    }
    broad_support = {
        "title": "선거 관리 허점 책임 물어야 선관위 질타",
        "publisher": "한겨레",
        "url": "https://example.com/support",
        "query": "선거 대선",
        "published_at": "2026-06-07T00:00:00+00:00",
        "score": 90,
    }

    assert schedule_planner._supporting_rows(row, [row, broad_support]) == []


def test_schedule_election_gate_blocks_action_not_admin_issue() -> None:
    assert schedule_planner._contains_direct_election_action("내일 꼭 투표하자")
    assert not schedule_planner._contains_direct_election_action("투표용지 부족, 책임 추궁인가 음모론인가?")
    assert schedule_planner._has_public_accountability_frame("재선거 주장, 근거는 어디까지 있나?")
    assert schedule_planner._has_public_accountability_frame("부정선거 프레임, 누가 키우나?")


def test_planned_title_duplicate_gate_allows_distinct_special_prosecutor_topics() -> None:
    existing = ["선관위 특검론, 책임 규명인가 정치공세인가?"]

    assert not schedule_planner._is_duplicate_planned_title(
        "윤석열 특검 조사, 책임선은 어디까지인가?",
        existing,
    )
    assert schedule_planner._is_duplicate_planned_title(
        "선관위 특검론, 책임 규명인가 정치공세인가?",
        existing,
    )


def test_schedule_duplicate_gate_does_not_collapse_distinct_topics_on_generic_responsibility() -> None:
    assert not schedule_planner._is_duplicate_topic(
        "선관위 허점, 책임은 어디까지인가?",
        ["윤석열 특검 조사, 책임선은 어디까지인가?"],
    )


def test_schedule_duplicate_gate_does_not_collapse_distinct_special_probe_actors() -> None:
    assert not schedule_planner._is_duplicate_topic(
        "김건희 특검, 다음 책임선은 어디인가?",
        ["윤석열 특검 조사, 책임선은 어디까지인가?"],
    )


def test_configured_hook_headline_replaces_repetitive_issue_fallback() -> None:
    topic = pipeline.TopicCandidate(
        title="국정조사와 특검, 책임 규명은 어디서 갈리나?",
        angle="책임 규명 경로와 지연 가능성 비교",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )

    assert pipeline._custom_issue_hook_headline(topic) == "국정조사냐 특검이냐?"


def test_reference_post_title_uses_configured_hot_hook_before_generic_primary_term() -> None:
    topic = pipeline.TopicCandidate(
        title="선관위 허점, 책임은 어디까지인가?",
        angle="선거 관리 허점과 책임선",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )

    assert pipeline._reference_unique_post_title("generic hook", topic, {}) == "선관위 허점, 누가 책임지나?"


def test_visual_location_prioritizes_role_location_before_issue_context() -> None:
    location = pipeline._visual_location_for_role_issue(
        "evidence",
        "election_frame",
        {"location": "document comparison table in a quiet editorial room"},
        {"location": "election-frame war room or debate monitoring booth"},
    )

    assert location.startswith("document comparison table")
    assert "tied to election-frame war room" in location


def test_metadata_caption_uses_topic_specific_profile_instead_of_generic_body() -> None:
    topic = pipeline.TopicCandidate(
        title="투표용지 부족, 책임 추궁인가 음모론인가?",
        angle="선거 행정 책임과 음모론 경계를 분리",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )
    script = pipeline.ScriptPackage(
        title="투표용지 부족",
        caption="",
        hashtags=["정치"],
        post_title="투표용지 부족, 단순 실수였나?",
        post_body="",
        pinned_comment="",
        narration="",
        scenes=[],
        target_duration_sec=75,
        sources=[],
        disclosure="해당 이미지는 생성된 이미지입니다.",
        variant_id="hot_issue_growth_short",
    )

    enriched = pipeline._enrich_post_metadata(script, topic, {})

    assert "절차 신뢰" in enriched.caption
    assert "핵심은 누가 이겼냐" not in enriched.caption


def test_metadata_caption_keeps_kim_special_probe_out_of_generic_trial_template() -> None:
    topic = pipeline.TopicCandidate(
        title="김건희 특검, 다음 책임선은 어디인가?",
        angle="김건희 특검 수사 범위와 반론을 분리",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[
            pipeline.Claim(
                text="MBC 뉴스 보도 제목 기준: 내란 가담·김건희 수사 청탁 관련 1심 선고 연기",
                source_ids=["s1"],
                risk="medium",
            )
        ],
        source_ids=["s1"],
    )
    script = pipeline.ScriptPackage(
        title="김건희 특검",
        caption="",
        hashtags=["정치"],
        post_title=pipeline._custom_issue_hook_headline(topic),
        post_body="",
        pinned_comment="",
        narration="",
        scenes=[],
        target_duration_sec=75,
        sources=[],
        disclosure="해당 이미지는 생성된 이미지입니다.",
        variant_id="hot_issue_reward",
    )

    enriched = pipeline._enrich_post_metadata(script, topic, {})

    assert enriched.post_title == "김건희 특검, 윗선은 어디까지?"
    assert "수사 범위" in enriched.caption
    assert "위증 쟁점" not in enriched.caption


def test_topic_from_ready_slot_preserves_planned_multi_source_gate() -> None:
    slot = {
        "ready_for_generation": True,
        "source_count": 3,
        "sources": [
            {
                "source_id": "s1",
                "title": "YTN: 윤석열, 6시간 특검 조사",
                "url": "https://example.com/1",
            },
            {
                "source_id": "s2",
                "title": "KBS 뉴스: 종합특검 첫 소환 조사",
                "url": "https://example.com/2",
            },
            {
                "source_id": "s3",
                "title": "경향신문: 계엄 정당화 메시지 지시 혐의 조사",
                "url": "https://example.com/3",
            },
        ],
        "topic_candidate": {
            "title": "윤석열 특검 조사, 책임선은 어디까지인가?",
            "angle": "특검 조사 책임선과 남은 쟁점을 분리",
            "slot": "hot discovery",
            "target_duration_sec": 75,
            "source_ids": ["s1", "s2", "s3"],
            "claims": [
                {
                    "text": "YTN 보도 기준 윤석열 특검 조사가 진행됐다고 전한다.",
                    "source_ids": ["s1"],
                    "risk": "medium",
                }
            ],
        },
    }

    topic, sources = generate_from_schedule._topic_from_slot(slot, 1)

    assert topic.source_ids == ["s1", "s2", "s3"]
    assert sorted(sources) == ["s1", "s2", "s3"]
    assert any(set(claim.source_ids) == {"s1", "s2", "s3"} for claim in topic.claims)


def test_reference_opening_scene_changes_by_topic_instead_of_reusing_press_scrum() -> None:
    kim_scene = pipeline._reference_visual_scene(
        "street_speech_closeup",
        "hook",
        "김건희 특검, 다음 책임선은 어디인가?",
        "MBC 뉴스 기준",
        0,
    )
    asset_scene = pipeline._reference_visual_scene(
        "street_speech_closeup",
        "hook",
        "친일 부당재산 환수, 왜 다시 꺼냈나?",
        "연합뉴스 기준",
        0,
    )

    assert kim_scene != asset_scene
    assert "street press-scrum" not in kim_scene
    assert "street press-scrum" not in asset_scene
    assert "luxury-receipt evidence" in kim_scene
    assert "archive-vault ledger" in asset_scene


def test_reference_visual_scene_includes_scene_focus_for_image_alignment() -> None:
    visual = pipeline._reference_visual_scene(
        "document_receipt_desk",
        "evidence",
        "국정조사와 특검, 책임 규명은 어디서 갈리나?",
        "YTN 기준",
        2,
        scene_focus="특검은 뭐가 다른가; 특검은 수사 권한과 강제력이 핵심입니다.",
    )

    assert "scene focus:" in visual
    assert "특검은 뭐가 다른가" in visual
    assert "수사 권한" in visual


def test_topic_specific_visual_rules_override_generic_reference_scene() -> None:
    cases = [
        (
            "팩트 조작, 언론 자유인가?",
            "media_accountability",
            "press-room corridor",
        ),
        (
            "국정조사 요구, 진상규명인가 시간끌기인가?",
            "national_assembly",
            "committee corridor",
        ),
        (
            "평화공존, 순진한 말인가 현실 전략인가?",
            "peace_security",
            "border-observation",
        ),
    ]
    for title, expected_issue_type, expected_scene_marker in cases:
        topic = pipeline.TopicCandidate(
            title=title,
            angle="",
            slot="hot discovery",
            target_duration_sec=75,
            claims=[],
            source_ids=[],
        )
        scene = pipeline.Scene(
            scene_id=1,
            duration_sec=8,
            title="훅",
            body="테스트 본문",
            visual="reference_scene: night editorial desk with three evidence packets",
            on_screen_text=title,
        )

        brief = pipeline._build_visual_brief(topic, scene, 0, 9)

        assert brief.issue_type == expected_issue_type
        assert expected_scene_marker in brief.concrete_scene
        assert "night editorial desk" not in brief.concrete_scene


def test_topic_anchor_terms_normalize_korean_case_particles() -> None:
    topic = pipeline.TopicCandidate(
        title="국정조사와 특검, 책임 규명은 어디서 갈리나?",
        angle="국정조사와 특검을 책임 규명 경로로 비교한다.",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )

    anchors = pipeline._topic_scene_anchor_terms(topic, {})

    assert "국정조사" in anchors
    assert "규명" in anchors
    assert "국정조사와" not in anchors
    assert "규명은" not in anchors


def test_national_investigation_only_storyboard_preserves_party_anchors() -> None:
    base_rows = [
        {"title": "훅", "screen": "기본 훅", "body": "기본 본문", "role": "hook"},
        {"title": "출처", "screen": "출처부터 확인하자", "body": "기본 출처", "role": "why_now"},
        {"title": "자료", "screen": "자료가 말한 지점", "body": "기본 자료", "role": "evidence"},
        {"title": "빈칸", "screen": "아직 남은 빈칸", "body": "기본 빈칸", "role": "verification"},
        {"title": "프레임", "screen": "프레임이 갈린다", "body": "기본 프레임", "role": "criteria"},
        {"title": "기준", "screen": "세 가지 판단 기준", "body": "기본 기준", "role": "criteria"},
        {"title": "책임", "screen": "책임은 어디까지?", "body": "기본 책임", "role": "responsibility"},
        {"title": "저장", "screen": "출처 반론 기록 저장", "body": "기본 저장", "role": "verification"},
        {"title": "판정", "screen": "당신의 기준은?", "body": "기본 판정", "role": "cta"},
    ]
    topic = pipeline.TopicCandidate(
        title="국정조사 요구, 진상규명인가 시간끌기인가?",
        angle="국정조사 요구를 진상규명 경로, 정치적 계산, 반론 가능성으로 나눈다.",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )
    rows = pipeline._reference_story_rows_from_strategy(
        topic,
        base_rows,
        {
            "topic_title": topic.title,
            "post_title": "국정조사, 누가 시간 끄나?",
            "claim": "YTN 보도 기준 국정조사 시동",
            "counter": "정치공세 반론도 남아 있다.",
            "open_question": "책임 규명 경로가 어디서 갈리는지 봐야 한다.",
            "comment_question": "어느 경로가 맞나?",
            "source_line": "YTN 기준",
        },
    )

    assert rows[1]["screen"] == "민주당과 국민의힘 계산"
    assert "민주당" in rows[1]["body"]
    assert "국민의힘" in rows[1]["body"]


def test_long_custom_body_is_compacted_instead_of_generic_suffix() -> None:
    body = "언론 자유는 권력 감시의 방패입니다. 그런데 사실을 비틀어도 책임이 없다는 말로 쓰이면 방패가 핑계가 됩니다."

    compacted = pipeline._readable_custom_body_text(body, body_max=46, final_scene=False)

    assert "핵심은 근거와 책임선입니다" not in compacted
    assert "언론 자유" in compacted
    assert len(compacted) <= 46


def test_peace_security_hook_scores_as_safe_provocation() -> None:
    scenes = [
        pipeline.Scene(
            1,
            9,
            "안보 훅",
            "강경한 말은 시원합니다. 그런데 안보는 시원함보다 전쟁 비용 계산입니다.",
            "border observation room",
            "평화공존, 순진한가?",
        )
    ]
    script = pipeline.ScriptPackage(
        title="평화공존, 순진한가?",
        caption="평화공존과 안보 비용을 나눠 봅니다.",
        hashtags=["정치", "안보", "평화"],
        post_title="평화공존, 순진한가?",
        post_body="평화공존 발언을 안보 실익과 강경론 반론으로 나눕니다.",
        pinned_comment="1 현실 전략, 2 너무 순진함, 3 조건부 대화?",
        narration="\n".join(scene.body for scene in scenes),
        scenes=scenes,
        target_duration_sec=75,
        sources=["s1"],
        disclosure="AI-generated content disclosure required",
        variant_id="peace_security",
    )

    assert pipeline._score_safe_provocation(script) >= 70


def test_reference_storyboard_strategy_varies_repeated_middle_cards_by_topic() -> None:
    base_rows = [
        {"title": "훅", "screen": "기본 훅", "body": "기본 본문", "role": "hook"},
        {"title": "출처", "screen": "출처부터 확인하자", "body": "기본 출처", "role": "why_now"},
        {"title": "자료", "screen": "자료가 말한 지점", "body": "기본 자료", "role": "evidence"},
        {"title": "빈칸", "screen": "아직 남은 빈칸", "body": "기본 빈칸", "role": "verification"},
        {"title": "프레임", "screen": "프레임이 갈린다", "body": "기본 프레임", "role": "criteria"},
        {"title": "기준", "screen": "세 가지 판단 기준", "body": "기본 기준", "role": "criteria"},
        {"title": "책임", "screen": "책임은 어디까지?", "body": "기본 책임", "role": "responsibility"},
        {"title": "저장", "screen": "출처 반론 기록 저장", "body": "기본 저장", "role": "verification"},
        {"title": "판정", "screen": "당신의 기준은?", "body": "기본 판정", "role": "cta"},
    ]
    values = {
        "topic_title": "국정조사와 특검, 책임 규명은 어디서 갈리나?",
        "post_title": "국정조사냐 특검이냐?",
        "claim": "YTN 보도 기준 국정조사와 특검 책임 공방이 가열됐다.",
        "counter": "정치공세 반론도 남아 있다.",
        "open_question": "책임 규명 경로가 어디서 갈리는지 봐야 한다.",
        "comment_question": "어느 경로가 맞나?",
        "source_line": "YTN 기준",
    }
    national_topic = pipeline.TopicCandidate(
        title="국정조사와 특검, 책임 규명은 어디서 갈리나?",
        angle="국정조사와 특검을 책임 규명 경로로 비교한다.",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )
    kim_topic = pipeline.TopicCandidate(
        title="김건희 특검, 다음 책임선은 어디인가?",
        angle="김건희 특검 책임선",
        slot="hot discovery",
        target_duration_sec=75,
        claims=[],
        source_ids=[],
    )

    national_rows = pipeline._reference_story_rows_from_strategy(national_topic, base_rows, values)
    kim_rows = pipeline._reference_story_rows_from_strategy(kim_topic, base_rows, values | {"post_title": "김건희 특검, 윗선은 어디까지?"})

    assert [row["screen"] for row in national_rows[1:5]] == [
        "국정조사는 뭘 하나",
        "특검은 뭐가 다른가",
        "원 구성부터 갈림",
        "요구서가 의미하는 것",
    ]
    assert [row["screen"] for row in kim_rows[1:5]] == [
        "22일 선고 변수",
        "수사 청탁 쟁점",
        "김건희·심우정 책임선",
        "정치공세 반론은?",
    ]
    assert national_rows[2]["screen"] != kim_rows[2]["screen"]
