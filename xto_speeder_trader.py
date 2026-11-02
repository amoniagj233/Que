import pandas as pd
"""
XTO Speeder Rebuilt - Live Python Trader
XAUUSD M1 | Magic 1111 | GroupTP + DCA Grid
Mirrors the MQL5 EA logic in Python for immediate deployment
"""
import MetaTrader5 as mt5
import time
import sys
import math
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===================== CONFIGURATION =====================
MAGIC           = 1111
SYMBOL          = "XAUUSD"
COMMENT         = "XTO-Rebuilt"
BASE_LOT        = 0.01
LOT_MULTIPLIER  = 1.5
GRID_STEP_PTS   = 60        # 60 points = $0.60 on Gold
MAX_LAYERS      = 5         # Maximum DCA grid layers
GROUP_TP_PTS    = 60        # Take profit from VWAP in points = $0.60
GROUP_TP_USD    = 2.50      # Alternatively: close basket when profit >= $2.50
MAX_BASKET_LOSS = 50.0      # Emergency liquidation if basket loss > $50
ALLOW_BUY       = True
ALLOW_SELL      = True
SLIPPAGE        = 20
LOOP_INTERVAL   = 2         # Tick loop in seconds
LOG_FILE        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xto_speeder_trades.log")

# ===================== HELPERS ===========================
def get_point():
    s = mt5.symbol_info(SYMBOL)
    return s.point if s else 0.01

def calc_lot(layer):
    lot = round(BASE_LOT * (LOT_MULTIPLIER ** layer), 2)
    s = mt5.symbol_info(SYMBOL)
    if s:
        step = s.volume_step
        lot = math.floor(lot / step) * step
        lot = max(s.volume_min, min(s.volume_max, lot))
    return round(lot, 2)

