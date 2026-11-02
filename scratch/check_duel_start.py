import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

# Dual run started around 19:28 UTC
start_time = datetime(2026, 10, 28, 19, 25, 0)
deals = mt5.history_deals_get(start_time, datetime(2026, 10, 30))

print(f"Checking deals since {start_time}...")
if deals:
    b1_deals = [d for d in deals if d.magic == 1111 and d.entry == 1] # entry=1 is deal out (closed)
    b2_deals = [d for d in deals if d.magic == 2222 and d.entry == 1]
    
    print(f"Total deals: {len(deals)}")
    print(f"Bot 1 (Magic 1111) Closed Deals: {len(b1_deals)}")
    print(f"Bot 2 (Magic 2222) Closed Deals: {len(b2_deals)}")
    
    for d in deals:
        if d.magic in [1111, 2222]:
            cmt = d.comment.encode('ascii', errors='ignore').decode()
            print(f"  Deal #{d.ticket} | Magic: {d.magic} | Entry: {d.entry} | Lots: {d.volume} @ {d.price:.2f} | PnL: ${d.profit:+.2f} | {cmt}")
else:
    print("No deals found yet.")

mt5.shutdown()
