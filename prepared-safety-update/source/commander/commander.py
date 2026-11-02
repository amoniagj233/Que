"""Supreme AI Commander orchestrator."""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .agents import Adapters, discover_specs
from .core import (BASE_DIR, DATA_DIR, LEVELS, PERMISSIONS, TERMINAL, Approvals, Audit, Bus, CommanderError,
                   Health, Permissions, Quality, Registry, Scheduler, Store, jd, jl, now)

# Hard live-trading limits. Constants on purpose: no setting, task, agent or chat message can change them.
LIVE_LIMITS = {"symbols": {"XAUUSD", "XAUUSDc"}, "max_volume": 0.01, "max_open_positions": 1, "require_sl_tp": True}
READ_ONLY = {"READ_DATA", "ANALYZE_DATA"}

DEFAULT_WORKFLOWS = {
    "fleet_report": [("report", "agent_report", "ops", ["READ_DATA"], [])],
    "diagnose": [("report", "agent_report", "ops", ["READ_DATA"], []),
                 ("diag", "diagnose", "ops", ["READ_DATA", "ANALYZE_DATA"], ["report"])],
    "permissions": [("gaps", "permission_gaps", "ops", ["READ_DATA"], [])],
    "teams": [("teams", "team_plan", "ops", ["READ_DATA", "ANALYZE_DATA"], [])],
    "strategy_review": [("rank", "rank_strategies", "analyst", ["READ_DATA", "ANALYZE_DATA"], []),
                        ("trades", "trade_summary", "analyst", ["READ_DATA"], []),
                        ("validate", "validate_strategies", "auditor", ["READ_DATA", "ANALYZE_DATA"], ["rank"])],
    "strategy_dev": [("rank", "rank_strategies", "analyst", ["READ_DATA", "ANALYZE_DATA"], []),
                     ("bt", "backtest_review", "analyst", ["READ_DATA", "RUN_BACKTESTS"], []),
                     ("validate", "validate_strategies", "auditor", ["READ_DATA", "ANALYZE_DATA"], ["rank"])],
}


