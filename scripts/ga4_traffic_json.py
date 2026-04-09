"""GA4 traffic report with JSON output."""

import base64
import json
import os
import sys
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
SA_PATH = os.environ.get("GA4_SERVICE_ACCOUNT_PATH", "")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "ga4_result.json")

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


with open(SA_PATH, encoding="utf-8") as f:
    sa = json.load(f)

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
private_key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
signature = private_key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
jwt_token = signing_input + "." + b64url(signature)

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
    json.dump({"error": "TOKEN_FAIL", "detail": response.text}, open(OUT_PATH, "w"), indent=2)
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def run_report(site: dict, start: str, end: str, metrics: list[str]) -> dict:
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "metrics": [{"name": metric} for metric in metrics],
        "keepEmptyRows": True,
    }
    if site.get("host"):
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": "hostName",
                "stringFilter": {"matchType": "EXACT", "value": site["host"]},
            }
        }

    response = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/{site['property']}:runReport",
        headers=headers,
        json=body,
        timeout=15,
    )
    return response.json()


def value(report: dict, idx: int = 0) -> int:
    rows = report.get("rows", [])
    return int(rows[0]["metricValues"][idx]["value"]) if rows else 0


results = {}
for site in SITES:
    try:
        report_7d = run_report(site, "7daysAgo", "yesterday", ["activeUsers", "screenPageViews", "sessions"])
        report_28d = run_report(site, "28daysAgo", "yesterday", ["activeUsers", "screenPageViews", "sessions"])
        report_today = run_report(site, "today", "today", ["activeUsers"])
        results[site["name"]] = {
            "property": site["property"],
            "host": site.get("host"),
            "users_7d": value(report_7d, 0),
            "views_7d": value(report_7d, 1),
            "sessions_7d": value(report_7d, 2),
            "users_28d": value(report_28d, 0),
            "views_28d": value(report_28d, 1),
            "sessions_28d": value(report_28d, 2),
            "users_today": value(report_today, 0),
        }
    except Exception as exc:
        results[site["name"]] = {"error": str(exc)}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUT_PATH}")
