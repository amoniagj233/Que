import json

with open("trades_journal.json", "r", encoding="utf-8") as f:
    journal = json.load(f)

print(f"Total journal records: {len(journal)}")
for item in journal[:15]:
    print(f"[{item.get('execution_time')}] {item.get('symbol')} {item.get('direction')} @ {item.get('entry_price')} | SL: {item.get('sl')}, TP: {item.get('tp')} | Status: {item.get('status')} | Reason: {item.get('reason')}")
