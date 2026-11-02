import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commander.commander import Commander  # noqa: E402
from commander.core import CommanderError, safe_write, rollback_file, BASE_DIR  # noqa: E402


@pytest.fixture
def cmd(tmp_path):
    c = Commander(db_path=str(tmp_path / "t.db"), autostart=False)
    c.adapters.process_table = lambda: {}          # no powershell in tests; nothing is "running"
    yield c
    c.release_estop()


def drain(c, rounds=40):
    for _ in range(rounds):
        c.store.execute("UPDATE tasks SET not_before=0 WHERE state='pending'")
        c.scheduler.run_pending_sync()
        time.sleep(0.1)
        if not c.store.query("SELECT 1 FROM tasks WHERE state IN ('pending','running')"):
            return
    raise AssertionError("tasks did not drain")


def test_discovery_registers_existing_agents(cmd):
    ids = {a["id"]: a for a in cmd.registry.all()}
    assert {"agent_cro_risk", "strategy_evolution_agent", "bot_slot_1", "ops", "analyst", "auditor"} <= set(ids)
    assert ids["bot_slot_1"]["risk"] == "live" and ids["quant_desk_orchestrator"]["risk"] == "live"
    assert ids["agent_cro_risk"]["team"] == "Risk"
    assert cmd.discover() == []                      # idempotent


def test_permissions_ceiling_and_sensitive_approval(cmd):
    assert cmd.perms.grant("agent_cro_risk", "MODIFY_CODE")["status"] == "denied"      # above ceiling
    assert cmd.perms.grant("agent_cro_risk", "ACCESS_API")["status"] == "granted"
    cmd.perms.set_ceiling("bot_slot_1", ["READ_DATA", "REQUEST_LIVE_TRADES"])
    r = cmd.perms.grant("bot_slot_1", "REQUEST_LIVE_TRADES")
    assert r["status"] == "pending_approval" and not cmd.perms.has("bot_slot_1", "REQUEST_LIVE_TRADES")
    cmd.approvals.decide(r["approval"], True)
    assert cmd.perms.has("bot_slot_1", "REQUEST_LIVE_TRADES")
    cmd.perms.revoke("bot_slot_1", "REQUEST_LIVE_TRADES")
    actions = [a["action"] for a in cmd.audit.recent(50, "permission")]
    assert "permission.grant" in actions and "permission.revoke" in actions and "permission.denied" in actions


def test_observer_is_read_only(cmd):
    assert cmd.level() == 1
    with pytest.raises(CommanderError):
        cmd.agent_action("agent_cro_risk", "start")
    out = cmd.chat("Commander, check all my AI agents and report their current activities", wait=0)
    assert out["objective"]
    drain(cmd)
    rep = cmd.store.one("SELECT report,state FROM objectives WHERE id=?", (out["objective"],))
    assert rep["state"] == "done" and "CRO Risk Officer" in rep["report"]
    # mutating plan stays queued at level 1
    cmd.chat("assign the strategy agents to develop and backtest improved gold strategies", wait=0)
    assert "needs level 2" in cmd.chat("develop and backtest strategies", wait=0)["reply"]


def test_dependency_order_and_strategy_validation_is_skeptical(cmd):
    cmd.set_level(2)
    oid = cmd.chat("analyze the results from all my trading bots and recommend the most promising strategies", wait=0)["objective"]
    drain(cmd)
    t = {x["key"]: x for x in cmd.store.query("SELECT * FROM tasks WHERE objective=?", (oid,))}
    assert t["validate"]["started"] >= t["rank"]["finished"]
    rep = cmd.store.one("SELECT report FROM objectives WHERE id=?", (oid,))["report"]
    assert "UNVALIDATED" in rep and "out-of-sample" in rep


def test_duplicate_suppression_and_missing_permission(cmd):
    cmd.set_level(2)
    a = cmd.scheduler.submit({"kind": "tail_log", "owner": "agent_cro_risk", "perms": ["READ_DATA"], "params": {"n": 3}})
    b = cmd.scheduler.submit({"kind": "tail_log", "owner": "agent_cro_risk", "perms": ["READ_DATA"], "params": {"n": 3}})
    assert a == b
    c = cmd.scheduler.submit({"kind": "tail_log", "owner": "agent_cro_risk", "perms": ["MODIFY_CODE"], "params": {"n": 4}})
    drain(cmd)
    assert cmd.store.one("SELECT state FROM tasks WHERE id=?", (c,))["state"] == "failed"
    assert "permission denied" in cmd.store.one("SELECT error FROM tasks WHERE id=?", (c,))["error"]


def test_retry_limit_and_circuit_breaker(cmd):
    cmd.set_level(2)
    ids = [cmd.scheduler.submit({"kind": "bogus", "owner": "agent_news_sentinel", "perms": ["READ_DATA"],
                                 "params": {"i": i}, "max_attempts": 2}) for i in range(3)]
    for _ in range(20):
        drain_step = cmd.store.query("SELECT state FROM tasks WHERE state IN ('pending','running','blocked')")
        if not drain_step:
            break
        cmd.store.execute("UPDATE tasks SET not_before=0 WHERE state IN ('pending','blocked')")
        cmd.scheduler.run_pending_sync()
        time.sleep(0.1)
    a = cmd.registry.get("agent_news_sentinel")
    assert a["paused"] == 1 and a["breaker_until"] > time.time()      # auto-paused, no infinite retry loop
    states = [cmd.store.one("SELECT state,attempts FROM tasks WHERE id=?", (i,)) for i in ids]
    assert all(s["attempts"] <= 2 for s in states)
    assert any(m["type"] == "escalation" for m in cmd.bus.since(0, 500))


