import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 initialize failed:", mt5.last_error())
    sys.exit(1)

symbol = "XAUUSD"
for s in ["XAUUSD", "XAUUSDm", "GOLD"]:
    if mt5.symbol_info(s):
        symbol = s
        break

mt5.symbol_select(symbol, True)
tick = mt5.symbol_info_tick(symbol)
if not tick:
    print(f"Failed to get tick for {symbol}")
    sys.exit(1)

print(f"=== MARKET TICK: {symbol} Bid={tick.bid} Ask={tick.ask} Spread={(tick.ask - tick.bid):.2f} ===")

# The 8 Fleet Bots
bots = [
    ("Apex-Quantum-DeepSL", 1111),
    ("Mut-8037 Adaptive", 2222),
    ("SMC Breaker Sniper", 3333),
    ("Strategic Pattern Pro", 4444),
    ("TikTalk Bot", 5555),
    ("Academic MA 44/332", 6666),
    ("Gold Auto Trader", 7777),
    ("ML Intelligence Engine", 8888),
]

open_positions = mt5.positions_get(symbol=symbol) or []
active_magics = {p.magic for p in open_positions}
print(f"Current open positions in {symbol}: {len(open_positions)} (Active Magics: {active_magics})")

tp_distance = 1.50   # Take profit $1.50 above ask
sl_distance = 2.50   # Stop loss $2.50 below ask
volume = 0.01

opened_trades = []

for bot_name, magic in bots:
    # Check if this bot already has an active position
    has_pos = any(p.magic == magic for p in open_positions)
    if has_pos:
        pos_obj = [p for p in open_positions if p.magic == magic][0]
        print(f"[{bot_name} (Magic {magic})] Already has active position: Ticket #{pos_obj.ticket} {pos_obj.type} {pos_obj.volume} @ {pos_obj.price_open}")
        opened_trades.append({
            "bot": bot_name,
            "magic": magic,
            "ticket": pos_obj.ticket,
            "status": "ALREADY_ACTIVE",
            "price": pos_obj.price_open,
            "sl": pos_obj.sl,
            "tp": pos_obj.tp
        })
        continue

    # Refresh tick
    cur_tick = mt5.symbol_info_tick(symbol)
    ask_price = cur_tick.ask
    tp_price = round(ask_price + tp_distance, 2)
    sl_price = round(ask_price - sl_distance, 2)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": ask_price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 30,
        "magic": magic,
        "comment": f"Force {bot_name[:12]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    res = mt5.order_send(request)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"[FORCE BUY SUCCESS] {bot_name} (Magic {magic}): Ticket #{res.order} @ {res.price} | SL: {sl_price} | TP: {tp_price}")
        opened_trades.append({
            "bot": bot_name,
            "magic": magic,
            "ticket": res.order,
            "status": "NEW_ORDER_OPENED",
            "price": res.price,
            "sl": sl_price,
            "tp": tp_price
        })
    else:
        err = res.comment if res else str(mt5.last_error())
        print(f"[REJECTED] {bot_name} (Magic {magic}): {err}")
        opened_trades.append({
            "bot": bot_name,
            "magic": magic,
            "ticket": None,
            "status": f"FAILED: {err}"
        })
    time.sleep(0.3)

mt5.shutdown()
print("\nForce trade execution complete.")
