#!/usr/bin/env python3
"""
Persona Embedding Cache Builder (Dispatcher Layer 3)

32 페르소나 frontmatter 를 읽어 KURE-v1 embedding service (port 7702) 로
1024-dim normalized vector 를 사전 계산하고 persona_embeddings.json 에 박제한다.

작성: 2026-05-10, Claude Opus 4.7 Strategy Lead
SSOT:
  - .agent/personas/tier-{s,a,b,c}/*.md (frontmatter description 추출)
  - .agent/personas/dispatcher/persona_embeddings.json (output)
  - http://desktop-sol01:7702/embed (KURE-v1 service)

사용:
  python scripts/persona/build_embedding_cache.py
  python scripts/persona/build_embedding_cache.py --service-url http://localhost:7702
  python scripts/persona/build_embedding_cache.py --dry-run

Behavior:
  - service 미가용 → graceful fail (cache 생성 안 함, dispatcher L3 stub 유지)
  - 32 페르소나 frontmatter 일괄 파싱 → service 1회 batch 호출 → cache 박제
  - idempotent (재실행 시 동일 결과)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("[ERROR] pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    import httpx
except ImportError:
    print("[ERROR] pip install httpx", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = REPO_ROOT / ".agent" / "personas"
CACHE_PATH = PERSONAS_DIR / "dispatcher" / "persona_embeddings.json"

DEFAULT_SERVICE_URLS = [
    "http://localhost:7702",
    "http://desktop-sol01:7702",
    "http://172.17.0.1:7702",
]


def parse_frontmatter(md_path: Path) -> Optional[dict[str, Any]]:
    """Markdown 의 첫 `---` ~ `---` 블록을 YAML 로 파싱."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[WARN] read fail {md_path}: {e}", file=sys.stderr)
        return None

    if not text.startswith("---"):
        return None

    end = text.find("\n---", 4)
    if end < 0:
        return None

    raw = text[4:end]
    try:
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError as e:
        print(f"[WARN] yaml parse fail {md_path}: {e}", file=sys.stderr)
        return None


def collect_personas() -> list[dict[str, Any]]:
    """tier-s/a/b/c 4개 디렉토리에서 32 페르소나 frontmatter 수집."""
    personas: list[dict[str, Any]] = []
    for tier in ["tier-s", "tier-a", "tier-b", "tier-c"]:
        tier_dir = PERSONAS_DIR / tier
        if not tier_dir.exists():
            continue
        for md_path in sorted(tier_dir.glob("*.md")):
            fm = parse_frontmatter(md_path)
            if not fm or not fm.get("name"):
                continue

            persona_id = fm["name"]
            display = fm.get("display_name", persona_id)
            desc = fm.get("description", "") or ""
            if isinstance(desc, str):
                desc = desc.strip()
            else:
                desc = str(desc).strip()

            method = fm.get("methodology") or {}
            framework = ""
            if isinstance(method, dict):
                framework = method.get("primary_framework", "") or ""

            # description text 생성: display_name + description + framework
            parts = [display]
            if desc:
                parts.append(desc)
            if framework:
                parts.append(f"Primary framework: {framework}")
            description_text = ". ".join(p.rstrip(".") for p in parts if p) + "."

            personas.append(
                {
                    "persona_id": persona_id,
                    "tier": tier.replace("tier-", "").upper(),
                    "display_name": display,
                    "description_text": description_text,
                    "framework": framework or None,
                    "source_path": str(md_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                }
            )

    return personas


def find_service_url(candidates: list[str], explicit: Optional[str] = None) -> Optional[str]:
    """우선순위 + healthcheck 로 가용 service URL 탐색."""
    urls = [explicit] if explicit else []
    urls.extend(candidates)
    for url in urls:
        if not url:
            continue
        url = url.rstrip("/")
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok" and data.get("kure_loaded"):
                    return url
        except Exception:
            continue
    return None


def call_embed(url: str, texts: list[str]) -> Optional[list[list[float]]]:
    """KURE-v1 /embed 호출 (normalize=true). graceful fail."""
    try:
        r = httpx.post(
            f"{url}/embed",
            json={"texts": texts, "model": "kure-v1"},
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("embeddings")
    except Exception as e:
        print(f"[ERROR] embed call failed: {e}", file=sys.stderr)
        return None


def build_cache(
    personas: list[dict[str, Any]],
    embeddings: list[list[float]],
    model_name: str,
) -> dict[str, Any]:
    """cache JSON 구조 빌드."""
    if len(personas) != len(embeddings):
        raise ValueError(
            f"persona count {len(personas)} != embedding count {len(embeddings)}"
        )

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    dim = len(embeddings[0]) if embeddings else 0

    persona_map: dict[str, Any] = {}
    for p, emb in zip(personas, embeddings):
        persona_map[p["persona_id"]] = {
            "description_text": p["description_text"],
            "embedding": emb,
            "framework": p["framework"],
            "tier": p["tier"],
            "source_path": p["source_path"],
        }

    return {
        "schema_version": "1.0",
        "model": model_name,
        "dimension": dim,
        "computed_at_kst": now,
        "persona_count": len(persona_map),
        "personas": persona_map,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Persona Embedding Cache Builder")
    parser.add_argument(
        "--service-url",
        help=f"KURE-v1 endpoint (default tries: {', '.join(DEFAULT_SERVICE_URLS)})",
    )
    parser.add_argument("--dry-run", action="store_true", help="parse only, no embed call")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # 1. Persona 수집
    personas = collect_personas()
    print(f"[INFO] collected {len(personas)} personas")
    if args.verbose:
        for p in personas:
            print(f"  - {p['tier']:1} | {p['persona_id']:40} | {p['source_path']}")

    if not personas:
        print("[ERROR] no personas found", file=sys.stderr)
        return 1

    if args.dry_run:
        print("[DRY-RUN] skipping embed call")
        if args.verbose and personas:
            print("\n[DRY-RUN] sample description text:")
            print(f"  {personas[0]['persona_id']}: {personas[0]['description_text']}")
        return 0

    # 2. Service URL 탐색
    service_url = find_service_url(DEFAULT_SERVICE_URLS, args.service_url)
    if not service_url:
        print(
            "[ERROR] KURE-v1 service unavailable. "
            "tried: localhost:7702, desktop-sol01:7702, 172.17.0.1:7702",
            file=sys.stderr,
        )
        print("[INFO] cache 생성 skip — dispatcher L3 stub 유지", file=sys.stderr)
        return 3
    print(f"[INFO] using service: {service_url}")

    # 3. Batch embed (32 texts in single call)
    texts = [p["description_text"] for p in personas]
    print(f"[INFO] calling /embed with {len(texts)} texts...")
    embeddings = call_embed(service_url, texts)
    if not embeddings or len(embeddings) != len(personas):
        print(
            f"[ERROR] embed result count mismatch: got {len(embeddings) if embeddings else 0}, expected {len(personas)}",
            file=sys.stderr,
        )
        return 4

    dim = len(embeddings[0])
    print(f"[INFO] received {len(embeddings)} embeddings × {dim} dims")

    # 4. Cache 빌드 + 박제
    cache = build_cache(personas, embeddings, model_name="KURE-v1")

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    size_kb = CACHE_PATH.stat().st_size / 1024
    print(f"[OK] cache written: {CACHE_PATH} ({size_kb:.1f} KB)")
    print(f"[OK] {cache['persona_count']} personas × {cache['dimension']} dims, model={cache['model']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
