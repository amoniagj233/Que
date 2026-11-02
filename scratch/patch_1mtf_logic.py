def patch_1mtf_logic():
    with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update check in execute_twin_gold_orders
    old_twin_check = '''            # Twin trade policy: Allow current twin pair (up to 2 positions), but block if >= 2 open
            if self.config.get("single_trade_enforcement", True):
                open_pos = mt5.positions_get(symbol="XAUUSD")
                if open_pos and len(open_pos) >= 2:
                    return {"success": False, "message": "Blocked by Risk Policy: Twin XAUUSD positions are already open (2/2 active)"}'''

    new_twin_check = '''            # Twin trade policy: Allow 1 active twin pair per timeframe, prevent blocking by manual/swing trades
            if self.config.get("single_trade_enforcement", True):
                open_pos = mt5.positions_get(symbol="XAUUSD")
                if open_pos:
                    if timeframe == "M1":
                        m1_active = [p for p in open_pos if getattr(p, "magic", 0) in (777111, 777112) or "M1" in getattr(p, "comment", "")]
                        if len(m1_active) >= 2:
                            return {"success": False, "message": "Blocked: Active 1MTF twin scalp already running (2/2 active)"}
                    elif len(open_pos) >= 6:
                        return {"success": False, "message": "Blocked by Risk Policy: Maximum concurrent account exposure reached"}'''

    if old_twin_check in content:
        content = content.replace(old_twin_check, new_twin_check, 1)
        print("Updated twin_check in execute_twin_gold_orders")
    else:
        print("ERROR: old_twin_check not found")

    # 2. Update magic & comment tags in req1 & req2
    old_req1_magic = '"magic": 777101,  # Fixed TP leg\n                "comment": f"G1-FIX-{confidence_score}%",'
    new_req1_magic = '"magic": 777111 if timeframe == "M1" else 777101,  # Fixed TP leg\n                "comment": f"{timeframe}-FIX-{confidence_score}%",'

    if old_req1_magic in content:
        content = content.replace(old_req1_magic, new_req1_magic, 1)
        print("Updated req1 magic & comment")
    else:
        print("ERROR: old_req1_magic not found")

    old_req2_magic = '"magic": 777102,  # Trailing TP leg\n                "comment": f"G2-TRL-{confidence_score}%",'
    new_req2_magic = '"magic": 777112 if timeframe == "M1" else 777102,  # Trailing TP leg\n                "comment": f"{timeframe}-TRL-{confidence_score}%",'

    if old_req2_magic in content:
        content = content.replace(old_req2_magic, new_req2_magic, 1)
        print("Updated req2 magic & comment")
    else:
        print("ERROR: old_req2_magic not found")

    # 3. Update Gate 2 in evaluate_and_execute_auto_trades
    old_gate2 = '''        # Gate 2: Twin Trade Policy Check (Allow up to 2 open positions for 1 active twin setup)
        if self.config.get("single_trade_enforcement", True):
            open_gold = self.get_open_gold_positions()
            if open_gold and len(open_gold) >= 2:
                self.last_eval_status = "MONITORING_OPEN_TRADE"
                pos_summaries = [f"#{p.ticket} ({'BUY' if p.type == 0 else 'SELL'} ${p.profit:.2f})" for p in open_gold[:2]]
                self.last_eval_message = f"Active Twin Trades open: {', '.join(pos_summaries)}. Trailing manager active."
                return {"status": "MONITORING_OPEN_TRADE", "message": self.last_eval_message}'''

    new_gate2 = '''        # Gate 2: Dedicated Timeframe Concurrency Check (1MTF scalps run independently)
        if self.config.get("single_trade_enforcement", True):
            open_gold = self.get_open_gold_positions()
            tf_filter = self.config.get("timeframe_filter", "M1")
            if tf_filter == "M1":
                m1_active = [p for p in open_gold if getattr(p, "magic", 0) in (777111, 777112) or "M1" in getattr(p, "comment", "")]
                if len(m1_active) >= 2:
                    self.last_eval_status = "MONITORING_1M_SCALP"
                    pos_summaries = [f"#{p.ticket} ({'BUY' if p.type == 0 else 'SELL'} ${p.profit:.2f})" for p in m1_active[:2]]
                    self.last_eval_message = f"Active 1MTF Scalp running: {', '.join(pos_summaries)}. Trailing manager active."
                    return {"status": "MONITORING_1M_SCALP", "message": self.last_eval_message}
            elif open_gold and len(open_gold) >= 4:
                self.last_eval_status = "MONITORING_OPEN_TRADE"
                pos_summaries = [f"#{p.ticket} ({'BUY' if p.type == 0 else 'SELL'} ${p.profit:.2f})" for p in open_gold[:2]]
                self.last_eval_message = f"Active Trades open: {', '.join(pos_summaries)}. Trailing manager active."
                return {"status": "MONITORING_OPEN_TRADE", "message": self.last_eval_message}'''

    if old_gate2 in content:
        content = content.replace(old_gate2, new_gate2, 1)
        print("Updated Gate 2 in evaluate_and_execute_auto_trades")
    else:
        print("ERROR: old_gate2 not found")

    with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: 1MTF auto-execution logic applied to gold_auto_trader.py!")
    return True

if __name__ == '__main__':
    patch_1mtf_logic()
