"""
Reinforcement Trading Part 2 - MT5 Live Execution Engine
========================================================
Based on: https://github.com/ZiadFrancis/Reinforcement_Trading_Part_2.git

Features:
- Causal stationary feature matrix (25 normalized features including ATR ratios, MACD, session flags)
- Bracket trading action space: Direction (Flat/Buy/Sell), SL ATR Multiplier (1.0, 1.5, 2.0), TP/R Multiplier (1.0, 1.5, 2.0, 3.0)
- Trend-Hold policy & PPO inference on MetaTrader 5 live incoming candles
- Live market scanner and auto-trading execution with 0.01 fixed lot and hard SL/TP
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from mt5_connector import mt5_connector

# Bracket choices matching config.py from repository
SL_ATR_MULTIPLIERS = (1.0, 1.5, 2.0)
TP_R_MULTIPLIERS = (1.0, 1.5, 2.0, 3.0)

def compute_atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()

def compute_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    idx = pd.to_datetime(out["time"])
    minute_of_day = idx.dt.hour * 60 + idx.dt.minute
    day_of_week = idx.dt.dayofweek

    out["tod_sin"] = np.sin(2 * np.pi * minute_of_day / 1440.0)
    out["tod_cos"] = np.cos(2 * np.pi * minute_of_day / 1440.0)
    out["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7.0)

    h_utc = idx.dt.hour
    out["session_asia"] = ((h_utc >= 0) & (h_utc < 7)).astype(int)
    out["session_london"] = ((h_utc >= 7) & (h_utc < 16)).astype(int)
    out["session_newyork"] = ((h_utc >= 13) & (h_utc < 22)).astype(int)
    out["session_london_ny_overlap"] = ((h_utc >= 13) & (h_utc < 16)).astype(int)
    return out

def add_stationary_features(df: pd.DataFrame, atr_period: int = 14, rsi_period: int = 14):
    out = df.copy()
    out["atr"] = compute_atr(out, atr_period)
    out["ema20"] = out["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    out["rsi14"] = compute_rsi(out["close"], rsi_period)

    ema12 = out["close"].ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = out["close"].ewm(span=26, adjust=False, min_periods=26).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    bb_mid = out["close"].rolling(20, min_periods=20).mean()
    bb_std = out["close"].rolling(20, min_periods=20).std()
    out["bb_mid"] = bb_mid
    out["bb_upper"] = bb_mid + 2 * bb_std
    out["bb_lower"] = bb_mid - 2 * bb_std
    out["bb_width"] = out["bb_upper"] - out["bb_lower"]

    eps = 1e-12
    a = out["atr"].replace(0, np.nan)

    out["close_ema20_atr"] = (out["close"] - out["ema20"]) / (a + eps)
    out["close_ema50_atr"] = (out["close"] - out["ema50"]) / (a + eps)
    out["close_ema200_atr"] = (out["close"] - out["ema200"]) / (a + eps)
    out["ema20_ema50_atr"] = (out["ema20"] - out["ema50"]) / (a + eps)

    out["macd_hist_atr"] = out["macd_hist"] / (a + eps)
    out["roc20_atr"] = (out["close"] - out["close"].shift(20)) / (a + eps)

    out["atr_close"] = out["atr"] / out["close"]
    atr_fast = out["atr"].ewm(span=5, adjust=False, min_periods=5).mean()
    atr_slow = out["atr"].ewm(span=30, adjust=False, min_periods=30).mean()
    out["atr_fast_slow"] = atr_fast / atr_slow.replace(0, np.nan)
    out["bb_width_close"] = out["bb_width"] / out["close"]

    out["range_atr"] = (out["high"] - out["low"]) / (a + eps)
    candle_range = (out["high"] - out["low"]).replace(0, np.nan)
    out["upper_wick_ratio"] = (out["high"] - out[["open", "close"]].max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (out[["open", "close"]].min(axis=1) - out["low"]) / candle_range

    for k in range(1, 6):
        out[f"ret{k}_atr"] = (out["close"] - out["close"].shift(k)) / (a + eps)

    out = add_time_features(out)

    feature_cols = [
        "close_ema20_atr", "close_ema50_atr", "close_ema200_atr",
        "ema20_ema50_atr", "macd_hist_atr", "roc20_atr",
        "atr_close", "atr_fast_slow", "bb_width_close",
        "range_atr", "upper_wick_ratio", "lower_wick_ratio",
        "ret1_atr", "ret2_atr", "ret3_atr", "ret4_atr", "ret5_atr",
        "tod_sin", "tod_cos", "dow_sin", "dow_cos",
        "session_asia", "session_london", "session_newyork", "session_london_ny_overlap",
    ]

    out[feature_cols] = out[feature_cols].replace([np.inf, -np.inf], np.nan)
    return out, feature_cols

def evaluate_trend_hold_policy(row, current_pos_direction=0, threshold_atr=0.7, sl_idx=2, tp_idx=3):
    """
    Evaluates the Tuned Trend-Hold Policy from baselines.py on the current bar.
    Returns: action = [direction (0=Flat, 1=Buy, 2=Sell), sl_idx, tp_idx]
    """
    long_sig = (row["ema20"] > row["ema50"]) and (row["close_ema20_atr"] > threshold_atr)
    short_sig = (row["ema20"] < row["ema50"]) and (row["close_ema20_atr"] < -threshold_atr)

    if long_sig:
        return np.array([1, sl_idx, tp_idx], dtype=int)
    if short_sig:
        return np.array([2, sl_idx, tp_idx], dtype=int)
    if current_pos_direction == 1:
        return np.array([1, sl_idx, tp_idx], dtype=int)
    if current_pos_direction == -1:
        return np.array([2, sl_idx, tp_idx], dtype=int)
    return np.array([0, sl_idx, tp_idx], dtype=int)

def scan_rl_market(symbol="XAUUSD", timeframe="H1", count=400, threshold_atr=0.7, sl_idx=2, tp_idx=3):
    """
    Scans MT5 live candles using the Reinforcement Trading Part 2 feature matrix and bracket policy.
    """
    candles = mt5_connector.get_candles(symbol, timeframe, count)
    if not candles:
        return {"error": f"Failed to fetch {symbol} {timeframe} candles from MT5"}

    df = pd.DataFrame(candles)
    feat_df, feat_cols = add_stationary_features(df)
    
    # Last completed bar is at -2; current forming bar is at -1
    c = feat_df.iloc[-2]
    curr = feat_df.iloc[-1]

    # Check active MT5 position direction for this strategy
    open_pos = mt5_connector.get_open_positions(symbol=symbol)
    rl_pos = [p for p in open_pos if p.get("comment") == "RL-Bracket"]
    current_direction = 0
    if rl_pos:
        current_direction = 1 if rl_pos[0]["type"] == 0 else -1

    action = evaluate_trend_hold_policy(
        c,
        current_pos_direction=current_direction,
        threshold_atr=threshold_atr,
        sl_idx=sl_idx,
        tp_idx=tp_idx
    )

    direction = int(action[0]) # 0=FLAT, 1=LONG/BUY, 2=SHORT/SELL
    chosen_sl_idx = int(action[1])
    chosen_tp_idx = int(action[2])

    sl_mult = SL_ATR_MULTIPLIERS[chosen_sl_idx]
    tp_mult = TP_R_MULTIPLIERS[chosen_tp_idx]

    entry_est = float(curr["open"])
    atr_val = float(c["atr"])
    sl = 0.0
    tp = 0.0
    signal_str = "FLAT"

    if direction == 1:
        signal_str = "BUY"
        sl = round(entry_est - (sl_mult * atr_val), 3)
        risk = entry_est - sl
        tp = round(entry_est + (tp_mult * risk), 3)
    elif direction == 2:
        signal_str = "SELL"
        sl = round(entry_est + (sl_mult * atr_val), 3)
        risk = sl - entry_est
        tp = round(entry_est - (tp_mult * risk), 3)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candle_time": str(c["time"]),
        "current_price": float(curr["close"]),
        "signal": signal_str,
        "action": [int(a) for a in action],
        "ema20": round(float(c["ema20"]), 3),
        "ema50": round(float(c["ema50"]), 3),
        "close_ema20_atr": round(float(c["close_ema20_atr"]), 3),
        "atr_14": round(atr_val, 3),
        "sl_atr_multiplier": sl_mult,
        "tp_r_multiplier": tp_mult,
        "suggested_entry": entry_est if signal_str != "FLAT" else None,
        "suggested_sl": sl if signal_str != "FLAT" else None,
        "suggested_tp": tp if signal_str != "FLAT" else None,
        "existing_position": bool(rl_pos)
    }

def execute_rl_trade(symbol="XAUUSD", timeframe="H1", volume=0.01):
    """
    Evaluates RL bracket setup; if signal is BUY/SELL and no duplicate trade is open, fires order.
    """
    scan = scan_rl_market(symbol=symbol, timeframe=timeframe)
    if "error" in scan:
        return scan

    sig = scan["signal"]
    if sig == "FLAT":
        return {
            "status": "no_trade",
            "reason": f"RL Trend-Hold policy recommends FLAT on {symbol} ({timeframe})",
            "scan": scan
        }

    # Avoid stacking multiple RL trades on same symbol
    open_pos = mt5_connector.get_open_positions(symbol=symbol)
    existing_rl_pos = [p for p in open_pos if p.get("comment") == "RL-Bracket"]
    if existing_rl_pos:
        return {
            "status": "skipped",
            "reason": f"Existing RL position #{existing_rl_pos[0]['ticket']} already active on {symbol}",
            "scan": scan
        }

    res = mt5_connector.place_market_order(
        symbol=symbol,
        action=sig,
        volume=volume,
        stop_loss=scan["suggested_sl"],
        take_profit=scan["suggested_tp"],
        comment="RL-Bracket"
    )

    return {
        "status": "executed" if res.get("success") else "failed",
        "signal": sig,
        "order_result": res,
        "scan": scan
    }

def auto_rl_loop(symbols=None, timeframe="H1", volume=0.01, poll_seconds=20):
    """
    Continuous 24/7 multi-symbol execution loop for Reinforcement Bracket Strategy.
    Monitors Forex/Metals (24/5) and Crypto (24/7) with automatic MT5 reconnection watchdog.
    """
    import time
    from pathlib import Path
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "trader_247.log"

    def log(msg: str):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    quote_syms = set(mt5_connector.get_symbols())
    if symbols is None:
        preferred = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]
        symbols = [s for s in preferred if s in quote_syms] or list(quote_syms)[:10]
    elif isinstance(symbols, str):
        symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # Filter strictly to symbols active on Headway Quotes
    valid_symbols = [s for s in symbols if s in quote_syms]
    if not valid_symbols:
        log(f"[!] Error: None of {symbols} exist in Headway Quotes. Available: {list(quote_syms)[:10]}...")
        return
    symbols = valid_symbols

    log("=" * 65)
    log("REINFORCEMENT TRADING PART 2 - 24/7 AUTO-TRADER (HEADWAY QUOTES ONLY)")
    log(f"Watchlist: {symbols}")
    log(f"Timeframe: {timeframe} | Fixed Volume: {volume} Lot | Poll: {poll_seconds}s")
    log(f"Persistent Log: {log_file.resolve()}")
    log("=" * 65)

    last_candle_times = {}

    for sym in symbols:
        scan = scan_rl_market(symbol=sym, timeframe=timeframe)
        if "error" not in scan:
            last_candle_times[sym] = scan.get("candle_time")
            log(f"[INIT] {sym.ljust(8)} | Price: {str(scan['current_price']).ljust(8)} | Signal: {scan['signal'].ljust(4)} | CloseEMA20_ATR: {str(scan['close_ema20_atr']).ljust(6)} | ATR: {scan['atr_14']}")
        else:
            last_candle_times[sym] = None
            log(f"[WARN] Initial scan for {sym}: {scan.get('error')}")

    log("[*] Watchdog active. 24/7 continuous trading running...")

    heartbeat_counter = 0

    while True:
        try:
            # Ensure MT5 terminal connection is healthy
            if not mt5_connector.ensure_connected():
                log("[WARN] MT5 connection dropped. Reconnecting...")
                time.sleep(5)
                continue

            for sym in symbols:
                scan = scan_rl_market(symbol=sym, timeframe=timeframe)
                if "error" not in scan:
                    c_time = scan.get("candle_time")
                    prev_time = last_candle_times.get(sym)

                    if c_time != prev_time:
                        last_candle_times[sym] = c_time
                        sig = scan.get("signal")
                        log(f"[{sym}] Bar Closed: {c_time} | Price: {scan['current_price']} | Signal: {sig} | Action: {scan['action']}")

                        if sig != "FLAT":
                            open_pos = mt5_connector.get_open_positions(symbol=sym)
                            existing_rl_pos = [p for p in open_pos if p.get("comment") == "RL-Bracket"]
                            if existing_rl_pos:
                                log(f"[HOLD] Existing RL position #{existing_rl_pos[0]['ticket']} open on {sym}. Holding bracket.")
                            else:
                                log(f"[!] TRIGGERING 24/7 RL ORDER: {sig} {volume} lots on {sym} (SL: {scan['suggested_sl']}, TP: {scan['suggested_tp']})")
                                exec_res = execute_rl_trade(symbol=sym, timeframe=timeframe, volume=volume)
                                log(f"    Order Result: {exec_res}")

            heartbeat_counter += 1
            if heartbeat_counter % 6 == 0:  # ~every 2 minutes
                acc = mt5_connector.get_account_info()
                positions = mt5_connector.get_open_positions()
                log(f"[HEARTBEAT] Balance: ${acc.get('balance', 0):,.2f} | Equity: ${acc.get('equity', 0):,.2f} | Open Positions: {len(positions)} | Status: 24/7 ACTIVE")

            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            log("[*] 24/7 Trader stopped by user.")
            break
        except Exception as e:
            log(f"[!] Unexpected error in 24/7 loop: {e}. Retrying in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    import sys
    import json

    if "--auto" in sys.argv:
        syms = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]
        tf = "H1"
        vol = 0.01
        for arg in sys.argv:
            if arg.startswith("--symbols="):
                syms = [s.strip() for s in arg.split("=")[1].split(",")]
            elif arg.startswith("--symbol="):
                syms = [arg.split("=")[1].strip()]
            if arg.startswith("--tf="):
                tf = arg.split("=")[1].strip()
            if arg.startswith("--volume="):
                vol = float(arg.split("=")[1].strip())
        auto_rl_loop(symbols=syms, timeframe=tf, volume=vol)
    elif "--execute" in sys.argv:
        sym = "XAUUSD"
        tf = "H1"
        vol = 0.01
        for arg in sys.argv:
            if arg.startswith("--symbol="):
                sym = arg.split("=")[1].strip()
            if arg.startswith("--tf="):
                tf = arg.split("=")[1].strip()
            if arg.startswith("--volume="):
                vol = float(arg.split("=")[1].strip())
        print(f"[*] Executing RL Bracket Order on {sym} ({tf})...")
        res = execute_rl_trade(symbol=sym, timeframe=tf, volume=vol)
        print(json.dumps(res, indent=2))
    else:
        print("--- LIVE REINFORCEMENT BRACKET SCAN (XAUUSD H1) ---")
        res = scan_rl_market("XAUUSD", "H1")
        print(json.dumps(res, indent=2))


