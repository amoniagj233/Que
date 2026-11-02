@echo off
title XTO Speeder EA Guardian & News Shield
color 0A
echo ======================================================================
echo             XTO SPEEDER EA GUARDIAN & RISK SHIELD
echo ======================================================================
echo Target EA: XTO Speeder (Magic 1111) on XAUUSD
echo Max Basket Drawdown Stop: $50.00
echo Macro Blackout Monitoring: Active
echo ======================================================================
echo.

python ea_sentinel.py --max-loss 50.0

pause
