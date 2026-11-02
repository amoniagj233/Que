with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace hard exit with retry loop
old_init = """    from commander.mt5_bridge import bridge
    if not bridge.initialize():
        logger.error(f"MT5 Init failed via bridge: {bridge.last_error}")
        sys.exit(1)"""

new_init = """    from commander.mt5_bridge import bridge
    while not bridge.initialize():
        logger.warning(f"MT5 Init pending via bridge: {bridge.last_error}. Retrying in 5 seconds...")
        time.sleep(5)"""

old_acc = """            # 1. Query account health & equity drawdown
            acc = mt5.account_info()
            if acc:"""

new_acc = """            # 1. Query account health & equity drawdown
            acc = mt5.account_info()
            if not acc:
                if iteration % 12 == 0:
                    logger.warning("MT5 terminal connection dropped or account query failed. Reconnecting bridge...")
                bridge.initialize()
                time.sleep(2)
                continue
            if acc:"""

text_crlf = text.replace("\r\n", "\n")
old_init_crlf = old_init.replace("\r\n", "\n")
new_init_crlf = new_init.replace("\r\n", "\n")
old_acc_crlf = old_acc.replace("\r\n", "\n")
new_acc_crlf = new_acc.replace("\r\n", "\n")

if old_init_crlf in text_crlf:
    text_crlf = text_crlf.replace(old_init_crlf, new_init_crlf)
    print("Patched bridge init.")
else:
    print("old_init not matched")

if old_acc_crlf in text_crlf:
    text_crlf = text_crlf.replace(old_acc_crlf, new_acc_crlf)
    print("Patched account query loop.")
else:
    print("old_acc not matched")

with open("continuous_tp_reopen_daemon.py", "w", encoding="utf-8") as f:
    f.write(text_crlf.replace("\n", "\r\n"))

print("continuous_tp_reopen_daemon.py updated successfully.")
