import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8765/api/profit_chaser/dashboard')
with urllib.request.urlopen(req, timeout=5) as resp:
    data = json.loads(resp.read().decode())
    positions = data.get('positions', [])
    print(f"Tracked Positions in Profit Chaser: {len(positions)}")
    found = False
    for p in positions:
        if p.get('ticket') == 857169226 or p.get('symbol') == 'XAUUSD':
            print(f"Ticket #{p.get('ticket')}: {p.get('symbol')} {p.get('direction')} Entry: {p.get('entry_price')}, State: {p.get('state')}, Peak: ${p.get('peak_profit')}, Unrealized: ${p.get('unrealized_profit')}")
            found = True
    if not found:
        print("Ticket 857169226 not yet registered in profit chaser memory.")
