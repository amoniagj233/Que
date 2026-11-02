def add_route():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = '        elif url.path == "/api/gold/setups":'
    replacement = '''        elif url.path == "/api/gold/candles":
            qs = parse_qs(url.query)
            tf = qs.get("tf", ["M15"])[0].upper()
            count = int(qs.get("count", ["150"])[0])
            with mt5_lock:
                df = get_gold_candles(tf, count=count)
            candles = []
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    try:
                        t = int(pd.to_datetime(row['time']).timestamp())
                        candles.append({
                            "time": t,
                            "open": float(row['open']),
                            "high": float(row['high']),
                            "low": float(row['low']),
                            "close": float(row['close']),
                            "volume": float(row.get('tick_volume', row.get('volume', 0)))
                        })
                    except Exception:
                        pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(candles).encode("utf-8"))
        elif url.path == "/api/gold/setups":'''

    if target not in content:
        print("ERROR: target not found!")
        return False

    content = content.replace(target, replacement, 1)

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Added /api/gold/candles route!")
    return True

if __name__ == '__main__':
    add_route()
