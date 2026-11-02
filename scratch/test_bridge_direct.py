import sys
sys.path.insert(0, ".")
from commander.mt5_bridge import bridge

print("Calling bridge.initialize()...")
res = bridge.initialize()
print("Bridge init result:", res)
if not res:
    print("Bridge last error:", bridge.last_error)
else:
    print("Bridge connected successfully to:", bridge.terminal_name)
    pos = bridge.get_open_positions()
    print("Open positions count:", len(pos))
