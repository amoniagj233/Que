import urllib.request
import json
import time

base_url = "http://127.0.0.1:8765"
t0 = time.time()
req = urllib.request.urlopen(base_url + "/api/ml/overview", timeout=20)
body = json.loads(req.read().decode('utf-8'))
print(f"Elapsed: {time.time()-t0:.2f}s")
print("Model Version:", body.get("model_version"))
print("Current Regime:", body.get("current_regime"))
print("Accuracy:", body.get("accuracy"))
print("Brier Score:", body.get("brier_score"))
print("ROC-AUC:", body.get("roc_auc"))
print("MTF Confluence:", body.get("mtf_confluence"))
print("Spread Pts:", body.get("spread_pts"))
