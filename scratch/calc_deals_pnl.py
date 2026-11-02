import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

mt5.initialize()
now = datetime.now(timezone.utc)
from_date = now - timedelta(days=2)
deals = mt5.history_deals_get(from_date, now)

so_deals = []
profit_deals = []
loss_deals = []

for d in (deals or []):
    if d.entry == 1: # Deal out (close)
        t_str = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        info = {
            "ticket": d.ticket,
            "pos_id": d.position_id,
            "symbol": d.symbol,
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "time": t_str,
            "comment": d.comment
        }
        if d.profit > 0:
            profit_deals.append(info)
        elif d.profit < 0:
            loss_deals.append(info)
            if "[so" in d.comment or "so" in d.comment:
                so_deals.append(info)

print(f"Total Exit Deals: {len(profit_deals) + len(loss_deals)}")
print(f"Profitable Exits: {len(profit_deals)} | Total Gain: ${sum(d['profit'] for d in profit_deals):.2f}")
print(f"Losing Exits: {len(loss_deals)} | Total Loss: ${sum(d['profit'] for d in loss_deals):.2f}")
print(f"Stop-Out Deals (Margin Call [so]): {len(so_deals)} | Total SO Loss: ${sum(d['profit'] for d in so_deals):.2f}")

print("\n--- Big Losses (No-SL & Stop-Outs) ---")
for d in sorted(loss_deals, key=lambda x: x["profit"])[:8]:
    print(f"Pos #{d['pos_id']} closed at {d['time']} @ {d['price']:.2f} | PnL: ${d['profit']:.2f} | Comment: {d['comment']}")

mt5.shutdown()
