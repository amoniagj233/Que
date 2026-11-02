import sys; sys.path.insert(0, '.')
from gold_intelligence import generate_gold_trade_setups

setups = generate_gold_trade_setups()
m1_setups = [s for s in setups if s.get("timeframe") == "M1"]
print(f"Total M1 Setups: {len(m1_setups)}")
for s in m1_setups:
    print(f"[{s['timeframe']}] {s['strategy']}: {s['direction']} Entry: {s['entry']} SL: {s['sl']} TP1: {s['tp1']} TP2: {s['tp2']} (Conf: {s['confidence_score']}%)")
    print(f"  Quality: {s.get('quality')}")
    print(f"  Invalidation: {s.get('invalidation')}")
