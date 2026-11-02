"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Master Autonomous Loop Daemon
Coordinates:
- 1-Minute: Portfolio Risk & 10-Cap Guardrails
- 15-Minute: Market Regime Analysis on Gold
- 1-Hour: Strict 80% Performance Policy Fleet Audit & Candidate Processing
- 24-Hour: Deep Strategy Optimization & Champion vs Challenger Arenas
"""

import os
import sys
import time
import logging
import datetime
from typing import Dict, Any

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import MetaTrader5 as mt5
from agent_settings.database import SettingsDatabase
from agent_settings.registry import FleetRegistry
from agent_settings.audit_engine import AuditEngine
from agent_settings.optimizer import StrategyOptimizer
from agent_settings.elimination_agent import EliminationAgent
from agent_settings.champion_challenger import ChampionChallengerArena
from agent_settings.regime_analyzer import MarketRegimeAnalyzer
from agent_settings.portfolio_coordinator import PortfolioCoordinator

MT5_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] SUPREME_COMMANDER: %(message)s"
)
logger = logging.getLogger("SUPREME_COMMANDER")

class SupremeSettingsCommander:
    def __init__(self):
        self.db = SettingsDatabase()
        self.registry = FleetRegistry(self.db)
        self.audit_engine = AuditEngine(self.db)
        self.optimizer = StrategyOptimizer(self.db)
        self.elimination_agent = EliminationAgent(self.db, self.audit_engine, self.optimizer)
        self.arena = ChampionChallengerArena(self.db)
        self.regime_analyzer = MarketRegimeAnalyzer(self.db)
        self.portfolio_coordinator = PortfolioCoordinator(self.db)

        self.last_1m = 0
        self.last_15m = 0
        self.last_1h = 0
        self.last_24h = 0

    def start(self):
        logger.info("=" * 80)
        logger.info("AGENT SETTINGS: SUPREME SETTINGS COMMANDER ONLINE")
        logger.info("MANDATE: ACHIEVE & MAINTAIN >80% VERIFIED WIN RATE FOR EVERY LIVE EA")
        logger.info("PORTFOLIO LIMIT: STRICT 10 TRADES FLEET-WIDE | 1 TRADE PER BOT")
        logger.info("=" * 80)

        # Step 1: Initial Discovery & Registry
        self.registry.discover_fleet()

        # Step 2: Initial Market Regime Check
        self.regime_analyzer.analyze_current_regime()

        # Step 3: Initial Audit
        self.audit_engine.run_full_fleet_audit()

        # Step 4: Autonomous loop
        while True:
            try:
                now = time.time()

                # --- 1-MINUTE SCHEDULE: Risk & Positions Audit ---
                if now - self.last_1m >= 60:
                    self._run_1min_schedule()
                    self.last_1m = now

                # --- 15-MINUTE SCHEDULE: Market Regime ---
                if now - self.last_15m >= 900:
                    self._run_15min_schedule()
                    self.last_15m = now

                # --- 1-HOUR SCHEDULE: 80% Policy Audit & Optimization ---
                if now - self.last_1h >= 3600:
                    self._run_1hour_schedule()
                    self.last_1h = now

                # --- 24-HOUR SCHEDULE: Deep Walk-Forward Arenas ---
                if now - self.last_24h >= 86400:
                    self._run_24hour_schedule()
                    self.last_24h = now

                time.sleep(5)
            except KeyboardInterrupt:
                logger.info("Supreme Settings Commander shutting down gracefully.")
                break
            except Exception as e:
                logger.error(f"Error in Commander loop: {e}", exc_info=True)
                time.sleep(10)

    def _run_1min_schedule(self):
        if not mt5.initialize(path=MT5_PATH):
            return

        positions = mt5.positions_get(symbol="XAUUSD")
        pos_list = [
            {"ticket": p.ticket, "magic": p.magic, "profit": p.profit, "volume": p.volume, "comment": p.comment}
            for p in (positions or [])
        ]
        acc = mt5.account_info()
        acc_dict = {"balance": acc.balance, "equity": acc.equity, "margin": acc.margin} if acc else {}
        mt5.shutdown()

        risk_summary = self.portfolio_coordinator.compute_portfolio_risk_summary(acc_dict, pos_list)
        logger.info(f"[1-MIN AUDIT] Positions: {risk_summary['total_open_positions']}/10 | Floating PnL: ${risk_summary['floating_profit']:.2f} | Margin: ${risk_summary['margin']:.2f}")

    def _run_15min_schedule(self):
        logger.info("[15-MIN SCHEDULE] Running Market Regime Classification...")
        regime = self.regime_analyzer.analyze_current_regime()
        logger.info(f"Regime: {regime['regime_type']} | Recommendation: {regime['recommendation']}")

    def _run_1hour_schedule(self):
        logger.info("[1-HOUR SCHEDULE] Running Fleet 80% Performance Audit...")
        results = self.audit_engine.run_full_fleet_audit()
        for r in results:
            if r["retirement_ready"]:
                logger.warning(f"Candidate for optimization/elimination: {r['name']} ({r['ea_id']}) with WR {r['win_rate']:.2f}%")
                # Trigger autonomous 11-step workflow
                self.elimination_agent.process_underperforming_ea(r["ea_id"])

    def _run_24hour_schedule(self):
        logger.info("[24-HOUR SCHEDULE] Running Comprehensive Arena Evaluations...")
        champions = self.arena.get_champions()
        for c in champions:
            logger.info(f"Champion {c['name']} maintained with verified Win Rate {c['verified_win_rate']:.2f}%.")

if __name__ == "__main__":
    commander = SupremeSettingsCommander()
    commander.start()
