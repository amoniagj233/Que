import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

if mt5.initialize():
    acc = mt5.account_info()
    print(f"Logged into {acc.login} ({acc.server})")
    
    # Check history using wide range
    from_time = datetime(2026, 10, 20)
    to_time = datetime(2026, 10, 30)
    deals = mt5.history_deals_get(from_time, to_time)
    print(f"Total deals in range: {len(deals) if deals else 0}")
    if deals:
        for d in deals[-10:]:
            sanitized = d.comment.encode('ascii', 'replace').decode('ascii')
            print(f"Deal #{d.ticket} | Pos #{d.position_id} | Order #{d.order} | Profit: ${d.profit:+.2f} | Magic: {d.magic} | {sanitized}")
            
    mt5.shutdown()
