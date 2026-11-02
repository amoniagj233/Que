import MetaTrader5 as mt5

def protect():
    if not mt5.initialize():
        print("MT5 init failed")
        return
        
    positions = mt5.positions_get()
    if not positions:
        print("No open positions")
        return
        
    for p in positions:
        sym = p.symbol
        info = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        if not info or not tick:
            continue
            
        cur_p = (tick.bid + tick.ask) / 2.0
        digits = info.digits
        
        # If BTC
        if "BTC" in sym.upper():
            new_sl = round(p.price_open - (p.price_open * 0.020), digits) if p.type == 0 else round(p.price_open + (p.price_open * 0.020), digits)
            if (p.type == 0 and new_sl < p.sl) or (p.type == 1 and new_sl > p.sl):
                print(f"Upgrading BTC #{p.ticket} SL from {p.sl} to {new_sl} (giving 2.0% breathing room)")
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": p.ticket,
                    "sl": new_sl,
                    "tp": p.tp
                }
                res = mt5.order_send(req)
                print(f"Result: {res.retcode if res else 'None'}")
                
        # If DOGE
        elif "DOGE" in sym.upper():
            new_sl = round(p.price_open - (p.price_open * 0.020), digits) if p.type == 0 else round(p.price_open + (p.price_open * 0.020), digits)
            if (p.type == 0 and new_sl < p.sl) or (p.type == 1 and new_sl > p.sl):
                print(f"Upgrading DOGE #{p.ticket} SL from {p.sl} to {new_sl} (giving 2.0% breathing room)")
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": p.ticket,
                    "sl": new_sl,
                    "tp": p.tp
                }
                res = mt5.order_send(req)
                print(f"Result: {res.retcode if res else 'None'}")

    mt5.shutdown()

if __name__ == '__main__':
    protect()
