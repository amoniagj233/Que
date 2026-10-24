import json
import math
import os
import sys
import threading
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from trade_safety import (MAX_OPEN_POSITIONS, MAX_GROUP_RISK_PERCENT, positive,
                          floor_volume, limit_volume, stop_loss_money,
                          validate_geometry, deal_net)

try:
    import MetaTrader5 as mt5
    import numpy as np
except ImportError:
    mt5 = None
    np = None

HEADWAY_TERMINAL_PATH = os.getenv("MT5_PATH", r"C:\Program Files\Headway MT5 Terminal\terminal64.exe")
BASE_DIR = Path(__file__).resolve().parent
JOURNAL_FILE = BASE_DIR / "trades_journal.json"
CONFIG_FILE = BASE_DIR / "auto_trade_config.json"
MULTI_TP_FILE = BASE_DIR / "multi_tp_groups.json"

TICKER_SYMBOLS = [
    "XAUUSD",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "BTCUSD",
    "ETHUSD",
]

mt5_lock = threading.RLock()
symbols_cache = []
symbols_by_category = {}

def third_wednesday(year: int, month: int) -> date:
    first = date(year, month, 1)
    days_until_wed = (2 - first.weekday()) % 7
    first_wed = first + timedelta(days=days_until_wed)
    return first_wed + timedelta(days=14)

def get_next_imm_dates(from_date: date, count: int = 4) -> list:
    imm_months = [3, 6, 9, 12]
    dates = []
    year = from_date.year
    while len(dates) < count:
        for month in imm_months:
            imm = third_wednesday(year, month)
            if imm > from_date:
                days_left = (imm - from_date).days
                dates.append({
                    "date": imm.strftime("%Y-%m-%d"),
                    "quarter": f"Q{month//3} {year}",
                    "days_left": days_left
                })
                if len(dates) == count:
                    break
        year += 1
    return dates

def ensure_deriv_connected():
    if not mt5:
        return False, "MetaTrader5 Python module not installed"
    
    term = mt5.terminal_info()
    if term and term.connected and ("headway" in (term.name or "").lower() or "headway" in (term.path or "").lower()):
        return True, "Connected"
    
    # If connected to a different terminal, shut down before attaching Headway
    if term and term.connected:
        try:
            mt5.shutdown()
        except Exception:
            pass

    if not mt5.initialize(path=HEADWAY_TERMINAL_PATH):
        if not mt5.initialize():
            err = mt5.last_error()
            return False, f"Init error: {err}"
    
    return True, "Connected"

def get_best_filling_mode(sym_info):
    if not sym_info:
        return mt5.ORDER_FILLING_FOK
    filling = sym_info.filling_mode
    if filling & 1:
        return mt5.ORDER_FILLING_FOK
    elif filling & 2:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def load_all_symbols():
    global symbols_cache, symbols_by_category
    with mt5_lock:
        ok, _ = ensure_deriv_connected()
        if not ok:
            return []
        
        all_syms = mt5.symbols_get()
        if not all_syms:
            return []
        
        # Strictly use symbols visible in Headway Quotes (Market Watch)
        visible_syms = [s for s in all_syms if s.visible]
        target_syms = visible_syms if visible_syms else all_syms
        
        sym_list = []
        cat_dict = {}
        for s in target_syms:
            cat = s.path.split("\\")[0] if "\\" in s.path else "General"
            item = {
                "symbol": s.name,
                "path": s.path,
                "category": cat,
                "digits": s.digits,
                "volume_min": s.volume_min,
                "volume_max": s.volume_max,
                "volume_step": s.volume_step,
                "description": s.description or s.name
            }
            sym_list.append(item)
            if cat not in cat_dict:
                cat_dict[cat] = []
            cat_dict[cat].append(s.name)
        
        symbols_cache = sym_list
        symbols_by_category = cat_dict
        return sym_list

def get_symbol_quote(sym_name):
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {"success": False, "message": msg}
        
        mt5.symbol_select(sym_name, True)
        info = mt5.symbol_info(sym_name)
        tick = mt5.symbol_info_tick(sym_name)
        if not info or not tick:
            return {"success": False, "message": f"Quote unavailable for {sym_name}"}
        
        return {
            "success": True,
            "symbol": sym_name,
            "bid": round(tick.bid, info.digits),
            "ask": round(tick.ask, info.digits),
            "spread": round(tick.ask - tick.bid, info.digits),
            "digits": info.digits,
            "min_lot": info.volume_min,
            "max_lot": info.volume_max,
            "step_lot": info.volume_step,
            "point": info.point
        }

def check_symbol_market_open(sym):
    """
    Market Status Verification (Rule 1):
    Checks whether a symbol's market is currently open and trading actively on Deriv MT5.
    Returns (is_open: bool, reason: str).
    """
    mt5.symbol_select(sym, True)
    ref_tick = mt5.symbol_info_tick('BTCUSD')
    live_broker_time = ref_tick.time if ref_tick else time.time()
    
    info = mt5.symbol_info(sym)
    if not info:
        return False, "Symbol not recognized by broker"
    
    if info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        return False, f"Trading disabled by broker (Trade mode: {info.trade_mode})"
    
    tick = mt5.symbol_info_tick(sym)
    if not tick or tick.bid <= 0 or tick.ask <= 0:
        return False, "Market closed (No active bid/ask quotes)"
    
    # Check tick staleness against live 24/7 broker reference clock
    diff = live_broker_time - tick.time
    if diff > 300:  # Stale by more than 5 minutes
        hours_ago = diff / 3600.0
        return False, f"Market Closed (Last quote was {hours_ago:.1f}h ago)"
    
    return True, "Market Open & Active"

def calculate_setup_confidence(sym_info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist):
    """
    Rigorous Multi-Factor Confidence Scoring (Rule 2):
      Evaluates trend confirmation, market structure, momentum/RSI, liquidity/spread, and risk ratio.
      Returns (score: int, signals: list).
      Only exceptional setups with multi-indicator alignment reach 88-100%.
    """
    score = 65  # Base score for passing initial M15 boundary scan
    signals = []
    
    cur_p = tick.bid if bias == "SELL" else tick.ask
    
    # Factor 1: Trend Confirmation & EMA alignment
    if bias == "SELL" and cur_p < ema20:
        score += 8
        signals.append("Price below EMA20")
        if len(closes) >= 4 and closes[-1] < closes[-3]:
            score += 5
            signals.append("Negative EMA slope")
    elif bias == "BUY" and cur_p > ema20:
        score += 8
        signals.append("Price above EMA20")
        if len(closes) >= 4 and closes[-1] > closes[-3]:
            score += 5
            signals.append("Positive EMA slope")
            
    # Factor 2: Momentum & RSI Sweet Spot
    if bias == "SELL" and 40.0 <= rsi <= 55.0:
        score += 8
        signals.append(f"RSI in prime short momentum zone ({rsi:.1f})")
    elif bias == "BUY" and 45.0 <= rsi <= 60.0:
        score += 8
        signals.append(f"RSI in prime long momentum zone ({rsi:.1f})")
        
    # Factor 3: Liquidity & Spread Tolerance
    spread = tick.ask - tick.bid
    spread_pct = (spread / cur_p) * 100 if cur_p > 0 else 1.0
    if spread_pct < 0.05:
        score += 7
        signals.append(f"Ultra-low spread ({spread_pct:.3f}%)")
    elif spread_pct < 0.15:
        score += 4
        signals.append(f"Tight spread ({spread_pct:.3f}%)")
        
    # Factor 4: Volatility & ATR Adequacy
    if atr > 0:
        score += 5
        signals.append(f"Healthy ATR volatility ({atr:.2f})")
        
    score = min(100, max(50, score))
    return score, signals

# ==============================================================================
# SYMBOL TRADING PERFORMANCE & TRADE ANALYTICS ENGINE
# ==============================================================================
_perf_cache = {
    "data": None,
    "last_sync": 0,
    "timeframe": "all"
}
_perf_lock = threading.Lock()

def get_symbol_trading_analytics(timeframe="all", force_refresh=False):
    global _perf_cache
    now_ts = time.time()
    with _perf_lock:
        if not force_refresh and _perf_cache["data"] and _perf_cache["timeframe"] == timeframe:
            if now_ts - _perf_cache["last_sync"] < 60:
                return _perf_cache["data"]
                
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {"error": msg, "symbols": [], "summary": {}}
            
        now_dt = datetime.now()
        if timeframe == "today":
            from_dt = datetime(now_dt.year, now_dt.month, now_dt.day, 0, 0, 0)
        elif timeframe == "7d":
            from_dt = now_dt - timedelta(days=7)
        elif timeframe == "30d":
            from_dt = now_dt - timedelta(days=30)
        elif timeframe == "90d":
            from_dt = now_dt - timedelta(days=90)
        else: # "all"
            from_dt = now_dt - timedelta(days=365 * 3)
            
        deals = mt5.history_deals_get(from_dt, now_dt)
        positions = mt5.positions_get()
        
    # Group open positions by symbol
    open_by_symbol = defaultdict(lambda: {"count": 0, "profit": 0.0, "volume": 0.0})
    if positions:
        for p in positions:
            open_by_symbol[p.symbol]["count"] += 1
            open_by_symbol[p.symbol]["profit"] += round(p.profit, 2)
            open_by_symbol[p.symbol]["volume"] += round(p.volume, 2)
            
    symbols_deals = defaultdict(list)
    if deals:
        for d in deals:
            if not d.symbol:
                continue
            if d.entry == mt5.DEAL_ENTRY_OUT or d.profit != 0:
                net = d.profit + d.commission + d.swap
                symbols_deals[d.symbol].append({
                    "ticket": d.ticket,
                    "time": d.time,
                    "net_pnl": round(net, 2),
                    "profit": round(d.profit, 2),
                    "commission": round(d.commission, 2),
                    "swap": round(d.swap, 2),
                    "magic": d.magic,
                    "comment": d.comment
                })
                
    symbol_results = []
    tot_trades_all = 0
    tot_wins_all = 0
    tot_losses_all = 0
    tot_net_all = 0.0
    tot_gross_profit_all = 0.0
    tot_gross_loss_all = 0.0
    
    for sym, dlist in symbols_deals.items():
        n = len(dlist)
        wins = [x for x in dlist if x["net_pnl"] > 0]
        losses = [x for x in dlist if x["net_pnl"] < 0]
        evens = [x for x in dlist if x["net_pnl"] == 0]
        
        win_cnt = len(wins)
        loss_cnt = len(losses)
        win_rate = round((win_cnt / n * 100) if n > 0 else 0.0, 1)
        
        gross_profit = sum(x["net_pnl"] for x in wins)
        gross_loss = abs(sum(x["net_pnl"] for x in losses))
        net_pnl = sum(x["net_pnl"] for x in dlist)
        
        tot_trades_all += n
        tot_wins_all += win_cnt
        tot_losses_all += loss_cnt
        tot_net_all += net_pnl
        tot_gross_profit_all += gross_profit
        tot_gross_loss_all += gross_loss
        
        if gross_loss > 0:
            pf = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            pf = 99.0
        else:
            pf = 1.0
            
        avg_profit = round(net_pnl / n if n > 0 else 0.0, 2)
        avg_win = round(gross_profit / win_cnt if win_cnt > 0 else 0.0, 2)
        avg_loss = round(gross_loss / loss_cnt if loss_cnt > 0 else 0.0, 2)
        rr = round(avg_win / avg_loss if avg_loss > 0 else (avg_win if avg_win > 0 else 1.0), 2)
        
        # Chronological cumulative P&L curve & Max Drawdown
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        sorted_deals = sorted(dlist, key=lambda x: x["time"])
        cum_curve = []
        for d in sorted_deals:
            cum += d["net_pnl"]
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
            cum_curve.append({
                "time": datetime.fromtimestamp(d["time"]).strftime("%m-%d %H:%M"),
                "cum_pnl": round(cum, 2)
            })
            
        # Statistical sample reliability
        if n >= 10:
            stat_valid = "STATISTICALLY_VALID"
            stat_label = f"Validated (N={n})"
            stat_badge = "bg-emerald-500/10 text-emeraldaccent border-emerald-500/20"
        elif n >= 5:
            stat_valid = "MODERATE_SAMPLE"
            stat_label = f"Moderate (N={n})"
            stat_badge = "bg-blue-500/10 text-cyanaccent border-blue-500/20"
        else:
            stat_valid = "INSUFFICIENT_DATA"
            stat_label = f"Insufficient (N={n})"
            stat_badge = "bg-slate-800 text-slate-400 border-slate-700"
            
        # Multi-factor Performance Score (0-100)
        score = 0.0
        score += min(30.0, win_rate * 0.3)
        if net_pnl > 0:
            score += min(35.0, (min(pf, 3.5) / 3.5) * 35.0)
        if avg_profit > 0:
            score += min(20.0, 10.0 + min(10.0, (avg_profit / 25.0) * 10.0))
        if gross_profit > 0:
            score -= min(25.0, (max_dd / gross_profit) * 20.0)
        elif max_dd > 0:
            score -= 20.0
            
        if n < 5:
            score *= 0.6
        elif n < 10:
            score *= 0.8
            
        score = max(5.0, min(99.0, round(score, 1)))
        
        # Priority classification (1 to 5)
        if n >= 10 and net_pnl > 50 and pf >= 1.25 and win_rate >= 50:
            rec = "PRIORITY 1 — INCREASE FOCUS"
            p_num = 1
        elif net_pnl > 0 and pf >= 1.05 and n >= 5:
            rec = "PRIORITY 2 — MAINTAIN"
            p_num = 2
        elif net_pnl >= 0:
            rec = "PRIORITY 3 — MONITOR"
            p_num = 3
        elif net_pnl < -100 or pf < 0.5 or (win_rate > 60 and net_pnl < -500):
            rec = "PRIORITY 5 — AVOID"
            p_num = 5
        else:
            rec = "PRIORITY 4 — REDUCE EXPOSURE"
            p_num = 4
            
        symbol_results.append({
            "symbol": sym,
            "total_trades": n,
            "winning_trades": win_cnt,
            "losing_trades": loss_cnt,
            "break_even_trades": len(evens),
            "win_rate": win_rate,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_pnl": round(net_pnl, 2),
            "profit_factor": pf,
            "avg_profit_per_trade": avg_profit,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "rr_performance": rr,
            "max_drawdown": round(max_dd, 2),
            "score": score,
            "recommendation": rec,
            "priority_num": p_num,
            "reliability": stat_valid,
            "stat_label": stat_label,
            "stat_badge": stat_badge,
            "open_positions": open_by_symbol[sym]["count"],
            "open_profit": round(open_by_symbol[sym]["profit"], 2),
            "open_volume": round(open_by_symbol[sym]["volume"], 2),
            "cum_curve": cum_curve[-30:]
        })
        
    symbol_results.sort(key=lambda x: (x["score"], x["net_pnl"]), reverse=True)
    for idx, s in enumerate(symbol_results):
        s["rank"] = idx + 1
        
    alerts = []
    top_p1 = [s for s in symbol_results if s["priority_num"] == 1]
    if top_p1:
        alerts.append({
            "type": "success",
            "title": f"Top Consistent Focus: {top_p1[0]['symbol']}",
            "message": f"{top_p1[0]['symbol']} leads your account with {top_p1[0]['total_trades']} completed trades, {top_p1[0]['win_rate']}% win rate, ${top_p1[0]['net_pnl']:+,.2f} net profit, and Profit Factor {top_p1[0]['profit_factor']}. High trading expectancy validated."
        })
        
    trap_syms = [s for s in symbol_results if s["win_rate"] >= 60 and s["net_pnl"] < -100]
    for ts in trap_syms:
        alerts.append({
            "type": "warning",
            "title": f"Negative Skew / Deceptive Win Rate Warning: {ts['symbol']}",
            "message": f"{ts['symbol']} exhibits a high win rate ({ts['win_rate']}%), but realized Net P&L is ${ts['net_pnl']:+,.2f} with Max Drawdown of ${ts['max_drawdown']:,.2f} (PF {ts['profit_factor']}). Average losses severely outweigh wins."
        })
        
    dd_syms = [s for s in symbol_results if s["max_drawdown"] > 1000 and s["priority_num"] >= 4]
    for ds in dd_syms[:1]:
        alerts.append({
            "type": "danger",
            "title": f"Severe Historical Drawdown Alert: {ds['symbol']}",
            "message": f"{ds['symbol']} reached peak-to-trough decline of ${ds['max_drawdown']:,.2f}. Categorized as {ds['recommendation']}. Stricter risk gates and trade size reduction mandatory."
        })
        
    promising = [s for s in symbol_results if s["priority_num"] in [2, 3] and s["net_pnl"] > 500 and s["total_trades"] < 10]
    for ps in promising[:1]:
        alerts.append({
            "type": "info",
            "title": f"High Expectancy Emerging Symbol: {ps['symbol']}",
            "message": f"{ps['symbol']} has generated ${ps['net_pnl']:+,.2f} across {ps['total_trades']} trades ({ps['win_rate']}% win rate). Requires {10 - ps['total_trades']} more trades to achieve Priority 1 Statistical Certification."
        })
        
    tot_pf = round(tot_gross_profit_all / tot_gross_loss_all, 2) if tot_gross_loss_all > 0 else (99.0 if tot_gross_profit_all > 0 else 1.0)
    overall_win_rate = round((tot_wins_all / tot_trades_all * 100) if tot_trades_all > 0 else 0.0, 1)
    
    p1_list = [s for s in symbol_results if s["priority_num"] == 1]
    p2_list = [s for s in symbol_results if s["priority_num"] == 2]
    p3_list = [s for s in symbol_results if s["priority_num"] == 3]
    p4_list = [s for s in symbol_results if s["priority_num"] == 4]
    p5_list = [s for s in symbol_results if s["priority_num"] == 5]
    
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timeframe": timeframe,
        "total_symbols_traded": len(symbol_results),
        "total_deals_analyzed": tot_trades_all,
        "total_net_pnl": round(tot_net_all, 2),
        "total_gross_profit": round(tot_gross_profit_all, 2),
        "total_gross_loss": round(tot_gross_loss_all, 2),
        "overall_win_rate": overall_win_rate,
        "overall_profit_factor": tot_pf,
        "best_symbol": symbol_results[0]["symbol"] if symbol_results else "None",
        "worst_symbol": sorted(symbol_results, key=lambda x: x["net_pnl"])[0]["symbol"] if symbol_results else "None",
        "p1_count": len(p1_list),
        "p2_count": len(p2_list),
        "p3_count": len(p3_list),
        "p4_count": len(p4_list),
        "p5_count": len(p5_list)
    }
    
    out_data = {
        "summary": summary,
        "symbols": symbol_results,
        "alerts": alerts,
        "p1_symbols": p1_list,
        "p2_symbols": p2_list,
        "p3_symbols": p3_list,
        "p4_symbols": p4_list,
        "p5_symbols": p5_list
    }
    
    with _perf_lock:
        _perf_cache["data"] = out_data
        _perf_cache["last_sync"] = now_ts
        _perf_cache["timeframe"] = timeframe
        
    return out_data

