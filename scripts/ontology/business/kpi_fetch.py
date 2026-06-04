"""Neo Genesis -- KPI auto-fetch (GA4 / GSC / PostHog → biz:KPI.current_value).

매일 fetch 해서 KPI 노드의 `current_value` + `current_value_observed_at` 갱신.

v0.1 PoC: 실 API 호출 대신 placeholder 박제 (credentials 없을 시).
v0.2 권고: GA4 service-account / PostHog API / GSC OAuth 통합.

Usage:
    python scripts/ontology/business/kpi_fetch.py [--dry-run] [--source ga4|gsc|posthog|all]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"

# Force stdout/stderr to UTF-8 (Windows cp949 console mojibake fix)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


def _load_dotenv_chain(repo_root: Path) -> None:
    """Auto-load .env + .env.local from neo-genesis root. Process env only."""
    for env_file in [repo_root / ".env", repo_root / ".env.local"]:
        if not env_file.exists():
            continue
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        except Exception as e:
            print(f"[WARN] .env load failed ({env_file}): {e}", file=sys.stderr)


_load_dotenv_chain(REPO_ROOT)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# Track auth/permission failures where creds WERE present but the API rejected
# them (expired token / 403). Distinct from creds-absent (legit SKIP). Lets
# main() surface a WARN exit so daily_maintain stops reporting silent "OK"
# while every analytics feed is actually dead (2026-05-16 grill-toast finding).
_FETCH_ERRORS: list[dict] = []


METRIC_TO_GA4 = {
    "monthly_active_users": "activeUsers",
    "daily_active_users": "activeUsers",
    "page_views": "screenPageViews",
    "sessions": "sessions",
    "conversion_rate": "userConversionRate",
}

# Per CREDENTIAL_BIBLE.md (2026-04-01 라이브). 14 SBU GA4 property IDs.
GA4_PROPERTY_MAP = {
    "toolpick": "524659689",
    "ur-wrong": "524964770",
    "aiforge": "526067387",
    "craftdesk": "526119553",
    "deploystack": "526129622",
    "finstack": "526115982",
    "sellkit": "526095401",
    "reviewlab": "526133350",
    "kott": "525765817",
    "ethicaai-paper": "524688217",
    "whylab": "525758342",
    "whylab-paper": "525758342",
    "heoyesol-brand": "524705454",
    "2dlivegame": "524700566",
    "multiverse-creature-lab": "524681004",
}

GSC_SITE_URL_MAP = {
    "kott": "https://kott.kr",
    "toolpick": "https://toolpick.dev",
    "ur-wrong": "https://ur-wrong.com",
    "heoyesol-brand": "https://heoyesol.kr",
}


def fetch_ga4(product_slug: str, metric: str) -> dict | None:
    """Fetch GA4 daily metric via google-analytics-data SDK.

    Required env:
    - GOOGLE_APPLICATION_CREDENTIALS (SA JSON path) OR GA4_SERVICE_ACCOUNT_PATH
    GA4 Property ID 는 GA4_PROPERTY_MAP 에서 자동 조회 (per CREDENTIAL_BIBLE 2026-04-01).
    """
    # 1순위: hardcoded map (per CREDENTIAL_BIBLE)
    prop_id = GA4_PROPERTY_MAP.get(product_slug)
    if not prop_id:
        prop_id = os.environ.get(f"GA4_PROPERTY_ID_{product_slug.upper()}")
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GA4_SERVICE_ACCOUNT_PATH")
    if not prop_id or not creds:
        return None
    if not Path(creds).exists():
        return None

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Metric, RunReportRequest, Dimension, FilterExpression, Filter
        )
    except ImportError:
        # Package missing — graceful skip
        return None

    ga4_metric = METRIC_TO_GA4.get(metric)
    if not ga4_metric:
        return None

    client = BetaAnalyticsDataClient()
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=30 if "monthly" in metric else 1)

    # If using shared property, filter by hostname
    dimension_filter = None
    domain_map = {"kott": "kott.kr", "toolpick": "toolpick.dev", "ur-wrong": "ur-wrong.com",
                  "heoyesol-brand": "heoyesol.kr"}
    if product_slug in domain_map and "SHARED" in (os.environ.get("GA4_PROPERTY_ID_SHARED", "") or ""):
        dimension_filter = FilterExpression(
            filter=Filter(field_name="hostName", string_filter=Filter.StringFilter(value=domain_map[product_slug]))
        )

    request = RunReportRequest(
        property=f"properties/{prop_id}",
        date_ranges=[DateRange(start_date=start_date.isoformat(), end_date=end_date.isoformat())],
        metrics=[Metric(name=ga4_metric)],
        dimension_filter=dimension_filter,
    )
    try:
        response = client.run_report(request)
        if not response.rows:
            return {"value": 0, "source": "ga4_live"}
        total = sum(int(row.metric_values[0].value) for row in response.rows)
        return {"value": total, "source": "ga4_live", "period_days": (end_date - start_date).days}
    except Exception as e:
        print(f"[WARN] GA4 fetch failed for {product_slug}/{metric}: {e}", file=sys.stderr)
        _FETCH_ERRORS.append({"source": "ga4", "product": product_slug, "error": str(e)[:200]})
        return None


def fetch_gsc(product_slug: str, metric: str) -> dict | None:
    """Fetch GSC daily metric via google-search-console OAuth refresh token.

    Per CREDENTIAL_BIBLE: GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN in .env.local +
    GOOGLE_OAUTH_CLIENT_SECRET_FILE (oauth client JSON).
    """
    # 1순위: hardcoded GSC site mapping
    site_url = GSC_SITE_URL_MAP.get(product_slug)
    if not site_url:
        site_url = os.environ.get(f"GSC_SITE_URL_{product_slug.upper()}")
    refresh = (os.environ.get("GSC_REFRESH_TOKEN")
               or os.environ.get("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN"))
    # Load client_id / client_secret from oauth JSON file if provided
    client_id = os.environ.get("GSC_CLIENT_ID")
    client_secret = os.environ.get("GSC_CLIENT_SECRET")
    if not (client_id and client_secret):
        oauth_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE")
        if oauth_file and Path(oauth_file).exists():
            try:
                oauth_data = json.loads(Path(oauth_file).read_text(encoding="utf-8"))
                installed = oauth_data.get("installed", oauth_data.get("web", {}))
                client_id = client_id or installed.get("client_id")
                client_secret = client_secret or installed.get("client_secret")
            except Exception:
                pass
    if not all([site_url, refresh, client_id, client_secret]):
        return None

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None

    try:
        creds = Credentials(
            None,
            refresh_token=refresh,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("searchconsole", "v1", credentials=creds)
        end_date = dt.date.today()
        start_date = end_date - dt.timedelta(days=28)
        body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": [],  # site-wide aggregate
        }
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = resp.get("rows", [])
        impressions = int(rows[0].get("impressions", 0)) if rows else 0
        clicks = int(rows[0].get("clicks", 0)) if rows else 0
        ctr = float(rows[0].get("ctr", 0.0)) if rows else 0.0
        position = float(rows[0].get("position", 0.0)) if rows else 0.0

        # Branch by metric_suffix (per CREDENTIAL_BIBLE GSC KPI 12 신규 노드)
        m = (metric or "").lower()
        if "clicks" in m:
            value = clicks
        elif "position" in m:
            value = round(position, 2)
        elif "ctr" in m:
            value = round(ctr, 4)
        else:
            value = impressions  # default = impressions
        return {
            "value": value,
            "source": "gsc_live",
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "position": round(position, 2),
        }
    except Exception as e:
        print(f"[WARN] GSC fetch failed for {product_slug}: {e}", file=sys.stderr)
        _FETCH_ERRORS.append({"source": "gsc", "product": product_slug, "error": str(e)[:200]})
        return None


def fetch_posthog(product_slug: str, metric: str) -> dict | None:
    """Fetch PostHog daily metric via REST API.

    Per CREDENTIAL_BIBLE: POSTHOG_PERSONAL_API_KEY (phx_*) + POSTHOG_PROJECT_ID (322404).
    """
    key = (os.environ.get("POSTHOG_API_KEY")
           or os.environ.get("POSTHOG_PERSONAL_API_KEY"))
    project = (os.environ.get(f"POSTHOG_PROJECT_ID_{product_slug.upper()}")
               or os.environ.get("POSTHOG_PROJECT_ID_SHARED")
               or os.environ.get("POSTHOG_PROJECT_ID"))
    if not key or not project:
        return None

    import urllib.request
    import urllib.error

    # 2026-05-29: legacy insights/trend endpoint deprecated (403 permission_denied).
    # PostHog 현행 API = HogQL query endpoint. host default us (app→us redirect).
    host = os.environ.get("POSTHOG_HOST", "https://us.posthog.com")
    url = f"{host}/api/projects/{project}/query/"
    # 단일 project 322404 공유 → SBU 는 $host property 로 필터 (DAU per SBU)
    # 실제 PostHog $host 값 (2026-05-29 라이브 확인 — distinct host 쿼리 근거)
    sbu_host = {"kott": "kott.kr", "toolpick": "www.toolpick.dev", "ur-wrong": "ur-wrong.com",
                "heoyesol-brand": "heoyesol.kr", "reviewlab": "review.neogenesis.app",
                "sellkit": "sellkit.dev", "deploystack": "deploystack.dev",
                "aiforge": "aiforge.dev", "craftdesk": "craftdesk.dev",
                "finstack": "finstack.dev", "whylab": "whylab.dev"}.get(product_slug)
    where = "event = '$pageview' AND timestamp >= now() - INTERVAL 1 DAY"
    if sbu_host:
        where += f" AND properties.$host = '{sbu_host}'"
    hogql = f"SELECT count(DISTINCT person_id) AS dau FROM events WHERE {where}"
    body = {"query": {"kind": "HogQLQuery", "query": hogql}}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results") or data.get("result") or []
        if results and isinstance(results[0], (list, tuple)) and results[0]:
            return {"value": int(results[0][0]), "source": "posthog_live",
                    "metric": "daily_active_users", "host_filter": sbu_host or "all"}
        return {"value": 0, "source": "posthog_live", "host_filter": sbu_host or "all"}
    except urllib.error.HTTPError as e:
        print(f"[WARN] PostHog fetch failed for {product_slug}: {e.code} {e.reason}", file=sys.stderr)
        _FETCH_ERRORS.append({"source": "posthog", "product": product_slug, "error": f"{e.code} {e.reason}"})
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"[WARN] PostHog fetch failed for {product_slug}: {e}", file=sys.stderr)
        _FETCH_ERRORS.append({"source": "posthog", "product": product_slug, "error": str(e)[:200]})
        return None


def fetch_kpi_value(kpi: dict) -> dict | None:
    """Route by KPI.source."""
    source = kpi.get("source", "manual")
    product = kpi.get("product", "").split("/")[-1]
    metric = kpi.get("metric_name", "")

    if source == "ga4":
        return fetch_ga4(product, metric)
    if source == "gsc":
        return fetch_gsc(product, metric)
    if source == "posthog":
        return fetch_posthog(product, metric)
    if source == "supabase":
        # Could implement direct supabase query
        return None
    return None  # manual or unknown


def load_nodes() -> list[dict]:
    return [json.loads(l) for l in NODES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_nodes(nodes: list[dict]) -> None:
    with NODES_PATH.open("w", encoding="utf-8") as f:
        for n in nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", default="all", choices=["all", "ga4", "gsc", "posthog"])
    args = parser.parse_args()

    nodes = load_nodes()
    kpis = [n for n in nodes if n.get("rdf_type") == "biz:KPI"]
    print(f"Loaded {len(kpis)} KPI nodes")

    results = []
    updated_count = 0
    for kpi in kpis:
        source = kpi.get("source")
        if args.source != "all" and source != args.source:
            continue

        value = fetch_kpi_value(kpi)
        if value is None:
            results.append({
                "kpi": kpi["id"],
                "source": source,
                "status": "SKIP_NO_CREDS_OR_NOT_IMPLEMENTED",
            })
            continue

        # Update node
        if not args.dry_run:
            kpi["current_value"] = str(value.get("value"))
            kpi["current_value_observed_at"] = now_iso()
            kpi["current_value_source"] = value.get("source", source)
            kpi["provenance"] = "observed_from_live_source"
            # GSC 의 경우 raw breakdown 같이 박제 (impressions/clicks/position/ctr)
            if value.get("source") == "gsc_live":
                kpi["gsc_breakdown"] = {
                    "impressions": value.get("impressions"),
                    "clicks": value.get("clicks"),
                    "ctr": value.get("ctr"),
                    "position": value.get("position"),
                }
            updated_count += 1

        results.append({
            "kpi": kpi["id"],
            "source": source,
            "status": "FETCHED" if not args.dry_run else "DRY_RUN",
            "value": value,
        })

    if not args.dry_run and updated_count > 0:
        write_nodes(nodes)
        print(f"[OK] {updated_count} KPI updated in {NODES_PATH}")

    auth_failed = len(_FETCH_ERRORS) > 0
    print(json.dumps({
        "total_kpis": len(kpis),
        "filter_source": args.source,
        "results": results,
        "updated": updated_count,
        "auth_errors": _FETCH_ERRORS,
        "note": "v0.1 PoC — GA4/GSC/PostHog credentials 통합 진행 중. auth_errors > 0 이면 creds 는 있으나 API 가 거부 (만료/권한). owner action: GSC 재인증 / GA4 SA Viewer / PostHog scope.",
    }, indent=2, ensure_ascii=False))

    # Exit WARN(1) when creds were present but the API rejected them, so
    # daily_maintain surfaces it instead of reporting a silent OK while every
    # analytics feed is dead. exit 0 only when 0 auth errors.
    if auth_failed:
        print(f"[WARN] {len(_FETCH_ERRORS)} live-fetch auth/permission failure(s) — KPI current_value NOT refreshed for those.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
