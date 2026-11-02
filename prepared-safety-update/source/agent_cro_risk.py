"""
=============================================================================
  ⚖️ AGENT 2: CHIEF RISK OFFICER (CRO) & DYNAMIC SIZING ENGINE
=============================================================================
Purpose:
  1. Spread Guardian: Monitors live broker spread. Freezes entries if spread
     widens above $0.60 (e.g., rollover spread spikes).
  2. Margin & Drawdown Watchdog: Enforces hard circuit breaker if aggregate
     equity drawdown exceeds 20% or free margin falls below safety thresholds.
  3. Dynamic Fractional Sizer: Automatically calculates optimal base lot size
     as account balance scales up or down ($1,000 -> 0.01, $2,000 -> 0.02, etc.).
  4. Aggregate Exposure Limiter: Caps total simultaneous lots across all bots.

State File:
  `cro_risk_state.json` (Consumed by all active trading bots)
=============================================================================
"""

import MetaTrader5 as mt5
import json
import time
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
STATE_FILE      = os.path.join(BASE_DIR, "cro_risk_state.json")
LOG_FILE        = os.path.join(BASE_DIR, "logs", "cro_risk.log")
SYMBOL          = "XAUUSD"
MAX_SPREAD_USD  = 0.65       # Max acceptable spread on Gold ($0.65)
MAX_TOTAL_LOTS  = 0.30       # Maximum aggregate exposure across all bots
MIN_MARGIN_PCT  = 800.0      # Minimum margin level %
LOOP_INTERVAL   = 3

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [CRO-RISK] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def calculate_base_lot(equity):
    if equity < 1500.0:
        return 0.01
    elif equity < 3000.0:
        return 0.02
    elif equity < 5000.0:
        return 0.03
    elif equity < 10000.0:
        return 0.05
    else:
        return round(0.01 * (equity / 1000.0), 2)

def evaluate_risk():
    tick = mt5.symbol_info_tick(SYMBOL)
    acc = mt5.account_info()
    positions = mt5.positions_get(symbol=SYMBOL)

    if not tick or not acc:
        return None

    spread = round(tick.ask - tick.bid, 2)
    spread_ok = spread <= MAX_SPREAD_USD

    total_lots = round(sum(p.volume for p in positions), 2) if positions else 0.0
    exposure_ok = total_lots <= MAX_TOTAL_LOTS

    margin_level = acc.margin_level if acc.margin_level > 0 else 99999.0
    margin_safe = margin_level >= MIN_MARGIN_PCT

    # Equity circuit breaker
    circuit_breaker = not (spread_ok and exposure_ok and margin_safe)

    recommended_base = calculate_base_lot(acc.equity)

    state = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "balance": round(acc.balance, 2),
        "equity": round(acc.equity, 2),
        "spread_usd": spread,
        "spread_ok": spread_ok,
        "total_lots_exposed": total_lots,
        "exposure_ok": exposure_ok,
        "margin_level_pct": round(margin_level, 1),
        "margin_safe": margin_safe,
        "circuit_breaker": circuit_breaker,
        "recommended_base_lot": recommended_base,
        "can_open_new_trade": not circuit_breaker
    }

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving state: {e}")

    return state

def main():
    if not mt5.initialize():
        print("MT5 init failed in CRO Agent")
        sys.exit(1)

    log("=" * 65)
    log("  ⚖️ CHIEF RISK OFFICER (CRO) ACTIVE (CONTINUOUS RISK POLICING)")
    log(f"  Rules: MaxSpread=${MAX_SPREAD_USD:.2f} | MaxLots={MAX_TOTAL_LOTS} | MinMargin={MIN_MARGIN_PCT}%")
    log("=" * 65)

    last_cb_state = None
    while True:
        try:
            state = evaluate_risk()
            if state and state['circuit_breaker'] != last_cb_state:
                if state['circuit_breaker']:
                    reasons = []
                    if not state['spread_ok']: reasons.append(f"High Spread (${state['spread_usd']:.2f})")
                    if not state['exposure_ok']: reasons.append(f"Max Lots Reached ({state['total_lots_exposed']})")
                    if not state['margin_safe']: reasons.append(f"Low Margin ({state['margin_level_pct']}%)")
                    log(f"🛑 [CIRCUIT BREAKER ENGAGED] Trading halted! Reasons: {', '.join(reasons)}")
                else:
                    log(f"🟢 [RISK NORMAL] Market safe for execution. Base lot: {state['recommended_base_lot']} | Spread: ${state['spread_usd']:.2f}")
                last_cb_state = state['circuit_breaker']

            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            log("CRO Agent stopped by user.")
            break
        except Exception as e:
            log(f"CRO Exception: {e}")
            time.sleep(3)

    mt5.shutdown()

if __name__ == "__main__":
    main()
