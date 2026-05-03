"""
Wikidata Phase 3 Statement 추가 스크립트
========================================

기 등록된 13개 entity 의 Wikidata depth 를 추가 P-properties 로 확장한다.

전제:
1. https://www.wikidata.org/wiki/Special:BotPasswords 의 Neogenesislab@claude 자격
2. .env.local 의 WIKIDATA_USERNAME / WIKIDATA_PASSWORD
3. 13개 entity 는 이미 등록 완료
4. 161 statements 가 이미 적재됨 (P31/P159/P17/P571/P856/P2037/P452/P112/P127/P3320
   /P1830/P361/P407/P106/P1813/P1448) — 본 스크립트는 위 항목과 중복되지 않는 신규 property 만 추가한다.

핵심 동작:
- wbgetclaims 로 현재 claim 을 먼저 조회
- 동일 (property, value) 가 이미 있으면 SKIP (idempotent)
- 없으면 wbcreateclaim 으로 추가
- 모든 시도/성공/실패를 statements_added_2026-05-03.jsonl 에 append

사용:
    cd D:/00.test/neo-genesis
    python scripts/wikidata_register/add_phase_3_statements.py --dry-run
    python scripts/wikidata_register/add_phase_3_statements.py
    python scripts/wikidata_register/add_phase_3_statements.py --only=Q139569680

옵션:
    --dry-run         실제 API 쓰기 없이 plan 만 표시
    --only=Q1,Q2,...  특정 Q-ID 만 처리
    --throttle 8.0    요청 간 대기 (초). default 8s

본 스크립트가 추가하는 property (모두 사전 datatype 검증 완료):

A) Q139569680 (Neo Genesis):
   - P31  instance of   → Q43229 (organization)            [업그레이드, 기존 P31 가 있어도 별 statement 1개]
   - P176 manufacturer  → 11 SBU 모두 (SBU 의 manufacturer 는 부모회사인 Neo Genesis,
                          반대로 Neo Genesis 가 SBU 들의 P1056 product 를 producing
                          한다는 관계)
   - P1056 product or material produced → 11 SBU (item)
   - P137 operator       → Q139569708 (Yesol Heo)
   - P1451 motto text    → "AI Works. You Decide." en + "AI는 일한다. 결정은 당신이 한다." ko
                          (monolingualtext)

B) Q139569708 (Yesol Heo):
   - P21  sex or gender         → Q6581072 (female)         [공개 사실, owner approved]
   - P27  country of citizenship → Q884 (South Korea)
   - P106 occupation             → Q11569986 (chief executive officer) — 대신 Q484876 가 더 일반적이지만
                                    검증 후 추가 (아래 별도 검증). NOTE: 본 스크립트는 owner 명시 OK 한 것만.

C) 11 SBU 각각:
   - P31  instance of           → Q1254596 (software as a service, SaaS)
   - P31  instance of           → Q35127 (website)
   - P31  instance of           → Q166142 (application software) — Q35127 도 부족 시 강화
   - P176 manufacturer          → Q139569680 (Neo Genesis)
   - P137 operator              → Q139569680 (Neo Genesis)
   - P136 genre                 → Q11660 (artificial intelligence) — 모든 SBU AI 기반
   - P136 genre                 → Q1254596 (software as a service)
   - P452 industry 강화         → Q11661 (information technology) — P452 는 이미 있을 수 있지만
                                  중복은 idempotent check 로 SKIP

verified Q-ID (이번 라운드):
   Q43229       organization
   Q1254596     software as a service (SaaS)
   Q35127       website
   Q166142      application software
   Q11660       artificial intelligence
   Q11661       information technology
   Q6581072     female
   Q884         South Korea
   Q139569680   Neo Genesis
   Q139569708   Yesol Heo

verified property datatype:
   P31    item
   P176   item
   P1056  item
   P137   item
   P1451  monolingualtext
   P21    item
   P27    item
   P136   item
   P452   item

NOT used in this round (ambiguity / risk of bad mapping):
   P306   operating system → Q193424 web service 는 OS 가 아님. 다른 후보 검증 부족.
   P19    place of birth   → owner explicit Seoul confirmation 부재.
   P69    educated at      → owner 가 별도 결정.
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
# 동일 날짜의 audit log 에 append
AUDIT_FILE = AUDIT_DIR / "statements_added_2026-05-03.jsonl"

NEO_GENESIS_QID = "Q139569680"
YESOL_HEO_QID = "Q139569708"

# 11 SBU Q-IDs
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

# verified Q-IDs (this round)
Q_ORGANIZATION = "Q43229"
Q_SAAS         = "Q1254596"
Q_WEBSITE      = "Q35127"
Q_APP_SOFTWARE = "Q166142"
Q_AI           = "Q11660"
Q_IT           = "Q11661"
Q_FEMALE       = "Q6581072"
Q_SOUTH_KOREA  = "Q884"


# ──────────────────────────────────────────────
# Plan: (qid, property, value_kind, value)
#   value_kind ∈ {item, string, url, monolingualtext}
#   monolingualtext value = (text, language) tuple
# ──────────────────────────────────────────────

PLAN: list[tuple[str, str, str, object]] = []


def _add_neo_genesis() -> None:
    qid = NEO_GENESIS_QID

    # P31 instance of organization (이미 다른 P31 statement 가 있어도 OK; idempotent check 가 정확히 그 value 만 SKIP)
    PLAN.append((qid, "P31", "item", Q_ORGANIZATION))

    # P137 operator → Yesol Heo
    PLAN.append((qid, "P137", "item", YESOL_HEO_QID))

    # P1056 product or material produced → 11 SBU
    for _, sbu_qid in SBU_QIDS.items():
        PLAN.append((qid, "P1056", "item", sbu_qid))

    # P1451 motto text (monolingualtext)
    PLAN.append((qid, "P1451", "monolingualtext", ("AI Works. You Decide.", "en")))
    PLAN.append((qid, "P1451", "monolingualtext", ("AI는 일한다. 결정은 당신이 한다.", "ko")))


def _add_yesol_heo() -> None:
    qid = YESOL_HEO_QID

    # P21 sex or gender → female (publicly known, owner approved)
    PLAN.append((qid, "P21", "item", Q_FEMALE))

    # P27 country of citizenship → South Korea
    PLAN.append((qid, "P27", "item", Q_SOUTH_KOREA))


def _add_sbu(sbu_qid: str) -> None:
    # P31 instance of: SaaS + website + application software (다중 type 정합)
    PLAN.append((sbu_qid, "P31", "item", Q_SAAS))
    PLAN.append((sbu_qid, "P31", "item", Q_WEBSITE))
    PLAN.append((sbu_qid, "P31", "item", Q_APP_SOFTWARE))

    # P176 manufacturer → Neo Genesis (parent company creates the SBU)
    PLAN.append((sbu_qid, "P176", "item", NEO_GENESIS_QID))

    # P137 operator → Neo Genesis
    PLAN.append((sbu_qid, "P137", "item", NEO_GENESIS_QID))

    # P136 genre → AI + SaaS
    PLAN.append((sbu_qid, "P136", "item", Q_AI))
    PLAN.append((sbu_qid, "P136", "item", Q_SAAS))

    # P452 industry → information technology
    PLAN.append((sbu_qid, "P452", "item", Q_IT))


def build_plan() -> None:
    _add_neo_genesis()
    _add_yesol_heo()
    for _, sbu_qid in SBU_QIDS.items():
        _add_sbu(sbu_qid)


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
        self._refresh_csrf()

    def _refresh_csrf(self) -> None:
        r = self._get({"action": "query", "meta": "tokens", "type": "csrf"})
        self.csrf_token = r["query"]["tokens"]["csrftoken"]
        if self.csrf_token == "+\\":
            raise RuntimeError("CSRF token is anonymous — login likely failed silently.")

    def get_claims(self, entity: str) -> dict:
        r = self._get({"action": "wbgetclaims", "entity": entity})
        return r.get("claims", {})

    def create_claim(self, entity: str, prop: str, value_kind: str, value: object) -> dict:
        if value_kind == "item":
            assert isinstance(value, str)
            numeric_id = int(value.lstrip("Q"))
            value_str = json.dumps({"entity-type": "item", "numeric-id": numeric_id})
        elif value_kind in ("string", "url"):
            assert isinstance(value, str)
            value_str = json.dumps(value)
        elif value_kind == "monolingualtext":
            assert isinstance(value, tuple) and len(value) == 2
            text, lang = value
            value_str = json.dumps({"text": text, "language": lang})
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
# Idempotency
# ──────────────────────────────────────────────

def claim_matches(existing_claim: dict, value_kind: str, value: object) -> bool:
    mainsnak = existing_claim.get("mainsnak", {})
    if mainsnak.get("snaktype") != "value":
        return False
    dv = mainsnak.get("datavalue", {})
    dv_type = dv.get("type")
    dv_value = dv.get("value")

    if value_kind == "item":
        if dv_type != "wikibase-entityid":
            return False
        existing_id = (dv_value or {}).get("id") or f"Q{(dv_value or {}).get('numeric-id','?')}"
        return existing_id == value
    if value_kind in ("string", "url"):
        if dv_type != "string":
            return False
        return dv_value == value
    if value_kind == "monolingualtext":
        if dv_type != "monolingualtext":
            return False
        text, lang = value  # type: ignore[misc]
        return (dv_value or {}).get("text") == text and (dv_value or {}).get("language") == lang
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


def audit_log(record: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def _format_value(value_kind: str, value: object) -> str:
    if value_kind == "monolingualtext":
        text, lang = value  # type: ignore[misc]
        return f"({text!r}@{lang})"
    return str(value)


def _audit_value(value_kind: str, value: object) -> object:
    if value_kind == "monolingualtext":
        text, lang = value  # type: ignore[misc]
        return {"text": text, "language": lang}
    return value


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

    print(f"[plan] Total Phase-3 candidate statements: {len(plan)}")

    by_qid: dict[str, list[tuple[str, str, object]]] = {}
    for qid, prop, kind, val in plan:
        by_qid.setdefault(qid, []).append((prop, kind, val))

    if args.dry_run:
        print("\n=== DRY RUN ===")
        for qid in sorted(by_qid.keys()):
            entries = by_qid[qid]
            print(f"\n{qid}  ({len(entries)} candidate statements)")
            for prop, kind, val in entries:
                print(f"  {prop}  {kind}  {_format_value(kind, val)}")
        print(f"\n[dry-run] Audit log will be written to: {AUDIT_FILE}")
        return 0

    user, pw = load_credentials()
    print(f"[auth] Using BotPassword for {user.split('@')[0]}")

    client = WikidataClient(user, pw)
    client.login()
    print("[auth] Logged in. CSRF token acquired.")

    added = 0
    skipped = 0
    failed = 0
    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}

    for qid in sorted(by_qid.keys()):
        entries = by_qid[qid]
        print(f"\n--- {qid} ({len(entries)} candidate statements) ---")

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
                print(f"  SKIP {prop} = {_format_value(kind, val)}  (already present)")
                audit_log({
                    "action": "skip",
                    "qid": qid,
                    "property": prop,
                    "value_kind": kind,
                    "value": _audit_value(kind, val),
                    "reason": "already_present",
                })
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
                print(f"  ERR {prop} = {_format_value(kind, val)}  HTTP {e.code} {e.reason} {body}")
                audit_log({
                    "action": "error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": kind,
                    "value": _audit_value(kind, val),
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
                print(f"  ERR {prop} = {_format_value(kind, val)}  {e}")
                audit_log({
                    "action": "error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": kind,
                    "value": _audit_value(kind, val),
                    "error": str(e),
                })
                failed += 1
                time.sleep(args.throttle)
                continue

            if "error" in resp:
                err = resp["error"]
                # badtoken: refresh CSRF and retry once
                if err.get("code") == "badtoken":
                    print(f"  [token-refresh] CSRF expired; refreshing and retrying {prop} = {_format_value(kind, val)}")
                    try:
                        client._refresh_csrf()
                    except Exception as re:  # noqa: BLE001
                        print(f"  [ERR] CSRF refresh failed: {re}")
                    try:
                        resp = client.create_claim(qid, prop, kind, val)
                    except Exception as re:  # noqa: BLE001
                        print(f"  ERR {prop} = {_format_value(kind, val)}  retry-after-refresh: {re}")
                        audit_log({
                            "action": "error",
                            "qid": qid,
                            "property": prop,
                            "value_kind": kind,
                            "value": _audit_value(kind, val),
                            "error": str(re),
                            "retry_after_csrf_refresh": True,
                        })
                        failed += 1
                        time.sleep(args.throttle)
                        continue
                    if "error" not in resp:
                        claim_id = (resp.get("claim") or {}).get("id", "")
                        print(f"  ADD {prop} = {_format_value(kind, val)}  → {claim_id} (after CSRF refresh)")
                        audit_log({
                            "action": "added",
                            "qid": qid,
                            "property": prop,
                            "value_kind": kind,
                            "value": _audit_value(kind, val),
                            "claim_id": claim_id,
                            "retry_after_csrf_refresh": True,
                        })
                        added += 1
                        added_for_this_qid += 1
                        time.sleep(args.throttle)
                        continue
                    # If still error, fall through to error logging
                    err = resp["error"]
                print(f"  ERR {prop} = {_format_value(kind, val)}  wikidata: {err.get('code')} {err.get('info','')[:120]}")
                audit_log({
                    "action": "wikidata_error",
                    "qid": qid,
                    "property": prop,
                    "value_kind": kind,
                    "value": _audit_value(kind, val),
                    "error": err,
                })
                failed += 1
            else:
                claim_id = (resp.get("claim") or {}).get("id", "")
                print(f"  ADD {prop} = {_format_value(kind, val)}  → {claim_id}")
                audit_log({
                    "action": "added",
                    "qid": qid,
                    "property": prop,
                    "value_kind": kind,
                    "value": _audit_value(kind, val),
                    "claim_id": claim_id,
                })
                added += 1
                added_for_this_qid += 1

            time.sleep(args.throttle)

        after_counts[qid] = before_total + added_for_this_qid

    print("\n=== SUMMARY ===")
    print(f"Added:   {added}")
    print(f"Skipped: {skipped}  (already present)")
    print(f"Failed:  {failed}")
    print(f"Audit log: {AUDIT_FILE}")

    print("\n--- per-entity counts (before → after) ---")
    for qid in sorted(by_qid.keys()):
        b = before_counts.get(qid, "?")
        a = after_counts.get(qid, "?")
        print(f"  {qid}: {b} → {a}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
