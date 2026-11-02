import MetaTrader5 as mt5
import json
import os

if mt5.initialize():
    acc = mt5.account_info()
    tick = mt5.symbol_info_tick('XAUUSD')
    positions = mt5.positions_get(symbol='XAUUSD')
    
    challenge_state = {}
    if os.path.exists('challenge_100_state.json'):
        with open('challenge_100_state.json', 'r', encoding='utf-8') as f:
            challenge_state = json.load(f)
            
    print("=== LIVE 5-MIN BASELINE TELEMETRY ===")
    print(f"Broker Account   : {acc.login} ({acc.server})")
    print(f"Broker Balance   : ${acc.balance:,.2f}")
    print(f"Broker Equity    : ${acc.equity:,.2f}")
    print(f"XAUUSD Price     : Bid={tick.bid:.2f} | Ask={tick.ask:.2f}")
    print(f"Open Positions   : {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            side = 'BUY' if p.type == 0 else 'SELL'
            cmt = p.comment.encode('ascii', errors='ignore').decode()
            print(f"  #{p.ticket} | {side} {p.volume} @ {p.price_open:.2f} | Magic: {p.magic} | PnL: ${p.profit:+.2f} | {cmt}")
            
    print("\n=== $100 CHALLENGE LEDGER ===")
    c_bal = challenge_state.get("current_balance", 100.0)
    c_lvl = challenge_state.get("level", 1)
    c_lot = challenge_state.get("base_lot", 0.01)
    c_tgt = challenge_state.get("target_balance", 200.0)
    c_won = challenge_state.get("cycles_won", 0)
    c_lst = challenge_state.get("cycles_lost", 0)
    
    print(f"Challenge Balance: ${c_bal:.2f}")
    print(f"Active Level     : Level {c_lvl} (Base: {c_lot} lots)")
    print(f"Next Target Goal : ${c_tgt:.2f} (Doubling to Level {c_lvl+1})")
    print(f"Cycles Won/Lost  : {c_won}W / {c_lst}L")
    mt5.shutdown()
