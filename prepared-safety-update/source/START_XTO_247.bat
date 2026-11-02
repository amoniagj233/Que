@echo off
title XTO Speeder 24/7 Watchdog
color 0A
echo.
echo =====================================================
echo   🚀 XTO SPEEDER — 24/7 AUTO-RESTART WATCHDOG
echo =====================================================
echo   This window keeps XTO Speeder running forever.
echo   DO NOT CLOSE this window while trading.
echo   Press Ctrl+C only to stop ALL trading.
echo =====================================================
echo.
cd /d "%~dp0"
python xto_watchdog.py
echo.
echo [Watchdog stopped — check positions in MT5]
pause
