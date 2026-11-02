"""
M1 Confluence Scalper - DEMO ONLY forward test
Magic Number : 3333
Setting      : backtest_m1_hunt.py PASS config
               filters adx+bb+rsi | vol_k 6 | all hours | TP 0.2 ATR | SL 4 ATR | time stop 60 bars
Backtest     : 98 trades, 98.0% win, +$33.19, PF 2.63 (7 weeks M1, incl. untouched holdout)
Warning      : avg win ~$0.56 vs avg loss ~$10; +$0.20 extra cost per trade turns it negative.

Refuses to start on any account that is not a DEMO account.
Run:  python bot_m1_confluence_demo.py            (trades on demo)
      python bot_m1_confluence_demo.py --dry-run  (logs signals, sends no orders)
"""

from execution_gateway import guarded_order_send

import MetaTrader5 as mt5
import pandas as pd
import time, sys, os, csv
from datetime import datetime

import strategy_evolution_agent as sea
import backtest_m1_confluence as bc
import backtest_m1_hunt as hunt

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SYMBOL        = "XAUUSD"
MAGIC         = 3333
COMMENT       = "M1-Confluence-Demo"
LOT           = 0.01
FILTERS       = ('adx', 'bb', 'rsi')
VOL_K         = 6
HOURS         = (0, 24)
TP_ATR        = 0.2
SL_ATR        = 4.0
MAX_BARS      = 60          # minutes on M1
HISTORY_BARS  = 3000        # enough warm-up for EMA750 trend filter
SLIPPAGE      = 25
LOOP_INTERVAL = 2
DRY_RUN       = "--dry-run" in sys.argv
TRADE_LOG     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "m1_confluence_demo_trades.csv")

HEADWAY_TERMINAL_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [M1-CONF] {msg}", flush=True)

def record(row):
    os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
    new = not os.path.exists(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["time", "event", "side", "price", "sl", "tp", "ticket", "note"])
        w.writerow(row)

def latest_signal():
    """Signal on the last CLOSED M1 bar, computed exactly like the backtest."""
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 1, HISTORY_BARS)
    if rates is None or len(rates) < 1000:
        return 0, None, None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = bc.features(sea.enrich_features(df))
    sig_l, sig_s = hunt.sig(hunt.prep(df, VOL_K, HOURS), FILTERS)
    d = 1 if sig_l.iloc[-1] else -1 if sig_s.iloc[-1] else 0
    return d, float(df['atr14'].iloc[-1]), df['time'].iloc[-1]

def my_position():
    positions = mt5.positions_get(symbol=SYMBOL) or []
    mine = [p for p in positions if p.magic == MAGIC]
    return mine[0] if mine else None

def send(req):
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = guarded_order_send(mt5, req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            return r
    log(f"[FAIL] order rejected: {r.retcode if r else mt5.last_error()} {r.comment if r else ''}")
    return None

def open_trade(d, atr):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    side = "BUY" if d > 0 else "SELL"
    price = tick.ask if d > 0 else tick.bid
    sl = round(price - d * SL_ATR * atr, 2)
    tp = round(price + d * TP_ATR * atr, 2)
    if DRY_RUN:
        log(f"[DRY] would {side} {LOT} @ {price:.2f} SL {sl:.2f} TP {tp:.2f}")
        record([datetime.now().isoformat(), "DRY_OPEN", side, price, sl, tp, "", ""])
        return
    r = send({
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY if d > 0 else mt5.ORDER_TYPE_SELL, "price": price,
        "sl": sl, "tp": tp, "deviation": SLIPPAGE, "magic": MAGIC, "comment": COMMENT,
        "type_time": mt5.ORDER_TIME_GTC,
    })
    if r:
        log(f"[OPEN] {side} {LOT} @ {r.price:.2f} SL {sl:.2f} TP {tp:.2f} | Ticket #{r.order}")
        record([datetime.now().isoformat(), "OPEN", side, r.price, sl, tp, r.order, ""])

def close_trade(p, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    buy = p.type == mt5.POSITION_TYPE_BUY
    r = send({
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL if buy else mt5.ORDER_TYPE_BUY, "position": p.ticket,
        "price": tick.bid if buy else tick.ask, "deviation": SLIPPAGE, "magic": MAGIC,
        "comment": f"{COMMENT}-{reason}", "type_time": mt5.ORDER_TIME_GTC,
    })
    if r:
        log(f"[CLOSE] #{p.ticket} {reason} @ {r.price:.2f} | P/L ${p.profit:.2f}")
        record([datetime.now().isoformat(), "CLOSE", "BUY" if buy else "SELL", r.price, "", "", p.ticket, f"{reason} pnl={p.profit:.2f}"])

def main():
    if not mt5.initialize(path=HEADWAY_TERMINAL_PATH):
        if not mt5.initialize():
            print("MT5 init failed")
            sys.exit(1)
    acc = mt5.account_info()
    if acc is None or acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        print(f"REFUSING TO RUN: account {getattr(acc, 'login', '?')} on {getattr(acc, 'server', '?')} is not a DEMO account.")
        mt5.shutdown()
        sys.exit(1)
    mt5.symbol_select(SYMBOL, True)
    log("=" * 60)
    log(f"  M1 Confluence Scalper (Magic {MAGIC}) {'[DRY RUN - no orders]' if DRY_RUN else '[DEMO]'}")
    log(f"  Account : {acc.login} @ {acc.server} | Balance: {acc.balance:.2f} {acc.currency}")
    log(f"  Filters : {'+'.join(FILTERS)} | TP {TP_ATR} ATR | SL {SL_ATR} ATR | time stop {MAX_BARS} min")
    log("=" * 60)

    last_bar = None
    while True:
        try:
            # re-check every loop: stop if the terminal is switched to a live account
            a = mt5.account_info()
            if a is None or a.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
                log(f"[STOP] account {getattr(a, 'login', '?')} is not DEMO anymore. Exiting.")
                break
            p = my_position()
            tick = mt5.symbol_info_tick(SYMBOL)
            # position time and tick time are both broker server time
            if p and tick and (tick.time - p.time) >= MAX_BARS * 60:
                close_trade(p, "TimeStop")
                p = None

            d, atr, bar_time = latest_signal()
            if bar_time is not None and bar_time != last_bar:
                last_bar = bar_time
                if d and p is None:
                    open_trade(d, atr)

            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"[ERR] {e}")
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
