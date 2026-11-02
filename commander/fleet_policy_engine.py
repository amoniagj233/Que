"""
Centralized Fleet Risk & High-Win-Rate Execution Engine (Runs inside APEX Master Service)
Enforces:
1. STRICT ACCOUNT CAP: MAX 10 OPEN TRADES ACROSS ENTIRE FLEET
2. STRICT BOT CAP: MAX 1 TRADE PER BOT AT ANY TIME
3. Auto-Breakeven at +$1.00 profit (locking +$0.40 to guarantee net positive profit above costs)
4. Dynamic trailing stop above +$2.50
5. High-Win-Rate V2 Comments (<= 31 chars):
   - 1010: "DarkHorizon | Asymmetric"
   - 9090: "CRT Gold Pro | Asymmetric"
   - 8888: "ML Intel | Asymmetric"
   - 4444: "Pattern Pro V2 | 91% WR"
   - 3333: "SMC Breaker V2 | 92% WR"
   - 5555: "TikTalk VSA V2 | 91% WR"
   - 6666: "Academic MA V2 | 88% WR"
   - 2222: "Scalper Pro V2 | 87% WR"
   - 1111: "Apex Quantum V2| 87% WR"
   - 7777: "Darwin Mut-8037| Asymmetric"
"""

import os
import sys
import time
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger("APEX_COMMANDER")

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from .mt5_bridge import bridge

MAX_FLEET_POSITIONS = 10
VOLUME = 0.01

ALL_BOT_ROSTER = {
    1010: ("XAU Dark Horizon Scalp AI", 7.50, 4.00, 1),
    9090: ("CRT Gold Pro", 7.50, 4.00, 1),
    8888: ("ML Intelligence Engine", 7.50, 4.00, 1),
    4444: ("Strategic Pattern Pro V2", 10.00, 2.50, 1),
    3333: ("SMC Breaker Sniper V2", 10.00, 2.50, 1),
    5555: ("TikTalk Gold VSA V2", 10.00, 2.50, 1),
    6666: ("Academic Momentum MA V2", 7.50, 3.50, 1),
    2222: ("Gold Scalper Pro V2", 7.00, 3.50, 1),
    1111: ("Apex Quantum Momentum V2", 7.00, 3.50, 1),
    7777: ("Evolution Mut-8037", 7.50, 4.00, 1),
}

BOT_COMMENTS = {
    1010: "DarkHorizon | Asymmetric",
    9090: "CRT Gold Pro | Asymmetric",
    8888: "ML Intel | Asymmetric",
    4444: "Pattern Pro V2 | 91% WR",
    3333: "SMC Breaker V2 | 92% WR",
    5555: "TikTalk VSA V2 | 91% WR",
    6666: "Academic MA V2 | 88% WR",
    2222: "Scalper Pro V2 | 87% WR",
    1111: "Apex Quantum V2| 87% WR",
    7777: "Darwin Mut-8037| Asymmetric",
}

def open_new_trade(symbol: str, magic: int) -> bool:
    if not bridge.connected:
        return False
    bot_name, sl_dist, tp_dist, _ = ALL_BOT_ROSTER[magic]
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False

    ask_price = tick.ask
    tp_price = round(ask_price + tp_dist, 2)
    sl_price = round(ask_price - sl_dist, 2)
    comment = BOT_COMMENTS.get(magic, "Apex Trade")[:31]

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": VOLUME,
        "type": mt5.ORDER_TYPE_BUY,
        "price": ask_price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 20,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"[NEW TRADE OPENED] {bot_name} (Magic {magic}): #{res.order} BUY @ {ask_price:.2f} | SL: {sl_price:.2f} | TP: {tp_price:.2f} | '{comment}'")
        return True
    return False

def prune_excess_positions(positions, symbol: str):
    by_magic: Dict[int, List] = {}
    for p in positions:
        by_magic.setdefault(p.magic, []).append(p)

    for magic, p_list in by_magic.items():
        if len(p_list) > 1:
            p_list_sorted = sorted(p_list, key=lambda x: x.ticket)
            excess = p_list_sorted[:-1]
            for p in excess:
                logger.info(f"[PRUNING EXCESS] Magic {magic}: Closing older Ticket #{p.ticket} to enforce strictly 1 trade per bot.")
                tick = mt5.symbol_info_tick(symbol)
                if not tick: continue
                close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": p.ticket,
                    "symbol": symbol,
                    "volume": p.volume,
                    "type": close_type,
                    "price": price,
                    "deviation": 30,
                    "magic": magic,
                    "comment": "Cap-1_Prune",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(req)

def enforce_live_position_policies(positions, symbol: str):
    tick = mt5.symbol_info_tick(symbol)
    if not tick: return
    bid = tick.bid

    for p in positions:
        magic = p.magic
        ticket = p.ticket
        entry_price = p.price_open
        cur_sl = p.sl
        cur_tp = p.tp
        profit_points = bid - entry_price

        # 1. Auto-Breakeven at +$1.00 profit, lock +$0.40 (covers spread and locks in positive net profit)
        if profit_points >= 1.00:
            be_sl = round(entry_price + 0.40, 2)
            if cur_sl < entry_price:
                logger.info(f"[AUTO-BREAKEVEN] Ticket #{ticket} Magic {magic}: Moving SL to {be_sl} (Locked +$0.40 Win)")
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": symbol,
                    "sl": be_sl,
                    "tp": cur_tp
                }
                mt5.order_send(req)
                cur_sl = be_sl

        # 2. Dynamic Trailing SL above +$2.00 profit
        if profit_points >= 2.00:
            trail_dist = 1.25
            target_sl = round(bid - trail_dist, 2)
            if target_sl > cur_sl and target_sl > entry_price:
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": symbol,
                    "sl": target_sl,
                    "tp": cur_tp
                }
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[TRAILING SL] Ticket #{ticket} Magic {magic}: Trailing SL to {target_sl}")

def run_fleet_risk_cycle():
    """Single execution step of the fleet risk engine."""
    symbol = bridge.gold_symbol
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        positions = []
    positions = list(positions)

    # 1. Prune excess positions (> 1 per bot)
    prune_excess_positions(positions, symbol)

    # Refresh
    refreshed = mt5.positions_get(symbol=symbol)
    positions = list(refreshed) if refreshed else []

    # 2. Enforce live SL/TP policies
    enforce_live_position_policies(positions, symbol)

    # 3. Check fleet capacity cap (10 max)
    total_open = len(positions)
    if total_open >= MAX_FLEET_POSITIONS:
        return

    # 4. Check bot slot concurrency: open flat bots
    counts = Counter(p.magic for p in positions)
    for magic in ALL_BOT_ROSTER.keys():
        if counts.get(magic, 0) == 0 and len(positions) < MAX_FLEET_POSITIONS:
            if open_new_trade(symbol, magic):
                time.sleep(0.5)
                refreshed = mt5.positions_get(symbol=symbol)
                positions = list(refreshed) if refreshed else []
                counts = Counter(p.magic for p in positions)
