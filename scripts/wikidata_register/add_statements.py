"""
Wikidata 13 Entity Statement 추가 스크립트
=========================================

기 등록된 13개 entity 에 추가 P-properties 를 idempotent 하게 보강한다.

전제:
1. https://www.wikidata.org/wiki/Special:BotPasswords 의 Neogenesislab@claude 자격
2. .env.local 의 WIKIDATA_USERNAME / WIKIDATA_PASSWORD
3. 13개 entity 는 이미 등록 완료 (.agent/knowledge/wikidata-entities/registered.json)

핵심 동작:
- wbgetclaims 로 현재 claim 을 먼저 조회
- 동일 (property, value) 가 이미 있으면 SKIP (idempotent)
- 없으면 wbcreateclaim 으로 추가
- 모든 시도/성공/실패를 .agent/knowledge/wikidata-entities/statements_added_<date>.jsonl 에 기록

사용:
    cd D:/00.test/neo-genesis
    python scripts/wikidata_register/add_statements.py --dry-run
    python scripts/wikidata_register/add_statements.py
    python scripts/wikidata_register/add_statements.py --only=Q139569680,Q139569708

옵션:
    --dry-run         실제 API 쓰기 없이 plan 만 표시
    --only=Q1,Q2,...  특정 Q-ID 만 처리
    --throttle 8.0    요청 간 대기 (초). default 8s (rate limit 안전치)

설계 노트:
- 본 스크립트는 register_entities.py 와 독립 동작 (기존 파일 수정 X).
- 사용 가능한 datavalue 타입: wikibase-item, string, url
  → 모든 추가 statement 가 이 3 타입 안에 들어옴 (시간/문자열-fallback 은 미사용).
- Wikidata 의 문제 있는 Q-ID 는 전부 미리 검증함:
  Q1622272 (university teacher), Q4964182 (philosopher), Q42490 (Asterix), Q11458 (Orna Berry),
  Q3400985 (academic) 등은 task 에서 제안됐지만 의미가 안 맞아 제외하고 정확한 Q-ID 로 대체.
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
AUDIT_FILE = AUDIT_DIR / f"statements_added_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

NEO_GENESIS_QID = "Q139569680"
YESOL_HEO_QID = "Q139569708"

# 11 SBU Q-IDs (등록 순)
SBU_QIDS = {
    "ur_wrong":    "Q139569710",
    "toolpick":    "Q139569711",
    "reviewlab":   "Q139569712",
    "kott":        "Q139569715",
    "whylab":      "Q139569716",
    "ethicaai":    "Q139569718",
    "finstack":    "Q139569720",
    "aiforge":     "Q139569724",
    "sellkit":     "Q139569725",
    "deploystack": "Q139569726",
    "craftdesk":   "Q139569727",
}


# ──────────────────────────────────────────────
# 추가할 Statement 정의
# ──────────────────────────────────────────────
#
# 각 항목: (qid, property, value_kind, value)
#   value_kind = "item"   → value 가 Q-ID  (datavalue: wikibase-entityid)
#   value_kind = "string" → value 가 문자열  (datavalue: string)
#   value_kind = "url"    → value 가 URL    (datavalue: string, P 가 URL 데이터타입)
#
# 검증된 Q-ID:
#   Q5         human                 (Yesol Heo 에 이미 있음)
#   Q884       South Korea           (P27 citizenship)
#   Q8684      Seoul                 (P19 birth, optional)
#   Q131524    entrepreneur          (P106 occupation)
#   Q5482740   programmer            (P106 occupation, Yesol 에 이미 있음)
#   Q183888    software developer    (P106 occupation)
#   Q466       World Wide Web        (참조용, P306 으로 쓰면 의미 안 맞아 제외)
#   Q1860      English               (P407)
#   Q9176      Korean                (P407)
#
# task 에서 제안됐지만 잘못된 Q-ID (제외):
#   Q1622272 (university teacher) — task 에서 P106 software dev 라고 했으나 실제는 university teacher
#   Q4964182 (philosopher)        — task 에서 software developer 라고 했으나 실제는 philosopher
#   Q42490   (Asterix)            — task 에서 Web platform 이라고 했으나 실제는 Asterix
#   Q11458   (Orna Berry)         — task 에서 Seoul 이라고 했으나 실제는 Orna Berry; Seoul 은 Q8684

STATEMENTS_TO_ADD: list[tuple[str, str, str, str]] = []


# Q139569680 (Neo Genesis) — 추가 statement
def _add_neo_genesis() -> None:
    qid = NEO_GENESIS_QID
    # P112 founded by → Yesol Heo
    STATEMENTS_TO_ADD.append((qid, "P112", "item", YESOL_HEO_QID))
    # P127 owned by → Yesol Heo
    STATEMENTS_TO_ADD.append((qid, "P127", "item", YESOL_HEO_QID))
    # P3320 board member → Yesol Heo (founder/sole-operator)
    STATEMENTS_TO_ADD.append((qid, "P3320", "item", YESOL_HEO_QID))
    # P1830 owner of → 11 SBU 모두
    for key, sbu_qid in SBU_QIDS.items():
        STATEMENTS_TO_ADD.append((qid, "P1830", "item", sbu_qid))
    # P1056 product or material produced → string fallback (entity 가 1순위지만 안전한 string)
    # NOTE: P1056 은 wikibase-item 데이터타입. string 못 넣음 → 제외.
    # P1813 short name
    STATEMENTS_TO_ADD.append((qid, "P1813", "string", "Neo Genesis"))
    # P1448 official name (mono-lingual text 라 별도 처리 필요. 제외.)


# Q139569708 (Yesol Heo) — 추가 statement
def _add_yesol_heo() -> None:
    qid = YESOL_HEO_QID
    # P106 occupation 추가 (이미 있는 것 외에)
    STATEMENTS_TO_ADD.append((qid, "P106", "item", "Q131524"))   # entrepreneur
    STATEMENTS_TO_ADD.append((qid, "P106", "item", "Q183888"))   # software developer
    # P800 notable work → Neo Genesis (이미 있을 수 있지만 idempotent check 가 막아줌)
    STATEMENTS_TO_ADD.append((qid, "P800", "item", NEO_GENESIS_QID))
    # P19 place of birth → Seoul (Q8684) — owner-verifiable, 참조 가능한 합리적 추정. 이번 세션에서는 제외 (owner explicit 확인 부재).
    # P3479 Omni domain — string. heoyesol.kr.
    # NOTE: P3479 데이터타입 검증 필요. 제외 (외부 ID 라서 문법 다를 수 있음).
    # P39 position held — wikibase-item 만. 적절한 Q-ID 부재. 제외.


# 11 SBU — 공통 statement 추가
def _add_sbu(sbu_qid: str, *, language_qid: Optional[str] = None) -> None:
    # P361 part of → Neo Genesis
    STATEMENTS_TO_ADD.append((sbu_qid, "P361", "item", NEO_GENESIS_QID))
    # P112 founded by → Yesol Heo
    STATEMENTS_TO_ADD.append((sbu_qid, "P112", "item", YESOL_HEO_QID))
    # P3320 board member → Yesol Heo
    STATEMENTS_TO_ADD.append((sbu_qid, "P3320", "item", YESOL_HEO_QID))
    # P407 language of work or name (English default + Korean for kott)
    STATEMENTS_TO_ADD.append((sbu_qid, "P407", "item", "Q1860"))  # English
    if language_qid:
        STATEMENTS_TO_ADD.append((sbu_qid, "P407", "item", language_qid))


def build_plan() -> None:
    _add_neo_genesis()
    _add_yesol_heo()
    for key, sbu_qid in SBU_QIDS.items():
        # kott 만 한국어 추가
        lang = "Q9176" if key == "kott" else None
        _add_sbu(sbu_qid, language_qid=lang)


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

    def create_claim(self, entity: str, prop: str, value_kind: str, value: str) -> dict:
        """Create one claim. value_kind ∈ {item,string,url}."""
        if value_kind == "item":
            numeric_id = int(value.lstrip("Q"))
            value_str = json.dumps({"entity-type": "item", "numeric-id": numeric_id})
        elif value_kind in ("string", "url"):
            value_str = json.dumps(value)
        else:
            raise ValueError(f"Unknown value_kind: {value_kind}")

        params = {
            "action": "wbcreateclaim",
            "entity": entity,
            "property": prop,
            "snaktype": "value",
            "value": value_str,
            "token": self.csrf_token,
            "bot": "1",
        }
        return self._post(params)


# ──────────────────────────────────────────────
# Idempotency: claim 비교
# ──────────────────────────────────────────────

def claim_matches(existing_claim: dict, value_kind: str, value: str) -> bool:
    """Return True iff existing_claim 의 mainsnak 값이 (value_kind, value) 와 일치."""
    mainsnak = existing_claim.get("mainsnak", {})
    if mainsnak.get("snaktype") != "value":
        return False
    dv = mainsnak.get("datavalue", {})
    dv_type = dv.get("type")
    dv_value = dv.get("value")

    if value_kind == "item":
        if dv_type != "wikibase-entityid":
            return False
        # value 는 "Q139569680" 형식
        existing_id = dv_value.get("id") or f"Q{dv_value.get('numeric-id','?')}"
        return existing_id == value
    elif value_kind in ("string", "url"):
        if dv_type != "string":
            return False
        return dv_value == value
    return False


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
    plan = STATEMENTS_TO_ADD
    if only_qids:
        plan = [s for s in plan if s[0] in only_qids]

    print(f"[plan] Total statements to consider: {len(plan)}")

    # Group by Q-ID for nicer logs
    by_qid: dict[str, list[tuple[str, str, str]]] = {}
    for qid, prop, kind, val in plan:
        by_qid.setdefault(qid, []).append((prop, kind, val))

    if args.dry_run:
        print("\n=== DRY RUN ===")
        for qid in sorted(by_qid.keys()):
            entries = by_qid[qid]
            print(f"\n{qid}  ({len(entries)} candidate statements)")
            for prop, kind, val in entries:
                print(f"  {prop}  {kind:6}  {val}")
        print(f"\n[dry-run] Audit log will be written to: {AUDIT_FILE}")
        return 0

    user, pw = load_credentials()
    print(f"[auth] Using BotPassword for {user.split('@')[0]}")

    client = WikidataClient(user, pw)
    client.login()
    print("[auth] Logged in. CSRF token acquired.")

    # before/after counts
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
            existing = current_claims.get(prop, [])
            duplicate = any(claim_matches(c, kind, val) for c in existing)
            if duplicate:
                print(f"  SKIP {prop} = {val}  (already present)")
                audit_log({"action": "skip", "qid": qid, "property": prop, "value": val, "reason": "already_present"})
                skipped += 1
                continue

            try:
                resp = client.create_claim(qid, prop, kind, val)
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass
                print(f"  ERR {prop} = {val}  HTTP {e.code} {e.reason} {body}")
                audit_log({"action": "error", "qid": qid, "property": prop, "value": val, "http_status": e.code, "body": body})
                failed += 1
                if e.code == 429:
                    print(f"  [rate-limit] sleeping 60s")
                    time.sleep(60)
                else:
                    time.sleep(args.throttle)
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  ERR {prop} = {val}  {e}")
                audit_log({"action": "error", "qid": qid, "property": prop, "value": val, "error": str(e)})
                failed += 1
                time.sleep(args.throttle)
                continue

            if "error" in resp:
                err = resp["error"]
                print(f"  ERR {prop} = {val}  wikidata: {err.get('code')} {err.get('info','')[:120]}")
                audit_log({"action": "wikidata_error", "qid": qid, "property": prop, "value": val, "error": err})
                failed += 1
            else:
                claim_id = (resp.get("claim") or {}).get("id", "")
                print(f"  ADD {prop} = {val}  → {claim_id}")
                audit_log({"action": "added", "qid": qid, "property": prop, "value_kind": kind, "value": val, "claim_id": claim_id})
                added += 1
                added_for_this_qid += 1

            # Throttle between writes
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
