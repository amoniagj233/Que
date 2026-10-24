import pandas as pd
import numpy as np
from mt5_connector import mt5_connector

def detect_pinbars(df, wick_ratio=2.0, body_ratio=0.33):
    out = df.copy()
    body = (out["close"] - out["open"]).abs().replace(0, 1e-6)
    rng = (out["high"] - out["low"]).clip(lower=0)
    upper_wick = out["high"] - out[["open", "close"]].max(axis=1)
    lower_wick = out[["open", "close"]].min(axis=1) - out["low"]

    out["pinbar_signal"] = 0
    bullish = (
        (lower_wick >= wick_ratio * body)
        & (body <= body_ratio * rng)
        & (upper_wick < body)
        & (rng > 0)
    )
    bearish = (
        (upper_wick >= wick_ratio * body)
        & (body <= body_ratio * rng)
        & (lower_wick < body)
        & (rng > 0)
    )
    out.loc[bullish, "pinbar_signal"] = 1
    out.loc[bearish, "pinbar_signal"] = -1
    return out

def add_trend_filter(df, fast_ema=50, slow_ema=200):
    out = df.copy()
    out["ema_fast"] = out["close"].ewm(span=fast_ema, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow_ema, adjust=False).mean()
    out["trend"] = 0
    up = (out["close"] > out["ema_fast"]) & (out["ema_fast"] > out["ema_slow"])
    dn = (out["close"] < out["ema_fast"]) & (out["ema_fast"] < out["ema_slow"])
    out.loc[up, "trend"] = 1
    out.loc[dn, "trend"] = -1
    return out

def detect_swing_points(df, left_bars=10, right_bars=10):
    out = df.copy()
    out["swing_high"] = np.nan
    out["swing_low"] = np.nan
    for i in range(left_bars, len(out) - right_bars):
        ch = float(out.iloc[i]["high"])
        cl = float(out.iloc[i]["low"])
        left_highs = out.iloc[i - left_bars : i]["high"]
        right_highs = out.iloc[i + 1 : i + right_bars + 1]["high"]
        if (ch > left_highs.max()) and (ch > right_highs.max()):
            out.iloc[i, out.columns.get_loc("swing_high")] = ch
        left_lows = out.iloc[i - left_bars : i]["low"]
        right_lows = out.iloc[i + 1 : i + right_bars + 1]["low"]
        if (cl < left_lows.min()) and (cl < right_lows.min()):
            out.iloc[i, out.columns.get_loc("swing_low")] = cl
    if right_bars > 0:
        out["swing_high"] = out["swing_high"].shift(right_bars)
        out["swing_low"] = out["swing_low"].shift(right_bars)
    return out

def identify_key_levels(df, lookback_bars=100):
    out = df.copy()
    out["nearest_support"] = np.nan
    out["nearest_resistance"] = np.nan
    for i in range(lookback_bars, len(out)):
        recent = out.iloc[max(0, i - lookback_bars) : i]
        sh = recent["swing_high"].dropna()
        sl = recent["swing_low"].dropna()
        price = float(out.iloc[i]["close"])
        resistances = sh[sh > price]
        if len(resistances) > 0:
            out.iloc[i, out.columns.get_loc("nearest_resistance")] = float(resistances.iloc[-1])
        supports = sl[sl < price]
        if len(supports) > 0:
            out.iloc[i, out.columns.get_loc("nearest_support")] = float(supports.iloc[-1])
    return out

def add_level_proximity(df, proximity_threshold=0.005): # 0.5% for commodities
    out = df.copy()
    out["at_support"] = False
    out["at_resistance"] = False
    close = out["close"].astype(float).values
    sup = out["nearest_support"].astype(float).values
    res = out["nearest_resistance"].astype(float).values
    for i in range(len(out)):
        p = close[i]
        if np.isfinite(sup[i]) and sup[i] != 0:
            if abs(p - sup[i]) / abs(sup[i]) <= proximity_threshold:
                out.iloc[i, out.columns.get_loc("at_support")] = True
        if np.isfinite(res[i]) and res[i] != 0:
            if abs(p - res[i]) / abs(res[i]) <= proximity_threshold:
                out.iloc[i, out.columns.get_loc("at_resistance")] = True
    return out

