with open("run_apex_commander.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '''    logger.info("APEX AI Commander is fully operational and standing watch 24/7.")

    # 24/7 Autonomous Supervision Loop
    iteration = 0
    while True:'''

replacement = '''    # Step 6: Start Centralized Fleet Risk & High-Win-Rate Execution Engine (Strict 10-cap, 1 trade per bot)
    def fleet_policy_loop():
        from commander.fleet_policy_engine import run_fleet_risk_cycle
        logger.info("Centralized Fleet Policy Engine active: Strictly enforcing Max 10 positions & 1 trade per bot with Smart Asymmetric V2.")
        while True:
            try:
                if bridge.connected:
                    run_fleet_risk_cycle()
                time.sleep(2.5)
            except Exception as e:
                time.sleep(5.0)

    fleet_thread = threading.Thread(target=fleet_policy_loop, daemon=True, name="fleet-policy-engine")
    fleet_thread.start()

    logger.info("APEX AI Commander is fully operational and standing watch 24/7.")

    # 24/7 Autonomous Supervision Loop
    iteration = 0
    while True:'''

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open("run_apex_commander.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Embedded Fleet Policy Engine directly into run_apex_commander.py!")
