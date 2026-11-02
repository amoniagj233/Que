import MetaTrader5 as mt5

def check():
    mt5.initialize()
    positions = mt5.positions_get(symbol="XAUUSD")
    ea_positions = [p for p in (positions or []) if p.magic == 1111]
    print(f"XTO Speeder Positions (Magic 1111): {len(ea_positions)}")
    tot_vol = sum(p.volume for p in ea_positions)
    tot_profit = sum(p.profit for p in ea_positions)
    print(f"Total Basket Volume: {tot_vol:.2f} lots | Total Floating P/L: ${tot_profit:.2f}")
    for p in ea_positions:
        d = "BUY" if p.type == 0 else "SELL"
        print(f"  #{p.ticket}: {d} {p.volume} @ {p.price_open:.2f} | Profit: ${p.profit:.2f}")
    mt5.shutdown()

if __name__ == "__main__":
    check()
