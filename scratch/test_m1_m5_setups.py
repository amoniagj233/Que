import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
from gold_intelligence import (
    get_gold_candles, compute_atr, compute_rsi, analyze_market_regime
)

def test_m1_m5_generation():
    if not mt5.initialize():
        print("MT5 init failed")
        return

    df_m1 = get_gold_candles("M1", 300)
    df_m5 = get_gold_candles("M5", 300)
    df_h1 = get_gold_candles("H1", 200)

    cur_p = float(df_m1["close"].iloc[-1])
    atr_m1 = float(compute_atr(df_m1, 14).iloc[-1])
    atr_m5 = float(compute_atr(df_m5, 14).iloc[-1])
    atr_h1 = float(compute_atr(df_h1, 14).iloc[-1]) if len(df_h1) >= 15 else 10.0
    rsi_m1 = float(compute_rsi(df_m1["close"], 14).iloc[-1])
    rsi_m5 = float(compute_rsi(df_m5["close"], 14).iloc[-1])

    h1_regime = analyze_market_regime(df_h1)
    trend_dir = h1_regime.get("direction", "SELL")
    if trend_dir not in ["BUY", "SELL"]:
        trend_dir = "SELL" if h1_regime.get("ema20", 0) <= h1_regime.get("ema50", 0) else "BUY"

    now_ts = int(time.time())

    # --- M1 Setup ---
    min_m1_stop = max(3.50, atr_m1 * 2.5)
    recent_m1_high = float(df_m1["high"].iloc[-10:].max())
    recent_m1_low = float(df_m1["low"].iloc[-10:].min())

    if trend_dir == "SELL":
        entry_m1 = cur_p
        sl_m1 = round(max(recent_m1_high + 0.5 * atr_m1, entry_m1 + min_m1_stop), 2)
        risk_m1 = sl_m1 - entry_m1
        m1_setup = {
            "id": f"GOLD_M1_SCALP_{now_ts}",
            "strategy": "M1 Sniper Scalp & Micro-Imbalance",
            "methodology": "High-Frequency Micro-Liquidity Sweep + Trend Flow",
            "bias": "BEARISH",
            "direction": "SELL",
            "timeframe": "M1",
            "entry_zone": f"{round(cur_p, 2)} - {round(recent_m1_high, 2)}",
            "entry": entry_m1,
            "sl": sl_m1,
            "tp1": round(entry_m1 - 1.5 * risk_m1, 2),
            "tp2": round(entry_m1 - 3.0 * risk_m1, 2),
            "tp3": round(entry_m1 - 5.0 * risk_m1, 2),
            "rr_ratio": "1:3.0",
            "confidence_score": 91,
            "quality": "ULTRA-FAST SCALP (91%)"
        }
    else:
        entry_m1 = cur_p
        sl_m1 = round(min(recent_m1_low - 0.5 * atr_m1, entry_m1 - min_m1_stop), 2)
        risk_m1 = entry_m1 - sl_m1
        m1_setup = {
            "id": f"GOLD_M1_SCALP_{now_ts}",
            "strategy": "M1 Sniper Scalp & Micro-Imbalance",
            "methodology": "High-Frequency Micro-Liquidity Sweep + Trend Flow",
            "bias": "BULLISH",
            "direction": "BUY",
            "timeframe": "M1",
            "entry_zone": f"{round(recent_m1_low, 2)} - {round(cur_p, 2)}",
            "entry": entry_m1,
            "sl": sl_m1,
            "tp1": round(entry_m1 + 1.5 * risk_m1, 2),
            "tp2": round(entry_m1 + 3.0 * risk_m1, 2),
            "tp3": round(entry_m1 + 5.0 * risk_m1, 2),
            "rr_ratio": "1:3.0",
            "confidence_score": 91,
            "quality": "ULTRA-FAST SCALP (91%)"
        }

    # --- M5 Setup ---
    ema9_m5 = float(df_m5["close"].ewm(span=9, adjust=False).mean().iloc[-1])
    ema21_m5 = float(df_m5["close"].ewm(span=21, adjust=False).mean().iloc[-1])
    min_m5_stop = max(4.50, atr_m5 * 2.0)

    if trend_dir == "SELL":
        entry_m5 = cur_p
        sl_m5 = round(max(ema21_m5 + 1.2 * atr_m5, entry_m5 + min_m5_stop), 2)
        risk_m5 = sl_m5 - entry_m5
        m5_setup = {
            "id": f"GOLD_M5_MOMENTUM_{now_ts}",
            "strategy": "M5 Momentum Impulse & Dynamic EMA Pullback",
            "methodology": "M5 EMA9/EMA21 Trend Confirmation + Volume Retest",
            "bias": "BEARISH",
            "direction": "SELL",
            "timeframe": "M5",
            "entry_zone": f"{round(cur_p, 2)} - {round(ema21_m5, 2)}",
            "entry": entry_m5,
            "sl": sl_m5,
            "tp1": round(entry_m5 - 1.8 * risk_m5, 2),
            "tp2": round(entry_m5 - 3.5 * risk_m5, 2),
            "tp3": round(entry_m5 - 5.5 * risk_m5, 2),
            "rr_ratio": "1:3.5",
            "confidence_score": 93,
            "quality": "SHORT-TERM MOMENTUM (93%)"
        }
    else:
        entry_m5 = cur_p
        sl_m5 = round(min(ema21_m5 - 1.2 * atr_m5, entry_m5 - min_m5_stop), 2)
        risk_m5 = entry_m5 - sl_m5
        m5_setup = {
            "id": f"GOLD_M5_MOMENTUM_{now_ts}",
            "strategy": "M5 Momentum Impulse & Dynamic EMA Pullback",
            "methodology": "M5 EMA9/EMA21 Trend Confirmation + Volume Retest",
            "bias": "BULLISH",
            "direction": "BUY",
            "timeframe": "M5",
            "entry_zone": f"{round(ema21_m5, 2)} - {round(cur_p, 2)}",
            "entry": entry_m5,
            "sl": sl_m5,
            "tp1": round(entry_m5 + 1.8 * risk_m5, 2),
            "tp2": round(entry_m5 + 3.5 * risk_m5, 2),
            "tp3": round(entry_m5 + 5.5 * risk_m5, 2),
            "rr_ratio": "1:3.5",
            "confidence_score": 93,
            "quality": "SHORT-TERM MOMENTUM (93%)"
        }

    print("M1 Setup:")
    print(m1_setup)
    print("\nM5 Setup:")
    print(m5_setup)

    mt5.shutdown()

if __name__ == '__main__':
    test_m1_m5_generation()
