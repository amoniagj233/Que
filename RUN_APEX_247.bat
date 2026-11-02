@echo off
title APEX AI TRADER - 24/7 AUTONOMOUS RESILIENT GUARDIAN
color 0A

:: Ensure working directory is Headway trader
cd /d "%~dp0"

echo =====================================================================
echo   [APEX AI] 24/7 AUTONOMOUS TRADING ENGINE & FLEET WATCHDOG
echo =====================================================================
echo   1. Windows Sleep / Standby Prevention: ACTIVE
echo   2. MetaTrader 5 Terminal Watcher: ACTIVE
echo   3. Apex Web Server & Supreme Commander API (Port 8765): SUPERVISED
echo   4. 10-Bot Single-Trade Fleet Reopening Engine: SUPERVISED
echo   5. Automatic Auto-Heal & Infinite Crash Recovery: ENABLED
echo =====================================================================
echo.
echo   [NOTE] Keep this window open or minimized to allow 24/7 operation.
echo   Press Ctrl+C at any time to halt all operations.
echo =====================================================================
echo.

:WATCHDOG_LOOP
echo [%DATE% %TIME%] Starting Apex 24/7 Watchdog Supervisor...
python apex_247_watchdog.py

echo.
echo [!] [%DATE% %TIME%] Watchdog stopped or exited unexpectedly.
echo Auto-restarting in 5 seconds (Press Ctrl+C to abort)...
timeout /t 5 /nobreak >nul
goto WATCHDOG_LOOP
