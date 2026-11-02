import urllib.request
import json

def check():
    req = urllib.request.Request('http://127.0.0.1:8765/api/setups')
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        setups = data.get('setups', [])
        print(f"Total Setups: {len(setups)}")
        for s in setups:
            print(f"- [{s.get('symbol')}] Action: {s.get('action')}, Conf: {s.get('confidence_score')}%, Entry: {s.get('entry')}, SL: {s.get('sl')}, TP1: {s.get('tp1')}, Dist: {s.get('stop_dist')} | Signals: {s.get('technical_signals')[:60]}")
        filtered = data.get('filtered_reasons', {})
        print(f"\nFiltered Reasons count: {len(filtered)}")
        for k, v in list(filtered.items())[:6]:
            print(f"  {k}: {v}")

if __name__ == '__main__':
    check()
