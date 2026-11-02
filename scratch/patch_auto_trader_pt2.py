import re

def patch_gold_auto_trader_pt2():
    with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the execute_gold_order definition start
    target_start = "    def execute_gold_order("
    idx = content.find(target_start)
    if idx == -1:
        print("ERROR: execute_gold_order start not found!")
        return False

    # Find where def _run_auto_loop starts
    loop_start = "    def _run_auto_loop(self):"
    idx2 = content.find(loop_start)
    if idx2 == -1:
        print("ERROR: _run_auto_loop start not found!")
        return False

    new_methods = '''    def execute_twin_gold_orders(
        self,
        action: str,
        lot: float,
        sl: float,
        tp_fixed: float,
        trail_dist: float = 0.0,
        confidence_score: int = 90,
        strategy_name: str = "Gold Intelligence Setup",
        timeframe: str = "M1",
        notes: str = "",
        is_auto: bool = False
    ) -> Dict[str, Any]:
        """
        User Rule: Anytime a trade is opened, open TWICE the trade:
          - Trade 1 (Fixed Target TP): Locks in profit at tp_fixed (e.g. TP1).
          - Trade 2 (Trailing TP): Has no fixed cap, actively trailed by background manager.
        """
        action = action.upper()
        if action not in ["BUY", "SELL"]:
            return {"success": False, "message": f"Invalid order direction: {action}"}

        if mt5 is None:
            return {"success": False, "message": "MetaTrader 5 API not loaded"}

        with self.mt5_lock:
            term = mt5.terminal_info()
            if term is None or not term.connected:
                return {"success": False, "message": "MT5 terminal is disconnected"}

            acc = mt5.account_info()
            if acc is None:
                return {"success": False, "message": "Account info unavailable"}
            if not getattr(acc, "trade_allowed", False) or not getattr(acc, "trade_expert", False):
                return {"success": False, "message": "Account does not permit automated/expert trading"}

            # Twin trade policy: Allow current twin pair (up to 2 positions), but block if >= 2 open
            if self.config.get("single_trade_enforcement", True):
                open_pos = mt5.positions_get(symbol="XAUUSD")
                if open_pos and len(open_pos) >= 2:
                    return {"success": False, "message": "Blocked by Risk Policy: Twin XAUUSD positions are already open (2/2 active)"}

            info = mt5.symbol_info("XAUUSD")
            tick = mt5.symbol_info_tick("XAUUSD")
            if info is None or tick is None:
                return {"success": False, "message": "XAUUSD quotes unavailable"}

            min_lot = info.volume_min
            max_lot = info.volume_max
            step_lot = info.volume_step
            req_lot = max(min_lot, min(lot, max_lot))
            req_lot = round(round(req_lot / step_lot) * step_lot, 2)

            order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if action == "BUY" else tick.bid

            filling_mode = mt5.ORDER_FILLING_IOC
            if info.filling_mode & 1:
                filling_mode = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

            # Trailing distance determination
            if trail_dist <= 0:
                tf_up = timeframe.upper()
                if "M1" in tf_up:
                    trail_dist = float(self.config.get("m1_trail_dist", 3.00))
                elif "M5" in tf_up:
                    trail_dist = float(self.config.get("m5_trail_dist", 4.50))
                else:
                    trail_dist = float(self.config.get("default_trail_dist", 5.00))

            results = []
            tickets = []

            # --- 1. TRADE 1: FIXED TARGET TP ---
            req1 = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD",
                "volume": req_lot,
                "type": order_type,
                "price": price,
                "sl": round(float(sl), info.digits) if sl > 0 else 0.0,
                "tp": round(float(tp_fixed), info.digits) if tp_fixed > 0 else 0.0,
                "deviation": 40,
                "magic": 777101,  # Fixed TP leg
                "comment": f"G1-FIX-{confidence_score}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode
            }

            try:
                res1 = mt5.order_send(req1)
            except Exception as e:
                return {"success": False, "message": f"Order 1 send exception: {e}"}

            if res1 is None or res1.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                err_code = getattr(res1, "retcode", -1) if res1 else "None"
                err_comment = getattr(res1, "comment", "Order failed") if res1 else "No response"
                msg = f"Trade 1 (Fixed TP) rejected by broker (code {err_code}): {err_comment}"
                self._append_log({
                    "type": "ORDER_REJECTED",
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "status": "ERROR",
                    "message": msg
                })
                return {"success": False, "message": msg}

            fill1_price = float(res1.price or price)
            t1 = int(res1.order)
            tickets.append(t1)
            results.append({"ticket": t1, "type": "FIXED_TP", "fill_price": fill1_price, "tp": tp_fixed, "sl": sl})

            # 0.15s pause before sending twin trade
            time.sleep(0.15)

            # --- 2. TRADE 2: DYNAMIC TRAILING TP RUNNER ---
            tick2 = mt5.symbol_info_tick("XAUUSD")
            price2 = (tick2.ask if action == "BUY" else tick2.bid) if tick2 else price

            req2 = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD",
                "volume": req_lot,
                "type": order_type,
                "price": price2,
                "sl": round(float(sl), info.digits) if sl > 0 else 0.0,
                "tp": 0.0,  # Open-ended: managed by active trailing stop!
                "deviation": 40,
                "magic": 777102,  # Trailing TP leg
                "comment": f"G2-TRL-{confidence_score}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode
            }

            try:
                res2 = mt5.order_send(req2)
            except Exception as e:
                res2 = None

            t2 = None
            if res2 and res2.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                fill2_price = float(res2.price or price2)
                t2 = int(res2.order)
                tickets.append(t2)
                results.append({"ticket": t2, "type": "TRAILING_TP", "fill_price": fill2_price, "trail_dist": trail_dist, "sl": sl})

                # Register Trade 2 in active trailing manager
                with self.lock:
                    self.trailing_positions[t2] = {
                        "ticket": t2,
                        "action": action,
                        "volume": req_lot,
                        "entry": fill2_price,
                        "initial_sl": sl,
                        "current_sl": sl,
                        "trail_dist": trail_dist,
                        "timeframe": timeframe,
                        "strategy": strategy_name,
                        "be_moved": False,
                        "highest_favorable": fill2_price
                    }

            # Optional link with Profit Chaser Option B
            if self.config.get("enable_profit_chaser", True) and self.profit_chaser:
                for t, item in zip(tickets, results):
                    try:
                        self.profit_chaser.register_position(
                            ticket=t,
                            symbol="XAUUSD",
                            direction=action,
                            entry_price=item.get("fill_price", price),
                            lot_size=req_lot,
                            stop_loss=sl,
                            take_profit=item.get("tp", 0.0)
                        )
                    except Exception:
                        pass

            self.daily_trades_count += len(tickets)
            log_item = {
                "type": "TWIN_AUTO_TRADE_FILLED" if is_auto else "TWIN_MANUAL_TRADE_FILLED",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "FILLED",
                "tickets": tickets,
                "direction": action,
                "lot": req_lot,
                "timeframe": timeframe,
                "strategy": strategy_name,
                "sl": sl,
                "tp_fixed": tp_fixed,
                "trail_dist": trail_dist,
                "confidence": confidence_score,
                "message": f"Twin Trades Filled: #{t1} (Fixed TP {tp_fixed}) & #{t2 or 'N/A'} (Dynamic Trailing TP, trail ${trail_dist:.2f}/oz)"
            }
            self._append_log(log_item)

            return {
                "success": True,
                "twin_trade": True,
                "tickets": tickets,
                "trade_fixed": results[0] if len(results) > 0 else None,
                "trade_trailing": results[1] if len(results) > 1 else None,
                "fill_price": fill1_price,
                "message": f"Successfully executed TWIN TRADES on XAUUSD:\\n• Trade 1 (#{t1}): Fixed TP @ {tp_fixed}\\n• Trade 2 (#{t2 or 'N/A'}): Dynamic Trailing TP (${trail_dist:.2f}/oz trail)"
            }

    def execute_gold_order(
        self,
        action: str,
        lot: float,
        sl: float,
        tp: float,
        confidence_score: int,
        strategy_name: str,
        notes: str = "",
        is_auto: bool = False
    ) -> Dict[str, Any]:
        """
        Executes Gold trade. If twin_trade_enabled is True, automatically executes
        both Trade 1 (Fixed TP) and Trade 2 (Trailing TP).
        """
        if self.config.get("twin_trade_enabled", True):
            tf = "M1" if "M1" in strategy_name else ("M5" if "M5" in strategy_name else "M15")
            return self.execute_twin_gold_orders(
                action=action,
                lot=lot,
                sl=sl,
                tp_fixed=tp,
                trail_dist=0.0,
                confidence_score=confidence_score,
                strategy_name=strategy_name,
                timeframe=tf,
                notes=notes,
                is_auto=is_auto
            )

        # Fallback single trade if explicitly configured
        action = action.upper()
        if action not in ["BUY", "SELL"]:
            return {"success": False, "message": f"Invalid order direction: {action}"}

        if mt5 is None:
            return {"success": False, "message": "MetaTrader 5 API not loaded"}

        with self.mt5_lock:
            term = mt5.terminal_info()
            if term is None or not term.connected:
                return {"success": False, "message": "MT5 terminal is disconnected"}

            acc = mt5.account_info()
            if acc is None:
                return {"success": False, "message": "Account info unavailable"}
            if not getattr(acc, "trade_allowed", False) or not getattr(acc, "trade_expert", False):
                return {"success": False, "message": "Account does not permit automated/expert trading"}

            if self.config.get("single_trade_enforcement", True):
                open_pos = mt5.positions_get(symbol="XAUUSD")
                if open_pos and len(open_pos) > 0:
                    return {"success": False, "message": "Blocked by Policy: An active XAUUSD trade is already open"}

            info = mt5.symbol_info("XAUUSD")
            tick = mt5.symbol_info_tick("XAUUSD")
            if info is None or tick is None:
                return {"success": False, "message": "XAUUSD quotes unavailable"}

            min_lot = info.volume_min
            max_lot = info.volume_max
            step_lot = info.volume_step
            req_lot = max(min_lot, min(lot, max_lot))
            req_lot = round(round(req_lot / step_lot) * step_lot, 2)

            order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if action == "BUY" else tick.bid

            filling_mode = mt5.ORDER_FILLING_IOC
            if info.filling_mode & 1:
                filling_mode = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD",
                "volume": req_lot,
                "type": order_type,
                "price": price,
                "sl": round(float(sl), info.digits) if sl > 0 else 0.0,
                "tp": round(float(tp), info.digits) if tp > 0 else 0.0,
                "deviation": 40,
                "magic": 777100,
                "comment": f"GOLD-AI-{action[:1]}-{confidence_score}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode
            }

            try:
                res = mt5.order_send(request)
            except Exception as e:
                return {"success": False, "message": f"Order send exception: {e}"}

            if res is None or res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                err_code = getattr(res, "retcode", -1) if res else "None"
                err_comment = getattr(res, "comment", "Order failed") if res else "No response"
                msg = f"Order rejected by broker (code {err_code}): {err_comment}"
                return {"success": False, "message": msg}

            fill_price = float(res.price or price)
            fill_volume = float(res.volume or req_lot)
            ticket = int(res.order)

            self.daily_trades_count += 1
            return {
                "success": True,
                "ticket": ticket,
                "fill_price": fill_price,
                "fill_volume": fill_volume,
                "message": f"Filled {action} {fill_volume} lot XAUUSD at {fill_price} (Ticket #{ticket})"
            }

    def _run_trailing_loop(self):
        """Dedicated high-frequency daemon loop managing dynamic trailing stops for Trade 2."""
        while self.running:
            try:
                self._update_trailing_stops()
            except Exception as e:
                pass
            time.sleep(1.5)

    def _update_trailing_stops(self):
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
                        del self.trailing_positions[t]

            # Also auto-enroll any position with comment containing G2 or TRL or tp == 0
            for p in open_pos:
                comment = getattr(p, "comment", "") or ""
                if ("G2" in comment or "TRL" in comment or p.tp == 0.0) and p.ticket not in self.trailing_positions:
                    action = "BUY" if p.type == 0 else "SELL"
                    with self.lock:
                        self.trailing_positions[p.ticket] = {
                            "ticket": p.ticket,
                            "action": action,
                            "volume": p.volume,
                            "entry": p.price_open,
                            "initial_sl": p.sl,
                            "current_sl": p.sl,
                            "trail_dist": 3.50,
                            "timeframe": "M1",
                            "strategy": "Trailing Runner",
                            "be_moved": False,
                            "highest_favorable": p.price_open
                        }

            tick = mt5.symbol_info_tick("XAUUSD")
            if not tick:
                return

            bid = tick.bid
            ask = tick.ask
            spread = ask - bid

            for ticket, tr_state in list(self.trailing_positions.items()):
                p = pos_by_ticket.get(ticket)
                if not p:
                    continue

                action = tr_state["action"]
                entry = tr_state["entry"]
                initial_sl = tr_state.get("initial_sl", p.sl)
                current_sl = p.sl
                trail_dist = tr_state.get("trail_dist", 3.50)
                risk_pts = abs(entry - initial_sl) if initial_sl > 0 else 5.0
                be_trigger = max(1.50, risk_pts * 0.8)

                if action == "BUY":
                    favorable_gain = bid - entry
                    if favorable_gain > (tr_state.get("highest_favorable", entry) - entry):
                        tr_state["highest_favorable"] = bid

                    # 1. Break-Even Check: Once price moves +1.0R (or +$2.50)
                    if favorable_gain >= be_trigger and not tr_state.get("be_moved", False):
                        be_sl = round(entry + spread + 0.20, 2)
                        if be_sl > current_sl:
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": "XAUUSD",
                                "sl": be_sl,
                                "tp": p.tp
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                tr_state["be_moved"] = True
                                tr_state["current_sl"] = be_sl
                                event_msg = f"🛡️ Trade 2 (#{ticket}) moved to Break-Even @ {be_sl} (+{favorable_gain:.2f}/oz profit protected)"
                                print(event_msg)
                                self.trailing_events_log.insert(0, {
                                    "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                                    "ticket": ticket,
                                    "event": "BREAK_EVEN",
                                    "new_sl": be_sl,
                                    "message": event_msg
                                })

                    # 2. Dynamic Trailing SL Ratchet
                    calc_trail_sl = round(bid - trail_dist, 2)
                    if calc_trail_sl > (current_sl + 0.40) and calc_trail_sl > entry:
                        req = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": ticket,
                            "symbol": "XAUUSD",
                            "sl": calc_trail_sl,
                            "tp": p.tp
                        }
                        res = mt5.order_send(req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            tr_state["current_sl"] = calc_trail_sl
                            locked_profit = calc_trail_sl - entry
                            event_msg = f"🎯 Trailing SL ratcheted for #{ticket} BUY to {calc_trail_sl} (Secured profit: +${locked_profit:.2f}/oz)"
                            print(event_msg)
                            self.trailing_events_log.insert(0, {
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                                "ticket": ticket,
                                "event": "TRAILING_SL_UPDATE",
                                "new_sl": calc_trail_sl,
                                "message": event_msg
                            })

                elif action == "SELL":
                    favorable_gain = entry - ask
                    if favorable_gain > (entry - tr_state.get("highest_favorable", entry)):
                        tr_state["highest_favorable"] = ask

                    # 1. Break-Even Check: Once price drops +1.0R (or +$2.50)
                    if favorable_gain >= be_trigger and not tr_state.get("be_moved", False):
                        be_sl = round(entry - spread - 0.20, 2)
                        if current_sl == 0.0 or be_sl < current_sl:
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": "XAUUSD",
                                "sl": be_sl,
                                "tp": p.tp
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                tr_state["be_moved"] = True
                                tr_state["current_sl"] = be_sl
                                event_msg = f"🛡️ Trade 2 (#{ticket}) moved to Break-Even @ {be_sl} (+{favorable_gain:.2f}/oz profit protected)"
                                print(event_msg)
                                self.trailing_events_log.insert(0, {
                                    "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                                    "ticket": ticket,
                                    "event": "BREAK_EVEN",
                                    "new_sl": be_sl,
                                    "message": event_msg
                                })

                    # 2. Dynamic Trailing SL Ratchet
                    calc_trail_sl = round(ask + trail_dist, 2)
                    if (current_sl == 0.0 or calc_trail_sl < (current_sl - 0.40)) and calc_trail_sl < entry:
                        req = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": ticket,
                            "symbol": "XAUUSD",
                            "sl": calc_trail_sl,
                            "tp": p.tp
                        }
                        res = mt5.order_send(req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            tr_state["current_sl"] = calc_trail_sl
                            locked_profit = entry - calc_trail_sl
                            event_msg = f"🎯 Trailing SL ratcheted for #{ticket} SELL to {calc_trail_sl} (Secured profit: +${locked_profit:.2f}/oz)"
                            print(event_msg)
                            self.trailing_events_log.insert(0, {
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                                "ticket": ticket,
                                "event": "TRAILING_SL_UPDATE",
                                "new_sl": calc_trail_sl,
                                "message": event_msg
                            })

    def evaluate_and_execute_auto_trades(self) -> Dict[str, Any]:
        """Core cycle: scans Gold conditions, validates criteria, and auto-executes high-confidence setups."""
        cur_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.last_eval_time = cur_time

        # Update daily date if rolled over
        cur_d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if cur_d != self.today_date:
            self.today_date = cur_d
            self.daily_trades_count = 0

        # Gate 1: Enabled
        if not self.config.get("enabled", False):
            self.last_eval_status = "STANDBY"
            self.last_eval_message = "Gold Auto-Trading is paused/disabled by user."
            return {"status": "STANDBY", "message": self.last_eval_message}

        # Gate 2: Twin Trade Policy Check (Allow up to 2 open positions for 1 active twin setup)
        if self.config.get("single_trade_enforcement", True):
            open_gold = self.get_open_gold_positions()
            if open_gold and len(open_gold) >= 2:
                self.last_eval_status = "MONITORING_OPEN_TRADE"
                pos_summaries = [f"#{p.ticket} ({'BUY' if p.type == 0 else 'SELL'} ${p.profit:.2f})" for p in open_gold[:2]]
                self.last_eval_message = f"Active Twin Trades open: {', '.join(pos_summaries)}. Trailing manager active."
                return {"status": "MONITORING_OPEN_TRADE", "message": self.last_eval_message}

        # Gate 3: Max Daily Trades Cap
        max_daily = self.config.get("max_daily_trades", 6)
        if self.daily_trades_count >= max_daily:
            self.last_eval_status = "DAILY_CAP_REACHED"
            self.last_eval_message = f"Daily Gold trade cap reached ({self.daily_trades_count}/{max_daily} legs). Capital preservation active until tomorrow."
            return {"status": "DAILY_CAP_REACHED", "message": self.last_eval_message}

        # Gate 4: News Blackout
        is_news, news_reason = self.is_news_blackout_active()
        if is_news:
            self.last_eval_status = "NEWS_BLACKOUT"
            self.last_eval_message = f"Auto-Execution paused: {news_reason}"
            return {"status": "NEWS_BLACKOUT", "message": self.last_eval_message}

        # Gate 5: Scan Setups
        try:
            setups = generate_gold_trade_setups()
        except Exception as e:
            self.last_eval_status = "ERROR"
            self.last_eval_message = f"Setup generation error: {e}"
            return {"status": "ERROR", "message": self.last_eval_message}

        if not setups:
            self.last_eval_status = "SCANNING"
            self.last_eval_message = "No setups currently generated."
            return {"status": "SCANNING", "message": self.last_eval_message}

        # Filter strictly for valid BUY/SELL setups with confidence >= min_confidence (90-100%)
        min_conf = self.config.get("min_confidence", 90)
        tf_filter = self.config.get("timeframe_filter", "M1_M5")

        actionable_setups = [
            s for s in setups
            if s.get("direction") in ["BUY", "SELL"]
            and s.get("confidence_score", 0) >= min_conf
        ]

        # Prioritize or filter by chosen timeframe
        if tf_filter == "M1":
            actionable_setups = [s for s in actionable_setups if s.get("timeframe") == "M1"]
        elif tf_filter == "M5":
            actionable_setups = [s for s in actionable_setups if s.get("timeframe") == "M5"]
        elif tf_filter == "M1_M5":
            fast_setups = [s for s in actionable_setups if s.get("timeframe") in ["M1", "M5"]]
            if fast_setups:
                actionable_setups = fast_setups

        if not actionable_setups:
            self.last_eval_status = "FILTERING"
            top_conf = max([s.get("confidence_score", 0) for s in setups]) if setups else 0
            self.last_eval_message = f"No setups meet criteria ({tf_filter} filter, >={min_conf}% conf). Awaiting institutional trigger."
            return {"status": "FILTERING", "message": self.last_eval_message}

        # Sort by confidence score
        actionable_setups.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        chosen = actionable_setups[0]
        lot = self.config.get("lot_size", 0.01)

        # Trigger Twin Order Execution (1 Fixed TP + 1 Trailing TP)
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
            return {"status": "EXECUTION_BLOCKED", "message": self.last_eval_message}

'''

    content = content[:idx] + new_methods + content[idx2:]

    # Also update get_status to return trailing details
    status_target = '            return {\n                "enabled": self.config.get("enabled", False),'
    status_replacement = '''            tr_list = []
            for t, tr in self.trailing_positions.items():
                p = next((x for x in open_pos if x.ticket == t), None)
                tr_list.append({
                    "ticket": t,
                    "action": tr.get("action"),
                    "entry": tr.get("entry"),
                    "current_sl": tr.get("current_sl"),
                    "trail_dist": tr.get("trail_dist"),
                    "timeframe": tr.get("timeframe"),
                    "be_moved": tr.get("be_moved"),
                    "floating_profit": round(float(p.profit), 2) if p else 0.0
                })

            return {
                "enabled": self.config.get("enabled", False),
                "twin_trade_enabled": self.config.get("twin_trade_enabled", True),
                "timeframe_filter": self.config.get("timeframe_filter", "M1_M5"),
                "trailing_positions": tr_list,
                "trailing_events": list(self.trailing_events_log[:15]),'''

    if status_target in content:
        content = content.replace(status_target, status_replacement, 1)
        print("Updated get_status in gold_auto_trader.py")

    with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Part 2 applied to gold_auto_trader.py!")
    return True

if __name__ == '__main__':
    patch_gold_auto_trader_pt2()
