"""
========================================================================================
🎵 TIKTALK BOT 2.0 (Gold / XAUUSD)
Asset   : XAUUSD (Gold)
Platform: MetaTrader 5 (Headway MT5 Terminal, Account 6278930)
Magic   : 5555
Timeframe: M5
Strategy: 9/21 EMA Golden/Death Cross + RSI 14 + 200 EMA Trend Alignment + ATR Dynamic TP
========================================================================================
"""

import sys
import os
import time
from datetime import datetime, timezone
import pandas as pd
import numpy as np

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import MetaTrader5 as mt5

TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
MAGIC_NUMBER = 5555
BASE_LOT = 0.01
MAX_SPREAD_USD = 0.45
FAST_EMA = 9
SLOW_EMA = 21
RSI_PERIOD = 14
TARGET_PROFIT_USD = 4.00
DISASTER_STOP_USD = 85.00
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot5_tiktalk.log")

os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [TIKTALK-BOT] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def init_mt5():
    if not mt5.initialize():
        if not mt5.initialize(path=TERMINAL_PATH):
            log(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
    info = mt5.account_info()
    if info is None:
        log("❌ Failed to retrieve account info.")
        return False
    log(f" Connected to Headway MT5 | Login: {info.login} | Balance: ${info.balance:,.2f}")
    if not mt5.symbol_select(SYMBOL, True):
        return False
    return True

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def fetch_m5_data(bars=200):
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, bars)
    if rates is None or len(rates) < 60:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_fast'] = df['close'].ewm(span=FAST_EMA, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=SLOW_EMA, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['rsi'] = calculate_rsi(df['close'], period=RSI_PERIOD)
    return df

def get_active_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [p for p in positions if p.magic == MAGIC_NUMBER]

def execute_order(order_type, volume, comment):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return None
    spread = tick.ask - tick.bid
    if spread > MAX_SPREAD_USD:
        return None
    action_type = mt5.ORDER_TYPE_BUY if order_type == 'BUY' else mt5.ORDER_TYPE_SELL
    price = tick.ask if order_type == 'BUY' else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": volume,
        "type": action_type,
        "price": price,
        "sl": 0.0,
        "tp": 0.0,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        request["type_filling"] = mt5.ORDER_FILLING_FOK
        result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"✅ [TIKTALK EXECUTED] {order_type} {volume} lots @ {price:.2f} | {comment} | Ticket: #{result.order}")
        return result
    return None

def close_position(ticket):
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return False
    p = pos[0]
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return False
    close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": SYMBOL,
        "volume": p.volume,
        "type": close_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "TikTalk_TP_Close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    return res.retcode == mt5.TRADE_RETCODE_DONE

def run_tiktalk_loop():
    log("=" * 65)
    log("🎵 TIKTALK BOT 2.0 INITIALIZING (9/21 EMA + RSI + 200 EMA)")
    log(f"Asset: {SYMBOL} | Timeframe: M5 | Magic: {MAGIC_NUMBER}")
    log("=" * 65)
    if not init_mt5():
        sys.exit(1)
        
    last_processed_candle_time = None
    try:
        while True:
            time.sleep(5)
            df = fetch_m5_data(bars=100)
            if df is None:
                continue
            positions = get_active_positions()
            
            # Check Active Position TP / SL
            if len(positions) > 0:
                total_profit = sum(p.profit for p in positions)
                if total_profit >= TARGET_PROFIT_USD:
                    log(f"🎯 [TIKTALK TP HIT] +${total_profit:.2f} profit booked.")
                    for p in positions:
                        close_position(p.ticket)
                    continue
                elif total_profit <= -DISASTER_STOP_USD:
                    log(f"🛑 [TIKTALK SL HIT] -${abs(total_profit):.2f} disaster stop triggered.")
                    for p in positions:
                        close_position(p.ticket)
                    continue

            # Check Signal
            if len(positions) == 0:
                curr = df.iloc[-1]
                prev = df.iloc[-2]
                c_time = curr['time']
                if last_processed_candle_time == c_time:
                    continue
                last_processed_candle_time = c_time
                
                is_uptrend = curr['close'] > curr['ema200']
                is_downtrend = curr['close'] < curr['ema200']
                
                bullish_cross = (prev['ema_fast'] <= prev['ema_slow']) and (curr['ema_fast'] > curr['ema_slow'])
                bearish_cross = (prev['ema_fast'] >= prev['ema_slow']) and (curr['ema_fast'] < curr['ema_slow'])
                
                if (bullish_cross or (is_uptrend and curr['rsi'] <= 35)) and is_uptrend:
                    log(f"🎯 [TIKTALK BUY SIGNAL] Golden Cross / RSI Dip @ {curr['close']:.2f}")
                    execute_order('BUY', BASE_LOT, "TikTalk_Initial_BUY")
                elif (bearish_cross or (is_downtrend and curr['rsi'] >= 65)) and is_downtrend:
                    log(f"🎯 [TIKTALK SELL SIGNAL] Death Cross / RSI Peak @ {curr['close']:.2f}")
                    execute_order('SELL', BASE_LOT, "TikTalk_Initial_SELL")
    except KeyboardInterrupt:
        log("🛑 TikTalk bot shutting down gracefully...")
    finally:
        mt5.shutdown()

if __name__ == '__main__':
    run_tiktalk_loop()
