import pandas as pd

df = pd.read_csv('data_cache/XAUUSD_M5_1MONTH.csv')
df['ma44'] = df['close'].rolling(44).mean()
df['ma332'] = df['close'].rolling(332).mean()
df['ret1h'] = df['close'].shift(-12) - df['close']
df['ret3h'] = df['close'].shift(-36) - df['close']
df['ret6h'] = df['close'].shift(-72) - df['close']

bull = df[df['ma44'] > df['ma332']]
bear = df[df['ma44'] < df['ma332']]

print("=== 44/332 REGIME PREDICTIVE POWER (M5 GOLD) ===")
print(f"Bullish Regime Bars: {len(bull)}")
print(f"  Avg 1h return: ${bull['ret1h'].mean():+.2f}/oz")
print(f"  Avg 3h return: ${bull['ret3h'].mean():+.2f}/oz")
print(f"  Avg 6h return: ${bull['ret6h'].mean():+.2f}/oz")
print(f"  Upward drift bias (3h): {(bull['ret3h'] > 0).mean()*100:.1f}%")

print(f"\nBearish Regime Bars: {len(bear)}")
print(f"  Avg 1h return: ${bear['ret1h'].mean():+.2f}/oz")
print(f"  Avg 3h return: ${bear['ret3h'].mean():+.2f}/oz")
print(f"  Avg 6h return: ${bear['ret6h'].mean():+.2f}/oz")
print(f"  Downward drift bias (3h): {(bear['ret3h'] < 0).mean()*100:.1f}%")