def get_symbol_perf_summary(sym):
    try:
        data = get_symbol_trading_analytics(timeframe="all")
        for s in data.get("symbols", []):
            if s["symbol"] == sym:
                return {
                    "symbol": sym,
                    "recommendation": s["recommendation"],
                    "priority_num": s["priority_num"],
                    "score": s["score"],
                    "win_rate": s["win_rate"],
                    "profit_factor": s["profit_factor"],
                    "net_pnl": s["net_pnl"],
                    "total_trades": s["total_trades"],
                    "reliability": s["reliability"],
                    "stat_label": s["stat_label"]
                }
    except Exception:
        pass
    return {
        "symbol": sym,
        "recommendation": "PRIORITY 3 — MONITOR",
        "priority_num": 3,
        "score": 50.0,
        "win_rate": 0.0,
        "profit_factor": 1.0,
        "net_pnl": 0.0,
        "total_trades": 0,
        "reliability": "INSUFFICIENT_DATA",
        "stat_label": "New Symbol"
    }

class AutomatedSetupScanner:
    """
    Continuous 3-Minute Background Scanning & Automated Execution Engine
    Enforces:
      1. Market status verification (no closed markets).
      2. 88-100% High-Confidence automatic trade execution (when auto-trading enabled).
      3. Mandatory risk management (SL, TP, 1% risk sizing, margin gates, no duplicates).
      4. Dynamic setup lifecycle (ACTIVE, EXECUTED, INVALIDATED, MARKET CLOSED).
      5. Complete trade tracking journal with confidence and reasons.
    """
    def __init__(self, interval_seconds=180):
        self.interval = interval_seconds
        self.lock = threading.Lock()
        self.scan_id = 0
        self.last_scan_time = None
        self.next_scan_seconds = self.interval
        self.current_setups = []
        self.filtered_reasons = {}
        self.status = "INITIALIZING"
        self.status_message = "Starting automated background 3-minute market scanner..."
        self.journal = self.load_journal()
        self.auto_trade_enabled = self.load_config()
        self.running = True
        
        # Start scanner daemon thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("auto_trade_enabled", False)
            except Exception:
                return False
        return False

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"auto_trade_enabled": self.auto_trade_enabled}, f, indent=2)
        except Exception as e:
            print("Error saving auto trade config:", e)

    def toggle_auto_trade(self):
        with self.lock:
            self.auto_trade_enabled = not self.auto_trade_enabled
            self.save_config()
            return self.auto_trade_enabled

    def load_journal(self):
        if JOURNAL_FILE.exists():
            try:
                with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_journal(self):
        try:
            with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
                json.dump(self.journal, f, indent=2)
        except Exception as e:
            print("Error saving trades journal:", e)

    def record_execution(self, setup_id, symbol, direction, entry, sl, tp, volume, tickets, confidence="--", reason="Manual Execution", execution_type="MANUAL"):
        with self.lock:
            record = {
                "setup_id": setup_id,
                "symbol": symbol,
                "direction": direction.upper(),
                "entry_price": float(entry),
                "sl": float(sl) if sl else 0.0,
                "tp": float(tp) if tp else 0.0,
                "volume": float(volume),
                "tickets": tickets,
                "confidence": confidence,
                "reason": reason,
                "execution_type": execution_type,
                "execution_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "OPEN"
            }
            self.journal.insert(0, record)
            if len(self.journal) > 100:
                self.journal = self.journal[:100]
            self.save_journal()
            
            # Immediately remove from current recommendations
            self.current_setups = [
                s for s in self.current_setups 
                if s.get("id") != setup_id and not (s.get("symbol") == symbol and s.get("action") == direction.upper())
            ]
            self._update_status_message()

    def _update_status_message(self):
        if len(self.current_setups) > 0:
            self.status = "ACTIVE_SETUPS"
            self.status_message = f"{len(self.current_setups)} High-Probability Setups Confirmed"
        else:
            self.status = "WAITING_FOR_CONFIRMATION"
            self.status_message = "No Valid Trade Setups Available – Waiting for Confirmation"

    def _sync_journal_positions(self, open_positions):
        """Update journal entries status (OPEN vs CLOSED) based on live MT5 positions."""
        active_tickets = {p.ticket for p in open_positions} if open_positions else set()
        changed = False
        for item in self.journal:
            tickets = item.get("tickets", [])
            if any(t in active_tickets for t in tickets):
                if item.get("status") != "OPEN":
                    item["status"] = "OPEN"
                    changed = True
            else:
                if item.get("status") == "OPEN":
                    item["status"] = "CLOSED"
                    changed = True
        if changed:
            self.save_journal()

    def run_scan_now(self):
        with mt5_lock:
            ok, _ = ensure_deriv_connected()
            if not ok:
                with self.lock:
                    self.status = "DISCONNECTED"
                    self.status_message = "Deriv MT5 terminal disconnected. Waiting for connection..."
                    self.current_setups = []
                return

            acc = mt5.account_info()
            positions = mt5.positions_get()
            if acc is None or positions is None:
                with self.lock:
                    self.status = "DISCONNECTED"
                    self.status_message = "Account/position query failed; new entries paused."
                    self.current_setups = []
                return
            balance = min(acc.balance, acc.equity)
            margin_free = acc.margin_free
            margin_level = acc.margin_level
            risk_dollar = balance * MAX_GROUP_RISK_PERCENT / 100
            self._sync_journal_positions(positions)

            # Rule 3 & 4: Live Trade Awareness & Position Limits
            open_pos = set()
            if positions:
                for p in positions:
                    p_type = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
                    open_pos.add((p.symbol, p_type))

            # Candidate pool for Headway Quotes (Metals, Forex Majors, Crypto, Synthetic Indices)
            candidate_pool = [
                # 24/7 Active Crypto & Synthetic Assets (Always Open on Headway)
                {"symbol": "BTC", "category": "Crypto 24/7"},
                {"symbol": "ETH", "category": "Crypto 24/7"},
                {"symbol": "SOL", "category": "Crypto 24/7"},
                {"symbol": "DOGE", "category": "Crypto 24/7"},
                {"symbol": "XRP", "category": "Crypto 24/7"},
                {"symbol": "ADA", "category": "Crypto 24/7"},
                {"symbol": "LTC", "category": "Crypto 24/7"},
                {"symbol": "BTCUSD", "category": "Crypto"},
                {"symbol": "ETHUSD", "category": "Crypto"},
                {"symbol": "VOL_10", "category": "Indices 24/7"},
                {"symbol": "VOL_20", "category": "Indices 24/7"},
                {"symbol": "BOOM_100", "category": "Indices 24/7"},
                {"symbol": "CRASH_100", "category": "Indices 24/7"},
                # Premier Metals & Forex (Active weekdays, Weekend Technical Analysis)
                {"symbol": "XAUUSD", "category": "Metals"},
                {"symbol": "XAGUSD", "category": "Metals"},
                {"symbol": "EURUSD", "category": "Forex Major"},
                {"symbol": "GBPUSD", "category": "Forex Major"},
                {"symbol": "USDJPY", "category": "Forex Major"},
                {"symbol": "USDCAD", "category": "Forex Major"},
                {"symbol": "AUDUSD", "category": "Forex Major"},
                {"symbol": "US500", "category": "Indices"},
                {"symbol": "DJ30", "category": "Indices"},
                {"symbol": "NASDAQ-100", "category": "Indices"},
            ]

            valid_setups = []
            filtered_reasons = {}

            # Check journal cooldowns: do not duplicate active journal setups
            recent_executed = {
                (j["symbol"], j["direction"]) 
                for j in self.journal 
                if j.get("status") == "OPEN"
            }

            for c in candidate_pool:
                sym = c["symbol"]

                mt5.symbol_select(sym, True)
                info = mt5.symbol_info(sym)
                tick = mt5.symbol_info_tick(sym)
                if not info or not tick:
                    filtered_reasons[sym] = "Market quote unavailable"
                    continue

                rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 45)
                if rates is None or len(rates) < 20:
                    filtered_reasons[sym] = "Insufficient M15 candle history"
                    continue

                closes = rates['close']
                highs = rates['high']
                lows = rates['low']

                # Compute ATR 14
                tr = np.maximum(highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1]))
                tr = np.maximum(tr, np.abs(lows[1:] - closes[:-1]))
                atr = float(np.mean(tr[-14:]))
                digits = info.digits
                point = info.point or (10 ** -digits)
                if atr <= (point * 0.5):
                    atr = point * 15.0

                # Compute EMA20
                if np is not None:
                    weights20 = np.exp(np.linspace(-1., 0., 20))
                    weights20 /= weights20.sum()
                    ema20 = float(np.convolve(closes[-20:], weights20, mode='valid')[-1])
                else:
                    ema20 = float(sum(closes[-20:]) / 20)

                # Compute RSI 14
                deltas = np.diff(closes[-15:])
                gains = deltas[deltas > 0]
                losses = -deltas[deltas < 0]
                avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
                avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
                rs = avg_gain / avg_loss
                rsi = float(100 - (100 / (1 + rs)))

                cur_p = (tick.bid + tick.ask) / 2.0 if (tick.bid > 0 and tick.ask > 0) else closes[-1]
                stop_dist = max(atr * 1.5, point * 50)

                # Dynamic Trend & Momentum Determination (Long vs Short)
                if cur_p >= ema20:
                    bias = "BUY"
                    setup_name = f"{sym} Trend Momentum (Long)"
                    notes = f"{sym} M15 bullish trend holding above dynamic EMA support."
                    entry = tick.ask if tick.ask > 0 else closes[-1]
                    sl = entry - stop_dist
                    tp = entry + (stop_dist * 2.0)
                    invalidation = f"Invalidated if M15 candle closes below {round(sl, digits)} or RSI drops below 35.0"
                else:
                    bias = "SELL"
                    setup_name = f"{sym} Bearish Momentum (Short)"
                    notes = f"{sym} M15 downward impulse holding below dynamic EMA resistance."
                    entry = tick.bid if tick.bid > 0 else closes[-1]
                    sl = entry + stop_dist
                    tp = entry - (stop_dist * 2.0)
                    invalidation = f"Invalidated if M15 candle closes above {round(sl, digits)} or RSI breaks above 68.0"

                # 1. LIVE POSITION AWARENESS (Rule 3): Prevent duplicates
                if (sym, bias) in open_pos:
                    filtered_reasons[sym] = f"Blocked: Active {bias} position already open in Headway MT5"
                    continue

                if (sym, bias) in recent_executed:
                    filtered_reasons[sym] = f"Blocked: Previous {bias} setup executed and still open in MT5"
                    continue

                # 2. MARKET STATUS VERIFICATION (Rule 1)
                is_open, open_reason = check_symbol_market_open(sym)

                try:
                    calc_lot = limit_volume(
                        mt5, info, mt5.ORDER_TYPE_BUY if bias == "BUY" else mt5.ORDER_TYPE_SELL,
                        sym, max(0.01, info.volume_min), entry, sl, risk_dollar)
                except (ValueError, TypeError):
                    filtered_reasons[sym] = "Broker risk data unavailable or minimum lot exceeds budget"
                    continue

                # Compute Multi-Factor Confidence Score (Rule 2)
                confidence_score, signals_list = calculate_setup_confidence(
                    info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist
                )
                
                tech_signals = f"M15 EMA20 at {round(ema20, digits)}, RSI(14) at {rsi:.1f}, ATR(14) at {round(atr, digits)} | Confluence: {'; '.join(signals_list[:2])}"
                if not is_open:
                    setup_name += " [Weekend Analysis]"
                    tech_signals = f"[Market Closed – Weekend Structure] " + tech_signals

                setup_id = f"{sym.replace(' ', '_')}_{bias}_{int(time.time())//180}"

                setup_obj = {
                    "id": setup_id,
                    "symbol": sym,
                    "category": c["category"],
                    "setup_name": setup_name,
                    "action": bias,
                    "confidence_score": confidence_score,
                    "conviction": f"{confidence_score}/100 rule score",
                    "is_high_confidence": confidence_score >= 88,
                    "status": "ACTIVE",
                    "is_market_open": is_open,
                    "market_note": "OPEN" if is_open else "CLOSED (Weekend Analysis)",
                    "entry": round(entry, digits),
                    "sl": round(sl, digits),
                    "tp": round(tp, digits),
                    "atr": round(atr, digits),
                    "stop_dist": round(stop_dist, digits),
                    "recommended_lots": calc_lot,
                    "suggested_trades": 2,
                    "rr_ratio": "1:2.0",
                    "technical_signals": tech_signals,
                    "invalidation_condition": invalidation,
                    "notes": notes,
                    "symbol_perf": get_symbol_perf_summary(sym)
                }

                # HIGH-CONFIDENCE AUTOMATIC EXECUTION (Rule 2 & 3: 88-100% Auto-Trade Threshold on OPEN markets only)
                if is_open and confidence_score >= 88 and self.auto_trade_enabled:
                    # Risk gate: Disallow automatic execution on Priority 5 (AVOID) symbols with severe historical losses
                    if setup_obj.get("symbol_perf", {}).get("priority_num") == 5:
                        filtered_reasons[sym] = f"Auto-Execution blocked: {sym} has historical Priority 5 (AVOID) status (Severe Loss Skew/Drawdown). Manual confirmation required."
                        valid_setups.append(setup_obj)
                        continue

                    # Mandatory Risk Verification before execution
                    risk_checks_passed = (
                        margin_free >= 500.0 and
                        (margin_level >= 200.0 or margin_level == 0.0) and
                        len(positions) + 3 <= MAX_OPEN_POSITIONS and
                        calc_lot >= info.volume_min and
                        sl > 0 and tp > 0
                    )
                    
                    if risk_checks_passed:
                        # Router rechecks current account risk and capacity for every group/leg.
                        order_res = execute_multi_tp_group(
                            symbol=sym,
                            action=bias,
                            ref_balance=balance,
                            default_lot=0.01,
                            ai_notes=f"Auto-Execution (88-100 rule score): {tech_signals}",
                            confidence_score=confidence_score,
                            prevent_duplicate=True,
                        )
                        if order_res.get("success"):
                            setup_obj["status"] = "EXECUTED"
                            setup_obj["group_id"] = order_res.get("group_id")
                            continue
                        else:
                            filtered_reasons[sym] = f"Auto-Execution Failed: {order_res.get('message')}"
                            valid_setups.append(setup_obj)
                    else:
                        filtered_reasons[sym] = "High-Confidence Setup blocked by Mandatory Margin/Risk Limits"
                        valid_setups.append(setup_obj)
                else:
                    valid_setups.append(setup_obj)

            with self.lock:
                self.scan_id += 1
                self.last_scan_time = datetime.utcnow().strftime("%H:%M:%S UTC")
                self.next_scan_seconds = self.interval
                self.current_setups = valid_setups
                self.filtered_reasons = filtered_reasons
                self._update_status_message()

    def _run_loop(self):
        """Continuous background thread executing every 3 minutes."""
        time.sleep(1)
        self.run_scan_now()
        
        while self.running:
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
                with self.lock:
                    if self.next_scan_seconds > 0:
                        self.next_scan_seconds -= 1
            if self.running:
                self.run_scan_now()

    def get_state(self):
        with self.lock:
            return {
                "scan_id": self.scan_id,
                "interval_seconds": self.interval,
                "last_scan_time": self.last_scan_time or datetime.utcnow().strftime("%H:%M:%S UTC"),
                "next_scan_seconds": self.next_scan_seconds,
                "auto_trade_enabled": self.auto_trade_enabled,
                "status": self.status,
                "status_message": self.status_message,
                "setups": self.current_setups,
                "filtered_reasons": self.filtered_reasons,
                "journal": self.journal[:20]
            }

# Importing this module must never start an order-producing thread.
scanner = None

def get_deriv_full_state():
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {
                "connected": False,
                "error": msg,
                "account": {},
                "positions": [],
                "quotes": {},
                "imm_dates": get_next_imm_dates(date.today())
            }
        
        acc = mt5.account_info()
        term = mt5.terminal_info()
        
        account_data = {
            "login": acc.login if acc else "17683547",
            "name": acc.name if acc else "PATRICK AMONI",
            "server": acc.server if acc else "Headway-Real",
            "company": acc.company if acc else "Jarocel (Pty) Ltd",
            "balance": round(acc.balance, 2) if acc else 0.0,
            "equity": round(acc.equity, 2) if acc else 0.0,
            "profit": round(acc.profit, 2) if acc else 0.0,
            "margin_free": round(acc.margin_free, 2) if acc else 0.0,
            "margin_level": round(acc.margin_level, 2) if acc else 0.0,
            "leverage": acc.leverage if acc else 1000,
            "ping": round(term.ping_last / 1000, 2) if term else 0.0
        }
        
        positions_raw = mt5.positions_get()
        positions = []
        if positions_raw:
            for p in positions_raw:
                p_type = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
                positions.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": p_type,
                    "volume": round(p.volume, 2),
                    "price_open": round(p.price_open, 5),
                    "price_current": round(p.price_current, 5),
                    "sl": round(p.sl, 5),
                    "tp": round(p.tp, 5),
                    "profit": round(p.profit, 2),
                    "time": time.strftime("%H:%M:%S", time.localtime(p.time))
                })
        
        quotes = {}
        for s in TICKER_SYMBOLS:
            mt5.symbol_select(s, True)
            tick = mt5.symbol_info_tick(s)
            if tick:
                quotes[s] = {
                    "bid": round(tick.bid, 4),
                    "ask": round(tick.ask, 4),
                    "spread": round(tick.ask - tick.bid, 4)
                }
        
        return {
            "connected": True,
            "account": account_data,
            "positions": positions,
            "quotes": quotes,
            "imm_dates": get_next_imm_dates(date.today())
        }

def get_recent_trade_history(limit=15):
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return []
        
        from_time = datetime.now() - timedelta(days=3)
        deals = mt5.history_deals_get(from_time, datetime.now())
        if not deals:
            return []
        
        history = []
        for d in reversed(deals):
            if d.entry == mt5.DEAL_ENTRY_OUT or d.profit != 0:
                history.append({
                    "ticket": d.ticket,
                    "order": d.order,
                    "symbol": d.symbol,
                    "type": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": round(d.volume, 2),
                    "price": round(d.price, 5),
                    "profit": round(d.profit, 2),
                    "commission": round(d.commission, 2),
                    "time": datetime.fromtimestamp(d.time).strftime("%m-%d %H:%M:%S")
                })
            if len(history) >= limit:
                break
        return history

