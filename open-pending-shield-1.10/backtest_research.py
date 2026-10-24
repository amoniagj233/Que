"""Run only the isolated portable MT5 Strategy Tester; never send live orders."""
from pathlib import Path
from html.parser import HTMLParser
import configparser
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "research-2026-10-22"
OUT.mkdir(exist_ok=True)
TERMINAL = Path(r"C:\Users\amoni\MT5_Tester")

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag=='td': self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag=='td' and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row: self.rows.append(self.row)

def read_report(path):
    b=path.read_bytes()
    s=b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    parser=TableParser();parser.feed(s)
    metrics={}
    for row in parser.rows:
        for i,cell in enumerate(row[:-1]):
            if cell.endswith(':'): metrics[cell[:-1]]=row[i+1]
    def number(key):
        value=metrics.get(key,'0').replace(' ','').replace(',','')
        m=re.match(r'[-+]?\d+(?:\.\d+)?',value)
        return float(m[0]) if m else 0.0
    wins=re.search(r'([\d ]+)\s*\(([\d.]+)%\)',metrics.get('Profit Trades (% of total)',''))
    dd=re.search(r'([\d.]+)%',metrics.get('Equity Drawdown Maximal',''))
    deals=[row for row in parser.rows if len(row)==13 and re.match(r'^\d{4}\.\d{2}\.\d{2}',row[0]) and row[4] in ('in','out','out by','in/out')]
    return dict(net=number('Total Net Profit'),profit_factor=number('Profit Factor'),trades=int(number('Total Trades')),
                wins=int(wins[1].replace(' ','')) if wins else 0,win_rate=float(wins[2]) if wins else 0,
                dd_amount=number('Equity Drawdown Maximal'),dd_percent=float(dd[1]) if dd else None,
                history_quality=metrics.get('History Quality','unknown'),ticks=int(number('Ticks')),
                gross_profit=number('Gross Profit'),gross_loss=number('Gross Loss'),
                commission=sum(float(r[8].replace(' ','')) for r in deals),
                swap=sum(float(r[9].replace(' ','')) for r in deals),metrics=metrics,deals=deals)

def defaults():
    c=configparser.ConfigParser();c.optionxform=str;c.read(ROOT/'tester-defaults.ini')
    return dict(c['TesterInputs'])

