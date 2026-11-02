import urllib.request
import json

base_url = "http://127.0.0.1:8765"
for ep in ["/api/ml/overview", "/api/ml/recommendations", "/api/ml/strategies", "/api/ml/mtf", "/api/ml/regime", "/api/ml/train/status", "/api/ml/backtest"]:
    try:
        req = urllib.request.urlopen(base_url + ep, timeout=5)
        body = json.loads(req.read().decode('utf-8'))
        print(f"--- {ep} ---")
        print(body)
    except Exception as e:
        print(f"Error {ep}: {e}")
