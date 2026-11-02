import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone

def fetch_and_analyze():
    if not mt5.initialize():
        path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
        if not mt5.initialize(path=path):
            print("MT5 Init Failed:", mt5.last_error())
            return

    # Yesterday: 2026-10-27 00:00:00 to 2026-10-27 23:59:59 UTC
    start_dt = datetime(2026, 10, 27, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 10, 27, 23, 59, 59, tzinfo=timezone.utc)

    rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, start_dt, end_dt)
    if rates is None or len(rates) == 0:
        print("No rates returned for XAUUSD on 2026-10-27 via UTC. Checking broker time...")
        # Try local time without tzinfo
        rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, datetime(2026, 10, 27, 0, 0, 0), datetime(2026, 10, 27, 23, 59, 59))

    if rates is None or len(rates) == 0:
        print("Still no rates. Last error:", mt5.last_error())
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"Total M1 Candles fetched for 2026-10-27: {len(df)}")
    print(f"Start: {df['time'].iloc[0]} | End: {df['time'].iloc[-1]}")
    print(f"Open: {df['open'].iloc[0]:.2f} | High: {df['high'].max():.2f} | Low: {df['low'].min():.2f} | Close: {df['close'].iloc[-1]:.2f}")
    print(f"Total Daily Range: ${df['high'].max() - df['low'].min():.2f}")

    # Identify Swing Highs and Swing Lows
    # Using classic 3-bar and 5-bar swing pivot definition:
    # A swing high at index i has high[i] > high[i-1] and high[i] > high[i+1] (for 3-bar)
    # or high[i] > high[i-2], high[i-1], high[i+1], high[i+2] (for 5-bar fractal)
    
    for n_bars in [3, 5]:
        half = n_bars // 2
        df_sw = df.copy()
        
        swing_highs = []
        swing_lows = []
        
        for i in range(half, len(df_sw) - half):
            is_sh = True
            is_sl = True
            curr_h = df_sw['high'].iloc[i]
            curr_l = df_sw['low'].iloc[i]
            
            for j in range(1, half + 1):
                if df_sw['high'].iloc[i - j] >= curr_h or df_sw['high'].iloc[i + j] >= curr_h:
                    is_sh = False
                if df_sw['low'].iloc[i - j] <= curr_l or df_sw['low'].iloc[i + j] <= curr_l:
                    is_sl = False
                    
            if is_sh:
                swing_highs.append((df_sw['time'].iloc[i], curr_h, i))
            if is_sl:
                swing_lows.append((df_sw['time'].iloc[i], curr_l, i))
                
        # Classify Higher Highs (HH) vs Lower Highs (LH)
        hh_count = 0
        lh_count = 0
        equal_h_count = 0
        prev_sh = None
        hh_list = []
        
        for t, h, idx in swing_highs:
            if prev_sh is not None:
                if h > prev_sh:
                    hh_count += 1
                    hh_list.append((t, h, prev_sh, h - prev_sh))
                elif h < prev_sh:
                    lh_count += 1
                else:
                    equal_h_count += 1
            prev_sh = h
            
        # Classify Lower Lows (LL) vs Higher Lows (HL)
        ll_count = 0
        hl_count = 0
        equal_l_count = 0
        prev_sl = None
        ll_list = []
        
        for t, l, idx in swing_lows:
            if prev_sl is not None:
                if l < prev_sl:
                    ll_count += 1
                    ll_list.append((t, l, prev_sl, prev_sl - l))
                elif l > prev_sl:
                    hl_count += 1
                else:
                    equal_l_count += 1
            prev_sl = l

        print(f"\n--- {n_bars}-BAR PIVOT STRUCTURE ANALYSIS ---")
        print(f"Total Swing Highs: {len(swing_highs)}")
        print(f"  • Higher Highs (HH): {hh_count}")
        print(f"  • Lower Highs (LH):  {lh_count}")
        print(f"Total Swing Lows:  {len(swing_lows)}")
        print(f"  • Lower Lows (LL):   {ll_count}")
        print(f"  • Higher Lows (HL):  {hl_count}")

    mt5.shutdown()

if __name__ == "__main__":
    fetch_and_analyze()
