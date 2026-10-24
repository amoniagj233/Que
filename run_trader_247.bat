@echo off
title MT5 24/7 Reinforcement Trading Bracket Bot
color 0A
echo ======================================================================
echo          MT5 24/7 REINFORCEMENT TRADING BRACKET BOT
echo ======================================================================
echo Watchlist: XAUUSD, EURUSD, GBPUSD, USDJPY, BTCUSD, ETHUSD
echo Fixed Lot: 0.01 | Strategy: Reinforcement Trading Part 2
echo Watchdog mode: Active (auto-restarts on crash)
echo ======================================================================

:loop
echo [%date% %time%] Starting 24/7 Trading Bot...
python rl_bracket_strategy.py --auto --symbols=XAUUSD,EURUSD,GBPUSD,USDJPY,BTCUSD,ETHUSD --tf=H1 --volume=0.01
echo [!] Bot process ended. Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
