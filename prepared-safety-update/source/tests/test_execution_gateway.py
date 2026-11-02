"""Offline broker-contract tests: never import or initialize MetaTrader5."""
import ast
import json
import multiprocessing
import sqlite3
import os
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from execution_gateway import ExecutionGateway

NOW = 1793620800


class FakeBroker:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_REMOVE = 8
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_PLACED = 10008

    def __init__(self):
        self.account = NS(login=123, server="Test-Demo", equity=10000., margin_free=10000., trade_mode=0)
        self.tick = NS(bid=3000., ask=3000.3, time=NOW)
        self.info = NS(volume_min=.01, volume_max=100., volume_step=.01, trade_stops_level=10, point=.01)
        self.positions = []
        self.orders = []
        self.sent = []
        self.outcome = NS(retcode=10009, order=101, comment="done")

    def account_info(self): return self.account
    def symbol_info(self, symbol): return self.info
    def symbol_info_tick(self, symbol): return self.tick
    def positions_get(self, ticket=None):
        return self.positions if ticket is None or self.positions is None else [p for p in self.positions if p.ticket == ticket]
    def orders_get(self, ticket=None):
        return self.orders if ticket is None or self.orders is None else [p for p in self.orders if p.ticket == ticket]
    def order_calc_profit(self, side, symbol, volume, entry, stop):
        return (stop - entry) * volume * 100 * (1 if side == 0 else -1)
    def order_calc_margin(self, *args): return 10.
    def order_send(self, request):
        self.sent.append(request.copy())
        return self.outcome


def request(**changes):
    return dict(action=1, symbol="XAUUSD", type=0, volume=.01,
                price=3000.3, sl=2990., tp=3020., deviation=20, **changes)


@pytest.fixture
def env(tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(dict(enabled=True, account_login=123, account_server="Test-Demo", allow_live=False)))
    gateway = ExecutionGateway(policy, tmp_path / "risk.db", tmp_path / "STOP", clock=lambda: NOW)
    return gateway, FakeBroker(), policy


def blocked(gateway, broker, req, text, **kwargs):
    result = gateway.send(broker, req, **kwargs)
    assert result.retcode == 10006
    assert text in result.comment
    assert broker.sent == []
    return result


def test_valid_entry_uses_broker_risk_and_current_price(env):
    g, b, _ = env
    req = request()
    req["price"] = 2500
    assert g.send(b, req).retcode == 10009
    assert b.sent[0]["price"] == b.tick.ask
    assert req["price"] == 2500


@pytest.mark.parametrize("field,value,text", [
    ("sl", 0, "Stop loss"), ("sl", float("nan"), "Stop loss"),
    ("tp", 0, "Take profit"), ("sl", 3010, "geometry"),
    ("tp", 2999, "geometry"), ("volume", .02, "volume"),
    ("volume", -.01, "Volume"), ("volume", float("inf"), "Volume"),
    ("type", 2, "market BUY"), ("action", 5, "unsupported"),
    ("symbol", "EURUSD", "allowlist"), ("sl", 2900, "trade exceeds"),
    ("deviation", float("nan"), "deviation"),
])
def test_bad_entries_never_reach_broker(env, field, value, text):
    g, b, _ = env
    req = request()
    req[field] = value
    blocked(g, b, req, text)


@pytest.mark.parametrize("change,text", [
    ({"enabled": False}, "disabled"), ({"account_login": 321}, "pinned"),
    ({"account_server": "Other"}, "pinned"), ({"allow_live": "true"}, "boolean"),
    ({"max_combined_risk_pct": .05}, "portfolio limit"),
])
def test_policy_is_enforced(env, change, text):
    g, b, path = env
    p = json.loads(path.read_text())
    p.update(change)
    path.write_text(json.dumps(p))
    blocked(g, b, request(), text)


def test_missing_policy_fails_closed(env):
    g, b, p = env
    p.unlink()
    blocked(g, b, request(), "policy.json")


def test_estop_blocks_entry(env):
    g, b, _ = env
    g.estop_path.touch()
    blocked(g, b, request(), "EMERGENCY STOP")


