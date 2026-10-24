from pathlib import Path
import datetime as dt
import hashlib,json,re,subprocess,time
from report_parser import read_report

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'tests';OUT.mkdir(exist_ok=True)
TERMINAL=Path(r'C:\Users\amoni\MT5_Tester')
def defaults():
    return {m[1]:m[2] for m in re.finditer(r'^input\s+\w+\s+(\w+)=(.*?);',(ROOT/'GoldTrendBurst.mq5').read_text(),re.M)}
def run(name,start,end,overrides=None,period='M1',delay=150):
    params=defaults();params.update(overrides or {})
    binary_hash=hashlib.sha256((ROOT/'GoldTrendBurst.ex5').read_bytes()).hexdigest()
    saved=OUT/(name+'.json')
    if saved.exists():
        r=json.loads(saved.read_text())
        if r.get('complete') and r.get('binary_sha256')==binary_hash and r.get('inputs')==params:return r
    stem='GTB_'+name;report=TERMINAL/(stem+'.htm');cfg=OUT/(name+'.ini')
    cfg.write_text('\n'.join(['[Common]','KeepPrivate=1','[Experts]','Enabled=0','AllowLiveTrading=0','[Tester]',
        'Expert=GoldTrendBurst\\GoldTrendBurst.ex5','Symbol=XAUUSDc','Period='+period,'Deposit=10000','Currency=USD','Leverage=100',
        'Model=4','ExecutionMode='+str(delay),'Optimization=0','FromDate='+start,'ToDate='+end,'Report='+stem,
        'ReplaceReport=1','ShutdownTerminal=1','UseLocal=1','UseRemote=0','UseCloud=0','Visual=0','[TesterInputs]']+
        [k+'='+v for k,v in params.items()])+'\n')
    print(json.dumps(dict(event='start',name=name,period=period,delay_ms=delay)),flush=True)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    begin=time.time()
    p=subprocess.Popen([str(TERMINAL/'terminal64.exe'),'/portable','/config:'+str(cfg)],startupinfo=si,
        creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try: code=p.wait(timeout=360)
    except subprocess.TimeoutExpired:
        p.terminate();p.wait(timeout=20);raise RuntimeError('Isolated tester timeout')
    logs=sorted((TERMINAL/'Tester').glob('Agent-*/logs/*.log'),key=lambda p:p.stat().st_mtime)
    text=logs[-1].read_bytes().decode('utf-16',errors='replace')
    index=text.rfind('GTB START');text=text[index:] if index>=0 else text[-10000:]
    (OUT/(name+'.log')).write_text(text,encoding='utf-8')
    complete=report.exists() and report.stat().st_mtime>=begin and logs[-1].stat().st_mtime>=begin and 'Test passed' in text and 'GTB STATS' in text
    if not complete:
        r=dict(name=name,complete=False,exit_code=code,tail=text[-3500:]);saved.write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True);return r
    dest=OUT/(name+'.htm');dest.write_bytes(report.read_bytes())
    for png in TERMINAL.glob(stem+'*.png'):(OUT/png.name).write_bytes(png.read_bytes())
    r=read_report(dest)
    stat=re.search(r'GTB STATS baskets=(\d+) entries=(\d+)',text)
    assert stat and int(stat[2])==sum(d[4]=='in' for d in r['deals']), 'Journal/report entry mismatch'
    baskets=[];active=0;peak=0;current=None;signal_ids=set();profit_exits=0;zeros=0
    for d in r['deals']:
        if d[4]=='in':
            if current is None:current=dict(start=d[0],legs=0,pnl=0,signal=d[12].rsplit('-',1)[0],volume=0)
            current['legs']+=1;current['volume']+=float(d[5]);active+=1;peak=max(peak,active)
            current['pnl']+=float(d[8])+float(d[9])+float(d[10])
        elif d[4]=='out':
            if current is None:raise RuntimeError('Exit without basket')
            pnl=float(d[8])+float(d[9])+float(d[10]);current['pnl']+=pnl
            profit_exits+=pnl>0;zeros+=pnl==0;active-=1
            if active==0:
                current['end']=d[0];current['pnl']=round(current['pnl'],2)
                current['seconds']=(dt.datetime.strptime(d[0],'%Y.%m.%d %H:%M:%S')-dt.datetime.strptime(current['start'],'%Y.%m.%d %H:%M:%S')).total_seconds()
                if current['signal'] in signal_ids:raise RuntimeError('Duplicate signal basket')
                signal_ids.add(current['signal']);baskets.append(current);current=None
    if active!=0:raise RuntimeError('Unclosed basket')
    assert peak<=3
    assert abs(sum(b['pnl'] for b in baskets)-r['net'])<.05
    # Each accepted market entry must contain attached positive SL and TP in the tester journal.
    protected=[]
    for line in text.splitlines():
        if '\tTrade\t' in line and 'failed' not in line:
            m=re.search(r'market (?:buy|sell) ([\d.]+) \S+ sl: ([\d.]+) tp: ([\d.]+)',line)
            if m:assert float(m[2])>0 and float(m[3])>0;protected.append(m.groups())
    assert len(protected)>=sum(b['legs'] for b in baskets), 'Missing protected entry evidence'
    r.update(name=name,complete=True,inputs=params,period=period,start=start,end=end,delay_ms=delay,
        binary_sha256=binary_hash,halts=text.count('HALTED:'),seconds=round(time.time()-begin,1),
        baskets=baskets,basket_count=len(baskets),full_bursts=sum(b['legs']==3 for b in baskets),
        basket_win_rate=100*sum(b['pnl']>0 for b in baskets)/len(baskets) if baskets else 0,
        avg_basket_seconds=sum(b['seconds'] for b in baskets)/len(baskets) if baskets else 0,
        max_open=peak,protected_entry_logs=len(protected),strict_win_rate=100*profit_exits/r['trades'] if r['trades'] else 0,
        break_even=zeros)
    saved.write_text(json.dumps(r,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ('inputs','metrics','deals','baskets')}),flush=True)
    return r

