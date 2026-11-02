import pandas as pd
import numpy as np

def run_champion_test():
    print("=" * 70)
    print("[CHAMPION BENCHMARK] OPTIMIZED HIGH-WIN-RATE PATTERN PRO")
    print("=" * 70)
    
    for tf_name, path in [("M5 (1 Month)", "data_cache/XAUUSD_M5_1MONTH.csv"), 
                          ("M1 (43,200 Bars / ~45 Days)", "data_cache/XAUUSD_M1_43200.csv")]:
        df = pd.read_csv(path)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        close = df['close'].values
        open_p = df['open'].values
        n = len(df)
        
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
        ema21 = df['ema21'].values
        ema55 = df['ema55'].values
        
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        ema200 = df['ema200'].values
        
        hl = df['high'] - df['low']
        hc = (df['high'] - df['close'].shift()).abs()
        lc = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean().fillna(1.5)
        atr = df['atr'].values
        
        df['h_box'] = df['high'].shift(1).rolling(15).max().fillna(999999)
        df['l_box'] = df['low'].shift(1).rolling(15).min().fillna(0)
        h_box = df['h_box'].values
        l_box = df['l_box'].values
        
        spread = 0.35
        lot_size = 0.01
        tp_usd = 3.50
        asym_growth = 1.4
        atr_mult = 2.0
        disaster_sl = 85.0
        
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
                
                if pnl >= tp_usd or pnl <= -disaster_sl:
                    balance += pnl
                    trades.append({'win': pnl > 0, 'pnl': pnl})
                    equity_curve.append(balance)
                    positions = []
                    continue
                    
                if len(positions) < 5:
                    last_entry = positions[-1]['price']
                    spacing = c_atr * atr_mult * (asym_growth ** (len(positions) - 1))
                    vel = abs(curr_c - open_p[i])
                    if vel < (c_atr * 2.2):
                        if pos_type == 'BUY' and (last_entry - curr_c) >= spacing:
                            positions.append({'type': 'BUY', 'price': curr_c, 'vol': lot_size})
                        elif pos_type == 'SELL' and (curr_c - last_entry) >= spacing:
                            positions.append({'type': 'SELL', 'price': curr_c, 'vol': lot_size})
                            
            if len(positions) == 0:
                is_bull = (curr_c > ema200[i]) and (ema21[i] > ema55[i])
                is_bear = (curr_c < ema200[i]) and (ema21[i] < ema55[i])
                prev_c = close[i-1]
                
                if curr_c > h_box[i] and prev_c <= h_box[i] and is_bull:
                    positions.append({'type': 'BUY', 'price': curr_c + (spread / 2.0), 'vol': lot_size})
                elif curr_c < l_box[i] and prev_c >= l_box[i] and is_bear:
                    positions.append({'type': 'SELL', 'price': curr_c - (spread / 2.0), 'vol': lot_size})

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
                
        print(f"Results for {tf_name}:")
        print(f"  Total Trades:  {len(trades)}")
        print(f"  Win Rate:      {wr:.2f}% ({len(wins)} Wins / {len(losses)} Losses)")
        print(f"  Gross Profit:  ${gp:,.2f}")
        print(f"  Gross Loss:    ${gl:,.2f}")
        print(f"  Net Profit:    ${net:+,.2f} ({(net/1000)*100:+.2f}%)")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Max Drawdown:  {max_dd:.2f}%")
        print(f"  Final Balance: ${balance:,.2f}")
        print("-" * 70)

if __name__ == '__main__':
    run_champion_test()
