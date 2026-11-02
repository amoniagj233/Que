"""
Smart Dynamic Profit Chasing, Pullback and Recovery System
==========================================================
Production-grade engine for MetaTrader 5 (MT5) and Python.

Key Pillars:
1. Highest Profit Tracking (Continuous Peak Monitor).
2. Dynamic Pullback Detection (Fixed Currency, Percent of Peak, ATR Volatility).
3. Option B Profit Recovery Logic:
   - Trade experiences pullback -> enters Pullback Mode.
   - Trade recovers to previous peak -> DO NOT CLOSE. Mark recovery completed, deactivate pullback mode.
   - Trade breaks above previous peak -> record new peak immediately.
   - Trade allowed to grow indefinitely without artificial hard take-profit caps.
4. Independent Smart Trailing Profit Protection:
   - Activates after configurable activation threshold.
   - Ratchets floor up with new peaks; never moves backward.
   - Exits position when protected floor is breached.
5. Multi-Mode Profit Valuation:
   - Account Currency ($), Account Balance %, Entry Equity %, Margin Return %, Points/Pips, ATR Multiples.
6. Multi-Tier Profit Milestones & Adaptive Volatility Scaling.
7. Anti-Premature Exit Whipsaw Filter (Hysteresis & Confirmation Distance).
8. State Persistence across restarts (Zero state loss).
9. Concurrency-safe thread execution & Hedging/Netting MT5 order execution.
"""

from __future__ import annotations

from execution_gateway import guarded_order_send
import os
import json
import time
import math
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict

# Optional MT5 import
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

logger = logging.getLogger("ProfitChaser")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

# ==============================================================================
# ENUMS & DATA STRUCTURES
# ==============================================================================

class ProfitMode(str, Enum):
    ACCOUNT_CURRENCY = "ACCOUNT_CURRENCY"       # Net profit in account currency ($)
    ACCOUNT_BALANCE_PCT = "ACCOUNT_BALANCE_PCT" # Profit as % of current balance
    ENTRY_EQUITY_PCT = "ENTRY_EQUITY_PCT"       # Profit as % of equity at entry
    MARGIN_RETURN_PCT = "MARGIN_RETURN_PCT"     # Return on position margin (%)
    POINTS_PIPS = "POINTS_PIPS"                 # Price movement in points
    ATR_MULTIPLE = "ATR_MULTIPLE"               # Profit expressed in ATR (R-multiple)

class PullbackMethod(str, Enum):
    FIXED_CURRENCY = "FIXED_CURRENCY"           # Fixed monetary drop from peak ($)
    PERCENT_PEAK = "PERCENT_PEAK"               # Drop as percentage of highest peak (%)
    ATR_VOLATILITY = "ATR_VOLATILITY"           # Volatility-adjusted drop (ATR multiplier)

class TrailingMethod(str, Enum):
    PERCENT_GIVEBACK = "PERCENT_GIVEBACK"       # Max allowed percentage giveback from peak (%)
    FIXED_DISTANCE = "FIXED_DISTANCE"           # Fixed monetary buffer below peak ($)
    ATR_ADAPTIVE = "ATR_ADAPTIVE"               # Dynamic buffer based on live ATR

class PositionState(str, Enum):
    INITIALIZING = "INITIALIZING"
    TRACKING_NEW_HIGH = "TRACKING_NEW_HIGH"
    PULLBACK_DETECTED = "PULLBACK_DETECTED"
    WAITING_FOR_RECOVERY = "WAITING_FOR_RECOVERY"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    NEW_PEAK_RECORDED = "NEW_PEAK_RECORDED"
    PROFIT_PROTECTION_TRIGGERED = "PROFIT_PROTECTION_TRIGGERED"
    MAX_TARGET_REACHED = "MAX_TARGET_REACHED"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    TREND_REVERSAL_EXIT = "TREND_REVERSAL_EXIT"
    TRADE_CLOSED = "TRADE_CLOSED"

@dataclass
class ProfitMilestone:
    """Configurable profit milestone to tighten trailing protection as trade grows."""
    threshold: float          # Profit level where this milestone activates
    protection_pct: float     # Percentage of peak locked in at this tier (e.g. 50% locked)
    name: str = "Milestone"