def backtest_pinbar(symbol="XAUUSD", timeframe="M15", count=2000, rr=2.0, atr_mult=1.5):
    candles = mt5_connector.get_candles(symbol, timeframe, count)
    if not candles:
        return {"error": "Failed to fetch candles"}
    df = pd.DataFrame(candles)
    df = detect_pinbars(df)
    df = add_trend_filter(df)
    df = detect_swing_points(df)
    df = identify_key_levels(df)
    df = add_level_proximity(df)

    prev_close = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean().bfill()

    trades = []
    in_pos = False
    entry_bar = 0
    side = 0
    entry_price = 0.0
    sl = 0.0
    tp = 0.0

    for i in range(250, len(df) - 1):
        c = df.iloc[i]
        nxt = df.iloc[i + 1]

        # Manage existing trade
        if in_pos:
            hold_bars = i - entry_bar
            hit_tp = (nxt["high"] >= tp) if side == 1 else (nxt["low"] <= tp)
            hit_sl = (nxt["low"] <= sl) if side == 1 else (nxt["high"] >= sl)

            if hit_sl:
                trades.append({"side": "BUY" if side == 1 else "SELL", "r": -1.0, "reason": "SL", "hold": hold_bars})
                in_pos = False
            elif hit_tp:
                trades.append({"side": "BUY" if side == 1 else "SELL", "r": rr, "reason": "TP", "hold": hold_bars})
                in_pos = False
            elif hold_bars >= 50:
                # Time exit
                exit_p = nxt["close"]
                r_result = (exit_p - entry_price) * side / abs(entry_price - sl)
                trades.append({"side": "BUY" if side == 1 else "SELL", "r": round(float(r_result), 2), "reason": "TIME", "hold": hold_bars})
                in_pos = False
            continue

        # Look for new signal on bar close i
        sig = 0
        if c["pinbar_signal"] == 1 and c["trend"] == 1 and c["at_support"]:
            sig = 1
        elif c["pinbar_signal"] == -1 and c["trend"] == -1 and c["at_resistance"]:
            sig = -1

        if sig != 0:
            in_pos = True
            entry_bar = i + 1
            side = sig
            entry_price = float(nxt["open"])
            atr = float(c["atr"])
            if side == 1:
                sl = float(c["low"]) - atr_mult * atr
                risk = entry_price - sl
                tp = entry_price + rr * risk
            else:
                sl = float(c["high"]) + atr_mult * atr
                risk = sl - entry_price
                tp = entry_price - rr * risk

    n_trades = len(trades)
    if n_trades == 0:
        return {"trades": 0, "note": "No setups matched triple criteria in this period"}

    rs = [t["r"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    win_rate = len(wins) / n_trades * 100
    total_r = sum(rs)
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 99.0

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars_tested": len(df),
        "total_trades": n_trades,
        "win_rate_pct": round(win_rate, 1),
        "total_r_profit": round(total_r, 2),
        "profit_factor": round(profit_factor, 2),
        "trades": trades
    }

def scan_market(symbol="XAUUSD", timeframe="M15", count=300, rr=2.0, atr_mult=1.5):
    """
    Scans the latest closed bar of the symbol for a valid Pin Bar + Trend + Key Level setup.
    """
    candles = mt5_connector.get_candles(symbol, timeframe, count)
    if not candles:
        return {"error": f"Failed to fetch {symbol} {timeframe} candles from MT5"}
    
    df = pd.DataFrame(candles)
    df = detect_pinbars(df)
    df = add_trend_filter(df)
    df = detect_swing_points(df)
    df = identify_key_levels(df)
    df = add_level_proximity(df)

    prev_close = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean().bfill()

    # The last closed candle is index -2 (index -1 is the currently forming candle)
    c = df.iloc[-2]
    curr = df.iloc[-1]

    trend_str = "BULLISH" if c["trend"] == 1 else ("BEARISH" if c["trend"] == -1 else "NEUTRAL")
    pinbar_type = "BULLISH_HAMMER" if c["pinbar_signal"] == 1 else ("BEARISH_SHOOTING_STAR" if c["pinbar_signal"] == -1 else "NONE")
    
    signal = "NONE"
    sl = 0.0
    tp = 0.0
    entry_est = float(curr["open"])
    atr = float(c["atr"])

    if c["pinbar_signal"] == 1 and c["trend"] == 1 and c["at_support"]:
        signal = "BUY"
        sl = round(float(c["low"]) - atr_mult * atr, 3)
        risk = entry_est - sl
        tp = round(entry_est + rr * risk, 3)
    elif c["pinbar_signal"] == -1 and c["trend"] == -1 and c["at_resistance"]:
        signal = "SELL"
        sl = round(float(c["high"]) + atr_mult * atr, 3)
        risk = sl - entry_est
        tp = round(entry_est - rr * risk, 3)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candle_time": str(c["time"]),
        "current_price": float(curr["close"]),
        "trend": trend_str,
        "ema_fast_50": round(float(c["ema_fast"]), 3),
        "ema_slow_200": round(float(c["ema_slow"]), 3),
        "nearest_support": round(float(c["nearest_support"]), 3) if pd.notnull(c["nearest_support"]) else None,
        "nearest_resistance": round(float(c["nearest_resistance"]), 3) if pd.notnull(c["nearest_resistance"]) else None,
        "at_support": bool(c["at_support"]),
        "at_resistance": bool(c["at_resistance"]),
        "pinbar_detected": pinbar_type,
        "signal": signal,
        "suggested_entry": entry_est if signal != "NONE" else None,
        "suggested_sl": sl if signal != "NONE" else None,
        "suggested_tp": tp if signal != "NONE" else None,
        "atr_14": round(atr, 3)
    }

