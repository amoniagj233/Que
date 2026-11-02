import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

positions = mt5.positions_get(symbol="XAUUSD")
print(f"Total open XAUUSD positions: {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f"Ticket #{p.ticket}: {('BUY' if p.type==0 else 'SELL')} {p.volume} lots @ {p.price_open} (Current: {p.price_current}, SL: {p.sl}, TP: {p.tp}, P&L: ${p.profit:.2f}, Comment: {p.comment})")

mt5.shutdown()
