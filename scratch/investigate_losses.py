import sys, os
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

if mt5.initialize():
    acc = mt5.account_info()
    print("=== ACCOUNT INFO ===")
    print(f"Login: {acc.login}, Balance: {acc.balance}, Equity: {acc.equity}, Profit: {acc.profit}")

    print("\n=== OPEN POSITIONS ===")
    open_pos = mt5.positions_get()
    if open_pos:
        for p in open_pos:
            p_type = 'BUY' if p.type == mt5.ORDER_TYPE_BUY else 'SELL'
            print(f"Ticket #{p.ticket}: {p.symbol} {p_type} {p.volume} lots | Open: {p.price_open} -> Curr: {p.price_current} | SL: {p.sl}, TP: {p.tp} | Profit: ${p.profit:.2f} | Magic: {p.magic} | Comment: {p.comment}")
    else:
        print("No open positions.")

    print("\n=== CLOSED DEALS (LAST 48 HOURS) ===")
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=2)
    deals = mt5.history_deals_get(from_date, now)
    if deals:
        print(f"Total deals found: {len(deals)}")
        trades_by_position = {}
        for d in deals:
            # deal type: 0=BUY, 1=SELL, 2=BALANCE
            if d.entry == 1:  # DEAL_ENTRY_OUT (exit deal)
                pos_id = d.position_id
                trades_by_position[pos_id] = {
                    "ticket": d.ticket,
                    "symbol": d.symbol,
                    "volume": d.volume,
                    "profit": d.profit,
                    "commission": d.commission,
                    "swap": d.swap,
                    "net_pnl": round(d.profit + d.commission + d.swap, 2),
                    "price": d.price,
                    "time": datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "comment": d.comment
                }

        # Print all exit deals
        total_pnl = 0.0
        losses = 0
        wins = 0
        for pos_id, t in trades_by_position.items():
            net = t["net_pnl"]
            total_pnl += net
            if net > 0:
                wins += 1
            elif net < 0:
                losses += 1
            print(f"Exit #{pos_id} | {t['symbol']} | Net: ${net:.2f} (Profit: ${t['profit']:.2f}, Comm: ${t['commission']:.2f}, Swap: ${t['swap']:.2f}) | Time: {t['time']} | Comment: '{t['comment']}'")
        
        print(f"\nSummary of Exits: Wins={wins}, Losses={losses}, Total Net P&L=${total_pnl:.2f}")
    else:
        print("No deals found in last 48 hours.")

    mt5.shutdown()
else:
    print("MT5 initialization failed.")
