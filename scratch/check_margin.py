import sys; sys.path.insert(0, '.')
import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 init failed")
    sys.exit(1)

acc = mt5.account_info()
print(f"Balance: ${acc.balance:.2f}")
print(f"Equity: ${acc.equity:.2f}")
print(f"Margin: ${acc.margin:.2f}")
print(f"Free Margin: ${acc.margin_free:.2f}")
print(f"Margin Level: {acc.margin_level:.1f}%")
print(f"Leverage: 1:{acc.leverage}")

mt5.shutdown()
