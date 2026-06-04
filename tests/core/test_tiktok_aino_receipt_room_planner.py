from src.core.tiktok_aino import receipt_room_planner as planner


def _strong_candidate() -> planner.IssueCandidate:
    return planner.candidate_from_dict(
        {
            "title": "The red carpet run-in that split the internet",
            "summary": "A short public clip became a global fan debate about whether the greeting was awkward or over-read.",
            "entities": ["Taylor Swift", "Travis Kelce"],
            "source_ids": ["people", "vogue_trend_tracker", "tiktok_creative_center"],
            "keywords": ["red carpet", "awkward", "ex", "fan theory", "what happened", "receipt"],
            "trend_signals": {
                "trend_velocity": 90,
                "fandom_conflict": 92,
                "visual_drama": 90,
                "microdrama_fit": 88,
                "search_intent": 84,
                "freshness": 86,
                "originality": 72,
            },
            "claims": [
                {
                    "text": "The public appearance was reported by entertainment media.",
                    "evidence_level": "reported",
                    "sensitivity": "ordinary",
                    "source_ids": ["people"],
                },
                {
                    "text": "Fans argued about whether the greeting looked awkward.",
                    "evidence_level": "fan_speculation",
                    "sensitivity": "ordinary",
                    "source_ids": ["tiktok_creative_center"],
                },
            ],
        }
    )


def test_strong_candidate_produces_symbolic_video_plan() -> None:
    candidate = _strong_candidate()

    plan = planner.plan_episode(candidate)

    assert plan["decision"] == "greenlight"
    assert plan["scorecard"]["total"] >= plan["scorecard"]["decision_floor"]
    assert plan["roast_gate"]["passed"]
    prompts = " ".join(shot["visual_prompt"] for shot in plan["shot_list"])
    assert "Taylor Swift" not in prompts
    assert "Travis Kelce" not in prompts
    assert all(shot["motion"] for shot in plan["shot_list"])
    pop_queen = next(character for character in plan["characters"] if character["screen_character"] == "The Pop Queen")
    assert pop_queen["presentation"] == "female_glamour"
    assert "fitted" in pop_queen["reference_style_rules"]
    assert "Creative direction" in pop_queen["reference_style_rules"]
    assert "fictionalized features" in pop_queen["reference_style_rules"]
    assert "Blocked:" not in pop_queen["reference_style_rules"]


def test_unverified_sensitive_claim_is_blocked() -> None:
    candidate = planner.candidate_from_dict(
        {
            "title": "Fans claim a singer is pregnant after one photo",
            "summary": "The issue is based only on social comments and no verified report.",
            "entities": ["Famous Singer"],
            "source_ids": ["x_social", "reddit_popculture"],
            "keywords": ["pregnant", "fan theory"],
            "trend_signals": {
                "trend_velocity": 80,
                "fandom_conflict": 90,
                "visual_drama": 70,
                "microdrama_fit": 75,
                "search_intent": 85,
                "freshness": 80,
            },
            "claims": [
                {
                    "text": "Fans say the singer is pregnant based on one photo.",
                    "evidence_level": "rumor",
                    "sensitivity": "pregnancy",
                    "source_ids": ["x_social"],
                }
            ],
        }
    )

    plan = planner.plan_episode(candidate)

    assert plan["decision"] == "blocked"
    assert "unsupported_sensitive_claim" in plan["risk"]["hard_blockers"]


def test_low_signal_social_only_candidate_is_not_greenlit() -> None:
    candidate = planner.candidate_from_dict(
        {
            "title": "A vague celebrity like got noticed",
            "summary": "One post got a few comments without a reliable report or strong visual moment.",
            "entities": ["Celebrity"],
            "source_ids": ["reddit_popculture"],
            "keywords": ["like", "maybe"],
            "trend_signals": {
                "trend_velocity": 20,
                "fandom_conflict": 25,
                "visual_drama": 15,
                "microdrama_fit": 20,
                "search_intent": 18,
                "freshness": 35,
            },
            "claims": [
                {
                    "text": "A fan noticed a social like.",
                    "evidence_level": "fan_speculation",
                    "sensitivity": "ordinary",
                    "source_ids": ["reddit_popculture"],
                }
            ],
        }
    )

    plan = planner.plan_episode(candidate)

    assert plan["decision"] == "revise"
    assert plan["scorecard"]["total"] < plan["scorecard"]["decision_floor"]


def test_roast_gate_rejects_static_or_name_leaking_plan() -> None:
    candidate = _strong_candidate()
    plan = planner.plan_episode(candidate)
    bad_plan = dict(plan)
    bad_plan["shot_list"] = [
        {
            "shot_id": 1,
            "beat": "cold_open",
            "duration_sec": 4,
            "visual_prompt": "Taylor Swift stands still in a realistic scene.",
            "motion": "",
            "evidence_boundary": "commentary",
        }
    ]

    result = planner.roast_gate(bad_plan)

    assert not result["passed"]
    assert "static_shot_found" in result["blockers"]
    assert "real_name_leaked_to_visual_prompt" in result["blockers"]
