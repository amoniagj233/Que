"""
Headway Institutional Quantitative Backtest Laboratory
======================================================
Automated systematic backtesting engine for Headway MT5 symbols:
- Fetches and caches historical bars (M15 & H1) for Crypto, Synthetics, Forex, Metals.
- Simulates realistic 2-trade execution (TP1 + TP2 runner with break-even move).
- Simulates the user's Profit Guardian (lock-in when profit >= $10, trailing ratchet with max giveback).
- Deducts broker spread and evaluates exact dollar P&L using broker contract sizes.
- Sweeps multiple strategy archetypes and parameters to identify high-expectancy profitable setups.
"""

import os
import json
import time
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Broker specs for Headway MT5 symbols
SYMBOL_SPECS = {
    "BTC": {"digits": 2, "point": 0.01, "contract_size": 1.0, "spread_pts": 15, "min_lot": 0.01},
    "ETH": {"digits": 2, "point": 0.01, "contract_size": 100.0, "spread_pts": 20, "min_lot": 0.01},
    "SOL": {"digits": 2, "point": 0.01, "contract_size": 1000.0, "spread_pts": 20, "min_lot": 0.01},
    "DOGE": {"digits": 5, "point": 0.00001, "contract_size": 100000.0, "spread_pts": 10, "min_lot": 0.01},
    "XRP": {"digits": 4, "point": 0.0001, "contract_size": 10000.0, "spread_pts": 10, "min_lot": 0.01},
    "BOOM_100": {"digits": 0, "point": 1.0, "contract_size": 1.0, "spread_pts": 15, "min_lot": 0.01},
    "CRASH_100": {"digits": 0, "point": 1.0, "contract_size": 1.0, "spread_pts": 13, "min_lot": 0.01},
    "VOL_10": {"digits": 0, "point": 1.0, "contract_size": 1.0, "spread_pts": 8, "min_lot": 0.01},
    "VOL_20": {"digits": 0, "point": 1.0, "contract_size": 1.0, "spread_pts": 17, "min_lot": 0.01},
    "XAUUSD": {"digits": 2, "point": 0.01, "contract_size": 100.0, "spread_pts": 380, "min_lot": 0.01},
    "EURUSD": {"digits": 5, "point": 0.00001, "contract_size": 100000.0, "spread_pts": 35, "min_lot": 0.01},
    "US500": {"digits": 2, "point": 0.01, "contract_size": 10.0, "spread_pts": 120, "min_lot": 0.01},
}

TIMEFRAME_MAP = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
}

def fetch_and_cache_data(symbols: List[str], timeframes: List[str] = ["M15", "H1"], count: int = 5000) -> Dict[str, pd.DataFrame]:
    """Connects to MT5, fetches historical candles, and caches them to disk as CSV."""
    datasets = {}
    connected = mt5.initialize()
    if not connected:
        print("[!] MT5 initialization failed. Trying cached files...")
    
    for s in symbols:
        for tf in timeframes:
            cache_file = CACHE_DIR / f"{s}_{tf}_{count}.csv"
            df = None
            if cache_file.exists():
                # Read from disk cache if fresh (< 2 hours old)
                age = time.time() - cache_file.stat().st_mtime
                if age < 7200:
                    df = pd.read_csv(cache_file)
                    datasets[f"{s}_{tf}"] = df
                    continue
            
            if connected:
                mt5.symbol_select(s, True)
                tf_code = TIMEFRAME_MAP.get(tf.upper(), mt5.TIMEFRAME_M15)
                rates = mt5.copy_rates_from_pos(s, tf_code, 0, count)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
                    df = df[["time", "open", "high", "low", "close", "tick_volume"]]
                    df.to_csv(cache_file, index=False)
                    datasets[f"{s}_{tf}"] = df
                    print(f"[+] Cached {s} {tf}: {len(df)} bars")
                else:
                    if cache_file.exists():
                        df = pd.read_csv(cache_file)
                        datasets[f"{s}_{tf}"] = df
            else:
                if cache_file.exists():
                    df = pd.read_csv(cache_file)
                    datasets[f"{s}_{tf}"] = df
                    
    if connected:
        mt5.shutdown()
        
    return datasets

