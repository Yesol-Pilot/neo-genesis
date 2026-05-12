"""GA4 traffic report with JSON output."""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ga4_traffic_report import SITES, resolve_access_token

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=False)
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "ga4_result.json")
token, token_source = resolve_access_token()

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def run_report(site: dict, start: str, end: str, metrics: list[str]) -> dict:
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "metrics": [{"name": metric} for metric in metrics],
        "keepEmptyRows": True,
    }
    if site.get("host"):
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": "hostName",
                "stringFilter": {"matchType": "EXACT", "value": site["host"]},
            }
        }

    response = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/{site['property']}:runReport",
        headers=headers,
        json=body,
        timeout=15,
    )
    return response.json()


def value(report: dict, idx: int = 0) -> int:
    rows = report.get("rows", [])
    return int(rows[0]["metricValues"][idx]["value"]) if rows else 0


results = {"_meta": {"token_source": token_source}}
for site in SITES:
    try:
        report_7d = run_report(site, "7daysAgo", "yesterday", ["activeUsers", "screenPageViews", "sessions"])
        report_28d = run_report(site, "28daysAgo", "yesterday", ["activeUsers", "screenPageViews", "sessions"])
        report_today = run_report(site, "today", "today", ["activeUsers"])
        results[site["name"]] = {
            "property": site["property"],
            "host": site.get("host"),
            "users_7d": value(report_7d, 0),
            "views_7d": value(report_7d, 1),
            "sessions_7d": value(report_7d, 2),
            "users_28d": value(report_28d, 0),
            "views_28d": value(report_28d, 1),
            "sessions_28d": value(report_28d, 2),
            "users_today": value(report_today, 0),
        }
    except Exception as exc:
        results[site["name"]] = {"error": str(exc)}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUT_PATH}")
