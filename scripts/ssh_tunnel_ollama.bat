@echo off
REM SSH Reverse Tunnel keeper — desktop-home Ollama (11434) -> ysh-server (0.0.0.0:11434)
REM 2026-05-20 v3: check-and-heal 단발 방식 (Task Scheduler 5분 트리거가 keeper).
REM   - foreground 루프(ssh -N) 는 Task Scheduler 세션에서 reverse-forward stall 발생 → 폐기.
REM   - 매 실행: 터널 forward 헬스 체크 → 정상이면 즉시 종료 / 끊겼으면 stale 정리 후 ssh -fN 재연결.
REM
REM Task Scheduler: 'NeoGenesis-Ollama-Tunnel-Keeper' (5분 간격, MultipleInstances=IgnoreNew)
REM Startup 폴더 사본: 재로그인 시 1회 실행 (이후는 Task Scheduler 가 keeper)
REM
REM 검증: ssh ysh-server "curl -s http://localhost:11434/api/version"

REM 1) 로컬 ssh reverse-tunnel 프로세스(11434) 존재 확인 — 있으면 정상으로 간주, no-op.
REM    (원격 curl health-check 는 transient false-negative 로 불필요 churn 유발 → 폐기.
REM     ssh ServerAliveInterval 이 죽은 connection 은 자체 종료하므로 process 존재 = 살아있음.)
for /f %%n in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='ssh.exe'\" ^| Where-Object { $_.CommandLine -like '*11434*' } ^| Measure-Object).Count"') do set SSHCNT=%%n
if "%SSHCNT%"=="0" goto heal
REM 살아있음 — no-op
exit /b 0

:heal

REM 2) 끊김 — desktop-home 의 Ollama 자체가 죽었으면 먼저 살림
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %ERRORLEVEL%==1 (
    start "" /b ollama serve
    ping -n 6 127.0.0.1 >nul
)

REM 3) stale ssh reverse-tunnel 프로세스 정리 (11434 보유분만 — powershell 위임)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='ssh.exe'\" | Where-Object { $_.CommandLine -like '*11434*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
ping -n 3 127.0.0.1 >nul

REM 4) 새 reverse tunnel (fork, 백그라운드 persist)
ssh -fN -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new -R 0.0.0.0:11434:localhost:11434 ysh-server
exit /b 0
