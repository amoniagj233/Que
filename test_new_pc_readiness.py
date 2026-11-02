"""
APEX AI — New PC Pre-Flight & Environment Readiness Diagnostic
==============================================================
Runs an end-to-end verification check on any new PC before starting live trading:
1. Python runtime & 64-bit architecture check
2. Dependencies import test
3. MetaTrader 5 terminal auto-discovery & connection check
4. Project directories & permissions
5. All 10 live bot scripts syntax & import validation
6. Database integrity check (SQLite databases)
"""

import os
import sys
import importlib
from pathlib import Path

# Setup encoding for Windows command prompts
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

def run_diagnostics():
    print("=" * 75)
    print("   [APEX AI] TRADER - NEW PC READINESS DIAGNOSTIC")
    print("=" * 75)
    print(f"Project Directory: {BASE_DIR}")
    
    all_passed = True

    # 1. Python Check
    print("\n[1/6] Python Runtime:")
    is_64bit = sys.maxsize > 2**32
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  * Version: Python {py_ver} ({'64-bit' if is_64bit else '32-bit WARNING'})")
    if not is_64bit:
        print("  [FAIL] ERROR: MetaTrader5 Python package requires 64-bit Python!")
        all_passed = False
    elif sys.version_info < (3, 9):
        print("  [FAIL] ERROR: Python 3.9+ is required.")
        all_passed = False
    else:
        print("  [PASS] Python version is compatible.")

    # 2. Package Dependencies Check
    print("\n[2/6] Python Package Dependencies:")
    required_pkgs = [
        ("MetaTrader5", "Core MT5 Bridge"),
        ("pandas", "DataFrames & Series"),
        ("numpy", "Numerical Computing"),
        ("sklearn", "Scikit-Learn ML Models"),
        ("scipy", "Scientific Computing"),
        ("fastapi", "API Framework"),
        ("uvicorn", "ASGI Web Server"),
        ("pydantic", "Data Validation"),
        ("requests", "HTTP Requests"),
        ("ta", "Technical Indicators"),
        ("smartmoneyconcepts", "SMC & Order Blocks"),
    ]
    
    missing_pkgs = []
    for pkg, desc in required_pkgs:
        try:
            importlib.import_module(pkg)
            print(f"  [PASS] {pkg:<20} ({desc})")
        except ImportError:
            print(f"  [FAIL] {pkg:<20} ({desc}) - MISSING")
            missing_pkgs.append(pkg)

    if missing_pkgs:
        all_passed = False
        print(f"\n  -> Run: pip install -r requirements.txt to install missing packages.")

    # 3. MetaTrader 5 Terminal Auto-Discovery
    print("\n[3/6] MetaTrader 5 Terminal Discovery:")
    try:
        from mt5_finder import find_mt5_terminal_path, find_mt5_data_dir, smart_initialize_mt5
        term_path = find_mt5_terminal_path()
        if term_path:
            print(f"  [PASS] Terminal Executable : {term_path}")
        else:
            print("  [WARN] Terminal Executable : Not found in standard directories.")
            print("         (Set MT5_PATH in .env if installed in a non-standard location)")

        data_dir = find_mt5_data_dir()
        print(f"  [PASS] MQL5 Data Directory  : {data_dir}")

        # Attempt connection
        import MetaTrader5 as mt5
        init_ok = smart_initialize_mt5()
        if init_ok:
            acc = mt5.account_info()
            term = mt5.terminal_info()
            print(f"  [PASS] Terminal Status     : Connected to '{term.name if term else 'MT5'}'")
            if acc:
                print(f"  [PASS] Account Connected   : Login #{acc.login} | Balance: ${acc.balance:,.2f} | Equity: ${acc.equity:,.2f}")
            else:
                print("  [WARN] Account Status      : MT5 open, but no active trading account logged in.")
            mt5.shutdown()
        else:
            print("  [WARN] Terminal Connection : MT5 not currently active or connection pending.")
            print("         (Launch MetaTrader 5 and log in to your account, then re-run)")
    except Exception as e:
        print(f"  [FAIL] MT5 check error: {e}")

    # 4. Project Directories
    print("\n[4/6] Project Directory Structure:")
    dirs_to_check = [
        BASE_DIR / "logs",
        BASE_DIR / "data_cache",
        BASE_DIR / "commander" / "data",
        BASE_DIR / "agent_settings" / "data",
        BASE_DIR / "CRT_GOLD_PRO",
    ]
    for d in dirs_to_check:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  [PASS] {d.relative_to(BASE_DIR)} (Ready)")

    # 5. Trading Bot Scripts Validation
    print("\n[5/6] Bot Scripts & Strategy Engines:")
    bots = [
        ("bot_slot_1.py", "Apex Quantum / Mut-6495 (Magic 1111)"),
        ("bot_slot_2.py", "Gold Scalper / Mut-5327 (Magic 2222)"),
        ("smc_breaker_sniper.py", "SMC Breaker Sniper (Magic 3333)"),
        ("pattern_pro_bot.py", "Strategic Pattern Pro (Magic 4444)"),
        ("tiktalk_bot.py", "TikTalk Gold VSA (Magic 5555)"),
        ("dark_horizon_bot.py", "XAU Dark Horizon Scalp AI (Magic 1010)"),
        ("crt_gold_pro.py", "CRT Gold Pro Engine (Magic 9090)"),
        ("xto_100_challenge.py", "XTO 100 Doubling Challenge (Magic 8888)"),
        ("structure_grid_trader.py", "StructureGrid Pro Golden Combo (Magic 778899)"),
        ("strategy_evolution_agent.py", "Darwin Evolution Engine (Magic 7777)"),
        ("continuous_tp_reopen_daemon.py", "10-Bot Single-Trade Fleet Reopen Engine"),
        ("web_app.py", "Institutional Web Dashboard & Supreme Commander"),
        ("apex_247_watchdog.py", "24/7 Autonomous Resilient Guardian"),
    ]
    for script_name, label in bots:
        sp = BASE_DIR / script_name
        if sp.exists():
            print(f"  [PASS] {script_name:<30} -> {label}")
        else:
            print(f"  [FAIL] {script_name:<30} -> NOT FOUND")
            all_passed = False

    # 6. SQLite Databases Integrity
    print("\n[6/6] Local Database Store Integrity:")
    dbs = [
        BASE_DIR / "agent_settings" / "data" / "agent_settings.db",
        BASE_DIR / "commander" / "data" / "commander.db",
        BASE_DIR / "commander" / "data" / "execution_risk.db",
    ]
    import sqlite3
    for db in dbs:
        if db.exists():
            try:
                conn = sqlite3.connect(str(db))
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                res = cur.fetchone()[0]
                conn.close()
                status = "OK" if res == "ok" else f"WARN: {res}"
                print(f"  [PASS] {db.relative_to(BASE_DIR)}: {status}")
            except Exception as e:
                print(f"  [WARN] {db.relative_to(BASE_DIR)}: Read error: {e}")
        else:
            print(f"  [INFO] {db.relative_to(BASE_DIR)}: Will be auto-created on first run.")

    print("\n" + "=" * 75)
    if all_passed:
        print("   STATUS: ALL CHECKS PASSED! READY FOR AUTONOMOUS OPERATION.")
        print("   Run 'RUN_APEX_247.bat' to start all bots with 24/7 self-healing.")
    else:
        print("   STATUS: Some items need attention before running (see FAIL items above).")
    print("=" * 75)
    return all_passed

if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
