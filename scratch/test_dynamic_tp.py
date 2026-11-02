import pandas as pd
from test_quantum_improvements import load_extended_data, run_quantum_simulation

df = load_extended_data()

# Modify simulation with Layer-Weighted Target TP
def run_weighted_tp(df, base_target=3.0, disaster_sl=130.0):
    balance = 1000.0
    initial_balance = 1000.0
    peak_equity = 1000.0
    max_dd = 0.0
    closed_trades = []
    basket = []
    basket_type = None

    for i in range(60, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        high = row['high']
        low = row['low']
        atr = row['atr']
        rsi = row['rsi']
        vel3 = row['velocity_3bar']
        bull_c = row['bullish']
        bear_c = row['bearish']
        trend_m5 = 1 if row['ema21'] > row['ema55'] else -1

        if len(basket) > 0:
            total_lots = sum(x['lot'] for x in basket)
            vwap = sum(x['price'] * x['lot'] for x in basket) / total_lots

            if basket_type == 'BUY':
                floating_pnl = sum((curr_price - x['price']) * x['lot'] * 100 for x in basket)
            else:
                floating_pnl = sum((x['price'] - curr_price) * x['lot'] * 100 for x in basket)

            current_equity = balance + floating_pnl
            if current_equity > peak_equity: peak_equity = current_equity
            dd = peak_equity - current_equity
            if dd > max_dd: max_dd = dd

            if disaster_sl > 0 and floating_pnl <= -disaster_sl:
                balance += floating_pnl
                closed_trades.append({'pnl': floating_pnl, 'reason': 'Disaster_SL'})
                basket = []
                basket_type = None
                continue

            # Layer-Weighted Target TP
            target_usd = base_target + (len(basket) - 1) * 2.0
            tp_dist = max(1.20, atr * 1.1)

            tp_hit = False
            realized_pnl = 0.0
            if basket_type == 'BUY':
                target_tp = vwap + tp_dist
                if high >= target_tp or floating_pnl >= target_usd:
                    tp_hit = True
                    realized_pnl = sum((target_tp - x['price']) * x['lot'] * 100 for x in basket)
            else:
                target_tp = vwap - tp_dist
                if low <= target_tp or floating_pnl >= target_usd:
                    tp_hit = True
                    realized_pnl = sum((x['price'] - target_tp) * x['lot'] * 100 for x in basket)

            if tp_hit:
                balance += realized_pnl
                closed_trades.append({'pnl': realized_pnl, 'reason': 'GroupTP'})
                basket = []
                basket_type = None
                continue

            # Asymmetric Grid Addition + Waterfall Freeze
            if len(basket) < 5:
                layer = len(basket)
                exp_factors = [1.8, 2.4, 3.2, 4.2]
                mult = exp_factors[min(layer - 1, len(exp_factors) - 1)]
                step = max(3.00, atr * mult)

                worst_price = min(x['price'] for x in basket) if basket_type == 'BUY' else max(x['price'] for x in basket)
                dist_ok = (worst_price - curr_price >= step) if basket_type == 'BUY' else (curr_price - worst_price >= step)

                if dist_ok:
                    confirm_ok = True
                    if basket_type == 'BUY':
                        is_waterfall = vel3 < -(2.0 * atr)
                        confirm_ok = (bull_c or rsi < 28) if is_waterfall else (bull_c or rsi < 35)
                    else:
                        is_waterfall = vel3 > (2.0 * atr)
                        confirm_ok = (bear_c or rsi > 72) if is_waterfall else (bear_c or rsi > 65)

                    if confirm_ok:
                        next_lot = 0.01 if layer < 2 else 0.02
                        fill_p = (curr_price + 0.35) if basket_type == 'BUY' else (curr_price - 0.35)
                        basket.append({'type': basket_type, 'lot': next_lot, 'price': fill_p})

        else:
            allow_buy = trend_m5 > 0
            allow_sell = trend_m5 < 0
            if allow_buy and (bull_c or rsi < 32):
                basket_type = 'BUY'
                basket.append({'type': 'BUY', 'lot': 0.01, 'price': curr_price + 0.35})
            elif allow_sell and (bear_c or rsi > 68):
                basket_type = 'SELL'
                basket.append({'type': 'SELL', 'lot': 0.01, 'price': curr_price - 0.35})

    total = len(closed_trades)
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    net_profit = balance - initial_balance
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0

    return {
        'final_bal': balance, 'profit': net_profit, 'roi': net_profit / initial_balance * 100,
        'win_rate': win_rate, 'max_dd': max_dd, 'dd_pct': max_dd / peak_equity * 100,
        'pf': pf, 'sls': len(losses)
    }

for sl in [110, 125, 140, 150]:
    r = run_weighted_tp(df, base_target=3.5, disaster_sl=sl)
    print(f"SL ${sl} -> Final: ${r['final_bal']:.2f} | Profit: +${r['profit']:.2f} (+{r['roi']:.1f}%) | WinRate: {r['win_rate']:.1f}% | MaxDD: ${r['max_dd']:.1f} ({r['dd_pct']:.1f}%) | PF: {r['pf']:.2f} | Stops: {r['sls']}")
