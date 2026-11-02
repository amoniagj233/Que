import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5
from gold_intelligence import generate_gold_trade_setups

def verify():
    if not mt5.initialize():
        print("MT5 init failed")
        return
        
    setups = generate_gold_trade_setups()
    print(f"Total setups generated: {len(setups)}")
    for i, s in enumerate(setups, 1):
        strat = s.get("strategy")
        direction = s.get("direction")
        conf = s.get("confidence_score")
        entry = s.get("entry")
        sl = s.get("sl")
        tp1 = s.get("tp1")
        tp2 = s.get("tp2")
        tp3 = s.get("tp3")
        rr = s.get("rr_ratio")
        print(f"\n{i}. [{strat}]")
        print(f"   Bias/Direction: {direction} | Conviction: {conf}% | R:R: {rr}")
        print(f"   Entry: {entry} | SL: {sl} | TP1: {tp1} | TP2: {tp2} | TP3: {tp3}")
        print(f"   Signals: {s.get('supporting_signals')[:2]}")
        print(f"   Invalidation: {s.get('invalidation', {}).get('stop_loss_invalidation')}")

    mt5.shutdown()

if __name__ == '__main__':
    verify()
