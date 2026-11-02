import MetaTrader5 as mt5
from datetime import datetime, timedelta

if mt5.initialize():
    from_time = datetime.now() - timedelta(hours=1)
    orders = mt5.history_orders_get(from_time, datetime.now())
    if orders:
        print(f"Historical orders in last 1 hour: {len(orders)}")
        for o in orders:
            print(f"Order #{o.ticket} | Pos #{o.position_id} | State: {o.state} | Type: {o.type} | Lots: {o.volume_current}/{o.volume_initial} | Price: {o.price_current}/{o.price_open} | Magic: {o.magic} | Comment: {o.comment}")
    else:
        print("No historical orders found.")
    
    # Check total history
    all_orders = mt5.history_orders_get(datetime(2026, 1, 1), datetime.now())
    print(f"Total orders since Jan 2026: {len(all_orders) if all_orders else 0}")
    if all_orders:
        for o in all_orders[-5:]:
            print(f"  Recent Order #{o.ticket} | State: {o.state} | Magic: {o.magic} | Comment: {o.comment}")
            
    mt5.shutdown()
