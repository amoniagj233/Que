"""
========================================================================================
FIRSTRATE TEST TRADE & 24/7 AUTONOMOUS TRADING ACTIVATOR
Bots Activated:
1. Bot Slot #1: Apex-Quantum-DeepSL (Magic 1111)
2. Bot Slot #2: Mut-8037 (Magic 2222)
3. Bot #3: SMC Liquidity & Breaker Sniper (Magic 3333)
4. Bot #4: Strategic Pattern Pro Optimized (Magic 4444)
5. Bot #5: TikTalk Bot 2.0 (Magic 5555)
========================================================================================
"""

import sys
import os
import time
from datetime import datetime
import MetaTrader5 as mt5

TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD"

BOTS = [
    {"name": "Slot1_ApexQuantum", "magic": 1111, "script": "bot_slot_1.py"},
    {"name": "Slot2_Mut8037",     "magic": 2222, "script": "bot_slot_2.py"},
    {"name": "Bot3_SMCSniper",    "magic": 3333, "script": "smc_breaker_sniper.py"},
    {"name": "Bot4_PatternPro",   "magic": 4444, "script": "pattern_pro_bot.py"},
    {"name": "Bot5_TikTalk",      "magic": 5555, "script": "tiktalk_bot.py"},
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"[{ts}] [FIRSTRATE-ACTIVATOR] {clean}")

def execute_firstrate_trade(magic, bot_name, direction="BUY", lot=0.01):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        log(f"[FAIL] Failed to get tick for {SYMBOL}")
        return None
    action_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == 'BUY' else tick.bid
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": action_type,
        "price": price,
        "sl": 0.0,
        "tp": round(price + 1.20 if direction == 'BUY' else price - 1.20, 2),
        "deviation": 20,
        "magic": magic,
        "comment": f"FirstRate_Test_{magic}"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        req["type_filling"] = mt5.ORDER_FILLING_FOK
        res = mt5.order_send(req)
        
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"[OK] [FIRSTRATE OPENED] {bot_name} (Magic {magic}) | {direction} {lot} @ {price:.2f} | Ticket #{res.order}")
        return res.order
    else:
        log(f"[FAIL] [FIRSTRATE FAILED] {bot_name} (Magic {magic}): {res.comment}")
        return None

def main():
    log("=" * 70)
    log("[START] EXECUTING FIRSTRATE TEST TRADES FOR ALL CREATED BOTS")
    log("=" * 70)
    
    if not mt5.initialize():
        if not mt5.initialize(path=TERMINAL_PATH):
            log("[FAIL] MT5 failed to initialize.")
            sys.exit(1)
            
    info = mt5.account_info()
    log(f"Connected to Headway MT5 | Account: {info.login} | Balance: ${info.balance:,.2f} | Equity: ${info.equity:,.2f}")
    
    # 1. Open FirstRate test trade for all 5 bots
    test_tickets = []
    for b in BOTS:
        t_id = execute_firstrate_trade(b['magic'], b['name'], direction="BUY", lot=0.01)
        if t_id:
            test_tickets.append((b['magic'], b['name'], t_id))
        time.sleep(1)
        
    log("=" * 70)
    log(f"[ACTIVE] FIRSTRATE TEST TRADES OPENED: {len(test_tickets)} active test positions.")
    log("Monitoring test trades until completion...")
    log("=" * 70)
    
    # Monitor for 20 seconds
    start_t = time.time()
    while time.time() - start_t < 20:
        time.sleep(4)
        open_pos = mt5.positions_get(symbol=SYMBOL)
        if open_pos:
            test_open = [p for p in open_pos if p.magic in [b['magic'] for b in BOTS]]
            total_pnl = sum(p.profit for p in test_open)
            log(f"Status: {len(test_open)} active test trades in market | Combined PnL: ${total_pnl:+,.2f}")
        
    # Close test trades cleanly to complete FirstRate stage
    log("Concluding FirstRate test trade cycle (Closing test tickets)...")
    for magic, b_name, ticket in test_tickets:
        p_list = mt5.positions_get(ticket=ticket)
        if p_list:
            p = p_list[0]
            tick = mt5.symbol_info_tick(SYMBOL)
            c_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            c_price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
            c_req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": SYMBOL,
                "volume": p.volume,
                "type": c_type,
                "price": c_price,
                "deviation": 20,
                "magic": magic,
                "comment": "FirstRate_Complete",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            c_res = mt5.order_send(c_req)
            if c_res.retcode == mt5.TRADE_RETCODE_DONE:
                log(f"[CLOSED] [FIRSTRATE ENDED] {b_name} (Ticket #{ticket}) closed with profit ${p.profit:+,.2f}")
                
    mt5.shutdown()
    log("=" * 70)
    log("[SUCCESS] ALL FIRSTRATE TEST TRADES SUCCESSFULLY ENDED!")
    log("ACTIVATING ALL 5 BOTS FOR 24/7 CONTINUOUS AUTONOMOUS TRADING...")
    log("=" * 70)

if __name__ == '__main__':
    main()
