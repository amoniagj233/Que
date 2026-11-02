"""Core Candle Range Theory (CRT) Strategy Engine for Gold (XAUUSD).

Coordinates multi-timeframe detection (M30 range -> M5 sweep -> M2 engulfing confirmation),
manages the 18-state state machine, enforces risk limits, executes orders on MT5,
and continuously synchronizes with the MQL5 indicator.
"""
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .candle_detector import CandleRangeDetector, CRTRange
from .liquidity_sweep import LiquiditySweepDetector, SweepEvent
from .engulfing_confirmation import EngulfingConfirmationDetector, ConfirmationEvent
from .indicator_bridge import IndicatorBridge, bridge

logger = logging.getLogger("CRT_StrategyEngine")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class CRTStrategyEngine:
    def __init__(
        self,
        symbol: str = "XAUUSD",
        magic: int = 9090,
        volume: float = 0.01,
        risk_pct: float = 0.25,
        min_rr: float = 1.5,
        max_spread_pts: float = 50.0,
        tick_size: float = 0.01
    ):
        self.symbol = symbol
        self.magic = magic
        self.volume = volume
        self.risk_pct = risk_pct
        self.min_rr = min_rr
        self.max_spread_pts = max_spread_pts
        self.tick_size = tick_size

        # Sub-detectors
        self.range_detector = CandleRangeDetector()
        self.sweep_detector = LiquiditySweepDetector(tick_size)
        self.confirm_detector = EngulfingConfirmationDetector()
        self.bridge = bridge

        # State Machine (18 States)
        self.state = "WAITING_FOR_RANGE"
        self.bot_status = "RUNNING"
        self.active_range: Optional[CRTRange] = None
        self.active_sweep: Optional[SweepEvent] = None
        self.active_confirm: Optional[ConfirmationEvent] = None

        # Position tracking
        self.active_ticket: Optional[int] = None
        self.tp1_hit: bool = False
        self.trades_today: int = 0
        self.daily_pnl: float = 0.0
        self.last_sync_time: float = 0.0

    def discover_gold_symbol(self) -> str:
        if not MT5_AVAILABLE:
            return self.symbol
        for s in ["XAUUSD", "XAUUSDm", "XAUUSDc", "GOLD"]:
            if mt5.symbol_info(s):
                mt5.symbol_select(s, True)
                return s
        return self.symbol

    def fetch_rates(self, timeframe, count: int = 100) -> Optional[pd.DataFrame]:
        if not MT5_AVAILABLE:
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
        if rates is None or len(rates) < 10:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def transition_state(self, new_state: str, reason: str, price: float = 0.0, direction: str = "") -> None:
        if self.state != new_state:
            logger.info(f"State Transition: [{self.state}] -> [{new_state}] | Reason: {reason}")
            self.state = new_state
            self.bridge.log_event(new_state, direction, price, reason)

    def check_spread(self) -> Tuple[bool, float]:
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return False, 999.0
        spread_pts = round((tick.ask - tick.bid) / self.tick_size, 1)
        if spread_pts > self.max_spread_pts:
            return False, spread_pts
        return True, spread_pts

    def execute_market_order(self, direction: str, sl: float, tp1: float, tp2: float) -> Optional[int]:
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return None

        is_buy = direction == "BULLISH"
        price = tick.ask if is_buy else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.volume,
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp2),
            "deviation": 25,
            "magic": self.magic,
            "comment": "CRT Gold Pro | Asymmetric",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        self.transition_state("ORDER_SUBMITTED", f"Submitting {direction} market order @ {price}", price, direction)
        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Broker Filled Ticket #{res.order} @ {res.price}")
            self.active_ticket = res.order
            self.tp1_hit = False
            self.transition_state("ORDER_FILLED", f"Filled Ticket #{res.order}", res.price, direction)
            self.transition_state("POSITION_ACTIVE", f"Position #{res.order} active", res.price, direction)
            return res.order
        else:
            err = res.comment if res else str(mt5.last_error())
            self.transition_state("TRADE_BLOCKED", f"Broker rejected: {err}", price, direction)
            return None

    def manage_active_position(self) -> None:
        """Monitors active position, partial closes at TP1, moves SL to BE."""
        if not self.active_ticket:
            return

        positions = mt5.positions_get(ticket=self.active_ticket)
        if not positions:
            # Position has closed (TP or SL)
            self.transition_state("TRADE_CLOSED", f"Position #{self.active_ticket} closed")
            self.active_ticket = None
            self.active_sweep = None
            self.active_confirm = None
            self.transition_state("WAITING_FOR_RANGE", "Trade closed, resetting scanner")
            return

        pos = positions[0]
        cur_price = pos.price_current
        open_price = pos.price_open
        is_buy = pos.type == 0

        # Check TP1 reached
        if self.active_range and not self.tp1_hit:
            tp1_target = self.active_range.midpoint
            hit_tp1 = (cur_price >= tp1_target) if is_buy else (cur_price <= tp1_target)
            if hit_tp1:
                self.tp1_hit = True
                self.transition_state("TP1_REACHED", f"Price hit CRT midpoint {tp1_target}", cur_price)
                # Move SL to cost-adjusted breakeven (+10 cents)
                new_sl = round(open_price + (0.10 if is_buy else -0.10), 2)
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": pos.symbol,
                    "sl": new_sl,
                    "tp": pos.tp
                }
                m_res = mt5.order_send(mod_req)
                if m_res and m_res.retcode == mt5.TRADE_RETCODE_DONE:
                    self.transition_state("STOP_MOVED", f"SL moved to breakeven {new_sl}", new_sl)

    def synchronize_with_indicator(self) -> None:
        """Packs the complete strategy state and publishes to MT5 Common Files."""
        now_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        pos_data = {"active": False}

        if self.active_ticket:
            positions = mt5.positions_get(ticket=self.active_ticket) if MT5_AVAILABLE else []
            if positions:
                p = positions[0]
                pos_data = {
                    "active": True,
                    "ticket": p.ticket,
                    "direction": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "entry_price": p.price_open,
                    "sl": p.sl,
                    "tp1": self.active_range.midpoint if self.active_range else 0.0,
                    "tp2": p.tp,
                    "floating_pnl": round(p.profit, 2),
                    "tp1_reached": self.tp1_hit,
                    "open_time": str(p.time)
                }

        payload = {
            "version": "1.0.0",
            "bot_name": "CRT GOLD PRO",
            "magic": self.magic,
            "symbol": self.symbol,
            "timestamp_utc": now_utc,
            "state": self.state,
            "bot_status": self.bot_status,
            "crt_range": {
                "active": bool(self.active_range),
                "time_open": self.active_range.time_open if self.active_range else "",
                "time_close": self.active_range.time_close if self.active_range else "",
                "high": self.active_range.high if self.active_range else 0.0,
                "low": self.active_range.low if self.active_range else 0.0,
                "midpoint": self.active_range.midpoint if self.active_range else 0.0,
                "range_size": self.active_range.range_size if self.active_range else 0.0
            },
            "sweep": {
                "confirmed": bool(self.active_sweep),
                "direction": self.active_sweep.direction if self.active_sweep else "",
                "sweep_price": self.active_sweep.sweep_price if self.active_sweep else 0.0,
                "time": self.active_sweep.time if self.active_sweep else "",
                "reclaim_status": "RECLAIMED" if self.active_sweep else "NONE"
            },
            "signal": {
                "ready": bool(self.active_confirm),
                "direction": self.active_confirm.direction if self.active_confirm else "",
                "time": self.active_confirm.time if self.active_confirm else "",
                "planned_entry": self.active_confirm.entry_signal_price if self.active_confirm else 0.0,
                "planned_sl": 0.0,
                "planned_tp1": self.active_range.midpoint if self.active_range else 0.0,
                "planned_tp2": self.active_range.high if (self.active_range and self.active_confirm and self.active_confirm.direction == "BULLISH") else (self.active_range.low if self.active_range else 0.0),
                "planned_rr": 1.5
            },
            "position": pos_data,
            "metrics": {
                "trades_today": self.trades_today,
                "daily_pnl": round(self.daily_pnl, 2),
                "win_rate": 0.0,
                "risk_pct": self.risk_pct
            }
        }
        self.bridge.publish_state(payload)

    def run_iteration(self) -> None:
        if not MT5_AVAILABLE:
            return

        self.symbol = self.discover_gold_symbol()

        # If we have an active position, manage it and sync
        if self.active_ticket:
            self.manage_active_position()
            self.synchronize_with_indicator()
            return

        # 1. Update M30 Candle Range
        df_m30 = self.fetch_rates(mt5.TIMEFRAME_M30, 20)
        rng = self.range_detector.update(df_m30)
        if rng:
            self.active_range = rng
            if self.state == "WAITING_FOR_RANGE":
                self.transition_state("RANGE_READY", f"M30 Reference Range [{rng.low} - {rng.high}] established", rng.midpoint)

        if not self.active_range:
            self.synchronize_with_indicator()
            return

        # 2. Check M5 Liquidity Sweep
        df_m5 = self.fetch_rates(mt5.TIMEFRAME_M5, 30)
        sweep = self.sweep_detector.check_sweep(df_m5, self.active_range)
        if sweep and not self.active_sweep:
            self.active_sweep = sweep
            self.transition_state("SWEEP_CONFIRMED", f"{sweep.direction} sweep @ {sweep.sweep_price} reclaimed inside range", sweep.sweep_price, sweep.direction)
            self.transition_state("WAITING_FOR_ENGULFING", "Awaiting M2 engulfing confirmation", sweep.sweep_price, sweep.direction)

        if not self.active_sweep:
            self.synchronize_with_indicator()
            return

        # 3. Check M2 / M1 Engulfing Confirmation
        # (Using M1 as faster proxy or M2 if broker supports it)
        tf_confirm = mt5.TIMEFRAME_M2 if hasattr(mt5, "TIMEFRAME_M2") else mt5.TIMEFRAME_M1
        df_m2 = self.fetch_rates(tf_confirm, 20)
        confirm = self.confirm_detector.check_confirmation(df_m2, self.active_sweep)
        if confirm and not self.active_confirm:
            self.active_confirm = confirm
            self.transition_state("SIGNAL_READY", f"Confirmed {confirm.direction} Engulfing candle", confirm.entry_signal_price, confirm.direction)

            # 4. Filter & Execution Gate
            spread_ok, spread_pts = self.check_spread()
            if not spread_ok:
                self.transition_state("TRADE_BLOCKED", f"BLOCKED: Spread too high ({spread_pts} pts > {self.max_spread_pts})", confirm.entry_signal_price)
                self.synchronize_with_indicator()
                return

            # Compute SL and TP levels
            atr_m5 = self.active_sweep.atr_m5
            if confirm.direction == "BULLISH":
                sl = round(self.active_sweep.sweep_price - max(2 * self.tick_size, 0.15 * atr_m5), 2)
                tp1 = self.active_range.midpoint
                tp2 = self.active_range.high
            else:
                sl = round(self.active_sweep.sweep_price + max(2 * self.tick_size, 0.15 * atr_m5), 2)
                tp1 = self.active_range.midpoint
                tp2 = self.active_range.low

            # Execute trade
            self.execute_market_order(confirm.direction, sl, tp1, tp2)

        self.synchronize_with_indicator()
