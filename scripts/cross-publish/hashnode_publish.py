#!/usr/bin/env python3
"""
Hashnode cross-publish — POST 2 prepared markdown files via Hashnode GraphQL API.

Reads HASHNODE_API_KEY + HASHNODE_PUBLICATION_ID from .env.local. Each markdown
file already carries front-matter (title, published, description, tags, canonical_url).

Hashnode GraphQL: https://gql.hashnode.com
Mutation: publishPost (requires PublishPostInput)
Auth: header "Authorization: <PAT>" (no "Bearer" prefix per Hashnode docs)

Usage:
    python scripts/cross-publish/hashnode_publish.py
    python scripts/cross-publish/hashnode_publish.py --dry-run

Idempotent: queries existing publication posts and skips re-publishes of the
same canonical_url.

Updates: .agent/knowledge/cross-publish/canonical_links.json with the published URL.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = REPO_ROOT / ".env.local"
TRACKER = REPO_ROOT / ".agent/knowledge/cross-publish/canonical_links.json"

HASHNODE_GQL = "https://gql.hashnode.com"

POSTS = [
    {
        "slug": "inside-hive-mind",
        "markdown": REPO_ROOT / ".agent/knowledge/cross-publish/hashnode-inside-hive-mind.md",
        "canonical": "https://neogenesis.app/blog/inside-hive-mind",
    },
    {
        "slug": "running-11-saas-products-as-solo-founder-2026",
        "markdown": REPO_ROOT / ".agent/knowledge/cross-publish/hashnode-running-11-saas-products.md",
        "canonical": "https://neogenesis.app/blog/running-11-saas-products-as-solo-founder-2026",
    },
]


def load_env_local() -> dict:
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


def gql(query: str, variables: dict, key: str) -> tuple[int, dict]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(HASHNODE_GQL, data=payload, method="POST")
    req.add_header("authorization", key)
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"raw": str(e)}


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


def existing_canonical_urls(key: str, publication_id: str) -> dict[str, str]:
    """Return {canonical_url: hashnode_post_url} for existing posts in the publication."""
    q = """
    query GetPubPosts($id: ObjectId!) {
      publication(id: $id) {
        posts(first: 50) {
          edges {
            node {
              id
              url
              canonicalUrl
            }
          }
        }
      }
    }
    """
    out: dict[str, str] = {}
    status, data = gql(q, {"id": publication_id}, key)
    if status != 200 or "errors" in data:
        return out
    edges = data.get("data", {}).get("publication", {}).get("posts", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        cu = node.get("canonicalUrl")
        if cu:
            out[cu] = node.get("url", "")
    return out


def publish(key: str, publication_id: str, post: dict, dry_run: bool, existing: dict[str, str]) -> dict:
    fm, body = parse_frontmatter(post["markdown"])
    canonical = post["canonical"]
    if canonical in existing:
        return {"slug": post["slug"], "status": "already-published", "url": existing[canonical]}

    tags_raw = fm.get("tags", "")
    tag_objs = [{"name": t.strip(), "slug": t.strip().lower().replace(" ", "-")} for t in tags_raw.split(",") if t.strip()][:5]

    input_obj = {
        "title": fm.get("title", post["slug"]),
        "publicationId": publication_id,
        "contentMarkdown": body,
        "tags": tag_objs,
        "originalArticleURL": canonical,
        "settings": {"isTableOfContentEnabled": True},
    }
    if "description" in fm:
        input_obj["subtitle"] = fm["description"][:200]

    if dry_run:
        return {"slug": post["slug"], "status": "dry-run", "input": input_obj}

    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { id url slug canonicalUrl }
      }
    }
    """
    status, resp = gql(mutation, {"input": input_obj}, key)
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
            if cp.get("platform") != "Hashnode":
                continue
            if result["status"] == "already-published":
                cp["status"] = "PUBLISHED"
                cp["url"] = result["url"]
                cp["note"] = "verified existing publication"
            elif result["status"] == 200 and "errors" not in result.get("response", {}):
                post = result["response"].get("data", {}).get("publishPost", {}).get("post", {})
                cp["status"] = "PUBLISHED"
                cp["url"] = post.get("url", "")
                cp["hashnode_id"] = post.get("id")
                cp["note"] = "auto-published via GraphQL API"
            else:
                cp["status"] = "FAILED"
                cp["last_error"] = json.dumps(result.get("response", result.get("status")))[:300]
    TRACKER.write_text(json.dumps(tracker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env_local()
    key = env.get("HASHNODE_API_KEY", "")
    publication_id = env.get("HASHNODE_PUBLICATION_ID", "")
    if not key:
        if args.dry_run:
            print("[hashnode] dry-run mode: HASHNODE_API_KEY not in .env.local - using placeholder")
            key = "DRYRUN_PLACEHOLDER"
        else:
            print("[hashnode] ERROR: HASHNODE_API_KEY not in .env.local", file=sys.stderr)
            return 2
    if not publication_id:
        if args.dry_run:
            print("[hashnode] dry-run mode: HASHNODE_PUBLICATION_ID not in .env.local - using placeholder")
            publication_id = "DRYRUN_PUB_ID"
        else:
            print("[hashnode] ERROR: HASHNODE_PUBLICATION_ID not in .env.local", file=sys.stderr)
            print("[hashnode] Find it: query { me { publications(first:1) { edges { node { id } } } } }", file=sys.stderr)
            return 2
    print(f"[hashnode] HASHNODE_API_KEY len={len(key)} prefix={key[:4]}... (redacted)")
    if publication_id:
        print(f"[hashnode] HASHNODE_PUBLICATION_ID len={len(publication_id)}")

    existing = existing_canonical_urls(key, publication_id) if (not args.dry_run and publication_id) else {}
    if existing:
        print(f"[hashnode] found {len(existing)} existing posts with canonical_url set")

    results = []
    for post in POSTS:
        if not post["markdown"].exists():
            print(f"[hashnode] missing source: {post['markdown']}", file=sys.stderr)
            continue
        print(f"[hashnode] publish {post['slug']}...")
        result = publish(key, publication_id, post, args.dry_run, existing)
        status = result.get("status")
        if status == "already-published":
            print(f"[hashnode] {post['slug']}: already published at {result['url']} (skipped)")
        elif status == "dry-run":
            print(f"[hashnode] {post['slug']}: dry-run OK, input keys = {list(result['input'].keys())}, body chars = {len(result['input']['contentMarkdown'])}")
        elif status == 200:
            resp = result["response"]
            if "errors" in resp:
                print(f"[hashnode] {post['slug']}: GraphQL error: {json.dumps(resp['errors'])[:300]}")
            else:
                post_data = resp.get("data", {}).get("publishPost", {}).get("post", {})
                print(f"[hashnode] {post['slug']}: PUBLISHED id={post_data.get('id')} url={post_data.get('url')}")
        else:
            print(f"[hashnode] {post['slug']}: FAIL status={status} resp={json.dumps(result.get('response'))[:300]}")
        results.append(result)

    if not args.dry_run:
        update_tracker(results)
        print(f"[hashnode] tracker updated: {TRACKER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
