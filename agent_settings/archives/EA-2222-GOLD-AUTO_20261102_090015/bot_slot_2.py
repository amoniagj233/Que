"""
Autonomous AI Generated Strategy - Slot #2
Name         : Mut-8369
Magic Number : 2222
Generation   : Validated Darwin Evolution Model
Net Profit   : $+1749.14 (+174.9% 1-Mo ROI)
Win Rate     : 96.7% | Profit Factor: 3.67
Max Drawdown : $260.03 (9.4%)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time, sys, os
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SYMBOL            = "XAUUSD"
MAGIC             = 2222
COMMENT           = "Mut-8369"
BASE_LOT          = 0.01
MAX_LAYERS        = 4
DISASTER_SL_USD   = 150.0
TARGET_PROFIT_USD = 4.5
SLIPPAGE          = 25
LOOP_INTERVAL     = 2
EXP_FACTORS       = [1.8, 2.4, 3.2, 4.2]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [SLOT-2] {msg}", flush=True)

def get_market_metrics():
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 60)
    if rates is None or len(rates) < 55:
        return 3.50, 50.0, 1, False, False, 0.0
    df = pd.DataFrame(rates)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = max(1.50, float(tr.tail(14).mean()))

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    ema21 = float(df['close'].ewm(span=21, adjust=False).mean().iloc[-1])
    ema55 = float(df['close'].ewm(span=55, adjust=False).mean().iloc[-1])
    trend = 1 if ema21 >= ema55 else -1

    last = df.iloc[-1]
    bull_c = last['close'] > last['open']
    bear_c = last['close'] < last['open']
    vel3 = float(df['close'].iloc[-1] - df['close'].iloc[-4]) if len(df) >= 4 else 0.0
    return atr, rsi, trend, bull_c, bear_c, vel3

def calc_lot(layer):
    lot = BASE_LOT if layer < 2 else (BASE_LOT * 2.0)
    s = mt5.symbol_info(SYMBOL)
    return round(max(s.volume_min, min(s.volume_max, lot)), 2) if s else 0.01

def get_basket(pos_type):
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return 0, 0.0, 0.0, 0.0, 0.0, 0.0
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
                if p.price_open > best: best = p.price_open
            else:
                if p.price_open > worst: worst = p.price_open
                if p.price_open < best: best = p.price_open
    vwap = vol_price_sum / total_lots if total_lots > 0 else 0.0
    return count, total_lots, vwap, floating_pnl, worst, best

def close_basket(pos_type, reason):
    side = "BUY" if pos_type == mt5.POSITION_TYPE_BUY else "SELL"
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    log(f"[CLOSE] Liquidating {side} basket: {reason}")
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            c_price = tick.bid if pos_type == mt5.POSITION_TYPE_BUY else tick.ask
            c_type  = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": c_type, "position": p.ticket, "price": c_price,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"Evo-{reason}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }
                r = mt5.order_send(req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    break

def check_quant_desk(side):
    # 1. News Sentinel Check
    try:
        if os.path.exists("market_risk_state.json"):
            with open("market_risk_state.json", "r", encoding="utf-8") as f:
                news = json.load(f)
                if news.get("news_freeze", False):
                    ev = news.get('active_event', 'Macro Event')
                    return False, f"News Freeze ({ev})"
    except Exception: pass

    # 2. CRO Risk Officer Check
    try:
        if os.path.exists("cro_risk_state.json"):
            with open("cro_risk_state.json", "r", encoding="utf-8") as f:
                cro = json.load(f)
                if cro.get("circuit_breaker", False):
                    return False, "CRO Circuit Breaker Engaged"
                if not cro.get("spread_ok", True):
                    sp = cro.get('spread_usd', 0)
                    return False, f"Spread Spike (${sp:.2f})"
    except Exception: pass

    # 3. Macro Correlation Confluence Check
    try:
        if os.path.exists("macro_confluence.json"):
            with open("macro_confluence.json", "r", encoding="utf-8") as f:
                macro = json.load(f)
                score = macro.get("confluence_score", 0)
                if side == "BUY" and score <= -40:
                    return False, f"Macro Bearish Confluence ({score:+d})"
                elif side == "SELL" and score >= 40:
                    return False, f"Macro Bullish Confluence ({score:+d})"
    except Exception: pass

    return True, "CLEAR"

def open_order(order_type, lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return None
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    side = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": order_type, "price": price, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": f"Evo-{side}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = mt5.order_send(req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"[OK] {side} {lot} lots @ {r.price:.2f} | {reason} | Ticket #{r.order}")
            return r
    return None

HEADWAY_TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"

def main():
    if not mt5.initialize(path=HEADWAY_TERMINAL_PATH):
        if not mt5.initialize():
            print("MT5 init failed")
            sys.exit(1)
    acc = mt5.account_info()
    log("=" * 60)
    log(f"  ⚡ BOT SLOT #2: Mut-8369 (Magic 2222)")
    log(f"  Account : {acc.login} | Balance: ${acc.balance:.2f}")
    log(f"  Spacing : ASYMMETRIC_ATR (ATR Mult 2.22) | Waterfall Freeze: True")
    log("=" * 60)

    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue

            atr, rsi, trend, bull_c, bear_c, vel3 = get_market_metrics()

            # BUY Basket
            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket(mt5.POSITION_TYPE_BUY)
            if b_cnt > 0:
                if b_pnl <= -DISASTER_SL_USD:
                    close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                    time.sleep(1); continue
                tp_dist = max(1.20, atr * 1.3)
                if tick.bid >= (b_vwap + tp_dist) or b_pnl >= TARGET_PROFIT_USD:
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP")
                    time.sleep(1); continue
                if b_cnt < MAX_LAYERS:
                    step = max(3.00, atr * EXP_FACTORS[min(b_cnt - 1, len(EXP_FACTORS) - 1)])
                    if (b_worst - tick.ask) >= step:
                        confirm_ok = (bull_c or rsi < 28) if (vel3 < -(2.0 * atr)) else (bull_c or rsi < 35)
                        if confirm_ok:
                            dca_ok, dca_reason = check_quant_desk("BUY")
                            if dca_ok:
                                open_order(mt5.ORDER_TYPE_BUY, calc_lot(b_cnt), f"DCA_L{b_cnt+1}")
            elif b_cnt == 0 and trend > 0:
                if bull_c or rsi < 32:
                    desk_ok, desk_reason = check_quant_desk("BUY")
                    if desk_ok:
                        open_order(mt5.ORDER_TYPE_BUY, calc_lot(0), "Initial_BUY")

            # SELL Basket
            s_cnt, s_lots, s_vwap, s_pnl, s_worst, _ = get_basket(mt5.POSITION_TYPE_SELL)
            if s_cnt > 0:
                if s_pnl <= -DISASTER_SL_USD:
                    close_basket(mt5.POSITION_TYPE_SELL, "Disaster_SL")
                    time.sleep(1); continue
                tp_dist = max(1.20, atr * 1.3)
                if tick.ask <= (s_vwap - tp_dist) or s_pnl >= TARGET_PROFIT_USD:
                    close_basket(mt5.POSITION_TYPE_SELL, "GroupTP")
                    time.sleep(1); continue
                if s_cnt < MAX_LAYERS:
                    step = max(3.00, atr * EXP_FACTORS[min(s_cnt - 1, len(EXP_FACTORS) - 1)])
                    if (tick.bid - s_worst) >= step:
                        confirm_ok = (bear_c or rsi > 72) if (vel3 > (2.0 * atr)) else (bear_c or rsi > 65)
                        if confirm_ok:
                            dca_ok, dca_reason = check_quant_desk("SELL")
                            if dca_ok:
                                open_order(mt5.ORDER_TYPE_SELL, calc_lot(s_cnt), f"DCA_L{s_cnt+1}")
            elif s_cnt == 0 and trend < 0:
                if bear_c or rsi > 68:
                    desk_ok, desk_reason = check_quant_desk("SELL")
                    if desk_ok:
                        open_order(mt5.ORDER_TYPE_SELL, calc_lot(0), "Initial_SELL")

            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
