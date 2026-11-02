import json
p = r"C:\Users\amoni\Downloads\_LevelBreakOut_EURUSD_H1.ipynb"
try:
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("Cells count:", len(data.get('cells', [])))
    for c in data.get('cells', [])[:3]:
        source = "".join(c.get('source', []))
        print("CELL:")
        print(source[:300])
except Exception as e:
    print("Error:", e)
