import pandas as pd
import numpy as np

print("Loading historical Gold dataset (XAUUSD M5)...")
df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
# Use the most recent 15,000 M5 bars (approx 2 months of continuous trading)
df = df.iloc[-15000:].reset_index(drop=True)
n_bars = len(df)
print(f"Loaded {n_bars} M5 bars for simulation.")

# Precalculate indicators
closes = df["close"].to_numpy()
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
opens = df["open"].to_numpy()
volumes = df["tick_volume"].to_numpy()

ema9 = pd.Series(closes).ewm(span=9, adjust=False).mean().to_numpy()
ema21 = pd.Series(closes).ewm(span=21, adjust=False).mean().to_numpy()
ema55 = pd.Series(closes).ewm(span=55, adjust=False).mean().to_numpy()
ema200 = pd.Series(closes).ewm(span=200, adjust=False).mean().to_numpy()

# ATR 14
tr = np.maximum(highs[1:] - lows[1:], np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
tr = np.insert(tr, 0, highs[0] - lows[0])
atr14 = pd.Series(tr).rolling(14).mean().bfill().to_numpy()

# RSI 14
delta = pd.Series(closes).diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / (avg_loss + 1e-9)
rsi14 = (100 - (100 / (1 + rs))).bfill().to_numpy()

# Define Strategy Signals Generator
def generate_signals():
    signals = {
        "XAU Dark Horizon Scalp AI": np.zeros(n_bars, dtype=int),
        "CRT Gold Pro": np.zeros(n_bars, dtype=int),
        "ML Intelligence Engine": np.zeros(n_bars, dtype=int),
        "Strategic Pattern Pro": np.zeros(n_bars, dtype=int),
        "Gold Auto Trader": np.zeros(n_bars, dtype=int),
        "TikTalk Bot": np.zeros(n_bars, dtype=int),
        "SMC Breaker Sniper": np.zeros(n_bars, dtype=int),
    }
    
    for i in range(200, n_bars - 1):
        # 1. Dark Horizon (Direction Matrix + Rejection Wick)
        body = abs(closes[i] - opens[i])
        lower_wick = min(opens[i], closes[i]) - lows[i]
        if closes[i] > ema200[i] and ema9[i] > ema21[i] and lower_wick > body * 1.2:
            signals["XAU Dark Horizon Scalp AI"][i] = 1 # BUY
        elif closes[i] < ema200[i] and ema9[i] < ema21[i] and (highs[i] - max(opens[i], closes[i])) > body * 1.2:
            signals["XAU Dark Horizon Scalp AI"][i] = -1 # SELL
            
        # 2. CRT Gold Pro (M30 reference sweep on M5)
        # Lookback 6 bars (30 min) high/low
        m30_h = np.max(highs[i-6:i])
        m30_l = np.min(lows[i-6:i])
        if lows[i] < m30_l - 0.5 and closes[i] > m30_l and closes[i] > opens[i]:
            signals["CRT Gold Pro"][i] = 1 # Bullish CRT
        elif highs[i] > m30_h + 0.5 and closes[i] < m30_h and closes[i] < opens[i]:
            signals["CRT Gold Pro"][i] = -1 # Bearish CRT
            
        # 3. ML Intelligence Engine (Momentum & Volatility filter)
        vol_ratio = volumes[i] / (np.mean(volumes[i-20:i]) + 1e-9)
        if closes[i] > ema21[i] and rsi14[i] > 55 and vol_ratio > 1.3:
            signals["ML Intelligence Engine"][i] = 1
        elif closes[i] < ema21[i] and rsi14[i] < 45 and vol_ratio > 1.3:
            signals["ML Intelligence Engine"][i] = -1
            
        # 4. Strategic Pattern Pro (Box Breakout + 3 EMA)
        box_h = np.max(highs[i-12:i])
        box_l = np.min(lows[i-12:i])
        if closes[i] > box_h and closes[i] > ema55[i] and ema9[i] > ema21[i]:
            signals["Strategic Pattern Pro"][i] = 1
        elif closes[i] < box_l and closes[i] < ema55[i] and ema9[i] < ema21[i]:
            signals["Strategic Pattern Pro"][i] = -1
            
        # 5. Gold Auto Trader (Session Reversal + Volume Surge)
        rolling_l = np.min(lows[i-30:i])
        rolling_h = np.max(highs[i-30:i])
        if lows[i] <= rolling_l and closes[i] > opens[i] and vol_ratio > 1.2:
            signals["Gold Auto Trader"][i] = 1
        elif highs[i] >= rolling_h and closes[i] < opens[i] and vol_ratio > 1.2:
            signals["Gold Auto Trader"][i] = -1
            
        # 6. TikTalk Bot (9/21 EMA Cross + RSI Dip)
        if ema9[i-1] <= ema21[i-1] and ema9[i] > ema21[i] and rsi14[i] < 60:
            signals["TikTalk Bot"][i] = 1
        elif ema9[i-1] >= ema21[i-1] and ema9[i] < ema21[i] and rsi14[i] > 40:
            signals["TikTalk Bot"][i] = -1
            
        # 7. SMC Breaker Sniper (Turtle Soup Sweep)
        swing_l = np.min(lows[i-24:i])
        swing_h = np.max(highs[i-24:i])
        if lows[i] < swing_l and closes[i] > swing_l and closes[i] > opens[i]:
            signals["SMC Breaker Sniper"][i] = 1
        elif highs[i] > swing_h and closes[i] < swing_h and closes[i] < opens[i]:
            signals["SMC Breaker Sniper"][i] = -1
            
    return signals

signals = generate_signals()

# Simulation function
def backtest_strategy(sig_array, use_sl=True, tp_dist=2.50, sl_dist=2.50, lot=0.01):
    trades = []
    in_pos = False
    pos_type = 0 # 1=BUY, -1=SELL
    entry_p = 0.0
    entry_idx = 0
    max_floating_dd = 0.0
    
    # Iterate through bars
    i = 200
    while i < n_bars - 1:
        sig = sig_array[i]
        
        # Check open position exit
        if in_pos:
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]
            
            # Track floating drawdown for this trade
            if pos_type == 1:
                floating_pnl = (cur_low - entry_p) * lot * 100
            else:
                floating_pnl = (entry_p - cur_high) * lot * 100
            if floating_pnl < max_floating_dd:
                max_floating_dd = floating_pnl
                
            hit_tp = False
            hit_sl = False
            exit_p = 0.0
            
            if pos_type == 1: # BUY
                if cur_high >= entry_p + tp_dist:
                    hit_tp = True
                    exit_p = entry_p + tp_dist
                elif use_sl and cur_low <= entry_p - sl_dist:
                    hit_sl = True
                    exit_p = entry_p - sl_dist
            elif pos_type == -1: # SELL
                if cur_low <= entry_p - tp_dist:
                    hit_tp = True
                    exit_p = entry_p - tp_dist
                elif use_sl and cur_high >= entry_p + sl_dist:
                    hit_sl = True
                    exit_p = entry_p + sl_dist
                    
            if hit_tp or hit_sl or (not use_sl and i == n_bars - 2): # Forced close at dataset end
                if not hit_tp and not hit_sl:
                    exit_p = cur_close
                    
                pnl = (exit_p - entry_p if pos_type == 1 else entry_p - exit_p) * lot * 100
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "duration": i - entry_idx,
                    "type": pos_type,
                    "pnl": pnl,
                    "is_win": pnl > 0
                })
                in_pos = False
                pos_type = 0
                
        # Open new position if flat and signal triggered
        if not in_pos and sig != 0:
            in_pos = True
            pos_type = sig
            entry_p = closes[i]
            entry_idx = i
            
        i += 1
        
    # Analyze trade results
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "wr": 0.0, "net_pnl": 0.0, "pf": 0.0, "max_dd": 0.0, "worst_trade": 0.0, "avg_dur": 0.0}
        
    tdf = pd.DataFrame(trades)
    total = len(tdf)
    wins = len(tdf[tdf["is_win"]])
    losses = total - wins
    wr = (wins / total * 100) if total > 0 else 0.0
    net_pnl = tdf["pnl"].sum()
    gross_win = tdf[tdf["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(tdf[tdf["pnl"] < 0]["pnl"].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
    
    # Calculate equity curve & drawdown
    tdf["cum_pnl"] = tdf["pnl"].cumsum()
    peak = tdf["cum_pnl"].cummax()
    dd = peak - tdf["cum_pnl"]
    max_closed_dd = dd.max()
    worst_trade = tdf["pnl"].min()
    avg_duration = tdf["duration"].mean()
    
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "wr": wr,
        "net_pnl": net_pnl,
        "pf": pf,
        "max_closed_dd": max_closed_dd,
        "worst_trade": worst_trade,
        "max_floating_dd": abs(max_floating_dd),
        "avg_dur": avg_duration
    }

print("\n" + "=" * 95)
print("             BACKTEST COMPARISON: WITH STOP LOSS vs NO STOP LOSS             ")
print("                          Dataset: 15,000 M5 Bars of Gold                     ")
print("=" * 95)

results = []
for bot_name, sig_arr in signals.items():
    res_sl = backtest_strategy(sig_arr, use_sl=True, tp_dist=2.50, sl_dist=2.50)
    res_nosl = backtest_strategy(sig_arr, use_sl=False, tp_dist=2.50)
    
    results.append({
        "bot": bot_name,
        "sl_trades": res_sl["total"],
        "sl_wr": res_sl["wr"],
        "sl_pnl": res_sl["net_pnl"],
        "sl_pf": res_sl["pf"],
        "sl_dd": res_sl["max_closed_dd"],
        "nosl_trades": res_nosl["total"],
        "nosl_wr": res_nosl["wr"],
        "nosl_pnl": res_nosl["net_pnl"],
        "nosl_pf": res_nosl["pf"],
        "nosl_dd": res_nosl["max_closed_dd"],
        "nosl_worst": res_nosl["worst_trade"],
        "nosl_max_float_dd": res_nosl["max_floating_dd"],
        "sl_dur": res_sl["avg_dur"] * 5, # minutes
        "nosl_dur": res_nosl["avg_dur"] * 5 # minutes
    })

res_df = pd.DataFrame(results)

print(f"{'Bot Name':<28} | {'SL WinRate':<10} | {'No-SL WinRate':<13} | {'WR Change':<10} | {'SL Net PnL':<10} | {'No-SL Net PnL':<13} | {'Worst Trade'}")
print("-" * 115)
for _, r in res_df.iterrows():
    wr_diff = r["nosl_wr"] - r["sl_wr"]
    print(f"{r['bot']:<28} | {r['sl_wr']:>8.1f}% | {r['nosl_wr']:>11.1f}% | {wr_diff:>+8.1f}% | ${r['sl_pnl']:>8.2f} | ${r['nosl_pnl']:>11.2f} | -${abs(r['nosl_worst']):.2f} (Float: -${r['nosl_max_float_dd']:.2f})")

print("=" * 115)
