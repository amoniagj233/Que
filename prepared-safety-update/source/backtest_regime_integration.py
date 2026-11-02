"""
Comprehensive Backtest: Integrating the 24-Hour Macro Trend Filter (from the video analysis)
into the Champion Strategy (Mut-8407) from strategy_leaderboard.json.

Tests:
1. Mut-8407 Baseline (Standard EMA_21_55 trend indicator)
2. Mut-8407 + 24-Hour Price vs MA 332 Filter (Price must be on correct side of 24h baseline)
3. Mut-8407 + 24-Hour MA 44/332 Regime Gate (MA 44 must be above/below MA 332)
4. Mut-8407 + 24-Hour Slope Gate (MA 332 slope over 1h must align with trade direction)
"""

import os
import json
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_cache", "XAUUSD_M5_1MONTH.csv")

# 1. Load Data
df = pd.read_csv(DATA_FILE)
df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time').reset_index(drop=True)

# 2. Indicators & Features
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

# Video Macro Trend Indicators (24-Hour Cycle = 288 to 332 M5 bars)
df['ma44'] = df['close'].rolling(44).mean()
df['ma332'] = df['close'].rolling(332).mean()
df['ma332_slope_1h'] = df['ma332'] - df['ma332'].shift(12) # 1 hour slope of 24h line

df['bullish'] = df['close'] > df['open']
df['bearish'] = df['close'] < df['open']
df['body'] = (df['close'] - df['open']).abs()
df['hammer'] = (df['bullish']) & ((df['open'] - df['low']) > 2 * df['body'])
df['shooting_star'] = (df['bearish']) & ((df['high'] - df['open']) > 2 * df['body'])
df['vel3'] = (df['close'] - df['close'].shift(3)).fillna(0.0)

# Drop initial warmup
df = df.iloc[350:].reset_index(drop=True)

# Mut-8407 DNA from strategy_leaderboard.json
P = {
    "name": "Mut-8407",
    "timeframe": "M5",
    "trend_indicator": "EMA_21_55",
    "entry_trigger": "CANDLE_DIRECTION",
    "spacing_mode": "DYNAMIC_ATR",
    "atr_mult": 2.2,
    "asym_growth": 1.4,
    "waterfall_freeze": True,
    "waterfall_thresh": 2.2,
    "lot_mode": "clamped",
    "max_layers": 5,
    "tp_mode": "DYNAMIC_ATR",
    "tp_atr_mult": 1.3,
    "target_usd": 4.5,
    "disaster_sl": 140.0
}

