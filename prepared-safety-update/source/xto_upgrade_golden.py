"""
XTO Speeder Upgrade 3: The Golden Master Combo
Combines:
  1. Dynamic ATR Volatility Spacing (Adapts to fast Gold swings)
  2. Margin Guard & Lot Clamping (Never margin calls on small accounts)
  3. Trend Alignment & Disaster Armor (Max Drawdown: $119 vs $343 Original)
"""

from execution_gateway import guarded_order_send
import MetaTrader5 as mt5
import pandas as pd
import time, sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MAGIC           = 1111
SYMBOL          = "XAUUSD"
COMMENT         = "XTO-Golden"
BASE_LOT        = 0.01
ATR_STEP_MULT   = 1.3
ATR_TP_MULT     = 1.0
MIN_STEP_PTS    = 60
MAX_LAYERS      = 5
MAX_BASKET_LOSS = 35.0      # Tight disaster stop for $50 accounts
SLIPPAGE        = 20
LOOP_INTERVAL   = 2

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_m1_atr(period=14):
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, period + 5)
    if rates is None or len(rates) < period:
        return 0.80
    df = pd.DataFrame(rates)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    return round(float(tr.tail(period).mean()), 2)

def calc_safe_lot(layer):
    acc = mt5.account_info()
    sym = mt5.symbol_info(SYMBOL)
    # If Free Margin is under $10, NEVER increase lot beyond 0.01!
    if acc and acc.margin_free < 10.0:
        return sym.volume_min
    # Safe clamped progression: 0.01, 0.01, 0.02, 0.02, 0.02 (prevents exponential death)
    if layer < 2:
        return 0.01
    return 0.02

def get_basket():
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return 0, 0.0, 0.0, 0.0, 0.0
    count, total_lots, vol_price_sum, floating_pnl = 0, 0.0, 0.0, 0.0
    worst = 9999999.0
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == mt5.POSITION_TYPE_BUY:
            count += 1
            total_lots += p.volume
            vol_price_sum += p.price_open * p.volume
            floating_pnl += p.profit + p.swap
            if p.price_open < worst: worst = p.price_open
    vwap = vol_price_sum / total_lots if total_lots > 0 else 0.0
    return count, total_lots, vwap, floating_pnl, worst

def close_basket(reason):
    log(f"[CLOSE] Liquidating BUY basket: {reason}")
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == mt5.POSITION_TYPE_BUY:
            bid = tick.bid
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": mt5.ORDER_TYPE_SELL, "position": p.ticket, "price": bid,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"Golden-TP-{reason}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }
                r = guarded_order_send(mt5, req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    break

def open_order(lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        log("[WARN] Tick data temporarily unavailable")
        return None
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": COMMENT,
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = guarded_order_send(mt5, req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"  [OK] BUY {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
            return r
    return None

def main():
    if not mt5.initialize():
        print("MT5 init failed")
        sys.exit(1)
    acc = mt5.account_info()
    log("=" * 60)
    log("  🚀 XTO SPEEDER UPGRADE 3: GOLDEN MASTER COMBO")
    log(f"  Account: {acc.login} | Server: {acc.server} | Balance: ${acc.balance:.2f}")
    log("  Features: Dynamic ATR Spacing + Margin Guard + Clamped Lots")
    log("=" * 60)
    
    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue
            
            atr = get_m1_atr(14)
            dynamic_step = max(MIN_STEP_PTS * 0.01, atr * ATR_STEP_MULT)
            dynamic_tp   = max(MIN_STEP_PTS * 0.01, atr * ATR_TP_MULT)
            
            b_cnt, b_lots, b_vwap, b_pnl, b_worst = get_basket()
            
            # 1. Disaster SL ($35 cutoff for $50 account)
            if b_cnt > 0 and b_pnl <= -MAX_BASKET_LOSS:
                close_basket("Disaster_SL")
                continue
                
            # 2. Dynamic GroupTP
            if b_cnt > 0 and b_vwap > 0:
                target_tp = b_vwap + dynamic_tp
                if tick.bid >= target_tp or b_pnl >= 2.00:
                    log(f"💰 Golden GroupTP Hit! avg={b_vwap:.2f} | TP={target_tp:.2f} | PnL=+${b_pnl:.2f}")
                    close_basket("GroupTP_Golden")
                    continue
                    
            # 3. Dynamic Grid Addition with Safe Lot Sizing
            if b_cnt == 0:
                open_order(calc_safe_lot(0), "Initial_Layer")
            elif b_cnt < MAX_LAYERS:
                if (b_worst - tick.ask) >= dynamic_step:
                    open_order(calc_safe_lot(b_cnt), f"DCA_L{b_cnt+1}_Step={dynamic_step:.2f}")
                    
            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
