import re

with open('run_apex_commander.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_pattern = r'fleet_bots = \[\s*\(.*?\]'
new_block = '''fleet_bots = [
        ("bot_slot_1", "bot_slot_1.py", "Apex-Quantum-DeepSL", 1111, "M1", "Deep-SL Momentum Grid"),
        ("bot_slot_2", "bot_slot_2.py", "Mut-8037 Adaptive", 2222, "M1", "Dynamic ATR Spacing"),
        ("smc_breaker_sniper", "smc_breaker_sniper.py", "SMC Breaker Sniper", 3333, "M5", "Turtle Soup Liquidity"),
        ("pattern_pro_bot", "pattern_pro_bot.py", "Strategic Pattern Pro", 4444, "M5", "Asymmetric Box Breakout"),
        ("tiktalk_bot", "tiktalk_bot.py", "TikTalk Bot", 5555, "M5", "9/21 EMA Cross + RSI 14"),
        ("dark_horizon_bot", "dark_horizon_bot.py", "XAU Dark Horizon Scalp AI", 1010, "M1", "9/21/200 EMA + Flow Telemetry"),
        ("crt_gold_pro", "crt_gold_pro.py", "CRT Gold Pro", 9090, "M5", "Candle Range Theory + M5 Reclaim"),
        ("xto_100_challenge", "xto_100_challenge.py", "XTO 100 Challenge", 8888, "M5", "Adaptive Doubling Grid"),
        ("structure_grid_trader", "structure_grid_trader.py", "StructureGrid Pro", 778899, "M1", "Institutional Market Structure"),
        ("strategy_evolution_agent", "strategy_evolution_agent.py", "Darwin Evolution Engine", 7777, "M5", "Continuous Strategy Mutation"),
    ]'''

subbed, n = re.subn(old_pattern, new_block, text, flags=re.DOTALL)
if n > 0:
    with open('run_apex_commander.py', 'w', encoding='utf-8') as f:
        f.write(subbed)
    print(f'Successfully updated {n} instance(s)')
else:
    print('Pattern not matched')
