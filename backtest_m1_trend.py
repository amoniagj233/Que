"""Improved XAUUSD M1 bot: M1 entry timing inside the higher-timeframe trend.
- Trend: price vs EMA750 on M1 (~EMA50 on M15) and its slope.
- Entry: pullback to EMA21 then close back above the prior bar high (short: mirror).
- Volatility gate: ATR14 >= vol_k x spread, so the spread is a small part of the move.
- Exit: hard SL, TP in ATR, breakeven at 1 ATR, time stop.
Same honest fills as backtest_m1_scalper.py. Tuned on first 60%, judged on last 40%."""
import itertools, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea

LOT, MULT, START = 0.01, 100, 1000.0

def sim(df, tp_atr, sl_atr, vol_k, max_bars, hours, be=True):
    o,h,l,c = (df[k].values for k in ('open','high','low','close'))
    atr, spr, e21 = df['atr14'].values, df['spread'].values*0.01, df['ema21'].values
    htf = df['close'].ewm(span=750, adjust=False).mean().values
    hour = df['time'].dt.hour.values
    pos=None; bal=START; peak=START; mdd=0.0; pnls=[]
    for i in range(800, len(df)-1):
        if pos:
            d,e,tp,sl,t0,a = pos
            hit_sl = l[i]<=sl if d>0 else h[i]+spr[i]>=sl
            hit_tp = h[i]>=tp if d>0 else l[i]+spr[i]<=tp
            if hit_sl or hit_tp or i-t0>=max_bars:
                px = sl if hit_sl else tp if hit_tp else (c[i] if d>0 else c[i]+spr[i])
                p=(px-e)*d*LOT*MULT; bal+=p; pnls.append(p); pos=None
                peak=max(peak,bal); mdd=max(mdd,peak-bal)
            elif be and (d*(sl-e) < 0) and ((h[i]-e) if d>0 else (e-l[i]-spr[i])) >= a:
                pos=(d,e,tp,e,t0,a)                          # move SL to entry after +1 ATR
            continue
        if not (hours[0] <= hour[i] < hours[1]) or atr[i] < vol_k*spr[i]: continue
        up = c[i]>htf[i] and htf[i]>htf[i-30]
        dn = c[i]<htf[i] and htf[i]<htf[i-30]
        touched_up = l[i-1]<=e21[i-1] or l[i-2]<=e21[i-2]
        touched_dn = h[i-1]>=e21[i-1] or h[i-2]>=e21[i-2]
        d = 1 if (up and touched_up and c[i]>h[i-1]) else -1 if (dn and touched_dn and c[i]<l[i-1]) else 0
        if d:
            a=atr[i]; e=o[i+1]+(spr[i] if d>0 else 0)
            pos=(d,e,e+d*tp_atr*a,e-d*sl_atr*a,i+1,a)
    k=len(pnls); w=[x for x in pnls if x>0]; ls=[-x for x in pnls if x<=0]
    return dict(trades=k, net=round(bal-START,2), win=round(len(w)/k*100,1) if k else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2),
                avg_win=round(np.mean(w),2) if w else 0, avg_loss=round(np.mean(ls),2) if ls else 0)

if __name__=="__main__":
    df=pd.read_csv('data_cache/XAUUSD_M1_LONG.csv'); df['time']=pd.to_datetime(df['time'])
    df=sea.enrich_features(df); cut=int(len(df)*0.6)
    tr, te = df.iloc[:cut].reset_index(drop=True), df.iloc[cut-800:].reset_index(drop=True)
    res=[]
    for p in itertools.product([1.5,2.0,3.0,4.0],[1.0,1.5,2.0],[3,4,6],[20,40,60],[(7,17),(12,17),(0,24)],[True,False]):
        r=sim(tr,*p)
        if r['trades']>=60: res.append((r['pf'],p,r))
    res.sort(key=lambda x:-x[0])
    print("profitable on train:",sum(1 for x in res if x[2]['net']>0),"/",len(res))
    print("\nTOP 5 TRAIN -> TEST  (tp_atr, sl_atr, vol_k, max_bars, hours, breakeven)")
    for _,p,r in res[:5]: print(p,"\n  train",r,"\n  TEST ",sim(te,*p))
    te_pos=sum(1 for _,p,r in res if r['net']>0 and sim(te,*p)['net']>0)
    print("\nprofitable on BOTH train and test:",te_pos)
