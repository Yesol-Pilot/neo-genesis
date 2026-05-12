# -*- coding: utf-8 -*-
"""Weekly traffic alert composed from GA4 and PostHog data."""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ga4_traffic_report import SITES, resolve_access_token, run_report, val
from scripts.posthog_traffic import fetch_traffic


def generate_traffic_report() -> str:
    ga4_data = []
    total_ga4_users = 0
    total_ga4_views = 0

    try:
        token, _token_source = resolve_access_token()
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
    except Exception:
        pass

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
