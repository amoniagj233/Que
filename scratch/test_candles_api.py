import urllib.request
import json
import time

for i in range(10):
    try:
        req = urllib.request.Request('http://127.0.0.1:8765/api/gold/candles?tf=M15&count=5')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"Candles API Online! Candles count: {len(data)}")
            for c in data:
                print(f"  Timestamp: {c.get('time')}, O: {c.get('open')}, H: {c.get('high')}, L: {c.get('low')}, C: {c.get('close')}")
            break
    except Exception as e:
        print(f"Waiting ({i+1}/10): {e}")
        time.sleep(2)
