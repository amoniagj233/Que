with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

target1 = "if is_open and confidence_score >= 90 and self.auto_trade_enabled:\n"
replacement1 = """if is_open and confidence_score >= 90 and self.auto_trade_enabled:
                    # Policy: Take trade automatically one symbol at a time per scan pass
                    if auto_trade_executed_this_pass:
                        setup_obj["notes"] += " [Queued: Taking 1 symbol at a time policy]"
                        valid_setups.append(setup_obj)
                        continue
"""

target2 = """                        if order_res.get("success"):
                            setup_obj["status"] = "EXECUTED"
                            setup_obj["group_id"] = order_res.get("group_id")
                            continue"""

replacement2 = """                        if order_res.get("success"):
                            setup_obj["status"] = "EXECUTED"
                            setup_obj["group_id"] = order_res.get("group_id")
                            auto_trade_executed_this_pass = True
                            valid_setups.append(setup_obj)
                            print(f"[AutoTrader] Successfully opened 1 trade on {sym} ({bias}). Adhering to 1 symbol at a time.")
                            continue"""

if target1 in text and "auto_trade_executed_this_pass" in text:
    text = text.replace(target1, replacement1, 1)
    text = text.replace(target2, replacement2, 1)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: Inserted one-symbol-at-a-time gate.")
else:
    print("target1 not found in text.")
