# Update commander/agents.py
with open("commander/agents.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '"bot_slot_1.py": ("Apex-Quantum-DeepSL (Bot Slot 1)",'
addition = '"dark_horizon_bot.py": ("XAU Dark Horizon Scalp AI", "Live 6-Matrix Telemetry Decision Engine, magic 1010.", "Execution", "live", "dark_horizon_bot.log", None),\n    '

if target in text and "dark_horizon_bot.py" not in text:
    text = text.replace(target, addition + target)
    with open("commander/agents.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Registered dark_horizon_bot in commander/agents.py")

# Update continuous_tp_reopen_daemon.py
with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    text = f.read()

target_roster = 'BOT_ROSTER = ['
addition_roster = 'BOT_ROSTER = [\n    ("XAU Dark Horizon Scalp AI", 1010),'

if target_roster in text and "1010" not in text:
    text = text.replace(target_roster, addition_roster)
    with open("continuous_tp_reopen_daemon.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Registered dark_horizon_bot in continuous_tp_reopen_daemon.py")
