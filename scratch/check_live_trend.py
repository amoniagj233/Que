import MetaTrader5 as mt5
import pandas as pd

if mt5.initialize():
    rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M5, 0, 100)
    df = pd.DataFrame(rates)
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema55'] = df['close'].ewm(span=55).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()
    c = df.iloc[-1]
    trend = "BULLISH" if (c['close'] > c['ema200'] and c['ema21'] > c['ema55']) else "BEARISH" if (c['close'] < c['ema200'] and c['ema21'] < c['ema55']) else "CONSOLIDATING"
    print(f"Gold Price: {c['close']:.2f} | EMA21: {c['ema21']:.2f} | EMA55: {c['ema55']:.2f} | EMA200: {c['ema200']:.2f} | Trend: {trend}")
    mt5.shutdown()
