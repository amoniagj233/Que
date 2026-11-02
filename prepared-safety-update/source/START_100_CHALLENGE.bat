@echo off
title $100 ACCOUNT DOUBLING CHALLENGE - XAUUSD M1
color 0E
echo.
echo ===================================================================
echo   🏆 XTO SPEEDER: $100 ACCOUNT DOUBLING COMPOUNDING CHALLENGE
echo ===================================================================
echo   Level 1 ($100 - $199): Base Lot 0.01  ^| Target TP: +$2.50
echo   Level 2 ($200 - $399): Base Lot 0.02  ^| Target TP: +$5.00 (DOUBLED!)
echo   Level 3 ($400 - $799): Base Lot 0.04  ^| Target TP: +$10.00
echo   Level 4 ($800 - $1599): Base Lot 0.08 ^| Target TP: +$20.00
echo ===================================================================
echo.
cd /d "%~dp0"
python xto_100_challenge.py
echo.
echo [Challenge trader paused]
pause
