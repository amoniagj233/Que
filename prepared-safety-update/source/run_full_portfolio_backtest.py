"""
End-to-End Multi-Strategy Portfolio Backtest
Validates Slot 1 (Mut-8407) and Slot 2 (Mut-1580)
With and Without the 24-Hour Macro Anti-Exhaustion Guard.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_cache", "XAUUSD_M5_1MONTH.csv")
LEADERBOARD_FILE = os.path.join(BASE_DIR, "strategy_leaderboard.json")

# Load leaderboard DNAs
with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
    leaderboard = json.load(f)

strat1 = leaderboard["top_strategies"][0]["dna"] # Mut-8407
strat2 = leaderboard["top_strategies"][1]["dna"] # Mut-1580

# Load dataset
df = pd.read_csv(DATA_FILE)
df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time').reset_index(drop=True)

# Compute Features
tr1 = df['high'] - df['low']
tr2 = (df['high'] - df['close'].shift(1)).abs()
tr3 = (df['low'] - df['close'].shift(1)).abs()
df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['atr14'] = df['tr'].rolling(14).mean().bfill()

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / (loss + 1e-9)
df['rsi14'] = (100 - (100 / (1 + rs))).bfill()

df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
df['ma332'] = df['close'].rolling(332).mean()
df['dist_332_atr'] = (df['close'] - df['ma332']) / df['atr14']

df['bullish'] = df['close'] > df['open']
df['bearish'] = df['close'] < df['open']
df['body'] = (df['close'] - df['open']).abs()
df['hammer'] = (df['bullish']) & ((df['open'] - df['low']) > 2 * df['body'])
df['shooting_star'] = (df['bearish']) & ((df['high'] - df['open']) > 2 * df['body'])
df['vel3'] = (df['close'] - df['close'].shift(3)).fillna(0.0)

# Discard warmup
df = df.iloc[350:].reset_index(drop=True)

def run_simulation(strat_dna, use_exhaustion_guard=False, spread=0.38):
    balance = 1000.0
    initial_balance = 1000.0
    peak_equity = 1000.0
    max_dd = 0.0
    closed_trades = []
    basket = []
    basket_type = None
    base_lot = 0.01
    
    max_layers = strat_dna.get('max_layers', 5)
    disaster_sl = strat_dna.get('disaster_sl', 140.0)
    atr_mult = strat_dna.get('atr_mult', 2.2)
    tp_atr_mult = strat_dna.get('tp_atr_mult', 1.3)
    target_usd = strat_dna.get('target_usd', 4.5)
    
    for i in range(len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr14']
        rsi = row['rsi14']
        vel3 = row['vel3']
        bull_c = row['bullish']
        bear_c = row['bearish']
        dist_332_atr = row['dist_332_atr']
        
        # 1. Active Basket Management
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots
            floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket) if basket_type == 'BUY' else sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)
            
            equity = balance + floating_pnl
            if equity > peak_equity: peak_equity = equity
            dd = peak_equity - equity
            if dd > max_dd: max_dd = dd
            
            # Disaster Stop
            if floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue
                
            # TP Check
            tp_dist = max(1.20, atr * tp_atr_mult)
            tp_hit = False
            realized_pnl = 0.0
            
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
                
            # DCA Grid Addition
            if len(basket) < max_layers:
                layer = len(basket)
                step = max(2.50, atr * atr_mult)
                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)
                
                if dist_ok:
                    next_lot = base_lot if layer < 2 else (base_lot * 2.0)
                    fill_p = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                    basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})
                    
        else:
            # 2. Initial Entry Evaluation
            trend = 1 if row['ema21'] >= row['ema55'] else -1
            allow_buy = (trend == 1)
            allow_sell = (trend == -1)
            
            # 24h Anti-Exhaustion Guard (MA 332, 7.0x ATR)
            if use_exhaustion_guard:
                if dist_332_atr > 7.0:
                    allow_buy = False
                elif dist_332_atr < -7.0:
                    allow_sell = False
                    
            if allow_buy and (bull_c or rsi < 32):
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and (bear_c or rsi > 68):
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': base_lot, 'price': curr_price - spread})
                
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    disasters = [t for t in closed_trades if t['reason'] == 'Disaster_SL']
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0
    net_profit = balance - initial_balance
    win_rate = (len(wins) / len(closed_trades) * 100.0) if closed_trades else 0.0
    
    return {
        "cycles": len(closed_trades),
        "wins": len(wins),
        "losses": len(losses),
        "disasters": len(disasters),
        "win_rate": round(win_rate, 1),
        "net_profit": round(net_profit, 2),
        "profit_factor": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "max_dd_pct": round((max_dd / initial_balance) * 100, 1)
    }

print("=" * 80)
print("  OFFICIAL SYSTEM VERIFICATION: BEFORE VS. AFTER 24H EXHAUSTION GUARD")
print("  Historical Sample: XAUUSD M5 (8,640 Real Candles) | Headway Friction Included")
print("=" * 80)

for name, dna in [("Slot 1 (Mut-8407)", strat1), ("Slot 2 (Mut-1580)", strat2)]:
    res_before = run_simulation(dna, use_exhaustion_guard=False)
    res_after = run_simulation(dna, use_exhaustion_guard=True)
    
    print(f"\n▶ Strategy: {name}")
    print(f"  WITHOUT Guard : Net Profit: ${res_before['net_profit']:+,.2f} | PF: {res_before['profit_factor']:.2f} | Win Rate: {res_before['win_rate']}% | Disasters: {res_before['disasters']} | MaxDD: ${res_before['max_dd']:,.2f} ({res_before['max_dd_pct']}%)")
    print(f"  WITH 24h Guard: Net Profit: ${res_after['net_profit']:+,.2f} | PF: {res_after['profit_factor']:.2f} | Win Rate: {res_after['win_rate']}% | Disasters: {res_after['disasters']} | MaxDD: ${res_after['max_dd']:,.2f} ({res_after['max_dd_pct']}%)")
    
    p_diff = res_after['net_profit'] - res_before['net_profit']
    d_diff = res_before['disasters'] - res_after['disasters']
    dd_diff = res_before['max_dd'] - res_after['max_dd']
    print(f"  IMPROVEMENT   : Net Gain: ${p_diff:+,.2f} | Disasters Prevented: {d_diff} | Drawdown Reduced: -${dd_diff:,.2f}")

print("\n" + "=" * 80)
