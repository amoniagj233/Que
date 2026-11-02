import MetaTrader5 as mt5

if mt5.initialize():
    acc = mt5.account_info()
    print(f"Logged into {acc.login} ({acc.server})")
    positions = mt5.positions_get()
    print(f"Active positions ({len(positions) if positions else 0}):")
    if positions:
        for p in positions:
            print(f"Ticket #{p.ticket} | Sym: {p.symbol} | Type: {p.type} | Lots: {p.volume} | Open: {p.price_open} | Current: {p.price_current} | Profit: {p.profit} | Magic: {p.magic} | Comment: {p.comment}")
    mt5.shutdown()
