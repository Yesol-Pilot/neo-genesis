"""Local HTTP bridge for the AiNo TikTok Chrome Extension.

The bridge exposes the latest generated video package over 127.0.0.1 so the
extension can fetch the MP4 as a Blob and place it into TikTok's upload input.
It prints no secrets and does not contact TikTok.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.core.tiktok_aino import pipeline


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8757
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def _manifest_publish_status(manifest: dict[str, object]) -> str:
    return str(pipeline.validate_manifest_for_upload(dict(manifest))["status"])


class BridgeState:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.token = secrets.token_urlsafe(24)
        self.metrics_dir = output_dir / "studio_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def latest_manifest(self) -> Path | None:
        manifests = sorted(
            self.output_dir.glob("leftaino_*/manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return manifests[0] if manifests else None

    def manifest_for_run(self, run_id: str | None) -> Path | None:
        if not run_id:
            return self.latest_manifest()
        if not RUN_ID_PATTERN.match(run_id):
            return None
        path = self.output_dir / run_id / "manifest.json"
        return path if path.exists() else None

    def build_upload_job(self, run_id: str | None = None) -> dict[str, object]:
        manifest_path = self.manifest_for_run(run_id)
        if not manifest_path:
            return {"ok": False, "error": "no_manifest_found", "output_dir": str(self.output_dir), "run_id": run_id}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = manifest.get("artifacts", {})
        script = manifest.get("script", {})
        format_plan = manifest.get("format_plan", {})
        mp4_path = Path(str(artifacts.get("mp4", "")))
        if not mp4_path.exists():
            return {"ok": False, "error": "mp4_missing", "manifest_path": str(manifest_path), "mp4": str(mp4_path)}
        validation = pipeline.validate_manifest_for_upload(manifest)
        if not validation["upload_ready"]:
            return {
                "ok": False,
                "error": "manifest_not_upload_ready",
                "manifest_path": str(manifest_path),
                "status": validation["status"],
                "raw_manifest_status": manifest.get("status"),
                "validation": validation,
            }
        caption = str(script.get("caption", ""))
        post_title = str(script.get("post_title", ""))
        hashtags = script.get("hashtags", [])
        return {
            "ok": True,
            "manifest_path": str(manifest_path),
            "run_id": manifest.get("run_id"),
            "status": validation["status"],
            "raw_manifest_status": manifest.get("status"),
            "validation": validation,
            "format_plan": format_plan,
            "planned_publish_at_local": manifest.get("planned_publish_at_local"),
            "schedule_status": manifest.get("schedule_status"),
            "filename": mp4_path.name,
            "mp4_path": str(mp4_path),
            "video_url": f"/video?token={self.token}&run_id={manifest.get('run_id')}",
            "caption": caption,
            "post_title": post_title,
            "hashtags": hashtags,
            "aigc_required": True,
            "final_post_click_allowed": False,
            "operator_checks": [
                "Confirm TikTok AIGC label is enabled for realistic AI media.",
                "Confirm no CAPTCHA or account-security warning is present.",
                "Confirm caption, hashtags, cover, and visibility before posting.",
            ],
        }


def _json_response(handler: BaseHTTPRequestHandler, payload: dict[str, object], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def _metric_nodes_count(payload: dict[str, Any]) -> int:
    for key in ("metricNodes", "metric_node_texts", "metricNodeDetails"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def _text_sample(payload: dict[str, Any]) -> str:
    for key in ("textSample", "text_sample", "combined"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    snapshots = payload.get("snapshots")
    if isinstance(snapshots, list):
        return "\n".join(str(row.get("text", "")) for row in snapshots if isinstance(row, dict))
    return ""


def enrich_metrics_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize extension metrics before appending them to JSONL."""

    enriched = dict(payload)
    enriched.setdefault("schema_version", "studio_metrics_capture_v2")
    text = _text_sample(enriched)
    metric_count = _metric_nodes_count(enriched)

    if "metricNodes" not in enriched and isinstance(enriched.get("metricNodeDetails"), list):
        enriched["metricNodes"] = [
            str(row.get("text", ""))
            for row in enriched["metricNodeDetails"]
            if isinstance(row, dict) and str(row.get("text", "")).strip()
        ]
        metric_count = len(enriched["metricNodes"])

    if "snapshots" not in enriched and text:
        enriched["snapshots"] = [{"kind": "bridge_text_sample", "text": text[:12000]}]

    try:
        from src.core.tiktok_aino import monitoring

        normalized = monitoring.normalize_metrics(enriched)
    except Exception as exc:
        normalized = {}
        enriched.setdefault("warnings", []).append(f"normalization_failed:{type(exc).__name__}")

    if normalized:
        enriched["normalizedMetrics"] = normalized
        enriched["normalized_metrics"] = normalized

    warnings = list(enriched.get("warnings", [])) if isinstance(enriched.get("warnings"), list) else []
    if not str(enriched.get("run_id") or enriched.get("runId") or enriched.get("latestRunId") or "").strip() and not isinstance(enriched.get("latestJob"), dict):
        warnings.append("missing_run_id")
    if len(text) < 500:
        warnings.append("sparse_text_sample")
    if metric_count < 3:
        warnings.append("sparse_metric_nodes")
    if not normalized:
        warnings.append("no_normalized_metrics")
    if enriched.get("security_blocker"):
        warnings.append("security_blocker_present")
    warnings = list(dict.fromkeys(str(item) for item in warnings if str(item).strip()))
    enriched["warnings"] = warnings
    enriched["capture_quality"] = {
        **(enriched.get("capture_quality") if isinstance(enriched.get("capture_quality"), dict) else {}),
        "text_length": len(text),
        "metric_nodes_count": metric_count,
        "normalized_metric_keys": sorted(normalized.keys()),
        "has_run_id": "missing_run_id" not in warnings,
        "ok": len(text) >= 500 and metric_count >= 3 and bool(normalized) and not enriched.get("security_blocker"),
        "warnings": warnings,
    }
    return enriched


