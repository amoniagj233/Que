import pandas as pd
import numpy as np

# Load scratch/optimize_pattern_pro.py simulation exactly to see how 90.82% was achieved
df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
df = df.iloc[-20000:].reset_index(drop=True)
n_bars = len(df)

closes = df["close"].to_numpy()
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
opens = df["open"].to_numpy()
volumes = df["tick_volume"].to_numpy()

ema21 = pd.Series(closes).ewm(span=21, adjust=False).mean().to_numpy()
ema55 = pd.Series(closes).ewm(span=55, adjust=False).mean().to_numpy()
ema200 = pd.Series(closes).ewm(span=200, adjust=False).mean().to_numpy()

delta = pd.Series(closes).diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / (avg_loss + 1e-9)
rsi14 = (100 - (100 / (1 + rs))).bfill().to_numpy()

h_box = pd.Series(highs).shift(1).rolling(15).max().bfill().to_numpy()
l_box = pd.Series(lows).shift(1).rolling(15).min().bfill().to_numpy()
vol_ma = pd.Series(volumes).rolling(20).mean().bfill().to_numpy()

def test_pattern_pro():
    trades = []
    in_pos = False
    pos_type = 0
    entry_p = 0.0
    cur_sl = 0.0
    tp_dist = 2.50
    sl_dist = 10.00
    be_trigger = 1.00
    be_lock = 0.40 # Covers $0.35 broker spread + $0.05 net profit!

    for i in range(200, n_bars - 1):
        if in_pos:
            hit = False
            exit_p = 0.0
            if pos_type == 1:
                if highs[i] >= entry_p + be_trigger and cur_sl < entry_p:
                    cur_sl = entry_p + be_lock
                if highs[i] >= entry_p + 2.50:
                    cand = highs[i] - 1.50
                    if cand > cur_sl:
                        cur_sl = cand
                if highs[i] >= entry_p + tp_dist:
                    hit = True
                    exit_p = entry_p + tp_dist
                elif lows[i] <= cur_sl:
                    hit = True
                    exit_p = cur_sl
            else:
                if lows[i] <= entry_p - be_trigger and cur_sl > entry_p:
                    cur_sl = entry_p - be_lock
                if lows[i] <= entry_p - 2.50:
                    cand = lows[i] + 1.50
                    if cand < cur_sl:
                        cur_sl = cand
                if lows[i] <= entry_p - tp_dist:
                    hit = True
                    exit_p = entry_p - tp_dist
                elif highs[i] >= cur_sl:
                    hit = True
                    exit_p = cur_sl

            if hit:
                # Deduct broker spread ($0.30) + slippage ($0.05) = $0.35
                gross_pnl = (exit_p - entry_p) if pos_type == 1 else (entry_p - exit_p)
                net_pnl = gross_pnl - 0.35
                trades.append({
                    "gross": gross_pnl,
                    "net": net_pnl,
                    "is_win": net_pnl > 0
                })
                in_pos = False

        if not in_pos:
            is_bull = (closes[i] > ema200[i]) and (ema21[i] > ema55[i])
            is_bear = (closes[i] < ema200[i]) and (ema21[i] < ema55[i])
            vol_ok = volumes[i] > (vol_ma[i] * 1.1)

            sig = 0
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
                cur_sl = (entry_p - sl_dist) if sig == 1 else (entry_p + sl_dist)

    total = len(trades)
    wins = sum(1 for t in trades if t["is_win"])
    wr = (wins / total) * 100.0 if total > 0 else 0
    net = sum(t["net"] for t in trades)
    print(f"Pattern Pro with be_lock=0.40: WR: {wr:.2f}% | Total: {total} | Wins: {wins} | Net Profit: ${net:.2f}")

test_pattern_pro()
