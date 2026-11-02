import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

symbol = "XAUUSD"
num_bars = 6000  # ~4.5 days of M1 data
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, num_bars)
mt5.shutdown()

if rates is None or len(rates) == 0:
    print("Failed to fetch rates")
    sys.exit(1)

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

# Calculate indicators
# 1. ATR (14)
tr1 = df['high'] - df['low']
tr2 = (df['high'] - df['close'].shift(1)).abs()
tr3 = (df['low'] - df['close'].shift(1)).abs()
df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['atr'] = df['tr'].rolling(14).mean()

# 2. RSI (14)
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / (loss + 1e-9)
df['rsi'] = 100 - (100 / (1 + rs))

# 3. Fast & Slow EMA on M1
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

# 4. Bullish reversal candle
df['bullish_candle'] = df['close'] > df['open']
df['bearish_candle'] = df['close'] < df['open']

df.dropna(inplace=True)
df.reset_index(drop=True, inplace=True)

print(f"Data ready: {len(df)} M1 bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

# Backtest Engine Function
def run_simulation(name, strategy_type, params):
    balance = 1000.0  # Starting balance $1000 for realistic scaling
    initial_balance = balance
    max_equity = balance
    max_drawdown = 0.0
    closed_trades = []
    
    # Position tracking
    # Basket: list of dicts: {'type': 'BUY', 'lot': 0.01, 'price': 4050.0}
    basket = []
    basket_type = None # 'BUY' or 'SELL'
    
    spread = 0.35 # $0.35 spread on gold (35 pts)
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr']
        rsi = row['rsi']
        bull_c = row['bullish_candle']
        bear_c = row['bearish_candle']
        trend = 1 if row['ema21'] > row['ema55'] else -1
        
        # Calculate Basket stats
        if len(basket) > 0:
            total_lots = sum(p['lot'] for p in basket)
            vwap = sum(p['price'] * p['lot'] for p in basket) / total_lots
            
            # Current floating PnL
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
                
            # Check Disaster Stop Loss
            if params.get('disaster_sl', 50.0) > 0 and floating_pnl <= -params['disaster_sl']:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'layers': len(basket), 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue
                
            # Check Group Take Profit (VWAP)
            # TP distance can be fixed or ATR-based
            if params.get('use_atr_tp', False):
                tp_dist = max(0.50, atr * params.get('atr_tp_mult', 1.0))
            else:
                tp_dist = params.get('tp_dist', 0.60)
                
            tp_hit = False
            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                if high >= target_tp or floating_pnl >= params.get('target_usd', 2.50):
                    tp_hit = True
                    pnl = sum((target_tp - p['price']) * p['lot'] * 100 for p in basket)
            else:
                target_tp = vwap - tp_dist
                if low <= target_tp or floating_pnl >= params.get('target_usd', 2.50):
                    tp_hit = True
                    pnl = sum((p['price'] - target_tp) * p['lot'] * 100 for p in basket)
                    
            if tp_hit:
                balance += pnl
                closed_trades.append({'pnl': pnl, 'layers': len(basket), 'reason': 'GroupTP'})
                basket = []
                basket_type = None
                continue
                
            # Check DCA Grid Addition
            max_layers = params.get('max_layers', 5)
            if len(basket) < max_layers:
                # Calculate grid step
                if params.get('use_atr_step', False):
                    step = max(0.60, atr * params.get('atr_step_mult', 1.5))
                else:
                    step = params.get('grid_step', 0.60)
                    
                worst_price = min(p['price'] for p in basket) if basket_type == 'BUY' else max(p['price'] for p in basket)
                
                # Check distance trigger
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)
                
                if dist_ok:
                    # Check Reversal Filter if enabled
                    confirm_ok = True
                    if params.get('use_reversal_filter', False):
                        if basket_type == 'BUY':
                            # Require green candle OR RSI hook from oversold
                            confirm_ok = bull_c or (rsi < 35 and row['close'] > row['open'])
                        else:
                            confirm_ok = bear_c or (rsi > 65 and row['close'] < row['open'])
                            
                    if confirm_ok:
                        layer = len(basket)
                        # Sizing: Martingale multiplier vs Safe Clamped Sizing
                        if params.get('lot_mode', 'multiplier') == 'clamped':
                            # 0.01, 0.01, 0.02, 0.02, 0.02 (Safe linear/clamped)
                            next_lot = 0.01 if layer < 2 else 0.02
                        else:
                            # 0.01, 0.01, 0.02, 0.03, 0.05 (1.5x Multiplier)
                            next_lot = round(0.01 * (1.5 ** layer), 2)
                            
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': curr_price})
                        
        else:
            # Basket is empty, check for initial entry
            # Filter check: Trend filter
            allow_buy = True
            allow_sell = True
            if params.get('use_trend_filter', False):
                if trend > 0:
                    allow_sell = False
                elif trend < 0:
                    allow_buy = False
                    
            # Open initial layer
            if allow_buy and (not params.get('use_reversal_filter', False) or bull_c):
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': 0.01, 'price': curr_price + spread})
            elif allow_sell and (not params.get('use_reversal_filter', False) or bear_c):
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': 0.01, 'price': curr_price - spread})
                
    # Summary metrics
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
    avg_layers = np.mean([t['layers'] for t in closed_trades]) if closed_trades else 0
    profit_factor = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))) if losses and sum(t['pnl'] for t in losses) != 0 else 999.0
    
    return {
        'name': name,
        'net_profit': net_profit,
        'win_rate': win_rate,
        'total_cycles': total_trades,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'avg_layers': avg_layers,
        'disaster_stops': len(losses)
    }

