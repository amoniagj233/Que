import pandas as pd
import numpy as np

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def backtest_tiktalk(data_path, timeframe_name="M5", spread=0.35):
    print(f"\n==========================================")
    print(f"[TEST] BACKTESTING 'TikTalk' (EMA 9/21 + RSI 14) on {timeframe_name}")
    print(f"==========================================")
    df = pd.read_csv(data_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    fast_ema = 9
    slow_ema = 21
    rsi_period = 14
    stop_loss_pct = 0.02
    take_profit_pct = 0.04
    
    df['ema_fast'] = df['close'].ewm(span=fast_ema, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow_ema, adjust=False).mean()
    df['rsi'] = calculate_rsi(df['close'], period=rsi_period)
    
    initial_balance = 1000.0
    balance = initial_balance
    equity_curve = [balance]
    trades = []
    
    position = 0 # 0: None, 1: Long
    entry_price = 0.0
    entry_idx = 0
    trade_size_oz = 0.1 # 0.1 lot gold
    
    for i in range(25, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        price = curr['close']
        
        # Check active position exit
        if position == 1:
            pnl_pct = (price - entry_price) / entry_price
            exit_reason = None
            
            # SL / TP
            if pnl_pct <= -stop_loss_pct:
                exit_reason = "Stop Loss (-2%)"
            elif pnl_pct >= take_profit_pct:
                exit_reason = "Take Profit (+4%)"
            elif prev['ema_fast'] >= prev['ema_slow'] and curr['ema_fast'] < curr['ema_slow']:
                exit_reason = "Death Cross (EMA 9 < 21)"
            elif curr['rsi'] >= 75:
                exit_reason = "RSI Overbought (>=75)"
                
            if exit_reason:
                dollar_pnl = (price - entry_price - spread) * trade_size_oz * 100 # 100 oz per full lot
                balance += dollar_pnl
                trades.append({
                    'entry_time': df.iloc[entry_idx]['time'],
                    'exit_time': curr['time'],
                    'entry': entry_price,
                    'exit': price,
                    'pnl': dollar_pnl,
                    'reason': exit_reason,
                    'win': dollar_pnl > 0
                })
                position = 0
                equity_curve.append(balance)
                continue
                
        # Entry check
        if position == 0:
            bullish_cross = (prev['ema_fast'] <= prev['ema_slow']) and (curr['ema_fast'] > curr['ema_slow'])
            if (bullish_cross and curr['rsi'] < 70) or (curr['rsi'] <= 30):
                position = 1
                entry_price = price + (spread / 2.0)
                entry_idx = i

    # Analysis
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
    
    # Max DD
    peak = initial_balance
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    print(f"Total Bars Tested: {len(df):,}")
    print(f"Total Trades:      {total_trades}")
    print(f"Win Rate:          {win_rate:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Gross Profit:      ${gross_profit:,.2f}")
    print(f"Gross Loss:        ${gross_loss:,.2f}")
    print(f"Net Profit:        ${net_pnl:,.2f} ({roi:+.2f}%)")
    print(f"Profit Factor:     {profit_factor:.2f}")
    print(f"Max Drawdown:      {max_dd:.2f}%")
    print(f"Final Balance:     ${balance:,.2f}")
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'net_pnl': net_pnl,
        'profit_factor': profit_factor,
        'max_dd': max_dd
    }

if __name__ == '__main__':
    # Test on M5
    backtest_tiktalk('data_cache/XAUUSD_M5_1MONTH.csv', 'XAUUSD M5 (1 Month)')
    # Test on M1
    backtest_tiktalk('data_cache/XAUUSD_M1_43200.csv', 'XAUUSD M1 (43,200 Bars / ~45 Days)')
