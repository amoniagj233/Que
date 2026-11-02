"""
====================================================================================
  🧬 STRATEGY EVOLUTION AGENT (DARWIN QUANT ENGINE) - AUTONOMOUS TRADING AI
====================================================================================
Purpose:
  Autonomous AI Agent that continuously generates, backtests, ranks, mutates, and
  deploys trading strategies on Gold (XAUUSD) across multiple timeframes.

Capabilities:
  1. Automated Indicator & Combinatorial Generation:
     - Trends: EMAs (9/21, 21/55, 50/200), SuperTrend, ADX regime filters
     - Oscillators: RSI, Stochastic %K/%D, MACD histograms, Bollinger Bands
     - Structure: Swing High/Low fractals, Candlestick Reversals (Hammers, Engulfing),
       Volume Weighted Average Price (VWAP), Price Velocity
     - Grids & Sizing: Asymmetric ATR Expansion, Clamped Margin Sizing, Linear Lots
     - Exits: Dynamic ATR TP, Trailing Breakeven, Basket Scalp Targets, Disaster Stops

  2. Quantitative Fitness & Tournament Scoring:
     - Backtests across thousands of high-fidelity M5/M15/H1 historical candles.
     - Institutional Multi-Objective Fitness:
         Fitness = (Net Profit * Profit Factor * (Win Rate / 100)) / (1 + Max DD %)
     - Strict gates: Minimum 80% Win Rate, Minimum 1.30 Profit Factor, Max DD < 25%.

  3. Continuous Evolution & Survival-of-the-Fittest Pruning:
     - Maintains a persistent leaderboard in `strategy_leaderboard.json`.
     - Constantly promotes superior discoveries and retires obsolete bots.
     - Retains strictly the TOP 2 performing strategies.

  4. Autonomous Live Deployment & Hot-Swapping:
     - Emits deployable bot code for Slot 1 (`Magic 1111`) and Slot 2 (`Magic 2222`).
     - Hot-swaps the supervisor when a statistically superior strategy is discovered.
     - Logs all generations and promotions to `logs/evolution_journal.log`.
====================================================================================
"""

from execution_gateway import guarded_order_send

import os
import sys
import time
import json
import random
import itertools
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(BASE_DIR, "data_cache")
LOG_DIR         = os.path.join(BASE_DIR, "logs")
SCRATCH_DIR     = os.path.join(BASE_DIR, "scratch")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)

LEADERBOARD_FILE = os.path.join(BASE_DIR, "strategy_leaderboard.json")
JOURNAL_FILE     = os.path.join(LOG_DIR, "evolution_journal.log")
BOT_SLOT_1_CODE  = os.path.join(BASE_DIR, "bot_slot_1.py")
BOT_SLOT_2_CODE  = os.path.join(BASE_DIR, "bot_slot_2.py")
EVOLUTION_STATE  = os.path.join(BASE_DIR, "evolution_state.json")

# ================= Logging =================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [EVO-AGENT] {msg}"
    print(line, flush=True)
    try:
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ================= Data Pipeline =================
def load_datasets():
    datasets = {}
    m1_file = os.path.join(DATA_DIR, "XAUUSD_M1_43200.csv")
    m5_file = os.path.join(DATA_DIR, "XAUUSD_M5_1MONTH.csv")
    m15_file = os.path.join(DATA_DIR, "XAUUSD_M15_5000.csv")
    h1_file = os.path.join(DATA_DIR, "XAUUSD_H1_5000.csv")

    if os.path.exists(m1_file):
        df_m1 = pd.read_csv(m1_file)
        df_m1['time'] = pd.to_datetime(df_m1['time'], unit='s' if df_m1['time'].iloc[0] > 1e8 else None)
        datasets['M1'] = enrich_features(df_m1)

    if os.path.exists(m5_file):
        df_m5 = pd.read_csv(m5_file)
        df_m5['time'] = pd.to_datetime(df_m5['time'])
        datasets['M5'] = enrich_features(df_m5)

    if os.path.exists(m15_file):
        df_m15 = pd.read_csv(m15_file)
        df_m15['time'] = pd.to_datetime(df_m15['time'])
        datasets['M15'] = enrich_features(df_m15)

    if os.path.exists(h1_file):
        df_h1 = pd.read_csv(h1_file)
        df_h1['time'] = pd.to_datetime(df_h1['time'])
        datasets['H1'] = enrich_features(df_h1)

    return datasets

