"""Validation helpers for URL-backed short-form reference benchmarks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_FIELDS = [
    "id",
    "platform",
    "url",
    "channel_name",
    "post_date",
    "topic",
    "political_context",
    "format_type",
    "duration_sec",
    "views",
    "likes",
    "comments",
    "first_1s_hook",
    "first_3s_hook",
    "first_5s_hook",
    "source_card_position",
    "evidence_type",
    "scene_types",
    "cut_count_estimate",
    "caption_density",
    "visual_style",
    "voice_style",
    "cta_type",
    "trust_signal",
    "risk_signal",
    "why_it_worked",
    "aino_applicability",
    "pipeline_rule",
]

CRITICAL_CODED_FIELDS = [
    "format_type",
    "first_1s_hook",
    "first_3s_hook",
    "first_5s_hook",
    "scene_types",
    "caption_density",
    "visual_style",
    "voice_style",
    "cta_type",
    "trust_signal",
    "risk_signal",
    "why_it_worked",
    "aino_applicability",
    "pipeline_rule",
]

FORMAT_TYPES = {
    "news_clip",
    "evidence_briefing",
    "timeline_explainer",
    "satire_character",
    "comment_battle",
    "fact_check",
    "hybrid",
}

UNKNOWN_MARKERS = {"", "-", "n/a", "na", "unknown", "unknown.", "확인 불가"}
AINO_APPLICABILITY = {"적용 가능", "수정 후 가능", "부적합", "applicable", "conditional", "not_applicable"}
HEADER_ALIASES = {
    "플랫폼": "platform",
    "링크": "url",
    "채널명": "channel_name",
    "게시일": "post_date",
    "주제": "topic",
    "길이": "duration_sec",
    "조회수": "views",
    "좋아요": "likes",
    "댓글": "comments",
}


@dataclass
class BenchmarkRowError:
    row_id: str
    field: str
    code: str
    value: str = ""


@dataclass
class BenchmarkValidation:
    passed: bool
    status: str
    row_count: int
    platform_counts: dict[str, int]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_errors: list[BenchmarkRowError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["row_errors"] = [asdict(error) for error in self.row_errors]
        return payload


def _canonical_header(header: str) -> str:
    value = header.strip().strip("`").lower()
    value = re.sub(r"\s+", "_", value)
    return HEADER_ALIASES.get(value, value)


def _clean_cell(value: str) -> str:
    return value.replace("<br>", " ").replace("<br/>", " ").strip().strip("`")


def _split_markdown_row(line: str) -> list[str]:
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [_clean_cell(cell) for cell in row.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_markdown_benchmark_table(text: str) -> list[dict[str, str]]:
    """Extract the first markdown table with id, platform, and url columns."""

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "|" not in line:
            continue
        headers = [_canonical_header(cell) for cell in _split_markdown_row(line)]
        if not {"id", "platform", "url"}.issubset(set(headers)):
            continue
        if index + 1 >= len(lines):
            continue
        separator = _split_markdown_row(lines[index + 1])
        if not _is_separator_row(separator):
            continue
        rows: list[dict[str, str]] = []
        for body_line in lines[index + 2 :]:
            if "|" not in body_line:
                break
            cells = _split_markdown_row(body_line)
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            row = {headers[cell_index]: cells[cell_index] for cell_index in range(len(headers))}
            rows.append(row)
        return rows
    return []


def load_benchmark_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            return [row for row in payload["rows"] if isinstance(row, dict)]
        return []
    return parse_markdown_benchmark_table(text)


def _is_unknown(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in UNKNOWN_MARKERS


def _canonical_platform(platform: Any) -> str:
    value = str(platform or "").strip().lower()
    if "tiktok" in value or "틱톡" in value:
        return "tiktok"
    if "short" in value or "youtube" in value or "유튜브" in value:
        return "youtube_shorts"
    if "instagram" in value or "reels" in value or "릴스" in value:
        return "instagram_reels"
    return value or "unknown"


def _platform_url_ok(platform: str, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if platform == "tiktok":
        return "tiktok.com" in host and "/video/" in path
    if platform == "youtube_shorts":
        return ("youtube.com" in host and "/shorts/" in path) or "youtu.be" in host
    if platform == "instagram_reels":
        return "instagram.com" in host and ("/reel/" in path or "/reels/" in path)
    return True


def _url_contains_extra_text(url: str) -> bool:
    return bool(re.search(r"\s|cite|turn\d+", url))


def validate_benchmark_rows(
    rows: list[dict[str, Any]],
    *,
    min_rows: int = 20,
    min_tiktok: int = 8,
    min_youtube_shorts: int = 8,
    min_instagram_reels: int = 0,
) -> BenchmarkValidation:
    blockers: list[str] = []
    warnings: list[str] = []
    row_errors: list[BenchmarkRowError] = []
    platform_counts = {"tiktok": 0, "youtube_shorts": 0, "instagram_reels": 0, "unknown": 0}
    seen_urls: set[str] = set()

    for index, row in enumerate(rows, start=1):
        row_id = str(row.get("id") or f"row_{index}").strip()
        platform = _canonical_platform(row.get("platform"))
        if platform not in platform_counts:
            platform_counts["unknown"] += 1
        else:
            platform_counts[platform] += 1

        for field_name in REQUIRED_FIELDS:
            if field_name not in row:
                row_errors.append(BenchmarkRowError(row_id, field_name, "missing_field"))

        if not re.fullmatch(r"R\d{3}", row_id):
            row_errors.append(BenchmarkRowError(row_id, "id", "invalid_id", row_id))

        url = str(row.get("url") or "").strip()
        if _is_unknown(url):
            row_errors.append(BenchmarkRowError(row_id, "url", "url_required", url))
        else:
            if _url_contains_extra_text(url):
                row_errors.append(BenchmarkRowError(row_id, "url", "url_contains_non_url_text", url))
            if not _platform_url_ok(platform, url):
                row_errors.append(BenchmarkRowError(row_id, "url", "url_platform_mismatch", url))
            if url in seen_urls:
                row_errors.append(BenchmarkRowError(row_id, "url", "duplicate_url", url))
            seen_urls.add(url)

        format_type = str(row.get("format_type") or "").strip()
        if format_type and format_type not in FORMAT_TYPES:
            row_errors.append(BenchmarkRowError(row_id, "format_type", "invalid_format_type", format_type))

        applicability = str(row.get("aino_applicability") or "").strip()
        if applicability and applicability not in AINO_APPLICABILITY:
            row_errors.append(
                BenchmarkRowError(row_id, "aino_applicability", "invalid_aino_applicability", applicability)
            )

        for field_name in CRITICAL_CODED_FIELDS:
            if _is_unknown(row.get(field_name)):
                row_errors.append(BenchmarkRowError(row_id, field_name, "critical_coding_required"))

    if len(rows) < min_rows:
        blockers.append(f"url_rows_lt_{min_rows}")
    if platform_counts["tiktok"] < min_tiktok:
        blockers.append(f"tiktok_rows_lt_{min_tiktok}")
    if platform_counts["youtube_shorts"] < min_youtube_shorts:
        blockers.append(f"youtube_shorts_rows_lt_{min_youtube_shorts}")
    if platform_counts["instagram_reels"] < min_instagram_reels:
        blockers.append(f"instagram_reels_rows_lt_{min_instagram_reels}")

    if row_errors:
        blockers.append("row_level_validation_failed")
    if platform_counts["instagram_reels"] == 0:
        warnings.append("instagram_reels_rows_missing")

    passed = not blockers
    return BenchmarkValidation(
        passed=passed,
        status="passed" if passed else "failed",
        row_count=len(rows),
        platform_counts=platform_counts,
        blockers=blockers,
        warnings=warnings,
        row_errors=row_errors,
    )


def validate_benchmark_file(path: Path) -> BenchmarkValidation:
    text = path.read_text(encoding="utf-8")
    validation = validate_benchmark_rows(load_benchmark_rows(path))
    if re.search(r"^\s*#?\s*FAILED_URL_COLLECTION\b", text, flags=re.MULTILINE):
        if "failed_url_collection_marker" not in validation.blockers:
            validation.blockers.insert(0, "failed_url_collection_marker")
        validation.passed = False
        validation.status = "failed"
    return validation


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate AiNo URL-backed reference benchmark tables.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation output.")
    args = parser.parse_args(argv)

    validation = validate_benchmark_file(args.path)
    if args.json:
        print(json.dumps(validation.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"status={validation.status} row_count={validation.row_count} blockers={','.join(validation.blockers)}")
    return 0 if validation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
