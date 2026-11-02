import pandas as pd
import numpy as np

df = pd.read_csv('data_cache/XAUUSD_M5_1MONTH.csv')
df['ma44'] = df['close'].rolling(44).mean()
df['ma332'] = df['close'].rolling(332).mean()

# Trend definition: price above ma332
# Pullback: price touches or crosses below ma44, then closes back above ma44
df['in_uptrend'] = df['close'] > df['ma332']
df['pullback_buy'] = df['in_uptrend'] & (df['low'] <= df['ma44']) & (df['close'] > df['ma44']) & (df['close'].shift(1) <= df['ma44'].shift(1))

df['in_downtrend'] = df['close'] < df['ma332']
df['pullback_sell'] = df['in_downtrend'] & (df['high'] >= df['ma44']) & (df['close'] < df['ma44']) & (df['close'].shift(1) >= df['ma44'].shift(1))

df['fwd_max_run_up_3h'] = df['high'].rolling(36).max().shift(-36) - df['close']
df['fwd_max_drawdown_3h'] = df['close'] - df['low'].rolling(36).min().shift(-36)

buys = df[df['pullback_buy']]
sells = df[df['pullback_sell']]

print("=== PULLBACK TO 44 IN DIRECTION OF 332 ===")
print(f"Buy setups found: {len(buys)}")
print(f"  Avg 3h Max Run-Up: ${buys['fwd_max_run_up_3h'].mean():.2f}/oz")
print(f"  Avg 3h Max Drawdown: ${buys['fwd_max_drawdown_3h'].mean():.2f}/oz")
print(f"  Win ratio (RunUp > 1.5x Drawdown): {(buys['fwd_max_run_up_3h'] > 1.5 * buys['fwd_max_drawdown_3h']).mean()*100:.1f}%")

print(f"\nSell setups found: {len(sells)}")
print(f"  Avg 3h Max Run-Up: ${sells['fwd_max_run_up_3h'].mean():.2f}/oz")
print(f"  Avg 3h Max Drawdown: ${sells['fwd_max_drawdown_3h'].mean():.2f}/oz")
