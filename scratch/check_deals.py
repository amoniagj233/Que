import MetaTrader5 as mt5
from datetime import datetime, timedelta

if mt5.initialize():
    from_time = datetime.now() - timedelta(minutes=15)
    deals = mt5.history_deals_get(from_time, datetime.now())
    if deals:
        print(f"Recent deals in last 15 min: {len(deals)}")
        for d in deals:
            d_type = "BUY" if d.type == 0 else "SELL"
            print(f"Deal #{d.ticket} | Order #{d.order} | Pos #{d.position_id} | {d_type} {d.volume} @ {d.price:.2f} | Profit: ${d.profit:+.2f} | Reason: {d.reason} | Comment: {d.comment}")
    
    positions = mt5.positions_get(symbol="XAUUSD")
    print(f"\nAll current open positions on XAUUSD: {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            print(f"  Ticket #{p.ticket} | Pos #{p.identifier} | {'BUY' if p.type==0 else 'SELL'} {p.volume} @ {p.price_open:.2f} | Magic: {p.magic} | SL: {p.sl} | TP: {p.tp}")
            
    mt5.shutdown()
