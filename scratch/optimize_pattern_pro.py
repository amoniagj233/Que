import pandas as pd
import numpy as np

print("Loading historical Gold dataset (XAUUSD M5)...")
df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
df = df.iloc[-20000:].reset_index(drop=True)
n_bars = len(df)
print(f"Loaded {n_bars} M5 bars.")

closes = df["close"].to_numpy()
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
opens = df["open"].to_numpy()
volumes = df["tick_volume"].to_numpy()

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

# 15-candle box
h_box = pd.Series(highs).shift(1).rolling(15).max().bfill().to_numpy()
l_box = pd.Series(lows).shift(1).rolling(15).min().bfill().to_numpy()

# Volume MA 20
vol_ma = pd.Series(volumes).rolling(20).mean().bfill().to_numpy()

def run_simulation(version="baseline", tp_dist=4.00, sl_dist=7.50, be_trigger=1.50, be_lock=0.20):
    trades = []
    in_pos = False
    pos_type = 0
    entry_p = 0.0
    entry_idx = 0
    cur_sl = 0.0
    
    for i in range(200, n_bars - 1):
        # Manage open position
        if in_pos:
            hit_tp = False
            hit_sl = False
            exit_p = 0.0
            
            if pos_type == 1: # BUY
                # Check Auto-Breakeven
                if highs[i] >= entry_p + be_trigger and cur_sl < entry_p:
                    cur_sl = entry_p + be_lock
                # Check Trailing
                if highs[i] >= entry_p + 2.50:
                    trail_candidate = highs[i] - 1.50
                    if trail_candidate > cur_sl:
                        cur_sl = trail_candidate
                        
                if highs[i] >= entry_p + tp_dist:
                    hit_tp = True
                    exit_p = entry_p + tp_dist
                elif lows[i] <= cur_sl:
                    hit_sl = True
                    exit_p = cur_sl
            else: # SELL
                if lows[i] <= entry_p - be_trigger and cur_sl > entry_p:
                    cur_sl = entry_p - be_lock
                if lows[i] <= entry_p - 2.50:
                    trail_candidate = lows[i] + 1.50
                    if trail_candidate < cur_sl:
                        cur_sl = trail_candidate
                        
                if lows[i] <= entry_p - tp_dist:
                    hit_tp = True
                    exit_p = entry_p - tp_dist
                elif highs[i] >= cur_sl:
                    hit_sl = True
                    exit_p = cur_sl
                    
            if hit_tp or hit_sl:
                pnl = (exit_p - entry_p if pos_type == 1 else entry_p - exit_p) * 0.01 * 100
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "pnl": pnl,
                    "is_win": pnl > 0
                })
                in_pos = False
                pos_type = 0
                
        # Check Entry Signal
        if not in_pos:
            is_bull = (closes[i] > ema200[i]) and (ema21[i] > ema55[i])
            is_bear = (closes[i] < ema200[i]) and (ema21[i] < ema55[i])
            
            sig = 0
            if version == "baseline":
                if closes[i] > h_box[i] and is_bull:
                    sig = 1
                elif closes[i] < l_box[i] and is_bear:
                    sig = -1
                elif is_bull and closes[i] > opens[i]:
                    sig = 1
                elif is_bear and closes[i] < opens[i]:
                    sig = -1
            elif version == "v2_filtered":
                # Only clean box breakouts + RSI non-exhausted + Volume confirmation
                vol_ok = volumes[i] > (vol_ma[i] * 1.1)
                
                # Condition 1: Pure Box Breakout with Momentum
                if closes[i] > h_box[i] and is_bull and 48 < rsi14[i] < 68 and vol_ok:
                    sig = 1
                elif closes[i] < l_box[i] and is_bear and 32 < rsi14[i] < 52 and vol_ok:
                    sig = -1
                # Condition 2: High-Quality EMA21 Pullback Rejection
                elif is_bull and lows[i] <= ema21[i] and closes[i] > ema21[i] and closes[i] > opens[i] and 45 < rsi14[i] < 62:
                    sig = 1
                elif is_bear and highs[i] >= ema21[i] and closes[i] < ema21[i] and closes[i] < opens[i] and 38 < rsi14[i] < 55:
                    sig = -1
                    
            if sig != 0:
                in_pos = True
                pos_type = sig
                entry_p = closes[i]
                entry_idx = i
                cur_sl = (entry_p - sl_dist) if sig == 1 else (entry_p + sl_dist)
                
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "wr": 0.0, "net_pnl": 0.0, "pf": 0.0}
        
    tdf = pd.DataFrame(trades)
    tot = len(tdf)
    wins = len(tdf[tdf["is_win"]])
    wr = (wins / tot * 100) if tot > 0 else 0.0
    pnl = tdf["pnl"].sum()
    gross_w = tdf[tdf["pnl"] > 0]["pnl"].sum()
    gross_l = abs(tdf[tdf["pnl"] < 0]["pnl"].sum())
    pf = (gross_w / gross_l) if gross_l > 0 else 99.0
    return {"total": tot, "wins": wins, "losses": tot - wins, "wr": wr, "net_pnl": pnl, "pf": pf}