class Commander:
    def __init__(self, db_path=None, autostart=True):
        self.store = Store(db_path)
        self.audit = Audit(self.store)
        self.bus = Bus(self.store)
        self.approvals = Approvals(self.store, self.audit, self.bus)
        self.perms = Permissions(self.store, self.audit, self.approvals)
        self.registry = Registry(self.store, self.audit)
        self.quality = Quality()
        self.exec_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="cmdr-exec")
        self.adapters = Adapters(self)
        self.scheduler = Scheduler(self)
        self.health = Health(self)
        self.last_health = {}
        self.live_executor = None      # callable(order)->dict, injected by the web layer
        self.positions_fn = None       # callable()->int open positions, injected by the web layer
        self.approvals.handlers.update({
            "grant_permission": lambda d: self.perms.grant(d["agent"], d["perm"], "owner", approved=True),
            "start_agent": lambda d: self._do_start(d["agent"]),
            "live_trade": self._execute_live_trade,
        })
        self.discover()
        self._recover_after_restart()
        self._seed_workflows()
        if autostart:
            self.scheduler.start()
            self.health.start()
        self.audit.log("commander", "commander.started", level=self.level())

    # ---------- state ----------
    def level(self):
        return int(self.store.get("level", 1))

    def estop(self):
        return bool(self.store.get("estop", False))

    def set_level(self, n, actor="owner"):
        if n not in LEVELS:
            raise CommanderError("level must be 1-4")
        self.store.put("level", n)
        self.audit.log(actor, "level.set", level=n, name=LEVELS[n])
        return {"level": n, "name": LEVELS[n]}

    def _need(self, min_level, what):
        if self.estop():
            raise CommanderError(f"EMERGENCY STOP active: {what} refused")
        if self.level() < min_level:
            raise CommanderError(f"{what} needs level {min_level} ({LEVELS[min_level]}); current level {self.level()} ({LEVELS[self.level()]})")

    def discover(self):
        new = [s["id"] for s in discover_specs() if self.registry.register(s)]
        if new:
            self.bus.send("commander", "owner", "discovery", {"registered": new})
        return new

    def _recover_after_restart(self):
        n = self.store.execute("UPDATE tasks SET state='pending', updated=? WHERE state='running'", (now(),)).rowcount
        if n:
            self.audit.log("commander", "recovery.tasks_requeued", count=n)

    # ---------- agent control ----------
    def _agent(self, aid):
        a = self.registry.get(aid)
        if not a:
            raise CommanderError(f"unknown agent {aid}")
        return a

    def _do_start(self, aid):
        self._need(2, "start agent")
        a = self._agent(aid)
        res = self.adapters.start(a)
        self.audit.log("commander", "agent.start", agent=aid, result=res)
        return res

    def agent_action(self, aid, op, actor="owner"):
        a = self._agent(aid)
        if op == "stop":
            self._need(2, "stop agent")
            res = self.adapters.stop(a)
        elif op == "pause":
            self._need(2, "pause agent")
            self.store.execute("UPDATE agents SET paused=1 WHERE id=?", (aid,))
            res = self.adapters.stop(a, desired="paused")
        elif op in ("start", "resume"):
            self._need(2, f"{op} agent")
            self.store.execute("UPDATE agents SET paused=0, failures=0, breaker_until=0 WHERE id=?", (aid,))
            if a["risk"] in ("live", "unknown"):
                ap = self.approvals.request("start_agent", aid, {"agent": aid, "name": a["name"]}, actor)
                res = {"status": "pending_approval", "approval": ap, "why": "live/unknown-risk agent can open trades"}
            else:
                res = self._do_start(aid)
        else:
            raise CommanderError("op must be start|stop|pause|resume")
        self.audit.log(actor, f"agent.{op}", agent=aid, result=res)
        return res

    def emergency_stop(self, actor="owner"):
        self.store.put("estop", True)
        open(os.path.join(DATA_DIR, "EMERGENCY_STOP"), "w").write(str(now()))
        killed = {}
        for a in self.registry.all():
            if a["kind"] == "process":
                killed[a["id"]] = self.adapters.stop(a)["killed"]
        n = self.store.execute("UPDATE tasks SET state='cancelled', finished=? WHERE state IN ('pending','running','blocked')",
                               (now(),)).rowcount
        self.audit.log(actor, "estop.engaged", killed=killed, tasks_cancelled=n)
        self.bus.send("commander", "*", "emergency_stop", {"by": actor})
        return {"estop": True, "killed": killed, "tasks_cancelled": n}

    def release_estop(self, actor="owner"):
        self.store.put("estop", False)
        try:
            os.remove(os.path.join(DATA_DIR, "EMERGENCY_STOP"))
        except OSError:
            pass
        self.audit.log(actor, "estop.released")
        return {"estop": False}

    # ---------- live-trading gateway ----------
    def request_live_trade(self, aid, order):
        """Validates against hard limits, then queues for explicit owner approval. Never executes directly."""
        if self.estop():
            raise CommanderError("EMERGENCY STOP active")
        if not self.perms.has(aid, "REQUEST_LIVE_TRADES"):
            self.audit.log(aid, "live.denied", reason="no REQUEST_LIVE_TRADES", order=order)
            raise CommanderError("agent lacks REQUEST_LIVE_TRADES")
        self._check_live_limits(order)
        ap = self.approvals.request("live_trade", f"{aid}:{time.time()}", {"agent": aid, "order": order}, aid)
        return {"status": "pending_approval", "approval": ap}

    def _check_live_limits(self, o):
        L = LIVE_LIMITS
        if o.get("symbol") not in L["symbols"]:
            raise CommanderError(f"symbol {o.get('symbol')} not allowed")
        if not 0 < float(o.get("volume", 0)) <= L["max_volume"]:
            raise CommanderError(f"volume must be in (0, {L['max_volume']}]")
        if L["require_sl_tp"] and not (o.get("sl") and o.get("tp")):
            raise CommanderError("stop loss and take profit are mandatory")
        if o.get("action") not in ("BUY", "SELL"):
            raise CommanderError("action must be BUY or SELL")
        if self.positions_fn is not None and self.positions_fn() >= L["max_open_positions"]:
            raise CommanderError("max open positions reached")

    def _execute_live_trade(self, d):
        self._need(2, "execute approved trade")
        if not self.perms.has(d["agent"], "REQUEST_LIVE_TRADES"):
            raise CommanderError("agent's live-trading permission was revoked")
        self._check_live_limits(d["order"])          # re-check at execution time
        if self.live_executor is None:
            return {"executed": False, "reason": "no live executor configured"}
        res = self.live_executor(d["order"])
        self.audit.log("owner", "live.executed", order=d["order"], result=str(res)[:300])
        return {"executed": bool(res.get("ok", res.get("success", False))), "result": res}

    # ---------- objectives / planning ----------
    def _seed_workflows(self):
        for key, steps in DEFAULT_WORKFLOWS.items():
            if not self.store.one("SELECT id FROM workflows WHERE key=?", (key,)):
                self.store.execute("INSERT INTO workflows(key,version,steps,status,ts) VALUES(?,?,?, 'active', ?)",
                                   (key, 1, jd(steps), now()))

    def pick_workflow(self, key):
        rows = self.store.query("SELECT * FROM workflows WHERE key=? AND status IN ('active','candidate') ORDER BY version", (key,))
        active = next(r for r in rows if r["status"] == "active")
        cand = next((r for r in rows if r["status"] == "candidate"), None)
        # A/B: candidate gets every second run until evaluated
        use = cand if cand and (active["runs"] + cand["runs"]) % 2 == 1 else active
        return use

    def plan_objective(self, text, key, level_check=True):
        wf = self.pick_workflow(key)
        steps = jl(wf["steps"], [])
        if self.estop():
            raise CommanderError("EMERGENCY STOP active")
        oid = os.urandom(5).hex()
        self.store.execute("INSERT INTO objectives(id,text,state,plan,workflow,created) VALUES(?,?,?,?,?,?)",
                           (oid, text, "running", jd(steps), jd([key, wf["version"]]), now()))
        for key_, kind, owner, perms, deps in steps:
            self.scheduler.submit({"key": key_, "kind": kind, "owner": owner, "perms": perms, "deps": deps,
                                   "title": f"{kind} ({owner})", "priority": 3 if kind == "agent_report" else 5}, oid)
        self.audit.log("owner", "objective.created", id=oid, text=text[:200], workflow=[key, wf["version"]])
        return oid

    def on_task_finished(self, tid):
        t = self.store.one("SELECT objective FROM tasks WHERE id=?", (tid,))
        if not t or not t["objective"]:
            return
        oid = t["objective"]
        tasks = self.store.query("SELECT * FROM tasks WHERE objective=?", (oid,))
        if any(x["state"] not in TERMINAL for x in tasks):
            return
        obj = self.store.one("SELECT * FROM objectives WHERE id=?", (oid,))
        if obj["state"] != "running":
            return
        ok = all(x["state"] == "done" for x in tasks)
        report = self.render_report(oid)
        self.store.execute("UPDATE objectives SET state=?, report=?, finished=? WHERE id=?",
                           ("done" if ok else "failed", report, now(), oid))
        wf = jl(obj["workflow"], [])
        if wf:
            self.store.execute("UPDATE workflows SET runs=runs+1, successes=successes+? WHERE key=? AND version=?",
                               (int(ok), wf[0], wf[1]))
        self.bus.send("commander", "owner", "objective_report", {"objective": oid, "ok": ok, "report": report})
        self.audit.log("commander", "objective.finished", id=oid, ok=ok)

    def render_report(self, oid):
        lines = []
        for t in self.store.query("SELECT * FROM tasks WHERE objective=? ORDER BY created", (oid,)):
            out = jl(t["output"], {}) or {}
            head = f"[{t['state'].upper()}] {t['kind']} by {t['owner']}"
            if t["state"] != "done":
                lines.append(f"{head}: {t['error']}")
                continue
            k = t["kind"]
            if k == "agent_report":
                lines.append(head)
                for a in out["agents"]:
                    lines.append(f"  - {a['name']} ({a['team']}, {a['risk']}): {a['status']}")
            elif k == "diagnose":
                lines.append(f"{head}: {len(out['findings'])} problem agent(s) of {out['checked']}")
                for f in out["findings"]:
                    lines.append(f"  - {f['agent']} {f['status']} failures={f['failures']} next={f['next_step']}")
                    for e in f["recent_errors"]:
                        lines.append(f"      ! {e[:140]}")
            elif k == "permission_gaps":
                lines.append(f"{head}: {len(out['gaps'])} agent(s) with gaps")
                for g in out["gaps"]:
                    lines.append(f"  - {g['agent']} missing {g['missing']} (grantable now: {g['grantable']})")
            elif k == "team_plan":
                lines.append(head)
                for team, ids in out["teams"].items():
                    lines.append(f"  - {team}: {', '.join(ids)}")
                for d in out["duplicates"]:
                    lines.append(f"  ! duplicate: {d['a']} ~ {d['b']} ({d['similarity']}) {d['advice']}")
                for c in out["conflicts"]:
                    lines.append(f"  ! conflict: {c['issue']}")
            elif k == "rank_strategies":
                lines.append(f"{head} ({out['basis']})")
                for r in out["ranking"][:5]:
                    lines.append(f"  - {r['name']}: robustness {r['robustness_score']} PF {r['profit_factor']} DD {r['max_dd_pct']}% win {r['win_rate']}%")
            elif k == "validate_strategies":
                lines.append(head)
                lines.append(f"  live reference: {out['live_reference']}")
                for v in out["verdicts"][:3]:
                    lines.append(f"  - {v['name']}: {v['verdict']}")
                    for i in v["issues"]:
                        lines.append(f"      * {i}")
            elif k == "trade_summary":
                lines.append(f"{head}: {out['summary']}")
            else:
                lines.append(f"{head}: {str(out)[:200]}")
        return "\n".join(lines)

    # ---------- chat ----------
    INTENTS = [
        (r"emergency|kill all|stop everything", "estop"),
        (r"\blevel\s*([1-4])\b", "level"),
        (r"(develop|backtest|improv\w*).*(strateg)|(strateg).*(develop|backtest)", "strategy_dev"),
        (r"(analy[sz]e|recommend|promising|best|rank|result).*(strateg|bot|trad)", "strategy_review"),
        (r"permission", "permissions"),
        (r"team|organi[sz]e|duplicate", "teams"),
        (r"fail|investigat|problem|broken|unhealthy", "diagnose"),
        (r"check|report|status|activit|what.*doing|list.*agent", "fleet_report"),
    ]

    def chat(self, text, actor="owner", wait=10):
        text = (text or "").strip()[:500]
        self.bus.send(actor, "commander", "chat", {"text": text})
        low = text.lower()
        intent, m = None, None
        for pat, name in self.INTENTS:
            m = re.search(pat, low)
            if m:
                intent = name
                break
        if intent is None:
            return self._reply(text, "I can: report agent status, investigate failures, show permission gaps, organise teams/"
                               "duplicates, rank & validate strategies, plan strategy development, set level N, or emergency stop.")
        if intent == "estop":
            return self._reply(text, f"Emergency stop engaged: {self.emergency_stop(actor)}")
        if intent == "level":
            return self._reply(text, f"Autonomy set: {self.set_level(int(m.group(1)), actor)}")
        if intent in ("strategy_dev",) and self.level() < 2:
            return self._reply(text, f"Strategy development assigns work; that needs level 2+. Current: {LEVELS[self.level()]}. "
                               "I can still do a read-only 'analyze strategies' review.")
        try:
            oid = self.plan_objective(text, intent)
        except CommanderError as e:
            return self._reply(text, f"Refused: {e}")
        if intent == "strategy_dev":
            self.bus.send("commander", "strategy_evolution_agent", "instruction",
                          {"task": "produce a new candidate generation; submit results for out-of-sample validation",
                           "note": "agent is a standalone script and does not poll the bus yet; delivery is advisory"}, None)
        deadline = time.time() + wait
        while time.time() < deadline:
            o = self.store.one("SELECT state, report FROM objectives WHERE id=?", (oid,))
            if o["state"] != "running":
                return self._reply(text, o["report"] or "(no output)", oid, o["state"])
            time.sleep(0.3)
        return self._reply(text, "Plan created and delegated; still running. Watch the Task Control Center.", oid, "running")

    def _reply(self, q, a, oid=None, state=None):
        self.bus.send("commander", "owner", "chat_reply", {"text": a, "objective": oid})
        return {"reply": a, "objective": oid, "state": state}

    # ---------- performance / self-improvement ----------
    def performance(self):
        out = {}
        snap = self.last_health or self.health.snapshot()
        weights = {"Active": 100, "Working": 100, "Idle": 100, "Stopped": 60, "Paused": 40, "Failed": 0}
        for a in self.registry.all():
            m = self.store.query("SELECT ok,duration FROM metrics WHERE agent=? ORDER BY id DESC LIMIT 50", (a["id"],))
            runs = len(m)
            succ = sum(x["ok"] for x in m) / runs if runs else None
            health = weights.get(snap.get(a["id"], {}).get("status", "Stopped"), 60)
            out[a["id"]] = {"runs": runs, "success_rate": succ,
                            "avg_duration": sum(x["duration"] for x in m) / runs if runs else None,
                            "score": round(health if succ is None else 0.6 * succ * 100 + 0.4 * health, 1)}
        return out

    def recommendations(self):
        recs, perf = [], self.performance()
        for aid, p in perf.items():
            if p["runs"] >= 5 and p["success_rate"] < 0.7:
                recs.append({"type": "underperforming", "agent": aid, "detail": f"success {p['success_rate']:.0%} over {p['runs']} tasks; reassign or investigate"})
            if p["avg_duration"] and p["avg_duration"] > 15:
                recs.append({"type": "slow", "agent": aid, "detail": f"avg task {p['avg_duration']:.1f}s"})
        for a in self.registry.all():
            if a["risk"] == "unknown":
                recs.append({"type": "classify", "agent": a["id"], "detail": "auto-discovered, unclassified: set team/risk before granting anything"})
        have = " ".join(a["purpose"].lower() for a in self.registry.all())
        if "slippage" not in have and "cost" not in have:
            recs.append({"type": "new_agent", "agent": None, "detail": "Add a Transaction-Cost Validator agent (spread/slippage/commission stress) - no existing agent owns this"})
        if "walk-forward" not in have and "out-of-sample" not in have.replace("out-of-sample", "out-of-sample"):
            pass
        recs.append({"type": "new_agent", "agent": None, "detail": "Add a Paper-Trading Forward-Test agent so strategies pass a live-data paper period before any live request"})
        return recs

    def propose_workflow_candidate(self, key, extra_step):
        """Level>=3: add a candidate variant of a Commander workflow (affects only Commander plans, not trading code)."""
        self._need(3, "workflow optimisation")
        active = self.store.one("SELECT * FROM workflows WHERE key=? AND status='active'", (key,))
        if self.store.one("SELECT id FROM workflows WHERE key=? AND status='candidate'", (key,)):
            raise CommanderError("a candidate is already under test")
        ver = self.store.one("SELECT MAX(version) v FROM workflows WHERE key=?", (key,))["v"] + 1
        steps = jl(active["steps"], []) + [list(extra_step)]
        self.store.execute("INSERT INTO workflows(key,version,steps,status,note,ts) VALUES(?,?,?,'candidate',?,?)",
                           (key, ver, jd(steps), "added step " + extra_step[0], now()))
        self.audit.log("commander", "workflow.candidate", key=key, version=ver)
        return ver

    def evaluate_workflows(self, min_runs=5):
        """Promote a candidate that is at least as reliable as the active version; otherwise roll it back."""
        done = []
        for c in self.store.query("SELECT * FROM workflows WHERE status='candidate' AND runs>=?", (min_runs,)):
            a = self.store.one("SELECT * FROM workflows WHERE key=? AND status='active'", (c["key"],))
            rate = lambda w: (w["successes"] / w["runs"]) if w["runs"] else 0
            if rate(c) >= rate(a):
                self.store.execute("UPDATE workflows SET status='archived' WHERE id=?", (a["id"],))
                self.store.execute("UPDATE workflows SET status='active' WHERE id=?", (c["id"],))
                done.append((c["key"], c["version"], "promoted"))
            else:
                self.store.execute("UPDATE workflows SET status='rolled_back' WHERE id=?", (c["id"],))
                done.append((c["key"], c["version"], "rolled_back"))
            self.audit.log("commander", f"workflow.{done[-1][2]}", key=c["key"], version=c["version"],
                           cand_rate=rate(c), active_rate=rate(a))
        return done

    # ---------- dashboard snapshot ----------
    def overview(self):
        health = self.last_health or self.health.snapshot()
        ag = self.registry.all()
        perf = self.performance()
        counts = {"total": len(ag), "active": 0, "idle": 0, "failed": 0, "paused": 0, "stopped": 0}
        rows = []
        for a in ag:
            h = health.get(a["id"], {"status": "Stopped"})
            st = h["status"]
            counts["active" if st in ("Active", "Working") else st.lower()] += 1
            cur = self.store.one("SELECT title FROM tasks WHERE owner=? AND state='running'", (a["id"],))
            rows.append({**{k: a[k] for k in ("id", "name", "purpose", "team", "risk", "kind", "perms", "ceiling", "needs", "failures")},
                         "status": st, "last_activity": h.get("last_activity"), "current_task": cur["title"] if cur else None,
                         "pids": h.get("pids", []), "performance": perf[a["id"]]})
        tasks = self.store.query("SELECT id,objective,kind,title,owner,priority,state,deps,attempts,error,created,finished,quality "
                                 "FROM tasks ORDER BY created DESC LIMIT 80")
        for t in tasks:
            t["deps"] = jl(t["deps"], [])
        obj = self.store.one("SELECT text,state FROM objectives ORDER BY created DESC LIMIT 1")
        return {"level": self.level(), "level_name": LEVELS[self.level()], "levels": LEVELS, "estop": self.estop(),
                "counts": counts, "agents": rows, "tasks": tasks, "objective": obj,
                "health": {"scheduler": bool(self.scheduler.thread and self.scheduler.thread.is_alive()),
                           "running_tasks": len(self.scheduler.running)},
                "approvals": self.approvals.list("pending"), "permissions": PERMISSIONS,
                "limits": {**LIVE_LIMITS, "symbols": sorted(LIVE_LIMITS["symbols"])}}

    def versions(self):
        return {"workflows": self.store.query("SELECT key,version,status,runs,successes,note,ts FROM workflows ORDER BY key,version"),
                "files": self.store.query("SELECT ts,path,backup,note FROM file_versions ORDER BY id DESC LIMIT 20")}
