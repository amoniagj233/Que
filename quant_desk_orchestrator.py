"""
=============================================================================
  🏛️ MASTER QUANT TRADING DESK ORCHESTRATOR
=============================================================================
Supervises and orchestrates all 6 autonomous agents in the quant ecosystem:
  1. 📰 News Sentinel Agent (`agent_news_sentinel.py`)
  2. ⚖️ Chief Risk Officer & Sizing Agent (`agent_cro_risk.py`)
  3. 🏛️ Smart Money Concepts & Liquidity Agent (`agent_smc_liquidity.py`)
  4. 🌐 Inter-Market Macro Correlation Agent (`agent_macro_correlation.py`)
  5. 🔬 Postmortem Critic & Loss Auditor Agent (`agent_critic_auditor.py`)
  6. 🧬 Darwin Strategy Evolution Agent (`strategy_evolution_agent.py`)

Outputs a unified, institutional-grade real-time dashboard HUD.
=============================================================================
"""

import subprocess
import time
import sys
import os
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PYTHON_EXE = sys.executable
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_DIR    = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

AGENTS = [
    {"name": "News Sentinel", "script": "agent_news_sentinel.py", "log": os.path.join(LOG_DIR, "news_sentinel.log")},
    {"name": "CRO Risk Officer", "script": "agent_cro_risk.py", "log": os.path.join(LOG_DIR, "cro_risk.log")},
    {"name": "SMC Liquidity", "script": "agent_smc_liquidity.py", "log": os.path.join(LOG_DIR, "smc_liquidity.log")},
    {"name": "Macro Correlation", "script": "agent_macro_correlation.py", "log": os.path.join(LOG_DIR, "macro_correlation.log")},
    {"name": "Critic Auditor", "script": "agent_critic_auditor.py", "log": os.path.join(LOG_DIR, "critic_auditor.log")},
    {"name": "Darwin Evolution", "script": "strategy_evolution_agent.py", "log": os.path.join(LOG_DIR, "evolution_journal.log")},
    {"name": "Dual Bot Supervisor", "script": "run_dual_xto_traders.py", "log": os.path.join(LOG_DIR, "dual_traders.log")}
]

def read_json_safe(filename):
    path = os.path.join(BASE_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def start_agent_process(agent_info):
    script_path = os.path.join(BASE_DIR, agent_info['script'])
    log_fp = open(agent_info['log'], "a", encoding="utf-8", buffering=1)
    p = subprocess.Popen(
        [PYTHON_EXE, "-u", script_path],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return p

def render_hud(procs):
    news = read_json_safe("market_risk_state.json")
    cro  = read_json_safe("cro_risk_state.json")
    smc  = read_json_safe("smc_levels.json")
    macro = read_json_safe("macro_confluence.json")
    leaderboard = read_json_safe("strategy_leaderboard.json")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.system("cls" if os.name == "nt" else "clear")

    print("=" * 78)
    print(f"  🏛️ AUTONOMOUS QUANT TRADING DESK | LIVE TERMINAL HUD | {now_str}")
    print("=" * 78)

    # Agent Process Health
    print("🤖 ACTIVE AGENTS STATUS:")
    for a in AGENTS:
        p = procs.get(a['name'])
        status = "🟢 RUNNING" if p and p.poll() is None else "🔴 STOPPED"
        print(f"  [{status}] {a['name']:<22} -> {a['script']}")
    print("-" * 78)

    # Risk & Macro Telemetry
    print("📊 LIVE QUANT SIGNALS & RISK TELEMETRY:")
    if news:
        freeze_str = "🚨 ACTIVE (HALTED)" if news.get('news_freeze') else "🟢 CLEAR (TRADING ALLOWED)"
        print(f"  • News Sentinel : Status={freeze_str} | Next={news.get('next_event', 'N/A')}")
    if cro:
        cb_str = "🔴 ENGAGED" if cro.get('circuit_breaker') else "🟢 NORMAL"
        print(f"  • Risk Officer  : Spread=${cro.get('spread_usd', 0):.2f} | BaseLot={cro.get('recommended_base_lot', 0.01)} | MarginLevel={cro.get('margin_level_pct', 0)}% | CircuitBreaker={cb_str}")
    if smc:
        print(f"  • SMC Liquidity : Price=${smc.get('current_price', 0):.2f} | Bias={smc.get('bias', 'N/A')} | Demand OB=${smc.get('nearest_demand_zone', 0):.2f} | Supply OB=${smc.get('nearest_supply_zone', 0):.2f}")
    if macro:
        print(f"  • Macro Confl.  : Score={macro.get('confluence_score', 0):+d}/100 | Regime={macro.get('regime', 'N/A')} | Action={macro.get('recommendation', 'N/A')}")

    print("-" * 78)
    print("🏆 TOURNAMENT TOP 2 SURVIVOR BOTS:")
    if leaderboard and leaderboard.get('top_strategies'):
        for rank, s in enumerate(leaderboard['top_strategies'][:2], 1):
            dna = s['dna']
            print(f"  Rank #{rank}: {dna['name']:<18} | ROI: +{s['roi_pct']:.1f}% | Win: {s['win_rate']:.1f}% | PF: {s['profit_factor']:.2f} | MaxDD: ${s['max_drawdown']:.0f} | Fitness: {s['fitness']}")
    print("=" * 78)
    print("  Auto-refreshing every 5 seconds. Press Ctrl+C to safely pause all agents.")

def main():
    print("Initializing Autonomous Quant Desk...")
    procs = {}

    for a in AGENTS:
        p = start_agent_process(a)
        procs[a['name']] = p
        print(f"Started {a['name']} (PID: {p.pid})")

    time.sleep(2)

    while True:
        try:
            # Check and auto-restart crashed agents
            for a in AGENTS:
                p = procs.get(a['name'])
                if p is None or p.poll() is not None:
                    new_p = start_agent_process(a)
                    procs[a['name']] = new_p

            render_hud(procs)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nSafely shutting down all agents...")
            for name, p in procs.items():
                try: p.terminate()
                except Exception: pass
            print("All agents stopped.")
            break
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
