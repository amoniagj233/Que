"""
Multi-Strategy Backtest Comparator:
- Option A: Hybrid M30/M5 (M30 ATR Spacing + M5 Entry Triggers)
- Option B: Pure H1 Swing Grid (H1 ATR Spacing + H1 Trend & TP)
- Option C: Current M5 Scalper (M5 ATR Spacing + M5 Trend & TP)

Simulates on XAUUSD starting at $100.00 with compounding and realistic spreads.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SYMBOL = "XAUUSD"
START_BALANCE = 100.0
SPREAD_PTS = 30 # $0.30 typical gold spread
MAX_LAYERS = 3
DISASTER_SL_USD = 30.0

def get_data(num_m5=5000):
    if not mt5.initialize():
        print("MT5 Init Failed")
        return None, None, None
        
    rates_m5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, num_m5)
    rates_m30 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M30, 0, int(num_m5 / 6) + 50)
    rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, int(num_m5 / 12) + 50)
    mt5.shutdown()
    
    df_m5 = pd.DataFrame(rates_m5)
    df_m30 = pd.DataFrame(rates_m30)
    df_h1 = pd.DataFrame(rates_h1)
    
    df_m5['time_dt'] = pd.to_datetime(df_m5['time'], unit='s')
    df_m30['time_dt'] = pd.to_datetime(df_m30['time'], unit='s')
    df_h1['time_dt'] = pd.to_datetime(df_h1['time'], unit='s')
    
    # Calculate ATR and EMA for M5
    df_m5['tr'] = np.maximum(df_m5['high'] - df_m5['low'], 
                             np.maximum(abs(df_m5['high'] - df_m5['close'].shift(1)), 
                                        abs(df_m5['low'] - df_m5['close'].shift(1))))
    df_m5['atr14'] = df_m5['tr'].rolling(14).mean().fillna(1.80)
    df_m5['ema21'] = df_m5['close'].ewm(span=21, adjust=False).mean()
    df_m5['ema55'] = df_m5['close'].ewm(span=55, adjust=False).mean()
    
    # Calculate ATR and EMA for M30
    df_m30['tr'] = np.maximum(df_m30['high'] - df_m30['low'], 
                              np.maximum(abs(df_m30['high'] - df_m30['close'].shift(1)), 
                                         abs(df_m30['low'] - df_m30['close'].shift(1))))
    df_m30['atr14'] = df_m30['tr'].rolling(14).mean().fillna(3.50)
    df_m30['ema21'] = df_m30['close'].ewm(span=21, adjust=False).mean()
    df_m30['ema55'] = df_m30['close'].ewm(span=55, adjust=False).mean()
    
    # Calculate ATR and EMA for H1
    df_h1['tr'] = np.maximum(df_h1['high'] - df_h1['low'], 
                            np.maximum(abs(df_h1['high'] - df_h1['close'].shift(1)), 
                                       abs(df_h1['low'] - df_h1['close'].shift(1))))
    df_h1['atr14'] = df_h1['tr'].rolling(14).mean().fillna(6.00)
    df_h1['ema21'] = df_h1['close'].ewm(span=21, adjust=False).mean()
    df_h1['ema55'] = df_h1['close'].ewm(span=55, adjust=False).mean()
    
    return df_m5, df_m30, df_h1

def run_simulation(strategy_name, df_bars, df_m30, df_h1):
    balance = START_BALANCE
    equity = START_BALANCE
    peak_equity = START_BALANCE
    max_dd = 0.0
    
    active_basket = [] # list of dicts: {'type': 'BUY'/'SELL', 'lot': 0.01, 'open_price': float, 'layer': int}
    closed_cycles = []
    
    def get_base_lot(bal):
        if bal < 200: return 0.01
        elif bal < 400: return 0.02
        elif bal < 800: return 0.04
        elif bal < 1600: return 0.08
        else: return 0.16

    for i in range(60, len(df_bars)):
        bar = df_bars.iloc[i]
        curr_time = bar['time_dt']
        
        # Determine higher TF metrics based on strategy
        if strategy_name == "OPTION_A_HYBRID_M30_M5":
            # Match recent completed M30 bar
            m30_sub = df_m30[df_m30['time_dt'] <= curr_time]
            if len(m30_sub) < 55: continue
            last_m30 = m30_sub.iloc[-1]
            trend = 1 if last_m30['ema21'] >= last_m30['ema55'] else -1
            spacing = max(1.80, last_m30['atr14'] * 1.2)
            target_pnl = max(2.50, last_m30['atr14'] * 0.8) * (get_base_lot(balance) / 0.01)
            
        elif strategy_name == "OPTION_B_PURE_H1":
            # Bar is H1 bar
            trend = 1 if bar['ema21'] >= bar['ema55'] else -1
            spacing = max(3.50, bar['atr14'] * 1.2)
            target_pnl = max(5.00, bar['atr14'] * 1.0) * (get_base_lot(balance) / 0.01)
            
        elif strategy_name == "OPTION_C_PURE_M5":
            trend = 1 if bar['ema21'] >= bar['ema55'] else -1
            spacing = max(1.20, bar['atr14'] * 1.3)
            target_pnl = 2.50 * (get_base_lot(balance) / 0.01)

        base_lot = get_base_lot(balance)
        disaster_limit = DISASTER_SL_USD * (base_lot / 0.01)

        # Evaluate active basket
        if len(active_basket) > 0:
            b_type = active_basket[0]['type']
            total_lots = sum(p['lot'] for p in active_basket)
            vwap = sum(p['open_price'] * p['lot'] for p in active_basket) / total_lots
            worst_price = min(p['open_price'] for p in active_basket) if b_type == 'BUY' else max(p['open_price'] for p in active_basket)
            
            # Calculate PnL on bar close
            curr_price = bar['close']
            if b_type == 'BUY':
                floating_pnl = (curr_price - vwap) * total_lots * 100
                adverse_dist = worst_price - bar['low']
            else:
                floating_pnl = (vwap - curr_price) * total_lots * 100
                adverse_dist = bar['high'] - worst_price
                
            equity = balance + floating_pnl
            if equity > peak_equity: peak_equity = equity
            dd = peak_equity - equity
            if dd > max_dd: max_dd = dd
            
            # Check Take Profit
            tp_hit = (floating_pnl >= target_pnl)
            
            # Check Disaster SL
            sl_hit = (floating_pnl <= -disaster_limit)
            
            if tp_hit or sl_hit:
                balance += floating_pnl
                closed_cycles.append({
                    'type': b_type, 'pnl': floating_pnl, 'layers': len(active_basket), 
                    'win': floating_pnl > 0, 'balance': balance
                })
                active_basket = []
                continue
                
            # Check Layer Add (DCA)
            if len(active_basket) < MAX_LAYERS and adverse_dist >= spacing:
                next_layer = len(active_basket)
                layer_lot = round(base_lot * (1.5 ** next_layer), 2)
                add_price = bar['close']
                active_basket.append({
                    'type': b_type, 'lot': layer_lot, 'open_price': add_price, 'layer': next_layer + 1
                })
        else:
            # Open new Layer 1 in trend direction
            open_price = bar['close']
            pos_type = 'BUY' if trend > 0 else 'SELL'
            active_basket.append({
                'type': pos_type, 'lot': base_lot, 'open_price': open_price, 'layer': 1
            })

    total_cycles = len(closed_cycles)
    wins = [c for c in closed_cycles if c['win']]
    losses = [c for c in closed_cycles if not c['win']]
    win_rate = (len(wins) / total_cycles * 100) if total_cycles > 0 else 0
    gross_profit = sum(c['pnl'] for c in wins)
    gross_loss = abs(sum(c['pnl'] for c in losses))
    pf = (gross_profit / gross_loss) if gross_loss > 0 else 99.0
    net_profit = balance - START_BALANCE
    ret_dd = (net_profit / max_dd) if max_dd > 0 else 0.0

    return {
        'strategy': strategy_name,
        'final_balance': round(balance, 2),
        'net_profit': round(net_profit, 2),
        'total_cycles': total_cycles,
        'win_rate': round(win_rate, 1),
        'wins': len(wins),
        'losses': len(losses),
        'max_dd': round(max_dd, 2),
        'profit_factor': round(pf, 2),
        'ret_dd_ratio': round(ret_dd, 2)
    }

def main():
    print("Fetching historical multi-timeframe data for Gold (XAUUSD)...")
    df_m5, df_m30, df_h1 = get_data(5000)
    if df_m5 is None: return

    print(f"Data period: {df_m5['time_dt'].iloc[0]} -> {df_m5['time_dt'].iloc[-1]} (~{len(df_m5)/288:.1f} trading days)")
    print("\nSimulating Strategy Options A, B, and C with $100 starting balance and compounding...\n")

    res_a = run_simulation("OPTION_A_HYBRID_M30_M5", df_m5, df_m30, df_h1)
    res_b = run_simulation("OPTION_B_PURE_H1", df_h1, df_m30, df_h1)
    res_c = run_simulation("OPTION_C_PURE_M5", df_m5, df_m30, df_h1)

    results = [res_a, res_b, res_c]

    print("=" * 86)
    print(f"{'STRATEGY':<24} | {'NET PROFIT':<11} | {'FINAL BAL':<10} | {'WIN RATE':<9} | {'MAX DD':<9} | {'PF':<5} | {'RET/DD'}")
    print("-" * 86)
    for r in results:
        print(f"{r['strategy']:<24} | ${r['net_profit']:<10.2f} | ${r['final_balance']:<9.2f} | {r['win_rate']:<5.1f}% ({r['wins']}/{r['total_cycles']}) | ${r['max_dd']:<8.2f} | {r['profit_factor']:<5.2f} | {r['ret_dd_ratio']:.2f}x")
    print("=" * 86)

    with open("scratch/options_backtest_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
