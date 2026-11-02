"""Sentinel: single-position trend-pullback bot, hard SL, no grid/martingale.
Honest backtest: next-bar-open fills, spread, SL-first on ambiguous bars,
parameters tuned on first 60% (train), judged on last 40% (test).
Compares against the two leaderboard grid bots on the same slices."""
import itertools, json, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea

SPREAD, LOT, MULT, START = 0.35, 0.01, 100, 1000.0

def sim(df, rsi_lo, tp_atr, sl_atr, be_atr=0.0):
    o,h,l,c = (df[k].values for k in ('open','high','low','close'))
    atr,rsi = df['atr14'].values, df['rsi14'].values
    e21,e55,e200 = df['ema21'].values, df['ema55'].values, df['ema200'].values
    bull,bear = df['bullish'].values, df['bearish'].values
    pos=None; bal=START; peak=START; mdd=0.0; pnls=[]
    for i in range(210, len(df)-1):
        if pos:
            d,e,tp,sl,a = pos
            hit_sl = l[i]<=sl if d>0 else h[i]>=sl
            hit_tp = h[i]>=tp if d>0 else l[i]<=tp
            if hit_sl or hit_tp:                       # SL wins ties
                px = sl if hit_sl else tp
                p = (px-e)*d*LOT*MULT; bal+=p; pnls.append(p); pos=None
                peak=max(peak,bal); mdd=max(mdd,peak-bal)
            elif be_atr>0 and ((h[i]-e)*d if d>0 else (e-l[i]))>=be_atr*a:
                pos=(d,e,tp,e,a)                       # move SL to entry
            continue
        up = e21[i]>e55[i] and c[i]>e200[i]
        dn = e21[i]<e55[i] and c[i]<e200[i]
        d = 1 if (up and rsi[i]<rsi_lo and bull[i]) else -1 if (dn and rsi[i]>100-rsi_lo and bear[i]) else 0
        if d:
            a=atr[i]; e=o[i+1]+SPREAD*d
            pos=(d,e,e+d*tp_atr*a,e-d*sl_atr*a,a)
    n=len(pnls); w=[p for p in pnls if p>0]; ls=[-p for p in pnls if p<=0]
    return dict(trades=n, net=round(bal-START,2), win=round(len(w)/n*100,1) if n else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2),
                avg_win=round(np.mean(w),2) if w else 0, avg_loss=round(-np.mean(ls),2) if ls else 0)

if __name__=="__main__":
    df = sea.load_datasets()['M5']; cut=int(len(df)*0.6)
    tr, te = df.iloc[:cut].reset_index(drop=True), df.iloc[cut-210:].reset_index(drop=True)
    grid = itertools.product([30,35,40,45],[0.3,0.5,0.8,1.2,2.0],[1.0,1.5,2.0,3.0],[0,0.5])
    res=[]
    for p in grid:
        r=sim(tr,*p)
        if r['trades']>=20 and r['net']>0: res.append((r['net']*r['pf']*r['win']/100/(1+r['dd']/START),p,r))
    res.sort(key=lambda x:-x[0])
    print("TOP TRAIN:"); [print(p,r) for _,p,r in res[:5]]
    best=res[0][1]
    print("\nSENTINEL params (rsi_lo,tp_atr,sl_atr,be_atr) =",best)
    print("  train:",sim(tr,*best)); print("  TEST :",sim(te,*best))
    lb=json.load(open('strategy_leaderboard.json'))['top_strategies']
    for s in lb:
        g=sea.StrategyDNA(s['dna'])
        a=sea.backtest_genome(df.iloc[cut:].reset_index(drop=True),g)
        print(f"\n{s['dna']['name']} on same TEST slice (grid bot, tuned on whole data):",
              {k:a[k] for k in ('net_profit','win_rate','total_cycles','profit_factor','max_drawdown','disaster_stops')})
