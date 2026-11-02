"""Agent discovery, adapters (process + in-process workers) and the analysis workers.

Adapters are the only place that knows how an agent is run. A new agent type = a new adapter branch
(or a registered spec with kind='internal' and a handler in WORKERS).
"""
import difflib
import glob
import json
import os
import subprocess
import sys
import threading
import time

from .core import BASE_DIR, CommanderError, now

LOG_DIR = os.path.join(BASE_DIR, "logs")
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

# Known scripts. Anything else matching the discovery globs is registered generically as risk 'unknown'
# (treated like live for approvals: unknown code that may trade is never auto-started).
CATALOG = {
    "agent_news_sentinel.py": ("News Sentinel", "Watches news/economic calendar; freezes entries around high-impact events.", "Intelligence", "research", "news_sentinel.log", None),
    "agent_cro_risk.py": ("CRO Risk Officer", "Spread, margin and drawdown watchdog; dynamic lot sizing; aggregate exposure cap.", "Risk", "safety", "cro_risk.log", "cro_risk_state.json"),
    "agent_smc_liquidity.py": ("SMC Liquidity", "Smart-money liquidity/structure levels for gold.", "Intelligence", "research", "smc_liquidity.log", "smc_levels.json"),
    "agent_macro_correlation.py": ("Macro Correlation", "Inter-market (DXY/yields) confluence for gold.", "Intelligence", "research", "macro_correlation.log", "macro_confluence.json"),
    "agent_critic_auditor.py": ("Critic Auditor", "Post-mortem of losing trades; writes penalty rules.", "Quality", "research", "critic_auditor.log", "critic_rules.json"),
    "strategy_evolution_agent.py": ("Darwin Evolution", "Genetic strategy search/backtests; ranks candidate strategies.", "Research", "research", "evolution_journal.log", "strategy_leaderboard.json"),
    "live_pattern_learner.py": ("Live Pattern Learner", "Learns market regime parameters from live data.", "Research", "research", None, "live_learning_state.json"),
    "xto_watchdog.py": ("XTO Watchdog", "Restarts/monitors the XTO trading processes.", "Safety", "live", None, None),
    "quant_desk_orchestrator.py": ("Legacy Quant Desk Orchestrator", "Older supervisor that launches the 7 desk agents INCLUDING live bots.", "Execution", "live", None, None),
    "run_dual_xto_traders.py": ("Dual Bot Supervisor", "Runs bot slots 1 and 2 (live).", "Execution", "live", "dual_traders.log", None),
    "crt_gold_pro.py": ("CRT Gold Pro", "Candle Range Theory + MQL5 Synchronized Indicator, magic 9090.", "Execution", "live", "crt_gold_pro.log", None),
    "dark_horizon_bot.py": ("XAU Dark Horizon Scalp AI", "Live 6-Matrix Telemetry Decision Engine, magic 1010.", "Execution", "live", "dark_horizon_bot.log", None),
    "bot_slot_1.py": ("Apex-Quantum-DeepSL (Bot Slot 1)", "Live Deep-SL Momentum Grid, magic 1111 (96.7% WR, PF 3.65).", "Execution", "live", "bot1_magic1111.log", None),
    "bot_slot_2.py": ("Mut-8037 Adaptive (Bot Slot 2)", "Live Dynamic ATR Grid, magic 2222 (96.6% WR, PF 3.57).", "Execution", "live", "bot2_magic2222.log", None),
    "smc_breaker_sniper.py": ("SMC Breaker Sniper", "Live Institutional Turtle Soup & Liquidity Sweep, magic 3333.", "Execution", "live", "smc_sniper.log", None),
    "pattern_pro_bot.py": ("Strategic Pattern Pro (Optimized)", "Live Asymmetric Box Breakout with Waterfall Freeze, magic 4444 (93.25% WR).", "Execution", "live", "pattern_pro.log", None),
    "tiktalk_bot.py": ("TikTalk Bot", "Live 9/21 EMA Cross + RSI 14 Dip Scalper, magic 5555.", "Execution", "live", "tiktalk.log", None),
    "gold_auto_trader.py": ("Gold Auto Trader", "Live Gold Auto Trader with Smart Chaser, magic 7777.", "Execution", "live", "gold_auto.log", None),
    "ml_trading_engine.py": ("ML Intelligence Engine", "Live Machine Learning 24-feature Trade Setup Engine, magic 8888.", "Execution", "live", "ml_engine.log", None),
    "backtest_ma44_332.py": ("Academic MA 44/332 Bot", "Dual Moving Average Academic System, magic 6666.", "Execution", "live", "ma44_332.log", None),
    "xto_speeder_trader.py": ("XTO Speeder", "Live XTO speeder trader.", "Execution", "live", None, None),
    "xto_apex_quantum.py": ("XTO Apex Quantum", "Live Apex Quantum trader.", "Execution", "live", "apex_quantum.log", None),
    "xto_100_challenge.py": ("XTO 100 Challenge", "Live $100 challenge trader.", "Execution", "live", None, "challenge_100_state.json"),
    "structure_grid_trader.py": ("Structure Grid Trader", "Live HH/LL structure grid trader.", "Execution", "live", None, None),
}
DISCOVERY_GLOBS = ["agent_*.py", "bot_slot_*.py", "xto_*.py", "*_trader.py", "*_agent.py", "*_bot.py", "*_sniper.py"]
NON_AGENT = {"xto_upgrade_atr.py", "xto_upgrade_golden.py", "xto_upgrade_reversal.py"}  # patch scripts / library

