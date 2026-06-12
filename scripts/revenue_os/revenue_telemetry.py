# -*- coding: utf-8 -*-
"""Revenue telemetry aggregator for the Neo Genesis autonomous revenue OS.

The collector is intentionally conservative: it records only live values that
can be collected from local reports or read-only analytics APIs, and leaves
platform revenue consoles as explicit no_data rows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - local fallback for lean envs
    load_dotenv = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KST = timezone(timedelta(hours=9))
OUT_DIR = PROJECT_ROOT / "output" / "revenue_os"
LATEST_JSON = OUT_DIR / "revenue_telemetry_latest.json"
TIKTOK_REPORT_DIR = PROJECT_ROOT / "output" / "tiktok_aino_performance_reports"
POSTHOG_HOST = "https://us.posthog.com"
POSTHOG_PROJECT_ID = "322404"
POSTHOG_TARGETS = [
    {"engine_id": "R3", "site": "daysleft", "host": "daysleft.io"},
    {"engine_id": "R4", "site": "toolpick", "host": "www.toolpick.dev"},
    {"engine_id": "R4", "site": "kott", "host": "kott.kr"},
]
GA4_TARGETS = [
    {"engine_id": "R4", "site": "toolpick", "property": "properties/524659689", "host": None},
    {"engine_id": "R4", "site": "kott", "property": "properties/525765817", "host": None},
]


ENGINE_NAMES = {
    "R1": "AIT Toss factory",
    "R2": "TikTok @leftaino",
    "R3": "FINITE daysleft.io",
    "R4": "SBU passive",
}


def now_kst() -> datetime:
    return datetime.now(KST)


def iso_now() -> str:
    return now_kst().isoformat(timespec="seconds")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def load_env() -> None:
    if load_dotenv:
        load_dotenv(PROJECT_ROOT / ".env")
        load_dotenv(PROJECT_ROOT / ".env.local", override=False)
        return

    for name in (".env", ".env.local"):
        path = PROJECT_ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def metric_row(
    engine_id: str,
    metric: str,
    value: Any,
    unit: str,
    status: str,
    source: str,
    asof: str,
    **extra: Any,
) -> dict[str, Any]:
    row = {
        "engine_id": engine_id,
        "engine_name": ENGINE_NAMES.get(engine_id, engine_id),
        "metric": metric,
        "value": value,
        "unit": unit,
        "status": status,
        "source": source,
        "asof": asof,
    }
    row.update({key: val for key, val in extra.items() if val is not None})
    return row


def no_data_row(
    engine_id: str,
    metric: str,
    unit: str,
    source: str,
    unlock_path: str,
    asof: str,
    **extra: Any,
) -> dict[str, Any]:
    return metric_row(
        engine_id,
        metric,
        None,
        unit,
        "no_data",
        source,
        asof,
        unlock_path=unlock_path,
        **extra,
    )


def latest_file(pattern: str) -> Path | None:
    if not TIKTOK_REPORT_DIR.exists():
        return None
    files = [path for path in TIKTOK_REPORT_DIR.glob(pattern) if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime, default=None)


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def compact_number(value: str) -> int | float | None:
    raw = value.strip().replace(",", "")
    if not raw or raw in {"--", "-"}:
        return None
    match = re.match(r"^([<>]?)(\d+(?:\.\d+)?)([KkMmBb]|만|천)?$", raw)
    if not match:
        return None
    prefix, number, suffix = match.groups()
    amount = float(number)
    multiplier = {
        None: 1,
        "K": 1_000,
        "k": 1_000,
        "M": 1_000_000,
        "m": 1_000_000,
        "B": 1_000_000_000,
        "b": 1_000_000_000,
        "천": 1_000,
        "만": 10_000,
    }[suffix]
    parsed = amount * multiplier
    if prefix == "<":
        parsed = max(parsed - 1, 0)
    return int(parsed) if parsed.is_integer() else parsed


def extract_after_label(text: str, label: str) -> tuple[int | float | None, str | None]:
    pattern = re.compile(rf"{re.escape(label)}\s*\n\s*([<>]?\d[\d,.]*(?:\.\d+)?\s*(?:[KkMmBb]|만|천)?)")
    match = pattern.search(text)
    if not match:
        return None, None
    raw = match.group(1).replace(" ", "")
    return compact_number(raw), raw


def first_text_sample(payload: dict[str, Any] | None, path_hint: str) -> str:
    if not payload:
        return ""
    for key, value in payload.items():
        if path_hint in key and isinstance(value, dict):
            text = value.get("text_sample")
            if isinstance(text, str):
                return text
    for value in payload.values():
        if isinstance(value, dict) and isinstance(value.get("text_sample"), str):
            return str(value["text_sample"])
    return ""


def collect_tiktok_metrics(asof: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    report_path = latest_file("performance_report_*.json")
    report = load_json(report_path)
    source_asof = report.get("created_at") if report else None
    if not isinstance(source_asof, str):
        source_asof = (
            datetime.fromtimestamp(report_path.stat().st_mtime, KST).isoformat(timespec="seconds")
            if report_path
            else asof
        )

    metrics.append(
        no_data_row(
            "R2",
            "creator_rewards_revenue",
            "USD",
            "TikTok Creator Rewards console",
            "owner 콘솔 확인 필요",
            asof,
        )
    )

    if report:
        rows = report.get("top_rows") if isinstance(report.get("top_rows"), list) else []
        scheduled = report.get("scheduled_rows") if isinstance(report.get("scheduled_rows"), list) else []
        views = [float(row.get("views") or 0) for row in rows if isinstance(row, dict)]
        likes = [float(row.get("likes") or 0) for row in rows if isinstance(row, dict)]
        comments = [float(row.get("comments") or 0) for row in rows if isinstance(row, dict)]
        metrics.extend(
            [
                metric_row(
                    "R2",
                    "latest_report_top_rows_views",
                    int(sum(views)),
                    "views",
                    "live",
                    "local_tiktok_performance_report",
                    source_asof,
                    source_path=rel(report_path),
                    sample_count=len(rows),
                ),
                metric_row(
                    "R2",
                    "latest_report_max_video_views",
                    int(max(views)) if views else 0,
                    "views",
                    "live",
                    "local_tiktok_performance_report",
                    source_asof,
                    source_path=rel(report_path),
                    sample_count=len(rows),
                ),
                metric_row(
                    "R2",
                    "latest_report_top_rows_likes",
                    int(sum(likes)),
                    "likes",
                    "live",
                    "local_tiktok_performance_report",
                    source_asof,
                    source_path=rel(report_path),
                    sample_count=len(rows),
                ),
                metric_row(
                    "R2",
                    "latest_report_top_rows_comments",
                    int(sum(comments)),
                    "comments",
                    "live",
                    "local_tiktok_performance_report",
                    source_asof,
                    source_path=rel(report_path),
                    sample_count=len(rows),
                ),
                metric_row(
                    "R2",
                    "scheduled_rows_not_evaluable",
                    len(scheduled),
                    "rows",
                    "live",
                    "local_tiktok_performance_report",
                    source_asof,
                    source_path=rel(report_path),
                ),
            ]
        )
    else:
        metrics.append(
            no_data_row(
                "R2",
                "latest_report_top_rows_views",
                "views",
                "local_tiktok_performance_report",
                "output/tiktok_aino_performance_reports 의 performance_report_*.json 생성 필요",
                asof,
            )
        )

    overview_path = latest_file("analytics_snapshot_*.json")
    overview = load_json(overview_path)
    overview_text = first_text_sample(overview, "/analytics/overview")
    views_7d, views_raw = extract_after_label(overview_text, "동영상 조회 수")
    if views_7d is None:
        metrics.append(
            no_data_row(
                "R2",
                "analytics_snapshot_video_views_7d",
                "views",
                "local_tiktok_analytics_snapshot",
                "TikTok Studio analytics snapshot 재수집 필요",
                asof,
                source_path=rel(overview_path),
            )
        )
    else:
        metrics.append(
            metric_row(
                "R2",
                "analytics_snapshot_video_views_7d",
                views_7d,
                "views",
                "live",
                "local_tiktok_analytics_snapshot",
                datetime.fromtimestamp(overview_path.stat().st_mtime, KST).isoformat(timespec="seconds")
                if overview_path
                else asof,
                source_path=rel(overview_path),
                raw_value=views_raw,
            )
        )

    follower_path = latest_file("follower_analytics_snapshot_*.json")
    follower = load_json(follower_path)
    follower_text = first_text_sample(follower, "/analytics/followers")
    followers, followers_raw = extract_after_label(follower_text, "총 팔로워 수")
    if followers is None:
        metrics.append(
            no_data_row(
                "R2",
                "followers_total",
                "followers",
                "local_tiktok_follower_snapshot",
                "TikTok Studio followers snapshot 재수집 필요",
                asof,
                source_path=rel(follower_path),
            )
        )
    else:
        metrics.append(
            metric_row(
                "R2",
                "followers_total",
                followers,
                "followers",
                "live",
                "local_tiktok_follower_snapshot",
                datetime.fromtimestamp(follower_path.stat().st_mtime, KST).isoformat(timespec="seconds")
                if follower_path
                else asof,
                source_path=rel(follower_path),
                raw_value=followers_raw,
            )
        )

    return metrics, {
        "latest_performance_report": rel(report_path),
        "latest_analytics_snapshot": rel(overview_path),
        "latest_follower_snapshot": rel(follower_path),
    }


def hogql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def date_window(days: int) -> list[str]:
    today = now_kst().date()
    return [(today - timedelta(days=offset)).isoformat() for offset in reversed(range(days))]


def posthog_config() -> tuple[str, str, str] | None:
    api_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.environ.get("POSTHOG_PROJECT_ID", POSTHOG_PROJECT_ID).strip() or POSTHOG_PROJECT_ID
    host = (
        os.environ.get("POSTHOG_API_HOST")
        or os.environ.get("POSTHOG_HOST")
        or POSTHOG_HOST
    ).strip().rstrip("/")
    if not api_key:
        return None
    return host, project_id, api_key


def run_hogql(query: str, config: tuple[str, str, str]) -> list[list[Any]]:
    host, project_id, api_key = config
    response = requests.post(
        f"{host}/api/projects/{project_id}/query/",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"query": {"kind": "HogQLQuery", "query": query}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("results", [])


def collect_posthog_metrics(days: int, asof: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    config = posthog_config()
    source_meta = {
        "project_id": os.environ.get("POSTHOG_PROJECT_ID", POSTHOG_PROJECT_ID) or POSTHOG_PROJECT_ID,
        "host_filters": [target["host"] for target in POSTHOG_TARGETS],
        "credential_present": bool(config),
    }
    if not config:
        for target in POSTHOG_TARGETS:
            metrics.append(
                no_data_row(
                    target["engine_id"],
                    "posthog_daily_unique_visitors",
                    "visitors_per_day",
                    "posthog_hogql",
                    "POSTHOG_PERSONAL_API_KEY 설정 필요",
                    asof,
                    site=target["site"],
                    host_filter=target["host"],
                )
            )
        return metrics, source_meta

    for target in POSTHOG_TARGETS:
        host_filter = target["host"]
        query = f"""
