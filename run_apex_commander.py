"""APEX AI — Autonomous MT5 Gold Trading Commander Master 24/7 Service.

Runs continuously 24/7 in the background without needing a browser open.
Starts automatically whenever the Windows PC powers on or reboots.

Orchestrates all 10 Multi-Agents:
1. Chief Commander AI
2. Live Bot Supervisor
3. Autonomous Research AI
4. Strategy Development AI
5. Backtesting & Validation AI
6. Automatic Optimization AI
7. Bot Performance Evaluator
8. Autonomous Bot Replacement Manager
9. Central Risk Manager
10. Daily Intelligence & Reporting AI (06:00 AM Ghana Time)
"""
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone

# Ensure project root in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "apex_commander_master.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("APEX_COMMANDER")

from commander.mt5_bridge import bridge
from commander.risk_manager import risk_manager
from commander.supervisor import bot_supervisor
from commander.researcher import quant_researcher
from commander.daily_reporter import daily_reporter
from commander.replacement_manager import replacement_manager
from commander.evaluator import bot_evaluator
from commander.backtester import backtester_ai
import commander.api as commander_api


def setup_windows_boot_autostart():
    """Install VBScript into Windows Startup folder to auto-launch on PC boot."""
    try:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return
        startup_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        if not os.path.exists(startup_dir):
            return

        vbs_path = os.path.join(startup_dir, "StartApexCommander.vbs")
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)

        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{BASE_DIR}"
