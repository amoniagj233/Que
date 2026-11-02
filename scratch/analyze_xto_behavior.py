import MetaTrader5 as mt5
from datetime import datetime

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

deals = mt5.history_deals_get(datetime(2026, 10, 20), datetime(2026, 11, 1))
print(f"Total deals in range: {len(deals) if deals else 0}")

if deals:
    xto_deals = [d for d in deals if d.magic == 1111 or 'Zalo' in d.comment or 'XTO' in d.comment]
    print(f"XTO deals count: {len(xto_deals)}")
    
    positions = {}
    for d in deals:
        pos_id = d.position_id
        if pos_id not in positions:
            positions[pos_id] = []
        positions[pos_id].append(d)
        
    print(f"\nRecent closed/open position cycles ({len(positions)}):")
    for pos_id, p_deals in list(positions.items())[-25:]:
        entry = p_deals[0]
        exit_deal = p_deals[-1] if len(p_deals) > 1 else None
        p_type = "BUY" if entry.type == 0 else "SELL"
        profit = sum(d.profit for d in p_deals)
        comment = entry.comment.encode('ascii', errors='ignore').decode()
        duration = (exit_deal.time - entry.time) if exit_deal else 'STILL OPEN'
        print(f"Pos #{pos_id} | Magic: {entry.magic} | {p_type} {entry.volume} @ {entry.price:.2f} | Deals: {len(p_deals)} | PnL: ${profit:+.2f} | Dur: {duration} | Comment: {comment}")

mt5.shutdown()
