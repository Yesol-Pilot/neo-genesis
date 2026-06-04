# -*- coding: utf-8 -*-
"""
Analytics brain tools — GA4 트래픽 + PostHog DAU (sora ALL_TOOLS 등록용).

2026-05-29: 기존 standalone scripts/ga4_traffic_report.py + posthog_traffic.py 의
검증된 REST/JWT 로직을 brain 도구로 wrap. owner "오늘 kott 방문자" 류 텔레그램 직접.
무거운 SDK 불요 — requests + cryptography(JWT) 만.

NOTE: `from __future__ import annotations` 금지 — Gemini AFC 가 type hint 로 인자
검증(isinstance) 하는데 lazy string annotation 이면 "isinstance arg 2" 에러. 실타입 유지.
"""
import base64
import json
import os
import time

# SBU → GA4 property + (선택) hostName 필터.  scripts/ga4_traffic_report.py 정합.
_SBU_GA4 = {
    "neogenesis": ("properties/526345390", None),
    "toolpick": ("properties/524659689", None),
    "ur-wrong": ("properties/524964770", None),
    "urwrong": ("properties/524964770", None),
    "kott": ("properties/525765817", None),
    "k-ott": ("properties/525765817", None),
    "heoyesol": ("properties/524705454", None),
    "portfolio": ("properties/524705454", None),
    # 공유 property + host 필터
    "aiforge": ("properties/526345390", "aiforge.neogenesis.app"),
    "craftdesk": ("properties/526345390", "craftdesk.neogenesis.app"),
    "sellkit": ("properties/526345390", "sellkit.neogenesis.app"),
    "finstack": ("properties/526345390", "finstack.neogenesis.app"),
    "deploystack": ("properties/526345390", "deploystack.neogenesis.app"),
    "reviewlab": ("properties/526345390", "review.neogenesis.app"),
    "whylab": ("properties/526345390", "whylab.neogenesis.app"),
}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _ga4_sa_token() -> str:
    """GA4 service account → access token (RS256 JWT, REST)."""
    sa_path = os.getenv("GA4_SERVICE_ACCOUNT_PATH", "/app/secrets/ga4_service_account.json")
    if not os.path.exists(sa_path):
        # WSL2 Windows-path fallback
        alt = sa_path.replace("\\", "/")
        if alt.startswith("D:"):
            alt = "/mnt/d" + alt[2:]
        sa_path = alt if os.path.exists(alt) else "/app/secrets/ga4_service_account.json"
    with open(sa_path, encoding="utf-8") as f:
        sa = json.load(f)
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    import requests
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    signing_input = _b64url(json.dumps(header).encode()) + "." + _b64url(json.dumps(claims).encode())
    pk = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = pk.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt_token = signing_input + "." + _b64url(sig)
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt_token},
        timeout=15,
    )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"GA4 token 실패: {resp.text[:150]}")
    return token


def _ga4_run(prop: str, token: str, start: str, end: str, host: str | None):
    import requests
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "screenPageViews"}],
        "keepEmptyRows": True,
    }
    if host:
        body["dimensionFilter"] = {"filter": {"fieldName": "hostName",
                                              "stringFilter": {"matchType": "EXACT", "value": host}}}
    resp = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body, timeout=15,
    )
    return resp.json()


def get_sbu_traffic(sbu: str = "", days: int = 7) -> str:
    """SBU 웹사이트 방문자/세션/페이지뷰를 GA4에서 조회합니다.

    Args:
        sbu: SBU 이름 (kott, toolpick, ur-wrong, heoyesol, aiforge, reviewlab 등).
             빈 값이면 주요 SBU 전체 요약.
        days: 최근 N일 (기본 7)
    """
    start = f"{max(1, int(days))}daysAgo"
    try:
        token = _ga4_sa_token()
    except Exception as e:
        return json.dumps({"error": f"GA4 인증 실패: {str(e)[:160]}"}, ensure_ascii=False)

    def one(name):
        prop, host = _SBU_GA4[name]
        rep = _ga4_run(prop, token, start, "today", host)
        if "error" in rep:
            return {"sbu": name, "error": rep["error"].get("message", "")[:100]}
        rows = rep.get("rows", [])
        if not rows:
            return {"sbu": name, "sessions": 0, "users": 0, "pageviews": 0}
        m = rows[0]["metricValues"]
        return {"sbu": name, "sessions": int(m[0]["value"]), "users": int(m[1]["value"]),
                "pageviews": int(m[2]["value"])}

    key = (sbu or "").strip().lower().replace(" ", "")
    if key and key in _SBU_GA4:
        return json.dumps({"window": f"최근 {days}일", **one(key)}, ensure_ascii=False)
    # 전체 요약 (주요 5)
    targets = ["kott", "toolpick", "ur-wrong", "heoyesol", "reviewlab"]
    out = []
    for t in targets:
        try:
            out.append(one(t))
        except Exception as e:
            out.append({"sbu": t, "error": str(e)[:80]})
    return json.dumps({"window": f"최근 {days}일", "sbu_traffic": out}, ensure_ascii=False)


