import MetaTrader5 as mt5
import numpy as np
import time

def test_engine():
    if not mt5.initialize():
        print("MT5 init failed")
        return
        
    symbols = ["BTC", "DOGE", "SOL", "ETH", "XAUUSD", "EURUSD"]
    
    CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "LTC", "BTCUSD", "ETHUSD"}
    METALS_SYMBOLS = {"XAUUSD", "XAGUSD"}
    FOREX_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"}
    
    for sym in symbols:
        info = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        if not info or not tick:
            print(f"{sym}: No quote")
            continue
            
        cur_p = (tick.bid + tick.ask) / 2.0
        digits = info.digits
        point = info.point or (10 ** -digits)
        
        rates_m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 30)
        rates_h1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 30)
        
        m15_atr = 0.0
        if rates_m15 is not None and len(rates_m15) >= 14:
            tr = np.maximum(rates_m15['high'][1:] - rates_m15['low'][1:], np.abs(rates_m15['high'][1:] - rates_m15['close'][:-1]))
            tr = np.maximum(tr, np.abs(rates_m15['low'][1:] - rates_m15['close'][:-1]))
            m15_atr = float(np.mean(tr[-14:]))
            
        h1_atr = 0.0
        if rates_h1 is not None and len(rates_h1) >= 14:
            tr = np.maximum(rates_h1['high'][1:] - rates_h1['low'][1:], np.abs(rates_h1['high'][1:] - rates_h1['close'][:-1]))
            tr = np.maximum(tr, np.abs(rates_h1['low'][1:] - rates_h1['close'][:-1]))
            h1_atr = float(np.mean(tr[-14:]))
            
        spread = tick.ask - tick.bid
        min_broker = max(info.trade_stops_level * point, spread * 1.5, point * 50)
        
        # New Robust Stop Distance Formula
        if sym in CRYPTO_SYMBOLS:
            # Minimum 2.0% price distance or 2.5x H1 ATR
            dist = max(cur_p * 0.020, h1_atr * 2.2, m15_atr * 2.5, min_broker)
        elif sym in METALS_SYMBOLS:
            # Minimum $5.00/oz for Gold or 2.0x H1 ATR
            dist = max(5.00, h1_atr * 2.0, m15_atr * 2.2, min_broker)
        elif sym in FOREX_SYMBOLS:
            # Minimum 28 pips or 1.8x H1 ATR
            dist = max(point * 280, h1_atr * 1.8, min_broker)
        else:
            dist = max(cur_p * 0.012, h1_atr * 2.0, m15_atr * 2.2, min_broker)
            
        dist_pct = (dist / cur_p) * 100
        print(f"[{sym}] Price: {cur_p:.{digits}f} | Old M15 Range Stop: ~{m15_atr*1.5:.{digits}f} | NEW Robust Stop: {dist:.{digits}f} ({dist_pct:.2f}%) | H1 ATR: {h1_atr:.{digits}f}")
        
    mt5.shutdown()

if __name__ == "__main__":
    test_engine()
