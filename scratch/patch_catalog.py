import re

with open("commander/agents.py", "r", encoding="utf-8") as f:
    text = f.read()

old_catalog = """CATALOG = {
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
    "bot_slot_1.py": ("Bot Slot 1 (Mut-8407)", "Live grid/DCA trader, magic 1111.", "Execution", "live", "bot1_magic1111.log", None),
    "bot_slot_2.py": ("Bot Slot 2", "Live grid/DCA trader, magic 2222.", "Execution", "live", "bot2_magic2222.log", None),
    "xto_speeder_trader.py": ("XTO Speeder", "Live XTO speeder trader.", "Execution", "live", None, None),
    "xto_apex_quantum.py": ("XTO Apex Quantum", "Live Apex Quantum trader.", "Execution", "live", "apex_quantum.log", None),
    "xto_100_challenge.py": ("XTO 100 Challenge", "Live $100 challenge trader.", "Execution", "live", None, "challenge_100_state.json"),
    "structure_grid_trader.py": ("Structure Grid Trader", "Live HH/LL structure grid trader.", "Execution", "live", None, None),
}
DISCOVERY_GLOBS = ["agent_*.py", "bot_slot_*.py", "xto_*.py", "*_trader.py", "*_agent.py"]
NON_AGENT = {"xto_upgrade_atr.py", "xto_upgrade_golden.py", "xto_upgrade_reversal.py", "gold_auto_trader.py"}"""

new_catalog = """CATALOG = {
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
NON_AGENT = {"xto_upgrade_atr.py", "xto_upgrade_golden.py", "xto_upgrade_reversal.py"}"""

if old_catalog in text:
    text = text.replace(old_catalog, new_catalog)
    with open("commander/agents.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Catalog updated successfully!")
else:
    print("Old catalog string not matched.")