def get_posthog_events(days: int = 1) -> str:
    """PostHog 에서 최근 N일 일별 활성 사용자(DAU)/이벤트 수를 조회합니다 (HogQL).

    Args:
        days: 최근 N일 (기본 1 = 어제~오늘)
    """
    import requests
    api_key = os.getenv("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.getenv("POSTHOG_PROJECT_ID", "").strip()
    host = os.getenv("POSTHOG_API_HOST", "https://us.posthog.com").strip().rstrip("/")
    if not api_key or not project_id:
        return json.dumps({"error": "PostHog 자격증명 없음 (POSTHOG_PERSONAL_API_KEY/PROJECT_ID)"}, ensure_ascii=False)
    d = max(1, int(days))
    query = (
        f"SELECT toDate(timestamp) AS day, count() AS events, count(DISTINCT distinct_id) AS dau "
        f"FROM events WHERE timestamp >= now() - INTERVAL {d} DAY "
        f"GROUP BY day ORDER BY day DESC LIMIT {d + 1}"
    )
    try:
        resp = requests.post(
            f"{host}/api/projects/{project_id}/query/",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"query": {"kind": "HogQLQuery", "query": query}},
            timeout=20,
        )
        data = resp.json()
        results = data.get("results", [])
        rows = [{"day": str(r[0]), "events": r[1], "dau": r[2]} for r in results]
        return json.dumps({"window": f"최근 {d}일", "posthog": rows}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"PostHog 조회 실패: {str(e)[:150]}"}, ensure_ascii=False)


def get_weekly_report() -> str:
    """이번주 종합 주간 보고를 생성합니다 (GA4 SBU 트래픽 + PostHog DAU + 최근 git 커밋 + 자비스 audit).

    owner "이번주 한 일 / 주간 보고" 류 명령에 1-command 합성 보고.
    """
    report = {"period": "최근 7일"}
    # 1. GA4 SBU 트래픽
    try:
        report["traffic"] = json.loads(get_sbu_traffic("", 7)).get("sbu_traffic", [])
    except Exception as e:
        report["traffic"] = {"error": str(e)[:80]}
    # 2. PostHog DAU
    try:
        report["posthog"] = json.loads(get_posthog_events(7)).get("posthog", [])
    except Exception as e:
        report["posthog"] = {"error": str(e)[:80]}
    # 3. 최근 git 커밋 (neo-genesis, WSL interop)
    try:
        from src.core.tools.system_tools import _local_powershell, _LOCAL_EXEC
        if _LOCAL_EXEC:
            r = _local_powershell(
                "cd D:\\00.test\\neo-genesis; git log --since='7 days ago' --oneline 2>&1 | Select-Object -First 15", 30)
            report["recent_commits"] = (r.get("stdout") or r.get("error") or "")[:800]
        else:
            report["recent_commits"] = "(local exec 비활성)"
    except Exception as e:
        report["recent_commits"] = f"git 조회 실패: {str(e)[:80]}"
    # 4. 자비스 audit 요약
    try:
        from src.core.tools.system_tools import get_jarvis_audit_summary
        report["jarvis_audit"] = json.loads(get_jarvis_audit_summary(168)).get("counts", {})
    except Exception as e:
        report["jarvis_audit"] = {"error": str(e)[:80]}
    return json.dumps(report, ensure_ascii=False, default=str)


ANALYTICS_TOOLS = [get_sbu_traffic, get_posthog_events, get_weekly_report]


if __name__ == "__main__":
    print("=== GA4 kott (7d) ===")
    print(get_sbu_traffic("kott", 7))
    print("=== GA4 전체 (7d) ===")
    print(get_sbu_traffic("", 7))
    print("=== PostHog (1d) ===")
    print(get_posthog_events(1))
