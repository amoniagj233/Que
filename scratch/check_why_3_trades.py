import MetaTrader5 as mt5
import json
import urllib.request

def run():
    if not mt5.initialize():
        print("MT5 failed to init")
        return

    acc = mt5.account_info()
    pos = mt5.positions_get()

    print("=== ACCOUNT INFO ===")
    print(f"Balance: {acc.balance}, Equity: {acc.equity}, Free Margin: {acc.margin_free}, Margin Level: {acc.margin_level}%")

    print("\n=== OPEN POSITIONS ===")
    print(f"Count: {len(pos) if pos else 0}")
    if pos:
        for p in pos:
            direction = "BUY" if p.type == 0 else "SELL"
            print(f"Ticket #{p.ticket}: {p.symbol} {direction} vol={p.volume} open_p={p.price_open} sl={p.sl} tp={p.tp} profit={p.profit}")

    mt5.shutdown()

    print("\n=== SCANNER STATUS & FILTERED REASONS ===")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/setups", timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"Active Setups shown: {len(data.get('setups', []))}")
            for s in data.get('setups', []):
                print(f"  - {s.get('symbol')}: Action={s.get('action')}, Conf={s.get('confidence_score')}%, Open={s.get('is_market_open')}")
            print("\nFiltered reasons:")
            for sym, reason in data.get('filtered_reasons', {}).items():
                print(f"  - {sym}: {reason}")
    except Exception as e:
        print("Failed to reach web_app api:", e)

if __name__ == '__main__':
    run()
