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

def run_smc_partials(csv_path="data_cache/XAUUSD_M5_1MONTH.csv"):
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    df['sh'], df['sl'] = detect_swings(df['high'].values, df['low'].values, depth=4)
    
    spread = 0.35
    total_lot = 0.06 # 2 parts of 0.03
    half_lot = 0.03
    min_rr = 2.8
    
    balance = 1000.0
    equity_curve = [balance]
    trades = []
    active = None
    
    for i in range(25, len(df)):
        curr = df.iloc[i]
        c_time = curr['time']
        hour = c_time.hour
        
        if active is not None:
            t_type = active['type']
            sl_p = active['sl']
            tp1 = active['tp1']
            tp2 = active['tp2']
            entry = active['entry']
            
            # Check TP1
            if not active['tp1_closed']:
                if (t_type == 'BUY' and curr['high'] >= tp1) or (t_type == 'SELL' and curr['low'] <= tp1):
                    # Close 50%
                    pnl_tp1 = (tp1 - entry - spread if t_type == 'BUY' else entry - tp1 - spread) * half_lot * 100
                    balance += pnl_tp1
                    active['tp1_closed'] = True
                    active['remaining_lot'] = half_lot
                    active['sl'] = entry + (0.20 if t_type == 'BUY' else -0.20) # Protected BE
                    trades.append({'win': pnl_tp1 > 0, 'pnl': pnl_tp1, 'stage': 'TP1'})
                    
            # Check Exit for remaining
            rem_lot = active['remaining_lot']
            closed_rem = False
            pnl_rem = 0.0
            
            if t_type == 'BUY':
                if curr['low'] <= active['sl']:
                    closed_rem = True
                    pnl_rem = (active['sl'] - entry - spread) * rem_lot * 100
                elif curr['high'] >= tp2:
                    closed_rem = True
                    pnl_rem = (tp2 - entry - spread) * rem_lot * 100
            elif t_type == 'SELL':
                if curr['high'] >= active['sl']:
                    closed_rem = True
                    pnl_rem = (entry - active['sl'] - spread) * rem_lot * 100
                elif curr['low'] <= tp2:
                    closed_rem = True
                    pnl_rem = (entry - tp2 - spread) * rem_lot * 100
                    
            if closed_rem:
                balance += pnl_rem
                trades.append({'win': pnl_rem > 0, 'pnl': pnl_rem, 'stage': 'Runner/SL'})
                equity_curve.append(balance)
                active = None
                continue
                
        if active is None:
            if hour < 7 or hour > 19:
                continue
            recent_sh = df.iloc[max(0, i-40):i-2]['sh'].dropna()
            recent_sl = df.iloc[max(0, i-40):i-2]['sl'].dropna()
            if len(recent_sh) == 0 or len(recent_sl) == 0:
                continue
                
            last_sh = recent_sh.iloc[-1]
            last_sl = recent_sl.iloc[-1]
            prev1 = df.iloc[i-1]
            
            # Bullish CHoCH setup
            bullish_sweep = (prev1['low'] < last_sl) and (curr['close'] > last_sl) and (curr['close'] > curr['ema200'])
            if bullish_sweep and (curr['close'] > curr['open']):
                entry = curr['close'] + (spread / 2.0)
                sl_p = min(prev1['low'], curr['low']) - (curr['atr'] * 0.25)
                risk = entry - sl_p
                if 0.8 <= risk <= 4.5:
                    active = {
                        'type': 'BUY',
                        'entry': entry,
                        'sl': sl_p,
                        'tp1': entry + (risk * 1.2),
                        'tp2': entry + (risk * min_rr),
                        'tp1_closed': False,
                        'remaining_lot': total_lot
                    }
                    continue
                    
            # Bearish CHoCH setup
            bearish_sweep = (prev1['high'] > last_sh) and (curr['close'] < last_sh) and (curr['close'] < curr['ema200'])
            if bearish_sweep and (curr['close'] < curr['open']):
                entry = curr['close'] - (spread / 2.0)
                sl_p = max(prev1['high'], curr['high']) + (curr['atr'] * 0.25)
                risk = sl_p - entry
                if 0.8 <= risk <= 4.5:
                    active = {
                        'type': 'SELL',
                        'entry': entry,
                        'sl': sl_p,
                        'tp1': entry - (risk * 1.2),
                        'tp2': entry - (risk * min_rr),
                        'tp1_closed': False,
                        'remaining_lot': total_lot
                    }
                    continue

    wins = [t for t in trades if t['win']]
    losses = [t for t in trades if not t['win']]
    total = len(trades)
    wr = len(wins) / total * 100
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
            
    print("=" * 65)
    print("INSTITUTIONAL SMC SNIPER WITH PARTIAL SCALING RESULTS:")
    print("=" * 65)
    print(f"Total Trade Executions: {total}")
    print(f"Win Rate:               {wr:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Gross Profit:           ${gp:,.2f}")
    print(f"Gross Loss:             ${gl:,.2f}")
    print(f"Net Profit:             ${net:,.2f} ({(net/1000)*100:+.2f}%)")
    print(f"Profit Factor:          {pf:.2f}")
    print(f"Max Drawdown:           {max_dd:.2f}%")
    print(f"Final Balance:          ${balance:,.2f}")
    print("=" * 65)

if __name__ == '__main__':
    run_smc_partials()
