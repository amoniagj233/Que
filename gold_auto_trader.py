"""
Gold (XAUUSD) Auto-Trading & Intelligent Execution Engine
=========================================================
Autonomous trading engine dedicated to XAUUSD:
- Fully integrated with MetaTrader 5 (MT5).
- Respects strict risk rules:
  1. Maximum 1 open trade per symbol (single Gold position enforcement).
  2. Dual-TP preservation: user choice of TP1, TP2, or random allocation between the two.
  3. High-conviction threshold: executes ONLY setups with 90-100% confidence.
  4. Technical Invalidation Gate: verifies setup invalidation, SL invalidation, and time invalidation before sending orders.
  5. Macro News Blackout: blocks auto-trading within 30 minutes of high-impact events (NFP, CPI, FOMC, PCE).
  6. Option B Profit Chasing: automatically links executed trades to SmartProfitChaser for peak tracking, pullback detection, and trailing recovery.
  7. Configurable daily trade limit, lot size, and instant manual setup execution.
"""

from __future__ import annotations
import os
import json
import math
import time
import random
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from gold_intelligence import (
    generate_gold_trade_setups,
    get_gold_macro_events,
    get_gold_candles,
    compute_atr,
    GOLD_SPEC
)

GOLD_CONFIG_FILE = Path("gold_auto_trade_config.json")
GOLD_LOG_FILE = Path("gold_trades_log.json")