@dataclass
class ProfitChaserConfig:
    # Master switch
    enabled: bool = True
    
    # Valuation & Calculation mode
    profit_mode: ProfitMode = ProfitMode.ACCOUNT_CURRENCY
    
    # Highest Profit Tracking & Activation
    activation_threshold: float = 10.0      # Minimum profit required to arm trailing protection
    
    # Pullback Detection
    pullback_method: PullbackMethod = PullbackMethod.PERCENT_PEAK
    pullback_value: float = 25.0            # 25% drop from peak, or $10 fixed, or 1.5x ATR
    adaptive_pullback: bool = True          # Scale pullback threshold with ATR/volatility
    
    # Option B: Profit Recovery Logic
    recovery_hysteresis_pct: float = 2.0    # Within 2% of previous peak confirms recovery
    
    # Smart Trailing Profit Protection
    trailing_enabled: bool = True
    trailing_method: TrailingMethod = TrailingMethod.PERCENT_GIVEBACK
    max_giveback_pct: float = 35.0          # Max allowable retracement from peak before closing
    trailing_fixed_distance: float = 5.0    # Monetary buffer if FIXED_DISTANCE used
    trailing_atr_multiplier: float = 2.0    # ATR buffer if ATR_ADAPTIVE used
    min_guaranteed_profit: float = 4.0      # Hard floor (break-even guarantee once activated)
    
    # Independent Exit Mechanisms
    max_profit_target_enabled: bool = False
    max_profit_target_value: float = 500.0   # Optional hard maximum take-profit
    
    trend_reversal_exit_enabled: bool = False
    
    # Anti-Premature Exit Filters
    min_bars_confirmation: int = 1         # Require 1 bar/tick confirmation to prevent spike exit
    
    # Milestones (Tiered lock-in)
    use_milestones: bool = True
    milestones: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"threshold": 15.0, "protection_pct": 50.0, "name": "Tier 1: 50% Lock"},
        {"threshold": 30.0, "protection_pct": 65.0, "name": "Tier 2: 65% Lock"},
        {"threshold": 60.0, "protection_pct": 80.0, "name": "Tier 3: 80% Lock"}
    ])

@dataclass
class PositionProfitState:
    ticket: int
    symbol: str
    direction: str                          # "BUY" or "SELL"
    volume: float
    entry_price: float
    entry_time: str
    
    # Live Profit Metrics
    current_profit: float = 0.0             # Net floating profit in chosen valuation unit
    current_profit_currency: float = 0.0    # Always stored in account currency for reference
    highest_profit: float = 0.0             # Peak recorded floating profit
    previous_peak: float = 0.0              # Prior peak before the most recent pullback
    
    # Pullback & Recovery State
    current_pullback: float = 0.0           # Absolute distance pulled back from peak
    current_pullback_pct: float = 0.0       # Retracement % from peak
    pullback_threshold: float = 0.0         # Calculated threshold to trigger pullback mode
    recovery_target: float = 0.0            # Price/profit level needed to complete recovery
    pullback_active: bool = False           # Currently in pullback mode?
    recovery_count: int = 0                 # Number of successful Option-B recoveries completed
    
    # Trailing Protection State
    protected_floor: float = 0.0            # Floor profit level (breach triggers exit)
    trailing_armed: bool = False            # Has profit reached activation threshold?
    current_milestone_tier: int = 0         # Active milestone tier
    
    # State Machine & Status
    state: PositionState = PositionState.INITIALIZING
    status_label: str = "INITIALIZING"
    last_event_note: str = "Position initialized"
    last_update_time: str = ""
    
    # Context data (ATR, margin, equity at entry)
    atr_at_entry: float = 0.0
    current_atr: float = 0.0
    entry_equity: float = 0.0
    position_margin: float = 0.0
    point_size: float = 0.01

# ==============================================================================
# CORE ENGINE: SMART PROFIT CHASER & RECOVERY
# ==============================================================================

