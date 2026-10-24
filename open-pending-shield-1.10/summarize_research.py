from pathlib import Path
import csv, datetime as dt, hashlib, html, json, math, re, statistics
from collections import defaultdict
from backtest_research import OUT, ROOT, defaults

def load(name):
    r=json.loads((OUT/(name+'.json')).read_text())
    assert r['complete'] and r['execution_halts']==0, 'Incomplete/ halted test: '+name
    assert r['history_quality']=='100% real ticks', 'Real tick coverage not complete: '+name
    assert r['binary_sha256']==hashlib.sha256((ROOT/'OpenPendingShield_1_10.ex5').read_bytes()).hexdigest()
    return r

def close_trades(r):
    pending=defaultdict(list); closed=[]
    for d in r['deals']:
        side=d[3];vol=float(d[5]);price=float(d[6]);fees=float(d[8])+float(d[9])
        if d[4]=='in':
            pending[side].append(dict(entry_time=d[0],side=side,volume=vol,entry_price=price,entry_fees=fees))
        else:
            other='buy' if side=='sell' else 'sell'
            assert pending[other], 'Unmatched closing deal'
            entry=pending[other].pop(0)
            assert abs(entry['volume']-vol)<1e-8, 'Partial position requires allocation'
            pnl=float(d[10])+fees+entry['entry_fees']
            a=dt.datetime.strptime(entry['entry_time'],'%Y.%m.%d %H:%M:%S')
            b=dt.datetime.strptime(d[0],'%Y.%m.%d %H:%M:%S')
            closed.append(dict(run=r['name'],timeframe=r['timeframe'],symbol=d[2],**entry,exit_time=d[0],exit_price=price,
                               net=round(pnl,2),win=pnl>0,duration_seconds=int((b-a).total_seconds()),entry_hour=a.hour,
                               exit_comment=d[12]))
    assert not any(pending.values()), 'Open position not closed at test end'
    assert len(closed)==r['trades']
    assert abs(sum(t['net'] for t in closed)-r['net'])<.03, 'Deal totals do not reconcile'
    return closed