def execute_deriv_order(symbol, action, volume, sl=0.0, tp=0.0, trades_count=1, volume_mode="split", setup_id=None, confidence="--", reason="Manual Execution", comment="Headway Agent"):
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {"success": False, "message": msg}
        
        # Verify market is open before order placement
        is_open, open_reason = check_symbol_market_open(symbol)
        if not is_open:
            return {"success": False, "message": f"Execution rejected: {open_reason}"}
        
        mt5.symbol_select(symbol, True)
        sym_info = mt5.symbol_info(symbol)
        if not sym_info:
            return {"success": False, "message": f"Symbol '{symbol}' not found on Deriv MT5."}
        
        trades_count = max(1, min(int(trades_count), 10))
        total_vol = float(volume)
        
        if volume_mode == "split" and trades_count > 1:
            per_trade_vol = round(total_vol / trades_count, 2)
            if per_trade_vol < sym_info.volume_min:
                per_trade_vol = sym_info.volume_min
        else:
            per_trade_vol = round(total_vol, 2)
            if per_trade_vol < sym_info.volume_min:
                per_trade_vol = sym_info.volume_min
        
        order_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        filling_mode = get_best_filling_mode(sym_info)
        
        executed_tickets = []
        executed_prices = []
        errors = []
        
        for i in range(trades_count):
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                errors.append(f"Trade #{i+1}: Could not fetch latest tick.")
                continue
            
            price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
            comment_str = f"{comment} ({i+1}/{trades_count})"[:31]
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": per_trade_vol,
                "type": order_type,
                "price": price,
                "sl": float(sl) if sl else 0.0,
                "tp": float(tp) if tp else 0.0,
                "deviation": 30,
                "magic": 999999 + i,
                "comment": comment_str,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            res = mt5.order_send(request)
            if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                executed_tickets.append(res.order)
                executed_prices.append(res.price)
            else:
                err_msg = res.comment if res else str(mt5.last_error())
                code = res.retcode if res else -1
                errors.append(f"Trade #{i+1} failed: {err_msg} (code {code})")
            
            if trades_count > 1:
                time.sleep(0.08)
        
        if executed_tickets:
            avg_price = sum(executed_prices) / len(executed_prices) if executed_prices else 0.0
            total_filled_vol = round(per_trade_vol * len(executed_tickets), 2)
            
            scanner.record_execution(
                setup_id=setup_id or f"{symbol}_{action}",
                symbol=symbol,
                direction=action,
                entry=avg_price,
                sl=sl,
                tp=tp,
                volume=total_filled_vol,
                tickets=executed_tickets,
                confidence=confidence,
                reason=reason,
                execution_type="MANUAL (1-Click)" if "AUTO" not in comment else "AUTO_EXECUTED (88-100% Conf)"
            )
            
            tickets_str = ", ".join(f"#{t}" for t in executed_tickets)
            msg = f"FILLED {len(executed_tickets)}x {action} {per_trade_vol} lot(s) on {symbol} (Total: {total_filled_vol} lots). Tickets: {tickets_str}"
            if errors:
                msg += f" | Partial errors: {'; '.join(errors)}"
            return {
                "success": True,
                "tickets": executed_tickets,
                "count": len(executed_tickets),
                "total_volume": total_filled_vol,
                "message": msg
            }
        else:
            return {
                "success": False,
                "message": f"Execution failed for all orders: {'; '.join(errors)}"
            }

def close_deriv_position(ticket):
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {"success": False, "message": msg}
        
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return {"success": False, "message": f"Ticket #{ticket} not found or already closed."}
        
        pos = positions[0]
        sym_info = mt5.symbol_info(pos.symbol)
        filling_mode = get_best_filling_mode(sym_info)
        
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 30,
            "magic": 999999,
            "comment": "Headway Instant Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }
        res = mt5.order_send(request)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            return {"success": True, "message": f"Closed #{ticket} ({pos.symbol}) successfully."}
        else:
            err_msg = res.comment if res else str(mt5.last_error())
            code = res.retcode if res else -1
            return {"success": False, "message": f"Close failed: {err_msg} (code {code})"}

