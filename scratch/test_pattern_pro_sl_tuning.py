import pandas as pd
import numpy as np

def run_sl_tuning():
    print("=" * 70)
    print("[TUNING] TUNING STOP LOSS & RETEST ATR SPACING FOR HIGH WIN RATE + PROFIT")
    print("=" * 70)
    
    df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    close = df['close'].values
    open_p = df['open'].values
    n = len(df)
    
    # 21 & 55 EMA
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    ema21 = df['ema21'].values
    ema55 = df['ema55'].values
    
    # 200 EMA
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    ema200 = df['ema200'].values
    
    # ATR 14
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    atr = df['atr'].values
    
    # 15-candle box
    df['h_box'] = df['high'].shift(1).rolling(15).max().fillna(999999)
    df['l_box'] = df['low'].shift(1).rolling(15).min().fillna(0)
    h_box = df['h_box'].values
    l_box = df['l_box'].values
    
    spread = 0.35
    lot_size = 0.02
    
    results = []
    
    for stop_loss_usd in [20.0, 30.0, 40.0, 50.0]:
        for tp_usd in [4.0, 5.0, 6.0, 7.5]:
            for atr_mult in [2.4, 2.8, 3.2]:
                for max_layers in [2, 3]:
                    balance = 1000.0
                    trades = []
                    positions = []
                    equity_curve = [balance]
                    
                    for i in range(25, n):
                        curr_c = close[i]
                        c_atr = atr[i]
                        
                        if len(positions) > 0:
                            total_vol = sum(p['vol'] for p in positions)
                            pos_type = positions[0]['type']
                            avg_p = sum(p['price'] * p['vol'] for p in positions) / total_vol
                            
                            pnl = (curr_c - avg_p - spread) * total_vol * 100 if pos_type == 'BUY' else (avg_p - curr_c - spread) * total_vol * 100
                            
                            # Exit condition
                            if pnl >= tp_usd or pnl <= -stop_loss_usd:
                                balance += pnl
                                trades.append({'win': pnl > 0, 'pnl': pnl})
                                equity_curve.append(balance)
                                positions = []
                                continue
                                
                            # Retest Spacing Layer
                            if len(positions) < max_layers:
                                last_entry = positions[-1]['price']
                                spacing = c_atr * atr_mult
                                velocity = abs(close[i] - open_p[i])
                                if velocity < (c_atr * 2.5):
                                    if pos_type == 'BUY' and (last_entry - curr_c) >= spacing:
                                        positions.append({'type': 'BUY', 'price': curr_c, 'vol': lot_size})
                                    elif pos_type == 'SELL' and (curr_c - last_entry) >= spacing:
                                        positions.append({'type': 'SELL', 'price': curr_c, 'vol': lot_size})
                                        
                        if len(positions) == 0:
                            is_bull = (curr_c > ema200[i]) and (ema21[i] > ema55[i])
                            is_bear = (curr_c < ema200[i]) and (ema21[i] < ema55[i])
                            prev_c = close[i-1]
                            h_b = h_box[i]
                            l_b = l_box[i]
                            
                            if curr_c > h_b and prev_c <= h_b and is_bull:
                                positions.append({'type': 'BUY', 'price': curr_c + (spread / 2.0), 'vol': lot_size})
                            elif curr_c < l_b and prev_c >= l_b and is_bear:
                                positions.append({'type': 'SELL', 'price': curr_c - (spread / 2.0), 'vol': lot_size})

                    if len(trades) < 20:
                        continue
                        
                    wins = [t for t in trades if t['win']]
                    losses = [t for t in trades if not t['win']]
                    wr = len(wins) / len(trades) * 100
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
                            
                    results.append({
                        'sl': stop_loss_usd,
                        'tp': tp_usd,
                        'atr_m': atr_mult,
                        'max_l': max_layers,
                        'trades': len(trades),
                        'wr': wr,
                        'pf': pf,
                        'net': net,
                        'dd': max_dd
                    })

    # Sort by Win Rate then Profit Factor
    results.sort(key=lambda x: (x['wr'], x['pf']), reverse=True)
    
    print("\n" + "=" * 80)
    print("TOP 10 TUNED SETTINGS (RANKED BY HIGHEST WIN RATE & PROFIT FACTOR):")
    print("=" * 80)
    for idx, r in enumerate(results[:10]):
        print(f"Rank #{idx+1:>2} | Win Rate: {r['wr']:>5.1f}% | Profit Factor: {r['pf']:>5.2f} | Net: ${r['net']:>+7.2f} | DD: {r['dd']:>4.1f}% | Trades: {r['trades']:>3}")
        print(f"        Settings -> TP: ${r['tp']} | SL: ${r['sl']} | RetestATR: {r['atr_m']}x | MaxLayers: {r['max_l']}")
        print("-" * 80)
        
    return results[0]

if __name__ == '__main__':
    run_sl_tuning()
