@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  NeoGenesis-GEO-Citations-Daily — wrapper batch
REM
REM  Why this exists: the Windows Scheduled Task previously called the MS Store
REM  redirector at AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.
REM  Python.3.13_qbz5n2kfra8p0\python.exe.  That redirector returns
REM  ERROR_FILE_NOT_FOUND (-2147024894) when the Store package shim is stale —
REM  e.g. across reboots, Windows updates, or after the Store re-syncs.
REM
REM  This wrapper picks the first stable Python that actually exists on disk
REM  in priority order: miniconda → conda envs → system Python → MS Store last.
REM  It also writes a heartbeat log every run so we can see WHICH python was used.
REM ─────────────────────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

set "REPO=D:\00.test\neo-genesis"
set "LOG_DIR=%REPO%\logs\geo_measure"
set "LOG=%LOG_DIR%\cron-%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "PY="

REM 1) miniconda base (preferred — owner standard)
if exist "C:\Users\yesol\miniconda3\python.exe" (
    set "PY=C:\Users\yesol\miniconda3\python.exe"
    set "PY_SRC=miniconda-base"
    goto :found
)

REM 2) miniconda envs (any subfolder with python.exe)
for /D %%E in ("C:\Users\yesol\miniconda3\envs\*") do (
    if exist "%%E\python.exe" (
        set "PY=%%E\python.exe"
        set "PY_SRC=miniconda-env-%%~nxE"
        goto :found
    )
)

REM 3) system-wide python
for %%P in ("C:\Python313\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (
    if exist %%P (
        set "PY=%%~P"
        set "PY_SRC=system-python"
        goto :found
    )
)

REM 4) PATH lookup (skip Store redirector)
for /F "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | findstr /I /C:"WindowsApps" >nul
    if errorlevel 1 (
        if exist "%%P" (
            set "PY=%%P"
            set "PY_SRC=path"
            goto :found
        )
    )
)

REM 5) last resort — Store redirector (may fail with -2147024894)
if exist "C:\Users\yesol\AppData\Local\Microsoft\WindowsApps\python.exe" (
    set "PY=C:\Users\yesol\AppData\Local\Microsoft\WindowsApps\python.exe"
    set "PY_SRC=ms-store-fallback"
    goto :found
)

echo [%DATE% %TIME%] FATAL: no python.exe found >> "%LOG%"
exit /b 1

:found
echo [%DATE% %TIME%] using PY=!PY! (source=!PY_SRC!) >> "%LOG%"

REM Run the GEO citation tracker. Pass through any args supplied to the wrapper.
"!PY!" "%REPO%\scripts\geo_measure\measure_citations.py" --providers openai,gemini %* >> "%LOG%" 2>&1
set "RC=!ERRORLEVEL!"
echo [%DATE% %TIME%] exit_code=!RC! >> "%LOG%"
exit /b !RC!
