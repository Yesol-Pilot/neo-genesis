# -*- coding: utf-8 -*-
"""On-demand ComfyUI tools.

ComfyUI is a GPU worker, not a resident desktop service. Tool calls start it
only when needed, bind it to localhost by default, and stop it after a
generation when this module started the process.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import random
import subprocess
import time
from typing import Any, Iterator
import urllib.error
import urllib.parse
import urllib.request
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output" / "comfyui"
PID_FILE = LOG_DIR / "comfyui-on-demand.pid"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8188
DEFAULT_TIMEOUT_SEC = 300
_DEFAULT_NEGATIVE = (
    "low quality, blurry, distorted, watermark, text artifacts, bad anatomy, "
    "extra fingers, malformed hands"
)
_NSFW_NEGATIVE_TAGS = "minor, child, underage, non-consensual, illegal content"


def _host() -> str:
    return os.environ.get("COMFYUI_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST


def _port() -> int:
    return int(os.environ.get("COMFYUI_PORT", str(DEFAULT_PORT)))


def _root() -> Path:
    return Path(os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI"))


def _python_exe() -> str:
    configured = os.environ.get("COMFYUI_PYTHON", "").strip()
    if configured:
        return configured
    venv_python = _root() / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    conda_python = Path.home() / "miniconda3" / "python.exe"
    if conda_python.exists():
        return str(conda_python)
    return "python.exe" if os.name == "nt" else "python"


def _api_base(host: str | None = None, port: int | None = None) -> str:
    return f"http://{host or _host()}:{port or _port()}"


def _request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5,
) -> Any:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        _api_base() + path,
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = res.read()
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def _is_comfyui_running() -> bool:
    try:
        _request_json("/system_stats", timeout=2)
        return True
    except Exception:
        return False


def _wait_for_ready(timeout_sec: int) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _is_comfyui_running():
            return True
        time.sleep(1)
    return False


def _port_owner_pid(port: int) -> int | None:
    if os.name == "nt":
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                if parts[1].rsplit(":", 1)[-1] == str(port):
                    try:
                        return int(parts[-1])
                    except ValueError:
                        return None
        return None

    proc = subprocess.run(
        ["sh", "-lc", f"lsof -ti tcp:{port} -sTCP:LISTEN | head -n 1"],
        capture_output=True,
        text=True,
        check=False,
    )
    value = proc.stdout.strip()
    return int(value) if value.isdigit() else None


def _queue_empty() -> bool:
    try:
        queue = _request_json("/queue", timeout=5)
    except Exception:
        return True
    return not queue.get("queue_running") and not queue.get("queue_pending")


def _start_comfyui_process() -> subprocess.Popen:
    root = _root()
    main_py = root / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"ComfyUI main.py not found: {main_py}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout = open(LOG_DIR / "comfyui-on-demand.log", "ab")
    stderr = open(LOG_DIR / "comfyui-on-demand.err.log", "ab")
    args = [
        _python_exe(),
        str(main_py),
        "--listen",
        _host(),
        "--port",
        str(_port()),
    ]
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        args,
        cwd=str(root),
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    PID_FILE.write_text(str(proc.pid), encoding="ascii")
    return proc


def _stop_pid(pid: int, *, force: bool = False) -> bool:
    if pid <= 0:
        return False
    deadline = time.monotonic() + 10
    if os.name == "nt":
        args = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            args.append("/F")
        subprocess.run(args, capture_output=True, text=True, check=False)
        while time.monotonic() < deadline:
            if _port_owner_pid(_port()) != pid:
                return True
            time.sleep(0.5)
        if _port_owner_pid(_port()) == pid and not force:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, check=False)
            while time.monotonic() < deadline + 5:
                if _port_owner_pid(_port()) != pid:
                    return True
                time.sleep(0.5)
        return _port_owner_pid(_port()) != pid

    subprocess.run(["kill", str(pid)], capture_output=True, text=True, check=False)
    while time.monotonic() < deadline:
        if _port_owner_pid(_port()) != pid:
            return True
        time.sleep(0.5)
    return _port_owner_pid(_port()) != pid


@contextmanager
def managed_comfyui(*, keep_alive: bool = False, timeout_sec: int = 120) -> Iterator[None]:
    started_here = False
    if not _is_comfyui_running():
        _start_comfyui_process()
        started_here = True
        if not _wait_for_ready(timeout_sec):
            raise TimeoutError(f"ComfyUI did not become ready within {timeout_sec}s")
    try:
        yield
    finally:
        if started_here and not keep_alive:
            comfyui_stop(force=False)


def comfyui_status() -> str:
    """Return local ComfyUI status, queue state, and listener PID."""
    pid = _port_owner_pid(_port())
    try:
        stats = _request_json("/system_stats", timeout=3)
        queue = _request_json("/queue", timeout=3)
        running = True
    except Exception as exc:
        stats = {"error": str(exc)}
        queue = {}
        running = False
    return json.dumps(
        {
            "running": running,
            "host": _host(),
            "port": _port(),
            "pid": pid,
            "queue": queue,
            "system": stats,
            "policy": "on_demand_stop_after_use",
        },
        ensure_ascii=False,
        default=str,
    )


def comfyui_start(timeout_sec: int = 120) -> str:
    """Start ComfyUI hidden on localhost if it is not already running."""
    if _is_comfyui_running():
        return json.dumps({"status": "already_running", "pid": _port_owner_pid(_port())}, ensure_ascii=False)
    proc = _start_comfyui_process()
    if not _wait_for_ready(timeout_sec):
        return json.dumps({"status": "timeout", "pid": proc.pid, "timeout_sec": timeout_sec}, ensure_ascii=False)
    return json.dumps({"status": "started", "pid": proc.pid, "host": _host(), "port": _port()}, ensure_ascii=False)


def comfyui_stop(force: bool = False) -> str:
    """Stop local ComfyUI if the queue is empty, or force-stop when requested."""
    pid = _port_owner_pid(_port())
    if not pid:
        return json.dumps({"status": "not_running"}, ensure_ascii=False)
    if not force and not _queue_empty():
        return json.dumps({"status": "busy", "pid": pid, "message": "queue is not empty"}, ensure_ascii=False)
    stopped = _stop_pid(pid, force=force)
    if stopped and PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)
    return json.dumps({"status": "stopped" if stopped else "failed", "pid": pid}, ensure_ascii=False)


def comfyui_list_models() -> str:
    """List available checkpoint names from ComfyUI."""
    with managed_comfyui(keep_alive=True):
        info = _request_json("/object_info/CheckpointLoaderSimple", timeout=10)
    required = info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
    values = required.get("ckpt_name", [[]])[0]
    return json.dumps({"checkpoints": values}, ensure_ascii=False)


def _select_checkpoint() -> str:
    configured = os.environ.get("COMFYUI_CHECKPOINT", "").strip()
    if configured:
        return configured
    info = _request_json("/object_info/CheckpointLoaderSimple", timeout=10)
    required = info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
    values = required.get("ckpt_name", [[]])[0]
    if not values:
        raise RuntimeError("No ComfyUI checkpoints are available")
    return str(values[0])


def _build_basic_workflow(
    positive_prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    seed: int,
) -> dict[str, Any]:
    if seed < 0:
        seed = random.randint(0, 2**63 - 1)
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": _select_checkpoint()},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt or _DEFAULT_NEGATIVE, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": int(width), "height": int(height), "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": int(steps),
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "neo_comfyui", "images": ["6", 0]},
        },
    }


def _download_history_images(history: dict[str, Any]) -> list[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for node in history.get("outputs", {}).values():
        for image in node.get("images", []):
            query = urllib.parse.urlencode(
                {
                    "filename": image.get("filename", ""),
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
            )
            url = _api_base() + "/view?" + query
            suffix = Path(str(image.get("filename") or "image.png")).suffix or ".png"
            target = OUTPUT_DIR / f"{uuid.uuid4().hex}{suffix}"
            with urllib.request.urlopen(url, timeout=30) as res:
                target.write_bytes(res.read())
            paths.append(str(target))
    return paths


def comfyui_generate_image(
    positive_prompt: str,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 768,
    steps: int = 25,
    seed: int = -1,
    send_telegram: bool = False,
    keep_alive: bool = False,
) -> str:
    """Generate one image through ComfyUI, stopping the worker if this call started it."""
    try:
        with managed_comfyui(keep_alive=keep_alive):
            workflow = _build_basic_workflow(
                positive_prompt,
                negative_prompt or _DEFAULT_NEGATIVE,
                width,
                height,
                steps,
                seed,
            )
            client_id = str(uuid.uuid4())
            queued = _request_json("/prompt", method="POST", payload={"prompt": workflow, "client_id": client_id}, timeout=10)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI did not return prompt_id: {queued}")
            deadline = time.monotonic() + DEFAULT_TIMEOUT_SEC
            history = None
            while time.monotonic() < deadline:
                all_history = _request_json(f"/history/{prompt_id}", timeout=10)
                history = all_history.get(prompt_id)
                if history:
                    break
                time.sleep(2)
            if not history:
                raise TimeoutError(f"ComfyUI generation timed out after {DEFAULT_TIMEOUT_SEC}s")
            image_paths = _download_history_images(history)
            if send_telegram and image_paths:
                _send_telegram_photo(image_paths[0], f"ComfyUI: {positive_prompt[:80]}")
            return json.dumps(
                {
                    "status": "success",
                    "image_path": image_paths[0] if image_paths else "",
                    "image_paths": image_paths,
                    "prompt_id": prompt_id,
                    "provider": "local_comfyui",
                    "lifecycle": "stopped_after_use" if not keep_alive else "kept_alive",
                },
                ensure_ascii=False,
            )
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc), "provider": "local_comfyui"}, ensure_ascii=False)


def _translate_prompt(user_message: str) -> tuple[str, bool, bool]:
    text = user_message.strip()
    lowered = text.lower()
    nsfw_terms = ("nsfw", "adult", "nude", "sexy", "sensual", "노출", "성인")
    anime_terms = ("anime", "manga", "webtoon", "애니", "만화", "캐릭터")
    is_nsfw = any(term in lowered for term in nsfw_terms)
    use_anime = any(term in lowered for term in anime_terms)
    style = "anime illustration, clean line art" if use_anime else "high quality digital illustration"
    return f"{text}, {style}", is_nsfw, use_anime


def _send_telegram_photo(image_path: str, caption: str = "") -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or not image_path:
        return False
    try:
        import requests

        with open(image_path, "rb") as f:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f},
                timeout=30,
            )
        return response.ok
    except Exception:
        return False


TOOLS = [
    comfyui_generate_image,
    comfyui_start,
    comfyui_stop,
    comfyui_status,
    comfyui_list_models,
]
