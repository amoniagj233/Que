import MetaTrader5 as mt5

if mt5.initialize():
    sym = mt5.symbol_info("XAUUSD")
    tick = mt5.symbol_info_tick("XAUUSD")
    print(f"Symbol: {sym.name} | Filling mode: {sym.filling_mode}")
    for f_mode, name in [(mt5.ORDER_FILLING_FOK, "FOK"), (mt5.ORDER_FILLING_IOC, "IOC"), (mt5.ORDER_FILLING_RETURN, "RETURN")]:
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "XAUUSD",
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 20,
            "magic": 1111,
            "comment": "Check",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": f_mode
        }
        res = mt5.order_check(req)
        print(f"Check {name} ({f_mode}): retcode={res.retcode if res else 'None'}, comment={res.comment if res else 'None'}, margin_free={res.margin_free if res else 'None'}")
    mt5.shutdown()
