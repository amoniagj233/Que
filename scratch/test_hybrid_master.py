import pandas as pd
from test_quantum_improvements import load_extended_data, run_quantum_simulation

df = load_extended_data()

hybrids = [
    {
        'name': 'Hybrid 1: Asymmetric + Waterfall Freeze (SL $100)',
        'base_lot': 0.01, 'max_layers': 5, 'disaster_sl': 100.0,
        'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': False,
        'use_waterfall_halt': True, 'use_be_trail': False
    },
    {
        'name': 'Hybrid 2: Asymmetric + Waterfall Freeze (SL $120)',
        'base_lot': 0.01, 'max_layers': 5, 'disaster_sl': 120.0,
        'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': False,
        'use_waterfall_halt': True, 'use_be_trail': False
    },
    {
        'name': 'Hybrid 3: Asymmetric + Waterfall Freeze (SL $150)',
        'base_lot': 0.01, 'max_layers': 5, 'disaster_sl': 150.0,
        'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': False,
        'use_waterfall_halt': True, 'use_be_trail': False
    },
    {
        'name': 'Hybrid 4: Asymmetric + Waterfall + Safe 4-Layers Max',
        'base_lot': 0.01, 'max_layers': 4, 'disaster_sl': 100.0,
        'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': False,
        'use_waterfall_halt': True, 'use_be_trail': False
    }
]

print("=" * 115)
print(f"{'HYBRID SYSTEM':<50} | {'FINAL BAL':<10} | {'NET PnL':<9} | {'ROI %':<7} | {'WIN %':<6} | {'MAX DD ($/%)':<15} | {'PF':<5} | {'SLs':<4}")
print("-" * 115)
for h in hybrids:
    res = run_quantum_simulation(df, h, start_bal=1000.0)
    dd_str = f"${res['max_drawdown']:.0f} ({res['max_dd_pct']:.1f}%)"
    print(f"{res['name']:<50} | ${res['final_balance']:>9.2f} | ${res['net_profit']:>8.2f} | {res['roi_pct']:>6.1f}% | {res['win_rate']:>5.1f}% | {dd_str:>15} | {res['profit_factor']:>5.2f} | {res['disaster_stops']:>4}")
print("=" * 115)
