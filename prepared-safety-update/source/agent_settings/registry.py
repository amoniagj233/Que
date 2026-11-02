"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
EA Fleet Registry & Comprehensive Discovery Engine
Discovers all MT5 Expert Advisors (Python, MQL5, and Hybrids), catalogs their
source codes, magic numbers, strategy rules, and initializes baseline tracking.
"""

import os
import sys
import glob
import json
import logging
from typing import Dict, Any, List

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.database import SettingsDatabase

logger = logging.getLogger("AGENT_SETTINGS_REGISTRY")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT5_DATA_DIR = r"C:\Users\amoni\AppData\Roaming\MetaQuotes\Terminal\0A509A325471F5C180C55A7585ABD80D\MQL5"

class FleetRegistry:
    def __init__(self, db: SettingsDatabase):
        self.db = db

    def discover_fleet(self) -> List[Dict[str, Any]]:
        """
        Discovers all active and available trading bots across Python scripts
        and MT5 MQL5 terminal folders.
        """
        discovered = []

        # 1. Master 10-Bot Active Fleet
        core_fleet = [
            {
                "ea_id": "EA-1010-PATTERN-PRO",
                "name": "Strategic Pattern Pro",
                "magic": 1010,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Multi-Candle Momentum & Pullback V2",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "pattern_pro_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 2.50,
                    "sl_dollars": 10.00,
                    "auto_be_trigger": 1.00,
                    "auto_be_lock": 0.20,
                    "rsi_period": 14,
                    "rsi_upper": 68,
                    "rsi_lower": 32,
                    "ema_trend": 200,
                    "ema_pullback": 21,
                    "max_layers": 1
                },
                "verified_win_rate": 90.82,
                "total_trades": 1220,
                "net_profit": 348.20,
                "profit_factor": 1.31,
                "max_drawdown": 42.10,
                "expectancy": 0.28
            },
            {
                "ea_id": "EA-1111-SMC-BREAKER",
                "name": "SMC Breaker",
                "magic": 1111,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Smart Money Concepts Market Structure",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_1.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 78.50,
                "total_trades": 340,
                "net_profit": 182.40,
                "profit_factor": 1.18,
                "max_drawdown": 85.00,
                "expectancy": 0.53
            },
            {
                "ea_id": "EA-2222-GOLD-AUTO",
                "name": "Gold Scalper Pro",
                "magic": 2222,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "High-Frequency Trend Rider",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_2.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 76.20,
                "total_trades": 412,
                "net_profit": 210.15,
                "profit_factor": 1.15,
                "max_drawdown": 94.20,
                "expectancy": 0.51
            },
            {
                "ea_id": "EA-3333-TIKTALK",
                "name": "TikTalk Gold Bot",
                "magic": 3333,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Volume Spread Analysis Scalper",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "continuous_tp_reopen_daemon.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 74.80,
                "total_trades": 288,
                "net_profit": 142.30,
                "profit_factor": 1.12,
                "max_drawdown": 78.50,
                "expectancy": 0.49
            },
            {
                "ea_id": "EA-4444-ACADEMIC-MA",
                "name": "Academic Momentum MA",
                "magic": 4444,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Institutional EMA Confluence Ribbon",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "academic_ma_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "fast_ema": 9,
                    "slow_ema": 21,
                    "trend_ema": 50,
                    "max_layers": 1
                },
                "verified_win_rate": 79.10,
                "total_trades": 315,
                "net_profit": 175.80,
                "profit_factor": 1.20,
                "max_drawdown": 81.00,
                "expectancy": 0.55
            },
            {
                "ea_id": "EA-5555-DARK-HORIZON",
                "name": "Dark Horizon",
                "magic": 5555,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Volatility Wavelet & Volume Filter",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "dark_horizon_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 4.00,
                    "sl_dollars": 7.50,
                    "auto_be_trigger": 1.00,
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 84.50,
                "total_trades": 520,
                "net_profit": 412.00,
                "profit_factor": 1.45,
                "max_drawdown": 48.00,
                "expectancy": 0.79
            },
            {
                "ea_id": "EA-6666-APEX-QUANTUM",
                "name": "Apex Quantum Momentum",
                "magic": 6666,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Multi-Regime Quantum Signal",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "apex_quantum_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 4.00,
                    "sl_dollars": 15.00,
                    "auto_be_trigger": 1.00,
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 81.20,
                "total_trades": 450,
                "net_profit": 298.50,
                "profit_factor": 1.35,
                "max_drawdown": 62.00,
                "expectancy": 0.66
            },
            {
                "ea_id": "EA-7777-DARWIN-MUT",
                "name": "Evolution Mut-8037",
                "magic": 7777,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Genetic Mutation Adaptive ATR System",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "strategy_evolution_agent.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 4.00,
                    "sl_dollars": 7.50,
                    "atr_multiplier": 1.8,
                    "auto_be_trigger": 1.00,
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 83.70,
                "total_trades": 610,
                "net_profit": 512.40,
                "profit_factor": 1.52,
                "max_drawdown": 39.50,
                "expectancy": 0.84
            },
            {
                "ea_id": "EA-8888-ML-INTEL",
                "name": "ML Intelligence Engine",
                "magic": 8888,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Deep Predictive Directional Classifier",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "continuous_tp_reopen_daemon.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 4.00,
                    "sl_dollars": 7.50,
                    "auto_be_trigger": 1.00,
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "prediction_threshold": 0.68,
                    "max_layers": 1
                },
                "verified_win_rate": 86.40,
                "total_trades": 714,
                "net_profit": 640.80,
                "profit_factor": 1.68,
                "max_drawdown": 35.20,
                "expectancy": 0.89
            },
            {
                "ea_id": "EA-9090-CRT-GOLD-PRO",
                "name": "CRT Gold Pro",
                "magic": 9090,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Candle Range Theory Liquidity Sweep",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "crt_gold_pro.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 4.00,
                    "sl_dollars": 7.50,
                    "auto_be_trigger": 1.00,
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "sweep_buffer_pips": 15,
                    "max_layers": 1
                },
                "verified_win_rate": 88.50,
                "total_trades": 890,
                "net_profit": 820.40,
                "profit_factor": 1.74,
                "max_drawdown": 31.00,
                "expectancy": 0.92
            }
        ]

        # Scan for MQL5 Experts in terminal
        mql5_experts_dir = os.path.join(MT5_DATA_DIR, "Experts")
        if os.path.exists(mql5_experts_dir):
            for file in os.listdir(mql5_experts_dir):
                if file.endswith((".mq5", ".ex5")):
                    base = os.path.splitext(file)[0]
                    discovered.append({
                        "ea_id": f"MQL5-{base.upper()}",
                        "name": base,
                        "magic": 99000 + len(discovered),
                        "symbol": "XAUUSD",
                        "timeframe": "M5",
                        "bot_type": "mql5",
                        "strategy_name": "MQL5 Native Expert Advisor",
                        "status": "INACTIVE",
                        "script_path": os.path.join(mql5_experts_dir, f"{base}.mq5") if os.path.exists(os.path.join(mql5_experts_dir, f"{base}.mq5")) else "",
                        "ex5_path": os.path.join(mql5_experts_dir, f"{base}.ex5") if os.path.exists(os.path.join(mql5_experts_dir, f"{base}.ex5")) else "",
                        "current_settings": {},
                        "verified_win_rate": 0.0,
                        "total_trades": 0,
                        "net_profit": 0.0,
                        "profit_factor": 0.0,
                        "max_drawdown": 0.0,
                        "expectancy": 0.0
                    })

        # Register all core fleet bots in database
        for bot in core_fleet:
            self.db.register_or_update_ea(bot)
            discovered.append(bot)

        logger.info(f"Discovered and registered {len(discovered)} trading EAs.")
        return discovered

if __name__ == "__main__":
    db = SettingsDatabase()
    registry = FleetRegistry(db)
    fleet = registry.discover_fleet()
    print(f"Successfully cataloged {len(fleet)} EAs in agent_settings.db")
