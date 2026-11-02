import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

def compute_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean().bfill()

def run_backtest_for_tf(rates_df, tf_name, base_lot=0.01, target_tp=3.50, max_loss=25.00, max_layers=3):
    df = rates_df.copy()
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['atr'] = compute_atr(df, period=14)
    
    half = 2 # 5-bar fractal (2 before, 2 after)
    n = len(df)
    
    # Precompute swing highs and lows
    is_sh = np.zeros(n, dtype=bool)
    is_sl = np.zeros(n, dtype=bool)
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    opens = df['open'].values
    atrs = df['atr'].values
    
    for i in range(half, n - half):
        curr_h = highs[i]
        curr_l = lows[i]
        if all(highs[i-j] < curr_h and highs[i+j] < curr_h for j in range(1, half+1)):
            is_sh[i] = True
        if all(lows[i-j] > curr_l and lows[i+j] > curr_l for j in range(1, half+1)):
            is_sl[i] = True

    # Simulation state
    cycles = []
    active_basket = None # list of {side, vol, price}
    active_inv_level = None
    
    recent_sh = []
    recent_sl = []
    
    for i in range(10, n):
        # Update swing pivots known up to bar i-half (no lookahead bias!)
        eval_bar = i - half
        if is_sh[eval_bar]:
            recent_sh.append(highs[eval_bar])
            if len(recent_sh) > 4:
                recent_sh.pop(0)
        if is_sl[eval_bar]:
            recent_sl.append(lows[eval_bar])
            if len(recent_sl) > 4:
                recent_sl.pop(0)
                
        # Determine structure regime
        regime = "CHOP"
        allowed_side = None
        inv_level = None
        
        if len(recent_sh) >= 2 and len(recent_sl) >= 2:
            is_hh = recent_sh[-1] > recent_sh[-2]
            is_hl = recent_sl[-1] > recent_sl[-2]
            is_ll = recent_sl[-1] < recent_sl[-2]
            is_lh = recent_sh[-1] < recent_sh[-2]
            
            if is_hh and is_hl:
                regime = "BULLISH"
                allowed_side = "BUY"
                inv_level = recent_sl[-1] - 0.50
            elif is_ll and is_lh:
                regime = "BEARISH"
                allowed_side = "SELL"
                inv_level = recent_sh[-1] + 0.50
                
        curr_open = opens[i]
        curr_high = highs[i]
        curr_low = lows[i]
        curr_close = closes[i]
        curr_atr = atrs[i]
        
        # 1. Manage Active Basket
        if active_basket is not None:
            side = active_basket[0]['side']
            
            # Check worst and best case on this bar
            # PnL function: For Gold, 0.01 lot = $1.00 per $1.00 move
            def calc_pnl(eval_p):
                total_p = 0.0
                for order in active_basket:
                    if order['side'] == 'BUY':
                        total_p += (eval_p - order['price']) * (order['vol'] * 100.0)
                    else:
                        total_p += (order['price'] - eval_p) * (order['vol'] * 100.0)
                return total_p

            # Check if Target TP is reached on this candle
            best_p = curr_high if side == 'BUY' else curr_low
            best_pnl = calc_pnl(best_p)
            
            # Check if Invalidation SL is reached on this candle
            worst_p = curr_low if side == 'BUY' else curr_high
            worst_pnl = calc_pnl(worst_p)
            
            # Take Profit hit?
            if best_pnl >= target_tp:
                cycles.append({
                    'result': 'WIN',
                    'pnl': target_tp,
                    'layers': len(active_basket),
                    'duration': i - active_basket[0]['entry_idx'],
                    'reason': 'TP_HIT'
                })
                active_basket = None
                active_inv_level = None
                continue
                
            # Invalidation Stop hit?
            is_inv_hit = False
            if active_inv_level is not None:
                if side == 'BUY' and curr_low <= active_inv_level:
                    is_inv_hit = True
                elif side == 'SELL' and curr_high >= active_inv_level:
                    is_inv_hit = True
                    
            if is_inv_hit or worst_pnl <= -max_loss:
                loss_amt = max(-max_loss, calc_pnl(active_inv_level if is_inv_hit else worst_p))
                cycles.append({
                    'result': 'LOSS',
                    'pnl': loss_amt,
                    'layers': len(active_basket),
                    'duration': i - active_basket[0]['entry_idx'],
                    'reason': 'INVALIDATION' if is_inv_hit else 'MAX_LOSS'
                })
                active_basket = None
                active_inv_level = None
                continue
                
            # Check if we should add another layer
            if len(active_basket) < max_layers:
                last_entry = active_basket[-1]['price']
                dist = abs(curr_close - last_entry)
                min_dist = max(1.50, curr_atr * 1.0)
                
                is_pullback = (side == 'BUY' and curr_close <= last_entry - min_dist) or \
                              (side == 'SELL' and curr_close >= last_entry + min_dist)
                              
                # Reversal candle check
                is_bounce = (side == 'BUY' and curr_close > curr_open) or \
                            (side == 'SELL' and curr_close < curr_open)
                            
                if is_pullback and is_bounce:
                    layer_lots = [0.01, 0.01, 0.02]
                    next_vol = layer_lots[len(active_basket)]
                    active_basket.append({
                        'side': side,
                        'vol': next_vol,
                        'price': curr_close,
                        'entry_idx': i
                    })
                    
        # 2. Open New Basket (if flat and clean structure exists)
        else:
            if allowed_side is not None and inv_level is not None:
                # Candle alignment
                is_aligned = (allowed_side == 'BUY' and curr_close >= curr_open) or \
                             (allowed_side == 'SELL' and curr_close <= curr_open)
                if is_aligned:
                    active_basket = [{
                        'side': allowed_side,
                        'vol': base_lot,
                        'price': curr_close,
                        'entry_idx': i
                    }]
                    active_inv_level = inv_level

    # Performance Stats
    if not cycles:
        return None
        
    df_c = pd.DataFrame(cycles)
    wins = (df_c['result'] == 'WIN').sum()
    losses = (df_c['result'] == 'LOSS').sum()
    win_rate = (wins / len(df_c)) * 100.0
    
    total_gain = df_c[df_c['pnl'] > 0]['pnl'].sum()
    total_loss = abs(df_c[df_c['pnl'] < 0]['pnl'].sum())
    net_pnl = df_c['pnl'].sum()
    profit_factor = (total_gain / total_loss) if total_loss > 0 else 999.0
    
    # Cumulative drawdown
    cum_pnl = df_c['pnl'].cumsum()
    peak = cum_pnl.cummax()
    dd = peak - cum_pnl
    max_dd = dd.max() if len(dd) > 0 else 0.0
    avg_layers = df_c['layers'].mean()
    
    return {
        'timeframe': tf_name,
        'total_cycles': len(df_c),
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 1),
        'net_pnl': round(net_pnl, 2),
        'total_gain': round(total_gain, 2),
        'total_loss': round(total_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown': round(max_dd, 2),
        'avg_layers': round(avg_layers, 2)
    }

