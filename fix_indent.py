from pathlib import Path

app_path = Path("web_app.py")
text = app_path.read_text(encoding="utf-8")

bad = """        request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lot,
                   "type": order_type, "price": price, "sl": shared_sl, "tp": tp,
                   "deviation": 30, "magic": 555000 + chosen_leg,
                   "comment": f"1T-{chosen_label[:3]}-{symbol[:4]}",
                   "type_time": mt5.ORDER_TIME_GTC,
                   "type_filling": get_best_filling_mode(info)}
        leg = 1
        multiple = chosen_multiple"""

good = """        for leg, multiple in [(1, chosen_multiple)]:
            request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lot,
                       "type": order_type, "price": price, "sl": shared_sl, "tp": tp,
                       "deviation": 30, "magic": 555000 + chosen_leg,
                       "comment": f"1T-{chosen_label[:3]}-{symbol[:4]}",
                       "type_time": mt5.ORDER_TIME_GTC,
                       "type_filling": get_best_filling_mode(info)}"""

assert bad in text, "bad target not found"
text = text.replace(bad, good, 1)

app_path.write_text(text, encoding="utf-8")
print("[+] Cleanly fixed loop indentation!")