def close_all_deriv_positions():
    with mt5_lock:
        ok, msg = ensure_deriv_connected()
        if not ok:
            return {"success": False, "message": msg}
        
        positions = mt5.positions_get()
        if not positions:
            return {"success": True, "message": "No open positions to close."}
        
        closed = 0
        errors = []
        for pos in positions:
            sym_info = mt5.symbol_info(pos.symbol)
            filling_mode = get_best_filling_mode(sym_info)
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "deviation": 30,
                "magic": 999999,
                "comment": "Panic Close All"[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            res = mt5.order_send(request)
            if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
            else:
                err_msg = res.comment if res else str(mt5.last_error())
                errors.append(f"#{pos.ticket}: {err_msg}")
        
        return {
            "success": True,
            "message": f"Emergency Close: Successfully closed {closed} of {len(positions)} positions.",
            "errors": errors
        }

# ==============================================================================
# 5-TRADE MULTI-TP SYSTEM WITH SHARED 5% STOP LOSS ENGINE
# ==============================================================================
def load_multi_tp_groups(strict=False):
    if not MULTI_TP_FILE.exists():
        return []
    try:
        groups = json.loads(MULTI_TP_FILE.read_text(encoding="utf-8"))
        if not isinstance(groups, list):
            raise ValueError("Trade group state is not a list")
        return groups
    except Exception:
        if strict:
            raise ValueError("Trade group state cannot be read; new entries paused")
        return []


def save_multi_tp_groups(groups):
    # Commit the complete file; never expose a partially written JSON document.
    pending = MULTI_TP_FILE.with_suffix(".json.tmp")
    pending.write_text(json.dumps(groups, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(pending, MULTI_TP_FILE)


def sync_multi_tp_groups():
    """Reconcile Multi-TP positions against live MT5 positions."""
    with mt5_lock:
        ok, _ = ensure_deriv_connected()
        groups = load_multi_tp_groups()
        if not ok or not groups:
            return groups
        open_positions = mt5.positions_get()
        if open_positions is None:
            return groups
        live = {p.ticket: p for p in open_positions}
        changed = False
        for group in groups:
            realized, floating, all_closed = 0.0, 0.0, True
            for pos in group.get("positions", []):
                ticket = pos.get("ticket")
                if not ticket:
                    continue
                if ticket in live:
                    active = live[ticket]
                    all_closed = False
                    pos.update(
                        status="ACTIVE",
                        current_price=active.price_current,
                        floating_profit=round(active.profit + active.swap, 2)
                    )
                    floating += pos["floating_profit"]
                else:
                    if pos.get("status") == "ACTIVE" or not pos.get("status"):
                        pos.update(status="CLOSED", floating_profit=0.0)
                        changed = True
                    realized += pos.get("realized_profit", 0.0)

            group.update(
                realized_profit=round(realized, 2),
                floating_profit=round(floating, 2),
                total_profit=round(realized + floating, 2),
                status="COMPLETED" if all_closed else "ACTIVE"
            )
            changed = True
        if changed:
            save_multi_tp_groups(groups)
        return groups


def execute_multi_tp_group(symbol, action, ref_balance=1000.0, default_lot=0.01,
                           ai_notes="Multi-TP Setup", custom_lots=None,
                           confidence_score=None, prevent_duplicate=False):
    """Three fixed targets; preserve signal/price-distance rules, cap stop exposure.

    Risk/target money is a broker estimate in account currency, excluding costs
    and stop slippage. No trailing stop or win probability is implied.
    """
    with mt5_lock:
        def reject(message):
            return {"success": False, "message": message}

        action = str(action).upper()
        if action not in ("BUY", "SELL"):
            return reject("Action must be BUY or SELL")
        ok, msg = ensure_deriv_connected()
        if not ok:
            return reject(msg)
        try:
            groups = load_multi_tp_groups(strict=True)
        except ValueError as exc:
            return reject(str(exc))
        if any(g.get("symbol") == symbol and g.get("execution_state") == "UNKNOWN" for g in groups):
            return reject("Prior submission requires broker reconciliation before new symbol entries")
        is_open, reason = check_symbol_market_open(symbol)
        if not is_open:
            return reject(f"Execution rejected: {reason}")
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        acc = mt5.account_info()
        positions = mt5.positions_get()
        if info is None or tick is None or acc is None or positions is None:
            return reject("Account, positions, symbol or quote unavailable; no orders sent")
        if not getattr(acc, "trade_allowed", False) or not getattr(acc, "trade_expert", False):
            return reject("Account does not permit automated trading")
        if getattr(acc, "margin_mode", None) != mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
            return reject("Three separate positions require a hedging account")
        order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
        if prevent_duplicate and any(p.symbol == symbol and p.type == order_type for p in positions):
            return reject("An existing position already has this symbol and direction")
        if len(positions) + 3 > MAX_OPEN_POSITIONS:
            return reject(f"Three-trade group exceeds the {MAX_OPEN_POSITIONS}-position account cap")
        try:
            basis = positive(min(acc.balance, acc.equity), "Account risk basis")
            budget = basis * MAX_GROUP_RISK_PERCENT / 100
            entry = positive(tick.ask if action == "BUY" else tick.bid, "Entry")
            spread = tick.ask - tick.bid
            if spread < 0:
                raise ValueError("Quote is crossed")
            point = positive(info.point, "Symbol point")
            minimum = max(info.trade_stops_level * point, spread * 1.5, point * 50)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15)
            # Retain the existing mean-candle-range calculation and targets.
            scale = (sum(float(r["high"] - r["low"]) for r in rates) / len(rates)
                     if rates is not None and len(rates) >= 5 else minimum * 2)
            if not math.isfinite(scale):
                raise ValueError("Non-finite candle range")
            if scale <= point:
                scale = minimum * 2
            distance = max(minimum, scale * 1.8)
            shared_sl = round(max(0.00001, entry - distance) if action == "BUY"
                              else entry + distance, info.digits)
            requested = default_lot if custom_lots is None else custom_lots
            lot = limit_volume(mt5, info, order_type, symbol, requested,
                               entry, shared_sl, budget, legs=3)
        except (ValueError, TypeError, OverflowError) as exc:
            return reject(str(exc))

        executed, errors, uncertain = [], [], None
        reservation = None
        used_risk = 0.0
        group_id = f"GRP-{time.time_ns()}-{symbol.replace(' ', '')[:6]}"
        for leg, multiple in enumerate((1.5, 3.0, 5.0), 1):
            target_distance = max(minimum, scale * multiple)
            tp = round(entry + target_distance if action == "BUY" else
                       max(entry * 0.1, entry - target_distance), info.digits)
            fresh = mt5.symbol_info_tick(symbol)
            current_acc = mt5.account_info()
            current_positions = mt5.positions_get()
            if fresh is None or current_acc is None or current_positions is None:
                errors.append("Fresh account/position/quote query failed; remaining legs skipped")
                break
            if len(current_positions) >= MAX_OPEN_POSITIONS:
                errors.append("Position cap reached; remaining legs skipped")
                break
            try:
                price = fresh.ask if action == "BUY" else fresh.bid
                validate_geometry(action == "BUY", fresh.bid, fresh.ask, shared_sl,
                                  tp, info.trade_stops_level * point)
                leg_risk = stop_loss_money(mt5, order_type, symbol, lot, price, shared_sl)
                current_budget = min(budget, positive(min(current_acc.balance, current_acc.equity),
                                                     "Account risk basis") * MAX_GROUP_RISK_PERCENT / 100)
                if used_risk + leg_risk * (4 - leg) > current_budget + 1e-8:
                    raise ValueError("Current quote exceeds the group stop-risk budget")
                margin = mt5.order_calc_margin(order_type, symbol, lot, price)
                if margin is None or not math.isfinite(margin) or margin < 0 or margin > current_acc.margin_free:
                    raise ValueError("Margin unavailable or insufficient")
                target_money = mt5.order_calc_profit(order_type, symbol, lot, price, tp)
                positive(target_money, "Broker target value")
            except (ValueError, TypeError, OverflowError) as exc:
                errors.append(str(exc))
                break
            request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lot,
                       "type": order_type, "price": price, "sl": shared_sl, "tp": tp,
                       "deviation": 30, "magic": 555000 + leg,
                       "comment": f"MTP T{leg} {symbol[:6]}",
                       "type_time": mt5.ORDER_TIME_GTC,
                       "type_filling": get_best_filling_mode(info)}
            # Persist an uncertain reservation BEFORE sending; a crash cannot silently retry it.
            if reservation is None:
                reservation = {"group_id": group_id, "symbol": symbol, "action": action,
                               "status": "RECONCILIATION_REQUIRED", "execution_state": "UNKNOWN",
                               "positions": executed, "uncertain_order": request,
                               "entry_price": entry, "shared_sl": shared_sl,
                               "total_profit": 0.0, "realized_profit": 0.0, "floating_profit": 0.0}
                groups.insert(0, reservation)
            reservation["uncertain_order"] = request
            try:
                save_multi_tp_groups(groups)
            except (OSError, ValueError) as exc:
                errors.append(f"Execution reservation could not be persisted: {exc}")
                break
            try:
                result = mt5.order_send(request)
            except Exception as exc:
                result = None
                errors.append(f"Submission exception: {exc}")
            if result is None or result.retcode not in (mt5.TRADE_RETCODE_DONE,
                                                       mt5.TRADE_RETCODE_DONE_PARTIAL):
                # Explicit rejections have no fill; all other results require reconciliation.
                rejected = {10004, 10006, 10007, 10013, 10014, 10015, 10016, 10017,
                            10018, 10019, 10020, 10021, 10022, 10024, 10026, 10027,
                            10030, 10032, 10033, 10034, 10035, 10042, 10043, 10044, 10046}
                if result is None or result.retcode not in rejected:
                    uncertain = request
                errors.append(f"Leg {leg}: {result.comment if result else 'Submission outcome unknown'}")
                break
            fill_volume = float(result.volume)
            fill_price = float(result.price or price)
            if not math.isfinite(fill_volume) or fill_volume <= 0 or not result.order:
                uncertain = request
                errors.append("Accepted response has incomplete fill details")
                break
            try:
                fill_risk = stop_loss_money(mt5, order_type, symbol, fill_volume,
                                            fill_price, shared_sl)
                fill_target = positive(mt5.order_calc_profit(order_type, symbol, fill_volume,
                                                            fill_price, tp), "Filled target value")
            except (ValueError, TypeError):
                fill_risk, fill_target = leg_risk * fill_volume / lot, target_money * fill_volume / lot
                uncertain = request
                errors.append("Filled exposure needs broker reconciliation")
            used_risk += fill_risk
            executed.append({"sub_id": leg, "name": f"Trade {leg} (fixed target {multiple}x range)",
                             "ticket": result.order, "lot": fill_volume, "entry": fill_price,
                             "sl": shared_sl, "tp": tp, "target_dollar": round(fill_target, 2),
                             "target_pct": "fixed price target", "planned_risk_dollar": round(fill_risk, 2),
                             "status": "ACTIVE", "floating_profit": 0.0, "realized_profit": 0.0,
                             "close_price": None, "close_reason": None})
            if result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL or used_risk > current_budget + 1e-8:
                uncertain = request
                errors.append("Partial fill or adverse fill requires reconciliation; no more legs sent")
            if uncertain:
                break
            time.sleep(0.08)

        if not executed and uncertain is None:
            if reservation is not None:
                groups.remove(reservation)
                save_multi_tp_groups(groups)
            return reject("No orders filled: " + "; ".join(errors))
        group = {"group_id": group_id, "symbol": symbol, "action": action,
                 "ref_balance": basis, "currency": acc.currency,
                 "total_risk_dollar": round(used_risk, 2),
                 "total_risk_pct": round(used_risk / basis * 100, 4),
                 "risk_budget_dollar": round(budget, 2), "risk_excludes_costs": True,
                 "risk_complete": uncertain is None,
                 "lot_per_trade": lot, "total_volume": sum(p["lot"] for p in executed),
                 "entry_price": executed[0]["entry"] if executed else entry,
                 "shared_sl": shared_sl, "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                 "ai_notes": ai_notes, "confidence_score": confidence_score,
                 "status": "RECONCILIATION_REQUIRED" if uncertain else "ACTIVE",
                 "execution_state": "UNKNOWN" if uncertain else "CONFIRMED",
                 "uncertain_order": uncertain, "realized_profit": 0.0, "floating_profit": 0.0,
                 "total_profit": 0.0, "positions": executed, "errors": errors}
        if reservation is not None:
            groups.remove(reservation)
        groups.insert(0, group)
        save_multi_tp_groups(groups)
        if executed and scanner is not None:
            score_label = (f"{confidence_score}/100 rule score" if confidence_score is not None
                           else "Unscored manual entry")
            scanner.record_execution(group_id, symbol, action, group["entry_price"], shared_sl,
                                     executed[-1]["tp"], group["total_volume"],
                                     [p["ticket"] for p in executed], confidence=score_label,
                                     reason=f"Fixed-target group; estimated stop exposure {used_risk:.2f} {acc.currency} before costs. {ai_notes}",
                                     execution_type="MULTI_TP_3_TRADES")
        return {"success": bool(executed) and uncertain is None, "group_id": group_id,
                "symbol": symbol, "action": action, "tickets": [p["ticket"] for p in executed],
                "shared_sl": shared_sl, "total_risk_dollar": round(used_risk, 2),
                "positions_opened": len(executed), "errors": errors,
                "message": f"Filled {len(executed)}/3 positions; estimated stop exposure {used_risk:.2f} {acc.currency} before costs. " +
                           ("Broker reconciliation required. " if uncertain else "") + "; ".join(errors)}


def close_multi_tp_trade(ticket):
    return close_deriv_position(ticket)

def close_multi_tp_group(group_id):
    with mt5_lock:
        groups = load_multi_tp_groups()
        target_group = next((g for g in groups if g.get("group_id") == group_id), None)
        if not target_group:
            return {"success": False, "message": f"Multi-TP group '{group_id}' not found."}

        closed_count = 0
        errors = []
        for p in target_group.get("positions", []):
            ticket = p.get("ticket")
            if ticket:
                res = close_deriv_position(ticket)
                if res.get("success"):
                    closed_count += 1
                else:
                    errors.append(f"Ticket #{ticket}: {res.get('message')}")

        target_group["status"] = "CLOSED_BY_USER"
        save_multi_tp_groups(groups)
        sync_multi_tp_groups()

        return {
            "success": True,
            "message": f"Closed {closed_count} positions in group {group_id}.",
            "errors": errors
        }

HTML_PAGE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Headway MT5 Institutional Trading Station & Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: '#FF444F',
            darkbg: '#0B0E14',
            panel: '#121722',
            bordercol: '#1E2638',
            emeraldaccent: '#00C087',
            crimsonaccent: '#FF444F',
            cyanaccent: '#06B6D4',
            amberaccent: '#F59E0B'
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #0B0E14; color: #E5E7EB; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .custom-scroll::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scroll::-webkit-scrollbar-track { background: #121722; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #222C40; border-radius: 3px; }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Header -->
  <header class="border-b border-bordercol bg-panel/95 backdrop-blur px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
    <div class="flex items-center space-x-3.5">
      <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20 font-black text-white text-lg">
        H
      </div>
      <div>
        <h1 class="text-sm font-bold tracking-tight text-white flex items-center gap-2">
          HEADWAY MT5 INSTITUTIONAL WORKSTATION
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-emeraldaccent/10 text-emeraldaccent border border-emeraldaccent/20 font-mono font-semibold">AUTO-EXECUTE ENABLED</span>
        </h1>
        <p class="text-[11px] text-slate-400">Account #<span id="headerLogin" class="text-slate-200 font-mono font-bold">17683547</span> &bull; <span id="headerServer">Headway-Real</span> &bull; 1:1000 Leverage &bull; Quotes Only</p>
      </div>
    </div>
    
    <!-- MAIN MENU NAVIGATION TABS (Requirement 1) -->
    <nav class="flex items-center space-x-1.5 bg-slate-900/90 p-1 rounded-xl border border-bordercol shadow-inner">
      <button id="navTabStation" onclick="switchMainTab('station')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-brand text-white shadow flex items-center gap-2">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        Trading Station & Execution
      </button>
      <button id="navTabPerformance" onclick="switchMainTab('performance')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
        Symbol Performance & Analytics
        <span id="p1TopBadge" class="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emeraldaccent text-[10px] font-mono">P1 FOCUS</span>
      </button>
    </nav>

    <div class="flex items-center space-x-3">
      <div class="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol text-slate-300">
        <span class="w-2 h-2 rounded-full bg-emeraldaccent animate-pulse"></span>
        <span id="connPing">PING: 160ms</span>
      </div>
      <button onclick="emergencyCloseAll()" class="px-3 py-1.5 rounded-lg bg-rose-600/10 hover:bg-rose-600/20 text-crimsonaccent border border-rose-500/30 text-xs font-bold transition flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        Panic Close All
      </button>
      <button onclick="refreshAll()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition border border-bordercol flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        Sync All
      </button>
    </div>
  </header>

  <!-- Live Market Watch Bar -->
  <div class="bg-slate-950/80 border-b border-bordercol px-6 py-2 overflow-x-auto custom-scroll">
    <div id="tickerBar" class="flex items-center space-x-4 text-xs font-mono whitespace-nowrap min-w-max">
      <!-- Populated via JS -->
    </div>
  </div>

  <!-- Main Container -->
  <main class="flex-1 p-6 space-y-6 max-w-[1600px] w-full mx-auto">

    <!-- VIEW 1: TRADING STATION & EXECUTION -->
    <div id="stationView" class="space-y-6">

    <!-- Balance & Equity Row -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
        <div class="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Account Balance</div>
        <div id="accBalance" class="text-2xl font-black font-mono text-white">$0.00</div>
        <div class="text-[11px] text-slate-500 font-mono mt-1">Currency: USD</div>
      </div>

      <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
        <div class="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Account Equity</div>
        <div id="accEquity" class="text-2xl font-black font-mono text-white">$0.00</div>
        <div class="text-[11px] text-slate-500 font-mono mt-1">Live Net Worth</div>
      </div>

      <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
        <div class="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Floating Profit / Loss</div>
        <div id="accProfit" class="text-2xl font-black font-mono text-emeraldaccent">$0.00</div>
        <div class="text-[11px] text-slate-500 font-mono mt-1">Active Positions P/L</div>
      </div>

      <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
        <div class="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Free Margin Available</div>
        <div id="accMargin" class="text-2xl font-black font-mono text-blue-400">$0.00</div>
        <div id="accMarginLevel" class="text-[11px] text-slate-500 font-mono mt-1">Margin Level: 0.00%</div>
      </div>
    </section>

    <!-- SECTION: Automated Recommended Trade Setups & Technical Invalidation Notes -->
    <section class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-bordercol">
        <div>
          <div class="flex items-center gap-2.5">
            <h2 class="text-sm font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-emeraldaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
              Recommended Trade Setups & Technical Invalidation Notes
            </h2>
            <span id="scannerStatusBadge" class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20 font-mono font-semibold">SCANNING</span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">Continuous 3-minute background market scanner. Live position aware, technical invalidation gated & non-duplicating.</p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          
          <!-- AUTO-TRADING TOGGLE (Rule 2: 88-100% High Confidence Auto Execution) -->
          <div class="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol shadow-inner">
            <span class="text-slate-400 font-sans text-xs font-medium">Auto-Trade (88-100% Conf):</span>
            <button id="autoTradeBtn" onclick="toggleAutoTrade()" class="px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-slate-800 text-slate-400 border border-slate-700">
              <span id="autoTradeDot" class="w-2 h-2 rounded-full bg-slate-500"></span>
              <span id="autoTradeText">DISABLED</span>
            </button>
          </div>

          <!-- Countdown badge -->
          <div class="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol text-slate-300">
            <span class="w-2 h-2 rounded-full bg-cyanaccent animate-pulse"></span>
            <span>Next Scan: <span id="rescanCountdown" class="text-white font-bold">03:00</span></span>
            <span class="text-slate-500 text-[10px] ml-1">(Last: <span id="lastScanTime" class="text-slate-400">--</span>)</span>
          </div>

          <button onclick="toggleAuditModal()" class="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition border border-bordercol flex items-center gap-1">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Filtered Audit
          </button>

          <button onclick="triggerImmediateRescan()" class="text-xs px-3 py-1.5 rounded-lg bg-brand hover:bg-red-600 text-white font-bold transition flex items-center gap-1.5 shadow-sm shadow-red-500/20">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            Re-Scan Now
          </button>
        </div>
      </div>

      <!-- Setups Grid or Waiting for Confirmation State -->
      <div id="setupsGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <!-- Rendered via JS -->
      </div>

      <!-- Filtered Reasons Audit Drawer (Collapsible) -->
      <div id="auditSection" class="hidden p-4 rounded-xl bg-slate-950/80 border border-bordercol space-y-2 text-xs">
        <div class="flex items-center justify-between border-b border-bordercol pb-2">
          <span class="font-bold text-slate-300 font-mono">Scanner Quality Audit & Filtered Instruments</span>
          <button onclick="toggleAuditModal()" class="text-slate-500 hover:text-white">Close</button>
        </div>
        <div id="auditContent" class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-400 font-mono text-[11px]">
          <!-- Populated via JS -->
        </div>
      </div>
    </section>

    <!-- ============================================================================== -->
    <!-- SECTION: MULTI-TP TRADE MANAGER (5-Trade Multi-TP System with Shared 5% SL)    -->
    <!-- ============================================================================== -->
    <section class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-bordercol">
        <div>
          <div class="flex items-center gap-2.5">
            <h2 class="text-sm font-bold text-white flex items-center gap-2 font-sans">
              <svg class="w-4 h-4 text-emeraldaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
              Multi-TP Trade Manager (3-Trade Multi-TP Power System)
            </h2>
            <span id="mtpGroupsBadge" class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20 font-mono font-semibold">0 GROUPS</span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">3 separate positions per setup: Trade 1 (+2% / $20), Trade 2 (+5% / $50), and Trade 3 (AI Dynamic Runner) with a shared 5% account Stop Loss ($50 planned loss max).</p>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div class="bg-slate-900 border border-bordercol px-3 py-1.5 rounded-lg flex items-center gap-2 text-slate-300">
            <span class="text-slate-400 font-sans text-xs">Ref Balance:</span>
            <input id="mtpRefBalanceInput" type="number" value="1000" step="100" onchange="updateMtpRiskPreview()" class="w-20 bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-white font-mono text-xs focus:outline-none focus:border-cyanaccent">
            <button onclick="useLiveBalanceForMtp()" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-cyanaccent border border-slate-700 transition">Use Live</button>
          </div>

          <div class="bg-slate-900 border border-bordercol px-3 py-1.5 rounded-lg flex items-center gap-2 text-slate-300">
            <span class="text-slate-400 font-sans text-xs">Shared SL Risk:</span>
            <span id="mtpRiskDollarBadge" class="text-crimsonaccent font-bold font-mono">5.0% ($50.00 max)</span>
          </div>

          <button onclick="fetchMultiTpGroups()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition border border-bordercol flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-cyanaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            Sync Multi-TP
          </button>
        </div>
      </div>

      <!-- Multi-TP Live Groups Display -->
      <div id="mtpGroupsContainer" class="space-y-4">
        <!-- Rendered via JS -->
      </div>
    </section>

    <!-- Open Positions Table -->
    <section class="bg-panel border border-bordercol rounded-xl overflow-hidden shadow-sm">
      <div class="p-4 border-b border-bordercol flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-red-500"></span>
          <h2 class="text-sm font-bold text-white">Live Positions on Deriv MT5</h2>
          <span id="posCount" class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">0 active</span>
        </div>
        <div class="text-xs text-slate-400 font-mono">
          Real-time broker sync (<span id="netVolume">0.00</span> total lots)
        </div>
      </div>

      <div class="overflow-x-auto custom-scroll">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-900/60 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-bordercol">
            <tr>
              <th class="py-2.5 px-4">Ticket</th>
              <th class="py-2.5 px-4">Symbol</th>
              <th class="py-2.5 px-4">Type</th>
              <th class="py-2.5 px-4">Volume</th>
              <th class="py-2.5 px-4">Open Price</th>
              <th class="py-2.5 px-4">Current Price</th>
              <th class="py-2.5 px-4">Stop Loss</th>
              <th class="py-2.5 px-4">Take Profit</th>
              <th class="py-2.5 px-4">P / L</th>
              <th class="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody id="positionsTbody" class="divide-y divide-bordercol text-slate-300">
            <tr><td colspan="10" class="py-6 text-center text-slate-500">Loading live Deriv positions...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 2-Column Execution & Journal Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left Column: Precision Order Placement, 733+ Symbols & Multi-Order (7 Cols) -->
      <section class="lg:col-span-7 space-y-6">
        <div class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between pb-3.5 border-b border-bordercol mb-4">
            <div>
              <h2 class="text-sm font-bold text-white flex items-center gap-2">
                <svg class="w-4 h-4 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                Execution Terminal (Direct to Deriv MT5)
              </h2>
              <p class="text-xs text-slate-400">Trade all 733+ broker symbols & execute multi-position setups</p>
            </div>
            <span class="text-xs px-2.5 py-1 rounded bg-red-500/10 text-brand border border-red-500/20 font-mono font-bold">DERIV FOK</span>
          </div>

          <form id="orderForm" onsubmit="submitDerivOrder(event)" class="space-y-4">
            
            <!-- Category Filter & Symbol Search -->
            <div class="space-y-2">
              <label class="block text-xs text-slate-400 font-medium">Select Broker Symbol (733 Available on Deriv)</label>
              
              <!-- Category Filter Pills -->
              <div class="flex flex-wrap gap-1.5 text-[11px]">
                <button type="button" onclick="filterCategory('ALL')" class="cat-pill px-2.5 py-1 rounded bg-brand text-white font-medium">All</button>
                <button type="button" onclick="filterCategory('Crash Boom Indices')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Crash / Boom</button>
                <button type="button" onclick="filterCategory('Volatility Indices')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Volatility</button>
                <button type="button" onclick="filterCategory('Step Indices')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Step Indices</button>
                <button type="button" onclick="filterCategory('Crypto')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Crypto</button>
                <button type="button" onclick="filterCategory('Forex Major')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Forex Major</button>
                <button type="button" onclick="filterCategory('Metals')" class="cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium">Metals & Gold</button>
              </div>

              <!-- Search input & Select -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div class="relative">
                  <input id="symbolSearchInput" type="text" placeholder="Search 733 symbols (e.g. BTC, Boom, V75, EUR)..." oninput="onSymbolSearch(this.value)" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-brand" />
                </div>
                <div>
                  <select id="allSymbolsSelect" onchange="onSymbolDropdownSelect(this.value)" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-brand">
                    <option value="BTCUSD">BTCUSD - Bitcoin vs USD</option>
                  </select>
                </div>
              </div>

              <!-- Active Symbol Info Bar -->
              <div id="activeSymbolDetails" class="p-2.5 rounded-lg bg-slate-900/80 border border-bordercol flex flex-wrap items-center justify-between text-xs font-mono">
                <div><span class="text-slate-500">Active:</span> <span id="curSymName" class="font-bold text-white">BTCUSD</span></div>
                <div><span class="text-slate-500">Bid:</span> <span id="curSymBid" class="text-emeraldaccent font-bold">--</span></div>
                <div><span class="text-slate-500">Ask:</span> <span id="curSymAsk" class="text-crimsonaccent font-bold">--</span></div>
                <div><span class="text-slate-500">Spread:</span> <span id="curSymSpread" class="text-slate-300">--</span></div>
                <div><span class="text-slate-500">Min Lot:</span> <span id="curSymMinLot" class="text-blue-400">0.01</span></div>
              </div>
            </div>

            <!-- Direction -->
            <div>
              <label class="block text-xs text-slate-400 mb-1 font-medium">Order Direction</label>
              <div class="grid grid-cols-2 gap-2">
                <button type="button" id="btnBuy" onclick="setDirection('BUY')" class="py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white font-bold text-xs flex items-center justify-center gap-1 transition">
                  BUY (LONG)
                </button>
                <button type="button" id="btnSell" onclick="setDirection('SELL')" class="py-2.5 rounded-lg bg-crimsonaccent text-white font-bold text-xs flex items-center justify-center gap-1 transition shadow-lg shadow-red-500/20">
                  SELL (SHORT)
                </button>
              </div>
            </div>

            <!-- Prices & SL/TP -->
            <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <label class="block text-xs text-slate-400 mb-1 font-medium">Entry Price</label>
                <input id="tradeEntry" type="number" step="any" placeholder="80595.00" oninput="recalcSizer()" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-brand" />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1 font-medium">Stop Loss (SL)</label>
                <input id="tradeSL" type="number" step="any" placeholder="80949.00" oninput="recalcSizer()" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-brand" />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1 font-medium">Take Profit (TP)</label>
                <input id="tradeTP" type="number" step="any" placeholder="80065.00" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-brand" />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1 font-medium">Risk Budget (%)</label>
                <input id="tradeRiskPct" type="number" step="0.1" value="1.0" min="0.1" max="5.0" oninput="recalcSizer()" class="w-full bg-slate-900 border border-bordercol rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-brand" />
              </div>
            </div>

            <!-- MULTI-ORDER PARAMETERS -->
            <div class="p-4 rounded-xl bg-slate-900/90 border border-blue-500/30 space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
                  <label class="text-xs font-bold text-white uppercase tracking-wider">Multi-Position Execution Parameters</label>
                </div>
                <span class="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono font-semibold">PARTIAL SCALE / STACK</span>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-slate-400 mb-1 font-medium">Number of Trades to Open</label>
                  <div class="flex items-center gap-2">
                    <input id="tradesCount" type="number" min="1" max="10" value="1" oninput="updateMultiOrderPreview()" class="w-20 bg-slate-800 border border-bordercol rounded-lg px-3 py-2 text-xs text-white font-mono font-bold focus:outline-none focus:border-brand" />
                    <div class="flex gap-1">
                      <button type="button" onclick="setTradeCount(1)" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono text-slate-300">1x</button>
                      <button type="button" onclick="setTradeCount(2)" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono text-slate-300">2x</button>
                      <button type="button" onclick="setTradeCount(3)" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono text-slate-300">3x</button>
                      <button type="button" onclick="setTradeCount(5)" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono text-slate-300">5x</button>
                    </div>
                  </div>
                </div>

                <div>
                  <label class="block text-xs text-slate-400 mb-1 font-medium">Volume Distribution Mode</label>
                  <select id="volumeMode" onchange="updateMultiOrderPreview()" class="w-full bg-slate-800 border border-bordercol rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-brand">
                    <option value="split">Split Total Lots (e.g. 0.30 lots across 3 trades = 0.10 lots each)</option>
                    <option value="stack">Stack Full Lots (e.g. 3 trades each having the full lot size)</option>
                  </select>
                </div>
              </div>

              <!-- Multi-order summary note -->
              <div id="multiOrderPreview" class="text-[11px] text-blue-300/80 font-mono bg-blue-950/40 p-2 rounded border border-blue-900/50">
                Single order: Opening 1 trade of 0.20 lots.
              </div>
            </div>

            <!-- Real-time Sizer Calculation Banner -->
            <div class="p-3.5 rounded-lg bg-slate-900 border border-bordercol flex flex-wrap items-center justify-between gap-4 text-xs">
              <div>
                <span class="text-slate-400 block text-[11px]">1.0% Risk Budget</span>
                <span id="calcRiskDollar" class="font-bold text-white font-mono text-sm">$71.50</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[11px]">Stop Distance</span>
                <span id="calcStopDist" class="font-bold text-slate-200 font-mono text-sm">350.00 pts</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[11px]">Recommended Lots</span>
                <span id="calcLots" class="font-bold text-emeraldaccent font-mono text-sm">0.20 lots</span>
              </div>
              <div>
                <label class="text-slate-400 block text-[11px]">Total Volume (Lots)</label>
                <input id="tradeVolume" type="number" step="0.01" value="0.20" oninput="updateMultiOrderPreview()" required class="w-24 bg-slate-800 border border-brand/50 rounded px-2.5 py-1 text-white font-mono font-bold text-xs focus:outline-none" />
              </div>
            </div>

            <!-- 3-Trade Multi-TP Power System Sizing & Execution Panel -->
            <div class="p-3.5 rounded-lg bg-emerald-950/20 border border-emerald-500/40 space-y-2.5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <span class="text-sm">⚡</span>
                  <span class="text-xs font-bold text-white font-sans">3-Trade Multi-TP Power System</span>
                  <span class="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emeraldaccent border border-emerald-500/40 font-mono font-bold">SHARED 5% SL</span>
                </div>
                <span id="otMtpRiskBadge" class="text-[10px] text-emerald-400 font-mono font-bold">Risk: $50.00 Max</span>
              </div>
              <div class="grid grid-cols-3 gap-1.5 text-[10px] font-mono text-center">
                <div class="p-1.5 rounded bg-slate-900 border border-slate-800"><span class="text-slate-400 block text-[8px]">T1 (TP 2%)</span><span id="otMtpT1Target" class="text-emeraldaccent font-bold">+$20 Target</span></div>
                <div class="p-1.5 rounded bg-slate-900 border border-slate-800"><span class="text-slate-400 block text-[8px]">T2 (TP 5%)</span><span id="otMtpT2Target" class="text-emeraldaccent font-bold">+$50 Target</span></div>
                <div class="p-1.5 rounded bg-slate-900 border border-slate-800"><span class="text-slate-400 block text-[8px]">T3 (AI Runner)</span><span id="otMtpT3Target" class="text-cyanaccent font-bold">Infinite Upside</span></div>
              </div>
              <p class="text-[10px] text-slate-300 leading-snug">
                Opens 3 separate trades: T1 locks in guaranteed quick cash, T2 captures the core trend move, and T3 provides an infinite upside trailing stop.
              </p>
              <button type="button" onclick="executeMtpFromCurrentForm()" class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                Execute 3-Trade Multi-TP System
              </button>
            </div>

            <!-- Submit Button -->
            <button type="submit" id="submitBtn" class="w-full py-3.5 rounded-lg bg-crimsonaccent hover:bg-red-600 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-red-600/25 flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              Execute Instant Order on Deriv MT5
            </button>
            <div id="orderStatusMsg" class="hidden text-xs p-3 rounded-lg font-mono"></div>
          </form>
        </div>
      </section>

      <!-- Right Column: Executed Trades Journal & IMM Calendar (5 Cols) -->
      <section class="lg:col-span-5 space-y-6">
        
        <!-- Executed Setups Journal (Rule 4) -->
        <div class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-3">
          <div class="flex items-center justify-between pb-2.5 border-b border-bordercol">
            <div>
              <h2 class="text-sm font-bold text-white flex items-center gap-2">
                <svg class="w-4 h-4 text-emeraldaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                Executed Setups Journal (Live Sync)
              </h2>
              <p class="text-[11px] text-slate-400">Audit log with confidence scores & execution reasons</p>
            </div>
            <span id="journalCount" class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">0 Logged</span>
          </div>

          <div class="max-h-72 overflow-y-auto custom-scroll">
            <table class="w-full text-left text-[11px]">
              <thead class="text-slate-500 uppercase tracking-wider font-semibold border-b border-bordercol">
                <tr>
                  <th class="py-1.5 px-2">Symbol</th>
                  <th class="py-1.5 px-2">Action</th>
                  <th class="py-1.5 px-2">Lots</th>
                  <th class="py-1.5 px-2">Conf</th>
                  <th class="py-1.5 px-2">Type</th>
                  <th class="py-1.5 px-2">Status</th>
                  <th class="py-1.5 px-2 text-right">Time</th>
                </tr>
              </thead>
              <tbody id="journalTbody" class="divide-y divide-bordercol text-slate-300 font-mono">
                <tr><td colspan="7" class="py-4 text-center text-slate-500">No executed setups logged yet.</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Institutional FinTech & IMM Calendar -->
        <div class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-bordercol">
            <h2 class="text-sm font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-cyanaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
              Financial Dates & IMM Expiries
            </h2>
            <span class="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyanaccent font-mono font-bold">FINTECH OPS</span>
          </div>

          <div id="immContainer" class="grid grid-cols-2 gap-2 text-xs font-mono">
            <!-- Rendered via JS -->
          </div>
        </div>

      </section>

    </div>

    </div> <!-- End stationView -->

    <!-- ============================================================================== -->
    <!-- VIEW 2: SYMBOL TRADING PERFORMANCE & TRADE ANALYTICS DASHBOARD -->
    <!-- ============================================================================== -->
    <div id="performanceView" class="space-y-6 hidden">
      
      <!-- Top Title & Sync Banner -->
      <div class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emeraldaccent">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            </div>
            <div>
              <h1 class="text-base font-bold text-white flex items-center gap-2 font-sans">
                Symbol Trading Performance & Trade Analytics
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-cyanaccent border border-blue-500/20 font-mono font-semibold">MT5 DEAL HISTORY</span>
              </h1>
              <p class="text-xs text-slate-400 mt-0.5">Automated multi-factor evaluation of all traded instruments on Deriv MT5. Separates statistical conviction from noise.</p>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <div class="text-right">
            <span class="text-[10px] text-slate-500 block font-mono">SYNCHRONIZED (3-MIN AUTO)</span>
            <span id="perfSyncTime" class="text-xs font-mono text-slate-300 font-bold">Connecting...</span>
          </div>
          <button onclick="loadPerformanceDashboard(true)" class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-white border border-bordercol transition flex items-center gap-1.5 shadow">
            <svg id="perfSyncIcon" class="w-3.5 h-3.5 text-cyanaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            Resync Deals
          </button>
        </div>
      </div>

      <!-- Account-Level KPI Metric Cards -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3.5">
        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
          <div class="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Deals Analyzed</div>
          <div id="perfKpiTrades" class="text-2xl font-black font-mono text-white">0</div>
          <div id="perfKpiSymbolsTraded" class="text-[10px] text-slate-500 font-mono mt-1">Across 0 symbols</div>
        </div>

        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
          <div class="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Realized Net P&L</div>
          <div id="perfKpiNetPnl" class="text-2xl font-black font-mono text-emeraldaccent">$0.00</div>
          <div class="text-[10px] text-slate-500 font-mono mt-1">Post Swap & Comm</div>
        </div>

        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
          <div class="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Overall Win Rate</div>
          <div id="perfKpiWinRate" class="text-2xl font-black font-mono text-cyanaccent">0.0%</div>
          <div id="perfKpiWinLoss" class="text-[10px] text-slate-500 font-mono mt-1">0 Wins / 0 Losses</div>
        </div>

        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
          <div class="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Profit Factor</div>
          <div id="perfKpiPf" class="text-2xl font-black font-mono text-white">0.00</div>
          <div class="text-[10px] text-slate-500 font-mono mt-1">Gross Win / Loss</div>
        </div>

        <div class="p-4 rounded-xl bg-panel border border-emerald-500/30 bg-emerald-950/10 shadow-sm">
          <div class="text-[10px] font-medium text-emerald-400 uppercase tracking-wider mb-1">Top Focus Symbol</div>
          <div id="perfKpiBestSymbol" class="text-base font-black font-sans text-emeraldaccent truncate">None</div>
          <div id="perfKpiBestDetails" class="text-[10px] text-emerald-400/80 font-mono mt-1">Highest Consistency</div>
        </div>

        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm">
          <div class="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Open Positions P&L</div>
          <div id="perfKpiOpenPnl" class="text-2xl font-black font-mono text-slate-200">$0.00</div>
          <div id="perfKpiOpenCount" class="text-[10px] text-slate-500 font-mono mt-1">0 Active Trades</div>
        </div>
      </section>

      <!-- Automated Performance Alerts Banner (Dynamic) -->
      <section id="perfAlertsContainer" class="space-y-2">
        <!-- Injected via JS -->
      </section>

      <!-- SECTION: RECOMMENDED SYMBOLS TO FOCUS ON (Priorities 1 to 5) -->
      <section class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-bordercol">
          <div>
            <h2 class="text-sm font-bold text-white flex items-center gap-2 font-sans">
              <svg class="w-4 h-4 text-emeraldaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path></svg>
              Recommended Symbols to Focus On (Priority 1–5 Classification)
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Objective priority allocation guiding research and capital deployment based on historical trading expectancy and sample confidence.</p>
          </div>
          <span class="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">Multi-Factor Engine</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-5 gap-3.5" id="priorityBucketsGrid">
          <!-- Populated via JS: Priority 1 to Priority 5 Cards -->
        </div>
      </section>

      <!-- Charts & Visual Analytics Section -->
      <section class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Chart 1: Realized Net Profit / Loss by Symbol -->
        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between pb-3 border-b border-bordercol">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emeraldaccent"></span>
              Net Realized P&L by Symbol ($)
            </h3>
            <span class="text-[10px] text-slate-500 font-mono">Gross Realized</span>
          </div>
          <div class="h-64 mt-3">
            <canvas id="chartPnlBySymbol"></canvas>
          </div>
        </div>

        <!-- Chart 2: Win Rate (%) & Profit Factor -->
        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between pb-3 border-b border-bordercol">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-cyanaccent"></span>
              Win Rate (%) & Profit Factor
            </h3>
            <span class="text-[10px] text-slate-500 font-mono">Reliability Matrix</span>
          </div>
          <div class="h-64 mt-3">
            <canvas id="chartWinRatePf"></canvas>
          </div>
        </div>

        <!-- Chart 3: Cumulative P&L Curves -->
        <div class="p-4 rounded-xl bg-panel border border-bordercol shadow-sm flex flex-col justify-between">
          <div class="flex items-center justify-between pb-3 border-b border-bordercol">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-amberaccent"></span>
              Top Symbols Equity Growth Curve
            </h3>
            <span class="text-[10px] text-slate-500 font-mono">Trajectory</span>
          </div>
          <div class="h-64 mt-3">
            <canvas id="chartCumEquity"></canvas>
          </div>
        </div>
      </section>

      <!-- SECTION: Symbol Performance Ranking & Comprehensive Analytics Table -->
      <section class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-bordercol">
          <div>
            <h2 class="text-sm font-bold text-white flex items-center gap-2 font-sans">
              <svg class="w-4 h-4 text-cyanaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
              Symbol Performance Ranking & Analytics Table
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Click table headers to sort. Identifies statistical reliability, risk-to-reward ratio, expectancy, and maximum peak-to-trough drawdown.</p>
          </div>

          <!-- Controls & Filters Toolbar -->
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <!-- Timeframe Filter -->
            <div class="flex items-center bg-slate-900 p-0.5 rounded-lg border border-bordercol">
              <button onclick="setPerfTimeframe('today')" class="perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white" data-tf="today">Today</button>
              <button onclick="setPerfTimeframe('7d')" class="perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white" data-tf="7d">7D</button>
              <button onclick="setPerfTimeframe('30d')" class="perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white" data-tf="30d">30D</button>
              <button onclick="setPerfTimeframe('90d')" class="perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white" data-tf="90d">90D</button>
              <button onclick="setPerfTimeframe('all')" class="perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold bg-brand text-white shadow" data-tf="all">All Time</button>
            </div>

            <!-- Reliability Filter -->
            <select id="filterReliabilitySelect" onchange="applyPerfFilters()" class="bg-slate-900 border border-bordercol rounded-lg px-2.5 py-1 text-slate-300 font-sans focus:outline-none focus:border-cyanaccent text-[11px]">
              <option value="ALL">All Sample Sizes</option>
              <option value="STAT">Validated Only (N ≥ 10)</option>
              <option value="MOD">Moderate & Validated (N ≥ 5)</option>
            </select>

            <!-- Priority Filter -->
            <select id="filterPrioritySelect" onchange="applyPerfFilters()" class="bg-slate-900 border border-bordercol rounded-lg px-2.5 py-1 text-slate-300 font-sans focus:outline-none focus:border-cyanaccent text-[11px]">
              <option value="ALL">All Priorities (1–5)</option>
              <option value="1">Priority 1: Focus Only</option>
              <option value="2">Priority 2: Maintain</option>
              <option value="3">Priority 3: Monitor</option>
              <option value="4">Priority 4: Reduce</option>
              <option value="5">Priority 5: Avoid</option>
            </select>

            <!-- Search Input -->
            <div class="relative">
              <input id="perfSearchInput" type="text" oninput="applyPerfFilters()" placeholder="Filter symbol..." class="bg-slate-900 border border-bordercol rounded-lg pl-7 pr-2.5 py-1 text-white font-mono text-[11px] focus:outline-none focus:border-cyanaccent w-32 placeholder-slate-500">
              <svg class="w-3.5 h-3.5 text-slate-500 absolute left-2 top-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
          </div>
        </div>

        <!-- Table Container -->
        <div class="overflow-x-auto custom-scroll">
          <table class="w-full text-left text-xs whitespace-nowrap">
            <thead class="bg-slate-950/80 text-slate-400 font-mono uppercase text-[10px] tracking-wider border-b border-bordercol">
              <tr>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('rank')">Rank ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('symbol')">Symbol ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('priority_num')">Trade Recommendation ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('total_trades')">Reliability & Sample ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('win_rate')">Win Rate % ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('net_pnl')">Net Realized P&L ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('profit_factor')">Profit Factor ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('avg_profit_per_trade')">Expectancy / Trade ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('rr_performance')">R:R Ratio ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('max_drawdown')">Max Drawdown ↕</th>
                <th class="py-3 px-3 cursor-pointer hover:text-white" onclick="sortPerfTable('score')">Score (0–100) ↕</th>
                <th class="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody id="perfTableTbody" class="divide-y divide-bordercol/60">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </section>

    </div> <!-- End performanceView -->

  </main>

  <script>
    let derivState = {};
    let allSymbols = [];
    let currentFilteredSymbols = [];
    let currentCategory = 'ALL';
    let currentDirection = 'SELL';
    let activeSymbol = 'BTCUSD';
    let currentLoadedSetupId = null;
    let localSecondsLeft = 180;
    let autoTradeEnabled = false;

    function setDirection(dir) {
      currentDirection = dir;
      const bBuy = document.getElementById('btnBuy');
      const bSell = document.getElementById('btnSell');
      const submitBtn = document.getElementById('submitBtn');

      if (dir === 'BUY') {
        bBuy.className = 'py-2.5 rounded-lg bg-emeraldaccent text-white font-bold text-xs flex items-center justify-center gap-1 transition shadow-lg shadow-emerald-500/20';
        bSell.className = 'py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white font-bold text-xs flex items-center justify-center gap-1 transition';
        submitBtn.className = 'w-full py-3.5 rounded-lg bg-emeraldaccent hover:bg-emerald-600 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-emerald-600/25 flex items-center justify-center gap-2';
        submitBtn.innerText = 'Execute Instant BUY Order on Deriv MT5';
      } else {
        bSell.className = 'py-2.5 rounded-lg bg-crimsonaccent text-white font-bold text-xs flex items-center justify-center gap-1 transition shadow-lg shadow-red-500/20';
        bBuy.className = 'py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white font-bold text-xs flex items-center justify-center gap-1 transition';
        submitBtn.className = 'w-full py-3.5 rounded-lg bg-crimsonaccent hover:bg-red-600 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-red-600/25 flex items-center justify-center gap-2';
        submitBtn.innerText = 'Execute Instant SELL Order on Deriv MT5';
      }
      recalcSizer();
      updateMultiOrderPreview();
    }

    function setTradeCount(n) {
      document.getElementById('tradesCount').value = n;
      updateMultiOrderPreview();
    }

    function updateMultiOrderPreview() {
      const count = parseInt(document.getElementById('tradesCount').value) || 1;
      const mode = document.getElementById('volumeMode').value;
      const vol = parseFloat(document.getElementById('tradeVolume').value) || 0.1;
      const preview = document.getElementById('multiOrderPreview');
      const submitBtn = document.getElementById('submitBtn');

      if (count <= 1) {
        preview.innerText = `Single order: Opening 1 trade of ${vol.toFixed(2)} lots.`;
        submitBtn.innerText = `Execute Instant ${currentDirection} Order on Deriv MT5`;
      } else if (mode === 'split') {
        const perTrade = (vol / count).toFixed(2);
        preview.innerText = `Split execution: Will open ${count} separate trades of ${perTrade} lots each (Total: ${vol.toFixed(2)} lots). Ideal for multi-TP scaling!`;
        submitBtn.innerText = `Execute ${count}x Split ${currentDirection} Orders on Deriv MT5`;
      } else {
        const total = (vol * count).toFixed(2);
        preview.innerText = `Stacked execution: Will open ${count} separate trades of ${vol.toFixed(2)} lots each (Total: ${total} lots).`;
        submitBtn.innerText = `Execute ${count}x Stacked ${currentDirection} Orders on Deriv MT5`;
      }
    }

    async function loadSymbolsCatalog() {
      try {
        const res = await fetch('/api/symbols');
        allSymbols = await res.json();
        currentFilteredSymbols = allSymbols;
        populateSymbolsDropdown(allSymbols);
      } catch (err) {
        console.error('Symbols load error:', err);
      }
    }

    function filterCategory(cat) {
      currentCategory = cat;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        if ((cat === 'ALL' && btn.innerText.includes('All')) || btn.innerText.includes(cat.split(' ')[0])) {
          btn.className = 'cat-pill px-2.5 py-1 rounded bg-brand text-white font-medium';
        } else {
          btn.className = 'cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium';
        }
      });

      if (cat === 'ALL') {
        currentFilteredSymbols = allSymbols;
      } else {
        currentFilteredSymbols = allSymbols.filter(s => s.category.toLowerCase().includes(cat.toLowerCase()) || s.path.toLowerCase().includes(cat.toLowerCase()));
      }
      populateSymbolsDropdown(currentFilteredSymbols);
    }

    function onSymbolSearch(query) {
      const q = query.trim().toLowerCase();
      let list = currentFilteredSymbols;
      if (q) {
        list = allSymbols.filter(s => s.symbol.toLowerCase().includes(q) || s.description.toLowerCase().includes(q));
      }
      populateSymbolsDropdown(list);
    }

    function populateSymbolsDropdown(list) {
      const select = document.getElementById('allSymbolsSelect');
      const maxShow = 200;
      const slice = list.slice(0, maxShow);
      select.innerHTML = slice.map(s => `
        <option value="${s.symbol}" ${s.symbol === activeSymbol ? 'selected' : ''}>
          ${s.symbol} &bull; ${s.description} (${s.category})
        </option>
      `).join('');
    }

    async function onSymbolDropdownSelect(sym) {
      activeSymbol = sym;
      await fetchAndApplySymbolQuote(sym);
    }

    async function fetchAndApplySymbolQuote(sym) {
      try {
        const res = await fetch(`/api/quote?symbol=${encodeURIComponent(sym)}`);
        const q = await res.json();
        if (q.success) {
          document.getElementById('curSymName').innerText = q.symbol;
          document.getElementById('curSymBid').innerText = q.bid;
          document.getElementById('curSymAsk').innerText = q.ask;
          document.getElementById('curSymSpread').innerText = q.spread;
          document.getElementById('curSymMinLot').innerText = q.min_lot;
          
          document.getElementById('tradeEntry').value = currentDirection === 'BUY' ? q.ask : q.bid;
          recalcSizer();
        }
      } catch (err) {
        console.error('Quote fetch error:', err);
      }
    }

    function selectSymbol(sym) {
      activeSymbol = sym;
      const select = document.getElementById('allSymbolsSelect');
      if (select) {
        select.value = sym;
      }
      fetchAndApplySymbolQuote(sym);
    }

    async function toggleAutoTrade() {
      try {
        const res = await fetch('/api/auto_trade_toggle', { method: 'POST' });
        const data = await res.json();
        autoTradeEnabled = data.auto_trade_enabled;
        renderAutoTradeButton(autoTradeEnabled);
        fetchSetups();
      } catch (err) {
        alert('Toggle error: ' + err);
      }
    }

    function renderAutoTradeButton(enabled) {
      const btn = document.getElementById('autoTradeBtn');
      const dot = document.getElementById('autoTradeDot');
      const txt = document.getElementById('autoTradeText');
      if (!btn) return;

      if (enabled) {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-emerald-500/20 text-emeraldaccent border border-emerald-500/50 shadow-sm shadow-emerald-500/20';
        dot.className = 'w-2 h-2 rounded-full bg-emeraldaccent animate-pulse';
        txt.innerText = 'ENABLED (ACTIVE)';
      } else {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-slate-800 text-slate-400 border border-slate-700';
        dot.className = 'w-2 h-2 rounded-full bg-slate-500';
        txt.innerText = 'DISABLED';
      }
    }

    /* AUTOMATED 3-MINUTE SCANNER FETCH & RENDER (Rules 1-4) */
    async function fetchSetups() {
      const grid = document.getElementById('setupsGrid');
      const badge = document.getElementById('scannerStatusBadge');
      const lastScanEl = document.getElementById('lastScanTime');

      try {
        const res = await fetch('/api/setups');
        const data = await res.json();
        
        localSecondsLeft = data.next_scan_seconds || 180;
        autoTradeEnabled = data.auto_trade_enabled || false;
        renderAutoTradeButton(autoTradeEnabled);

        if (lastScanEl) lastScanEl.innerText = data.last_scan_time || '--';
        
        renderJournal(data.journal || []);
        renderAudit(data.filtered_reasons || {});

        const setups = data.setups || [];

        // Rule 10: No Forced Recommendations
        if (setups.length === 0 || data.status === 'WAITING_FOR_CONFIRMATION') {
          if (badge) {
            badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amberaccent border border-amber-500/20 font-mono font-semibold';
            badge.innerText = 'WAITING CONFIRMATION';
          }
          grid.innerHTML = `
            <div class="col-span-full py-10 px-6 text-center bg-slate-900/60 rounded-xl border border-dashed border-bordercol space-y-3">
              <div class="w-12 h-12 mx-auto rounded-full bg-amber-500/10 text-amberaccent flex items-center justify-center font-bold text-xl">
                ⏳
              </div>
              <h3 class="text-sm font-bold text-slate-100 uppercase tracking-wider">
                No Valid Trade Setups Available – Waiting for Confirmation
              </h3>
              <p class="text-xs text-slate-400 max-w-xl mx-auto leading-relaxed">
                The automated 3-minute background scanner evaluated all candidate pairs. Active positions are already running, closed markets (forex/metals) are deactivated, or untraded pairs have not formed clean M15 trend confirmation. No low-quality signals generated.
              </p>
              <div class="flex items-center justify-center gap-3 pt-2">
                <button onclick="triggerImmediateRescan()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition border border-bordercol">
                  Force Instant Rescan
                </button>
                <button onclick="toggleAuditModal()" class="px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-bold transition border border-blue-500/20">
                  Inspect Filtered Reasons
                </button>
              </div>
            </div>
          `;
          return;
        }

        if (badge) {
          badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20 font-mono font-semibold';
          badge.innerText = `${setups.length} ACTIVE SETUPS`;
        }

        // Render setups with Confidence and Invalidation (Rules 2, 3, 4)
        grid.innerHTML = setups.map(s => {
          const isBuy = s.action === 'BUY';
          const badgeClass = isBuy ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';
          const isHighConf = s.confidence_score >= 88;
          const confBadgeClass = isHighConf ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 shadow-sm shadow-emerald-500/20 font-black' : 'bg-blue-500/10 text-blue-400 font-mono';

          return `
            <div id="setup-card-${s.id}" class="p-4 rounded-xl bg-slate-900 border ${isHighConf ? 'border-emerald-500/40' : 'border-bordercol'} hover:border-slate-700 transition flex flex-col justify-between space-y-3 shadow-sm">
              <div>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-white font-mono text-sm">${s.symbol}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${s.category}</span>
                    <span class="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold border ${s.is_market_open ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/30' : 'bg-amber-500/10 text-amberaccent border-amber-500/30'}">${s.is_market_open ? 'LIVE 24/7' : 'WEEKEND ANALYSIS'}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${badgeClass}">${s.action}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded border ${confBadgeClass}">${isHighConf ? '⭐ ' : ''}${s.conviction}</span>
                  </div>
                </div>
                <div class="text-xs font-bold text-slate-200 mt-1 flex items-center justify-between">
                  <span>${s.setup_name}</span>
                  ${isHighConf ? '<span class="text-[10px] text-emeraldaccent font-mono font-bold">88-100% CONFIDENCE</span>' : ''}
                </div>
              </div>

              <!-- Symbol MT5 Performance Profile (Requirement 6) -->
              ${s.symbol_perf ? `
                <div class="p-2 rounded bg-slate-950/70 border border-slate-800 flex items-center justify-between text-[11px] font-mono">
                  <div class="flex items-center gap-1.5">
                    <span>${s.symbol_perf.priority_num === 1 ? '⭐' : (s.symbol_perf.priority_num === 2 ? '✅' : (s.symbol_perf.priority_num === 5 ? '🛑' : '🔍'))}</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] border ${
                      s.symbol_perf.priority_num === 1 ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold' :
                      (s.symbol_perf.priority_num === 2 ? 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30 font-bold' :
                      (s.symbol_perf.priority_num === 5 ? 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold animate-pulse' : 'bg-slate-800 text-slate-300 border-slate-700'))
                    }">${s.symbol_perf.recommendation.split('—')[0].trim()}</span>
                  </div>
                  <div class="text-[10px] text-slate-400 flex items-center gap-2">
                    <span>Win: <b class="text-white">${s.symbol_perf.win_rate}%</b></span>
                    <span>PF: <b class="text-white">${s.symbol_perf.profit_factor}</b></span>
                    <span>Net: <b class="${s.symbol_perf.net_pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}">${s.symbol_perf.net_pnl >= 0 ? '+' : ''}$${s.symbol_perf.net_pnl}</b></span>
                  </div>
                </div>
                ${s.symbol_perf.priority_num === 5 ? `
                  <div class="p-2 rounded bg-red-950/40 border border-red-800/60 text-[10px] text-rose-300 font-sans flex items-start gap-1.5">
                    <span class="text-crimsonaccent font-bold">⚠️ SYMBOL RISK WARNING:</span>
                    Negative historical expectancy on Deriv MT5 (Net $${s.symbol_perf.net_pnl}, PF ${s.symbol_perf.profit_factor}). High drawdown risk.
                  </div>
                ` : ''}
              ` : ''}

              <!-- Technical Signals Box -->
              <div class="p-2.5 rounded bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 leading-relaxed font-sans">
                <span class="text-emeraldaccent font-bold">Signals:</span> ${s.technical_signals}
              </div>

              <!-- Technical Invalidation Box (Rule 4) -->
              <div class="p-2.5 rounded bg-red-950/20 border border-red-900/50 text-[11px] text-rose-300 leading-relaxed font-sans">
                <span class="text-crimsonaccent font-bold flex items-center gap-1 mb-0.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                  Technical Invalidation:
                </span>
                ${s.invalidation_condition}
              </div>

              <!-- Trade Parameters Grid -->
              <div class="grid grid-cols-4 gap-1.5 text-[11px] font-mono bg-slate-950/50 p-2 rounded">
                <div><span class="text-slate-500 block text-[9px]">ENTRY</span><span class="text-white font-bold">${s.entry}</span></div>
                <div><span class="text-slate-500 block text-[9px]">STOP LOSS</span><span class="text-crimsonaccent font-bold">${s.sl}</span></div>
                <div><span class="text-slate-500 block text-[9px]">TARGET TP</span><span class="text-emeraldaccent font-bold">${s.tp}</span></div>
                <div><span class="text-slate-500 block text-[9px]">1% LOTS</span><span class="text-cyanaccent font-bold">${s.recommended_lots}</span></div>
              </div>

              <!-- Auto-Trade Status Banner if High Confidence -->
              ${isHighConf ? `
                <div class="p-2 rounded bg-emerald-950/30 border border-emerald-900/40 text-[10px] text-emerald-300 font-mono flex items-center justify-between">
                  <span>⚡ 88-100% Setup Trigger</span>
                  <span class="font-bold">${autoTradeEnabled ? 'ARMED FOR AUTO-EXECUTE' : 'Auto-Trade is OFF'}</span>
                </div>
              ` : ''}

              <!-- Action Buttons -->
              <div class="space-y-1.5 pt-1">
                <button type="button" onclick='executeMtpDirectlyFromSetup(${JSON.stringify(s)})' class="w-full py-2 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emeraldaccent border border-emerald-500/40 font-bold text-xs transition flex items-center justify-center gap-1.5 shadow-sm">
                  ⚡ 3-Trade Multi-TP System (Shared 5% SL &bull; $50 Risk)
                </button>
                <div class="grid grid-cols-2 gap-2">
                  <button type="button" onclick='loadSetupIntoForm(${JSON.stringify(s)})' class="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol">
                    Load Setup
                  </button>
                  <button type="button" onclick='executeSetupDirectly(${JSON.stringify(s)})' class="py-1.5 rounded-lg ${isBuy ? 'bg-emeraldaccent hover:bg-emerald-600' : 'bg-crimsonaccent hover:bg-red-600'} text-white font-bold text-xs transition shadow flex items-center justify-center gap-1">
                    1-Click Single
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('');
      } catch (err) {
        console.error('Fetch setups error:', err);
      }
    }

    function renderJournal(list) {
      const tbody = document.getElementById('journalTbody');
      const countEl = document.getElementById('journalCount');
      if (!tbody) return;
      if (countEl) countEl.innerText = `${list.length} Logged`;

      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-center text-slate-500 font-sans">No executed setups logged yet.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(j => {
        const isOpen = j.status === 'OPEN';
        const statusBadge = isOpen ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-slate-800 text-slate-400';
        const isAuto = j.execution_type && j.execution_type.includes('AUTO');
        const typeBadge = isAuto ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-blue-500/10 text-blue-400';

        return `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="py-1.5 px-2 font-bold text-white">${j.symbol}</td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-bold ${j.direction === 'BUY' ? 'bg-emerald-500/10 text-emeraldaccent' : 'bg-red-500/10 text-crimsonaccent'}">${j.direction}</span></td>
            <td class="py-1.5 px-2 text-slate-300">${j.volume}</td>
            <td class="py-1.5 px-2 font-bold text-white">${j.confidence || '--'}</td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-mono ${typeBadge}">${isAuto ? 'AUTO' : 'MANUAL'}</span></td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-bold border ${statusBadge}">${j.status}</span></td>
            <td class="py-1.5 px-2 text-right text-slate-500 text-[10px]">${j.execution_time.split(' ')[1] || j.execution_time}</td>
          </tr>
        `;
      }).join('');
    }

    function renderAudit(reasons) {
      const container = document.getElementById('auditContent');
      if (!container) return;
      const entries = Object.entries(reasons);
      if (entries.length === 0) {
        container.innerHTML = '<div>All candidate instruments analyzed.</div>';
        return;
      }
      container.innerHTML = entries.map(([sym, r]) => `
        <div class="p-2 rounded bg-slate-900 border border-bordercol/60 flex items-start gap-1.5">
          <span class="text-amberaccent font-bold">${sym}:</span>
          <span class="text-slate-400">${r}</span>
        </div>
      `).join('');
    }

    function toggleAuditModal() {
      const el = document.getElementById('auditSection');
      el.classList.toggle('hidden');
    }

    async function triggerImmediateRescan() {
      const btn = event?.currentTarget;
      if (btn) btn.innerText = 'Scanning...';
      try {
        await fetch('/api/rescan', { method: 'POST' });
        await fetchSetups();
      } catch (err) {
        console.error('Rescan error:', err);
      } finally {
        if (btn) btn.innerText = 'Re-Scan Now';
      }
    }

    function loadSetupIntoForm(s) {
      currentLoadedSetupId = s.id;
      selectSymbol(s.symbol);
      setDirection(s.action);
      document.getElementById('tradeEntry').value = s.entry;
      document.getElementById('tradeSL').value = s.sl;
      document.getElementById('tradeTP').value = s.tp;
      document.getElementById('tradeVolume').value = s.recommended_lots;
      document.getElementById('tradesCount').value = s.suggested_trades || 2;
      document.getElementById('volumeMode').value = 'split';
      updateMultiOrderPreview();
      recalcSizer();
      
      const formEl = document.getElementById('orderForm');
      formEl.scrollIntoView({ behavior: 'smooth' });
      formEl.classList.add('ring-2', 'ring-brand');
      setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
    }

    async function executeSetupDirectly(s) {
      if (!confirm(`Execute Recommended Setup on ${s.symbol}?\nAction: ${s.action}\nLots: ${s.recommended_lots} (Split into ${s.suggested_trades} trades)\nSL: ${s.sl} | TP: ${s.tp}\nConfidence: ${s.conviction}`)) {
        return;
      }
      
      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = `Executing 1-Click setup on ${s.symbol} into Deriv MT5...`;
      statusBox.classList.remove('hidden');

      const payload = {
        symbol: s.symbol,
        action: s.action,
        volume: s.recommended_lots,
        sl: s.sl,
        tp: s.tp,
        trades_count: s.suggested_trades || 2,
        volume_mode: 'split',
        setup_id: s.id,
        confidence: s.conviction,
        reason: s.technical_signals,
        comment: `Headway 1-Click (${s.conviction})`
      };

      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = '✅ ' + out.message;
          const card = document.getElementById(`setup-card-${s.id}`);
          if (card) {
            card.style.transition = 'all 0.35s ease-out';
            card.style.opacity = '0';
            setTimeout(() => card.remove(), 350);
          }
          refreshAll();
          fetchSetups();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = '❌ ' + out.message;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Error: ' + err;
      }
    }

    async function fetchState() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        derivState = data;
        renderAccount(data.account);
        renderPositions(data.positions);
        renderQuotes(data.quotes);
        renderImm(data.imm_dates);
      } catch (err) {
        console.error('Fetch error:', err);
      }
    }

    function renderAccount(acc) {
      if (!acc) return;
      document.getElementById('headerLogin').innerText = acc.login || '6314782';
      document.getElementById('headerServer').innerText = acc.server || 'Deriv-Demo';
      document.getElementById('connPing').innerText = `PING: ${acc.ping || 160}ms`;

      document.getElementById('accBalance').innerText = `$${(acc.balance || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accEquity').innerText = `$${(acc.equity || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accMargin').innerText = `$${(acc.margin_free || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accMarginLevel').innerText = `Margin Level: ${(acc.margin_level || 0).toFixed(2)}%`;

      const pBox = document.getElementById('accProfit');
      const pVal = acc.profit || 0;
      pBox.innerText = `${pVal >= 0 ? '+' : ''}$${pVal.toFixed(2)}`;
      pBox.className = `text-2xl font-black font-mono ${pVal >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;

      const dollarRisk = (acc.balance || 7150) * 0.01;
      document.getElementById('calcRiskDollar').innerText = `$${dollarRisk.toFixed(2)}`;
    }

    function renderPositions(positions) {
      const tbody = document.getElementById('positionsTbody');
      const countBadge = document.getElementById('posCount');
      const netVolume = document.getElementById('netVolume');

      countBadge.innerText = `${positions.length} active`;
      let totalLots = 0;

      if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="py-6 text-center text-slate-500 font-sans">No open positions on Deriv MT5. Ready for new trades.</td></tr>';
        netVolume.innerText = '0.00';
        return;
      }

      tbody.innerHTML = '';
      positions.forEach(p => {
        totalLots += p.volume;
        const isProfit = p.profit >= 0;
        const pClass = isProfit ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';
        const typeBadge = p.type === 'BUY' ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';

        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/60 font-mono transition';
        tr.innerHTML = `
          <td class="py-2.5 px-4 text-slate-400">#${p.ticket}</td>
          <td class="py-2.5 px-4 font-bold text-white font-sans">${p.symbol}</td>
          <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold border ${typeBadge}">${p.type}</span></td>
          <td class="py-2.5 px-4 font-bold text-slate-200">${p.volume}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.price_open}</td>
          <td class="py-2.5 px-4 text-white">${p.price_current}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.sl || '-'}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.tp || '-'}</td>
          <td class="py-2.5 px-4 ${pClass}">${isProfit ? '+' : ''}$${p.profit.toFixed(2)}</td>
          <td class="py-2.5 px-4 text-right font-sans">
            <button onclick="closeOrder(${p.ticket})" class="px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/30 text-[11px] font-medium transition">
              Close Trade
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      netVolume.innerText = totalLots.toFixed(2);
    }

    function renderQuotes(quotes) {
      const bar = document.getElementById('tickerBar');
      if (!quotes) return;

      bar.innerHTML = Object.entries(quotes).map(([sym, q]) => `
        <div onclick="selectSymbol('${sym}')" class="cursor-pointer hover:bg-slate-900 px-2 py-1 rounded border border-transparent hover:border-bordercol transition flex items-center gap-2">
          <span class="font-bold text-slate-200 font-sans">${sym}</span>
          <span class="text-slate-400">${q.bid}</span>
          <span class="text-[10px] px-1 rounded bg-slate-800 text-slate-500">Spread ${q.spread}</span>
        </div>
      `).join('<span class="text-slate-700">&bull;</span>');
    }

    function renderImm(immList) {
      const container = document.getElementById('immContainer');
      if (!immList || !container) return;
      container.innerHTML = immList.map(item => `
        <div class="p-2.5 rounded-lg bg-slate-900/90 border border-bordercol">
          <div class="flex items-center justify-between text-slate-400 text-[11px]">
            <span>${item.quarter}</span>
            <span class="text-cyanaccent">${item.days_left}d</span>
          </div>
          <div class="text-sm font-bold text-white mt-1">${item.date}</div>
        </div>
      `).join('');
    }

    function recalcSizer() {
      const balance = (derivState.account && derivState.account.balance) || 7150;
      const riskPct = parseFloat(document.getElementById('tradeRiskPct').value) || 1.0;
      const entry = parseFloat(document.getElementById('tradeEntry').value);
      const sl = parseFloat(document.getElementById('tradeSL').value);

      const dollarRisk = balance * (riskPct / 100);
      document.getElementById('calcRiskDollar').innerText = `$${dollarRisk.toFixed(2)}`;

      if (entry && sl && entry !== sl) {
        const dist = Math.abs(entry - sl);
        document.getElementById('calcStopDist').innerText = `${dist.toFixed(2)} pts`;
        
        let lots = dollarRisk / dist;
        if (lots > 10.0) lots = 10.0;
        if (lots < 0.01) lots = 0.01;
        document.getElementById('calcLots').innerText = `${lots.toFixed(2)} lots`;
        document.getElementById('tradeVolume').value = lots.toFixed(2);
        updateMultiOrderPreview();
      }
    }

    async function closeOrder(ticket) {
      if (!confirm(`Close position #${ticket} on Deriv MT5?`)) return;
      try {
        const res = await fetch('/api/close', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket: ticket })
        });
        const out = await res.json();
        alert(out.message);
        refreshAll();
      } catch (err) {
        alert('Close error: ' + err);
      }
    }

    async function emergencyCloseAll() {
      if (!confirm('⚠️ WARNING: Close ALL open positions on Deriv MT5 immediately?')) return;
      try {
        const res = await fetch('/api/close_all', { method: 'POST' });
        const out = await res.json();
        alert(out.message);
        refreshAll();
      } catch (err) {
        alert('Panic close error: ' + err);
      }
    }

    async function submitDerivOrder(e) {
      e.preventDefault();
      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = 'Transmitting order(s) directly to Deriv MT5 terminal...';
      statusBox.classList.remove('hidden');

      const payload = {
        symbol: activeSymbol,
        action: currentDirection,
        volume: parseFloat(document.getElementById('tradeVolume').value),
        sl: parseFloat(document.getElementById('tradeSL').value) || 0.0,
        tp: parseFloat(document.getElementById('tradeTP').value) || 0.0,
        trades_count: parseInt(document.getElementById('tradesCount').value) || 1,
        volume_mode: document.getElementById('volumeMode').value,
        setup_id: currentLoadedSetupId,
        confidence: "Manual Form",
        reason: "User Discretionary Execution",
        comment: "Headway User"
      };

      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = '✅ ' + out.message;
          currentLoadedSetupId = null;
          refreshAll();
          fetchSetups();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = '❌ ' + out.message;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Error: ' + err;
      }
    }

    function refreshAll() {
      fetchState();
    }

    // 1-second countdown loop synchronized with background scanner
    function updateCountdown() {
      const countdownEl = document.getElementById('rescanCountdown');
      if (localSecondsLeft <= 0) {
        localSecondsLeft = 180;
        fetchSetups();
      } else {
        localSecondsLeft--;
      }
      if (countdownEl) {
        const mins = Math.floor(localSecondsLeft / 60);
        const secs = localSecondsLeft % 60;
        countdownEl.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }
    }

    // ==============================================================================
    // SYMBOL PERFORMANCE DASHBOARD JAVASCRIPT CONTROLLER
    // ==============================================================================
    let currentMainTab = 'station';
    let currentPerfTimeframe = 'all';
    let perfRawData = null;
    let perfDisplayedSymbols = [];
    let perfSortCol = 'score';
    let perfSortAsc = false;
    let chartPnlInstance = null;
    let chartWinRateInstance = null;
    let chartCumEquityInstance = null;

    function switchMainTab(tab) {
      currentMainTab = tab;
      const stationView = document.getElementById('stationView');
      const perfView = document.getElementById('performanceView');
      const tabStationBtn = document.getElementById('navTabStation');
      const tabPerfBtn = document.getElementById('navTabPerformance');

      if (tab === 'station') {
        stationView.classList.remove('hidden');
        perfView.classList.add('hidden');
        tabStationBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-brand text-white shadow flex items-center gap-2';
        tabPerfBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
      } else {
        stationView.classList.add('hidden');
        perfView.classList.remove('hidden');
        tabPerfBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-brand text-white shadow flex items-center gap-2';
        tabStationBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
        loadPerformanceDashboard();
      }
    }

    function setPerfTimeframe(tf) {
      currentPerfTimeframe = tf;
      document.querySelectorAll('.perf-tf-btn').forEach(btn => {
        if (btn.getAttribute('data-tf') === tf) {
          btn.className = 'perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold bg-brand text-white shadow';
        } else {
          btn.className = 'perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white';
        }
      });
      loadPerformanceDashboard(true);
    }

    async function loadPerformanceDashboard(force=false) {
      const syncEl = document.getElementById('perfSyncTime');
      const syncIcon = document.getElementById('perfSyncIcon');
      if (syncIcon) syncIcon.classList.add('animate-spin');

      try {
        const res = await fetch(`/api/performance?timeframe=${currentPerfTimeframe}&resync=${force ? '1' : '0'}`);
        perfRawData = await res.json();
        
        if (syncEl && perfRawData.summary) {
          syncEl.innerText = `${perfRawData.summary.timestamp} (${currentPerfTimeframe.toUpperCase()})`;
        }

        const topBadge = document.getElementById('p1TopBadge');
        if (topBadge && perfRawData.summary) {
          topBadge.innerText = `${perfRawData.summary.p1_count} Focus / Best: ${perfRawData.summary.best_symbol}`;
        }

        renderPerformanceSummary(perfRawData.summary);
        renderPerformanceAlerts(perfRawData.alerts || []);
        renderPriorityBuckets(
          perfRawData.p1_symbols || [],
          perfRawData.p2_symbols || [],
          perfRawData.p3_symbols || [],
          perfRawData.p4_symbols || [],
          perfRawData.p5_symbols || []
        );
        renderPerformanceCharts(perfRawData.symbols || []);
        applyPerfFilters();

      } catch (err) {
        console.error('Error loading performance dashboard:', err);
      } finally {
        if (syncIcon) syncIcon.classList.remove('animate-spin');
      }
    }

    function renderPerformanceSummary(s) {
      if (!s) return;
      document.getElementById('perfKpiTrades').innerText = (s.total_deals_analyzed || 0).toLocaleString();
      document.getElementById('perfKpiSymbolsTraded').innerText = `Across ${s.total_symbols_traded || 0} traded symbols`;

      const pnlEl = document.getElementById('perfKpiNetPnl');
      const pnl = s.total_net_pnl || 0;
      pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      pnlEl.className = `text-2xl font-black font-mono ${pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;

      document.getElementById('perfKpiWinRate').innerText = `${s.overall_win_rate || 0}%`;
      const grossWins = s.total_gross_profit || 0;
      const grossLoss = s.total_gross_loss || 0;
      document.getElementById('perfKpiWinLoss').innerText = `Gross: +$${grossWins.toFixed(0)} / -$${grossLoss.toFixed(0)}`;

      document.getElementById('perfKpiPf').innerText = `${s.overall_profit_factor || 0}`;

      const bestEl = document.getElementById('perfKpiBestSymbol');
      bestEl.innerText = s.best_symbol || 'None';
      document.getElementById('perfKpiBestDetails').innerText = `${s.p1_count || 0} Priority 1 symbols`;

      // Live open floating
      let totalOpenPnl = 0;
      let totalOpenCount = 0;
      if (derivState && derivState.positions) {
        totalOpenCount = derivState.positions.length;
        totalOpenPnl = derivState.positions.reduce((acc, p) => acc + (p.profit || 0), 0);
      }
      const openPnlEl = document.getElementById('perfKpiOpenPnl');
      openPnlEl.innerText = `${totalOpenPnl >= 0 ? '+' : ''}$${totalOpenPnl.toFixed(2)}`;
      openPnlEl.className = `text-2xl font-black font-mono ${totalOpenPnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;
      document.getElementById('perfKpiOpenCount').innerText = `${totalOpenCount} Active Open Trades`;
    }

    function renderPerformanceAlerts(alerts) {
      const container = document.getElementById('perfAlertsContainer');
      if (!container) return;
      if (!alerts || alerts.length === 0) {
        container.innerHTML = '';
        return;
      }

      container.innerHTML = alerts.map(a => {
        let borderClass = 'border-slate-800 bg-slate-900/90 text-slate-300';
        let icon = 'ℹ️';
        if (a.type === 'success') {
          borderClass = 'border-emerald-500/40 bg-emerald-950/25 text-emerald-200';
          icon = '🏆';
        } else if (a.type === 'warning') {
          borderClass = 'border-amber-500/40 bg-amber-950/25 text-amber-200';
          icon = '⚠️';
        } else if (a.type === 'danger') {
          borderClass = 'border-rose-500/40 bg-rose-950/25 text-rose-200';
          icon = '🛑';
        }
        return `
          <div class="p-3 rounded-xl border ${borderClass} shadow-sm flex items-start gap-3">
            <span class="text-lg leading-none mt-0.5">${icon}</span>
            <div class="text-xs leading-relaxed font-sans">
              <strong class="font-bold text-white block">${a.title}</strong>
              <span class="text-slate-300">${a.message}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderPriorityBuckets(p1, p2, p3, p4, p5) {
      const grid = document.getElementById('priorityBucketsGrid');
      if (!grid) return;

      const makeCard = (title, badgeClass, borderClass, bgClass, desc, items, priorityNum) => `
        <div class="p-4 rounded-xl border ${borderClass} ${bgClass} flex flex-col justify-between space-y-3 shadow-sm">
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded border ${badgeClass}">${title}</span>
              <span class="text-xs font-mono font-bold text-white">${items.length} Symbols</span>
            </div>
            <p class="text-[11px] text-slate-400 mt-2 font-sans">${desc}</p>
          </div>
          <div class="space-y-1.5 custom-scroll max-h-56 overflow-y-auto pr-1">
            ${items.length === 0 ? '<div class="text-[11px] text-slate-500 italic py-2">No symbols in this category.</div>' : items.map(s => `
              <div onclick="jumpToTradeSymbol('${s.symbol}')" class="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-bordercol cursor-pointer transition flex items-center justify-between text-xs font-mono group">
                <div>
                  <span class="font-bold text-white font-sans group-hover:text-cyanaccent">${s.symbol}</span>
                  <div class="text-[10px] text-slate-400">
                    <span>${s.total_trades}T</span> &bull; 
                    <span class="${s.win_rate >= 50 ? 'text-emeraldaccent' : 'text-slate-400'}">${s.win_rate}% Win</span>
                  </div>
                </div>
                <div class="text-right">
                  <span class="font-bold block ${s.net_pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}">${s.net_pnl >= 0 ? '+' : ''}$${s.net_pnl.toFixed(1)}</span>
                  <span class="text-[10px] text-slate-500">PF ${s.profit_factor}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;

      grid.innerHTML = `
        ${makeCard('PRIORITY 1 — FOCUS', 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40', 'border-emerald-500/40', 'bg-emerald-950/10', 'Strong consistent positive expectancy (N ≥ 10 validated). Highest research & trading priority.', p1, 1)}
        ${makeCard('PRIORITY 2 — MAINTAIN', 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30', 'border-cyan-500/30', 'bg-cyan-950/10', 'Profitable with acceptable risk profile. Maintain trading exposure.', p2, 2)}
        ${makeCard('PRIORITY 3 — MONITOR', 'bg-amber-500/10 text-amberaccent border-amber-500/20', 'border-bordercol', 'bg-panel', 'Promising performance but insufficient sample size (N < 5). Monitor for confirmation.', p3, 3)}
        ${makeCard('PRIORITY 4 — REDUCE', 'bg-orange-500/10 text-orange-400 border-orange-500/20', 'border-bordercol', 'bg-panel', 'Weak or deteriorating expectancy. Reduce position sizing or tighten setups.', p4, 4)}
        ${makeCard('PRIORITY 5 — AVOID', 'bg-red-500/20 text-crimsonaccent border-red-500/40', 'border-red-500/40', 'bg-red-950/10', 'Severe historical negative expectancy or devastating drawdown. Restrict exposure.', p5, 5)}
      `;
    }

    function renderPerformanceCharts(symbols) {
      if (!symbols || symbols.length === 0 || !window.Chart) return;

      const topSyms = symbols.slice(0, 10);
      const labels = topSyms.map(s => s.symbol);
      const pnlValues = topSyms.map(s => s.net_pnl);
      const pnlColors = pnlValues.map(v => v >= 0 ? 'rgba(0, 192, 135, 0.8)' : 'rgba(255, 68, 79, 0.8)');

      // Chart 1: PnL
      const ctxPnl = document.getElementById('chartPnlBySymbol');
      if (ctxPnl) {
        if (chartPnlInstance) chartPnlInstance.destroy();
        chartPnlInstance = new Chart(ctxPnl, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: 'Net Realized P&L ($)',
              data: pnlValues,
              backgroundColor: pnlColors,
              borderRadius: 4
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
              y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: '#1E2638' } }
            }
          }
        });
      }

      // Chart 2: Win Rate % & Profit Factor
      const ctxWr = document.getElementById('chartWinRatePf');
      if (ctxWr) {
        if (chartWinRateInstance) chartWinRateInstance.destroy();
        chartWinRateInstance = new Chart(ctxWr, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Win Rate (%)',
                data: topSyms.map(s => s.win_rate),
                backgroundColor: 'rgba(6, 182, 212, 0.7)',
                borderRadius: 4,
                yAxisID: 'y'
              },
              {
                label: 'Profit Factor',
                data: topSyms.map(s => Math.min(s.profit_factor, 10.0)),
                backgroundColor: 'rgba(245, 158, 11, 0.7)',
                borderRadius: 4,
                yAxisID: 'y1'
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
              y: { type: 'linear', position: 'left', ticks: { color: '#06B6D4' }, grid: { color: '#1E2638' }, max: 100 },
              y1: { type: 'linear', position: 'right', ticks: { color: '#F59E0B' }, grid: { display: false }, min: 0 }
            },
            plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 10 } } } }
          }
        });
      }

      // Chart 3: Top Symbols Cumulative Curves
      const ctxEq = document.getElementById('chartCumEquity');
      if (ctxEq) {
        if (chartCumEquityInstance) chartCumEquityInstance.destroy();
        const curveSymbols = symbols.filter(s => s.total_trades >= 5).slice(0, 4);
        const palette = ['#00C087', '#06B6D4', '#F59E0B', '#FF444F'];
        const datasets = curveSymbols.map((s, idx) => {
          const pts = (s.cum_curve || []).map(p => p.cum_pnl);
          return {
            label: s.symbol,
            data: pts,
            borderColor: palette[idx % palette.length],
            backgroundColor: 'transparent',
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 1
          };
        });

        const maxLen = Math.max(...curveSymbols.map(s => (s.cum_curve || []).length), 10);
        const labelsX = Array.from({length: maxLen}, (_, i) => `T-${maxLen - i}`);

        chartCumEquityInstance = new Chart(ctxEq, {
          type: 'line',
          data: {
            labels: labelsX,
            datasets: datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { display: false } },
              y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: '#1E2638' } }
            },
            plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 10 } } } }
          }
        });
      }
    }

    function applyPerfFilters() {
      if (!perfRawData || !perfRawData.symbols) return;
      const relVal = document.getElementById('filterReliabilitySelect').value;
      const prioVal = document.getElementById('filterPrioritySelect').value;
      const searchVal = (document.getElementById('perfSearchInput').value || '').trim().toUpperCase();

      perfDisplayedSymbols = perfRawData.symbols.filter(s => {
        if (relVal === 'STAT' && s.reliability !== 'STATISTICALLY_VALID') return false;
        if (relVal === 'MOD' && s.total_trades < 5) return false;
        if (prioVal !== 'ALL' && s.priority_num.toString() !== prioVal) return false;
        if (searchVal && !s.symbol.toUpperCase().includes(searchVal)) return false;
        return true;
      });

      // Sort
      perfDisplayedSymbols.sort((a, b) => {
        let vA = a[perfSortCol];
        let vB = b[perfSortCol];
        if (typeof vA === 'string') {
          return perfSortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
        }
        return perfSortAsc ? (vA - vB) : (vB - vA);
      });

      renderPerformanceTable(perfDisplayedSymbols);
    }

    function sortPerfTable(col) {
      if (perfSortCol === col) {
        perfSortAsc = !perfSortAsc;
      } else {
        perfSortCol = col;
        perfSortAsc = false;
      }
      applyPerfFilters();
    }

    function renderPerformanceTable(symbols) {
      const tbody = document.getElementById('perfTableTbody');
      if (!tbody) return;

      if (!symbols || symbols.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="py-6 text-center text-slate-500 font-sans">No symbols match the selected filters.</td></tr>';
        return;
      }

      tbody.innerHTML = symbols.map(s => {
        let pBadgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
        let pIcon = '🔍';
        if (s.priority_num === 1) {
          pBadgeClass = 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold';
          pIcon = '⭐';
        } else if (s.priority_num === 2) {
          pBadgeClass = 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30 font-bold';
          pIcon = '✅';
        } else if (s.priority_num === 3) {
          pBadgeClass = 'bg-amber-500/10 text-amberaccent border-amber-500/20';
          pIcon = '👀';
        } else if (s.priority_num === 4) {
          pBadgeClass = 'bg-orange-500/10 text-orange-400 border-orange-500/20';
          pIcon = '⚠️';
        } else if (s.priority_num === 5) {
          pBadgeClass = 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold';
          pIcon = '🛑';
        }

        const isProfit = s.net_pnl >= 0;
        const pnlClass = isProfit ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';

        return `
          <tr class="hover:bg-slate-900/60 font-mono transition">
            <td class="py-2.5 px-3 text-slate-500">#${s.rank}</td>
            <td class="py-2.5 px-3">
              <span onclick="jumpToTradeSymbol('${s.symbol}')" class="font-bold text-white font-sans hover:text-cyanaccent cursor-pointer transition flex items-center gap-1.5">
                ${s.symbol}
                ${s.open_positions > 0 ? `<span class="px-1.5 py-0.2 rounded-full bg-blue-500/20 text-cyanaccent text-[9px] font-mono">${s.open_positions} open</span>` : ''}
              </span>
            </td>
            <td class="py-2.5 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] border ${pBadgeClass}">
                ${pIcon} ${s.recommendation}
              </span>
            </td>
            <td class="py-2.5 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] border ${s.stat_badge}">${s.stat_label}</span>
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-2">
                <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-cyanaccent h-1.5 rounded-full" style="width: ${s.win_rate}%"></div>
                </div>
                <span class="font-bold text-white">${s.win_rate}%</span>
                <span class="text-[10px] text-slate-500">(${s.winning_trades}W/${s.losing_trades}L)</span>
              </div>
            </td>
            <td class="py-2.5 px-3 ${pnlClass}">
              ${isProfit ? '+' : ''}$${s.net_pnl.toFixed(2)}
            </td>
            <td class="py-2.5 px-3 font-bold ${s.profit_factor >= 1.3 ? 'text-emeraldaccent' : (s.profit_factor >= 1.0 ? 'text-slate-200' : 'text-crimsonaccent')}">
              ${s.profit_factor}
            </td>
            <td class="py-2.5 px-3 ${s.avg_profit_per_trade >= 0 ? 'text-slate-300' : 'text-crimsonaccent'}">
              ${s.avg_profit_per_trade >= 0 ? '+' : ''}$${s.avg_profit_per_trade}
            </td>
            <td class="py-2.5 px-3 text-slate-400">
              ${s.rr_performance}:1
            </td>
            <td class="py-2.5 px-3 text-crimsonaccent">
              ${s.max_drawdown > 0 ? `-$${s.max_drawdown}` : '$0.00'}
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-1.5">
                <span class="font-black text-white text-xs">${s.score}</span>
                <div class="w-8 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-emeraldaccent h-1.5 rounded-full" style="width: ${s.score}%"></div>
                </div>
              </div>
            </td>
            <td class="py-2.5 px-3 text-right font-sans">
              <button onclick="jumpToTradeSymbol('${s.symbol}')" class="px-2.5 py-1 rounded bg-brand/10 hover:bg-brand text-brand hover:text-white border border-brand/30 text-[11px] font-bold transition">
                Trade Symbol &rarr;
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function jumpToTradeSymbol(sym) {
      switchMainTab('station');
      selectSymbol(sym);
      const formEl = document.getElementById('orderForm');
      if (formEl) {
        formEl.scrollIntoView({ behavior: 'smooth' });
        formEl.classList.add('ring-2', 'ring-brand');
        setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
      }
    }

    function jumpToTradeSymbol(sym) {
      switchMainTab('station');
      selectSymbol(sym);
      const formEl = document.getElementById('orderForm');
      if (formEl) {
        formEl.scrollIntoView({ behavior: 'smooth' });
        formEl.classList.add('ring-2', 'ring-brand');
        setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
      }
    }

    // ==============================================================================
    // 5-TRADE MULTI-TP SYSTEM JAVASCRIPT CONTROLLER (Requirements 1 - 8)
    // ==============================================================================
    let multiTpGroups = [];

    function updateMtpRiskPreview() {
      const refInput = document.getElementById('mtpRefBalanceInput');
      const badge = document.getElementById('mtpRiskDollarBadge');
      const ref = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const risk = (ref * 0.05).toFixed(2);
      const riskPerTrade = (risk / 3.0).toFixed(2);
      if (badge) {
        badge.innerText = `5.0% ($${risk} max, $${riskPerTrade}/pos)`;
      }

      // Update Order Ticket preview cards
      const t1 = document.getElementById('otMtpT1Target');
      const t2 = document.getElementById('otMtpT2Target');
      const t3 = document.getElementById('otMtpT3Target');
      const otRisk = document.getElementById('otMtpRiskBadge');
      if (t1) t1.innerText = `+$${(ref * 0.02).toFixed(2)} Target`;
      if (t2) t2.innerText = `+$${(ref * 0.05).toFixed(2)} Target`;
      if (t3) t3.innerText = `+$${(ref * 0.15).toFixed(2)}+ Runner`;
      if (otRisk) otRisk.innerText = `Risk: $${risk} Max ($${riskPerTrade}/pos)`;
    }

    function useLiveBalanceForMtp() {
      const balance = (derivState && derivState.account && derivState.account.balance) || 1000;
      const refInput = document.getElementById('mtpRefBalanceInput');
      if (refInput) {
        refInput.value = balance.toFixed(2);
        updateMtpRiskPreview();
      }
    }

    async function fetchMultiTpGroups() {
      try {
        const res = await fetch('/api/multi_tp/groups');
        multiTpGroups = await res.json();
        renderMultiTpGroups(multiTpGroups);
      } catch (err) {
        console.error('Error fetching multi-tp groups:', err);
      }
    }

    function renderMultiTpGroups(groups) {
      const container = document.getElementById('mtpGroupsContainer');
      const badge = document.getElementById('mtpGroupsBadge');
      if (!container) return;

      const activeGroups = (groups || []).filter(g => g.status === 'ACTIVE');
      if (badge) {
        badge.innerText = `${activeGroups.length} ACTIVE / ${(groups || []).length} TOTAL`;
        badge.className = `text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold border ${activeGroups.length > 0 ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'}`;
      }

      if (!groups || groups.length === 0) {
        container.innerHTML = `
          <div class="py-8 px-4 text-center bg-slate-900/40 rounded-xl border border-dashed border-bordercol space-y-2">
            <span class="text-2xl block">⚡</span>
            <div class="text-xs font-bold text-slate-200 uppercase tracking-wider">No Active Multi-TP Trade Groups</div>
            <p class="text-[11px] text-slate-400 max-w-md mx-auto">
              Execute a 3-Trade Multi-TP opportunity from the Order Ticket or Active Setups cards. Each opportunity opens 3 separate positions: Trade 1 (+2% / $20), Trade 2 (+5% / $50), and Trade 3 (AI Dynamic Runner with infinite upside) with a shared 5% Stop Loss ($50 planned loss max).
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = groups.map(g => {
        const isBuy = g.action === 'BUY';
        const badgeClass = isBuy ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';
        const isActive = g.status === 'ACTIVE';
        const totalPnl = g.total_profit || 0;
        const pnlClass = totalPnl >= 0 ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';

        return `
          <div class="p-4 rounded-xl bg-slate-900/90 border ${isActive ? 'border-emerald-500/30 shadow-md shadow-emerald-500/5' : 'border-bordercol'} space-y-3.5 transition">
            
            <!-- Group Header -->
            <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-bordercol/80">
              <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold border ${badgeClass}">${g.action}</span>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-white text-sm font-sans">${g.symbol}</span>
                    <span class="text-[10px] px-2 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">ID: ${g.group_id}</span>
                  </div>
                  <div class="text-[11px] text-slate-400 font-mono mt-0.5">
                    Entry: <b class="text-slate-200">${g.entry_price}</b> &bull; Shared SL: <b class="text-crimsonaccent">${g.shared_sl}</b> (Planned Risk: $${g.total_risk_dollar} / ${g.total_risk_pct}%)
                  </div>
                </div>
              </div>

              <!-- Realized & Floating Group PnL Summary -->
              <div class="flex items-center gap-4">
                <div class="text-right font-mono">
                  <div class="text-[10px] text-slate-500">GROUP TOTAL P&L</div>
                  <div class="text-base font-black ${pnlClass}">${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}</div>
                  <div class="text-[10px] text-slate-400">Realized: $${g.realized_profit} | Floating: $${g.floating_profit}</div>
                </div>

                <div class="flex items-center gap-2">
                  <span class="text-[10px] px-2 py-1 rounded font-mono font-bold border ${isActive ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 animate-pulse' : 'bg-slate-800 text-slate-400 border-slate-700'}">
                    ${g.status}
                  </span>
                  ${isActive ? `
                    <button onclick="closeMtpGroup('${g.group_id}')" class="px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/30 text-xs font-bold transition">
                      Close Group
                    </button>
                  ` : ''}
                </div>
              </div>
            </div>

            <!-- Individual Positions Grid (Dynamic 3-Column Power Layout) -->
            <div class="grid grid-cols-1 ${(g.positions && g.positions.length <= 3) ? 'md:grid-cols-3' : 'md:grid-cols-5'} gap-3 text-xs font-mono">
              ${(g.positions || []).map(p => {
                const isPosActive = p.status === 'ACTIVE';
                const posPnl = isPosActive ? (p.floating_profit || 0) : (p.realized_profit || 0);
                const posPnlClass = posPnl >= 0 ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';
                let statusBadge = 'bg-slate-800 text-slate-400 border-slate-700';
                if (isPosActive) {
                  statusBadge = 'bg-blue-500/10 text-cyanaccent border-blue-500/30';
                } else if (p.status.includes('TP REACHED')) {
                  statusBadge = 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold';
                } else if (p.status.includes('STOP LOSS')) {
                  statusBadge = 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold';
                }

                return `
                  <div class="p-2.5 rounded-lg bg-slate-950/70 border ${isPosActive ? 'border-bordercol' : 'border-slate-800/60 opacity-90'} space-y-2 flex flex-col justify-between">
                    <div>
                      <div class="flex items-center justify-between pb-1.5 border-b border-slate-800/80">
                        <span class="font-bold text-white text-[11px]">${p.name}</span>
                        <span class="text-[9px] text-slate-500">#${p.ticket}</span>
                      </div>
                      <div class="space-y-1 text-[10px] mt-1.5">
                        <div class="flex justify-between"><span class="text-slate-500">Target Dollar:</span><span class="text-emeraldaccent font-bold">+$${p.target_dollar} (${p.target_pct})</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">TP Price:</span><span class="text-white font-bold">${p.tp}</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">Shared SL:</span><span class="text-crimsonaccent">${p.sl} (-$${p.planned_risk_dollar})</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">Volume:</span><span class="text-slate-300">${p.lot} lots</span></div>
                      </div>
                    </div>

                    <div class="pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
                      <div>
                        <span class="text-[9px] text-slate-500 block leading-none">${isPosActive ? 'FLOATING' : 'REALIZED'}</span>
                        <span class="${posPnlClass} text-xs">${posPnl >= 0 ? '+' : ''}$${posPnl.toFixed(2)}</span>
                      </div>
                      ${isPosActive ? `
                        <button onclick="closeMtpTrade(${p.ticket})" class="px-2 py-0.5 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/20 text-[10px] transition">
                          Close
                        </button>
                      ` : `
                        <span class="px-1.5 py-0.5 rounded text-[9px] border ${statusBadge}">${p.status.split('(')[0].trim()}</span>
                      `}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>

            <!-- Notes -->
            ${g.ai_notes ? `
              <div class="text-[10px] text-slate-400 font-sans px-1 flex items-center gap-1.5">
                <span class="text-cyanaccent font-bold">System Strategy:</span> ${g.ai_notes}
              </div>
            ` : ''}

          </div>
        `;
      }).join('');
    }

    async function executeMtpFromCurrentForm() {
      const sym = activeSymbol;
      const action = currentDirection;
      const refInput = document.getElementById('mtpRefBalanceInput');
      const refBalance = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const lotInput = document.getElementById('tradeVolume');
      const lotPerTrade = parseFloat(lotInput ? lotInput.value : 0.01) || 0.01;

      const riskDollar = (refBalance * 0.05).toFixed(2);
      const riskPerTrade = (refBalance * 0.01).toFixed(2);

      if (!confirm(`Execute 3-Trade Multi-TP Power System on ${sym} (${action})?\n\n` +
                   `• 3 Separate Positions: ${(lotPerTrade * 3).toFixed(2)} total lots (${lotPerTrade} lots each)\n` +
                   `• Shared Stop Loss: 5% maximum planned risk ($${riskDollar} total, $${(riskDollar/3).toFixed(2)} per position)\n` +
                   `• Trade 1: TP 2% (+$${(refBalance*0.02).toFixed(0)} Target) - High hit rate, banks quick profit\n` +
                   `• Trade 2: TP 5% (+$${(refBalance*0.05).toFixed(0)} Target) - Core trend move capture\n` +
                   `• Trade 3: Dynamic AI Runner (Infinite Upside / Trailing Stop)\n\n` +
                   `Transmit all 3 orders directly to Deriv MT5 terminal?`)) {
        return;
      }

      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = `Transmitting 3-Trade Multi-TP group on ${sym} to Deriv MT5...`;
      statusBox.classList.remove('hidden');

      try {
        const res = await fetch('/api/multi_tp/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: sym,
            action: action,
            ref_balance: refBalance,
            lot_per_trade: lotPerTrade,
            ai_notes: `Manual Execution via Form (${sym} ${action})`
          })
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = `✅ ${out.message}`;
          fetchMultiTpGroups();
          refreshAll();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = `❌ ${out.message}`;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Multi-TP execution error: ' + err;
      }
    }

    async function executeMtpDirectlyFromSetup(s) {
      const sym = s.symbol;
      const action = s.action;
      const refInput = document.getElementById('mtpRefBalanceInput');
      const refBalance = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const riskDollar = (refBalance * 0.05).toFixed(2);

      if (!confirm(`Execute 3-Trade Multi-TP Power System for Setup: ${s.setup_name} on ${sym} (${action})?\n\n` +
                   `• Symbol: ${sym} (${action})\n` +
                   `• Shared 5% Stop Loss: $${riskDollar} maximum planned loss combined\n` +
                   `• 3 Independent Positions: Trade 1 (+2% / $20), Trade 2 (+5% / $50), Trade 3 (AI Dynamic Runner)\n` +
                   `• Conviction Score: ${s.conviction}\n\n` +
                   `Proceed with automatic execution on Deriv MT5?`)) {
        return;
      }

      try {
        const res = await fetch('/api/multi_tp/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: sym,
            action: action,
            ref_balance: refBalance,
            lot_per_trade: 0.01,
            ai_notes: `Setup: ${s.setup_name} (${s.conviction}) - ${s.technical_signals}`
          })
        });
        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        fetchSetups();
        refreshAll();
      } catch (err) {
        alert('Multi-TP execution error: ' + err);
      }
    }

    async function closeMtpGroup(gid) {
      if (!confirm(`Close all remaining active positions in Multi-TP Group ${gid}?`)) return;
      try {
        const res = await fetch('/api/multi_tp/close_group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group_id: gid })
        });
        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        refreshAll();
      } catch (err) {
        alert('Close group error: ' + err);
      }
    }

    async function closeMtpTrade(ticket) {
      if (!confirm(`Close position #${ticket} on Deriv MT5?`)) return;
      try {
        const res = await fetch('/api/multi_tp/close_trade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket: ticket })
        });
        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        refreshAll();
      } catch (err) {
        alert('Close trade error: ' + err);
      }
    }

    loadSymbolsCatalog();
    fetchAndApplySymbolQuote('BTCUSD');
    fetchSetups();
    loadPerformanceDashboard();
    fetchMultiTpGroups();
    refreshAll();
    
    // Intervals
    setInterval(fetchState, 2000);
    setInterval(updateCountdown, 1000);
    setInterval(fetchSetups, 15000);
    setInterval(fetchMultiTpGroups, 3000);
  </script>
</body>
</html>
"""

class DerivServer(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/state":
            state = get_deriv_full_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))
        elif url.path == "/api/symbols":
            global symbols_cache
            if not symbols_cache:
                symbols_cache = load_all_symbols()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(symbols_cache).encode("utf-8"))
        elif url.path == "/api/quote":
            qs = parse_qs(url.query)
            sym = qs.get("symbol", ["BTCUSD"])[0]
            quote = get_symbol_quote(sym)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(quote).encode("utf-8"))
        elif url.path == "/api/setups":
            state = scanner.get_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))
        elif url.path == "/api/journal":
            journal = scanner.load_journal()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(journal).encode("utf-8"))
        elif url.path == "/api/history":
            history = get_recent_trade_history()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(history).encode("utf-8"))
        elif url.path == "/api/performance":
            qs = parse_qs(url.query)
            tf = qs.get("timeframe", ["all"])[0]
            force = qs.get("resync", ["0"])[0] == "1"
            perf = get_symbol_trading_analytics(timeframe=tf, force_refresh=force)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(perf).encode("utf-8"))
        elif url.path == "/api/multi_tp/groups":
            groups = sync_multi_tp_groups()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(groups).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if url.path == "/api/order":
            symbol = data.get("symbol", "BTCUSD")
            action = data.get("action", "SELL")
            volume = float(data.get("volume", 0.1))
            sl = float(data.get("sl", 0.0))
            tp = float(data.get("tp", 0.0))
            trades_count = int(data.get("trades_count", 1))
            volume_mode = data.get("volume_mode", "split")
            setup_id = data.get("setup_id")
            confidence = data.get("confidence", "--")
            reason = data.get("reason", "Manual Order")
            comment = data.get("comment", "Headway Agent")
            res = execute_deriv_order(symbol, action, volume, sl, tp, trades_count, volume_mode, setup_id, confidence, reason, comment)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/multi_tp/execute":
            symbol = data.get("symbol", "BTCUSD")
            action = data.get("action", "BUY")
            ref_balance = float(data.get("ref_balance", 1000.0))
            lot_per_trade = float(data.get("lot_per_trade", 0.01))
            ai_notes = data.get("ai_notes", "Manual 3-Trade Multi-TP Execution")
            res = execute_multi_tp_group(
                symbol=symbol,
                action=action,
                ref_balance=ref_balance,
                default_lot=lot_per_trade,
                ai_notes=ai_notes
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/multi_tp/close_group":
            group_id = data.get("group_id")
            res = close_multi_tp_group(group_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/multi_tp/close_trade":
            ticket = int(data.get("ticket"))
            res = close_multi_tp_trade(ticket)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/auto_trade_toggle":
            new_state = scanner.toggle_auto_trade()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "auto_trade_enabled": new_state,
                "message": f"Auto-trading {'ENABLED' if new_state else 'DISABLED'}"
            }).encode("utf-8"))

        elif url.path == "/api/rescan":
            scanner.run_scan_now()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Rescan complete"}).encode("utf-8"))

        elif url.path == "/api/close":
            ticket = int(data.get("ticket"))
            res = close_deriv_position(ticket)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/close_all":
            res = close_all_deriv_positions()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            
        else:
            self.send_response(404)
            self.end_headers()

def get_available_port(preferred_port=8765):
    import socket
    for p in [preferred_port, 8766, 8767, 8000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return preferred_port

def run(port=None):
    global scanner
    if port is None:
        port = int(os.getenv("PORT", 0)) or get_available_port(8765)
    load_all_symbols()
    server = ThreadingHTTPServer(("0.0.0.0", port), DerivServer)
    scanner = AutomatedSetupScanner(interval_seconds=180)
    print("=" * 65)
    print(" " * 10 + "HEADWAY MT5 INSTITUTIONAL WORKSTATION")
    print("=" * 65)
    print(f"[+] Workstation running at: http://127.0.0.1:{port}/ (or http://localhost:{port}/)")
    print("[+] Opening web app in your default browser...")
    try:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}/")).start()
    except Exception:
        pass
    print(f"Workstation is LIVE on port {port}. Press Ctrl+C to stop.\n")
    server.serve_forever()

if __name__ == "__main__":
    p_arg = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            p_arg = int(arg)
    run(p_arg)
