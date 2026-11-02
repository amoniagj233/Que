import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

positions = mt5.positions_get(symbol="XAUUSD")
print(f"Open XAUUSD positions count: {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f"Ticket: {p.ticket}, Type: {p.type}, Volume: {p.volume}, Price Open: {p.price_open}, Current: {p.price_current}, SL: {p.sl}, TP: {p.tp}, Comment: {p.comment}")

mt5.shutdown()
