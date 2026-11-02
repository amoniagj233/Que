"""Honest out-of-sample comparison on ~15 months of XAUUSD M5 (MT5 history).
Grid bots: genomes from strategy_leaderboard.json (tuned only on Sep-Oct 2026),
re-simulated with intrabar worst-case stops, TP filled at target, spread on both sides.
Sentinel: tuned on first 6 months only, judged on the rest."""
import json, sys, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea
import backtest_sentinel as bs

SPREAD, START, MULT = 0.35, 1000.0, 100

def grid_honest(df, p):
    A = {k: df[k].values for k in ('open','high','low','close','atr14','rsi14','vel3','ema21','ema55','ema9','ema200','bullish','bearish','hammer','shooting_star','dist_332_atr')}
    bal=START; peak=START; mdd=0.0; pnls=[]; basket=[]; bt=None; disasters=0
    for i in range(50, len(df)):
        c,h,l,atr,rsi,vel3 = A['close'][i],A['high'][i],A['low'][i],A['atr14'][i],A['rsi14'][i],A['vel3'][i]
        bull,bear = A['bullish'][i],A['bearish'][i]
        if basket:
            lots=sum(x[1] for x in basket); vwap=sum(x[0]*x[1] for x in basket)/lots
            d = 1 if bt=='BUY' else -1
            worst = l if d>0 else h
            worst_pnl = sum((worst-x[0])*d*x[1]*MULT for x in basket) - (SPREAD*lots*MULT if d<0 else 0)
            eq = bal+worst_pnl
            mdd=max(mdd,peak-eq)
            if p['disaster_sl']>0 and worst_pnl<=-p['disaster_sl']:
                bal-=p['disaster_sl']; pnls.append(-p['disaster_sl']); disasters+=1
                basket=[]; bt=None; peak=max(peak,bal); continue
            tp_dist=max(1.20, atr*p.get('tp_atr_mult',1.2))
            best = h if d>0 else l
            tgt = vwap+d*tp_dist
            fl_best = sum((best-x[0])*d*x[1]*MULT for x in basket) - (SPREAD*lots*MULT if d<0 else 0)
            tp_hit=False; pnl=0.0
            if p['tp_mode'] in ('DYNAMIC_ATR','HYBRID') and ((h>=tgt) if d>0 else (l<=tgt)):
                tp_hit=True; pnl=sum((tgt-x[0])*d*x[1]*MULT for x in basket) - (SPREAD*lots*MULT if d<0 else 0)
            elif p['tp_mode'] in ('FIXED_USD','HYBRID') and fl_best>=p['target_usd']:
                tp_hit=True; pnl=p['target_usd']
            if tp_hit:
                bal+=pnl; pnls.append(pnl); basket=[]; bt=None; peak=max(peak,bal); continue
            if len(basket)<p['max_layers']:
                layer=len(basket)
                if p['spacing_mode']=='ASYMMETRIC_ATR': step=max(3.0, atr*p['atr_mult']*(p['asym_growth']**(layer-1)))
                elif p['spacing_mode']=='DYNAMIC_ATR': step=max(2.5, atr*p['atr_mult'])
                else: step=max(4.0, p['atr_mult']*2.0)
                wp=min(x[0] for x in basket) if d>0 else max(x[0] for x in basket)
                if ((wp-c)>=step) if d>0 else ((c-wp)>=step):
                    ok=True
                    if p['waterfall_freeze']:
                        th=p['waterfall_thresh']*atr
                        if d>0: ok=(bull or A['hammer'][i] or rsi<28) if vel3<-th else (bull or rsi<35)
                        else:   ok=(bear or A['shooting_star'][i] or rsi>72) if vel3>th else (bear or rsi>65)
                    if ok:
                        lot=0.01 if (p['lot_mode']!='clamped' or layer<2) else 0.02
                        basket.append((c+(SPREAD if d>0 else 0), lot))
        else:
            tr=0
            ti=p['trend_indicator']
            if ti=='EMA_21_55': tr=1 if A['ema21'][i]>=A['ema55'][i] else -1
            elif ti=='EMA_9_21': tr=1 if A['ema9'][i]>=A['ema21'][i] else -1
            elif ti=='PRICE_VS_EMA200': tr=1 if c>=A['ema200'][i] else -1
            ab,as_ = tr>=0, tr<=0
            cap=p.get('exhaustion_cap',7.0); dist=A['dist_332_atr'][i]
            if cap>0:
                if dist>cap: ab=False
                elif dist<-cap: as_=False
            t=p['entry_trigger']
            if t=='CANDLE_DIRECTION': bt_,st_=bull,bear
            elif t=='RSI_EXTREMES': bt_,st_=(rsi<35 or (bull and rsi<50)),(rsi>65 or (bear and rsi>50))
            else: bt_,st_=False,False
            if ab and bt_: bt='BUY'; basket.append((c+SPREAD,0.01))
            elif as_ and st_: bt='SELL'; basket.append((c,0.01))
        peak=max(peak,bal)
    n=len(pnls); w=[x for x in pnls if x>0]; ls=[-x for x in pnls if x<=0]
    return dict(trades=n, net=round(bal-START,2), win=round(len(w)/n*100,1) if n else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2), disasters=disasters)

if __name__=="__main__":
    df = pd.read_csv('data_cache/XAUUSD_M5_LONG.csv'); df['time']=pd.to_datetime(df['time'])
    df = sea.enrich_features(df)
    n=len(df); cut=int(n*0.4)
    folds=[(f"{df['time'].iloc[a].date()}..{df['time'].iloc[b-1].date()}", df.iloc[a:b].reset_index(drop=True))
           for a,b in zip(np.linspace(cut,n,4,dtype=int)[:-1], np.linspace(cut,n,4,dtype=int)[1:])]
    print("bars",n,"| train",df['time'].iloc[0].date(),"..",df['time'].iloc[cut-1].date())
    tr=df.iloc[:cut].reset_index(drop=True)
    res=[]
    for p in itertools.product([30,35,40,45],[0.3,0.5,0.8,1.2,2.0],[1.0,1.5,2.0,3.0],[0,0.5]):
        r=bs.sim(tr,*p)
        if r['trades']>=40 and r['net']>0: res.append((r['net']*r['pf']*r['win']/100/(1+r['dd']/START),p,r))
    res.sort(key=lambda x:-x[0]); sp=res[0][1] if res else None
    print("Sentinel params (tuned on train only):",sp, res[0][2] if res else "no profitable config")
    lb=json.load(open('strategy_leaderboard.json'))['top_strategies']
    rows=[]
    for label,run in [("Sentinel",lambda d: bs.sim(d,*sp) if sp else {})]+[(s['dna']['name'],(lambda g: lambda d: grid_honest(d,g))(s['dna'])) for s in lb]:
        for fn,fd in folds: rows.append((label,fn,run(pd.concat([tr.iloc[-210:],fd],ignore_index=True)) if label=="Sentinel" else run(fd)))
    for lbl,fn,r in rows: print(f"{lbl:22s} {fn}  {r}")