NEEDS_BY_RISK = {
    "research": ["READ_DATA", "ANALYZE_DATA"],
    "safety": ["READ_DATA", "ANALYZE_DATA"],
    "live": ["READ_DATA"],
    "unknown": ["READ_DATA"],
}
CEILING_BY_RISK = {
    "research": ["READ_DATA", "ANALYZE_DATA", "ACCESS_API", "RUN_BACKTESTS", "RUN_TESTS", "WRITE_FILES"],
    "safety": ["READ_DATA", "ANALYZE_DATA", "ACCESS_API"],
    "live": ["READ_DATA", "ANALYZE_DATA", "EXECUTE_PAPER_TRADES", "REQUEST_LIVE_TRADES"],
    "unknown": ["READ_DATA"],
}

INTERNAL = [
    {"id": "ops", "name": "Ops Reporter", "purpose": "Collects fleet status, diagnoses failures, plans teams and permission gaps.",
     "team": "Commander Staff", "perms": ["READ_DATA", "ANALYZE_DATA", "ASSIGN_TASKS"]},
    {"id": "analyst", "name": "Trading Analyst", "purpose": "Ranks strategies and summarises trade results from stored data.",
     "team": "Commander Staff", "perms": ["READ_DATA", "ANALYZE_DATA", "RUN_BACKTESTS"]},
    {"id": "auditor", "name": "Validation Auditor", "purpose": "Independently challenges strategy claims (out-of-sample, costs, tail risk).",
     "team": "Commander Staff", "perms": ["READ_DATA", "ANALYZE_DATA", "RUN_TESTS"]},
]