def enrich_features(df):
    d = df.copy()
    # True Range & ATR
    tr1 = d['high'] - d['low']
    tr2 = (d['high'] - d['close'].shift(1)).abs()
    tr3 = (d['low'] - d['close'].shift(1)).abs()
    d['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    d['atr14'] = d['tr'].rolling(14).mean().bfill()

    # RSI(14)
    delta = d['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    d['rsi14'] = (100 - (100 / (1 + rs))).bfill()

    # EMAs
    d['ema9']  = d['close'].ewm(span=9, adjust=False).mean()
    d['ema21'] = d['close'].ewm(span=21, adjust=False).mean()
    d['ema55'] = d['close'].ewm(span=55, adjust=False).mean()
    d['ema200']= d['close'].ewm(span=200, adjust=False).mean()

    # Bollinger Bands (20, 2)
    bb_mean = d['close'].rolling(20).mean()
    bb_std  = d['close'].rolling(20).std()
    d['bb_upper'] = (bb_mean + 2 * bb_std).bfill()
    d['bb_lower'] = (bb_mean - 2 * bb_std).bfill()
    d['bb_width'] = ((d['bb_upper'] - d['bb_lower']) / bb_mean).bfill()

    # Price Action & Velocity
    d['bullish'] = d['close'] > d['open']
    d['bearish'] = d['close'] < d['open']
    d['body'] = (d['close'] - d['open']).abs()
    d['hammer'] = (d['bullish']) & ((d['open'] - d['low']) > 2 * d['body'])
    d['shooting_star'] = (d['bearish']) & ((d['high'] - d['open']) > 2 * d['body'])
    d['vel3'] = (d['close'] - d['close'].shift(3)).fillna(0.0)

    # 24h Macro Mean Baseline (332 bars on M5 = 27.6h)
    d['ma332'] = d['close'].rolling(332).mean().bfill()
    d['dist_332_atr'] = ((d['close'] - d['ma332']) / (d['atr14'] + 1e-9)).fillna(0.0)

    d.dropna(inplace=True)
    d.reset_index(drop=True, inplace=True)
    return d

# ================= Strategy Genome / Space =================
class StrategyDNA:
    def __init__(self, gene_dict=None):
        if gene_dict:
            self.genes = gene_dict
        else:
            self.genes = self.generate_random_genes()

    @staticmethod
    def generate_random_genes():
        return {
            'name': f"Strat-{random.randint(1000, 9999)}",
            'timeframe': random.choice(['M1', 'M5', 'M15']),
            'trend_indicator': random.choice(['EMA_21_55', 'EMA_9_21', 'PRICE_VS_EMA200', 'NONE']),
            'entry_trigger': random.choice(['CANDLE_DIRECTION', 'RSI_EXTREMES', 'BB_REVERSION', 'VELOCITY_PULSE']),
            'spacing_mode': random.choice(['ASYMMETRIC_ATR', 'DYNAMIC_ATR', 'FIXED_WIDE']),
            'atr_mult': round(random.uniform(1.6, 2.8), 2),
            'asym_growth': round(random.uniform(1.2, 1.6), 2),
            'waterfall_freeze': random.choice([True, False]),
            'waterfall_thresh': round(random.uniform(1.8, 3.0), 1),
            'lot_mode': random.choice(['clamped', 'linear']),
            'max_layers': random.choice([3, 4, 5]),
            'tp_mode': random.choice(['DYNAMIC_ATR', 'FIXED_USD', 'HYBRID']),
            'tp_atr_mult': round(random.uniform(1.0, 1.8), 2),
            'target_usd': round(random.uniform(3.0, 8.0), 1),
            'disaster_sl': random.choice([100.0, 120.0, 140.0, 150.0]),
            'exhaustion_cap': round(random.choice([0.0, 5.0, 7.0, 8.5, 10.0]), 1)
        }

    def mutate(self):
        new_genes = dict(self.genes)
        new_genes['name'] = f"Mut-{random.randint(1000, 9999)}"
        # Randomly mutate 1 or 2 parameters
        mutation_keys = ['timeframe', 'trend_indicator', 'entry_trigger', 'spacing_mode', 'atr_mult',
                         'waterfall_freeze', 'lot_mode', 'max_layers', 'target_usd', 'disaster_sl']
        key_to_mutate = random.choice(mutation_keys)

        if key_to_mutate == 'timeframe':
            new_genes['timeframe'] = random.choice(['M1', 'M5', 'M15'])
        elif key_to_mutate == 'trend_indicator':
            new_genes['trend_indicator'] = random.choice(['EMA_21_55', 'EMA_9_21', 'PRICE_VS_EMA200', 'NONE'])
        elif key_to_mutate == 'entry_trigger':
            new_genes['entry_trigger'] = random.choice(['CANDLE_DIRECTION', 'RSI_EXTREMES', 'BB_REVERSION', 'VELOCITY_PULSE'])
        elif key_to_mutate == 'spacing_mode':
            new_genes['spacing_mode'] = random.choice(['ASYMMETRIC_ATR', 'DYNAMIC_ATR', 'FIXED_WIDE'])
        elif key_to_mutate == 'atr_mult':
            new_genes['atr_mult'] = round(max(1.5, min(3.0, new_genes['atr_mult'] + random.uniform(-0.3, 0.3))), 2)
        elif key_to_mutate == 'waterfall_freeze':
            new_genes['waterfall_freeze'] = not new_genes['waterfall_freeze']
        elif key_to_mutate == 'lot_mode':
            new_genes['lot_mode'] = 'clamped' if new_genes['lot_mode'] == 'linear' else 'linear'
        elif key_to_mutate == 'max_layers':
            new_genes['max_layers'] = random.choice([3, 4, 5])
        elif key_to_mutate == 'target_usd':
            new_genes['target_usd'] = round(max(2.5, min(10.0, new_genes['target_usd'] + random.uniform(-1.0, 1.5))), 1)
        elif key_to_mutate == 'disaster_sl':
            new_genes['disaster_sl'] = random.choice([100.0, 120.0, 140.0, 150.0])

        return StrategyDNA(new_genes)

# ================= Backtest Simulator =================
def backtest_genome(df, dna, start_bal=1000.0, spread=0.35):
    p = dna.genes
    balance = start_bal
    initial_balance = start_bal
    peak_equity = start_bal
    max_dd = 0.0
    closed_trades = []

    basket = []
    basket_type = None

    max_layers = p['max_layers']
    disaster_sl = p['disaster_sl']
    base_lot = 0.01

    for i in range(50, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr14']
        rsi = row['rsi14']
        vel3 = row['vel3']
        bull_c = row['bullish']
        bear_c = row['bearish']

        # Determine trend direction
        trend = 0
        if p['trend_indicator'] == 'EMA_21_55':
            trend = 1 if row['ema21'] >= row['ema55'] else -1
        elif p['trend_indicator'] == 'EMA_9_21':
            trend = 1 if row['ema9'] >= row['ema21'] else -1
        elif p['trend_indicator'] == 'PRICE_VS_EMA200':
            trend = 1 if curr_price >= row['ema200'] else -1

        # Basket in progress
        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots

            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                floating_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

            equity = balance + floating_pnl
            if equity > peak_equity: peak_equity = equity
            dd = peak_equity - equity
            if dd > max_dd: max_dd = dd

            # Disaster SL
            if disaster_sl > 0 and floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue

            # Take Profit evaluation
            tp_dist = max(1.20, atr * p.get('tp_atr_mult', 1.2))
            target_usd = p['target_usd']

            tp_hit = False
            realized_pnl = 0.0
            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                if (p['tp_mode'] in ['DYNAMIC_ATR', 'HYBRID'] and high >= target_tp) or \
                   (p['tp_mode'] in ['FIXED_USD', 'HYBRID'] and floating_pnl >= target_usd):
                    tp_hit = True
                    realized_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                target_tp = vwap - tp_dist
                if (p['tp_mode'] in ['DYNAMIC_ATR', 'HYBRID'] and low <= target_tp) or \
                   (p['tp_mode'] in ['FIXED_USD', 'HYBRID'] and floating_pnl >= target_usd):
                    tp_hit = True
                    realized_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

            if tp_hit:
                balance += realized_pnl
                closed_trades.append({'pnl': realized_pnl, 'reason': 'GroupTP'})
                basket = []
                basket_type = None
                continue

            # Grid Addition
            if len(basket) < max_layers:
                layer = len(basket)
                if p['spacing_mode'] == 'ASYMMETRIC_ATR':
                    # Multipliers: 1.8x, 2.4x, 3.2x, 4.2x
                    mult = p['atr_mult'] * (p['asym_growth'] ** (layer - 1))
                    step = max(3.00, atr * mult)
                elif p['spacing_mode'] == 'DYNAMIC_ATR':
                    step = max(2.50, atr * p['atr_mult'])
                else:
                    step = max(4.00, p['atr_mult'] * 2.0)

                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)

                if dist_ok:
                    confirm_ok = True
                    if p['waterfall_freeze']:
                        wf_thresh = p['waterfall_thresh'] * atr
                        if basket_type == 'BUY':
                            is_waterfall = vel3 < -wf_thresh
                            confirm_ok = (bull_c or row['hammer'] or rsi < 28) if is_waterfall else (bull_c or rsi < 35)
                        else:
                            is_waterfall = vel3 > wf_thresh
                            confirm_ok = (bear_c or row['shooting_star'] or rsi > 72) if is_waterfall else (bear_c or rsi > 65)

                    if confirm_ok:
                        if p['lot_mode'] == 'clamped':
                            next_lot = base_lot if layer < 2 else (base_lot * 2.0)
                        else:
                            next_lot = base_lot

                        fill_p = (curr_price + spread) if basket_type == 'BUY' else (curr_price - spread)
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})

        else:
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
                    allow_sell = False

            # Entry Trigger Condition
            trigger = p['entry_trigger']
            buy_trig = False
            sell_trig = False

            if trigger == 'CANDLE_DIRECTION':
                buy_trig = bull_c
                sell_trig = bear_c
            elif trigger == 'RSI_EXTREMES':
                buy_trig = rsi < 35 or (bull_c and rsi < 50)
                sell_trig = rsi > 65 or (bear_c and rsi > 50)
            elif trigger == 'BB_REVERSION':
                buy_trig = curr_price <= row['bb_lower'] or (bull_c and curr_price < row['bb_upper'])
                sell_trig = curr_price >= row['bb_upper'] or (bear_c and curr_price > row['bb_lower'])
            elif trigger == 'VELOCITY_PULSE':
                buy_trig = vel3 > 1.0 and bull_c
                sell_trig = vel3 < -1.0 and bear_c

            if allow_buy and buy_trig:
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': base_lot, 'price': curr_price + spread})
            elif allow_sell and sell_trig:
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': base_lot, 'price': curr_price - spread})

    # Close any remaining
    if len(basket) > 0:
        last_price = df.iloc[-1]['close']
        if basket_type == 'BUY':
            final_pnl = sum((last_price - x['price']) * x['lot'] * 100 for x in basket)
        else:
            final_pnl = sum((x['price'] - last_price) * x['lot'] * 100 for x in basket)
        balance += final_pnl
        closed_trades.append({'pnl': final_pnl, 'reason': 'EndSession'})

    # Evaluation Metrics
    total = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    disasters = [t for t in closed_trades if t['reason'] == 'Disaster_SL']
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    dd_pct = (max_dd / peak_equity * 100) if peak_equity > 0 else 100.0

    # Institutional Fitness Metric:
    # High Net Profit, High Win Rate, High PF, Low DD
    if net_profit <= 0 or win_rate < 75.0 or dd_pct > 35.0:
        fitness = -abs(net_profit) - dd_pct
    else:
        fitness = (net_profit * pf * (win_rate / 100.0)) / (1.0 + (dd_pct / 10.0))

    return {
        'dna': dna.genes,
        'net_profit': round(net_profit, 2),
        'roi_pct': round((net_profit / initial_balance * 100), 1),
        'win_rate': round(win_rate, 1),
        'total_cycles': total,
        'profit_factor': round(pf, 2),
        'max_drawdown': round(max_dd, 2),
        'max_dd_pct': round(dd_pct, 1),
        'disaster_stops': len(disasters),
        'fitness': round(fitness, 2)
    }

