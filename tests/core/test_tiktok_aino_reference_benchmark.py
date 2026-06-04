from __future__ import annotations

from src.core.tiktok_aino import reference_benchmark


FIELDS = reference_benchmark.REQUIRED_FIELDS


def _row(index: int, platform: str, url: str) -> dict[str, str]:
    return {
        "id": f"R{index:03d}",
        "platform": platform,
        "url": url,
        "channel_name": f"reference channel {index}",
        "post_date": "2026-05-01",
        "topic": "civic accountability issue",
        "political_context": "중립뉴스",
        "format_type": "evidence_briefing",
        "duration_sec": "42",
        "views": "123000",
        "likes": "1200",
        "comments": "300",
        "first_1s_hook": "document close-up",
        "first_3s_hook": "source and claim boundary",
        "first_5s_hook": "date, place, and public consequence",
        "source_card_position": "0~2초",
        "evidence_type": "언론보도",
        "scene_types": "document card, newsroom",
        "cut_count_estimate": "8",
        "caption_density": "높음 14자",
        "visual_style": "실사뉴스",
        "voice_style": "진행자",
        "cta_type": "저장",
        "trust_signal": "source, date, quote",
        "risk_signal": "low",
        "why_it_worked": "fast source-backed tension",
        "aino_applicability": "적용 가능",
        "pipeline_rule": "require source card in opening seconds",
    }


def _passing_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(1, 9):
        rows.append(_row(index, "TikTok", f"https://www.tiktok.com/@ref{index}/video/70000000000000000{index}"))
    for index in range(9, 17):
        rows.append(_row(index, "YouTube Shorts", f"https://www.youtube.com/shorts/ref{index}"))
    for index in range(17, 21):
        rows.append(_row(index, "Instagram Reels", f"https://www.instagram.com/reel/ref{index}/"))
    return rows


def _markdown_table(rows: list[dict[str, str]]) -> str:
    header = "| " + " | ".join(FIELDS) + " |"
    separator = "| " + " | ".join("---" for _ in FIELDS) + " |"
    body = ["| " + " | ".join(row[field] for field in FIELDS) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def test_url_backed_benchmark_passes_when_requirements_are_met() -> None:
    validation = reference_benchmark.validate_benchmark_rows(_passing_rows())

    assert validation.passed is True
    assert validation.blockers == []
    assert validation.platform_counts["tiktok"] == 8
    assert validation.platform_counts["youtube_shorts"] == 8
    assert validation.platform_counts["instagram_reels"] == 4


def test_markdown_table_parser_extracts_benchmark_rows() -> None:
    rows = reference_benchmark.parse_markdown_benchmark_table(_markdown_table(_passing_rows()))

    validation = reference_benchmark.validate_benchmark_rows(rows)

    assert len(rows) == 20
    assert validation.passed is True


def test_report_without_direct_url_table_fails_collection_gate() -> None:
    text = """
| 후보 id | 채널 또는 원출처 | 공개적으로 확인된 사건 |
|---|---|---|
| C01 | news channel | channel-only candidate |
"""

    rows = reference_benchmark.parse_markdown_benchmark_table(text)
    validation = reference_benchmark.validate_benchmark_rows(rows)

    assert rows == []
    assert validation.passed is False
    assert "url_rows_lt_20" in validation.blockers
    assert "tiktok_rows_lt_8" in validation.blockers
    assert "youtube_shorts_rows_lt_8" in validation.blockers


def test_unknown_url_and_missing_hook_fail_row_level_validation() -> None:
    rows = _passing_rows()
    rows[0] = {**rows[0], "url": "확인 불가", "first_3s_hook": "확인 불가"}

    validation = reference_benchmark.validate_benchmark_rows(rows)
    errors = {(error.row_id, error.field, error.code) for error in validation.row_errors}

    assert validation.passed is False
    assert "row_level_validation_failed" in validation.blockers
    assert ("R001", "url", "url_required") in errors
    assert ("R001", "first_3s_hook", "critical_coding_required") in errors


def test_url_with_deep_research_citation_text_fails_validation() -> None:
    rows = _passing_rows()
    rows[0] = {**rows[0], "url": rows[0]["url"] + " citeturn1view0"}

    validation = reference_benchmark.validate_benchmark_rows(rows)

    assert validation.passed is False
    assert any(error.code == "url_contains_non_url_text" for error in validation.row_errors)


def test_youtube_watch_url_is_not_accepted_as_shorts_reference() -> None:
    rows = _passing_rows()
    rows[8] = {**rows[8], "platform": "YouTube", "url": "https://www.youtube.com/watch?v=abc123"}

    validation = reference_benchmark.validate_benchmark_rows(rows)

    assert validation.passed is False
    assert any(error.code == "url_platform_mismatch" for error in validation.row_errors)


def test_duplicate_url_fails_validation() -> None:
    rows = _passing_rows()
    rows[1] = {**rows[1], "url": rows[0]["url"]}

    validation = reference_benchmark.validate_benchmark_rows(rows)

    assert validation.passed is False
    assert any(error.code == "duplicate_url" for error in validation.row_errors)


def test_failed_url_collection_marker_blocks_file(tmp_path) -> None:
    path = tmp_path / "benchmark.md"
    path.write_text("# FAILED_URL_COLLECTION\n\n" + _markdown_table(_passing_rows()), encoding="utf-8")

    validation = reference_benchmark.validate_benchmark_file(path)

    assert validation.passed is False
    assert validation.blockers[0] == "failed_url_collection_marker"
