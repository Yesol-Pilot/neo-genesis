#!/usr/bin/env python3
"""Gemini API monthly budget pacer for the Revenue OS.

Tracks Gemini month-to-date spend against a KRW 100,000 cap.

Source priority:
1. GCP billing export / Cloud Monitoring with existing credentials.
2. Local generativelanguage request/token logs estimated at Flash pricing.
3. Honest no_data output.

Secrets are never printed. Telegram alerts are sent only for warn/critical.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8 fallback only
    ZoneInfo = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "output" / "revenue_os" / "gemini_budget_status.json"
KST = ZoneInfo("Asia/Seoul") if ZoneInfo else timezone.utc
UTC = timezone.utc

MONTHLY_CAP_KRW = 100_000.0
DAILY_PACE_CAP_KRW = 3_300.0
WARN_RATIO = 0.80
CRITICAL_RATIO = 1.00

# Official Gemini 2.5 Flash paid-tier text/image/video price defaults as of
# 2026-06-12. Keep overridable because Gemini pricing changes.
DEFAULT_FLASH_INPUT_USD_PER_1M = 0.30
DEFAULT_FLASH_OUTPUT_USD_PER_1M = 2.50
DEFAULT_ESTIMATED_INPUT_TOKENS_PER_REQUEST = 1_000
DEFAULT_ESTIMATED_OUTPUT_TOKENS_PER_REQUEST = 250
DEFAULT_KRW_PER_USD = 1450.0

GEMINI_SERVICE = "generativelanguage.googleapis.com"
SERVICERUNTIME_REQUEST_COUNT = "serviceruntime.googleapis.com/api/request_count"


@dataclass
class UsageResult:
    status: str
    month_to_date_krw: float | None
    data_quality: str
    data_source: str
    is_estimate: bool | None
    request_count: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    evidence: dict[str, Any] | None = None
    errors: list[str] | None = None


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key:
                out[key] = value
    except OSError:
        return out
    return out


def load_env() -> dict[str, str]:
    """Load process env plus repo .env/.env.local, with .env.local winning."""
    merged: dict[str, str] = {}
    merged.update(_parse_env_file(REPO_ROOT / ".env"))
    merged.update(_parse_env_file(REPO_ROOT / ".env.local"))
    for key, value in os.environ.items():
        if value.strip():
            merged[key] = value
    return merged


def _float_env(env: dict[str, str], key: str, default: float) -> float:
    try:
        return float(env.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_env(env: dict[str, str], key: str, default: int) -> int:
    try:
        return int(float(env.get(key, default)))
    except (TypeError, ValueError):
        return default


def month_window(now: datetime | None = None) -> tuple[datetime, datetime, int]:
    local_now = now or datetime.now(KST)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=KST)
    month_start_local = datetime.combine(local_now.date().replace(day=1), time(), tzinfo=KST)
    elapsed_days = max(1, local_now.day)
    return month_start_local.astimezone(UTC), local_now.astimezone(UTC), elapsed_days


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def redact_error(exc: BaseException) -> str:
    return type(exc).__name__


def project_id_from_env_or_gcloud(env: dict[str, str], errors: list[str]) -> str | None:
    for key in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "CLOUDSDK_CORE_PROJECT"):
        if env.get(key, "").strip():
            return env[key].strip()

    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        return None
    try:
        proc = subprocess.run(
            [gcloud, "config", "get-value", "project", "--quiet"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        project = proc.stdout.strip()
        if proc.returncode == 0 and project and project != "(unset)":
            return project
        errors.append("gcloud_project_unset")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"gcloud_project_failed:{redact_error(exc)}")
    return None


def token_from_service_account(env: dict[str, str], errors: list[str]) -> str | None:
    cred_path = (
        env.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        or env.get("GCP_SERVICE_ACCOUNT_FILE", "").strip()
        or env.get("GA4_SERVICE_ACCOUNT_PATH", "").strip()
    )
    if not cred_path:
        return None
    path = Path(cred_path)
    if not path.exists():
        errors.append("service_account_path_missing")
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            str(path),
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform",
                "https://www.googleapis.com/auth/monitoring.read",
            ],
        )
        creds.refresh(Request())
        return str(creds.token)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"service_account_auth_failed:{redact_error(exc)}")
        return None


def token_from_gcloud(errors: list[str]) -> str | None:
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        return None
    try:
        proc = subprocess.run(
            [gcloud, "auth", "print-access-token", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        token = proc.stdout.strip()
        if proc.returncode == 0 and token:
            return token
        errors.append("gcloud_access_token_unavailable")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"gcloud_auth_failed:{redact_error(exc)}")
    return None


def get_access_token(env: dict[str, str], errors: list[str]) -> tuple[str | None, str]:
    token = token_from_service_account(env, errors)
    if token:
        return token, "service_account"
    token = token_from_gcloud(errors)
    if token:
        return token, "gcloud_cli"
    return None, "none"


def api_get_json(url: str, token: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post_json(url: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_billing_info(project_id: str, token: str, errors: list[str]) -> dict[str, Any] | None:
    url = f"https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo"
    try:
        data = api_get_json(url, token)
        return {
            "billing_enabled": data.get("billingEnabled"),
            "billing_account_present": bool(data.get("billingAccountName")),
        }
    except urllib.error.HTTPError as exc:
        errors.append(f"cloud_billing_info_http_{exc.code}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cloud_billing_info_failed:{redact_error(exc)}")
    return None


def billing_export_table(env: dict[str, str]) -> str | None:
    for key in (
        "GCP_BILLING_EXPORT_TABLE",
        "CLOUD_BILLING_EXPORT_TABLE",
        "GOOGLE_CLOUD_BILLING_EXPORT_TABLE",
    ):
        value = env.get(key, "").strip().strip("`")
        if value:
            return value
    return None


def table_project_id(table: str, fallback: str) -> str:
    parts = table.split(".")
    return parts[0] if len(parts) == 3 and parts[0] else fallback


def fetch_billing_export_cost(
    *,
    env: dict[str, str],
    project_id: str,
    token: str,
    errors: list[str],
) -> UsageResult | None:
    table = billing_export_table(env)
    if not table:
        return None

    query_project = env.get("GCP_BILLING_QUERY_PROJECT", "").strip() or table_project_id(
        table, project_id
    )
    fx = _float_env(env, "KRW_PER_USD", DEFAULT_KRW_PER_USD)
    query = f"""
