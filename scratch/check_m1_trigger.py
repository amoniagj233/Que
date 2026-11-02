import sys; sys.path.insert(0, '.')
import json
import MetaTrader5 as mt5
from gold_intelligence import generate_gold_trade_setups

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

setups = generate_gold_trade_setups()
m1_setups = [s for s in setups if s.get("timeframe") == "M1" and s.get("confidence_score", 0) >= 90]

print(f"Qualifying 1MTF setups (>=90% conf): {len(m1_setups)}")
if m1_setups:
    s = m1_setups[0]
    print(f"Strategy: {s['strategy']}")
    print(f"Direction: {s['direction']}")
    print(f"Confidence: {s['confidence_score']}%")
    print(f"Entry: {s['entry']}")
    print(f"SL: {s['sl']}")
    print(f"TP1 (Fixed): {s['tp1']}")
    print(f"TP2 (Runner): {s['tp2']}")
else:
    print("No qualifying M1 setups found right now.")

mt5.shutdown()
