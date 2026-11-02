import urllib.request
import json

base = "http://localhost:8765"

# 1. Test setups
try:
    with urllib.request.urlopen(f"{base}/api/gold/setups") as res:
        setups = json.loads(res.read().decode())
        print(f"Server returned {len(setups)} setups:")
        for s in setups:
            print(f"  [{s.get('timeframe')}] {s.get('strategy')} - {s.get('direction')} Entry: {s.get('entry')} SL: {s.get('sl')} TP1: {s.get('tp1')} (Conf: {s.get('confidence_score')}%)")
except Exception as e:
    print(f"Error fetching setups: {e}")

# 2. Test M1 candles
try:
    with urllib.request.urlopen(f"{base}/api/gold/candles?tf=M1&count=5") as res:
        candles_m1 = json.loads(res.read().decode())
        print(f"Server returned {len(candles_m1)} M1 candles. Latest: {candles_m1[-1] if candles_m1 else 'None'}")
except Exception as e:
    print(f"Error fetching M1 candles: {e}")

# 3. Test M5 candles
try:
    with urllib.request.urlopen(f"{base}/api/gold/candles?tf=M5&count=5") as res:
        candles_m5 = json.loads(res.read().decode())
        print(f"Server returned {len(candles_m5)} M5 candles. Latest: {candles_m5[-1] if candles_m5 else 'None'}")
except Exception as e:
    print(f"Error fetching M5 candles: {e}")
