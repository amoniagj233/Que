import urllib.request
import json
import time

def check():
    for i in range(10):
        try:
            req = urllib.request.Request('http://127.0.0.1:8765/api/gold/auto_trade/status')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                print(f"Gold Auto-Trade Status: {data.get('eval_status')} | Message: {data.get('eval_message')}")
                print(f"Config: {data.get('config')}")
                print(f"Open Gold Position in MT5: {len(data.get('open_positions', []))}")
                return True
        except Exception as e:
            print(f"Waiting for server ({i+1}/10): {e}")
            time.sleep(2)
    return False

if __name__ == '__main__':
    check()