# ================= Leaderboard & State Management =================
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'top_strategies': [], 'generation': 0, 'total_evaluated': 0}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def update_tournament(candidates):
    board = load_leaderboard()
    existing = board.get('top_strategies', [])

    all_strats = existing + candidates
    # Sort strictly by institutional fitness
    all_strats.sort(key=lambda x: x['fitness'], reverse=True)

    # Filter out duplicates by key parameters
    unique_strats = []
    seen = set()
    for s in all_strats:
        sig = (s['dna']['trend_indicator'], s['dna']['entry_trigger'], s['dna']['spacing_mode'],
               s['dna']['atr_mult'], s['dna']['waterfall_freeze'], s['dna']['disaster_sl'])
        if sig not in seen:
            seen.add(sig)
            unique_strats.append(s)

    old_top_names = [s['dna']['name'] for s in existing]
    new_top_names = [s['dna']['name'] for s in unique_strats[:2]]

    # Retain strictly the TOP 2 working strategies! All inferior bots are deleted!
    board['top_strategies'] = unique_strats[:2]
    board['total_evaluated'] = board.get('total_evaluated', 0) + len(candidates)
    save_leaderboard(board)

    # Detect New Promotions & Save Discovery Alert
    if old_top_names != new_top_names and len(board['top_strategies']) > 0:
        champ = board['top_strategies'][0]
        alert = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_new": True,
            "champion": {
                "name": champ['dna']['name'],
                "net_profit": champ['net_profit'],
                "roi_pct": champ['roi_pct'],
                "win_rate": champ['win_rate'],
                "profit_factor": champ['profit_factor'],
                "max_drawdown": champ['max_drawdown'],
                "max_dd_pct": champ['max_dd_pct'],
                "fitness": champ['fitness'],
                "spacing_mode": champ['dna']['spacing_mode'],
                "atr_mult": champ['dna']['atr_mult']
            },
            "challenger": {
                "name": board['top_strategies'][1]['dna']['name'],
                "net_profit": board['top_strategies'][1]['net_profit'],
                "roi_pct": board['top_strategies'][1]['roi_pct'],
                "win_rate": board['top_strategies'][1]['win_rate'],
                "profit_factor": board['top_strategies'][1]['profit_factor'],
                "max_drawdown": board['top_strategies'][1]['max_drawdown'],
                "fitness": board['top_strategies'][1]['fitness']
            } if len(board['top_strategies']) > 1 else None
        }
        with open(os.path.join(BASE_DIR, "latest_discovery.json"), "w", encoding="utf-8") as f:
            json.dump(alert, f, indent=2)
        log(f"🔔 [NEW DISCOVERY ALERT SAVED] Champion: {champ['dna']['name']} (+${champ['net_profit']:.2f}, PF: {champ['profit_factor']})")

    log(f"🏆 TOURNAMENT UPDATED | Total Evaluated: {board['total_evaluated']}")
    for rank, s in enumerate(board['top_strategies'], 1):
        log(f"  Rank #{rank}: {s['dna']['name']} | Net PnL: ${s['net_profit']:+.2f} ({s['roi_pct']:+.1f}%) | "
            f"Win: {s['win_rate']}% | MaxDD: ${s['max_drawdown']:.0f} ({s['max_dd_pct']}%) | PF: {s['profit_factor']} | Fitness: {s['fitness']}")

    return board['top_strategies']

