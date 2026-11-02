"""
Quantum Optimization Lab: Systematic Improvement for XAUUSD (Gold)
Dataset: 8,640 M5 bars (Sep 16 - Oct 29, 2026)
Capital: $1,000.00

Systematic Tests:
  Test A: Baseline 2.2x ATR
  Test B: + Multi-Timeframe Trend Gate (H1 EMA 50 Macro Filter)
  Test C: + Asymmetric Grid Spacing (Geometric expansion: 1.8x -> 2.5x -> 3.5x)
  Test D: + Trailing Breakeven & Dynamic Run Trailing
  Test E: + Volatility Waterfall Halt (Pause DCA until Reversal Bar Confirmed)
  Test F: Master Quantum Engine (All synergies combined)
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache", "XAUUSD_M5_1MONTH.csv")

def load_extended_data():
    df = pd.read_csv(DATA_PATH)
    df['time'] = pd.to_datetime(df['time'])

    # True Range & ATR(14)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean().bfill()

    # RSI(14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = (100 - (100 / (1 + rs))).bfill()

    # M5 EMAs
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

    # Macro H1 Proxy: 12 bars of M5 = 1 hour, so H1 EMA 50 ~= M5 EMA 600
    df['h1_macro_trend'] = df['close'].ewm(span=600, adjust=False).mean()

    # Candlestick characteristics
    df['body'] = (df['close'] - df['open']).abs()
    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']
    df['hammer'] = (df['bullish']) & ((df['open'] - df['low']) > 2 * df['body'])
    df['shooting_star'] = (df['bearish']) & ((df['high'] - df['open']) > 2 * df['body'])

    # 3-bar momentum velocity ($ price change over last 3 bars)
    df['velocity_3bar'] = df['close'] - df['close'].shift(3)

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def run_quantum_simulation(df, params, start_bal=1000.0, spread=0.35):
    balance = start_bal
    initial_balance = start_bal
    peak_equity = start_bal
    max_dd = 0.0
    closed_trades = []

    basket = []
    basket_type = None

    # Params
    base_lot = params.get('base_lot', 0.01)
    max_layers = params.get('max_layers', 5)
    disaster_sl = params.get('disaster_sl', 120.0)
    spacing_type = params.get('spacing_type', 'linear_atr') # 'linear_atr' or 'asymmetric'
    atr_mult = params.get('atr_mult', 2.0)
    use_h1_filter = params.get('use_h1_filter', False)
    use_waterfall_halt = params.get('use_waterfall_halt', False)
    use_be_trail = params.get('use_be_trail', False)
    lot_mode = params.get('lot_mode', 'clamped')

    for i in range(60, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr']
        rsi = row['rsi']
        vel3 = row['velocity_3bar']
        bull_c = row['bullish']
        bear_c = row['bearish']
        trend_m5 = 1 if row['ema21'] > row['ema55'] else -1
        macro_h1 = 1 if curr_price > row['h1_macro_trend'] else -1

        # Check existing basket
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots

            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                floating_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

            current_equity = balance + floating_pnl
            if current_equity > peak_equity:
                peak_equity = current_equity
            dd = peak_equity - current_equity
            if dd > max_dd:
                max_dd = dd

            # 1. Hard Disaster Stop-Loss Check
            if disaster_sl > 0 and floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({
                    'pnl': floating_pnl, 'layers': len(basket), 'reason': 'Disaster_SL', 'time': row['time']
                })
                basket = []
                basket_type = None
                continue

            # 2. Dynamic Trailing Breakeven / GroupTP Check
            tp_dist = max(1.50, atr * params.get('tp_atr_mult', 1.2))
            tp_hit = False
            realized_pnl = 0.0

            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                # Breakeven lock: If price reached +$6 or 1x ATR profit, lock in at least +$1.00
                if use_be_trail and floating_pnl >= 6.0:
                    be_price = vwap + 0.30
                    if curr_price < be_price:
                        # Exit at breakeven lock
                        tp_hit = True
                        realized_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)

                if high >= target_tp or floating_pnl >= params.get('target_usd', 4.00):
                    tp_hit = True
                    realized_pnl = sum((target_tp - x['price']) * x['lot'] * 100 for x in basket)
            else:
                target_tp = vwap - tp_dist
                if use_be_trail and floating_pnl >= 6.0:
                    be_price = vwap - 0.30
                    if curr_price > be_price:
                        tp_hit = True
                        realized_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

                if low <= target_tp or floating_pnl >= params.get('target_usd', 4.00):
                    tp_hit = True
                    realized_pnl = sum((x['price'] - target_tp) * x['lot'] * 100 for x in basket)

            if tp_hit:
                balance += realized_pnl
                closed_trades.append({
                    'pnl': realized_pnl, 'layers': len(basket), 'reason': 'GroupTP', 'time': row['time']
                })
                basket = []
                basket_type = None
                continue

            # 3. Dynamic Grid Addition (DCA)
            if len(basket) < max_layers:
                layer = len(basket)
                # Spacing calculation: Linear vs Asymmetric Expansion
                if spacing_type == 'asymmetric':
                    # Multipliers: L1->L2 = 1.8x ATR, L2->L3 = 2.4x ATR, L3->L4 = 3.2x ATR
                    exp_factors = [1.8, 2.4, 3.2, 4.2]
                    mult = exp_factors[min(layer - 1, len(exp_factors) - 1)]
                    step = max(3.00, atr * mult)
                else:
                    step = max(2.50, atr * atr_mult)

                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)

                if dist_ok:
                    confirm_ok = True
                    # Waterfall Protection: If price dropped > 2x ATR in last 3 bars, DO NOT ADD until a green reversal candle forms!
                    if use_waterfall_halt:
                        if basket_type == 'BUY':
                            is_waterfall = vel3 < -(2.0 * atr)
                            if is_waterfall:
                                confirm_ok = bull_c or row['hammer'] or rsi < 28
                            else:
                                confirm_ok = bull_c or (rsi < 35)
                        else:
                            is_waterfall = vel3 > (2.0 * atr)
                            if is_waterfall:
                                confirm_ok = bear_c or row['shooting_star'] or rsi > 72
                            else:
                                confirm_ok = bear_c or (rsi > 65)

                    if confirm_ok:
                        # Lot sizing
                        if lot_mode == 'clamped':
                            # 0.01 -> 0.01 -> 0.02 -> 0.02 -> 0.02 max
                            next_lot = 0.01 if layer < 2 else 0.02
                        elif lot_mode == 'linear':
                            next_lot = 0.01
                        else:
                            next_lot = round(base_lot * (1.5 ** layer), 2)

                        fill_p = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})

        else:
            # Basket empty: evaluate entry
            allow_buy = True
            allow_sell = True

            # M5 Trend
            if trend_m5 > 0:
                allow_sell = False
            elif trend_m5 < 0:
                allow_buy = False

            # Macro H1 Filter: Only buy if above H1 EMA, only sell if below H1 EMA
            if use_h1_filter:
                if macro_h1 > 0:
                    allow_sell = False
                elif macro_h1 < 0:
                    allow_buy = False

            # Entry Trigger
            if allow_buy and (bull_c or rsi < 32):
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and (bear_c or rsi > 68):
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': base_lot, 'price': curr_price - spread})

    # Close any open basket at end
    if len(basket) > 0:
        last_price = df.iloc[-1]['close']
        if basket_type == 'BUY':
            final_pnl = sum((last_price - x['price']) * x['lot'] * 100 for x in basket)
        else:
            final_pnl = sum((x['price'] - last_price) * x['lot'] * 100 for x in basket)
        balance += final_pnl
        closed_trades.append({'pnl': final_pnl, 'layers': len(basket), 'reason': 'EndSession', 'time': df.iloc[-1]['time']})

    # Metrics
    total = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    disaster_count = len([t for t in closed_trades if t['reason'] == 'Disaster_SL'])
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0
    max_dd_pct = (max_dd / peak_equity * 100) if peak_equity > 0 else 0.0
    recovery_factor = (net_profit / max_dd) if max_dd > 0 else 0.0

    return {
        'name': params.get('name', 'Strategy'),
        'final_balance': balance,
        'net_profit': net_profit,
        'roi_pct': (net_profit / initial_balance * 100),
        'win_rate': win_rate,
        'total_cycles': total,
        'profit_factor': pf,
        'max_drawdown': max_dd,
        'max_dd_pct': max_dd_pct,
        'disaster_stops': disaster_count,
        'recovery_factor': recovery_factor
    }

def main():
    df = load_extended_data()
    print("=" * 120)
    print("🔬 QUANTUM OPTIMIZATION LAB: $1,000 GOLD CAPITAL (8,640 M5 CANDLES)")
    print("=" * 120)

    experiments = [
        {
            'name': '1. Baseline 2.2x ATR Linear',
            'base_lot': 0.01, 'max_layers': 5, 'atr_mult': 2.2, 'disaster_sl': 100.0,
            'lot_mode': 'clamped', 'spacing_type': 'linear_atr', 'use_h1_filter': False,
            'use_waterfall_halt': False, 'use_be_trail': False
        },
        {
            'name': '2. + H1 Macro Trend Gate (No Counter-Trend)',
            'base_lot': 0.01, 'max_layers': 5, 'atr_mult': 2.2, 'disaster_sl': 100.0,
            'lot_mode': 'clamped', 'spacing_type': 'linear_atr', 'use_h1_filter': True,
            'use_waterfall_halt': False, 'use_be_trail': False
        },
        {
            'name': '3. + Asymmetric Geometry (1.8x -> 2.4x -> 3.2x ATR)',
            'base_lot': 0.01, 'max_layers': 5, 'disaster_sl': 100.0,
            'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': False,
            'use_waterfall_halt': False, 'use_be_trail': False
        },
        {
            'name': '4. + Waterfall Dump Freeze (Anti-Liquidation)',
            'base_lot': 0.01, 'max_layers': 5, 'atr_mult': 2.2, 'disaster_sl': 100.0,
            'lot_mode': 'clamped', 'spacing_type': 'linear_atr', 'use_h1_filter': False,
            'use_waterfall_halt': True, 'use_be_trail': False
        },
        {
            'name': '5. + Breakeven Lock & Trail',
            'base_lot': 0.01, 'max_layers': 5, 'atr_mult': 2.2, 'disaster_sl': 100.0,
            'lot_mode': 'clamped', 'spacing_type': 'linear_atr', 'use_h1_filter': False,
            'use_waterfall_halt': False, 'use_be_trail': True
        },
        {
            'name': '6. Quantum Apex Master (All 4 Modules Combined)',
            'base_lot': 0.01, 'max_layers': 5, 'disaster_sl': 120.0,
            'lot_mode': 'clamped', 'spacing_type': 'asymmetric', 'use_h1_filter': True,
            'use_waterfall_halt': True, 'use_be_trail': True, 'tp_atr_mult': 1.3, 'target_usd': 5.0
        },
        {
            'name': '7. Quantum Apex Conservative (Max DD < 15%)',
            'base_lot': 0.01, 'max_layers': 4, 'disaster_sl': 80.0,
            'lot_mode': 'linear', 'spacing_type': 'asymmetric', 'use_h1_filter': True,
            'use_waterfall_halt': True, 'use_be_trail': True, 'tp_atr_mult': 1.2, 'target_usd': 4.0
        }
    ]

    print(f"{'SYSTEM MODEL':<48} | {'FINAL BAL':<10} | {'NET PnL':<9} | {'ROI %':<7} | {'WIN %':<6} | {'MAX DD ($/%)':<15} | {'PF':<5} | {'SLs':<4} | {'REC':<5}")
    print("-" * 120)

    for exp in experiments:
        res = run_quantum_simulation(df, exp, start_bal=1000.0)
        dd_str = f"${res['max_drawdown']:.0f} ({res['max_dd_pct']:.1f}%)"
        print(f"{res['name']:<48} | ${res['final_balance']:>9.2f} | ${res['net_profit']:>8.2f} | {res['roi_pct']:>6.1f}% | {res['win_rate']:>5.1f}% | {dd_str:>15} | {res['profit_factor']:>5.2f} | {res['disaster_stops']:>4} | {res['recovery_factor']:>5.2f}")

    print("=" * 120)

if __name__ == "__main__":
    main()
