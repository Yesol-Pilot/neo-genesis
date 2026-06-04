@echo off
setlocal
chcp 65001 >nul 2>&1
title Sora PC Agent

set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%" || exit /b 1

if not defined SORA_PC_AGENT_ID set "SORA_PC_AGENT_ID=%COMPUTERNAME%"
if not defined SORA_PC_AGENT_SERVER (
  echo ERROR: SORA_PC_AGENT_SERVER is not set.
  exit /b 1
)
if not defined PC_AGENT_TOKEN (
  echo ERROR: PC_AGENT_TOKEN is not set.
  exit /b 1
)

set "PYTHONPATH=%PROJECT_ROOT%"
set "PYTHONIOENCODING=utf-8"

:loop
echo [%date% %time%] Sora PC Agent starting: %SORA_PC_AGENT_ID%
python scripts\sora_pc_agent.py --id "%SORA_PC_AGENT_ID%" --server "%SORA_PC_AGENT_SERVER%"
echo [%date% %time%] Agent disconnected. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
