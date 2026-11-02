import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from commander.mt5_bridge import bridge

if bridge.initialize():
    acc = bridge.get_account_summary()
    print("=== ACCOUNT SUMMARY ===")
    for k, v in acc.items():
        print(f"  {k}: {v}")
    
    pos = bridge.get_open_positions()
    print(f"\n=== OPEN POSITIONS ({len(pos)}) ===")
    for p in pos:
        t = p['ticket']
        typ = p['type']
        vol = p['volume']
        sym = p['symbol']
        po = p['price_open']
        sl = p['sl']
        tp = p['tp']
        prof = p['profit']
        mag = p['magic']
        print(f"  Ticket #{t}: {typ} {vol} {sym} @ {po:.2f} | SL: {sl} | TP: {tp} | Profit: ${prof:+.2f} | Magic: {mag}")
else:
    print("Bridge init failed:", bridge.last_error)
