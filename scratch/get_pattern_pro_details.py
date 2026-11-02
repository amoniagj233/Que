import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

mt5.initialize()
deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
exits = df[(df["magic"] == 4444) & (df["entry"].isin([1, 2]))].copy()

total = len(exits)
wins = exits[exits["profit"] > 0]
losses = exits[exits["profit"] < 0]
w_cnt = len(wins)
l_cnt = len(losses)
wr = (w_cnt / total * 100) if total > 0 else 0
net_pnl = exits["profit"].sum()
gross_win = wins["profit"].sum()
gross_loss = abs(losses["profit"].sum())
pf = (gross_win / gross_loss) if gross_loss > 0 else 0
best = exits["profit"].max()
worst = exits["profit"].min()
avg = exits["profit"].mean()

print(f"Total Trades: {total}")
print(f"Wins: {w_cnt}")
print(f"Losses: {l_cnt}")
print(f"Win Rate: {wr:.2f}%")
print(f"Gross Win: {gross_win:.2f}")
print(f"Gross Loss: {gross_loss:.2f}")
print(f"Net PnL: {net_pnl:.2f}")
print(f"Profit Factor: {pf:.2f}")
print(f"Best: {best:.2f}")
print(f"Worst: {worst:.2f}")
print(f"Avg: {avg:.2f}")

pos = mt5.positions_get()
open_pos = [p for p in pos if p.magic == 4444]
print(f"Active Open Positions: {len(open_pos)}")
for p in open_pos:
    print(f"Ticket #{p.ticket} | Open: {p.price_open} | Profit: {p.profit:.2f} | Comment: {p.comment}")

mt5.shutdown()
