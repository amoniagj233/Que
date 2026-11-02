"""
========================================================================================
🏛️ SMC LIQUIDITY & BREAKER BLOCK SNIPER (Gold / XAUUSD)
Strategy: Institutional Smart Money Concepts (SMC) + Liquidity Sweep & Breaker Retest
Asset   : XAUUSD (Gold)
Platform: MetaTrader 5 (Headway MT5 Terminal, Account 6278930)
Magic   : 3333
Timeframe: M5 (Noise-filtered execution) with H1/200 EMA Trend Alignment
========================================================================================
"""

import sys
import os
import time
import math
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Force UTF-8 encoding on Windows console
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import MetaTrader5 as mt5

# --- CONFIGURATION ---
TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
MAGIC_NUMBER = 3333
BASE_LOT = 0.02              # Base lot size per order (split into 2 tranches: 0.01 TP1, 0.01 Runner)
MAX_SPREAD_USD = 0.45        # Max allowable spread on Gold ($0.45/oz)
RISK_REWARD_RUNNER = 2.8     # Runner Target (1:2.8 R:R)
TP1_RR = 1.2                 # First scale-out target (1:1.2 R:R)
SWING_DEPTH = 4              # Pivot lookback depth
EMA_FILTER_PERIOD = 200      # Macro trend anchor
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot3_smc_sniper.log")

os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [SMC-SNIPER] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def init_mt5():
    # If terminal is already running, standard initialize connects instantly
    if not mt5.initialize():
        if not mt5.initialize(path=TERMINAL_PATH):
            log(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
    info = mt5.account_info()
    if info is None:
        log("❌ Failed to retrieve account info.")
        return False
    log(f" Connected to Headway MT5 | Login: {info.login} | Balance: ${info.balance:,.2f} | Equity: ${info.equity:,.2f}")
    if not mt5.symbol_select(SYMBOL, True):
        log(f"❌ Failed to select {SYMBOL}")
        return False
    return True

def fetch_m5_data(bars=300):
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, bars)
    if rates is None or len(rates) < 100:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # 200 EMA
    df['ema200'] = df['close'].ewm(span=EMA_FILTER_PERIOD, adjust=False).mean()
    
    # ATR 14
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(1.5)
    
    # Swing Detection
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    d = SWING_DEPTH
    for i in range(d, n - d):
        if highs[i] == np.max(highs[i - d : i + d + 1]):
            sh[i] = highs[i]
        if lows[i] == np.min(lows[i - d : i + d + 1]):
            sl[i] = lows[i]
            
    df['sh'] = sh
    df['sl'] = sl
    return df

def get_active_smc_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [p for p in positions if p.magic == MAGIC_NUMBER]

def execute_order(order_type, volume, price, sl, tp, comment):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return None
    
    spread = tick.ask - tick.bid
    if spread > MAX_SPREAD_USD:
        log(f"⚠️ Spread too high ({spread:.2f} > {MAX_SPREAD_USD}). Skipping trade.")
        return None

    action_type = mt5.ORDER_TYPE_BUY if order_type == 'BUY' else mt5.ORDER_TYPE_SELL
    exec_price = tick.ask if order_type == 'BUY' else tick.bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": volume,
        "type": action_type,
        "price": exec_price,
        "sl": round(sl, 2),
        "tp": round(tp, 2) if tp > 0 else 0.0,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        # Fallback to FOK
        request["type_filling"] = mt5.ORDER_FILLING_FOK
        result = mt5.order_send(request)
        
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"✅ [ORDER EXECUTED] {order_type} {volume} lots @ {exec_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | Ticket: #{result.order}")
        return result
    else:
        log(f"❌ Order failed: {result.comment} (code {result.retcode})")
        return None

def manage_open_trades(df):
    positions = get_active_smc_positions()
    if not positions:
        return
        
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return
        
    curr_close = df.iloc[-1]['close']
    
    for pos in positions:
        # Check if stop loss needs to be moved to breakeven after TP1 reached
        ticket = pos.ticket
        pos_type = pos.type # 0: BUY, 1: SELL
        entry = pos.price_open
        current_sl = pos.sl
        comment = pos.comment
        
        # If position profit is > 1.2R, secure breakeven stop loss
        if "TP1" in comment and pos.profit > 0:
            pass # Already scaled
            
        # Trailing Breakeven logic
        if pos_type == mt5.ORDER_TYPE_BUY:
            if current_sl < entry and (tick.bid - entry) >= 2.50:
                new_sl = round(entry + 0.20, 2) # BE + small buffer
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": new_sl,
                    "tp": pos.tp
                }
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    log(f"🛡️ [BREAKEVEN SECURED] BUY #{ticket} SL moved to {new_sl:.2f}")
        elif pos_type == mt5.ORDER_TYPE_SELL:
            if (current_sl > entry or current_sl == 0) and (entry - tick.ask) >= 2.50:
                new_sl = round(entry - 0.20, 2)
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": new_sl,
                    "tp": pos.tp
                }
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    log(f"🛡️ [BREAKEVEN SECURED] SELL #{ticket} SL moved to {new_sl:.2f}")