WshShell.Run """{python_exe}"" -u ""{script_path}""", 0, False
'''
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        logger.info(f"Windows Boot Autostart configured successfully at: {vbs_path}")
    except Exception as e:
        logger.error(f"Failed to configure Windows boot autostart: {e}")


def main():
    logger.info("=" * 70)
    logger.info("   APEX AI — AUTONOMOUS MT5 GOLD TRADING COMMANDER (24/7)   ")
    logger.info("=" * 70)
    logger.info(f"Working Directory: {BASE_DIR}")
    logger.info("Configuring Windows 24/7 Boot Autostart...")
    setup_windows_boot_autostart()

    # Step 1: Initialize MT5 Bridge
    logger.info("Initializing Centralized MT5 Gold Bridge...")
    if bridge.initialize():
        summary = bridge.get_account_summary()
        logger.info(f"Connected to MT5 Terminal: {summary.get('terminal')} | Account: {summary.get('login')}")
        logger.info(f"Account Balance: ${summary.get('balance'):,.2f} | Equity: ${summary.get('equity'):,.2f}")
        logger.info(f"Gold Symbol Discovered: {summary.get('gold_symbol')} | Margin Mode: {summary.get('margin_mode')}")
    else:
        logger.warning(f"MT5 Bridge initialize warning: {bridge.last_error}. Bridge will retry in background.")

    # Step 2: Initialize Core Commander Engine
    logger.info("Starting Supreme Commander Orchestrator & Database Store...")
    cmdr = commander_api.get()
    cmdr.set_level(4, "apex_system")  # Grant Full Autonomous Management
    logger.info("Commander Autonomy Level set to: L4 (Full Authorized Command)")

    # Step 3: Register & Supervise All Fleet Bots
    fleet_bots = [
        ("bot_slot_1", "bot_slot_1.py", "Apex-Quantum-DeepSL", 1111, "M1", "Deep-SL Momentum Grid"),
        ("bot_slot_2", "bot_slot_2.py", "Mut-8037 Adaptive", 2222, "M1", "Dynamic ATR Spacing"),
        ("smc_breaker_sniper", "smc_breaker_sniper.py", "SMC Breaker Sniper", 3333, "M5", "Turtle Soup Liquidity"),
        ("pattern_pro_bot", "pattern_pro_bot.py", "Strategic Pattern Pro", 4444, "M5", "Asymmetric Box Breakout"),
        ("tiktalk_bot", "tiktalk_bot.py", "TikTalk Bot", 5555, "M5", "9/21 EMA Cross + RSI 14"),
        ("dark_horizon_bot", "dark_horizon_bot.py", "XAU Dark Horizon Scalp AI", 1010, "M1", "9/21/200 EMA + Flow Telemetry"),
        ("crt_gold_pro", "crt_gold_pro.py", "CRT Gold Pro", 9090, "M5", "Candle Range Theory + M5 Reclaim"),
        ("xto_100_challenge", "xto_100_challenge.py", "XTO 100 Challenge", 8888, "M5", "Adaptive Doubling Grid"),
        ("structure_grid_trader", "structure_grid_trader.py", "StructureGrid Pro", 778899, "M1", "Institutional Market Structure"),
        ("strategy_evolution_agent", "strategy_evolution_agent.py", "Darwin Evolution Engine", 7777, "M5", "Continuous Strategy Mutation"),
    ]

    for bid, script, name, magic, tf, strat in fleet_bots:
        bot_supervisor.register_bot(bid, name, script, magic, tf, strat)
    bot_supervisor.bridge = bridge
    bot_supervisor.commander = cmdr
    bot_supervisor.start()
    logger.info(f"Live Bot Supervisor monitoring {len(fleet_bots)} registered bots.")

    # Step 4: Start Daily Intelligence & Reporting AI (06:00 AM Ghana Time)
    daily_reporter.bridge = bridge
    daily_reporter.supervisor = bot_supervisor
    daily_reporter.commander = cmdr
    daily_reporter.start()
    logger.info("Agent 10 — Daily Intelligence Reporter scheduled for 06:00 AM Africa/Accra (Ghana Time) daily.")

    # Generate initial 06:00 AM baseline report
    logger.info("Generating initial baseline daily intelligence report...")
    initial_report = daily_reporter.generate_and_archive_daily_report()
    logger.info(f"Baseline report generated successfully for {initial_report.get('date')}.")

    # Step 5: Start Standalone Web Dashboard Server on port 8000
    try:
        from web_app import run as run_web_app
        logger.info("Starting APEX AI Gold Trading Command Center Web Dashboard on port 8000...")
        web_thread = threading.Thread(target=run_web_app, daemon=True, name="apex-web-dashboard")
        web_thread.start()
        logger.info("Web Dashboard active at: http://127.0.0.1:8000/ (Nav Tab: APEX AI COMMANDER)")
    except Exception as e:
        logger.warning(f"Could not bind web_app: {e}")

    # Step 6: Start Centralized Fleet Risk & High-Win-Rate Execution Engine (Strict 10-cap, 1 trade per bot)
    def fleet_policy_loop():
        from commander.fleet_policy_engine import run_fleet_risk_cycle
        logger.info("Centralized Fleet Policy Engine active: Strictly enforcing Max 10 positions & 1 trade per bot with Smart Asymmetric V2.")
        while True:
            try:
                if bridge.connected:
                    run_fleet_risk_cycle()
                time.sleep(2.5)
            except Exception as e:
                time.sleep(5.0)

    fleet_thread = threading.Thread(target=fleet_policy_loop, daemon=True, name="fleet-policy-engine")
    fleet_thread.start()

    logger.info("APEX AI Commander is fully operational and standing watch 24/7.")

    # 24/7 Autonomous Supervision Loop
    iteration = 0
    while True:
        try:
            time.sleep(30.0)
            iteration += 1

            # Every 5 minutes (10 iterations * 30s): run risk health check
            if iteration % 10 == 0:
                acc = bridge.get_account_summary()
                if acc.get("connected"):
                    risk_manager.update_account_baseline(acc["balance"], acc["equity"])
                    logger.info(f"[24/7 Heartbeat] Balance: ${acc['balance']:,.2f} | Equity: ${acc['equity']:,.2f} | Mode: {acc['margin_mode']}")

            # Every 30 minutes (60 iterations * 30s): run autonomous quant R&D
            if iteration % 60 == 0:
                new_hyp = quant_researcher.generate_new_hypothesis()
                logger.info(f"[Agent 3 R&D] Synthesized new hypothesis: {new_hyp['id']} ({new_hyp['name']})")

        except KeyboardInterrupt:
            logger.info("Shutdown requested by operator.")
            break
        except Exception as e:
            logger.error(f"Error in Commander main loop: {e}")


if __name__ == "__main__":
    main()
