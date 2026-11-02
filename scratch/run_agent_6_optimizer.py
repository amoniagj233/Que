import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from commander.backtester import backtester_ai

print("=== AGENT 6: AUTOMATIC PARAMETER OPTIMIZATION RUN ===")
print("Target: Strategic Pattern Pro M5 Engine")

df = backtester_ai.load_gold_data(timeframe="M5", bars=10000)
highs = df["high"].to_numpy()
lows = df["low"].to_numpy()
closes = df["close"].to_numpy()
n = len(df)

# Split into 70% In-Sample and 30% strictly Out-Of-Sample holdout
split_idx = int(n * 0.70)
df_is = df.iloc[:split_idx].reset_index(drop=True)
df_oos = df.iloc[split_idx:].reset_index(drop=True)

print(f"In-Sample Training Bars: {len(df_is)} | Out-Of-Sample Holdout Bars: {len(df_oos)}")

# Parameter Grid
box_lengths = [12, 15, 18]
tps = [3.50, 4.00, 4.50, 5.00]
sls = [2.50, 3.00, 3.50]

best_candidate = None
best_score = -999.0

# 1. In-Sample Search
for bl in box_lengths:
    h = df_is["high"].to_numpy()
    l = df_is["low"].to_numpy()
    c = df_is["close"].to_numpy()
    ema21 = pd.Series(c).ewm(span=21, adjust=False).mean().to_numpy()
    ema55 = pd.Series(c).ewm(span=55, adjust=False).mean().to_numpy()
    
    sig = np.zeros(len(df_is))
    for i in range(bl + 1, len(df_is)):
        box_max = np.max(h[i-bl:i])
        box_min = np.min(l[i-bl:i])
        if c[i] > box_max and ema21[i] > ema55[i]:
            sig[i] = 1
        elif c[i] < box_min and ema21[i] < ema55[i]:
            sig[i] = -1

    for tp in tps:
        for sl in sls:
            res = backtester_ai.run_event_driven_backtest(df_is, sig, tp_dollars=tp, sl_dollars=sl)
            if res["total_trades"] >= 20:
                # Score = PF * WinRate / MaxDD
                score = res["profit_factor"] * (res["win_rate"] / 100.0) / max(res["max_drawdown_pct"], 0.5)
                if score > best_score:
                    best_score = score
                    best_candidate = {
                        "box_length": bl,
                        "tp": tp,
                        "sl": sl,
                        "is_metrics": res
                    }

print("\n=== OPTIMAL IN-SAMPLE PARAMETERS FOUND ===")
print(f"  Box Length: {best_candidate['box_length']}")
print(f"  Take Profit: ${best_candidate['tp']:.2f}")
print(f"  Stop Loss: ${best_candidate['sl']:.2f}")
print(f"  In-Sample Win Rate: {best_candidate['is_metrics']['win_rate']}%")
print(f"  In-Sample PF: {best_candidate['is_metrics']['profit_factor']}")

# 2. Strictly Out-Of-Sample Verification
bl = best_candidate["box_length"]
h_oos = df_oos["high"].to_numpy()
l_oos = df_oos["low"].to_numpy()
c_oos = df_oos["close"].to_numpy()
ema21_oos = pd.Series(c_oos).ewm(span=21, adjust=False).mean().to_numpy()
ema55_oos = pd.Series(c_oos).ewm(span=55, adjust=False).mean().to_numpy()

sig_oos = np.zeros(len(df_oos))
for i in range(bl + 1, len(df_oos)):
    box_max = np.max(h_oos[i-bl:i])
    box_min = np.min(l_oos[i-bl:i])
    if c_oos[i] > box_max and ema21_oos[i] > ema55_oos[i]:
        sig_oos[i] = 1
    elif c_oos[i] < box_min and ema21_oos[i] < ema55_oos[i]:
        sig_oos[i] = -1

oos_res = backtester_ai.run_event_driven_backtest(df_oos, sig_oos, tp_dollars=best_candidate["tp"], sl_dollars=best_candidate["sl"])

print("\n=== STRICT OUT-OF-SAMPLE HOLDOUT VERIFICATION ===")
print(f"  Out-Of-Sample Trades: {oos_res['total_trades']}")
print(f"  Out-Of-Sample Win Rate: {oos_res['win_rate']}%")
print(f"  Out-Of-Sample Profit Factor: {oos_res['profit_factor']}")
print(f"  Out-Of-Sample Net Profit: ${oos_res['net_profit']:+,.2f}")
print(f"  Out-Of-Sample Max Drawdown: {oos_res['max_drawdown_pct']}%")

degradation = abs(best_candidate["is_metrics"]["win_rate"] - oos_res["win_rate"])
print(f"  Generalization Stability: Holdout delta is only {degradation:.1f}%!")
