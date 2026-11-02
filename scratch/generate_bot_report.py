import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

if not mt5.initialize():
    print("Failed to initialize MT5")
    exit(1)

from_date = datetime.now() - timedelta(days=3)
to_date = datetime.now() + timedelta(days=1)
deals = mt5.history_deals_get(from_date, to_date)

if not deals:
    print("No deals found")
    mt5.shutdown()
    exit(0)

df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
exits = df[df["entry"].isin([1, 2])].copy()

bot_map = {
    1010: ("XAU Dark Horizon Scalp AI", "Real-Time Telemetry (Impulse Meter, Wick Pressure, Liquidity Sweep & Turn Radar)"),
    1111: ("Apex-Quantum-DeepSL", "Multi-Timeframe Volatility Confluence with Deep Dynamic Stop-Loss"),
    2222: ("Mut-8037 Adaptive Core", "Dynamic Asymmetric ATR Scalping with Elastic Trailing Runner"),
    3333: ("SMC Breaker Sniper", "Turtle Soup Swing Liquidity Sweep + Order Block Reclaim Confirmation"),
    4444: ("Strategic Pattern Pro", "Asymmetric ATR Range Box Breakout with 21/55/200 EMA Macro Gating"),
    5555: ("TikTalk Bot", "Fast 9/21 Exponential Crossover + Multi-Timeframe RSI Dip Confirmation"),
    6666: ("Academic MA 44/332", "Institutional Dual Moving Average Envelope (44/332 Period Alignment)"),
    7777: ("Gold Auto Trader", "Session High/Low Range Reversal with Volume Surge Confirmation"),
    8888: ("ML Intelligence Engine", "Machine Learning Classifier trained on Rolling Volatility & Momentum"),
    9090: ("CRT Gold Pro", "Candle Range Theory (M30 Reference Range + M5 Sweep + M2 Engulfing Confirmation)"),
    0: ("Manual / System Init", "Manual or Initial Platform Calibration Deals"),
    10101: ("Proto Scalp Verification", "Inaugural System Health Probe")
}

records = []
for magic, grp in exits.groupby("magic"):
    if magic not in bot_map:
        name, strat = f"Bot-{magic}", "Unassigned Strategy"
    else:
        name, strat = bot_map[magic]
        
    wins = grp[grp["profit"] > 0]
    losses = grp[grp["profit"] < 0]
    total = len(grp)
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / total * 100) if total > 0 else 0
    gross_win = float(wins["profit"].sum())
    gross_loss = float(abs(losses["profit"].sum()))
    net_pnl = float(grp["profit"].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
    best_trade = float(grp["profit"].max()) if total > 0 else 0.0
    worst_trade = float(grp["profit"].min()) if total > 0 else 0.0
    avg_trade = float(grp["profit"].mean()) if total > 0 else 0.0
    
    records.append({
        "magic": magic,
        "name": name,
        "strategy": strat,
        "total": total,
        "wins": w_count,
        "losses": l_count,
        "wr": wr,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "pf": pf,
        "best": best_trade,
        "worst": worst_trade,
        "avg": avg_trade
    })

res_df = pd.DataFrame(records).sort_values(by="net_pnl", ascending=False).reset_index(drop=True)

print("=" * 85)
print("             APEX AI — FLEET PERFORMANCE RANKING TABLE             ")
print("=" * 85)

for rank, r in res_df.iterrows():
    print(f"RANK #{rank+1}: {r['name']} (Magic: {r['magic']})")
    print(f"  Strategy      : {r['strategy']}")
    print(f"  Total Trades  : {r['total']} | Won: {r['wins']} | Lost: {r['losses']} | Win Rate: {r['wr']:.1f}%")
    print(f"  Financials    : Gross Win: +${r['gross_win']:.2f} | Gross Loss: -${r['gross_loss']:.2f} | Net P&L: ${r['net_pnl']:+.2f}")
    print(f"  Profit Factor : {r['pf']:.2f} | Avg Trade: ${r['avg']:+.2f} | Best: ${r['best']:+.2f} | Worst: ${r['worst']:+.2f}")
    print("-" * 85)

# Also rank individual top 10 winning trades across all bots
print("\n" + "=" * 85)
print("             TOP 10 BEST INDIVIDUAL TRADES ACROSS FLEET            ")
print("=" * 85)
top_trades = exits.sort_values(by="profit", ascending=False).head(10)
for i, (_, t) in enumerate(top_trades.iterrows(), 1):
    m = t["magic"]
    b_name = bot_map.get(m, (f"Bot-{m}", ""))[0]
    dt = datetime.fromtimestamp(t["time"]).strftime("%Y-%m-%d %H:%M:%S")
    print(f"#{i:2d} | Deal #{t['ticket']} | {b_name:<26} (Magic {m}) | Profit: +${t['profit']:.2f} | Time: {dt}")

print("\n" + "=" * 85)
print("             TOP 5 BIGGEST DRAWDOWN / LOSS TRADES ACROSS FLEET      ")
print("=" * 85)
worst_trades = exits.sort_values(by="profit", ascending=True).head(5)
for i, (_, t) in enumerate(worst_trades.iterrows(), 1):
    m = t["magic"]
    b_name = bot_map.get(m, (f"Bot-{m}", ""))[0]
    dt = datetime.fromtimestamp(t["time"]).strftime("%Y-%m-%d %H:%M:%S")
    print(f"#{i:2d} | Deal #{t['ticket']} | {b_name:<26} (Magic {m}) | Loss: ${t['profit']:.2f} | Time: {dt}")

mt5.shutdown()
