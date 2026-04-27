"""
Wikidata 14 Entity 자동 등록 스크립트
======================================

QuickStatements autoconfirmed (4일 + 50 edit) 요구 우회.
BotPassword 인증 → wbeditentity API 직접 호출.
새 계정도 가능 (rate limit 적용 — 새 계정 시간당 ~8 edit, 14 entity = 약 2시간).

전제:
1. https://www.wikidata.org/wiki/Special:BotPasswords 에서 BotPassword 발급
2. 환경변수 또는 .env 에 저장:
   WIKIDATA_USERNAME=your_username@NeoGenesisRegister
   WIKIDATA_PASSWORD=16자_비밀번호
3. pip install requests

사용:
    cd D:/00.test/neo-genesis
    python scripts/wikidata_register/register_entities.py

옵션:
    --dry-run         실제 등록 없이 entity payload 만 표시
    --skip-existing   Q139569680 statements 추가 건너뛰기
    --only=2,3,4      특정 entity 인덱스만 (1=NeoGenesis 보강, 2=Yesol Heo, 3-13=11 SBU)

결과:
- scripts/wikidata_register/result.json — Q-ID 매핑
- 콘솔에 진행 상황 + 에러
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import urllib.parse
import urllib.request


# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "NeoGenesisRegister/1.0 (https://neogenesis.app; neogenesis.research@gmail.com)"

ROOT = Path(__file__).resolve().parent
RESULT_FILE = ROOT / "result.json"

NEO_GENESIS_QID = "Q139569680"  # 이미 owner 가 등록한 본체


# ──────────────────────────────────────────────
# 14 Entity 정의
# ──────────────────────────────────────────────

# Action: "edit_existing" → Q139569680 보강
#         "create_new"    → 신규 entity 생성

ENTITIES = [
    # 1. Neo Genesis 본체 (이미 존재) — statements 추가
    {
        "_action": "edit_existing",
        "_qid": NEO_GENESIS_QID,
        "_label_short": "Neo Genesis (existing)",
        "labels": {
            "ko": "네오제네시스",
        },
        "descriptions": {
            "ko": "단일 자율 AI 시스템으로 11개의 라이브 비즈니스 유닛을 운영하는 AI 네이티브 자동화 회사",
        },
        "aliases": {
            "en": ["NeoGenesis", "Neo-Genesis"],
            "ko": ["네오 제네시스"],
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q4830453"},  # business
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},  # South Korea
            {"property": "P159", "value_type": "wikibase-item", "value_id": "Q8684"},  # Seoul
            {"property": "P856", "value_type": "url", "value": "https://neogenesis.app"},  # official website
            {"property": "P571", "value_type": "time", "value": "+2024-01-01T00:00:00Z", "precision": 9},  # inception
            {"property": "P2037", "value_type": "string", "value": "Yesol-Pilot"},  # GitHub
            {"property": "P452", "value_type": "wikibase-item", "value_id": "Q11660"},  # AI industry
            {"property": "P452", "value_type": "wikibase-item", "value_id": "Q11661"},  # IT industry
        ],
    },

    # 2. Yesol Heo (창업자)
    {
        "_action": "create_new",
        "_label_short": "Yesol Heo (founder)",
        "_register_key": "yesol_heo",
        "labels": {
            "en": "Yesol Heo",
            "ko": "허예솔",
        },
        "descriptions": {
            "en": "Korean entrepreneur and founder of Neo Genesis, an AI-native automation company running 11 live business units",
            "ko": "AI 네이티브 자동화 회사 Neo Genesis 의 창업자",
        },
        "aliases": {
            "en": ["Heo Yesol"],
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q5"},  # human
            {"property": "P27", "value_type": "wikibase-item", "value_id": "Q884"},  # citizenship: South Korea
            {"property": "P106", "value_type": "wikibase-item", "value_id": "Q3400985"},  # entrepreneur
            {"property": "P106", "value_type": "wikibase-item", "value_id": "Q5482740"},  # computer scientist
            {"property": "P800", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},  # notable work: Neo Genesis
            {"property": "P2037", "value_type": "string", "value": "Yesol-Pilot"},
            {"property": "P856", "value_type": "url", "value": "https://heoyesol.kr"},
        ],
    },

    # 3-13. 11 SBU
    {
        "_action": "create_new",
        "_label_short": "UR WRONG",
        "_register_key": "ur_wrong",
        "labels": {"en": "UR WRONG"},
        "descriptions": {
            "en": "AI debate platform that generates arguments for both sides on any topic with community voting",
            "ko": "주제 양측 논거를 AI가 생성하고 커뮤니티 투표로 토론을 진화시키는 AI 토론 플랫폼",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://ur-wrong.com"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "ToolPick",
        "_register_key": "toolpick",
        "labels": {"en": "ToolPick", "ko": "툴픽"},
        "descriptions": {
            "en": "B2B SaaS comparison engine that uses AI to analyze hundreds of tools and surface the optimal stack",
            "ko": "AI가 수백 개 도구를 분석해 최적 스택을 찾아주는 B2B SaaS 비교 엔진",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://toolpick.dev"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "ReviewLab",
        "_register_key": "reviewlab",
        "labels": {"en": "ReviewLab", "ko": "리뷰랩"},
        "descriptions": {
            "en": "AI-powered product review magazine producing data-driven reviews from automated analysis",
            "ko": "자동 분석으로 데이터 기반 리뷰를 생성하는 AI 제품 리뷰 매거진",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://review.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "K-OTT",
        "_register_key": "kott",
        "labels": {"en": "K-OTT"},
        "descriptions": {
            "en": "AI-powered OTT recommendation platform for Korean streaming services including Netflix, Disney+, Wavve, and Tving",
            "ko": "넷플릭스, 디즈니+, 웨이브, 티빙 등을 아우르는 한국 OTT 추천 AI 플랫폼",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://kott.kr"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "WhyLab",
        "_register_key": "whylab",
        "labels": {"en": "WhyLab", "ko": "와이랩"},
        "descriptions": {
            "en": "Causal inference SaaS that answers Why questions with rigorous data-driven causal analysis",
            "ko": "엄격한 데이터 기반 인과 분석으로 Why 질문에 답하는 인과추론 SaaS",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://whylab.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "EthicaAI",
        "_register_key": "ethicaai",
        "labels": {"en": "EthicaAI", "ko": "에티카AI"},
        "descriptions": {
            "en": "AI ethics research project verifying Amartya Sen rationality theory via multi-agent reinforcement learning",
            "ko": "멀티 에이전트 강화학습으로 아마르티아 센의 합리성 이론을 검증하는 AI 윤리 연구 프로젝트",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://ethica.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "FinStack",
        "_register_key": "finstack",
        "labels": {"en": "FinStack", "ko": "핀스택"},
        "descriptions": {
            "en": "Fintech tool reviews covering banking APIs, payment gateways, and financial infrastructure",
            "ko": "뱅킹 API, 결제 게이트웨이, 금융 인프라를 다루는 핀테크 도구 리뷰",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://finstack.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "AIForge",
        "_register_key": "aiforge",
        "labels": {"en": "AIForge"},
        "descriptions": {
            "en": "AI tool deep analysis with comprehensive benchmarks and ROI calculations for enterprise AI solutions",
            "ko": "엔터프라이즈 AI 솔루션의 종합 벤치마크와 ROI 계산을 제공하는 AI 도구 심층 분석",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://aiforge.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "SellKit",
        "_register_key": "sellkit",
        "labels": {"en": "SellKit", "ko": "셀킷"},
        "descriptions": {
            "en": "E-commerce tool reviews including Shopify apps, marketing automation, and conversion optimization",
            "ko": "쇼피파이 앱, 마케팅 자동화, 전환 최적화를 포함한 이커머스 도구 리뷰",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://sellkit.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "DeployStack",
        "_register_key": "deploystack",
        "labels": {"en": "DeployStack", "ko": "디플로이스택"},
        "descriptions": {
            "en": "DevOps tool reviews covering CI/CD pipelines, cloud platforms, and infrastructure-as-code",
            "ko": "CI/CD 파이프라인, 클라우드 플랫폼, IaC를 다루는 DevOps 도구 리뷰",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://deploystack.neogenesis.app"},
        ],
    },
    {
        "_action": "create_new",
        "_label_short": "CraftDesk",
        "_register_key": "craftdesk",
        "labels": {"en": "CraftDesk", "ko": "크래프트데스크"},
        "descriptions": {
            "en": "Design tool reviews including UI kits, prototyping tools, and creative workflow optimization",
            "ko": "UI 키트, 프로토타이핑 도구, 창작 워크플로 최적화를 포함한 디자인 도구 리뷰",
        },
        "claims": [
            {"property": "P31", "value_type": "wikibase-item", "value_id": "Q1668024"},
            {"property": "P127", "value_type": "wikibase-item", "value_id": NEO_GENESIS_QID},
            {"property": "P17", "value_type": "wikibase-item", "value_id": "Q884"},
            {"property": "P856", "value_type": "url", "value": "https://craftdesk.neogenesis.app"},
        ],
    },
]


# ──────────────────────────────────────────────
# Wikidata API helpers (urllib + cookiejar 사용 — requests 의존성 없이)
# ──────────────────────────────────────────────

class WikidataClient:
    def __init__(self, username: str, password: str):
        import http.cookiejar
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
        # 1. Get login token
        r = self._get({"action": "query", "meta": "tokens", "type": "login"})
        login_token = r["query"]["tokens"]["logintoken"]

        # 2. Login
        r = self._post({
            "action": "login",
            "lgname": self.username,
            "lgpassword": self.password,
            "lgtoken": login_token,
        })
        if r.get("login", {}).get("result") != "Success":
            raise RuntimeError(f"Login failed: {r}")

        # 3. Get CSRF token (for editing)
        r = self._get({"action": "query", "meta": "tokens", "type": "csrf"})
        self.csrf_token = r["query"]["tokens"]["csrftoken"]
        if self.csrf_token == "+\\":
            raise RuntimeError("CSRF token is anonymous — login likely failed silently. Check BotPassword grants.")

    def edit_entity(self, data: dict, *, qid: Optional[str] = None) -> dict:
        params: dict = {
            "action": "wbeditentity",
            "data": json.dumps(data, ensure_ascii=False),
            "token": self.csrf_token,
            "bot": "1",
        }
        if qid:
            params["id"] = qid
        else:
            params["new"] = "item"
        return self._post(params)


# ──────────────────────────────────────────────
# Entity payload 빌더
# ──────────────────────────────────────────────

def claim_to_snak(claim: dict) -> dict:
    """Convert simplified claim dict to Wikidata mainsnak format."""
    prop = claim["property"]
    vt = claim["value_type"]

    if vt == "wikibase-item":
        datavalue = {
            "type": "wikibase-entityid",
            "value": {"entity-type": "item", "id": claim["value_id"]},
        }
    elif vt == "string":
        datavalue = {"type": "string", "value": claim["value"]}
    elif vt == "url":
        datavalue = {"type": "string", "value": claim["value"]}
    elif vt == "time":
        datavalue = {
            "type": "time",
            "value": {
                "time": claim["value"],
                "timezone": 0,
                "before": 0,
                "after": 0,
                "precision": claim.get("precision", 11),
                "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
            },
        }
    else:
        raise ValueError(f"Unknown value_type: {vt}")

    return {
        "mainsnak": {
            "snaktype": "value",
            "property": prop,
            "datavalue": datavalue,
        },
        "type": "statement",
        "rank": "normal",
    }


def build_payload(entity: dict) -> dict:
    payload: dict = {}
    if "labels" in entity:
        payload["labels"] = {
            lang: {"language": lang, "value": v}
            for lang, v in entity["labels"].items()
        }
    if "descriptions" in entity:
        payload["descriptions"] = {
            lang: {"language": lang, "value": v}
            for lang, v in entity["descriptions"].items()
        }
    if "aliases" in entity:
        payload["aliases"] = {
            lang: [{"language": lang, "value": v} for v in vals]
            for lang, vals in entity["aliases"].items()
        }
    if "claims" in entity and entity["claims"]:
        payload["claims"] = [claim_to_snak(c) for c in entity["claims"]]
    return payload


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    user = os.environ.get("WIKIDATA_USERNAME")
    pw = os.environ.get("WIKIDATA_PASSWORD")
    if user and pw:
        return user, pw

    # .env.local 또는 .env 자동 로드
    for env_file in [".env.local", ".env", "scripts/wikidata_register/.env"]:
        p = Path(env_file)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
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

    print("ERROR: WIKIDATA_USERNAME / WIKIDATA_PASSWORD 환경변수 또는 .env.local 필요")
    print("  https://www.wikidata.org/wiki/Special:BotPasswords 에서 발급")
    print("  형식: WIKIDATA_USERNAME=your_username@NeoGenesisRegister")
    print("        WIKIDATA_PASSWORD=16자_password")
    sys.exit(1)


def parse_qid_from_response(resp: dict) -> Optional[str]:
    return resp.get("entity", {}).get("id")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", help="Q139569680 보강 건너뛰기")
    parser.add_argument("--only", default=None, help="Comma 분리 인덱스 (1-13)")
    parser.add_argument("--throttle", type=float, default=8.0, help="요청 간 대기 (초). 새 계정 rate limit 안전치 8s")
    args = parser.parse_args()

    indices = None
    if args.only:
        indices = {int(x) for x in args.only.split(",") if x.strip()}

    user, pw = load_credentials()
    print(f"[auth] Using BotPassword for {user.split('@')[0]}")

    if args.dry_run:
        print("\n=== DRY RUN ===")
        for i, e in enumerate(ENTITIES, start=1):
            payload = build_payload(e)
            print(f"\n--- Entity {i}: {e['_label_short']} ({e['_action']}) ---")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    client = WikidataClient(user, pw)
    print("[auth] Logging in...")
    client.login()
    print(f"[auth] OK. CSRF token acquired.")

    results = {}
    if RESULT_FILE.exists():
        results = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

    for i, entity in enumerate(ENTITIES, start=1):
        if indices and i not in indices:
            continue
        if args.skip_existing and entity["_action"] == "edit_existing":
            continue

        label = entity["_label_short"]
        print(f"\n[{i:02d}/{len(ENTITIES):02d}] {label} ({entity['_action']})")
        payload = build_payload(entity)

        try:
            if entity["_action"] == "edit_existing":
                resp = client.edit_entity(payload, qid=entity["_qid"])
            else:
                resp = client.edit_entity(payload)
        except Exception as e:  # noqa: BLE001
            print(f"  ERRERROR: {e}")
            continue

        if "error" in resp:
            print(f"  ERRWikidata error: {resp['error']}")
            continue

        qid = parse_qid_from_response(resp)
        if qid:
            print(f"  OK{qid}")
            key = entity.get("_register_key") or entity.get("_qid", qid)
            results[key] = {
                "qid": qid,
                "url": f"https://www.wikidata.org/wiki/{qid}",
                "registered_at": time.strftime("%Y-%m-%d"),
                "label": label,
            }
            RESULT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            print(f"  ? response: {json.dumps(resp, ensure_ascii=False)[:200]}")

        # Rate limit 안전치 (새 계정 시간당 ~8 edit)
        if i < len(ENTITIES):
            print(f"  …throttle {args.throttle}s (rate limit safe)")
            time.sleep(args.throttle)

    print(f"\n=== DONE ===")
    print(f"Results saved to: {RESULT_FILE}")
    print(f"Q-ID mapping:")
    for k, v in results.items():
        print(f"  {k}: {v['qid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
