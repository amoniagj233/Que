with open("commander/mt5_bridge.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(35, 80):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end="")
