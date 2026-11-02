"""
Comprehensive Timeframe Backtest on Gold (XAUUSD)
Tests Dual (BUY & SELL) Dynamic ATR XTO Speeder across:
  - M1  (1 Minute)
  - M5  (5 Minutes)
  - M15 (15 Minutes)
  - M30 (30 Minutes)
  - H1  (1 Hour)
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

symbol = "XAUUSD"

timeframes = [
    ('M1', mt5.TIMEFRAME_M1, 6000),   # ~4.5 days
    ('M5', mt5.TIMEFRAME_M5, 3000),   # ~10 days
    ('M15', mt5.TIMEFRAME_M15, 2000), # ~21 days
    ('M30', mt5.TIMEFRAME_M30, 1500), # ~31 days
    ('H1', mt5.TIMEFRAME_H1, 1000)    # ~42 days
]

def run_tf_simulation(tf_name, tf_const, bars_count):
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, bars_count)
    if rates is None or len(rates) < 100:
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    # Indicators
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()

    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    df['trend'] = np.where(df['ema21'] >= df['ema55'], 1, -1) # 1 = BUY, -1 = SELL

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    balance = 1000.0
    initial_balance = balance
    max_equity = balance
    max_drawdown = 0.0
    closed_trades = []
    
    basket = []
    basket_type = None
    spread = 0.35 # $0.35 on gold
    max_layers = 5
    disaster_sl = 50.0

    for i in range(50, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr']
        trend = row['trend']

        dynamic_step = max(0.80, atr * 1.5)
        dynamic_tp   = max(0.60, atr * 1.0)

        if len(basket) > 0:
            total_lots = sum(p['lot'] for p in basket)
            vwap = sum(p['price'] * p['lot'] for p in basket) / total_lots

            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - p['price']) * p['lot'] * 100 for p in basket)
            else:
                floating_pnl = sum((p['price'] - curr_price) * p['lot'] * 100 for p in basket)

            equity = balance + floating_pnl
            if equity > max_equity:
                max_equity = equity
            dd = max_equity - equity
            if dd > max_drawdown:
                max_drawdown = dd

            # Disaster SL
            if floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'layers': len(basket), 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue

            # GroupTP Check
            tp_hit = False
            if basket_type == 'BUY':
                target_tp = vwap + dynamic_tp
                if high >= target_tp or floating_pnl >= 2.50:
                    tp_hit = True
                    pnl = sum((target_tp - p['price']) * p['lot'] * 100 for p in basket)
            else:
                target_tp = vwap - dynamic_tp
                if low <= target_tp or floating_pnl >= 2.50:
                    tp_hit = True
                    pnl = sum((p['price'] - target_tp) * p['lot'] * 100 for p in basket)

            if tp_hit:
                balance += pnl
                closed_trades.append({'pnl': pnl, 'layers': len(basket), 'reason': 'GroupTP'})
                basket = []
                basket_type = None
                continue

            # DCA Grid Addition
            if len(basket) < max_layers:
                worst_price = min(p['price'] for p in basket) if basket_type == 'BUY' else max(p['price'] for p in basket)
                dist_ok = (worst_price - curr_price >= dynamic_step) if basket_type == 'BUY' else (curr_price - worst_price >= dynamic_step)
                if dist_ok:
                    layer = len(basket)
                    next_lot = round(0.01 * (1.5 ** layer), 2)
                    basket.append({'type': basket_type, 'lot': next_lot, 'price': curr_price})
        else:
            # Open new basket following trend bias
            if trend > 0:
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': 0.01, 'price': curr_price + spread})
            elif trend < 0:
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': 0.01, 'price': curr_price - spread})

    total_cycles = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total_cycles * 100) if total_cycles > 0 else 0.0
    avg_layers = np.mean([t['layers'] for t in closed_trades]) if closed_trades else 0
    profit_factor = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))) if losses and sum(t['pnl'] for t in losses) != 0 else 999.0
    calmar = (net_profit / max_drawdown) if max_drawdown > 0 else 0.0

    return {
        'tf': tf_name,
        'bars': len(df),
        'date_from': df['time'].iloc[0].strftime('%Y-%m-%d'),
        'date_to': df['time'].iloc[-1].strftime('%Y-%m-%d'),
        'net_profit': net_profit,
        'win_rate': win_rate,
        'total_cycles': total_cycles,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'avg_layers': avg_layers,
        'disaster_stops': len(losses),
        'calmar': calmar
    }

print("\n" + "=" * 88)
print(f"  🏁 MULTI-TIMEFRAME BACKTEST: XAUUSD (DUAL BUY & SELL DYNAMIC ATR GRID)")
print("=" * 88)
print(f"{'TF':<5} | {'PERIOD COVERED':<23} | {'NET PROFIT':<11} | {'WIN %':<7} | {'CYCLES':<7} | {'MAX DD':<9} | {'PF':<5} | {'RETURN/DD':<9}")
print("-" * 88)

results = []
for tf_name, tf_const, count in timeframes:
    res = run_tf_simulation(tf_name, tf_const, count)
    if res:
        results.append(res)
        print(f"{res['tf']:<5} | {res['date_from']} to {res['date_to']:<10} | ${res['net_profit']:>9.2f} | {res['win_rate']:>5.1f}% | {res['total_cycles']:>7} | ${res['max_drawdown']:>7.2f} | {res['profit_factor']:>5.2f} | {res['calmar']:>8.2f}x")

print("=" * 88)

# Sort by Return / Drawdown and Net Profit
results_sorted = sorted(results, key=lambda x: x['calmar'], reverse=True)
print(f"\n🏆 OVERALL WINNER (Best Risk-Adjusted Return): {results_sorted[0]['tf']}")
print(f"💰 PROFIT KING (Highest Raw Dollars): {max(results, key=lambda x: x['net_profit'])['tf']}")
print(f"🛡️ SAFETY KING (Lowest Drawdown): {min(results, key=lambda x: x['max_drawdown'])['tf']}")

mt5.shutdown()