# Run 4 Configurations
configs = [
    {
        'name': 'Original Baseline (Fixed 60pts, No Filter)',
        'params': {
            'grid_step': 0.60,
            'tp_dist': 0.60,
            'max_layers': 5,
            'lot_mode': 'multiplier',
            'disaster_sl': 50.0,
            'use_atr_step': False,
            'use_reversal_filter': False,
            'use_trend_filter': False
        }
    },
    {
        'name': 'Upgrade 1: Dynamic ATR Volatility Spacing',
        'params': {
            'use_atr_step': True,
            'atr_step_mult': 1.5,   # Spacing widens to ~$1.00-$1.50 during high volatility
            'use_atr_tp': True,
            'atr_tp_mult': 1.0,
            'max_layers': 5,
            'lot_mode': 'multiplier',
            'disaster_sl': 50.0,
            'use_reversal_filter': False,
            'use_trend_filter': False
        }
    },
    {
        'name': 'Upgrade 2: Candle Reversal Filter (No Falling Knife)',
        'params': {
            'grid_step': 0.60,
            'tp_dist': 0.60,
            'max_layers': 5,
            'lot_mode': 'multiplier',
            'disaster_sl': 50.0,
            'use_atr_step': False,
            'use_reversal_filter': True, # Only adds DCA on green reversal / RSI bounce
            'use_trend_filter': True     # EMA trend alignment
        }
    },
    {
        'name': 'Upgrade 3: Small-Account Margin Clamped Sizing',
        'params': {
            'grid_step': 0.60,
            'tp_dist': 0.60,
            'max_layers': 5,
            'lot_mode': 'clamped',       # 0.01, 0.01, 0.02 max (no 0.03/0.05 margin calls)
            'disaster_sl': 35.0,
            'use_atr_step': False,
            'use_reversal_filter': False,
            'use_trend_filter': True
        }
    },
    {
        'name': 'Golden Master Combo (All 3 Upgrades Combined)',
        'params': {
            'use_atr_step': True,        # Dynamic ATR step
            'atr_step_mult': 1.3,
            'use_atr_tp': True,
            'atr_tp_mult': 1.0,
            'max_layers': 5,
            'lot_mode': 'clamped',       # Clamped lots for account safety
            'disaster_sl': 35.0,
            'use_reversal_filter': True, # Candle reversal confirmation
            'use_trend_filter': True     # Trend filter
        }
    }
]

print("\n" + "=" * 80)
print(f"{'STRATEGY UPGRADE':<42} | {'NET P/L':<9} | {'WIN %':<7} | {'CYCLES':<7} | {'MAX DD':<9} | {'PF':<5}")
print("=" * 80)

results = []
for c in configs:
    res = run_simulation(c['name'], None, c['params'])
    results.append(res)
    print(f"{res['name']:<42} | ${res['net_profit']:>7.2f} | {res['win_rate']:>5.1f}% | {res['total_cycles']:>7} | ${res['max_drawdown']:>7.2f} | {res['profit_factor']:>5.2f}")

print("=" * 80)