def make_handler(state: BridgeState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            _json_response(self, {"ok": True})

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                _json_response(self, {"ok": True, "service": "aino_tiktok_bridge"})
                return
            if parsed.path == "/latest":
                job = state.build_upload_job()
                if job.get("ok"):
                    job["video_url"] = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}{job['video_url']}"
                _json_response(self, job, HTTPStatus.OK if job.get("ok") else HTTPStatus.NOT_FOUND)
                return
            if parsed.path == "/job":
                params = parse_qs(parsed.query)
                job = state.build_upload_job(params.get("run_id", [""])[0] or None)
                if job.get("ok"):
                    job["video_url"] = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}{job['video_url']}"
                _json_response(self, job, HTTPStatus.OK if job.get("ok") else HTTPStatus.NOT_FOUND)
                return
            if parsed.path == "/video":
                params = parse_qs(parsed.query)
                if params.get("token", [""])[0] != state.token:
                    _json_response(self, {"ok": False, "error": "bad_token"}, HTTPStatus.FORBIDDEN)
                    return
                job = state.build_upload_job(params.get("run_id", [""])[0] or None)
                if not job.get("ok"):
                    _json_response(self, job, HTTPStatus.NOT_FOUND)
                    return
                mp4_path = Path(str(job["mp4_path"]))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(mp4_path.name)[0] or "video/mp4")
                self.send_header("Content-Length", str(mp4_path.stat().st_size))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with mp4_path.open("rb") as file:
                    while chunk := file.read(1024 * 1024):
                        self.wfile.write(chunk)
                return
            _json_response(self, {"ok": False, "error": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/metrics":
                _json_response(self, {"ok": False, "error": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            raw_len = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(min(raw_len, 250_000))
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                _json_response(self, {"ok": False, "error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
                return
            payload["captured_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            payload = enrich_metrics_payload(payload)
            path = state.metrics_dir / f"studio_metrics_{dt.datetime.now():%Y%m%d}.jsonl"
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            _json_response(self, {"ok": True, "path": str(path)})

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local AiNo TikTok Extension bridge.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    state = BridgeState(args.output_dir)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"AiNo TikTok bridge listening on http://{args.host}:{args.port}")
    print(f"Output dir: {args.output_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
