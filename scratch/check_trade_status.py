import MetaTrader5 as mt5

if mt5.initialize():
    pos = mt5.positions_get(ticket=1388573398)
    if pos:
        p = pos[0]
        tick = mt5.symbol_info_tick("XAUUSD")
        print(f"Test Trade Ticket #{p.ticket}:")
        print(f"  Type       : {'BUY' if p.type == 0 else 'SELL'}")
        print(f"  Lots       : {p.volume}")
        print(f"  Open Price : ${p.price_open:.2f}")
        print(f"  Current    : ${p.price_current:.2f}")
        print(f"  P/L        : ${p.profit:+.2f}")
        print(f"  SL         : ${p.sl:.2f} ({p.price_current - p.sl:+.2f} away)")
        print(f"  TP         : ${p.tp:.2f} ({p.tp - p.price_current:+.2f} away)")
    else:
        deals = mt5.history_deals_get(ticket=1388573398)
        print("Position closed or moved to history.")
    mt5.shutdown()
