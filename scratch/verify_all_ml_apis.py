import urllib.request
import json
import time

time.sleep(2)  # brief wait for server bind

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
passed = 0

for ep in endpoints:
    t0 = time.time()
    try:
        req = urllib.request.urlopen(base_url + ep, timeout=25)
        status = req.getcode()
        body = json.loads(req.read().decode('utf-8'))
        ok = body.get("success", False)
        elapsed = time.time() - t0
        print(f"[{status}] {ep} -> success={ok} ({elapsed:.2f}s)")
        if status == 200:
            passed += 1
    except Exception as e:
        print(f"[FAIL] {ep} -> {e}")

print(f"\nFinal Score: {passed} / {len(endpoints)} ML Endpoints Responding HTTP 200 OK")
