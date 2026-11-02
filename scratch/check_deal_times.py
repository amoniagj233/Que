import MetaTrader5 as mt5
from datetime import datetime

if mt5.initialize():
    deals = mt5.history_deals_get(datetime(2026, 10, 28, 19, 0, 0), datetime(2026, 10, 30))
    print(f"Total deals: {len(deals)}")
    for d in deals:
        if d.magic in [1111, 2222] and d.entry == 1:
            t_str = datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M:%S')
            cmt = d.comment.encode('ascii', errors='ignore').decode()
            print(f"Time: {t_str} | Deal #{d.ticket} | Magic: {d.magic} | PnL: ${d.profit:+.2f} | {cmt}")
    mt5.shutdown()