@pytest.mark.parametrize("change,text", [("stale", "stale"), ("spread", "spread"),
                                         ("positions", "snapshot"), ("orders", "snapshot"),
                                         ("margin", "margin"), ("profit", "risk calculation")])
def test_failed_observation_and_execution_costs_block(env, change, text):
    g, b, _ = env
    if change == "stale": b.tick.time -= 60
    if change == "spread": b.tick.ask += 2
    if change == "positions": b.positions = None
    if change == "orders": b.orders = None
    if change == "margin": b.order_calc_margin = lambda *args: None
    if change == "profit": b.order_calc_profit = lambda *args: None
    blocked(g, b, request(), text)


def test_existing_account_exposure_counts_across_bots(env):
    g, b, _ = env
    b.positions = [NS(ticket=99, magic=999, symbol="XAUUSD", type=0, volume=.01, price_open=3000, sl=2990)]
    blocked(g, b, request(), "position/order cap")


def test_live_requires_both_policy_and_per_order_owner_approval(env):
    g, b, path = env
    b.account.trade_mode = 2
    blocked(g, b, request(), "real/contest", owner_approved=True)
    p = json.loads(path.read_text()); p["allow_live"] = True
    path.write_text(json.dumps(p))
    blocked(g, b, request(), "owner approval")
    assert g.send(b, request(), owner_approved=True).retcode == 10009


def test_account_change_during_validation_blocks(env):
    g, b, _ = env
    original = b.account_info
    count = [0]
    def switch():
        count[0] += 1
        return original() if count[0] == 1 else NS(login=456, server="Test-Demo", trade_mode=0)
    b.account_info = switch
    blocked(g, b, request(), "changed during")


@pytest.mark.parametrize("days,equity,reason", [(0, 9790, "daily loss"), (1, 9390, "weekly loss"),
                                               (8, 8990, "peak drawdown")])
def test_circuit_breakers_persist_across_process_restarts(env, days, equity, reason):
    g, b, _ = env
    # A rejected trade still records the initial observed account baseline.
    req = request(); req["volume"] = .02
    blocked(g, b, req, "volume")
    now = NOW + days * 86400
    g.clock = lambda: now
    b.tick.time = now
    b.account.equity = equity
    blocked(g, b, request(), reason)
    b.account.equity = 10000
    fresh = ExecutionGateway(g.policy_path, g.state_path, g.estop_path, clock=lambda: now)
    blocked(fresh, b, request(), reason)


@pytest.mark.parametrize("outcome", [None, NS(retcode=10012, order=0, comment="timeout"),
                                     NS(retcode=10009, order=101, comment="done")])
def test_uncertain_or_not_yet_observed_submission_cannot_be_retried(env, outcome):
    g, b, _ = env
    b.outcome = outcome
    g.send(b, request())
    b.sent.clear()
    fresh = ExecutionGateway(g.policy_path, g.state_path, g.estop_path, clock=lambda: NOW)
    blocked(fresh, b, request(), "reconciliation")


def test_explicit_rejection_releases_reservation(env):
    g, b, _ = env
    b.outcome = NS(retcode=10016, order=0, comment="invalid stops")
    g.send(b, request())
    b.outcome = NS(retcode=10009, order=101, comment="done")
    assert g.send(b, request()).retcode == 10009
    assert len(b.sent) == 2


def test_verified_close_and_tighten_work_during_estop_without_policy(env):
    g, b, policy = env
    policy.unlink()
    g.estop_path.touch()
    b.positions = [NS(ticket=99, symbol="XAUUSD", type=0, volume=.01, sl=2990)]
    req = request(); req.update(position=99, type=1)
    assert g.send(b, req).retcode == 10009
    req = dict(action=6, position=99, symbol="XAUUSD", sl=2995, tp=3020)
    assert g.send(b, req).retcode == 10009


@pytest.mark.parametrize("changes,text", [({"volume": .02}, "without reversing"),
                                         ({"type": 0}, "without reversing"),
                                         ({"symbol": "EURUSD"}, "symbol mismatch"),
                                         ({"position": 333}, "not found")])
