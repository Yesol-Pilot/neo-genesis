#!/usr/bin/env python3
"""
dev.to cross-publish — POST 2 prepared markdown files via dev.to API.

Reads DEVTO_API_KEY from .env.local. Each markdown file already carries
front-matter (title, published, description, tags, canonical_url, cover_image, series).
The dev.to API accepts the markdown body_markdown directly with title/tags/canonical
extracted from front-matter or passed explicitly.

Usage:
    python scripts/cross-publish/devto_publish.py
    python scripts/cross-publish/devto_publish.py --dry-run

Idempotent: checks the user's existing dev.to articles and skips re-posts of the
same canonical_url.

Updates: .agent/knowledge/cross-publish/canonical_links.json with the published URL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = REPO_ROOT / ".env.local"
TRACKER = REPO_ROOT / ".agent/knowledge/cross-publish/canonical_links.json"

POSTS = [
    {
        "slug": "inside-hive-mind",
        "markdown": REPO_ROOT / ".agent/knowledge/cross-publish/devto-inside-hive-mind.md",
        "canonical": "https://neogenesis.app/blog/inside-hive-mind",
    },
    {
        "slug": "running-11-saas-products-as-solo-founder-2026",
        "markdown": REPO_ROOT / ".agent/knowledge/cross-publish/devto-running-11-saas-products.md",
        "canonical": "https://neogenesis.app/blog/running-11-saas-products-as-solo-founder-2026",
    },
]


def load_env_local() -> dict:
    """Parse .env.local for DEVTO_API_KEY (and any future keys)."""
    env: dict = {}
    if not ENV_LOCAL.exists():
        return env
    for raw in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def api_request(path: str, key: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict | list]:
    url = f"https://dev.to/api{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("api-key", key)
    req.add_header("accept", "application/vnd.forem.api-v1+json")
    if body:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(payload)
            except json.JSONDecodeError:
                return resp.status, payload  # type: ignore[return-value]
    except urllib.error.HTTPError as e:
        try:
            payload = e.read().decode("utf-8")
            try:
                return e.code, json.loads(payload)
            except json.JSONDecodeError:
                return e.code, {"raw": payload}
        except Exception:
            return e.code, {"error": str(e)}


def existing_urls(key: str) -> dict[str, str]:
    """Return {canonical_url: dev_to_url} for the user's existing articles, where set."""
    out: dict[str, str] = {}
    page = 1
    while True:
        status, data = api_request(f"/articles/me?page={page}&per_page=50", key)
        if status != 200 or not isinstance(data, list) or not data:
            break
        for art in data:
            cu = art.get("canonical_url")
            if cu:
                out[cu] = art.get("url", "")
        page += 1
        if len(data) < 50:
            break
    return out


def parse_frontmatter(md_path: Path) -> tuple[dict, str]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm_block = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    fm: dict = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def publish(key: str, post: dict, dry_run: bool, existing: dict[str, str]) -> dict:
    fm, body = parse_frontmatter(post["markdown"])
    canonical = post["canonical"]
    if canonical in existing:
        return {"slug": post["slug"], "status": "already-published", "url": existing[canonical]}

    article_payload = {
        "article": {
            "title": fm.get("title", post["slug"]),
            "published": True,
            "body_markdown": body,
            "canonical_url": canonical,
            "tags": [t.strip() for t in fm.get("tags", "").split(",") if t.strip()][:4],
        }
    }
    if "description" in fm:
        article_payload["article"]["description"] = fm["description"]
    # NOTE: main_image and series fields trigger 403 on this account state.
    # Dropped from payload; cover_image is auto-generated by dev.to from the
    # canonical_url's og:image. Series can be set later in the dev.to UI.

    if dry_run:
        return {"slug": post["slug"], "status": "dry-run", "payload": article_payload}

    status, resp = api_request("/articles", key, method="POST", body=article_payload)
    return {"slug": post["slug"], "status": status, "response": resp}


def update_tracker(results: list[dict]) -> None:
    if not TRACKER.exists():
        return
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    by_slug = {r["slug"]: r for r in results}
    for entry in tracker.get("posts", []):
        slug = entry["slug"]
        if slug not in by_slug:
            continue
        result = by_slug[slug]
        for cp in entry.get("cross_published", []):
            if cp.get("platform") != "dev.to":
                continue
            if result["status"] == "already-published":
                cp["status"] = "PUBLISHED"
                cp["url"] = result["url"]
                cp["note"] = "verified existing publication 2026-05-04"
            elif result["status"] in (200, 201):
                cp["status"] = "PUBLISHED"
                cp["url"] = result["response"].get("url", "")
                cp["note"] = "auto-published via API 2026-05-04"
                cp["dev_to_id"] = result["response"].get("id")
            else:
                cp["status"] = "FAILED"
                cp["last_error"] = str(result.get("response", result.get("status")))
    TRACKER.write_text(json.dumps(tracker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env_local()
    key = env.get("DEVTO_API_KEY", "")
    if not key:
        print("[devto] ERROR: DEVTO_API_KEY not found in .env.local", file=sys.stderr)
        return 2
    print(f"[devto] DEVTO_API_KEY len={len(key)} prefix={key[:4]}... (redacted)")

    existing = existing_urls(key) if not args.dry_run else {}
    if existing:
        print(f"[devto] found {len(existing)} existing articles with canonical_url set")

    results = []
    for post in POSTS:
        if not post["markdown"].exists():
            print(f"[devto] missing source: {post['markdown']}", file=sys.stderr)
            continue
        print(f"[devto] publish {post['slug']}...")
        result = publish(key, post, args.dry_run, existing)
        status = result.get("status")
        if status == "already-published":
            print(f"[devto] {post['slug']}: already published at {result['url']} (skipped)")
        elif status == "dry-run":
            print(f"[devto] {post['slug']}: dry-run OK, payload keys = {list(result['payload']['article'].keys())}")
        elif status in (200, 201):
            url = result["response"].get("url", "")
            article_id = result["response"].get("id")
            print(f"[devto] {post['slug']}: PUBLISHED id={article_id} url={url}")
        else:
            print(f"[devto] {post['slug']}: FAIL status={status}")
            err_detail = result.get("response")
            if err_detail:
                print(f"[devto]   error detail: {json.dumps(err_detail, ensure_ascii=False)[:500]}")
        results.append(result)

    if not args.dry_run:
        update_tracker(results)
        print(f"[devto] tracker updated: {TRACKER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
