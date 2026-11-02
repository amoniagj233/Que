import json

cfg = {
    "enabled": True,
    "timeframe_filter": "M1",
    "min_confidence": 90,
    "lot_size": 0.01,
    "tp_mode": "TWIN_FIXED_AND_TRAILING",
    "twin_trade_enabled": True,
    "m1_trail_dist": 3.0,
    "m5_trail_dist": 4.5,
    "default_trail_dist": 5.0,
    "news_filter_enabled": True,
    "max_daily_trades": 50,
    "single_trade_enforcement": True,
    "enable_profit_chaser": True,
    "scan_interval_seconds": 3
}

with open("gold_auto_trade_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("gold_auto_trade_config.json verified!")
