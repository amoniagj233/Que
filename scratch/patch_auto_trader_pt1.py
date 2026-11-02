import re

def update_gold_auto_trader():
    with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update default config to include twin_trade_enabled and timeframe_filter
    old_cfg = '''        default_cfg = {
            "enabled": False,
            "min_confidence": 90,
            "lot_size": 0.01,
            "tp_mode": "RANDOM_TP1_TP2",  # Options: RANDOM_TP1_TP2, TP1_CONSERVATIVE, TP2_RUNNER
            "news_filter_enabled": True,
            "max_daily_trades": 3,
            "single_trade_enforcement": True,
            "enable_profit_chaser": True,
            "scan_interval_seconds": 15
        }'''

    new_cfg = '''        default_cfg = {
            "enabled": False,
            "min_confidence": 90,
            "lot_size": 0.01,
            "tp_mode": "TWIN_FIXED_AND_TRAILING",  # Twin trade: 1 Fixed TP + 1 Trailing TP
            "twin_trade_enabled": True,             # Rule: Anytime a trade opens, open twice (1 Fixed TP, 1 Trailing TP)
            "timeframe_filter": "M1_M5",           # Options: "M1", "M5", "M1_M5", "ALL"
            "m1_trail_dist": 3.00,                 # $3.00/oz trailing distance for M1 scalps
            "m5_trail_dist": 4.50,                 # $4.50/oz trailing distance for M5 momentum
            "default_trail_dist": 5.00,            # $5.00/oz trailing distance for higher TFs
            "news_filter_enabled": True,
            "max_daily_trades": 6,                 # 6 legs (up to 3 twin setups per day)
            "single_trade_enforcement": True,      # Allows 1 twin pair (2 concurrent legs) at a time
            "enable_profit_chaser": True,
            "scan_interval_seconds": 10
        }'''

    if old_cfg in content:
        content = content.replace(old_cfg, new_cfg, 1)
        print("Updated default_cfg in gold_auto_trader.py")
    else:
        print("WARNING: old_cfg not found!")

    # 2. Add self.trailing_positions and trailing worker thread in __init__
    old_init = '''        self.running = True
        self._worker_thread = threading.Thread(target=self._run_auto_loop, daemon=True, name="GoldAutoTraderWorker")
        self._worker_thread.start()'''

    new_init = '''        self.running = True
        self.trailing_positions: Dict[int, Dict[str, Any]] = {}
        self.trailing_events_log: List[Dict[str, Any]] = []

        self._worker_thread = threading.Thread(target=self._run_auto_loop, daemon=True, name="GoldAutoTraderWorker")
        self._worker_thread.start()

        self._trailing_thread = threading.Thread(target=self._run_trailing_loop, daemon=True, name="GoldTrailingRunnerWorker")
        self._trailing_thread.start()'''

    if old_init in content:
        content = content.replace(old_init, new_init, 1)
        print("Added trailing thread and state to __init__ in gold_auto_trader.py")
    else:
        print("WARNING: old_init not found!")

    # 3. Update update_config method to allow new fields
    old_update_cfg = '''            for k in ["min_confidence", "lot_size", "tp_mode", "news_filter_enabled", "max_daily_trades", "single_trade_enforcement", "enable_profit_chaser"]:'''
    new_update_cfg = '''            for k in ["min_confidence", "lot_size", "tp_mode", "twin_trade_enabled", "timeframe_filter", "m1_trail_dist", "m5_trail_dist", "news_filter_enabled", "max_daily_trades", "single_trade_enforcement", "enable_profit_chaser"]:'''

    if old_update_cfg in content:
        content = content.replace(old_update_cfg, new_update_cfg, 1)
        print("Updated allowed fields in update_config")

    with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Part 1 applied to gold_auto_trader.py")

if __name__ == '__main__':
    update_gold_auto_trader()
