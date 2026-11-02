import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

mt5.initialize()
from_date = datetime(2026, 11, 1, 0, 0, 0)
to_date = datetime.now()

deals = mt5.history_deals_get(from_date, to_date)
df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
exits = df[df["entry"].isin([1, 2])].copy()

total_trades = len(exits)
wins = exits[exits["profit"] > 0]
losses = exits[exits["profit"] < 0]
be = exits[exits["profit"] == 0]

gross_win = wins["profit"].sum()
gross_loss = abs(losses["profit"].sum())
net_pnl = exits["profit"].sum()
wr = (len(wins) / total_trades * 100) if total_trades > 0 else 0

print("SUMMARY:")
print(f"Total: {total_trades}")
print(f"Wins: {len(wins)}")
print(f"Losses: {len(losses)}")
print(f"WinRate: {wr:.2f}%")
print(f"GrossWin: {gross_win:.2f}")
print(f"GrossLoss: {gross_loss:.2f}")
print(f"NetPnL: {net_pnl:.2f}")

bot_names = {
    1010: "XAU Dark Horizon Scalp AI",
    1111: "Apex-Quantum-DeepSL (Evo-1)",
    2222: "Mut-8037 Adaptive (Evo-2)",
    3333: "SMC Breaker Sniper",
    4444: "Strategic Pattern Pro",
    5555: "TikTalk Bot",
    6666: "Academic MA 44/332",
    7777: "Gold Auto Trader",
    8888: "ML Intelligence Engine",
    9090: "CRT Gold Pro",
    0: "Manual / System Deals",
    10101: "Proto Scalp Test"
}

print("\nBOT DETAILS:")
for m, g in exits.groupby("magic"):
    name = bot_names.get(m, f"Bot-{m}")
    w = len(g[g["profit"] > 0])
    l = len(g[g["profit"] < 0])
    tot = len(g)
    b_wr = (w / tot * 100) if tot > 0 else 0
    p = g["profit"].sum()
    print(f"Magic {m} | {name} | Trades: {tot} | Wins: {w} | Losses: {l} | WR: {b_wr:.1f}% | PnL: {p:.2f}")

mt5.shutdown()
