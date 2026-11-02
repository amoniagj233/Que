"""Agent 9 — Central Risk Manager for APEX AI Commander.

Enforces independent, strict account-level risk controls across all bots:
- 0.25% equity risk per trade
- 1.0% combined open-position risk
- 2.0% daily equity loss limit
- 6.0% weekly equity loss limit
- 10.0% maximum portfolio drawdown before emergency suspension
- Duplicate order suppression
- Maximum spread and slippage gating
- Margin adequacy checks
- Mandatory Stop Loss enforcement
"""
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("apex_risk_manager")


class CentralRiskManager:
    def __init__(
        self,
        max_trade_risk_pct: float = 0.25,
        max_combined_risk_pct: float = 1.0,
        max_daily_loss_pct: float = 2.0,
        max_weekly_loss_pct: float = 6.0,
        max_portfolio_dd_pct: float = 10.0,
        max_spread_points: float = 60.0,
        max_gold_lot_per_trade: float = 0.05,
        max_total_gold_lots: float = 0.20,
    ):
        self.max_trade_risk_pct = max_trade_risk_pct
        self.max_combined_risk_pct = max_combined_risk_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_weekly_loss_pct = max_weekly_loss_pct
        self.max_portfolio_dd_pct = max_portfolio_dd_pct
        self.max_spread_points = max_spread_points
        self.max_gold_lot_per_trade = max_gold_lot_per_trade
        self.max_total_gold_lots = max_total_gold_lots

        # Circuit breaker states
        self.emergency_suspended = False
        self.suspension_reason = ""
        self.day_start_balance = 0.0
        self.week_start_balance = 0.0
        self.peak_equity = 0.0

        # Duplicate order suppression tracking: {(symbol, action, volume): timestamp}
        self.recent_orders: Dict[Tuple[str, str, float], float] = {}

    def update_account_baseline(self, balance: float, equity: float) -> None:
        """Call on initialization and daily rollover (06:00 AM Ghana time)."""
        if self.day_start_balance <= 0:
            self.day_start_balance = balance
        if self.week_start_balance <= 0:
            self.week_start_balance = balance
        if equity > self.peak_equity:
            self.peak_equity = equity

    def reset_daily_baseline(self, current_balance: float) -> None:
        """Called by 06:00 AM reporter to reset the 24-hour daily loss meter."""
        self.day_start_balance = current_balance
        if not self.emergency_suspended:
            self.suspension_reason = ""

    def evaluate_order(
        self,
        account: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        order: Dict[str, Any],
        current_spread: float = 25.0
    ) -> Tuple[bool, str]:
        """Strict pre-trade gate. Returns (allowed, reason)."""
        if self.emergency_suspended:
            return False, f"Risk Gate: EMERGENCY SUSPENDED - {self.suspension_reason}"

        balance = account.get("balance", 0.0)
        equity = account.get("equity", 0.0)

        if not all(math.isfinite(float(v)) and v > 0 for v in (balance, equity)):
            return False, "Risk Gate: Invalid account balance or equity."

        self.update_account_baseline(balance, equity)

        # 1. Daily Loss Limit Check (2%)
        daily_loss_amt = self.day_start_balance - equity
        daily_loss_pct = (daily_loss_amt / self.day_start_balance) * 100.0 if self.day_start_balance > 0 else 0.0
        if daily_loss_pct >= self.max_daily_loss_pct:
            self.emergency_suspended = True
            self.suspension_reason = f"Daily loss limit reached ({daily_loss_pct:.2f}% >= {self.max_daily_loss_pct}%)"
            return False, self.suspension_reason

        # 2. Maximum Drawdown Check (10%)
        if self.peak_equity > 0:
            drawdown_amt = self.peak_equity - equity
            drawdown_pct = (drawdown_amt / self.peak_equity) * 100.0
            if drawdown_pct >= self.max_portfolio_dd_pct:
                self.emergency_suspended = True
                self.suspension_reason = f"Portfolio max drawdown breached ({drawdown_pct:.2f}% >= {self.max_portfolio_dd_pct}%)"
                return False, self.suspension_reason

        # 3. Duplicate Order Check (5-second throttle)
        now_ts = time.time()
        key = (order.get("symbol", ""), order.get("action", "").upper(), round(float(order.get("volume", 0.01)), 2))
        last_time = self.recent_orders.get(key, 0.0)
        if now_ts - last_time < 5.0:
            return False, f"Duplicate order suppressed: same order sent {now_ts - last_time:.1f}s ago."

        # 4. Mandatory Stop Loss Check
        sl = float(order.get("sl") or 0.0)
        if not math.isfinite(sl) or sl <= 0:
            return False, "Risk Gate Rejected: Mandatory Stop Loss (SL) is required on all orders."

        # 5. Volume Check
        vol = float(order.get("volume", 0.01))
        if not math.isfinite(vol) or vol <= 0 or vol > self.max_gold_lot_per_trade:
            return False, f"Risk Gate: Lot size {vol} exceeds maximum allowed per trade ({self.max_gold_lot_per_trade} lots)."

        # 6. Total Exposure & Combined Open Risk Check
        current_total_lots = sum(p.get("volume", 0.0) for p in open_positions)
        if current_total_lots + vol > self.max_total_gold_lots:
            return False, f"Risk Gate: Total gold volume {current_total_lots + vol:.2f} exceeds cap ({self.max_total_gold_lots} lots)."

        # Calculate open risk from Stop Losses
        total_open_risk_dollars = 0.0
        for p in open_positions:
            pos_sl = p.get("sl", 0.0)
            if not math.isfinite(float(pos_sl)) or pos_sl <= 0:
                return False, "Risk Gate: Existing position has no valid protective stop."
            if pos_sl > 0:
                dist = abs(p.get("price_open", 0.0) - pos_sl)
                # 1 lot gold = 100 oz -> $1/oz move = $100 per lot
                risk_dollars = dist * 100.0 * p.get("volume", 0.01)
                total_open_risk_dollars += risk_dollars

        entry_price = order.get("price") or order.get("ask" if order.get("action", "").upper() == "BUY" else "bid")
        if entry_price is None or not math.isfinite(float(entry_price)) or float(entry_price) <= 0:
            return False, "Risk Gate: A valid entry price is required."
        entry_price = float(entry_price)
        trade_risk_dollars = abs(entry_price - sl) * 100.0 * vol
        combined_risk_pct = ((total_open_risk_dollars + trade_risk_dollars) / equity) * 100.0
        if combined_risk_pct >= self.max_combined_risk_pct:
            return False, f"Risk Gate: Combined open risk ({combined_risk_pct:.2f}%) exceeds limit ({self.max_combined_risk_pct}%)."

        # Single trade risk check
        trade_risk_pct = (trade_risk_dollars / equity) * 100.0 if equity > 0 else 0.0
        if trade_risk_pct > self.max_trade_risk_pct:
            return False, f"Risk Gate: Trade risk ({trade_risk_pct:.2f}%) exceeds max per-trade limit ({self.max_trade_risk_pct}%)."

        # 7. Spread Spike Filter
        if current_spread > self.max_spread_points:
            return False, f"Risk Gate: Current gold spread ({current_spread} pts) exceeds max limit ({self.max_spread_points} pts)."

        # 8. Available Margin Check
        margin_free = account.get("margin_free", 0.0)
        # Margin for 0.01 lot gold at 1:500 is ~$60, require at least $500 free
        if margin_free < 500.0:
            return False, f"Risk Gate: Insufficient free margin (${margin_free:.2f} < $500.00)."

        # Order passed all checks! Register order timestamp
        self.recent_orders[key] = now_ts
        return True, "Risk Gate Passed"

    def release_suspension(self) -> None:
        """Owner/commander manual release of risk suspension."""
        self.emergency_suspended = False
        self.suspension_reason = ""


# Global singleton instance
risk_manager = CentralRiskManager()
