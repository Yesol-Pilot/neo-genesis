"""
Neo Genesis 3rd-Party Citation Monitor (L1)
============================================

외부 권위 매체 + 커뮤니티 + Wikipedia 에서 `neogenesis.app` 또는 브랜드명 mention 을
주간 cron 으로 자동 grep + 신규 mention Telegram alert.

데이터 소스 (모두 무료, API key 불필요):
  - Hacker News (Algolia API)            — https://hn.algolia.com/api/v1/search
  - Reddit (public JSON)                 — https://www.reddit.com/search.json
  - Lobste.rs (public RSS)               — https://lobste.rs/search.rss
  - Wikipedia EN (MediaWiki API)         — https://en.wikipedia.org/w/api.php
  - Wikipedia KO (MediaWiki API)         — https://ko.wikipedia.org/w/api.php
  - Common Crawl Index (URL lookup)      — https://index.commoncrawl.org/

산출:
  - `D:/00.test/neo-genesis/scripts/citation_monitor/citations_3rd_party.sqlite3`
    Table: mentions (id, source, url, title, snippet, found_at, query, raw_json)
  - 신규 mention 발견 시 Telegram alert (NEO_ALERT_BOT_TOKEN + OWNER_CHAT_ID)
  - 주간 보고서 markdown: `D:/00.test/neo-genesis/.agent/knowledge/citation_reports/YYYY-MM-DD.md`

실행:
    python scripts/citation_monitor/monitor_3rd_party_citations.py
    python scripts/citation_monitor/monitor_3rd_party_citations.py --dry-run
    python scripts/citation_monitor/monitor_3rd_party_citations.py --source hn,reddit
    python scripts/citation_monitor/monitor_3rd_party_citations.py --no-alert

cron 등록:
    Windows Scheduled Task: NeoGenesis-Citation-Monitor-Weekly
    매주 월요일 09:30 KST
    Action: python D:/00.test/neo-genesis/scripts/citation_monitor/monitor_3rd_party_citations.py

Reference:
  - 20260512_AI_CORPUS_CITATION_STRATEGY_v1.md §2.L.L1
  - Strategy Lead Claude Opus 4.7 박제

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "citations_3rd_party.sqlite3"
REPORT_DIR = Path(__file__).resolve().parents[2] / ".agent" / "knowledge" / "citation_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "citation_monitor"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 검색 query (모든 brand variant + canonical URL)
QUERIES = [
    "neogenesis.app",        # canonical URL — 가장 강한 trust signal
    "Neo Genesis",           # full brand
    "neogenesislab",         # HF/GitHub handle
    "Yesol Heo",             # founder
]

USER_AGENT = (
    "Neo Genesis Citation Monitor/1.0 "
    "(https://neogenesis.app; research-tool; contact: dpthf1537@gmail.com)"
)


# ──────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────

@dataclass
class Mention:
    source: str          # hn / reddit / lobsters / wikipedia_en / wikipedia_ko / commoncrawl
    url: str
    title: str
    snippet: str
    query: str
    found_at: str
    raw: dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
# 데이터 소스
# ──────────────────────────────────────────────

def _http_get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ! HTTP error on {url}: {e}", file=sys.stderr)
        return b""


def fetch_hn(query: str) -> list[Mention]:
    """Hacker News via Algolia API (free, no auth)."""
    enc = urllib.parse.quote(query)
    url = f"https://hn.algolia.com/api/v1/search?query={enc}&tags=story&hitsPerPage=50"
    body = _http_get(url)
    if not body:
        return []
    try:
        data = json.loads(body)
    except Exception:
        return []
    out: list[Mention] = []
    for hit in data.get("hits", []):
        title = hit.get("title") or ""
        story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        snippet = (hit.get("story_text") or "")[:240]
        out.append(Mention(
            source="hn",
            url=story_url,
            title=title,
            snippet=snippet,
            query=query,
            found_at=datetime.now(timezone.utc).isoformat(),
            raw={"objectID": hit.get("objectID"), "points": hit.get("points"), "author": hit.get("author")},
        ))
    return out


def fetch_reddit(query: str) -> list[Mention]:
    """Reddit search via public JSON (no auth required, rate-limited but OK for weekly)."""
    enc = urllib.parse.quote(query)
    url = f"https://www.reddit.com/search.json?q={enc}&limit=50&sort=new&type=link"
    body = _http_get(url)
    if not body:
        return []
    try:
        data = json.loads(body)
    except Exception:
        return []
    out: list[Mention] = []
    for child in (data.get("data") or {}).get("children", []):
        d = child.get("data") or {}
        out.append(Mention(
            source="reddit",
            url=f"https://reddit.com{d.get('permalink', '')}",
            title=d.get("title", ""),
            snippet=(d.get("selftext") or "")[:240],
            query=query,
            found_at=datetime.now(timezone.utc).isoformat(),
            raw={
                "subreddit": d.get("subreddit"),
                "score": d.get("score"),
                "num_comments": d.get("num_comments"),
                "author": d.get("author"),
            },
        ))
    return out


def fetch_lobsters(query: str) -> list[Mention]:
    """Lobste.rs search via public HTML (RSS not searchable, fallback to HTML scrape)."""
    enc = urllib.parse.quote(query)
    url = f"https://lobste.rs/search?q={enc}&what=stories&order=newest"
    body = _http_get(url)
    if not body:
        return []
    text = body.decode("utf-8", errors="ignore")
    # 간단한 HTML scrape — 상세 parser 는 lxml/bs4 의존성 회피
    pattern = re.compile(
        r'<a class="u-url"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>[^<]+)</a>',
        re.IGNORECASE,
    )
    out: list[Mention] = []
    for m in pattern.finditer(text):
        story_url = m.group("url")
        if not story_url.startswith("http"):
            story_url = f"https://lobste.rs{story_url}"
        out.append(Mention(
            source="lobsters",
            url=story_url,
            title=m.group("title").strip(),
            snippet="",
            query=query,
            found_at=datetime.now(timezone.utc).isoformat(),
        ))
    return out


def fetch_wikipedia(query: str, lang: str = "en") -> list[Mention]:
    """Wikipedia (en/ko) MediaWiki search API (free, no auth)."""
    enc = urllib.parse.quote(query)
    url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={enc}&srlimit=20&format=json"
    )
    body = _http_get(url)
    if not body:
        return []
    try:
        data = json.loads(body)
    except Exception:
        return []
    out: list[Mention] = []
    for hit in (data.get("query") or {}).get("search", []):
        title = hit.get("title", "")
        page_url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", ""))[:240]
        out.append(Mention(
            source=f"wikipedia_{lang}",
            url=page_url,
            title=title,
            snippet=snippet,
            query=query,
            found_at=datetime.now(timezone.utc).isoformat(),
        ))
    return out


def fetch_commoncrawl(query: str) -> list[Mention]:
    """
    Common Crawl Index API — 직전 snapshot 에서 neogenesis.app URLs grep.
    URL 도메인 검색은 무료지만 단일 도메인 lookup 만 효율적 (full-text grep 은 CDX 한계).
    """
    if "neogenesis.app" not in query.lower():
        return []  # 도메인 query 일 때만 CC index lookup
    # 직전 CC index (CC-MAIN-2025-*) — 자동 발견은 별도 API call 필요. 본 stub 은 통과
    # 실제 구현: https://index.commoncrawl.org/collinfo.json 에서 최신 index 발견
    # 본 cron 에서는 매 실행마다 직전 index 1개만 lookup (rate-limit 안전)
    try:
        coll_body = _http_get("https://index.commoncrawl.org/collinfo.json")
        if not coll_body:
            return []
        collections = json.loads(coll_body)
        if not collections:
            return []
        latest = collections[0]  # 최신 index 첫 번째
        index_url = latest.get("cdx-api")
        if not index_url:
            return []
        lookup = f"{index_url}?url=neogenesis.app/*&output=json&limit=100"
        body = _http_get(lookup)
        if not body:
            return []
        out: list[Mention] = []
        for line in body.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            out.append(Mention(
                source="commoncrawl",
                url=rec.get("url", ""),
                title=f"CC-MAIN index: {rec.get('url', '')}",
                snippet=f"status={rec.get('status')} digest={rec.get('digest', '')[:12]}",
                query=query,
                found_at=datetime.now(timezone.utc).isoformat(),
                raw={"timestamp": rec.get("timestamp"), "collection": latest.get("id")},
            ))
        return out
    except Exception as e:
        print(f"  ! Common Crawl lookup error: {e}", file=sys.stderr)
        return []


SOURCES = {
    "hn": fetch_hn,
    "reddit": fetch_reddit,
    "lobsters": fetch_lobsters,
    "wikipedia_en": lambda q: fetch_wikipedia(q, "en"),
    "wikipedia_ko": lambda q: fetch_wikipedia(q, "ko"),
    "commoncrawl": fetch_commoncrawl,
}


# ──────────────────────────────────────────────
# DB
# ──────────────────────────────────────────────

def init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            snippet TEXT,
            query TEXT,
            found_at TEXT NOT NULL,
            raw_json TEXT,
            UNIQUE(source, url, query)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_found_at ON mentions(found_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON mentions(source)")
    conn.commit()
    return conn


def insert_mention(conn: sqlite3.Connection, m: Mention) -> bool:
    """Returns True if NEW row inserted, False if duplicate (already known)."""
    try:
        conn.execute(
            """INSERT INTO mentions (source, url, title, snippet, query, found_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (m.source, m.url, m.title, m.snippet, m.query, m.found_at, json.dumps(m.raw, ensure_ascii=False)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # UNIQUE constraint hit — 이미 알고 있는 mention


# ──────────────────────────────────────────────
# Telegram
# ──────────────────────────────────────────────

def telegram_alert(text: str) -> bool:
    """NEO_ALERT_BOT_TOKEN + OWNER_CHAT_ID 사용. 없으면 stdout 만."""
    token = os.environ.get("NEO_ALERT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("OWNER_CHAT_ID") or os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    if not token or not chat_id:
        print("[NO TELEGRAM CREDS — stdout only]")
        print(text)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  ! Telegram alert error: {e}", file=sys.stderr)
        return False


# ──────────────────────────────────────────────
# 주간 보고서
# ──────────────────────────────────────────────

def write_weekly_report(conn: sqlite3.Connection, new_mentions: list[Mention]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}_3rd_party_citations.md"

    # 전체 누적 통계
    cursor = conn.execute("SELECT source, COUNT(*) FROM mentions GROUP BY source ORDER BY 2 DESC")
    totals = cursor.fetchall()
    cursor = conn.execute("SELECT COUNT(*) FROM mentions")
    grand_total = cursor.fetchone()[0]

    lines = [
        f"# 3rd-Party Citation Report — {today}",
        "",
        f"> 자동 생성: `scripts/citation_monitor/monitor_3rd_party_citations.py`",
        f"> 누적 mentions: **{grand_total}** rows",
        f"> 신규 mentions (이번 run): **{len(new_mentions)}**",
        "",
        "## 누적 by source",
        "",
        "| source | count |",
        "|---|---|",
    ]
    for source, count in totals:
        lines.append(f"| {source} | {count} |")
    lines.append("")

    if new_mentions:
        lines.append("## 신규 mentions (이번 run)")
        lines.append("")
        for m in new_mentions:
            lines.append(f"### [{m.source}] {m.title}")
            lines.append(f"- URL: {m.url}")
            lines.append(f"- query: `{m.query}`")
            if m.snippet:
                lines.append(f"- snippet: {m.snippet}")
            lines.append("")
    else:
        lines.append("## 신규 mentions — 0건 (이번 run 변동 없음)")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Neo Genesis 3rd-party citation monitor")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 수집만")
    parser.add_argument("--source", default="all", help="comma-separated source filter (default=all)")
    parser.add_argument("--no-alert", action="store_true", help="Telegram alert 비활성")
    args = parser.parse_args()

    requested_sources = (
        list(SOURCES.keys())
        if args.source == "all"
        else [s.strip() for s in args.source.split(",") if s.strip() in SOURCES]
    )
    if not requested_sources:
        print(f"! No valid sources. Choices: {list(SOURCES.keys())}", file=sys.stderr)
        return 2

    print(f"[citation_monitor] run start {datetime.now(timezone.utc).isoformat()}")
    print(f"[citation_monitor] sources: {requested_sources}")
    print(f"[citation_monitor] queries: {QUERIES}")
    print(f"[citation_monitor] dry-run: {args.dry_run}")

    all_mentions: list[Mention] = []
    new_mentions: list[Mention] = []

    conn = None if args.dry_run else init_db(DB_FILE)

    for source_name in requested_sources:
        fetcher = SOURCES[source_name]
        for query in QUERIES:
            print(f"  → {source_name} :: {query}")
            try:
                results = fetcher(query)
            except Exception as e:
                print(f"    ! fetch error: {e}", file=sys.stderr)
                continue
            for m in results:
                all_mentions.append(m)
                if conn is not None:
                    if insert_mention(conn, m):
                        new_mentions.append(m)
            time.sleep(1.5)  # rate-limit politeness

    print(f"[citation_monitor] total mentions returned: {len(all_mentions)}")
    print(f"[citation_monitor] new (after dedup):       {len(new_mentions)}")

    if conn is not None:
        report_path = write_weekly_report(conn, new_mentions)
        print(f"[citation_monitor] report: {report_path}")

        if new_mentions and not args.no_alert:
            alert_lines = [f"🔍 Neo Genesis 신규 3rd-party citation {len(new_mentions)}건"]
            for m in new_mentions[:5]:  # 상위 5건만
                alert_lines.append(f"• [{m.source}] {m.title[:80]}")
                alert_lines.append(f"  {m.url}")
            if len(new_mentions) > 5:
                alert_lines.append(f"... +{len(new_mentions) - 5}건 더 (report 참조)")
            alert_lines.append(f"\n📍 {report_path}")
            telegram_alert("\n".join(alert_lines))

        conn.close()

    print(f"[citation_monitor] done {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
