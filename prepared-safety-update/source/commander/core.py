"""Supreme AI Commander core: store, audit, permissions, registry, bus, scheduler, health, quality.

Persistence is SQLite (stdlib, no extra service). The Store is the only thing that would change
to move to PostgreSQL; every other class talks to it through execute()/query().
"""
import json
import os
import shutil
import sqlite3
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

PERMISSIONS = [
    "READ_DATA", "ANALYZE_DATA", "WRITE_FILES", "MODIFY_CODE", "CREATE_AGENTS", "ASSIGN_TASKS",
    "RUN_BACKTESTS", "RUN_TESTS", "ACCESS_DATABASE", "ACCESS_API", "MODIFY_STRATEGIES",
    "DEPLOY_TO_STAGING", "EXECUTE_PAPER_TRADES", "REQUEST_LIVE_TRADES", "ACCESS_EXTERNAL_TOOLS",
]
# Granting these (or ceilings above what the owner set) always needs explicit owner approval.
SENSITIVE_PERMISSIONS = {"REQUEST_LIVE_TRADES"}
LEVELS = {1: "OBSERVER", 2: "SUPERVISOR", 3: "AUTONOMOUS MANAGER", 4: "FULL AUTHORIZED COMMAND"}
# Never writable by any agent task, at any autonomy level.
PROTECTED_FILES = {"config.py", "mt5_connector.py", "trade_safety.py", "execution_gateway.py",
                   "execution_policy.json", "execution_policy.example.json", ".mcp.json", "web_app.py",
                   "main.py", "client.py", "ea_sentinel.py"}

TERMINAL = ("done", "failed", "cancelled")


class CommanderError(Exception):
    pass


def now():
    return time.time()


def jd(v):
    return json.dumps(v, default=str)


def jl(s, default=None):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default


