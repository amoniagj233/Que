with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update default_cfg
old_1 = '"timeframe_filter": "M1",              # 1MTF trades'
new_1 = '"timeframe_filter": "M1",              # 1MTF trades\n            "m1_use_sl": False,                    # Do not use SL on M1 trades (User experiment)'

# 2. Update update_config allowed keys
old_2 = '"single_trade_enforcement", "enable_profit_chaser"]'
new_2 = '"single_trade_enforcement", "enable_profit_chaser", "m1_use_sl"]'

# 3. Update execute_twin_gold_orders
old_3 = '# --- 1. TRADE 1: FIXED TARGET TP ---'
new_3 = '''# User experiment: If M1 trades should not use Stop Loss
            tf_up = str(timeframe).upper()
            if (tf_up == "M1" or "M1" in tf_up or "1M" in tf_up) and not self.config.get("m1_use_sl", True):
                sl = 0.0

            # --- 1. TRADE 1: FIXED TARGET TP ---'''

# 4. Update execute_single_gold_order
old_4 = 'req = {\n                "action": mt5.TRADE_ACTION_DEAL,'
if old_4 not in content:
    old_4 = 'req = {\r\n                "action": mt5.TRADE_ACTION_DEAL,'
new_4 = '''tf_up = str(timeframe).upper()
            if (tf_up == "M1" or "M1" in tf_up or "1M" in tf_up) and not self.config.get("m1_use_sl", True):
                sl = 0.0

            req = {
                "action": mt5.TRADE_ACTION_DEAL,'''

# 5. Update execute_gold_order fallback
old_5 = 'tf = "M1" if "M1" in strategy_name else ("M5" if "M5" in strategy_name else "M15")'
new_5 = '''tf = "M1" if ("M1" in strategy_name or "1M" in strategy_name) else ("M5" if "M5" in strategy_name else "M15")
            if (tf == "M1" or "1M" in tf) and not self.config.get("m1_use_sl", True):
                sl = 0.0'''

assert old_1 in content, "old_1 not found"
assert old_2 in content, "old_2 not found"
assert old_3 in content, "old_3 not found"
assert old_4 in content, "old_4 not found"
assert old_5 in content, "old_5 not found"

content = content.replace(old_1, new_1, 1)
content = content.replace(old_2, new_2, 1)
content = content.replace(old_3, new_3, 1)
content = content.replace(old_4, new_4, 1)
content = content.replace(old_5, new_5, 1)

with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied m1_use_sl to gold_auto_trader.py!")
