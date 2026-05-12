"""GA4 traffic report via the Data API.

OAuth refresh tokens are preferred because the GA4 properties are usually
granted to a human Google account. Service-account JWT remains as a fallback
for environments that explicitly grant property access to the bot account.
"""

import base64
import json
import os
import sys
import time

from dotenv import load_dotenv

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"), override=False)


def resolve_service_account_path() -> str:
    candidates = [
        os.environ.get("GA4_SERVICE_ACCOUNT_PATH", ""),
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return candidates[0] if candidates else ""


def resolve_oauth_client_path() -> str:
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()

SITES = [
    {"name": "ToolPick", "property": "properties/524659689"},
    {"name": "UR WRONG", "property": "properties/524964770"},
    {"name": "K-OTT", "property": "properties/525765817"},
    {"name": "HeoYesol Portfolio", "property": "properties/524705454"},
    {"name": "AIForge", "property": "properties/526345390", "host": "aiforge.neogenesis.app"},
    {"name": "CraftDesk", "property": "properties/526345390", "host": "craftdesk.neogenesis.app"},
    {"name": "SellKit", "property": "properties/526345390", "host": "sellkit.neogenesis.app"},
    {"name": "FinStack", "property": "properties/526345390", "host": "finstack.neogenesis.app"},
    {"name": "DeployStack", "property": "properties/526345390", "host": "deploystack.neogenesis.app"},
    {"name": "ReviewLab", "property": "properties/526345390", "host": "review.neogenesis.app"},
    {"name": "WhyLab", "property": "properties/526345390", "host": "whylab.neogenesis.app"},
    {"name": "EthicaAI", "property": "properties/526345390", "host": "ethica.neogenesis.app"},
]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def get_service_account_access_token(sa: dict) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    header = {"alg": "RS256", "typ": "JWT"}
    now = int(time.time())
    claims = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = b64url(json.dumps(header).encode()) + "." + b64url(json.dumps(claims).encode())
    pk = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = pk.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt_token = signing_input + "." + b64url(sig)

    import requests

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
        },
        timeout=15,
    )
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError(f"service-account token failed: {response.text[:200]}")
    return token


def get_oauth_access_token() -> str:
    import requests

    client_path = resolve_oauth_client_path()
    refresh_token = os.environ.get("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN", "").strip()
    if not client_path or not refresh_token:
        raise RuntimeError("OAuth client path or refresh token is not configured")
    if not os.path.exists(client_path):
        raise RuntimeError(f"OAuth client path does not exist: {client_path}")

    with open(client_path, encoding="utf-8") as f:
        client = json.load(f)
    client_info = client.get("installed") or client.get("web") or {}
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_info.get("client_id"),
            "client_secret": client_info.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        error = payload.get("error") or response.text[:200]
        raise RuntimeError(f"OAuth refresh token failed: {error}")
    return token


def resolve_access_token() -> tuple[str, str]:
    errors = []
    try:
        return get_oauth_access_token(), "oauth_refresh_token"
    except Exception as exc:
        errors.append(str(exc))

    sa_path = resolve_service_account_path()
    if sa_path and os.path.exists(sa_path):
        try:
            with open(sa_path, encoding="utf-8") as f:
                return get_service_account_access_token(json.load(f)), "service_account"
        except Exception as exc:
            errors.append(str(exc))
    elif sa_path:
        errors.append(f"GA4 service account path does not exist: {sa_path}")

    raise SystemExit("GA4 token resolution failed: " + " | ".join(errors))


def get_access_token(sa: dict | None = None) -> str:
    """Backward-compatible token helper for older reporting scripts."""
    try:
        return get_oauth_access_token()
    except Exception:
        if sa is not None:
            return get_service_account_access_token(sa)
    return resolve_access_token()[0]


def run_report(
    prop: str,
    token: str,
    start: str,
    end: str,
    metrics: list[str],
    host: str | None = None,
):
    import requests

    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "metrics": [{"name": metric} for metric in metrics],
        "keepEmptyRows": True,
    }
    if host:
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": "hostName",
                "stringFilter": {"matchType": "EXACT", "value": host},
            }
        }

    response = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    return response.json()


