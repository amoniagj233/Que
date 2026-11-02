import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone

def session_breakdown():
    mt5.initialize()
    rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, datetime(2026, 10, 27, 0, 0, 0), datetime(2026, 10, 27, 23, 59, 59))
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # 5-bar fractal swing pivots
    half = 2
    swing_highs = []
    swing_lows = []
    
    for i in range(half, len(df) - half):
        curr_h = df['high'].iloc[i]
        curr_l = df['low'].iloc[i]
        if all(df['high'].iloc[i-j] < curr_h and df['high'].iloc[i+j] < curr_h for j in range(1, half+1)):
            swing_highs.append({'time': df['time'].iloc[i], 'price': curr_h, 'idx': i})
        if all(df['low'].iloc[i-j] > curr_l and df['low'].iloc[i+j] > curr_l for j in range(1, half+1)):
            swing_lows.append({'time': df['time'].iloc[i], 'price': curr_l, 'idx': i})

    df_sh = pd.DataFrame(swing_highs)
    df_sl = pd.DataFrame(swing_lows)

    # Label HH / LH
    df_sh['type'] = 'LH'
    for i in range(1, len(df_sh)):
        if df_sh['price'].iloc[i] > df_sh['price'].iloc[i-1]:
            df_sh.loc[df_sh.index[i], 'type'] = 'HH'
        elif df_sh['price'].iloc[i] == df_sh['price'].iloc[i-1]:
            df_sh.loc[df_sh.index[i], 'type'] = 'EH'

    # Label LL / HL
    df_sl['type'] = 'HL'
    for i in range(1, len(df_sl)):
        if df_sl['price'].iloc[i] < df_sl['price'].iloc[i-1]:
            df_sl.loc[df_sl.index[i], 'type'] = 'LL'
        elif df_sl['price'].iloc[i] == df_sl['price'].iloc[i-1]:
            df_sl.loc[df_sl.index[i], 'type'] = 'EL'

    sessions = [
        ("Asian Session", "00:00:00", "07:00:00"),
        ("London Morning / The Dump to Day Low", "07:00:00", "10:00:00"),
        ("London-NY Overlap / 4000 Breakout", "10:00:00", "15:00:00"),
        ("NY Expansion / Runaway Trend to High", "15:00:00", "23:00:00"),
    ]

    print("=== SESSION-BY-SESSION MARKET STRUCTURE (5-BAR FRACTAL) ===")
    for name, s_time, e_time in sessions:
        s_dt = pd.to_datetime(f"2026-10-27 {s_time}")
        e_dt = pd.to_datetime(f"2026-10-27 {e_time}")
        
        sub_c = df[(df['time'] >= s_dt) & (df['time'] < e_dt)]
        if len(sub_c) == 0:
            continue
            
        sh_sub = df_sh[(df_sh['time'] >= s_dt) & (df_sh['time'] < e_dt)]
        sl_sub = df_sl[(df_sl['time'] >= s_dt) & (df_sl['time'] < e_dt)]
        
        hh = (sh_sub['type'] == 'HH').sum()
        lh = (sh_sub['type'] == 'LH').sum()
        ll = (sl_sub['type'] == 'LL').sum()
        hl = (sl_sub['type'] == 'HL').sum()
        
        low_p = sub_c['low'].min()
        high_p = sub_c['high'].max()
        open_p = sub_c['open'].iloc[0]
        close_p = sub_c['close'].iloc[-1]
        
        print(f"\n[{name}] ({s_time[:5]} - {e_time[:5]})")
        print(f"  Range: {open_p:.2f} -> {close_p:.2f} (Low: {low_p:.2f}, High: {high_p:.2f}, Diff: ${high_p - low_p:.2f})")
        print(f"  Swing Highs: {len(sh_sub)} -> Higher Highs (HH): {hh} | Lower Highs (LH): {lh}")
        print(f"  Swing Lows:  {len(sl_sub)} -> Lower Lows (LL): {ll}   | Higher Lows (HL): {hl}")
        dominant = "BULLISH EXPANSION" if hh > lh and hl >= ll else ("BEARISH DOWNTREND" if ll > hl and lh >= hh else "CHOP / CONSOLIDATION")
        print(f"  Dominant Structure: {dominant}")

    mt5.shutdown()

if __name__ == "__main__":
    session_breakdown()
