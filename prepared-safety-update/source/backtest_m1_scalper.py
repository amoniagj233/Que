"""Aggressive XAUUSD M1 scalper search. Single position, hard SL, quick TP, time stop.
Fills at next-bar open, per-bar broker spread, SL first on ambiguous bars.
Tuned on first 60% of bars, judged on the last 40%."""
import itertools, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea

LOT, MULT, START = 0.01, 100, 1000.0

def sim(df, mode, n, tp_atr, sl_atr, max_bars, session):
    o,h,l,c = (df[k].values for k in ('open','high','low','close'))
    atr, rsi, spr = df['atr14'].values, df['rsi14'].values, df['spread'].values*0.01
    e21, e55 = df['ema21'].values, df['ema55'].values
    hh = df['high'].rolling(n).max().shift(1).values; ll = df['low'].rolling(n).min().shift(1).values
    hour = df['time'].dt.hour.values
    pos=None; bal=START; peak=START; mdd=0.0; pnls=[]
    for i in range(210, len(df)-1):
        if pos:
            d,e,tp,sl,t0 = pos
            hit_sl = l[i]<=sl if d>0 else h[i]+spr[i]>=sl     # shorts exit at ask
            hit_tp = h[i]>=tp if d>0 else l[i]+spr[i]<=tp
            if hit_sl or hit_tp or i-t0>=max_bars:
                px = sl if hit_sl else tp if hit_tp else (c[i] if d>0 else c[i]+spr[i])
                p=(px-e)*d*LOT*MULT; bal+=p; pnls.append(p); pos=None
                peak=max(peak,bal); mdd=max(mdd,peak-bal)
            continue
        if session and not (7<=hour[i]<17): continue          # London + NY overlap (server time)
        up, dn = e21[i]>e55[i], e21[i]<e55[i]
        if mode=='breakout':
            d = 1 if (up and c[i]>hh[i]) else -1 if (dn and c[i]<ll[i]) else 0
        else:  # pullback
            d = 1 if (up and rsi[i]<n and c[i]>o[i]) else -1 if (dn and rsi[i]>100-n and c[i]<o[i]) else 0
        if d:
            a=atr[i]; e=o[i+1]+(spr[i] if d>0 else 0)
            pos=(d,e,e+d*tp_atr*a,e-d*sl_atr*a,i+1)
    k=len(pnls); w=[x for x in pnls if x>0]; ls=[-x for x in pnls if x<=0]
    return dict(trades=k, net=round(bal-START,2), win=round(len(w)/k*100,1) if k else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2),
                avg_win=round(np.mean(w),2) if w else 0, avg_loss=round(np.mean(ls),2) if ls else 0)

if __name__=="__main__":
    df=pd.read_csv('data_cache/XAUUSD_M1_LONG.csv'); df['time']=pd.to_datetime(df['time'])
    df=sea.enrich_features(df); cut=int(len(df)*0.6)
    tr, te = df.iloc[:cut].reset_index(drop=True), df.iloc[cut-210:].reset_index(drop=True)
    print("train",tr.time.iloc[0].date(),"..",tr.time.iloc[-1].date(),"| test ..",te.time.iloc[-1].date())
    grid=[('breakout',n,tp,sl,mb,s) for n,tp,sl,mb,s in itertools.product([10,20,30],[0.5,1.0,1.5,2.0],[0.75,1.0,1.5,2.0],[5,10,20],[True,False])] + \
         [('pullback',n,tp,sl,mb,s) for n,tp,sl,mb,s in itertools.product([30,40],[0.5,1.0,1.5,2.0],[0.75,1.0,1.5,2.0],[5,10,20],[True,False])]
    res=[]
    for p in grid:
        r=sim(tr,*p)
        if r['trades']>=100: res.append((r['pf'],p,r))
    res.sort(key=lambda x:-x[0])
    print("\nTOP 5 TRAIN -> TEST")
    for pf,p,r in res[:5]: print(p,"\n  train",r,"\n  TEST ",sim(te,*p))
    print("\nprofitable on train:",sum(1 for x in res if x[2]['net']>0),"/",len(res))
