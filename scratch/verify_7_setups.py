import sys; sys.path.insert(0, '.')
from gold_intelligence import generate_gold_trade_setups

setups = generate_gold_trade_setups()
print(f"Total setups generated: {len(setups)}")
for s in setups:
    print(f"- [{s['timeframe']}] {s['strategy']}: {s['direction']} Entry {s['entry']} SL {s['sl']} TP1 {s['tp1']} TP2 {s['tp2']} (Conf: {s['confidence_score']}%)")
