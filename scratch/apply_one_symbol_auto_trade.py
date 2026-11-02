with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update interval default to 60 seconds
text = text.replace("def __init__(self, interval_seconds=180):", "def __init__(self, interval_seconds=60):", 1)

# 2. Update _run_loop to actively re-scan when auto_trade_enabled is True
old_run_loop = """    def _run_loop(self):
        \"\"\"Initial startup scan, then re-scans ONLY if auto_rescan_enabled is True or user clicks Re-Scan.\"\"\"
        time.sleep(1)
        self.run_scan_now()
        
        while self.running:
            if not self.auto_rescan_enabled:
                time.sleep(1.0)
                continue
            for _ in range(self.interval):
                if not self.running or not self.auto_rescan_enabled:
                    break
                time.sleep(1)
                with self.lock:
                    if self.next_scan_seconds > 0:
                        self.next_scan_seconds -= 1
            if self.running and self.auto_rescan_enabled:
                self.run_scan_now()"""

new_run_loop = """    def _run_loop(self):
        \"\"\"Initial startup scan, then re-scans automatically when auto_trade_enabled or auto_rescan_enabled is True.\"\"\"
        time.sleep(1)
        self.run_scan_now()
        
        while self.running:
            if not self.auto_trade_enabled and not self.auto_rescan_enabled:
                time.sleep(1.0)
                continue
            for _ in range(self.interval):
                if not self.running or (not self.auto_trade_enabled and not self.auto_rescan_enabled):
                    break
                time.sleep(1)
                with self.lock:
                    if self.next_scan_seconds > 0:
                        self.next_scan_seconds -= 1
            if self.running and (self.auto_trade_enabled or self.auto_rescan_enabled):
                self.run_scan_now()"""

if old_run_loop in text:
    text = text.replace(old_run_loop, new_run_loop, 1)
    print("[+] Updated _run_loop.")
else:
    print("[!] old_run_loop not found directly, checking normalized...")
    norm_text = text.replace("\r\n", "\n")
    norm_old = old_run_loop.replace("\r\n", "\n")
    norm_new = new_run_loop.replace("\r\n", "\n")
    if norm_old in norm_text:
        text = norm_text.replace(norm_old, norm_new, 1)
        print("[+] Updated _run_loop with normalized line endings.")

# 3. In run_scan_now, enforce strictly 1 symbol at a time and sort by confidence
old_auto_exec = """                # ULTRA-HIGH CONFIDENCE AUTOMATIC EXECUTION (Rule 3: 90-100% Threshold Only - Exactly 1 Trade Per Symbol)
                if is_open and confidence_score >= 90 and self.auto_trade_enabled:
                    # Risk gate: Disallow automatic execution on Priority 5 (AVOID) symbols with severe historical losses
                    if setup_obj.get("symbol_perf", {}).get("priority_num") == 5:
                        filtered_reasons[sym] = f"Auto-Execution blocked: {sym} has historical Priority 5 (AVOID) status (Severe Loss Skew/Drawdown). Manual confirmation required."
                        valid_setups.append(setup_obj)
                        continue

                    # Mandatory Risk Verification before execution
                    risk_checks_passed = (
                        margin_free >= 500.0 and
                        (margin_level >= 200.0 or margin_level == 0.0) and
                        len(positions) + 1 <= MAX_OPEN_POSITIONS and
                        calc_lot >= info.volume_min and
                        sl > 0 and tp1 > 0 and tp2 > 0
                    )

                    if risk_checks_passed:
                        # Router rechecks current account risk and capacity for every group/leg.
                        order_res = execute_multi_tp_group(
                            symbol=sym,
                            action=bias,
                            ref_balance=balance,
                            default_lot=0.01,
                            ai_notes=f"Auto-Execution (88-100 rule score): {tech_signals}",
                            confidence_score=confidence_score,
                            prevent_duplicate=True,
                        )
                        if order_res.get("success"):
                            setup_obj["status"] = "EXECUTED"
                            setup_obj["group_id"] = order_res.get("group_id")
                            continue
                        else:
                            filtered_reasons[sym] = f"Auto-Execution Failed: {order_res.get('message')}"
                            valid_setups.append(setup_obj)
                    else:
                        filtered_reasons[sym] = "High-Confidence Setup blocked by Mandatory Margin/Risk Limits"
                        valid_setups.append(setup_obj)
                else:
                    valid_setups.append(setup_obj)"""

