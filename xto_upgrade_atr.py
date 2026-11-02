import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
"""
XTO Speeder Upgrade 1: Dynamic ATR Volatility Spacing (Dual BUY & SELL)
The Profit Maximizer with Full Dual-Direction Trading:
  - Takes BUY trades in uptrends
  - Takes SELL trades in downtrends
  - Dynamically adapts grid spacing and TP based on live ATR
"""
import MetaTrader5 as mt5
import pandas as pd
import time, math
from datetime import datetime
from live_pattern_learner import analyze_live_market_pattern

MAGIC           = 2222
SYMBOL          = "XAUUSD"
COMMENT         = "XTO-ATR-Pro"
BASE_LOT        = 0.01
LOT_MULTIPLIER  = 1.5
ATR_STEP_MULT   = 1.5
ATR_TP_MULT     = 1.0
MIN_STEP_PTS    = 60
MAX_LAYERS      = 5
MAX_BASKET_LOSS = 50.0
SLIPPAGE        = 20
LOOP_INTERVAL   = 2

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_atr(period=14, timeframe=mt5.TIMEFRAME_M5):
    rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, period + 5)
    if rates is None or len(rates) < period:
        return 1.80
    df = pd.DataFrame(rates)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    return max(1.20, round(float(tr.tail(period).mean()), 2))

def get_trend_bias(timeframe=mt5.TIMEFRAME_M5):
    rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, 60)
    if rates is None or len(rates) < 55:
        return 1
    df = pd.DataFrame(rates)
    ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
    ema55 = df['close'].ewm(span=55, adjust=False).mean().iloc[-1]
    return 1 if ema21 >= ema55 else -1

def calc_lot(layer):
    lot = round(BASE_LOT * (LOT_MULTIPLIER ** layer), 2)
    s = mt5.symbol_info(SYMBOL)
    if s:
        lot = max(s.volume_min, min(s.volume_max, lot))
    return round(lot, 2)

def get_basket(pos_type):
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

def close_basket(pos_type, reason):
    side = "BUY" if pos_type == mt5.POSITION_TYPE_BUY else "SELL"
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            c_price = tick.bid if pos_type == mt5.POSITION_TYPE_BUY else tick.ask
            c_type  = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": c_type, "position": p.ticket, "price": c_price,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"ATR-TP-{reason}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }
                r = mt5.order_send(req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    log(f"  [OK] Closed #{p.ticket} {p.volume} lots @ {r.price:.2f} | PnL: ${p.profit:+.2f}")
                    break

def open_order(order_type, lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        log("[WARN] Tick data temporarily unavailable")
        return None
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    side_str = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": order_type, "price": price, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": f"{COMMENT}-{side_str}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = mt5.order_send(req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"  [OK] {side_str} {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
            return r
    return None

def main():
    if not mt5.initialize():
        print("MT5 init failed")
        sys.exit(1)
    acc = mt5.account_info()
    log("=" * 60)
    log("  [DUAL] XTO SPEEDER UPGRADE 1: DUAL BUY & SELL (ATR SPACING)")
    log(f"  Account: {acc.login} | Server: {acc.server} | Balance: ${acc.balance:.2f}")
    log("=" * 60)

    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue

            pat = analyze_live_market_pattern(SYMBOL, mt5.TIMEFRAME_M5)
            atr = pat['atr'] if pat else get_atr(14, mt5.TIMEFRAME_M5)
            step_m = pat['step_mult'] if pat else ATR_STEP_MULT
            tp_m   = pat['tp_mult'] if pat else ATR_TP_MULT
            allow_new = pat['allow_new_basket'] if pat else True
            need_green = pat['require_green_bar'] if pat else False

            dynamic_step = max(MIN_STEP_PTS * 0.01, atr * step_m)
            dynamic_tp   = max(MIN_STEP_PTS * 0.01, atr * tp_m)
            trend        = get_trend_bias()

            # --- 1. BUY Basket Management ---
            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket(mt5.POSITION_TYPE_BUY)
            if b_cnt > 0:
                if b_pnl <= -MAX_BASKET_LOSS:
                    close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                    continue
                target_tp = b_vwap + dynamic_tp
                if tick.bid >= target_tp or b_pnl >= 2.00:
                    log(f"[TP] Dynamic ATR BUY TP Hit! avg={b_vwap:.2f} | TP={target_tp:.2f} | PnL=+${b_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP_ATR")
                    continue
                if b_cnt < MAX_LAYERS and (b_worst - tick.ask) >= dynamic_step:
                    can_dca = True
                    if need_green:
                        rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 2)
                        if rates_m1 is not None and len(rates_m1) >= 2:
                            can_dca = rates_m1[-1]['close'] > rates_m1[-1]['open']
                    if can_dca:
                        open_order(mt5.ORDER_TYPE_BUY, calc_lot(b_cnt), f"DCA_L{b_cnt+1}_Regime={pat['regime'] if pat else 'NORMAL'}")
            elif b_cnt == 0 and allow_new and trend > 0:
                open_order(mt5.ORDER_TYPE_BUY, calc_lot(0), "Initial_BUY_Layer")

            # --- 2. SELL Basket Management ---
            s_cnt, s_lots, s_vwap, s_pnl, s_worst, _ = get_basket(mt5.POSITION_TYPE_SELL)
            if s_cnt > 0:
                if s_pnl <= -MAX_BASKET_LOSS:
                    close_basket(mt5.POSITION_TYPE_SELL, "Disaster_SL")
                    continue
                target_tp = s_vwap - dynamic_tp
                if tick.ask <= target_tp or s_pnl >= 2.00:
                    log(f"[TP] Dynamic ATR SELL TP Hit! avg={s_vwap:.2f} | TP={target_tp:.2f} | PnL=+${s_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_SELL, "GroupTP_ATR")
                    continue
                if s_cnt < MAX_LAYERS and (tick.bid - s_worst) >= dynamic_step:
                    open_order(mt5.ORDER_TYPE_SELL, calc_lot(s_cnt), f"DCA_L{s_cnt+1}_Regime={pat['regime'] if pat else 'NORMAL'}")
            elif s_cnt == 0 and allow_new and trend < 0:
                open_order(mt5.ORDER_TYPE_SELL, calc_lot(0), "Initial_SELL_Layer")

            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
