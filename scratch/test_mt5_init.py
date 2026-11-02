import MetaTrader5 as mt5

print("Attempting mt5.initialize()...")
MT5_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
res = mt5.initialize(path=MT5_PATH, timeout=10000)
print("mt5.initialize result:", res)
if not res:
    print("Last error:", mt5.last_error())
else:
    print("Terminal info:", mt5.terminal_info())
    mt5.shutdown()
