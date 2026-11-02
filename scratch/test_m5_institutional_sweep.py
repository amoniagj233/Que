import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from commander.backtester import backtester_ai
from commander.evaluator import bot_evaluator

print("=== AGENT 3 & 4: M5 INSTITUTIONAL SWEEP WITH ATR EXTENSION ===")

df = backtester_ai.load_gold_data(timeframe="M5", bars=10000)
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
closes = df["close"].to_numpy()
n = len(df)

ema_55 = pd.Series(closes).ewm(span=55, adjust=False).mean().to_numpy()
ema_200 = pd.Series(closes).ewm(span=200, adjust=False).mean().to_numpy()

signals = np.zeros(n)
window = 24  # 2 hours of M5 structure

for i in range(201, n):
    prior_high = np.max(highs[i - window - 1:i - 1])
    prior_low = np.min(lows[i - window - 1:i - 1])
    
    # In bull trend (EMA 55 > EMA 200), buy sweep of lows
    if ema_55[i] > ema_200[i] and lows[i] < prior_low - 0.50 and closes[i] > prior_low:
        signals[i] = 1
    # In bear trend (EMA 55 < EMA 200), sell sweep of highs
    elif ema_55[i] < ema_200[i] and highs[i] > prior_high + 0.50 and closes[i] < prior_high:
        signals[i] = -1

results = backtester_ai.run_event_driven_backtest(
    df=df,
    signals=signals,
    tp_dollars=8.00,
    sl_dollars=3.50,
    lot_size=0.01,
    starting_balance=10000.0
)

print("\n=== M5 INSTITUTIONAL SWEEP RESULTS ===")
print(f"  Total Qualifying Trades: {results['total_trades']}")
print(f"  Win Rate: {results['win_rate']}%")
print(f"  Profit Factor: {results['profit_factor']}")
print(f"  Net Profit: ${results['net_profit']:+,.2f}")
print(f"  Max Drawdown: {results['max_drawdown_pct']}%")
print(f"  Expectancy: ${results['expectancy']:+.2f} / trade")
print(f"  Sharpe Ratio: {results['sharpe_ratio']}")
print(f"  Monte Carlo P95 Max Drawdown: {results['monte_carlo_p95_dd']}%")

backtester_ai.log_experiment("RES-10-M5-INSTITUTIONAL-SWEEP", "M5 Institutional Sweep & EMA Confluence", results)
score_eval = bot_evaluator.evaluate_bot(results)
print(f"Agent 7 Composite Score: {score_eval['composite_score']} / 100 ({score_eval['confidence']})")
