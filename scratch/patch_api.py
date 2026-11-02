with open("commander/api.py", "r", encoding="utf-8") as f:
    content = f.read()

target_import = 'from .core import CommanderError\n\n_cmd = None'

replacement_import = '''from .core import CommanderError

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

_cmd = None'''

assert target_import in content, "target_import not found"
content = content.replace(target_import, replacement_import, 1)

target_get = '    if path == "objective":\n        return c.store.one("SELECT * FROM objectives WHERE id=?", (q.get("id", ""),)) or {}\n    raise CommanderError(f"unknown endpoint {path}")'

replacement_get = '''    if path == "objective":
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
    raise CommanderError(f"unknown endpoint {path}")'''

assert target_get in content, "target_get not found"
content = content.replace(target_get, replacement_get, 1)

target_post = '    if path == "research/generate":'

replacement_post = '''    # --- AGENT SETTINGS ACTIONS ---
    if path == "agent_settings/trigger_audit":
        return {"results": as_audit.run_full_fleet_audit()}
    if path == "agent_settings/trigger_optimize":
        ea_id = d.get("ea_id", "EA-4444-ACADEMIC-MA")
        return as_opt.optimize_momentum_strategy(ea_id)
    if path == "agent_settings/trigger_elimination":
        ea_id = d.get("ea_id")
        return as_elim.process_underperforming_ea(ea_id)
    if path == "research/generate":'''

assert target_post in content, "target_post not found"
content = content.replace(target_post, replacement_post, 1)

with open("commander/api.py", "w", encoding="utf-8") as f:
    f.write(content)

print("commander/api.py updated successfully!")
