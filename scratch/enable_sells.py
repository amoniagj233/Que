with open('xto_speeder_trader.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """            # SELL basket management (if enabled)
            if ALLOW_SELL:
                if sell_count == 0 and buy_count == 0:
                    # Only open SELL if no BUY basket active (avoid fighting both sides at once)
                    pass  # Safe mode: only trade one direction at a time
                elif sell_count > 0 and sell_count < MAX_LAYERS:
                    if (tick.bid - sell_worst) >= step_dist:
                        next_lot = calc_lot(sell_count)
                        open_order(mt5.ORDER_TYPE_SELL, next_lot, f"Layer_{sell_count+1}_DCA_avg={sell_vwap:.2f}")"""

replacement = """            # SELL basket management (Bi-Directional Active)
            if ALLOW_SELL:
                if sell_count == 0:
                    rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 30)
                    if rates_m1 is not None and len(rates_m1) >= 20:
                        df_t = pd.DataFrame(rates_m1)
                        if df_t['close'].iloc[-1] < df_t['close'].ewm(span=21, adjust=False).mean().iloc[-1]:
                            open_order(mt5.ORDER_TYPE_SELL, calc_lot(0), "Layer_1_Initial_SELL")
                elif sell_count > 0 and sell_count < MAX_LAYERS:
                    if (tick.bid - sell_worst) >= step_dist:
                        next_lot = calc_lot(sell_count)
                        open_order(mt5.ORDER_TYPE_SELL, next_lot, f"Layer_{sell_count+1}_DCA_avg={sell_vwap:.2f}")"""

if target in text:
    text = text.replace(target, replacement)
    with open('xto_speeder_trader.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Updated xto_speeder_trader.py to allow SELL trades successfully!")
else:
    print("Target block not matched exactly")
