@echo off
title MT5 Universal AI Trading Bridge
color 0b
echo ========================================================
echo        MT5 UNIVERSAL AI TRADING BRIDGE LAUNCHER
echo ========================================================
echo.
echo Starting Python MT5 AI Bridge Server on http://127.0.0.1:8000...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] The server stopped unexpectedly.
    pause
)
