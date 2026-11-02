import MetaTrader5 as mt5

print("Trying simple mt5.initialize()...")
if mt5.initialize():
    print("SUCCESS: Attached to running MT5!")
    acc = mt5.account_info()
    if acc:
        print(f"Account: {acc.login} | Balance: {acc.balance} | Equity: {acc.equity}")
    mt5.shutdown()
else:
    print("Init without path failed:", mt5.last_error())
