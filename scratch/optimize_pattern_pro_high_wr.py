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

def run_optimization():
    print("=" * 70)
    print("[OPTIMIZER] PATTERN PRO ULTRA-HIGH WIN RATE GRID ON GOLD (XAUUSD)")
    print("=" * 70)
    
    df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # Precompute Indicators
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    
    # Candle body metrics
    df['body_size'] = (df['close'] - df['open']).abs()
    df['total_range'] = df['high'] - df['low']
    df['body_ratio'] = df['body_size'] / df['total_range'].replace(0, 0.001)
    
    # Pivots
    df['ph'], df['pl'] = detect_pivots(df['high'].values, df['low'].values, depth=4, confirm=2)
    
    spread = 0.35
    lot_size = 0.05
    
    results = []
    
    # Test matrix
    body_ratios = [0.55, 0.65, 0.75]
    breakout_buffers = [0.25, 0.50, 0.75]
    tp_mults = [0.8, 1.0, 1.3]
    dual_ema_opts = [True, False]
    fast_be_opts = [True, False]
    
    for min_body in body_ratios:
        for buff in breakout_buffers:
            for tp_m in tp_mults:
                for dual_ema in dual_ema_opts:
                    for fast_be in fast_be_opts:
                        balance = 1000.0
                        trades = []
                        active = None
                        
                        p1_v = 0.0; p1_i = 0
                        v1_v = 0.0; v1_i = 0
                        
                        for i in range(25, len(df)):
                            curr = df.iloc[i]
                            price = curr['close']
                            c_time = curr['time']
                            hour = c_time.hour
                            
                            if not np.isnan(curr['ph']):
                                p1_v = curr['ph']; p1_i = i - 2
                            if not np.isnan(curr['pl']):
                                v1_v = curr['pl']; v1_i = i - 2
                                
                            # Manage active trade
                            if active is not None:
                                t_type = active['type']
                                entry = active['entry']
                                sl = active['sl']
                                tp = active['tp']
                                
                                # Fast Breakeven Trail
                                if fast_be and not active['be_moved']:
                                    if t_type == 'BUY' and (curr['high'] - entry) >= (active['risk'] * 0.5):
                                        active['sl'] = entry + 0.15
                                        active['be_moved'] = True
                                    elif t_type == 'SELL' and (entry - curr['low']) >= (active['risk'] * 0.5):
                                        active['sl'] = entry - 0.15
                                        active['be_moved'] = True
                                        
                                closed = False
                                exit_price = 0.0
                                pnl = 0.0
                                
                                if t_type == 'BUY':
                                    if curr['low'] <= active['sl']:
                                        closed = True
                                        exit_price = active['sl']
                                        pnl = (exit_price - entry - spread) * lot_size * 100
                                    elif curr['high'] >= tp:
                                        closed = True
                                        exit_price = tp
                                        pnl = (exit_price - entry - spread) * lot_size * 100
                                elif t_type == 'SELL':
                                    if curr['high'] >= active['sl']:
                                        closed = True
                                        exit_price = active['sl']
                                        pnl = (entry - exit_price - spread) * lot_size * 100
                                    elif curr['low'] <= tp:
                                        closed = True
                                        exit_price = tp
                                        pnl = (entry - exit_price - spread) * lot_size * 100
                                        
                                if closed:
                                    balance += pnl
                                    trades.append({'win': pnl > 0, 'pnl': pnl})
                                    active = None
                                    continue
                                    
                            # Entry logic
                            if active is None:
                                # Session filter: London & NY (07:00 to 19:00 UTC)
                                if hour < 7 or hour > 19:
                                    continue
                                    
                                if dual_ema:
                                    is_uptrend = (curr['close'] > curr['ema200']) and (curr['ema50'] > curr['ema200'])
                                    is_downtrend = (curr['close'] < curr['ema200']) and (curr['ema50'] < curr['ema200'])
                                else:
                                    is_uptrend = curr['close'] > curr['ema200']
                                    is_downtrend = curr['close'] < curr['ema200']
                                    
                                # Body strength confirmation
                                if curr['body_ratio'] < min_body:
                                    continue
                                    
                                pat = ""; ent = 0.0; sl = 0.0
                                prev1 = df.iloc[i-1]
                                
                                # Rectangle Breakout
                                h_box = df.iloc[max(0, i-15):i]['high'].max()
                                l_box = df.iloc[max(0, i-15):i]['low'].min()
                                
                                if (h_box - l_box) <= (curr['atr'] * 2.5):
                                    if curr['close'] > (h_box + buff) and prev1['close'] <= h_box and is_uptrend:
                                        pat = "RECTANGLE_BULL"
                                        ent = curr['close'] + (spread / 2.0)
                                        sl = l_box - 0.20
                                    elif curr['close'] < (l_box - buff) and prev1['close'] >= l_box and is_downtrend:
                                        pat = "RECTANGLE_BEAR"
                                        ent = curr['close'] - (spread / 2.0)
                                        sl = h_box + 0.20
                                        
                                if pat != "":
                                    risk = abs(ent - sl)
                                    is_buy = ent > sl
                                    if 0.8 <= risk <= 4.5:
                                        tp = ent + (risk * tp_m) if is_buy else ent - (risk * tp_m)
                                        active = {
                                            'type': 'BUY' if is_buy else 'SELL',
                                            'entry': ent,
                                            'sl': sl,
                                            'tp': tp,
                                            'risk': risk,
                                            'be_moved': False
                                        }

                        if len(trades) < 10:
                            continue
                            
                        wins = [t for t in trades if t['win']]
                        losses = [t for t in trades if not t['win']]
                        wr = len(wins) / len(trades) * 100
                        gp = sum(t['pnl'] for t in wins)
                        gl = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
                        pf = gp / gl if gl > 0 else 999.0
                        net = balance - 1000.0
                        
                        results.append({
                            'min_body': min_body,
                            'buff': buff,
                            'tp_m': tp_m,
                            'dual_ema': dual_ema,
                            'fast_be': fast_be,
                            'trades': len(trades),
                            'win_rate': wr,
                            'pf': pf,
                            'net': net
                        })

    # Sort results by Win Rate then Profit Factor
    results.sort(key=lambda x: (x['win_rate'], x['pf']), reverse=True)
    
    print("\n" + "=" * 75)
    print("TOP 5 CONFIGURATIONS RANKED BY HIGHEST WIN RATE:")
    print("=" * 75)
    for idx, r in enumerate(results[:5]):
        print(f"Rank #{idx+1} | Win Rate: {r['win_rate']:.1f}% | Profit Factor: {r['pf']:.2f} | Net PnL: ${r['net']:+,.2f} | Trades: {r['trades']}")
        print(f"       Settings: BodyRatio >= {r['min_body']} | BreakoutBuffer: ${r['buff']} | TP: {r['tp_m']}R | DualEMA: {r['dual_ema']} | FastBE: {r['fast_be']}")
        print("-" * 75)
        
    return results[0] if results else None

if __name__ == '__main__':
    run_optimization()
