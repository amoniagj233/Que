import json

pc = json.load(open('profit_chaser_state.json'))
pos = pc.get('positions', {})
print('Total positions in state:', len(pos))

recent_pos = {k: v for k, v in pos.items() if '2026-10-27' in str(v.get('entry_time', '')) or '2026-10-28' in str(v.get('entry_time', ''))}
print(f'Total 10/27 and 10/28 positions: {len(recent_pos)}')

for k, v in sorted(recent_pos.items(), key=lambda x: str(x[1].get('entry_time', ''))):
    t = k
    et = v.get('entry_time')
    sym = v.get('symbol')
    d = v.get('direction')
    ep = v.get('entry_price')
    hp = v.get('highest_profit')
    cp = v.get('current_profit')
    st = v.get('state')
    sl = v.get('stop_loss', v.get('sl', 'N/A'))
    tp = v.get('take_profit', v.get('tp', 'N/A'))
    note = v.get('last_event_note', '')
    print(f"#{t} | {et} | {sym} {d} @ {ep} | Peak: +{hp} | Cur: {cp} | SL: {sl} | TP: {tp} | State: {st} | {note}")
