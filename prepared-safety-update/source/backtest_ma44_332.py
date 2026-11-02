"""
Backtest Engine for Academic MA 44 / 332 Strategy on XAUUSD (Gold) M5
Compares:
1. Video Raw Academic Crossover (Always-in, no SL)
2. Video Version with Yesterday's High/Low Stop Loss ($100 Risk)
3. Headway Friction Applied ($3.80/oz spread, $0.20 slippage, swap)
4. Engineered Hybrid (24h Trend Filter + London/NY Session + ATR Stop)
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Load data
df = pd.read_csv("data_cache/XAUUSD_M5_1MONTH.csv")
df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time').reset_index(drop=True)

# Compute indicators
df['ma44'] = df['close'].rolling(window=44).mean()
df['ma332'] = df['close'].rolling(window=332).mean()

# True Range & ATR
high_low = df['high'] - df['low']
high_close = (df['high'] - df['close'].shift()).abs()
low_close = (df['low'] - df['close'].shift()).abs()
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr14'] = tr.rolling(window=14).mean()

# Extract Date for Daily High/Low
df['date'] = df['time'].dt.date
daily_hl = df.groupby('date').agg({'high': 'max', 'low': 'min'}).shift(1)
df['prev_day_high'] = df['date'].map(daily_hl['high'])
df['prev_day_low'] = df['date'].map(daily_hl['low'])

# Crossover signals (bar close confirmed)
df['bullish_cross'] = (df['ma44'] > df['ma332']) & (df['ma44'].shift(1) <= df['ma332'].shift(1))
df['bearish_cross'] = (df['ma44'] < df['ma332']) & (df['ma44'].shift(1) >= df['ma332'].shift(1))

SPREAD_USD = 3.80     # Headway average Gold spread per oz ($3.80)
SLIPPAGE_USD = 0.20   # Execution slippage per oz ($0.20)
TOTAL_FRICTION = SPREAD_USD + SLIPPAGE_USD
SWAP_DAILY_PCT = 0.03 / 365 # ~3% annual financing swap rate

def backtest_raw_academic(df_in, use_friction=True):
    """Exact Paper: Flip on crossover, always in market, no stop loss."""
    position = 0 # +1 Long, -1 Short
    entry_price = 0.0
    entry_time = None
    trades = []
    
    for i in range(333, len(df_in)):
        row = df_in.iloc[i]
        
        # Bullish cross -> Buy / Flip to Long
        if row['bullish_cross']:
            if position == -1: # Close Short
                exit_price = row['close']
                pnl = (entry_price - exit_price) # points/usd per oz
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'SELL', 'pnl': pnl, 'entry': entry_price, 'exit': exit_price, 'entry_time': entry_time, 'exit_time': row['time']})
            position = 1
            entry_price = row['close']
            entry_time = row['time']
            
        elif row['bearish_cross']:
            if position == 1: # Close Long
                exit_price = row['close']
                pnl = (exit_price - entry_price)
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'BUY', 'pnl': pnl, 'entry': entry_price, 'exit': exit_price, 'entry_time': entry_time, 'exit_time': row['time']})
            position = -1
            entry_price = row['close']
            entry_time = row['time']
            
    return summarize_trades("1. Raw Academic Crossover (Always-In)", trades, fixed_lot=0.05)


def backtest_video_with_sl(df_in, use_friction=True):
    """Video Rule: MA 44/332 cross, SL = prev day low/high, wait for next cross if stopped."""
    position = 0 # 0 none, 1 long, -1 short
    entry_price = 0.0
    stop_loss = 0.0
    entry_time = None
    trades = []
    
    for i in range(333, len(df_in)):
        row = df_in.iloc[i]
        
        # Check Stop Loss if in trade
        if position == 1:
            if row['low'] <= stop_loss: # Stopped out
                exit_price = stop_loss
                pnl = (exit_price - entry_price)
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'BUY', 'pnl': pnl, 'result': 'SL', 'entry': entry_price, 'exit': exit_price})
                position = 0
            elif row['bearish_cross']: # Opposite cross exit
                exit_price = row['close']
                pnl = (exit_price - entry_price)
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'BUY', 'pnl': pnl, 'result': 'CROSS', 'entry': entry_price, 'exit': exit_price})
                position = -1
                entry_price = row['close']
                entry_time = row['time']
                stop_loss = row['prev_day_high'] if pd.notna(row['prev_day_high']) else entry_price + 20.0
                
        elif position == -1:
            if row['high'] >= stop_loss: # Stopped out
                exit_price = stop_loss
                pnl = (entry_price - exit_price)
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'SELL', 'pnl': pnl, 'result': 'SL', 'entry': entry_price, 'exit': exit_price})
                position = 0
            elif row['bullish_cross']: # Opposite cross exit
                exit_price = row['close']
                pnl = (entry_price - exit_price)
                if use_friction:
                    pnl -= TOTAL_FRICTION
                    days = (row['time'] - entry_time).total_seconds() / 86400
                    pnl -= (entry_price * SWAP_DAILY_PCT * days)
                trades.append({'type': 'SELL', 'pnl': pnl, 'result': 'CROSS', 'entry': entry_price, 'exit': exit_price})
                position = 1
                entry_price = row['close']
                entry_time = row['time']
                stop_loss = row['prev_day_low'] if pd.notna(row['prev_day_low']) else entry_price - 20.0

        else: # Out of position, wait for fresh cross
            if row['bullish_cross'] and pd.notna(row['prev_day_low']):
                position = 1
                entry_price = row['close']
                entry_time = row['time']
                stop_loss = row['prev_day_low']
            elif row['bearish_cross'] and pd.notna(row['prev_day_high']):
                position = -1
                entry_price = row['close']
                entry_time = row['time']
                stop_loss = row['prev_day_high']

    return summarize_trades("2. Video Strategy (+ Prev Day H/L Stop)", trades, fixed_lot=0.05)


def backtest_engineered_hybrid(df_in):
    """
    Engineered Hybrid for Gold:
    - 24h Baseline Filter (MA 332 slope / trend)
    - Active Session only: 07:00 to 19:00 UTC (London + NY overlap, avoiding dead spread hours)
    - Dynamic ATR Stop (1.8x ATR) & 2.5x ATR Take Profit (R:R 1.4+)
    - No overnight rollover held past 21:00 UTC
    """
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    trades = []
    
    for i in range(333, len(df_in)):
        row = df_in.iloc[i]
        hour = row['time'].hour
        is_active_session = 7 <= hour <= 19
        
        # Manage open trade
        if position == 1:
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) - TOTAL_FRICTION
                trades.append({'type': 'BUY', 'pnl': pnl, 'result': 'SL'})
                position = 0
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) - TOTAL_FRICTION
                trades.append({'type': 'BUY', 'pnl': pnl, 'result': 'TP'})
                position = 0
            elif hour >= 21: # End of day close
                pnl = (row['close'] - entry_price) - TOTAL_FRICTION
                trades.append({'type': 'BUY', 'pnl': pnl, 'result': 'SESSION_CLOSE'})
                position = 0
                
        elif position == -1:
            if row['high'] >= stop_loss:
                pnl = (entry_price - stop_loss) - TOTAL_FRICTION
                trades.append({'type': 'SELL', 'pnl': pnl, 'result': 'SL'})
                position = 0
            elif row['low'] <= take_profit:
                pnl = (entry_price - take_profit) - TOTAL_FRICTION
                trades.append({'type': 'SELL', 'pnl': pnl, 'result': 'TP'})
                position = 0
            elif hour >= 21: # End of day close
                pnl = (entry_price - row['close']) - TOTAL_FRICTION
                trades.append({'type': 'SELL', 'pnl': pnl, 'result': 'SESSION_CLOSE'})
                position = 0
                
        # New Entry Conditions (Active session only)
        if position == 0 and is_active_session and pd.notna(row['atr14']):
            atr = row['atr14']
            if atr < 1.0: # Skip low-volatility dead chop
                continue
                
            # Bullish: MA44 crossed above MA332 AND slope of MA332 is positive (True 24h trend)
            ma332_slope = row['ma332'] - df_in.iloc[i - 12]['ma332'] # 1 hour slope
            
            if row['bullish_cross'] and ma332_slope > 0:
                position = 1
                entry_price = row['close']
                stop_loss = entry_price - (1.8 * atr)
                take_profit = entry_price + (2.5 * atr)
                
            elif row['bearish_cross'] and ma332_slope < 0:
                position = -1
                entry_price = row['close']
                stop_loss = entry_price + (1.8 * atr)
                take_profit = entry_price - (2.5 * atr)

    return summarize_trades("3. Engineered Hybrid (24h Trend + ATR + Session)", trades, fixed_lot=0.05)


def summarize_trades(title, trades, fixed_lot=0.05):
    contract_size = 100 # oz per lot -> 0.05 lot = 5 oz
    oz = fixed_lot * contract_size
    
    if not trades:
        return f"\n=== {title} ===\nNo trades executed."
    
    df_t = pd.DataFrame(trades)
    df_t['usd_pnl'] = df_t['pnl'] * oz
    
    total_trades = len(df_t)
    wins = (df_t['usd_pnl'] > 0).sum()
    losses = (df_t['usd_pnl'] <= 0).sum()
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = df_t[df_t['usd_pnl'] > 0]['usd_pnl'].sum()
    gross_loss = abs(df_t[df_t['usd_pnl'] < 0]['usd_pnl'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    net_pnl = df_t['usd_pnl'].sum()
    
    # Cumulative Drawdown
    equity = df_t['usd_pnl'].cumsum()
    peak = equity.cummax()
    drawdown = peak - equity
    max_dd = drawdown.max()
    
    res = f"""
======================================================
  {title}
======================================================
Total Trades:       {total_trades}
Win Rate:           {win_rate:.1f}% ({wins} wins / {losses} losses)
Net P&L:            ${net_pnl:+,.2f}  (Lot size: {fixed_lot} = {oz:.0f} oz Gold)
Profit Factor:      {profit_factor:.2f}
Gross Profit:       ${gross_profit:,.2f}
Gross Loss:         ${gross_loss:,.2f}
Max Drawdown:       ${max_dd:,.2f}
"""
    return res

if __name__ == '__main__':
    print("Testing on XAUUSD M5 (Sep 16, 2026 to Oct 29, 2026)...")
    print(backtest_raw_academic(df, use_friction=True))
    print(backtest_video_with_sl(df, use_friction=True))
    print(backtest_engineered_hybrid(df))
