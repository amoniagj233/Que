with open("commander/api.py", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(25):
    print(f"{i+1}: {repr(lines[i])}")
