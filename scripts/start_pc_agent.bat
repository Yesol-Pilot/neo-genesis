@echo off
chcp 65001 >nul 2>&1
title Sora PC Agent (home-pc)
cd /d D:\00.test\neo-genesis
set PYTHONPATH=D:\00.test\neo-genesis
set PYTHONIOENCODING=utf-8
set PC_AGENT_TOKEN=sora-pc-agent-2026-yesol

:loop
echo [%date% %time%] Sora PC Agent starting...
python scripts\sora_pc_agent.py --id home-pc --server ws://34.47.114.142:7700/ws/pc-agent --token %PC_AGENT_TOKEN%
echo [%date% %time%] Agent disconnected. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
