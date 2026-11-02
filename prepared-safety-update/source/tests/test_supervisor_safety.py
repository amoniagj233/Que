from types import SimpleNamespace as NS

import pytest

from commander.commander import Commander
from commander.supervisor import LiveBotSupervisor
from commander.risk_manager import CentralRiskManager
from commander.core import CommanderError
from concurrent.futures import ThreadPoolExecutor
import threading


@pytest.mark.parametrize("risk", ["live", "unknown", "research", "safety"])
def test_observer_supervisor_never_launches_processes(monkeypatch, risk):
    supervisor = LiveBotSupervisor()
    supervisor.register_bot("bot", "Bot", "bot_slot_1.py", 1111, risk_tier=risk)
    supervisor._get_running_python_scripts = lambda: {}
    monkeypatch.setattr("commander.supervisor.subprocess.Popen", lambda *a, **k: pytest.fail("observer launched a process"))
    supervisor.reconcile_fleet_state()
    assert not supervisor._attempt_safe_restart("bot")


@pytest.mark.parametrize("risk", ["live", "unknown"])
def test_commander_health_does_not_restart_unapproved_code(tmp_path, risk):
    c = Commander(db_path=str(tmp_path / "commander.db"), autostart=False)
    c.set_level(4)
    c.adapters.start = lambda *args: pytest.fail("unapproved restart")
    c.health._recover(dict(id="bot_slot_1", risk=risk))
    assert c.bus.since(0, 100)
    c.exec_pool.shutdown(wait=True)


def test_combined_risk_includes_proposed_order():
    risk = CentralRiskManager(max_trade_risk_pct=.25, max_combined_risk_pct=1.)
    account = dict(balance=10000., equity=10000., margin_free=10000.)
    positions = [dict(volume=.01, price_open=3000., sl=2910.)]  # $90 already at risk
    order = dict(symbol="XAUUSD", action="BUY", volume=.01, price=3000., sl=2980.)  # +$20
    allowed, reason = risk.evaluate_order(account, positions, order)
    assert not allowed
    assert "Combined open risk" in reason


def test_commander_reports_failed_execution_as_not_executed(tmp_path):
    c = Commander(db_path=str(tmp_path / "commander.db"), autostart=False)
    c.set_level(2)
    c.perms.set_ceiling("bot_slot_1", ["REQUEST_LIVE_TRADES"])
    c.perms.grant("bot_slot_1", "REQUEST_LIVE_TRADES", approved=True)
    c.positions_fn = lambda: 0
    c.live_executor = lambda order: {"ok": False, "error": "Risk gate rejected"}
    res = c._execute_live_trade({"agent": "bot_slot_1", "order": dict(symbol="XAUUSD", action="BUY", volume=.01, sl=2990, tp=3020)})
    assert res["executed"] is False
    c.exec_pool.shutdown(wait=True)


@pytest.mark.parametrize("revoke", [True, False])
def test_pending_trade_rechecks_permission_and_autonomy(tmp_path, revoke):
    c = Commander(db_path=str(tmp_path / "commander.db"), autostart=False)
    c.set_level(2)
    c.perms.set_ceiling("bot_slot_1", ["REQUEST_LIVE_TRADES"])
    c.perms.grant("bot_slot_1", "REQUEST_LIVE_TRADES", approved=True)
    c.positions_fn = lambda: 0
    c.live_executor = lambda *args: pytest.fail("stale approval executed")
    pending = c.request_live_trade("bot_slot_1", dict(symbol="XAUUSD", action="BUY", volume=.01, sl=2990, tp=3020))
    if revoke: c.perms.revoke("bot_slot_1", "REQUEST_LIVE_TRADES")
    else: c.set_level(1)
    with pytest.raises(CommanderError):
        c.approvals.decide(pending["approval"], True)
    c.exec_pool.shutdown(wait=True)


def test_competing_approval_clicks_execute_handler_once(tmp_path):
    c = Commander(db_path=str(tmp_path / "commander.db"), autostart=False)
    calls = []
    aid = c.approvals.request("test", "one", {}, "owner")
    c.approvals.handlers["test"] = lambda detail: calls.append(detail)
    barrier = threading.Barrier(2)
    original = c.store.one
    def simultaneous_read(sql, args=()):
        result = original(sql, args)
        if sql.startswith("SELECT * FROM approvals WHERE id="):
            barrier.wait(timeout=10)
        return result
    c.store.one = simultaneous_read
    def decide():
        try:
            c.approvals.decide(aid, True)
            return "approved"
        except CommanderError:
            return "refused"
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: decide(), range(2)))
    assert sorted(result) == ["approved", "refused"]
    assert len(calls) == 1
    c.exec_pool.shutdown(wait=True)
