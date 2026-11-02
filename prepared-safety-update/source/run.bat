@echo off
title Headway MT5 Institutional Trading Station
color 0b
echo ========================================================
echo   HEADWAY MT5 INSTITUTIONAL TRADING STATION & ANALYTICS
echo ========================================================
echo.
echo Starting Institutional Workstation on http://127.0.0.1:8765...
echo.

python web_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] The workstation server stopped unexpectedly.
    pause
)