class Store:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, name TEXT, purpose TEXT, kind TEXT, script TEXT,
      team TEXT, risk TEXT, perms TEXT, ceiling TEXT, needs TEXT, desired TEXT DEFAULT 'unknown',
      paused INTEGER DEFAULT 0, failures INTEGER DEFAULT 0, breaker_until REAL DEFAULT 0, meta TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, objective TEXT, key TEXT, kind TEXT, title TEXT,
      owner TEXT, priority INTEGER, state TEXT, perms TEXT, deps TEXT, params TEXT, output TEXT, history TEXT,
      attempts INTEGER DEFAULT 0, max_attempts INTEGER DEFAULT 2, timeout REAL DEFAULT 30, lock TEXT,
      not_before REAL DEFAULT 0, created REAL, updated REAL, started REAL, finished REAL, error TEXT,
      quality TEXT, progress TEXT);
    CREATE TABLE IF NOT EXISTS objectives(id TEXT PRIMARY KEY, text TEXT, state TEXT, plan TEXT, report TEXT,
      workflow TEXT, created REAL, finished REAL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, sender TEXT,
      recipient TEXT, type TEXT, task_id TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, action TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, ts REAL, kind TEXT, subject TEXT, detail TEXT,
      status TEXT, decided_at REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, ok INTEGER,
      duration REAL, quality REAL);
    CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, version INTEGER,
      steps TEXT, status TEXT, runs INTEGER DEFAULT 0, successes INTEGER DEFAULT 0, note TEXT, ts REAL);
    CREATE TABLE IF NOT EXISTS file_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, path TEXT, backup TEXT, note TEXT);
    """

    def __init__(self, path=None):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.path = path or os.path.join(DATA_DIR, "commander.db")
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(self.SCHEMA)
            self.db.commit()

    def execute(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    def query(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.query(sql, args)
        return rows[0] if rows else None

    def get(self, k, default=None):
        r = self.one("SELECT v FROM settings WHERE k=?", (k,))
        return jl(r["v"], default) if r else default

    def put(self, k, v):
        self.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, jd(v)))


class Audit:
    def __init__(self, store):
        self.s = store

    def log(self, actor, action, **detail):
        self.s.execute("INSERT INTO audit(ts,actor,action,detail) VALUES(?,?,?,?)", (now(), actor, action, jd(detail)))

    def recent(self, n=100, action_prefix=None):
        if action_prefix:
            rows = self.s.query("SELECT * FROM audit WHERE action LIKE ? ORDER BY id DESC LIMIT ?", (action_prefix + "%", n))
        else:
            rows = self.s.query("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (n,))
        for r in rows:
            r["detail"] = jl(r["detail"], {})
        return rows


class Bus:
    """Structured, persisted message bus. Every message is stored; consumers read by id cursor."""

    def __init__(self, store):
        self.s = store

    def send(self, sender, recipient, mtype, body, task_id=None):
        cur = self.s.execute("INSERT INTO messages(ts,sender,recipient,type,task_id,body) VALUES(?,?,?,?,?,?)",
                             (now(), sender, recipient, mtype, task_id, jd(body)))
        return cur.lastrowid

    def since(self, last_id=0, limit=200, recipient=None):
        q, a = "SELECT * FROM messages WHERE id>?", [last_id]
        if recipient:
            q += " AND (recipient=? OR recipient='*')"
            a.append(recipient)
        rows = self.s.query(q + " ORDER BY id ASC LIMIT ?", a + [limit])
        for r in rows:
            r["body"] = jl(r["body"], {})
        return rows


class Permissions:
    def __init__(self, store, audit, approvals):
        self.s, self.a, self.ap = store, audit, approvals

    def _agent(self, agent_id):
        r = self.s.one("SELECT perms, ceiling FROM agents WHERE id=?", (agent_id,))
        if not r:
            raise CommanderError(f"unknown agent {agent_id}")
        return set(jl(r["perms"], [])), set(jl(r["ceiling"], []))

    def has(self, agent_id, perm):
        return perm in self._agent(agent_id)[0]

    def missing(self, agent_id, perms):
        have = self._agent(agent_id)[0]
        return [p for p in perms if p not in have]

    def grant(self, agent_id, perm, actor="commander", approved=False):
        if perm not in PERMISSIONS:
            raise CommanderError(f"unknown permission {perm}")
        have, ceiling = self._agent(agent_id)
        if perm in have:
            return {"status": "already_granted"}
        if perm not in ceiling:
            self.a.log(actor, "permission.denied", agent=agent_id, perm=perm, reason="above owner ceiling")
            return {"status": "denied", "reason": "above owner-defined ceiling; owner must raise ceiling"}
        if perm in SENSITIVE_PERMISSIONS and not approved:
            aid = self.ap.request("grant_permission", f"{agent_id}:{perm}", {"agent": agent_id, "perm": perm}, actor)
            return {"status": "pending_approval", "approval": aid}
        have.add(perm)
        self.s.execute("UPDATE agents SET perms=? WHERE id=?", (jd(sorted(have)), agent_id))
        self.a.log(actor, "permission.grant", agent=agent_id, perm=perm, approved=approved)
        return {"status": "granted"}

    def revoke(self, agent_id, perm, actor="commander"):
        have, _ = self._agent(agent_id)
        have.discard(perm)
        self.s.execute("UPDATE agents SET perms=? WHERE id=?", (jd(sorted(have)), agent_id))
        self.a.log(actor, "permission.revoke", agent=agent_id, perm=perm)
        return {"status": "revoked"}

    def set_ceiling(self, agent_id, perms, actor="owner"):
        """Owner-only: the maximum the Commander may ever grant this agent."""
        perms = [p for p in perms if p in PERMISSIONS]
        have, _ = self._agent(agent_id)
        self.s.execute("UPDATE agents SET ceiling=?, perms=? WHERE id=?",
                       (jd(sorted(perms)), jd(sorted(have & set(perms))), agent_id))
        self.a.log(actor, "permission.ceiling", agent=agent_id, ceiling=sorted(perms))


class Approvals:
    def __init__(self, store, audit, bus):
        self.s, self.a, self.bus = store, audit, bus
        self.handlers = {}

    def request(self, kind, subject, detail, actor):
        existing = self.s.one("SELECT id FROM approvals WHERE kind=? AND subject=? AND status='pending'", (kind, subject))
        if existing:
            return existing["id"]
        aid = uuid.uuid4().hex[:10]
        self.s.execute("INSERT INTO approvals(id,ts,kind,subject,detail,status) VALUES(?,?,?,?,?,'pending')",
                       (aid, now(), kind, subject, jd(detail)))
        self.a.log(actor, "approval.requested", id=aid, kind=kind, subject=subject)
        self.bus.send(actor, "owner", "approval_request", {"id": aid, "kind": kind, "subject": subject})
        return aid

    def list(self, status=None):
        rows = self.s.query("SELECT * FROM approvals " + ("WHERE status=? " if status else "") + "ORDER BY ts DESC LIMIT 100",
                            (status,) if status else ())
        for r in rows:
            r["detail"] = jl(r["detail"], {})
        return rows

    def decide(self, aid, approve, note=""):
        r = self.s.one("SELECT * FROM approvals WHERE id=?", (aid,))
        if not r or r["status"] != "pending":
            raise CommanderError("approval not found or already decided")
        status = "approved" if approve else "rejected"
        claimed = self.s.execute("UPDATE approvals SET status=?, decided_at=?, note=? WHERE id=? AND status='pending'",
                                 (status, now(), note, aid)).rowcount
        if claimed != 1:
            raise CommanderError("approval already decided")
        self.a.log("owner", f"approval.{status}", id=aid, kind=r["kind"], subject=r["subject"])
        result = None
        if approve and r["kind"] in self.handlers:
            result = self.handlers[r["kind"]](jl(r["detail"], {}))
        return {"status": status, "result": result}


class Registry:
    def __init__(self, store, audit):
        self.s, self.a = store, audit

    def register(self, spec):
        """Upsert by id. Existing perms/ceiling/desired state are kept; only descriptive fields refresh."""
        old = self.s.one("SELECT * FROM agents WHERE id=?", (spec["id"],))
        if old:
            self.s.execute("UPDATE agents SET name=?, purpose=?, kind=?, script=?, team=?, risk=?, needs=?, meta=? WHERE id=?",
                           (spec["name"], spec["purpose"], spec["kind"], spec.get("script"), spec["team"], spec["risk"],
                            jd(spec.get("needs", [])), jd(spec.get("meta", {})), spec["id"]))
            return False
        perms = spec.get("perms", [])
        self.s.execute("INSERT INTO agents(id,name,purpose,kind,script,team,risk,perms,ceiling,needs,desired,meta) "
                       "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (spec["id"], spec["name"], spec["purpose"], spec["kind"], spec.get("script"), spec["team"],
                        spec["risk"], jd(sorted(perms)), jd(sorted(spec.get("ceiling", perms))),
                        jd(spec.get("needs", [])), "unknown", jd(spec.get("meta", {}))))
        self.a.log("commander", "agent.registered", agent=spec["id"], kind=spec["kind"], risk=spec["risk"])
        return True

    def all(self):
        rows = self.s.query("SELECT * FROM agents ORDER BY team, name")
        for r in rows:
            for f in ("perms", "ceiling", "needs", "meta"):
                r[f] = jl(r[f], [] if f != "meta" else {})
        return rows

    def get(self, agent_id):
        return next((r for r in self.all() if r["id"] == agent_id), None)


class Quality:
    """Verifies task output against per-kind contracts. Never trusts the producing agent's own claim."""
    REQUIRED = {
        "agent_report": ["agents"], "diagnose": ["findings"], "permission_gaps": ["gaps"],
        "team_plan": ["teams"], "rank_strategies": ["ranking"], "validate_strategies": ["verdicts"],
        "trade_summary": ["summary"], "status": ["alive"], "tail_log": ["lines"], "read_state": ["state"],
        "backtest_review": ["review"],
    }

    def evaluate(self, task, output):
        if not isinstance(output, dict):
            return {"score": 0.0, "ok": False, "issues": ["output is not a structured object"]}
        issues = [f"missing field '{k}'" for k in self.REQUIRED.get(task["kind"], []) if k not in output]
        if output.get("error"):
            issues.append(f"agent reported error: {output['error']}")
        return {"score": max(0.0, 1.0 - 0.5 * len(issues)), "ok": not issues, "issues": issues}