def _read_json(name):
    try:
        with open(os.path.join(BASE_DIR, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def discover_specs():
    specs, seen = [], set()
    known = [os.path.join(BASE_DIR, f) for f in CATALOG if os.path.exists(os.path.join(BASE_DIR, f))]
    for path in known + [p for g in DISCOVERY_GLOBS for p in sorted(glob.glob(os.path.join(BASE_DIR, g)))]:
        fn = os.path.basename(path)
        if fn in seen or fn in NON_AGENT:
            continue
        seen.add(fn)
        name, purpose, team, risk, log, state = CATALOG.get(
            fn, (fn[:-3].replace("_", " ").title(), "Auto-discovered script (not in catalog).", "Unassigned", "unknown", None, None))
        specs.append({"id": fn[:-3], "name": name, "purpose": purpose, "kind": "process", "script": fn, "team": team,
                      "risk": risk, "perms": NEEDS_BY_RISK[risk], "ceiling": CEILING_BY_RISK[risk],
                      "needs": NEEDS_BY_RISK[risk], "meta": {"log": log, "state": state}})
    for a in INTERNAL:
        specs.append({**a, "kind": "internal", "script": None, "risk": "internal", "needs": a["perms"],
                      "ceiling": a["perms"], "meta": {}})
    return specs


class Adapters:
    def __init__(self, cmd):
        self.c = cmd
        self._ptab, self._ptab_ts = {}, 0
        self._lock = threading.Lock()
        self.popen = {}

    # ---- process table (no psutil dependency) ----
    def process_table(self):
        with self._lock:
            if now() - self._ptab_ts < 5:
                return self._ptab
            tab = {}
            try:
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                     "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=15).stdout.strip()
                rows = json.loads(out) if out else []
                rows = [rows] if isinstance(rows, dict) else rows
                for r in rows:
                    cl = r.get("CommandLine") or ""
                    if r["ProcessId"] != os.getpid():
                        tab[r["ProcessId"]] = cl
            except Exception:
                pass
            self._ptab, self._ptab_ts = tab, now()
            return tab

    def probe(self, a, procs=None):
        if a["kind"] == "internal":
            return {"alive": True, "pids": [], "last_activity": now(), "log": None}
        procs = self.process_table() if procs is None else procs
        pids = [p for p, cl in procs.items() if a["script"] in cl and "commander" not in cl]
        newest = 0
        for rel in (a["meta"].get("log") and os.path.join("logs", a["meta"]["log"]), a["meta"].get("state")):
            if rel:
                try:
                    newest = max(newest, os.path.getmtime(os.path.join(BASE_DIR, rel)))
                except OSError:
                    pass
        return {"alive": bool(pids), "pids": pids, "last_activity": newest or None, "log": a["meta"].get("log")}

    # ---- lifecycle ----
    def start(self, a):
        if a["kind"] != "process":
            return {"ok": True, "note": "internal agent"}
        if self.probe(a)["alive"]:
            self.c.store.execute("UPDATE agents SET desired='running', paused=0 WHERE id=?", (a["id"],))
            return {"ok": True, "note": "already running"}
        os.makedirs(LOG_DIR, exist_ok=True)
        log = open(os.path.join(LOG_DIR, f"commander_{a['id']}.out"), "ab")
        p = subprocess.Popen([sys.executable, a["script"]], cwd=BASE_DIR, stdout=log, stderr=log,
                             creationflags=DETACHED if os.name == "nt" else 0)
        self.popen[a["id"]] = p
        self._ptab_ts = 0
        self.c.store.execute("UPDATE agents SET desired='running', paused=0, failures=0, breaker_until=0 WHERE id=?", (a["id"],))
        return {"ok": True, "pid": p.pid}

    def stop(self, a, desired="stopped"):
        if a["kind"] != "process":
            return {"ok": True, "note": "internal agent"}
        killed = []
        for pid in self.probe(a)["pids"]:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            killed.append(pid)
        self._ptab_ts = 0
        self.c.store.execute("UPDATE agents SET desired=? WHERE id=?", (desired, a["id"]))
        return {"ok": True, "killed": killed}

    # ---- task execution ----
    def execute(self, a, task, dep_out):
        kind, params = task["kind"], json.loads(task["params"] or "{}")
        if a["kind"] == "internal":
            fn = WORKERS.get(kind)
            if not fn:
                raise CommanderError(f"{a['id']} cannot do '{kind}'")
            return fn(self.c, params, dep_out)
        if kind == "status":
            return {**self.probe(a), "alive": self.probe(a)["alive"]}
        if kind == "tail_log":
            return tail_log(a, params.get("n", 20))
        if kind == "read_state":
            st = a["meta"].get("state")
            return {"state": _read_json(st) if st else None, "file": st}
        raise CommanderError(f"process agent {a['id']} has no handler for '{kind}'; message it via the bus instead")


def tail_log(a, n=20):
    lines = []
    for rel in (a["meta"].get("log") and os.path.join(LOG_DIR, a["meta"]["log"]),
                os.path.join(LOG_DIR, f"commander_{a['id']}.out")):
        if rel and os.path.exists(rel):
            with open(rel, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 8000))
                lines = f.read().decode("utf-8", "replace").splitlines()[-n:]
            break
    return {"lines": lines, "log": a["meta"].get("log")}


# ----------------------------- workers (internal agents) -----------------------------

def w_agent_report(c, params, dep):
    snap = c.health.snapshot()
    rows = []
    for a in c.registry.all():
        s = snap[a["id"]]
        rows.append({"id": a["id"], "name": a["name"], "team": a["team"], "risk": a["risk"], "status": s["status"],
                     "last_activity": s["last_activity"], "pids": s["pids"]})
    return {"agents": rows}


def w_diagnose(c, params, dep):
    snap, findings = c.health.snapshot(), []
    for a in c.registry.all():
        s = snap[a["id"]]
        if s["status"] in ("Failed", "Paused"):
            tl = tail_log(a, 15)["lines"] if a["kind"] == "process" else []
            errs = [l for l in tl if any(w in l.lower() for w in ("error", "traceback", "exception", "failed"))]
            findings.append({"agent": a["id"], "status": s["status"], "failures": a["failures"],
                             "recent_errors": errs[-5:], "log_tail": tl[-5:],
                             "next_step": "owner review" if a["risk"] == "live" else "controlled restart at level>=3"})
    return {"findings": findings, "checked": len(snap)}


def w_permission_gaps(c, params, dep):
    gaps = []
    for a in c.registry.all():
        miss = [p for p in a["needs"] if p not in a["perms"]]
        if miss:
            gaps.append({"agent": a["id"], "missing": miss,
                         "grantable": [p for p in miss if p in a["ceiling"]]})
    return {"gaps": gaps}


def w_team_plan(c, params, dep):
    teams, scripts = {}, {}
    for a in c.registry.all():
        teams.setdefault(a["team"], []).append(a["id"])
        if a["script"]:
            try:
                with open(os.path.join(BASE_DIR, a["script"]), "r", encoding="utf-8", errors="replace") as f:
                    scripts[a["id"]] = f.read()
            except OSError:
                pass
    dupes, ids = [], list(scripts)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            r = difflib.SequenceMatcher(None, scripts[ids[i]], scripts[ids[j]], autojunk=False).quick_ratio()
            if r > 0.9 and difflib.SequenceMatcher(None, scripts[ids[i]], scripts[ids[j]], autojunk=False).ratio() > 0.85:
                dupes.append({"a": ids[i], "b": ids[j], "similarity": round(r, 2),
                              "advice": "same template, different params: run as one parameterised agent; keep distinct magic numbers"})
    return {"teams": teams, "duplicates": dupes,
            "conflicts": [{"issue": "multiple live bots + legacy orchestrator can all open positions on XAUUSD",
                           "advice": "CLAUDE.md policy is max 1 open position; only the CRO caps aggregate lots. Route live entries through the gateway."}]}


def _ranked_strategies():
    lb = _read_json("strategy_leaderboard.json") or {}
    return lb.get("top_strategies", [])


def w_rank_strategies(c, params, dep):
    rows = []
    for s in _ranked_strategies():
        d = s.get("dna", {})
        pf, dd = s.get("profit_factor", 0), s.get("max_dd_pct", 100)
        tail_ratio = (s.get("net_profit", 0) / max(1.0, s.get("disaster_stops", 0) * d.get("disaster_sl", 0))) if d.get("disaster_sl") else None
        # robustness: reward profit factor, punish drawdown, punish tail risk; ignore raw win rate and 'fitness'
        score = round(pf * 40 - dd * 1.5 + (min(tail_ratio, 3) * 10 if tail_ratio else 0), 1)
        rows.append({"name": d.get("name"), "net_profit": s.get("net_profit"), "win_rate": s.get("win_rate"),
                     "profit_factor": pf, "max_dd_pct": dd, "disaster_stops": s.get("disaster_stops"),
                     "max_layers": d.get("max_layers"), "robustness_score": score, "native_fitness": s.get("fitness")})
    rows.sort(key=lambda r: r["robustness_score"], reverse=True)
    return {"ranking": rows, "basis": "backtest leaderboard from strategy_leaderboard.json (in-sample, unvalidated)"}


def w_validate_strategies(c, params, dep):
    ranking = (dep.get("rank") or {}).get("ranking") or w_rank_strategies(c, {}, {})["ranking"]
    critic = _read_json("critic_rules.json") or {}
    wins, losses = critic.get("total_wins_audited"), critic.get("total_losses_audited")
    live_wr = round(100 * wins / (wins + losses), 1) if wins and losses else None
    live_net = round(critic.get("total_realized_wins", 0) - critic.get("total_realized_losses", 0), 2) if critic else None
    verdicts = []
    for r in ranking:
        issues = []
        if (r.get("win_rate") or 0) > 90:
            issues.append(f"{r['win_rate']}% win rate on a multi-layer grid/DCA ({r.get('max_layers')} layers) is the signature of rare large losses; "
                          "win rate says nothing about expectancy")
        issues.append("no out-of-sample or walk-forward result recorded; leaderboard is in-sample")
        issues.append("no spread/slippage/commission model recorded in the leaderboard")
        if live_wr is not None and live_wr < (r.get("win_rate") or 0) - 15:
            issues.append(f"live record (critic audit) is {live_wr}% win rate with realized net {live_net} vs backtest {r['win_rate']}%")
        verdicts.append({"name": r["name"], "verdict": "UNVALIDATED", "issues": issues,
                         "required_before_promotion": ["walk-forward / out-of-sample split", "spread+slippage stress",
                                                       "max-adverse-excursion of the full basket", "paper-trade period"]})
    return {"verdicts": verdicts, "live_reference": {"win_rate_pct": live_wr, "realized_net": live_net,
                                                      "disaster_stops": critic.get("disaster_stops_detected")}}


def w_trade_summary(c, params, dep):
    critic = _read_json("critic_rules.json") or {}
    return {"summary": {k: critic.get(k) for k in ("total_wins_audited", "total_losses_audited", "total_realized_wins",
                                                    "total_realized_losses", "disaster_stops_detected", "win_loss_ratio")},
            "challenge": _read_json("challenge_100_state.json"), "source": "critic_rules.json / challenge_100_state.json"}


def w_backtest_review(c, params, dep):
    # No new backtest is executed here: heavy runs belong to the evolution agent. This reviews stored results.
    lb = _read_json("strategy_leaderboard.json") or {}
    return {"review": {"strategies_on_file": len(lb.get("top_strategies", [])),
                       "note": "stored results only; request a new generation from Darwin Evolution via the bus"}}


WORKERS = {
    "agent_report": w_agent_report, "diagnose": w_diagnose, "permission_gaps": w_permission_gaps,
    "team_plan": w_team_plan, "rank_strategies": w_rank_strategies, "validate_strategies": w_validate_strategies,
    "trade_summary": w_trade_summary, "backtest_review": w_backtest_review,
}
