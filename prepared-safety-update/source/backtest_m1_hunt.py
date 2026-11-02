"""Search for an M1 gold config with win rate > 90% that is ALSO profitable.
Splits: train 50% / validate 25% / holdout 25%. Selection uses train+validate only;
holdout is reported once for the selected configs.
Extends backtest_m1_confluence.py with more filters and a 'quick close' exit:
exit on the first bar close at least exit_atr x ATR in profit (else SL or time stop)."""
import random, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea
import backtest_m1_confluence as bc

LOT, MULT, START, WARM = 0.01, 100, 1000.0, 3200

def extra(df, F):
    c, h1 = df['close'], df['close'].ewm(span=3000, adjust=False).mean()
    body = (df['close']-df['open']).abs()
    F['h1']       = (c>h1, c<h1)
    F['rsi_deep'] = (df['rsi14'].rolling(5).min()<30, df['rsi14'].rolling(5).max()>70)
    F['body']     = (body>0.5*df['atr14'], body>0.5*df['atr14'])
    F['calm']     = (df['bb_width']<df['bb_width'].rolling(500).median(),)*2
    return F

def run(df, sl_l, sl_s, mode, tgt, sl_atr, max_bars):
    o,h,l,c = (df[x].values for x in ('open','high','low','close'))
    atr, spr = df['atr14'].values, df['spread'].values*0.01
    sL, sS = sl_l.values, sl_s.values
    pos=None; bal=START; peak=START; mdd=0.0; pnls=[]
    for i in range(WARM, len(df)-1):
        if pos:
            d,e,tp,sl,t0,a = pos
            hit_sl = l[i]<=sl if d>0 else h[i]+spr[i]>=sl
            exit_c = c[i] if d>0 else c[i]+spr[i]
            if mode=='tp': hit_tp = h[i]>=tp if d>0 else l[i]+spr[i]<=tp; px_tp = tp
            else:          hit_tp = (exit_c-e)*d >= tgt*a;              px_tp = exit_c
            if hit_sl or hit_tp or i-t0>=max_bars:
                px = sl if hit_sl else px_tp if hit_tp else exit_c
                p=(px-e)*d*LOT*MULT; bal+=p; pnls.append(p); pos=None
                peak=max(peak,bal); mdd=max(mdd,peak-bal)
            continue
        d = 1 if sL[i] else -1 if sS[i] else 0
        if d:
            a=atr[i]; e=o[i+1]+(spr[i] if d>0 else 0)
            pos=(d,e,e+d*tgt*a,e-d*sl_atr*a,i+1,a)
    k=len(pnls); w=[x for x in pnls if x>0]; ls=[-x for x in pnls if x<=0]
    return dict(trades=k, net=round(bal-START,2), win=round(len(w)/k*100,1) if k else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2),
                avg_win=round(float(np.mean(w)),2) if w else 0, avg_loss=round(float(np.mean(ls)),2) if ls else 0)

def prep(d, vol_k, hours):
    bl, bs_, F = bc.signals(d, vol_k, hours); return bl, bs_, extra(d, F)

def sig(p, combo):
    bl, bs_, F = p
    for f in combo: bl = bl&F[f][0]; bs_ = bs_&F[f][1]
    return bl.fillna(False).astype(bool), bs_.fillna(False).astype(bool)

if __name__=="__main__":
    random.seed(7)
    df=pd.read_csv('data_cache/XAUUSD_M1_LONG.csv'); df['time']=pd.to_datetime(df['time'])
    df=bc.features(sea.enrich_features(df)); n=len(df); a,b=int(n*.5),int(n*.75)
    parts={'train':df.iloc[:a],'val':df.iloc[a-WARM:b],'hold':df.iloc[b-WARM:]}
    parts={k:v.reset_index(drop=True) for k,v in parts.items()}
    for k,v in parts.items(): print(k, v.time.iloc[WARM if k!='train' else 0].date(), "..", v.time.iloc[-1].date())
    cache={}
    names=['rsi','bb','adx','stoch','macd','m5','h1','rsi_deep','body','calm']
    passed=[]; tested=0; best=None
    for it in range(2500):
        vol_k=random.choice([3,4,6,8]); hours=random.choice([(7,17),(12,17),(7,12),(0,24)])
        combo=tuple(sorted(random.sample(names, random.choice([0,1,2,3,4]))))
        mode=random.choice(['tp','close']); tgt=random.choice([0.1,0.2,0.3,0.5,0.8])
        sl=random.choice([1.5,2.0,3.0,4.0,6.0]); mb=random.choice([15,30,60,120])
        key=(vol_k,hours)
        if key not in cache: cache[key]={k:prep(v,vol_k,hours) for k,v in parts.items()}
        r=run(parts['train'],*sig(cache[key]['train'],combo),mode,tgt,sl,mb); tested+=1
        if r['trades']<40 or r['win']<88 or r['net']<=0: continue
        v=run(parts['val'],*sig(cache[key]['val'],combo),mode,tgt,sl,mb)
        cfg=(combo,vol_k,hours,mode,tgt,sl,mb)
        if best is None or min(r['win'],v['win'])>best[0] and v['net']>0: best=(min(r['win'],v['win']),cfg,r,v)
        if v['trades']>=20 and r['win']>90 and v['win']>90 and v['net']>0: passed.append((cfg,r,v))
    print(f"\ntested {tested} | >90% win AND profitable on train+validate: {len(passed)}")
    print("best min-win profitable seen:", best)
    for cfg,r,v in passed:
        key=(cfg[1],cfg[2]); h=run(parts['hold'],*sig(cache[key]['hold'],cfg[0]),*cfg[3:])
        print("\nPASS",cfg,"\n  train",r,"\n  val  ",v,"\n  HOLD ",h)
