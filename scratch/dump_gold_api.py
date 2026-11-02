import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8765/api/gold/auto_trade/status')
with urllib.request.urlopen(req, timeout=5) as resp:
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2))
