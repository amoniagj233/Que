import urllib.request
import json

endpoints = [
    "/api/ml/overview",
    "/api/ml/recommendations",
    "/api/ml/strategies",
    "/api/ml/mtf",
    "/api/ml/regime",
    "/api/ml/models",
    "/api/ml/train/status",
    "/api/ml/backtest",
    "/api/ml/performance",
    "/api/ml/journal",
    "/api/ml/risk",
    "/api/ml/settings"
]

base_url = "http://127.0.0.1:8765"
all_ok = True

for ep in endpoints:
    try:
        req = urllib.request.urlopen(base_url + ep, timeout=5)
        status = req.getcode()
        body = json.loads(req.read().decode('utf-8'))
        success = body.get("success", False)
        print(f"[{status}] {ep} -> success={success}")
        if status != 200:
            all_ok = False
    except Exception as e:
        print(f"[FAIL] {ep} -> {e}")
        all_ok = False

if all_ok:
    print("\nALL 12 ML ENDPOINTS TESTED AND RESPONDING 200 OK!")
else:
    print("\nSOME ENDPOINTS FAILED")
