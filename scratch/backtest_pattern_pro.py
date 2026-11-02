import pandas as pd
import numpy as np

"""
Backtest engine for Strategic Pattern Pro ported from Pine Script (PATTEN.txt)
Features:
- Double Bottom (W Pattern) & Double Top (M Pattern)
- Rectangle Consolidation Breakout (Bull & Bear)
- 200 EMA Trend Filter + Dynamic ATR Proximity Check (High Confidence vs Standard)
- Multi-tier Projections: TP1 (0.5R), TP2 (1.0R), TP3 (2.0R)
"""

def detect_pivots(highs, lows, depth=5, confirm=2):
    n = len(highs)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(depth, n - confirm):
        # pivot high at i
        is_ph = True
        for j in range(1, depth + 1):
            if highs[i] <= highs[i - j] or highs[i] < highs[i + j]:
                is_ph = False
                break
        if is_ph:
            ph[i + confirm] = highs[i]
            
        # pivot low at i
        is_pl = True
        for j in range(1, depth + 1):
            if lows[i] >= lows[i - j] or lows[i] > lows[i + j]:
                is_pl = False
                break
        if is_pl:
            pl[i + confirm] = lows[i]
            
    return ph, pl

def backtest_pattern_pro(csv_path="data_cache/XAUUSD_M5_1MONTH.csv", spread=0.35):
    print("=" * 65)
    print("[TEST] BACKTESTING STRATEGIC PATTERN PRO (PORTED FROM PATTEN.TXT)")
    print("=" * 65)
    
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # 200 EMA
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # ATR 14
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    
    # Detect Pivots
    df['ph'], df['pl'] = detect_pivots(df['high'].values, df['low'].values, depth=5, confirm=2)
    
    # Track pivots
    p1_v = 0.0; p1_i = 0; p2_v = 0.0; p2_i = 0
    v1_v = 0.0; v1_i = 0; v2_v = 0.0; v2_i = 0
    
    i_width = 0.008 # 0.8% price symmetry
    tp1_mult = 0.6
    tp2_mult = 1.2
    tp3_mult = 2.4
    
    balance = 1000.0
    equity_curve = [balance]
    trades = []
    active = None
    
    tranche_lot = 0.02 # 3 tranches of 0.02 = 0.06 total lot
    
    for i in range(25, len(df)):
        curr = df.iloc[i]
        price = curr['close']
        c_time = curr['time']
        
        # Update pivots
        if not np.isnan(curr['ph']):
            p2_v = p1_v; p2_i = p1_i
            p1_v = curr['ph']; p1_i = i - 2
        if not np.isnan(curr['pl']):
            v2_v = v1_v; v2_i = v1_i
            v1_v = curr['pl']; v1_i = i - 2
            
        # Manage active trade
        if active is not None:
            t_type = active['type']
            sl_p = active['sl']
            tp1 = active['tp1']
            tp2 = active['tp2']
            tp3 = active['tp3']
            entry = active['entry']
            
            # 1. Check TP1 (close 1/3)
            if not active['tp1_hit']:
                if (t_type == 'BUY' and curr['high'] >= tp1) or (t_type == 'SELL' and curr['low'] <= tp1):
                    pnl1 = (tp1 - entry - spread if t_type == 'BUY' else entry - tp1 - spread) * tranche_lot * 100
                    balance += pnl1
                    active['tp1_hit'] = True
                    active['sl'] = entry + (0.15 if t_type == 'BUY' else -0.15) # Move to BE
                    trades.append({'win': pnl1 > 0, 'pnl': pnl1, 'stage': 'TP1'})
                    
            # 2. Check TP2 (close 1/3)
            if active['tp1_hit'] and not active['tp2_hit']:
                if (t_type == 'BUY' and curr['high'] >= tp2) or (t_type == 'SELL' and curr['low'] <= tp2):
                    pnl2 = (tp2 - entry - spread if t_type == 'BUY' else entry - tp2 - spread) * tranche_lot * 100
                    balance += pnl2
                    active['tp2_hit'] = True
                    active['sl'] = tp1 # Trail to TP1 level
                    trades.append({'win': pnl2 > 0, 'pnl': pnl2, 'stage': 'TP2'})
                    
            # 3. Check Runner Exit (TP3 or SL)
            closed_runner = False
            pnl_run = 0.0
            
            # Current remaining lot
            rem_lot = tranche_lot if (active['tp1_hit'] and active['tp2_hit']) else (tranche_lot * 2 if active['tp1_hit'] else tranche_lot * 3)
            
            if t_type == 'BUY':
                if curr['low'] <= active['sl']:
                    closed_runner = True
                    pnl_run = (active['sl'] - entry - spread) * rem_lot * 100
                elif curr['high'] >= tp3:
                    closed_runner = True
                    pnl_run = (tp3 - entry - spread) * rem_lot * 100
            elif t_type == 'SELL':
                if curr['high'] >= active['sl']:
                    closed_runner = True
                    pnl_run = (entry - active['sl'] - spread) * rem_lot * 100
                elif curr['low'] <= tp3:
                    closed_runner = True
                    pnl_run = (entry - tp3 - spread) * rem_lot * 100
                    
            if closed_runner:
                balance += pnl_run
                trades.append({'win': pnl_run > 0, 'pnl': pnl_run, 'stage': 'Runner/SL'})
                equity_curve.append(balance)
                active = None
                continue
                
        # Entry Logic
        if active is None:
            is_uptrend = price > curr['ema200']
            is_downtrend = price < curr['ema200']
            
            pat = ""
            ent = 0.0
            sl = 0.0
            high_conf = False
            
            # 1. Double Bottom (W Pattern)
            if v1_v > 0 and v2_v > 0 and is_uptrend:
                if abs(v1_v - v2_v) <= (v1_v * i_width):
                    window = max(1, v1_i - v2_i)
                    mid_peak = df.iloc[max(0, v2_i):v1_i]['high'].max() if v1_i > v2_i else 0
                    if mid_peak > 0 and curr['close'] > mid_peak and df.iloc[i-1]['close'] <= mid_peak and (i - v1_i < 60):
                        pat = "DOUBLE BOTTOM"
                        ent = curr['close'] + (spread / 2.0)
                        sl = min(v1_v, v2_v) - 0.20
                        # MA proximity check
                        ma_at_v1 = df.iloc[v1_i]['ema200']
                        high_conf = abs(v1_v - ma_at_v1) < (curr['atr'] * 0.8)
                        
            # 2. Double Top (M Pattern)
            if p1_v > 0 and p2_v > 0 and pat == "" and is_downtrend:
                if abs(p1_v - p2_v) <= (p1_v * i_width):
                    window = max(1, p1_i - p2_i)
                    mid_valley = df.iloc[max(0, p2_i):p1_i]['low'].min() if p1_i > p2_i else 0
                    if mid_valley > 0 and curr['close'] < mid_valley and df.iloc[i-1]['close'] >= mid_valley and (i - p1_i < 60):
                        pat = "DOUBLE TOP"
                        ent = curr['close'] - (spread / 2.0)
                        sl = max(p1_v, p2_v) + 0.20
                        ma_at_p1 = df.iloc[p1_i]['ema200']
                        high_conf = abs(p1_v - ma_at_p1) < (curr['atr'] * 0.8)
                        
            # 3. Rectangle Breakout
            if pat == "":
                h_range = df.iloc[max(0, i-15):i]['high'].max()
                l_range = df.iloc[max(0, i-15):i]['low'].min()
                is_rect = (h_range - l_range) <= (h_range * i_width * 2.5)
                
                if is_rect:
                    if curr['close'] > h_range and df.iloc[i-1]['close'] <= h_range and is_uptrend:
                        pat = "RECTANGLE BULL"
                        ent = curr['close'] + (spread / 2.0)
                        sl = l_range - 0.20
                    elif curr['close'] < l_range and df.iloc[i-1]['close'] >= l_range and is_downtrend:
                        pat = "RECTANGLE BEAR"
                        ent = curr['close'] - (spread / 2.0)
                        sl = h_range + 0.20

            if pat != "":
                h_dist = abs(ent - sl)
                is_buy = ent > sl
                if 1.0 <= h_dist <= 6.5: # Realistic risk range on Gold
                    tp1 = ent + h_dist * tp1_mult if is_buy else ent - h_dist * tp1_mult
                    tp2 = ent + h_dist * tp2_mult if is_buy else ent - h_dist * tp2_mult
                    tp3 = ent + h_dist * tp3_mult if is_buy else ent - h_dist * tp3_mult
                    
                    active = {
                        'type': 'BUY' if is_buy else 'SELL',
                        'entry': ent,
                        'sl': sl,
                        'tp1': tp1,
                        'tp2': tp2,
                        'tp3': tp3,
                        'tp1_hit': False,
                        'tp2_hit': False,
                        'pattern': pat,
                        'high_conf': high_conf
                    }

    wins = [t for t in trades if t['win']]
    losses = [t for t in trades if not t['win']]
    total = len(trades)
    wr = len(wins) / total * 100 if total > 0 else 0
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
    pf = gp / gl if gl > 0 else 999.0
    net = balance - 1000.0
    
    peak = 1000.0
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    print(f"Total Trade Stages Executed: {total}")
    print(f"Win Rate:                   {wr:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Gross Profit:               ${gp:,.2f}")
    print(f"Gross Loss:                 ${gl:,.2f}")
    print(f"Net Profit:                 ${net:,.2f} ({(net/1000)*100:+.2f}%)")
    print(f"Profit Factor:              {pf:.2f}")
    print(f"Max Drawdown:               {max_dd:.2f}%")
    print(f"Final Balance:              ${balance:,.2f}")
    print("=" * 65)

if __name__ == '__main__':
    backtest_pattern_pro('data_cache/XAUUSD_M5_1MONTH.csv')
