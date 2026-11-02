import pandas as pd
import numpy as np

def test_breakout():
    df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    open_p = df['open'].values
    hours = df['time'].dt.hour.values
    n = len(df)
    
    # 200 EMA
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    ema200 = df['ema200'].values
    
    # 15-candle box
    df['h_box'] = df['high'].shift(1).rolling(15).max().fillna(999999)
    df['l_box'] = df['low'].shift(1).rolling(15).min().fillna(0)
    h_box = df['h_box'].values
    l_box = df['l_box'].values
    
    # Body ratio
    body_ratio = np.abs(close - open_p) / np.maximum(high - low, 0.001)
    
    spread = 0.35
    lot_size = 0.05
    
    for tp_mult in [1.0, 1.5, 2.0]:
        for min_body in [0.50, 0.60, 0.70]:
            for buffer_usd in [0.20, 0.50]:
                balance = 1000.0
                trades = []
                active = None
                
                for i in range(25, n):
                    curr_h = high[i]
                    curr_l = low[i]
                    curr_c = close[i]
                    
                    if active is not None:
                        t_type = active['type']
                        entry = active['entry']
                        sl = active['sl']
                        tp = active['tp']
                        
                        # Move to BE at 50% TP
                        if not active['be_moved']:
                            if t_type == 'BUY' and (curr_h - entry) >= (active['risk'] * 0.5):
                                active['sl'] = entry + 0.15
                                active['be_moved'] = True
                            elif t_type == 'SELL' and (entry - curr_l) >= (active['risk'] * 0.5):
                                active['sl'] = entry - 0.15
                                active['be_moved'] = True
                                
                        closed = False
                        pnl = 0.0
                        
                        if t_type == 'BUY':
                            if curr_l <= active['sl']:
                                closed = True
                                pnl = (active['sl'] - entry - spread) * lot_size * 100
                            elif curr_h >= tp:
                                closed = True
                                pnl = (tp - entry - spread) * lot_size * 100
                        elif t_type == 'SELL':
                            if curr_h >= active['sl']:
                                closed = True
                                pnl = (entry - active['sl'] - spread) * lot_size * 100
                            elif curr_l <= tp:
                                closed = True
                                pnl = (entry - tp - spread) * lot_size * 100
                                
                        if closed:
                            balance += pnl
                            trades.append({'win': pnl > 0, 'pnl': pnl})
                            active = None
                            continue
                            
                    if active is None:
                        h_now = hours[i]
                        if h_now < 7 or h_now > 19:
                            continue
                            
                        is_uptrend = curr_c > ema200[i]
                        is_downtrend = curr_c < ema200[i]
                        
                        if body_ratio[i] < min_body:
                            continue
                            
                        h_b = h_box[i]
                        l_b = l_box[i]
                        prev_c = close[i-1]
                        
                        order_type = ""; ent = 0.0; sl = 0.0
                        
                        # Bullish breakout above box
                        if curr_c > (h_b + buffer_usd) and prev_c <= h_b and is_uptrend:
                            order_type = "BUY"
                            ent = curr_c + (spread / 2.0)
                            # Stop loss at breakout candle low - $0.30 buffer
                            sl = low[i] - 0.30
                        # Bearish breakdown below box
                        elif curr_c < (l_b - buffer_usd) and prev_c >= l_b and is_downtrend:
                            order_type = "SELL"
                            ent = curr_c - (spread / 2.0)
                            # Stop loss at breakout candle high + $0.30 buffer
                            sl = high[i] + 0.30
                            
                        if order_type != "":
                            risk = abs(ent - sl)
                            if 1.0 <= risk <= 4.5:
                                tp = ent + (risk * tp_mult) if order_type == "BUY" else ent - (risk * tp_mult)
                                active = {
                                    'type': order_type,
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
                print(f"TP_Mult: {tp_mult} | MinBody: {min_body} | Buffer: ${buffer_usd} => Trades: {len(trades):>2} | WinRate: {wr:>5.1f}% | PF: {pf:>5.2f} | Net: ${net:>+7.2f}")

if __name__ == '__main__':
    test_breakout()
