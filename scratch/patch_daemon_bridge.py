with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '''    MT5_PATH = r"C:\\Program Files\\Headway MT5 Terminal\\terminal64.exe"
    if not mt5.initialize(path=MT5_PATH):
        logger.error(f"MT5 Init failed: {mt5.last_error()}")
        sys.exit(1)

    symbol = get_symbol()
    logger.info(f"Target Asset: {symbol} | Managed Roster: {len(ALL_BOT_ROSTER)} Bot Magics")'''

replacement = '''    from commander.mt5_bridge import bridge
    if not bridge.initialize():
        logger.error(f"MT5 Init failed via bridge: {bridge.last_error}")
        sys.exit(1)

    symbol = bridge.gold_symbol
    logger.info(f"Target Asset: {symbol} ({bridge.terminal_name}) | Managed Roster: {len(ALL_BOT_ROSTER)} Bot Magics")'''

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open("continuous_tp_reopen_daemon.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated continuous_tp_reopen_daemon.py to use bridge.initialize()!")
