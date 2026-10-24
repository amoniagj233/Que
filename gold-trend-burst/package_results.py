from pathlib import Path
import csv,hashlib,json,shutil,zipfile
from backtest import defaults,OUT,ROOT

dest=Path.home()/'OneDrive'/'Desktop'/'Gold Trend Burst MT5 EA'
dest.mkdir(exist_ok=True)
selected=json.loads((OUT/'selected.json').read_text())
names=['train_'+n for n in ('blueprint','fast','momentum','strong','runner','tight')]+['validation_M1','validation_M5','delay_stress','final_defaults','disabled','daily_stop']
rows=[json.loads((OUT/(n+'.json')).read_text()) for n in names if (OUT/(n+'.json')).exists()]
assert all(r['complete'] for r in rows)
fields=['name','period','trades','strict_win_rate','basket_count','basket_win_rate','net','profit_factor','dd_percent','avg_basket_seconds','max_open','halts']
with (ROOT/'results.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
lines=['# Gold Trend Burst — backtest results','',
    'Testing uses XAUUSDc on HFMarketsGlobal-Live20 history, a $10,000 USD simulated hedging account, 1:100 leverage and real ticks. Contract size is 1 Gold unit per cent lot; exposure is normalized by contract size. These are historical simulations, not live results.',
    '', 'Training: October 5–9, 2026. Held-out validation: October 12–16, 2026. Default execution delay 150 ms; stress test 500 ms. M1 and M5 refer to attached chart timeframe; both use the same internal M5/M1 strategy.', '',
    'Selection was fixed before validation: at least 30 training baskets, no execution halts, positive net after commission stress, profit factor above 1.1 and drawdown no greater than 8%; choose the most frequent qualifying candidate. If none passes, the highest-net functioning candidate is research-only.', '',
    f"Selected candidate: **{selected['name']}**. Training qualification passed: **{selected['training_pass']}**.", '',
    'None of the six presets passed the training qualification. The original blueprint was the least losing training candidate and remains embedded. Faster/high-frequency alternatives are documented, not presented as profitable defaults. Smaller targets can reduce entries because the spread filter becomes stricter; the preset named fast did not produce the most trades.', '',
    '| Test | Trades | Trade wins | Baskets | Basket wins | Net USD | PF | Drawdown | Mean basket seconds |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['name']} | {r['trades']} | {r['strict_win_rate']:.2f}% | {r['basket_count']} | {r['basket_win_rate']:.2f}% | {r['net']:.2f} | {r['profit_factor']:.2f} | {r['dd_percent']:.2f}% | {r['avg_basket_seconds']:.1f} |")
lines+=['','Win rate counts strictly positive closed trade P/L; break-even trades remain in the denominator. Basket win rate counts total P/L across its legs. Drawdown is MT5 maximal equity drawdown, including floating losses. Three correlated legs are not three independent signals.', '', '## Cost stress and limitations','']
for r in rows:
    if r['name'].startswith('validation') or r['name']=='delay_stress':
        cost=sum(b['volume'] for b in r['baskets'])*.07
        lines.append(f"- {r['name']}: net after an additional $7 per standard lot round-trip commission = ${r['net']-cost:.2f} (deducted ${cost:.2f}). MT5 itself reported commission ${r['commission']:.2f}.")
lines+=['', 'Only two historical weeks were evaluated. These results cannot establish robustness across market regimes. Spread is from the historical quotes; live execution, commission, liquidity and slippage may differ. No profitable setting is claimed unless both training criteria and independent validation survive costs. A research candidate that fails these checks is not recommended for live deployment.', '', '## Embedded defaults','', '```', '\n'.join(k+'='+v for k,v in defaults().items()), '```', '', '## Verification','',
    'Compilation: 0 errors and 0 warnings (see compile.log). Each completed run reconciles basket P/L with MT5 net P/L, checks no duplicate signal basket, no more than three open positions and protected entry journal evidence. Full and partial baskets are recorded separately. The disabled and daily-stop runs are functional controls, not performance estimates. Broker disconnects and restart recovery were not exercised end-to-end.', '',
    'The build is supplied for demo research. No live charts or live order permissions were changed.', '',
    'Binary SHA-256: '+hashlib.sha256((ROOT/'GoldTrendBurst.ex5').read_bytes()).hexdigest()]
(ROOT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
(ROOT/'Research.set').write_text('\n'.join(k+'='+v for k,v in defaults().items())+'\n')
for name in ('GoldTrendBurst.mq5','GoldTrendBurst.ex5','README.md','RESULTS.md','results.csv','Research.set','compile.log'):
    shutil.copy2(ROOT/name,dest/name)
with zipfile.ZipFile(dest/'Evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.iterdir():
        if p.is_file():z.write(p,'tests/'+p.name)
    for name in ('backtest.py','report_parser.py','package_results.py','audit.py'):z.write(ROOT/name,name)
print(dest)
