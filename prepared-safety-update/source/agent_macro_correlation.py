"""
=============================================================================
  🌐 AGENT 4: INTER-MARKET MACRO CORRELATION AGENT
=============================================================================
Purpose:
  1. Tracks the US Dollar Index momentum via EURUSD and USDJPY inverse proxies.
  2. Tracks Precious Metals confluence via Silver (XAGUSD).
  3. Computes a real-time Macro Confluence Score (-100 to +100).
  4. Prevents active bots from buying into a surging Dollar breakout or selling
     into a plunging Dollar dump.

State File:
  `macro_confluence.json` (Read by active trading engines)
=============================================================================
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import time
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
STATE_FILE      = os.path.join(BASE_DIR, "macro_confluence.json")
LOG_FILE        = os.path.join(BASE_DIR, "logs", "macro_correlation.log")
LOOP_INTERVAL   = 15

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [MACRO-AGENT] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_symbol_trend(symbol, timeframe=mt5.TIMEFRAME_M15):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 50)
    if rates is None or len(rates) < 30:
        return 0, 0.0
    df = pd.DataFrame(rates)
    ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
    ema55 = df['close'].ewm(span=55, adjust=False).mean().iloc[-1]
    pct_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100.0
    trend = 1 if ema21 >= ema55 else -1
    return trend, pct_change

def evaluate_macro_confluence():
    # 1. Gold (XAUUSD) Trend
    gold_trend, gold_chg = get_symbol_trend("XAUUSD")

    # 2. EURUSD (Inverse proxy for USD strength: EUR down = USD up)
    eur_trend, eur_chg = get_symbol_trend("EURUSD")

    # 3. Silver (XAGUSD) Confluence (Usually leads Gold)
    silver_trend, silver_chg = get_symbol_trend("XAGUSD")

    # Confluence Calculation:
    # If EURUSD is falling (eur_trend == -1), USD is surging -> Strong Bearish headwind for Gold (-40 pts)
    # If EURUSD is rising (eur_trend == +1), USD is falling -> Bullish tailwind for Gold (+40 pts)
    # If Silver is aligned with Gold -> +30 pts in that direction
    score = 0
    if eur_trend < 0:
        score -= 45 # Strong USD
    elif eur_trend > 0:
        score += 45 # Weak USD

    if silver_trend > 0:
        score += 35 # Silver bullish
    elif silver_trend < 0:
        score -= 35 # Silver bearish

    if gold_trend > 0:
        score += 20
    elif gold_trend < 0:
        score -= 20

    score = max(-100, min(100, score))

    if score >= 40:
        regime = "STRONG_BULLISH_CONFLUENCE"
        recommendation = "PREFER_BUY_BASKETS"
    elif score <= -40:
        regime = "STRONG_BEARISH_CONFLUENCE"
        recommendation = "PREFER_SELL_BASKETS"
    else:
        regime = "NEUTRAL_CHOP_CONFLUENCE"
        recommendation = "BALANCED_DUAL_GRID"

    state = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "confluence_score": score,
        "regime": regime,
        "recommendation": recommendation,
        "eur_usd_momentum": round(eur_chg, 2),
        "silver_momentum": round(silver_chg, 2),
        "gold_momentum": round(gold_chg, 2)
    }

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving macro state: {e}")

    return state

def main():
    if not mt5.initialize():
        print("MT5 init failed in Macro Correlation Agent")
        sys.exit(1)

    log("=" * 65)
    log("  🌐 INTER-MARKET MACRO CORRELATION AGENT INITIALIZED")
    log("  Monitoring DXY / EURUSD, Silver, and Macro Confluence...")
    log("=" * 65)

    while True:
        try:
            state = evaluate_macro_confluence()
            if state:
                log(f"[MACRO PULSE] Score: {state['confluence_score']:+3d} | Regime: {state['regime']} | "
                    f"Rec: {state['recommendation']} | EUR: {state['eur_usd_momentum']:+.2f}% | Silver: {state['silver_momentum']:+.2f}%")
            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            log("Macro Correlation Agent stopped by user.")
            break
        except Exception as e:
            log(f"Macro Exception: {e}")
            time.sleep(5)

    mt5.shutdown()

if __name__ == "__main__":
    main()
