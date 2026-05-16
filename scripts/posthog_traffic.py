# -*- coding: utf-8 -*-
"""PostHog traffic probe for Neo Genesis SBU sites.

The script uses PostHog's query API with a personal API key and returns a
host/site-level event summary. It intentionally prints aggregate counts only.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
OUT_DIR = PROJECT_ROOT / "data" / "sbu-growth"
LATEST_JSON = OUT_DIR / "posthog-traffic-latest.json"
LATEST_MD = OUT_DIR / "posthog-traffic-latest.md"
OWNER_ANALYTICS_DIR = PROJECT_ROOT / "data" / "owner-analytics"
DECISION_EVENT_ALLOWLIST_PATH = OWNER_ANALYTICS_DIR / "decision_event_allowlist.json"

DEFAULT_DECISION_EVENTS = [
    "cta_click",
    "signup_intent",
    "pricing_view",
    "signup_click",
    "demo_request",
    "lead_submit",
    "subscribe_submit",
    "tool_submit",
    "search_submit",
    "filter_apply",
    "compare_select",
    "calculator_run",
    "download_click",
    "outbound_click",
    "outbound_official_click",
    "affiliate_click",
    "copy_link",
]

SITES = [
    ("neogenesis", "neogenesis.app"),
    ("toolpick", "toolpick.dev"),
    ("aiforge", "aiforge.neogenesis.app"),
    ("craftdesk", "craftdesk.neogenesis.app"),
    ("deploystack", "deploystack.neogenesis.app"),
    ("finstack", "finstack.neogenesis.app"),
    ("sellkit", "sellkit.neogenesis.app"),
    ("reviewlab", "review.neogenesis.app"),
    ("ur-wrong", "ur-wrong.com"),
    ("kott", "kott.kr"),
    ("whylab", "whylab.neogenesis.app"),
    ("ethicaai", "ethica.neogenesis.app"),
]


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local", override=False)


def posthog_config() -> tuple[str, str, str]:
    load_env()
    api_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.environ.get("POSTHOG_PROJECT_ID", "").strip()
    host = os.environ.get("POSTHOG_API_HOST", "https://us.posthog.com").strip().rstrip("/")
    if not api_key:
        raise RuntimeError("POSTHOG_PERSONAL_API_KEY is missing")
    if not project_id:
        raise RuntimeError("POSTHOG_PROJECT_ID is missing")
    return host, project_id, api_key


def run_hogql(query: str) -> list[list[Any]]:
    host, project_id, api_key = posthog_config()
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


def decision_events() -> tuple[str, list[str]]:
    """Return the allowlisted PostHog events that count as owner decisions."""
    if DECISION_EVENT_ALLOWLIST_PATH.exists():
        payload = json.loads(DECISION_EVENT_ALLOWLIST_PATH.read_text(encoding="utf-8"))
        events = [str(item) for item in payload.get("numerator_events", []) if str(item).strip()]
        version = str(payload.get("version") or "local-file")
        if events:
            return version, events
    return "fallback-default", DEFAULT_DECISION_EVENTS


def hogql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def site_case_expression() -> str:
    cases = []
    for site_id, host in SITES:
        cases.append(
            "WHEN properties.site_id = '{site_id}' "
            "OR properties.site_domain = '{host}' "
            "OR properties.$host = '{host}' "
            "OR properties.$current_url LIKE '%{host}%' "
            "THEN '{site_id}'".format(site_id=site_id, host=host)
        )
    return "CASE " + " ".join(cases) + " ELSE 'unknown' END"


def fetch_traffic(days: int = 7) -> list[tuple[str, int, int]]:
    """Return rows compatible with scripts.traffic_alert: host, pageviews, users."""
    rows = fetch_site_events(days)
    return [
        (row["site"], row["pageviews"], row["users"])
        for row in sorted(rows, key=lambda item: (item["pageviews"], item["users"]), reverse=True)
    ]


def fetch_site_events(days: int = 7) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    allowlist_version, allowed_events = decision_events()
    allowed_sql = ", ".join(hogql_string(event) for event in allowed_events)
    for site_id, host in SITES:
        query = f"""
SELECT
  count() AS events,
  countIf(event = '$pageview') AS pageviews,
  countIf(event IN ({allowed_sql})) AS decision_events,
  countIf(event != '$pageview') AS legacy_action_events,
  uniq(distinct_id) AS users,
  max(timestamp) AS last_seen
FROM events
WHERE timestamp >= now() - INTERVAL {int(days)} DAY
  AND (
    trim(toString(properties.site_id)) = '{site_id}'
    OR properties.site_domain = '{host}'
    OR properties.$host = '{host}'
    OR properties.$current_url LIKE '%{host}%'
  )
"""
        rows = run_hogql(query)
        if rows:
            row = rows[0]
            results.append({
                "site": site_id,
                "events": int(row[0] or 0),
                "pageviews": int(row[1] or 0),
                "decisionEvents": int(row[2] or 0),
                "actionEvents": int(row[2] or 0),
                "legacyActionEvents": int(row[3] or 0),
                "users": int(row[4] or 0),
                "lastSeen": row[5],
                "allowlistVersion": allowlist_version,
            })
        else:
            results.append({
                "site": site_id,
                "events": 0,
                "pageviews": 0,
                "decisionEvents": 0,
                "actionEvents": 0,
                "legacyActionEvents": 0,
                "users": 0,
                "lastSeen": None,
                "allowlistVersion": allowlist_version,
            })
    return results


def write_report(days: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "generatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "days": days,
        "scope": [site_id for site_id, _host in SITES],
        "passed": any(row["events"] > 0 for row in rows),
        "sitesWithEvents": sum(1 for row in rows if row["events"] > 0),
        "totalEvents": sum(row["events"] for row in rows),
        "totalPageviews": sum(row["pageviews"] for row in rows),
        "totalDecisionEvents": sum(row["decisionEvents"] for row in rows),
        "totalLegacyActionEvents": sum(row["legacyActionEvents"] for row in rows),
        "decisionEventAllowlist": rows[0].get("allowlistVersion") if rows else None,
        "rows": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# PostHog Traffic Probe",
        "",
        f"- days: {days}",
        f"- passed: {report['passed']}",
        f"- sitesWithEvents: {report['sitesWithEvents']}/{len(SITES)}",
        f"- totalEvents: {report['totalEvents']}",
        f"- totalPageviews: {report['totalPageviews']}",
        f"- totalDecisionEvents: {report['totalDecisionEvents']}",
        f"- totalLegacyActionEvents: {report['totalLegacyActionEvents']}",
        f"- decisionEventAllowlist: {report['decisionEventAllowlist']}",
        "",
        "| Site | Events | Pageviews | Decision Events | Legacy Non-Pageview | Users | Last Seen |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {site} | {events} | {pageviews} | {decision_events} | {legacy_actions} | {users} | {last_seen} |".format(
                site=row["site"],
                events=row["events"],
                pageviews=row["pageviews"],
                decision_events=row["decisionEvents"],
                legacy_actions=row["legacyActionEvents"],
                users=row["users"],
                last_seen=row["lastSeen"] or "",
            )
        )
    LATEST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    rows = fetch_site_events(days=args.days)
    report = write_report(args.days, rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
