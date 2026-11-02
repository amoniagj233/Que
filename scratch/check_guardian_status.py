import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8765/api/profit_guardian/status')
with urllib.request.urlopen(req, timeout=5) as resp:
    data = json.loads(resp.read().decode())
    print("Profit Guardian & Break-Even Status:")
    print("  Tracked positions:", list(data.get("tracked_positions", {}).keys()))
    print("  BE Events:", data.get("be_events"))
    print("  Recent Protections:", data.get("recent_protections"))
