import pandas as pd
from backtest_1000_1month import load_data, simulate_strategy

df = load_data()

variations = [
    ('2.0x ATR | Clamped | SL $100', {'use_atr_step': True, 'atr_step_mult': 2.0, 'use_atr_tp': True, 'atr_tp_mult': 1.2, 'lot_mode': 'clamped', 'disaster_sl': 100.0, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('2.0x ATR | Clamped | SL $150', {'use_atr_step': True, 'atr_step_mult': 2.0, 'use_atr_tp': True, 'atr_tp_mult': 1.2, 'lot_mode': 'clamped', 'disaster_sl': 150.0, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('2.2x ATR | Clamped | SL $100', {'use_atr_step': True, 'atr_step_mult': 2.2, 'use_atr_tp': True, 'atr_tp_mult': 1.3, 'lot_mode': 'clamped', 'disaster_sl': 100.0, 'use_trend_filter': True, 'use_reversal_filter': True}),
    ('2.0x ATR | Linear 0.01 (No Grid Sizing) | SL $80', {'use_atr_step': True, 'atr_step_mult': 2.0, 'use_atr_tp': True, 'atr_tp_mult': 1.2, 'lot_mode': 'linear', 'disaster_sl': 80.0, 'use_trend_filter': True, 'use_reversal_filter': True}),
]

print("=" * 110)
print(f"{'STRATEGY VARIANT':<45} | {'FINAL BAL':<10} | {'NET PnL':<9} | {'ROI %':<7} | {'WIN %':<6} | {'MAX DD':<8} | {'PF':<5} | {'SLs':<4}")
print("-" * 110)
for name, p_override in variations:
    params = {
        'base_lot': 0.01,
        'max_layers': 5,
        'target_usd': 3.50
    }
    params.update(p_override)
    cfg = {'name': name, 'params': params}
    res = simulate_strategy(df, cfg, start_bal=1000.0)
    print(f"{name:<45} | ${res['final_balance']:>9.2f} | ${res['net_profit']:>8.2f} | {res['roi_pct']:>6.1f}% | {res['win_rate']:>5.1f}% | ${res['max_drawdown']:>7.2f} | {res['profit_factor']:>5.2f} | {res['disaster_stops']:>4}")
print("=" * 110)