def val(report: dict, idx: int = 0) -> str:
    if "error" in report:
        error = report["error"]
        status = error.get("status", "ERROR")
        code = error.get("code", "unknown")
        raise RuntimeError(f"GA4 API {status} ({code})")
    rows = report.get("rows", [])
    if not rows:
        return "0"
    return rows[0]["metricValues"][idx]["value"]


def main():
    token, token_source = resolve_access_token()
    print(f"TOKEN OK ({token_source})")
    print("NOTE: NeoGenesis subdomains are reported via shared property properties/526345390.")

    metrics = ["activeUsers", "screenPageViews", "sessions"]
    separator = "=" * 90
    header = f"{'Site':<22} {'7d Users':>10} {'7d Views':>10} {'28d Users':>10} {'28d Views':>10} {'Today':>8}"

    print(f"\n{separator}")
    print(header)
    print(separator)

    totals = {"7u": 0, "7v": 0, "28u": 0, "28v": 0, "today": 0}
    had_error = False

    for site in SITES:
        try:
            report_7d = run_report(site["property"], token, "7daysAgo", "yesterday", metrics, site.get("host"))
            report_28d = run_report(site["property"], token, "28daysAgo", "yesterday", metrics, site.get("host"))
            report_today = run_report(site["property"], token, "today", "today", ["activeUsers"], site.get("host"))

            users_7d, views_7d = val(report_7d, 0), val(report_7d, 1)
            users_28d, views_28d = val(report_28d, 0), val(report_28d, 1)
            today_users = val(report_today, 0)

            totals["7u"] += int(users_7d)
            totals["7v"] += int(views_7d)
            totals["28u"] += int(users_28d)
            totals["28v"] += int(views_28d)
            totals["today"] += int(today_users)

            print(
                f"{site['name']:<22} {users_7d:>10} {views_7d:>10} "
                f"{users_28d:>10} {views_28d:>10} {today_users:>8}"
            )
        except Exception as exc:
            had_error = True
            print(f"{site['name']:<22} ERROR: {str(exc)[:50]}")

    print(separator)
    print(
        f"{'TOTAL':<22} {totals['7u']:>10} {totals['7v']:>10} "
        f"{totals['28u']:>10} {totals['28v']:>10} {totals['today']:>8}"
    )
    print(separator)

    engagement_metrics = [
        "bounceRate",
        "averageSessionDuration",
        "engagementRate",
        "screenPageViewsPerSession",
    ]
    active_sites = [
        site for site in SITES if site["name"] in {"ToolPick", "UR WRONG", "K-OTT", "CraftDesk", "DeployStack"}
    ]

    if active_sites:
        print(f"\n{'Site':<22} {'Bounce%':>10} {'AvgSec':>10} {'Engage%':>10} {'PV/Sess':>10}")
        print("-" * 66)
        for site in active_sites:
            try:
                report = run_report(
                    site["property"],
                    token,
                    "7daysAgo",
                    "yesterday",
                    engagement_metrics,
                    site.get("host"),
                )
                bounce_rate, avg_sec, engage_rate, pv_per_session = [val(report, i) for i in range(4)]
                print(
                    f"{site['name']:<22} {float(bounce_rate) * 100:>9.1f}% "
                    f"{float(avg_sec):>9.1f}s {float(engage_rate) * 100:>9.1f}% {float(pv_per_session):>9.2f}"
                )
            except Exception as exc:
                had_error = True
                print(f"{site['name']:<22} ERROR: {str(exc)[:40]}")

    print(f"\n{'Site':<22} {'This Wk':>10} {'Last Wk':>10} {'WoW %':>10}")
    print("-" * 56)
    for site in SITES:
        try:
            this_week = run_report(
                site["property"], token, "7daysAgo", "yesterday", ["activeUsers"], site.get("host")
            )
            last_week = run_report(
                site["property"], token, "14daysAgo", "8daysAgo", ["activeUsers"], site.get("host")
            )
            this_value = int(val(this_week, 0))
            last_value = int(val(last_week, 0))
            if last_value > 0:
                delta = ((this_value - last_value) / last_value) * 100
                print(f"{site['name']:<22} {this_value:>10} {last_value:>10} {delta:>+9.1f}%")
            elif this_value > 0:
                print(f"{site['name']:<22} {this_value:>10} {last_value:>10}      NEW")
        except Exception as exc:
            had_error = True
            print(f"{site['name']:<22} ERROR: {str(exc)[:40]}")

    print(separator)
    if had_error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
