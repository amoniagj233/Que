"""
Comprehensive 6-Month Deep Backtest Tournament Across All Bots
Period: April 23, 2026 to October 23, 2026 (3,003 Hourly Candles = 183 Days)
Asset: XAUUSD (Gold, $3,962 - $5,562/oz)
Broker: Headway ($3.80 spread + $0.20 slippage = $4.00 friction/oz)
Lot Size: 0.05 Lot (5 oz) | Account Balance: $10,000.00
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
H1_FILE = os.path.join(BASE_DIR, "data_cache", "XAUUSD_H1_5000.csv")

# 1. Load exact 6-Month Slice
df_full = pd.read_csv(H1_FILE)
df_full['dt'] = pd.to_datetime(df_full['time'])
end_dt = df_full['dt'].max()
start_6m = end_dt - pd.DateOffset(months=6)
df = df_full[df_full['dt'] >= start_6m].copy().reset_index(drop=True)

SPREAD_USD = 3.80
SLIPPAGE_USD = 0.20
TOTAL_COST = SPREAD_USD + SLIPPAGE_USD
CONTRACT_SIZE = 100
FIXED_LOT = 0.05
OZ = FIXED_LOT * CONTRACT_SIZE # 5 oz Gold
START_BAL = 10000.0

# Precompute Market Indicators
tr1 = df['high'] - df['low']
tr2 = (df['high'] - df['close'].shift(1)).abs()
tr3 = (df['low'] - df['close'].shift(1)).abs()
df['atr14'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean().bfill()

delta = df['close'].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
df['rsi14'] = (100 - (100 / (1 + (gain / (loss + 1e-9))))).bfill()

df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

# 24-Hour Cycle baseline on H1 = 24 bars
df['ma24'] = df['close'].rolling(24).mean().bfill()
df['dist_24h_atr'] = (df['close'] - df['ma24']) / (df['atr14'] + 1e-9)

# Swing Highs & Lows (10-bar lookback for Structure Grid)
df['swing_high'] = df['high'].rolling(10).max().shift(1)
df['swing_low'] = df['low'].rolling(10).min().shift(1)

def compute_metrics(name, trades):
    if not trades:
        return {"name": name, "trades": 0, "win_rate": 0.0, "net_profit": 0.0, "pf": 0.0, "max_dd": 0.0, "max_dd_pct": 0.0, "wins": 0, "losses": 0}
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    net_profit = sum(t['pnl'] for t in trades)
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0
    win_rate = (len(wins) / len(trades)) * 100.0
    
    curr = START_BAL
    peak = START_BAL
    max_dd = 0.0
    for t in trades:
        curr += t['pnl']
        if curr > peak: peak = curr
        dd = peak - curr
        if dd > max_dd: max_dd = dd
        
    return {
        "name": name,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "net_profit": round(net_profit, 2),
        "profit_factor": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "max_dd_pct": round((max_dd / START_BAL) * 100, 1)
    }

# ==============================================================================
# BOT 1: The Darwin Flagship (Mut-8407 + 24H Anti-Exhaustion Guard)
# ==============================================================================
def sim_darwin_flagship():
    trades = []
    basket = []
    basket_type = None
    max_layers = 5
    
    for i in range(30, len(df)):
        row = df.iloc[i]
        curr = row['close']
        atr = row['atr14']
        disaster_sl = 11.2 * atr * OZ # Proportional to M5 DNA ($140 / 5 oz = 11.2x ATR)
        
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['p'] * x['lot'] for x in basket) / total_lots
            fl_pnl = sum((curr - x['p']) * x['lot'] * CONTRACT_SIZE for x in basket) if basket_type == 'BUY' else sum((x['p'] - curr) * x['lot'] * CONTRACT_SIZE for x in basket)
            
            # Disaster Stop
            if fl_pnl <= -disaster_sl:
                trades.append({'pnl': fl_pnl, 'type': 'SL'})
                basket = []; basket_type = None; continue
                
            # Take Profit: 1.3x ATR
            tp_dist = max(5.0, atr * 1.3)
            if (basket_type == 'BUY' and row['high'] >= vwap + tp_dist) or (basket_type == 'SELL' and row['low'] <= vwap - tp_dist):
                real_pnl = sum(tp_dist * x['lot'] * CONTRACT_SIZE for x in basket) - (TOTAL_COST * total_lots * CONTRACT_SIZE)
                trades.append({'pnl': real_pnl, 'type': 'TP'})
                basket = []; basket_type = None; continue
                
            # DCA Grid Addition: 2.2x ATR
            if len(basket) < max_layers:
                step = max(8.0, atr * 2.2)
                worst = min(x['p'] for x in basket) if basket_type == 'BUY' else max(x['p'] for x in basket)
                if (basket_type == 'BUY' and worst - curr >= step) or (basket_type == 'SELL' and curr - worst >= step):
                    lot = FIXED_LOT if len(basket) < 2 else (FIXED_LOT * 1.5)
                    fill = curr + SPREAD_USD if basket_type == 'BUY' else curr - SPREAD_USD
                    basket.append({'p': fill, 'lot': lot})
        else:
            trend = 1 if row['ema21'] >= row['ema55'] else -1
            allow_buy = trend == 1
            allow_sell = trend == -1
            
            # 24H Anti-Exhaustion Guard (Cap 7.0x ATR)
            if row['dist_24h_atr'] > 7.0: allow_buy = False
            elif row['dist_24h_atr'] < -7.0: allow_sell = False
            
            if allow_buy and row['close'] > row['open']:
                basket_type = 'BUY'
                basket.append({'p': curr + SPREAD_USD, 'lot': FIXED_LOT})
            elif allow_sell and row['close'] < row['open']:
                basket_type = 'SELL'
                basket.append({'p': curr - SPREAD_USD, 'lot': FIXED_LOT})
                
    return compute_metrics("The Darwin Flagship (Mut-8407)", trades)

# ==============================================================================
# BOT 2: The Darwin Co-Pilot (Mut-1580 + 24H Anti-Exhaustion Guard)
# ==============================================================================
def sim_darwin_copilot():
    trades = []
    basket = []
    basket_type = None
    max_layers = 5
    
    for i in range(30, len(df)):
        row = df.iloc[i]
        curr = row['close']
        atr = row['atr14']
        disaster_sl = 12.0 * atr * OZ # $150 equivalent
        
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['p'] * x['lot'] for x in basket) / total_lots
            fl_pnl = sum((curr - x['p']) * x['lot'] * CONTRACT_SIZE for x in basket) if basket_type == 'BUY' else sum((x['p'] - curr) * x['lot'] * CONTRACT_SIZE for x in basket)
            
            if fl_pnl <= -disaster_sl:
                trades.append({'pnl': fl_pnl, 'type': 'SL'})
                basket = []; basket_type = None; continue
                
            tp_dist = max(6.0, atr * 1.4)
            if (basket_type == 'BUY' and row['high'] >= vwap + tp_dist) or (basket_type == 'SELL' and row['low'] <= vwap - tp_dist):
                real_pnl = sum(tp_dist * x['lot'] * CONTRACT_SIZE for x in basket) - (TOTAL_COST * total_lots * CONTRACT_SIZE)
                trades.append({'pnl': real_pnl, 'type': 'TP'})
                basket = []; basket_type = None; continue
                
            if len(basket) < max_layers:
                step = max(10.0, atr * 2.4)
                worst = min(x['p'] for x in basket) if basket_type == 'BUY' else max(x['p'] for x in basket)
                if (basket_type == 'BUY' and worst - curr >= step) or (basket_type == 'SELL' and curr - worst >= step):
                    lot = FIXED_LOT if len(basket) < 2 else (FIXED_LOT * 1.5)
                    fill = curr + SPREAD_USD if basket_type == 'BUY' else curr - SPREAD_USD
                    basket.append({'p': fill, 'lot': lot})
        else:
            trend = 1 if row['ema21'] >= row['ema55'] else -1
            allow_buy = trend == 1 and row['rsi14'] < 68
            allow_sell = trend == -1 and row['rsi14'] > 32
            
            if row['dist_24h_atr'] > 7.0: allow_buy = False
            elif row['dist_24h_atr'] < -7.0: allow_sell = False
            
            if allow_buy and row['close'] > row['open']:
                basket_type = 'BUY'
                basket.append({'p': curr + SPREAD_USD, 'lot': FIXED_LOT})
            elif allow_sell and row['close'] < row['open']:
                basket_type = 'SELL'
                basket.append({'p': curr - SPREAD_USD, 'lot': FIXED_LOT})
                
    return compute_metrics("The Darwin Co-Pilot (Mut-1580)", trades)

# ==============================================================================
# BOT 3: The SMC Sniper (Order Block & Fair Value Gap Retests)
# ==============================================================================
def sim_smc_sniper():
    trades = []
    n = len(df)
    bullish_obs = []
    bearish_obs = []
    
    for k in range(5, n - 2):
        atr_k = df['atr14'].iloc[k]
        c1, o1 = df['close'].iloc[k+1], df['open'].iloc[k+1]
        c0, o0 = df['close'].iloc[k], df['open'].iloc[k]
        if (c1 > o1) and ((c1 - o1) > 1.2 * atr_k) and (c0 < o0):
            bullish_obs.append({"idx": k, "top": df['high'].iloc[k], "bottom": df['low'].iloc[k]})
        elif (c1 < o1) and ((o1 - c1) > 1.2 * atr_k) and (c0 > o0):
            bearish_obs.append({"idx": k, "top": df['high'].iloc[k], "bottom": df['low'].iloc[k]})

    active = None
    for i in range(50, n):
        row = df.iloc[i]
        curr = row['close']
        atr = row['atr14']
        
        if active is not None:
            if active['side'] == 'BUY':
                if row['low'] <= active['sl']:
                    pnl = ((active['sl'] - active['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    active = None
                elif row['high'] >= active['tp']:
                    pnl = ((active['tp'] - active['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    active = None
            else:
                if row['high'] >= active['sl']:
                    pnl = ((active['entry'] - active['sl']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    active = None
                elif row['low'] <= active['tp']:
                    pnl = ((active['entry'] - active['tp']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    active = None
                    
        if active is None and i % 2 == 0:
            for ob in reversed(bullish_obs):
                if ob["idx"] >= i - 1: continue
                if ob["idx"] < i - 40: break
                if ob["bottom"] <= curr <= ob["top"] * 1.002:
                    sl = ob["bottom"] - (1.0 * atr)
                    risk = curr - sl
                    if 10.0 <= risk <= 60.0:
                        active = {'side': 'BUY', 'entry': curr, 'sl': sl, 'tp': curr + (2.5 * risk)}
                        break
            if active is None:
                for ob in reversed(bearish_obs):
                    if ob["idx"] >= i - 1: continue
                    if ob["idx"] < i - 40: break
                    if ob["bottom"] * 0.998 <= curr <= ob["top"]:
                        sl = ob["top"] + (1.0 * atr)
                        risk = sl - curr
                        if 10.0 <= risk <= 60.0:
                            active = {'side': 'SELL', 'entry': curr, 'sl': sl, 'tp': curr - (2.5 * risk)}
                            break

    return compute_metrics("The SMC Sniper (Order Blocks/FVG)", trades)

# ==============================================================================
# BOT 4: The Structure Grid (Higher-High / Lower-Low Geometry)
# ==============================================================================
def sim_structure_grid():
    trades = []
    pos = None
    
    for i in range(25, len(df)):
        row = df.iloc[i]
        curr = row['close']
        atr = row['atr14']
        sw_h = row['swing_high']
        sw_l = row['swing_low']
        
        if pos is not None:
            if pos['side'] == 'BUY':
                if row['low'] <= pos['sl']:
                    pnl = ((pos['sl'] - pos['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                elif row['high'] >= pos['tp']:
                    pnl = ((pos['tp'] - pos['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
            else:
                if row['high'] >= pos['sl']:
                    pnl = ((pos['entry'] - pos['sl']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                elif row['low'] <= pos['tp']:
                    pnl = ((pos['entry'] - pos['tp']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                    
        if pos is None:
            if curr > sw_h and row['ema21'] > row['ema55']:
                sl = curr - (1.8 * atr)
                pos = {'side': 'BUY', 'entry': curr, 'sl': sl, 'tp': curr + (3.0 * atr)}
            elif curr < sw_l and row['ema21'] < row['ema55']:
                sl = curr + (1.8 * atr)
                pos = {'side': 'SELL', 'entry': curr, 'sl': sl, 'tp': curr - (3.0 * atr)}
                    
    return compute_metrics("The Structure Grid (HH/LL Geometry)", trades)

# ==============================================================================
# BOT 5: The XTO Speeder (Momentum Pulse Scalper)
# ==============================================================================
def sim_xto_speeder():
    trades = []
    pos = None
    
    for i in range(25, len(df)):
        row = df.iloc[i]
        curr = row['close']
        atr = row['atr14']
        
        if pos is not None:
            if pos['side'] == 'BUY':
                if row['low'] <= pos['sl']:
                    pnl = ((pos['sl'] - pos['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                elif row['high'] >= pos['tp']:
                    pnl = ((pos['tp'] - pos['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
            else:
                if row['high'] >= pos['sl']:
                    pnl = ((pos['entry'] - pos['sl']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                elif row['low'] <= pos['tp']:
                    pnl = ((pos['entry'] - pos['tp']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                    
        if pos is None:
            ema9_cross_up = (row['ema9'] > row['ema21']) and (df['ema9'].iloc[i-1] <= df['ema21'].iloc[i-1])
            ema9_cross_dn = (row['ema9'] < row['ema21']) and (df['ema9'].iloc[i-1] >= df['ema21'].iloc[i-1])
            
            if ema9_cross_up and row['rsi14'] > 50:
                pos = {'side': 'BUY', 'entry': curr, 'sl': curr - (1.5 * atr), 'tp': curr + (2.2 * atr)}
            elif ema9_cross_dn and row['rsi14'] < 50:
                pos = {'side': 'SELL', 'entry': curr, 'sl': curr + (1.5 * atr), 'tp': curr - (2.2 * atr)}
                
    return compute_metrics("The XTO Speeder (Momentum Pulse)", trades)

# ==============================================================================
# BOT 6: Today's Baseline (MA 44 / 332 Strategy)
# ==============================================================================
def sim_today_baseline():
    trades = []
    pos = None
    # 24h baseline on H1
    df_temp = df.copy()
    df_temp['ma_fast'] = df_temp['close'].rolling(8).mean()
    df_temp['ma_slow'] = df_temp['close'].rolling(24).mean()
    
    for i in range(26, len(df_temp)):
        row = df_temp.iloc[i]
        prev = df_temp.iloc[i-1]
        curr = row['close']
        atr = row['atr14']
        
        cross_up = row['ma_fast'] > row['ma_slow'] and prev['ma_fast'] <= prev['ma_slow']
        cross_dn = row['ma_fast'] < row['ma_slow'] and prev['ma_fast'] >= prev['ma_slow']
        
        if pos is not None:
            if pos['side'] == 'BUY':
                if row['low'] <= pos['sl'] or cross_dn:
                    exit_p = pos['sl'] if row['low'] <= pos['sl'] else curr
                    pnl = ((exit_p - pos['entry']) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
            else:
                if row['high'] >= pos['sl'] or cross_up:
                    exit_p = pos['sl'] if row['high'] >= pos['sl'] else curr
                    pnl = ((pos['entry'] - exit_p) * OZ) - (TOTAL_COST * OZ)
                    trades.append({'pnl': pnl})
                    pos = None
                    
        if pos is None:
            if cross_up:
                pos = {'side': 'BUY', 'entry': curr, 'sl': curr - (2.5 * atr)}
            elif cross_dn:
                pos = {'side': 'SELL', 'entry': curr, 'sl': curr + (2.5 * atr)}
                
    return compute_metrics("Today's Baseline (MA 44/332 Crossover)", trades)

# Run All
results = [
    sim_darwin_flagship(),
    sim_darwin_copilot(),
    sim_smc_sniper(),
    sim_structure_grid(),
    sim_xto_speeder(),
    sim_today_baseline()
]

# Sort by Net Profit descending
results.sort(key=lambda x: x['net_profit'], reverse=True)

print("=" * 95)
print(f"  TOURNAMENT LEADERBOARD (6-MONTH CONTINUOUS BACKTEST: APR 23 - OCT 23, 2026)")
print("=" * 95)
print(f"{'RANK':<5} | {'BOT NAME':<40} | {'WIN RATE':<9} | {'NET PROFIT':<13} | {'PF':<6} | {'TRADES':<7} | {'MAX DD':<10}")
print("-" * 95)

for idx, b in enumerate(results, 1):
    medals = {1: "🥇 1", 2: "🥈 2", 3: "🥉 3"}
    rank_str = medals.get(idx, f"  {idx}")
    print(f"{rank_str:<5} | {b['name']:<40} | {b['win_rate']:>6.1f}%  | ${b['net_profit']:>10,.2f} | {b['profit_factor']:>5.2f} | {b['trades']:>6}  | ${b['max_dd']:>8,.2f}")

print("=" * 95)
champion = results[0]
print(f"\n🏆 CHAMPION BOT (MADE THE MOST MONEY):")
print(f"   Name         : {champion['name']}")
print(f"   Net Profit   : ${champion['net_profit']:+,.2f} on $10,000 capital")
print(f"   Win Rate     : {champion['win_rate']}%")
print(f"   Profit Factor: {champion['profit_factor']}")
print(f"   Max Drawdown : ${champion['max_dd']:,.2f} ({champion['max_dd_pct']}%)")
