@echo off
title StructureGrid Pro - Golden Combo Edition
color 0B
cd /d "%~dp0"

echo ======================================================================
echo          STRUCTUREGRID PRO : GOLDEN COMBO EDITION (XAUUSD)
echo ======================================================================
echo Confluence: H1 Macro Trend (EMA50) + M15 Fractal Structure (HH/LL)
echo Precision Trigger: M1/M5 Pullback Rejection Candle
echo Smart DCA: Max 3 Layers (0.01, 0.01, 0.02) Spaced by >= 1.2x ATR
echo Target Basket TP: +$3.50 | Hard Structural SL: On Broker Server
echo Emergency Max Loss: -$25.00 | News Blackout: 30-min window
echo ======================================================================
echo.

python structure_grid_trader.py --base-lot 0.01 --target-tp 3.50 --max-loss 25.00

pause
