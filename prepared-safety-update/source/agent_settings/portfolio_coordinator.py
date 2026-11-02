"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Multi-EA Portfolio Coordinator & Risk Governor
Enforces:
1. STRICT ACCOUNT CAP: MAX 10 OPEN TRADES ACROSS ENTIRE FLEET
2. STRICT BOT CAP: MAX 1 TRADE PER BOT AT ANY TIME
3. No bot may open another trade until previous trade closes by TP or SL
4. Risk allocation and portfolio margin monitoring
"""

import os
import sys
import logging
from typing import Dict, Any, List

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.database import SettingsDatabase

logger = logging.getLogger("AGENT_SETTINGS_PORTFOLIO")

MAX_FLEET_TRADES = 10
MAX_PER_BOT = 1

class PortfolioCoordinator:
    def __init__(self, db: SettingsDatabase):
        self.db = db

    def check_trade_permission(self, magic: int, current_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determines whether a bot with given magic number is permitted to open a new trade.
        """
        total_open = len(current_positions)
        bot_positions = [p for p in current_positions if p.get("magic") == magic]
        bot_open = len(bot_positions)

        # Rule 1: Account-wide 10-trade limit
        if total_open >= MAX_FLEET_TRADES:
            return {
                "allowed": False,
                "reason": f"FLEET_CAP_REACHED: Total open positions ({total_open}) equals or exceeds max allowed ({MAX_FLEET_TRADES}).",
                "total_open": total_open,
                "bot_open": bot_open
            }

        # Rule 2: Single trade per bot
        if bot_open >= MAX_PER_BOT:
            return {
                "allowed": False,
                "reason": f"BOT_CAP_REACHED: Bot (Magic {magic}) already has an active position (#{bot_positions[0].get('ticket')}). Must wait for TP or SL.",
                "total_open": total_open,
                "bot_open": bot_open
            }

        return {
            "allowed": True,
            "reason": f"APPROVED: Fleet capacity {total_open}/{MAX_FLEET_TRADES}, Bot slots {bot_open}/{MAX_PER_BOT}.",
            "total_open": total_open,
            "bot_open": bot_open
        }

    def compute_portfolio_risk_summary(self, account_info: Dict[str, Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        balance = account_info.get("balance", 0.0)
        equity = account_info.get("equity", 0.0)
        margin = account_info.get("margin", 0.0)
        total_open = len(positions)
        floating_profit = sum(p.get("profit", 0.0) for p in positions)
        total_volume = sum(p.get("volume", 0.0) for p in positions)

        margin_level = (equity / margin * 100.0) if margin > 0 else 9999.0

        return {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "margin": round(margin, 2),
            "margin_level": round(margin_level, 2),
            "floating_profit": round(floating_profit, 2),
            "total_open_positions": total_open,
            "max_fleet_positions": MAX_FLEET_TRADES,
            "total_volume_lots": round(total_volume, 2),
            "fleet_capacity_pct": round((total_open / MAX_FLEET_TRADES) * 100.0, 1)
        }

if __name__ == "__main__":
    db = SettingsDatabase()
    coord = PortfolioCoordinator(db)
    print("Portfolio Coordinator loaded. Strict fleet cap:", MAX_FLEET_TRADES, "Strict bot cap:", MAX_PER_BOT)
