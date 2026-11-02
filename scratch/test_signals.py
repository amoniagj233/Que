import sys
sys.path.insert(0, ".")
import pandas as pd
import numpy as np

df = pd.read_csv("data_cache/XAUUSD_M5_LONG.csv")
sample = df.tail(15000).reset_index(drop=True)

close = sample['close']
ema9 = close.ewm(span=9, adjust=False).mean()
ema21 = close.ewm(span=21, adjust=False).mean()
ema100 = close.ewm(span=100, adjust=False).mean()

delta = close.diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / (loss + 1e-9)
rsi = 100 - (100 / (1 + rs))

# Vectorized signals with Trend filter EMA100
buy_cond = (close > ema100) & (ema9 > ema21) & (rsi >= 48) & (rsi <= 66)
sell_cond = (close < ema100) & (ema9 < ema21) & (rsi >= 34) & (rsi <= 52)

signals = np.zeros(len(sample), dtype=int)
signals[buy_cond] = 1
signals[sell_cond] = -1

opens = sample['open'].values
highs = sample['high'].values
lows = sample['low'].values
n = len(signals)

tp_dollars = 2.50
sl_dollars = 7.50
auto_be_trigger = 1.00
auto_be_lock = 0.20
cost = 0.35

trades = []
in_pos = False
pos_type = 0
entry_price = 0.0
tp_price = 0.0
sl_price = 0.0
be_active = False

for i in range(n - 1):
    if in_pos:
        closed = False
        pnl = 0.0
        if pos_type == 1:
            # Check BE trigger
            if not be_active and highs[i] >= (entry_price + auto_be_trigger):
                sl_price = entry_price + auto_be_lock
                be_active = True
            
            if highs[i] >= tp_price:
                pnl = (tp_price - entry_price) - cost
                closed = True
            elif lows[i] <= sl_price:
                pnl = (sl_price - entry_price) - cost
                closed = True
        elif pos_type == -1:
            if not be_active and lows[i] <= (entry_price - auto_be_trigger):
                sl_price = entry_price - auto_be_lock
                be_active = True
                
            if lows[i] <= tp_price:
                pnl = (entry_price - tp_price) - cost
                closed = True
            elif highs[i] >= sl_price:
                pnl = (entry_price - sl_price) - cost
                closed = True
                
        if closed:
            trades.append(pnl)
            in_pos = False

    if not in_pos and signals[i] != 0:
        in_pos = True
        pos_type = signals[i]
        entry_price = opens[i + 1]
        be_active = False
        if pos_type == 1:
            tp_price = entry_price + tp_dollars
            sl_price = entry_price - sl_dollars
        else:
            tp_price = entry_price - tp_dollars
            sl_price = entry_price + sl_dollars

wins = sum(1 for p in trades if p > 0)
total = len(trades)
wr = (wins / total) * 100 if total > 0 else 0
net = sum(trades)
gross_p = sum(p for p in trades if p > 0)
gross_l = abs(sum(p for p in trades if p < 0))
pf = gross_p / gross_l if gross_l > 0 else 99

print(f"SMART ASYMMETRIC SIMULATION:")
print(f"Total Trades: {total} | Wins: {wins} | Losses: {total-wins}")
print(f"Win Rate: {wr:.2f}% | Net Profit: ${net:.2f} | Profit Factor: {pf:.2f}")
