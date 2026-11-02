import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Init Failed:", mt5.last_error())
    exit(1)

positions = mt5.positions_get()
print(f"Total Positions: {len(positions) if positions else 0}")
for p in (positions or []):
    side = "BUY" if p.type == 0 else "SELL"
    print(f"Ticket: {p.ticket} | Magic: {p.magic} | Type: {side} | Vol: {p.volume} | Profit: ${p.profit:.2f} | Comment: '{p.comment}'")

account = mt5.account_info()
print(f"Balance: ${account.balance:.2f} | Equity: ${account.equity:.2f} | Margin: ${account.margin:.2f}")

mt5.shutdown()
