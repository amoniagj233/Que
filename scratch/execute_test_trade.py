import MetaTrader5 as mt5
import sys
import time

def main():
    if not mt5.initialize():
        print(f"FAILED to initialize MT5: {mt5.last_error()}")
        sys.exit(1)

    account_info = mt5.account_info()
    if not account_info:
        print("Could not retrieve account info.")
        mt5.shutdown()
        sys.exit(1)

    print(f"Logged into Account: {account_info.login} on {account_info.server}")
    print(f"Balance: ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f}")

    symbol = "XAUUSD"
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        sys.exit(1)

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"Failed to get tick for {symbol}")
        mt5.shutdown()
        sys.exit(1)

    print(f"Current {symbol} Tick: Bid={tick.bid:.2f}, Ask={tick.ask:.2f}, Spread={round((tick.ask-tick.bid)*100, 1)} pts")

    # Determine trade parameters
    # Let's execute a small 0.01 Buy or Sell test trade
    lot = 0.01
    action = mt5.ORDER_TYPE_BUY
    price = tick.ask
    sl_dist = 4.0 # $4.00 stop loss distance (~40 pips)
    tp_dist = 3.5 # $3.50 take profit distance (~35 pips)
    sl = round(price - sl_dist, 2)
    tp = round(price + tp_dist, 2)
    magic = 778899
    comment = "SG-Test-Trade"

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": action,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"\nSending Market Buy Order: {lot} lots of {symbol} @ {price:.2f} | SL={sl:.2f} | TP={tp:.2f} | Magic={magic}...")
    result = mt5.order_send(request)

    if result is None:
        print(f"Order failed, no result returned: {mt5.last_error()}")
        mt5.shutdown()
        sys.exit(1)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        # If IOC failed, try FOK or RETURN
        print(f"IOC filling rejected (retcode={result.retcode}: {result.comment}). Trying ORDER_FILLING_FOK...")
        request["type_filling"] = mt5.ORDER_FILLING_FOK
        result = mt5.order_send(request)
        
        if result and result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"FOK filling rejected. Trying ORDER_FILLING_RETURN...")
            request["type_filling"] = mt5.ORDER_FILLING_RETURN
            result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print("\n================ TEST TRADE EXECUTED SUCCESSFULLY ================")
        print(f"Order Ticket   : {result.order}")
        print(f"Deal ID        : {result.deal}")
        print(f"Volume Executed: {result.volume} lots")
        print(f"Execution Price: ${result.price:.2f}")
        print(f"Stop Loss (SL) : ${sl:.2f} (-${sl_dist:.2f})")
        print(f"Take Profit(TP): ${tp:.2f} (+${tp_dist:.2f})")
        print(f"Broker Comment : {result.comment}")
        print("===================================================================")
    else:
        print(f"\nOrder placement FAILED: retcode={result.retcode if result else 'None'}, comment={result.comment if result else 'None'}")
        print(f"Last error: {mt5.last_error()}")

    # Display active open positions
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        print(f"\nCurrently open positions on {symbol}: ({len(positions)} total)")
        for pos in positions:
            p_type = "BUY" if pos.type == 0 else "SELL"
            sanitized_comment = pos.comment.encode('ascii', 'replace').decode('ascii')
            print(f"  Ticket #{pos.ticket} | {p_type} {pos.volume} lots @ {pos.price_open:.2f} | Current: {pos.price_current:.2f} | P/L: ${pos.profit:+.2f} | SL: {pos.sl:.2f} | TP: {pos.tp:.2f} | Magic: {pos.magic} | {sanitized_comment}")
    else:
        print(f"No active positions on {symbol}.")

    mt5.shutdown()

if __name__ == "__main__":
    main()
