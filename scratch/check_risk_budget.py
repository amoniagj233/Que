import sys, os
sys.path.insert(0, os.path.abspath('.'))
import MetaTrader5 as mt5
from trade_safety import limit_volume, MAX_GROUP_RISK_PERCENT

if mt5.initialize():
    acc = mt5.account_info()
    balance = min(acc.balance, acc.equity)
    risk_dollar = balance * MAX_GROUP_RISK_PERCENT / 100
    print(f"Balance: {balance}, Risk budget: {risk_dollar}")

    for sym in ["VOL_20", "BOOM_100", "CRASH_100", "ETH"]:
        info = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        if not info or not tick:
            print(f"{sym}: No info or tick")
            continue
        print(f"\n{sym}: min_vol={info.volume_min}, vol_step={info.volume_step}, trade_contract_size={info.trade_contract_size}, point={info.point}, digits={info.digits}")
        entry = tick.ask
        sl = entry - (info.point * 1000)
        try:
            lot = limit_volume(mt5, info, mt5.ORDER_TYPE_BUY, sym, info.volume_min, entry, sl, risk_dollar, legs=1)
            print(f"{sym}: limit_volume success -> {lot}")
        except Exception as e:
            print(f"{sym}: limit_volume failed -> {e}")
    mt5.shutdown()
