"""
XTO Speeder Upgrade 2: Candle Reversal Confirmation
"No Falling Knife" Filter
Only adds DCA averaging layers on green reversal candles or RSI hooks.
"""
import MetaTrader5 as mt5
import pandas as pd
import time, sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MAGIC           = 1111
SYMBOL          = "XAUUSD"
COMMENT         = "XTO-Reversal"
BASE_LOT        = 0.01
LOT_MULTIPLIER  = 1.5
GRID_STEP_PTS   = 60
MAX_LAYERS      = 5
GROUP_TP_PTS    = 60
MAX_BASKET_LOSS = 50.0
SLIPPAGE        = 20
LOOP_INTERVAL   = 2

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def is_reversal_candle():
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 3)
    if rates is None or len(rates) < 2:
        return True
    last_candle = rates[-2] # Completed M1 bar
    return last_candle['close'] > last_candle['open'] # Bullish green close

def calc_lot(layer):
    lot = round(BASE_LOT * (LOT_MULTIPLIER ** layer), 2)
    s = mt5.symbol_info(SYMBOL)
    return max(s.volume_min, min(s.volume_max, lot)) if s else 0.01

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
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == mt5.POSITION_TYPE_BUY:
            bid = mt5.symbol_info_tick(SYMBOL).bid
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": mt5.ORDER_TYPE_SELL, "position": p.ticket, "price": bid,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"Rev-TP-{reason}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }
                r = mt5.order_send(req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    break

def open_order(lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": COMMENT,
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = mt5.order_send(req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"  [OK] BUY {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
            return r
    return None

def main():
    if not mt5.initialize():
        print("MT5 init failed")
        sys.exit(1)
    log("=" * 60)
    log("  🚀 XTO SPEEDER UPGRADE 2: REVERSAL CONFIRMATION")
    log("=" * 60)
    step_dist = GRID_STEP_PTS * 0.01
    
    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue
            
            b_cnt, b_lots, b_vwap, b_pnl, b_worst = get_basket()
            
            # Disaster SL
            if b_cnt > 0 and b_pnl <= -MAX_BASKET_LOSS:
                close_basket("Disaster_SL")
                continue
                
            # GroupTP
            if b_cnt > 0 and b_vwap > 0:
                target_tp = b_vwap + (GROUP_TP_PTS * 0.01)
                if tick.bid >= target_tp or b_pnl >= 2.50:
                    log(f"💰 GroupTP Hit! avg={b_vwap:.2f} | PnL=+${b_pnl:.2f}")
                    close_basket("GroupTP")
                    continue
                    
            # Grid Addition with Reversal Filter
            if b_cnt == 0:
                if is_reversal_candle():
                    open_order(calc_lot(0), "Initial_Bullish_Bar")
            elif b_cnt < MAX_LAYERS:
                if (b_worst - tick.ask) >= step_dist:
                    if is_reversal_candle():
                        open_order(calc_lot(b_cnt), f"DCA_L{b_cnt+1}_Reversal_Confirmed")
                        
            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