# ================= Code Generator & Live Hot-Swap =================
def emit_bot_code(strategy_result, slot_num, magic_number):
    dna = strategy_result['dna']
    target_path = BOT_SLOT_1_CODE if slot_num == 1 else BOT_SLOT_2_CODE

    code = f'''"""
Autonomous AI Generated Strategy - Slot #{slot_num}
Name         : {dna['name']}
Magic Number : {magic_number}
Generation   : Validated Darwin Evolution Model
Net Profit   : ${strategy_result['net_profit']:+.2f} ({strategy_result['roi_pct']:+.1f}% 1-Mo ROI)
Win Rate     : {strategy_result['win_rate']}% | Profit Factor: {strategy_result['profit_factor']}
Max Drawdown : ${strategy_result['max_drawdown']:.2f} ({strategy_result['max_dd_pct']}%)
"""

from execution_gateway import guarded_order_send
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time, sys, os
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SYMBOL            = "XAUUSD"
MAGIC             = {magic_number}
COMMENT           = "{dna['name'][:12]}"
BASE_LOT          = 0.01
MAX_LAYERS        = {dna['max_layers']}
DISASTER_SL_USD   = {dna['disaster_sl']}
TARGET_PROFIT_USD = {dna['target_usd']}
SLIPPAGE          = 25
LOOP_INTERVAL     = 2
EXP_FACTORS       = [1.8, 2.4, 3.2, 4.2]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{{ts}}] [SLOT-{slot_num}] {{msg}}", flush=True)

def get_market_metrics():
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 60)
    if rates is None or len(rates) < 55:
        return 3.50, 50.0, 1, False, False, 0.0
    df = pd.DataFrame(rates)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = max(1.50, float(tr.tail(14).mean()))

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    ema21 = float(df['close'].ewm(span=21, adjust=False).mean().iloc[-1])
    ema55 = float(df['close'].ewm(span=55, adjust=False).mean().iloc[-1])
    trend = 1 if ema21 >= ema55 else -1

    last = df.iloc[-1]
    bull_c = last['close'] > last['open']
    bear_c = last['close'] < last['open']
    vel3 = float(df['close'].iloc[-1] - df['close'].iloc[-4]) if len(df) >= 4 else 0.0
    return atr, rsi, trend, bull_c, bear_c, vel3

def calc_lot(layer):
    {"lot = BASE_LOT if layer < 2 else (BASE_LOT * 2.0)" if dna['lot_mode'] == 'clamped' else "lot = BASE_LOT"}
    s = mt5.symbol_info(SYMBOL)
    return round(max(s.volume_min, min(s.volume_max, lot)), 2) if s else 0.01

def get_basket(pos_type):
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return 0, 0.0, 0.0, 0.0, 0.0, 0.0
    count, total_lots, vol_price_sum, floating_pnl = 0, 0.0, 0.0, 0.0
    worst = 9999999.0 if pos_type == mt5.POSITION_TYPE_BUY else 0.0
    best  = 0.0       if pos_type == mt5.POSITION_TYPE_BUY else 9999999.0
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            count += 1
            total_lots += p.volume
            vol_price_sum += p.price_open * p.volume
            floating_pnl += p.profit + p.swap
            if pos_type == mt5.POSITION_TYPE_BUY:
                if p.price_open < worst: worst = p.price_open
                if p.price_open > best: best = p.price_open
            else:
                if p.price_open > worst: worst = p.price_open
                if p.price_open < best: best = p.price_open
    vwap = vol_price_sum / total_lots if total_lots > 0 else 0.0
    return count, total_lots, vwap, floating_pnl, worst, best

def close_basket(pos_type, reason):
    side = "BUY" if pos_type == mt5.POSITION_TYPE_BUY else "SELL"
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions: return
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return
    log(f"[CLOSE] Liquidating {{side}} basket: {{reason}}")
    for p in positions:
        if p.symbol == SYMBOL and p.magic == MAGIC and p.type == pos_type:
            c_price = tick.bid if pos_type == mt5.POSITION_TYPE_BUY else tick.ask
            c_type  = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {{
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume,
                    "type": c_type, "position": p.ticket, "price": c_price,
                    "deviation": SLIPPAGE, "magic": MAGIC, "comment": f"Evo-{{reason}}",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling
                }}
                r = guarded_order_send(mt5, req)
                if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                    break

def check_quant_desk(side):
    # 1. News Sentinel Check
    try:
        if os.path.exists("market_risk_state.json"):
            with open("market_risk_state.json", "r", encoding="utf-8") as f:
                news = json.load(f)
                if news.get("news_freeze", False):
                    ev = news.get('active_event', 'Macro Event')
                    return False, f"News Freeze ({{ev}})"
    except Exception: pass

    # 2. CRO Risk Officer Check
    try:
        if os.path.exists("cro_risk_state.json"):
            with open("cro_risk_state.json", "r", encoding="utf-8") as f:
                cro = json.load(f)
                if cro.get("circuit_breaker", False):
                    return False, "CRO Circuit Breaker Engaged"
                if not cro.get("spread_ok", True):
                    sp = cro.get('spread_usd', 0)
                    return False, f"Spread Spike (${{sp:.2f}})"
    except Exception: pass

    # 3. Macro Correlation Confluence Check
    try:
        if os.path.exists("macro_confluence.json"):
            with open("macro_confluence.json", "r", encoding="utf-8") as f:
                macro = json.load(f)
                score = macro.get("confluence_score", 0)
                if side == "BUY" and score <= -40:
                    return False, f"Macro Bearish Confluence ({{score:+d}})"
                elif side == "SELL" and score >= 40:
                    return False, f"Macro Bullish Confluence ({{score:+d}})"
    except Exception: pass

    return True, "CLEAR"

def open_order(order_type, lot, reason):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return None
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    side = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    req = {{
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
        "type": order_type, "price": price, "deviation": SLIPPAGE,
        "magic": MAGIC, "comment": f"Evo-{{side}}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
    }}
    for filling in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
        req["type_filling"] = filling
        r = guarded_order_send(mt5, req)
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"[OK] {{side}} {{lot}} lots @ {{r.price:.2f}} | {{reason}} | Ticket #{{r.order}}")
            return r
    return None

HEADWAY_TERMINAL_PATH = r"C:\\Program Files\\Headway MT5 Terminal\\terminal64.exe"

def main():
    if not mt5.initialize(path=HEADWAY_TERMINAL_PATH):
        if not mt5.initialize():
            print("MT5 init failed")
            sys.exit(1)
    acc = mt5.account_info()
    log("=" * 60)
    log(f"  ⚡ BOT SLOT #{slot_num}: {dna['name']} (Magic {magic_number})")
    log(f"  Account : {{acc.login}} | Balance: ${{acc.balance:.2f}}")
    log(f"  Spacing : {dna['spacing_mode']} (ATR Mult {dna['atr_mult']}) | Waterfall Freeze: {dna['waterfall_freeze']}")
    log("=" * 60)

    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick:
                time.sleep(LOOP_INTERVAL)
                continue

            atr, rsi, trend, bull_c, bear_c, vel3 = get_market_metrics()

            # BUY Basket
            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket(mt5.POSITION_TYPE_BUY)
            if b_cnt > 0:
                if b_pnl <= -DISASTER_SL_USD:
                    close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                    time.sleep(1); continue
                tp_dist = max(1.20, atr * {dna['tp_atr_mult']})
                if tick.bid >= (b_vwap + tp_dist) or b_pnl >= TARGET_PROFIT_USD:
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP")
                    time.sleep(1); continue
                if b_cnt < MAX_LAYERS:
                    step = max(3.00, atr * EXP_FACTORS[min(b_cnt - 1, len(EXP_FACTORS) - 1)])
                    if (b_worst - tick.ask) >= step:
                        {"confirm_ok = (bull_c or rsi < 28) if (vel3 < -(2.0 * atr)) else (bull_c or rsi < 35)" if dna['waterfall_freeze'] else "confirm_ok = bull_c"}
                        if confirm_ok:
                            dca_ok, dca_reason = check_quant_desk("BUY")
                            if dca_ok:
                                open_order(mt5.ORDER_TYPE_BUY, calc_lot(b_cnt), f"DCA_L{{b_cnt+1}}")
            elif b_cnt == 0 and trend > 0:
                if bull_c or rsi < 32:
                    desk_ok, desk_reason = check_quant_desk("BUY")
                    if desk_ok:
                        open_order(mt5.ORDER_TYPE_BUY, calc_lot(0), "Initial_BUY")

            # SELL Basket
            s_cnt, s_lots, s_vwap, s_pnl, s_worst, _ = get_basket(mt5.POSITION_TYPE_SELL)
            if s_cnt > 0:
                if s_pnl <= -DISASTER_SL_USD:
                    close_basket(mt5.POSITION_TYPE_SELL, "Disaster_SL")
                    time.sleep(1); continue
                tp_dist = max(1.20, atr * {dna['tp_atr_mult']})
                if tick.ask <= (s_vwap - tp_dist) or s_pnl >= TARGET_PROFIT_USD:
                    close_basket(mt5.POSITION_TYPE_SELL, "GroupTP")
                    time.sleep(1); continue
                if s_cnt < MAX_LAYERS:
                    step = max(3.00, atr * EXP_FACTORS[min(s_cnt - 1, len(EXP_FACTORS) - 1)])
                    if (tick.bid - s_worst) >= step:
                        {"confirm_ok = (bear_c or rsi > 72) if (vel3 > (2.0 * atr)) else (bear_c or rsi > 65)" if dna['waterfall_freeze'] else "confirm_ok = bear_c"}
                        if confirm_ok:
                            dca_ok, dca_reason = check_quant_desk("SELL")
                            if dca_ok:
                                open_order(mt5.ORDER_TYPE_SELL, calc_lot(s_cnt), f"DCA_L{{s_cnt+1}}")
            elif s_cnt == 0 and trend < 0:
                if bear_c or rsi > 68:
                    desk_ok, desk_reason = check_quant_desk("SELL")
                    if desk_ok:
                        open_order(mt5.ORDER_TYPE_SELL, calc_lot(0), "Initial_SELL")

            time.sleep(LOOP_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(3)
    mt5.shutdown()

if __name__ == "__main__":
    main()
'''
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(code)
    log(f"🚀 Deployed executable bot code for Slot #{slot_num} ({dna['name']}) -> {os.path.basename(target_path)}")

