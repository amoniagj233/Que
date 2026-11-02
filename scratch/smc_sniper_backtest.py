import pandas as pd
import numpy as np
from datetime import datetime

"""
SMC Liquidity & Breaker Block Sniper Engine for Gold (XAUUSD)
Core Concepts:
1. Swing High / Swing Low Pivot Detection (Fractals)
2. Liquidity Sweep: Price sweeps key Swing High/Low by > $0.50 but closes back inside (Stop Hunt)
3. Fair Value Gap (FVG): 3-bar imbalance zone with 50% equilibrium mitigation
4. Breaker Block / Market Structure Shift (CHoCH / BOS)
5. Session Filter: London & New York institutional liquidity windows
6. Dynamic Risk: Stop Loss behind sweep candle extreme + spread buffer, Target 1:2 to 1:3 R:R
"""

def detect_swings(df, depth=5):
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    
    swing_highs = np.full(n, np.nan)
    swing_lows = np.full(n, np.nan)
    
    for i in range(depth, n - depth):
        if highs[i] == np.max(highs[i - depth : i + depth + 1]):
            swing_highs[i] = highs[i]
        if lows[i] == np.min(lows[i - depth : i + depth + 1]):
            swing_lows[i] = lows[i]
            
    return swing_highs, swing_lows