class Scheduler:
    """Dependency-aware task scheduler. One running task per agent and per lock; retry with backoff;
    timeout; circuit breaker pauses an agent after repeated failures."""

    BREAKER_FAILS = 3
    BREAKER_SECS = 300

    def __init__(self, cmd):
        self.c = cmd
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="cmdr-task")
        self.running = {}
        self._stop = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._loop, daemon=True, name="cmdr-scheduler")
        self.thread.start()

    def stop(self):
        self._stop.set()

    def submit(self, spec, objective=None):
        s = self.c.store
        dup = s.one("SELECT id FROM tasks WHERE owner=? AND kind=? AND params=? AND state IN ('pending','running','blocked')",
                    (spec["owner"], spec["kind"], jd(spec.get("params", {}))))
        if dup:
            self.c.audit.log("commander", "task.duplicate_suppressed", existing=dup["id"], kind=spec["kind"])
            return dup["id"]
        agent = self.c.registry.get(spec["owner"])
        if not agent:
            raise CommanderError(f"unknown owner {spec['owner']}")
        tid = uuid.uuid4().hex[:10]
        s.execute("INSERT INTO tasks(id,objective,key,kind,title,owner,priority,state,perms,deps,params,history,max_attempts,"
                  "timeout,lock,created,updated) VALUES(?,?,?,?,?,?,?,'pending',?,?,?,?,?,?,?,?,?)",
                  (tid, objective, spec.get("key"), spec["kind"], spec.get("title", spec["kind"]), spec["owner"],
                   spec.get("priority", 5), jd(spec.get("perms", [])), jd(spec.get("deps", [])),
                   jd(spec.get("params", {})), jd([[now(), "created"]]), spec.get("max_attempts", 2),
                   spec.get("timeout", 30), spec.get("lock"), now(), now()))
        self.c.bus.send("commander", spec["owner"], "task_assigned",
                        {"objective": spec.get("title", spec["kind"]), "tools": [spec["kind"]],
                         "permissions": spec.get("perms", []), "deadline_s": spec.get("timeout", 30),
                         "expected_output": Quality.REQUIRED.get(spec["kind"], [])}, tid)
        self.c.audit.log("commander", "task.created", task=tid, owner=spec["owner"], kind=spec["kind"])
        return tid

    def set_state(self, tid, state, **fields):
        t = self.c.store.one("SELECT history FROM tasks WHERE id=?", (tid,))
        hist = jl(t["history"], []) if t else []
        hist.append([now(), state, fields.get("error") or ""])
        cols = {"state": state, "updated": now(), "history": jd(hist[-30:])}
        for k, v in fields.items():
            cols[k] = jd(v) if isinstance(v, (dict, list)) else v
        self.c.store.execute(f"UPDATE tasks SET {','.join(k + '=?' for k in cols)} WHERE id=?", (*cols.values(), tid))

    def cancel(self, tid):
        t = self.c.store.one("SELECT state FROM tasks WHERE id=?", (tid,))
        if not t or t["state"] in TERMINAL:
            raise CommanderError("task not cancellable")
        self.set_state(tid, "cancelled", finished=now())
        self.c.audit.log("owner", "task.cancelled", task=tid)

    def reassign(self, tid, new_owner):
        t = self.c.store.one("SELECT * FROM tasks WHERE id=?", (tid,))
        if not t or t["state"] == "running":
            raise CommanderError("task missing or running")
        missing = self.c.perms.missing(new_owner, jl(t["perms"], []))
        if missing:
            raise CommanderError(f"{new_owner} lacks permissions {missing}")
        self.c.store.execute("UPDATE tasks SET owner=?, state='pending', attempts=0, error=NULL, updated=? WHERE id=?",
                             (new_owner, now(), tid))
        self.c.audit.log("commander", "task.reassigned", task=tid, to=new_owner)

    def _ready(self):
        s = self.c.store
        busy_agents = {self.running[k]["owner"] for k in self.running}
        busy_locks = {self.running[k]["lock"] for k in self.running if self.running[k]["lock"]}
        for t in s.query("SELECT * FROM tasks WHERE state IN ('pending','blocked') AND not_before<=? "
                         "ORDER BY priority ASC, created ASC", (now(),)):
            deps = jl(t["deps"], [])
            states = [s.one("SELECT state FROM tasks WHERE objective=? AND key=?", (t["objective"], d)) for d in deps]
            if any(x and x["state"] in ("failed", "cancelled") for x in states):
                self.set_state(t["id"], "failed", error="dependency failed", finished=now())
                continue
            if any(not x or x["state"] != "done" for x in states):
                continue
            if t["owner"] in busy_agents or (t["lock"] and t["lock"] in busy_locks):
                continue
            # OBSERVER may only run read-only analysis; anything else waits for a higher level
            if self.c.level() < 2 and set(jl(t["perms"], [])) - {"READ_DATA", "ANALYZE_DATA"}:
                continue
            yield t

    def _loop(self):
        while not self._stop.is_set():
            try:
                if self.c.estop():
                    time.sleep(0.5)
                    continue
                for t in list(self._ready()):
                    if len(self.running) >= 6 or t["owner"] in {r["owner"] for r in self.running.values()}:
                        continue
                    if t["lock"] and t["lock"] in {r["lock"] for r in self.running.values()}:
                        continue
                    self._launch(t)
            except Exception:
                self.c.audit.log("commander", "scheduler.error", trace=traceback.format_exc()[-500:])
            time.sleep(0.4)

    def run_pending_sync(self, max_rounds=50):
        """Test helper: run ready tasks to completion without the background thread."""
        for _ in range(max_rounds):
            ready = list(self._ready())
            if not ready and not self.running:
                return
            for t in ready:
                if t["owner"] not in {r["owner"] for r in self.running.values()}:
                    self._launch(t)
            time.sleep(0.05)

    def _launch(self, t):
        agent = self.c.registry.get(t["owner"])
        missing = self.c.perms.missing(t["owner"], jl(t["perms"], []))
        if missing:
            self.set_state(t["id"], "failed", error=f"permission denied: {missing}", finished=now())
            self.c.audit.log("commander", "task.permission_denied", task=t["id"], missing=missing)
            return
        if agent["paused"] or agent["breaker_until"] > now():
            self.set_state(t["id"], "blocked", error="agent paused / circuit open")
            return
        self.running[t["id"]] = {"owner": t["owner"], "lock": t["lock"]}
        self.set_state(t["id"], "running", started=now(), attempts=t["attempts"] + 1)
        self.pool.submit(self._run, t, agent)

    def _run(self, t, agent):
        t0, ok, out, err = now(), False, None, None
        try:
            dep_out = {}
            for d in jl(t["deps"], []):
                r = self.c.store.one("SELECT output FROM tasks WHERE objective=? AND key=?", (t["objective"], d))
                dep_out[d] = jl(r["output"], {}) if r else {}
            fut = self.c.exec_pool.submit(self.c.adapters.execute, agent, t, dep_out)
            out = fut.result(timeout=t["timeout"])
            q = self.c.quality.evaluate(t, out)
            ok = q["ok"]
            if not ok:
                err = "quality check failed: " + "; ".join(q["issues"])
            self.c.store.execute("UPDATE tasks SET quality=? WHERE id=?", (jd(q), t["id"]))
        except FutTimeout:
            err = f"timeout after {t['timeout']}s"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        dur = now() - t0
        self.c.store.execute("INSERT INTO metrics(ts,agent,ok,duration,quality) VALUES(?,?,?,?,?)",
                             (now(), t["owner"], int(ok), dur, 1.0 if ok else 0.0))
        if ok:
            self.set_state(t["id"], "done", output=out, finished=now(), error=None)
            self.c.store.execute("UPDATE agents SET failures=0 WHERE id=?", (t["owner"],))
            self.c.bus.send(t["owner"], "commander", "task_result", {"summary": str(out)[:300]}, t["id"])
        else:
            self.c.bus.send(t["owner"], "commander", "error_report", {"error": err, "attempt": t["attempts"] + 1}, t["id"])
            fails = (agent["failures"] or 0) + 1
            self.c.store.execute("UPDATE agents SET failures=? WHERE id=?", (fails, t["owner"]))
            if t["attempts"] + 1 < t["max_attempts"]:
                self.c.bus.send("commander", t["owner"], "correction_request", {"reason": err}, t["id"])
                self.set_state(t["id"], "pending", error=err, not_before=now() + 2 ** (t["attempts"] + 1))
            else:
                self.set_state(t["id"], "failed", error=err, finished=now())
            if fails >= self.BREAKER_FAILS:
                self.c.store.execute("UPDATE agents SET breaker_until=?, paused=1 WHERE id=?",
                                     (now() + self.BREAKER_SECS, t["owner"]))
                self.c.audit.log("commander", "circuit.open", agent=t["owner"], failures=fails)
                self.c.bus.send("commander", "owner", "escalation",
                                {"agent": t["owner"], "reason": f"{fails} consecutive failures; agent paused"})
        self.running.pop(t["id"], None)
        self.c.on_task_finished(t["id"])