def simulate(df_data, filter_mode="none", spread=0.38):
    """
    Simulates the Mut-8407 engine with Headway spread friction ($3.80/oz = $0.38 on 0.1 lot scaling).
    filter_mode:
      - 'none': standard Mut-8407
      - 'price_vs_332': Price > MA 332 for BUY, Price < MA 332 for SELL
      - 'ma44_vs_332': MA 44 > MA 332 for BUY, MA 44 < MA 332 for SELL
      - 'slope_332': MA 332 Slope > 0 for BUY, Slope < 0 for SELL
    """
    balance = 1000.0
    initial_balance = 1000.0
    peak_equity = 1000.0
    max_dd = 0.0
    closed_trades = []
    
    basket = []
    basket_type = None
    base_lot = 0.01
    
    for i in range(len(df_data)):
        row = df_data.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr14']
        rsi = row['rsi14']
        vel3 = row['vel3']
        bull_c = row['bullish']
        bear_c = row['bearish']
        
        # 1. Manage Active Basket
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots
            
            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                floating_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)
                
            equity = balance + floating_pnl
            if equity > peak_equity:
                peak_equity = equity
            dd = peak_equity - equity
            if dd > max_dd:
                max_dd = dd
                
            # Disaster SL
            if P['disaster_sl'] > 0 and floating_pnl <= -P['disaster_sl']:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'reason': 'Disaster_SL', 'layers': len(basket)})
                basket = []
                basket_type = None
                continue
                
            # Take Profit evaluation
            tp_dist = max(1.20, atr * P['tp_atr_mult'])
            tp_hit = False
            realized_pnl = 0.0
            
            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                if high >= target_tp:
                    tp_hit = True
                    realized_pnl = sum((target_tp - x['price']) * x['lot'] * 100 for x in basket)
            else:
                target_tp = vwap - tp_dist
                if low <= target_tp:
                    tp_hit = True
                    realized_pnl = sum((x['price'] - target_tp) * x['lot'] * 100 for x in basket)
                    
            if tp_hit:
                balance += realized_pnl
                closed_trades.append({'pnl': realized_pnl, 'reason': 'GroupTP', 'layers': len(basket)})
                basket = []
                basket_type = None
                continue
                
            # Grid Addition
            if len(basket) < P['max_layers']:
                layer = len(basket)
                step = max(2.50, atr * P['atr_mult'])
                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)
                
                if dist_ok:
                    confirm_ok = True
                    if P['waterfall_freeze']:
                        wf_thresh = P['waterfall_thresh'] * atr
                        if basket_type == 'BUY':
                            is_waterfall = vel3 < -wf_thresh
                            confirm_ok = (bull_c or row['hammer'] or rsi < 28) if is_waterfall else (bull_c or rsi < 35)
                        else:
                            is_waterfall = vel3 > wf_thresh
                            confirm_ok = (bear_c or row['shooting_star'] or rsi > 72) if is_waterfall else (bear_c or rsi > 65)
                            
                    if confirm_ok:
                        next_lot = base_lot if layer < 2 else (base_lot * 2.0)
                        fill_p = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})
                        
        else:
            # 2. Basket is empty -> Evaluate New Entry
            # Core M5 Trend: EMA 21 >= EMA 55
            trend = 1 if row['ema21'] >= row['ema55'] else -1
            
            allow_buy = (trend == 1)
            allow_sell = (trend == -1)
            
            # Apply Macro Filter
            if filter_mode == 'price_vs_332':
                allow_buy = allow_buy and (curr_price > row['ma332'])
                allow_sell = allow_sell and (curr_price < row['ma332'])
            elif filter_mode == 'ma44_vs_332':
                allow_buy = allow_buy and (row['ma44'] > row['ma332'])
                allow_sell = allow_sell and (row['ma44'] < row['ma332'])
            elif filter_mode == 'slope_332':
                allow_buy = allow_buy and (row['ma332_slope_1h'] > 0)
                allow_sell = allow_sell and (row['ma332_slope_1h'] < 0)
                
            buy_trig = bull_c
            sell_trig = bear_c
            
            if allow_buy and buy_trig:
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and sell_trig:
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': base_lot, 'price': curr_price - spread})
                
    # Close any leftover basket at end
    if len(basket) > 0:
        last_p = df_data.iloc[-1]['close']
        if basket_type == 'BUY':
            final_pnl = sum((last_p - x['price']) * x['lot'] * 100 for x in basket)
        else:
            final_pnl = sum((x['price'] - last_p) * x['lot'] * 100 for x in basket)
        balance += final_pnl
        closed_trades.append({'pnl': final_pnl, 'reason': 'EndSession', 'layers': len(basket)})

    return compute_stats(closed_trades, initial_balance, balance, max_dd)

def compute_stats(trades, initial_bal, final_bal, max_dd):
    total = len(trades)
    if total == 0:
        return {"total": 0, "net_profit": 0, "win_rate": 0, "pf": 0, "max_dd": 0, "disasters": 0}
        
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    disasters = [t for t in trades if t.get('reason') == 'Disaster_SL']
    
    net_profit = final_bal - initial_bal
    win_rate = (len(wins) / total) * 100.0
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0
    
    return {
        "total_cycles": total,
        "wins": len(wins),
        "losses": len(losses),
        "disasters": len(disasters),
        "win_rate": round(win_rate, 1),
        "net_profit": round(net_profit, 2),
        "profit_factor": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "max_dd_pct": round((max_dd / initial_bal) * 100, 1),
        "avg_trade_pnl": round(net_profit / total, 2)
    }

if __name__ == '__main__':
    print("=" * 70)
    print("  SIMULATION RESULTS: MUT-8407 ENHANCED WITH 24H MACRO FILTERS")
    print("=" * 70)
    
    modes = [
        ("1. Baseline (No Macro Filter)", "none"),
        ("2. Price vs 24h Baseline (MA 332)", "price_vs_332"),
        ("3. 24h Regime Gate (MA 44 > MA 332)", "ma44_vs_332"),
        ("4. 24h Slope Momentum (Slope MA 332 > 0)", "slope_332")
    ]
    
    for label, mode in modes:
        res = simulate(df, filter_mode=mode)
        print(f"\n>>> {label}:")
        print(f"    Total Completed Cycles:  {res['total_cycles']}")
        print(f"    Win Rate:                {res['win_rate']}% ({res['wins']} wins / {res['losses']} losses)")
        print(f"    Net Profit:              ${res['net_profit']:+,.2f} on $1,000 starting account")
        print(f"    Profit Factor:           {res['profit_factor']}")
        print(f"    Disaster Stop Hits:      {res['disasters']} times")
        print(f"    Max Drawdown:            ${res['max_dd']:,.2f} ({res['max_dd_pct']}%)")
        print(f"    Avg Profit per Cycle:    ${res['avg_trade_pnl']:+,.2f}")
    print("=" * 70)
