"""SBU page audit — same pattern as audit_blog_metadata.py but for the
11 SBU entries. Validates per-SBU:
  - HTTP 200 on /sbu/<slug>
  - Schema.org SoftwareApplication + BreadcrumbList emit
  - Wikidata Q-ID present and the URL resolves
  - HuggingFace / GitHub external links resolve
  - SBU description length 80-300 chars
  - Korean description present (multilingual brand has KO market)

Run: PYTHONIOENCODING=utf-8 python scripts/landing/audit_sbu_pages.py
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SBUS_TS = ROOT / "src/landing/src/lib/data/sbus.ts"


def parse_sbus() -> list[dict]:
    text = SBUS_TS.read_text(encoding="utf-8")
    # Block between SBUS = and ];
    block = text[text.find("SBUS:"):text.find("];", text.find("SBUS:"))]
    sbus = []
    for m in re.finditer(
        r'\{\s*slug:\s*"([^"]+)",\s*name:\s*"([^"]+)"(?:.*?)\s*desc:\s*"((?:[^"\\]|\\.)*)"(?:.*?)\s*url:\s*"([^"]+)"(?:.*?)(?:wikidataQid:\s*"([^"]+)")?\s*,?\s*\}',
        block,
        re.DOTALL,
    ):
        sbus.append({
            "slug": m.group(1),
            "name": m.group(2),
            "desc": m.group(3),
            "url": m.group(4),
            "wikidataQid": m.group(5) or "",
        })
    # Korean description as a separate field
    desc_ko_map = {}
    for m in re.finditer(
        r'slug:\s*"([^"]+)"(?:.*?)descKo:\s*"((?:[^"\\]|\\.)*)"',
        block,
        re.DOTALL,
    ):
        desc_ko_map[m.group(1)] = m.group(2)
    for s in sbus:
        s["descKo"] = desc_ko_map.get(s["slug"], "")
    return sbus


def head_check(url: str, timeout: int = 10) -> tuple[str, int]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "neo-genesis-sbu-audit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "neo-genesis-sbu-audit/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return url, r.status
            except Exception:
                pass
        return url, e.code
    except Exception:
        return url, 0


def audit_sbu_page(slug: str) -> dict:
    """Check the /sbu/<slug> page for Schema emit and 200 status."""
    url = f"https://neogenesis.app/sbu/{slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "neo-genesis-sbu-audit/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": r.status,
                "has_software_app": '"@type":"SoftwareApplication"' in html,
                "has_breadcrumb": '"@type":"BreadcrumbList"' in html,
                "size": len(html),
            }
    except Exception as e:
        return {"url": url, "status": 0, "error": str(e)[:120]}


def main() -> int:
    sbus = parse_sbus()
    print(f"Auditing {len(sbus)} SBUs")
    print()
    issues: list[str] = []

    # Per-SBU page audit
    print(f"{'slug':<14} {'page':>5} {'app':>5} {'crumb':>5} {'desc':>5} {'koDesc':>7} {'qid':>10} {'qid_url':>8}")
    print("-" * 100)
    page_audits = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(audit_sbu_page, s["slug"]): s["slug"] for s in sbus}
        for fut in as_completed(futures):
            slug = futures[fut]
            page_audits[slug] = fut.result()

    qid_check_urls = []
    for s in sbus:
        if s["wikidataQid"]:
            qid_check_urls.append((s["slug"], f"https://www.wikidata.org/wiki/{s['wikidataQid']}"))
    qid_results = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(head_check, url): slug for slug, url in qid_check_urls}
        for fut in as_completed(futures):
            slug = futures[fut]
            url, status = fut.result()
            qid_results[slug] = status

    for s in sbus:
        slug = s["slug"]
        page = page_audits.get(slug, {})
        page_ok = page.get("status") == 200
        app_ok = page.get("has_software_app", False)
        crumb_ok = page.get("has_breadcrumb", False)
        desc_len = len(s["desc"])
        ko_desc_len = len(s["descKo"])
        qid = s["wikidataQid"] or "MISSING"
        qid_status = qid_results.get(slug, 0)

        flags = []
        if not page_ok:
            flags.append(f"page-{page.get('status', 0)}")
            issues.append(f"{slug}: page returns {page.get('status', 0)}")
        if not app_ok:
            flags.append("no-app-schema")
            issues.append(f"{slug}: missing SoftwareApplication Schema")
        if not crumb_ok:
            flags.append("no-breadcrumb")
            issues.append(f"{slug}: missing BreadcrumbList Schema")
        if desc_len < 80 or desc_len > 300:
            flags.append(f"desc-{desc_len}c")
            issues.append(f"{slug}: desc {desc_len} chars (want 80-300)")
        if ko_desc_len < 30:
            flags.append(f"koDesc-{ko_desc_len}c")
            issues.append(f"{slug}: koDesc only {ko_desc_len} chars")
        if qid == "MISSING":
            flags.append("no-qid")
            issues.append(f"{slug}: no Wikidata Q-ID")
        elif qid_status != 200:
            flags.append(f"qid-{qid_status}")
            issues.append(f"{slug}: Wikidata Q-ID {qid} returns {qid_status}")

        flag_str = (" " + ",".join(flags)) if flags else ""
        print(f"  {slug:<14} {'OK' if page_ok else page.get('status', 0):>5} {'Y' if app_ok else 'N':>5} {'Y' if crumb_ok else 'N':>5} {desc_len:>5} {ko_desc_len:>7} {qid:>10} {qid_status:>8}{flag_str}")

    # External brand URL HEAD check
    print()
    print("=== External brand URLs ===")
    brand_urls = sorted({s["url"] for s in sbus})
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(head_check, u): u for u in brand_urls}
        for fut in as_completed(futures):
            url, status = fut.result()
            ok = status in (200, 301, 302, 307, 308, 403)  # 403 often anti-bot but alive
            label = "OK" if ok else f"BAD({status})"
            print(f"  [{label}] {url}")
            if not ok:
                issues.append(f"brand URL {status}: {url}")

    print()
    print("=" * 100)
    print(f"Total issues: {len(issues)}")
    if issues:
        for i in issues[:30]:
            print(f"  - {i}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
