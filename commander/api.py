"""HTTP glue for web_app.py. RBAC: loopback clients are 'owner'; every other client is read-only 'viewer'."""
import json
import threading
from urllib.parse import parse_qs, urlparse

from .mt5_bridge import bridge
from .risk_manager import risk_manager
from .supervisor import bot_supervisor
from .researcher import quant_researcher
from .daily_reporter import daily_reporter
from .replacement_manager import replacement_manager
from .evaluator import bot_evaluator

from .commander import Commander
from .core import CommanderError

from agent_settings.database import SettingsDatabase
from agent_settings.audit_engine import AuditEngine
from agent_settings.optimizer import StrategyOptimizer
from agent_settings.elimination_agent import EliminationAgent
from agent_settings.champion_challenger import ChampionChallengerArena
from agent_settings.regime_analyzer import MarketRegimeAnalyzer
from agent_settings.portfolio_coordinator import PortfolioCoordinator

as_db = SettingsDatabase()
as_audit = AuditEngine(as_db)
as_opt = StrategyOptimizer(as_db)
as_elim = EliminationAgent(as_db, as_audit, as_opt)
as_arena = ChampionChallengerArena(as_db)
as_regime = MarketRegimeAnalyzer(as_db)
as_port = PortfolioCoordinator(as_db)

_cmd = None
_lock = threading.Lock()
PREFIX = "/api/commander"


def get():
    global _cmd
    with _lock:
        if _cmd is None:
            _cmd = Commander()
            _wire_mt5(_cmd)
        return _cmd


def _wire_mt5(c):
    """Wire centralized MT5 Gold Bridge, Live Supervisor, Risk Manager, and Daily Reporter."""
    try:
        bridge.initialize()
        bot_supervisor.bridge = bridge
        bot_supervisor.commander = c
        # Register core fleet bots
        for bid, script, name, magic, tf, strat in [
            ("bot_slot_1", "bot_slot_1.py", "Apex-Quantum-DeepSL", 1111, "M1", "Deep-SL Momentum Grid"),
            ("bot_slot_2", "bot_slot_2.py", "Mut-8037 Adaptive", 2222, "M1", "Dynamic ATR Spacing"),
            ("smc_breaker_sniper", "smc_breaker_sniper.py", "SMC Breaker Sniper", 3333, "M5", "Turtle Soup Liquidity"),
            ("pattern_pro_bot", "pattern_pro_bot.py", "Strategic Pattern Pro", 4444, "M5", "Asymmetric Box Breakout"),
            ("tiktalk_bot", "tiktalk_bot.py", "TikTalk Bot", 5555, "M5", "9/21 EMA Cross + RSI 14"),
            ("gold_auto_trader", "gold_auto_trader.py", "Gold Auto Trader", 7777, "M5", "Smart Profit Chaser"),
            ("ml_trading_engine", "ml_trading_engine.py", "ML Intelligence Engine", 8888, "M5", "24-Feature ML Setup"),
            ("backtest_ma44_332", "backtest_ma44_332.py", "Academic MA 44/332 Bot", 6666, "M1", "Dual Moving Average"),
        ]:
            bot_supervisor.register_bot(bid, name, script, magic, tf, strat)
        bot_supervisor.start()

        daily_reporter.bridge = bridge
        daily_reporter.supervisor = bot_supervisor
        daily_reporter.commander = c
        daily_reporter.start()

        def execute(o):
            return bridge.place_order(symbol=o.get("symbol", "XAUUSD"), action=o.get("action", "BUY"),
                                      volume=float(o.get("volume", 0.01)), sl=float(o.get("sl", 0.0)),
                                      tp=float(o.get("tp", 0.0)), magic=int(o.get("magic", 1000)))

        c.live_executor = execute
        c.positions_fn = lambda: len(bridge.get_open_positions())
    except Exception as e:
        pass


def _role(handler):
    return "owner" if handler.client_address[0] in ("127.0.0.1", "::1") else "viewer"


