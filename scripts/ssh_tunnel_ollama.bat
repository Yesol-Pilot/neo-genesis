@echo off
REM SSH Reverse Tunnel — desktop-home Ollama (11434) → ysh-server (0.0.0.0:11434)
REM 2026-05-12: Sora-live container 에서 desktop-home Ollama 도달 가능하게 만드는 영속 터널
REM
REM 설치 (Windows Task Scheduler):
REM   schtasks /Create /SC ONLOGON /TN "NeoGenesis-Ollama-Tunnel" /TR "%USERPROFILE%\D:\00.test\neo-genesis\scripts\ssh_tunnel_ollama.bat" /F
REM
REM 또는 작업 스케줄러 GUI:
REM   - 트리거: 로그온 시
REM   - 동작: 프로그램 시작 → scripts\ssh_tunnel_ollama.bat
REM   - 설정: 작업이 이미 실행 중이면 새 인스턴스 시작 안 함
REM
REM 라이브 검증:
REM   ssh ysh-server "ss -tlnp | grep :11434"
REM   ssh ysh-server "docker exec sora-live curl -s http://172.17.0.1:11434/api/version"

REM autossh 같은 keep-alive 패턴 - ssh -o ServerAliveInterval/CountMax 로 자동 재연결
:loop
echo [%date% %time%] Starting SSH reverse tunnel: desktop-home:11434 ^-^> ysh-server:11434
ssh -N ^
    -R 0.0.0.0:11434:localhost:11434 ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -o StrictHostKeyChecking=accept-new ^
    ysh-server

echo [%date% %time%] Tunnel disconnected — restart in 10s
timeout /t 10 /nobreak
goto loop
