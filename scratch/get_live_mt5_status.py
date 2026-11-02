import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

def query():
    init_res = mt5.initialize(path=r"C:\Program Files\Headway MT5 Terminal\terminal64.exe")
    if not init_res:
        init_res = mt5.initialize()
    if not init_res:
        print("MT5 Init Failed:", mt5.last_error())
        return

    acc = mt5.account_info()
    if acc is None:
        print("No active account")
        return

    print("=== ACCOUNT ===")
    print(f"Login: {acc.login} | Server: {acc.server}")
    print(f"Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f} | Profit: ${acc.profit:.2f} | Margin Free: ${acc.margin_free:.2f}")

    tick = mt5.symbol_info_tick("XAUUSD")
    if tick:
        print(f"XAUUSD Live Quote -> Bid: {tick.bid} | Ask: {tick.ask}")

    positions = mt5.positions_get()
    print(f"\n=== OPEN POSITIONS ({len(positions) if positions else 0}) ===")
    if positions:
        for p in positions:
            d = "BUY" if p.type == 0 else "SELL"
            print(f"Ticket #{p.ticket}: {p.symbol} {d} {p.volume} lots @ {p.price_open:.2f} | SL: {p.sl} | TP: {p.tp} | Cur: {p.price_current:.2f} | Profit: ${p.profit:.2f} | Comment: {p.comment}")

    # Today and Yesterday deals
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=2)
    deals = mt5.history_deals_get(from_date, now)
    print(f"\n=== CLOSED DEALS RECENT ({len(deals) if deals else 0}) ===")
    if deals:
        for d in deals[-15:]:
            t_str = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Deal #{d.ticket} ({t_str}): {d.symbol} type={d.type} vol={d.volume} @ {d.price:.2f} | Profit: ${d.profit:.2f} | PosID: {d.position_id} | Comment: {d.comment}")

    mt5.shutdown()

if __name__ == "__main__":
    query()