new_auto_exec = """                # ULTRA-HIGH CONFIDENCE AUTOMATIC EXECUTION (90-100% Threshold Only - Exactly 1 Trade Per Symbol & One Symbol at a Time)
                if is_open and confidence_score >= 90 and self.auto_trade_enabled:
                    # Rule: Take trade automatically one symbol at a time
                    if auto_trade_executed_this_pass:
                        setup_obj["notes"] += " [Queued: Taking 1 symbol at a time]"
                        valid_setups.append(setup_obj)
                        continue

                    # Risk gate: Disallow automatic execution on Priority 5 (AVOID) symbols with severe historical losses
                    if setup_obj.get("symbol_perf", {}).get("priority_num") == 5:
                        filtered_reasons[sym] = f"Auto-Execution blocked: {sym} has historical Priority 5 (AVOID) status (Severe Loss Skew/Drawdown). Manual confirmation required."
                        valid_setups.append(setup_obj)
                        continue

                    # Live verification: ensure symbol has NO open position in MT5 (Strictly 1 Trade Per Symbol)
                    fresh_positions = mt5.positions_get()
                    if fresh_positions and any(p.symbol == sym for p in fresh_positions):
                        filtered_reasons[sym] = f"Blocked: Exactly 1 trade per symbol allowed ({sym} already has an open position)"
                        continue

                    # Mandatory Risk Verification before execution
                    risk_checks_passed = (
                        margin_free >= 500.0 and
                        (margin_level >= 200.0 or margin_level == 0.0) and
                        len(positions) + 1 <= MAX_OPEN_POSITIONS and
                        calc_lot >= info.volume_min and
                        sl > 0 and tp1 > 0 and tp2 > 0
                    )

                    if risk_checks_passed:
                        # Router rechecks current account risk and capacity for every group/leg.
                        order_res = execute_multi_tp_group(
                            symbol=sym,
                            action=bias,
                            ref_balance=balance,
                            default_lot=0.01,
                            ai_notes=f"Auto-Execution (90-100 score, 1 symbol at a time): {tech_signals}",
                            confidence_score=confidence_score,
                            prevent_duplicate=True,
                        )
                        if order_res.get("success"):
                            setup_obj["status"] = "EXECUTED"
                            setup_obj["group_id"] = order_res.get("group_id")
                            auto_trade_executed_this_pass = True
                            valid_setups.append(setup_obj)
                            print(f"[AutoTrader] Successfully opened 1 trade on {sym} ({bias}). Policy: One symbol at a time.")
                            continue
                        else:
                            filtered_reasons[sym] = f"Auto-Execution Failed: {order_res.get('message')}"
                            valid_setups.append(setup_obj)
                    else:
                        filtered_reasons[sym] = "High-Confidence Setup blocked by Mandatory Margin/Risk Limits"
                        valid_setups.append(setup_obj)
                else:
                    valid_setups.append(setup_obj)"""

# Also initialize auto_trade_executed_this_pass = False in run_scan_now
init_marker = "            valid_setups = []\n            filtered_reasons = {}"
init_replacement = "            valid_setups = []\n            filtered_reasons = {}\n            auto_trade_executed_this_pass = False"

norm_text = text.replace("\r\n", "\n")
norm_old_exec = old_auto_exec.replace("\r\n", "\n")
norm_new_exec = new_auto_exec.replace("\r\n", "\n")

if norm_old_exec in norm_text:
    norm_text = norm_text.replace(norm_old_exec, norm_new_exec, 1)
    print("[+] Replaced auto execution block with 'one symbol at a time' logic.")
else:
    print("[!] old_auto_exec not found in text.")

if init_marker in norm_text:
    norm_text = norm_text.replace(init_marker, init_replacement, 1)
    print("[+] Added auto_trade_executed_this_pass initialization.")
else:
    print("[!] init_marker not found.")

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(norm_text)

print("[+] web_app.py updated successfully.")