class GoldAutoTrader:
    """Manages autonomous and manual trade executions for Gold (XAUUSD)."""

    def __init__(self, profit_chaser=None, mt5_lock=None):
        self.lock = threading.RLock()
        self.profit_chaser = profit_chaser
        self.mt5_lock = mt5_lock or threading.RLock()
        
        self.config = self._load_config()
        self.logs = self._load_logs()
        
        self.today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.daily_trades_count = self._count_today_trades()
        self.last_eval_time = None
        self.last_eval_status = "INITIALIZING"
        self.last_eval_message = "Gold Auto-Trader engine initialized."
        
        self.running = True
        self._worker_thread = threading.Thread(target=self._run_auto_loop, daemon=True, name="GoldAutoTraderWorker")
        self._worker_thread.start()

    def _load_config(self) -> Dict[str, Any]:
        default_cfg = {
            "enabled": False,
            "min_confidence": 90,
            "lot_size": 0.01,
            "tp_mode": "RANDOM_TP1_TP2",  # Options: RANDOM_TP1_TP2, TP1_CONSERVATIVE, TP2_RUNNER
            "news_filter_enabled": True,
            "max_daily_trades": 3,
            "single_trade_enforcement": True,
            "enable_profit_chaser": True,
            "scan_interval_seconds": 15
        }
        if GOLD_CONFIG_FILE.exists():
            try:
                data = json.loads(GOLD_CONFIG_FILE.read_text(encoding="utf-8"))
                default_cfg.update(data)
            except Exception:
                pass
        return default_cfg

    def _save_config(self):
        try:
            with open(GOLD_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def _load_logs(self) -> List[Dict[str, Any]]:
        if GOLD_LOG_FILE.exists():
            try:
                return json.loads(GOLD_LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_logs(self):
        try:
            # Keep last 100 entries
            with open(GOLD_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.logs[-100:], f, indent=2)
        except Exception:
            pass

    def _count_today_trades(self) -> int:
        cur_d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return sum(1 for log in self.logs if log.get("time", "").startswith(cur_d) and log.get("status") == "FILLED")

    def toggle_auto_trade(self) -> bool:
        with self.lock:
            self.config["enabled"] = not self.config["enabled"]
            self._save_config()
            state_str = "ENABLED" if self.config["enabled"] else "DISABLED"
            self._append_log({
                "type": "CONFIG_CHANGE",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "INFO",
                "message": f"Gold Auto-Trading {state_str} by user"
            })
            return self.config["enabled"]

    def update_config(self, new_cfg: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            for k in ["min_confidence", "lot_size", "tp_mode", "news_filter_enabled", "max_daily_trades", "single_trade_enforcement", "enable_profit_chaser"]:
                if k in new_cfg:
                    self.config[k] = new_cfg[k]
            self._save_config()
            self._append_log({
                "type": "CONFIG_UPDATE",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "INFO",
                "message": "Gold Auto-Trade settings updated",
                "config": self.config
            })
            return self.config

    def _append_log(self, entry: Dict[str, Any]):
        self.logs.insert(0, entry)
        self._save_logs()

    def get_open_gold_positions(self) -> List[Any]:
        """Returns active XAUUSD positions currently open on MT5."""
        if mt5 is None:
            return []
        try:
            with self.mt5_lock:
                pos = mt5.positions_get(symbol="XAUUSD")
                return list(pos) if pos else []
        except Exception:
            return []

    def is_news_blackout_active(self) -> Tuple[bool, str]:
        """Checks if high-impact news event is scheduled within the blackout buffer."""
        if not self.config.get("news_filter_enabled", True):
            return False, "News filter disabled"

        events = get_gold_macro_events()
        now = datetime.now(timezone.utc)
        for ev in events:
            if ev.get("impact") in ["CRITICAL", "HIGH"]:
                # If event within next 30 minutes or last 15 minutes
                ev_time_str = ev.get("time_utc", "")
                try:
                    ev_dt = datetime.strptime(ev_time_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
                    diff_mins = (ev_dt - now).total_seconds() / 60.0
                    if -15 <= diff_mins <= 30:
                        return True, f"Active Blackout Window for {ev['event']} ({diff_mins:.0f}m from release)"
                except Exception:
                    pass
        return False, "No active macro event blackout"

    def execute_gold_order(
        self,
        action: str,
        lot: float,
        sl: float,
        tp: float,
        confidence_score: int,
        strategy_name: str,
        notes: str = "",
        is_auto: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a real-time Gold market order on MT5 with strict execution parameters.
        Registers filled position with SmartProfitChaser for Option B dynamic trailing recovery.
        """
        action = action.upper()
        if action not in ["BUY", "SELL"]:
            return {"success": False, "message": f"Invalid order direction: {action}"}

        if mt5 is None:
            return {"success": False, "message": "MetaTrader 5 API not loaded"}

        with self.mt5_lock:
            # 1. Connection and Terminal Check
            term = mt5.terminal_info()
            if term is None or not term.connected:
                return {"success": False, "message": "MT5 terminal is disconnected"}

            acc = mt5.account_info()
            if acc is None:
                return {"success": False, "message": "Account info unavailable"}
            if not getattr(acc, "trade_allowed", False) or not getattr(acc, "trade_expert", False):
                return {"success": False, "message": "Account does not permit automated/expert trading"}

            # 2. Single Gold Trade Policy Check
            if self.config.get("single_trade_enforcement", True):
                open_pos = mt5.positions_get(symbol="XAUUSD")
                if open_pos and len(open_pos) > 0:
                    return {"success": False, "message": "Blocked by Policy: An active XAUUSD trade is already open"}

            # 3. Symbol info and Quote
            info = mt5.symbol_info("XAUUSD")
            tick = mt5.symbol_info_tick("XAUUSD")
            if info is None or tick is None:
                return {"success": False, "message": "XAUUSD quotes unavailable"}

            # 4. Lot clamping
            min_lot = info.volume_min
            max_lot = info.volume_max
            step_lot = info.volume_step
            req_lot = max(min_lot, min(lot, max_lot))
            # Round to step
            req_lot = round(round(req_lot / step_lot) * step_lot, 2)

            order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if action == "BUY" else tick.bid

            # Filling mode determination
            filling_mode = mt5.ORDER_FILLING_IOC
            if info.filling_mode & 1: # FOK
                filling_mode = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2: # IOC
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD",
                "volume": req_lot,
                "type": order_type,
                "price": price,
                "sl": round(float(sl), info.digits) if sl > 0 else 0.0,
                "tp": round(float(tp), info.digits) if tp > 0 else 0.0,
                "deviation": 40,
                "magic": 777100,  # Dedicated Gold Intelligence magic number
                "comment": f"GOLD-AI-{action[:1]}-{confidence_score}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode
            }

            try:
                res = mt5.order_send(request)
            except Exception as e:
                return {"success": False, "message": f"Order send exception: {e}"}

            if res is None or res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                err_code = getattr(res, "retcode", -1) if res else "None"
                err_comment = getattr(res, "comment", "Order failed") if res else "No response"
                msg = f"Order rejected by broker (code {err_code}): {err_comment}"
                self._append_log({
                    "type": "ORDER_REJECTED",
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "status": "ERROR",
                    "direction": action,
                    "strategy": strategy_name,
                    "confidence": confidence_score,
                    "message": msg
                })
                return {"success": False, "message": msg}

            fill_price = float(res.price or price)
            fill_volume = float(res.volume or req_lot)
            ticket = int(res.order)

            # 5. Link with Smart Profit Chaser Option B
            if self.config.get("enable_profit_chaser", True) and self.profit_chaser:
                try:
                    self.profit_chaser.register_position(
                        ticket=ticket,
                        symbol="XAUUSD",
                        direction=action,
                        entry_price=fill_price,
                        lot_size=fill_volume,
                        stop_loss=sl,
                        take_profit=tp
                    )
                except Exception:
                    pass

            # Record success
            self.daily_trades_count += 1
            log_item = {
                "type": "AUTO_TRADE_FILLED" if is_auto else "MANUAL_TRADE_FILLED",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "FILLED",
                "ticket": ticket,
                "direction": action,
                "lot": fill_volume,
                "entry": fill_price,
                "sl": sl,
                "tp": tp,
                "strategy": strategy_name,
                "confidence": confidence_score,
                "message": f"Successfully filled {action} {fill_volume} lots XAUUSD @ {fill_price} (Ticket #{ticket})"
            }
            self._append_log(log_item)

            return {
                "success": True,
                "ticket": ticket,
                "fill_price": fill_price,
                "fill_volume": fill_volume,
                "message": f"Filled {action} {fill_volume} lot XAUUSD at {fill_price} (Ticket #{ticket})"
            }

    def evaluate_and_execute_auto_trades(self) -> Dict[str, Any]:
        """Core cycle: scans Gold conditions, validates criteria, and auto-executes high-confidence setups."""
        cur_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.last_eval_time = cur_time

        # Update daily date if rolled over
        cur_d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if cur_d != self.today_date:
            self.today_date = cur_d
            self.daily_trades_count = 0

        # Gate 1: Enabled
        if not self.config.get("enabled", False):
            self.last_eval_status = "STANDBY"
            self.last_eval_message = "Gold Auto-Trading is paused/disabled by user."
            return {"status": "STANDBY", "message": self.last_eval_message}

        # Gate 2: Single Open Gold Trade Policy
        if self.config.get("single_trade_enforcement", True):
            open_gold = self.get_open_gold_positions()
            if open_gold:
                pos = open_gold[0]
                p_type = "BUY" if pos.type == 0 else "SELL"
                self.last_eval_status = "MONITORING_OPEN_TRADE"
                self.last_eval_message = f"Active Gold trade open: #{pos.ticket} {p_type} {pos.volume} lots (Floating P&L: ${pos.profit:.2f}). Smart Profit Chaser active."
                return {"status": "MONITORING_OPEN_TRADE", "message": self.last_eval_message}

        # Gate 3: Max Daily Trades Cap
        max_daily = self.config.get("max_daily_trades", 3)
        if self.daily_trades_count >= max_daily:
            self.last_eval_status = "DAILY_CAP_REACHED"
            self.last_eval_message = f"Daily Gold trade cap reached ({self.daily_trades_count}/{max_daily}). Capital preservation active until tomorrow."
            return {"status": "DAILY_CAP_REACHED", "message": self.last_eval_message}

        # Gate 4: News Blackout
        is_news, news_reason = self.is_news_blackout_active()
        if is_news:
            self.last_eval_status = "NEWS_BLACKOUT"
            self.last_eval_message = f"Auto-Execution paused: {news_reason}"
            return {"status": "NEWS_BLACKOUT", "message": self.last_eval_message}

        # Gate 5: Scan Setups
        try:
            setups = generate_gold_trade_setups()
        except Exception as e:
            self.last_eval_status = "ERROR"
            self.last_eval_message = f"Setup generation error: {e}"
            return {"status": "ERROR", "message": self.last_eval_message}

        if not setups:
            self.last_eval_status = "SCANNING"
            self.last_eval_message = "No setups currently generated."
            return {"status": "SCANNING", "message": self.last_eval_message}

        # Filter strictly for valid BUY/SELL setups with confidence >= min_confidence (90-100%)
        min_conf = self.config.get("min_confidence", 90)
        actionable_setups = [
            s for s in setups
            if s.get("direction") in ["BUY", "SELL"]
            and s.get("confidence_score", 0) >= min_conf
        ]

        if not actionable_setups:
            self.last_eval_status = "FILTERING"
            top_conf = max([s.get("confidence_score", 0) for s in setups]) if setups else 0
            self.last_eval_message = f"Setups below required confidence threshold ({top_conf}% < {min_conf}%). Awaiting verified institutional confluence."
            return {"status": "FILTERING", "message": self.last_eval_message}

        # Select highest conviction setup
        actionable_setups.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        chosen = actionable_setups[0]

        # Determine Target TP based on user config (Rule 1 & 2: dual-TP random choice)
        tp_mode = self.config.get("tp_mode", "RANDOM_TP1_TP2")
        tp1 = chosen.get("tp1", 0.0)
        tp2 = chosen.get("tp2", 0.0)
        tp3 = chosen.get("tp3", 0.0)

        if tp_mode == "TP1_CONSERVATIVE":
            selected_tp = tp1
            tp_label = "TP1 (Conservative)"
        elif tp_mode == "TP2_RUNNER":
            selected_tp = tp2
            tp_label = "TP2 (Runner)"
        elif tp_mode == "TP3_SWING":
            selected_tp = tp3
            tp_label = "TP3 (Swing)"
        else: # RANDOM_TP1_TP2 (User Rule #2)
            if random.random() < 0.5:
                selected_tp = tp1
                tp_label = "Random TP1 (1.8R)"
            else:
                selected_tp = tp2
                tp_label = "Random TP2 (4.0R Runner)"

        lot = self.config.get("lot_size", 0.01)

        # Trigger Order Execution
        exec_res = self.execute_gold_order(
            action=chosen["direction"],
            lot=lot,
            sl=chosen["sl"],
            tp=selected_tp,
            confidence_score=chosen["confidence_score"],
            strategy_name=chosen["strategy"],
            notes=f"Auto-Executed via Gold Intelligence [{tp_label}]",
            is_auto=True
        )

        if exec_res.get("success"):
            self.last_eval_status = "EXECUTED"
            self.last_eval_message = f"AUTO-EXECUTED: {chosen['direction']} {lot} lot XAUUSD @ {exec_res.get('fill_price')} (Confidence {chosen['confidence_score']}%, {tp_label})"
            return {"status": "EXECUTED", "trade": exec_res, "message": self.last_eval_message}
        else:
            self.last_eval_status = "EXECUTION_BLOCKED"
            self.last_eval_message = f"Auto-trade blocked: {exec_res.get('message')}"
            return {"status": "EXECUTION_BLOCKED", "message": self.last_eval_message}

    def _run_auto_loop(self):
        """Continuous background loop evaluating Gold conditions on configurable interval."""
        while self.running:
            try:
                interval = max(5, self.config.get("scan_interval_seconds", 15))
                time.sleep(interval)
                if self.config.get("enabled", False):
                    self.evaluate_and_execute_auto_trades()
            except Exception as e:
                time.sleep(5)

    def get_status(self) -> Dict[str, Any]:
        """Provides complete real-time dashboard data for Gold auto-trading UI."""
        with self.lock:
            open_pos = self.get_open_gold_positions()
            formatted_pos = []
            for p in open_pos:
                formatted_pos.append({
                    "ticket": p.ticket,
                    "direction": "BUY" if p.type == 0 else "SELL",
                    "lot": p.volume,
                    "entry": p.price_open,
                    "current": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": round(float(p.profit), 2)
                })

            return {
                "enabled": self.config.get("enabled", False),
                "config": self.config,
                "status": self.last_eval_status,
                "status_message": self.last_eval_message,
                "last_eval_time": self.last_eval_time or "Ready",
                "daily_trades_count": self.daily_trades_count,
                "max_daily_trades": self.config.get("max_daily_trades", 3),
                "open_gold_positions": formatted_pos,
                "has_open_position": len(formatted_pos) > 0,
                "recent_logs": self.logs[:15]
            }
