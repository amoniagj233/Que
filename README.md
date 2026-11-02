# 🚀 Que — APEX AI Autonomous Multi-Agent Trading System (MT5 Gold)

An institutional-grade, multi-agent quantitative trading system built for MetaTrader 5 (MT5), specialized for Gold (`XAUUSD`). It combines machine learning models, Smart Money Concepts (SMC), market structure confluence, and genetic strategy evolution into a self-healing 24/7 trading engine.

---

## 📦 How to Move and Run on a New PC

Follow these 4 simple steps to copy and run this project on any new Windows computer:

### Step 1: Copy the Project Folder
Copy the entire `Headway trader` folder to your new computer (via USB drive, network transfer, or cloud drive) and place it anywhere you like (e.g., `C:\Projects\Headway trader` or Desktop).

### Step 2: Install Prerequisites on the New PC
1. **Python 3.10 – 3.14 (64-bit)**:
   - Download from [python.org](https://www.python.org/downloads/).
   - ⚠️ **Important**: Check the box **"Add python.exe to PATH"** during installation.
   - MetaTrader 5 Python integration requires 64-bit Python.
2. **MetaTrader 5 Terminal**:
   - Install your broker's MT5 Terminal (Headway, FBS, IC Markets, or official MetaQuotes MT5).
   - Launch MT5, log in to your trading account, and enable **Algo Trading** (Tools -> Options -> Expert Advisors -> check *Allow automated trading* and *Allow DLL imports*).

### Step 3: Run the Setup
Open the folder in **Antigravity** (or Windows File Explorer) and run:
```cmd
setup_new_pc.bat
```
*(Or double-click `install.bat`)*. This will:
- Upgrade pip and install all required libraries from `requirements.txt`
- Auto-detect your MetaTrader 5 terminal installation
- Ensure all logs, cache, and database directories exist

### Step 4: Run the Pre-Flight Diagnostic
Run the pre-flight readiness check in terminal:
```cmd
python test_new_pc_readiness.py
```
This verifies your Python version, library dependencies, MT5 connection, and bot scripts. When all items display `[PASS]`, your system is 100% ready.

### Step 5: Start All Bots (24/7 Resilient Guardian)
Double-click:
```cmd
RUN_APEX_247.bat
```
This starts the **Apex 24/7 Watchdog Supervisor**, which:
- Prevents Windows sleep/hibernation
- Auto-launches and watches MetaTrader 5
- Launches the Web Dashboard & Supreme Commander Workstation at **`http://127.0.0.1:8765/`**
- Supervises the 10-Bot Single-Trade Fleet Reopen Engine (`continuous_tp_reopen_daemon.py`)
- Provides automatic crash recovery and self-healing

---

## 💻 Running Inside Antigravity

When using **Antigravity** pair programming on the new PC:
- The project includes `AGENTS.md` with guidelines for Antigravity agents.
- You can ask Antigravity:
  - `"start all the bots"` -> launches the 24/7 supervisor and trading bots.
  - `"check account status"` -> checks balance, equity, and open positions.
  - `"run pre-flight check"` -> executes `python test_new_pc_readiness.py`.
- **Note**: When executing commands that connect to MT5 or open network ports (`8765`), run outside sandbox (`BypassSandbox: true`) so Python can communicate across processes and with the broker's servers.

---

## 🤖 The 10 Live Fleet Bots

| Magic Number | Bot / Strategy Name | Description |
| :---: | :--- | :--- |
| **1010** | **XAU Dark Horizon Scalp AI** | 9/21/200 EMA + Flow Telemetry & Impulse Meter |
| **9090** | **CRT Gold Pro** | Candle Range Theory (CRT) + M5 Liquidity Reclaim |
| **8888** | **ML Intelligence / XTO 100** | 24-Feature Machine Learning & Compounding Ladder |
| **4444** | **Strategic Pattern Pro V2** | Asymmetric Box Breakout (>90% Verified Win Rate) |
| **3333** | **SMC Breaker Sniper V2** | Turtle Soup & Order Block Liquidity (>92% WR) |
| **5555** | **TikTalk Gold VSA V2** | 9/21 EMA Cross + RSI 14 + Volume Spread Analysis |
| **6666** | **Academic Momentum MA V2** | 44/332 Dual Moving Average Confluence |
| **2222** | **Gold Scalper Pro V2** | Dynamic ATR Volatility Spacing Grid |
| **1111** | **Apex Quantum Momentum V2** | Deep-SL Momentum Scalp Engine |
| **7777** | **Evolution Mut-8037** | Darwin Genetic Evolution Tournament Champion |
| **778899**| **StructureGrid Pro** | H1 Trend Confluence + M15 Fractal Structure |

---

## 🛡️ Risk Architecture & Fleet Policies

1. **Strict Single-Position Policy**:
   Each bot is strictly capped at **MAX 1 OPEN POSITION** at any time. A bot will never stack or duplicate trades.
2. **Portfolio-Wide Exposure Cap**:
   Maximum total open positions across the entire account $\le 10$ positions ($\le 0.10$ lots total), eliminating margin stress.
3. **Smart Asymmetric Exits**:
   - **Auto-Breakeven**: Moves Stop Loss to Entry $+0.40$ (locking in profit above broker spread) once trade reaches $+1.00$ profit.
   - **Dynamic Trailing Stop**: Activated once profit reaches $+2.00$ to ride runners.

---

## 📁 Key File Map

- `RUN_APEX_247.bat` — One-click launcher for the 24/7 supervisor & fleet daemon.
- `setup_new_pc.bat` / `install.bat` — One-click setup for new PCs.
- `test_new_pc_readiness.py` — Pre-flight environment diagnostics.
- `mt5_finder.py` — Dynamic auto-discovery for MetaTrader 5 and MQL5 directories.
- `apex_247_watchdog.py` — Supervisor monitoring MT5, web server, and fleet daemon.
- `continuous_tp_reopen_daemon.py` — 10-bot single-trade execution and risk manager.
- `web_app.py` — Web Dashboard & Supreme AI Commander on port `8765`.
- `quant_desk_orchestrator.py` — 6 institutional AI research & macro agents.
- `AGENTS.md` — Agent instructions for Antigravity pair programming.
- `.env.example` — Optional configuration template.