SELECT
  currency,
  SUM(cost) AS cost
FROM `{table}`
WHERE DATE(usage_start_time, "Asia/Seoul") >= DATE_TRUNC(CURRENT_DATE("Asia/Seoul"), MONTH)
  AND (
    LOWER(service.description) LIKE "%gemini%"
    OR LOWER(service.description) LIKE "%generative language%"
    OR (
      LOWER(service.description) LIKE "%vertex ai%"
      AND LOWER(sku.description) LIKE "%gemini%"
    )
  )
GROUP BY currency
""".strip()

    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{query_project}/queries"
    try:
        body: dict[str, Any] = {
            "query": query,
            "useLegacySql": False,
            "timeoutMs": 30000,
        }
        location = env.get("GCP_BILLING_EXPORT_LOCATION", "").strip()
        if location:
            body["location"] = location
        data = api_post_json(url, token, body)
        schema = data.get("schema", {}).get("fields", [])
        names = [field.get("name") for field in schema]
        rows = data.get("rows", [])
        month_to_date_krw = 0.0
        cost_usd = 0.0
        currencies: list[dict[str, Any]] = []
        for row in rows:
            cells = row.get("f", [])
            values = {
                names[i]: cells[i].get("v")
                for i in range(min(len(names), len(cells)))
                if names[i]
            }
            currency = str(values.get("currency") or "").upper()
            try:
                cost = float(values.get("cost") or 0)
            except (TypeError, ValueError):
                cost = 0.0
            if currency == "KRW":
                krw = cost
                usd = cost / fx if fx else 0.0
            elif currency == "USD":
                usd = cost
                krw = cost * fx
            else:
                usd = cost
                krw = cost * fx
            month_to_date_krw += krw
            cost_usd += usd
            currencies.append({"currency": currency or "unknown", "raw_cost": round(cost, 6)})

        return UsageResult(
            status="ok",
            month_to_date_krw=month_to_date_krw,
            data_quality="actual_from_gcp_billing_export",
            data_source="gcp_cloud_billing_export_bigquery",
            is_estimate=False,
            cost_usd=cost_usd,
            evidence={
                "query_project": query_project,
                "billing_export_table_configured": True,
                "currency_rows": currencies,
                "krw_per_usd": fx,
                "filter": "Gemini / Generative Language / Vertex AI Gemini service rows",
            },
            errors=errors,
        )
    except urllib.error.HTTPError as exc:
        errors.append(f"bigquery_billing_export_http_{exc.code}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"bigquery_billing_export_failed:{redact_error(exc)}")
    return None


def sum_points(series: list[dict[str, Any]]) -> int:
    total = 0.0
    for item in series:
        for point in item.get("points", []):
            value = point.get("value", {})
            raw = (
                value.get("int64Value")
                or value.get("doubleValue")
                or value.get("stringValue")
                or 0
            )
            try:
                total += float(raw)
            except (TypeError, ValueError):
                continue
    return int(round(total))


def fetch_monitoring_request_count(
    *,
    project_id: str,
    token: str,
    start: datetime,
    end: datetime,
    errors: list[str],
) -> tuple[int | None, dict[str, Any] | None]:
    filter_expr = (
        f'metric.type = "{SERVICERUNTIME_REQUEST_COUNT}" '
        'AND resource.type = "consumed_api" '
        f'AND resource.labels.service = "{GEMINI_SERVICE}"'
    )
    params = {
        "filter": filter_expr,
        "interval.startTime": iso_z(start),
        "interval.endTime": iso_z(end),
        "aggregation.alignmentPeriod": "86400s",
        "aggregation.perSeriesAligner": "ALIGN_DELTA",
        "aggregation.crossSeriesReducer": "REDUCE_SUM",
    }
    url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries"
    try:
        data = api_get_json(url, token, params)
        series = data.get("timeSeries", [])
        return sum_points(series), {
            "metric_type": SERVICERUNTIME_REQUEST_COUNT,
            "service": GEMINI_SERVICE,
            "series_count": len(series),
        }
    except urllib.error.HTTPError as exc:
        errors.append(f"monitoring_request_count_http_{exc.code}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"monitoring_request_count_failed:{redact_error(exc)}")
    return None, None


def pricing(env: dict[str, str]) -> dict[str, float | int | str]:
    return {
        "model_family": env.get("GEMINI_BUDGET_PRICE_MODEL", "gemini-2.5-flash"),
        "input_usd_per_1m": _float_env(
            env, "GEMINI_FLASH_INPUT_USD_PER_1M", DEFAULT_FLASH_INPUT_USD_PER_1M
        ),
        "output_usd_per_1m": _float_env(
            env, "GEMINI_FLASH_OUTPUT_USD_PER_1M", DEFAULT_FLASH_OUTPUT_USD_PER_1M
        ),
        "assumed_input_tokens_per_request": _int_env(
            env,
            "GEMINI_ESTIMATED_INPUT_TOKENS_PER_REQUEST",
            DEFAULT_ESTIMATED_INPUT_TOKENS_PER_REQUEST,
        ),
        "assumed_output_tokens_per_request": _int_env(
            env,
            "GEMINI_ESTIMATED_OUTPUT_TOKENS_PER_REQUEST",
            DEFAULT_ESTIMATED_OUTPUT_TOKENS_PER_REQUEST,
        ),
        "krw_per_usd": _float_env(env, "KRW_PER_USD", DEFAULT_KRW_PER_USD),
    }


def estimate_from_tokens(input_tokens: int, output_tokens: int, env: dict[str, str]) -> tuple[float, float]:
    price = pricing(env)
    cost_usd = (
        (input_tokens / 1_000_000.0) * float(price["input_usd_per_1m"])
        + (output_tokens / 1_000_000.0) * float(price["output_usd_per_1m"])
    )
    return cost_usd, cost_usd * float(price["krw_per_usd"])


def estimate_from_requests(requests: int, env: dict[str, str]) -> tuple[float, float, int, int]:
    price = pricing(env)
    input_tokens = requests * int(price["assumed_input_tokens_per_request"])
    output_tokens = requests * int(price["assumed_output_tokens_per_request"])
    cost_usd, cost_krw = estimate_from_tokens(input_tokens, output_tokens, env)
    return cost_usd, cost_krw, input_tokens, output_tokens


def collect_from_gcp(env: dict[str, str], start: datetime, end: datetime) -> UsageResult | None:
    errors: list[str] = []
    project_id = project_id_from_env_or_gcloud(env, errors)
    if not project_id:
        return UsageResult(
            status="unavailable",
            month_to_date_krw=None,
            data_quality="gcp_unavailable",
            data_source="gcp",
            is_estimate=None,
            errors=errors + ["project_id_missing"],
        )

    token, auth_source = get_access_token(env, errors)
    if not token:
        return UsageResult(
            status="unavailable",
            month_to_date_krw=None,
            data_quality="gcp_unavailable",
            data_source="gcp",
            is_estimate=None,
            evidence={"project_id": project_id, "auth_source": auth_source},
            errors=errors + ["gcp_auth_unavailable"],
        )

    evidence: dict[str, Any] = {
        "project_id": project_id,
        "auth_source": auth_source,
        "period_start_utc": iso_z(start),
        "period_end_utc": iso_z(end),
    }
    billing_info = fetch_billing_info(project_id, token, errors)
    if billing_info:
        evidence["cloud_billing_api"] = billing_info

    billing_export = fetch_billing_export_cost(
        env=env,
        project_id=project_id,
        token=token,
        errors=errors,
    )
    if billing_export:
        billing_export.evidence = {
            **evidence,
            **(billing_export.evidence or {}),
        }
        billing_export.errors = errors
        return billing_export

    requests, monitoring_evidence = fetch_monitoring_request_count(
        project_id=project_id,
        token=token,
        start=start,
        end=end,
        errors=errors,
    )
    if requests is None:
        return UsageResult(
            status="unavailable",
            month_to_date_krw=None,
            data_quality="gcp_unavailable",
            data_source="gcp_cloud_billing_monitoring",
            is_estimate=None,
            evidence=evidence,
            errors=errors,
        )

    cost_usd, cost_krw, input_tokens, output_tokens = estimate_from_requests(requests, env)
    evidence["monitoring_api"] = monitoring_evidence
    evidence["pricing"] = pricing(env)
    evidence["actual_billing_cost_available"] = False
    evidence["billing_cost_note"] = (
        "Cloud Billing Account API confirms billing state but does not expose "
        "month-to-date service cost here; Monitoring request count is estimated "
        "with Flash pricing."
    )
    return UsageResult(
        status="ok",
        month_to_date_krw=cost_krw,
        data_quality="estimated_from_gcp_monitoring_requests",
        data_source="gcp_cloud_monitoring_serviceruntime",
        is_estimate=True,
        request_count=requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        evidence=evidence,
        errors=errors,
    )


def parse_local_usage_log(path: Path) -> tuple[int, int, int] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    total_requests = 0
    total_input = 0
    total_output = 0

    if isinstance(data, dict) and isinstance(data.get("sbu_usage"), dict):
        for value in data["sbu_usage"].values():
            if not isinstance(value, dict):
                continue
            total_requests += int(value.get("requests") or 0)
            total_input += int(value.get("input_tokens") or 0)
            total_output += int(value.get("output_tokens") or 0)

    if isinstance(data, dict) and (
        "requests" in data or "input_tokens" in data or "output_tokens" in data
    ):
        total_requests += int(data.get("requests") or 0)
        total_input += int(data.get("input_tokens") or 0)
        total_output += int(data.get("output_tokens") or 0)

    if total_requests or total_input or total_output:
        return total_requests, total_input, total_output
    return None


def parse_local_jsonl(path: Path) -> tuple[int, int, int] | None:
    if not path.exists():
        return None
    requests = 0
    input_tokens = 0
    output_tokens = 0
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            service = str(row.get("service") or row.get("provider") or "").lower()
            model = str(row.get("model") or "").lower()
            if service and "gemini" not in service and "generativelanguage" not in service:
                continue
            if model and "gemini" not in model:
                continue
            requests += int(row.get("requests") or row.get("request_count") or 1)
            input_tokens += int(row.get("input_tokens") or row.get("prompt_tokens") or 0)
            output_tokens += int(row.get("output_tokens") or row.get("completion_tokens") or 0)
    except OSError:
        return None
    if requests or input_tokens or output_tokens:
        return requests, input_tokens, output_tokens
    return None


def collect_from_local_logs(env: dict[str, str]) -> UsageResult | None:
    candidates = [
        REPO_ROOT / "data" / "gemini_usage_log.json",
        REPO_ROOT / "output" / "revenue_os" / "gemini_usage_log.json",
    ]
    jsonl_candidates = [
        REPO_ROOT / "logs" / "gemini_usage.jsonl",
        REPO_ROOT / "logs" / "generativelanguage_usage.jsonl",
    ]

    requests = 0
    input_tokens = 0
    output_tokens = 0
    sources: list[str] = []

    for path in candidates:
        parsed = parse_local_usage_log(path)
        if not parsed:
            continue
        r, i, o = parsed
        requests += r
        input_tokens += i
        output_tokens += o
        sources.append(str(path.relative_to(REPO_ROOT)))

    for path in jsonl_candidates:
        parsed = parse_local_jsonl(path)
        if not parsed:
            continue
        r, i, o = parsed
        requests += r
        input_tokens += i
        output_tokens += o
        sources.append(str(path.relative_to(REPO_ROOT)))

    if not sources:
        return None

    if input_tokens or output_tokens:
        cost_usd, cost_krw = estimate_from_tokens(input_tokens, output_tokens, env)
        quality = "estimated_from_local_usage_tokens"
    else:
        cost_usd, cost_krw, input_tokens, output_tokens = estimate_from_requests(requests, env)
        quality = "estimated_from_local_request_count"

    return UsageResult(
        status="ok",
        month_to_date_krw=cost_krw,
        data_quality=quality,
        data_source="local_usage_logs",
        is_estimate=True,
        request_count=requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        evidence={"sources": sources, "pricing": pricing(env)},
        errors=[],
    )


def choose_usage(env: dict[str, str], start: datetime, end: datetime) -> UsageResult:
    attempts: list[dict[str, Any]] = []

    gcp = collect_from_gcp(env, start, end)
    if gcp and gcp.status == "ok":
        if gcp.evidence is None:
            gcp.evidence = {}
        gcp.evidence["source_attempts"] = attempts
        return gcp
    if gcp:
        attempts.append(
            {
                "source": gcp.data_source,
                "status": gcp.status,
                "data_quality": gcp.data_quality,
                "errors": gcp.errors or [],
            }
        )

    local = collect_from_local_logs(env)
    if local:
        if local.evidence is None:
            local.evidence = {}
        local.evidence["source_attempts"] = attempts
        return local

    return UsageResult(
        status="no_data",
        month_to_date_krw=None,
        data_quality="no_data",
        data_source="none",
        is_estimate=None,
        evidence={"source_attempts": attempts, "pricing": pricing(env)},
        errors=["no_gcp_cost_or_request_data", "no_local_generativelanguage_usage_log"],
    )


def classify_alert(month_to_date_krw: float | None, daily_pace_krw: float | None) -> str:
    if month_to_date_krw is None or daily_pace_krw is None:
        return "no_data"
    cap_ratio = month_to_date_krw / MONTHLY_CAP_KRW
    pace_ratio = daily_pace_krw / DAILY_PACE_CAP_KRW
    ratio = max(cap_ratio, pace_ratio)
    if ratio >= CRITICAL_RATIO:
        return "critical"
    if ratio >= WARN_RATIO:
        return "warn"
    return "ok"


def build_status(env: dict[str, str]) -> dict[str, Any]:
    start, end, elapsed_days = month_window()
    usage = choose_usage(env, start, end)

    if usage.month_to_date_krw is None:
        daily_pace = None
        pct_of_cap = None
        pace_pct = None
    else:
        daily_pace = usage.month_to_date_krw / elapsed_days
        pct_of_cap = usage.month_to_date_krw / MONTHLY_CAP_KRW * 100.0
        pace_pct = daily_pace / DAILY_PACE_CAP_KRW * 100.0

    alert_level = classify_alert(usage.month_to_date_krw, daily_pace)
    now = datetime.now(KST)
    return {
        "status": usage.status,
        "captured_at": now.isoformat(),
        "period": {
            "timezone": "Asia/Seoul",
            "month_start_utc": iso_z(start),
            "captured_until_utc": iso_z(end),
            "elapsed_days_in_month": elapsed_days,
        },
        "monthly_cap_krw": int(MONTHLY_CAP_KRW),
        "daily_pace_cap_krw": int(DAILY_PACE_CAP_KRW),
        "month_to_date_krw": round(usage.month_to_date_krw, 2)
        if usage.month_to_date_krw is not None
        else None,
        "daily_pace_krw": round(daily_pace, 2) if daily_pace is not None else None,
        "pct_of_cap": round(pct_of_cap, 2) if pct_of_cap is not None else None,
        "pace_pct_of_daily_allowance": round(pace_pct, 2) if pace_pct is not None else None,
        "data_quality": usage.data_quality,
        "data_source": usage.data_source,
        "measurement_type": "estimate"
        if usage.is_estimate is True
        else ("actual" if usage.is_estimate is False else "none"),
        "is_estimate": usage.is_estimate,
        "alert_level": alert_level,
        "request_count_month_to_date": usage.request_count,
        "input_tokens_month_to_date": usage.input_tokens,
        "output_tokens_month_to_date": usage.output_tokens,
        "cost_usd_month_to_date": round(usage.cost_usd, 6)
        if usage.cost_usd is not None
        else None,
        "evidence": usage.evidence or {},
        "errors": usage.errors or [],
    }


def send_telegram(env: dict[str, str], status: dict[str, Any]) -> dict[str, Any]:
    if status.get("alert_level") not in {"warn", "critical"}:
        return {"attempted": False, "reason": "alert_level_below_warn"}

    token = env.get("CODEX_ALERT_BOT_TOKEN", "").strip()
    chat_id = env.get("OWNER_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"attempted": False, "reason": "missing_token_or_chat_id"}

    text = (
        "[Neo Genesis] Gemini budget "
        f"{status['alert_level'].upper()}: "
        f"MTD ₩{status.get('month_to_date_krw')}, "
        f"pace ₩{status.get('daily_pace_krw')}/day, "
        f"{status.get('pct_of_cap')}% of cap, "
        f"quality={status.get('data_quality')}"
    )
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"attempted": True, "sent": resp.status == 200, "http_status": resp.status}
    except Exception as exc:  # noqa: BLE001
        return {"attempted": True, "sent": False, "error": redact_error(exc)}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gemini API monthly budget pacer")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="status JSON output path")
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="do not send Telegram alert even when warn/critical",
    )
    args = parser.parse_args(argv)

    env = load_env()
    status = build_status(env)
    if args.no_telegram:
        status["telegram"] = {"attempted": False, "reason": "disabled_by_flag"}
    else:
        status["telegram"] = send_telegram(env, status)

    output_path = Path(args.output)
    write_json(output_path, status)

    print(
        "gemini-budget-pacer: "
        f"status={status['status']} "
        f"quality={status['data_quality']} "
        f"alert={status['alert_level']} "
        f"output={output_path}"
    )
    return 0 if status["status"] in {"ok", "no_data"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
