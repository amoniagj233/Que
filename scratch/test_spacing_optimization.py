import pandas as pd
import numpy as np
from backtest_1000_1month import load_data, simulate_strategy

df = load_data()

test_steps = [
    ('Step = $0.60 (Bot 1 Baseline)', {'grid_step': 0.60, 'use_atr_step': False, 'tp_dist': 0.60, 'use_atr_tp': False, 'use_trend_filter': False, 'use_reversal_filter': False}),
    ('Step = $2.00 Fixed', {'grid_step': 2.00, 'use_atr_step': False, 'tp_dist': 1.50, 'use_atr_tp': False, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('Step = $4.00 Fixed (~1x ATR)', {'grid_step': 4.00, 'use_atr_step': False, 'tp_dist': 2.50, 'use_atr_tp': False, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('Step = 1.0x Dynamic ATR', {'use_atr_step': True, 'atr_step_mult': 1.0, 'use_atr_tp': True, 'atr_tp_mult': 0.8, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('Step = 1.5x Dynamic ATR', {'use_atr_step': True, 'atr_step_mult': 1.5, 'use_atr_tp': True, 'atr_tp_mult': 1.0, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('Step = 2.0x Dynamic ATR (Wide Grid)', {'use_atr_step': True, 'atr_step_mult': 2.0, 'use_atr_tp': True, 'atr_tp_mult': 1.2, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('Step = 2.0x ATR + Clamped Lots (0.01-0.02)', {'use_atr_step': True, 'atr_step_mult': 2.0, 'use_atr_tp': True, 'atr_tp_mult': 1.2, 'use_trend_filter': True, 'use_reversal_filter': True, 'lot_mode': 'clamped'}),
]

print("=" * 105)
print(f"{'SPACING CONFIG':<42} | {'FINAL BAL':<10} | {'NET PnL':<9} | {'WIN %':<6} | {'CYCLES':<6} | {'MAX DD':<8} | {'PF':<5} | {'SLs':<4}")
print("-" * 105)
for name, p_override in test_steps:
    params = {
        'base_lot': 0.01,
        'max_layers': 5,
        'lot_mode': 'multiplier',
        'disaster_sl': 100.0,
        'target_usd': 3.50
    }
    params.update(p_override)
    cfg = {'name': name, 'params': params}
    res = simulate_strategy(df, cfg, start_bal=1000.0)
    print(f"{name:<42} | ${res['final_balance']:>9.2f} | ${res['net_profit']:>8.2f} | {res['win_rate']:>5.1f}% | {res['total_cycles']:>6} | ${res['max_drawdown']:>7.2f} | {res['profit_factor']:>5.2f} | {res['disaster_stops']:>4}")
print("=" * 105)