SELECT
  toDate(timestamp) AS day,
  count() AS events,
  countIf(event = '$pageview') AS pageviews,
  uniq(distinct_id) AS visitors,
  max(timestamp) AS last_seen
FROM events
WHERE timestamp >= now() - INTERVAL {int(days)} DAY
  AND properties.$host = {hogql_string(host_filter)}
GROUP BY day
ORDER BY day ASC
"""
        try:
            rows = run_hogql(query, config)
            by_day = {
                day: {"date": day, "events": 0, "pageviews": 0, "visitors": 0, "last_seen": None}
                for day in date_window(days)
            }
            for row in rows:
                day = str(row[0])
                by_day[day] = {
                    "date": day,
                    "events": int(row[1] or 0),
                    "pageviews": int(row[2] or 0),
                    "visitors": int(row[3] or 0),
                    "last_seen": row[4],
                }
            daily = [by_day[day] for day in sorted(by_day)]
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "posthog_daily_unique_visitors",
                    daily,
                    "visitors_per_day",
                    "live",
                    "posthog_hogql",
                    asof,
                    site=target["site"],
                    host_filter=host_filter,
                    days=days,
                    total_visitors=sum(day["visitors"] for day in daily),
                    total_events=sum(day["events"] for day in daily),
                    total_pageviews=sum(day["pageviews"] for day in daily),
                )
            )
        except requests.HTTPError as exc:
            response = exc.response
            status = response.status_code if response is not None else "unknown"
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "posthog_daily_unique_visitors",
                    None,
                    "visitors_per_day",
                    "error",
                    "posthog_hogql",
                    asof,
                    site=target["site"],
                    host_filter=host_filter,
                    error=f"PostHog HTTP {status}",
                    unlock_path="PostHog Personal API Key 권한(project read/query) 확인 필요",
                )
            )
        except Exception as exc:
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "posthog_daily_unique_visitors",
                    None,
                    "visitors_per_day",
                    "error",
                    "posthog_hogql",
                    asof,
                    site=target["site"],
                    host_filter=host_filter,
                    error=str(exc)[:160],
                    unlock_path="PostHog API 연결/권한 확인 필요",
                )
            )

    return metrics, source_meta


def collect_ga4_metrics(days: int, asof: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    credential_keys = {
        "GA4_SERVICE_ACCOUNT_PATH": bool(os.environ.get("GA4_SERVICE_ACCOUNT_PATH", "").strip()),
        "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()),
        "GOOGLE_OAUTH_CLIENT_SECRET_FILE": bool(os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()),
        "GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN": bool(os.environ.get("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN", "").strip()),
    }
    source_meta: dict[str, Any] = {"credential_keys_present": credential_keys, "attempted": False}
    if not any(credential_keys.values()):
        for target in GA4_TARGETS:
            metrics.append(
                no_data_row(
                    target["engine_id"],
                    "ga4_active_users_1d",
                    "active_users",
                    "ga4_data_api",
                    "GA4 credential 설정 필요",
                    asof,
                    site=target["site"],
                )
            )
        metrics.append(
            no_data_row(
                "R3",
                "ga4_active_users_1d",
                "active_users",
                "ga4_data_api",
                "daysleft.io GA4 property mapping 및 credential 설정 필요",
                asof,
                site="daysleft",
            )
        )
        return metrics, source_meta

    source_meta["attempted"] = True
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.ga4_traffic_report import resolve_access_token, run_report, val

        token, token_source = resolve_access_token()
        source_meta["token_source"] = token_source
        for target in GA4_TARGETS:
            report = run_report(
                target["property"],
                token,
                "today",
                "today",
                ["activeUsers", "screenPageViews"],
                target.get("host"),
            )
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "ga4_active_users_1d",
                    int(val(report, 0)),
                    "active_users",
                    "live",
                    "ga4_data_api",
                    asof,
                    site=target["site"],
                    property=target["property"],
                    host_filter=target.get("host"),
                )
            )
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "ga4_pageviews_1d",
                    int(val(report, 1)),
                    "pageviews",
                    "live",
                    "ga4_data_api",
                    asof,
                    site=target["site"],
                    property=target["property"],
                    host_filter=target.get("host"),
                )
            )
    except BaseException as exc:  # resolve_access_token can raise SystemExit
        source_meta["error"] = str(exc)[:180]
        for target in GA4_TARGETS:
            metrics.append(
                metric_row(
                    target["engine_id"],
                    "ga4_active_users_1d",
                    None,
                    "active_users",
                    "error",
                    "ga4_data_api",
                    asof,
                    site=target["site"],
                    unlock_path="GA4 credential 권한 또는 property access 확인 필요",
                    error=str(exc)[:160],
                )
            )

    metrics.append(
        no_data_row(
            "R3",
            "ga4_active_users_1d",
            "active_users",
            "ga4_data_api",
            "daysleft.io GA4 property mapping 확인 필요",
            asof,
            site="daysleft",
        )
    )
    return metrics, source_meta


def collect_static_no_data(asof: str) -> list[dict[str, Any]]:
    return [
        no_data_row(
            "R1",
            "toss_ad_revenue",
            "KRW",
            "Toss miniapp ads console",
            "owner 콘솔 확인 필요",
            asof,
        ),
        no_data_row(
            "R1",
            "ait_factory_review_revenue_proxy",
            "apps",
            "Apps in Toss console",
            "owner 콘솔에서 앱 생성/심사 상태 확인 필요",
            asof,
        ),
        no_data_row(
            "R3",
            "subscription_revenue",
            "KRW",
            "RevenueCat/Stripe console",
            "RevenueCat placeholder 해소 및 결제 콘솔 연결 필요",
            asof,
        ),
        no_data_row(
            "R4",
            "adsense_revenue",
            "KRW",
            "Google AdSense console",
            "owner 콘솔 확인 필요",
            asof,
            site="kott/toolpick",
        ),
        no_data_row(
            "R4",
            "coupang_affiliate_revenue",
            "KRW",
            "Coupang Partners console",
            "owner 콘솔 확인 필요",
            asof,
            site="toolpick",
        ),
    ]


def build_report(days: int) -> dict[str, Any]:
    load_env()
    generated_at = iso_now()
    metrics: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}

    metrics.extend(collect_static_no_data(generated_at))
    tiktok_metrics, sources["tiktok"] = collect_tiktok_metrics(generated_at)
    posthog_metrics, sources["posthog"] = collect_posthog_metrics(days, generated_at)
    ga4_metrics, sources["ga4"] = collect_ga4_metrics(days, generated_at)
    metrics.extend(tiktok_metrics)
    metrics.extend(posthog_metrics)
    metrics.extend(ga4_metrics)

    engines = []
    for engine_id in ["R1", "R2", "R3", "R4"]:
        engine_metrics = [row for row in metrics if row["engine_id"] == engine_id]
        engines.append(
            {
                "engine_id": engine_id,
                "engine_name": ENGINE_NAMES[engine_id],
                "metrics": engine_metrics,
            }
        )

    live_count = sum(1 for row in metrics if row["status"] == "live")
    error_count = sum(1 for row in metrics if row["status"] == "error")
    no_data_count = sum(1 for row in metrics if row["status"] == "no_data")
    return {
        "schema_version": "revenue_telemetry.v1",
        "generated_at": generated_at,
        "timezone": "Asia/Seoul",
        "days": days,
        "scope": {
            "engines": ["R1", "R2", "R3", "R4"],
            "posthog_project_id": sources["posthog"]["project_id"],
            "posthog_host_filters": sources["posthog"]["host_filters"],
        },
        "summary": {
            "metric_count": len(metrics),
            "live_count": live_count,
            "no_data_count": no_data_count,
            "error_count": error_count,
            "status": "ok" if live_count and not error_count else "degraded",
        },
        "sources": sources,
        "engines": engines,
        "metrics": metrics,
    }


def write_report(report: dict[str, Any]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S_KST")
    stamped = OUT_DIR / f"revenue_telemetry_{stamp}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    LATEST_JSON.write_text(payload, encoding="utf-8")
    stamped.write_text(payload, encoding="utf-8")
    return LATEST_JSON, stamped


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect revenue OS telemetry.")
    parser.add_argument("--days", type=int, default=7, help="Daily PostHog lookback window.")
    args = parser.parse_args()
    days = max(1, min(args.days, 30))
    report = build_report(days)
    latest, stamped = write_report(report)
    posthog_rows = [
        {
            "site": row.get("site"),
            "host_filter": row.get("host_filter"),
            "total_visitors": row.get("total_visitors"),
            "total_events": row.get("total_events"),
            "status": row.get("status"),
        }
        for row in report["metrics"]
        if row["metric"] == "posthog_daily_unique_visitors"
    ]
    print(
        json.dumps(
            {
                "ok": True,
                "latest": rel(latest),
                "stamped": rel(stamped),
                "summary": report["summary"],
                "posthog": posthog_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
