import urllib.request
import json

base = "http://localhost:8765"

# 1. Test auto trade status
try:
    with urllib.request.urlopen(f"{base}/api/gold/auto_trade/status") as res:
        st = json.loads(res.read().decode())
        print("Auto-Trade Status:")
        print(f"  Enabled: {st.get('enabled')}")
        print(f"  Twin Trade Mode: {st.get('twin_trade_enabled')}")
        print(f"  Timeframe Filter: {st.get('timeframe_filter')}")
        print(f"  Trailing Positions: {len(st.get('trailing_positions', []))}")
        print(f"  Open Gold Positions: {len(st.get('open_gold_positions', []))}")
        for p in st.get('open_gold_positions', []):
            print(f"    #{p['ticket']} {p['direction']} {p['lot']} lot @ {p['entry']} (SL: {p['sl']}, TP: {p['tp']}, P&L: ${p['profit']})")
except Exception as e:
    print(f"Error fetching status: {e}")

# 2. Test setups
try:
    with urllib.request.urlopen(f"{base}/api/gold/setups") as res:
        setups = json.loads(res.read().decode())
        print(f"\nSetups Count: {len(setups)}")
        for s in setups:
            print(f"  [{s['timeframe']}] {s['strategy']}: {s['direction']} Entry {s['entry']} SL {s['sl']} TP1 {s['tp1']} (Conf: {s['confidence_score']}%)")
except Exception as e:
    print(f"Error fetching setups: {e}")

# 3. Test HTML page contains Terminal elements
try:
    with urllib.request.urlopen(f"{base}/") as res:
        html = res.read().decode('utf-8', errors='ignore')
        has_terminal = "GOLD HIGH-FREQUENCY TRADING TERMINAL" in html
        has_twin_func = "executeManualGoldTrade" in html
        has_twin_btn = "BUY XAUUSD (TWIN TRADE)" in html
        print(f"\nHTML Verification:")
        print(f"  Contains Gold Trading Terminal: {has_terminal}")
        print(f"  Contains executeManualGoldTrade: {has_twin_func}")
        print(f"  Contains Twin Trade Buy Button: {has_twin_btn}")
except Exception as e:
    print(f"Error checking HTML: {e}")
