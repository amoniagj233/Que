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

print("=== AGENT 3 & 4: AUTONOMOUS QUANT R&D PIPELINE ===")

# 1. Synthesize hypothesis
hyp = quant_researcher.generate_new_hypothesis("M1 Turtle Soup & Micro-CHoCH Scalper")
print(f"Generated Hypothesis: {hyp['id']} - {hyp['name']}")
print(f"Core Idea: {hyp['hypothesis']}")

# 2. Load historical M1 Gold data
print("Fetching 10,000 Gold M1 bars...")
df = backtester_ai.load_gold_data(timeframe="M1", bars=10000)
print(f"Loaded {len(df)} bars of Gold price data.")

# 3. Strategy Signal Generator: Turtle Soup + CHoCH on M1
# Signal: If low breaches 20-candle low by > $0.20 and closes back above it -> BUY (+1)
#         If high breaches 20-candle high by > $0.20 and closes back below it -> SELL (-1)
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
closes = df["close"].to_numpy()
n = len(df)

signals = np.zeros(n)
window = 20

# Rolling 20-candle swing high/low
for i in range(window + 1, n):
    prior_high = np.max(highs[i - window - 1:i - 1])
    prior_low = np.min(lows[i - window - 1:i - 1])
    
    # Bullish Turtle Soup Sweep:
    if lows[i] < prior_low - 0.20 and closes[i] > prior_low:
        signals[i] = 1
    # Bearish Turtle Soup Sweep:
    elif highs[i] > prior_high + 0.20 and closes[i] < prior_high:
        signals[i] = -1

# 4. Event-Driven Backtest (TP $3.00, SL $2.20, accounting for spreads & slippage)
print("Executing Event-Driven Backtest with realistic gold costs ($0.30 spread, $3.50 comm, $0.15 slippage)...")
results = backtester_ai.run_event_driven_backtest(
    df=df,
    signals=signals,
    tp_dollars=3.00,
    sl_dollars=2.20,
    lot_size=0.01,
    starting_balance=10000.0
)

print("\n=== BACKTEST VALIDATION RESULTS ===")
print(f"  Total Qualifying Trades: {results['total_trades']}")
print(f"  Win Rate: {results['win_rate']}%")
print(f"  Profit Factor: {results['profit_factor']}")
print(f"  Net Profit: ${results['net_profit']:+,.2f}")
print(f"  Max Drawdown: {results['max_drawdown_pct']}%")
print(f"  Expectancy: ${results['expectancy']:+.2f} / trade")
print(f"  Sharpe Ratio: {results['sharpe_ratio']}")
print(f"  Monte Carlo P95 Max Drawdown: {results['monte_carlo_p95_dd']}%")

# 5. Log experiment permanently
backtester_ai.log_experiment(hyp["id"], hyp["name"], results)
print("Experiment permanently recorded in backtest_experiments.json.")

# 6. Evaluate via Agent 7
score_eval = bot_evaluator.evaluate_bot(results)
print(f"Agent 7 Composite Score: {score_eval['composite_score']} / 100 ({score_eval['confidence']})")
