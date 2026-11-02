import json

pc = json.load(open('profit_chaser_state.json'))
pos = pc.get('positions', {})
today_pos = {k: v for k, v in pos.items() if str(v.get('entry_time', '')).startswith('2026-10-27')}

total = len(today_pos)
closed = [v for v in today_pos.values() if v.get('state') == 'TRADE_CLOSED']
open_p = [v for v in today_pos.values() if v.get('state') != 'TRADE_CLOSED']

highest_profits = [v.get('highest_profit', 0) for v in today_pos.values()]
final_profits = [v.get('current_profit', 0) for v in today_pos.values()]

print("Total Today:", total)
print("Closed:", len(closed), "Active:", len(open_p))
print("Sum Current/Final Profit:", round(sum(final_profits), 2))
print("Sum Peak Profits:", round(sum(highest_profits), 2))
print("Avg Peak per Trade:", round(sum(highest_profits)/total, 2))

equities = [v.get('entry_equity', 0) for v in today_pos.values() if v.get('entry_equity', 0) > 0]
if equities:
    print("Equity Progression: Min", min(equities), "Max", max(equities))

for p in list(today_pos.values()):
    t = p.get('ticket')
    tm = p.get('entry_time', '')[11:19]
    d = p.get('direction')
    ep = p.get('entry_price')
    hp = p.get('highest_profit')
    cp = p.get('current_profit')
    st = p.get('state')
    pb = p.get('current_pullback_pct')
    print(f"#{t} | {tm} | {d} @ {ep} | Peak: +{hp} | Cur: {cp} | Pullback: {pb}% | {st}")
