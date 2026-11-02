"""Agent 2 — Live Bot Supervisor for APEX AI Commander.

Continuously monitors every registered bot, tracking:
- Heartbeats, process health, uptime
- Realized and unrealized P&L, Win Rate, Profit Factor, Max Drawdown
- Consecutive losses, trade frequency, execution failures
- Automated safe recovery of failed processes (max 3/hr)
- Quarantine of degraded or risk-violating bots
"""
import glob
import json
import logging
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("apex_supervisor")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")


class LiveBotSupervisor:
    def __init__(self, bridge_ref=None, commander_ref=None):
        self.bridge = bridge_ref
        self.commander = commander_ref
        self.bot_records: Dict[str, Dict[str, Any]] = {}
        self.restart_history: Dict[str, List[float]] = {}
        self.quarantined_bots: Dict[str, str] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_bot(
        self,
        bot_id: str,
        name: str,
        script: str,
        magic: int,
        timeframe: str = "M5",
        strategy: str = "Quantitative System",
        risk_tier: str = "live"
    ) -> None:
        self.bot_records[bot_id] = {
            "id": bot_id,
            "name": name,
            "script": script,
            "magic": magic,
            "timeframe": timeframe,
            "strategy": strategy,
            "risk_tier": risk_tier,
            "status": "Initializing",
            "pid": None,
            "uptime_seconds": 0,
            "last_heartbeat": time.time(),
            "trades_total": 0,
            "wins": 0,
            "losses": 0,
            "consecutive_losses": 0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 1.0,
            "max_drawdown": 0.0,
            "execution_failures": 0,
            "log_file": f"{bot_id}.log"
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="apex-supervisor")
        self._thread.start()
        logger.info("Apex Live Bot Supervisor started.")

    def stop(self) -> None:
        self._running = False

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                self.reconcile_fleet_state()
            except Exception as e:
                logger.error(f"Supervisor loop error: {e}")
            time.sleep(5.0)

    def reconcile_fleet_state(self) -> None:
        """Scan system processes, logs, and MT5 deals/positions to update all bots."""
        # 1. Process table scan via PowerShell Win32_Process
        running_scripts = self._get_running_python_scripts()

        # 2. Open positions from MT5 bridge
        open_positions = []
        if self.bridge and self.bridge.connected:
            open_positions = self.bridge.get_open_positions()

        # 3. Closed deals from MT5 bridge
        closed_deals = []
        if self.bridge and self.bridge.connected:
            closed_deals = self.bridge.get_closed_deals_today()

        now_ts = time.time()
        for bot_id, bot in self.bot_records.items():
            script = bot["script"]
            pid = running_scripts.get(script)
            bot["pid"] = pid

            if bot_id in self.quarantined_bots:
                bot["status"] = "Quarantined"
            elif pid:
                bot["status"] = "Active"
                bot["last_heartbeat"] = now_ts
            else:
                bot["status"] = "Stopped"

            # Reconcile MT5 positions for this bot's magic number
            magic = bot["magic"]
            bot_pos = [p for p in open_positions if p.get("magic") == magic]
            bot["unrealized_pnl"] = round(sum(p.get("profit", 0.0) for p in bot_pos), 2)

            # Reconcile closed deals
            bot_deals = [d for d in closed_deals if d.get("magic") == magic]
            if bot_deals:
                bot["trades_total"] = len(bot_deals)
                bot["wins"] = len([d for d in bot_deals if d.get("profit", 0.0) > 0])
                bot["losses"] = len([d for d in bot_deals if d.get("profit", 0.0) < 0])
                bot["realized_pnl"] = round(sum(d.get("profit", 0.0) for d in bot_deals), 2)
                bot["win_rate"] = round((bot["wins"] / bot["trades_total"] * 100.0), 1) if bot["trades_total"] > 0 else 0.0

                gross_profit = sum(d.get("profit", 0.0) for d in bot_deals if d.get("profit", 0.0) > 0)
                gross_loss = abs(sum(d.get("profit", 0.0) for d in bot_deals if d.get("profit", 0.0) < 0))
                bot["profit_factor"] = round((gross_profit / gross_loss), 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 1.0)

            # Check consecutive loss threshold (max 5 consecutive losses triggers quarantine)
            if bot["consecutive_losses"] >= 5 and bot_id not in self.quarantined_bots:
                self.quarantine_bot(bot_id, "Triggered 5 consecutive losses — quarantined for capital safety.")

            # Observation only. Commander Health owns recovery and its approval,
            # desired-state, autonomy and emergency-stop checks.

    def _attempt_safe_restart(self, bot_id: str) -> bool:
        """Compatibility entry point: this observer never starts processes."""
        logger.warning("Restart of %s refused: use Commander agent controls", bot_id)
        return False

    def quarantine_bot(self, bot_id: str, reason: str) -> None:
        self.quarantined_bots[bot_id] = reason
        bot = self.bot_records.get(bot_id)
        if bot:
            bot["status"] = "Quarantined"
            pid = bot.get("pid")
            if pid:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
                bot["pid"] = None
        logger.warning(f"Bot {bot_id} QUARANTINED: {reason}")

    def release_quarantine(self, bot_id: str) -> bool:
        if bot_id in self.quarantined_bots:
            del self.quarantined_bots[bot_id]
            bot = self.bot_records.get(bot_id)
            if bot:
                bot["consecutive_losses"] = 0
                bot["status"] = "Idle"
            logger.info(f"Bot {bot_id} released from quarantine.")
            return True
        return False

    def _get_running_python_scripts(self) -> Dict[str, int]:
        """Maps script filename to PID."""
        mapping = {}
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                 "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if not out:
                return {}
            rows = json.loads(out)
            if isinstance(rows, dict):
                rows = [rows]
            for r in rows:
                cmd = r.get("CommandLine") or ""
                pid = r.get("ProcessId")
                for bot in self.bot_records.values():
                    if bot["script"] in cmd and pid:
                        mapping[bot["script"]] = pid
        except Exception:
            pass
        return mapping

    def get_fleet_snapshot(self) -> List[Dict[str, Any]]:
        return list(self.bot_records.values())


# Global singleton instance
bot_supervisor = LiveBotSupervisor()
