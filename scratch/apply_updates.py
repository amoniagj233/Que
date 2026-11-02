import re

with open("gold_auto_trader.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update __init__ and default_cfg
old_init_block = """        self.running = True
        self.trailing_positions: Dict[int, Dict[str, Any]] = {}
        self.trailing_events_log: List[Dict[str, Any]] = []

        self._worker_thread = threading.Thread(target=self._run_auto_loop, daemon=True, name="GoldAutoTraderWorker")
        self._worker_thread.start()

        self._trailing_thread = threading.Thread(target=self._run_trailing_loop, daemon=True, name="GoldTrailingRunnerWorker")
        self._trailing_thread.start()

    def _load_config(self) -> Dict[str, Any]:
        default_cfg = {
            "enabled": False,
            "min_confidence": 90,
            "lot_size": 0.01,
            "tp_mode": "TWIN_FIXED_AND_TRAILING",  # Twin trade: 1 Fixed TP + 1 Trailing TP
            "twin_trade_enabled": True,             # Rule: Anytime a trade opens, open twice (1 Fixed TP, 1 Trailing TP)
            "timeframe_filter": "M1_M5",           # Options: "M1", "M5", "M1_M5", "ALL"
            "m1_trail_dist": 3.00,                 # $3.00/oz trailing distance for M1 scalps
            "m5_trail_dist": 4.50,                 # $4.50/oz trailing distance for M5 momentum
            "default_trail_dist": 5.00,            # $5.00/oz trailing distance for higher TFs
            "news_filter_enabled": True,
            "max_daily_trades": 50,                 # 6 legs (up to 3 twin setups per day)
            "single_trade_enforcement": True,      # Allows 1 twin pair (2 concurrent legs) at a time
            "enable_profit_chaser": True,
            "scan_interval_seconds": 10
        }"""

new_init_block = """        self.running = True
        self.trailing_positions: Dict[int, Dict[str, Any]] = {}
        self.trailing_events_log: List[Dict[str, Any]] = []
        self.known_gold_tickets = set()

        self._worker_thread = threading.Thread(target=self._run_auto_loop, daemon=True, name="GoldAutoTraderWorker")
        self._worker_thread.start()

        self._trailing_thread = threading.Thread(target=self._run_trailing_loop, daemon=True, name="GoldTrailingRunnerWorker")
        self._trailing_thread.start()

    def _load_config(self) -> Dict[str, Any]:
        default_cfg = {
            "enabled": True,
            "min_confidence": 90,
            "lot_size": 0.01,
            "max_concurrent_trades": 5,            # Strict concurrency cap: exactly 5 trades max
            "replace_on_tp": True,                 # Immediately replace on TP
            "tp_mode": "TWIN_FIXED_AND_TRAILING",  # Twin trade: 1 Fixed TP + 1 Trailing TP
            "twin_trade_enabled": True,             # Rule: Anytime a trade opens, open twice (1 Fixed TP, 1 Trailing TP)
            "timeframe_filter": "M1",              # 1MTF trades
            "m1_trail_dist": 3.00,                 # $3.00/oz trailing distance for M1 scalps
            "m5_trail_dist": 4.50,                 # $4.50/oz trailing distance for M5 momentum
            "default_trail_dist": 5.00,            # $5.00/oz trailing distance for higher TFs
            "news_filter_enabled": True,
            "max_daily_trades": 50,
            "single_trade_enforcement": False,
            "enable_profit_chaser": True,
            "scan_interval_seconds": 2
        }"""

assert old_init_block.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_init_block not found"
code = code.replace(old_init_block.replace("\r\n", "\n"), new_init_block) if "\r\n" not in code else code.replace(old_init_block.replace("\n", "\r\n"), new_init_block.replace("\n", "\r\n"))

# 2. Add execute_single_gold_order
single_order_def = '''    def execute_single_gold_order(
        self,
        action: str,
        lot: float,
        sl: float,
        tp: float,
        confidence_score: int,
        strategy_name: str,
        timeframe: str = "M1",
        notes: str = "",
        is_auto: bool = True
    ) -> Dict[str, Any]:
        """Executes a single Gold order to top off positions to exact 5-trade limit."""
        if mt5 is None:
            return {"success": False, "message": "MT5 terminal not available"}

        action = action.upper()
        if action not in ["BUY", "SELL"]:
            return {"success": False, "message": f"Invalid order direction: {action}"}

        with self.mt5_lock:
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

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD",
                "volume": req_lot,
                "type": order_type,
                "price": price,
                "sl": round(float(sl), info.digits) if sl > 0 else 0.0,
                "tp": round(float(tp), info.digits) if tp > 0 else 0.0,
                "deviation": 40,
                "magic": 777111 if timeframe == "M1" else 777101,
                "comment": f"{timeframe}-FIX-{confidence_score}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode
            }

            try:
                res = mt5.order_send(req)
            except Exception as e:
                return {"success": False, "message": f"Order send exception: {e}"}

            if res is None or res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                err_code = getattr(res, "retcode", -1) if res else "None"
                err_comment = getattr(res, "comment", "Order failed") if res else "No response"
                msg = f"Single replacement trade rejected by broker (code {err_code}): {err_comment}"
                return {"success": False, "message": msg}

            fill_price = float(res.price or price)
            t = int(res.order)

            if self.config.get("enable_profit_chaser", True) and self.profit_chaser:
                try:
                    self.profit_chaser.register_position(
                        ticket=t,
                        symbol="XAUUSD",
                        direction=action,
                        entry_price=fill_price,
                        lot_size=req_lot,
                        stop_loss=sl,
                        take_profit=tp
                    )
                except Exception:
                    pass

            self.daily_trades_count += 1
            log_item = {
                "type": "AUTO_REPLACEMENT_TRADE_FILLED" if is_auto else "MANUAL_TRADE_FILLED",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "FILLED",
                "tickets": [t],
                "direction": action,
                "lot": req_lot,
                "timeframe": timeframe,
                "strategy": strategy_name,
                "sl": sl,
                "tp": tp,
                "confidence": confidence_score,
                "message": f"Auto-Replacement Trade #{t} Filled: {action} @ {fill_price} (TP {tp})"
            }
            self._append_log(log_item)

            return {
                "success": True,
                "ticket": t,
                "fill_price": fill_price,
                "message": f"Replacement Trade #{t} Filled ({action} @ {fill_price}, TP {tp})"
            }

'''

target_above_single = '    def execute_gold_order('
assert target_above_single in code, "execute_gold_order not found"
code = code.replace(target_above_single, single_order_def + target_above_single)

with open("gold_auto_trader.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Part 1 applied successfully!")
