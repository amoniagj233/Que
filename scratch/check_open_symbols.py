import sys, os
sys.path.insert(0, os.path.abspath('.'))
import MetaTrader5 as mt5
from web_app import check_symbol_market_open

if mt5.initialize():
    syms = ["VOL_20", "BOOM_100", "CRASH_100", "ETH", "BTC", "VOL_10", "SOL", "DOGE", "XRP", "ADA", "LTC", "XAUUSD", "EURUSD"]
    for s in syms:
        is_open, reason = check_symbol_market_open(s)
        if is_open:
            print(f"[OPEN] {s}")
        else:
            print(f"[CLOSED] {s}: {reason}")
    mt5.shutdown()