def main():
    if not mt5.initialize():
        path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
        if not mt5.initialize(path=path):
            print("MT5 Init Failed:", mt5.last_error())
            return

    # Backtest across 5 timeframes over the last 14 days of market data
    tfs = [
        ("M1", mt5.TIMEFRAME_M1, 10000),
        ("M5", mt5.TIMEFRAME_M5, 4000),
        ("M15", mt5.TIMEFRAME_M15, 2000),
        ("M30", mt5.TIMEFRAME_M30, 1000),
        ("H1", mt5.TIMEFRAME_H1, 800)
    ]
    
    results = []
    print("=" * 80)
    print("      STRUCTUREGRID PRO : MULTI-TIMEFRAME BACKTEST COMPARISON (XAUUSD)")
    print("=" * 80)
    
    for name, tf_const, count in tfs:
        rates = mt5.copy_rates_from_pos("XAUUSD", tf_const, 0, count)
        if rates is None or len(rates) == 0:
            print(f"[!] Could not fetch data for {name}")
            continue
            
        rates_df = pd.DataFrame(rates)
        res = run_backtest_for_tf(rates_df, name)
        if res:
            results.append(res)
            print(f"[{name}] Tested {len(rates_df)} bars | Cycles: {res['total_cycles']} | Win Rate: {res['win_rate']}% | Net: ${res['net_pnl']} | PF: {res['profit_factor']} | Max DD: ${res['max_drawdown']}")

    mt5.shutdown()
    
    print("\n" + "=" * 80)
    print("                         FINAL RANKINGS & SUMMARY")
    print("=" * 80)
    
    # Sort by Profit Factor and Net PnL
    results.sort(key=lambda x: (x['profit_factor'], x['net_pnl']), reverse=True)
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))

if __name__ == "__main__":
    main()
