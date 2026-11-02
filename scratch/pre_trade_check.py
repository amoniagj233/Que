import MetaTrader5 as mt5
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    exit(1)

acc = mt5.account_info()
tick = mt5.symbol_info_tick("XAUUSD")
sym = mt5.symbol_info("XAUUSD")

print(f"Account  : {acc.login} | {acc.server}")
print(f"Balance  : ${acc.balance:.2f} | Equity: ${acc.equity:.2f} | Margin: ${acc.margin:.2f}")
print(f"XAUUSD   : Bid={tick.bid:.2f} | Ask={tick.ask:.2f} | Spread={round((tick.ask-tick.bid)*100,1)} pts")
print(f"Point    : {sym.point} | Digits: {sym.digits} | Vol Min: {sym.volume_min}")
print()

positions = mt5.positions_get(symbol="XAUUSD")
if positions:
    print(f"Open positions on XAUUSD ({len(positions)}):")
    for p in positions:
        cmt = p.comment.encode('ascii', 'replace').decode('ascii')
        ptype = "BUY" if p.type == 0 else "SELL"
        print(f"  #{p.ticket} | {ptype} {p.volume} @ {p.price_open:.2f} | Now: {p.price_current:.2f} | PnL: ${p.profit:+.2f} | Magic: {p.magic} | {cmt}")
else:
    print("No open positions on XAUUSD.")

mt5.shutdown()
