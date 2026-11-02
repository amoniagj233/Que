@echo off
title DARWIN QUANT AI - AUTONOMOUS STRATEGY EVOLUTION AGENT
color 0E
echo.
echo ====================================================================
echo   🤖 DARWIN QUANT AI: CONTINUOUS AUTONOMOUS STRATEGY EVOLUTION
echo ====================================================================
echo   Tasks:
echo     1. Combinatorial Strategy Generation (EMAs, RSI, BB, ATR Grids)
echo     2. Automatic Multi-Candle Backtesting & Stress-Testing
echo     3. Survival of the Fittest Pruning (Only TOP 2 Bots Survived)
echo     4. Autonomous Live Hot-Swapping into Bot Slot 1 and Slot 2
echo ====================================================================
echo.
cd /d "%~dp0"
python -u strategy_evolution_agent.py
echo.
echo [Evolution Agent Stopped]
pause
