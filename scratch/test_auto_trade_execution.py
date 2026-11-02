import urllib.request
import json
import time

base_url = "http://127.0.0.1:8765"

# 1. Check auto trade status
req = urllib.request.urlopen(base_url + "/api/state")
state = json.loads(req.read().decode('utf-8'))
scanner_state = state.get("scanner", {})
print("Scanner Status:", scanner_state.get("status"))
print("Scanner Status Message:", scanner_state.get("status_message"))
print("Auto-Trade Enabled:", scanner_state.get("auto_trade_enabled"))
print("Current Setups Count:", len(scanner_state.get("setups", [])))

# 2. Check if any setup was executed or queued
for s in scanner_state.get("setups", []):
    print(f"Setup: {s.get('symbol')} ({s.get('action')}) - Confidence: {s.get('confidence_score')}% - Status: {s.get('status')} - Notes: {s.get('notes')}")

# 3. Check Gold Auto Trader Status
req_gold = urllib.request.urlopen(base_url + "/api/gold/auto_trade/status")
gold_st = json.loads(req_gold.read().decode('utf-8'))
print("\nGold Auto-Trader Status:", gold_st.get("status"))
print("Gold Auto-Trader Message:", gold_st.get("status_message"))
print("Gold Auto-Trader Enabled:", gold_st.get("enabled"))
