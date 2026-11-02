# Update commander/agents.py
with open("commander/agents.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '"dark_horizon_bot.py":'
addition = '"crt_gold_pro.py": ("CRT Gold Pro", "Candle Range Theory + MQL5 Synchronized Indicator, magic 9090.", "Execution", "live", "crt_gold_pro.log", None),\n    '

if target in text and "crt_gold_pro.py" not in text:
    text = text.replace(target, addition + target)
    with open("commander/agents.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Registered crt_gold_pro in commander/agents.py")

# Update continuous_tp_reopen_daemon.py
with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    text = f.read()

target_roster = 'BOT_ROSTER = ['
addition_roster = 'BOT_ROSTER = [\n    ("CRT Gold Pro", 9090),'

if target_roster in text and "9090" not in text:
    text = text.replace(target_roster, addition_roster)
    with open("continuous_tp_reopen_daemon.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Registered crt_gold_pro in continuous_tp_reopen_daemon.py")
