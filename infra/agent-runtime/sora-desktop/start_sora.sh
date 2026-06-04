#!/bin/bash
# Sora WSL2 daemon launcher (single-PC canonical). 2026-05-29.
# 기존 daemon/brain 정리 후 새 코드로 재기동. TELEGRAM_POLLING=1.
cd /root/sora-live || exit 1

# 기존 인스턴스 종료 (특정 패턴 — 이 스크립트 자신은 start_sora 라 미매치)
pkill -f "venv/bin/python neo_genesis_daemon.py" 2>/dev/null
pkill -f "neo_assistant_bot import NeoAssistant" 2>/dev/null
sleep 3

# 잔존 확인 + 강제 종료
for pid in $(pgrep -f "venv/bin/python neo_genesis_daemon.py"); do kill -9 "$pid" 2>/dev/null; done
for pid in $(pgrep -f "neo_assistant_bot import NeoAssistant"); do kill -9 "$pid" 2>/dev/null; done
sleep 1

# 새 코드로 재기동 (detached, 세션 종료에도 생존)
export TELEGRAM_POLLING=1
export JARVIS_LOCAL_EXEC=1
nohup venv/bin/python neo_genesis_daemon.py > daemon.log 2>&1 &
echo "launched daemon pid $!"
