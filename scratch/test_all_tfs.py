import urllib.request
import json

for tf in ['M5', 'M15', 'H1', 'H4']:
    with urllib.request.urlopen(f'http://127.0.0.1:8765/api/gold/candles?tf={tf}&count=2') as r:
        d = json.loads(r.read().decode())
        print(f"Timeframe {tf}: {len(d)} candles loaded, latest close = {d[-1].get('close')}")
