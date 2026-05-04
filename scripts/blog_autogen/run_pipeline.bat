@echo off
REM Neo Genesis blog auto-generation pipeline (Windows wrapper)
REM Scheduled daily 10:30 KST via NeoGenesis-Blog-Autogen-Daily task

setlocal enableextensions enabledelayedexpansion

set "REPO=D:\00.test\neo-genesis"
set "SCRIPT=%REPO%\scripts\blog_autogen\run_pipeline.py"
set "LOGDIR=%REPO%\logs\blog_autogen"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "STAMP=%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%"
set "STAMP=!STAMP: =0!"
set "LOGFILE=%LOGDIR%\run-!STAMP!.log"

REM Find Python: prefer miniconda, then python on PATH
set "PYEXE="
if exist "C:\Users\yesol\miniconda3\python.exe" (
    set "PYEXE=C:\Users\yesol\miniconda3\python.exe"
) else if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYEXE=%USERPROFILE%\miniconda3\python.exe"
) else (
    where python >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        set "PYEXE=python"
    )
)

if "%PYEXE%"=="" (
    echo [%TIME%] FATAL: no Python interpreter found. >> "%LOGFILE%"
    exit /b 1
)

echo [%TIME%] Starting Neo Genesis blog autogen pipeline (Python=%PYEXE%) >> "%LOGFILE%"
echo [%TIME%] Args: %* >> "%LOGFILE%"

cd /d "%REPO%"
"%PYEXE%" "%SCRIPT%" %* >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"

echo [%TIME%] Exit code: %RC% >> "%LOGFILE%"
echo [%TIME%] Log: %LOGFILE%
exit /b %RC%
