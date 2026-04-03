# -*- coding: utf-8 -*-
"""
Sora PC Agent — 집/회사 PC에서 실행하는 경량 에이전트

클라우드 소라에 WebSocket으로 연결하여 원격 명령을 수신/실행합니다.
공유기/방화벽 설정 없이 아웃바운드 연결만 사용합니다.

사용법:
    # 집 PC
    python sora_pc_agent.py --id home-pc --server wss://neo.heoyesol.kr/ws/pc-agent

    # 회사 PC
    python sora_pc_agent.py --id work-pc --server wss://neo.heoyesol.kr/ws/pc-agent

    # 로컬 테스트
    python sora_pc_agent.py --id test-pc --server ws://localhost:7700/ws/pc-agent
"""
import argparse
import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── UTF-8 강제 (Windows cp949 방지) ──
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 로깅 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SoraAgent:%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("pc-agent")

# ── 설정 ──
AGENT_TOKEN = os.getenv("PC_AGENT_TOKEN", "sora-pc-agent-2026")
HEARTBEAT_INTERVAL = 30  # 초
RECONNECT_DELAY = 5  # 초
MAX_OUTPUT_SIZE = 10000  # 바이트
IS_WINDOWS = platform.system() == "Windows"


class PCAgent:
    """클라우드 소라에 연결하여 원격 명령을 실행하는 PC 에이전트."""

    def __init__(self, agent_id: str, server_url: str):
        self.agent_id = agent_id
        self.server_url = server_url
        self.ws = None
        self._running = True

    async def connect(self):
        """WebSocket으로 클라우드 소라에 연결 (자동 재연결)."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets 패키지 필요: pip install websockets")
            sys.exit(1)

        url = f"{self.server_url}?token={AGENT_TOKEN}&agent_id={self.agent_id}"

        while self._running:
            try:
                logger.info(f"소라 클라우드 연결 중... ({self.server_url})")
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    logger.info(f"연결 완료! (agent_id={self.agent_id})")

                    # 하트비트 + 메시지 수신 병렬 실행
                    await asyncio.gather(
                        self._heartbeat_loop(ws),
                        self._receive_loop(ws),
                    )

            except Exception as e:
                logger.warning(f"연결 끊김: {e}. {RECONNECT_DELAY}초 후 재연결...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def _heartbeat_loop(self, ws):
        """주기적 하트비트 전송 (PC 상태 포함)."""
        while True:
            try:
                info = self._collect_system_info()
                await ws.send(json.dumps({
                    "type": "heartbeat",
                    "info": info,
                }))
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except Exception:
                break

    async def _receive_loop(self, ws):
        """명령 수신 및 실행."""
        async for message in ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "heartbeat_ack":
                    continue

                if msg_type == "command":
                    cmd_id = data.get("cmd_id", "")
                    command = data.get("command", "")
                    payload = data.get("payload", {})

                    logger.info(f"명령 수신: [{command}] {str(payload)[:100]}")

                    # 명령 실행 (별도 태스크)
                    result = await self._execute_command(command, payload)

                    # 결과 전송
                    await ws.send(json.dumps({
                        "type": "command_result",
                        "cmd_id": cmd_id,
                        "result": result,
                    }))

            except Exception as e:
                logger.error(f"메시지 처리 오류: {e}")

    async def _execute_command(self, command: str, payload: dict) -> dict:
        """명령 실행 라우터."""
        handlers = {
            # 기본
            "exec": self._cmd_exec,
            "read_file": self._cmd_read_file,
            "write_file": self._cmd_write_file,
            "list_dir": self._cmd_list_dir,
            "system_status": self._cmd_system_status,
            "screenshot": self._cmd_screenshot,
            "clipboard_read": self._cmd_clipboard_read,
            "clipboard_write": self._cmd_clipboard_write,
            "process_list": self._cmd_process_list,
            "kill_process": self._cmd_kill_process,
            "open_app": self._cmd_open_app,
            "find_files": self._cmd_find_files,
            # Claude CLI 제어
            "claude_run": self._cmd_claude_run,
            "claude_chat": self._cmd_claude_chat,
            # Docker 관리
            "docker_ps": self._cmd_docker_ps,
            "docker_logs": self._cmd_docker_logs,
            "docker_exec": self._cmd_docker_exec,
            "docker_restart": self._cmd_docker_restart,
            # Git 작업
            "git_status": self._cmd_git_status,
            "git_pull": self._cmd_git_pull,
            "git_log": self._cmd_git_log,
            # 패키지 관리
            "pip_install": self._cmd_pip_install,
            "npm_install": self._cmd_npm_install,
            # 파일 전송
            "download_url": self._cmd_download_url,
            "upload_file": self._cmd_upload_file,
            # 웹 (SearXNG + Crawl4AI)
            "web_search": self._cmd_web_search,
            "web_crawl": self._cmd_web_crawl,
            # CI/CD
            "vercel_deploy": self._cmd_vercel_deploy,
            "npm_build": self._cmd_npm_build,
            # Git 확장
            "git_commit": self._cmd_git_commit,
            "git_push": self._cmd_git_push,
            "git_clone": self._cmd_git_clone,
            # 다중 명령
            "batch_exec": self._cmd_batch_exec,
        }

        handler = handlers.get(command)
        if not handler:
            return {"error": f"알 수 없는 명령: {command}", "available": list(handlers.keys())}

        try:
            return await asyncio.to_thread(handler, payload)
        except Exception as e:
            return {"error": str(e)[:500]}

    # ── 명령 핸들러들 ──

    def _cmd_exec(self, payload: dict) -> dict:
        """셸 명령 실행."""
        command = payload.get("command", "")
        timeout = min(payload.get("timeout", 60), 300)

        # 위험 명령 차단
        dangerous = [
            "format c:", "format d:", "del /s /q c:\\", "del /s /q d:\\",
            "remove-item -recurse c:\\", "remove-item -recurse d:\\",
            "rm -rf /", "rm -rf /*", "mkfs.", "dd if=/dev",
            "stop-computer", "shutdown /s", "shutdown -s", "restart-computer",
            "reg delete", "bcdedit", "diskpart", "cipher /w",
            "powershell -enc", "powershell -encodedcommand",
            "curl|sh", "curl|bash", "wget|sh", "wget|bash",
            "> /dev/sda", "chmod 777 /",
        ]
        cmd_lower = command.lower().replace(" ", "")
        for d in dangerous:
            if d.lower().replace(" ", "") in cmd_lower:
                return {"error": f"위험 명령 차단됨: {d}"}

        shell = ["powershell", "-NoProfile", "-Command", command] if IS_WINDOWS \
            else ["bash", "-c", command]

        try:
            result = subprocess.run(
                shell, capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[-MAX_OUTPUT_SIZE:],
                "stderr": result.stderr[-3000:],
                "shell": "powershell" if IS_WINDOWS else "bash",
            }
        except subprocess.TimeoutExpired:
            return {"error": f"타임아웃 ({timeout}초)"}

    def _cmd_read_file(self, payload: dict) -> dict:
        """파일 읽기."""
        path = Path(payload.get("path", ""))
        if not path.exists():
            return {"error": f"파일 없음: {path}"}
        if not path.is_file():
            return {"error": f"파일이 아님: {path}"}
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > MAX_OUTPUT_SIZE:
                content = content[:MAX_OUTPUT_SIZE] + "\n...(잘림)"
            return {"path": str(path), "content": content, "size": path.stat().st_size}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_write_file(self, payload: dict) -> dict:
        """파일 쓰기 (시스템 경로 보호)."""
        path = Path(payload.get("path", ""))
        content = payload.get("content", "")
        # 시스템 보호 경로 차단
        blocked = ["C:\\Windows", "C:\\Program Files", "/etc", "/usr", "/bin", "/sbin", "/boot"]
        for b in blocked:
            if str(path).lower().startswith(b.lower()):
                return {"error": f"보호 경로 접근 차단: {b}"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "success", "path": str(path), "bytes": len(content.encode("utf-8"))}

    def _cmd_list_dir(self, payload: dict) -> dict:
        """디렉토리 목록."""
        path = Path(payload.get("path", "."))
        if not path.exists():
            return {"error": f"경로 없음: {path}"}
        items = []
        for child in sorted(path.iterdir()):
            info = {"name": child.name, "type": "dir" if child.is_dir() else "file"}
            if child.is_file():
                info["size"] = child.stat().st_size
            items.append(info)
            if len(items) >= 200:
                break
        return {"path": str(path), "items": items}

    def _cmd_system_status(self, payload: dict) -> dict:
        """시스템 상태 (CPU, RAM, 디스크, 프로세스)."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk_parts = psutil.disk_partitions()
            disks = {}
            for part in disk_parts:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks[part.mountpoint] = {
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": usage.percent,
                    }
                except Exception:
                    pass

            battery = None
            try:
                bat = psutil.sensors_battery()
                if bat:
                    battery = {"percent": bat.percent, "charging": bat.power_plugged}
            except Exception:
                pass

            return {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 1),
                    "used_gb": round(mem.used / (1024**3), 1),
                    "percent": mem.percent,
                },
                "disks": disks,
                "battery": battery,
                "process_count": len(psutil.pids()),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }
        except ImportError:
            return {"error": "psutil 미설치: pip install psutil"}

    def _cmd_screenshot(self, payload: dict) -> dict:
        """스크린샷 캡처 → base64 반환."""
        try:
            import mss
            import base64
            from io import BytesIO

            with mss.mss() as sct:
                monitor = sct.monitors[0]  # 전체 화면
                img = sct.grab(monitor)

                # PNG → base64
                from PIL import Image
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

                # 리사이즈 (전송 크기 절감)
                max_width = payload.get("max_width", 1280)
                if pil_img.width > max_width:
                    ratio = max_width / pil_img.width
                    new_size = (max_width, int(pil_img.height * ratio))
                    pil_img = pil_img.resize(new_size, Image.LANCZOS)

                buf = BytesIO()
                pil_img.save(buf, format="JPEG", quality=payload.get("quality", 75))
                b64 = base64.b64encode(buf.getvalue()).decode()

                return {
                    "status": "success",
                    "image_base64": b64,
                    "width": pil_img.width,
                    "height": pil_img.height,
                    "size_kb": round(len(b64) * 3 / 4 / 1024, 1),
                }
        except ImportError as e:
            return {"error": f"스크린캡처 패키지 필요: {e}. pip install mss Pillow"}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_clipboard_read(self, payload: dict) -> dict:
        """클립보드 읽기."""
        try:
            import pyperclip
            content = pyperclip.paste()
            return {"content": content[:MAX_OUTPUT_SIZE]}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_clipboard_write(self, payload: dict) -> dict:
        """클립보드 쓰기."""
        try:
            import pyperclip
            text = payload.get("text", "")
            pyperclip.copy(text)
            return {"status": "success", "length": len(text)}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_process_list(self, payload: dict) -> dict:
        """실행 중 프로세스 목록."""
        try:
            import psutil
            filter_name = payload.get("filter", "").lower()
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    info = p.info
                    name = info.get('name', '')
                    if filter_name and filter_name not in name.lower():
                        continue
                    mem = info.get('memory_info')
                    procs.append({
                        "pid": info['pid'],
                        "name": name,
                        "memory_mb": round(mem.rss / (1024**2), 1) if mem else 0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x.get("memory_mb", 0), reverse=True)
            return {"count": len(procs), "processes": procs[:50]}
        except ImportError:
            return {"error": "psutil 미설치"}

    def _cmd_kill_process(self, payload: dict) -> dict:
        """프로세스 종료."""
        try:
            import psutil
            pid = payload.get("pid")
            name = payload.get("name", "")
            killed = []

            if pid:
                p = psutil.Process(pid)
                p.terminate()
                killed.append(pid)
            elif name:
                for p in psutil.process_iter(['pid', 'name']):
                    if name.lower() in (p.info['name'] or '').lower():
                        p.terminate()
                        killed.append(p.info['pid'])

            return {"killed_pids": killed, "count": len(killed)}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_open_app(self, payload: dict) -> dict:
        """앱/파일 열기."""
        target = payload.get("target", "")
        if not target:
            return {"error": "target 필수"}
        try:
            if IS_WINDOWS:
                os.startfile(target)
            else:
                subprocess.Popen(["xdg-open", target])
            return {"status": "success", "target": target}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_find_files(self, payload: dict) -> dict:
        """파일 검색."""
        directory = payload.get("directory", ".")
        pattern = payload.get("pattern", "*")
        max_depth = payload.get("max_depth", 5)

        p = Path(directory)
        if not p.exists():
            return {"error": f"경로 없음: {directory}"}

        results = []
        skip = {"__pycache__", "node_modules", ".git", ".next", "venv"}
        for match in p.rglob(pattern):
            rel = match.relative_to(p)
            if len(rel.parts) > max_depth:
                continue
            if set(rel.parts) & skip:
                continue
            results.append({
                "path": str(match),
                "type": "dir" if match.is_dir() else "file",
                "size": match.stat().st_size if match.is_file() else None,
            })
            if len(results) >= 100:
                break

        return {"directory": directory, "pattern": pattern, "found": len(results), "results": results}

    # ── Claude CLI 제어 ──

    def _cmd_claude_run(self, payload: dict) -> dict:
        """Claude CLI로 단일 프롬프트 실행 (비대화형)."""
        prompt = payload.get("prompt", "")
        cwd = payload.get("cwd", ".")
        timeout = min(payload.get("timeout", 120), 300)
        if not prompt:
            return {"error": "prompt 필수"}
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--no-input"],
                capture_output=True, text=True, timeout=timeout,
                cwd=cwd, encoding="utf-8", errors="replace",
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[-MAX_OUTPUT_SIZE:],
                "stderr": result.stderr[-2000:],
            }
        except FileNotFoundError:
            return {"error": "claude CLI 미설치. npm install -g @anthropic-ai/claude-code"}
        except subprocess.TimeoutExpired:
            return {"error": f"타임아웃 ({timeout}초)"}

    def _cmd_claude_chat(self, payload: dict) -> dict:
        """Claude CLI 대화 세션에 메시지 전송."""
        message = payload.get("message", "")
        session_id = payload.get("session_id", "")
        cwd = payload.get("cwd", ".")
        timeout = min(payload.get("timeout", 120), 300)
        if not message:
            return {"error": "message 필수"}
        cmd = ["claude"]
        if session_id:
            cmd.extend(["--resume", session_id])
        cmd.extend(["-p", message, "--no-input"])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                cwd=cwd, encoding="utf-8", errors="replace",
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[-MAX_OUTPUT_SIZE:],
                "stderr": result.stderr[-2000:],
            }
        except FileNotFoundError:
            return {"error": "claude CLI 미설치"}
        except subprocess.TimeoutExpired:
            return {"error": f"타임아웃 ({timeout}초)"}

    # ── Docker 관리 ──

    def _cmd_docker_ps(self, payload: dict) -> dict:
        """Docker 컨테이너 목록."""
        try:
            docker = "sudo docker" if not IS_WINDOWS else "docker"
            result = subprocess.run(
                f"{docker} ps -a --format '{{{{.Names}}}} {{{{.Status}}}} {{{{.Image}}}} {{{{.Ports}}}}'",
                shell=True, capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            return {"containers": lines, "count": len(lines)}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_docker_logs(self, payload: dict) -> dict:
        """Docker 컨테이너 로그."""
        name = payload.get("name", "")
        tail = min(payload.get("tail", 30), 100)
        if not name:
            return {"error": "name 필수"}
        try:
            docker = "sudo docker" if not IS_WINDOWS else "docker"
            result = subprocess.run(
                f"{docker} logs {name} --tail {tail}",
                shell=True, capture_output=True, text=True, timeout=10,
            )
            return {"logs": (result.stdout + result.stderr)[-MAX_OUTPUT_SIZE:]}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_docker_exec(self, payload: dict) -> dict:
        """Docker 컨테이너 내부 명령 실행."""
        name = payload.get("name", "")
        command = payload.get("command", "")
        if not name or not command:
            return {"error": "name, command 필수"}
        # 컨테이너 이름 검증 (영숫자, -, _ 만 허용)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return {"error": f"잘못된 컨테이너 이름: {name}"}
        try:
            docker_cmd = ["sudo", "docker", "exec", name] if not IS_WINDOWS else ["docker", "exec", name]
            docker_cmd.extend(["sh", "-c", command])
            result = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=30,
            )
            return {"stdout": result.stdout[-MAX_OUTPUT_SIZE:], "stderr": result.stderr[-2000:]}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_docker_restart(self, payload: dict) -> dict:
        """Docker 컨테이너 재시작."""
        name = payload.get("name", "")
        if not name:
            return {"error": "name 필수"}
        try:
            docker = "sudo docker" if not IS_WINDOWS else "docker"
            result = subprocess.run(f"{docker} restart {name}", shell=True, capture_output=True, text=True, timeout=30)
            return {"status": "restarted" if result.returncode == 0 else "failed", "output": result.stdout.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ── Git 작업 ──

    def _cmd_git_status(self, payload: dict) -> dict:
        """Git 상태 확인."""
        cwd = payload.get("cwd", ".")
        try:
            result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=10, cwd=cwd)
            branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5, cwd=cwd)
            return {"branch": branch.stdout.strip(), "changes": result.stdout.strip(), "clean": not result.stdout.strip()}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_git_pull(self, payload: dict) -> dict:
        """Git pull."""
        cwd = payload.get("cwd", ".")
        try:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=30, cwd=cwd)
            return {"output": result.stdout.strip(), "error": result.stderr.strip() if result.returncode != 0 else None}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_git_log(self, payload: dict) -> dict:
        """Git 최근 커밋 로그."""
        cwd = payload.get("cwd", ".")
        n = min(payload.get("n", 5), 20)
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline", "--no-decorate"],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            return {"commits": result.stdout.strip().split("\n")}
        except Exception as e:
            return {"error": str(e)}

    # ── 패키지 관리 ──

    def _cmd_pip_install(self, payload: dict) -> dict:
        """pip 패키지 설치."""
        package = payload.get("package", "")
        if not package:
            return {"error": "package 필수"}
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=120,
            )
            return {"status": "installed" if result.returncode == 0 else "failed", "output": result.stdout[-1000:]}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_npm_install(self, payload: dict) -> dict:
        """npm 패키지 설치."""
        package = payload.get("package", "")
        cwd = payload.get("cwd", ".")
        global_flag = payload.get("global", False)
        cmd = ["npm", "install"]
        if global_flag:
            cmd.append("-g")
        if package:
            cmd.append(package)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=cwd)
            return {"status": "installed" if result.returncode == 0 else "failed", "output": result.stdout[-1000:]}
        except Exception as e:
            return {"error": str(e)}

    # ── 파일 다운로드 ──

    def _cmd_download_url(self, payload: dict) -> dict:
        """URL에서 파일 다운로드."""
        url = payload.get("url", "")
        dest = payload.get("dest", "")
        if not url or not dest:
            return {"error": "url, dest 필수"}
        try:
            import urllib.request
            urllib.request.urlretrieve(url, dest)
            return {"status": "downloaded", "path": dest, "size": os.path.getsize(dest)}
        except Exception as e:
            return {"error": str(e)}

    # ── 파일 업로드 (Base64 경유) ──

    def _cmd_upload_file(self, payload: dict) -> dict:
        """Base64 인코딩된 파일을 저장."""
        import base64
        path = payload.get("path", "")
        data_b64 = payload.get("data", "")
        if not path or not data_b64:
            return {"error": "path, data 필수"}
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(base64.b64decode(data_b64))
            return {"status": "saved", "path": path, "size": os.path.getsize(path)}
        except Exception as e:
            return {"error": str(e)}

    # ── 웹 검색 (SearXNG) ──

    def _cmd_web_search(self, payload: dict) -> dict:
        """SearXNG로 웹 검색."""
        query = payload.get("query", "")
        if not query:
            return {"error": "query 필수"}
        try:
            import urllib.request, json as _json
            # 로컬 SearXNG 또는 서버의 SearXNG
            for port in [8888, 8889, 8890]:
                try:
                    url = f"http://127.0.0.1:{port}/search?q={urllib.parse.quote(query)}&format=json&categories=general&language=ko"
                    req = urllib.request.Request(url, headers={"User-Agent": "Sora/3.0"})
                    resp = urllib.request.urlopen(req, timeout=10)
                    data = _json.loads(resp.read())
                    results = [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:200]} for r in data.get("results", [])[:10]]
                    return {"query": query, "results": results, "count": len(results)}
                except Exception:
                    continue
            return {"error": "SearXNG 서버 연결 실패"}
        except Exception as e:
            return {"error": str(e)}

    # ── 웹 크롤링 (Crawl4AI) ──

    def _cmd_web_crawl(self, payload: dict) -> dict:
        """Crawl4AI로 웹페이지 크롤링."""
        url = payload.get("url", "")
        if not url:
            return {"error": "url 필수"}
        try:
            import urllib.request, json as _json
            req_data = _json.dumps({"urls": url, "priority": 5}).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:11235/crawl",
                data=req_data,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = _json.loads(resp.read())
            result = data.get("result", data)
            if isinstance(result, dict):
                return {"url": url, "markdown": str(result.get("markdown", result.get("text", "")))[:MAX_OUTPUT_SIZE]}
            return {"url": url, "content": str(result)[:MAX_OUTPUT_SIZE]}
        except Exception as e:
            return {"error": str(e)}

    # ── CI/CD ──

    def _cmd_vercel_deploy(self, payload: dict) -> dict:
        """Vercel 프로덕션 배포."""
        cwd = payload.get("cwd", ".")
        try:
            result = subprocess.run(
                ["npx", "vercel", "--prod", "--yes"],
                capture_output=True, text=True, timeout=180, cwd=cwd,
            )
            return {"status": "deployed" if result.returncode == 0 else "failed", "output": result.stdout[-2000:], "error": result.stderr[-500:] if result.returncode != 0 else None}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_npm_build(self, payload: dict) -> dict:
        """npm run build."""
        cwd = payload.get("cwd", ".")
        try:
            result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True, timeout=120, cwd=cwd)
            return {"status": "success" if result.returncode == 0 else "failed", "output": result.stdout[-2000:], "error": result.stderr[-500:] if result.returncode != 0 else None}
        except Exception as e:
            return {"error": str(e)}

    # ── Git 확장 ──

    def _cmd_git_commit(self, payload: dict) -> dict:
        """Git commit."""
        cwd = payload.get("cwd", ".")
        message = payload.get("message", "auto commit by Sora")
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10, cwd=cwd)
            result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, timeout=10, cwd=cwd)
            return {"status": "committed" if result.returncode == 0 else "nothing to commit", "output": result.stdout.strip()}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_git_push(self, payload: dict) -> dict:
        """Git push."""
        cwd = payload.get("cwd", ".")
        try:
            result = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=30, cwd=cwd)
            return {"status": "pushed" if result.returncode == 0 else "failed", "output": (result.stdout + result.stderr).strip()[-1000:]}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_git_clone(self, payload: dict) -> dict:
        """Git clone."""
        repo = payload.get("repo", "")
        dest = payload.get("dest", "")
        if not repo:
            return {"error": "repo 필수"}
        cmd = ["git", "clone", "--depth", "1", repo]
        if dest:
            cmd.append(dest)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {"status": "cloned" if result.returncode == 0 else "failed", "output": (result.stdout + result.stderr).strip()[-500:]}
        except Exception as e:
            return {"error": str(e)}

    # ── 다중 명령 (병렬 아님, 순차 배치) ──

    def _cmd_batch_exec(self, payload: dict) -> dict:
        """여러 셸 명령을 순차 실행."""
        commands = payload.get("commands", [])
        if not commands:
            return {"error": "commands 배열 필수"}
        results = []
        shell = ["powershell", "-NoProfile", "-Command"] if IS_WINDOWS else ["bash", "-c"]
        for cmd in commands[:10]:  # 최대 10개
            try:
                r = subprocess.run(shell + [cmd] if IS_WINDOWS else ["bash", "-c", cmd],
                    capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
                results.append({"cmd": cmd, "exit": r.returncode, "out": r.stdout.strip()[-500:]})
            except Exception as e:
                results.append({"cmd": cmd, "error": str(e)[:100]})
        return {"executed": len(results), "results": results}

    # ── 시스템 정보 수집 (하트비트용) ──

    def _collect_system_info(self) -> dict:
        """가벼운 시스템 정보 (하트비트 페이로드)."""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            import psutil
            info["cpu_percent"] = psutil.cpu_percent(interval=0)
            info["memory_percent"] = psutil.virtual_memory().percent
        except Exception:
            pass
        return info


# ── 엔트리포인트 ──

def main():
    parser = argparse.ArgumentParser(description="Sora PC Agent — 원격 PC 제어 에이전트")
    parser.add_argument("--id", required=True, help="PC 식별자 (예: home-pc, work-pc)")
    parser.add_argument("--server", default="wss://neo.heoyesol.kr/ws/pc-agent",
                        help="소라 클라우드 WebSocket URL")
    parser.add_argument("--token", default=None, help="인증 토큰 (기본: 환경변수 PC_AGENT_TOKEN)")
    args = parser.parse_args()

    if args.token:
        global AGENT_TOKEN
        AGENT_TOKEN = args.token

    agent = PCAgent(agent_id=args.id, server_url=args.server)

    print(f"\n=== Sora PC Agent v1.0 ===")
    print(f"  ID:     {args.id}")
    print(f"  Server: {args.server}")
    print(f"  OS:     {platform.system()} {platform.release()}")
    print(f"===========================\n")

    try:
        asyncio.run(agent.connect())
    except KeyboardInterrupt:
        print("\n소라 PC Agent 종료.")


if __name__ == "__main__":
    main()
