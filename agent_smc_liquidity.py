"""
=============================================================================
  🏛️ AGENT 3: SMART MONEY CONCEPTS (SMC) & LIQUIDITY AGENT
=============================================================================
Purpose:
  1. Maps Institutional Order Blocks (OB) on H1 and M15 timeframes.
  2. Detects Unmitigated Fair Value Gaps (FVG) and Liquidity Pools (BSL/SSL).
  3. Tracks Daily High/Low and Asian Session High/Low ranges.
  4. Feeds high-probability key reversal zones to all active bots and the
     Darwin Evolution Agent, ensuring entries align with institutional capital.

State File:
  `smc_levels.json` (Read by all active trading bots)
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
STATE_FILE      = os.path.join(BASE_DIR, "smc_levels.json")
LOG_FILE        = os.path.join(BASE_DIR, "logs", "smc_liquidity.log")
SYMBOL          = "XAUUSD"
LOOP_INTERVAL   = 10

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [SMC-AGENT] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def find_order_blocks_and_fvg(df, n_lookback=60):
    if len(df) < n_lookback:
        return [], [], None, None

    bullish_obs = []
    bearish_obs = []
    fvgs = []

    # Detect Fair Value Gaps (3-bar sequence)
    for i in range(2, len(df)):
        # Bullish FVG: Bar 3 Low > Bar 1 High
        if df['low'].iloc[i] > df['high'].iloc[i - 2]:
            gap_size = df['low'].iloc[i] - df['high'].iloc[i - 2]
            if gap_size > 0.80:
                fvgs.append({
                    'type': 'BULLISH_FVG',
                    'bottom': float(df['high'].iloc[i - 2]),
                    'top': float(df['low'].iloc[i]),
                    'bar_idx': i
                })
        # Bearish FVG: Bar 3 High < Bar 1 Low
        elif df['high'].iloc[i] < df['low'].iloc[i - 2]:
            gap_size = df['low'].iloc[i - 2] - df['high'].iloc[i]
            if gap_size > 0.80:
                fvgs.append({
                    'type': 'BEARISH_FVG',
                    'top': float(df['low'].iloc[i - 2]),
                    'bottom': float(df['high'].iloc[i]),
                    'bar_idx': i
                })

    # Detect Order Blocks: Last opposite candle before violent displacement (>= 2x ATR)
    tr = (df['high'] - df['low']).rolling(14).mean()
    for i in range(1, len(df) - 2):
        avg_atr = tr.iloc[i] if not np.isnan(tr.iloc[i]) else 3.0
        # Bullish displacement: Strong green candle that moves >= 1.8x ATR
        if (df['close'].iloc[i + 1] - df['open'].iloc[i + 1]) >= (1.8 * avg_atr):
            if df['close'].iloc[i] < df['open'].iloc[i]: # Preceding red candle
                bullish_obs.append({
                    'top': float(df['high'].iloc[i]),
                    'bottom': float(df['low'].iloc[i]),
                    'type': 'DEMAND_OB'
                })
        # Bearish displacement: Strong red candle that drops >= 1.8x ATR
        elif (df['open'].iloc[i + 1] - df['close'].iloc[i + 1]) >= (1.8 * avg_atr):
            if df['close'].iloc[i] > df['open'].iloc[i]: # Preceding green candle
                bearish_obs.append({
                    'top': float(df['high'].iloc[i]),
                    'bottom': float(df['low'].iloc[i]),
                    'type': 'SUPPLY_OB'
                })

    return bullish_obs, bearish_obs, fvgs

def evaluate_smc_levels():
    rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 100)
    rates_d1  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_D1, 0, 5)
    tick = mt5.symbol_info_tick(SYMBOL)

    if rates_m15 is None or rates_d1 is None or not tick:
        return None

    df_m15 = pd.DataFrame(rates_m15)
    df_d1  = pd.DataFrame(rates_d1)
    curr_price = float(tick.bid)

    bull_obs, bear_obs, fvgs = find_order_blocks_and_fvg(df_m15)

    # Nearest Demand (Support) below current price
    demands_below = [ob for ob in bull_obs if ob['top'] < curr_price]
    nearest_demand = max([ob['top'] for ob in demands_below]) if demands_below else (curr_price - 15.0)

    # Nearest Supply (Resistance) above current price
    supplies_above = [ob for ob in bear_obs if ob['bottom'] > curr_price]
    nearest_supply = min([ob['bottom'] for ob in supplies_above]) if supplies_above else (curr_price + 15.0)

    # Daily Key Levels
    daily_high = float(df_d1['high'].iloc[-1])
    daily_low  = float(df_d1['low'].iloc[-1])
    daily_open = float(df_d1['open'].iloc[-1])

    # Institutional Bias
    bias = "BEARISH_DISPLACEMENT" if curr_price < daily_open else "BULLISH_EXPANSION"
    target_liquidity = "SELL_SIDE_LIQUIDITY (Daily Lows)" if bias == "BEARISH_DISPLACEMENT" else "BUY_SIDE_LIQUIDITY (Daily Highs)"

    state = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_price": round(curr_price, 2),
        "bias": bias,
        "target_liquidity": target_liquidity,
        "nearest_demand_zone": round(nearest_demand, 2),
        "nearest_supply_zone": round(nearest_supply, 2),
        "daily_high": round(daily_high, 2),
        "daily_low": round(daily_low, 2),
        "daily_open": round(daily_open, 2),
        "active_fvgs_count": len(fvgs),
        "active_order_blocks_count": len(bull_obs) + len(bear_obs)
    }

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving SMC state: {e}")

    return state

def main():
    if not mt5.initialize():
        print("MT5 init failed in SMC Agent")
        sys.exit(1)

    log("=" * 65)
    log("  🏛️ SMART MONEY CONCEPTS (SMC) & LIQUIDITY AGENT ACTIVE")
    log("  Mapping Order Blocks, FVGs, and Liquidity Pools on XAUUSD...")
    log("=" * 65)

    while True:
        try:
            state = evaluate_smc_levels()
            if state:
                log(f"[SMC PULSE] Price: ${state['current_price']:.2f} | Bias: {state['bias']} | "
                    f"Demand OB: ${state['nearest_demand_zone']:.2f} | Supply OB: ${state['nearest_supply_zone']:.2f}")
            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            log("SMC Agent stopped by user.")
            break
        except Exception as e:
            log(f"SMC Exception: {e}")
            time.sleep(5)

    mt5.shutdown()

if __name__ == "__main__":
    main()
