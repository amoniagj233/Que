import pandas as pd
import numpy as np

def run_hybrid_backtest():
    print("=" * 70)
    print("[HYBRID] BACKTESTING HYBRID PATTERN PRO (ATR RETEST + MOMENTUM IMPULSE)")
    print("=" * 70)
    
    df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    open_p = df['open'].values
    hours = df['time'].dt.hour.values
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
    
    for tp_usd in [3.50, 4.50, 5.50]:
        for atr_spacing_mult in [1.8, 2.2, 2.6]:
            for max_layers in [3, 4, 5]:
                balance = 1000.0
                trades = []
                positions = [] # Active basket
                equity_curve = [balance]
                
                for i in range(25, n):
                    curr_c = close[i]
                    curr_h = high[i]
                    curr_l = low[i]
                    c_atr = atr[i]
                    
                    # 1. Manage Active Positions (Check Group TP)
                    if len(positions) > 0:
                        total_volume = sum(p['vol'] for p in positions)
                        pos_type = positions[0]['type']
                        avg_price = sum(p['price'] * p['vol'] for p in positions) / total_volume
                        
                        # Current profit
                        if pos_type == 'BUY':
                            pnl_usd = (curr_c - avg_price - spread) * total_volume * 100
                        else:
                            pnl_usd = (avg_price - curr_c - spread) * total_volume * 100
                            
                        # Check Target USD or Disaster Stop
                        if pnl_usd >= tp_usd or pnl_usd <= -120.0:
                            balance += pnl_usd
                            trades.append({'win': pnl_usd > 0, 'pnl': pnl_usd, 'layers': len(positions)})
                            equity_curve.append(balance)
                            positions = []
                            continue
                            
                        # Check Spacing for Retest Layer
                        if len(positions) < max_layers:
                            last_entry = positions[-1]['price']
                            spacing = c_atr * atr_spacing_mult * (1.3 ** (len(positions) - 1))
                            
                            # Velocity Freeze: Skip layer if candle is an extreme outlier
                            velocity = abs(close[i] - open_p[i])
                            if velocity < (c_atr * 2.5): # Only add if not an extreme crash
                                if pos_type == 'BUY' and (last_entry - curr_c) >= spacing:
                                    positions.append({'type': 'BUY', 'price': curr_c, 'vol': lot_size})
                                elif pos_type == 'SELL' and (curr_c - last_entry) >= spacing:
                                    positions.append({'type': 'SELL', 'price': curr_c, 'vol': lot_size})
                                    
                    # 2. Entry Signal (Pattern Pro: Double Bottom / Top / Box Breakout + 200 EMA + 21/55 EMA)
                    if len(positions) == 0:
                        is_bullish_trend = (curr_c > ema200[i]) and (ema21[i] > ema55[i])
                        is_bearish_trend = (curr_c < ema200[i]) and (ema21[i] < ema55[i])
                        
                        prev_c = close[i-1]
                        h_b = h_box[i]
                        l_b = l_box[i]
                        
                        # Pattern Breakout / Reversal Signal
                        if curr_c > h_b and prev_c <= h_b and is_bullish_trend:
                            positions.append({'type': 'BUY', 'price': curr_c + (spread / 2.0), 'vol': lot_size})
                        elif curr_c < l_b and prev_c >= l_b and is_bearish_trend:
                            positions.append({'type': 'SELL', 'price': curr_c - (spread / 2.0), 'vol': lot_size})

                if len(trades) < 15:
                    continue
                    
                wins = [t for t in trades if t['win']]
                losses = [t for t in trades if not t['win']]
                wr = len(wins) / len(trades) * 100
                gp = sum(t['pnl'] for t in wins)
                gl = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
                pf = gp / gl if gl > 0 else 999.0
                net = balance - 1000.0
                
                # Max DD
                peak = 1000.0
                max_dd = 0.0
                for eq in equity_curve:
                    if eq > peak:
                        peak = eq
                    dd = (peak - eq) / peak * 100
                    if dd > max_dd:
                        max_dd = dd
                        
                print(f"TP: ${tp_usd:.2f} | ATR_Mult: {atr_spacing_mult} | MaxL: {max_layers} => Trades: {len(trades):>3} | WinRate: {wr:>5.1f}% | PF: {pf:>5.2f} | Net: ${net:>+7.2f} | DD: {max_dd:>4.1f}%")

if __name__ == '__main__':
    run_hybrid_backtest()
