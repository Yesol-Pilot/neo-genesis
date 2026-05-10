# -*- coding: utf-8 -*-
"""PostHog traffic probe for Neo Genesis SBU sites.

The script uses PostHog's query API with a personal API key and returns a
host/site-level event summary. It intentionally prints aggregate counts only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "sbu-growth"
LATEST_JSON = OUT_DIR / "posthog-traffic-latest.json"
LATEST_MD = OUT_DIR / "posthog-traffic-latest.md"

SITES = [
    ("aiforge", "aiforge.neogenesis.app"),
    ("craftdesk", "craftdesk.neogenesis.app"),
    ("deploystack", "deploystack.neogenesis.app"),
    ("finstack", "finstack.neogenesis.app"),
    ("sellkit", "sellkit.neogenesis.app"),
    ("reviewlab", "review.neogenesis.app"),
    ("kott", "k-ott.com"),
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
    site_expr = site_case_expression()
    query = f"""
SELECT
  {site_expr} AS site,
  countIf(event = '$pageview') AS pageviews,
  uniq(distinct_id) AS users
FROM events
WHERE timestamp >= now() - INTERVAL {int(days)} DAY
  AND (
    properties.site_id IN ({", ".join("'" + site_id + "'" for site_id, _ in SITES)})
    OR properties.site_domain IN ({", ".join("'" + host + "'" for _, host in SITES)})
    OR properties.$host IN ({", ".join("'" + host + "'" for _, host in SITES)})
    OR properties.$current_url LIKE '%neogenesis.app%'
    OR properties.$current_url LIKE '%k-ott.com%'
  )
GROUP BY site
ORDER BY pageviews DESC, users DESC
"""
    rows = run_hogql(query)
    return [(str(row[0]), int(row[1] or 0), int(row[2] or 0)) for row in rows]


def fetch_site_events(days: int = 7) -> list[dict[str, Any]]:
    site_expr = site_case_expression()
    query = f"""
SELECT
  {site_expr} AS site,
  count() AS events,
  countIf(event = '$pageview') AS pageviews,
  countIf(event != '$pageview') AS action_events,
  uniq(distinct_id) AS users,
  max(timestamp) AS last_seen
FROM events
WHERE timestamp >= now() - INTERVAL {int(days)} DAY
  AND (
    properties.site_id IN ({", ".join("'" + site_id + "'" for site_id, _ in SITES)})
    OR properties.site_domain IN ({", ".join("'" + host + "'" for _, host in SITES)})
    OR properties.$host IN ({", ".join("'" + host + "'" for _, host in SITES)})
    OR properties.$current_url LIKE '%neogenesis.app%'
    OR properties.$current_url LIKE '%k-ott.com%'
  )
GROUP BY site
ORDER BY events DESC, users DESC
"""
    rows = run_hogql(query)
    by_site = {
        str(row[0]): {
            "site": str(row[0]),
            "events": int(row[1] or 0),
            "pageviews": int(row[2] or 0),
            "actionEvents": int(row[3] or 0),
            "users": int(row[4] or 0),
            "lastSeen": row[5],
        }
        for row in rows
    }
    return [
        by_site.get(site_id, {
            "site": site_id,
            "events": 0,
            "pageviews": 0,
            "actionEvents": 0,
            "users": 0,
            "lastSeen": None,
        })
        for site_id, _host in SITES
    ]


def write_report(days: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "days": days,
        "scope": [site_id for site_id, _host in SITES],
        "passed": any(row["events"] > 0 for row in rows),
        "sitesWithEvents": sum(1 for row in rows if row["events"] > 0),
        "totalEvents": sum(row["events"] for row in rows),
        "totalPageviews": sum(row["pageviews"] for row in rows),
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
        "",
        "| Site | Events | Pageviews | Actions | Users | Last Seen |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {site} | {events} | {pageviews} | {actions} | {users} | {last_seen} |".format(
                site=row["site"],
                events=row["events"],
                pageviews=row["pageviews"],
                actions=row["actionEvents"],
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
