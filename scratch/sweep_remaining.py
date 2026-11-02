import pandas as pd
import numpy as np

df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
df = df.iloc[-25000:].reset_index(drop=True)
n_bars = len(df)

closes = df["close"].to_numpy()
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
opens = df["open"].to_numpy()
volumes = df["tick_volume"].to_numpy()

ema9 = pd.Series(closes).ewm(span=9, adjust=False).mean().to_numpy()
ema21 = pd.Series(closes).ewm(span=21, adjust=False).mean().to_numpy()
ema55 = pd.Series(closes).ewm(span=55, adjust=False).mean().to_numpy()
ema100 = pd.Series(closes).ewm(span=100, adjust=False).mean().to_numpy()
ema200 = pd.Series(closes).ewm(span=200, adjust=False).mean().to_numpy()

delta = pd.Series(closes).diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / (avg_loss + 1e-9)
rsi14 = (100 - (100 / (1 + rs))).bfill().to_numpy()

vol_ma = pd.Series(volumes).rolling(20).mean().bfill().to_numpy()

def evaluate(signals, tp_dist, sl_dist, be_trigger=1.00, be_lock=0.40):
    trades = []
    in_pos = False
    pos_type = 0
    entry_p = 0.0
    cur_sl = 0.0
    cost = 0.35

    for i in range(250, n_bars - 1):
        if in_pos:
            hit = False
            exit_p = 0.0
            if pos_type == 1:
                if highs[i] >= (entry_p + be_trigger) and cur_sl < entry_p:
                    cur_sl = entry_p + be_lock
                if highs[i] >= (entry_p + 2.50):
                    cand = highs[i] - 1.50
                    if cand > cur_sl:
                        cur_sl = cand
                if highs[i] >= (entry_p + tp_dist):
                    hit = True
                    exit_p = entry_p + tp_dist
                elif lows[i] <= cur_sl:
                    hit = True
                    exit_p = cur_sl
            else:
                if lows[i] <= (entry_p - be_trigger) and cur_sl > entry_p:
                    cur_sl = entry_p - be_lock
                if lows[i] <= (entry_p - 2.50):
                    cand = lows[i] + 1.50
                    if cand < cur_sl:
                        cur_sl = cand
                if lows[i] <= (entry_p - tp_dist):
                    hit = True
                    exit_p = entry_p - tp_dist
                elif highs[i] >= cur_sl:
                    hit = True
                    exit_p = cur_sl

            if hit:
                gross = (exit_p - entry_p) if pos_type == 1 else (entry_p - exit_p)
                net = gross - cost
                trades.append(net)
                in_pos = False

        if not in_pos and signals[i] != 0:
            in_pos = True
            pos_type = signals[i]
            entry_p = opens[i + 1]
            cur_sl = (entry_p - sl_dist) if pos_type == 1 else (entry_p + sl_dist)

    total = len(trades)
    if total == 0:
        return 0, 0, 0, 0
    wins = sum(1 for p in trades if p > 0)
    wr = (wins / total) * 100.0
    net = sum(trades)
    gross_w = sum(p for p in trades if p > 0)
    gross_l = abs(sum(p for p in trades if p < 0))
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else 99.0
    return wr, total, round(net, 2), pf

print("SWEEPING PARAMETERS FOR ACADEMIC MA...")
# Refined Academic MA signal: require strong volume and tight RSI band
vol_strong = volumes > (vol_ma * 1.15)
is_bull_academic = (closes > ema200) & (ema21 > ema55) & (closes > ema9)
is_bear_academic = (closes < ema200) & (ema21 < ema55) & (closes < ema9)

best_acad = None
for r_min, r_max in [(48, 64), (50, 65), (46, 62)]:
    sig_acad = np.zeros(n_bars, dtype=int)
    sig_acad[is_bull_academic & (lows <= ema21) & (closes > ema21) & (closes > opens) & (r_min < rsi14) & (rsi14 < r_max) & vol_strong] = 1
    sig_acad[is_bear_academic & (highs >= ema21) & (closes < ema21) & (closes < opens) & ((100-r_max) < rsi14) & (rsi14 < (100-r_min)) & vol_strong] = -1

    for tp in [2.50, 3.00, 3.50]:
        for sl in [5.50, 6.50, 7.50]:
            wr, tot, net, pf = evaluate(sig_acad, tp_dist=tp, sl_dist=sl, be_trigger=1.00, be_lock=0.40)
            if wr > 85.0 and net > 0 and tot >= 100:
                print(f"  ACAD MATCH: WR {wr:.2f}% | Trades: {tot} | Net: ${net} | PF: {pf} | TP: ${tp} | SL: ${sl} | RSI: {r_min}-{r_max}")
                if best_acad is None or net > best_acad['net']:
                    best_acad = {'wr': wr, 'tot': tot, 'net': net, 'pf': pf, 'tp': tp, 'sl': sl, 'rsi': (r_min, r_max)}

print("\nSWEEPING PARAMETERS FOR GOLD SCALPER PRO...")
# Refined Scalper: Trend pullback + Donchian bounce
best_scalp = None
for r_min, r_max in [(48, 62), (50, 64), (45, 60)]:
    sig_scalp = np.zeros(n_bars, dtype=int)
    # Require close > EMA100 and price bouncing off EMA55 or EMA21
    scalp_b = (closes > ema100) & (ema21 > ema55) & (lows <= ema55) & (closes > ema55) & (closes > opens) & (r_min < rsi14) & (rsi14 < r_max) & vol_strong
    scalp_s = (closes < ema100) & (ema21 < ema55) & (highs >= ema55) & (closes < ema55) & (closes < opens) & ((100-r_max) < rsi14) & (rsi14 < (100-r_min)) & vol_strong
    sig_scalp[scalp_b] = 1
    sig_scalp[scalp_s] = -1

    for tp in [2.50, 3.00, 3.50]:
        for sl in [6.00, 7.00, 8.00]:
            wr, tot, net, pf = evaluate(sig_scalp, tp_dist=tp, sl_dist=sl, be_trigger=1.00, be_lock=0.40)
            if wr > 85.0 and net > 0 and tot >= 50:
                print(f"  SCALP MATCH: WR {wr:.2f}% | Trades: {tot} | Net: ${net} | PF: {pf} | TP: ${tp} | SL: ${sl} | RSI: {r_min}-{r_max}")
                if best_scalp is None or net > best_scalp['net']:
                    best_scalp = {'wr': wr, 'tot': tot, 'net': net, 'pf': pf, 'tp': tp, 'sl': sl, 'rsi': (r_min, r_max)}
