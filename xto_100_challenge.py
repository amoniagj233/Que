"""
XTO Speeder: $100 Account Doubling Challenge Engine (Dual BUY & SELL)
Rules:
  - Starting Capital: $100.00
  - Level 1 ($100 - $199): Base Lot = 0.01 | Target TP = $2.50
  - Level 2 ($200 - $399): Base Lot = 0.02 | Target TP = $5.00  (DOUBLED!)
  - Level 3 ($400 - $799): Base Lot = 0.04 | Target TP = $10.00
  - Level 4 ($800 - $1599): Base Lot = 0.08 | Target TP = $20.00
  - Level 5 ($1600+):       Base Lot = 0.16 | Target TP = $40.00
Capabilities:
  - DUAL DIRECTION: Takes BUY trades in uptrends AND SELL trades in downtrends!
  - Adaptive Trend Detection (EMA 21/55 Momentum)
  - Dynamic ATR Grid Spacing (Learns from live_pattern_learner)
  - Auto-Doubling Compounding Ladder
  - Independent Challenge Ledger persisted in challenge_100_state.json
"""
import MetaTrader5 as mt5
import pandas as pd
import json
import time
import sys
import os
import math
from datetime import datetime
from live_pattern_learner import analyze_live_market_pattern

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MAGIC           = 8888
SYMBOL          = "XAUUSD"
STATE_FILE      = "challenge_100_state.json"
MAX_LAYERS      = 4
LOT_MULTIPLIER  = 1.5
SLIPPAGE        = 20
LOOP_INTERVAL   = 2

def load_or_init_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    state = {
        'start_capital': 100.0,
        'current_balance': 100.0,
        'high_water_mark': 100.0,
        'level': 1,
        'base_lot': 0.01,
        'target_balance': 200.0,
        'total_profit': 0.0,
        'cycles_won': 0,
        'cycles_lost': 0,
        'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_state(state)
    return state

def save_state(state):
    state['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def update_compounding_ladder(state):
    bal = state['current_balance']
    if bal < 200.0:
        new_level, base_lot, target = 1, 0.01, 200.0
    elif bal < 400.0:
        new_level, base_lot, target = 2, 0.02, 400.0
    elif bal < 800.0:
        new_level, base_lot, target = 3, 0.04, 800.0
    elif bal < 1600.0:
        new_level, base_lot, target = 4, 0.08, 1600.0
    else:
        new_level, base_lot, target = 5, 0.16, 3200.0

    if new_level > state['level']:
        print(f"\n🎉 MILESTONE REACHED! ACCOUNT DOUBLED TO ${bal:.2f}! PROMOTED TO LEVEL {new_level}! BASE LOT: {base_lot} LOTS!\n")
    elif new_level < state['level']:
        print(f"\n⚠️ Equity protection: Stepping down to Level {new_level} (Base lot: {base_lot}) to protect bankroll.\n")

    state['level'] = new_level
    state['base_lot'] = base_lot
    state['target_balance'] = target
    if bal > state['high_water_mark']:
        state['high_water_mark'] = bal
    save_state(state)

def get_trend_bias(timeframe=mt5.TIMEFRAME_M5):
    rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, 60)
    if rates is None or len(rates) < 55:
        return 1
    df = pd.DataFrame(rates)
    ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
    ema55 = df['close'].ewm(span=55, adjust=False).mean().iloc[-1]
    return 1 if ema21 >= ema55 else -1 # 1 = BULLISH (BUY), -1 = BEARISH (SELL)

def calc_layer_lot(state, layer):
    lot = round(state['base_lot'] * (LOT_MULTIPLIER ** layer), 2)
    s = mt5.symbol_info(SYMBOL)
    if s:
        lot = max(s.volume_min, min(s.volume_max, lot))
    return round(lot, 2)

def get_basket_metrics(pos_type):
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0
    count, total_lots, vol_price_sum, floating_pnl = 0, 0.0, 0.0, 0.0
    worst = 9999999.0 if pos_type == mt5.POSITION_TYPE_BUY else 0.0
    best  = 0.0       if pos_type == mt5.POSITION_TYPE_BUY else 9999999.0
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            count += 1
            total_lots += p.volume
            vol_price_sum += p.price_open * p.volume
            floating_pnl += p.profit + p.swap
            if pos_type == mt5.POSITION_TYPE_BUY:
                if p.price_open < worst: worst = p.price_open
                if p.price_open > best:  best  = p.price_open
            else:
                if p.price_open > worst: worst = p.price_open
                if p.price_open < best:  best  = p.price_open
    vwap = vol_price_sum / total_lots if total_lots > 0 else 0.0
    return count, total_lots, vwap, floating_pnl, worst, best

def close_basket(state, pos_type, reason):
    side = "BUY" if pos_type == mt5.POSITION_TYPE_BUY else "SELL"
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return 0.0
    
    basket_pnl = 0.0
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            c_price = mt5.symbol_info_tick(SYMBOL).bid if pos_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask
            c_type  = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": c_type, "position": p.ticket, "price": c_price,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"C100-{reason}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }
                r = mt5.order_send(req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    basket_pnl += p.profit + p.swap
                    break

    state['current_balance'] += basket_pnl
    state['total_profit'] += basket_pnl
    if basket_pnl > 0:
        state['cycles_won'] += 1
    else:
        state['cycles_lost'] += 1
        
    update_compounding_ladder(state)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 Closed {side} Basket ({reason}): PnL: ${basket_pnl:+.2f} | Balance: ${state['current_balance']:.2f}")
    return basket_pnl

def open_order(state, order_type, lot, layer):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    side_str = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    comment = f"C100-{side_str}-L{state['level']}-{layer}"
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": order_type, "price": price, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = mt5.order_send(req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{side_str}] Layer {layer}: {lot} lots @ {r.price:.2f} ({comment}) | Ticket #{r.order}")
            return r
    return None

