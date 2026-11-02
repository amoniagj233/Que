import pandas as pd
import numpy as np

def detect_pivots(highs, lows, depth=4, confirm=2):
    n = len(highs)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(depth, n - confirm):
        if highs[i] == np.max(highs[i - depth : i + depth + 1]):
            ph[i + confirm] = highs[i]
        if lows[i] == np.min(lows[i - depth : i + depth + 1]):
            pl[i + confirm] = lows[i]
    return ph, pl

def test_full_pattern_pro(csv_path="data_cache/XAUUSD_M5_1MONTH.csv"):
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    df['ph'], df['pl'] = detect_pivots(df['high'].values, df['low'].values, depth=4, confirm=2)
    
    spread = 0.35
    p1_v = 0.0; p1_i = 0; p2_v = 0.0; p2_i = 0
    v1_v = 0.0; v1_i = 0; v2_v = 0.0; v2_i = 0
    
    balance = 1000.0
    equity_curve = [balance]
    trades = []
    active = None
    tranche_lot = 0.02
    
    for i in range(25, len(df)):
        curr = df.iloc[i]
        price = curr['close']
        c_time = curr['time']
        
        if not np.isnan(curr['ph']):
            p2_v = p1_v; p2_i = p1_i
            p1_v = curr['ph']; p1_i = i - 2
        if not np.isnan(curr['pl']):
            v2_v = v1_v; v2_i = v1_i
            v1_v = curr['pl']; v1_i = i - 2
            
        if active is not None:
            t_type = active['type']
            entry = active['entry']
            tp1 = active['tp1']
            tp2 = active['tp2']
            tp3 = active['tp3']
            
            # TP1
            if not active['tp1_hit']:
                if (t_type == 'BUY' and curr['high'] >= tp1) or (t_type == 'SELL' and curr['low'] <= tp1):
                    pnl1 = (tp1 - entry - spread if t_type == 'BUY' else entry - tp1 - spread) * tranche_lot * 100
                    balance += pnl1
                    active['tp1_hit'] = True
                    active['sl'] = entry + (0.20 if t_type == 'BUY' else -0.20)
                    trades.append({'win': pnl1 > 0, 'pnl': pnl1})
                    
            # TP2
            if active['tp1_hit'] and not active['tp2_hit']:
                if (t_type == 'BUY' and curr['high'] >= tp2) or (t_type == 'SELL' and curr['low'] <= tp2):
                    pnl2 = (tp2 - entry - spread if t_type == 'BUY' else entry - tp2 - spread) * tranche_lot * 100
                    balance += pnl2
                    active['tp2_hit'] = True
                    active['sl'] = tp1
                    trades.append({'win': pnl2 > 0, 'pnl': pnl2})
                    
            # Runner
            closed_runner = False
            pnl_run = 0.0
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
                trades.append({'win': pnl_run > 0, 'pnl': pnl_run})
                equity_curve.append(balance)
                active = None
                continue
                
        if active is None:
            is_uptrend = price > curr['ema200']
            is_downtrend = price < curr['ema200']
            pat = ""; ent = 0.0; sl = 0.0
            
            # 1. Double Bottom (W Pattern with ATR-based tolerance)
            if v1_v > 0 and v2_v > 0 and is_uptrend:
                if abs(v1_v - v2_v) <= (curr['atr'] * 1.5):
                    mid_peak = df.iloc[max(0, v2_i):v1_i]['high'].max() if v1_i > v2_i else 0
                    if mid_peak > 0 and curr['close'] > mid_peak and df.iloc[i-1]['close'] <= mid_peak and (i - v1_i < 60):
                        pat = "DOUBLE BOTTOM"
                        ent = curr['close'] + (spread / 2.0)
                        sl = min(v1_v, v2_v) - 0.20
                        
            # 2. Double Top (M Pattern)
            if p1_v > 0 and p2_v > 0 and pat == "" and is_downtrend:
                if abs(p1_v - p2_v) <= (curr['atr'] * 1.5):
                    mid_valley = df.iloc[max(0, p2_i):p1_i]['low'].min() if p1_i > p2_i else 0
                    if mid_valley > 0 and curr['close'] < mid_valley and df.iloc[i-1]['close'] >= mid_valley and (i - p1_i < 60):
                        pat = "DOUBLE TOP"
                        ent = curr['close'] - (spread / 2.0)
                        sl = max(p1_v, p2_v) + 0.20
                        
            # 3. Rectangle Breakout
            if pat == "":
                h_range = df.iloc[max(0, i-15):i]['high'].max()
                l_range = df.iloc[max(0, i-15):i]['low'].min()
                # Consolidation box: height < 2.5 * ATR
                if (h_range - l_range) <= (curr['atr'] * 2.5):
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
                if 0.8 <= h_dist <= 5.5:
                    active = {
                        'type': 'BUY' if is_buy else 'SELL',
                        'entry': ent,
                        'sl': sl,
                        'tp1': ent + (h_dist * 1.0) if is_buy else ent - (h_dist * 1.0),
                        'tp2': ent + (h_dist * 1.8) if is_buy else ent - (h_dist * 1.8),
                        'tp3': ent + (h_dist * 3.0) if is_buy else ent - (h_dist * 3.0),
                        'tp1_hit': False,
                        'tp2_hit': False
                    }

    wins = [t for t in trades if t['win']]
    losses = [t for t in trades if not t['win']]
    total = len(trades)
    wr = len(wins) / total * 100 if total > 0 else 0
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
    pf = gp / gl if gl > 0 else 999.0
    net = balance - 1000.0
    print("=" * 65)
    print("STRATEGIC PATTERN PRO (FULL ENGINE WITH RECTANGLE & W/M)")
    print("=" * 65)
    print(f"Total Trade Stages: {total}")
    print(f"Win Rate:           {wr:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Gross Profit:       ${gp:,.2f}")
    print(f"Gross Loss:         ${gl:,.2f}")
    print(f"Net Profit:         ${net:,.2f} ({(net/1000)*100:+.2f}%)")
    print(f"Profit Factor:      {pf:.2f}")
    print(f"Final Balance:      ${balance:,.2f}")
    print("=" * 65)

if __name__ == '__main__':
    test_full_pattern_pro()
