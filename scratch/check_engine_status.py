import urllib.request
import json
import time

time.sleep(3.0)
base = "http://localhost:8765"

req = urllib.request.Request(f"{base}/api/gold/auto_trade/status")
with urllib.request.urlopen(req, timeout=5.0) as res:
    st = json.loads(res.read().decode())
    print("Auto-Trader Engine Status:")
    print(f"  Enabled: {st.get('enabled')}")
    print(f"  Target Timeframe: {st.get('timeframe_filter')}")
    print(f"  Min Confidence: {st.get('config', {}).get('min_confidence')}%")
    print(f"  Engine State: {st.get('status')}")
    print(f"  Status Message: {st.get('status_message')}")
    print(f"  Last Check: {st.get('last_eval_time')}")
    print(f"  Daily Trades: {st.get('daily_trades_count')} / {st.get('max_daily_trades')}")
    print(f"\nLive Positions ({len(st.get('open_gold_positions', []))} total):")
    for p in st.get('open_gold_positions', []):
        print(f"  #{p['ticket']}: {p['direction']} {p['lot']} lot @ {p['entry']} | SL: {p['sl']} | TP: {p['tp']} | P&L: ${p['profit']}")
    print(f"\nRecent Execution Logs:")
    for log in st.get('recent_logs', [])[:6]:
        print(f"  [{log.get('time')}] {log.get('type')}: {log.get('message')}")