def test_restart_recovery_keeps_state(tmp_path):
    p = str(tmp_path / "r.db")
    c1 = Commander(db_path=p, autostart=False)
    c1.set_level(3)
    tid = c1.scheduler.submit({"kind": "tail_log", "owner": "agent_cro_risk", "perms": ["READ_DATA"]})
    c1.store.execute("UPDATE tasks SET state='running' WHERE id=?", (tid,))     # simulate crash mid-task
    c2 = Commander(db_path=p, autostart=False)
    assert c2.level() == 3
    assert c2.store.one("SELECT state FROM tasks WHERE id=?", (tid,))["state"] == "pending"
    assert c2.audit.recent(5, "commander.started")


def test_emergency_stop_blocks_everything(cmd):
    cmd.set_level(4)
    cmd.scheduler.submit({"kind": "tail_log", "owner": "agent_cro_risk", "perms": ["READ_DATA"]})
    cmd.emergency_stop()
    assert cmd.store.query("SELECT 1 FROM tasks WHERE state='cancelled'")
    with pytest.raises(CommanderError):
        cmd.agent_action("agent_cro_risk", "start")
    with pytest.raises(CommanderError):
        cmd.chat("check all agents", wait=0) if False else cmd.plan_objective("x", "fleet_report")
    cmd.release_estop()
    assert not cmd.estop()


def test_live_agent_start_needs_approval(cmd):
    cmd.set_level(4)
    started = []
    cmd.adapters.start = lambda a: started.append(a["id"]) or {"ok": True}
    r = cmd.agent_action("bot_slot_1", "start")
    assert r["status"] == "pending_approval" and not started
    cmd.approvals.decide(r["approval"], True)
    assert started == ["bot_slot_1"]
    cmd.agent_action("agent_news_sentinel", "start")                  # research agent: no approval
    assert "agent_news_sentinel" in started


def test_live_gateway_hard_limits(cmd):
    cmd.set_level(4)
    order = {"symbol": "XAUUSDc", "action": "BUY", "volume": 0.01, "sl": 1.0, "tp": 2.0}
    with pytest.raises(CommanderError):
        cmd.request_live_trade("bot_slot_1", order)                    # no permission
    cmd.perms.set_ceiling("bot_slot_1", ["READ_DATA", "REQUEST_LIVE_TRADES"])
    cmd.perms.grant("bot_slot_1", "REQUEST_LIVE_TRADES", approved=True)
    for bad in ({**order, "volume": 0.02}, {**order, "symbol": "BTCUSD"}, {**order, "sl": 0}):
        with pytest.raises(CommanderError):
            cmd.request_live_trade("bot_slot_1", bad)
    cmd.positions_fn = lambda: 1
    with pytest.raises(CommanderError):
        cmd.request_live_trade("bot_slot_1", order)                    # position limit
    cmd.positions_fn = lambda: 0
    sent = []
    cmd.live_executor = lambda o: sent.append(o) or {"ok": True}
    r = cmd.request_live_trade("bot_slot_1", order)
    assert r["status"] == "pending_approval" and not sent              # never auto-executes
    cmd.emergency_stop()
    with pytest.raises(CommanderError):
        cmd.approvals.decide(r["approval"], True)                      # estop beats approval
    assert not sent


def test_protected_files_and_rollback(cmd):
    with pytest.raises(CommanderError):
        safe_write(cmd.store, "config.py", "x")
    with pytest.raises(CommanderError):
        safe_write(cmd.store, "../outside.txt", "x")
    p = os.path.join(BASE_DIR, "scratch", "cmdr_test.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write("v1")
    safe_write(cmd.store, "scratch/cmdr_test.txt", "v2", "test")
    assert open(p).read() == "v2"
    rollback_file(cmd.store, p)
    assert open(p).read() == "v1"
    os.remove(p)


def test_workflow_ab_promote_and_rollback(cmd):
    cmd.set_level(3)
    v = cmd.propose_workflow_candidate("fleet_report", ["diag", "diagnose", "ops", ["READ_DATA"], ["report"]])
    cmd.store.execute("UPDATE workflows SET runs=6, successes=6 WHERE key='fleet_report' AND version=?", (v,))
    cmd.store.execute("UPDATE workflows SET runs=6, successes=5 WHERE key='fleet_report' AND version=1")
    assert cmd.evaluate_workflows() == [("fleet_report", v, "promoted")]
    v3 = cmd.propose_workflow_candidate("fleet_report", ["x", "diagnose", "ops", ["READ_DATA"], []])
    cmd.store.execute("UPDATE workflows SET runs=6, successes=1 WHERE key='fleet_report' AND version=?", (v3,))
    assert cmd.evaluate_workflows() == [("fleet_report", v3, "rolled_back")]
    cmd.set_level(2)
    with pytest.raises(CommanderError):
        cmd.propose_workflow_candidate("diagnose", ["y", "diagnose", "ops", ["READ_DATA"], []])
