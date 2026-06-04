"""
Neo Genesis GEO/LLMO Citation Tracker
======================================

매일 시드 prompt 30개를 4개 LLM (Anthropic Claude, OpenAI GPT-4, Perplexity, Google Gemini) 에
보내고, Neo Genesis 도메인/브랜드 mention 빈도를 집계해 Supabase 또는 로컬 SQLite 에 저장.

Reference: .agent/knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md
실행:
    python scripts/geo_measure/measure_citations.py
    python scripts/geo_measure/measure_citations.py --dry-run
    python scripts/geo_measure/measure_citations.py --providers anthropic,openai

cron 등록 예시는 README.md 참조.
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
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
PROMPTS_FILE = ROOT / "seed_prompts.json"
DB_FILE = ROOT / "citations.sqlite3"
LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "geo_measure"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Neo Genesis 브랜드 / 도메인 / SBU 패턴 (regex flag re.IGNORECASE)
# v1.5 (2026-05-14): expanded to include HF/Wikidata/GitHub/heoyesol + all 11 SBU subdomains
BRAND_PATTERNS = {
    # Core brand
    "neo_genesis":      re.compile(r"\b(neo[\s-]?genesis|네오제네시스)\b", re.IGNORECASE),
    "neogenesislab":    re.compile(r"\bneogenesislab\b", re.IGNORECASE),  # HF/GitHub org
    "domain_root":      re.compile(r"\bneogenesis\.app\b", re.IGNORECASE),
    "domain_subs":      re.compile(r"\b\w+\.neogenesis\.app\b", re.IGNORECASE),
    "heoyesol":         re.compile(r"\bheoyesol\.kr\b", re.IGNORECASE),
    # Structured authority signals
    "wikidata_qid":     re.compile(r"Q1395696[18]0|Q13956971[68]", re.IGNORECASE),
    "hf_neogenesislab": re.compile(r"huggingface\.co/(?:datasets/)?neogenesislab/", re.IGNORECASE),
    "github_yesol":     re.compile(r"github\.com/Yesol-Pilot\b", re.IGNORECASE),
    # 11 SBU brand keywords
    "toolpick":         re.compile(r"\btoolpick(\.dev)?\b", re.IGNORECASE),
    "kott":             re.compile(r"\bk[\s-]?ott(\.kr)?\b", re.IGNORECASE),
    "ur_wrong":         re.compile(r"\bur[\s-]?wrong(\.com)?\b", re.IGNORECASE),
    "whylab":           re.compile(r"\bwhylab\b", re.IGNORECASE),
    "ethicaai":         re.compile(r"\bethica[\s-]?ai\b", re.IGNORECASE),
    "aiforge":          re.compile(r"\baiforge\b", re.IGNORECASE),
    "craftdesk":        re.compile(r"\bcraftdesk\b", re.IGNORECASE),
    "deploystack":      re.compile(r"\bdeploystack\b", re.IGNORECASE),
    "finstack":         re.compile(r"\bfinstack\b", re.IGNORECASE),
    "sellkit":          re.compile(r"\bsellkit\b", re.IGNORECASE),
    "reviewlab":        re.compile(r"\b(reviewlab|review[\s-]?lab)\b", re.IGNORECASE),
    "founder":          re.compile(r"\b(yesol[\s-]?heo|허예솔|heo[\s-]?yesol)\b", re.IGNORECASE),
}


# ──────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────

@dataclass
class Measurement:
    timestamp: str
    provider: str
    model: str
    prompt_id: str
    prompt_category: str
    prompt_text: str
    response_text: str
    response_tokens: int
    mention_neo_genesis: int
    mention_domain_root: int
    mention_domain_subs: int
    mention_sbu_total: int
    mention_founder: int
    sentiment: str  # positive / neutral / negative / unknown
    citation_urls: list[str]
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Provider 어댑터
# ──────────────────────────────────────────────

def call_anthropic(prompt: str, model: str = "claude-sonnet-4-6") -> tuple[str, int]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    body = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    tokens = data.get("usage", {}).get("output_tokens", 0)
    return text, tokens


def call_openai(prompt: str, model: str = "gpt-4o") -> tuple[str, int]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    text = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("completion_tokens", 0)
    return text, tokens


def call_perplexity(prompt: str, model: str = "sonar") -> tuple[str, int]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not set")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    text = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("completion_tokens", 0)
    return text, tokens


def call_gemini(prompt: str, model: str = "gemini-2.5-flash") -> tuple[str, int]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    candidates = data.get("candidates", [])
    if not candidates:
        return "", 0
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    tokens = data.get("usageMetadata", {}).get("candidatesTokenCount", 0)
    return text, tokens


PROVIDERS = {
    "anthropic": ("claude-sonnet-4-6", call_anthropic),
    "openai": ("gpt-4o", call_openai),
    "perplexity": ("sonar", call_perplexity),
    "gemini": ("gemini-2.5-flash", call_gemini),
}


# ──────────────────────────────────────────────
# 분석
# ──────────────────────────────────────────────

URL_RE = re.compile(r"https?://[^\s\)\]\>\"]+")
# v1.5: bare hostname (no protocol) — AI often writes "toolpick.dev" not "https://toolpick.dev"
BARE_HOST_RE = re.compile(r"\b([a-z0-9][a-z0-9-]*\.)+(?:app|com|kr|dev|org|io|co)\b", re.IGNORECASE)

NEGATIVE_TOKENS = ["unreliable", "scam", "avoid", "untrustworthy", "fraud", "사기", "비추천", "신뢰 어려"]
POSITIVE_TOKENS = ["recommended", "trustworthy", "reliable", "best", "excellent", "추천", "신뢰", "우수"]

# v1.5: URL keywords to capture (broader than v1.0)
URL_BRAND_KEYWORDS = [
    "neogenesis", "neogenesislab",
    "toolpick.dev", "ur-wrong.com", "kott.kr",
    "heoyesol.kr",
    "huggingface.co/datasets/neogenesislab",
    "huggingface.co/neogenesislab",
    "wikidata.org/wiki/Q1395696",
    "github.com/Yesol-Pilot",
    "github.com/neogenesislab",
]


def analyze(text: str) -> dict[str, Any]:
    counts = {k: len(p.findall(text)) for k, p in BRAND_PATTERNS.items()}
    # v1.5: expanded SBU coverage (was 5, now 11)
    sbu_total = sum(
        counts[k] for k in (
            "toolpick", "kott", "ur_wrong", "whylab", "ethicaai",
            "aiforge", "craftdesk", "deploystack", "finstack", "sellkit", "reviewlab",
        )
    )
    # v1.5: broader URL match using URL_BRAND_KEYWORDS list
    urls = sorted({u for u in URL_RE.findall(text)
                   if any(kw.lower() in u.lower() for kw in URL_BRAND_KEYWORDS)})
    # v1.5: also capture bare hostnames (no protocol)
    bare_hosts = set()
    for m in BARE_HOST_RE.finditer(text):
        host = m.group(0).lower()
        if any(kw.lower() in host for kw in
               ["neogenesis", "toolpick.dev", "ur-wrong.com", "kott.kr", "heoyesol.kr"]):
            bare_hosts.add(host)
    if bare_hosts:
        urls = sorted(set(urls) | bare_hosts)
    sentiment = "unknown"
    lowered = text.lower()
    has_neg = any(t.lower() in lowered for t in NEGATIVE_TOKENS)
    has_pos = any(t.lower() in lowered for t in POSITIVE_TOKENS)
    if has_neg and not has_pos:
        sentiment = "negative"
    elif has_pos and not has_neg:
        sentiment = "positive"
    elif has_pos or has_neg:
        sentiment = "neutral"
    elif counts["neo_genesis"] > 0 or sbu_total > 0:
        sentiment = "neutral"
    return {
        "counts": counts,
        "sbu_total": sbu_total,
        "urls": urls,
        "sentiment": sentiment,
    }


# ──────────────────────────────────────────────
# 저장
# ──────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_id TEXT NOT NULL,
            prompt_category TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            response_tokens INTEGER NOT NULL,
            mention_neo_genesis INTEGER NOT NULL,
            mention_domain_root INTEGER NOT NULL,
            mention_domain_subs INTEGER NOT NULL,
            mention_sbu_total INTEGER NOT NULL,
            mention_founder INTEGER NOT NULL,
            sentiment TEXT NOT NULL,
            citation_urls TEXT NOT NULL,
            error TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements(timestamp DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_measurements_provider ON measurements(provider, timestamp DESC)"
    )
    conn.commit()
    return conn


def save(conn: sqlite3.Connection, m: Measurement) -> None:
    conn.execute(
        """INSERT INTO measurements (
            timestamp, provider, model, prompt_id, prompt_category, prompt_text,
            response_text, response_tokens,
            mention_neo_genesis, mention_domain_root, mention_domain_subs,
            mention_sbu_total, mention_founder, sentiment, citation_urls, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            m.timestamp, m.provider, m.model, m.prompt_id, m.prompt_category, m.prompt_text,
            m.response_text, m.response_tokens,
            m.mention_neo_genesis, m.mention_domain_root, m.mention_domain_subs,
            m.mention_sbu_total, m.mention_founder, m.sentiment,
            json.dumps(m.citation_urls, ensure_ascii=False), m.error,
        ),
    )
    conn.commit()


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def run(providers: list[str], dry_run: bool, prompts_filter: Optional[str]) -> dict[str, Any]:
    if not PROMPTS_FILE.exists():
        raise FileNotFoundError(f"prompts not found: {PROMPTS_FILE}")
    spec = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    prompts: Iterable[dict[str, str]] = spec["prompts"]
    if prompts_filter:
        prompts = [p for p in prompts if p["category"] == prompts_filter or p["id"] == prompts_filter]

    conn = init_db() if not dry_run else None

    summary: dict[str, dict[str, int]] = {p: {"calls": 0, "errors": 0, "mentions": 0} for p in providers}
    started = time.monotonic()

    for prompt in prompts:
        for provider in providers:
            if provider not in PROVIDERS:
                print(f"unknown provider: {provider}", file=sys.stderr)
                continue
            model, fn = PROVIDERS[provider]
            ts = datetime.now(timezone.utc).isoformat()
            error: Optional[str] = None
            text = ""
            tokens = 0
            try:
                text, tokens = fn(prompt["text"])
            except urllib.error.HTTPError as e:
                error = f"HTTP {e.code}: {e.read()[:300]!r}"
            except Exception as e:  # noqa: BLE001
                error = f"{type(e).__name__}: {e}"

            if error:
                summary[provider]["errors"] += 1
                analysis = {"counts": {k: 0 for k in BRAND_PATTERNS}, "sbu_total": 0, "urls": [], "sentiment": "unknown"}
            else:
                analysis = analyze(text)
                summary[provider]["calls"] += 1
                if analysis["counts"]["neo_genesis"] > 0 or analysis["sbu_total"] > 0:
                    summary[provider]["mentions"] += 1

            m = Measurement(
                timestamp=ts,
                provider=provider,
                model=model,
                prompt_id=prompt["id"],
                prompt_category=prompt["category"],
                prompt_text=prompt["text"],
                response_text=text,
                response_tokens=tokens,
                mention_neo_genesis=analysis["counts"]["neo_genesis"],
                mention_domain_root=analysis["counts"]["domain_root"],
                mention_domain_subs=analysis["counts"]["domain_subs"],
                mention_sbu_total=analysis["sbu_total"],
                mention_founder=analysis["counts"]["founder"],
                sentiment=analysis["sentiment"],
                citation_urls=analysis["urls"],
                error=error,
            )
            if dry_run:
                print(json.dumps(asdict(m), ensure_ascii=False, indent=2)[:600])
            else:
                save(conn, m)  # type: ignore[arg-type]

            time.sleep(0.5)  # rate limit safety

    elapsed = time.monotonic() - started
    return {"summary": summary, "elapsed_s": round(elapsed, 1), "dry_run": dry_run}


def _load_env_files() -> None:
    """`.env.local` 우선 + `.env` 보조 자동 로드. 이미 set 된 변수는 덮어쓰지 않음 (cron 안전).

    .env 에 sk-local-* (LiteLLM proxy mock) 가 있고 .env.local 에 진짜 키가 있을 때
    .env.local 이 winning 하도록 .env.local 을 먼저 로드.
    """
    repo_root = Path(__file__).resolve().parents[2]
    for fname in (".env.local", ".env"):  # .env.local 우선
        path = repo_root / fname
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    # 비어있는 값(예: 부모 shell 의 빈 export)은 override 허용 — 진짜 키가 winning
                    if k and (k not in os.environ or not os.environ[k].strip()):
                        os.environ[k] = v
        except Exception:
            # cron context 에서 .env 읽기 실패해도 진행 (이미 환경변수 set 되어 있을 수 있음)
            pass


def main() -> int:
    _load_env_files()

    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="anthropic,openai,perplexity,gemini")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--filter", default=None, help="prompt category 또는 id 로 필터")
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    result = run(providers, args.dry_run, args.filter)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
