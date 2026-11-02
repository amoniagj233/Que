"""Shared, fail-closed MT5 order boundary. Importing this never connects to MT5.

Policy, account baselines and in-flight reservations are shared by all Python
processes. Only this module may call the broker's order_send method.
"""
import json
import logging
import math
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from trade_safety import positive, validate_geometry

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "execution_policy.json"
STATE_PATH = ROOT / "commander" / "data" / "execution_risk.db"
ESTOP_PATH = ROOT / "commander" / "data" / "EMERGENCY_STOP"
LIMITS = {
    "max_trade_risk_pct": 0.25, "max_combined_risk_pct": 1.0,
    "max_daily_loss_pct": 2.0, "max_weekly_loss_pct": 6.0,
    "max_drawdown_pct": 10.0, "max_volume": 0.01,
    "max_open_positions": 1, "max_spread": 0.65,
    "max_quote_age_seconds": 15,
}
log = logging.getLogger("execution_gateway")


def _deny(reason, request):
    log.warning("Order blocked: %s", reason)
    # Match the MT5 result interface expected by existing bot call sites.
    values = dict(retcode=10006, comment=f"Risk gate: {reason}", order=0, deal=0,
                  volume=0.0, price=0.0, bid=0.0, ask=0.0, request_id=0,
                  retcode_external=0, request=request)
    return SimpleNamespace(**values, _asdict=lambda: values.copy())