def get_basket(pos_type):
    """Returns (count, total_lots, vwap, floating_pnl, worst_price, best_price)"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0

    count = 0
    total_lots = 0.0
    vol_price_sum = 0.0
    floating_pnl = 0.0
    worst = 9999999.0 if pos_type == mt5.POSITION_TYPE_BUY else 0.0
    best  = 0.0       if pos_type == mt5.POSITION_TYPE_BUY else 9999999.0

    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            count += 1
            total_lots   += p.volume
            vol_price_sum += p.price_open * p.volume
            floating_pnl  += p.profit + p.swap

            if pos_type == mt5.POSITION_TYPE_BUY:
                if p.price_open < worst: worst = p.price_open
                if p.price_open > best:  best  = p.price_open
            else:
                if p.price_open > worst: worst = p.price_open
                if p.price_open < best:  best  = p.price_open

    vwap = vol_price_sum / total_lots if total_lots > 0 else 0.0
    return count, total_lots, vwap, floating_pnl, worst, best

def close_basket(pos_type, reason):
    side = "BUY" if pos_type == mt5.POSITION_TYPE_BUY else "SELL"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [FAST] Closing {side} basket [{reason}]")
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            r = mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": p.volume,
                "type": mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": p.ticket,
                "price": mt5.symbol_info_tick(SYMBOL).bid if pos_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask,
                "deviation": SLIPPAGE,
                "magic": MAGIC,
                "comment": f"XTO-Close-{reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            })
            if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"  [OK] Closed #{p.ticket} {p.volume} lots @ {r.price:.2f} | PnL: ${p.profit:+.2f}")
            else:
                # Try FOK then RETURN
                for filling in [mt5.ORDER_FILLING_FOK]:
                    req2 = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": SYMBOL,
                        "volume": p.volume,
                        "type": mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                        "position": p.ticket,
                        "price": mt5.symbol_info_tick(SYMBOL).bid if pos_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask,
                        "deviation": SLIPPAGE,
                        "magic": MAGIC,
                        "comment": f"XTO-Close-{reason}",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": filling,
                    }
                    r2 = mt5.order_send(req2)
                    if r2 and r2.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"  [OK] Closed #{p.ticket} {p.volume} lots (filling={filling}) @ {r2.price:.2f}")
                        break
                else:
                    print(f"  [FAIL] Close FAILED #{p.ticket}: {r.retcode if r else 'None'}")

def open_order(order_type, lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": SLIPPAGE,
        "magic": MAGIC,
        "comment": COMMENT,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    r = mt5.order_send(req)
    if r and r.retcode == mt5.TRADE_RETCODE_DONE:
        side = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {side} {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
        return r
    else:
        # retry with other fillings
        for filling in [mt5.ORDER_FILLING_FOK]:
            req["type_filling"] = filling
            r = mt5.order_send(req)
            if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                side = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {side} {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
                return r
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [FAIL] Order FAILED: {r.retcode if r else 'None'} | {r.comment if r else ''}")
        return None

# ===================== LOGGING ===========================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ===================== MT5 RECONNECT =====================
def ensure_connected(max_retries=5):
    for attempt in range(max_retries):
        if mt5.terminal_info() is not None:
            return True
        log(f"MT5 disconnected. Reconnecting attempt {attempt+1}/{max_retries}...")
        mt5.shutdown()
        time.sleep(5)
        if mt5.initialize():
            log("MT5 reconnected successfully.")
            return True
    return False

# ===================== MAIN LOOP =========================
def main():
    if not mt5.initialize():
        print(f"MT5 init FAILED: {mt5.last_error()}")
        sys.exit(1)

    acc = mt5.account_info()
    pt = get_point()
    daily_start_balance = acc.balance
    daily_closed_pnl    = 0.0
    last_day            = datetime.now().date()

    log("=" * 60)
    log("  [XTO] XTO SPEEDER REBUILT — LIVE PYTHON TRADER")
    log("=" * 60)
    log(f"  Account : {acc.login} | {acc.server}")
    log(f"  Balance : ${acc.balance:.2f} | Equity: ${acc.equity:.2f}")
    log(f"  Symbol  : {SYMBOL} | Magic: {MAGIC}")
    log(f"  Config  : BaseLot={BASE_LOT} | Multi={LOT_MULTIPLIER}x | Step={GRID_STEP_PTS}pts | MaxLayers={MAX_LAYERS}")
    log(f"  TP      : {GROUP_TP_PTS} pts from VWAP (or +${GROUP_TP_USD:.2f})")
    log(f"  Disaster: SL at -${MAX_BASKET_LOSS:.2f} per basket")
    log(f"  24/7 MODE ACTIVE — Running continuously")
    log("=" * 60)

    tick_count = 0

    while True:
        try:
            # --- MT5 Connection Health Check ---
            if not ensure_connected():
                log("FATAL: Cannot reconnect to MT5. Exiting for watchdog restart.")
                sys.exit(1)

            # --- Daily Reset ---
            today = datetime.now().date()
            if today != last_day:
                acc_now = mt5.account_info()
                daily_gain = acc_now.balance - daily_start_balance
                log(f"=== NEW DAY {today} | Yesterday PnL: ${daily_gain:+.2f} | New Balance: ${acc_now.balance:.2f} ===")
                daily_start_balance = acc_now.balance
                daily_closed_pnl = 0.0
                last_day = today
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue

            pt = get_point()
            tick_count += 1

            # --- Get basket metrics ---
            buy_count, buy_lots, buy_vwap, buy_pnl, buy_worst, buy_best = get_basket(mt5.POSITION_TYPE_BUY)
            sell_count, sell_lots, sell_vwap, sell_pnl, sell_worst, sell_best = get_basket(mt5.POSITION_TYPE_SELL)

            # --- 1. DISASTER ARMOR CHECK ---
            if MAX_BASKET_LOSS > 0:
                if buy_count > 0 and buy_pnl <= -MAX_BASKET_LOSS:
                    print(f"[ALERT] DISASTER: BUY loss ${buy_pnl:.2f} exceeded -${MAX_BASKET_LOSS:.2f}! Liquidating basket!")
                    close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                    time.sleep(1)
                    continue
                if sell_count > 0 and sell_pnl <= -MAX_BASKET_LOSS:
                    print(f"[ALERT] DISASTER: SELL loss ${sell_pnl:.2f} exceeded -${MAX_BASKET_LOSS:.2f}! Liquidating basket!")
                    close_basket(mt5.POSITION_TYPE_SELL, "Disaster_SL")
                    time.sleep(1)
                    continue

            # --- 2. GROUP TAKE PROFIT CHECK ---
            if buy_count > 0 and buy_vwap > 0:
                buy_tp = buy_vwap + GROUP_TP_PTS * pt
                tp_hit = (tick.bid >= buy_tp) or (GROUP_TP_USD > 0 and buy_pnl >= GROUP_TP_USD)
                if tp_hit:
                    log(f"[TP] GroupTP_3 BUY avg={buy_vwap:.2f} | TP={buy_tp:.2f} | Bid={tick.bid:.2f} | Profit=+${buy_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP_Hit")
                    time.sleep(1)
                    continue

            if sell_count > 0 and sell_vwap > 0:
                sell_tp = sell_vwap - GROUP_TP_PTS * pt
                tp_hit = (tick.ask <= sell_tp) or (GROUP_TP_USD > 0 and sell_pnl >= GROUP_TP_USD)
                if tp_hit:
                    log(f"[TP] GroupTP_3 SELL avg={sell_vwap:.2f} | TP={sell_tp:.2f} | Ask={tick.ask:.2f} | Profit=+${sell_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_SELL, "GroupTP_Hit")
                    time.sleep(1)
                    continue

            # --- 3. GRID DCA MANAGEMENT ---
            step_dist = GRID_STEP_PTS * pt

            # BUY basket management
            if ALLOW_BUY:
                if buy_count == 0:
                    lot = calc_lot(0)
                    open_order(mt5.ORDER_TYPE_BUY, lot, "Layer_1_Initial")
                elif buy_count < MAX_LAYERS:
                    if (buy_worst - tick.ask) >= step_dist:
                        next_lot = calc_lot(buy_count)
                        open_order(mt5.ORDER_TYPE_BUY, next_lot, f"Layer_{buy_count+1}_DCA_avg={buy_vwap:.2f}")

            # SELL basket management (Bi-Directional Active)
            if ALLOW_SELL:
                if sell_count == 0:
                    rates_m5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 30)
                    if rates_m5 is not None and len(rates_m5) >= 20:
                        df_t = pd.DataFrame(rates_m5)
                        if df_t['close'].iloc[-1] < df_t['close'].ewm(span=21, adjust=False).mean().iloc[-1]:
                            open_order(mt5.ORDER_TYPE_SELL, calc_lot(0), "Layer_1_Initial_SELL")
                elif sell_count > 0 and sell_count < MAX_LAYERS:
                    if (tick.bid - sell_worst) >= step_dist:
                        next_lot = calc_lot(sell_count)
                        open_order(mt5.ORDER_TYPE_SELL, next_lot, f"Layer_{sell_count+1}_DCA_avg={sell_vwap:.2f}")

            # --- 4. HUD Dashboard (every 30 ticks) ---
            if tick_count % 15 == 0:
                acc = mt5.account_info()
                log(f"[HUD] Eq=${acc.equity:.2f} | Bal=${acc.balance:.2f} | BUY:{buy_count}L PnL${buy_pnl:+.2f} | SELL:{sell_count}L PnL${sell_pnl:+.2f} | Bid={tick.bid:.2f}")

            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            log("XTO Speeder stopped by user. Positions remain open.")
            break
        except Exception as e:
            log(f"[ERROR] {type(e).__name__}: {e}")
            time.sleep(5)

    mt5.shutdown()

if __name__ == "__main__":
    main()
