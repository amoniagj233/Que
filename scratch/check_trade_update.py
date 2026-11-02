import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

def main():
    if not mt5.initialize():
        print("MT5 initialization failed:", mt5.last_error())
        return

    acc = mt5.account_info()
    if not acc:
        print("Account info failed:", mt5.last_error())
        return

    print("=" * 70)
    print("HEADWAY MT5 ACCOUNT STATUS UPDATE")
    print("=" * 70)
    print(f"Account: #{acc.login} | Server: {acc.server}")
    print(f"Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f} | Margin: ${acc.margin:.2f}")
    print(f"Free Margin: ${acc.margin_free:.2f} | Floating P/L: ${acc.profit:.2f}")
    print(f"Leverage: 1:{acc.leverage}")
    print("-" * 70)

    # Open positions
    pos = mt5.positions_get()
    print(f"ACTIVE OPEN POSITIONS: {len(pos) if pos else 0}")
    if pos:
        for p in pos:
            side = "BUY" if p.type == 0 else "SELL"
            print(f"  • #{p.ticket} | {p.symbol} {side} {p.volume} lot")
            print(f"    Entry: {p.price_open:.2f} -> Current: {p.price_current:.2f}")
            print(f"    SL: {p.sl:.2f} | TP: {p.tp:.2f}")
            print(f"    Profit: ${p.profit:.2f} | Magic: {p.magic} | Comment: {p.comment}")
    else:
        print("  (No open positions currently)")

    print("-" * 70)
    # Closed deals today / recent 48 hours
    from_time = datetime.now(timezone.utc) - timedelta(days=2)
    deals = mt5.history_deals_get(from_time, datetime.now(timezone.utc))
    print(f"RECENT CLOSED DEALS (Past 48h): {len(deals) if deals else 0}")
    if deals:
        closed_deals = [d for d in deals if d.entry == 1] # Out deals
        for d in closed_deals[-10:]:
            side = "BUY" if d.type == 0 else "SELL"
            p_time = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"  • Deal #{d.ticket} (Pos #{d.position_id}) | {d.symbol} {side} {d.volume} lot @ {d.price:.2f} | P/L: ${d.profit:.2f} | Reason: {d.reason} | Time: {p_time}")

    # Gold Tick price
    tick = mt5.symbol_info_tick("XAUUSD")
    if tick:
        spread = tick.ask - tick.bid
        print("-" * 70)
        print(f"LIVE XAUUSD: Bid ${tick.bid:.2f} | Ask ${tick.ask:.2f} | Spread: ${spread:.2f}/oz")
    print("=" * 70)

    mt5.shutdown()

if __name__ == "__main__":
    main()