def test_close_cannot_disguise_new_exposure(env, changes, text):
    g, b, _ = env
    b.positions = [NS(ticket=99, symbol="XAUUSD", type=0, volume=.01, sl=2990)]
    req = request(); req.update(position=99, type=1); req.update(changes)
    blocked(g, b, req, text)


def test_stop_removal_or_loosening_is_blocked(env):
    g, b, _ = env
    b.positions = [NS(ticket=99, symbol="XAUUSD", type=0, volume=.01, sl=2990)]
    for sl, message in ((0, "Protective stop"), (2980, "increase risk")):
        blocked(g, b, dict(action=6, position=99, sl=sl), message)


def test_exception_after_submission_retains_reservation(env):
    g, b, _ = env
    def crash(req):
        raise RuntimeError("transport lost")
    b.order_send = crash
    blocked(g, b, request(), "submission reserved")
    blocked(g, b, request(), "reconciliation")


def test_estop_engaged_during_validation_prevents_submission(env):
    g, b, _ = env
    def margin(*args):
        g.estop_path.touch()
        return 10
    b.order_calc_margin = margin
    blocked(g, b, request(), "EMERGENCY STOP")


def test_evolution_generated_code_keeps_gateway(tmp_path):
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "strategy_evolution_agent.py").read_text(encoding="utf-8-sig"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "emit_bot_code")
    # Execute only the pure generator function, never the agent's module startup.
    scope = dict(BOT_SLOT_1_CODE=str(tmp_path / "slot.py"), BOT_SLOT_2_CODE=str(tmp_path / "slot2.py"),
                 log=lambda message: None, os=os)
    exec(compile(ast.Module(body=[function], type_ignores=[]), "generator", "exec"), scope)
    dna = dict(name="Test", atr_mult=2., disaster_sl=100., lot_mode="clamped", max_layers=4,
               spacing_mode="ASYMMETRIC_ATR", target_usd=4., tp_atr_mult=1.2, waterfall_freeze=True)
    metrics = dict(dna=dna, net_profit=0., roi_pct=0., win_rate=0., profit_factor=0.,
                   max_drawdown=0., max_dd_pct=0.)
    scope["emit_bot_code"](metrics, 1, 1111)
    generated = (tmp_path / "slot.py").read_text(encoding="utf-8")
    parsed = ast.parse(generated)
    assert any(isinstance(n, ast.ImportFrom) and n.module == "execution_gateway" for n in parsed.body)
    assert "mt5.order_send(" not in generated


def _concurrent_sender(policy, state, stop, barrier, queue):
    broker = FakeBroker()
    g = ExecutionGateway(policy, state, stop, clock=lambda: NOW)
    barrier.wait(timeout=15)
    res = g.send(broker, request())
    queue.put((res.retcode, len(broker.sent)))


def test_two_processes_cannot_both_submit_into_empty_capacity(env):
    g, _, _ = env
    context = multiprocessing.get_context("spawn")
    barrier, queue = context.Barrier(2), context.Queue()
    workers = [context.Process(target=_concurrent_sender,
               args=(str(g.policy_path), str(g.state_path), str(g.estop_path), barrier, queue)) for _ in range(2)]
    try:
        for worker in workers: worker.start()
        outcomes = [queue.get(timeout=25) for _ in workers]
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        assert sum(sent for _, sent in outcomes) == 1
        assert sorted(code for code, _ in outcomes) == [10006, 10009]
    finally:
        for worker in workers:
            if worker.is_alive(): worker.terminate(); worker.join(timeout=5)


def test_all_python_broker_sends_use_shared_gateway():
    root = Path(__file__).resolve().parents[1]
    files = list(root.glob("*.py")) + list((root / "commander").glob("*.py")) + list((root / "CRT_GOLD_PRO/python_bot").glob("*.py"))
    direct = []
    for path in files:
        if path.name == "execution_gateway.py": continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "order_send":
                direct.append(f"{path.name}:{node.lineno}")
    assert not direct, direct