# Indicator calculation utilities
def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calc_bollinger(series: pd.Series, period: int = 20, mult: float = 2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + mult * std
    lower = mid - mult * std
    return mid, upper, lower

def simulate_2trade_execution(
    df: pd.DataFrame,
    signals: pd.Series, # 1 for BUY, -1 for SELL, 0 for None
    symbol: str,
    sl_atr_mult: float = 1.8,
    tp1_atr_mult: float = 2.0,
    tp2_atr_mult: float = 4.5,
    profit_guardian_armed: bool = True,
    pg_activation_usd: float = 10.0,
    pg_giveback_pct: float = 0.35,
    fixed_lot: float = 0.01,
    max_hold_bars: int = 80
) -> Dict[str, Any]:
    """
    Simulates real Headway 2-Trade setup execution with:
    - Leg 1: Closes at TP1. Once TP1 hits, SL moves to Break-Even for Leg 2.
    - Leg 2: Closes at TP2 (runner).
    - Profit Guardian: If group floating profit >= $10.00, trails profit with max giveback.
    - Sized with exact contract sizes and broker spread.
    """
    spec = SYMBOL_SPECS.get(symbol, {"contract_size": 1.0, "point": 0.01, "spread_pts": 10})
    contract_size = spec["contract_size"]
    point = spec["point"]
    spread_cost = spec["spread_pts"] * point
    
    atr = calc_atr(df, 14).values
    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values
    closes = df["close"].values
    sig_vals = signals.values
    times = df["time"].values if "time" in df.columns else np.arange(len(df))
    
    n = len(df)
    trades = []
    in_pos = False
    pos_side = 0
    pos_entry = 0.0
    pos_sl = 0.0
    pos_tp1 = 0.0
    pos_tp2 = 0.0
    leg1_open = True
    leg2_open = True
    leg1_pnl = 0.0
    entry_idx = 0
    peak_profit = 0.0
    pg_armed = False
    
    for i in range(50, n - 1):
        # Manage existing active trade
        if in_pos:
            hold_bars = i - entry_idx
            bar_high = highs[i]
            bar_low = lows[i]
            bar_close = closes[i]
            
            # Leg 1 management
            if leg1_open:
                if pos_side == 1:
                    if bar_low <= pos_sl:
                        # Leg 1 Hit SL
                        loss = (pos_sl - pos_entry) * contract_size * fixed_lot
                        leg1_pnl = loss
                        leg1_open = False
                    elif bar_high >= pos_tp1:
                        # Leg 1 Hit TP1
                        win = (pos_tp1 - pos_entry) * contract_size * fixed_lot
                        leg1_pnl = win
                        leg1_open = False
                        # Move Leg 2 SL to Break-Even
                        pos_sl = pos_entry
                else: # SELL
                    if bar_high >= pos_sl:
                        # Leg 1 Hit SL
                        loss = (pos_entry - pos_sl) * contract_size * fixed_lot
                        leg1_pnl = loss
                        leg1_open = False
                    elif bar_low <= pos_tp1:
                        # Leg 1 Hit TP1
                        win = (pos_entry - pos_tp1) * contract_size * fixed_lot
                        leg1_pnl = win
                        leg1_open = False
                        # Move Leg 2 SL to Break-Even
                        pos_sl = pos_entry
            
            # Leg 2 & Profit Guardian management
            if leg2_open:
                # Calculate current floating profit of the group
                curr_leg2_float = (bar_close - pos_entry if pos_side == 1 else pos_entry - bar_close) * contract_size * fixed_lot
                total_float = (leg1_pnl if not leg1_open else curr_leg2_float) + curr_leg2_float
                
                if total_float > peak_profit:
                    peak_profit = total_float
                    
                if profit_guardian_armed:
                    if peak_profit >= pg_activation_usd:
                        pg_armed = True
                        
                    if pg_armed:
                        allowed_giveback = peak_profit * pg_giveback_pct
                        floor_profit = peak_profit - allowed_giveback
                        if total_float <= floor_profit:
                            # Profit Guardian trigger exit on Leg 2!
                            leg2_pnl = curr_leg2_float
                            leg2_open = False
                            total_trade_pnl = leg1_pnl + leg2_pnl
                            trades.append({
                                "entry_time": str(times[entry_idx]),
                                "exit_time": str(times[i]),
                                "side": "BUY" if pos_side == 1 else "SELL",
                                "entry_price": pos_entry,
                                "pnl": round(total_trade_pnl, 2),
                                "reason": "PROFIT_GUARDIAN",
                                "hold_bars": hold_bars
                            })
                            in_pos = False
                            continue
                
                # Hard TP2 and SL checks on Leg 2
                if pos_side == 1:
                    if bar_low <= pos_sl:
                        # Leg 2 Hit SL (or BE)
                        leg2_pnl = (pos_sl - pos_entry) * contract_size * fixed_lot
                        leg2_open = False
                    elif bar_high >= pos_tp2:
                        # Leg 2 Hit TP2 Runner
                        leg2_pnl = (pos_tp2 - pos_entry) * contract_size * fixed_lot
                        leg2_open = False
                else: # SELL
                    if bar_high >= pos_sl:
                        # Leg 2 Hit SL (or BE)
                        leg2_pnl = (pos_entry - pos_sl) * contract_size * fixed_lot
                        leg2_open = False
                    elif bar_low <= pos_tp2:
                        # Leg 2 Hit TP2 Runner
                        leg2_pnl = (pos_entry - pos_tp2) * contract_size * fixed_lot
                        leg2_open = False
            
            # Check if both legs closed
            if not leg1_open and not leg2_open:
                total_pnl = leg1_pnl + leg2_pnl
                trades.append({
                    "entry_time": str(times[entry_idx]),
                    "exit_time": str(times[i]),
                    "side": "BUY" if pos_side == 1 else "SELL",
                    "entry_price": pos_entry,
                    "pnl": round(total_pnl, 2),
                    "reason": "TARGET/STOP",
                    "hold_bars": hold_bars
                })
                in_pos = False
                continue
            
            # Time exit if held too long
            if hold_bars >= max_hold_bars:
                curr_exit = bar_close
                if leg1_open:
                    leg1_pnl = (curr_exit - pos_entry if pos_side == 1 else pos_entry - curr_exit) * contract_size * fixed_lot
                if leg2_open:
                    leg2_pnl = (curr_exit - pos_entry if pos_side == 1 else pos_entry - curr_exit) * contract_size * fixed_lot
                total_pnl = leg1_pnl + leg2_pnl
                trades.append({
                    "entry_time": str(times[entry_idx]),
                    "exit_time": str(times[i]),
                    "side": "BUY" if pos_side == 1 else "SELL",
                    "entry_price": pos_entry,
                    "pnl": round(total_pnl, 2),
                    "reason": "MAX_TIME",
                    "hold_bars": hold_bars
                })
                in_pos = False
                continue
            
            continue # still in position
        
        # Look for new signal
        sig = sig_vals[i]
        if sig != 0:
            nxt_open = opens[i + 1]
            c_atr = atr[i]
            if c_atr <= 0 or np.isnan(c_atr):
                continue
                
            in_pos = True
            pos_side = sig
            entry_idx = i + 1
            leg1_open = True
            leg2_open = True
            leg1_pnl = 0.0
            peak_profit = 0.0
            pg_armed = False
            
            if sig == 1: # BUY
                pos_entry = nxt_open + spread_cost
                pos_sl = pos_entry - sl_atr_mult * c_atr
                pos_tp1 = pos_entry + tp1_atr_mult * c_atr
                pos_tp2 = pos_entry + tp2_atr_mult * c_atr
            else: # SELL
                pos_entry = nxt_open
                pos_sl = pos_entry + sl_atr_mult * c_atr + spread_cost
                pos_tp1 = pos_entry - tp1_atr_mult * c_atr
                pos_tp2 = pos_entry - tp2_atr_mult * c_atr
                
    # Calculate performance metrics
    if not trades:
        return {"total_trades": 0, "net_profit": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0}
        
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    total_trades = len(trades)
    win_count = len(wins)
    win_rate = (win_count / total_trades) * 100.0
    net_profit = sum(pnls)
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0
    
    # Calculate Max Drawdown
    equity_curve = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity_curve)
    drawdowns = peak - equity_curve
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
    
    avg_trade = round(net_profit / total_trades, 2)
    
    return {
        "symbol": symbol,
        "total_trades": total_trades,
        "net_profit": round(net_profit, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": profit_factor,
        "max_drawdown": round(max_dd, 2),
        "avg_trade_usd": avg_trade,
        "trades": trades
    }

# ==========================================
# Strategy Implementations
# ==========================================

def strategy_trend_pullback_signals(
    df: pd.DataFrame,
    fast_ema: int = 20,
    slow_ema: int = 50,
    trend_ema: int = 200,
    rsi_buy_low: float = 40.0,
    rsi_buy_high: float = 52.0,
    rsi_sell_low: float = 48.0,
    rsi_sell_high: float = 60.0
) -> pd.Series:
    """Strategy 1: Multi-EMA Trend Filter + RSI Value Zone Pullback + MACD confirmation"""
    c = df["close"]
    ema_fast = c.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = c.ewm(span=slow_ema, adjust=False).mean()
    ema_trend = c.ewm(span=trend_ema, adjust=False).mean()
    rsi = calc_rsi(c, 14)
    _, _, macd_hist = calc_macd(c)
    
    signals = pd.Series(0, index=df.index)
    
    # Uptrend: Fast > Slow > Trend and Close > EMA200
    uptrend = (ema_fast > ema_slow) & (c > ema_trend) & (ema_slow > ema_trend)
    # Pullback to value: RSI in value pocket and MACD histogram turning upward
    macd_turning_up = macd_hist > macd_hist.shift(1)
    buy_cond = uptrend & (rsi >= rsi_buy_low) & (rsi <= rsi_buy_high) & macd_turning_up & (c > ema_fast * 0.99)
    
    # Downtrend: Fast < Slow < Trend and Close < EMA200
    downtrend = (ema_fast < ema_slow) & (c < ema_trend) & (ema_slow < ema_trend)
    macd_turning_dn = macd_hist < macd_hist.shift(1)
    sell_cond = downtrend & (rsi >= rsi_sell_low) & (rsi <= rsi_sell_high) & macd_turning_dn & (c < ema_fast * 1.01)
    
    signals[buy_cond] = 1
    signals[sell_cond] = -1
    return signals

def strategy_volatility_breakout_signals(
    df: pd.DataFrame,
    channel_period: int = 20,
    atr_mult_filter: float = 1.1
) -> pd.Series:
    """Strategy 2: Dynamic Donchian / Volatility Expansion Breakout"""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    atr = calc_atr(df, 14)
    atr_ma = atr.rolling(20).mean()
    
    upper_channel = high.shift(1).rolling(channel_period).max()
    lower_channel = low.shift(1).rolling(channel_period).min()
    
    signals = pd.Series(0, index=df.index)
    vol_expansion = atr > (atr_ma * atr_mult_filter)
    
    buy_breakout = (close > upper_channel) & vol_expansion
    sell_breakout = (close < lower_channel) & vol_expansion
    
    signals[buy_breakout] = 1
    signals[sell_breakout] = -1
    return signals

def strategy_pinbar_rejection_signals(
    df: pd.DataFrame,
    wick_ratio: float = 2.0,
    trend_ema_period: int = 100
) -> pd.Series:
    """Strategy 3: Institutional Pinbar / Wick Rejection aligned with dominant Trend"""
    c = df["close"]
    o = df["open"]
    h = df["high"]
    l = df["low"]
    
    body = (c - o).abs().replace(0, 1e-6)
    rng = (h - l).clip(lower=0)
    upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
    lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l
    
    ema_trend = c.ewm(span=trend_ema_period, adjust=False).mean()
    
    bullish_pin = (lower_wick >= wick_ratio * body) & (upper_wick < body) & (c > ema_trend) & (rng > 0)
    bearish_pin = (upper_wick >= wick_ratio * body) & (lower_wick < body) & (c < ema_trend) & (rng > 0)
    
    signals = pd.Series(0, index=df.index)
    signals[bullish_pin] = 1
    signals[bearish_pin] = -1
    return signals

def strategy_synthetic_asymmetry_signals(
    df: pd.DataFrame,
    symbol: str,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0
) -> pd.Series:
    """Strategy 4: Specialized Synthetic Crash/Boom & Volatility Index Edge"""
    c = df["close"]
    h = df["high"]
    l = df["low"]
    rsi = calc_rsi(c, 10)
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    atr = calc_atr(df, 14)
    
    signals = pd.Series(0, index=df.index)
    
    if "BOOM" in symbol:
        # BOOM indices spike UP and drift DOWN.
        # Edge A: Trend Shorting the steady down-drift after spike exhausts
        spike_exhaustion = (rsi > rsi_overbought) & (c < ema20)
        # Edge B: Breakout long when EMA20 crosses above EMA50 with expansion
        boom_uptrend = (ema20 > ema50) & (c > ema20) & (c.shift(1) <= ema20.shift(1))
        signals[spike_exhaustion] = -1
        signals[boom_uptrend] = 1
        
    elif "CRASH" in symbol:
        # CRASH indices drift UP and crash DOWN.
        # Edge A: Dip buying the steady upward recovery after a crash spike (RSI oversold snapback)
        crash_dip_buy = (rsi < rsi_oversold) & (c > l + 0.3 * (h - l))
        # Edge B: Riding upward trend
        crash_uptrend = (ema20 > ema50) & (c > ema20) & (rsi >= 45) & (rsi <= 65)
        signals[crash_dip_buy] = 1
        signals[crash_uptrend] = 1
        
    elif "VOL" in symbol:
        # Volatility Index: Mean Reversion off 2.5 Bollinger Bands + RSI Divergence
        mid, upper, lower = calc_bollinger(c, 20, 2.3)
        signals[(c < lower) & (rsi < 28)] = 1
        signals[(c > upper) & (rsi > 72)] = -1
        
    return signals

# ==========================================
# Continuous Backtest Optimizer
# ==========================================

def run_grid_search():
    """Runs high-speed systematic parameter sweeping across all symbols and models."""
    print("=" * 70)
    print("STARTING SYSTEMATIC BACKTEST OPTIMIZATION ENGINE")
    print("=" * 70)
    
    symbols = ["BTC", "ETH", "SOL", "BOOM_100", "CRASH_100", "VOL_10", "VOL_20", "XAUUSD", "EURUSD"]
    timeframes = ["M15", "H1"]
    
    print("[*] Fetching and caching historical candles...")
    datasets = fetch_and_cache_data(symbols, timeframes, count=5000)
    
    results = []
    
    for key, df in datasets.items():
        symbol, tf = key.split("_", 1)
        if len(df) < 500:
            continue
            
        print(f"\n---> Analyzing {symbol} ({tf}) [{len(df)} bars]...")
        
        # 1. Test Strategy 1: Trend Pullback Parameter Grid
        for sl_mult in [1.5, 1.8, 2.2]:
            for tp1_mult in [1.5, 2.0, 2.5]:
                for tp2_mult in [3.5, 4.5, 6.0]:
                    for rsi_low, rsi_high in [(38.0, 50.0), (42.0, 54.0)]:
                        sigs = strategy_trend_pullback_signals(
                            df, fast_ema=20, slow_ema=50, trend_ema=200,
                            rsi_buy_low=rsi_low, rsi_buy_high=rsi_high,
                            rsi_sell_low=100-rsi_high, rsi_sell_high=100-rsi_low
                        )
                        res = simulate_2trade_execution(
                            df, sigs, symbol,
                            sl_atr_mult=sl_mult, tp1_atr_mult=tp1_mult, tp2_atr_mult=tp2_mult,
                            profit_guardian_armed=True, pg_activation_usd=10.0, pg_giveback_pct=0.35
                        )
                        if res["total_trades"] >= 20 and res["profit_factor"] >= 1.3:
                            results.append({
                                "strategy": "Trend Pullback",
                                "symbol": symbol,
                                "timeframe": tf,
                                "params": f"SL={sl_mult}x, TP1={tp1_mult}x, TP2={tp2_mult}x, RSI=[{rsi_low},{rsi_high}]",
                                "trades": res["total_trades"],
                                "win_rate": res["win_rate"],
                                "net_profit": res["net_profit"],
                                "profit_factor": res["profit_factor"],
                                "max_drawdown": res["max_drawdown"],
                                "avg_trade": res["avg_trade_usd"]
                            })
                            
        # 2. Test Strategy 2: Volatility Breakout Grid
        for chan in [15, 20, 30]:
            for sl_mult in [1.5, 2.0]:
                for tp1_mult in [2.0, 2.5]:
                    for tp2_mult in [4.0, 5.5]:
                        sigs = strategy_volatility_breakout_signals(df, channel_period=chan)
                        res = simulate_2trade_execution(
                            df, sigs, symbol,
                            sl_atr_mult=sl_mult, tp1_atr_mult=tp1_mult, tp2_atr_mult=tp2_mult,
                            profit_guardian_armed=True, pg_activation_usd=10.0, pg_giveback_pct=0.35
                        )
                        if res["total_trades"] >= 20 and res["profit_factor"] >= 1.3:
                            results.append({
                                "strategy": "Volatility Breakout",
                                "symbol": symbol,
                                "timeframe": tf,
                                "params": f"Chan={chan}, SL={sl_mult}x, TP1={tp1_mult}x, TP2={tp2_mult}x",
                                "trades": res["total_trades"],
                                "win_rate": res["win_rate"],
                                "net_profit": res["net_profit"],
                                "profit_factor": res["profit_factor"],
                                "max_drawdown": res["max_drawdown"],
                                "avg_trade": res["avg_trade_usd"]
                            })

        # 3. Test Strategy 3: Pinbar Rejection
        for wick in [1.8, 2.2, 2.5]:
            for sl_mult in [1.5, 2.0]:
                for tp1_mult in [2.0, 2.5]:
                    for tp2_mult in [4.0, 5.0]:
                        sigs = strategy_pinbar_rejection_signals(df, wick_ratio=wick)
                        res = simulate_2trade_execution(
                            df, sigs, symbol,
                            sl_atr_mult=sl_mult, tp1_atr_mult=tp1_mult, tp2_atr_mult=tp2_mult,
                            profit_guardian_armed=True, pg_activation_usd=10.0, pg_giveback_pct=0.35
                        )
                        if res["total_trades"] >= 15 and res["profit_factor"] >= 1.3:
                            results.append({
                                "strategy": "Pinbar Rejection",
                                "symbol": symbol,
                                "timeframe": tf,
                                "params": f"Wick={wick}, SL={sl_mult}x, TP1={tp1_mult}x, TP2={tp2_mult}x",
                                "trades": res["total_trades"],
                                "win_rate": res["win_rate"],
                                "net_profit": res["net_profit"],
                                "profit_factor": res["profit_factor"],
                                "max_drawdown": res["max_drawdown"],
                                "avg_trade": res["avg_trade_usd"]
                            })

        # 4. Test Strategy 4: Synthetic Asymmetry (if synthetic index)
        if any(tag in symbol for tag in ["BOOM", "CRASH", "VOL"]):
            for sl_mult in [1.5, 2.0]:
                for tp1_mult in [1.8, 2.5]:
                    for tp2_mult in [3.5, 5.0]:
                        sigs = strategy_synthetic_asymmetry_signals(df, symbol)
                        res = simulate_2trade_execution(
                            df, sigs, symbol,
                            sl_atr_mult=sl_mult, tp1_atr_mult=tp1_mult, tp2_atr_mult=tp2_mult,
                            profit_guardian_armed=True, pg_activation_usd=10.0, pg_giveback_pct=0.35
                        )
                        if res["total_trades"] >= 15 and res["profit_factor"] >= 1.3:
                            results.append({
                                "strategy": "Synthetic Edge",
                                "symbol": symbol,
                                "timeframe": tf,
                                "params": f"SL={sl_mult}x, TP1={tp1_mult}x, TP2={tp2_mult}x",
                                "trades": res["total_trades"],
                                "win_rate": res["win_rate"],
                                "net_profit": res["net_profit"],
                                "profit_factor": res["profit_factor"],
                                "max_drawdown": res["max_drawdown"],
                                "avg_trade": res["avg_trade_usd"]
                            })

    # Save and rank all results
    res_df = pd.DataFrame(results)
    if not res_df.empty:
        # Sort by Net Profit and Profit Factor
        res_df = res_df.sort_values(by=["net_profit", "profit_factor"], ascending=[False, False])
        res_df.to_csv("backtest_results_ranked.csv", index=False)
        print("\n" + "=" * 80)
        print("TOP 20 MOST PROFITABLE STRATEGY CONFIGURATIONS FOUND:")
        print("=" * 80)
        print(res_df.head(20).to_string(index=False))
        
        # Save JSON artifact
        top_configs = res_df.head(25).to_dict(orient="records")
        with open("best_strategy_configs.json", "w") as f:
            json.dump(top_configs, f, indent=2)
            
        print("\n[+] Saved ranked results to 'backtest_results_ranked.csv' and 'best_strategy_configs.json'")
    else:
        print("[!] No configurations met the minimum trade count / profit factor filters.")

if __name__ == "__main__":
    run_grid_search()
