from pathlib import Path
import json,re,hashlib
from backtest import defaults
p=Path(__file__).parent
files=list((p/'tests').glob('train_*.json'))+list((p/'tests').glob('validation_*.json'))+[p/'tests/delay_stress.json',p/'tests/disabled.json',p/'tests/daily_stop.json']
for f in files:
    r=json.loads(f.read_text());log=f.with_suffix('.log').read_text()
    assert r['complete'],f
    stat=re.search(r'GTB STATS baskets=(\d+) entries=(\d+)',log)
    assert int(stat[2])==sum(d[4]=='in' for d in r['deals']),f
    assert r['protected_entry_logs']==int(stat[2]),f
    assert r['binary_sha256']==hashlib.sha256((p/'GoldTrendBurst.ex5').read_bytes()).hexdigest(),f
    print(f.stem,'report/journal/binary matched')
a=json.loads((p/'tests/validation_M1.json').read_text())
b=json.loads((p/'tests/validation_M5.json').read_text())
assert a['inputs']==defaults()
assert a['deals']==b['deals']
print('Final defaults and M1/M5 equivalence verified')
