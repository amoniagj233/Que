import MetaTrader5 as mt5
import time

if mt5.initialize():
    symbols = mt5.symbols_get()
    now = time.time()
    fresh = []
    for s in symbols:
        tick = mt5.symbol_info_tick(s.name)
        if tick and (now - tick.time) < 300:  # updated within last 5 minutes
            fresh.append((s.name, s.path, s.volume_min, (now - tick.time)))
    print(f"Total LIVE ticks within last 5m: {len(fresh)}")
    for item in fresh:
        print(item)
    mt5.shutdown()
