"""Neo Genesis blog auto-generation pipeline.

Sense -> Think -> Quality -> Append -> Commit -> Deploy -> IndexNow -> Log.

Usage:
    python run_pipeline.py                       # full autonomous run
    python run_pipeline.py --dry-run             # generate + validate, no commit/deploy
    python run_pipeline.py --topic "..."         # manual topic override
    python run_pipeline.py --provider gemini     # force a specific LLM provider
    python run_pipeline.py --no-deploy           # commit + push but no Vercel/IndexNow
    python run_pipeline.py --locale ko           # force Korean post

Requires environment (auto-loaded from .env.local then .env):
    GEMINI_API_KEY (preferred — free tier)
    ANTHROPIC_API_KEY (fallback)
    OPENAI_API_KEY (fallback)
    VERCEL_DEPLOY_HOOK (optional — if set, triggers deploy via webhook)

Cost cap: $0.10 per run. Auto-abort if exceeded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from topic_gap_analyzer import (  # noqa: E402
    TopicCandidate,
    build_candidates,
    load_existing_blog_slugs,
    load_press_release_slugs,
    load_research_slugs,
    select_topic,
)
from v_score_validator import THRESHOLD, format_result, validate_post  # noqa: E402


SBUS_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "sbus.ts"
BLOG_CONTENT_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "blog-content.ts"
LANDING_DIR = REPO / "src" / "landing"
LOG_FILE = REPO / ".agent" / "knowledge" / "blog_autogen_log.jsonl"
PROMPT_FILE = ROOT / "prompts" / "draft_post.md"
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

MAX_COST_USD = 0.10
COST_PER_TOKEN = {
    # USD per 1K tokens (output, conservative)
    "gemini-2.5-flash": 0.0,        # free tier
    "gemini-2.5-flash-paid": 0.0003,
    "gemini-2.5-pro": 0.005,
    "claude-haiku-4-5": 0.001,
    "gpt-4o-mini": 0.0006,
}

INDEXNOW_KEY = "68833447363a462a612e658317313cbc"
INDEXNOW_HOST = "neogenesis.app"


# ─────────────────────────────────────────────
# Env loading
# ─────────────────────────────────────────────

def _load_env_files() -> None:
    """Load .env.local then .env, allowing later override of empty values."""
    for fname in (".env.local", ".env"):
        path = REPO / fname
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and (k not in os.environ or not os.environ[k].strip()):
                        os.environ[k] = v
        except Exception:
            pass


# ─────────────────────────────────────────────
# LLM provider chain
# ─────────────────────────────────────────────

@dataclass
class LLMResult:
    provider: str
    model: str
    text: str
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


def _http_post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def call_gemini(system_prompt: str, user_prompt: str, model: str = "gemini-2.5-flash") -> LLMResult:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return LLMResult(provider="gemini", model=model, text="", error="GEMINI_API_KEY missing")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.6,
            "topP": 0.95,
            "maxOutputTokens": 16384,
            "responseMimeType": "application/json",
        },
    }
    try:
        resp = _http_post_json(url, {"Content-Type": "application/json"}, body, timeout=180)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = ""
        return LLMResult(provider="gemini", model=model, text="", error=f"HTTP {e.code}: {err_body}")
    except Exception as e:
        return LLMResult(provider="gemini", model=model, text="", error=f"{type(e).__name__}: {e}")
    candidates = resp.get("candidates", [])
    if not candidates:
        return LLMResult(provider="gemini", model=model, text="", error=f"empty candidates: {str(resp)[:300]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    tokens = resp.get("usageMetadata", {}).get("candidatesTokenCount", 0) or 0
    cost = (tokens / 1000.0) * COST_PER_TOKEN.get(model, 0.0)
    return LLMResult(provider="gemini", model=model, text=text, output_tokens=tokens, cost_usd=cost)


def call_anthropic(system_prompt: str, user_prompt: str, model: str = "claude-haiku-4-5") -> LLMResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return LLMResult(provider="anthropic", model=model, text="", error="ANTHROPIC_API_KEY missing")
    body = {
        "model": model,
        "system": system_prompt,
        "max_tokens": 8192,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    try:
        resp = _http_post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            body,
            timeout=180,
        )
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = ""
        return LLMResult(provider="anthropic", model=model, text="", error=f"HTTP {e.code}: {err_body}")
    except Exception as e:
        return LLMResult(provider="anthropic", model=model, text="", error=f"{type(e).__name__}: {e}")
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    tokens = resp.get("usage", {}).get("output_tokens", 0) or 0
    cost = (tokens / 1000.0) * COST_PER_TOKEN.get(model, 0.001)
    return LLMResult(provider="anthropic", model=model, text=text, output_tokens=tokens, cost_usd=cost)


def call_openai(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> LLMResult:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-local"):
        return LLMResult(provider="openai", model=model, text="", error="OPENAI_API_KEY missing or LiteLLM stub")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.55,
        "max_tokens": 8192,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = _http_post_json(
            "https://api.openai.com/v1/chat/completions",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            body,
            timeout=180,
        )
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = ""
        return LLMResult(provider="openai", model=model, text="", error=f"HTTP {e.code}: {err_body}")
    except Exception as e:
        return LLMResult(provider="openai", model=model, text="", error=f"{type(e).__name__}: {e}")
    choices = resp.get("choices", [])
    text = choices[0]["message"]["content"] if choices else ""
    tokens = resp.get("usage", {}).get("completion_tokens", 0) or 0
    cost = (tokens / 1000.0) * COST_PER_TOKEN.get(model, 0.0006)
    return LLMResult(provider="openai", model=model, text=text, output_tokens=tokens, cost_usd=cost)


PROVIDER_CHAIN = [
    ("gemini-flash-free", lambda sp, up: call_gemini(sp, up, "gemini-2.5-flash")),
    ("gemini-flash", lambda sp, up: call_gemini(sp, up, "gemini-flash-latest")),
    ("gemini-pro", lambda sp, up: call_gemini(sp, up, "gemini-2.5-pro")),
    ("claude-haiku", lambda sp, up: call_anthropic(sp, up, "claude-haiku-4-5")),
    ("openai-mini", lambda sp, up: call_openai(sp, up, "gpt-4o-mini")),
]


# ─────────────────────────────────────────────
# Prompt assembly + JSON repair
# ─────────────────────────────────────────────

def build_user_prompt(
    candidate: TopicCandidate,
    existing_blog: list[tuple[str, str]],
    research_assets: list[tuple[str, str]],
    press_releases: list[tuple[str, str]],
    sbus: list[tuple[str, str]],
    locale: str,
) -> str:
    sections: list[str] = [
        "## Topic brief",
        f"- target locale: {locale}",
        f"- proposed slug (you may refine, but cannot match any existing slug): {candidate.suggested_slug}",
        f"- title hint: {candidate.title_hint}",
        f"- source: {candidate.source}",
        f"- rationale: {candidate.rationale}",
    ]
    if candidate.sample_prompt:
        sections.append(f"- LLM probe prompt this post must answer: {candidate.sample_prompt!r}")
    if candidate.mention_rate_pct is not None:
        sections.append(f"- current LLM mention rate: {candidate.mention_rate_pct:.1f}%")

    sections.append("\n## Existing /blog slugs (do NOT duplicate; cross-link 3+ as relatedPosts):")
    for slug, title in existing_blog:
        sections.append(f"- /blog/{slug} — {title}")

    sections.append("\n## Existing /sbu slugs (cross-link in body where natural):")
    for slug, title in sbus:
        sections.append(f"- /sbu/{slug} — {title}")

    sections.append("\n## Existing /data/research slugs (use as 1st-party citations):")
    for slug, title in research_assets[:20]:
        sections.append(f"- /data/research/{slug} — {title}")

    sections.append("\n## Existing /press slugs (cross-link if topical):")
    for slug, title in press_releases[:10]:
        sections.append(f"- /press/{slug} — {title}")

    sections.append("\n## Wikidata Q-IDs available for `mentions`:")
    sections.append(
        "Q139569680 Neo Genesis | Q139569708 Yesol Heo | Q139569710 UR WRONG | "
        "Q139569711 ToolPick | Q139569712 ReviewLab | Q139569715 K-OTT | "
        "Q139569716 WhyLab | Q139569718 EthicaAI | Q139569720 FinStack | "
        "Q139569724 AIForge | Q139569725 SellKit | Q139569726 DeployStack | "
        "Q139569727 CraftDesk"
    )

    sections.append("\n## Final instruction")
    sections.append(
        "Produce the JSON object now. wordCount must be the actual word count of the body, "
        "not a placeholder. Body must contain >= 10 specific numerical signals. Do not hallucinate citations."
    )
    return "\n".join(sections)


def extract_json(raw: str) -> Optional[dict[str, Any]]:
    """Extract the largest JSON object from raw model text. Tolerant of fenced output."""
    if not raw:
        return None
    # Strip leading/trailing whitespace and code fences
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
    # Find first { and last }
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        return None
    candidate = s[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        # Try removing trailing commas before } or ]
        candidate2 = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate2)
        except Exception:
            return None


# ─────────────────────────────────────────────
# Citation URL verification
# ─────────────────────────────────────────────

def head_check(url: str, timeout: int = 10) -> bool:
    UA = "Mozilla/5.0 (compatible; NeoGenesisBlogAutogen/1.0; +https://neogenesis.app)"
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200 <= r.status < 400
        except urllib.error.HTTPError as e:
            # 405/403 on HEAD — try GET. Other HTTP errors mean the URL is genuinely bad.
            if method == "HEAD" and e.code in (403, 405):
                continue
            return False
        except Exception:
            if method == "HEAD":
                continue
            return False
    return False


def verify_citations(post: dict[str, Any], skip: bool = False) -> list[str]:
    """Return list of dead URLs. Empty list -> all OK."""
    dead: list[str] = []
    if skip:
        return dead
    for c in post.get("citations", []) or []:
        url = c.get("url", "")
        if not url.startswith("http"):
            continue
        if not head_check(url):
            dead.append(url)
    return dead


# ─────────────────────────────────────────────
# TS file mutation (atomic, idempotent)
# ─────────────────────────────────────────────

def ts_string_literal(value: str) -> str:
    """Encode a string for TypeScript (double-quoted)."""
    return json.dumps(value, ensure_ascii=False)


def render_blog_post_metadata_ts(post: dict[str, Any]) -> str:
    """Render the BlogPost metadata entry as TS source."""
    today = dt.date.today().isoformat()
    published = post.get("publishedAt") or today
    updated = post.get("updatedAt") or today
    return (
        "    {\n"
        f"        slug: {ts_string_literal(post['slug'])},\n"
        f"        title: {ts_string_literal(post['title'])},\n"
        f"        summary: {ts_string_literal(post['summary'])},\n"
        f"        publishedAt: {ts_string_literal(published)},\n"
        f"        updatedAt: {ts_string_literal(updated)},\n"
        f"        category: {ts_string_literal(post.get('category', 'engineering'))},\n"
        "    },\n"
    )


def _render_section_ts(s: dict[str, Any]) -> str:
    t = s.get("type", "p")
    out = "            {"
    out += f' type: "{t}"'
    if s.get("text") is not None:
        out += f", text: {ts_string_literal(s['text'])}"
    if s.get("items"):
        items_rendered = ", ".join(ts_string_literal(it) for it in s["items"])
        out += f", items: [{items_rendered}]"
    if s.get("lang"):
        out += f", lang: {ts_string_literal(s['lang'])}"
    out += " },\n"
    return out


def render_blog_content_ts(post: dict[str, Any]) -> str:
    """Render a BlogContent entry as TS source."""
    parts: list[str] = []
    parts.append("    {\n")
    parts.append(f"        slug: {ts_string_literal(post['slug'])},\n")
    parts.append(f"        lead: {ts_string_literal(post['lead'])},\n")
    parts.append(f"        readingTime: {ts_string_literal(post.get('readingTime', '12 min read'))},\n")
    parts.append(f"        wordCount: {int(post.get('wordCount', 1500))},\n")
    parts.append("        keywords: [\n")
    for kw in post.get("keywords", []) or []:
        parts.append(f"            {ts_string_literal(kw)},\n")
    parts.append("        ],\n")
    parts.append(f"        articleSection: {ts_string_literal(post.get('articleSection', 'Engineering'))},\n")
    if post.get("mentions"):
        parts.append("        mentions: [\n")
        for m in post["mentions"]:
            parts.append(
                f"            {{ name: {ts_string_literal(m['name'])}, url: {ts_string_literal(m['url'])} }},\n"
            )
        parts.append("        ],\n")
    parts.append("        sections: [\n")
    for s in post.get("sections", []) or []:
        parts.append(_render_section_ts(s))
    parts.append("        ],\n")
    parts.append("        citations: [\n")
    for c in post.get("citations", []) or []:
        parts.append(
            f"            {{ label: {ts_string_literal(c['label'])}, url: {ts_string_literal(c['url'])} }},\n"
        )
    parts.append("        ],\n")
    if post.get("relatedPosts"):
        rendered = ", ".join(ts_string_literal(s) for s in post["relatedPosts"])
        parts.append(f"        relatedPosts: [{rendered}],\n")
    if post.get("faq"):
        parts.append("        faq: [\n")
        for q in post["faq"]:
            parts.append("            {\n")
            parts.append(f"                question: {ts_string_literal(q['question'])},\n")
            parts.append(f"                answer: {ts_string_literal(q['answer'])},\n")
            parts.append("            },\n")
        parts.append("        ],\n")
    parts.append("    },\n")
    return "".join(parts)


def append_blog_content(post: dict[str, Any]) -> None:
    """Insert a BlogContent entry just before the final `];` of BLOG_CONTENT array."""
    text = BLOG_CONTENT_TS.read_text(encoding="utf-8")
    if f'slug: "{post["slug"]}"' in text:
        return  # idempotent: already exists
    # Find the last `];\n` that closes BLOG_CONTENT array
    # The pattern is `\n];\n` after the last entry
    idx = text.rfind("];")
    if idx < 0:
        raise RuntimeError("BLOG_CONTENT array close `];` not found")
    rendered = render_blog_content_ts(post)
    new_text = text[:idx] + rendered + text[idx:]
    tmp = BLOG_CONTENT_TS.with_suffix(".ts.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(BLOG_CONTENT_TS)


def append_blog_post_metadata(post: dict[str, Any]) -> None:
    """Insert a BlogPost metadata entry before the closing `];` of BLOG_POSTS array."""
    text = SBUS_TS.read_text(encoding="utf-8")
    if f'slug: "{post["slug"]}"' in text:
        return
    blog_idx = text.find("BLOG_POSTS:")
    if blog_idx < 0:
        # Try alternative: `BLOG_POSTS = [`
        blog_idx = text.find("BLOG_POSTS")
    if blog_idx < 0:
        raise RuntimeError("BLOG_POSTS array not found")
    # Find closing `];` AFTER blog_idx
    rest = text[blog_idx:]
    close_offset = rest.find("];")
    if close_offset < 0:
        raise RuntimeError("BLOG_POSTS closing `];` not found")
    abs_close = blog_idx + close_offset
    rendered = render_blog_post_metadata_ts(post)
    new_text = text[:abs_close] + rendered + text[abs_close:]
    tmp = SBUS_TS.with_suffix(".ts.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(SBUS_TS)


# ─────────────────────────────────────────────
# Git + Vercel + IndexNow
# ─────────────────────────────────────────────

def run_git(args: list[str], cwd: Path = REPO) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def git_commit_push(post: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {"status": "skipped (dry-run)"}
    # IMPORTANT: SBUS_TS and BLOG_CONTENT_TS live inside `src/landing/`, which is
    # a SEPARATE git repository (Yesol-Pilot/landing) ignored by neo-genesis main.
    # Running `git add` from neo-genesis main fails with
    # "The following paths are ignored by one of your .gitignore files: src/landing".
    # All git operations must run with cwd=LANDING_DIR and use paths relative to
    # the landing repo root.
    sbus_rel = SBUS_TS.relative_to(LANDING_DIR).as_posix()
    blog_rel = BLOG_CONTENT_TS.relative_to(LANDING_DIR).as_posix()
    rc, _, err = run_git(["add", sbus_rel, blog_rel], cwd=LANDING_DIR)
    if rc != 0:
        return {"status": "git_add_failed", "stderr": err}
    rc, status, _ = run_git(["status", "--porcelain"], cwd=LANDING_DIR)
    if rc != 0 or not status.strip():
        return {"status": "no_changes"}
    msg = (
        f"feat(blog): autogenerate {post['slug']}\n\n"
        f"V-Score gate passed. Topic source: {post.get('_meta', {}).get('source', 'manual')}.\n"
        f"Word count {post.get('wordCount', 0)} | citations {len(post.get('citations', []))} | "
        f"FAQ {len(post.get('faq', []))}.\n\n"
        f"Pipeline: scripts/blog_autogen/run_pipeline.py\n"
        f"SSOT: .agent/knowledge/blog_autogen_pipeline_v1.md"
    )
    rc, _, err = run_git(["commit", "-m", msg], cwd=LANDING_DIR)
    if rc != 0:
        return {"status": "git_commit_failed", "stderr": err}
    rc, head, _ = run_git(["rev-parse", "HEAD"], cwd=LANDING_DIR)
    rc2, _, perr = run_git(["push", "origin", "HEAD"], cwd=LANDING_DIR)
    return {
        "status": "ok" if rc2 == 0 else "push_failed",
        "commit": head.strip(),
        "push_stderr": perr if rc2 != 0 else "",
    }


def trigger_vercel_deploy(dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {"status": "skipped"}
    hook = os.environ.get("VERCEL_DEPLOY_HOOK", "").strip()
    if hook:
        try:
            req = urllib.request.Request(hook, method="POST", data=b"{}",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"status": "webhook_triggered", "http": r.status}
        except Exception as e:
            return {"status": "webhook_failed", "error": f"{type(e).__name__}: {e}"}
    return {"status": "skipped_no_hook"}


def indexnow_ping(slug: str, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {"status": "skipped"}
    urls = [
        f"https://{INDEXNOW_HOST}/blog/{slug}",
        f"https://{INDEXNOW_HOST}/blog",
        f"https://{INDEXNOW_HOST}/sitemap.xml",
    ]
    body = {
        "host": INDEXNOW_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{INDEXNOW_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    results: dict[str, Any] = {}
    # Yandex is the most reliable for new domains
    for endpoint in ("https://yandex.com/indexnow", "https://api.indexnow.org/indexnow"):
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(body).encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "NeoGenesis-BlogAutogen/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                results[endpoint] = r.status
        except urllib.error.HTTPError as e:
            results[endpoint] = f"HTTP {e.code}"
        except Exception as e:
            results[endpoint] = f"{type(e).__name__}"
    return {"status": "ok", "results": results, "urls_pinged": urls}


# ─────────────────────────────────────────────
# Run log (JSONL)
# ─────────────────────────────────────────────

def log_run(record: dict[str, Any]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record["logged_at"] = dt.datetime.utcnow().isoformat() + "Z"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────

def gather_context() -> dict[str, Any]:
    existing_slugs = load_existing_blog_slugs()
    sbus = []
    text = SBUS_TS.read_text(encoding="utf-8") if SBUS_TS.exists() else ""
    # Extract SBU slugs+names from the SBUS array
    sbu_section = text.split("BLOG_POSTS")[0] if "BLOG_POSTS" in text else text
    SLUG_RE = re.compile(r'slug:\s*"([^"]+)"')
    NAME_RE = re.compile(r'name:\s*"([^"]+)"')
    for m in SLUG_RE.finditer(sbu_section):
        slug = m.group(1)
        nm = NAME_RE.search(sbu_section[m.end(): m.end() + 400])
        sbus.append((slug, nm.group(1) if nm else slug))
    # Existing blog with title
    existing_blog: list[tuple[str, str]] = []
    if "BLOG_POSTS" in text:
        scoped = text[text.index("BLOG_POSTS"):]
        TITLE_RE = re.compile(r'title:\s*"([^"]+)"')
        for m in SLUG_RE.finditer(scoped):
            slug = m.group(1)
            tm = TITLE_RE.search(scoped[m.end(): m.end() + 600])
            existing_blog.append((slug, tm.group(1) if tm else ""))
    return {
        "existing_slugs": existing_slugs,
        "existing_blog": existing_blog,
        "sbus": sbus,
        "research": load_research_slugs(),
        "press": load_press_release_slugs(),
    }


def draft_with_chain(system_prompt: str, user_prompt: str, forced_provider: Optional[str] = None,
                     budget_remaining_usd: float = MAX_COST_USD) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    """Try providers in order; return (post, attempts)."""
    attempts: list[dict[str, Any]] = []
    chain = PROVIDER_CHAIN
    if forced_provider:
        chain = [(n, fn) for (n, fn) in chain if forced_provider in n]
    for name, fn in chain:
        if budget_remaining_usd <= 0:
            attempts.append({"provider": name, "skipped": "budget_exhausted"})
            continue
        t0 = time.monotonic()
        result = fn(system_prompt, user_prompt)
        elapsed = round(time.monotonic() - t0, 1)
        attempts.append({
            "provider": name,
            "model": result.model,
            "ok": not bool(result.error),
            "error": result.error,
            "tokens": result.output_tokens,
            "cost_usd": round(result.cost_usd, 4),
            "elapsed_s": elapsed,
        })
        if result.error or not result.text:
            continue
        budget_remaining_usd -= result.cost_usd
        post = extract_json(result.text)
        if post is None:
            attempts[-1]["parse_error"] = "json_extraction_failed"
            continue
        post["_meta"] = post.get("_meta", {})
        post["_meta"]["provider"] = name
        post["_meta"]["model"] = result.model
        post["_meta"]["cost_usd"] = round(result.cost_usd, 4)
        return post, attempts
    return None, attempts


def main() -> int:
    parser = argparse.ArgumentParser(description="Neo Genesis blog auto-generator")
    parser.add_argument("--dry-run", action="store_true", help="generate + validate; skip commit/deploy")
    parser.add_argument("--topic", default=None, help="manual topic override (title hint)")
    parser.add_argument("--slug", default=None, help="manual slug override")
    parser.add_argument("--provider", default=None, help="force provider substring (e.g. 'gemini')")
    parser.add_argument("--no-deploy", action="store_true", help="commit but skip Vercel + IndexNow")
    parser.add_argument("--locale", choices=["en", "ko", "auto"], default="auto")
    parser.add_argument("--max-attempts", type=int, default=3, help="V-Score retry budget")
    parser.add_argument("--skip-citation-verify", action="store_true", help="skip HTTP HEAD on each citation URL")
    parser.add_argument("--force", action="store_true", help="bypass oversaturation guard (BLOG_LIMIT)")
    args = parser.parse_args()

    _load_env_files()

    started = dt.datetime.utcnow().isoformat() + "Z"
    record: dict[str, Any] = {"started": started, "args": vars(args), "phases": {}}

    # 1. Sense
    ctx = gather_context()
    # Oversaturation guard: prevents the pipeline from publishing endlessly when
    # the blog already has many entries. Default raised to 50 (was 20) because
    # we now intentionally target GEO gaps and 19 entries on 2026-05-06 was
    # well below the natural saturation point. Override via BLOG_LIMIT env or
    # --force flag.
    limit = int(os.environ.get("BLOG_LIMIT", "50"))
    if not getattr(args, "force", False) and len(ctx["existing_blog"]) >= limit:
        record["phases"]["sense"] = {"status": "skipped", "reason": f"blog_count >= {limit} (oversaturation guard, override: BLOG_LIMIT env or --force)"}
        record["status"] = "skipped"
        log_run(record)
        print(f"Skipping: BLOG_POSTS already has {limit}+ entries (current: {len(ctx['existing_blog'])}).")
        return 0

    # Locale auto: alternate by weekday
    if args.locale == "auto":
        weekday = dt.date.today().weekday()  # Monday=0
        target_locale = "ko" if weekday == 0 else "en"
    else:
        target_locale = args.locale

    # Topic selection
    if args.topic:
        topic = TopicCandidate(
            priority=0,
            source="manual",
            suggested_slug=args.slug or f"manual-{int(time.time())}",
            title_hint=args.topic,
            rationale="Manual override.",
            target_locale=target_locale,
        )
    else:
        candidates = build_candidates()
        topic = select_topic(candidates, ctx["existing_slugs"])
        if topic is None:
            record["phases"]["sense"] = {"status": "no_candidate"}
            record["status"] = "skipped"
            log_run(record)
            print("No topic candidate available.")
            return 1
        topic.target_locale = target_locale if args.locale != "auto" else topic.target_locale
    record["phases"]["sense"] = {
        "status": "ok",
        "topic_slug": topic.suggested_slug,
        "topic_source": topic.source,
        "topic_priority": topic.priority,
        "locale": topic.target_locale,
    }
    print(f"Topic: {topic.suggested_slug} (priority={topic.priority}, source={topic.source})")

    # 2. Think — LLM draft + validate, retry up to N times
    if not PROMPT_FILE.exists():
        print(f"missing prompt file: {PROMPT_FILE}", file=sys.stderr)
        return 1
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    cost_used = 0.0
    last_post = None
    last_validation = None
    last_attempts: list[dict[str, Any]] = []
    for attempt in range(1, args.max_attempts + 1):
        user_prompt = build_user_prompt(
            topic,
            ctx["existing_blog"],
            ctx["research"],
            ctx["press"],
            ctx["sbus"],
            topic.target_locale,
        )
        if last_validation and not last_validation.passed:
            user_prompt += "\n\n## Previous attempt rejected — fix these:\n"
            for err in last_validation.errors:
                user_prompt += f"- {err}\n"
            for w in last_validation.warnings[:3]:
                user_prompt += f"- (warn) {w}\n"
        post, attempts = draft_with_chain(system_prompt, user_prompt,
                                          forced_provider=args.provider,
                                          budget_remaining_usd=MAX_COST_USD - cost_used)
        last_attempts.extend(attempts)
        if post is None:
            print(f"  attempt {attempt}: all providers failed")
            continue
        cost_used += float(post.get("_meta", {}).get("cost_usd", 0.0))
        # 3. Quality
        validation = validate_post(post)
        last_post, last_validation = post, validation
        print(f"  attempt {attempt}: V={validation.score} ({'PASS' if validation.passed else 'FAIL'})")
        if validation.passed:
            break
    record["phases"]["think"] = {
        "attempts": last_attempts,
        "cost_used_usd": round(cost_used, 4),
        "post_slug": last_post.get("slug") if last_post else None,
    }
    if cost_used >= MAX_COST_USD:
        print(f"COST CAP reached ({cost_used:.4f} USD). Aborting.")
        record["status"] = "cost_cap"
        log_run(record)
        return 2
    if last_post is None or last_validation is None or not last_validation.passed:
        record["phases"]["quality"] = {
            "status": "fail",
            "validation": (asdict_or_none(last_validation) if last_validation else None),
        }
        record["status"] = "validation_failed"
        log_run(record)
        # Save draft for debugging
        if last_post:
            (RUNS_DIR / f"rejected-{started.replace(':', '-')}.json").write_text(
                json.dumps(last_post, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"V-Score gate FAILED.")
        if last_validation:
            print(format_result(last_validation))
        return 3

    # Final V-Score result
    record["phases"]["quality"] = {
        "status": "pass",
        "v_score": last_validation.score,
        "breakdown": last_validation.breakdown,
        "counts": last_validation.counts,
    }
    print(format_result(last_validation))

    # Slug uniqueness final check (case LLM ignored)
    if last_post["slug"] in ctx["existing_slugs"]:
        last_post["slug"] = f"{last_post['slug']}-2026"

    # 3.5 Citation HEAD verification
    dead_urls = verify_citations(last_post, skip=args.skip_citation_verify)
    record["phases"]["citation_verify"] = {
        "skipped": args.skip_citation_verify,
        "dead_urls": dead_urls,
    }
    if dead_urls and not args.skip_citation_verify:
        # Strip dead URLs but keep going if remaining citations are still >= 5 authoritative
        last_post["citations"] = [c for c in last_post["citations"] if c["url"] not in dead_urls]
        revalidation = validate_post(last_post)
        if not revalidation.passed:
            record["status"] = "dead_citations_below_threshold"
            log_run(record)
            (RUNS_DIR / f"dead-citation-{started.replace(':', '-')}.json").write_text(
                json.dumps({"post": last_post, "dead_urls": dead_urls}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Dead citations dropped {len(dead_urls)} -> below V-Score threshold. Aborting.")
            return 4
        last_validation = revalidation
        record["phases"]["quality"]["after_citation_filter"] = {
            "v_score": revalidation.score,
            "dropped": len(dead_urls),
        }

    # Set publish dates if missing
    today = dt.date.today().isoformat()
    last_post.setdefault("publishedAt", today)
    last_post.setdefault("updatedAt", today)

    # Save final draft
    final_path = RUNS_DIR / f"draft-{last_post['slug']}.json"
    final_path.write_text(json.dumps(last_post, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Draft saved: {final_path}")

    if args.dry_run:
        record["phases"]["append"] = {"status": "skipped (dry-run)"}
        record["phases"]["commit"] = {"status": "skipped (dry-run)"}
        record["status"] = "dry_run_ok"
        record["v_score"] = last_validation.score
        log_run(record)
        print("Dry run complete.")
        return 0

    # 4. Append to TS files
    try:
        append_blog_content(last_post)
        append_blog_post_metadata(last_post)
        record["phases"]["append"] = {"status": "ok"}
    except Exception as e:
        record["phases"]["append"] = {"status": "fail", "error": f"{type(e).__name__}: {e}"}
        record["status"] = "append_failed"
        log_run(record)
        print(f"TS append FAILED: {e}")
        return 5

    # 5. Git commit + push
    git_result = git_commit_push(last_post, dry_run=False)
    record["phases"]["git"] = git_result
    if git_result.get("status") not in ("ok", "no_changes"):
        record["status"] = "git_failed"
        log_run(record)
        print(f"Git commit/push failed: {git_result}")
        return 6

    # 6. Vercel deploy + IndexNow
    if args.no_deploy:
        record["phases"]["deploy"] = {"status": "skipped (--no-deploy)"}
        record["phases"]["indexnow"] = {"status": "skipped (--no-deploy)"}
    else:
        record["phases"]["deploy"] = trigger_vercel_deploy(dry_run=False)
        record["phases"]["indexnow"] = indexnow_ping(last_post["slug"], dry_run=False)

    record["status"] = "published"
    record["v_score"] = last_validation.score
    record["slug"] = last_post["slug"]
    record["title"] = last_post["title"]
    record["url"] = f"https://neogenesis.app/blog/{last_post['slug']}"
    log_run(record)
    print(f"\nPublished: {record['url']}")
    print(f"V-Score: {last_validation.score}")
    print(f"Cost: ${cost_used:.4f}")
    return 0


def asdict_or_none(obj: Any) -> Optional[dict[str, Any]]:
    if obj is None:
        return None
    try:
        return {
            "score": obj.score,
            "passed": obj.passed,
            "errors": obj.errors,
            "warnings": obj.warnings,
            "counts": obj.counts,
            "breakdown": obj.breakdown,
        }
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
