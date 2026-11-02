"""
========================================================================================
🚀 TEST TRADE EXECUTOR FOR THE OTHER BOTS
1. GoldAutoTrader / SmartProfitChaser (Magic 7777)
2. ML Trading Intelligence Engine (Magic 8888)
3. Academic MA 44 / 332 Engine (Magic 6666)
4. XTO Speeder / Tradivo EA Suite (Magic 10101)
========================================================================================
"""

import sys
import os
import time
from datetime import datetime
import MetaTrader5 as mt5

TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD"

OTHER_BOTS = [
    {"name": "GoldAutoTrader_SmartChaser", "magic": 7777, "dir": "BUY", "lot": 0.01},
    {"name": "ML_Intelligence_Engine",    "magic": 8888, "dir": "BUY", "lot": 0.01},
    {"name": "Academic_MA44_332_Bot",     "magic": 6666, "dir": "BUY", "lot": 0.01},
    {"name": "XTO_Speeder_Tradivo",       "magic": 10101, "dir": "BUY", "lot": 0.01},
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"[{ts}] [OTHER-BOTS-TEST] {clean}")

def main():
    log("=" * 70)
    log("[START] OPENING TEST TRADES FOR ALL OTHER BOTS ON HEADWAY MT5")
    log("=" * 70)
    
    if not mt5.initialize():
        if not mt5.initialize(path=TERMINAL_PATH):
            log("[FAIL] MT5 failed to initialize.")
            sys.exit(1)
            
    info = mt5.account_info()
    log(f"Connected to Headway MT5 | Account: {info.login} | Balance: ${info.balance:,.2f} | Equity: ${info.equity:,.2f}")
    
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        log("[FAIL] Could not get tick for Gold.")
        sys.exit(1)
        
    opened_tickets = []
    
    for b in OTHER_BOTS:
        action_type = mt5.ORDER_TYPE_BUY if b['dir'] == 'BUY' else mt5.ORDER_TYPE_SELL
        price = tick.ask if b['dir'] == 'BUY' else tick.bid
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": b['lot'],
            "type": action_type,
            "price": price,
            "sl": 0.0,
            "tp": round(price + 1.20, 2), # Quick test TP
            "deviation": 20,
            "magic": b['magic'],
            "comment": f"Test_{b['magic']}"[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            req["type_filling"] = mt5.ORDER_FILLING_FOK
            res = mt5.order_send(req)
            
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"[OK] [TEST OPENED] {b['name']} (Magic {b['magic']}) | {b['dir']} {b['lot']} @ {price:.2f} | Ticket #{res.order}")
            opened_tickets.append((b['magic'], b['name'], res.order))
        else:
            log(f"[FAIL] {b['name']} (Magic {b['magic']}): {res.comment}")
        time.sleep(1)
        
    log("=" * 70)
    log(f"TOTAL TEST TRADES OPENED: {len(opened_tickets)}")
    log("=" * 70)
    mt5.shutdown()

if __name__ == '__main__':
    main()
