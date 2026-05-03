"""
Wikidata 13 Entity Monolingual-Text Statement 추가 스크립트
==========================================================

기존 add_statements.py 와 독립 동작. monolingualtext 데이터타입을 사용하는
P1813 (short name) 와 P1448 (official name) 를 보강한다.

핵심 차이점 (vs add_statements.py):
- value_kind="monolingualtext" 추가 처리
- snak.datavalue.value = {"text": ..., "language": ...} (object)
- snak.datavalue.type = "monolingualtext"
- idempotency 비교 시 (text, language) 쌍 모두 일치해야 SKIP
- 동일 entity 에 (en, ko) 두 언어 모두 추가 가능 (Wikidata 는 별도 statement 로 저장)

전제:
1. https://www.wikidata.org/wiki/Special:BotPasswords 의 Neogenesislab@claude 자격
2. .env.local 의 WIKIDATA_USERNAME / WIKIDATA_PASSWORD
3. 13개 entity 는 이미 등록 완료

사용:
    cd D:/00.test/neo-genesis
    python scripts/wikidata_register/add_monolingualtext_statements.py --dry-run
    python scripts/wikidata_register/add_monolingualtext_statements.py
    python scripts/wikidata_register/add_monolingualtext_statements.py --only=Q139569680

옵션:
    --dry-run         실제 API 쓰기 없이 plan 만 표시
    --only=Q1,Q2,...  특정 Q-ID 만 처리
    --throttle 8.0    요청 간 대기 (초). default 8s

설계 노트:
- 본 스크립트는 register_entities.py / add_statements.py 와 독립 (기존 파일 수정 X).
- 이전 라운드의 P1813 fail (invalid-snak) 의 root cause:
    * value 를 단순 string 으로 보냈으나 P1813 은 monolingualtext 데이터타입
    * 이번 스크립트는 datavalue.type="monolingualtext" + value=object 로 정확히 전송
- P1448 official name 도 동일 데이터타입 (monolingualtext)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request


# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "NeoGenesisRegister/1.0 (https://neogenesis.app; neogenesis.research@gmail.com)"

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent  # D:/00.test/neo-genesis
AUDIT_DIR = REPO_ROOT / ".agent" / "knowledge" / "wikidata-entities"
# 동일 날짜의 audit log 에 append (기존 라운드와 동일 파일 사용)
AUDIT_FILE = AUDIT_DIR / "statements_added_2026-05-03.jsonl"

NEO_GENESIS_QID = "Q139569680"
YESOL_HEO_QID = "Q139569708"

# 13개 entity 의 short name + official name 정의
# 형식: qid → {"short_name": [(text, lang), ...], "official_name": [(text, lang), ...]}
#
# 결정 사항:
#   - Q139569680 (Neo Genesis): short_name 와 official_name 동일 ("Neo Genesis" / "네오제네시스")
#   - Q139569708 (Yesol Heo): short + official 모두 동일
#   - 11 SBU: short_name 만 (official_name 은 short 와 동일하므로 P1448 도 같이 지정)
#   - UR WRONG: 한국어 표기 미정 → en 만
#
# task spec 에 따라 P1813 + P1448 모두 같은 (text, lang) 로 추가한다.
ENTITY_NAMES: dict[str, dict[str, list[tuple[str, str]]]] = {
    NEO_GENESIS_QID: {
        "short_name": [("Neo Genesis", "en"), ("네오제네시스", "ko")],
        "official_name": [("Neo Genesis", "en"), ("네오제네시스", "ko")],
    },
    YESOL_HEO_QID: {
        "short_name": [("Yesol Heo", "en"), ("허예솔", "ko")],
        "official_name": [("Yesol Heo", "en"), ("허예솔", "ko")],
    },
    "Q139569710": {  # UR WRONG
        "short_name": [("UR WRONG", "en")],
        "official_name": [("UR WRONG", "en")],
    },
    "Q139569711": {  # ToolPick
        "short_name": [("ToolPick", "en"), ("툴픽", "ko")],
        "official_name": [("ToolPick", "en"), ("툴픽", "ko")],
    },
    "Q139569712": {  # ReviewLab
        "short_name": [("ReviewLab", "en"), ("리뷰랩", "ko")],
        "official_name": [("ReviewLab", "en"), ("리뷰랩", "ko")],
    },
    "Q139569715": {  # K-OTT
        "short_name": [("K-OTT", "en"), ("케이오티티", "ko")],
        "official_name": [("K-OTT", "en"), ("케이오티티", "ko")],
    },
    "Q139569716": {  # WhyLab
        "short_name": [("WhyLab", "en"), ("와이랩", "ko")],
        "official_name": [("WhyLab", "en"), ("와이랩", "ko")],
    },
    "Q139569718": {  # EthicaAI
        "short_name": [("EthicaAI", "en"), ("에티카AI", "ko")],
        "official_name": [("EthicaAI", "en"), ("에티카AI", "ko")],
    },
    "Q139569720": {  # FinStack
        "short_name": [("FinStack", "en"), ("핀스택", "ko")],
        "official_name": [("FinStack", "en"), ("핀스택", "ko")],
    },
    "Q139569724": {  # AIForge
        "short_name": [("AIForge", "en"), ("에이아이포지", "ko")],
        "official_name": [("AIForge", "en"), ("에이아이포지", "ko")],
    },
    "Q139569725": {  # SellKit
        "short_name": [("SellKit", "en"), ("셀킷", "ko")],
        "official_name": [("SellKit", "en"), ("셀킷", "ko")],
    },
    "Q139569726": {  # DeployStack
        "short_name": [("DeployStack", "en"), ("디플로이스택", "ko")],
        "official_name": [("DeployStack", "en"), ("디플로이스택", "ko")],
    },
    "Q139569727": {  # CraftDesk
        "short_name": [("CraftDesk", "en"), ("크래프트데스크", "ko")],
        "official_name": [("CraftDesk", "en"), ("크래프트데스크", "ko")],
    },
}


# Plan 항목: (qid, property, value_kind, value)
#   value_kind = "monolingualtext"  → value = (text, language) tuple
PLAN: list[tuple[str, str, str, tuple[str, str]]] = []


def build_plan() -> None:
    for qid, names in ENTITY_NAMES.items():
        # P1813 short name
        for text, lang in names.get("short_name", []):
            PLAN.append((qid, "P1813", "monolingualtext", (text, lang)))
        # P1448 official name
        for text, lang in names.get("official_name", []):
            PLAN.append((qid, "P1448", "monolingualtext", (text, lang)))


# ──────────────────────────────────────────────
# Wikidata API client
# ──────────────────────────────────────────────

class WikidataClient:
    def __init__(self, username: str, password: str) -> None:
        self.cookiejar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookiejar),
            urllib.request.HTTPRedirectHandler(),
        )
        self.opener.addheaders = [("User-Agent", USER_AGENT)]
        self.username = username
        self.password = password
        self.csrf_token: Optional[str] = None

    def _post(self, params: dict) -> dict:
        params["format"] = "json"
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, method="POST")
        with self.opener.open(req, timeout=30) as r:
            return json.loads(r.read())

    def _get(self, params: dict) -> dict:
        params["format"] = "json"
        url = API_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        with self.opener.open(req, timeout=30) as r:
            return json.loads(r.read())

    def login(self) -> None:
        r = self._get({"action": "query", "meta": "tokens", "type": "login"})
        login_token = r["query"]["tokens"]["logintoken"]
        r = self._post({
            "action": "login",
            "lgname": self.username,
            "lgpassword": self.password,
            "lgtoken": login_token,
        })
        if r.get("login", {}).get("result") != "Success":
            raise RuntimeError(f"Login failed: {r}")
        r = self._get({"action": "query", "meta": "tokens", "type": "csrf"})
        self.csrf_token = r["query"]["tokens"]["csrftoken"]
        if self.csrf_token == "+\\":
            raise RuntimeError("CSRF token is anonymous — login likely failed silently.")

    def get_claims(self, entity: str) -> dict:
        """Return the raw claims dict {property: [statement,...]}"""
        r = self._get({"action": "wbgetclaims", "entity": entity})
        return r.get("claims", {})

    def create_claim_monolingualtext(
        self, entity: str, prop: str, text: str, language: str
    ) -> dict:
        """Create one monolingualtext claim using wbcreateclaim.

        IMPORTANT (root cause of previous P1813 fail):
        - For monolingualtext, the `value` field passed to wbcreateclaim must be
          the JSON-serialized object {"text": "...", "language": "..."} — NOT a
          plain string.
        - Wikidata wraps this into snak.datavalue = {
              "type": "monolingualtext",
              "value": {"text": "...", "language": "..."}
          }
        """
        value_obj = {"text": text, "language": language}
        params = {
            "action": "wbcreateclaim",
            "entity": entity,
            "property": prop,
            "snaktype": "value",
            "value": json.dumps(value_obj),
            "token": self.csrf_token,
            "bot": "1",
        }
        return self._post(params)


# ──────────────────────────────────────────────
# Idempotency: monolingualtext claim 비교
# ──────────────────────────────────────────────

def claim_matches_monolingualtext(
    existing_claim: dict, text: str, language: str
) -> bool:
    """Return True iff existing_claim 이 동일 (text, language) monolingualtext 값."""
    mainsnak = existing_claim.get("mainsnak", {})
    if mainsnak.get("snaktype") != "value":
        return False
    dv = mainsnak.get("datavalue", {})
    if dv.get("type") != "monolingualtext":
        return False
    val = dv.get("value", {})
    return val.get("text") == text and val.get("language") == language


# ──────────────────────────────────────────────
# 자격증명 로드
# ──────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    user = os.environ.get("WIKIDATA_USERNAME")
    pw = os.environ.get("WIKIDATA_PASSWORD")
    if user and pw:
        return user, pw
    for env_file in [REPO_ROOT / ".env.local", REPO_ROOT / ".env"]:
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k == "WIKIDATA_USERNAME" and not user:
                user = v
            elif k == "WIKIDATA_PASSWORD" and not pw:
                pw = v
        if user and pw:
            return user, pw
    print("ERROR: WIKIDATA_USERNAME / WIKIDATA_PASSWORD not found.", file=sys.stderr)
    sys.exit(1)


# ──────────────────────────────────────────────
# Audit log
# ──────────────────────────────────────────────

def audit_log(record: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", default=None, help="Comma-separated Q-IDs to limit scope")
    parser.add_argument("--throttle", type=float, default=8.0)
    args = parser.parse_args()

    only_qids: Optional[set[str]] = None
    if args.only:
        only_qids = {q.strip() for q in args.only.split(",") if q.strip()}

    build_plan()
    plan = PLAN
    if only_qids:
        plan = [s for s in plan if s[0] in only_qids]

    print(f"[plan] Total monolingualtext statements to consider: {len(plan)}")

    # Group by Q-ID for nicer logs
    by_qid: dict[str, list[tuple[str, str, tuple[str, str]]]] = {}
    for qid, prop, kind, val in plan:
        by_qid.setdefault(qid, []).append((prop, kind, val))

    if args.dry_run:
        print("\n=== DRY RUN ===")
        for qid in sorted(by_qid.keys()):
            entries = by_qid[qid]
            print(f"\n{qid}  ({len(entries)} candidate statements)")
            for prop, kind, val in entries:
                text, lang = val
                print(f"  {prop}  monolingualtext  text={text!r} lang={lang}")
        print(f"\n[dry-run] Audit log will be written to: {AUDIT_FILE}")
        return 0

    user, pw = load_credentials()
    print(f"[auth] Using BotPassword for {user.split('@')[0]}")

    client = WikidataClient(user, pw)
    client.login()
    print("[auth] Logged in. CSRF token acquired.")

    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}

    added = 0
    skipped = 0
    failed = 0

    for qid in sorted(by_qid.keys()):
        entries = by_qid[qid]
        print(f"\n--- {qid} ({len(entries)} candidate statements) ---")

        # 현재 claims 조회 (1 회)
        try:
            current_claims = client.get_claims(qid)
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR] wbgetclaims failed: {e}")
            audit_log({"action": "get_claims_error", "qid": qid, "error": str(e)})
            failed += len(entries)
            continue

        before_total = sum(len(v) for v in current_claims.values())
        before_counts[qid] = before_total
        print(f"  [before] {before_total} statements / properties: {sorted(current_claims.keys())}")

        added_for_this_qid = 0

        for prop, kind, val in entries:
            text, lang = val
            existing = current_claims.get(prop, [])
            duplicate = any(
                claim_matches_monolingualtext(c, text, lang) for c in existing
            )
            if duplicate:
                print(f"  SKIP {prop} = ({text!r}@{lang})  (already present)")
                audit_log({
                    "action": "skip",
                    "qid": qid,
                    "property": prop,
                    "value_kind": "monolingualtext",
                    "value": {"text": text, "language": lang},
                    "reason": "already_present",
                })
                skipped += 1
                continue

            try:
                resp = client.create_claim_monolingualtext(qid, prop, text, lang)
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass
                print(f"  ERR {prop} = ({text!r}@{lang})  HTTP {e.code} {e.reason} {body}")
                audit_log({
                    "action": "error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": "monolingualtext",
                    "value": {"text": text, "language": lang},
                    "http_status": e.code,
                    "body": body,
                })
                failed += 1
                if e.code == 429:
                    print(f"  [rate-limit] sleeping 60s")
                    time.sleep(60)
                else:
                    time.sleep(args.throttle)
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  ERR {prop} = ({text!r}@{lang})  {e}")
                audit_log({
                    "action": "error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": "monolingualtext",
                    "value": {"text": text, "language": lang},
                    "error": str(e),
                })
                failed += 1
                time.sleep(args.throttle)
                continue

            if "error" in resp:
                err = resp["error"]
                print(f"  ERR {prop} = ({text!r}@{lang})  wikidata: {err.get('code')} {err.get('info','')[:120]}")
                audit_log({
                    "action": "wikidata_error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": "monolingualtext",
                    "value": {"text": text, "language": lang},
                    "error": err,
                })
                failed += 1
            else:
                claim_id = (resp.get("claim") or {}).get("id", "")
                print(f"  ADD {prop} = ({text!r}@{lang})  → {claim_id}")
                audit_log({
                    "action": "added",
                    "qid": qid,
                    "property": prop,
                    "value_kind": "monolingualtext",
                    "value": {"text": text, "language": lang},
                    "claim_id": claim_id,
                })
                added += 1
                added_for_this_qid += 1

            time.sleep(args.throttle)

        after_counts[qid] = before_total + added_for_this_qid

    # Final summary
    print("\n=== SUMMARY ===")
    print(f"Added:   {added}")
    print(f"Skipped: {skipped}  (already present)")
    print(f"Failed:  {failed}")
    print(f"Audit log: {AUDIT_FILE}")

    print("\n--- per-entity counts (before → after, computed-not-fetched) ---")
    for qid in sorted(by_qid.keys()):
        b = before_counts.get(qid, "?")
        a = after_counts.get(qid, "?")
        print(f"  {qid}: {b} → {a}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
