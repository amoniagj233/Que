"""
Testing MA 332 as a Mean-Reversion Exhaustion Band:
If Price is stretched > 2.5x ATR above MA 332 -> Don't Buy (Exhaustion Zone)
If Price is stretched > 2.5x ATR below MA 332 -> Don't Sell
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_cache", "XAUUSD_M5_1MONTH.csv")

df = pd.read_csv(DATA_FILE)
df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time').reset_index(drop=True)

tr1 = df['high'] - df['low']
tr2 = (df['high'] - df['close'].shift(1)).abs()
tr3 = (df['low'] - df['close'].shift(1)).abs()
df['atr14'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean().bfill()

df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
df['ma332'] = df['close'].rolling(332).mean()

# Distance from 24h baseline in ATR multiples
df['dist_from_332_atr'] = (df['close'] - df['ma332']) / df['atr14']

df['bullish'] = df['close'] > df['open']
df['bearish'] = df['close'] < df['open']
df['body'] = (df['close'] - df['open']).abs()
df['hammer'] = (df['bullish']) & ((df['open'] - df['low']) > 2 * df['body'])
df['shooting_star'] = (df['bearish']) & ((df['high'] - df['open']) > 2 * df['body'])
df['vel3'] = (df['close'] - df['close'].shift(3)).fillna(0.0)

df = df.iloc[350:].reset_index(drop=True)

P = {
    "name": "Mut-8407",
    "atr_mult": 2.2,
    "max_layers": 5,
    "tp_atr_mult": 1.3,
    "disaster_sl": 140.0,
    "waterfall_freeze": True,
    "waterfall_thresh": 2.2
}

def run_exhaustion_test(exhaustion_cap=None):
    balance = 1000.0
    initial_balance = 1000.0
    peak_equity = 1000.0
    max_dd = 0.0
    closed_trades = []
    basket = []
    basket_type = None
    base_lot = 0.01
    spread = 0.38
    
    for i in range(len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr14']
        dist_atr = row['dist_from_332_atr']
        
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots
            floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket) if basket_type == 'BUY' else sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)
            
            equity = balance + floating_pnl
            if equity > peak_equity: peak_equity = equity
            dd = peak_equity - equity
            if dd > max_dd: max_dd = dd
            
            if floating_pnl <= -P['disaster_sl']:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue
                
            tp_dist = max(1.20, atr * P['tp_atr_mult'])
            tp_hit = False
            if basket_type == 'BUY' and high >= vwap + tp_dist:
                tp_hit = True
                realized_pnl = sum((vwap + tp_dist - x['price']) * x['lot'] * 100 for x in basket)
            elif basket_type == 'SELL' and low <= vwap - tp_dist:
                tp_hit = True
                realized_pnl = sum((x['price'] - (vwap - tp_dist)) * x['lot'] * 100 for x in basket)
                
            if tp_hit:
                balance += realized_pnl
                closed_trades.append({'pnl': realized_pnl, 'reason': 'GroupTP'})
                basket = []
                basket_type = None
                continue
                
            if len(basket) < P['max_layers']:
                layer = len(basket)
                step = max(2.50, atr * P['atr_mult'])
                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)
                if dist_ok:
                    next_lot = base_lot if layer < 2 else (base_lot * 2.0)
                    fill_p = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                    basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})
        else:
            trend = 1 if row['ema21'] >= row['ema55'] else -1
            allow_buy = (trend == 1)
            allow_sell = (trend == -1)
            
            # Anti-Exhaustion filter: Don't buy if price is extremely stretched above 24h line!
            if exhaustion_cap is not None:
                if dist_atr > exhaustion_cap:
                    allow_buy = False # Too stretched upwards, don't buy top!
                elif dist_atr < -exhaustion_cap:
                    allow_sell = False # Too stretched downwards, don't sell bottom!
                    
            if allow_buy and row['bullish']:
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and row['bearish']:
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': base_lot, 'price': curr_price - spread})
                
    wins = [t for t in closed_trades if t['pnl'] > 0]
    disasters = [t for t in closed_trades if t['reason'] == 'Disaster_SL']
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in closed_trades if t['pnl'] <= 0))
    pf = gross_win / gross_loss if gross_loss > 0 else 999.0
    
    return {
        "cap": exhaustion_cap if exhaustion_cap else "No Filter",
        "cycles": len(closed_trades),
        "profit": round(balance - initial_balance, 2),
        "pf": round(pf, 2),
        "disasters": len(disasters),
        "max_dd": round(max_dd, 2)
    }

for cap in [None, 10.0, 7.0, 5.0, 4.0]:
    r = run_exhaustion_test(cap)
    print(f"Exhaustion Cap: {r['cap']} | Profit: ${r['profit']:+,.2f} | PF: {r['pf']} | Disasters: {r['disasters']} | MaxDD: ${r['max_dd']:,.2f}")
