import urllib.request
import json
import time

time.sleep(2.0)
base = "http://localhost:8765"

with urllib.request.urlopen(f"{base}/api/gold/auto_trade/status") as res:
    st = json.loads(res.read().decode())
    print("Auto-Trader Live Status:")
    print(f"  Enabled: {st.get('enabled')}")
    print(f"  Target Timeframe: {st.get('timeframe_filter')}")
    print(f"  Min Confidence: {st.get('config', {}).get('min_confidence')}%")
    print(f"  Engine Status: {st.get('status')}")
    print(f"  Status Message: {st.get('status_message')}")
    print(f"  Open Gold Positions: {len(st.get('open_gold_positions', []))}")
    for p in st.get('open_gold_positions', []):
        print(f"    #{p['ticket']} {p['direction']} {p['lot']} lot @ {p['entry']} (SL: {p['sl']}, TP: {p['tp']}, P&L: ${p['profit']})")
    print(f"  Recent Logs:")
    for log in st.get('recent_logs', [])[:5]:
        print(f"    [{log.get('time')}] {log.get('type')}: {log.get('message')}")
