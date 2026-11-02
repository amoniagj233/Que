"""Synchronization Bridge between Python Bot and MQL5 Indicator.

Writes state to MT5 Common Files directory (accessible via MQL5 FILE_COMMON).
Maintains both an atomic real-time JSON state and an append-only CSV event log.
"""
import csv
import json
import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger("CRT_IndicatorBridge")

APPDATA = os.environ.get("APPDATA", "")
COMMON_DIR = os.path.join(APPDATA, "MetaQuotes", "Terminal", "Common", "Files")
os.makedirs(COMMON_DIR, exist_ok=True)

STATE_FILE = os.path.join(COMMON_DIR, "crt_gold_pro_state.json")
EVENTS_FILE = os.path.join(COMMON_DIR, "crt_gold_pro_events.csv")


class IndicatorBridge:
    def __init__(self, bot_name: str = "CRT GOLD PRO", magic: int = 9090, symbol: str = "XAUUSD"):
        self.bot_name = bot_name
        self.magic = magic
        self.symbol = symbol
        self._ensure_csv_header()

    def _ensure_csv_header(self) -> None:
        if not os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp_utc", "event_id", "state", "direction", "price", "message"])
            except Exception as e:
                logger.error(f"Failed to create CSV header: {e}")

    def publish_state(self, state_dict: Dict[str, Any]) -> bool:
        """Atomic write to crt_gold_pro_state.json in MT5 Common Files."""
        try:
            temp_file = STATE_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2)
            # Atomic replace on Windows
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            os.rename(temp_file, STATE_FILE)
            return True
        except Exception as e:
            logger.error(f"Error publishing state to MT5 Common Files: {e}")
            return False

    def log_event(self, state: str, direction: str, price: float, message: str) -> None:
        """Append to crt_gold_pro_events.csv in MT5 Common Files."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            event_id = f"EVT_{int(time.time() * 1000)}"
            with open(EVENTS_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([ts, event_id, state, direction, price, message])
        except Exception as e:
            logger.error(f"Error logging event to CSV: {e}")


# Global bridge instance
bridge = IndicatorBridge()
