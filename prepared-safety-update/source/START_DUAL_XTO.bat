@echo off
title DUAL XTO SPEEDER - 24/7 DUAL TRADING STATION
color 0B
echo.
echo ==============================================================
echo   🚀 DUAL XTO SPEEDER: 2 ENGINES RUNNING SIMULTANEOUSLY
echo ==============================================================
echo   Engine 1: Magic 1111 - Fixed 60pts DCA Scalp
echo   Engine 2: Magic 2222 - Dynamic ATR Volatility Spacing
echo ==============================================================
echo.
cd /d "%~dp0"
python run_dual_xto_traders.py
echo.
echo [Dual trading supervisor stopped]
pause
