"""Guarded Veo generation worker for AiNo TikTok video intent tests."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

from src.core.tiktok_aino import privacy as privacy_policy


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[2]
DEFAULT_OUTPUT_DIR = REPO_DIR / "output" / "tiktok_aino_veo_tests"
DEFAULT_STATE_DIR = REPO_DIR / "output" / "tiktok_aino_veo_state"
PRICING_PATH = PACKAGE_DIR / "config" / "veo_pricing_20260514.json"
DEFAULT_NEGATIVE_PROMPT = (
    "readable text, captions, subtitles, watermark, fake screenshot, distorted hands, "
    "extra fingers, low quality, flicker, frame warping"
)
DEFAULT_MOTION_INSTRUCTION = (
    "Create a short vertical documentary micro-video that preserves the supplied first frame composition. "
    "Use a slow push-in, slight parallax, subtle practical light drift, paper texture movement, and a restrained "
    "foreground object shift. Keep the scene realistic and editorial, not stylized or stock-like."
)


def _load_env_files() -> None:
    for path in [REPO_DIR / ".env.local", REPO_DIR / ".env"]:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


_load_env_files()


@dataclass(frozen=True)
class VeoSceneRequest:
    project_id: str
    location: str
    model_id: str
    scene_id: int
    prompt: str
    image_path: str | None
    storage_uri: str
    aspect_ratio: str
    resolution: str
    duration_seconds: int
    sample_count: int
    generate_audio: bool
    person_generation: str
    negative_prompt: str
    enhance_prompt: bool
    seed: int | None
    estimated_cost_usd: float
    request_body: dict[str, Any]


@dataclass(frozen=True)
class VeoRunConfig:
    manifest_path: Path
    scene_ids: list[int]
    output_dir: Path
    state_dir: Path
    project_id: str
    location: str
    model_id: str
    storage_uri: str | None
    aspect_ratio: str
    resolution: str
    duration_seconds: int
    sample_count: int
    generate_audio: bool
    person_generation: str
    enhance_prompt: bool
    seed: int | None
    run_cap_usd: float
    monthly_cap_usd: float
    allow_paid: bool
    enable_api: bool
    poll_timeout_sec: int
    poll_interval_sec: int
    dry_run: bool
    privacy_mode: str = privacy_policy.LOCAL_ONLY


@dataclass(frozen=True)
class VideoQualityReport:
    video_path: str
    passed: bool
    blockers: list[str]
    warnings: list[str]
    metrics: dict[str, Any]
    frame_paths: list[str] = field(default_factory=list)
    contact_sheet: str | None = None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_DIR.resolve()))
    except ValueError:
        return str(path)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _gcloud_json(args: list[str], *, timeout: int = 60) -> Any:
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        raise RuntimeError("gcloud executable not found")
    proc = subprocess.run(
        [gcloud, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"gcloud failed: {' '.join(args)}")
    text = proc.stdout.strip()
    return json.loads(text) if text else None


def _gcloud_text(args: list[str], *, timeout: int = 60) -> str:
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        raise RuntimeError("gcloud executable not found")
    proc = subprocess.run(
        [gcloud, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"gcloud failed: {' '.join(args)}")
    return proc.stdout.strip()


def default_project_id() -> str:
    env_project = os.environ.get("AINO_VEO_PROJECT_ID") or os.environ.get("GCP_PROJECT_ID")
    if env_project:
        return env_project.strip()
    try:
        config = _gcloud_json(["config", "list", "--format=json"], timeout=30)
        return str(config.get("core", {}).get("project") or "").strip()
    except Exception:
        return ""


def enabled_services() -> set[str]:
    try:
        lines = _gcloud_text(["services", "list", "--enabled", "--format=value(config.name)"], timeout=90)
    except Exception:
        return set()
    return {line.strip() for line in lines.splitlines() if line.strip()}


def vertex_api_enabled() -> bool:
    return "aiplatform.googleapis.com" in enabled_services()


def enable_vertex_api() -> None:
    _gcloud_text(["services", "enable", "aiplatform.googleapis.com"], timeout=180)


def discover_storage_uri(project_id: str) -> str | None:
    configured = os.environ.get("AINO_VEO_STORAGE_URI")
    if configured:
        return configured.rstrip("/") + "/"
    try:
        buckets = _gcloud_json(["storage", "buckets", "list", "--format=json"], timeout=90) or []
    except Exception:
        return None
    candidates: list[str] = []
    for bucket in buckets:
        name = str(bucket.get("name", ""))
        if not name:
            continue
        if project_id and name == f"{project_id}-source-bucket":
            candidates.insert(0, name)
        elif project_id and project_id in name and "source" in name and not name.startswith("run-sources-"):
            candidates.append(name)
        else:
            candidates.append(name)
    if not candidates:
        return None
    return f"gs://{candidates[0]}/veo/tiktok_aino/"


def load_pricing(path: Path = PRICING_PATH) -> dict[str, Any]:
    return _read_json(path)


def price_per_second(pricing: dict[str, Any], model_id: str, resolution: str, generate_audio: bool) -> float:
    family = "video_audio" if generate_audio else "video"
    try:
        return float(pricing["prices_per_second"][model_id][family][resolution])
    except KeyError as exc:
        raise ValueError(f"unsupported Veo price tuple: {model_id}/{resolution}/{family}") from exc


def estimate_cost_usd(
    *,
    pricing: dict[str, Any],
    model_id: str,
    resolution: str,
    generate_audio: bool,
    duration_seconds: int,
    sample_count: int,
    scene_count: int,
) -> float:
    unit = price_per_second(pricing, model_id, resolution, generate_audio)
    return round(unit * duration_seconds * sample_count * scene_count, 4)


def current_month_key(now: dt.datetime | None = None) -> str:
    current = now or dt.datetime.now(dt.timezone.utc)
    return current.strftime("%Y-%m")


def ledger_path(state_dir: Path) -> Path:
    return state_dir / "veo_cost_ledger.jsonl"


def read_monthly_ledger_total(path: Path, month_key: str) -> float:
    if not path.exists():
        return 0.0
    total = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("month")) == month_key:
            amount = float(row.get("estimated_cost_usd", 0) or 0)
            if row.get("status") == "ledger_adjustment":
                total += amount
            elif row.get("billable") is not False:
                total += amount
    return round(total, 4)


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _normal_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_visual_assets(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    direct = manifest.get("visual_assets")
    if isinstance(direct, list):
        return [row for row in direct if isinstance(row, dict)]
    asset_manifest = manifest.get("artifacts", {}).get("asset_manifest") if isinstance(manifest.get("artifacts"), dict) else None
    if asset_manifest:
        path = Path(asset_manifest)
        if not path.is_absolute():
            path = REPO_DIR / path
        if path.exists():
            data = _read_json(path)
            if isinstance(data, list):
                return [row for row in data if isinstance(row, dict)]
    sibling = manifest_path.parent / "visual_assets.json"
    if sibling.exists():
        data = _read_json(sibling)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


def _asset_for_scene(assets: list[dict[str, Any]], scene_id: int) -> dict[str, Any]:
    for asset in assets:
        if int(asset.get("scene_id", -1)) == scene_id:
            return asset
    raise ValueError(f"scene_id not found in visual assets: {scene_id}")


def _manifest_scene(manifest: dict[str, Any], scene_id: int) -> dict[str, Any]:
    script = manifest.get("script") if isinstance(manifest.get("script"), dict) else {}
    scenes = script.get("scenes") if isinstance(script.get("scenes"), list) else []
    for scene in scenes:
        if isinstance(scene, dict) and int(scene.get("scene_id", -1)) == scene_id:
            return scene
    return {}


def _absolute_asset_path(asset_path: str | None, manifest_path: Path) -> Path | None:
    if not asset_path:
        return None
    path = Path(asset_path)
    if path.is_absolute():
        return path
    for base in [REPO_DIR, manifest_path.parent]:
        candidate = base / path
        if candidate.exists():
            return candidate
    return REPO_DIR / path


def build_veo_prompt(manifest: dict[str, Any], asset: dict[str, Any], scene: dict[str, Any]) -> str:
    brief = asset.get("visual_brief") if isinstance(asset.get("visual_brief"), dict) else {}
    anchors = brief.get("visual_anchor") if isinstance(brief.get("visual_anchor"), list) else []
    safety = brief.get("safety_constraints") if isinstance(brief.get("safety_constraints"), list) else []
    parts = [
        DEFAULT_MOTION_INSTRUCTION,
        f"Scene role: {_normal_text(brief.get('role') or scene.get('title'))}.",
        f"Location: {_normal_text(brief.get('location'))}.",
        f"Camera: {_normal_text(brief.get('camera'))}.",
        f"Palette: {_normal_text(brief.get('palette'))}.",
        f"Visual intent: {_normal_text(brief.get('visual_intent') or scene.get('visual'))}.",
    ]
    if anchors:
        parts.append("Required anchors: " + "; ".join(_normal_text(item) for item in anchors[:6]) + ".")
    if safety:
        parts.append("Strict safety constraints: " + "; ".join(_normal_text(item) for item in safety[:8]) + ".")
    parts.append(
        "Do not add readable text, logos, watermarks, campaign material, identifiable people, or new story facts. "
        "Keep clean upper and lower overlay lanes for later TikTok text."
    )
    topic = manifest.get("topic") if isinstance(manifest.get("topic"), dict) else {}
    title = _normal_text(topic.get("title"))
    if title:
        parts.append(f"Context to imply visually without text: {title}.")
    return "\n".join(part for part in parts if part.strip())


def _image_instance(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    mime, _ = mimetypes.guess_type(str(path))
    if mime not in {"image/jpeg", "image/png"}:
        mime = "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"mimeType": mime, "bytesBase64Encoded": data}


def build_request_body(
    *,
    prompt: str,
    image_path: Path | None,
    storage_uri: str,
    aspect_ratio: str,
    resolution: str,
    duration_seconds: int,
    sample_count: int,
    generate_audio: bool,
    person_generation: str,
    negative_prompt: str,
    enhance_prompt: bool,
    seed: int | None,
) -> dict[str, Any]:
    instance: dict[str, Any] = {"prompt": prompt}
    image = _image_instance(image_path)
    if image:
        instance["image"] = image
    parameters: dict[str, Any] = {
        "storageUri": storage_uri,
        "sampleCount": sample_count,
        "durationSeconds": duration_seconds,
        "aspectRatio": aspect_ratio,
        "resolution": resolution,
        "personGeneration": person_generation,
        "negativePrompt": negative_prompt,
        "resizeMode": "crop",
    }
    del enhance_prompt
    if generate_audio:
        parameters["generateAudio"] = True
    if seed is not None:
        parameters["seed"] = seed
    return {"instances": [instance], "parameters": parameters}


def build_scene_requests(config: VeoRunConfig) -> list[VeoSceneRequest]:
    manifest = _read_json(config.manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest must be a JSON object: {config.manifest_path}")
    if privacy_policy.is_local_only(mode=config.privacy_mode) and config.allow_paid and not config.dry_run:
        raise RuntimeError(
            "Veo paid call blocked by local-only privacy mode; "
            "Vertex AI video generation can create provider-side request, billing, abuse, or service logs. "
            "Set --privacy-mode cloud_explicit only when that is acceptable."
        )
    receipt_room = manifest.get("receipt_room")
    if isinstance(receipt_room, dict) and config.allow_paid and not config.dry_run:
        if receipt_room.get("generation_ready") is not True:
            blockers = receipt_room.get("generation_blockers")
            blocker_text = ", ".join(str(item) for item in blockers) if isinstance(blockers, list) else "generation_ready_false"
            raise RuntimeError(
                "Receipt Room manifest is not approved for paid Veo generation. "
                f"Blockers: {blocker_text}"
            )
    assets = _load_visual_assets(config.manifest_path, manifest)
    if not assets:
        raise ValueError(f"visual assets not found for manifest: {config.manifest_path}")

    pricing = load_pricing()
    run_id = dt.datetime.now().strftime("veo_%Y%m%d_%H%M%S")
    storage_base = (config.storage_uri or discover_storage_uri(config.project_id) or "").rstrip("/")
    if not storage_base:
        storage_base = f"gs://{config.project_id}-veo-output/tiktok_aino"
    requests: list[VeoSceneRequest] = []
    for scene_id in config.scene_ids:
        asset = _asset_for_scene(assets, scene_id)
        scene = _manifest_scene(manifest, scene_id)
        prompt = build_veo_prompt(manifest, asset, scene)
        image_path = _absolute_asset_path(asset.get("path"), config.manifest_path)
        storage_uri = f"{storage_base}/{run_id}/scene_{scene_id:02d}/"
        body = build_request_body(
            prompt=prompt,
            image_path=image_path,
            storage_uri=storage_uri,
            aspect_ratio=config.aspect_ratio,
            resolution=config.resolution,
            duration_seconds=config.duration_seconds,
            sample_count=config.sample_count,
            generate_audio=config.generate_audio,
            person_generation=config.person_generation,
            negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            enhance_prompt=config.enhance_prompt,
            seed=config.seed,
        )
        cost = estimate_cost_usd(
            pricing=pricing,
            model_id=config.model_id,
            resolution=config.resolution,
            generate_audio=config.generate_audio,
            duration_seconds=config.duration_seconds,
            sample_count=config.sample_count,
            scene_count=1,
        )
        requests.append(
            VeoSceneRequest(
                project_id=config.project_id,
                location=config.location,
                model_id=config.model_id,
                scene_id=scene_id,
                prompt=prompt,
                image_path=str(image_path) if image_path else None,
                storage_uri=storage_uri,
                aspect_ratio=config.aspect_ratio,
                resolution=config.resolution,
                duration_seconds=config.duration_seconds,
                sample_count=config.sample_count,
                generate_audio=config.generate_audio,
                person_generation=config.person_generation,
                negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                enhance_prompt=config.enhance_prompt,
                seed=config.seed,
                estimated_cost_usd=cost,
                request_body=body,
            )
        )
    return requests


def assert_cost_allowed(config: VeoRunConfig, requests: list[VeoSceneRequest]) -> dict[str, Any]:
    projected = round(sum(item.estimated_cost_usd for item in requests), 4)
    month = current_month_key()
    ledger_total = read_monthly_ledger_total(ledger_path(config.state_dir), month)
    status = {
        "projected_cost_usd": projected,
        "current_month_estimated_spend_usd": ledger_total,
        "monthly_cap_usd": config.monthly_cap_usd,
        "run_cap_usd": config.run_cap_usd,
        "month": month,
    }
    blockers: list[str] = []
    if projected > config.run_cap_usd:
        blockers.append("projected_run_cost_exceeds_run_cap")
    if ledger_total + projected > config.monthly_cap_usd:
        blockers.append("projected_monthly_cost_exceeds_monthly_cap")
    if not config.allow_paid:
        blockers.append("allow_paid_not_set")
    status["blockers"] = blockers
    status["allowed"] = not blockers
    if blockers:
        raise RuntimeError("Veo paid call blocked: " + ", ".join(blockers))
    return status


def _api_url(request: VeoSceneRequest, method: str) -> str:
    return (
        f"https://{request.location}-aiplatform.googleapis.com/v1/projects/{request.project_id}"
        f"/locations/{request.location}/publishers/google/models/{request.model_id}:{method}"
    )


def _post_json(url: str, payload: dict[str, Any], *, timeout: int = 180) -> dict[str, Any]:
    token = _gcloud_text(["auth", "print-access-token"], timeout=60)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from Vertex AI: {detail[:1200]}") from exc


def submit_request(request: VeoSceneRequest) -> dict[str, Any]:
    return _post_json(_api_url(request, "predictLongRunning"), request.request_body, timeout=240)


def fetch_operation(request: VeoSceneRequest, operation_name: str) -> dict[str, Any]:
    return _post_json(_api_url(request, "fetchPredictOperation"), {"operationName": operation_name}, timeout=120)


def poll_operation(request: VeoSceneRequest, operation_name: str, *, timeout_sec: int, interval_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = fetch_operation(request, operation_name)
        if last.get("done") is True:
            return last
        time.sleep(max(5, interval_sec))
    raise TimeoutError(f"Veo operation timed out after {timeout_sec}s: {operation_name}; last={last}")


def extract_gcs_uris(payload: Any) -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for value in payload.values():
            found.extend(extract_gcs_uris(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(extract_gcs_uris(item))
    elif isinstance(payload, str) and payload.startswith("gs://"):
        found.append(payload)
    return sorted(set(found))


def download_gcs_uris(uris: list[str], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for index, uri in enumerate(uris, start=1):
        name = Path(uri.rstrip("/").split("/")[-1]).name or f"sample_{index}.mp4"
        if not name.lower().endswith(".mp4"):
            name = f"{Path(name).stem or 'sample'}_{index}.mp4"
        target = output_dir / name
        _gcloud_text(["storage", "cp", uri, str(target)], timeout=600)
        downloaded.append(target)
    return downloaded


def _ffmpeg_path() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg executable not found") from exc


def _media_probe(path: Path) -> dict[str, Any]:
    ffmpeg = _ffmpeg_path()
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    text = proc.stderr + proc.stdout
    duration = None
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if duration_match:
        duration = (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        )
    stream_match = re.search(r"Video:.*?(\d{3,5})x(\d{3,5}).*?(\d+(?:\.\d+)?)\s*fps", text)
    width = int(stream_match.group(1)) if stream_match else None
    height = int(stream_match.group(2)) if stream_match else None
    fps = float(stream_match.group(3)) if stream_match else None
    return {"duration_sec": duration, "width": width, "height": height, "fps": fps}


def _sample_video_frames(path: Path, max_frames: int = 12) -> list[np.ndarray]:
    reader = imageio.get_reader(str(path))
    try:
        length = reader.count_frames()
    except Exception:
        meta = reader.get_meta_data()
        fps = float(meta.get("fps", 24) or 24)
        duration = float(meta.get("duration", 0) or 0)
        length = max(1, int(duration * fps))
    if length <= 0:
        return []
    indexes = sorted({min(length - 1, int(round(i))) for i in np.linspace(0, length - 1, min(max_frames, length))})
    frames: list[np.ndarray] = []
    try:
        for index in indexes:
            frames.append(np.asarray(reader.get_data(index)).astype(np.uint8))
    finally:
        reader.close()
    return frames


def _save_frame_samples(frames: list[np.ndarray], output_dir: Path) -> tuple[list[str], str | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for index, frame in enumerate(frames, start=1):
        path = output_dir / f"sample_{index:02d}.png"
        Image.fromarray(frame).save(path)
        paths.append(str(path))
    if not frames:
        return paths, None
    thumb_w = 240
    thumbs = []
    for frame in frames:
        img = Image.fromarray(frame)
        thumb_h = max(1, round(img.height * thumb_w / img.width))
        thumbs.append(img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS))
    cols = min(4, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumbs[0].height), "#111111")
    draw = ImageDraw.Draw(sheet)
    for idx, thumb in enumerate(thumbs):
        x = (idx % cols) * thumb_w
        y = (idx // cols) * thumb.height
        sheet.paste(thumb, (x, y))
        draw.text((x + 8, y + 8), f"{idx + 1}", fill="#ffffff")
    sheet_path = output_dir / "contact_sheet.png"
    sheet.save(sheet_path)
    return paths, str(sheet_path)


def analyze_video_quality(
    video_path: Path,
    *,
    output_dir: Path,
    expected_duration_sec: int,
    expected_aspect_ratio: str = "9:16",
) -> VideoQualityReport:
    blockers: list[str] = []
    warnings: list[str] = []
    if not video_path.exists():
        return VideoQualityReport(str(video_path), False, ["video_missing"], [], {})
    size_bytes = video_path.stat().st_size
    if expected_duration_sec >= 4 and size_bytes < 100_000:
        blockers.append("video_too_small")
    probe = _media_probe(video_path)
    frames = _sample_video_frames(video_path)
    frame_paths, contact_sheet = _save_frame_samples(frames, output_dir / "qa_frames")
    metrics: dict[str, Any] = {"size_bytes": size_bytes, **probe, "sampled_frames": len(frames)}

    width = probe.get("width")
    height = probe.get("height")
    if width and height and expected_aspect_ratio == "9:16":
        ratio = width / height
        metrics["aspect_ratio"] = round(ratio, 4)
        if abs(ratio - (9 / 16)) > 0.035:
            blockers.append("aspect_ratio_not_9_16")
    duration = probe.get("duration_sec")
    if duration is not None:
        if duration < max(1, expected_duration_sec - 0.75):
            blockers.append("duration_shorter_than_expected")
        if duration > expected_duration_sec + 2.0:
            warnings.append("duration_longer_than_expected")
    fps = probe.get("fps")
    if fps is not None and fps < 20:
        blockers.append("fps_below_20")

    if len(frames) < 2:
        blockers.append("not_enough_frames_for_motion_check")
    else:
        lumas = [frame.astype(np.float32).mean(axis=2).mean() for frame in frames]
        variances = [float(frame.astype(np.float32).var()) for frame in frames]
        diffs = [
            np.abs(frames[i].astype(np.float32) - frames[i - 1].astype(np.float32))
            for i in range(1, len(frames))
        ]
        mean_abs_diffs = [float(diff.mean()) for diff in diffs]
        motion_pixel_ratios = [float((diff.mean(axis=2) > 12).mean()) for diff in diffs]
        metrics.update(
            {
                "luma_min": round(float(min(lumas)), 3),
                "luma_max": round(float(max(lumas)), 3),
                "frame_variance_min": round(float(min(variances)), 3),
                "motion_mean_abs_max": round(max(mean_abs_diffs), 3),
                "motion_mean_abs_avg": round(float(np.mean(mean_abs_diffs)), 3),
                "motion_pixel_ratio_max": round(max(motion_pixel_ratios), 4),
                "motion_pixel_ratio_avg": round(float(np.mean(motion_pixel_ratios)), 4),
            }
        )
        if min(variances) < 20:
            blockers.append("blank_or_flat_frame_detected")
        if min(lumas) < 8 or max(lumas) > 247:
            warnings.append("extreme_luma_detected")
        if max(mean_abs_diffs) < 3.0 and max(motion_pixel_ratios) < 0.015:
            blockers.append("motion_below_threshold")
        if float(np.std(lumas)) > 28:
            warnings.append("possible_global_flicker")

    report = VideoQualityReport(
        video_path=str(video_path),
        passed=not blockers,
        blockers=blockers,
        warnings=warnings,
        metrics=metrics,
        frame_paths=frame_paths,
        contact_sheet=contact_sheet,
    )
    _write_json(output_dir / "qa_report.json", asdict(report))
    return report


def run_dry_plan(config: VeoRunConfig, requests: list[VeoSceneRequest]) -> dict[str, Any]:
    out = config.output_dir / dt.datetime.now().strftime("dry_run_%Y%m%d_%H%M%S")
    request_dir = out / "requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in requests:
        body_path = request_dir / f"scene_{item.scene_id:02d}_request.json"
        _write_json(body_path, item.request_body)
        row = asdict(item)
        row["request_body_path"] = str(body_path)
        row["request_body"] = {
            "instances": [{"prompt": item.prompt, "image": bool(item.image_path)}],
            "parameters": item.request_body.get("parameters", {}),
        }
        rows.append(row)
    summary = {
        "status": "dry_run_ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "privacy": privacy_policy.manifest_record(config.privacy_mode),
        "manifest_path": str(config.manifest_path),
        "estimated_total_cost_usd": round(sum(item.estimated_cost_usd for item in requests), 4),
        "vertex_api_enabled": vertex_api_enabled(),
        "output_dir": str(out),
        "requests": rows,
    }
    _write_json(out / "veo_plan.json", summary)
    return summary


def run_execute(config: VeoRunConfig, requests: list[VeoSceneRequest]) -> dict[str, Any]:
    if config.enable_api and not vertex_api_enabled():
        enable_vertex_api()
    if not vertex_api_enabled():
        raise RuntimeError("aiplatform.googleapis.com is not enabled; rerun with --enable-api after confirming cloud side effects")
    cost_status = assert_cost_allowed(config, requests)
    run_dir = config.output_dir / dt.datetime.now().strftime("paid_run_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for item in requests:
        scene_dir = run_dir / f"scene_{item.scene_id:02d}"
        _write_json(scene_dir / "request.json", item.request_body)
        submitted = submit_request(item)
        _write_json(scene_dir / "submitted_operation.json", submitted)
        operation_name = str(submitted.get("name") or "")
        if not operation_name:
            raise RuntimeError(f"Veo response did not include operation name for scene {item.scene_id}")
        polled = poll_operation(
            item,
            operation_name,
            timeout_sec=config.poll_timeout_sec,
            interval_sec=config.poll_interval_sec,
        )
        _write_json(scene_dir / "operation_result.json", polled)
        if isinstance(polled.get("error"), dict):
            append_ledger(
                ledger_path(config.state_dir),
                {
                    "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "month": current_month_key(),
                    "scene_id": item.scene_id,
                    "model_id": item.model_id,
                    "resolution": item.resolution,
                    "duration_seconds": item.duration_seconds,
                    "sample_count": item.sample_count,
                    "generate_audio": item.generate_audio,
                    "estimated_cost_usd": 0,
                    "projected_cost_usd": item.estimated_cost_usd,
                    "billable": False,
                    "status": "operation_error",
                    "operation_name": operation_name,
                    "operation_error": polled.get("error"),
                },
            )
            results.append(
                {
                    "scene_id": item.scene_id,
                    "status": "operation_error",
                    "operation_name": operation_name,
                    "estimated_cost_usd": 0,
                    "projected_cost_usd": item.estimated_cost_usd,
                    "operation_error": polled.get("error"),
                    "gcs_uris": [],
                    "local_videos": [],
                    "qa_reports": [],
                }
            )
            continue
        gcs_uris = [uri for uri in extract_gcs_uris(polled) if uri.lower().endswith(".mp4")]
        local_videos = download_gcs_uris(gcs_uris, scene_dir / "videos") if gcs_uris else []
        qa_reports = [
            asdict(
                analyze_video_quality(
                    video,
                    output_dir=scene_dir / "qa" / video.stem,
                    expected_duration_sec=item.duration_seconds,
                    expected_aspect_ratio=item.aspect_ratio,
                )
            )
            for video in local_videos
        ]
        ledger_row = {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "month": current_month_key(),
            "scene_id": item.scene_id,
            "model_id": item.model_id,
            "resolution": item.resolution,
            "duration_seconds": item.duration_seconds,
            "sample_count": item.sample_count,
            "generate_audio": item.generate_audio,
            "estimated_cost_usd": item.estimated_cost_usd if gcs_uris else 0,
            "projected_cost_usd": item.estimated_cost_usd,
            "billable": bool(gcs_uris),
            "status": "videos_returned" if gcs_uris else "no_videos_returned",
            "operation_name": operation_name,
            "gcs_uris": gcs_uris,
        }
        append_ledger(ledger_path(config.state_dir), ledger_row)
        results.append(
            {
                "scene_id": item.scene_id,
                "status": "videos_returned" if gcs_uris else "no_videos_returned",
                "operation_name": operation_name,
                "estimated_cost_usd": item.estimated_cost_usd if gcs_uris else 0,
                "projected_cost_usd": item.estimated_cost_usd,
                "gcs_uris": gcs_uris,
                "local_videos": [str(path) for path in local_videos],
                "qa_reports": qa_reports,
            }
        )
    summary = {
        "status": "completed" if all(row.get("status") == "videos_returned" for row in results) else "completed_with_errors",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "privacy": privacy_policy.manifest_record(config.privacy_mode),
        "cost_guard": cost_status,
        "output_dir": str(run_dir),
        "results": results,
    }
    _write_json(run_dir / "veo_run_report.json", summary)
    return summary


def _parse_scene_ids(value: str) -> list[int]:
    ids: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        ids.append(int(part))
    return ids or [1]


def build_config(args: argparse.Namespace) -> VeoRunConfig:
    project_id = args.project_id or default_project_id()
    if not project_id:
        raise RuntimeError("GCP project id unavailable; set --project-id or AINO_VEO_PROJECT_ID")
    allow_paid = bool(args.allow_paid or _env_bool("AINO_VEO_ALLOW_PAID", False))
    storage_uri = args.storage_uri or os.environ.get("AINO_VEO_STORAGE_URI")
    return VeoRunConfig(
        manifest_path=args.manifest.resolve(),
        scene_ids=_parse_scene_ids(args.scene_ids),
        output_dir=args.output_dir.resolve(),
        state_dir=args.state_dir.resolve(),
        project_id=project_id,
        location=args.location,
        model_id=args.model_id,
        storage_uri=storage_uri,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        duration_seconds=args.duration,
        sample_count=args.sample_count,
        generate_audio=args.generate_audio,
        person_generation=args.person_generation,
        enhance_prompt=not args.disable_prompt_enhancement,
        seed=args.seed,
        run_cap_usd=args.run_cap_usd,
        monthly_cap_usd=args.monthly_cap_usd,
        allow_paid=allow_paid,
        enable_api=args.enable_api,
        poll_timeout_sec=args.poll_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
        dry_run=args.dry_run,
        privacy_mode=args.privacy_mode,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and QA guarded Veo candidates for AiNo TikTok scenes.")
    parser.add_argument("--manifest", type=Path, default=REPO_DIR / "output" / "tiktok_aino_scheduled_packages" / "leftaino_20260512_181016" / "manifest.json")
    parser.add_argument("--scene-ids", default="1")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--project-id", default=os.environ.get("AINO_VEO_PROJECT_ID"))
    parser.add_argument("--location", default=os.environ.get("AINO_VEO_LOCATION", "us-central1"))
    parser.add_argument("--model-id", default=os.environ.get("AINO_VEO_MODEL_ID", "veo-3.1-generate-001"))
    parser.add_argument("--storage-uri")
    parser.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "16:9"])
    parser.add_argument("--resolution", default=os.environ.get("AINO_VEO_RESOLUTION", "1080p"), choices=["720p", "1080p"])
    parser.add_argument("--duration", type=int, default=int(os.environ.get("AINO_VEO_DURATION", "4")), choices=[4, 6, 8])
    parser.add_argument("--sample-count", type=int, default=int(os.environ.get("AINO_VEO_SAMPLE_COUNT", "1")))
    parser.add_argument("--generate-audio", action="store_true")
    parser.add_argument("--person-generation", default=os.environ.get("AINO_VEO_PERSON_GENERATION", "allow_adult"), choices=["disallow", "allow_adult"])
    parser.add_argument("--disable-prompt-enhancement", action="store_true")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--run-cap-usd", type=float, default=float(os.environ.get("AINO_VEO_RUN_CAP_USD", "2.00")))
    parser.add_argument("--monthly-cap-usd", type=float, default=float(os.environ.get("AINO_VEO_MONTHLY_CAP_USD", "90.00")))
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--enable-api", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--privacy-mode",
        choices=[privacy_policy.LOCAL_ONLY, privacy_policy.CLOUD_EXPLICIT],
        default=privacy_policy.current_mode(),
    )
    parser.add_argument("--poll-timeout-sec", type=int, default=int(os.environ.get("AINO_VEO_POLL_TIMEOUT_SEC", "1800")))
    parser.add_argument("--poll-interval-sec", type=int, default=int(os.environ.get("AINO_VEO_POLL_INTERVAL_SEC", "20")))
    parser.add_argument("--qa-video", type=Path, help="Run local QA against an existing MP4 instead of calling Veo.")
    args = parser.parse_args(argv)

    if args.sample_count < 1 or args.sample_count > 4:
        raise RuntimeError("--sample-count must be between 1 and 4")

    if args.qa_video:
        out = args.output_dir.resolve() / dt.datetime.now().strftime("qa_only_%Y%m%d_%H%M%S")
        report = analyze_video_quality(
            args.qa_video.resolve(),
            output_dir=out,
            expected_duration_sec=args.duration,
            expected_aspect_ratio=args.aspect_ratio,
        )
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 0 if report.passed else 2

    config = build_config(args)
    requests = build_scene_requests(config)
    if args.dry_run or not config.allow_paid:
        summary = run_dry_plan(config, requests)
        if not config.allow_paid:
            summary["status"] = "dry_run_only_paid_call_blocked"
            summary["paid_call_blocker"] = "pass --allow-paid or set AINO_VEO_ALLOW_PAID=1 to submit to Vertex AI"
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    summary = run_execute(config, requests)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
