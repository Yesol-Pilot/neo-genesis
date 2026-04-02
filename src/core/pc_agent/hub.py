# -*- coding: utf-8 -*-
"""
PC Agent Hub — 클라우드 소라가 원격 PC를 통제하는 중앙 허브

각 PC에서 실행되는 sora_pc_agent.py가 이 허브에 WebSocket으로 연결합니다.
소라 엔진이 PC 명령을 보내면 허브가 해당 PC 에이전트로 중계합니다.

아키텍처:
    PC Agent (집/회사) ──WebSocket──▶ Hub ◀── SoraEngine (도구 호출)
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from starlette.websockets import WebSocketState

logger = logging.getLogger("neo.pc_agent.hub")

# ── 인증 토큰 (환경변수) ──
PC_AGENT_TOKEN = os.getenv("PC_AGENT_TOKEN", "sora-pc-agent-2026")

# ── 연결된 PC 에이전트 관리 ──
_connected_agents: dict[str, dict] = {}
# 구조: { "home-pc": { "ws": WebSocket, "info": {...}, "connected_at": "...", "last_heartbeat": "..." } }

# 명령 응답 대기용 Future 맵
_pending_commands: dict[str, asyncio.Future] = {}

router = APIRouter()


def get_connected_agents() -> dict:
    """현재 연결된 PC 에이전트 목록 반환 (도구 모듈에서 참조)."""
    result = {}
    for agent_id, agent in _connected_agents.items():
        result[agent_id] = {
            "connected_at": agent.get("connected_at", ""),
            "last_heartbeat": agent.get("last_heartbeat", ""),
            "info": agent.get("info", {}),
            "online": agent["ws"].client_state == WebSocketState.CONNECTED,
        }
    return result


async def send_command(agent_id: str, command_type: str, payload: dict, timeout: float = 60.0) -> dict:
    """특정 PC 에이전트에 명령을 전송하고 결과를 기다립니다.

    Args:
        agent_id: PC 식별자 (예: "home-pc", "work-pc")
        command_type: 명령 유형 (예: "exec", "read_file", "screenshot", "system_status")
        payload: 명령 데이터
        timeout: 응답 대기 시간 (초)

    Returns:
        에이전트 응답 dict
    """
    if agent_id not in _connected_agents:
        available = list(_connected_agents.keys())
        return {"error": f"PC '{agent_id}' 미연결. 연결된 PC: {available}"}

    agent = _connected_agents[agent_id]
    ws = agent["ws"]

    if ws.client_state != WebSocketState.CONNECTED:
        del _connected_agents[agent_id]
        return {"error": f"PC '{agent_id}' 연결이 끊어졌습니다."}

    # 고유 명령 ID 생성
    cmd_id = f"cmd-{agent_id}-{int(time.time()*1000)}"

    # Future 생성 (응답 대기용)
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _pending_commands[cmd_id] = future

    try:
        # 명령 전송
        await ws.send_json({
            "type": "command",
            "cmd_id": cmd_id,
            "command": command_type,
            "payload": payload,
        })

        # 응답 대기
        result = await asyncio.wait_for(future, timeout=timeout)
        return result

    except asyncio.TimeoutError:
        return {"error": f"PC '{agent_id}' 응답 시간 초과 ({timeout}초)"}
    except Exception as e:
        return {"error": f"명령 전송 실패: {str(e)[:200]}"}
    finally:
        _pending_commands.pop(cmd_id, None)


# ── WebSocket 엔드포인트: PC Agent 연결 ──

@router.websocket("/ws/pc-agent")
async def pc_agent_websocket(ws: WebSocket, token: str = Query(""), agent_id: str = Query("")):
    """PC Agent가 연결하는 WebSocket 엔드포인트.

    쿼리 파라미터:
        token: 인증 토큰 (PC_AGENT_TOKEN과 일치해야 함)
        agent_id: PC 식별자 (예: "home-pc", "work-pc")
    """
    # 인증
    if token != PC_AGENT_TOKEN:
        await ws.close(code=4001, reason="인증 실패")
        return

    if not agent_id:
        await ws.close(code=4002, reason="agent_id 필수")
        return

    await ws.accept()
    logger.info(f"[PCHub] PC Agent 연결: {agent_id}")

    # 기존 연결 교체
    if agent_id in _connected_agents:
        old_ws = _connected_agents[agent_id]["ws"]
        try:
            await old_ws.close(code=4003, reason="새 연결로 교체")
        except Exception:
            pass

    _connected_agents[agent_id] = {
        "ws": ws,
        "info": {},
        "connected_at": datetime.now().isoformat(),
        "last_heartbeat": datetime.now().isoformat(),
    }

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "heartbeat":
                # 하트비트 응답
                _connected_agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
                _connected_agents[agent_id]["info"] = data.get("info", {})
                await ws.send_json({"type": "heartbeat_ack"})

            elif msg_type == "command_result":
                # 명령 실행 결과
                cmd_id = data.get("cmd_id", "")
                if cmd_id in _pending_commands:
                    future = _pending_commands[cmd_id]
                    if not future.done():
                        future.set_result(data.get("result", {}))

            elif msg_type == "event":
                # PC에서 자발적으로 보내는 이벤트 (예: 에러 감지, 디스크 부족 등)
                logger.info(f"[PCHub] PC '{agent_id}' 이벤트: {data.get('event', 'unknown')}")

    except WebSocketDisconnect:
        logger.info(f"[PCHub] PC Agent 연결 해제: {agent_id}")
    except Exception as e:
        logger.error(f"[PCHub] PC Agent '{agent_id}' 오류: {e}")
    finally:
        _connected_agents.pop(agent_id, None)


# ── REST API: PC 상태 조회 ──

@router.get("/api/pc-agents")
async def list_pc_agents():
    """연결된 PC Agent 목록."""
    return get_connected_agents()


@router.post("/api/pc-agents/{agent_id}/command")
async def send_pc_command_api(agent_id: str, body: dict):
    """특정 PC에 명령 전송 (REST API).

    Body:
        command: 명령 유형
        payload: 명령 데이터
        timeout: 대기 시간 (기본 60초)
    """
    command = body.get("command", "")
    payload = body.get("payload", {})
    timeout = body.get("timeout", 60.0)

    if not command:
        raise HTTPException(400, "command 필드 필수")

    result = await send_command(agent_id, command, payload, timeout)
    return result