class Health:
    """Polls adapters for liveness, derives status, runs controlled recovery (level >= 3, non-live only)."""
    RESTARTS_PER_HOUR = 3

    def __init__(self, cmd):
        self.c = cmd
        self._stop = threading.Event()
        self.restarts = {}

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="cmdr-health").start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                self.c.audit.log("commander", "health.error", trace=traceback.format_exc()[-500:])
            self._stop.wait(10)

    def snapshot(self):
        """status per agent id: Active | Working | Idle | Paused | Failed | Stopped"""
        out = {}
        procs = self.c.adapters.process_table()
        working = {r["owner"] for r in self.c.scheduler.running.values()}
        for a in self.c.registry.all():
            info = self.c.adapters.probe(a, procs)
            if a["paused"] or a["breaker_until"] > now():
                st = "Paused"
            elif a["id"] in working:
                st = "Working"
            elif a["kind"] == "internal":
                st = "Idle"
            elif info["alive"]:
                st = "Active"
            elif a["desired"] == "running":
                st = "Failed"
            else:
                st = "Stopped"
            out[a["id"]] = {"status": st, **info}
        return out

    def tick(self):
        snap = self.snapshot()
        self.c.last_health = snap
        for a in self.c.registry.all():
            info = snap[a["id"]]
            if a["kind"] == "process" and info["status"] == "Active" and a["desired"] != "running":
                self.c.store.execute("UPDATE agents SET desired='running' WHERE id=?", (a["id"],))
            if info["status"] == "Failed":
                self._recover(a)

    def _recover(self, a):
        if self.c.estop() or self.c.level() < 3:
            return
        if a["risk"] not in ("research", "safety"):
            self.c.bus.send("commander", "owner", "escalation",
                            {"agent": a["id"], "reason": "live-trading agent down; never auto-restarted"})
            return
        hist = [t for t in self.restarts.get(a["id"], []) if t > now() - 3600]
        if len(hist) >= self.RESTARTS_PER_HOUR:
            self.c.store.execute("UPDATE agents SET paused=1, desired='stopped' WHERE id=?", (a["id"],))
            self.c.audit.log("commander", "recovery.gave_up", agent=a["id"])
            self.c.bus.send("commander", "owner", "escalation",
                            {"agent": a["id"], "reason": f"{len(hist)} restarts in 1h; paused for investigation"})
            return
        hist.append(now())
        self.restarts[a["id"]] = hist
        res = self.c.adapters.start(a)
        self.c.audit.log("commander", "recovery.restart", agent=a["id"], result=res)


def backup_file(store, path, note=""):
    os.makedirs(os.path.join(DATA_DIR, "backups"), exist_ok=True)
    dst = os.path.join(DATA_DIR, "backups", f"{int(now())}_{os.path.basename(path)}")
    shutil.copy2(path, dst)
    store.execute("INSERT INTO file_versions(ts,path,backup,note) VALUES(?,?,?,?)", (now(), path, dst, note))
    return dst


def safe_write(store, rel_path, content, note=""):
    """The only sanctioned write path for agents: refuses protected files and escapes, backs up first."""
    full = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    if not full.startswith(BASE_DIR + os.sep):
        raise CommanderError("path outside project")
    if os.path.basename(full) in PROTECTED_FILES or os.sep + "commander" + os.sep in full:
        raise CommanderError(f"{rel_path} is protected")
    if os.path.exists(full):
        backup_file(store, full, note)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return full


def rollback_file(store, path):
    row = store.one("SELECT * FROM file_versions WHERE path=? ORDER BY id DESC LIMIT 1", (os.path.abspath(path),))
    if not row:
        raise CommanderError("no backup for file")
    shutil.copy2(row["backup"], row["path"])
    return row["backup"]