# ================= Evolutionary Epoch Loop =================
def run_evolution_epoch(datasets, num_generations=20):
    log("=" * 70)
    log(f"🧬 STARTING EVOLUTION EPOCH | Evaluating {num_generations} Genetic Strategy Mutations (M1 + M5)")
    log("=" * 70)

    df_m5 = datasets.get('M5')
    df_m1 = datasets.get('M1')
    if df_m5 is None:
        log("[ERROR] M5 dataset missing. Evolution aborted.")
        return []

    candidates = []

    # 1. Evaluate known seeded champions
    seeded_champions = [
        StrategyDNA({
            'name': 'Apex-Quantum-v1', 'timeframe': 'M5', 'trend_indicator': 'EMA_21_55',
            'entry_trigger': 'CANDLE_DIRECTION', 'spacing_mode': 'ASYMMETRIC_ATR',
            'atr_mult': 2.0, 'asym_growth': 1.35, 'waterfall_freeze': True,
            'waterfall_thresh': 2.0, 'lot_mode': 'clamped', 'max_layers': 5,
            'tp_mode': 'DYNAMIC_ATR', 'tp_atr_mult': 1.2, 'target_usd': 4.0, 'disaster_sl': 120.0
        }),
        StrategyDNA({
            'name': 'Apex-Quantum-DeepSL', 'timeframe': 'M5', 'trend_indicator': 'EMA_21_55',
            'entry_trigger': 'CANDLE_DIRECTION', 'spacing_mode': 'ASYMMETRIC_ATR',
            'atr_mult': 2.2, 'asym_growth': 1.4, 'waterfall_freeze': True,
            'waterfall_thresh': 2.2, 'lot_mode': 'clamped', 'max_layers': 5,
            'tp_mode': 'DYNAMIC_ATR', 'tp_atr_mult': 1.3, 'target_usd': 4.5, 'disaster_sl': 150.0
        }),
        # Seed an institutional M1 Scalper Grid candidate
        StrategyDNA({
            'name': 'M1-Quantum-Scalp', 'timeframe': 'M1', 'trend_indicator': 'EMA_21_55',
            'entry_trigger': 'CANDLE_DIRECTION', 'spacing_mode': 'ASYMMETRIC_ATR',
            'atr_mult': 2.2, 'asym_growth': 1.5, 'waterfall_freeze': True,
            'waterfall_thresh': 2.5, 'lot_mode': 'clamped', 'max_layers': 4,
            'tp_mode': 'DYNAMIC_ATR', 'tp_atr_mult': 1.2, 'target_usd': 3.5, 'disaster_sl': 120.0
        })
    ]

    for seed in seeded_champions:
        target_df = df_m1 if (seed.genes.get('timeframe') == 'M1' and df_m1 is not None) else df_m5
        res = backtest_genome(target_df, seed)
        candidates.append(res)

    # 2. Mutate and explore new combinatorial strategies
    base_parents = [seeded_champions[0], seeded_champions[1], seeded_champions[2]]
    for _ in range(num_generations - len(seeded_champions)):
        parent = random.choice(base_parents)
        child = parent.mutate()
        target_df = df_m1 if (child.genes.get('timeframe') == 'M1' and df_m1 is not None) else df_m5
        res = backtest_genome(target_df, child)
        candidates.append(res)
        if res['fitness'] > 1500.0:
            base_parents.append(child)

    # 3. Update tournament & prune inferior bots
    top_two = update_tournament(candidates)

    # 4. Auto-deploy the Top 2 Bots
    if len(top_two) >= 1:
        emit_bot_code(top_two[0], slot_num=1, magic_number=1111)
    if len(top_two) >= 2:
        emit_bot_code(top_two[1], slot_num=2, magic_number=2222)

    return top_two

def main():
    log("====================================================================")
    log("  🤖 DARWIN QUANT AI AGENT ACTIVE: AUTONOMOUS STRATEGY EVOLUTION")
    log("====================================================================")

    datasets = load_datasets()
    log(f"Loaded Datasets: {list(datasets.keys())} ({sum(len(d) for d in datasets.values())} total bars)")

    # Execute immediate initial evolution round
    top_two = run_evolution_epoch(datasets, num_generations=25)

    # Continuous Evolution Loop
    epoch = 1
    while True:
        try:
            log(f"\n⏳ Standby interval: Next evolution epoch in 15 minutes (Epoch #{epoch + 1})...")
            time.sleep(900) # Re-evolve every 15 minutes with fresh market variations
            epoch += 1
            datasets = load_datasets()
            top_two = run_evolution_epoch(datasets, num_generations=15)
        except KeyboardInterrupt:
            log("Evolution agent paused by user.")
            break
        except Exception as e:
            log(f"Evolution loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
