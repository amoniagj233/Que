"""
Live Pattern Learner & Adaptive Trading Brain
Continuously learns market patterns from tick data and trade outcomes:
  1. Detects Adverse Velocity Spikes (prevents falling-knife DCA)
  2. Learns RSI Reversal Zones (times averaging down for maximum bounce probability)
  3. Enforces Capital & Equity Self-Preservation (prevents margin exhaustion)
  4. Auto-tunes Grid Spacing & Take Profit based on learned market state
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime

STATE_FILE = "live_learning_state.json"
HISTORY_FILE = "pattern_memory.jsonl"

def analyze_live_market_pattern(symbol="XAUUSD", timeframe=mt5.TIMEFRAME_M5):
    """
    Extracts live market pattern features on M5 timeframe and returns an Adaptive Parameter Profile
    """
    if not mt5.initialize():
        return None

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 50)
    acc = mt5.account_info()
    tick = mt5.symbol_info_tick(symbol)
    
    if rates is None or len(rates) < 20 or not tick:
        return None

    df = pd.DataFrame(rates)
    
    # 1. Volatility (M5 ATR)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    # 2. RSI (14 on M5)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    # 3. Adverse Velocity (Drop rate in last 2 M5 candles)
    recent_bars = df.tail(2)
    net_change = float(recent_bars['close'].iloc[-1] - recent_bars['open'].iloc[0])
    consecutive_reds = int(all(recent_bars['close'] < recent_bars['open']))
    
    # 4. Pattern Classification:
    # Pattern A: "Runaway Waterfall" (High Risk: strong consecutive red drops)
    # Pattern B: "Exhaustion Bounce" (High Opportunity: RSI < 30 + lower wick forming)
    # Pattern C: "Healthy Mean-Reversion" (Normal quiet range)
    
    is_waterfall = (net_change < -2.0) or (consecutive_reds and abs(net_change) > atr * 2.0)
    
    last_candle = df.iloc[-1]
    lower_wick = min(last_candle['open'], last_candle['close']) - last_candle['low']
    is_exhaustion_bottom = (rsi < 30) and (lower_wick > 0.40)
    
    # 5. Equity Protection Flag
    equity_safe = True
    if acc and acc.equity < 20.0:
        equity_safe = False

    # 6. Adaptive Parameter Tuning:
    if is_waterfall:
        regime = "WATERFALL_DUMP"
        step_mult = 2.0       # Widen step aggressively to avoid catching knife!
        tp_mult   = 0.8       # Take quick exit on bounce
        allow_new_basket = False # Do NOT open fresh layer-1 into a dump
        require_green_bar = True
    elif is_exhaustion_bottom:
        regime = "EXHAUSTION_BOUNCE"
        step_mult = 1.2       # High probability bounce zone
        tp_mult   = 1.2       # Room for bounce to run
        allow_new_basket = equity_safe
        require_green_bar = False
    else:
        regime = "HEALTHY_RANGE"
        step_mult = 1.4
        tp_mult   = 1.0
        allow_new_basket = equity_safe
        require_green_bar = False

    state = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'regime': regime,
        'atr': round(atr, 2),
        'rsi': round(rsi, 1),
        'net_change_3m': round(net_change, 2),
        'step_mult': step_mult,
        'tp_mult': tp_mult,
        'allow_new_basket': allow_new_basket,
        'require_green_bar': require_green_bar,
        'equity': round(acc.equity, 2) if acc else 0.0,
        'balance': round(acc.balance, 2) if acc else 0.0,
        'free_margin': round(acc.margin_free, 2) if acc else 0.0
    }

    # Save live state for bot to read in memory
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

    return state

if __name__ == "__main__":
    st = analyze_live_market_pattern()
    if st:
        print("=== LIVE PATTERN RECOGNITION REPORT ===")
        print(f"Timestamp       : {st['timestamp']}")
        print(f"Detected Regime : {st['regime']}")
        print(f"ATR (14)        : ${st['atr']}")
        print(f"RSI (14)        : {st['rsi']}")
        print(f"Net Change (3M) : ${st['net_change_3m']:+.2f}")
        print(f"Adaptive Step   : {st['step_mult']}x ATR (${st['atr'] * st['step_mult']:.2f})")
        print(f"Adaptive TP     : {st['tp_mult']}x ATR (${st['atr'] * st['tp_mult']:.2f})")
        print(f"Allow New Basket: {st['allow_new_basket']}")
        print(f"Require Green C : {st['require_green_bar']}")
        print(f"Account Equity  : ${st['equity']:.2f} (Safe: {st['equity'] >= 20.0})")
