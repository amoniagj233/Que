import MetaTrader5 as mt5

def check():
    if not mt5.initialize():
        print("MT5 init failed")
        return
        
    positions = mt5.positions_get(symbol="XAUUSD")
    print(f"Open Gold Positions: {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            direction = "BUY" if p.type == 0 else "SELL"
            print(f"Ticket #{p.ticket}: {p.symbol} {direction} {p.volume} lots @ {p.price_open}")
            print(f"  SL: {p.sl}, TP: {p.tp}")
            print(f"  Current Price: {p.price_current}, Floating Profit: ${p.profit:.2f}")
            print(f"  Comment: {p.comment}")
            
    all_pos = mt5.positions_get()
    print(f"\nTotal positions on entire account: {len(all_pos) if all_pos else 0}")
    for ap in (all_pos or []):
        print(f"  #{ap.ticket} {ap.symbol} {ap.profit}")

    mt5.shutdown()

if __name__ == '__main__':
    check()
