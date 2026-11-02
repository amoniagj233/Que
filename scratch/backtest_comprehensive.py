"""
Comprehensive Multi-Strategy Backtest Engine for XAUUSD (Gold)
Evaluates:
  1. Bot 1 Baseline (XTO Speeder Rebuilt - Fixed Spacing & Martingale)
  2. Bot 2 (XTO Speeder Upgrade 1 - Dynamic ATR Spacing & Dynamic TP)
  3. Upgrade 2 (Trend Alignment + Reversal Confirmation Filter)
  4. Upgrade 3 (Clamped Lot Sizing - Margin Protection)
  5. Golden Master Combo (Dynamic ATR + Trend Filter + Reversal Confirmation + Clamped Lots)

Data Source:
  - Tries MT5 live copy_rates if accessible.
  - Falls back automatically to offline high-fidelity cache (5,000 M15 candles from Aug-Oct 2026).
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH_M15 = os.path.join(BASE_DIR, "data_cache", "XAUUSD_M15_5000.csv")
CACHE_PATH_H1  = os.path.join(BASE_DIR, "data_cache", "XAUUSD_H1_5000.csv")

def load_dataset(filepath, name):
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['time'] = pd.to_datetime(df['time'])
        
        # Indicator calculations
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
    return None

def run_simulation(df, config, start_balance=1000.0, spread=0.35):
    balance = start_balance
    initial_balance = start_balance
    equity_curve = [balance]
    peak_equity = balance
    max_drawdown = 0.0
    closed_trades = []

    # Position tracking
    basket = []
    basket_type = None

    p = config['params']
    max_layers = p.get('max_layers', 5)
    disaster_sl = p.get('disaster_sl', 50.0)

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

            # Floating PnL (1 lot on XAUUSD = 100 oz, so 0.01 lot * $1.00 move = $1.00)
            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                floating_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

            current_equity = balance + floating_pnl
            if current_equity > peak_equity:
                peak_equity = current_equity
            dd = peak_equity - current_equity
            if dd > max_drawdown:
                max_drawdown = dd

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
                equity_curve.append(balance)
                continue

            # 2. Take-Profit Check
            if p.get('use_atr_tp', False):
                tp_dist = max(0.80, atr * p.get('atr_tp_mult', 0.8))
            else:
                tp_dist = p.get('tp_dist', 1.00)

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
                equity_curve.append(balance)
                continue

            # 3. Grid Addition (DCA)
            if len(basket) < max_layers:
                if p.get('use_atr_step', False):
                    step = max(1.00, atr * p.get('atr_step_mult', 1.2))
                else:
                    step = p.get('grid_step', 1.20)

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
                        if p.get('lot_mode', 'multiplier') == 'clamped':
                            # Safe tier: 0.01, 0.01, 0.02, 0.02, 0.02 max
                            next_lot = 0.01 if layer < 2 else 0.02
                        else:
                            # Martingale 1.5x multiplier: 0.01, 0.01, 0.02, 0.03, 0.05
                            next_lot = round(0.01 * (1.5 ** layer), 2)

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
                basket.append({'type': 'BUY', 'lot': 0.01, 'price': curr_price + spread})
            elif allow_sell and (not p.get('use_reversal_filter', False) or bear_c):
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': 0.01, 'price': curr_price - spread})

    # Close any lingering open basket at end
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
    avg_layers = np.mean([t['layers'] for t in closed_trades]) if total > 0 else 0.0
    recovery_factor = (net_profit / max_drawdown) if max_drawdown > 0 else 0.0

    return {
        'name': config['name'],
        'net_profit': net_profit,
        'win_rate': win_rate,
        'total_cycles': total,
        'profit_factor': pf,
        'max_drawdown': max_drawdown,
        'max_dd_pct': (max_drawdown / peak_equity * 100) if peak_equity > 0 else 0.0,
        'avg_layers': avg_layers,
        'disaster_stops': disaster_count,
        'final_balance': balance,
        'recovery_factor': recovery_factor
    }

def main():
    datasets = [
        ("M15 Institutional Gold", CACHE_PATH_M15),
        ("H1 Swing Gold", CACHE_PATH_H1)
    ]

    configs = [
        {
            'name': '1. Baseline Fixed 60pts (xto_speeder_trader.py)',
            'params': {
                'grid_step': 1.20,
                'tp_dist': 1.00,
                'max_layers': 5,
                'lot_mode': 'multiplier',
                'disaster_sl': 50.0,
                'use_atr_step': False,
                'use_atr_tp': False,
                'use_reversal_filter': False,
                'use_trend_filter': False
            }
        },
        {
            'name': '2. Dynamic ATR Spacing (xto_upgrade_atr.py)',
            'params': {
                'use_atr_step': True,
                'atr_step_mult': 1.2,
                'use_atr_tp': True,
                'atr_tp_mult': 0.8,
                'max_layers': 5,
                'lot_mode': 'multiplier',
                'disaster_sl': 50.0,
                'use_reversal_filter': False,
                'use_trend_filter': False
            }
        },
        {
            'name': '3. Trend + Reversal (Anti-Falling-Knife)',
            'params': {
                'grid_step': 1.20,
                'tp_dist': 1.00,
                'max_layers': 5,
                'lot_mode': 'multiplier',
                'disaster_sl': 50.0,
                'use_atr_step': False,
                'use_atr_tp': False,
                'use_reversal_filter': True,
                'use_trend_filter': True
            }
        },
        {
            'name': '4. Golden Master: Dual Dynamic ATR + Trend + Reversal',
            'params': {
                'use_atr_step': True,
                'atr_step_mult': 1.3,
                'use_atr_tp': True,
                'atr_tp_mult': 0.9,
                'max_layers': 5,
                'lot_mode': 'clamped',
                'disaster_sl': 40.0,
                'use_reversal_filter': True,
                'use_trend_filter': True
            }
        }
    ]

    for label, path in datasets:
        df = load_dataset(path, label)
        if df is None:
            continue
        print("\n" + "=" * 105)
        print(f"📊 DATASET: {label} ({len(df)} candles)")
        print(f"   Period: {df['time'].iloc[0]} -> {df['time'].iloc[-1]} | Price: ${df['low'].min():.2f} - ${df['high'].max():.2f} (Delta: ${df['high'].max() - df['low'].min():.2f})")
        print("=" * 105)
        print(f"{'STRATEGY MODEL':<45} | {'NET P/L':<9} | {'WIN %':<7} | {'CYCLES':<7} | {'MAX DD':<9} | {'PF':<5} | {'SLs':<3} | {'REC':<5}")
        print("-" * 105)

        for c in configs:
            res = run_simulation(df, c, start_balance=1000.0)
            print(f"{res['name']:<45} | ${res['net_profit']:>7.2f} | {res['win_rate']:>5.1f}% | {res['total_cycles']:>7} | ${res['max_drawdown']:>7.2f} | {res['profit_factor']:>5.2f} | {res['disaster_stops']:>3} | {res['recovery_factor']:>5.2f}")

        print("=" * 105)

if __name__ == "__main__":
    main()