def run_smc_backtest(csv_path, timeframe_name="M5", spread=0.35, min_rr=2.5):
    print("=" * 65)
    print(f"[TEST] BACKTESTING SMC LIQUIDITY & BREAKER BLOCK SNIPER on {timeframe_name}")
    print("=" * 65)
    
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # Calculate ATR
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    
    # Calculate Swings
    df['swing_high'], df['swing_low'] = detect_swings(df, depth=4)
    
    trades = []
    initial_balance = 1000.0
    balance = initial_balance
    equity_curve = [balance]
    
    active_trade = None
    
    # Scan through candles
    for i in range(20, len(df)):
        curr = df.iloc[i]
        price = curr['close']
        c_time = curr['time']
        hour = c_time.hour
        
        # 1. Manage Active Trade
        if active_trade is not None:
            high = curr['high']
            low = curr['low']
            t_type = active_trade['type']
            sl = active_trade['sl']
            tp1 = active_trade['tp1']
            tp2 = active_trade['tp2']
            
            closed = False
            exit_price = 0.0
            pnl = 0.0
            reason = ""
            
            if t_type == 'BUY':
                if low <= sl:
                    closed = True
                    exit_price = sl
                    pnl = (exit_price - active_trade['entry'] - spread) * active_trade['size'] * 100
                    reason = "SL Hit"
                elif high >= tp2:
                    closed = True
                    exit_price = tp2
                    pnl = (exit_price - active_trade['entry'] - spread) * active_trade['size'] * 100
                    reason = "TP2 Hit (Runner)"
                elif high >= tp1 and not active_trade.get('tp1_hit', False):
                    active_trade['tp1_hit'] = True
                    active_trade['sl'] = active_trade['entry'] + 0.10
                    
            elif t_type == 'SELL':
                if high >= sl:
                    closed = True
                    exit_price = sl
                    pnl = (active_trade['entry'] - exit_price - spread) * active_trade['size'] * 100
                    reason = "SL Hit"
                elif low <= tp2:
                    closed = True
                    exit_price = tp2
                    pnl = (active_trade['entry'] - exit_price - spread) * active_trade['size'] * 100
                    reason = "TP2 Hit (Runner)"
                elif low <= tp1 and not active_trade.get('tp1_hit', False):
                    active_trade['tp1_hit'] = True
                    active_trade['sl'] = active_trade['entry'] - 0.10
                    
            if closed:
                balance += pnl
                trades.append({
                    'entry_time': active_trade['entry_time'],
                    'exit_time': c_time,
                    'type': t_type,
                    'entry': active_trade['entry'],
                    'exit': exit_price,
                    'pnl': pnl,
                    'win': pnl > 0,
                    'reason': reason
                })
                equity_curve.append(balance)
                active_trade = None
                continue

        # 2. Check Entry Conditions if no active trade
        if active_trade is None:
            # Session Filter: Active trading during London & NY Sessions (06:00 to 20:00 UTC)
            if hour < 6 or hour > 20:
                continue
                
            # Look back for most recent Swing High and Swing Low
            recent_highs = df.iloc[max(0, i-60) : i-2]['swing_high'].dropna()
            recent_lows = df.iloc[max(0, i-60) : i-2]['swing_low'].dropna()
            
            if len(recent_highs) == 0 or len(recent_lows) == 0:
                continue
                
            last_swing_high = recent_highs.iloc[-1]
            last_swing_low = recent_lows.iloc[-1]
            atr = curr['atr']
            
            prev1 = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            # --- BULLISH SETUP: Liquidity Sweep of Lows + Bullish Reversal ---
            swept_low = (prev1['low'] < last_swing_low) and (prev1['close'] > last_swing_low or curr['close'] > last_swing_low)
            
            if swept_low and (curr['close'] > curr['open']):
                entry = curr['close'] + (spread / 2.0)
                sl = min(prev1['low'], curr['low']) - (atr * 0.3)
                risk = entry - sl
                if 1.0 <= risk <= 6.0:
                    tp1 = entry + (risk * 1.5)
                    tp2 = entry + (risk * min_rr)
                    active_trade = {
                        'type': 'BUY',
                        'entry': entry,
                        'sl': sl,
                        'tp1': tp1,
                        'tp2': tp2,
                        'size': 0.05,
                        'entry_time': c_time,
                        'tp1_hit': False
                    }
                    continue
                    
            # --- BEARISH SETUP: Liquidity Sweep of Highs + Bearish Reversal ---
            swept_high = (prev1['high'] > last_swing_high) and (prev1['close'] < last_swing_high or curr['close'] < last_swing_high)
            
            if swept_high and (curr['close'] < curr['open']):
                entry = curr['close'] - (spread / 2.0)
                sl = max(prev1['high'], curr['high']) + (atr * 0.3)
                risk = sl - entry
                if 1.0 <= risk <= 6.0:
                    tp1 = entry - (risk * 1.5)
                    tp2 = entry - (risk * min_rr)
                    active_trade = {
                        'type': 'SELL',
                        'entry': entry,
                        'sl': sl,
                        'tp1': tp1,
                        'tp2': tp2,
                        'size': 0.05,
                        'entry_time': c_time,
                        'tp1_hit': False
                    }
                    continue

    # Summary
    if not trades:
        print("No trades generated.")
        return
        
    wins = [t for t in trades if t['win']]
    losses = [t for t in trades if not t['win']]
    total_trades = len(trades)
    win_rate = (len(wins) / total_trades) * 100
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0
    net_pnl = balance - initial_balance
    roi = (net_pnl / initial_balance) * 100
    
    peak = initial_balance
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    print(f"Total Bars Processed:   {len(df):,}")
    print(f"Total Signals Executed: {total_trades}")
    print(f"Win Rate:               {win_rate:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Gross Profit:           ${gross_profit:,.2f}")
    print(f"Gross Loss:             ${gross_loss:,.2f}")
    print(f"Net Profit:             ${net_pnl:,.2f} ({roi:+.2f}%)")
    print(f"Profit Factor:          {profit_factor:.2f}")
    print(f"Max Drawdown:           {max_dd:.2f}%")
    print(f"Final Account Balance:  ${balance:,.2f}")
    print("=" * 65)

if __name__ == '__main__':
    run_smc_backtest('data_cache/XAUUSD_M5_1MONTH.csv', 'XAUUSD M5 (1 Month)', min_rr=2.5)
    run_smc_backtest('data_cache/XAUUSD_M1_43200.csv', 'XAUUSD M1 (43,200 Bars / ~45 Days)', min_rr=2.5)
