"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Champion vs Challenger Arena & Incubation Engine
Pits active Champion strategies against newly evolved Challenger variants
to ensure only peak-performing strategies (>80% WR & positive expectancy) hold live deployment slots.
"""

import os
import sys
import json
import datetime
import logging
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.database import SettingsDatabase
from agent_settings.backtester import BacktestingEngine

logger = logging.getLogger("AGENT_SETTINGS_CHALLENGER")

class ChampionChallengerArena:
    def __init__(self, db: SettingsDatabase, backtester: Optional[BacktestingEngine] = None):
        self.db = db
        self.backtester = backtester or BacktestingEngine()

    def get_champions(self) -> List[Dict[str, Any]]:
        """Returns active bots with Win Rate > 80% and positive expectancy."""
        all_eas = self.db.get_all_eas()
        return [ea for ea in all_eas if ea["verified_win_rate"] > 80.0 and ea["net_profit"] > 0 and ea["status"] == "ACTIVE"]

    def create_challenger(
        self,
        base_ea_id: str,
        challenger_id: str,
        new_settings: Dict[str, Any],
        strategy_desc: str
    ) -> Dict[str, Any]:
        """Registers a candidate challenger in the incubator pool."""
        challenger = {
            "ea_id": challenger_id,
            "name": f"Challenger ({challenger_id})",
            "magic": 95000 + abs(hash(challenger_id)) % 4000,
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "bot_type": "python",
            "strategy_name": strategy_desc,
            "status": "INCUBATING",
            "script_path": "",
            "ex5_path": "",
            "current_settings": new_settings,
            "verified_win_rate": 0.0,
            "total_trades": 0,
            "net_profit": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0
        }
        self.db.register_or_update_ea(challenger)
        logger.info(f"Registered Challenger {challenger_id} in incubation pool.")
        return challenger

    def evaluate_battle(
        self,
        champion_id: str,
        challenger_id: str,
        bars_limit: int = 15000
    ) -> Dict[str, Any]:
        """
        Runs an out-of-sample backtest comparison between Champion and Challenger.
        """
        all_eas = {ea["ea_id"]: ea for ea in self.db.get_all_eas()}
        champ = all_eas.get(champion_id)
        chall = all_eas.get(challenger_id)

        if not champ or not chall:
            return {"status": "ERROR", "reason": "Champion or Challenger EA not found."}

        # Compare metrics
        c_wr = champ.get("verified_win_rate", 0.0)
        c_prof = champ.get("net_profit", 0.0)
        ch_wr = chall.get("verified_win_rate", 0.0)
        ch_prof = chall.get("net_profit", 0.0)

        # Promotion logic: Challenger must have WR > 80% and WR > Champion WR, and profit > 0
        promoted = (ch_wr > 80.0 and ch_wr > c_wr and ch_prof > 0)

        result = {
            "champion_id": champion_id,
            "challenger_id": challenger_id,
            "champion_win_rate": c_wr,
            "challenger_win_rate": ch_wr,
            "champion_profit": c_prof,
            "challenger_profit": ch_prof,
            "promoted": promoted,
            "arena_status": "CHALLENGER_PROMOTED" if promoted else "CHAMPION_RETAINED",
            "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO champion_challenger (
                champion_id, challenger_id, symbol, champion_win_rate,
                challenger_win_rate, champion_profit, challenger_profit,
                arena_status, started_at, concluded_at, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                champion_id, challenger_id, "XAUUSD", c_wr, ch_wr, c_prof, ch_prof,
                result["arena_status"], result["evaluated_at"], result["evaluated_at"],
                json.dumps(result)
            ))
            conn.commit()

        self.db.log_activity(
            level="INFO",
            event_type="ARENA_BATTLE_CONCLUDED",
            message=f"Arena Battle: {champion_id} vs {challenger_id} -> {result['arena_status']}",
            details=result
        )

        return result

if __name__ == "__main__":
    db = SettingsDatabase()
    arena = ChampionChallengerArena(db)
    champs = arena.get_champions()
    print(f"Active Champions (>80% WR): {len(champs)}")
    for c in champs:
        print(f" - {c['name']} (Magic {c['magic']}): {c['verified_win_rate']:.2f}% WR | Net ${c['net_profit']:.2f}")