CANDIDATES={
    'blueprint':{},
    'fast':dict(MinBodyATR='0.15',BreakBufferATR='0.0',Target1ATR='0.4',Target2ATR='0.6',Target3ATR='0.8',MaxHoldingSeconds='120',CooldownSeconds='5'),
    'momentum':dict(MinADX='18.0',MinBodyATR='0.35',Target1ATR='0.6',Target2ATR='0.9',Target3ATR='1.2',MaxHoldingSeconds='180'),
    'strong':dict(MinADX='23.0',MinBodyATR='0.4',StopATR='0.8',Target1ATR='0.6',Target2ATR='0.9',Target3ATR='1.2',MaxHoldingSeconds='120'),
    'runner':dict(MinADX='18.0',StopATR='1.0',Target1ATR='0.75',Target2ATR='1.0',Target3ATR='1.5',TrailATR='0.5',MaxHoldingSeconds='240'),
    'tight':dict(MinADX='18.0',StopATR='0.7',Target1ATR='0.5',Target2ATR='0.75',Target3ATR='1.0',MinBodyATR='0.25',MaxHoldingSeconds='120'),
}
if __name__=='__main__':
    import sys
    mode=sys.argv[1]
    if mode=='smoke':run('smoke','2026.10.05','2026.10.06')
    if mode=='controls':
        disabled=run('disabled','2026.10.05','2026.10.06',dict(EnableTrading='false'))
        assert disabled['trades']==0
        stopped=run('daily_stop','2026.10.05','2026.10.06',dict(DailyLossPercent='0.1'))
        journal=(OUT/'daily_stop.log').read_text()
        marker=journal.find('Daily loss stop latched')
        assert marker>=0, 'Daily loss stop was not exercised'
        assert not re.search(r'\tTrade\t.*market (buy|sell).* sl:',journal[marker:]), 'Entry after daily stop'
        print('CONTROL CHECKS PASSED',flush=True)
    if mode=='train':
        (OUT/'plan.json').write_text(json.dumps(dict(candidates=CANDIDATES,training=['2026.10.05','2026.10.10'],validation=['2026.10.12','2026.10.17'],
            rule='Require >=30 baskets, no execution halts, positive training net after $7 per standard lot round-trip commission stress, PF>1.1 and drawdown<=8%; choose highest basket frequency among qualifiers. If none qualifies, select highest net only as a research candidate.'),indent=2))
        for n,c in CANDIDATES.items():run('train_'+n,'2026.10.05','2026.10.10',c)
    if mode=='validate':
        rows=[json.loads((OUT/('train_'+n+'.json')).read_text()) for n in CANDIDATES]
        rows=[r for r in rows if r['complete'] and r['halts']==0 and r['basket_count']>0]
        for r in rows:r['commission_stressed_net']=r['net']-sum(b['volume'] for b in r['baskets'])*0.07
        good=[r for r in rows if r['basket_count']>=30 and r['commission_stressed_net']>0 and r['profit_factor']>1.1 and r['dd_percent']<=8]
        if not rows:raise RuntimeError('No functioning candidate; investigate execution before selecting settings')
        chosen=max(good,key=lambda r:r['basket_count']) if good else max(rows,key=lambda r:r['net'])
        (OUT/'selected.json').write_text(json.dumps(dict(name=chosen['name'],inputs=chosen['inputs'],training_pass=bool(good),net=chosen['net'],commission_stressed_net=chosen['commission_stressed_net']),indent=2))
        for period in ('M1','M5'):run('validation_'+period,'2026.10.12','2026.10.17',chosen['inputs'],period=period)
        run('delay_stress','2026.10.12','2026.10.17',chosen['inputs'],delay=500)
