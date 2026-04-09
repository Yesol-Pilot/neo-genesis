"""GA4 Admin API lookup for web streams and measurement IDs."""

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
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "ga4_streams.json")

if not SA_PATH or not os.path.exists(SA_PATH):
    print(f"GA4_SERVICE_ACCOUNT_PATH not found: {SA_PATH}")
    sys.exit(1)

with open(SA_PATH, encoding="utf-8") as f:
    sa = json.load(f)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


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
    print(f"TOKEN FAIL: {response.text}")
    sys.exit(1)

props = [
    ("ToolPick", "properties/524659689"),
    ("UR WRONG", "properties/524964770"),
    ("K-OTT", "properties/525765817"),
    ("HeoYesol Portfolio", "properties/524705454"),
    ("NeoGenesis - Production", "properties/526345390"),
]

shared_hosts = {
    "AIForge": "aiforge.neogenesis.app",
    "CraftDesk": "craftdesk.neogenesis.app",
    "DeployStack": "deploystack.neogenesis.app",
    "FinStack": "finstack.neogenesis.app",
    "SellKit": "sellkit.neogenesis.app",
    "ReviewLab": "review.neogenesis.app",
    "WhyLab": "whylab.neogenesis.app",
    "EthicaAI": "ethica.neogenesis.app",
}

headers = {"Authorization": f"Bearer {token}"}
results: dict[str, dict] = {}

for name, prop in props:
    try:
        url = f"https://analyticsadmin.googleapis.com/v1beta/{prop}/dataStreams"
        response = requests.get(url, headers=headers, timeout=15)
        payload = response.json()
        if response.status_code != 200:
            results[name] = {
                "property": prop,
                "status": response.status_code,
                "error": payload.get("error", {}).get("message", "Unknown error"),
            }
            continue

        streams = []
        for stream in payload.get("dataStreams", []):
            streams.append(
                {
                    "name": stream.get("displayName", ""),
                    "measurementId": stream.get("webStreamData", {}).get("measurementId", "N/A"),
                    "defaultUri": stream.get("webStreamData", {}).get("defaultUri", "N/A"),
                    "type": stream.get("type", ""),
                }
            )

        results[name] = {"property": prop, "streams": streams}
    except Exception as exc:
        results[name] = {"property": prop, "error": str(exc)}

if "NeoGenesis - Production" in results:
    shared_result = results["NeoGenesis - Production"]
    for site, host in shared_hosts.items():
        results[site] = {
            "property": shared_result["property"],
            "sharedProperty": "NeoGenesis - Production",
            "host": host,
            "streams": shared_result.get("streams", []),
        }

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUT_PATH}")
