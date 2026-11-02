import pandas as pd
import numpy as np

def detect_swings(highs, lows, depth=4):
    n = len(highs)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    for i in range(depth, n - depth):
        if highs[i] == np.max(highs[i - depth : i + depth + 1]):
            sh[i] = highs[i]
        if lows[i] == np.min(lows[i - depth : i + depth + 1]):
            sl[i] = lows[i]
    return sh, sl

def optimize_smc(csv_path="data_cache/XAUUSD_M5_1MONTH.csv"):
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # 200 EMA for Macro Trend
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # ATR
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    
    df['sh'], df['sl'] = detect_swings(df['high'].values, df['low'].values, depth=4)
    
    # Grid search parameters
    best_res = None
    best_fitness = -9999
    
    spread = 0.35
    lot_size = 0.05
    
    for min_rr in [2.0, 2.5, 3.0]:
        for trend_filter in [True, False]:
            for require_fvg in [True, False]:
                balance = 1000.0
                trades = []
                active_trade = None
                
                for i in range(25, len(df)):
                    curr = df.iloc[i]
                    c_time = curr['time']
                    hour = c_time.hour
                    
                    # Trade management
                    if active_trade is not None:
                        t_type = active_trade['type']
                        sl_price = active_trade['sl']
                        tp1 = active_trade['tp1']
                        tp2 = active_trade['tp2']
                        entry = active_trade['entry']
                        
                        closed = False
                        exit_p = 0.0
                        pnl = 0.0
                        
                        if t_type == 'BUY':
                            if curr['low'] <= sl_price:
                                closed = True
                                exit_p = sl_price
                                pnl = (exit_p - entry - spread) * lot_size * 100
                            elif curr['high'] >= tp2:
                                closed = True
                                exit_p = tp2
                                pnl = (exit_p - entry - spread) * lot_size * 100
                            elif curr['high'] >= tp1 and not active_trade['be']:
                                active_trade['be'] = True
                                active_trade['sl'] = entry + 0.15 # Move to breakeven + buffer
                        elif t_type == 'SELL':
                            if curr['high'] >= sl_price:
                                closed = True
                                exit_p = sl_price
                                pnl = (entry - exit_p - spread) * lot_size * 100
                            elif curr['low'] <= tp2:
                                closed = True
                                exit_p = tp2
                                pnl = (entry - exit_p - spread) * lot_size * 100
                            elif curr['low'] <= tp1 and not active_trade['be']:
                                active_trade['be'] = True
                                active_trade['sl'] = entry - 0.15
                                
                        if closed:
                            balance += pnl
                            trades.append({'win': pnl > 0, 'pnl': pnl})
                            active_trade = None
                            continue
                            
                    # Entry logic
                    if active_trade is None:
                        if hour < 7 or hour > 19:
                            continue
                            
                        # Lookback swing levels
                        recent_sh = df.iloc[max(0, i-40):i-2]['sh'].dropna()
                        recent_sl = df.iloc[max(0, i-40):i-2]['sl'].dropna()
                        if len(recent_sh) == 0 or len(recent_sl) == 0:
                            continue
                            
                        last_sh = recent_sh.iloc[-1]
                        last_sl = recent_sl.iloc[-1]
                        
                        prev1 = df.iloc[i-1]
                        prev2 = df.iloc[i-2]
                        
                        # Bullish CHoCH setup
                        bullish_sweep = (prev1['low'] < last_sl) and (curr['close'] > last_sl)
                        bullish_trend = (curr['close'] > curr['ema200']) if trend_filter else True
                        fvg_bull = (curr['low'] > prev2['high']) if require_fvg else True
                        
                        if bullish_sweep and bullish_trend and fvg_bull and (curr['close'] > curr['open']):
                            entry = curr['close'] + (spread / 2.0)
                            sl_p = min(prev1['low'], curr['low']) - (curr['atr'] * 0.25)
                            risk = entry - sl_p
                            if 0.8 <= risk <= 4.5:
                                active_trade = {
                                    'type': 'BUY',
                                    'entry': entry,
                                    'sl': sl_p,
                                    'tp1': entry + (risk * 1.2),
                                    'tp2': entry + (risk * min_rr),
                                    'be': False
                                }
                                continue
                                
                        # Bearish CHoCH setup
                        bearish_sweep = (prev1['high'] > last_sh) and (curr['close'] < last_sh)
                        bearish_trend = (curr['close'] < curr['ema200']) if trend_filter else True
                        fvg_bear = (curr['high'] < prev2['low']) if require_fvg else True
                        
                        if bearish_sweep and bearish_trend and fvg_bear and (curr['close'] < curr['open']):
                            entry = curr['close'] - (spread / 2.0)
                            sl_p = max(prev1['high'], curr['high']) + (curr['atr'] * 0.25)
                            risk = sl_p - entry
                            if 0.8 <= risk <= 4.5:
                                active_trade = {
                                    'type': 'SELL',
                                    'entry': entry,
                                    'sl': sl_p,
                                    'tp1': entry - (risk * 1.2),
                                    'tp2': entry - (risk * min_rr),
                                    'be': False
                                }
                                continue

                if len(trades) < 15:
                    continue
                    
                wins = [t for t in trades if t['win']]
                losses = [t for t in trades if not t['win']]
                wr = len(wins) / len(trades) * 100
                gp = sum(t['pnl'] for t in wins)
                gl = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
                pf = gp / gl if gl > 0 else 999.0
                net = balance - 1000.0
                fitness = (net * pf) / (1.0 + (100.0 - wr))
                
                print(f"Config: RR={min_rr} | TrendFilter={trend_filter} | ReqFVG={require_fvg} => Trades: {len(trades)} | Win: {wr:.1f}% | PF: {pf:.2f} | Net: ${net:.2f} | Fit: {fitness:.1f}")
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_res = (min_rr, trend_filter, require_fvg, len(trades), wr, pf, net)
                    
    print("\n" + "=" * 60)
    print("BEST SMC CONFIGURATION:")
    print(f"RR: {best_res[0]} | TrendFilter: {best_res[1]} | ReqFVG: {best_res[2]}")
    print(f"Trades: {best_res[3]} | WinRate: {best_res[4]:.1f}% | PF: {best_res[5]:.2f} | Net: ${best_res[6]:.2f}")
    print("=" * 60)

if __name__ == '__main__':
    optimize_smc()