class SmartProfitChaser:
    """
    Intelligent Dynamic Profit Chasing, Pullback and Recovery System.
    Thread-safe, event-driven, compatible with MT5 and live workstations.
    """
    def __init__(self, config: Optional[ProfitChaserConfig] = None, state_file: str = "profit_chaser_state.json"):
        self.lock = threading.RLock()
        self.config = config or ProfitChaserConfig()
        self.state_file = Path(state_file)
        
        # In-memory tracking per position ticket: {ticket: PositionProfitState}
        self.positions: Dict[int, PositionProfitState] = {}
        
        # Historical protection / exit events log (circular buffer)
        self.event_log: List[Dict[str, Any]] = []
        
        # Optional external execution callback: func(ticket, symbol, reason) -> bool
        self.close_handler: Optional[Callable[[int, str, str], bool]] = None
        
        # Load state from disk if exists
        self.load_state()

    # --------------------------------------------------------------------------
    # STATE PERSISTENCE
    # --------------------------------------------------------------------------
    def save_state(self):
        """Saves all active position-tracking data to disk to survive reboots."""
        with self.lock:
            try:
                data = {
                    "config": asdict(self.config),
                    "positions": {str(k): asdict(v) for k, v in self.positions.items()},
                    "event_log": self.event_log[-50:],
                    "saved_at": datetime.now(timezone.utc).isoformat()
                }
                self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error(f"Error persisting state to {self.state_file}: {e}")

    def load_state(self):
        """Restores position tracking state from disk."""
        with self.lock:
            if not self.state_file.exists():
                return
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                pos_data = data.get("positions", {})
                for k, v in pos_data.items():
                    ticket = int(k)
                    # Convert string enum back to PositionState
                    if "state" in v and isinstance(v["state"], str):
                        try:
                            v["state"] = PositionState(v["state"])
                        except ValueError:
                            v["state"] = PositionState.INITIALIZING
                    self.positions[ticket] = PositionProfitState(**v)
                self.event_log = data.get("event_log", [])
                logger.info(f"Loaded {len(self.positions)} tracked positions from state storage.")
            except Exception as e:
                logger.error(f"Error reading state storage {self.state_file}: {e}")

    # --------------------------------------------------------------------------
    # POSITION REGISTRATION & INITIALIZATION
    # --------------------------------------------------------------------------
    def register_position(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        entry_equity: float = 0.0,
        position_margin: float = 0.0,
        current_atr: float = 0.0,
        point_size: float = 0.01
    ) -> PositionProfitState:
        """Rule 1: Initializes a new trade's profit-tracking state upon open."""
        with self.lock:
            if ticket in self.positions:
                return self.positions[ticket]

            state = PositionProfitState(
                ticket=ticket,
                symbol=symbol,
                direction=direction.upper(),
                volume=volume,
                entry_price=entry_price,
                entry_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                current_profit=0.0,
                current_profit_currency=0.0,
                highest_profit=0.0,
                previous_peak=0.0,
                current_pullback=0.0,
                current_pullback_pct=0.0,
                pullback_threshold=0.0,
                recovery_target=0.0,
                pullback_active=False,
                recovery_count=0,
                protected_floor=0.0,
                trailing_armed=False,
                current_milestone_tier=0,
                state=PositionState.TRACKING_NEW_HIGH,
                status_label="TRACKING NEW HIGH",
                last_event_note="Position registered for smart dynamic profit chasing",
                last_update_time=datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                atr_at_entry=current_atr,
                current_atr=current_atr,
                entry_equity=entry_equity,
                position_margin=position_margin,
                point_size=point_size
            )
            self.positions[ticket] = state
            self._log_event(ticket, symbol, "POSITION_REGISTERED", f"Initialized tracking for {symbol} {direction} (Ticket #{ticket})")
            self.save_state()
            return state

    # --------------------------------------------------------------------------
    # PROFIT VALUATION CONVERTER (SECTION 7)
    # --------------------------------------------------------------------------
    def calculate_valuation(self, pos: PositionProfitState, raw_currency_profit: float, current_price: float) -> float:
        """Converts raw MT5 net profit into the user's chosen valuation unit."""
        mode = self.config.profit_mode
        if mode == ProfitMode.ACCOUNT_CURRENCY:
            return raw_currency_profit
            
        elif mode == ProfitMode.ACCOUNT_BALANCE_PCT:
            base = pos.entry_equity if pos.entry_equity > 0 else 1000.0
            return (raw_currency_profit / base) * 100.0
            
        elif mode == ProfitMode.ENTRY_EQUITY_PCT:
            base = pos.entry_equity if pos.entry_equity > 0 else 1000.0
            return (raw_currency_profit / base) * 100.0
            
        elif mode == ProfitMode.MARGIN_RETURN_PCT:
            margin = pos.position_margin if pos.position_margin > 0 else 100.0
            return (raw_currency_profit / margin) * 100.0
            
        elif mode == ProfitMode.POINTS_PIPS:
            pt = pos.point_size if pos.point_size > 0 else 0.01
            diff = (current_price - pos.entry_price) if pos.direction == "BUY" else (pos.entry_price - current_price)
            return diff / pt
            
        elif mode == ProfitMode.ATR_MULTIPLE:
            atr = pos.current_atr if pos.current_atr > 0 else pos.atr_at_entry
            if atr <= 0:
                return raw_currency_profit
            diff = abs(current_price - pos.entry_price)
            return (diff / atr) * (1.0 if raw_currency_profit >= 0 else -1.0)
            
        return raw_currency_profit

    # --------------------------------------------------------------------------
    # DYNAMIC PULLBACK THRESHOLD CALCULATION (SECTION 3 & 9)
    # --------------------------------------------------------------------------
    def compute_pullback_threshold(self, pos: PositionProfitState) -> float:
        """
        Calculates the pullback distance required to trigger Pullback Mode.
        Supports FIXED_CURRENCY, PERCENT_PEAK, and ATR_VOLATILITY.
        """
        peak = pos.highest_profit
        if peak <= 0:
            return 0.0

        method = self.config.pullback_method
        base_thresh = 0.0
        
        if method == PullbackMethod.FIXED_CURRENCY:
            base_thresh = float(self.config.pullback_value)
            
        elif method == PullbackMethod.PERCENT_PEAK:
            pct = float(self.config.pullback_value) / 100.0
            base_thresh = peak * pct
            
        elif method == PullbackMethod.ATR_VOLATILITY:
            atr = pos.current_atr if pos.current_atr > 0 else pos.atr_at_entry
            multiplier = float(self.config.pullback_value) # e.g. 1.5x ATR
            if pos.entry_price > 0 and pos.current_profit_currency != 0:
                price_move = atr * multiplier
                diff = abs(pos.current_profit_currency) / max(1e-6, abs(pos.entry_price * 0.01))
                base_thresh = max(1.0, price_move * diff)
            else:
                base_thresh = max(1.0, peak * 0.25)

        # Adaptive Pullback scaling (Section 9):
        if self.config.adaptive_pullback and peak > (self.config.activation_threshold * 2):
            scale_factor = 1.0 + min(0.5, (peak / (self.config.activation_threshold * 5)))
            base_thresh *= scale_factor

        return round(base_thresh, 2)

    # --------------------------------------------------------------------------
    # SMART TRAILING PROFIT PROTECTION CALCULATION (SECTION 5 & 9)
    # --------------------------------------------------------------------------
    def compute_protected_floor(self, pos: PositionProfitState) -> float:
        """
        Computes the ratchet floor level.
        Activates once peak >= activation_threshold. Never moves backward!
        """
        if not self.config.trailing_enabled:
            return 0.0
            
        peak = pos.highest_profit
        act_thresh = float(self.config.activation_threshold)
        
        if peak < act_thresh and not pos.trailing_armed:
            return 0.0

        pos.trailing_armed = True
        min_guard = float(self.config.min_guaranteed_profit)
        method = self.config.trailing_method
        
        raw_floor = 0.0
        if method == TrailingMethod.PERCENT_GIVEBACK:
            giveback_pct = float(self.config.max_giveback_pct) / 100.0
            raw_floor = peak * (1.0 - giveback_pct)
            
        elif method == TrailingMethod.FIXED_DISTANCE:
            dist = float(self.config.trailing_fixed_distance)
            raw_floor = peak - dist
            
        elif method == TrailingMethod.ATR_ADAPTIVE:
            mult = float(self.config.trailing_atr_multiplier)
            atr_buffer = (pos.current_atr if pos.current_atr > 0 else 1.0) * mult
            raw_floor = peak - atr_buffer

        # Check Milestone Tiers (Section 9)
        if self.config.use_milestones and self.config.milestones:
            for idx, ms in enumerate(self.config.milestones, 1):
                if peak >= float(ms["threshold"]):
                    ms_floor = peak * (float(ms["protection_pct"]) / 100.0)
                    if ms_floor > raw_floor:
                        raw_floor = ms_floor
                        pos.current_milestone_tier = idx

        # Guarantee minimum floor once armed
        floor = max(min_guard, raw_floor)
        
        # Rule 5.3: Floor MUST NEVER move backward!
        floor = max(pos.protected_floor, floor)
        return round(floor, 2)

    # --------------------------------------------------------------------------
    # STATE MACHINE TICK PROCESSOR (SECTIONS 2, 3, 4, 5, 6)
    # --------------------------------------------------------------------------
    def update_position(
        self,
        ticket: int,
        current_profit_currency: float,
        current_price: float,
        current_atr: Optional[float] = None,
        trend_reversal_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Primary event handler. Called on every price tick / bar update for each open position.
        Evaluates peak tracking, pullback detection, Option-B recovery, and exit triggers.
        """
        with self.lock:
            pos = self.positions.get(ticket)
            if not pos:
                return {"action": "NONE", "error": f"Ticket #{ticket} not registered"}

            if current_atr and current_atr > 0:
                pos.current_atr = current_atr

            # Convert profit to chosen valuation unit
            pos.current_profit_currency = round(current_profit_currency, 2)
            profit = self.calculate_valuation(pos, current_profit_currency, current_price)
            pos.current_profit = round(profit, 2)
            pos.last_update_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

            # ------------------------------------------------------------------
            # 1. INDEPENDENT HARD EXIT CHECKS (Section 6)
            # ------------------------------------------------------------------
            # 1A. Optional Maximum Profit Target
            if self.config.max_profit_target_enabled and profit >= self.config.max_profit_target_value:
                note = f"Max profit target reached ({profit:.2f} >= {self.config.max_profit_target_value:.2f})"
                pos.last_event_note = note
                self._log_event(ticket, pos.symbol, "MAX_TARGET_EXIT", note)
                self.save_state()
                return self._trigger_close(ticket, pos, "MAX_PROFIT_TARGET")

            # 1B. Optional Trend Reversal Exit
            if self.config.trend_reversal_exit_enabled and trend_reversal_confirmed and profit > 0:
                note = f"Technical trend reversal confirmed with positive profit +{profit:.2f}"
                pos.last_event_note = note
                self._log_event(ticket, pos.symbol, "TREND_REVERSAL_EXIT", note)
                self.save_state()
                return self._trigger_close(ticket, pos, "TREND_REVERSAL")

            # ------------------------------------------------------------------
            # 2. HIGHEST PROFIT TRACKING (Section 2)
            # ------------------------------------------------------------------
            is_new_high = profit > pos.highest_profit

            if is_new_high:
                prior_high = pos.highest_profit
                pos.highest_profit = profit
                pos.pullback_threshold = self.compute_pullback_threshold(pos)
                pos.recovery_target = pos.highest_profit
                pos.protected_floor = self.compute_protected_floor(pos)

                # Breaking above previous peak after pullback or completed recovery
                if pos.pullback_active or pos.recovery_count > 0 or pos.previous_peak > 0:
                    pos.pullback_active = False
                    pos.state = PositionState.NEW_PEAK_RECORDED
                    pos.status_label = "NEW PEAK RECORDED"
                    note = f"New all-time profit peak reached: +{profit:.2f} (surpassed previous {prior_high:.2f})"
                    pos.last_event_note = note
                    self._log_event(ticket, pos.symbol, "NEW_PEAK_RECORDED", note)
                else:
                    pos.state = PositionState.TRACKING_NEW_HIGH
                    pos.status_label = "TRACKING NEW HIGH"
                    pos.last_event_note = f"Highest profit updated to +{profit:.2f}"

                self.save_state()

            # ------------------------------------------------------------------
            # 3. PULLBACK & RECOVERY EVALUATION (Section 3 & 4)
            # ------------------------------------------------------------------
            pullback_dist = pos.highest_profit - profit
            pos.current_pullback = round(max(0.0, pullback_dist), 2)
            pos.current_pullback_pct = round((pullback_dist / pos.highest_profit * 100.0) if pos.highest_profit > 0 else 0.0, 1)
            pos.pullback_threshold = self.compute_pullback_threshold(pos)

            # Update protected floor (ratchet only moves up)
            pos.protected_floor = self.compute_protected_floor(pos)

            # Option B Logic: Did we pullback?
            if not pos.pullback_active:
                if pos.highest_profit >= float(self.config.activation_threshold) and pullback_dist >= pos.pullback_threshold:
                    # ACTIVATE PULLBACK MODE (Monitoring event only - DO NOT CLOSE!)
                    pos.pullback_active = True
                    pos.previous_peak = pos.highest_profit
                    pos.recovery_target = pos.highest_profit
                    pos.state = PositionState.PULLBACK_DETECTED
                    pos.status_label = "PULLBACK DETECTED"
                    note = f"Profit dropped {pullback_dist:.2f} ({pos.current_pullback_pct:.1f}%) from peak {pos.highest_profit:.2f}. Threshold={pos.pullback_threshold:.2f}. Pullback Mode ARMED."
                    pos.last_event_note = note
                    self._log_event(ticket, pos.symbol, "PULLBACK_DETECTED", note)
                    self.save_state()
            else:
                # We ARE in Pullback Mode -> Monitor for OPTION B RECOVERY
                hysteresis = pos.previous_peak * (float(self.config.recovery_hysteresis_pct) / 100.0)
                recovery_level = pos.previous_peak - hysteresis

                if profit >= recovery_level and not is_new_high:
                    # RECOVERY COMPLETED (Option B: DO NOT CLOSE! Keep trade running!)
                    pos.pullback_active = False
                    pos.recovery_count += 1
                    pos.state = PositionState.RECOVERY_COMPLETED
                    pos.status_label = "RECOVERY COMPLETED"
                    note = f"🌟 Profit recovered to +{profit:.2f} (Peak was {pos.previous_peak:.2f}). Option B: Position kept open to grow!"
                    pos.last_event_note = note
                    self._log_event(ticket, pos.symbol, "RECOVERY_COMPLETED", note)
                    self.save_state()
                elif pos.state != PositionState.WAITING_FOR_RECOVERY:
                    pos.state = PositionState.WAITING_FOR_RECOVERY
                    pos.status_label = "WAITING FOR RECOVERY"

            # ------------------------------------------------------------------
            # 4. SMART TRAILING PROFIT PROTECTION EXIT (Section 5 & 6B)
            # ------------------------------------------------------------------
            if pos.trailing_armed and pos.protected_floor > 0:
                if profit <= pos.protected_floor:
                    # Floor breached -> Lock in accumulated profit!
                    note = f"🛡️ Protected floor breached (+{profit:.2f} <= floor +{pos.protected_floor:.2f}). Peak was +{pos.highest_profit:.2f}. Locking in gains!"
                    pos.last_event_note = note
                    self._log_event(ticket, pos.symbol, "PROTECTION_TRIGGERED", note)
                    self.save_state()
                    return self._trigger_close(ticket, pos, "PROFIT_PROTECTION_TRIGGERED")

            return {
                "action": "HOLD",
                "state": pos.state.value,
                "status_label": pos.status_label,
                "current_profit": pos.current_profit,
                "highest_profit": pos.highest_profit,
                "protected_floor": pos.protected_floor,
                "pullback_active": pos.pullback_active,
                "recovery_count": pos.recovery_count
            }

    # --------------------------------------------------------------------------
    # POSITION CLOSURE DISPATCHER
    # --------------------------------------------------------------------------
    def _trigger_close(self, ticket: int, pos: PositionProfitState, reason: str) -> Dict[str, Any]:
        """Dispatches trade close request via handler or MT5 integration."""
        logger.info(f"Triggering close on ticket #{ticket} ({pos.symbol}) - Reason: {reason}")
        success = False
        
        if self.close_handler:
            try:
                success = self.close_handler(ticket, pos.symbol, reason)
            except Exception as e:
                logger.error(f"Custom close_handler failed for #{ticket}: {e}")
                success = False
        elif mt5 is not None:
            success = self._close_mt5_position(ticket, pos.symbol, reason)

        # Transition state to specific exit reason
        if reason == "PROFIT_PROTECTION_TRIGGERED":
            pos.state = PositionState.PROFIT_PROTECTION_TRIGGERED
            pos.status_label = "PROFIT PROTECTION TRIGGERED"
        elif reason == "MAX_PROFIT_TARGET":
            pos.state = PositionState.MAX_TARGET_REACHED
            pos.status_label = "MAX TARGET REACHED"
        elif reason == "TREND_REVERSAL":
            pos.state = PositionState.TREND_REVERSAL_EXIT
            pos.status_label = "TREND REVERSAL EXIT"
        else:
            pos.state = PositionState.TRADE_CLOSED
            pos.status_label = "TRADE CLOSED"

        if success:
            self._log_event(ticket, pos.symbol, "TRADE_CLOSED", f"Position #{ticket} closed successfully: {reason}")
            self.save_state()

        return {
            "action": "CLOSE",
            "ticket": ticket,
            "symbol": pos.symbol,
            "reason": reason,
            "success": success,
            "banked_profit": pos.current_profit_currency,
            "peak_profit": pos.highest_profit
        }

    def _close_mt5_position(self, ticket: int, symbol: str, reason: str) -> bool:
        """Executes market close on MT5 with retry, slippage protection, and filling modes."""
        if mt5 is None or not mt5.initialize():
            logger.error("MT5 terminal not available to execute position close.")
            return False

        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            logger.warning(f"Position #{ticket} already closed in MT5.")
            return True

        p = pos[0]
        close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not info or not tick:
            logger.error(f"Could not get tick for {symbol}")
            return False

        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        
        filling = mt5.ORDER_FILLING_FOK
        if info.filling_mode & 1:
            filling = mt5.ORDER_FILLING_FOK
        elif info.filling_mode & 2:
            filling = mt5.ORDER_FILLING_IOC
        else:
            filling = mt5.ORDER_FILLING_RETURN

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": p.volume,
            "type": close_type,
            "price": price,
            "deviation": 25,
            "magic": 777001,
            "comment": f"SPC Close: {reason[:16]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling
        }

        for attempt in range(1, 4):
            res = guarded_order_send(mt5, req)
            if res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                logger.info(f"MT5 Position #{ticket} closed successfully on attempt {attempt}")
                return True
            time.sleep(0.15)
            t_fresh = mt5.symbol_info_tick(symbol)
            if t_fresh:
                req["price"] = t_fresh.bid if close_type == mt5.ORDER_TYPE_SELL else t_fresh.ask

        logger.error(f"Failed to close MT5 Position #{ticket}: {res.comment if res else 'Unknown error'}")
        return False

    # --------------------------------------------------------------------------
    # EVENT LOGGING & DASHBOARD EXPORT (SECTION 10)
    # --------------------------------------------------------------------------
    def _log_event(self, ticket: int, symbol: str, event_type: str, note: str):
        evt = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ticket": ticket,
            "symbol": symbol,
            "event_type": event_type,
            "note": note
        }
        self.event_log.insert(0, evt)
        if len(self.event_log) > 100:
            self.event_log = self.event_log[:100]
        logger.info(f"[{event_type}] Ticket #{ticket} ({symbol}): {note}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Provides full real-time telemetry for workstation UI dashboard."""
        with self.lock:
            active_list = []
            for t, p in self.positions.items():
                if p.state == PositionState.TRADE_CLOSED:
                    continue
                dist_to_peak = max(0.0, p.highest_profit - p.current_profit)
                dist_to_floor = max(0.0, p.current_profit - p.protected_floor)
                
                active_list.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "volume": p.volume,
                    "entry_price": p.entry_price,
                    "entry_time": p.entry_time,
                    "current_profit": p.current_profit,
                    "current_profit_currency": p.current_profit_currency,
                    "highest_profit": p.highest_profit,
                    "previous_peak": p.previous_peak,
                    "current_pullback": p.current_pullback,
                    "current_pullback_pct": p.current_pullback_pct,
                    "pullback_threshold": p.pullback_threshold,
                    "recovery_target": p.recovery_target,
                    "recovery_status": "PULLBACK ACTIVE" if p.pullback_active else ("RECOVERED" if p.recovery_count > 0 else "NORMAL"),
                    "recovery_count": p.recovery_count,
                    "protected_floor": p.protected_floor,
                    "trailing_armed": p.trailing_armed,
                    "current_milestone_tier": p.current_milestone_tier,
                    "status_label": p.status_label,
                    "last_event_note": p.last_event_note,
                    "last_update_time": p.last_update_time,
                    "dist_to_peak": round(dist_to_peak, 2),
                    "dist_to_floor": round(dist_to_floor, 2)
                })

            return {
                "config": asdict(self.config),
                "active_positions_count": len(active_list),
                "positions": active_list,
                "recent_events": self.event_log[:25]
            }

    def sync_with_live_mt5_positions(self, live_tickets: List[int]):
        """Synchronizes tracked positions with active broker tickets to purge stale items."""
        with self.lock:
            active_set = set(live_tickets)
            changed = False
            for t in list(self.positions.keys()):
                if t not in active_set and self.positions[t].state != PositionState.TRADE_CLOSED:
                    self.positions[t].state = PositionState.TRADE_CLOSED
                    self.positions[t].status_label = "TRADE CLOSED"
                    changed = True
            if changed:
                self.save_state()
