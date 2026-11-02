import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from commander.backtester import backtester_ai
from commander.researcher import quant_researcher
from commander.evaluator import bot_evaluator

print("=== AGENT 3 & 4: ADVANCED QUANT R&D (200 EMA TREND FILTERED TURTLE SOUP) ===")

df = backtester_ai.load_gold_data(timeframe="M1", bars=10000)
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
closes = df["close"].to_numpy()
n = len(df)

# Calculate 200 EMA
ema_200 = pd.Series(closes).ewm(span=200, adjust=False).mean().to_numpy()

signals = np.zeros(n)
window = 30  # 30-candle structure window

for i in range(201, n):
    prior_high = np.max(highs[i - window - 1:i - 1])
    prior_low = np.min(lows[i - window - 1:i - 1])
    
    # Trend-aligned Bullish Sweep: Price > 200 EMA and sweeps discount low
    if closes[i] > ema_200[i] and lows[i] < prior_low - 0.25 and closes[i] > prior_low:
        signals[i] = 1
    # Trend-aligned Bearish Sweep: Price < 200 EMA and sweeps premium high
    elif closes[i] < ema_200[i] and highs[i] > prior_high + 0.25 and closes[i] < prior_high:
        signals[i] = -1

# Run event-driven backtest with 2.5R target ($4.50 TP vs $1.80 SL)
results = backtester_ai.run_event_driven_backtest(
    df=df,
    signals=signals,
    tp_dollars=4.50,
    sl_dollars=1.80,
    lot_size=0.01,
    starting_balance=10000.0
)

print("\n=== FILTERED CANDIDATE RESULTS ===")
print(f"  Total Qualifying Trades: {results['total_trades']}")
print(f"  Win Rate: {results['win_rate']}%")
print(f"  Profit Factor: {results['profit_factor']}")
print(f"  Net Profit: ${results['net_profit']:+,.2f}")
print(f"  Max Drawdown: {results['max_drawdown_pct']}%")
print(f"  Expectancy: ${results['expectancy']:+.2f} / trade")
print(f"  Sharpe Ratio: {results['sharpe_ratio']}")
print(f"  Monte Carlo P95 Max Drawdown: {results['monte_carlo_p95_dd']}%")

# Log refined experiment
backtester_ai.log_experiment("RES-09-TREND-ALIGNED-TURTLE-SOUP", "M1 Trend-Aligned Turtle Soup Sniper", results)
score_eval = bot_evaluator.evaluate_bot(results)
print(f"Agent 7 Composite Score: {score_eval['composite_score']} / 100 ({score_eval['confidence']})")
