# APEX AI — Antigravity Agent Guidelines & Project Architecture

Autonomous Multi-Agent Quantitative Trading System running on MetaTrader 5 (MT5), specialized for Gold (XAUUSD).

---

## 🚀 Moving to a New PC & First-Time Setup in Antigravity

When this repository is copied to a new PC and opened in **Antigravity**:

1. **Prerequisites on New PC**:
   - Windows 10/11 (64-bit)
   - Python 3.10 – 3.14 (64-bit) on Windows `PATH`
   - MetaTrader 5 Terminal installed (Headway MT5, FBS MT5, IC Markets, or official MetaQuotes MT5) and logged in with your trading account.

2. **One-Click Setup**:
   Open a terminal in Antigravity or double-click:
   ```cmd
   setup_new_pc.bat
   ```
   *(Or run `python -m pip install -r requirements.txt`)*

3. **Verify Environment Readiness**:
   ```cmd
   python test_new_pc_readiness.py
   ```
   This performs an end-to-end audit verifying Python 64-bit, package imports, MT5 auto-discovery, project directories, bot scripts, and database integrity.

4. **Launch 24/7 Trading Engine**:
   - Double-click **`RUN_APEX_247.bat`** (or run `python apex_247_watchdog.py`).
   - Open Web Dashboard: **`http://127.0.0.1:8765/`**

---

## 🧠 Core System Architecture

### 1. 24/7 Watchdog Supervisor (`apex_247_watchdog.py` / `RUN_APEX_247.bat`)
- Prevents Windows sleep & hibernation via kernel execution state flags (`SetThreadExecutionState`).
- Auto-detects and auto-restarts MetaTrader 5 (`terminal64.exe`) if closed or crashed.
- Supervises the Institutional Web Dashboard (`web_app.py 8765`).
- Supervises the 10-Bot Single-Trade Fleet Reopen Engine (`continuous_tp_reopen_daemon.py`).
- Auto-heals and restarts failed processes with persistent health logging.

### 2. Fleet Policy & Single-Trade Risk Engine (`continuous_tp_reopen_daemon.py`)
- **Strict Single-Position Rule**: Every bot magic number is strictly capped at **MAX 1 OPEN TRADE**.
- **Portfolio Exposure Cap**: Total simultaneous trades across the entire fleet $\le 10$ positions ($\le 0.10$ lots total).
- **Auto-Breakeven**: Moves SL to entry $+0.40$ (locking win above spread) once price hits $+1.00$ profit.
- **Dynamic Trailing Stop**: Activates above $+2.00$ profit to let runners maximize gains.
- **Instant Reopen**: When a position hits TP or SL, the engine opens a fresh high-conviction trade.

### 3. Institutional Web Dashboard (`web_app.py` on Port 8765)
- Live account telemetry (balance, equity, floating P&L, free margin, leverage, ping).
- Real-time Chart Analysis & Gold Intelligence Matrix (Order Blocks, FVGs, Asian session ranges).
- AI Machine Learning Engine (24-feature ML models, regime classifier).
- **Supreme AI Commander** interface with manual and autonomous execution overrides.

### 4. Autonomous Quant Trading Desk (`quant_desk_orchestrator.py` / `START_FULL_QUANT_DESK.bat`)
Orchestrates 6 institutional AI research and risk agents:
1. `agent_news_sentinel.py` — Macro Volatility Guardian (CPI, NFP, FOMC freezes).
2. `agent_cro_risk.py` — Dynamic Sizing & Circuit Breaker.
3. `agent_smc_liquidity.py` — Order Blocks & FVG Liquidity.
4. `agent_macro_correlation.py` — Inter-Market Confluence (DXY, EURUSD, Metals).
5. `agent_critic_auditor.py` — Postmortem Critic & Loss Auditor.
6. `strategy_evolution_agent.py` — Darwin Evolution Genetic Algorithm.

---

## 🤖 The 10 Live Fleet Bots (Magic Numbers)

| Magic | Bot Name | Strategy & Engine |
| :---: | :--- | :--- |
| **1010** | **XAU Dark Horizon Scalp AI** | 9/21/200 EMA + Flow Telemetry |
| **9090** | **CRT Gold Pro** | Candle Range Theory + M5 Liquidity Reclaim |
| **8888** | **ML Intelligence / XTO 100** | 24-Feature ML Model & Compounding Ladder |
| **4444** | **Strategic Pattern Pro V2** | Asymmetric Box Breakout (>90% WR) |
| **3333** | **SMC Breaker Sniper V2** | Turtle Soup & Order Block Liquidity (>92% WR) |
| **5555** | **TikTalk Gold VSA V2** | 9/21 EMA Cross + RSI 14 + Volume Spread |
| **6666** | **Academic Momentum MA V2** | 44/332 Dual Moving Average Confluence |
| **2222** | **Gold Scalper Pro V2 / Mut-5327** | Dynamic ATR Spacing Grid |
| **1111** | **Apex Quantum Momentum / Mut-6495**| Deep-SL Momentum Grid |
| **7777** | **Evolution Mut-8037** | Darwin Genetic Evolution Champion |
| **778899**| **StructureGrid Pro** | H1 Macro Trend + M15 Fractal Structure |

---

## 🛠️ Antigravity Developer Instructions

- **Terminal Execution Mode**: When running commands that interface with MetaTrader 5 (IPC/sockets) or bind local servers (ports `8765`, `8000`), run with `BypassSandbox: true` so they can communicate across processes and access network broker servers.
- **Port Conflicts**: Port `8765` is the default web dashboard port. Check active processes with `Get-NetTCPConnection -LocalPort 8765` if port rebinding is needed.
- **No Hardcoded Absolute Paths**: All scripts must use relative paths via `Path(__file__).resolve().parent` or `mt5_finder.py`. Never commit hardcoded user folders like `C:\Users\<username>`.
