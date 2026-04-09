# -*- coding: utf-8 -*-
"""Weekly traffic alert composed from GA4 and PostHog data."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ga4_traffic_report import SITES, get_access_token, run_report, val
from scripts.posthog_traffic import fetch_traffic


def generate_traffic_report() -> str:
    sa_path = os.environ.get("GA4_SERVICE_ACCOUNT_PATH", "")
    ga4_data = []
    total_ga4_users = 0
    total_ga4_views = 0

    if sa_path and os.path.exists(sa_path):
        with open(sa_path, encoding="utf-8") as f:
            sa = json.load(f)
        token = get_access_token(sa)

        for site in SITES:
            try:
                report = run_report(
                    site["property"],
                    token,
                    "7daysAgo",
                    "today",
                    ["activeUsers", "screenPageViews"],
                    site.get("host"),
                )
                users = int(val(report, 0))
                views = int(val(report, 1))
                if users > 0 or views > 0:
                    ga4_data.append((site["name"], users, views))
                    total_ga4_users += users
                    total_ga4_views += views
            except Exception:
                pass

        ga4_data.sort(key=lambda row: row[1], reverse=True)

    ph_data = fetch_traffic(days=7)
    total_ph_views = sum(int(row[1]) for row in ph_data) if ph_data else 0
    total_ph_users = sum(int(row[2]) for row in ph_data) if ph_data else 0

    now = datetime.now()
    lines = [
        "<b>NEO GENESIS Weekly Traffic Report</b>",
        f"{now.strftime('%Y-%m-%d (%a)')} - last 7 days",
        "",
        "<b>GA4 Totals</b>",
        f"  - Users: {total_ga4_users:,}",
        f"  - Pageviews: {total_ga4_views:,}",
        "",
        "<b>GA4 Top 5 Sites</b>",
    ]

    for idx, (site, users, views) in enumerate(ga4_data[:5], start=1):
        lines.append(f"  {idx}. {site}: {users:,} users / {views:,} views")

    lines.extend(
        [
            "",
            "<b>PostHog Totals</b>",
            f"  - Visitors: {total_ph_users:,}",
            f"  - Pageviews: {total_ph_views:,}",
            "",
            "<b>PostHog Top 5 Hosts</b>",
        ]
    )

    for idx, row in enumerate(ph_data[:5], start=1):
        host = str(row[0] or "Unknown")
        views = int(row[1])
        users = int(row[2])
        lines.append(f"  {idx}. {host[:28]}: {users:,} users / {views:,} views")

    lines.extend(["", "<i>Automated by Antigravity Master Intelligence</i>"])
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_traffic_report())
