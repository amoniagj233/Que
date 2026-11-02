import MetaTrader5 as mt5

if not mt5.initialize():
    print("Failed to initialize MT5")
    exit(1)

pos = mt5.positions_get()
print(f"Total Open Positions: {len(pos) if pos else 0}")
print("-" * 96)
print(f"{'Ticket':<12} | {'Magic':<6} | {'Bot / Strategy Comment':<28} | {'Open':<8} | {'SL':<12} | {'TP':<8}")
print("-" * 96)

if pos:
    for p in sorted(pos, key=lambda x: x.magic):
        sl_str = f"{p.sl:.2f}" if p.sl > 0 else "NO SL (0.0)"
        tp_str = f"{p.tp:.2f}" if p.tp > 0 else "None"
        print(f"#{p.ticket:<11} | {p.magic:<6} | {p.comment:<28} | {p.price_open:<8.2f} | {sl_str:<12} | {tp_str:<8}")

mt5.shutdown()
