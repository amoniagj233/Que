@echo off
title XTO Speeder Rebuilt - XAUUSD M1 Live Trader
color 0A
echo.
echo ======================================================
echo   🚀 XTO SPEEDER REBUILT - LIVE XAUUSD M1 TRADER
echo ======================================================
echo.
cd /d "%~dp0"
echo Starting XTO Speeder engine...
echo Press Ctrl+C to safely stop (positions stay open)
echo.
python xto_speeder_trader.py
echo.
echo [Bot stopped - check positions in MT5]
pause
