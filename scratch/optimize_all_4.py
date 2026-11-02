import pandas as pd
import numpy as np

# Load historical XAUUSD data
df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
df = df.iloc[-25000:].reset_index(drop=True)
n_bars = len(df)
print(f"Loaded {n_bars} historical M5 bars of Gold (XAUUSD).")

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

# Volume MA 20
vol_ma = pd.Series(volumes).rolling(20).mean().bfill().to_numpy()

# Donchian 15
h_box = pd.Series(highs).shift(1).rolling(15).max().bfill().to_numpy()
l_box = pd.Series(lows).shift(1).rolling(15).min().bfill().to_numpy()

# Candle spread
bar_range = highs - lows
range_ma = pd.Series(bar_range).rolling(20).mean().bfill().to_numpy()

def evaluate_signals(signals, tp_dist=2.50, sl_dist=10.00, be_trigger=1.00, be_lock=0.40):
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
                # Auto-BE
                if highs[i] >= (entry_p + be_trigger) and cur_sl < entry_p:
                    cur_sl = entry_p + be_lock
                # Trailing
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
                # Auto-BE
                if lows[i] <= (entry_p - be_trigger) and cur_sl > entry_p:
                    cur_sl = entry_p - be_lock
                # Trailing
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
        return {"win_rate": 0.0, "total_trades": 0, "net_profit": 0.0, "profit_factor": 0.0}
    wins = sum(1 for p in trades if p > 0)
    wr = (wins / total) * 100.0
    net = sum(trades)
    gross_w = sum(p for p in trades if p > 0)
    gross_l = abs(sum(p for p in trades if p < 0))
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else 99.0
    return {
        "win_rate": round(wr, 2),
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "net_profit": round(net, 2),
        "profit_factor": pf
    }

print("=" * 80)
print("TESTING OPTIMIZED MODELS FOR THE 4 FLAGGED BOTS:")
print("=" * 80)

# 1. Academic Momentum MA V2 (Magic 6666)
is_bull_academic = (closes > ema200) & (ema21 > ema55)
is_bear_academic = (closes < ema200) & (ema21 < ema55)
vol_ok = volumes > (vol_ma * 1.05)
sig_academic = np.zeros(n_bars, dtype=int)
sig_academic[is_bull_academic & (lows <= ema21) & (closes > ema21) & (closes > opens) & (46 < rsi14) & (rsi14 < 66) & vol_ok] = 1
sig_academic[is_bear_academic & (highs >= ema21) & (closes < ema21) & (closes < opens) & (34 < rsi14) & (rsi14 < 54) & vol_ok] = -1
res_academic = evaluate_signals(sig_academic, tp_dist=2.50, sl_dist=10.00, be_trigger=1.00, be_lock=0.40)
print(f"Academic Momentum MA V2: WR {res_academic['win_rate']}% | Wins: {res_academic['wins']}/{res_academic['total_trades']} | Net: ${res_academic['net_profit']} | PF: {res_academic['profit_factor']}")

# 2. SMC Breaker Sniper V2 (Magic 3333)
sig_smc = np.zeros(n_bars, dtype=int)
# Liquidity sweep past Donchian box with immediate reversal inside
smc_bull = (lows < l_box) & (closes > l_box) & (closes > opens) & (closes > ema55) & (40 < rsi14) & (rsi14 < 60) & vol_ok
smc_bear = (highs > h_box) & (closes < h_box) & (closes < opens) & (closes < ema55) & (40 < rsi14) & (rsi14 < 60) & vol_ok
sig_smc[smc_bull] = 1
sig_smc[smc_bear] = -1
res_smc = evaluate_signals(sig_smc, tp_dist=2.50, sl_dist=10.00, be_trigger=1.00, be_lock=0.40)
print(f"SMC Breaker Sniper V2  : WR {res_smc['win_rate']}% | Wins: {res_smc['wins']}/{res_smc['total_trades']} | Net: ${res_smc['net_profit']} | PF: {res_smc['profit_factor']}")

# 3. TikTalk Gold VSA V2 (Magic 5555)
sig_tiktalk = np.zeros(n_bars, dtype=int)
vol_surge = volumes > (vol_ma * 1.20)
range_ok = bar_range > (range_ma * 1.10)
tik_bull = (closes > ema100) & (ema9 > ema21) & (closes > opens) & vol_surge & range_ok & (48 < rsi14) & (rsi14 < 68)
tik_bear = (closes < ema100) & (ema9 < ema21) & (closes < opens) & vol_surge & range_ok & (32 < rsi14) & (rsi14 < 52)
sig_tiktalk[tik_bull] = 1
sig_tiktalk[tik_bear] = -1
res_tiktalk = evaluate_signals(sig_tiktalk, tp_dist=2.50, sl_dist=10.00, be_trigger=1.00, be_lock=0.40)
print(f"TikTalk Gold VSA V2    : WR {res_tiktalk['win_rate']}% | Wins: {res_tiktalk['wins']}/{res_tiktalk['total_trades']} | Net: ${res_tiktalk['net_profit']} | PF: {res_tiktalk['profit_factor']}")

# 4. Gold Scalper Pro V2 (Magic 2222)
sig_scalper = np.zeros(n_bars, dtype=int)
# Dynamic ATR Pullback to EMA21
scalp_bull = (closes > ema200) & (lows <= ema21) & (closes > ema21) & (closes > opens) & (48 < rsi14) & (rsi14 < 65)
scalp_bear = (closes < ema200) & (highs >= ema21) & (closes < ema21) & (closes < opens) & (35 < rsi14) & (rsi14 < 52)
sig_scalper[scalp_bull] = 1
sig_scalper[scalp_bear] = -1
res_scalper = evaluate_signals(sig_scalper, tp_dist=2.50, sl_dist=10.00, be_trigger=1.00, be_lock=0.40)
print(f"Gold Scalper Pro V2    : WR {res_scalper['win_rate']}% | Wins: {res_scalper['wins']}/{res_scalper['total_trades']} | Net: ${res_scalper['net_profit']} | PF: {res_scalper['profit_factor']}")

print("=" * 80)
