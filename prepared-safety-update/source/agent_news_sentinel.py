"""
=============================================================================
  📰 AGENT 1: NEWS SENTINEL (MACRO VOLATILITY GUARDIAN)
=============================================================================
Purpose:
  Monitors macroeconomic high-impact events (US CPI, NFP, FOMC, PPI, Jobless Claims).
  Protects trading bots from catastrophic 300-pip news spikes by commanding a
  pre-news entry freeze (15 mins before) and letting volatility settle (15 mins after).

State File:
  `market_risk_state.json` (Read by all active trading bots)
=============================================================================
"""

import time
import json
import os
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "market_risk_state.json")
LOG_FILE   = os.path.join(BASE_DIR, "logs", "news_sentinel.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Standard High-Impact Macro Schedule (UTC hours/mins) for major market movers:
# 12:30 UTC (08:30 EST) -> US CPI, PPI, NFP, Retail Sales, GDP, Claims
# 14:00 UTC (10:00 EST) -> ISM Manufacturing, Consumer Confidence
# 18:00 UTC (14:00 EST) -> FOMC Interest Rate Decision
# 21:55 - 22:30 UTC     -> Market Daily Rollover / Spread Widening Window
SCHEDULED_WINDOWS = [
    {"name": "US Morning Macro Release (CPI/NFP/GDP/Claims)", "utc_hour": 12, "utc_min": 30, "buffer_pre_min": 15, "buffer_post_min": 15},
    {"name": "US Mid-Morning Data (ISM/PMI/Confidence)", "utc_hour": 14, "utc_min": 0, "buffer_pre_min": 10, "buffer_post_min": 15},
    {"name": "FOMC / Fed Rate Decision / Press Conference", "utc_hour": 18, "utc_min": 0, "buffer_pre_min": 25, "buffer_post_min": 30},
    {"name": "Daily Broker Rollover Spread Spike Window", "utc_hour": 22, "utc_min": 0, "buffer_pre_min": 10, "buffer_post_min": 20}
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [NEWS-SENTINEL] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def evaluate_macro_risk():
    now_utc = datetime.now(timezone.utc)
    current_minutes = now_utc.hour * 60 + now_utc.minute

    freeze_active = False
    active_event = None
    next_event_name = None
    min_time_to_next = 99999

    for w in SCHEDULED_WINDOWS:
        event_minutes = w['utc_hour'] * 60 + w['utc_min']
        start_freeze = event_minutes - w['buffer_pre_min']
        end_freeze   = event_minutes + w['buffer_post_min']

        # Currently in freeze window?
        if start_freeze <= current_minutes <= end_freeze:
            freeze_active = True
            active_event = w['name']

        # Calculate time to upcoming event
        diff = event_minutes - current_minutes
        if 0 < diff < min_time_to_next:
            min_time_to_next = diff
            next_event_name = f"{w['name']} in {diff} mins"

    state = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "utc_time": now_utc.strftime("%H:%M:%S UTC"),
        "news_freeze": freeze_active,
        "active_event": active_event,
        "next_event": next_event_name if next_event_name else "No high-impact news in next 4 hours",
        "action_required": "HALT_NEW_ENTRIES" if freeze_active else "NORMAL_TRADING"
    }

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving state: {e}")

    return state

def main():
    log("=" * 65)
    log("  📰 NEWS SENTINEL AGENT INITIALIZED (24/7 MACRO MONITOR)")
    log("=" * 65)

    last_freeze = None
    while True:
        try:
            state = evaluate_macro_risk()
            if state['news_freeze'] != last_freeze:
                if state['news_freeze']:
                    log(f"🚨 [RED ALERT] Macro Event Window Active: {state['active_event']}! COMMANDING BOT FREEZE!")
                else:
                    log("✅ [CLEAR] Macro window closed. Market conditions normalized. Resume trading.")
                last_freeze = state['news_freeze']

            time.sleep(10)
        except KeyboardInterrupt:
            log("News Sentinel stopped by user.")
            break
        except Exception as e:
            log(f"Loop Exception: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