def run_sniper_loop():
    log("=" * 65)
    log("🏛️ SMC LIQUIDITY & BREAKER BLOCK SNIPER INITIALIZING")
    log(f"Asset: {SYMBOL} | Timeframe: M5 | Magic: {MAGIC_NUMBER}")
    log(f"Macro Filter: 200 EMA | Scale Target: 1:{RISK_REWARD_RUNNER} R:R")
    log("=" * 65)
    
    if not init_mt5():
        sys.exit(1)
        
    last_processed_candle_time = None
    
    try:
        while True:
            # Sleep 5 seconds between ticks
            time.sleep(5)
            
            df = fetch_m5_data(bars=250)
            if df is None:
                continue
                
            manage_open_trades(df)
            
            latest_candle = df.iloc[-1]
            c_time = latest_candle['time']
            
            # Run entry evaluations when a new M5 candle appears
            if last_processed_candle_time == c_time:
                continue
                
            last_processed_candle_time = c_time
            
            # Check active position count (Max 1 set per direction)
            active_positions = get_active_smc_positions()
            if len(active_positions) >= 2:
                continue
                
            # Current session filter (07:00 to 20:00 UTC)
            hour = datetime.now(timezone.utc).hour
            if hour < 7 or hour > 20:
                continue
                
            # Completed candles
            curr = df.iloc[-2] # Completed bar
            prev1 = df.iloc[-3]
            prev2 = df.iloc[-4]
            
            recent_sh = df.iloc[-50:-3]['sh'].dropna()
            recent_sl = df.iloc[-50:-3]['sl'].dropna()
            
            if len(recent_sh) == 0 or len(recent_sl) == 0:
                continue
                
            last_sh = recent_sh.iloc[-1]
            last_sl = recent_sl.iloc[-1]
            atr = curr['atr']
            
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                continue
                
            # 1. BULLISH SMC SETUP: Liquidity Sweep of Lows + Bullish Rejection
            bullish_sweep = (prev1['low'] < last_sl) and (curr['close'] > last_sl) and (curr['close'] > curr['ema200'])
            if bullish_sweep and (curr['close'] > curr['open']) and not any(p.type == mt5.ORDER_TYPE_BUY for p in active_positions):
                entry_price = tick.ask
                sl_price = round(min(prev1['low'], curr['low']) - (atr * 0.25), 2)
                risk = entry_price - sl_price
                if 0.80 <= risk <= 5.00:
                    tp1 = round(entry_price + (risk * TP1_RR), 2)
                    tp2 = round(entry_price + (risk * RISK_REWARD_RUNNER), 2)
                    log(f"🎯 [BULLISH LIQUIDITY SWEEP DETECTED] Sweep Low: {last_sl:.2f} | Close: {curr['close']:.2f}")
                    # Order 1: TP1 Partial Target
                    execute_order('BUY', BASE_LOT / 2.0, entry_price, sl_price, tp1, "SMC_TP1_Scale")
                    # Order 2: TP2 Runner Target
                    execute_order('BUY', BASE_LOT / 2.0, entry_price, sl_price, tp2, "SMC_Runner")
                    
            # 2. BEARISH SMC SETUP: Liquidity Sweep of Highs + Bearish Rejection
            bearish_sweep = (prev1['high'] > last_sh) and (curr['close'] < last_sh) and (curr['close'] < curr['ema200'])
            if bearish_sweep and (curr['close'] < curr['open']) and not any(p.type == mt5.ORDER_TYPE_SELL for p in active_positions):
                entry_price = tick.bid
                sl_price = round(max(prev1['high'], curr['high']) + (atr * 0.25), 2)
                risk = sl_price - entry_price
                if 0.80 <= risk <= 5.00:
                    tp1 = round(entry_price - (risk * TP1_RR), 2)
                    tp2 = round(entry_price - (risk * RISK_REWARD_RUNNER), 2)
                    log(f"🎯 [BEARISH LIQUIDITY SWEEP DETECTED] Sweep High: {last_sh:.2f} | Close: {curr['close']:.2f}")
                    # Order 1: TP1 Partial Target
                    execute_order('SELL', BASE_LOT / 2.0, entry_price, sl_price, tp1, "SMC_TP1_Scale")
                    # Order 2: TP2 Runner Target
                    execute_order('SELL', BASE_LOT / 2.0, entry_price, sl_price, tp2, "SMC_Runner")
                    
    except KeyboardInterrupt:
        log("🛑 SMC Sniper shutting down gracefully on user interrupt...")
    finally:
        mt5.shutdown()
        log("🔌 MT5 disconnected.")

if __name__ == '__main__':
    run_sniper_loop()
