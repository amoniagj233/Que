from gold_intelligence import generate_gold_trade_setups, get_gold_candles, analyze_market_regime
import MetaTrader5 as mt5

def test_gold():
    if not mt5.initialize():
        print("MT5 init failed")
        return

    print("=== LIVE GOLD DATA ===")
    df_m15 = get_gold_candles("M15", 50)
    df_h1 = get_gold_candles("H1", 50)
    if not df_m15.empty:
        print(f"M15 latest close: {df_m15['close'].iloc[-1]}, H1 latest close: {df_h1['close'].iloc[-1]}")
        regime = analyze_market_regime(df_h1)
        print(f"H1 Regime: {regime['regime']}, Bias: {regime['bias']}")

    setups = generate_gold_trade_setups()
    print(f"\nTotal Gold Setups Generated: {len(setups)}")
    for s in setups:
        print(f"- ID: {s.get('id')}")
        print(f"  Strategy: {s.get('strategy')}")
        print(f"  Direction: {s.get('direction')}")
        print(f"  Confidence: {s.get('confidence_score')}%")
        print(f"  Entry: {s.get('entry')}, SL: {s.get('sl')}, TP1: {s.get('tp1')}, TP2: {s.get('tp2')}")
        print(f"  Signals: {s.get('supporting_signals')}")
        print(f"  Invalidation: {s.get('invalidation', {}).get('stop_loss_invalidation')}")
        print()

    mt5.shutdown()

if __name__ == '__main__':
    test_gold()
