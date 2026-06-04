"""Analyze AiNo TikTok Studio metrics and produce response plans.

The module only reads local manifests and locally captured Studio metrics. It
does not call TikTok APIs or modify published posts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.core.tiktok_aino import pipeline


CONFIG = pipeline._load_strategy_config("monitoring_strategy.json")
DEFAULT_REPORT_DIR = pipeline.REPO_DIR / "output" / "tiktok_aino_performance_reports"
NUMBER_PATTERN = re.compile(r"(?P<number>\d+(?:[,.]\d+)*(?:\.\d+)?)\s*(?P<unit>만|억|천|k|m|b|%)?", re.IGNORECASE)


@dataclass(frozen=True)
class MetricSnapshot:
    run_id: str
    captured_at: str
    metrics: dict[str, float]
    source_path: str
    raw_url: str = ""
    raw_title: str = ""


@dataclass(frozen=True)
class PerformanceAnalysis:
    run_id: str
    status: str
    window: str
    score: int
    metrics: dict[str, float]
    derived_metrics: dict[str, float]
    thresholds: dict[str, float]
    diagnoses: list[str]
    actions: list[str]
    manifest_path: str | None = None
    source_path: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StudioContentRow:
    title: str
    created_at_text: str
    privacy: str
    views: float
    likes: float
    comments: float
    duration_sec: int
    pinned: bool = False


def _config_dict(key: str) -> dict[str, Any]:
    value = CONFIG.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"monitoring strategy key must be an object: {key}")
    return value


def _config_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key, [])
    if not isinstance(value, list):
        raise RuntimeError(f"monitoring strategy key must be a list: {key}")
    return [str(item) for item in value if str(item).strip()]


def _config_int(section: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(section.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _report_cooldown_minutes() -> int:
    return max(0, _config_int(_config_dict("reporting"), "report_cooldown_minutes", 60))


def _canonical_path_text(path: str | Path) -> str:
    candidate = Path(path)
    try:
        if not candidate.is_absolute():
            candidate = pipeline.REPO_DIR / candidate
        return str(candidate.resolve()).casefold()
    except OSError:
        return str(candidate).casefold()


def _canonical_path_set(paths: list[Path] | list[str]) -> list[str]:
    return sorted({_canonical_path_text(path) for path in paths})


def _with_existing_report_artifacts(path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(summary)
    hydrated["path"] = str(path)
    stamp = path.stem.replace("performance_report_", "", 1)
    feedback_path = path.with_name(f"performance_feedback_{stamp}.json")
    if feedback_path.exists():
        hydrated["performance_feedback_path"] = str(feedback_path)
    latest_feedback_path = path.with_name("performance_feedback.json")
    if latest_feedback_path.exists():
        hydrated["performance_feedback_latest_path"] = str(latest_feedback_path)
    dashboard_path = path.with_name(f"performance_dashboard_{stamp}.html")
    if dashboard_path.exists():
        hydrated["dashboard_path"] = str(dashboard_path)
    hydrated["reused_existing_report"] = True
    hydrated["report_cooldown_minutes"] = _report_cooldown_minutes()
    return hydrated


def _recent_duplicate_report(
    output_dir: Path,
    *,
    mode: str | None = None,
    source_path: Path | None = None,
    run_id: str | None = None,
    output_dirs: list[Path] | None = None,
) -> dict[str, Any] | None:
    cooldown = _report_cooldown_minutes()
    if cooldown <= 0 or not output_dir.exists():
        return None
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=cooldown)
    expected_source = _canonical_path_text(source_path) if source_path else None
    expected_output_dirs = _canonical_path_set(output_dirs or []) if output_dirs is not None else None
    for path in sorted(output_dir.glob("performance_report_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        modified = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
        if modified < cutoff:
            break
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if mode is not None and summary.get("mode") != mode:
            continue
        if expected_source is not None and _canonical_path_text(str(summary.get("source_path", ""))) != expected_source:
            continue
        if run_id is not None and str(summary.get("run_id") or "").strip() != run_id:
            continue
        if run_id is None and "run_id" in summary and summary.get("run_id") not in (None, ""):
            continue
        if expected_output_dirs is not None and _canonical_path_set([str(item) for item in summary.get("output_dirs", [])]) != expected_output_dirs:
            continue
        return _with_existing_report_artifacts(path, summary)
    return None


def parse_metric_number(text: str) -> float | None:
    match = NUMBER_PATTERN.search(text.replace(",", ""))
    if not match:
        return None
    try:
        value = float(match.group("number"))
    except ValueError:
        return None
    unit = (match.group("unit") or "").lower()
    if unit == "천" or unit == "k":
        value *= 1_000
    elif unit == "만":
        value *= 10_000
    elif unit == "억":
        value *= 100_000_000
    elif unit == "m":
        value *= 1_000_000
    elif unit == "b":
        value *= 1_000_000_000
    elif unit == "%":
        value /= 100
    return value


def _metric_aliases() -> dict[str, list[str]]:
    aliases = _config_dict("metric_aliases")
    return {str(key): [str(item).lower() for item in value] for key, value in aliases.items() if isinstance(value, list)}


def _extract_metric_from_text(key: str, aliases: list[str], text: str) -> float | None:
    lowered = text.lower()
    for alias in aliases:
        escaped = re.escape(alias)
        patterns = [
            rf"{escaped}\s*[:：]?\s*(.{{0,32}})",
            rf"(.{{0,32}})\s*{escaped}",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                value = parse_metric_number(match.group(0))
                if value is not None:
                    if key in {"completion_rate", "retention_rate"} and value > 1:
                        value = value / 100
                    return value
    return None


def normalize_metrics(payload: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for source_key in ["metrics", "normalizedMetrics", "normalized_metrics"]:
        source = payload.get(source_key)
        if isinstance(source, dict):
            for key, value in source.items():
                if isinstance(value, (int, float)):
                    normalized[str(key)] = float(value)
                elif isinstance(value, str):
                    parsed = parse_metric_number(value)
                    if parsed is not None:
                        normalized[str(key)] = parsed

    metric_nodes = payload.get("metricNodes", [])
    text_parts = [str(payload.get("textSample", "")), str(payload.get("title", ""))]
    if isinstance(metric_nodes, list):
        text_parts.extend(str(item) for item in metric_nodes)
    text = "\n".join(text_parts)
    for key, aliases in _metric_aliases().items():
        if key in normalized:
            continue
        value = _extract_metric_from_text(key, aliases, text)
        if value is not None:
            normalized[key] = value
    return normalized


def _duration_text_to_sec(text: str) -> int | None:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text.strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def _is_studio_date_line(text: str) -> bool:
    return bool(re.search(r"(?:\d{4}년\s*)?\d{1,2}월\s+\d{1,2}일\s+(?:오전|오후)\s+\d{1,2}:\d{2}", text))


def parse_studio_content_rows(text: str) -> list[StudioContentRow]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[StudioContentRow] = []
    index = 0
    while index < len(lines) - 6:
        duration = _duration_text_to_sec(lines[index])
        if duration is None:
            index += 1
            continue
        title = lines[index + 1]
        cursor = index + 2
        pinned = False
        if cursor < len(lines) and lines[cursor] == "고정됨":
            pinned = True
            cursor += 1
        if cursor >= len(lines) or not _is_studio_date_line(lines[cursor]):
            index += 1
            continue
        created_at_text = lines[cursor]
        cursor += 1
        if cursor >= len(lines):
            break
        privacy = lines[cursor]
        cursor += 1
        metric_values: list[float] = []
        for offset in range(3):
            if cursor + offset >= len(lines):
                break
            parsed = parse_metric_number(lines[cursor + offset])
            if parsed is None:
                break
            metric_values.append(parsed)
        if len(metric_values) != 3:
            index += 1
            continue
        rows.append(
            StudioContentRow(
                title=title,
                created_at_text=created_at_text,
                privacy=privacy,
                views=metric_values[0],
                likes=metric_values[1],
                comments=metric_values[2],
                duration_sec=duration,
                pinned=pinned,
            )
        )
        index = cursor + 3
    return rows


def _studio_snapshot_text(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    if isinstance(payload.get("combined"), str):
        parts.append(str(payload["combined"]))
    if isinstance(payload.get("text_sample"), str):
        parts.append(str(payload["text_sample"]))
    snapshots = payload.get("snapshots")
    if isinstance(snapshots, list):
        parts.extend(str(row.get("text", "")) for row in snapshots if isinstance(row, dict))
    return "\n".join(part for part in parts if part)


def _strip_korean_particle(token: str) -> str:
    for suffix in ["입니다", "습니다", "으로", "에서", "에게", "까지", "부터", "하고", "라는", "처럼", "보다", "와", "과", "은", "는", "이", "가", "을", "를", "의", "도", "만"]:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            return token[: -len(suffix)]
    return token


def _reference_terms(text: str) -> list[str]:
    return [
        _strip_korean_particle(token)
        for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
        if _strip_korean_particle(token) not in pipeline.SEARCH_STOPWORDS
        and _strip_korean_particle(token) not in {"팔로우", "댓글", "공유", "올바른AiNo"}
    ]


def _engagement_count(row: StudioContentRow) -> float:
    return row.likes + row.comments


def _is_strong_reference_row(row: StudioContentRow, best_views: float) -> bool:
    if row.views >= 2000:
        return True
    if best_views >= 10000 and row.views >= best_views * 0.08 and _engagement_count(row) >= 20:
        return True
    return row.pinned and row.views >= 1000 and _engagement_count(row) >= 20


def _is_weak_reference_row(row: StudioContentRow, best_views: float) -> bool:
    if row.pinned or row.views <= 0:
        return False
    if row.views < 500 and _engagement_count(row) <= 5:
        return True
    if best_views >= 10000 and row.views < best_views * 0.01 and _engagement_count(row) <= 10:
        return True
    return False


def build_account_reference_feedback(rows: list[StudioContentRow]) -> dict[str, Any]:
    published = [row for row in rows if row.views > 0]
    if not published:
        return {
            "term_scores": {},
            "format_scores": {},
            "positive_terms": [],
            "negative_terms": [],
            "notes": ["no_published_studio_rows"],
            "sample_count": 0,
        }
    unique: dict[tuple[str, str], StudioContentRow] = {}
    for row in published:
        unique[(row.title, row.created_at_text)] = row
    ranked = sorted(unique.values(), key=lambda row: (row.views, row.likes + row.comments), reverse=True)
    best_views = ranked[0].views if ranked else 0
    strong_rows = [row for row in ranked if _is_strong_reference_row(row, best_views)]
    if not strong_rows:
        strong_rows = ranked[: min(3, len(ranked))]
    weak_rows = [row for row in ranked if _is_weak_reference_row(row, best_views)]
    term_scores: dict[str, int] = {}
    for row in strong_rows[:12]:
        boost = 14 if row.views >= 10000 else 10 if row.views >= 2000 else 6
        for term in _reference_terms(row.title)[:16]:
            term_scores[term] = max(-30, min(30, term_scores.get(term, 0) + boost))
    for row in weak_rows[:12]:
        penalty = -14 if row.views < 200 else -10
        for term in _reference_terms(row.title)[:18]:
            term_scores[term] = max(-30, min(30, term_scores.get(term, 0) + penalty))
    positive_terms = [term for term, score in sorted(term_scores.items(), key=lambda item: item[1], reverse=True) if score > 0]
    negative_terms = [term for term, score in sorted(term_scores.items(), key=lambda item: item[1]) if score < 0]
    return {
        "term_scores": term_scores,
        "format_scores": {},
        "positive_terms": positive_terms[:16],
        "negative_terms": negative_terms[:16],
        "notes": [
            *[
                f"strong_reference: {row.views:g} views; {row.likes:g} likes; {row.comments:g} comments; {row.title[:80]}"
                for row in strong_rows[:6]
            ],
            *[
                f"weak_reference: {row.views:g} views; {row.likes:g} likes; {row.comments:g} comments; {row.title[:80]}"
                for row in weak_rows[:6]
            ],
        ],
        "sample_count": len(ranked),
        "strong_sample_count": len(strong_rows),
        "weak_sample_count": len(weak_rows),
    }


def analyze_studio_snapshot(snapshot_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
    if output_dir:
        existing = _recent_duplicate_report(
            output_dir,
            mode="studio_content_reference",
            source_path=snapshot_path,
        )
        if existing:
            return existing
    rows = parse_studio_content_rows(_studio_snapshot_text(snapshot_path))
    feedback = build_account_reference_feedback(rows)
    unique: dict[tuple[str, str], StudioContentRow] = {}
    for row in rows:
        unique[(row.title, row.created_at_text)] = row
    ranked = sorted(unique.values(), key=lambda row: (row.views, row.likes + row.comments), reverse=True)
    summary = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_path": str(snapshot_path),
        "mode": "studio_content_reference",
        "row_count": len(rows),
        "feedback": feedback,
        "top_rows": [asdict(row) for row in ranked[:20]],
        "scheduled_rows": [asdict(row) for row in ranked if row.views == 0][:20],
    }
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"performance_report_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
        pipeline._write_json(path, summary)
        summary["path"] = str(path)
        summary.update(write_performance_feedback_artifacts(output_dir, summary, source_report_path=path))
    return summary


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def load_metric_snapshots(output_dirs: list[Path]) -> list[MetricSnapshot]:
    snapshots: list[MetricSnapshot] = []
    for output_dir in output_dirs:
        for path in sorted(output_dir.glob("**/studio_metrics_*.jsonl")):
            for row in _read_jsonl(path):
                run_id = str(row.get("run_id") or row.get("runId") or row.get("latestRunId") or "").strip()
                latest_job = row.get("latestJob")
                if not run_id and isinstance(latest_job, dict):
                    run_id = str(latest_job.get("run_id") or latest_job.get("runId") or "").strip()
                if not run_id:
                    run_id = _run_id_from_text(str(row.get("url", "")) + "\n" + str(row.get("textSample", "")))
                metrics = normalize_metrics(row)
                captured_at = str(row.get("captured_at") or row.get("capturedAt") or dt.datetime.now(dt.timezone.utc).isoformat())
                snapshots.append(
                    MetricSnapshot(
                        run_id=run_id or "unknown",
                        captured_at=captured_at,
                        metrics=metrics,
                        source_path=str(path),
                        raw_url=str(row.get("url", "")),
                        raw_title=str(row.get("title", "")),
                    )
                )
    return snapshots


def _run_id_from_text(text: str) -> str:
    match = re.search(r"leftaino_\d{8}_\d{6}", text)
    return match.group(0) if match else ""


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifests(output_dirs: list[Path]) -> dict[str, tuple[Path, dict[str, Any]]]:
    manifests: dict[str, tuple[Path, dict[str, Any]]] = {}
    for output_dir in output_dirs:
        for path in sorted(output_dir.glob("leftaino_*/manifest.json")):
            try:
                manifest = _load_manifest(path)
            except (OSError, json.JSONDecodeError):
                continue
            run_id = str(manifest.get("run_id") or path.parent.name)
            manifests[run_id] = (path, manifest)
    return manifests


def _latest_snapshot_by_run(snapshots: list[MetricSnapshot]) -> dict[str, MetricSnapshot]:
    latest: dict[str, MetricSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.run_id == "unknown":
            continue
        if snapshot.run_id not in latest or snapshot.captured_at > latest[snapshot.run_id].captured_at:
            latest[snapshot.run_id] = snapshot
    return latest


def _duration_sec(manifest: dict[str, Any]) -> float:
    value = manifest.get("synced_duration_sec")
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    script = manifest.get("script", {})
    if isinstance(script, dict) and isinstance(script.get("target_duration_sec"), (int, float)):
        return float(script["target_duration_sec"])
    return 45.0


def _age_hours(snapshot: MetricSnapshot, manifest: dict[str, Any]) -> float:
    captured = _parse_datetime(snapshot.captured_at) or dt.datetime.now(dt.timezone.utc)
    posted_at = (
        _parse_datetime(str(manifest.get("posted_at") or ""))
        or _parse_datetime(str(manifest.get("planned_publish_at_local") or ""))
        or _parse_datetime(str(manifest.get("created_at") or ""))
        or captured
    )
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=dt.timezone.utc)
    return max(0.0, (captured.astimezone(dt.timezone.utc) - posted_at.astimezone(dt.timezone.utc)).total_seconds() / 3600)


def _parse_datetime(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def _window_for_age(age_hours: float) -> tuple[str, dict[str, float]]:
    windows = _config_dict("windows")
    for name, row in windows.items():
        if not isinstance(row, dict):
            continue
        max_age = float(row.get("max_age_hours", 999999))
        if age_hours <= max_age:
            return str(name), {str(key): float(value) for key, value in row.items() if isinstance(value, (int, float))}
    name, row = list(windows.items())[-1]
    return str(name), {str(key): float(value) for key, value in row.items() if isinstance(value, (int, float))}


def _safe_rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _derived_metrics(metrics: dict[str, float], manifest: dict[str, Any]) -> dict[str, float]:
    views = float(metrics.get("views", 0))
    likes = float(metrics.get("likes", 0))
    comments = float(metrics.get("comments", 0))
    shares = float(metrics.get("shares", 0))
    saves = float(metrics.get("saves", 0))
    duration = _duration_sec(manifest)
    average_watch_time = float(metrics.get("average_watch_time_sec", 0))
    return {
        "engagement_rate": _safe_rate(likes + comments + shares + saves, views),
        "comment_rate": _safe_rate(comments, views),
        "share_rate": _safe_rate(shares, views),
        "save_rate": _safe_rate(saves, views),
        "follower_conversion_rate": _safe_rate(float(metrics.get("followers_gained", 0)), views),
        "average_watch_ratio": _safe_rate(average_watch_time, duration),
        "completion_rate": float(metrics.get("completion_rate", 0)),
    }


def _score_component(value: float, threshold: float, weight: float) -> float:
    if threshold <= 0:
        return weight
    return min(weight, weight * value / threshold)


def _score(metrics: dict[str, float], derived: dict[str, float], thresholds: dict[str, float]) -> int:
    weights = {str(key): float(value) for key, value in _config_dict("score_weights").items()}
    values = {
        "views": float(metrics.get("views", 0)),
        "engagement_rate": derived["engagement_rate"],
        "comment_rate": derived["comment_rate"],
        "share_rate": derived["share_rate"],
        "average_watch_ratio": derived["average_watch_ratio"],
        "completion_rate": derived["completion_rate"],
        "follower_conversion_rate": derived["follower_conversion_rate"],
    }
    threshold_values = {
        "views": thresholds.get("min_views", 0),
        "engagement_rate": thresholds.get("min_engagement_rate", 0),
        "comment_rate": thresholds.get("min_comment_rate", 0),
        "share_rate": thresholds.get("min_share_rate", 0),
        "average_watch_ratio": thresholds.get("min_average_watch_ratio", 0),
        "completion_rate": thresholds.get("min_completion_rate", 0),
        "follower_conversion_rate": 0.001,
    }
    total = sum(_score_component(values[key], threshold_values[key], weights.get(key, 0)) for key in values)
    return int(round(max(0, min(100, total))))


def _diagnoses(metrics: dict[str, float], derived: dict[str, float], thresholds: dict[str, float]) -> list[str]:
    diagnoses: list[str] = []
    if not metrics:
        return ["missing_metrics"]
    if metrics.get("views", 0) < thresholds.get("min_views", 0):
        diagnoses.append("views_lt_threshold")
    if derived["engagement_rate"] >= thresholds.get("min_engagement_rate", 0):
        diagnoses.append("engagement_gte_threshold")
    if metrics.get("views", 0) >= thresholds.get("min_views", 0):
        diagnoses.append("views_gte_threshold")
    if derived["comment_rate"] < thresholds.get("min_comment_rate", 0):
        diagnoses.append("comment_rate_lt_threshold")
    if derived["share_rate"] < thresholds.get("min_share_rate", 0):
        diagnoses.append("share_rate_lt_threshold")
    if derived["average_watch_ratio"] < thresholds.get("min_average_watch_ratio", 0):
        diagnoses.append("average_watch_ratio_lt_threshold")
    if derived["completion_rate"] and derived["completion_rate"] < thresholds.get("min_completion_rate", 0):
        diagnoses.append("completion_rate_lt_threshold")
    return diagnoses


def _actions(score: int, diagnoses: list[str]) -> list[str]:
    signals = set(diagnoses)
    if score >= 80:
        signals.add("score_gte_80")
    rules = _config_dict("response_rules")
    selected: list[tuple[int, str]] = []
    for rule in rules.values():
        if not isinstance(rule, dict):
            continue
        when = set(_config_list(rule, "when"))
        if when and when.issubset(signals):
            priority = int(rule.get("priority", 99))
            for action in _config_list(rule, "actions"):
                selected.append((priority, action))
    selected.sort(key=lambda item: item[0])
    limit = int(_config_dict("reporting").get("top_action_limit", 5))
    actions: list[str] = []
    for _, action in selected:
        if action not in actions:
            actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def analyze_run(run_id: str, manifest_path: Path, manifest: dict[str, Any], snapshot: MetricSnapshot | None) -> PerformanceAnalysis:
    if snapshot is None:
        window_name, thresholds = _window_for_age(0)
        diagnoses = ["missing_metrics"]
        return PerformanceAnalysis(
            run_id=run_id,
            status="needs_metrics",
            window=window_name,
            score=0,
            metrics={},
            derived_metrics={},
            thresholds=thresholds,
            diagnoses=diagnoses,
            actions=_actions(0, diagnoses),
            manifest_path=str(manifest_path),
            notes=[str(_config_dict("reporting").get("source_note", ""))],
        )
    age = _age_hours(snapshot, manifest)
    window_name, thresholds = _window_for_age(age)
    derived = _derived_metrics(snapshot.metrics, manifest)
    score = _score(snapshot.metrics, derived, thresholds)
    diagnoses = _diagnoses(snapshot.metrics, derived, thresholds)
    return PerformanceAnalysis(
        run_id=run_id,
        status="strong" if score >= 80 else ("watch" if score >= 55 else "respond"),
        window=window_name,
        score=score,
        metrics=snapshot.metrics,
        derived_metrics=derived,
        thresholds=thresholds,
        diagnoses=diagnoses,
        actions=_actions(score, diagnoses),
        manifest_path=str(manifest_path),
        source_path=snapshot.source_path,
        notes=[str(_config_dict("reporting").get("source_note", ""))],
    )


def analyze_performance(
    *,
    output_dirs: list[Path],
    run_id: str | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if output_dir:
        existing = _recent_duplicate_report(output_dir, run_id=run_id, output_dirs=output_dirs)
        if existing:
            return existing
    manifests = load_manifests(output_dirs)
    snapshots = _latest_snapshot_by_run(load_metric_snapshots(output_dirs))
    analyses: list[PerformanceAnalysis] = []
    for manifest_run_id, (manifest_path, manifest) in sorted(manifests.items()):
        if run_id and manifest_run_id != run_id:
            continue
        analyses.append(analyze_run(manifest_run_id, manifest_path, manifest, snapshots.get(manifest_run_id)))

    status_counts: dict[str, int] = {}
    for analysis in analyses:
        status_counts[analysis.status] = status_counts.get(analysis.status, 0) + 1
    feedback = build_feedback_profile(analyses)
    summary = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": run_id,
        "output_dirs": [str(path) for path in output_dirs],
        "status_counts": status_counts,
        "feedback": feedback,
        "analyses": [asdict(analysis) for analysis in analyses],
    }
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"performance_report_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
        pipeline._write_json(path, summary)
        summary["path"] = str(path)
        dashboard_path = output_dir / f"performance_dashboard_{dt.datetime.now():%Y%m%d_%H%M%S}.html"
        write_dashboard(dashboard_path, summary)
        summary["dashboard_path"] = str(dashboard_path)
        summary.update(write_performance_feedback_artifacts(output_dir, summary, source_report_path=path))
    return summary


def _analysis_terms(analysis: PerformanceAnalysis) -> list[str]:
    terms: list[str] = []
    if analysis.manifest_path:
        try:
            manifest = _load_manifest(Path(analysis.manifest_path))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        topic = manifest.get("topic", {})
        script = manifest.get("script", {})
        hashtags = script.get("hashtags", []) if isinstance(script, dict) else []
        text = " ".join(
            [
                str(topic.get("title", "")) if isinstance(topic, dict) else "",
                str(topic.get("angle", "")) if isinstance(topic, dict) else "",
                str(script.get("post_title", "")) if isinstance(script, dict) else "",
                " ".join(str(tag) for tag in hashtags if isinstance(hashtags, list)),
            ]
        )
        terms = [
            token
            for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
            if token not in pipeline.SEARCH_STOPWORDS
        ]
    return list(dict.fromkeys(terms))[:10]


def _analysis_format(analysis: PerformanceAnalysis) -> str:
    if not analysis.manifest_path:
        return ""
    try:
        manifest = _load_manifest(Path(analysis.manifest_path))
    except (OSError, json.JSONDecodeError):
        return ""
    format_plan = manifest.get("format_plan", {})
    return str(format_plan.get("format_id", "")) if isinstance(format_plan, dict) else ""


def _analysis_visual_patterns(analysis: PerformanceAnalysis) -> list[str]:
    if not analysis.manifest_path:
        return []
    try:
        manifest = _load_manifest(Path(analysis.manifest_path))
    except (OSError, json.JSONDecodeError):
        return []
    visual_plan = manifest.get("visual_plan", {})
    scenes = visual_plan.get("scenes", []) if isinstance(visual_plan, dict) else []
    patterns: list[str] = []
    for scene in scenes if isinstance(scenes, list) else []:
        if not isinstance(scene, dict):
            continue
        role = str(scene.get("visual_role", "")).strip()
        issue_type = str(scene.get("issue_type", "")).strip()
        if role:
            patterns.append(f"role:{role}")
        if issue_type:
            patterns.append(f"issue:{issue_type}")
    motion = manifest.get("visual_motion", {})
    if isinstance(motion, dict) and motion.get("all_static_hold") is True:
        patterns.append("motion:static_hold")
    return list(dict.fromkeys(patterns))[:12]


def build_feedback_profile(analyses: list[PerformanceAnalysis]) -> dict[str, Any]:
    term_scores: dict[str, int] = {}
    format_scores: dict[str, int] = {}
    visual_scores: dict[str, int] = {}
    notes: list[str] = []
    for analysis in analyses:
        if analysis.status == "needs_metrics":
            continue
        score_delta = 0
        if analysis.status == "strong":
            score_delta = 12
            notes.append(f"{analysis.run_id}: strong performer; boost related terms")
        elif analysis.status == "respond":
            score_delta = -10
            notes.append(f"{analysis.run_id}: weak performer; suppress related terms until reframed")
        elif "average_watch_ratio_lt_threshold" in analysis.diagnoses:
            score_delta = -6
        if score_delta == 0:
            continue
        for term in _analysis_terms(analysis):
            term_scores[term] = max(-30, min(30, term_scores.get(term, 0) + score_delta))
        content_format = _analysis_format(analysis)
        if content_format:
            format_scores[content_format] = max(-20, min(20, format_scores.get(content_format, 0) + round(score_delta / 2)))
        for pattern in _analysis_visual_patterns(analysis):
            visual_scores[pattern] = max(-20, min(20, visual_scores.get(pattern, 0) + round(score_delta / 3)))
    positive_terms = [term for term, score in sorted(term_scores.items(), key=lambda item: item[1], reverse=True) if score > 0]
    negative_terms = [term for term, score in sorted(term_scores.items(), key=lambda item: item[1]) if score < 0]
    positive_visual_patterns = [
        pattern for pattern, score in sorted(visual_scores.items(), key=lambda item: item[1], reverse=True) if score > 0
    ]
    negative_visual_patterns = [
        pattern for pattern, score in sorted(visual_scores.items(), key=lambda item: item[1]) if score < 0
    ]
    return {
        "term_scores": term_scores,
        "format_scores": format_scores,
        "visual_scores": visual_scores,
        "positive_terms": positive_terms[:12],
        "negative_terms": negative_terms[:12],
        "positive_visual_patterns": positive_visual_patterns[:12],
        "negative_visual_patterns": negative_visual_patterns[:12],
        "notes": notes[:12],
        "sample_count": len([analysis for analysis in analyses if analysis.status != "needs_metrics"]),
    }


def _score_rows(score_map: dict[str, Any], *, key_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, raw_delta in score_map.items():
        try:
            delta = int(raw_delta)
        except (TypeError, ValueError):
            continue
        if not str(key).strip() or delta == 0:
            continue
        rows.append(
            {
                key_name: str(key),
                "delta": delta,
                "direction": "boost" if delta > 0 else "suppress",
            }
        )
    return sorted(rows, key=lambda row: abs(int(row["delta"])), reverse=True)


def build_performance_feedback_artifact(
    summary: dict[str, Any],
    *,
    source_report_path: Path | None = None,
) -> dict[str, Any]:
    feedback = summary.get("feedback", {})
    if not isinstance(feedback, dict):
        feedback = {}
    term_scores = feedback.get("term_scores", {}) if isinstance(feedback.get("term_scores", {}), dict) else {}
    format_scores = feedback.get("format_scores", {}) if isinstance(feedback.get("format_scores", {}), dict) else {}
    visual_scores = feedback.get("visual_scores", {}) if isinstance(feedback.get("visual_scores", {}), dict) else {}
    keyword_adjustments = _score_rows(term_scores, key_name="keyword")
    format_adjustments = _score_rows(format_scores, key_name="format")
    visual_adjustments = _score_rows(visual_scores, key_name="pattern")
    positive_terms = feedback.get("positive_terms", []) if isinstance(feedback.get("positive_terms", []), list) else []
    negative_terms = feedback.get("negative_terms", []) if isinstance(feedback.get("negative_terms", []), list) else []
    best_format = ""
    if format_adjustments:
        positive_formats = [row for row in format_adjustments if int(row["delta"]) > 0]
        best_format = str((positive_formats or format_adjustments)[0]["format"])
    return {
        "version": "performance_feedback_v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_report_path": str(source_report_path) if source_report_path else str(summary.get("path", "")),
        "mode": str(summary.get("mode", "run_performance")),
        "sample_count": int(feedback.get("sample_count", 0) or 0),
        "topic_keywords": [str(item) for item in positive_terms[:12]],
        "format": best_format,
        "feedback": {
            "keyword_adjustments": keyword_adjustments,
            "format_adjustments": format_adjustments,
            "visual_adjustments": visual_adjustments,
            "term_scores": term_scores,
            "format_scores": format_scores,
            "visual_scores": visual_scores,
            "positive_terms": positive_terms,
            "negative_terms": negative_terms,
            "positive_visual_patterns": feedback.get("positive_visual_patterns", []),
            "negative_visual_patterns": feedback.get("negative_visual_patterns", []),
            "notes": feedback.get("notes", []),
            "sample_count": int(feedback.get("sample_count", 0) or 0),
        },
    }


def write_performance_feedback_artifacts(
    output_dir: Path,
    summary: dict[str, Any],
    *,
    source_report_path: Path | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_performance_feedback_artifact(summary, source_report_path=source_report_path)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stamped_path = output_dir / f"performance_feedback_{timestamp}.json"
    latest_path = output_dir / "performance_feedback.json"
    pipeline._write_json(stamped_path, artifact)
    sample_count = int(artifact.get("sample_count", 0) or 0)
    preserve_latest = False
    if sample_count <= 0 and latest_path.exists():
        try:
            existing = json.loads(latest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        existing_sample_count = int(existing.get("sample_count", 0) or 0) if isinstance(existing, dict) else 0
        preserve_latest = existing_sample_count > sample_count
    if not preserve_latest:
        pipeline._write_json(latest_path, artifact)
    return {"performance_feedback_path": str(stamped_path), "performance_feedback_latest_path": str(latest_path)}


def write_dashboard(path: Path, summary: dict[str, Any]) -> None:
    analyses = summary.get("analyses", [])
    rows = []
    for analysis in analyses if isinstance(analyses, list) else []:
        if not isinstance(analysis, dict):
            continue
        actions = "<br>".join(html.escape(str(action)) for action in analysis.get("actions", [])[:3])
        diagnoses = ", ".join(str(item) for item in analysis.get("diagnoses", []))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(analysis.get('run_id', '')))}</td>"
            f"<td>{html.escape(str(analysis.get('status', '')))}</td>"
            f"<td>{html.escape(str(analysis.get('window', '')))}</td>"
            f"<td>{int(analysis.get('score', 0) or 0)}</td>"
            f"<td>{html.escape(diagnoses)}</td>"
            f"<td>{actions}</td>"
            "</tr>"
        )
    feedback = summary.get("feedback", {})
    doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>AiNo TikTok Performance Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #0f1419; color: #f2f5f7; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ border-bottom: 1px solid #26323f; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: #9fb5c8; font-size: 13px; }}
    .panel {{ border: 1px solid #26323f; border-radius: 8px; padding: 16px; background: #151d25; }}
    .muted {{ color: #9fb5c8; }}
  </style>
</head>
<body>
<main>
  <h1>AiNo TikTok Performance Dashboard</h1>
  <p class="muted">Created at {html.escape(str(summary.get('created_at', '')))}</p>
  <section class="panel">
    <strong>Feedback sample count:</strong> {html.escape(str(feedback.get('sample_count', 0) if isinstance(feedback, dict) else 0))}<br>
    <strong>Positive terms:</strong> {html.escape(', '.join(feedback.get('positive_terms', [])) if isinstance(feedback, dict) else '')}<br>
    <strong>Negative terms:</strong> {html.escape(', '.join(feedback.get('negative_terms', [])) if isinstance(feedback, dict) else '')}
  </section>
  <table>
    <thead><tr><th>run_id</th><th>status</th><th>window</th><th>score</th><th>diagnoses</th><th>actions</th></tr></thead>
    <tbody>{''.join(rows) or '<tr><td colspan="6">No analyses</td></tr>'}</tbody>
  </table>
</main>
</body>
</html>"""
    path.write_text(doc, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze locally captured AiNo TikTok performance metrics.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        action="append",
        dest="output_dirs",
        default=[],
        help="Directory containing leftaino_* manifests and studio_metrics JSONL files.",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument(
        "--studio-snapshot",
        type=Path,
        help="JSON snapshot captured from TikTok Studio content page; builds an account-reference feedback report.",
    )
    args = parser.parse_args()

    report_dir = args.report_dir
    if report_dir is None:
        report_dir = DEFAULT_REPORT_DIR
    if args.studio_snapshot:
        summary = analyze_studio_snapshot(args.studio_snapshot, output_dir=report_dir)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    output_dirs = args.output_dirs or [
        pipeline.DEFAULT_OUTPUT_DIR,
        pipeline.REPO_DIR / "output" / "tiktok_aino_scheduled_packages",
        pipeline.REPO_DIR / "output" / "tiktok_aino_nohardcode_test",
    ]
    summary = analyze_performance(output_dirs=output_dirs, run_id=args.run_id, output_dir=report_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
