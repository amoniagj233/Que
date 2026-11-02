with open('strategy_evolution_agent.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. In enrich_features:
old_features = """    # Price Action & Velocity
    d['bullish'] = d['close'] > d['open']
    d['bearish'] = d['close'] < d['open']
    d['body'] = (d['close'] - d['open']).abs()
    d['hammer'] = (d['bullish']) & ((d['open'] - d['low']) > 2 * d['body'])
    d['shooting_star'] = (d['bearish']) & ((d['high'] - d['open']) > 2 * d['body'])
    d['vel3'] = (d['close'] - d['close'].shift(3)).fillna(0.0)

    d.dropna(inplace=True)"""

new_features = """    # Price Action & Velocity
    d['bullish'] = d['close'] > d['open']
    d['bearish'] = d['close'] < d['open']
    d['body'] = (d['close'] - d['open']).abs()
    d['hammer'] = (d['bullish']) & ((d['open'] - d['low']) > 2 * d['body'])
    d['shooting_star'] = (d['bearish']) & ((d['high'] - d['open']) > 2 * d['body'])
    d['vel3'] = (d['close'] - d['close'].shift(3)).fillna(0.0)

    # 24h Macro Mean Baseline (332 bars on M5 = 27.6h)
    d['ma332'] = d['close'].rolling(332).mean().bfill()
    d['dist_332_atr'] = ((d['close'] - d['ma332']) / (d['atr14'] + 1e-9)).fillna(0.0)

    d.dropna(inplace=True)"""

if old_features in c:
    c = c.replace(old_features, new_features)
    print('Updated enrich_features')

# 2. In backtest_genome:
old_entry_eval = """        else:
            # Basket empty: evaluate entry
            allow_buy = trend >= 0
            allow_sell = trend <= 0"""

new_entry_eval = """        else:
            # Basket empty: evaluate entry
            allow_buy = trend >= 0
            allow_sell = trend <= 0

            # 24h Anti-Exhaustion Guard (Caps overextension from 24h baseline)
            exh_cap = p.get('exhaustion_cap', 7.0)
            if exh_cap > 0:
                dist_atr = row.get('dist_332_atr', 0.0)
                if dist_atr > exh_cap:
                    allow_buy = False
                elif dist_atr < -exh_cap:
                    allow_sell = False"""

if old_entry_eval in c:
    c = c.replace(old_entry_eval, new_entry_eval)
    print('Updated backtest_genome entry logic')

# 3. Add to random genes
old_genes = "'disaster_sl': random.choice([100.0, 120.0, 140.0, 150.0])"
new_genes = "'disaster_sl': random.choice([100.0, 120.0, 140.0, 150.0]),\n            'exhaustion_cap': round(random.choice([0.0, 5.0, 7.0, 8.5, 10.0]), 1)"
if old_genes in c:
    c = c.replace(old_genes, new_genes)
    print('Updated generate_random_genes')

with open('strategy_evolution_agent.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done!')