class ExecutionGateway:
    def __init__(self, policy_path=POLICY_PATH, state_path=STATE_PATH,
                 estop_path=ESTOP_PATH, clock=time.time):
        self.policy_path = Path(policy_path)
        self.state_path = Path(state_path)
        self.estop_path = Path(estop_path)
        self.clock = clock

    def _policy(self):
        with self.policy_path.open(encoding="utf-8") as f:
            p = json.load(f)
        if p.get("enabled") is not True:
            raise ValueError("entries disabled by execution policy")
        if type(p.get("account_login")) is not int or p["account_login"] <= 0:
            raise ValueError("pin the account login in execution_policy.json")
        if not isinstance(p.get("account_server"), str) or not p["account_server"].strip():
            raise ValueError("pin the account server in execution_policy.json")
        if type(p.get("allow_live", False)) is not bool:
            raise ValueError("allow_live must be a boolean")
        for key, ceiling in LIMITS.items():
            p[key] = min(positive(p.get(key, ceiling), key), ceiling)
        return p

    def _db(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.state_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS baselines (account TEXT PRIMARY KEY, "
                   "day TEXT, week TEXT, day_equity REAL, week_equity REAL, peak REAL, halted TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, "
                   "account TEXT, created REAL, state TEXT, ticket INTEGER, request TEXT, detail TEXT)")
        return db

    @staticmethod
    def _positions(broker):
        positions = broker.positions_get()
        if positions is None:
            raise ValueError("position snapshot unavailable")
        return list(positions)

    @staticmethod
    def _loss(broker, side, symbol, volume, entry, stop):
        value = broker.order_calc_profit(side, symbol, volume, entry, stop)
        if value is None or not math.isfinite(float(value)):
            raise ValueError("broker risk calculation unavailable")
        return max(0.0, -float(value))

    def _reduce(self, broker, req):
        """Only verified closes, pending cancellations and SL tightening bypass entry gates."""
        action = req.get("action")
        if action == broker.TRADE_ACTION_REMOVE:
            orders = broker.orders_get(ticket=int(req.get("order", 0)))
            if not orders or len(orders) != 1:
                raise ValueError("pending order to cancel was not found")
            return True
        if action not in (broker.TRADE_ACTION_DEAL, broker.TRADE_ACTION_SLTP):
            raise ValueError("unsupported order action; pending entries/modifications are disabled")
        ticket = req.get("position")
        if not ticket:
            if action == broker.TRADE_ACTION_SLTP:
                raise ValueError("stop modification requires a position ticket")
            return False
        positions = broker.positions_get(ticket=int(ticket))
        if not positions or len(positions) != 1:
            raise ValueError("position to manage was not found")
        pos = positions[0]
        if req.get("symbol", pos.symbol) != pos.symbol:
            raise ValueError("position symbol mismatch")
        if action == broker.TRADE_ACTION_DEAL:
            opposite = broker.ORDER_TYPE_SELL if pos.type == broker.ORDER_TYPE_BUY else broker.ORDER_TYPE_BUY
            if req.get("type") != opposite or positive(req.get("volume", 0), "Close volume") > pos.volume:
                raise ValueError("close must reduce the specified position without reversing it")
        else:
            stop = positive(req.get("sl", 0), "Protective stop")
            if pos.sl > 0 and ((pos.type == broker.ORDER_TYPE_BUY and stop < pos.sl)
                               or (pos.type == broker.ORDER_TYPE_SELL and stop > pos.sl)):
                raise ValueError("stop changes may not increase risk")
            tick = broker.symbol_info_tick(pos.symbol)
            if tick is None or not (stop < tick.bid if pos.type == broker.ORDER_TYPE_BUY else stop > tick.ask):
                raise ValueError("stop is on the wrong side of the quote")
        return True

    def _baseline(self, db, key, equity, p, now):
        date = datetime.fromtimestamp(now, timezone.utc)
        day = date.date().isoformat()
        iso = date.isocalendar()
        week = f"{iso.year}-{iso.week}"
        row = db.execute("SELECT * FROM baselines WHERE account=?", (key,)).fetchone()
        if row is None:
            db.execute("INSERT INTO baselines VALUES (?,?,?,?,?,?,?)",
                       (key, day, week, equity, equity, equity, ""))
            row = db.execute("SELECT * FROM baselines WHERE account=?", (key,)).fetchone()
        day_base = row["day_equity"] if row["day"] == day else equity
        week_base = row["week_equity"] if row["week"] == week else equity
        peak = max(row["peak"], equity)
        halted = row["halted"]
        for base, limit, name in ((day_base, p["max_daily_loss_pct"], "daily loss"),
                                  (week_base, p["max_weekly_loss_pct"], "weekly loss"),
                                  (peak, p["max_drawdown_pct"], "peak drawdown")):
            if (base - equity) / base * 100 >= limit:
                halted = halted or name
        db.execute("UPDATE baselines SET day=?,week=?,day_equity=?,week_equity=?,peak=?,halted=? WHERE account=?",
                   (day, week, day_base, week_base, peak, halted, key))
        return halted

    def send(self, broker, request, *, owner_approved=False):
        req = dict(request)
        db = None
        submission = None
        try:
            db = self._db()
            db.execute("BEGIN IMMEDIATE")
            # Risk-reducing actions remain usable even with no policy or an estop.
            if self._reduce(broker, req):
                return broker.order_send(req)
            p = self._policy()
            if self.estop_path.exists():
                raise ValueError("EMERGENCY STOP active")
            acc = broker.account_info()
            if acc is None or acc.login != p["account_login"] or acc.server != p["account_server"]:
                raise ValueError("connected account does not match pinned login/server")
            if acc.trade_mode != broker.ACCOUNT_TRADE_MODE_DEMO and not p.get("allow_live", False):
                raise ValueError("real/contest account entries are disabled")
            if acc.trade_mode != broker.ACCOUNT_TRADE_MODE_DEMO and owner_approved is not True:
                raise ValueError("real-account entries require Commander owner approval")
            equity = positive(acc.equity, "Account equity")
            now = self.clock()
            key = f"{acc.server}:{acc.login}"
            halted = self._baseline(db, key, equity, p, now)
            if halted:
                db.commit()  # Circuit breakers must survive rejection and process restart.
                raise ValueError(f"persistent circuit breaker: {halted}")
            positions = self._positions(broker)
            orders = broker.orders_get()
            if orders is None:
                raise ValueError("pending-order snapshot unavailable")
            # Reservations are committed BEFORE order_send. A crash or uncertain
            # result cannot free capacity for another process to submit an entry.
            for row in db.execute("SELECT id,ticket FROM submissions WHERE account=? AND state='unsettled'", (key,)).fetchall():
                if row["ticket"] and any(pos.ticket == row["ticket"] for pos in positions):
                    db.execute("UPDATE submissions SET state='observed' WHERE id=?", (row["id"],))
                else:
                    raise ValueError("an earlier submission needs broker reconciliation; entries blocked")
            symbol = req.get("symbol")
            if symbol not in ("XAUUSD", "XAUUSDc"):
                raise ValueError("symbol is outside the gold allowlist")
            if req.get("type") not in (broker.ORDER_TYPE_BUY, broker.ORDER_TYPE_SELL):
                raise ValueError("entry must be a market BUY or SELL")
            if len(positions) + len(orders) >= p["max_open_positions"]:
                raise ValueError("account position/order cap reached")
            info = broker.symbol_info(symbol)
            tick = broker.symbol_info_tick(symbol)
            if info is None or tick is None:
                raise ValueError("symbol or quote unavailable")
            age = now - float(tick.time)
            if not math.isfinite(age) or age < -2 or age > p["max_quote_age_seconds"]:
                raise ValueError("quote is stale or has an invalid timestamp")
            if tick.ask - tick.bid > p["max_spread"]:
                raise ValueError("spread exceeds policy")
            buy = req["type"] == broker.ORDER_TYPE_BUY
            stop = positive(req.get("sl", 0), "Stop loss")
            target = positive(req.get("tp", 0), "Take profit")
            validate_geometry(buy, tick.bid, tick.ask, stop, target, info.trade_stops_level * info.point)
            volume = positive(req.get("volume", 0), "Volume")
            if volume > min(p["max_volume"], info.volume_max) or volume < info.volume_min:
                raise ValueError("volume exceeds policy/broker limits")
            if abs(volume / positive(info.volume_step, "Volume step") - round(volume / info.volume_step)) > 1e-7:
                raise ValueError("volume is not aligned to the broker step")
            # Reserve adverse execution within the requested deviation as well.
            deviation = float(req.get("deviation", 0))
            if not math.isfinite(deviation) or deviation < 0:
                raise ValueError("invalid execution deviation")
            entry = tick.ask if buy else tick.bid
            worst_entry = entry + deviation * info.point * (1 if buy else -1)
            new_risk = self._loss(broker, req["type"], symbol, volume, worst_entry, stop)
            open_risk = 0.0
            for pos in positions:
                sl = positive(pos.sl, "Existing position stop")
                open_risk += self._loss(broker, pos.type, pos.symbol, pos.volume, pos.price_open, sl)
            # Pending orders can also consume risk/capacity; never ignore them.
            for order in orders:
                sl = positive(order.sl, "Pending order stop")
                side = broker.ORDER_TYPE_BUY if order.type in (2, 4, 6) else broker.ORDER_TYPE_SELL
                open_risk += self._loss(broker, side, order.symbol, order.volume_current, order.price_open, sl)
            if new_risk / equity * 100 > p["max_trade_risk_pct"]:
                raise ValueError("proposed trade exceeds risk limit")
            if (open_risk + new_risk) / equity * 100 > p["max_combined_risk_pct"]:
                raise ValueError("existing plus proposed risk exceeds portfolio limit")
            margin = broker.order_calc_margin(req["type"], symbol, volume, entry)
            if margin is None or not math.isfinite(float(margin)) or margin < 0 or margin > acc.margin_free:
                raise ValueError("margin calculation failed or free margin is insufficient")
            req["price"] = entry
            if self.estop_path.exists():
                raise ValueError("EMERGENCY STOP active")
            current = broker.account_info()
            if current is None or (current.login, current.server, current.trade_mode) != (acc.login, acc.server, acc.trade_mode):
                raise ValueError("account changed during validation")
            submission = db.execute("INSERT INTO submissions(account,created,state,ticket,request,detail) VALUES(?,?,'unsettled',0,?,'awaiting broker result')",
                                    (key, now, json.dumps(req))).lastrowid
            db.commit()
            result = broker.order_send(req)
            accepted = {broker.TRADE_RETCODE_DONE, broker.TRADE_RETCODE_DONE_PARTIAL, broker.TRADE_RETCODE_PLACED}
            # Unknown/error/timeout results stay reserved. Only explicit rejection
            # codes whose meaning guarantees no execution may release a slot.
            rejected = {10004, 10006, 10013, 10014, 10015, 10016, 10017,
                        10018, 10019, 10020, 10021, 10022, 10024, 10026, 10027, 10030}
            state = "rejected" if result is not None and result.retcode in rejected else "unsettled"
            ticket = int(getattr(result, "order", 0) or 0)
            db.execute("UPDATE submissions SET state=?,ticket=?,detail=? WHERE id=?",
                       (state, ticket, str(getattr(result, "comment", "uncertain broker result")), submission))
            if result is None:
                return _deny("broker returned no result; reservation retained", req)
            if result.retcode not in accepted and state == "unsettled":
                log.error("Uncertain broker outcome retained for reconciliation: %s", result.retcode)
            return result
        except Exception as exc:
            detail = str(exc)
            if submission is not None:
                detail += "; submission reserved, reconcile broker outcome before retrying"
            return _deny(detail, req)
        finally:
            if db is not None:
                # Keep new peak/rollover baselines even when validation refuses
                # an entry, but never roll back a committed in-flight reservation.
                if db.in_transaction:
                    db.commit()
                db.close()


gateway = ExecutionGateway()


def guarded_order_send(broker, request, *, owner_approved=False):
    return gateway.send(broker, request, owner_approved=owner_approved)
