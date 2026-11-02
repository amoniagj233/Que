import urllib.request
import json
import time

for i in range(10):
    try:
        req = urllib.request.Request('http://127.0.0.1:8765/api/gold/setups')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"API Online! Total setups returned: {len(data)}")
            for s in data:
                strat = s.get("strategy")
                direction = s.get("direction")
                conf = s.get("confidence_score")
                entry = s.get("entry")
                sl = s.get("sl")
                tp1 = s.get("tp1")
                print(f"  - [{strat}] {direction} (Conviction: {conf}%) Entry: {entry}, SL: {sl}, TP1: {tp1}")
            break
    except Exception as e:
        print(f"Waiting ({i+1}/10): {e}")
        time.sleep(2)
