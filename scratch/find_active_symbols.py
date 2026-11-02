import MetaTrader5 as mt5

if mt5.initialize():
    symbols = mt5.symbols_get()
    open_syms = []
    for s in symbols:
        if s.visible:
            tick = mt5.symbol_info_tick(s.name)
            # Check if tick is fresh (within last 2 hours)
            if tick and tick.time > 0:
                open_syms.append((s.name, s.path, s.volume_min, s.trade_contract_size, s.point))
    print(f"Total visible symbols with ticks: {len(open_syms)}")
    for sym_info in open_syms[:30]:
        print(sym_info)
    mt5.shutdown()
