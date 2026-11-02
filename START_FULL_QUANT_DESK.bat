@echo off
title AUTONOMOUS QUANT DESK - 6 AI AGENTS + DUAL LIVE TRADERS
color 0A
cd /d "%~dp0"

echo.
echo ======================================================================
echo   [QUANT DESK] AUTONOMOUS QUANT TRADING DESK (INSTITUTIONAL GRADE)
echo ======================================================================
echo   Supervising:
echo     1. News Sentinel Agent (Macro Volatility Guardian)
echo     2. Chief Risk Officer (Dynamic Sizing & Circuit Breaker)
echo     3. Smart Money Concepts (Order Blocks & FVG Liquidity)
echo     4. Inter-Market Macro Correlation (DXY / EURUSD / Metals)
echo     5. Postmortem Critic (Loss Auditor & Constraint Engine)
echo     6. Darwin Evolution Agent (Continuous Strategy Mutation)
echo     7. Dual Live Bots Hot-Swap Supervisor (Top 2 Tournament Bots)
echo ======================================================================
echo.
python quant_desk_orchestrator.py
echo.
echo [Autonomous Quant Desk supervisor stopped]
pause
