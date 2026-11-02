with open("gold_auto_trader.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update _update_trailing_stops
old_trailing_head = """    def _update_trailing_stops(self):
        if mt5 is None:
            return

        with self.mt5_lock:
            open_pos = mt5.positions_get(symbol="XAUUSD")
            if not open_pos:
                with self.lock:
                    self.trailing_positions.clear()
                return

            pos_by_ticket = {p.ticket: p for p in open_pos}

            # Remove closed tickets from tracking
            with self.lock:
                for t in list(self.trailing_positions.keys()):
                    if t not in pos_by_ticket:
                        del self.trailing_positions[t]"""

new_trailing_head = """    def _update_trailing_stops(self):
        if mt5 is None:
            return

        with self.mt5_lock:
            open_pos = mt5.positions_get(symbol="XAUUSD")
            if open_pos is None:
                open_pos = []

            pos_by_ticket = {p.ticket: p for p in open_pos}
            current_tickets = set(pos_by_ticket.keys())

            # Detect closed tickets that were previously open
            if self.known_gold_tickets:
                closed_tickets = self.known_gold_tickets - current_tickets
                if closed_tickets:
                    max_cap = int(self.config.get("max_concurrent_trades", 5))
                    for t in closed_tickets:
                        tp_note = "Position closed"
                        try:
                            deals = mt5.history_deals_get(position=t)
                            if deals and len(deals) > 1:
                                last_deal = deals[-1]
                                profit = getattr(last_deal, "profit", 0.0)
                                reason = getattr(last_deal, "reason", 0)
                                is_tp = (reason == 4 or profit > 0)
                                tp_label = "TAKE PROFIT HIT" if is_tp else "CLOSED"
                                tp_note = f"🎯 {tp_label} on #{t}: P/L +${profit:.2f}"
                        except Exception:
                            pass
                        event_msg = f"{tp_note} -> Concurrency at {len(open_pos)}/{max_cap}. Replacing instantly..."
                        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {event_msg}")
                        self.trailing_events_log.insert(0, {
                            "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                            "ticket": t,
                            "event": "TP_HIT_REPLACING",
                            "message": event_msg
                        })

                    # If slots available, trigger evaluation immediately
                    if self.config.get("enabled", False) and len(open_pos) < max_cap:
                        threading.Thread(target=self.evaluate_and_execute_auto_trades, daemon=True).start()

            self.known_gold_tickets = current_tickets

            if not open_pos:
                with self.lock:
                    self.trailing_positions.clear()
                return

            # Remove closed tickets from tracking
            with self.lock:
                for t in list(self.trailing_positions.keys()):
                    if t not in pos_by_ticket:
                        del self.trailing_positions[t]"""

assert old_trailing_head.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_trailing_head not found"
code = code.replace(old_trailing_head.replace("\r\n", "\n"), new_trailing_head) if "\r\n" not in code else code.replace(old_trailing_head.replace("\n", "\r\n"), new_trailing_head.replace("\n", "\r\n"))

# 2. Update Gate 2 and execution in evaluate_and_execute_auto_trades
old_eval_body = """        # Gate 2: Dedicated Timeframe Concurrency Check (1MTF scalps run independently)
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
                return {"status": "MONITORING_OPEN_TRADE", "message": self.last_eval_message}"""

new_eval_body = """        # Gate 2: Concurrency Cap Check (Take max 5 trades at a time, replace on TP)
        max_concurrent = int(self.config.get("max_concurrent_trades", 5))
        open_gold = self.get_open_gold_positions()
        current_open = len(open_gold) if open_gold else 0

        if current_open >= max_concurrent:
            self.last_eval_status = "CAPACITY_FULL_5_TRADES"
            pos_summaries = [f"#{p.ticket} ({'BUY' if p.type == 0 else 'SELL'} ${p.profit:.2f})" for p in open_gold[:5]]
            self.last_eval_message = f"5 Concurrent Trades Active ({current_open}/{max_concurrent} slots filled). Dynamic Trailing & TPs active. Replaces instantly on TP exit."
            return {"status": "CAPACITY_FULL_5_TRADES", "message": self.last_eval_message}

        available_slots = max_concurrent - current_open"""

assert old_eval_body.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_eval_body not found"
code = code.replace(old_eval_body.replace("\r\n", "\n"), new_eval_body) if "\r\n" not in code else code.replace(old_eval_body.replace("\n", "\r\n"), new_eval_body.replace("\n", "\r\n"))

# 3. Update execution block in evaluate_and_execute_auto_trades
old_exec_block = """        # Trigger Twin Order Execution (1 Fixed TP + 1 Trailing TP)
        exec_res = self.execute_twin_gold_orders(
            action=chosen["direction"],
            lot=lot,
            sl=chosen["sl"],
            tp_fixed=chosen["tp1"],
            confidence_score=chosen["confidence_score"],
            strategy_name=chosen["strategy"],
            timeframe=chosen.get("timeframe", "M1"),
            notes=f"Auto-Executed via Gold Intelligence [Twin Trade: Fixed TP1 + Dynamic Trailing]",
            is_auto=True
        )

        if exec_res.get("success"):
            self.last_eval_status = "EXECUTED"
            self.last_eval_message = f"AUTO-EXECUTED TWIN TRADES: {chosen['direction']} {lot} lot XAUUSD @ {exec_res.get('fill_price')} (Confidence {chosen['confidence_score']}%, {chosen['strategy']})"
            return {"status": "EXECUTED", "trade": exec_res, "message": self.last_eval_message}
        else:
            self.last_eval_status = "EXECUTION_BLOCKED"
            self.last_eval_message = f"Auto-trade blocked: {exec_res.get('message')}"
            return {"status": "EXECUTION_BLOCKED", "message": self.last_eval_message}"""

new_exec_block = """        # Execute trade based on available slots (Twin trade if >= 2 slots open, single trade if 1 slot open)
        if available_slots >= 2 and self.config.get("twin_trade_enabled", True):
            exec_res = self.execute_twin_gold_orders(
                action=chosen["direction"],
                lot=lot,
                sl=chosen["sl"],
                tp_fixed=chosen["tp1"],
                confidence_score=chosen["confidence_score"],
                strategy_name=chosen["strategy"],
                timeframe=chosen.get("timeframe", "M1"),
                notes=f"Auto-Executed Twin Scalp ({current_open + 2}/{max_concurrent} active): Fixed TP1 + Trailing TP",
                is_auto=True
            )
            mode_desc = "TWIN TRADES (Fixed + Trailing)"
        else:
            # Exactly 1 slot remaining: execute single trade to fill the exact 5-trade cap
            exec_res = self.execute_single_gold_order(
                action=chosen["direction"],
                lot=lot,
                sl=chosen["sl"],
                tp=chosen["tp1"],
                confidence_score=chosen["confidence_score"],
                strategy_name=chosen["strategy"],
                timeframe=chosen.get("timeframe", "M1"),
                notes=f"Auto-Replacement Trade ({current_open + 1}/{max_concurrent} active cap)",
                is_auto=True
            )
            mode_desc = "SINGLE REPLACEMENT TRADE (Fixed TP)"

        if exec_res.get("success"):
            self.last_eval_status = "EXECUTED"
            self.last_eval_message = f"AUTO-EXECUTED {mode_desc}: {chosen['direction']} {lot} lot XAUUSD @ {exec_res.get('fill_price')} (Confidence {chosen['confidence_score']}%, {chosen['strategy']})"
            return {"status": "EXECUTED", "trade": exec_res, "message": self.last_eval_message}
        else:
            self.last_eval_status = "EXECUTION_BLOCKED"
            self.last_eval_message = f"Auto-trade blocked: {exec_res.get('message')}"
            return {"status": "EXECUTION_BLOCKED", "message": self.last_eval_message}"""

assert old_exec_block.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_exec_block not found"
code = code.replace(old_exec_block.replace("\r\n", "\n"), new_exec_block) if "\r\n" not in code else code.replace(old_exec_block.replace("\n", "\r\n"), new_exec_block.replace("\n", "\r\n"))

# 4. Update scan_interval clamp in _run_auto_loop
old_loop = """            try:
                interval = max(5, self.config.get("scan_interval_seconds", 15))
                time.sleep(interval)"""

new_loop = """            try:
                interval = max(1, self.config.get("scan_interval_seconds", 2))
                time.sleep(interval)"""

assert old_loop.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_loop not found"
code = code.replace(old_loop.replace("\r\n", "\n"), new_loop) if "\r\n" not in code else code.replace(old_loop.replace("\n", "\r\n"), new_loop.replace("\n", "\r\n"))

# 5. Update get_status return dictionary
old_status_ret = """                "daily_trades_count": self.daily_trades_count,
                "max_daily_trades": self.config.get("max_daily_trades", 50),
                "open_gold_positions": formatted_pos,"""

new_status_ret = """                "daily_trades_count": self.daily_trades_count,
                "max_daily_trades": self.config.get("max_daily_trades", 50),
                "max_concurrent_trades": int(self.config.get("max_concurrent_trades", 5)),
                "current_concurrent_trades": len(formatted_pos),
                "available_slots": max(0, int(self.config.get("max_concurrent_trades", 5)) - len(formatted_pos)),
                "replace_on_tp": self.config.get("replace_on_tp", True),
                "open_gold_positions": formatted_pos,"""

assert old_status_ret.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_status_ret not found"
code = code.replace(old_status_ret.replace("\r\n", "\n"), new_status_ret) if "\r\n" not in code else code.replace(old_status_ret.replace("\n", "\r\n"), new_status_ret.replace("\n", "\r\n"))

with open("gold_auto_trader.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Part 2 applied successfully!")
