"""
High-Speed Backtest: Pure Grid vs ATR-Dynamic Adaptive Grid on XAUUSD M1
Evaluates 43,200 M1 candles (~1.5 months) for $1,000 initial capital.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_m1_grid_backtest():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return

    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 43200)
    if rates is None or len(rates) == 0:
        print("No rates fetched")
        return

    df = pd.DataFrame(rates)
    # Calculate ATR 14 on M1
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(14).mean().bfill()
    df['vel3'] = (df['close'] - df['close'].shift(3)).fillna(0.0)
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

    # Configurations to test
    configs = [
        {"name": "Fixed Grid 1.50 (150 pts)", "mode": "FIXED", "step": 1.50, "tp": 1.50, "max_layers": 8, "lot_mode": "linear", "freeze": False, "sl": 150},
        {"name": "Fixed Grid 2.00 (200 pts)", "mode": "FIXED", "step": 2.00, "tp": 2.00, "max_layers": 6, "lot_mode": "linear", "freeze": False, "sl": 150},
        {"name": "Fixed Grid 2.50 + Freeze", "mode": "FIXED", "step": 2.50, "tp": 2.50, "max_layers": 6, "lot_mode": "clamped", "freeze": True, "sl": 150},
        {"name": "Adaptive ATR 1.8x Grid", "mode": "ATR", "mult": 1.8, "tp_mult": 1.2, "max_layers": 6, "lot_mode": "clamped", "freeze": True, "sl": 140},
        {"name": "Adaptive ATR 2.2x Grid (Quantum)", "mode": "ATR", "mult": 2.2, "tp_mult": 1.3, "max_layers": 6, "lot_mode": "clamped", "freeze": True, "sl": 140},
        {"name": "Asymmetric ATR Grid + Trend Filter", "mode": "ASYM", "mult": 2.0, "tp_mult": 1.3, "max_layers": 5, "lot_mode": "clamped", "freeze": True, "sl": 140, "trend": True}
    ]

    print("=" * 80)
    print(f"XAUUSD M1 GRID BACKTEST (43,200 Candles | Sep 16 - Oct 30, 2026)")
    print(f"Capital: $1,000 | Base Lot: 0.01 | Spread: $0.35")
    print("=" * 80)

    for cfg in configs:
        balance = 1000.0
        peak = 1000.0
        max_dd = 0.0
        closed_trades = 0
        wins = 0
        disasters = 0
        total_pnl = 0.0

        basket = [] # {'price': float, 'lot': float}
        b_type = None

        for i in range(60, len(df)):
            row = df.iloc[i]
            c = row['close']
            atr = max(1.20, row['atr14'])
            vel3 = row['vel3']
            trend = 1 if row['ema21'] >= row['ema55'] else -1

            # Floating PnL
            if len(basket) > 0:
                tot_lots = sum(x['lot'] for x in basket)
                vwap = sum(x['price'] * x['lot'] for x in basket) / tot_lots
                if b_type == 'BUY':
                    pnl = sum((c - x['price']) * x['lot'] * 100 for x in basket)
                else:
                    pnl = sum((x['price'] - c) * x['lot'] * 100 for x in basket)

                eq = balance + pnl
                if eq > peak: peak = eq
                dd = peak - eq
                if dd > max_dd: max_dd = dd

                # Disaster SL
                if pnl <= -cfg['sl']:
                    balance += pnl
                    total_pnl += pnl
                    closed_trades += 1
                    disasters += 1
                    basket = []
                    b_type = None
                    continue

                # Take Profit
                if cfg['mode'] == 'FIXED':
                    tp_target = cfg['tp']
                else:
                    tp_target = max(1.20, atr * cfg.get('tp_mult', 1.2))

                hit_tp = (c >= vwap + tp_target) if b_type == 'BUY' else (c <= vwap - tp_target)
                if hit_tp or pnl >= 3.5:
                    balance += pnl
                    total_pnl += pnl
                    closed_trades += 1
                    wins += 1
                    basket = []
                    b_type = None
                    continue

                # Layering (Grid spacing)
                if len(basket) < cfg['max_layers']:
                    layer_idx = len(basket)
                    if cfg['mode'] == 'FIXED':
                        step = cfg['step']
                    elif cfg['mode'] == 'ATR':
                        step = atr * cfg['mult']
                    elif cfg['mode'] == 'ASYM':
                        factors = [1.5, 2.0, 2.8, 3.8, 5.0]
                        step = atr * factors[min(layer_idx - 1, len(factors) - 1)]

                    worst_price = min(x['price'] for x in basket) if b_type == 'BUY' else max(x['price'] for x in basket)
                    dist = (worst_price - c) if b_type == 'BUY' else (c - worst_price)

                    if dist >= step:
                        freeze_trigger = False
                        if cfg['freeze']:
                            if b_type == 'BUY' and vel3 < -(2.0 * atr):
                                freeze_trigger = True # Waterfall drop, wait
                            elif b_type == 'SELL' and vel3 > (2.0 * atr):
                                freeze_trigger = True # Rocket pump, wait

                        if not freeze_trigger:
                            lot = 0.01 if (cfg['lot_mode'] == 'linear' or layer_idx < 2) else 0.02
                            basket.append({'price': c, 'lot': lot})

            else:
                # Open first layer
                lot = 0.01
                if cfg.get('trend'):
                    b_type = 'BUY' if trend > 0 else 'SELL'
                else:
                    b_type = 'BUY' if row['close'] > row['open'] else 'SELL'
                basket = [{'price': c, 'lot': lot}]

        win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0
        roi = ((balance - 1000.0) / 1000.0) * 100
        dd_pct = (max_dd / peak * 100) if peak > 0 else 100
        print(f"{cfg['name']:<35} | PnL: ${total_pnl:>+8.2f} ({roi:>+6.1f}%) | Win: {win_rate:>5.1f}% | DD: ${max_dd:>6.2f} ({dd_pct:>4.1f}%) | Cycles: {closed_trades} | Sl: {disasters}")

if __name__ == "__main__":
    run_m1_grid_backtest()
