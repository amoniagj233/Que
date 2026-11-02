import pandas as pd
import numpy as np

def run_fast_optimization():
    print("=" * 70)
    print("[OPTIMIZER] VECTORIZED PATTERN PRO ULTRA-HIGH WIN RATE OPTIMIZATION")
    print("=" * 70)
    
    df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # Precompute ALL Indicators in NumPy arrays for 100x speed
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    open_p = df['open'].values
    hours = df['time'].dt.hour.values
    n = len(df)
    
    # 50 & 200 EMA
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    ema50 = df['ema50'].values
    ema200 = df['ema200'].values
    
    # ATR 14
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    atr = df['atr'].values
    
    # Rolling 15-bar boxes (Rectangle ranges)
    df['h_box'] = df['high'].shift(1).rolling(15).max().fillna(999999)
    df['l_box'] = df['low'].shift(1).rolling(15).min().fillna(0)
    h_box = df['h_box'].values
    l_box = df['l_box'].values
    
    # Body ratio
    body_size = np.abs(close - open_p)
    total_range = np.maximum(high - low, 0.001)
    body_ratio = body_size / total_range
    
    spread = 0.35
    lot_size = 0.05
    results = []
    
    # Optimization Grid
    body_ratios = [0.50, 0.60, 0.70]
    breakout_buffers = [0.20, 0.40, 0.60]
    tp_mults = [0.8, 1.0, 1.2, 1.5]
    dual_emas = [True, False]
    fast_bes = [True, False]
    
    for min_body in body_ratios:
        for buff in breakout_buffers:
            for tp_m in tp_mults:
                for dual_ema in dual_emas:
                    for fast_be in fast_bes:
                        balance = 1000.0
                        trades = []
                        active = None
                        
                        for i in range(25, n):
                            curr_h = high[i]
                            curr_l = low[i]
                            curr_c = close[i]
                            h_now = hours[i]
                            
                            if active is not None:
                                t_type = active['type']
                                entry = active['entry']
                                sl = active['sl']
                                tp = active['tp']
                                
                                # Fast Breakeven Trail
                                if fast_be and not active['be_moved']:
                                    if t_type == 'BUY' and (curr_h - entry) >= (active['risk'] * 0.45):
                                        active['sl'] = entry + 0.15
                                        active['be_moved'] = True
                                    elif t_type == 'SELL' and (entry - curr_l) >= (active['risk'] * 0.45):
                                        active['sl'] = entry - 0.15
                                        active['be_moved'] = True
                                        
                                closed = False
                                exit_price = 0.0
                                pnl = 0.0
                                
                                if t_type == 'BUY':
                                    if curr_l <= active['sl']:
                                        closed = True
                                        exit_price = active['sl']
                                        pnl = (exit_price - entry - spread) * lot_size * 100
                                    elif curr_h >= tp:
                                        closed = True
                                        exit_price = tp
                                        pnl = (exit_price - entry - spread) * lot_size * 100
                                elif t_type == 'SELL':
                                    if curr_h >= active['sl']:
                                        closed = True
                                        exit_price = active['sl']
                                        pnl = (entry - exit_price - spread) * lot_size * 100
                                    elif curr_l <= tp:
                                        closed = True
                                        exit_price = tp
                                        pnl = (entry - exit_price - spread) * lot_size * 100
                                        
                                if closed:
                                    balance += pnl
                                    trades.append({'win': pnl > 0, 'pnl': pnl})
                                    active = None
                                    continue
                                    
                            if active is None:
                                if h_now < 7 or h_now > 19:
                                    continue
                                    
                                if dual_ema:
                                    is_uptrend = (curr_c > ema200[i]) and (ema50[i] > ema200[i])
                                    is_downtrend = (curr_c < ema200[i]) and (ema50[i] < ema200[i])
                                else:
                                    is_uptrend = curr_c > ema200[i]
                                    is_downtrend = curr_c < ema200[i]
                                    
                                if body_ratio[i] < min_body:
                                    continue
                                    
                                h_b = h_box[i]
                                l_b = l_box[i]
                                c_atr = atr[i]
                                
                                if (h_b - l_b) <= (c_atr * 2.5):
                                    prev_c = close[i-1]
                                    ent = 0.0; sl = 0.0; order_type = ""
                                    
                                    if curr_c > (h_b + buff) and prev_c <= h_b and is_uptrend:
                                        order_type = "BUY"
                                        ent = curr_c + (spread / 2.0)
                                        sl = l_b - 0.20
                                    elif curr_c < (l_b - buff) and prev_c >= l_b and is_downtrend:
                                        order_type = "SELL"
                                        ent = curr_c - (spread / 2.0)
                                        sl = h_b + 0.20
                                        
                                    if order_type != "":
                                        risk = abs(ent - sl)
                                        if 0.8 <= risk <= 4.5:
                                            tp = ent + (risk * tp_m) if order_type == "BUY" else ent - (risk * tp_m)
                                            active = {
                                                'type': order_type,
                                                'entry': ent,
                                                'sl': sl,
                                                'tp': tp,
                                                'risk': risk,
                                                'be_moved': False
                                            }

                        if len(trades) < 8:
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

    results.sort(key=lambda x: (x['win_rate'], x['pf']), reverse=True)
    
    print("\n" + "=" * 80)
    print("TOP 10 HIGH WIN-RATE CONFIGURATIONS (GOLD M5):")
    print("=" * 80)
    for idx, r in enumerate(results[:10]):
        print(f"Rank #{idx+1:>2} | Win Rate: {r['win_rate']:>5.1f}% | Profit Factor: {r['pf']:>5.2f} | Net: ${r['net']:>+7.2f} | Trades: {r['trades']:>3}")
        print(f"        Settings -> BodyRatio: {r['min_body']} | Buffer: ${r['buff']} | TP: {r['tp_m']}R | DualEMA: {r['dual_ema']} | FastBE: {r['fast_be']}")
        print("-" * 80)
        
    return results[0] if results else None

if __name__ == '__main__':
    run_fast_optimization()