def write_csv(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def wilson(w,n):
    z=1.96;p=w/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;e=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return f'{(c-e)*100:.1f}%–{(c+e)*100:.1f}%'

plan=json.loads((OUT/'candidate-plan.json').read_text())
selection=json.loads((OUT/'selection-before-validation.json').read_text())
training=[load(n) for n in ['pilot_real']+['train_'+n for n in plan['candidates']]]
validation=[load('validation_'+n+'_'+p) for p in ('M1','M5') for n in ('default','winner')]
for r in training+validation:
    closed=close_trades(r)
    r['mt5_profit_trade_count']=r['wins'];r['mt5_profit_trade_percent']=r['win_rate']
    r['wins']=sum(t['net']>0 for t in closed)
    r['break_even']=sum(t['net']==0 for t in closed)
    r['win_rate']=100*r['wins']/r['trades']
winner=next(t for t in training if t['name']==selection['name'])
held=next(t for t in validation if t['name']=='validation_winner_M1')
all_closed=[]
metrics=[]
for r in training+validation:
    closed=close_trades(r)
    if r in validation:all_closed+=closed
    row={k:r[k] for k in ('name','start','end','timeframe','trades','wins','break_even','win_rate','mt5_profit_trade_count','mt5_profit_trade_percent','net','profit_factor','dd_amount','dd_percent','commission','swap','history_quality')}
    row.update({k:r['inputs'][k] for k in ('EntryDistance','StopDistance','TakeProfitDistance','TrailStart','TrailDistance','RepriceSeconds','Lots')})
    metrics.append(row)
write_csv('all-results.csv',metrics)
write_csv('validation-every-trade.csv',all_closed)
hourly=[]
for r in validation:
    if r['timeframe']!='M1':continue
    trades=[t for t in all_closed if t['run']==r['name']]
    for h in range(24):
        group=[t for t in trades if t['entry_hour']==h]
        hourly.append(dict(run=r['name'],entry_hour_broker_time=h,trades=len(group),wins=sum(t['win'] for t in group),
                           win_rate=round(100*sum(t['win'] for t in group)/len(group),2) if group else '',net=round(sum(t['net'] for t in group),2)))
write_csv('entry-hours-exploratory.csv',hourly)

equal={}
for variant in ('default','winner'):
    a=next(r for r in validation if r['name']=='validation_'+variant+'_M1')
    b=next(r for r in validation if r['name']=='validation_'+variant+'_M5')
    equal[variant]=a['deals']==b['deals']

qualification=winner['net']>0 and held['net']>0 and held['profit_factor']>1 and held['trades']>=30
recommendation='Research candidate only; needs longer cost-aware forward validation.' if qualification else 'No profitable preset is recommended from this search.'
settings=defaults();settings.update(selection['inputs']);settings['Lots']='0.01';settings['EnableTrading']='false'
preset_name='Best-Tested-Research-Only-StandardGold-0.01.set'
(OUT/preset_name).write_text('; RESEARCH ONLY: disabled. Not a live profitability recommendation.\n; Standard Gold contract=100 uses 0.01 lots; tests used 1.00 cent-contract lot (contract=1).\n'+'\n'.join(k+'='+v for k,v in settings.items())+'\n')
research_settings=selection['inputs'].copy();research_settings['EnableTrading']='false'
(OUT/'Best-Tested-Research-Only-CentGold-1.00.set').write_text('; RESEARCH ONLY: disabled, for the tested cent contract size=1.\n'+'\n'.join(k+'='+v for k,v in research_settings.items())+'\n')

lines=['# OpenPendingShield 1.10: M1 / M5 real-tick backtests','',recommendation,'',
       f"The best training candidate lost **USD {abs(winner['net']):.2f}** in training and returned **USD {held['net']:+.2f}** in validation: **USD {winner['net']+held['net']:+.2f}** across the two independent periods. Validation has only {held['trades']} trades; it is not enough to establish a durable edge.",'',
       'Training: **5–9 October 2026** (exclusive end 10 October). Separate validation: **12–16 October 2026** (exclusive end 17 October). Eight parameter combinations, including defaults; winner selected by training net profit before viewing validation. No losses, stops or stored account state were changed in the live terminal.','',
       'All runs: isolated MT5 Strategy Tester, XAUUSDc, **100% real ticks**, simulated USD 1,000 deposit, leverage 1:100. Fixed **1.00 lot on the cent contract (size 1)** matches the Gold-price exposure of **0.01 lot on a standard contract (size 100)**. It does not mean 1.00 standard Gold lot. The account inspected earlier had standard contract size 100. Source defaults were retained except this explicit contract normalization and candidate parameters. Combined SL-risk cap 1% and daily equity-loss guard 5% stayed active.','',
       '## Separate-week M1 and M5 results','',
       'Win rate below means strictly positive net P/L divided by all closed trades; break-even trades remain in the denominator. In these reports MT5 included zero-profit exits in its Profit Trades count. The CSV preserves both percentages so they can be reconciled.','',
       '| Settings | Chart | Trades | Wins | Win rate | Net USD | Profit factor | Max equity DD |','|---|---|---:|---:|---:|---:|---:|---:|']
for r in validation:
    lines.append(f"| {'Current defaults' if 'default' in r['name'] else 'Training winner'} | {r['timeframe']} | {r['trades']} | {r['wins']} | {r['win_rate']:.2f}% | {r['net']:+.2f} | {r['profit_factor']:.2f} | {r['dd_percent']:.2f}% |")
lines+=['',f"Exact trade-by-trade M1/M5 equality: defaults **{equal['default']}**, candidate **{equal['winner']}**. ATR is disabled and the code uses ticks, timers and price distances, with no chart-timeframe signal filter. M1 and M5 are chart displays for this strategy, not independent strategies. Their duplicate tests must not be pooled to pretend the sample size doubled.",'',
        f"Candidate win-rate 95% Wilson interval on the separate week: **{wilson(held['wins'],held['trades'])}**. This interval describes sampling uncertainty only; it does not account for changing markets or repeated parameter searches.",'',
        '## Training comparison','', '| Candidate | Trades | Win rate | Net USD | PF | Max equity DD |','|---|---:|---:|---:|---:|---:|']
for r in sorted(training,key=lambda r:r['net'],reverse=True):
    lines.append(f"| {r['name']} | {r['trades']} | {r['win_rate']:.2f}% | {r['net']:+.2f} | {r['profit_factor']:.2f} | {r['dd_percent']:.2f}% |")
lines+=['',f"Selected candidate: **{selection['name']}**. Selection excluded tests with halts, incomplete reports or fewer than 30 trades. A high win rate alone was not the selection rule.",'',
        '## Best tested parameters (research, not a live recommendation)','', '| Parameter | Value |','|---|---:|']
for k in ('EntryDistance','StopDistance','TakeProfitDistance','TrailStart','TrailDistance','RepriceSeconds','EntryCooldownSeconds','MaxSpreadEntryRatio','AutoAdjustEntryDistance','UseATR','MaxCombinedRiskPercent','DailyEquityLossPercent'):
    lines.append(f"| {k} | {selection['inputs'][k]} |")
lines+=['','Price distances are quote-price units. Entry distance can grow to satisfy the spread ratio, up to the existing 5.0 cap. The research presets deliberately have `EnableTrading=false`; they do not replace your installed working EA or authorize a live account change.','',
        '## Costs and limitations','',
        'Historical bid/ask spreads were included. Reported commission was zero; swaps, when present, are included in the reports and deal reconciliation. No realistic latency or extra slippage was imposed. The table below subtracts hypothetical extra costs from the candidate validation net; it is arithmetic sensitivity, not a new execution simulation.','',
        '| Hypothetical extra round-trip cost per trade at normalized exposure | Candidate validation net USD |','|---|---:|',
        f"| None beyond report | {held['net']:+.2f} |",f"| USD 0.07 commission | {held['net']-.07*held['trades']:+.2f} |",f"| USD 0.07 commission + USD 0.20 adverse slippage | {held['net']-.27*held['trades']:+.2f} |",'',
        'This is ten trading days across two periods on one broker feed, not an exhaustive optimization or proof of future profitability. Contract normalization matches price exposure but cannot make different brokers’ spreads, fill rules, commissions and latency identical. Client-side opposite-order cancellation can still double-fill in live conditions.','',
        'The earlier June one-day generated-tick test checked execution. It did not establish profitability; the real-tick results here replace it as the relevant strategy evidence.','',
        '## Files and trading times','',
        '`all-results.csv`: every run and its settings. `validation-every-trade.csv`: each validation entry/exit timestamp, side, profit and win/loss. Times are **MT5 broker/server time**, not converted to Accra time because historical timezone offsets were not independently verified. `entry-hours-exploratory.csv` groups M1 entries by hour; it is descriptive only and no hour filter was fitted or enabled. M5 trades are the same underlying sample when equality is true.','',
        'Individual `.htm` reports, `.ini` inputs and tester journals are retained. Binary SHA-256: `'+held['binary_sha256']+'`. Every closed trade was matched to an entry and totals were reconciled to MT5 net profit.','',
        'Method references: [MT5 Strategy Testing](https://www.metatrader5.com/en/terminal/help/algotrading/testing), [MT5 execution and spread simulation](https://www.metatrader5.com/en/terminal/help/algotrading/testing_features).']
(OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
summary=dict(recommendation=recommendation,qualified_research_candidate=qualification,selected=selection['name'],
             candidate_combined_net=round(winner['net']+held['net'],2),
             timeframes_trade_equality=equal,training=metrics[:len(training)],validation=metrics[len(training):],
             total_runs=len(training)+len(validation),settings=selection['inputs'])
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
