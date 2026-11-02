with open('xto_upgrade_atr.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            atr = get_m1_atr(14)
            dynamic_step = max(MIN_STEP_PTS * 0.01, atr * ATR_STEP_MULT)
            dynamic_tp   = max(MIN_STEP_PTS * 0.01, atr * ATR_TP_MULT)
            
            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket(mt5.POSITION_TYPE_BUY)
            
            # 1. Disaster SL
            if b_cnt > 0 and b_pnl <= -MAX_BASKET_LOSS:
                close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                continue
                
            # 2. Dynamic ATR GroupTP
            if b_cnt > 0 and b_vwap > 0:
                target_tp = b_vwap + dynamic_tp
                if tick.bid >= target_tp or b_pnl >= 2.50:
                    log(f"[TP] Dynamic ATR GroupTP Hit! avg={b_vwap:.2f} | TP={target_tp:.2f} | PnL=+${b_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP_ATR")
                    continue
                    
            # 3. Dynamic Grid Addition
            if b_cnt == 0:
                open_order(mt5.ORDER_TYPE_BUY, calc_lot(0), "Initial_Layer")
            elif b_cnt < MAX_LAYERS:
                if (b_worst - tick.ask) >= dynamic_step:
                    open_order(mt5.ORDER_TYPE_BUY, calc_lot(b_cnt), f"DCA_L{b_cnt+1}_Step={dynamic_step:.2f}")"""

replacement = """            # Live Pattern Learning & Regime Adaptation
            pat = analyze_live_market_pattern(SYMBOL)
            atr = pat['atr'] if pat else get_m1_atr(14)
            step_m = pat['step_mult'] if pat else ATR_STEP_MULT
            tp_m   = pat['tp_mult'] if pat else ATR_TP_MULT
            allow_new = pat['allow_new_basket'] if pat else True
            need_green = pat['require_green_bar'] if pat else False

            dynamic_step = max(MIN_STEP_PTS * 0.01, atr * step_m)
            dynamic_tp   = max(MIN_STEP_PTS * 0.01, atr * tp_m)

            b_cnt, b_lots, b_vwap, b_pnl, b_worst, _ = get_basket(mt5.POSITION_TYPE_BUY)

            # 1. Disaster SL
            if b_cnt > 0 and b_pnl <= -MAX_BASKET_LOSS:
                close_basket(mt5.POSITION_TYPE_BUY, "Disaster_SL")
                continue

            # 2. Dynamic Adaptive GroupTP
            if b_cnt > 0 and b_vwap > 0:
                target_tp = b_vwap + dynamic_tp
                if tick.bid >= target_tp or b_pnl >= 2.00:
                    log(f"[TP] Adaptive ATR GroupTP Hit! avg={b_vwap:.2f} | TP={target_tp:.2f} | PnL=+${b_pnl:.2f}")
                    close_basket(mt5.POSITION_TYPE_BUY, "GroupTP_ATR")
                    continue

            # 3. Dynamic Grid Addition with Pattern Safeguards
            if b_cnt == 0:
                if allow_new:
                    open_order(mt5.ORDER_TYPE_BUY, calc_lot(0), "Initial_Layer")
            elif b_cnt < MAX_LAYERS:
                if (b_worst - tick.ask) >= dynamic_step:
                    can_dca = True
                    if need_green:
                        rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 2)
                        if rates_m1 is not None and len(rates_m1) >= 2:
                            can_dca = rates_m1[-1]['close'] > rates_m1[-1]['open']
                    if can_dca:
                        open_order(mt5.ORDER_TYPE_BUY, calc_lot(b_cnt), f"DCA_L{b_cnt+1}_Regime={pat['regime'] if pat else 'NORMAL'}")"""

if target in content:
    content = content.replace(target, replacement)
    with open('xto_upgrade_atr.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched xto_upgrade_atr.py with Live Pattern Learner")
else:
    print("Target string not found in xto_upgrade_atr.py")
