import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

sym = mt5.symbol_info("XAUUSD")
print("=== SYMBOL FILLING MODES ===")
print(f"  Filling mode flags: {sym.filling_mode}")
print(f"  FOK  (1): {'YES' if sym.filling_mode & 1 else 'NO'}")
print(f"  IOC  (2): {'YES' if sym.filling_mode & 2 else 'NO'}")
print(f"  RETURN (3/both): {'YES' if sym.filling_mode == 3 else 'NO'}")

print("\n=== ACCOUNT STATE ===")
acc = mt5.account_info()
print(f"  Login: {acc.login} | Server: {acc.server}")
print(f"  Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f}")
print(f"  Margin: ${acc.margin:.2f} | Free Margin: ${acc.margin_free:.2f}")
print(f"  Margin Level: {acc.margin_level:.1f}%")

print("\n=== OPEN POSITIONS ===")
positions = mt5.positions_get(symbol="XAUUSD")
total_pnl = 0
if positions:
    for p in positions:
        cmt = p.comment.encode('ascii','replace').decode()
        side = "BUY" if p.type==0 else "SELL"
        print(f"  #{p.ticket} | {side} {p.volume} @ {p.price_open:.2f} | PnL: ${p.profit:+.2f} | Magic:{p.magic} | {cmt}")
        total_pnl += p.profit
print(f"  Total Floating PnL: ${total_pnl:+.2f}")

print("\n=== RECENT DEALS (last 2h) ===")
deals = mt5.history_deals_get(datetime.now()-timedelta(hours=2), datetime.now())
if deals:
    magic1111 = [d for d in deals if d.magic==1111]
    print(f"  Total deals: {len(deals)} | Magic 1111 deals: {len(magic1111)}")
    closed_pnl = sum(d.profit for d in magic1111)
    print(f"  Magic 1111 closed PnL: ${closed_pnl:+.2f}")
    for d in list(magic1111)[-10:]:
        cmt = d.comment.encode('ascii','replace').decode()
        print(f"  Deal #{d.ticket} | {d.symbol} | Vol:{d.volume} @ {d.price:.2f} | PnL:${d.profit:+.2f} | {cmt}")

mt5.shutdown()