def run(name,start,end,period='M1',overrides=None,model=4):
    output=OUT/(name+'.json')
    if output.exists():
        saved=json.loads(output.read_text())
        if saved.get('complete'): return saved
    parameters=defaults(); parameters['Lots']='1.0' # Cent symbol contract=1: matches 0.01 of a 100-unit standard contract.
    parameters.update(overrides or {})
    report_stem='OPS_research_'+name
    report_path=TERMINAL/(report_stem+'.htm')
    cfg=OUT/(name+'.ini')
    text='\n'.join(['[Common]','KeepPrivate=1','[Experts]','Enabled=0','AllowLiveTrading=0','[Tester]',
                   'Expert=OpenPendingShield\\OpenPendingShield_1_10.ex5','Symbol=XAUUSDc','Period='+period,
                   'Deposit=1000','Currency=USD','Leverage=100','Model='+str(model),'Optimization=0',
                   'FromDate='+start,'ToDate='+end,'Report='+report_stem,'ReplaceReport=1','ShutdownTerminal=1',
                   'UseLocal=1','UseRemote=0','UseCloud=0','Visual=0','[TesterInputs]']+[k+'='+v for k,v in parameters.items()])+'\n'
    cfg.write_text(text)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    started=time.time()
    print(json.dumps(dict(event='started',name=name,start=start,end=end,timeframe=period,model=model)),flush=True)
    proc=subprocess.Popen([str(TERMINAL/'terminal64.exe'),'/portable','/config:'+str(cfg)],startupinfo=startup,
                          creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try: code=proc.wait(timeout=360)
    except subprocess.TimeoutExpired:
        # Stop only this isolated process we created, never other terminals.
        proc.terminate();proc.wait(timeout=20);raise RuntimeError('Isolated tester timeout: '+name)
    log_path=TERMINAL/'Tester'/'Agent-127.0.0.1-3000'/'logs'/'20261022.log'
    log=log_path.read_bytes().decode('utf-16',errors='replace') if log_path.exists() else ''
    i=log.rfind('OpenPendingShield 1.10: original EA; trading=true')
    log=log[i:] if i>=0 else log[-8000:]
    (OUT/(name+'.log')).write_text(log,encoding='utf-8')
    complete=report_path.exists() and report_path.stat().st_mtime>=started and 'Test passed' in log
    if not complete:
        result=dict(name=name,complete=False,exit_code=code,seconds=round(time.time()-started,1),log_tail=log[-3000:])
        output.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return result
    target=OUT/(name+'.htm');target.write_bytes(report_path.read_bytes())
    for png in TERMINAL.glob(report_stem+'*.png'): (OUT/png.name).write_bytes(png.read_bytes())
    result=read_report(target)
    result.update(name=name,complete=True,start=start,end=end,timeframe=period,model=model,inputs=parameters,
                  execution_halts=log.count('EXECUTION HALTED'),seconds=round(time.time()-started,1),
                  binary_sha256=hashlib.sha256((ROOT/'OpenPendingShield_1_10.ex5').read_bytes()).hexdigest())
    result['real_tick_messages']=[x for x in log.splitlines() if any(y in x.lower() for y in ('real ticks','ticks generated','discarded','mismatch'))][-20:]
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('metrics','deals','inputs','real_tick_messages')}),flush=True)
    return result

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='pilot':
        run('pilot_real','2026.10.05','2026.10.10')
    if len(sys.argv)>1 and sys.argv[1]=='train':
        candidates={
            'balanced':dict(EntryDistance='1.5',StopDistance='1.5',TakeProfitDistance='2.0',TrailStart='1.0',TrailDistance='0.75'),
            'wide':dict(EntryDistance='2.0',StopDistance='2.0',TakeProfitDistance='3.0',TrailStart='1.5',TrailDistance='1.0'),
            'reward':dict(EntryDistance='1.5',StopDistance='1.0',TakeProfitDistance='2.0',TrailStart='1.2',TrailDistance='0.6'),
            'patient':dict(EntryDistance='2.5',StopDistance='1.5',TakeProfitDistance='3.0',TrailStart='1.5',TrailDistance='0.8',RepriceSeconds='10'),
            'broad':dict(EntryDistance='3.0',StopDistance='3.0',TakeProfitDistance='6.0',TrailStart='3.0',TrailDistance='1.5'),
            'fixed_rr':dict(EntryDistance='2.0',StopDistance='2.0',TakeProfitDistance='4.0',TrailStart='5.0',TrailDistance='1.0',RepriceSeconds='10'),
            'broadest':dict(EntryDistance='3.0',StopDistance='4.0',TakeProfitDistance='8.0',TrailStart='4.0',TrailDistance='2.0'),
        }
        (OUT/'candidate-plan.json').write_text(json.dumps(dict(training=['2026.10.05','2026.10.10'],
                    validation=['2026.10.12','2026.10.17'],candidates=candidates,
                    selection_rule='Exclude halts/zero or <30 trades. Rank training net profit, then profit factor; validate only the training winner. No live recommendation if validation loses.'),indent=2))
        for name,settings in candidates.items(): run('train_'+name,'2026.10.05','2026.10.10',overrides=settings)
    if len(sys.argv)>1 and sys.argv[1]=='validate':
        plan=json.loads((OUT/'candidate-plan.json').read_text())
        training=[json.loads((OUT/(name+'.json')).read_text()) for name in ['pilot_real']+['train_'+n for n in plan['candidates']]]
        eligible=[r for r in training if r['complete'] and r['trades']>=30 and r['execution_halts']==0]
        best=max(eligible,key=lambda r:(r['net'],r['profit_factor']))
        (OUT/'selection-before-validation.json').write_text(json.dumps(dict(name=best['name'],inputs=best['inputs'],training_net=best['net'],
                        training_win_rate=best['win_rate'],selection_rule=plan['selection_rule'],selected_at=dt.datetime.now().isoformat()),indent=2))
        print(json.dumps(dict(event='selected_on_training_only',name=best['name'],net=best['net'],win_rate=best['win_rate'])),flush=True)
        for period in ('M1','M5'):
            run('validation_default_'+period,'2026.10.12','2026.10.17',period=period)
            run('validation_winner_'+period,'2026.10.12','2026.10.17',period=period,overrides=best['inputs'])
