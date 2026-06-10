"""Browser upload preparation for AiNo TikTok packages.

The automation uses a normal logged-in Chrome profile and stops on account
security prompts. Final posting/scheduling requires explicit mode selection
and AINO_UPLOAD_AUTOMATION_ENABLED=true.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


PACKAGE_DIR = Path(__file__).resolve().parent
EXTENSION_DIR = PACKAGE_DIR / "extension" / "chrome"
CONFIG_DIR = PACKAGE_DIR / "config"
DEFAULT_CDP_PORT = 9222
DEFAULT_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
LEGACY_UPLOAD_URL = "https://www.tiktok.com/upload"
REMOTE_FILE_TRANSFER_LIMIT_BYTES = 50 * 1024 * 1024
UPLOAD_SAFE_TARGET_BYTES = 44 * 1024 * 1024
VERIFICATION_STOPWORDS = {
    "지금",
    "중요한",
    "확인된",
    "근거",
    "무엇",
    "아직",
    "비어",
    "있는",
    "지점",
    "정리",
    "했습니다",
    "당신은",
    "생각하나요",
}
AIGC_DISCLOSURE_TERMS = (
    "생성된 이미지",
    "생성 이미지",
    "생성형 이미지",
    "생성형 AI",
    "AI 음성",
    "AI 생성",
    "AI-generated",
    "generated content",
)
FOLLOW_CTA_TERMS = ("팔로우", "구독")
SERIES_IDENTITY_TERMS = ("다음 편", "이어갑니다", "후속", "계속", "매일", "다음 흐름")


def _caption_has_aigc_disclosure(caption: str) -> bool:
    normalized = caption.lower()
    return any(term.lower() in normalized for term in AIGC_DISCLOSURE_TERMS)


def _caption_has_follow_cta(caption: str) -> bool:
    return any(term in caption for term in FOLLOW_CTA_TERMS)


def _caption_has_series_identity(caption: str) -> bool:
    return any(term in caption for term in SERIES_IDENTITY_TERMS)


def _caption_upload_cta_status(caption: str) -> dict[str, bool]:
    return {
        "caption_follow_cta_present": _caption_has_follow_cta(caption),
        "caption_series_identity_present": _caption_has_series_identity(caption),
    }


def _verification_needles(job: dict[str, Any]) -> list[str]:
    post_title = str(job.get("post_title") or "").strip()
    caption = str(job.get("caption") or "").strip()
    content_terms = [
        term
        for term in re.findall(r"[가-힣A-Za-z0-9·]{3,}", f"{post_title} {caption}")
        if term not in VERIFICATION_STOPWORDS and not term.startswith("#")
    ]
    needles: list[str] = []
    for needle in [post_title[:18], caption[:24], *content_terms[:6]]:
        if needle and needle not in needles:
            needles.append(needle)
    return needles


def _studio_time_needles(planned_publish_at_local: str | None) -> list[str]:
    if not planned_publish_at_local:
        return []
    schedule = _schedule_parts(planned_publish_at_local)
    if not schedule:
        return []
    parsed = dt.datetime.fromisoformat(schedule["iso"])
    hour = parsed.hour
    minute = parsed.minute
    ampm = "오전" if hour < 12 else "오후"
    hour12 = hour % 12 or 12
    return [
        f"{parsed.month}월 {parsed.day}일 {ampm} {hour12}:{minute:02d}",
        f"{parsed.month}월 {parsed.day}일",
        schedule["time_24h"],
        schedule["time_ampm"],
    ]


def _load_config(filename: str) -> dict[str, Any]:
    return json.loads((CONFIG_DIR / filename).read_text(encoding="utf-8"))


def _caption_with_aigc_disclosure(caption: str) -> str:
    if _caption_has_aigc_disclosure(caption):
        return caption
    label = str(_load_config("publish_quality_strategy.json").get("aigc_disclosure_label") or "해당 이미지는 생성된 이미지입니다").strip()
    if not label:
        return caption
    return f"{caption.rstrip()}\n\n{label}".strip()


def _chrome_executable() -> Path | None:
    env_path = os.environ.get("AINO_CHROME_EXE")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    candidates: list[Path] = []
    if platform.system().lower() == "windows":
        for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(key)
            if root:
                candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            resolved = shutil_which(name)
            if resolved:
                candidates.append(Path(resolved))
    return next((path for path in candidates if path.exists()), None)


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def _ffmpeg_executable() -> str | None:
    configured = os.environ.get("FFMPEG_BINARY") or os.environ.get("FFMPEG_EXE")
    if configured and Path(configured).exists():
        return configured
    found = shutil_which("ffmpeg")
    if found:
        return found
    bundled = Path("D:/local-dev/tools/ffmpeg/ffmpeg.exe")
    if bundled.exists():
        return str(bundled)
    with contextlib.suppress(Exception):
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    return None


def _video_duration_seconds(path: Path) -> float | None:
    ffmpeg = _ffmpeg_executable()
    if not ffmpeg:
        return None
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    text = f"{proc.stderr}\n{proc.stdout}"
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _upload_safe_mp4(source: Path) -> dict[str, Any]:
    source = source.resolve()
    size = source.stat().st_size if source.exists() else 0
    if size <= REMOTE_FILE_TRANSFER_LIMIT_BYTES:
        return {"ok": True, "mp4_path": str(source), "original_size_bytes": size, "transcoded": False}
    ffmpeg = _ffmpeg_executable()
    if not ffmpeg:
        return {
            "ok": False,
            "reason": "ffmpeg_not_found_for_upload_safe_transcode",
            "mp4_path": str(source),
            "original_size_bytes": size,
        }
    safe_path = source.with_name(f"{source.stem}_upload_safe{source.suffix}")
    if safe_path.exists() and safe_path.stat().st_size <= REMOTE_FILE_TRANSFER_LIMIT_BYTES:
        return {
            "ok": True,
            "mp4_path": str(safe_path.resolve()),
            "original_mp4_path": str(source),
            "original_size_bytes": size,
            "size_bytes": safe_path.stat().st_size,
            "transcoded": False,
            "reused": True,
        }
    duration = _video_duration_seconds(source) or 70.0
    target_video_kbps = max(900, min(4200, int((UPLOAD_SAFE_TARGET_BYTES * 8 / max(1.0, duration) / 1000) - 160)))
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        f"{target_video_kbps}k",
        "-maxrate",
        f"{target_video_kbps}k",
        "-bufsize",
        f"{target_video_kbps * 2}k",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(safe_path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not safe_path.exists():
        return {
            "ok": False,
            "reason": "upload_safe_transcode_failed",
            "mp4_path": str(source),
            "original_size_bytes": size,
            "stderr_tail": "\n".join((proc.stderr or proc.stdout or "").splitlines()[-6:]),
        }
    safe_size = safe_path.stat().st_size
    if safe_size > REMOTE_FILE_TRANSFER_LIMIT_BYTES:
        return {
            "ok": False,
            "reason": "upload_safe_transcode_still_too_large",
            "mp4_path": str(safe_path.resolve()),
            "original_mp4_path": str(source),
            "original_size_bytes": size,
            "size_bytes": safe_size,
        }
    return {
        "ok": True,
        "mp4_path": str(safe_path.resolve()),
        "original_mp4_path": str(source),
        "original_size_bytes": size,
        "size_bytes": safe_size,
        "target_video_kbps": target_video_kbps,
        "transcoded": True,
    }


def _default_profile_dir() -> Path:
    configured = os.environ.get("AINO_CHROME_PROFILE_DIR")
    if configured:
        return Path(configured)
    if platform.system().lower() == "windows":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NeoGenesis" / "TikTokAiNoChrome"
    return Path.home() / ".neo-genesis" / "tiktok-aino-chrome"


def _http_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def cdp_available(port: int) -> bool:
    return bool(_http_json(f"http://127.0.0.1:{port}/json/version"))


def launch_chrome(*, port: int, profile_dir: Path, extension_dir: Path = EXTENSION_DIR) -> dict[str, Any]:
    if cdp_available(port):
        return {"ok": True, "already_running": True, "port": port}
    chrome = _chrome_executable()
    if not chrome:
        return {"ok": False, "reason": "chrome_not_found"}
    profile_dir.mkdir(parents=True, exist_ok=True)
    args = [
        str(chrome),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if extension_dir.exists():
        args.extend([f"--disable-extensions-except={extension_dir}", f"--load-extension={extension_dir}"])
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        if cdp_available(port):
            return {"ok": True, "started": True, "port": port, "profile_dir": str(profile_dir)}
        time.sleep(0.5)
    return {"ok": False, "reason": "chrome_cdp_timeout", "profile_dir": str(profile_dir)}


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"manifest must be a JSON object: {manifest_path}")
    return data


def build_upload_job(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _load_manifest(manifest_path)
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest.get("artifacts"), dict) else {}
    script = manifest.get("script", {}) if isinstance(manifest.get("script"), dict) else {}
    raw_mp4 = str(artifacts.get("mp4", "") or "").strip()
    mp4 = Path(raw_mp4) if raw_mp4 else manifest_path.parent / "preview_1080x1920.mp4"
    if raw_mp4 and not mp4.is_absolute():
        cwd_mp4 = (Path.cwd() / mp4).resolve()
        manifest_mp4 = (manifest_path.parent / mp4).resolve()
        mp4 = cwd_mp4 if cwd_mp4.exists() else manifest_mp4
    if not mp4.exists():
        local_mp4 = manifest_path.parent / "preview_1080x1920.mp4"
        mp4 = local_mp4 if local_mp4.exists() else mp4
    if mp4.exists():
        mp4 = mp4.resolve()
    from src.core.tiktok_aino import pipeline

    validation = pipeline.validate_manifest_for_upload(manifest)
    if not validation["upload_ready"]:
        return {
            "ok": False,
            "reason": "manifest_not_upload_ready",
            "manifest_path": str(manifest_path),
            "run_id": manifest.get("run_id") or manifest_path.parent.name,
            "status": validation["status"],
            "raw_manifest_status": manifest.get("status"),
            "validation": validation,
            "mp4_path": str(mp4),
        }
    if not mp4.exists():
        return {
            "ok": False,
            "reason": "mp4_missing",
            "manifest_path": str(manifest_path),
            "run_id": manifest.get("run_id") or manifest_path.parent.name,
            "status": validation["status"],
            "raw_manifest_status": manifest.get("status"),
            "validation": validation,
            "mp4_path": str(mp4),
        }
    upload_safe = _upload_safe_mp4(mp4)
    if not upload_safe.get("ok"):
        return {
            "ok": False,
            "reason": upload_safe.get("reason") or "upload_safe_mp4_failed",
            "manifest_path": str(manifest_path),
            "run_id": manifest.get("run_id") or manifest_path.parent.name,
            "status": validation["status"],
            "raw_manifest_status": manifest.get("status"),
            "validation": validation,
            "mp4_path": str(mp4),
            "upload_safe": upload_safe,
        }
    upload_mp4 = Path(str(upload_safe.get("mp4_path") or mp4)).resolve()
    caption = _caption_with_aigc_disclosure(str(script.get("caption", "")))
    caption_cta = _caption_upload_cta_status(caption)
    if not all(caption_cta.values()):
        return {
            "ok": False,
            "reason": "caption_follow_cta_missing",
            "manifest_path": str(manifest_path),
            "run_id": manifest.get("run_id") or manifest_path.parent.name,
            "status": validation["status"],
            "raw_manifest_status": manifest.get("status"),
            "validation": validation,
            "mp4_path": str(upload_mp4),
            "source_mp4_path": str(mp4),
            "upload_safe": upload_safe,
            "caption_cta": caption_cta,
        }
    return {
        "ok": True,
        "manifest_path": str(manifest_path),
        "run_id": manifest.get("run_id") or manifest_path.parent.name,
        "status": validation["status"],
        "raw_manifest_status": manifest.get("status"),
        "validation": validation,
        "planned_publish_at_local": manifest.get("planned_publish_at_local"),
        "schedule_status": manifest.get("schedule_status"),
        "mp4_path": str(upload_mp4),
        "source_mp4_path": str(mp4),
        "upload_safe": upload_safe,
        "caption": caption,
        "post_title": str(script.get("post_title", "")),
        "hashtags": script.get("hashtags", []),
        "pinned_comment": str(script.get("pinned_comment", "")),
        "caption_cta": caption_cta,
        "aigc_required": True,
    }


def _schedule_parts(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return {
        "iso": parsed.isoformat(),
        "date_iso": parsed.strftime("%Y-%m-%d"),
        "date_slash": parsed.strftime("%m/%d/%Y"),
        "time_24h": parsed.strftime("%H:%M"),
        "time_ampm": parsed.strftime("%I:%M %p").lstrip("0"),
    }


async def _prepare_with_playwright(job: dict[str, Any], *, port: int, mode: str, allow_external_post: bool) -> dict[str, Any]:
    from playwright.async_api import async_playwright

    async def click_unique_button(page: Any, labels: list[str]) -> dict[str, Any]:
        return await page.evaluate(
            """(labels) => {
              const normalized = labels.map((label) => String(label).toLowerCase());
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const buttons = [...document.querySelectorAll("button")]
                .filter((node) => !node.disabled && visible(node))
                .map((node) => ({ node, text: (node.innerText || node.textContent || node.getAttribute("aria-label") || "").trim() }))
                .filter((item) => normalized.some((label) => item.text.toLowerCase().includes(label)));
              const exact = buttons.filter((item) => normalized.some((label) => item.text.toLowerCase() === label));
              const candidates = exact.length ? exact : buttons;
              if (candidates.length !== 1) {
                return { ok: false, reason: "button_match_count", count: buttons.length, labels, matches: buttons.slice(0, 5).map((item) => item.text) };
              }
              candidates[0].node.click();
              return { ok: true, label: candidates[0].text };
            }""",
            labels,
        )

    async def click_optional_exact(page: Any, labels: list[str]) -> dict[str, Any]:
        return await page.evaluate(
            """(labels) => {
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const buttons = [...document.querySelectorAll("button")]
                .filter((node) => !node.disabled && visible(node))
                .map((node) => ({ node, text: (node.innerText || node.textContent || node.getAttribute("aria-label") || "").trim() }));
              for (const label of labels) {
                const matches = buttons.filter((item) => item.text === label);
                if (matches.length === 1) {
                  matches[0].node.click();
                  return { ok: true, label };
                }
              }
              return { ok: false, reason: "no_exact_button", labels, matches: buttons.slice(-12).map((item) => item.text) };
            }""",
            labels,
        )

    async def click_best_button(page: Any, labels: list[str], *, purpose: str) -> dict[str, Any]:
        return await page.evaluate(
            """({ labels, purpose }) => {
              const normalized = labels.map((label) => String(label).toLowerCase().replace(/\\s+/g, " ").trim());
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const disallowed = ["creator academy", "analytics", "분석", "개인 정보", "아이디어", "피드백"];
              const nodes = [...document.querySelectorAll("button, [role='button']")]
                .filter((node) => !node.disabled && node.getAttribute("aria-disabled") !== "true" && visible(node))
                .map((node) => {
                  const box = node.getBoundingClientRect();
                  const text = (node.innerText || node.textContent || node.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim();
                  const lower = text.toLowerCase();
                  const labelScore = normalized.reduce((best, label) => {
                    if (!label) return best;
                    if (lower === label) return Math.max(best, 100);
                    if (lower.includes(label)) return Math.max(best, 70);
                    return best;
                  }, 0);
                  if (labelScore <= 0) return null;
                  const classText = String(node.className || "").toLowerCase();
                  let score = labelScore;
                  if (node.tagName === "BUTTON") score += 15;
                  if (classText.includes("primary") || classText.includes("tuxbutton")) score += 10;
                  if (box.y > window.innerHeight * 0.45) score += 8;
                  if (box.x > window.innerWidth * 0.45) score += 8;
                  if (text.length <= 24) score += 4;
                  if ((purpose.includes("submit") || purpose.includes("confirm")) && box.x < window.innerWidth * 0.35) score -= 90;
                  if (disallowed.some((term) => lower.includes(term))) score -= 100;
                  return { node, text, score, labelScore, x: box.x, y: box.y, width: box.width, height: box.height };
                })
                .filter(Boolean)
                .filter((item) => item.score > 0)
                .sort((a, b) => b.score - a.score || b.y - a.y || b.x - a.x);
              if (!nodes.length) {
                return { ok: false, reason: "button_not_found", labels, purpose };
              }
              nodes[0].node.scrollIntoView({ block: "center", inline: "center" });
              nodes[0].node.click();
              return {
                ok: true,
                label: nodes[0].text,
                purpose,
                score: nodes[0].score,
                candidate_count: nodes.length,
                candidates: nodes.slice(0, 8).map((item) => ({ text: item.text, score: item.score, labelScore: item.labelScore, x: item.x, y: item.y }))
              };
            }""",
            {"labels": labels, "purpose": purpose},
        )

    async def upload_editor_state(page: Any) -> dict[str, Any]:
        return await page.evaluate(
            """() => {
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const captionTargets = [...document.querySelectorAll("[contenteditable='true'], textarea")].filter(visible);
              const buttons = [...document.querySelectorAll("button, [role='button']")]
                .filter((node) => !node.disabled && node.getAttribute("aria-disabled") !== "true" && visible(node))
                .map((node) => (node.innerText || node.textContent || node.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim())
                .filter(Boolean);
              const bodyText = (document.body?.innerText || "").replace(/\\s+/g, " ").trim();
              const lower = bodyText.toLowerCase();
              const hasScheduleButton = buttons.some((text) => ["예약", "schedule"].some((label) => text.toLowerCase().includes(label)));
              const hasPostButton = buttons.some((text) => ["게시", "post"].some((label) => text.toLowerCase().includes(label)));
              const hasUploadProgress = /\\b\\d{1,3}(?:\\.\\d+)?%\\b/.test(bodyText)
                || /\\b\\d+(?:\\.\\d+)?MB\\s*\\/\\s*\\d+(?:\\.\\d+)?MB\\b/i.test(bodyText)
                || bodyText.includes("남음")
                || bodyText.includes("파일을 업로드한 후에만");
              const processing = hasUploadProgress || ["uploading", "processing", "업로드 중", "처리 중", "검사 중"].some((term) => lower.includes(term));
              const captionText = captionTargets.map((node) => node.innerText || node.value || "").join("\\n").trim();
              return {
                fileInputCount: document.querySelectorAll("input[type='file']").length,
                captionTargetCount: captionTargets.length,
                captionText,
                buttons: buttons.slice(-20),
                editorReady: captionTargets.length > 0,
                actionReady: captionTargets.length > 0 && (hasScheduleButton || hasPostButton),
                processing,
                bodySample: bodyText.slice(0, 800)
              };
            }"""
        )

    async def wait_until_upload_ready(page: Any, *, purpose: str) -> dict[str, Any]:
        last_state: dict[str, Any] = {}
        for attempt in range(240):
            last_state = await upload_editor_state(page)
            if last_state.get("actionReady") and not last_state.get("processing"):
                return {"ok": True, "attempt": attempt + 1, "purpose": purpose, "state": last_state}
            await page.wait_for_timeout(1000)
        return {"ok": False, "reason": "upload_action_not_ready", "purpose": purpose, "state": last_state}

    async def configure_aigc_disclosure(page: Any, job: dict[str, Any]) -> dict[str, Any]:
        caption = str(job.get("caption") or "")
        result: dict[str, Any] = {
            "required": bool(job.get("aigc_required")),
            "caption_disclosure_present": _caption_has_aigc_disclosure(caption),
            "platform_control_found": False,
            "platform_control_enabled": False,
            "ok": True,
        }
        if not result["required"]:
            return result
        platform = await page.evaluate(
            """() => {
              const terms = ["ai-generated", "ai generated", "ai 생성", "ai로 생성", "생성형 ai", "content disclosure", "콘텐츠 공개", "수정된 콘텐츠"];
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const labelFor = (node) => {
                const own = (node.innerText || node.textContent || node.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim();
                const parent = (node.closest("label, div, section")?.innerText || "").replace(/\\s+/g, " ").trim();
                return `${own} ${parent}`.trim();
              };
              const candidates = [...document.querySelectorAll("input[type='checkbox'], input[type='radio'], button, [role='switch'], [role='checkbox']")]
                .filter(visible)
                .map((node) => ({ node, text: labelFor(node), checked: node.checked || node.getAttribute("aria-checked") === "true" }))
                .filter((item) => terms.some((term) => item.text.toLowerCase().includes(term)));
              if (!candidates.length) {
                return { found: false, enabled: false, candidates: [] };
              }
              const target = candidates.find((item) => !item.checked) || candidates[0];
              if (!target.checked) target.node.click();
              const enabled = target.node.checked || target.node.getAttribute("aria-checked") === "true" || target.checked;
              return { found: true, enabled, clicked: !target.checked, label: target.text.slice(0, 120), candidates: candidates.slice(0, 5).map((item) => item.text.slice(0, 120)) };
            }"""
        )
        result["platform_control_found"] = bool(platform.get("found"))
        result["platform_control_enabled"] = bool(platform.get("enabled"))
        result["platform_result"] = platform
        result["ok"] = bool(result["caption_disclosure_present"] or result["platform_control_enabled"])
        if not result["ok"]:
            result["warning"] = "aigc_disclosure_not_confirmed"
        return result

    async def verify_studio_content_visible(page: Any, job: dict[str, Any]) -> dict[str, Any]:
        needles = _verification_needles(job)
        time_needles = _studio_time_needles(str(job.get("planned_publish_at_local") or ""))
        text = ""
        matched: list[str] = []
        time_matched: list[str] = []
        for attempt in range(3):
            await page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(10000 + attempt * 5000)
            with contextlib.suppress(Exception):
                text = await page.locator("body").inner_text(timeout=15000)
            matched = [needle for needle in needles if needle in text]
            time_matched = [needle for needle in time_needles if needle in text]
            if matched and (not time_needles or time_matched):
                break
        return {
            "ok": bool(matched and (not time_needles or time_matched)),
            "contains_topic": bool(matched),
            "contains_time": bool(time_matched) if time_needles else True,
            "needles": needles,
            "matched": matched,
            "time_needles": time_needles,
            "time_matched": time_matched,
            "url": page.url,
            "body_sample": text[:1000],
        }

    async def configure_schedule(page: Any, schedule: dict[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": False,
            "schedule_enabled": False,
            "date_set": False,
            "time_set": False,
            "notes": [],
        }

        def _time_parts(value: str) -> tuple[int, int]:
            hour, minute = value.split(":", 1)
            return int(hour), int(minute)

        async def schedule_inputs() -> dict[str, Any]:
            return await page.evaluate(
                """() => {
                  const visible = (node) => {
                    const style = window.getComputedStyle(node);
                    const box = node.getBoundingClientRect();
                    return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
                  };
                  const inputs = [...document.querySelectorAll("input.TUXTextInputCore-input")]
                    .filter(visible)
                    .map((node, index) => ({ index, value: node.value || "", type: node.type || "", cls: String(node.className || "") }));
                  return {
                    inputs,
                    timeIndex: inputs.find((item) => /^\\d{1,2}:\\d{2}$/.test(item.value))?.index ?? -1,
                    dateIndex: inputs.find((item) => /^\\d{4}-\\d{2}-\\d{2}$/.test(item.value))?.index ?? -1
                  };
                }"""
            )

        async def click_input(index: int) -> dict[str, Any]:
            box = await page.evaluate(
                """(index) => {
                  const visible = (node) => {
                    const style = window.getComputedStyle(node);
                    const box = node.getBoundingClientRect();
                    return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
                  };
                  const inputs = [...document.querySelectorAll("input.TUXTextInputCore-input")].filter(visible);
                  const node = inputs[index];
                  if (!node) return null;
                  node.scrollIntoView({ block: "center", inline: "center" });
                  const box = node.getBoundingClientRect();
                  const x = box.x + box.width / 2;
                  const y = box.y + box.height / 2;
                  node.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, clientX: x, clientY: y }));
                  node.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: x, clientY: y }));
                  node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: x, clientY: y }));
                  node.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: x, clientY: y }));
                  node.focus();
                  return { x, y, width: box.width, height: box.height, value: node.value || "" };
                }""",
                index,
            )
            if box:
                await page.mouse.click(float(box["x"]), float(box["y"]))
                await page.wait_for_timeout(120)
                return {"ok": True, **box}
            return {"ok": False, "reason": "input_not_found", "index": index}

        async def set_input_value(index: int, value: str) -> dict[str, Any]:
            return await page.evaluate(
                """({ index, value }) => {
                  const visible = (node) => {
                    const style = window.getComputedStyle(node);
                    const box = node.getBoundingClientRect();
                    return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
                  };
                  const inputs = [...document.querySelectorAll("input.TUXTextInputCore-input")].filter(visible);
                  const node = inputs[index];
                  if (!node) return { ok: false, reason: "input_not_found", index };
                  node.scrollIntoView({ block: "center", inline: "center" });
                  node.focus();
                  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
                  if (setter) setter.call(node, value);
                  else node.value = value;
                  node.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
                  node.dispatchEvent(new Event("change", { bubbles: true }));
                  node.dispatchEvent(new FocusEvent("blur", { bubbles: true }));
                  return { ok: node.value === value, value: node.value, index };
                }""",
                {"index": index, "value": value},
            )

        schedule_click = await page.evaluate(
            """(label) => {
              const visible = (node) => {
                const style = window.getComputedStyle(node);
                const box = node.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
              };
              const radio = [...document.querySelectorAll("input[name='postSchedule']")]
                .find((node) => node.value === "schedule");
              if (radio) {
                if (!radio.checked) radio.click();
                return { ok: true, method: "radio", checked: radio.checked };
              }
              const targets = [...document.querySelectorAll("button, label, div, span")]
                .filter(visible)
                .filter((node) => ((node.innerText || node.textContent || "").trim() === label));
              if (targets.length) {
                targets[targets.length - 1].click();
                return { ok: true, method: "text", count: targets.length };
              }
              return { ok: false, method: "not_found" };
            }""",
            "\uc608\uc57d",
        )
        result["schedule_enabled"] = bool(schedule_click.get("ok"))
        result["schedule_click"] = schedule_click
        await page.wait_for_timeout(500)

        inputs = await schedule_inputs()
        result["inputs_before"] = inputs.get("inputs", [])[:16]
        time_index = int(inputs.get("timeIndex", -1))
        date_index = int(inputs.get("dateIndex", -1))
        if time_index < 0 or date_index < 0:
            result["notes"].append("schedule inputs not found")
            return result

        target_date = dt.date.fromisoformat(schedule["date_iso"])

        async def click_target_date() -> dict[str, Any]:
            last: dict[str, Any] = {"ok": False, "count": 0}
            for attempt in range(4):
                await click_input(date_index)
                with contextlib.suppress(Exception):
                    await page.locator("input.TUXTextInputCore-input").nth(date_index).click(force=True, timeout=2000)
                await page.wait_for_timeout(700 + attempt * 250)
                last = await page.evaluate(
                    """(day) => {
                      const visible = (node) => {
                        const style = window.getComputedStyle(node);
                        const box = node.getBoundingClientRect();
                        return style.visibility !== "hidden" && style.display !== "none" && box.width > 8 && box.height > 8;
                      };
                      const candidates = [...document.querySelectorAll(".calendar-wrapper .day.valid, .calendar-wrapper .day")]
                        .filter((node) => visible(node))
                        .filter((node) => !String(node.className || "").toLowerCase().includes("disabled"))
                        .filter((node) => (node.innerText || node.textContent || "").trim() === String(day));
                      const validNodes = candidates.filter((node) => String(node.className || "").toLowerCase().includes("valid"));
                      const nodes = (validNodes.length ? validNodes : candidates)
                        .sort((a, b) => {
                          const boxA = a.getBoundingClientRect();
                          const boxB = b.getBoundingClientRect();
                          return (boxA.y < 0) - (boxB.y < 0) || boxA.y - boxB.y;
                        });
                      if (!nodes.length) return { ok: false, count: 0 };
                      nodes[0].click();
                      const box = nodes[0].getBoundingClientRect();
                      return { ok: true, count: nodes.length, pickedClass: String(nodes[0].className || ""), pickedY: box.y };
                    }""",
                    target_date.day,
                )
                if last.get("ok"):
                    return last
            return last

        date_clicked = await click_target_date()
        await page.wait_for_timeout(500)
        inputs = await schedule_inputs()
        current_date = next((item.get("value") for item in inputs.get("inputs", []) if item.get("index") == date_index), "")
        result["date_set"] = date_clicked.get("ok") and current_date == schedule["date_iso"]
        result["date_click"] = date_clicked
        result["date_value"] = current_date
        if not result["date_set"]:
            direct_date = await set_input_value(date_index, schedule["date_iso"])
            await page.wait_for_timeout(400)
            inputs = await schedule_inputs()
            current_date = next((item.get("value") for item in inputs.get("inputs", []) if item.get("index") == date_index), "")
            result["date_direct_set"] = direct_date
            result["date_value"] = current_date
            result["date_set"] = current_date == schedule["date_iso"]
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        target_hour, target_minute = _time_parts(schedule["time_24h"])
        if target_minute % 5 != 0:
            result["notes"].append("TikTok time picker only exposes 5-minute increments")
            return result

        async def open_time_picker() -> dict[str, Any]:
            for _ in range(3):
                await click_input(time_index)
                with contextlib.suppress(Exception):
                    await page.locator("input.TUXTextInputCore-input").nth(time_index).click(force=True, timeout=2000)
                await page.wait_for_timeout(800)
                picker = await page.evaluate(
                    """() => {
                      const containers = [...document.querySelectorAll(".tiktok-timepicker-time-picker-container")];
                      const node = containers.find((item) => !String(item.className).includes("invisible") && item.getBoundingClientRect().height > 20)
                        || containers.find((item) => item.getBoundingClientRect().height > 20);
                      const columns = [...document.querySelectorAll(".tiktok-timepicker-time-scroll-container")]
                        .map((item) => {
                          const box = item.getBoundingClientRect();
                          return { x: box.x, y: box.y, width: box.width, height: box.height, clientHeight: item.clientHeight };
                        })
                        .filter((box) => box.width > 20 && (box.height > 20 || box.clientHeight > 20));
                      if (columns.length >= 2) {
                        const hour = columns[0];
                        const minute = columns[1];
                        return {
                          x: Math.min(hour.x, minute.x),
                          y: Math.min(hour.y, minute.y),
                          width: Math.max(hour.x + hour.width, minute.x + minute.width) - Math.min(hour.x, minute.x),
                          height: Math.max(hour.height, minute.height),
                          hourX: hour.x + hour.width / 2,
                          minuteX: minute.x + minute.width / 2,
                          rowY: hour.y + hour.height / 2
                        };
                      }
                      if (!node) return null;
                      const box = node.getBoundingClientRect();
                      return { x: box.x, y: box.y, width: box.width, height: box.height };
                    }"""
                )
                if picker and picker.get("height", 0) > 20:
                    return picker
            return {}

        async def current_time_value() -> str:
            data = await schedule_inputs()
            return str(next((item.get("value") for item in data.get("inputs", []) if item.get("index") == time_index), ""))

        direct_time = await set_input_value(time_index, schedule["time_24h"])
        await page.wait_for_timeout(500)
        result["time_direct_set"] = direct_time
        if await current_time_value() == schedule["time_24h"]:
            result["time_set"] = True
        if not result["time_set"]:
            keyboard_click = await click_input(time_index)
            await page.keyboard.press("Control+A")
            await page.keyboard.type(schedule["time_24h"], delay=25)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
            result["time_keyboard_set"] = {
                "click": keyboard_click,
                "value": await current_time_value(),
            }
            if result["time_keyboard_set"]["value"] == schedule["time_24h"]:
                result["time_set"] = True

        for attempt in range(30):
            current_value = await current_time_value()
            if current_value == schedule["time_24h"]:
                result["time_set"] = True
                break
            if not current_value or ":" not in current_value:
                result["notes"].append(f"time value unreadable: {current_value}")
                break
            current_hour, current_minute = _time_parts(current_value)
            hour_delta = target_hour - current_hour
            minute_delta = (target_minute - current_minute) // 5
            picker = await open_time_picker()
            if not picker:
                result["notes"].append("time picker did not open")
                await page.evaluate(
                    """({ hourDelta, minuteDelta }) => {
                      const cols = [...document.querySelectorAll(".tiktok-timepicker-time-scroll-container")];
                      const step = (col, delta) => {
                        const direction = delta > 0 ? 32 : -32;
                        for (let index = 0; index < Math.abs(delta); index += 1) {
                          col.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: direction }));
                          col.dispatchEvent(new Event("scroll", { bubbles: true }));
                        }
                      };
                      if (cols.length >= 2) {
                        step(cols[0], hourDelta);
                        step(cols[1], minuteDelta);
                      }
                    }""",
                    {"hourDelta": hour_delta, "minuteDelta": minute_delta},
                )
                await page.wait_for_timeout(500)
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
                continue
            await page.evaluate(
                """({ hourDelta, minuteDelta }) => {
                  const cols = [...document.querySelectorAll(".tiktok-timepicker-time-scroll-container")];
                  const step = (col, delta, multiplier) => {
                    const direction = delta > 0 ? 32 : -32;
                    for (let index = 0; index < Math.abs(delta) * multiplier; index += 1) {
                      col.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: direction }));
                      col.dispatchEvent(new Event("scroll", { bubbles: true }));
                    }
                  };
                  if (cols.length >= 2) {
                    step(cols[0], hourDelta, 1);
                    step(cols[1], minuteDelta, 1);
                  }
                }""",
                {"hourDelta": hour_delta, "minuteDelta": minute_delta},
            )
            row_y = float(picker.get("rowY") or (float(picker["y"]) + max(float(picker["height"]), 224.0) / 2))
            await page.mouse.click(float(picker["x"]) + float(picker["width"]) + 280, max(120.0, row_y))
            await page.wait_for_timeout(700)
            result["notes"].append(f"time adjust attempt {attempt + 1}: {current_value} -> {schedule['time_24h']}")

        result["time_value"] = await current_time_value()
        result["time_set"] = result["time_value"] == schedule["time_24h"]
        result["ok"] = result["schedule_enabled"] and result["date_set"] and result["time_set"]
        return result

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def goto_upload_page() -> dict[str, Any]:
            last_error = ""
            for attempt, url in enumerate([DEFAULT_UPLOAD_URL, DEFAULT_UPLOAD_URL, LEGACY_UPLOAD_URL, DEFAULT_UPLOAD_URL], start=1):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(1200)
                    return {"ok": True, "attempt": attempt, "url": page.url}
                except Exception as exc:  # Playwright raises on some TikTok HTTP response codes.
                    last_error = str(exc)
                    await page.wait_for_timeout(1500 * attempt)
            return {"ok": False, "reason": "upload_navigation_failed", "error": last_error, "target_url": DEFAULT_UPLOAD_URL}

        current_url = page.url.lower()
        if "tiktok.com" not in current_url or "upload" not in current_url or "unavailable" in current_url:
            navigation = await goto_upload_page()
            if not navigation.get("ok"):
                return {"ok": False, "blocked": True, "blocker": "upload_navigation_failed", "navigation": navigation}
        file_inputs = page.locator("input[type='file']")
        blockers = [str(blocker).lower() for blocker in _load_config("ha_strategy.json").get("security_blockers", [])]
        text = ""
        state: dict[str, Any] = {}
        for attempt in range(45):
            with contextlib.suppress(Exception):
                text = (await page.locator("body").inner_text(timeout=5000)).lower()
            for blocker in blockers:
                if blocker and blocker in text:
                    return {"ok": False, "blocked": True, "blocker": blocker, "url": page.url}
            state = await upload_editor_state(page)
            if await file_inputs.count() > 0 or state.get("editorReady"):
                break
            if attempt in {5, 15} and ("tiktokstudio/upload" not in page.url.lower() or "unavailable" in page.url.lower()):
                navigation = await goto_upload_page()
                if not navigation.get("ok"):
                    return {"ok": False, "blocked": True, "blocker": "upload_navigation_failed", "navigation": navigation}
                file_inputs = page.locator("input[type='file']")
                await page.wait_for_timeout(3000)
                continue
            waiting = any(marker in text for marker in ["please wait", "잠시 기다려"])
            login_markers = ("/login" in page.url.lower()) or any(marker in text for marker in ["login", "log in", "로그인"])
            if login_markers and not waiting:
                return {
                    "ok": False,
                    "blocked": True,
                    "needs_login": True,
                    "blocker": "login_required",
                    "url": page.url,
                    "body_sample": text[:500],
                }
            await page.wait_for_timeout(2000)
        if await file_inputs.count() == 0 and not state.get("editorReady"):
            login_markers = ("/login" in page.url.lower()) or any(marker in text for marker in ["login", "log in", "로그인"])
            return {
                "ok": False,
                "blocked": True,
                "needs_login": login_markers,
                "blocker": "login_required" if login_markers else "upload_file_input_missing",
                "url": page.url,
                "body_sample": text[:500],
                "upload_editor_state": state,
            }
        caption = str(job.get("caption") or "")
        caption_probe = caption[:32].strip()
        uploaded_video_reused = bool(int(state.get("captionTargetCount") or 0) > 0)
        prepared_reused = bool(uploaded_video_reused and caption_probe and caption_probe in str(state.get("captionText") or ""))
        if uploaded_video_reused and not prepared_reused:
            return {
                "ok": False,
                "blocked": True,
                "blocker": "prepared_upload_conflict",
                "url": page.url,
                "run_id": job.get("run_id"),
                "caption_probe": caption_probe,
                "upload_editor_state": state,
            }
        if not uploaded_video_reused:
            if await file_inputs.count() == 0:
                return {
                    "ok": False,
                    "blocked": True,
                    "blocker": "upload_file_input_missing",
                    "url": page.url,
                    "body_sample": text[:500],
                    "upload_editor_state": state,
                }
            file_input = file_inputs.first
            await file_input.set_input_files(str(Path(job["mp4_path"]).resolve()), timeout=120000)
        caption_targets = page.locator("[contenteditable='true'], textarea")
        for _ in range(60):
            if await caption_targets.count():
                break
            await page.wait_for_timeout(1000)
        caption_result: dict[str, Any] = {"attempted": False, "matched": False}
        if await caption_targets.count():
            target = caption_targets.first
            for attempt in range(2):
                await target.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.insert_text(caption)
                with contextlib.suppress(Exception):
                    rendered_caption = (await target.inner_text(timeout=3000)).strip()
                    caption_result = {
                        "attempted": True,
                        "matched": rendered_caption == caption.strip(),
                        "rendered_length": len(rendered_caption),
                        "attempt": attempt + 1,
                    }
                    if caption_result["matched"]:
                        break
        evidence = {
            "ok": True,
            "mode": mode,
            "url": page.url,
            "run_id": job.get("run_id"),
            "final_click_performed": False,
            "review_required": True,
            "caption_result": caption_result,
            "uploaded_video_reused": uploaded_video_reused,
            "prepared_upload_reused": prepared_reused,
        }
        aigc_disclosure = await configure_aigc_disclosure(page, job)
        evidence["aigc_disclosure"] = aigc_disclosure
        if mode in {"schedule", "publish"} and not aigc_disclosure.get("ok"):
            evidence["ok"] = False
            evidence["blocked_reason"] = "aigc_disclosure_not_confirmed"
            return evidence
        if mode in {"schedule", "publish"} and not allow_external_post:
            evidence["blocked_reason"] = "posting_gate_env_not_enabled"
            return evidence
        if mode == "schedule":
            ready = await wait_until_upload_ready(page, purpose="schedule")
            evidence["upload_ready"] = ready
            if not ready.get("ok"):
                evidence["ok"] = False
                evidence["blocked_reason"] = "upload_action_not_ready"
                return evidence
            text_after_upload = (await page.locator("body").inner_text(timeout=15000)).lower()
            for blocker in _load_config("ha_strategy.json").get("security_blockers", []):
                if blocker.lower() in text_after_upload:
                    return {"ok": False, "blocked": True, "blocker": blocker, "url": page.url}
            schedule = _schedule_parts(str(job.get("planned_publish_at_local") or ""))
            if not schedule:
                evidence["blocked_reason"] = "missing_planned_publish_at_local"
                return evidence
            schedule_setup = await configure_schedule(page, schedule)
            evidence["schedule_setup"] = schedule_setup
            evidence["scheduled_at"] = schedule.get("iso")
            if not schedule_setup.get("ok"):
                evidence["ok"] = False
                evidence["blocked_reason"] = "schedule_controls_not_configured"
                return evidence
            ready_before_submit = await wait_until_upload_ready(page, purpose="schedule_submit")
            evidence["upload_ready_before_submit"] = ready_before_submit
            if not ready_before_submit.get("ok"):
                evidence["ok"] = False
                evidence["blocked_reason"] = "upload_action_not_ready_before_submit"
                return evidence
            click = await click_best_button(page, ["schedule post", "schedule", "예약 게시", "예약하기", "예약"], purpose="schedule_submit")
            evidence["schedule_click"] = click
            evidence["schedule_click_performed"] = bool(click.get("ok"))
            evidence["review_required"] = not bool(click.get("ok"))
            if click.get("ok"):
                await page.wait_for_timeout(3000)
                confirm = await click_best_button(page, ["지금 예약", "예약 게시", "예약하기", "예약", "Schedule post", "Schedule"], purpose="schedule_confirm")
                evidence["schedule_confirm_click"] = confirm
                if confirm.get("ok"):
                    await page.wait_for_timeout(5000)
                evidence["url_after_schedule"] = page.url
                verification = await verify_studio_content_visible(page, job)
                evidence["schedule_verification"] = verification
                if not verification.get("ok"):
                    evidence["ok"] = False
                    evidence["blocked_reason"] = "schedule_not_visible_in_studio"
                    evidence["review_required"] = True
            else:
                evidence["ok"] = False
                evidence["blocked_reason"] = "unique_schedule_button_not_found"
            return evidence
        if mode == "publish":
            ready = await wait_until_upload_ready(page, purpose="publish")
            evidence["upload_ready"] = ready
            if not ready.get("ok"):
                evidence["ok"] = False
                evidence["blocked_reason"] = "upload_action_not_ready"
                return evidence
            text_after_upload = (await page.locator("body").inner_text(timeout=15000)).lower()
            for blocker in _load_config("ha_strategy.json").get("security_blockers", []):
                if blocker.lower() in text_after_upload:
                    return {"ok": False, "blocked": True, "blocker": blocker, "url": page.url}
            click = await click_best_button(page, ["post now", "post", "게시하기", "게시"], purpose="publish_submit")
            evidence["final_click"] = click
            evidence["final_click_performed"] = bool(click.get("ok"))
            evidence["review_required"] = not bool(click.get("ok"))
            if click.get("ok"):
                await page.wait_for_timeout(3000)
                confirm = await click_best_button(page, ["지금 게시", "게시하기", "게시", "Post now", "Post"], purpose="publish_confirm")
                evidence["publish_confirm_click"] = confirm
                if confirm.get("ok"):
                    await page.wait_for_timeout(5000)
                evidence["published_url"] = page.url
            else:
                evidence["ok"] = False
                evidence["blocked_reason"] = "unique_post_button_not_found"
        return evidence


def prepare_upload(
    manifest_path: Path,
    *,
    mode: str,
    port: int,
    profile_dir: Path,
    dry_run: bool = False,
    schedule_at_local: str | None = None,
) -> dict[str, Any]:
    job = build_upload_job(manifest_path)
    if not job.get("ok"):
        return {"ok": False, "reason": job.get("reason") or "upload_job_not_ready", "job": job}
    if schedule_at_local:
        job["planned_publish_at_local"] = schedule_at_local
    validation = job.get("validation") if isinstance(job.get("validation"), dict) else {}
    if mode in {"schedule", "publish"} and validation.get("publish_ready") is not True:
        return {"ok": False, "reason": "manifest_not_publish_ready", "job": job}
    launch = launch_chrome(port=port, profile_dir=profile_dir)
    if not launch.get("ok"):
        return {"ok": False, "reason": "chrome_launch_failed", "launch": launch, "job": job}
    allow_external_post = os.environ.get("AINO_UPLOAD_AUTOMATION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    if dry_run or mode == "dry-run":
        return {
            "ok": True,
            "dry_run": True,
            "job": job,
            "chrome": launch,
            "posting_gate_enabled": allow_external_post,
            "next": "Run mode=prepare on a logged-in TikTok Chrome profile.",
        }
    import asyncio

    return asyncio.run(_prepare_with_playwright(job, port=port, mode=mode, allow_external_post=allow_external_post))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare AiNo TikTok upload in Chrome.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=["dry-run", "prepare", "schedule", "publish"], default="prepare")
    parser.add_argument("--cdp-port", type=int, default=int(os.environ.get("AINO_CHROME_CDP_PORT", DEFAULT_CDP_PORT)))
    parser.add_argument("--profile-dir", type=Path, default=_default_profile_dir())
    parser.add_argument("--schedule-at", default=None, help="Override planned publish time, ISO local format.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = prepare_upload(
        args.manifest,
        mode=args.mode,
        port=args.cdp_port,
        profile_dir=args.profile_dir,
        dry_run=args.dry_run,
        schedule_at_local=args.schedule_at,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
