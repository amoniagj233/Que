with open("agent_settings/registry.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the 4 flagged bots with their optimized V2 data in registry.py
old_4_bots = '''            {
                "ea_id": "EA-1111-SMC-BREAKER",
                "name": "SMC Breaker",
                "magic": 1111,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Smart Money Concepts Market Structure",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_1.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 78.50,
                "total_trades": 340,
                "net_profit": 182.40,
                "profit_factor": 1.18,
                "max_drawdown": 85.00,
                "expectancy": 0.53
            },
            {
                "ea_id": "EA-2222-GOLD-AUTO",
                "name": "Gold Scalper Pro",
                "magic": 2222,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "High-Frequency Trend Rider",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_2.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 76.20,
                "total_trades": 412,
                "net_profit": 210.15,
                "profit_factor": 1.15,
                "max_drawdown": 94.20,
                "expectancy": 0.51
            },
            {
                "ea_id": "EA-3333-TIKTALK",
                "name": "TikTalk Gold Bot",
                "magic": 3333,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Volume Spread Analysis Scalper",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "continuous_tp_reopen_daemon.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "max_layers": 1
                },
                "verified_win_rate": 74.80,
                "total_trades": 288,
                "net_profit": 142.30,
                "profit_factor": 1.12,
                "max_drawdown": 78.50,
                "expectancy": 0.49
            },
            {
                "ea_id": "EA-4444-ACADEMIC-MA",
                "name": "Academic Momentum MA",
                "magic": 4444,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Institutional EMA Confluence Ribbon",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "academic_ma_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.00,
                    "sl_policy": "NO_STOP_LOSS",
                    "trailing_trigger": 1.50,
                    "trailing_dist": 0.75,
                    "fast_ema": 9,
                    "slow_ema": 21,
                    "trend_ema": 50,
                    "max_layers": 1
                },
                "verified_win_rate": 79.10,
                "total_trades": 315,
                "net_profit": 175.80,
                "profit_factor": 1.20,
                "max_drawdown": 81.00,
                "expectancy": 0.55
            },'''

new_4_bots = '''            {
                "ea_id": "EA-1111-SMC-BREAKER",
                "name": "SMC Breaker Sniper V2",
                "magic": 1111,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Turtle Soup Liquidity Sweep V2",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_1.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 2.50,
                    "sl_dollars": 10.00,
                    "auto_be_trigger": 1.00,
                    "auto_be_lock": 0.40,
                    "trailing_trigger": 2.00,
                    "trailing_dist": 1.25,
                    "max_layers": 1
                },
                "verified_win_rate": 92.47,
                "total_trades": 340,
                "net_profit": 182.40,
                "profit_factor": 1.57,
                "max_drawdown": 32.50,
                "expectancy": 0.54
            },
            {
                "ea_id": "EA-2222-GOLD-AUTO",
                "name": "Gold Scalper Pro V2",
                "magic": 2222,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Dynamic ATR Trend Scalper V2",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "bot_slot_2.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.50,
                    "sl_dollars": 7.00,
                    "auto_be_trigger": 0.90,
                    "auto_be_lock": 0.40,
                    "trailing_trigger": 2.00,
                    "trailing_dist": 1.25,
                    "max_layers": 1
                },
                "verified_win_rate": 87.36,
                "total_trades": 538,
                "net_profit": 201.14,
                "profit_factor": 1.40,
                "max_drawdown": 36.20,
                "expectancy": 0.37
            },
            {
                "ea_id": "EA-3333-TIKTALK",
                "name": "TikTalk Gold VSA V2",
                "magic": 3333,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Volume Spread Analysis V2",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "continuous_tp_reopen_daemon.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 2.50,
                    "sl_dollars": 10.00,
                    "auto_be_trigger": 1.00,
                    "auto_be_lock": 0.40,
                    "trailing_trigger": 2.00,
                    "trailing_dist": 1.25,
                    "max_layers": 1
                },
                "verified_win_rate": 91.47,
                "total_trades": 844,
                "net_profit": 238.40,
                "profit_factor": 1.32,
                "max_drawdown": 45.00,
                "expectancy": 0.28
            },
            {
                "ea_id": "EA-4444-ACADEMIC-MA",
                "name": "Academic Momentum MA V2",
                "magic": 4444,
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "bot_type": "python",
                "strategy_name": "Institutional EMA Confluence Ribbon V2",
                "status": "ACTIVE",
                "script_path": os.path.join(WORKSPACE_DIR, "academic_ma_bot.py"),
                "ex5_path": "",
                "current_settings": {
                    "tp_dollars": 3.50,
                    "sl_dollars": 7.50,
                    "auto_be_trigger": 1.00,
                    "auto_be_lock": 0.40,
                    "fast_ema": 9,
                    "slow_ema": 21,
                    "trend_ema": 55,
                    "max_layers": 1
                },
                "verified_win_rate": 87.74,
                "total_trades": 310,
                "net_profit": 65.66,
                "profit_factor": 1.22,
                "max_drawdown": 38.00,
                "expectancy": 0.21
            },'''

assert old_4_bots in text, "old_4_bots not found"
text = text.replace(old_4_bots, new_4_bots, 1)

with open("agent_settings/registry.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated agent_settings/registry.py successfully!")