res_base = run_simulation("baseline", tp_dist=2.50, sl_dist=2.50)
res_v2 = run_simulation("v2_filtered", tp_dist=4.00, sl_dist=7.50, be_trigger=1.50, be_lock=0.20)

print("=" * 75)
print("       STRATEGIC PATTERN PRO: OPTIMIZATION PERFORMANCE RESULTS        ")
print("=" * 75)
print(f"BASELINE MODEL (Old flat scalper):")
print(f"  Total Trades: {res_base['total']} | Wins: {res_base['wins']} | Losses: {res_base['losses']}")
print(f"  Win Rate    : {res_base['wr']:.2f}% | Net PnL: ${res_base['net_pnl']:+.2f} | PF: {res_base['pf']:.2f}")
print("-" * 75)
print(f"OPTIMIZED MODEL V2 (Pullback + RSI Filter + Vol + Smart Asymmetric):")
print(f"  Total Trades: {res_v2['total']} | Wins: {res_v2['wins']} | Losses: {res_v2['losses']}")
print(f"  Win Rate    : {res_v2['wr']:.2f}% | Net PnL: ${res_v2['net_pnl']:+.2f} | PF: {res_v2['pf']:.2f}")
print("=" * 75)

print("\nExecuting comprehensive parameter sweep...")
best_wr = 0.0
best_params = {}

for tp in [2.50, 3.00, 3.50, 4.00]:
    for sl in [6.50, 7.50, 8.50, 10.00]:
        for be in [1.00, 1.20, 1.50]:
            res = run_simulation("v2_filtered", tp_dist=tp, sl_dist=sl, be_trigger=be, be_lock=0.20)
            if res["wr"] > best_wr and res["net_pnl"] > 0:
                best_wr = res["wr"]
                best_params = {"tp": tp, "sl": sl, "be": be, "res": res}

r = best_params["res"]
print("\n=== TOP OPTIMIZED CONFIGURATION FOUND ===")
print("Optimal Settings:")
print("  Take Profit Target : $" + str(best_params["tp"]))
print("  Stop Loss Distance : $" + str(best_params["sl"]))
print("  Auto-BE Trigger    : +$" + str(best_params["be"]))
print("Results across 20,000 M5 Bars:")
print("  Win Rate           : " + str(round(r["wr"], 2)) + "%")
print("  Total Trades       : " + str(r["total"]))
print("  Wins / Losses      : " + str(r["wins"]) + " Wins / " + str(r["losses"]) + " Losses")
print("  Net Profit         : +$" + str(round(r["net_pnl"], 2)))
print("  Profit Factor      : " + str(round(r["pf"], 2)))
