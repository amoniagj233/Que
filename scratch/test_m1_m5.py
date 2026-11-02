import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5
from gold_intelligence import get_gold_candles, compute_atr, compute_rsi

def test():
    if not mt5.initialize():
        print("MT5 init failed")
        return

    df_m1 = get_gold_candles('M1', 50)
    df_m5 = get_gold_candles('M5', 50)
    print(f"M1 bars: {len(df_m1)}, latest M1 close: {df_m1['close'].iloc[-1]}")
    print(f"M5 bars: {len(df_m5)}, latest M5 close: {df_m5['close'].iloc[-1]}")

    atr_m1 = compute_atr(df_m1, 14).iloc[-1]
    atr_m5 = compute_atr(df_m5, 14).iloc[-1]
    print(f"ATR M1: {atr_m1:.2f}, ATR M5: {atr_m5:.2f}")

    mt5.shutdown()

if __name__ == '__main__':
    test()