def main():
    if not mt5.initialize():
        print("MT5 init failed")
        sys.exit(1)

    state = load_or_init_state()
    update_compounding_ladder(state)
    
    print("=" * 68)
    print("  🚀 Starting $100 Dual (BUY & SELL) Challenge Trader")
    print(f"  Starting Balance: ${state['current_balance']:.2f} | Level: {state['level']} (Base: {state['base_lot']})")
    print("  Trend Detection: Active (Takes BUYs in uptrend, SELLs in downtrend)")
    print("=" * 68)

    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue

            pat = analyze_live_market_pattern(SYMBOL, mt5.TIMEFRAME_M5)
            atr = pat['atr'] if pat else 2.50
            step_m = pat['step_mult'] if pat else 1.5
            dynamic_step = max(1.20, atr * step_m)
            target_usd   = 2.50 * state['level']
            disaster_usd = 25.0 * state['level']
            trend        = get_trend_bias(mt5.TIMEFRAME_M5)

            # --- 1. BUY Basket Management ---
            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket_metrics(mt5.POSITION_TYPE_BUY)
            if b_cnt > 0:
                if b_pnl <= -disaster_usd:
                    close_basket(state, mt5.POSITION_TYPE_BUY, "Disaster_SL")
                    time.sleep(1)
                    continue
                buy_tp = b_vwap + (0.80 * state['level'])
                if (tick.bid >= buy_tp) or (b_pnl >= target_usd):
                    close_basket(state, mt5.POSITION_TYPE_BUY, "GroupTP_Hit")
                    time.sleep(1)
                    continue
                if b_cnt < MAX_LAYERS and (b_worst - tick.ask) >= dynamic_step:
                    open_order(state, mt5.ORDER_TYPE_BUY, calc_layer_lot(state, b_cnt), b_cnt + 1)
            elif b_cnt == 0 and trend > 0: # Bullish trend -> Open Initial BUY
                open_order(state, mt5.ORDER_TYPE_BUY, calc_layer_lot(state, 0), 1)

            # --- 2. SELL Basket Management ---
            s_cnt, s_lots, s_vwap, s_pnl, s_worst, _ = get_basket_metrics(mt5.POSITION_TYPE_SELL)
            if s_cnt > 0:
                if s_pnl <= -disaster_usd:
                    close_basket(state, mt5.POSITION_TYPE_SELL, "Disaster_SL")
                    time.sleep(1)
                    continue
                sell_tp = s_vwap - (0.80 * state['level'])
                if (tick.ask <= sell_tp) or (s_pnl >= target_usd):
                    close_basket(state, mt5.POSITION_TYPE_SELL, "GroupTP_Hit")
                    time.sleep(1)
                    continue
                if s_cnt < MAX_LAYERS and (tick.bid - s_worst) >= dynamic_step:
                    open_order(state, mt5.ORDER_TYPE_SELL, calc_layer_lot(state, s_cnt), s_cnt + 1)
            elif s_cnt == 0 and trend < 0: # Bearish trend -> Open Initial SELL
                open_order(state, mt5.ORDER_TYPE_SELL, calc_layer_lot(state, 0), 1)

            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            print("Challenge trader paused by user.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)

    mt5.shutdown()

if __name__ == "__main__":
    main()
