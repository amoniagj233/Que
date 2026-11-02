import MetaTrader5 as mt5

def check():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return

    acc = mt5.account_info()
    print(f"Account: {acc.login}, Balance: {acc.balance}, Equity: {acc.equity}, Free Margin: {acc.margin_free}")

    pos = mt5.positions_get()
    print(f"Total Open Positions: {len(pos) if pos else 0}")
    if pos:
        for p in pos:
            direction = "BUY" if p.type == 0 else "SELL"
            print(f"#{p.ticket}: {p.symbol} {direction} vol={p.volume} open={p.price_open} sl={p.sl} tp={p.tp} profit={p.profit}")

    tick = mt5.symbol_info_tick("XAUUSD")
    if tick:
        print(f"XAUUSD Bid: {tick.bid}, Ask: {tick.ask}, Spread: {round(tick.ask - tick.bid, 2)}")
    else:
        print("No tick for XAUUSD")

    mt5.shutdown()

if __name__ == '__main__':
    check()
