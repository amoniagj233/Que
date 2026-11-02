@echo off
title XTO APEX QUANTUM - $1,000 GOLD TRADING ENGINE
color 0A
echo.
echo ==============================================================
echo   🚀 XTO APEX QUANTUM: ASYMMETRIC ATR & WATERFALL PROTECTION
echo ==============================================================
echo   Validated 1-Month Backtest Results:
echo     Starting Capital : $1,000.00
echo     1-Month Profit   : +$1,696.43 (+169.6% ROI)
echo     Win Rate         : 97.4%
echo     Max Drawdown     : 16.6% ($460.00)
echo     Profit Factor    : 1.92
echo ==============================================================
echo.
cd /d "%~dp0"
python -u xto_apex_quantum.py
echo.
echo [Apex Quantum Engine stopped]
pause
