import urllib.request
import json
import time

def check():
    for i in range(10):
        try:
            req = urllib.request.Request('http://127.0.0.1:8765/api/state')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                print(f"Server Online! Status: {data.get('status')}, Scan ID: {data.get('scan_id')}, Setups: {len(data.get('setups', []))}")
                return True
        except Exception as e:
            print(f"Waiting for server ({i+1}/10): {e}")
            time.sleep(2)
    return False

if __name__ == '__main__':
    check()
