"""
$1000 Capital - 1-Month M5 High-Fidelity Backtest Engine (XAUUSD Gold)
Dataset: 8,640 M5 bars (Sep 16, 2026 - Oct 29, 2026)

Tests 5 Risk Profiles tailored for $1,000 Capital:
  1. Baseline Fixed DCA (Bot 1 default settings scaled to $1,000)
  2. Dynamic ATR Spacing (Bot 2 volatility grid)
  3. Golden Master (ATR Spacing + Trend Bias + Reversal Confirmation)
  4. Pro Growth (Base 0.02 lots + Dynamic ATR + Clamped sizing)
  5. Ultra-Safe Linear (Base 0.01 lots, No Martingale, Max DD Protection)
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache", "XAUUSD_M5_1MONTH.csv")

def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found")
        sys.exit(1)
    df = pd.read_csv(DATA_PATH)
    df['time'] = pd.to_datetime(df['time'])

    # Indicators
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean().bfill()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = (100 - (100 / (1 + rs))).bfill()

    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

    df['bullish_candle'] = df['close'] > df['open']
    df['bearish_candle'] = df['close'] < df['open']

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def simulate_strategy(df, cfg, start_bal=1000.0, spread=0.35):
    balance = start_bal
    initial_balance = start_bal
    peak_equity = start_bal
    max_dd_dollars = 0.0
    closed_trades = []

    basket = []
    basket_type = None

    p = cfg['params']
    base_lot = p.get('base_lot', 0.01)
    max_layers = p.get('max_layers', 5)
    disaster_sl = p.get('disaster_sl', 100.0)

    for i in range(55, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr']
        rsi = row['rsi']
        bull_c = row['bullish_candle']
        bear_c = row['bearish_candle']
        trend = 1 if row['ema21'] > row['ema55'] else -1

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
            if dd > max_dd_dollars:
                max_dd_dollars = dd

            # 1. Disaster Stop-Loss Check
            if disaster_sl > 0 and floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({
                    'pnl': floating_pnl,
                    'layers': len(basket),
                    'reason': 'Disaster_SL',
                    'time': row['time']
                })
                basket = []
                basket_type = None
                continue

            # 2. Take-Profit Check
            if p.get('use_atr_tp', False):
                tp_dist = max(0.80, atr * p.get('atr_tp_mult', 1.0))
            else:
                tp_dist = p.get('tp_dist', 0.80)

            tp_hit = False
            realized_pnl = 0.0

            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                if high >= target_tp or floating_pnl >= p.get('target_usd', 3.00):
                    tp_hit = True
                    realized_pnl = sum((target_tp - x['price']) * x['lot'] * 100 for x in basket)
            else:
                target_tp = vwap - tp_dist
                if low <= target_tp or floating_pnl >= p.get('target_usd', 3.00):
                    tp_hit = True
                    realized_pnl = sum((x['price'] - target_tp) * x['lot'] * 100 for x in basket)

            if tp_hit:
                balance += realized_pnl
                closed_trades.append({
                    'pnl': realized_pnl,
                    'layers': len(basket),
                    'reason': 'GroupTP',
                    'time': row['time']
                })
                basket = []
                basket_type = None
                continue

            # 3. Grid Addition (DCA)
            if len(basket) < max_layers:
                if p.get('use_atr_step', False):
                    step = max(1.00, atr * p.get('atr_step_mult', 1.3))
                else:
                    step = p.get('grid_step', 0.80)

                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)

                if dist_ok:
                    confirm_ok = True
                    if p.get('use_reversal_filter', False):
                        if basket_type == 'BUY':
                            confirm_ok = bull_c or (rsi < 35 and row['close'] > row['open'])
                        else:
                            confirm_ok = bear_c or (rsi > 65 and row['close'] < row['open'])

                    if confirm_ok:
                        layer = len(basket)
                        lot_mode = p.get('lot_mode', 'multiplier')
                        if lot_mode == 'linear':
                            next_lot = base_lot
                        elif lot_mode == 'clamped':
                            # e.g. 0.01, 0.01, 0.02, 0.02, 0.02 or 0.02, 0.02, 0.03, 0.04
                            if base_lot == 0.01:
                                next_lot = 0.01 if layer < 2 else 0.02
                            else:
                                next_lot = 0.02 if layer < 2 else (0.03 if layer == 2 else 0.04)
                        else:
                            # 1.5x Martingale multiplier
                            next_lot = round(base_lot * (1.5 ** layer), 2)

                        fill_price = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_price})

        else:
            # Basket empty: evaluate entry
            allow_buy = True
            allow_sell = True
            if p.get('use_trend_filter', False):
                if trend > 0:
                    allow_sell = False
                elif trend < 0:
                    allow_buy = False

            if allow_buy and (not p.get('use_reversal_filter', False) or bull_c):
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and (not p.get('use_reversal_filter', False) or bear_c):
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

    # Stats
    total = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    disaster_count = len([t for t in closed_trades if t['reason'] == 'Disaster_SL'])
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0
    max_dd_pct = (max_dd_dollars / peak_equity * 100) if peak_equity > 0 else 0.0
    recovery_factor = (net_profit / max_dd_dollars) if max_dd_dollars > 0 else 0.0

    return {
        'name': cfg['name'],
        'starting_capital': initial_balance,
        'final_balance': balance,
        'net_profit': net_profit,
        'roi_pct': (net_profit / initial_balance * 100),
        'win_rate': win_rate,
        'total_cycles': total,
        'profit_factor': pf,
        'max_drawdown': max_dd_dollars,
        'max_dd_pct': max_dd_pct,
        'disaster_stops': disaster_count,
        'recovery_factor': recovery_factor
    }

def main():
    df = load_data()
    print("=" * 115)
    print(f"📊 1-MONTH XAUUSD M5 BACKTEST: $1,000 CAPITAL SIMULATION")
    print(f"   Period : {df['time'].iloc[0]} -> {df['time'].iloc[-1]} ({len(df)} M5 Candles / ~43 Days)")
    print(f"   Price  : Low ${df['low'].min():.2f} -> High ${df['high'].max():.2f} (Swing Range: ${df['high'].max() - df['low'].min():.2f})")
    print("=" * 115)

    configs = [
        {
            'name': '1. Baseline Fixed 60pts (Bot 1 Default)',
            'params': {
                'base_lot': 0.01,
                'grid_step': 0.60,
                'tp_dist': 0.60,
                'target_usd': 2.50,
                'max_layers': 5,
                'lot_mode': 'multiplier',
                'disaster_sl': 100.0,
                'use_atr_step': False,
                'use_atr_tp': False,
                'use_reversal_filter': False,
                'use_trend_filter': False
            }
        },
        {
            'name': '2. Dynamic ATR Spacing (Bot 2 Default)',
            'params': {
                'base_lot': 0.01,
                'use_atr_step': True,
                'atr_step_mult': 1.3,
                'use_atr_tp': True,
                'atr_tp_mult': 0.9,
                'target_usd': 3.00,
                'max_layers': 5,
                'lot_mode': 'multiplier',
                'disaster_sl': 100.0,
                'use_reversal_filter': False,
                'use_trend_filter': False
            }
        },
        {
            'name': '3. Golden Master (ATR + Trend + Reversal)',
            'params': {
                'base_lot': 0.01,
                'use_atr_step': True,
                'atr_step_mult': 1.4,
                'use_atr_tp': True,
                'atr_tp_mult': 1.0,
                'target_usd': 3.50,
                'max_layers': 5,
                'lot_mode': 'clamped',
                'disaster_sl': 80.0,
                'use_reversal_filter': True,
                'use_trend_filter': True
            }
        },
        {
            'name': '4. Pro Growth $1000 (Base 0.02 + Clamped)',
            'params': {
                'base_lot': 0.02,
                'use_atr_step': True,
                'atr_step_mult': 1.4,
                'use_atr_tp': True,
                'atr_tp_mult': 1.0,
                'target_usd': 6.00,
                'max_layers': 4,
                'lot_mode': 'clamped',
                'disaster_sl': 120.0,
                'use_reversal_filter': True,
                'use_trend_filter': True
            }
        },
        {
            'name': '5. Ultra-Safe Linear (Fixed 0.01, No Martingale)',
            'params': {
                'base_lot': 0.01,
                'use_atr_step': True,
                'atr_step_mult': 1.5,
                'use_atr_tp': True,
                'atr_tp_mult': 1.0,
                'target_usd': 2.50,
                'max_layers': 4,
                'lot_mode': 'linear',
                'disaster_sl': 50.0,
                'use_reversal_filter': True,
                'use_trend_filter': True
            }
        }
    ]

    print(f"{'MODEL / STRATEGY':<44} | {'FINAL BAL':<10} | {'NET P/L':<9} | {'ROI %':<7} | {'WIN %':<6} | {'CYCLES':<6} | {'MAX DD ($/%)':<14} | {'PF':<5} | {'REC':<5}")
    print("-" * 115)

    for c in configs:
        res = simulate_strategy(df, c, start_bal=1000.0)
        dd_str = f"${res['max_drawdown']:.0f} ({res['max_dd_pct']:.1f}%)"
        print(f"{res['name']:<44} | ${res['final_balance']:>9.2f} | ${res['net_profit']:>8.2f} | {res['roi_pct']:>6.1f}% | {res['win_rate']:>5.1f}% | {res['total_cycles']:>6} | {dd_str:>14} | {res['profit_factor']:>5.2f} | {res['recovery_factor']:>5.2f}")

    print("=" * 115)

if __name__ == "__main__":
    main()