def execute_setup(symbol="XAUUSD", timeframe="M15", volume=0.01, rr=2.0, atr_mult=1.5):
    """
    Evaluates current market conditions; if a valid setup exists, places an MT5 trade.
    """
    scan = scan_market(symbol=symbol, timeframe=timeframe, rr=rr, atr_mult=atr_mult)
    if "error" in scan:
        return scan
    
    signal = scan["signal"]
    if signal == "NONE":
        return {
            "status": "no_trade",
            "reason": f"No active Pin Bar + Key Level setup on {symbol} ({timeframe})",
            "scan": scan
        }
    
    res = mt5_connector.place_market_order(
        symbol=symbol,
        action=signal,
        volume=volume,
        stop_loss=scan["suggested_sl"],
        take_profit=scan["suggested_tp"],
        comment="Pinbar-KeyLvl"
    )
    return {
        "status": "executed" if res.get("success") else "failed",
        "signal": signal,
        "order_result": res,
        "scan": scan
    }

def auto_trade_loop(symbols=None, timeframe="M15", volume=0.01, poll_seconds=20):
    """
    Continuous multi-symbol trading bot loop:
    Periodically checks for newly closed candles on a watchlist of symbols
    and executes valid Pin Bar + Trend + Key Level setups.
    """
    import time
    quote_syms = set(mt5_connector.get_symbols())
    if symbols is None:
        preferred = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]
        symbols = [s for s in preferred if s in quote_syms] or list(quote_syms)[:10]
    elif isinstance(symbols, str):
        symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # Strictly restrict to symbols currently active on Headway Quotes
    valid_symbols = [s for s in symbols if s in quote_syms]
    if not valid_symbols:
        print(f"[!] Error: Requested symbols {symbols} are not on Headway Quotes. Active on Quotes: {list(quote_syms)[:10]}...", flush=True)
        return
    symbols = valid_symbols

    print(f"[*] Starting Multi-Symbol Pin Bar Auto-Trader (Headway Quotes Only)", flush=True)
    print(f"    - Watchlist: {symbols}", flush=True)
    print(f"    - Timeframe: {timeframe}", flush=True)
    print(f"    - Lot Size:  {volume}", flush=True)
    print(f"    - Poll Rate: {poll_seconds}s", flush=True)
    print(f"=" * 60, flush=True)

    last_candle_times = {}

    # Initial scan for each symbol
    for sym in symbols:
        scan = scan_market(symbol=sym, timeframe=timeframe)
        if "error" not in scan:
            last_candle_times[sym] = scan.get("candle_time")
            print(f"[INIT] {sym.ljust(8)} | Price: {str(scan['current_price']).ljust(8)} | Trend: {scan['trend'].ljust(7)} | S: {str(scan['nearest_support']).ljust(8)} | R: {str(scan['nearest_resistance']).ljust(8)} | Pinbar: {scan['pinbar_detected']}", flush=True)
        else:
            last_candle_times[sym] = None
            print(f"[!] Warning on initial scan for {sym}: {scan.get('error')}", flush=True)

    print(f"[*] Continuous live scanner active. Listening for bar closes...", flush=True)

    heartbeat_counter = 0

    while True:
        try:
            for sym in symbols:
                scan = scan_market(symbol=sym, timeframe=timeframe)
                if "error" not in scan:
                    c_time = scan.get("candle_time")
                    prev_time = last_candle_times.get(sym)

                    if c_time != prev_time:
                        last_candle_times[sym] = c_time
                        sig = scan.get("signal")
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{sym}] Bar Closed: {c_time} | Price: {scan['current_price']} | Trend: {scan['trend']} | Pinbar: {scan['pinbar_detected']} | Signal: {sig}", flush=True)

                        if sig != "NONE":
                            # Check existing open positions to avoid stacking
                            open_pos = mt5_connector.get_positions(symbol=sym)
                            existing_bot_pos = [p for p in open_pos if p.get("comment") == "Pinbar-KeyLvl"]
                            if existing_bot_pos:
                                print(f"[SKIP] Existing Pinbar position #{existing_bot_pos[0]['ticket']} already open on {sym}. Waiting for exit.", flush=True)
                            else:
                                print(f"[!] TRIGGERING ORDER: {sig} {volume} lots on {sym} (SL: {scan['suggested_sl']}, TP: {scan['suggested_tp']})", flush=True)
                                exec_res = execute_setup(symbol=sym, timeframe=timeframe, volume=volume)
                                print(f"    Order Result: {exec_res}", flush=True)

            heartbeat_counter += 1
            # Print a concise heartbeat summary every ~2 minutes (6 cycles of 20s)
            if heartbeat_counter % 6 == 0:
                acc = mt5_connector.get_account_info()
                positions = mt5_connector.get_positions()
                print(f"[{time.strftime('%H:%M:%S')}] Heartbeat | Balance: ${acc.get('balance'):,.2f} | Open Positions: {len(positions)} | Monitoring {len(symbols)} symbols", flush=True)

            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            print("[*] Auto-trader stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"[!] Error in loop: {e}", flush=True)
            time.sleep(poll_seconds)

if __name__ == "__main__":
    import sys
    import json

    if "--auto" in sys.argv:
        syms = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        tf = "M15"
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
        auto_trade_loop(symbols=syms, timeframe=tf, volume=vol)
    else:
        print("--- LIVE SCAN ---")
        live_scan = scan_market("XAUUSD", "M15")
        print(json.dumps(live_scan, indent=2))

        print("\n--- BACKTEST XAUUSD M15 (2,500 Bars) ---")
        bt = backtest_pinbar("XAUUSD", "M15", 2500)
        print("Trades:", bt.get("total_trades"), "| Win Rate:", bt.get("win_rate_pct"), "% | Total R:", bt.get("total_r_profit"), "| Profit Factor:", bt.get("profit_factor"))