def _send(h, status, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(body)


def handles(path):
    return path.startswith(PREFIX)


def dispatch(h, method, data=None):
    url = urlparse(h.path)
    path = url.path[len(PREFIX):].strip("/")
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    role = _role(h)
    c = get()
    try:
        if method == "GET":
            return _send(h, 200, _get(c, path, q))
        if role != "owner":
            return _send(h, 403, {"error": "owner (localhost) access required"})
        return _send(h, 200, _post(c, path, data or {}))
    except CommanderError as e:
        return _send(h, 409, {"error": str(e)})
    except KeyError as e:
        return _send(h, 400, {"error": f"missing field {e}"})
    except Exception as e:  # never leak a traceback to the client
        c.audit.log("commander", "api.error", path=path, error=repr(e)[:300])
        return _send(h, 500, {"error": "internal error (see audit log)"})


def _get(c, path, q):
    if path in ("", "overview"):
        ov = c.overview()
        ov["account"] = bridge.get_account_summary()
        ov["open_positions"] = bridge.get_open_positions()
        return ov
    if path == "positions":
        return {"positions": bridge.get_open_positions()}
    if path == "fleet":
        return {"fleet": bot_supervisor.get_fleet_snapshot()}
    if path == "research/hypotheses":
        return {"hypotheses": quant_researcher.get_all_hypotheses()}
    if path == "daily_report/latest":
        rep = daily_reporter.get_latest_report()
        return rep or {"content": "No report generated yet. Click 'Run 06:00 Report Now' to generate."}
    if path == "daily_report/all":
        return {"reports": daily_reporter.list_all_reports()}
    if path == "replacement/audit":
        return {"audit": replacement_manager.get_audit_history()}
    if path == "risk/status":
        acc = bridge.get_account_summary()
        return {
            "daily_loss_limit": risk_manager.max_daily_loss_pct,
            "max_dd_limit": risk_manager.max_portfolio_dd_pct,
            "emergency_suspended": risk_manager.emergency_suspended,
            "suspension_reason": risk_manager.suspension_reason,
            "account": acc
        }
    if path == "messages":
        return {"messages": c.bus.since(int(q.get("since", 0)), 200)}
    if path == "audit":
        return {"audit": c.audit.recent(int(q.get("n", 100)), q.get("prefix"))}
    if path == "performance":
        return {"performance": c.performance(), "recommendations": c.recommendations(), "versions": c.versions()}
    if path == "approvals":
        return {"approvals": c.approvals.list(q.get("status"))}
    if path == "objective":
        return c.store.one("SELECT * FROM objectives WHERE id=?", (q.get("id", ""),)) or {}
    # --- AGENT SETTINGS ENDPOINTS ---
    if path == "agent_settings/overview":
        return as_db.get_dashboard_summary()
    if path == "agent_settings/leaderboard":
        return {"fleet": as_audit.run_full_fleet_audit()}
    if path == "agent_settings/optimizations":
        with as_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM optimization_runs ORDER BY id DESC LIMIT 50")
            return {"runs": [dict(r) for r in cursor.fetchall()]}
    if path == "agent_settings/eliminations":
        with as_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM eliminations ORDER BY id DESC")
            return {"eliminations": [dict(r) for r in cursor.fetchall()]}
    if path == "agent_settings/arena":
        return {"champions": as_arena.get_champions()}
    if path == "agent_settings/regime":
        return {"regime": as_regime.analyze_current_regime()}
    if path == "agent_settings/activity":
        return {"activities": as_db.get_recent_activities(50)}
    if path == "agent_settings/risk":
        acc = bridge.get_account_summary()
        pos = bridge.get_open_positions()
        return {"risk": as_port.compute_portfolio_risk_summary(acc, pos)}
    raise CommanderError(f"unknown endpoint {path}")


def _post(c, path, d):
    if path == "level":
        return c.set_level(int(d["level"]))
    if path == "estop":
        return c.emergency_stop()
    if path == "estop/release":
        return c.release_estop()
    if path.startswith("agent/"):
        _, aid, op = path.split("/")
        return c.agent_action(aid, op)
    if path == "chat":
        return c.chat(d["text"])
    if path == "task/cancel":
        return c.scheduler.cancel(d["id"]) or {"ok": True}
    if path == "task/reassign":
        c._need(2, "reassign task")
        c.scheduler.reassign(d["id"], d["owner"])
        return {"ok": True}
    if path == "perm/grant":
        c._need(2, "grant permission")
        return c.perms.grant(d["agent"], d["perm"], "owner")
    if path == "perm/revoke":
        return c.perms.revoke(d["agent"], d["perm"], "owner")
    if path == "perm/ceiling":
        c.perms.set_ceiling(d["agent"], d["perms"])
        return {"ok": True}
    if path == "approval/decide":
        return c.approvals.decide(d["id"], bool(d["approve"]), d.get("note", ""))
    if path == "discover":
        return {"registered": c.discover()}
    if path == "workflow/propose":
        return {"version": c.propose_workflow_candidate(d["key"], d["step"])}
    if path == "workflow/evaluate":
        return {"results": c.evaluate_workflows()}
    if path == "live/request":
        return c.request_live_trade(d["agent"], d["order"])
    # --- AGENT SETTINGS ACTIONS ---
    if path == "agent_settings/trigger_audit":
        return {"results": as_audit.run_full_fleet_audit()}
    if path == "agent_settings/trigger_optimize":
        ea_id = d.get("ea_id", "EA-4444-ACADEMIC-MA")
        return as_opt.optimize_momentum_strategy(ea_id)
    if path == "agent_settings/trigger_elimination":
        ea_id = d.get("ea_id")
        return as_elim.process_underperforming_ea(ea_id)
    if path == "research/generate":
        return {"hypothesis": quant_researcher.generate_new_hypothesis(d.get("family"))}
    if path == "daily_report/generate":
        return daily_reporter.generate_and_archive_daily_report()
    if path == "replacement/execute":
        return replacement_manager.execute_autonomous_replacement(
            d["incumbent_id"], d["candidate_script"], d["candidate_name"], d.get("reason", "Autonomous replacement")
        )
    if path == "replacement/rollback":
        return replacement_manager.rollback_replacement(d["incumbent_id"], d["backup_file"])
    raise CommanderError(f"unknown endpoint {path}")
