#!/usr/bin/env python3
"""Live SEO/GEO/analytics gate for all commercial Neo Genesis sites.

The gate intentionally checks the public production surface instead of local files:
home status, robots, sitemap, llms.txt, metadata, schema.org, GA, and PostHog
capture network calls.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SITE_MATRIX = [
    {"id": "toolpick", "name": "ToolPick", "url": "https://www.toolpick.dev/"},
    {"id": "aiforge", "name": "AIForge", "url": "https://aiforge.neogenesis.app/"},
    {"id": "craftdesk", "name": "CraftDesk", "url": "https://craftdesk.neogenesis.app/"},
    {"id": "deploystack", "name": "DeployStack", "url": "https://deploystack.neogenesis.app/"},
    {"id": "finstack", "name": "FinStack", "url": "https://finstack.neogenesis.app/"},
    {"id": "sellkit", "name": "SellKit", "url": "https://sellkit.neogenesis.app/"},
    {"id": "reviewlab", "name": "ReviewLab", "url": "https://review.neogenesis.app/"},
    {"id": "ur-wrong", "name": "UR WRONG", "url": "https://ur-wrong.com/"},
    {"id": "kott", "name": "K-OTT", "url": "https://kott.kr/"},
    {"id": "ethicaai", "name": "EthicaAI", "url": "https://ethica.neogenesis.app/"},
    {"id": "whylab", "name": "WhyLab", "url": "https://whylab.neogenesis.app/"},
    {"id": "portfolio", "name": "Portfolio", "url": "https://heoyesol.kr/"},
    {"id": "neogenesis", "name": "NeoGenesis", "url": "https://neogenesis.app/"},
]


@dataclass
class FetchResult:
    status: int
    text: str
    url: str
    error: str | None = None


def fetch_text(url: str, timeout: int = 20) -> FetchResult:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NeoGenesisLiveQualityAudit/1.0 (+https://neogenesis.app)",
            "Accept": "text/html,application/xml,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchResult(
                status=response.status,
                text=raw.decode(charset, errors="replace"),
                url=response.geturl(),
            )
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return FetchResult(status=exc.code, text=text, url=url, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - audit should continue per site
        return FetchResult(status=0, text="", url=url, error=str(exc))


def absolute_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def find_canonical(html: str) -> str:
    patterns = [
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return match.group(1).strip()
    return ""


def find_meta_description(html: str) -> str:
    patterns = [
        r'<meta[^>]+name=["\']description["\'][^>]+content=(["\'])(.*?)\1',
        r'<meta[^>]+content=(["\'])(.*?)\1[^>]+name=["\']description["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return match.group(2).strip()
    return ""


def has_ga_network(events: list[dict[str, Any]], html: str) -> bool:
    if "googletagmanager.com/gtag/js" in html or "google-analytics.com" in html:
        return True
    return any("googletagmanager.com" in event["url"] or "google-analytics.com" in event["url"] for event in events)


def has_posthog_capture(events: list[dict[str, Any]]) -> bool:
    for event in events:
        url = event["url"]
        if "posthog.com" not in url:
            continue
        if "/capture" in url or "/i/v0/e" in url or "/batch" in url:
            if event["status"] in {200, 202, 204}:
                return True
    return False


async def audit_browser_site(browser: Any, site: dict[str, str], wait_ms: int) -> dict[str, Any]:
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    network_events: list[dict[str, Any]] = []

    def record_response(response: Any) -> None:
        network_events.append({"url": response.url, "status": response.status})

    page.on("response", record_response)
    status = 0
    html = ""
    title = ""
    error: str | None = None
    try:
        response = await page.goto(site["url"], wait_until="networkidle", timeout=45_000)
        status = response.status if response else 0
        await page.wait_for_timeout(wait_ms)
        title = await page.title()
        html = await page.content()
    except Exception as exc:  # noqa: BLE001 - audit should continue per site
        error = str(exc)
    finally:
        await context.close()

    return {
        "status": status,
        "title": title,
        "titleLen": len(title.strip()),
        "htmlLen": len(html),
        "canonical": find_canonical(html),
        "description": find_meta_description(html),
        "descriptionLen": len(find_meta_description(html)),
        "jsonLdCount": len(re.findall(r'application/ld\+json', html, re.I)),
        "gaRuntimeOk": has_ga_network(network_events, html),
        "posthogCaptureOk": has_posthog_capture(network_events),
        "networkEvents": [
            event
            for event in network_events
            if any(host in event["url"] for host in ["posthog.com", "googletagmanager.com", "google-analytics.com"])
        ],
        "error": error,
    }


def audit_static_site(site: dict[str, str]) -> dict[str, Any]:
    base = site["url"]
    robots = fetch_text(absolute_url(base, "robots.txt"))
    sitemap = fetch_text(absolute_url(base, "sitemap.xml"))
    llms = fetch_text(absolute_url(base, "llms.txt"))
    sitemap_url_count = len(re.findall(r"<loc>[^<]+</loc>", sitemap.text, re.I))
    return {
        "robotsStatus": robots.status,
        "robotsHasSitemap": robots.status == 200 and "sitemap:" in robots.text.lower(),
        "sitemapStatus": sitemap.status,
        "sitemapUrlCount": sitemap_url_count,
        "llmsStatus": llms.status,
        "llmsLen": len(llms.text.strip()),
        "llmsWeak": llms.status != 200 or len(llms.text.strip()) < 200,
    }


def site_issues(site: dict[str, str], browser: dict[str, Any], static: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if browser["status"] != 200:
        issues.append("home_status_not_200")
    if browser["titleLen"] < 10:
        issues.append("weak_title")
    if browser["descriptionLen"] < 80:
        issues.append("weak_description")
    if not browser["canonical"]:
        issues.append("missing_canonical")
    if browser["jsonLdCount"] < 1:
        issues.append("missing_jsonld")
    if not browser["gaRuntimeOk"]:
        issues.append("ga_runtime_missing")
    if not browser["posthogCaptureOk"]:
        issues.append("posthog_capture_missing")
    if static["robotsStatus"] != 200 or not static["robotsHasSitemap"]:
        issues.append("robots_missing_sitemap")
    if static["sitemapStatus"] != 200 or static["sitemapUrlCount"] < 1:
        issues.append("sitemap_missing_urls")
    if static["llmsWeak"]:
        issues.append("llms_missing_or_weak")
    return issues


async def run_audit(wait_ms: int, excluded_ids: set[str] | None = None) -> dict[str, Any]:
    excluded_ids = excluded_ids or set()
    site_matrix = [site for site in SITE_MATRIX if site["id"] not in excluded_ids]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        results = []
        for site in site_matrix:
            browser_result = await audit_browser_site(browser, site, wait_ms)
            static_result = audit_static_site(site)
            issues = site_issues(site, browser_result, static_result)
            results.append(
                {
                    "id": site["id"],
                    "name": site["name"],
                    "url": site["url"],
                    "passed": not issues,
                    "issues": issues,
                    "browser": browser_result,
                    "static": static_result,
                }
            )
        await browser.close()

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    passed_count = sum(1 for item in results if item["passed"])
    return {
        "generatedAt": now.isoformat(),
        "siteCount": len(results),
        "passedCount": passed_count,
        "failedCount": len(results) - passed_count,
        "passed": passed_count == len(results),
        "sites": results,
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = datetime.fromisoformat(report["generatedAt"]).strftime("%Y-%m-%dT%H-%M-%S%z")
    slug = slug[:-2] + "-" + slug[-2:]
    json_path = output_dir / f"seo-geo-live-{slug}.json"
    md_path = output_dir / f"seo-geo-live-{slug}.md"
    latest_json = output_dir / "seo-geo-live-latest.json"
    latest_md = output_dir / "seo-geo-live-latest.md"

    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    latest_json.write_text(json_text + "\n", encoding="utf-8")

    lines = [
        "# SBU Full Live SEO/GEO/PostHog Audit",
        "",
        f"- generatedAt: `{report['generatedAt']}`",
        f"- sites: `{report['siteCount']}`",
        f"- passed: `{report['passedCount']}/{report['siteCount']}`",
        f"- overall: `{'PASS' if report['passed'] else 'FAIL'}`",
        "",
        "| Site | Status | Issues | Title | Canonical | JSON-LD | GA | PostHog | llms.txt |",
        "|---|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for site in report["sites"]:
        browser = site["browser"]
        static = site["static"]
        issues = ", ".join(site["issues"]) if site["issues"] else "-"
        lines.append(
            "| {name} | {status} | {issues} | {title_len} | {canonical} | {jsonld} | {ga} | {posthog} | {llms} |".format(
                name=site["name"],
                status=browser["status"],
                issues=issues,
                title_len=browser["titleLen"],
                canonical="yes" if browser["canonical"] else "no",
                jsonld=browser["jsonLdCount"],
                ga="yes" if browser["gaRuntimeOk"] else "no",
                posthog="yes" if browser["posthogCaptureOk"] else "no",
                llms=static["llmsStatus"],
            )
        )
    md_text = "\n".join(lines) + "\n"
    md_path.write_text(md_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    parser.add_argument("--wait-ms", type=int, default=3000, help="Post-load wait for analytics beacons")
    parser.add_argument("--no-write", action="store_true", help="Do not write report files")
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated site IDs to skip, for example: toolpick,ur-wrong,neogenesis",
    )
    args = parser.parse_args()

    excluded_ids = {item.strip() for item in args.exclude.split(",") if item.strip()}
    report = asyncio.run(run_audit(args.wait_ms, excluded_ids))
    if not args.no_write:
        repo_root = Path(__file__).resolve().parents[1]
        write_reports(report, repo_root / "data" / "sbu-growth")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"passed={report['passed']} passedCount={report['passedCount']}/{report['siteCount']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
