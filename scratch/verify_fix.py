import urllib.request
import json
import time

time.sleep(1.0)
base = "http://localhost:8765"

# 1. Test index page
with urllib.request.urlopen(f"{base}/") as res:
    print(f"GET / -> Status: {res.status}, Length: {len(res.read())}")

# 2. Test state
with urllib.request.urlopen(f"{base}/api/state") as res:
    state = json.loads(res.read().decode())
    print(f"GET /api/state -> Connected: {state.get('connected')}, Balance: {state.get('account', {}).get('balance')}, Equity: {state.get('account', {}).get('equity')}")

# 3. Test gold status
with urllib.request.urlopen(f"{base}/api/gold/auto_trade/status") as res:
    st = json.loads(res.read().decode())
    print(f"GET /api/gold/auto_trade/status -> Enabled: {st.get('enabled')}, Open Positions: {len(st.get('open_gold_positions', []))}")

# 4. Test setups
with urllib.request.urlopen(f"{base}/api/gold/setups") as res:
    setups = json.loads(res.read().decode())
    print(f"GET /api/gold/setups -> Setups: {len(setups)}")

# 5. Test M1 & M5 candles
with urllib.request.urlopen(f"{base}/api/gold/candles?tf=M1&count=5") as res:
    candles_m1 = json.loads(res.read().decode())
    print(f"GET /api/gold/candles?tf=M1 -> {len(candles_m1)} candles")

with urllib.request.urlopen(f"{base}/api/gold/candles?tf=M5&count=5") as res:
    candles_m5 = json.loads(res.read().decode())
    print(f"GET /api/gold/candles?tf=M5 -> {len(candles_m5)} candles")
