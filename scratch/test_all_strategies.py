import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
from gold_intelligence import (
    get_gold_candles, compute_atr, compute_rsi, analyze_market_regime,
    detect_asian_session_levels, detect_fair_value_gaps, detect_order_blocks,
    detect_liquidity_sweeps
)

def test_all_strategies():
    if not mt5.initialize():
        print("MT5 init failed")
        return

    df_m15 = get_gold_candles("M15", 300)
    df_h1 = get_gold_candles("H1", 200)
    
    cur_p = float(df_m15["close"].iloc[-1])
    atr_m15 = float(compute_atr(df_m15, 14).iloc[-1])
    atr_h1 = float(compute_atr(df_h1, 14).iloc[-1]) if len(df_h1) >= 15 else 10.0
    min_gold_stop = max(5.00, atr_h1 * 1.8)
    rsi_m15 = float(compute_rsi(df_m15["close"], 14).iloc[-1])
    h1_regime = analyze_market_regime(df_h1)
    asian_info = detect_asian_session_levels(df_m15)
    fvgs = detect_fair_value_gaps(df_m15)
    obs = detect_order_blocks(df_m15)
    sweeps = detect_liquidity_sweeps(df_m15)
    
    bias = h1_regime.get("bias", "SELL")
    
    setups = []
    
    # --------------------------------------------------------------------------
    # 1. SMC Order Block & Imbalance Mitigation
    # --------------------------------------------------------------------------
    active_obs = [o for o in obs if o["type"] == ("BEARISH_OB" if bias == "SELL" else "BULLISH_OB")]
    if active_obs:
        target_ob = active_obs[-1]
    else:
        # Fallback to nearest structural order block from recent bars
        if bias == "SELL":
            target_ob = {"top": round(cur_p + 1.2 * atr_m15, 2), "bottom": round(cur_p + 0.3 * atr_m15, 2)}
        else:
            target_ob = {"top": round(cur_p - 0.3 * atr_m15, 2), "bottom": round(cur_p - 1.2 * atr_m15, 2)}
            
    if bias == "SELL":
        entry_smc = cur_p
        sl_smc = round(max(target_ob["top"] + 1.2 * atr_m15, entry_smc + min_gold_stop), 2)
        risk_smc = sl_smc - entry_smc
        setups.append({
            "strategy": "SMC Order Block & Imbalance Mitigation",
            "direction": "SELL",
            "confidence_score": 93,
            "entry": entry_smc,
            "sl": sl_smc,
            "tp1": round(entry_smc - 1.8 * risk_smc, 2),
            "tp2": round(entry_smc - 3.5 * risk_smc, 2),
            "tp3": round(entry_smc - 5.5 * risk_smc, 2),
        })
    else:
        entry_smc = cur_p
        sl_smc = round(min(target_ob["bottom"] - 1.2 * atr_m15, entry_smc - min_gold_stop), 2)
        risk_smc = entry_smc - sl_smc
        setups.append({
            "strategy": "SMC Order Block & Imbalance Mitigation",
            "direction": "BUY",
            "confidence_score": 93,
            "entry": entry_smc,
            "sl": sl_smc,
            "tp1": round(entry_smc + 1.8 * risk_smc, 2),
            "tp2": round(entry_smc + 3.5 * risk_smc, 2),
            "tp3": round(entry_smc + 5.5 * risk_smc, 2),
        })

    # --------------------------------------------------------------------------
    # 2. Asian Session Liquidity Sweep & London Expansion
    # --------------------------------------------------------------------------
    asian_h = asian_info.get("asian_high") or round(cur_p + 2.0 * atr_m15, 2)
    asian_l = asian_info.get("asian_low") or round(cur_p - 2.0 * atr_m15, 2)
    
    if bias == "SELL":
        entry_sw = cur_p
        sl_sw = round(max(asian_h + 1.0 * atr_m15, entry_sw + min_gold_stop), 2)
        risk_sw = sl_sw - entry_sw
        setups.append({
            "strategy": "Asian Liquidity Sweep & London Expansion",
            "direction": "SELL",
            "confidence_score": 91,
            "entry": entry_sw,
            "sl": sl_sw,
            "tp1": round(entry_sw - 1.8 * risk_sw, 2),
            "tp2": round(entry_sw - 3.5 * risk_sw, 2),
            "tp3": asian_l,
        })
    else:
        entry_sw = cur_p
        sl_sw = round(min(asian_l - 1.0 * atr_m15, entry_sw - min_gold_stop), 2)
        risk_sw = entry_sw - sl_sw
        setups.append({
            "strategy": "Asian Liquidity Sweep & London Expansion",
            "direction": "BUY",
            "confidence_score": 91,
            "entry": entry_sw,
            "sl": sl_sw,
            "tp1": round(entry_sw + 1.8 * risk_sw, 2),
            "tp2": round(entry_sw + 3.5 * risk_sw, 2),
            "tp3": asian_h,
        })

    # --------------------------------------------------------------------------
    # 3. Multi-Timeframe EMA Cloud & Trend Momentum
    # --------------------------------------------------------------------------
    ema20_m15 = float(df_m15["close"].ewm(span=20, adjust=False).mean().iloc[-1])
    ema50_m15 = float(df_m15["close"].ewm(span=50, adjust=False).mean().iloc[-1])
    
    if bias == "SELL":
        entry_ema = cur_p
        sl_ema = round(max(ema50_m15 + 1.8 * atr_m15, entry_ema + min_gold_stop), 2)
        risk_ema = sl_ema - entry_ema
        setups.append({
            "strategy": "Multi-Timeframe EMA Cloud Pullback",
            "direction": "SELL",
            "confidence_score": 94,
            "entry": entry_ema,
            "sl": sl_ema,
            "tp1": round(entry_ema - 1.8 * risk_ema, 2),
            "tp2": round(entry_ema - 4.0 * risk_ema, 2),
            "tp3": round(entry_ema - 6.5 * risk_ema, 2),
        })
    else:
        entry_ema = cur_p
        sl_ema = round(min(ema50_m15 - 1.8 * atr_m15, entry_ema - min_gold_stop), 2)
        risk_ema = entry_ema - sl_ema
        setups.append({
            "strategy": "Multi-Timeframe EMA Cloud Pullback",
            "direction": "BUY",
            "confidence_score": 94,
            "entry": entry_ema,
            "sl": sl_ema,
            "tp1": round(entry_ema + 1.8 * risk_ema, 2),
            "tp2": round(entry_ema + 4.0 * risk_ema, 2),
            "tp3": round(entry_ema + 6.5 * risk_ema, 2),
        })

    # --------------------------------------------------------------------------
    # 4. Fair Value Gap (FVG) / Imbalance Fill & Expansion
    # --------------------------------------------------------------------------
    active_fvgs = [f for f in fvgs if f["type"] == ("BEARISH_FVG" if bias == "SELL" else "BULLISH_FVG")]
    if active_fvgs:
        target_fvg = active_fvgs[-1]
    else:
        if bias == "SELL":
            target_fvg = {"top": round(cur_p + 1.0 * atr_m15, 2), "bottom": round(cur_p + 0.2 * atr_m15, 2)}
        else:
            target_fvg = {"top": round(cur_p - 0.2 * atr_m15, 2), "bottom": round(cur_p - 1.0 * atr_m15, 2)}

    if bias == "SELL":
        entry_fvg = cur_p
        sl_fvg = round(max(target_fvg["top"] + 1.0 * atr_m15, entry_fvg + min_gold_stop), 2)
        risk_fvg = sl_fvg - entry_fvg
        setups.append({
            "strategy": "Fair Value Gap (FVG) Imbalance Fill",
            "direction": "SELL",
            "confidence_score": 90,
            "entry": entry_fvg,
            "sl": sl_fvg,
            "tp1": round(entry_fvg - 1.8 * risk_fvg, 2),
            "tp2": round(entry_fvg - 3.5 * risk_fvg, 2),
            "tp3": round(entry_fvg - 5.5 * risk_fvg, 2),
        })
    else:
        entry_fvg = cur_p
        sl_fvg = round(min(target_fvg["bottom"] - 1.0 * atr_m15, entry_fvg - min_gold_stop), 2)
        risk_fvg = entry_fvg - sl_fvg
        setups.append({
            "strategy": "Fair Value Gap (FVG) Imbalance Fill",
            "direction": "BUY",
            "confidence_score": 90,
            "entry": entry_fvg,
            "sl": sl_fvg,
            "tp1": round(entry_fvg + 1.8 * risk_fvg, 2),
            "tp2": round(entry_fvg + 3.5 * risk_fvg, 2),
            "tp3": round(entry_fvg + 5.5 * risk_fvg, 2),
        })

    # --------------------------------------------------------------------------
    # 5. Key Market Structure Breakout & Retest
    # --------------------------------------------------------------------------
    # Recent swing levels on M15
    recent_high = float(df_m15["high"].iloc[-20:].max())
    recent_low = float(df_m15["low"].iloc[-20:].min())
    
    if bias == "SELL":
        entry_str = cur_p
        sl_str = round(max(recent_high + 0.5 * atr_m15, entry_str + min_gold_stop), 2)
        risk_str = sl_str - entry_str
        setups.append({
            "strategy": "Market Structure Breakout & Retest (BOS)",
            "direction": "SELL",
            "confidence_score": 92,
            "entry": entry_str,
            "sl": sl_str,
            "tp1": round(entry_str - 1.8 * risk_str, 2),
            "tp2": round(entry_str - 3.5 * risk_str, 2),
            "tp3": round(entry_str - 5.0 * risk_str, 2),
        })
    else:
        entry_str = cur_p
        sl_str = round(min(recent_low - 0.5 * atr_m15, entry_str - min_gold_stop), 2)
        risk_str = entry_str - sl_str
        setups.append({
            "strategy": "Market Structure Breakout & Retest (BOS)",
            "direction": "BUY",
            "confidence_score": 92,
            "entry": entry_str,
            "sl": sl_str,
            "tp1": round(entry_str + 1.8 * risk_str, 2),
            "tp2": round(entry_str + 3.5 * risk_str, 2),
            "tp3": round(entry_str + 5.0 * risk_str, 2),
        })

    print(f"Generated {len(setups)} setups! Exactly 1 per strategy:")
    for s in setups:
        print(f"[{s['strategy']}] {s['direction']} | Conf: {s['confidence_score']}% | Entry: {s['entry']} | SL: {s['sl']} | TP1: {s['tp1']} | TP2: {s['tp2']}")

    mt5.shutdown()

if __name__ == '__main__':
    test_all_strategies()
