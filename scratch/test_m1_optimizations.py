"""
M1 Gold Grid Stress Test & Optimization
Tests:
1. Strict session filtering (London / NY overlap only vs 24/7)
2. ATR scaling relative to higher timeframe (M15 ATR reference)
3. Micro TP scalp with minimal layers (Max 3-4 layers)
4. Dynamic trend regime lock (RSI extreme + EMA cross)
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_opt():
    mt5.initialize()
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 43200)
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df['hour'] = df['datetime'].dt.hour
    
    # ATR
    tr = pd.concat([df['high']-df['low'], (df['high']-df['close'].shift(1)).abs(), (df['low']-df['close'].shift(1)).abs()], axis=1).max(axis=1)
    df['atr_m1'] = tr.rolling(14).mean().bfill()
    df['atr_slow'] = tr.rolling(150).mean().bfill() # Approx M15 ATR proxy
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['vel5'] = (df['close'] - df['close'].shift(5)).fillna(0.0)

    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = (100 - (100 / (1 + rs))).bfill()

    strategies = [
        # Scalp with M15-proportioned spacing (Step = $3.50+, TP = $1.80, Max 4 layers)
        {"name": "M1 Wide Micro-Grid ($3.50 step, $2.00 TP, Max 4)", "step": 3.5, "tp": 2.0, "max_layers": 4, "hours": range(24), "sl": 120},
        {"name": "M1 Wide Micro-Grid ($4.50 step, $2.50 TP, Max 4)", "step": 4.5, "tp": 2.5, "max_layers": 4, "hours": range(24), "sl": 120},
        # Session Filtered (07:00 - 19:00 UTC only)
        {"name": "M1 Active Sessions ($3.50 step, 07:00-19:00 UTC)", "step": 3.5, "tp": 2.0, "max_layers": 4, "hours": range(7, 19), "sl": 120},
        {"name": "M1 Active Sessions ($4.50 step, 07:00-19:00 UTC)", "step": 4.5, "tp": 2.5, "max_layers": 4, "hours": range(7, 19), "sl": 120},
        # Trend Lock (Only trade in direction of EMA50 > EMA200)
        {"name": "M1 Trend-Locked ($4.00 step, EMA200 align)", "step": 4.0, "tp": 2.2, "max_layers": 4, "hours": range(7, 21), "sl": 120, "trend_lock": True},
        # Range Bound RSI Reversion (Only enter initial when RSI < 30 or > 70)
        {"name": "M1 RSI Extreme Entry ($3.50 step, RSI < 28 / > 72)", "step": 3.5, "tp": 2.0, "max_layers": 4, "hours": range(24), "sl": 120, "rsi_gate": True}
    ]

    print("=" * 85)
    print("M1 OPTIMIZED GRID SIMULATION (43,200 Candles)")
    print("=" * 85)

    for st in strategies:
        balance = 1000.0
        peak = 1000.0
        max_dd = 0.0
        wins = 0
        losses = 0
        basket = []
        b_type = None

        for i in range(200, len(df)):
            row = df.iloc[i]
            c = row['close']
            atr = max(1.2, row['atr_m1'])
            hour = row['hour']

            if len(basket) > 0:
                tot_lots = sum(x['lot'] for x in basket)
                vwap = sum(x['price'] * x['lot'] for x in basket) / tot_lots
                pnl = sum((c - x['price']) * x['lot'] * 100 for x in basket) if b_type == 'BUY' else sum((x['price'] - c) * x['lot'] * 100 for x in basket)

                eq = balance + pnl
                if eq > peak: peak = eq
                dd = peak - eq
                if dd > max_dd: max_dd = dd

                if pnl <= -st['sl']:
                    balance += pnl
                    losses += 1
                    basket = []
                    b_type = None
                    continue

                if (c >= vwap + st['tp'] if b_type == 'BUY' else c <= vwap - st['tp']) or pnl >= 3.0:
                    balance += pnl
                    wins += 1
                    basket = []
                    b_type = None
                    continue

                if len(basket) < st['max_layers']:
                    worst = min(x['price'] for x in basket) if b_type == 'BUY' else max(x['price'] for x in basket)
                    dist = (worst - c) if b_type == 'BUY' else (c - worst)
                    if dist >= st['step']:
                        # Velocity freeze
                        if b_type == 'BUY' and row['vel5'] < -(2.5 * atr): pass
                        elif b_type == 'SELL' and row['vel5'] > (2.5 * atr): pass
                        else:
                            lot = 0.01 if len(basket) < 2 else 0.02
                            basket.append({'price': c, 'lot': lot})
            else:
                if hour not in st['hours']:
                    continue
                
                # Check initial entry condition
                go_buy = False
                go_sell = False

                if st.get('rsi_gate'):
                    if row['rsi'] <= 28: go_buy = True
                    elif row['rsi'] >= 72: go_sell = True
                elif st.get('trend_lock'):
                    if row['ema50'] > row['ema200'] and row['close'] > row['open']: go_buy = True
                    elif row['ema50'] < row['ema200'] and row['close'] < row['open']: go_sell = True
                else:
                    if row['close'] > row['open']: go_buy = True
                    else: go_sell = True

                if go_buy:
                    b_type = 'BUY'
                    basket = [{'price': c, 'lot': 0.01}]
                elif go_sell:
                    b_type = 'SELL'
                    basket = [{'price': c, 'lot': 0.01}]

        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        net = balance - 1000.0
        roi = (net / 1000.0) * 100
        dd_pct = (max_dd / peak * 100) if peak > 0 else 100
        print(f"{st['name']:<48} | Net: ${net:>+8.2f} ({roi:>+6.1f}%) | Win: {win_rate:>5.1f}% | DD: ${max_dd:>6.2f} ({dd_pct:>4.1f}%) | Wins: {wins} | SL: {losses}")

if __name__ == "__main__":
    run_opt()
