"""M1 gold trend bot + confluence filters, aimed at a 90%+ win rate.
Base signal from backtest_m1_trend.py (HTF trend, EMA21 pullback, prior-bar break,
volatility gate, 07-17 session). Adds 1-3 extra filters from:
  rsi    RSI14 in pullback zone (<45 long / >55 short)
  bb     low touched lower Bollinger band in last 3 bars (short: upper)
  adx    ADX14 > 20 (trend strength)
  stoch  Stochastic %K crossed up from <30 (short: down from >70)
  macd   MACD histogram rising (short: falling)
  m5     EMA105 (~EMA21 on M5) agrees with trend
A config passes only if win >= 90% AND profitable on BOTH train (60%) and test (40%)."""
import itertools, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import strategy_evolution_agent as sea

LOT, MULT, START, WARM = 0.01, 100, 1000.0, 800

def features(df):
    c,h,l = df['close'], df['high'], df['low']
    df['htf'] = c.ewm(span=750, adjust=False).mean()
    df['m5'] = c.ewm(span=105, adjust=False).mean()
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up>dn)&(up>0), up, 0.0); ndm = np.where((dn>up)&(dn>0), dn, 0.0)
    trs = df['tr'].ewm(alpha=1/14, adjust=False).mean()
    pdi = 100*pd.Series(pdm).ewm(alpha=1/14, adjust=False).mean()/trs
    ndi = 100*pd.Series(ndm).ewm(alpha=1/14, adjust=False).mean()/trs
    df['adx'] = (100*(pdi-ndi).abs()/(pdi+ndi+1e-9)).ewm(alpha=1/14, adjust=False).mean()
    lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
    df['k'] = 100*(c-lo14)/(hi14-lo14+1e-9)
    m = c.ewm(span=12, adjust=False).mean()-c.ewm(span=26, adjust=False).mean()
    df['hist'] = m - m.ewm(span=9, adjust=False).mean()
    return df

def signals(df, vol_k=6, hours=(7,17)):
    c,h,l,e21,htf = df['close'],df['high'],df['low'],df['ema21'],df['htf']
    spr = df['spread']*0.01; hr = df['time'].dt.hour
    gate = (hr>=hours[0])&(hr<hours[1])&(df['atr14']>=vol_k*spr)
    up = (c>htf)&(htf>htf.shift(30)); dn = (c<htf)&(htf<htf.shift(30))
    tu = (l.shift(1)<=e21.shift(1))|(l.shift(2)<=e21.shift(2))
    td = (h.shift(1)>=e21.shift(1))|(h.shift(2)>=e21.shift(2))
    base_l = gate&up&tu&(c>h.shift(1)); base_s = gate&dn&td&(c<l.shift(1))
    k, hist = df['k'], df['hist']
    F = {
      'rsi':   (df['rsi14']<45, df['rsi14']>55),
      'bb':    ((l<=df['bb_lower']).rolling(3).max()>0, (h>=df['bb_upper']).rolling(3).max()>0),
      'adx':   (df['adx']>20, df['adx']>20),
      'stoch': ((k.shift(1)<30)&(k>k.shift(1)), (k.shift(1)>70)&(k<k.shift(1))),
      'macd':  (hist>hist.shift(1), hist<hist.shift(1)),
      'm5':    ((df['m5']>htf)&(c>df['m5']), (df['m5']<htf)&(c<df['m5'])),
    }
    return base_l, base_s, F

def run(df, sig_l, sig_s, tp_atr, sl_atr, max_bars):
    o,h,l,c = (df[x].values for x in ('open','high','low','close'))
    atr, spr = df['atr14'].values, df['spread'].values*0.01
    sl_, ss_ = sig_l.values, sig_s.values
    pos=None; bal=START; peak=START; mdd=0.0; pnls=[]
    for i in range(WARM, len(df)-1):
        if pos:
            d,e,tp,sl,t0 = pos
            hit_sl = l[i]<=sl if d>0 else h[i]+spr[i]>=sl
            hit_tp = h[i]>=tp if d>0 else l[i]+spr[i]<=tp
            if hit_sl or hit_tp or i-t0>=max_bars:
                px = sl if hit_sl else tp if hit_tp else (c[i] if d>0 else c[i]+spr[i])
                p=(px-e)*d*LOT*MULT; bal+=p; pnls.append(p); pos=None
                peak=max(peak,bal); mdd=max(mdd,peak-bal)
            continue
        d = 1 if sl_[i] else -1 if ss_[i] else 0
        if d:
            a=atr[i]; e=o[i+1]+(spr[i] if d>0 else 0)
            pos=(d,e,e+d*tp_atr*a,e-d*sl_atr*a,i+1)
    k=len(pnls); w=[x for x in pnls if x>0]; ls=[-x for x in pnls if x<=0]
    return dict(trades=k, net=round(bal-START,2), win=round(len(w)/k*100,1) if k else 0,
                pf=round(sum(w)/sum(ls),2) if ls else 999, dd=round(mdd,2),
                avg_win=round(np.mean(w),2) if w else 0, avg_loss=round(np.mean(ls),2) if ls else 0)

if __name__=="__main__":
    df=pd.read_csv('data_cache/XAUUSD_M1_LONG.csv'); df['time']=pd.to_datetime(df['time'])
    df=features(sea.enrich_features(df)); cut=int(len(df)*0.6)
    tr, te = df.iloc[:cut].reset_index(drop=True), df.iloc[cut-WARM:].reset_index(drop=True)
    pre = {name: signals(d) for name,d in (('tr',tr),('te',te))}
    names = list(pre['tr'][2])
    combos = [()]+[c for r in (1,2,3) for c in itertools.combinations(names, r)]
    def sig(key, combo):
        bl,bs_,F = pre[key]
        for f in combo: bl = bl&F[f][0]; bs_ = bs_&F[f][1]
        return bl.fillna(False), bs_.fillna(False)
    rows=[]
    for combo in combos:
        str_, ste = sig('tr',combo), sig('te',combo)
        for tp,sl,mb in itertools.product([0.2,0.3,0.5,0.8],[2.0,3.0,4.0],[30,60]):
            r=run(tr,*str_,tp,sl,mb)
            if r['trades']>=30: rows.append((combo,(tp,sl,mb),r,run(te,*ste,tp,sl,mb)))
    hi=[x for x in rows if x[2]['win']>=90 and x[3]['win']>=90]
    ok=[x for x in hi if x[2]['net']>0 and x[3]['net']>0]
    print(f"configs tested: {len(rows)} | win>=90% train+test: {len(hi)} | ...and profitable both: {len(ok)}")
    print("\nHIGHEST TEST WIN RATES (combo, (tp_atr, sl_atr, max_bars)):")
    for combo,p,a,b in sorted(rows,key=lambda x:-x[3]['win'])[:5]:
        print(combo,p,"\n  train",a,"\n  TEST ",b)
    print("\nBEST PROFITABLE ON BOTH (by test PF):")
    both=[x for x in rows if x[2]['net']>0 and x[3]['net']>0]
    for combo,p,a,b in sorted(both,key=lambda x:-x[3]['pf'])[:5]:
        print(combo,p,"\n  train",a,"\n  TEST ",b)
    for combo,p,a,b in ok: print("PASS",combo,p,a,b)
