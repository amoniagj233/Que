import sys; sys.path.insert(0, '.')
import json
from gold_auto_trader import GoldAutoTrader
from gold_intelligence import generate_gold_trade_setups

trader = GoldAutoTrader()
print("Trader loaded. Config:")
print(json.dumps(trader.config, indent=2))

setups = generate_gold_trade_setups()
m1_setups = [s for s in setups if s.get("timeframe") == "M1" and s.get("confidence_score", 0) >= 90]
print(f"Actionable M1 setups: {len(m1_setups)}")
if m1_setups:
    s = m1_setups[0]
    print(f"Chosen M1 setup: {s['strategy']} {s['direction']} Entry: {s['entry']} SL: {s['sl']} TP1: {s['tp1']} (Conf: {s['confidence_score']}%)")

trader.running = False
