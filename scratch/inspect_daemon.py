with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(268, 290):
    print(f"{i+1}: {lines[i]}", end="")
