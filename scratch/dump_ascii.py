import re

path = r"C:\Users\amoni\AppData\Roaming\MetaQuotes\Terminal\0A509A325471F5C180C55A7585ABD80D\MQL5\Experts\XTO Speeder EA.ex5"
with open(path, "rb") as f:
    data = f.read()

ascii_strings = re.findall(b"[A-Za-z0-9_]{3,40}", data)
candidates = set()
for s in ascii_strings:
    try:
        w = s.decode("ascii")
        lower = w.lower()
        if any(k in lower for k in ["inp", "lot", "grid", "step", "trail", "profit", "magic", "risk", "stop", "time", "filter", "max", "tp", "sl", "news", "spread", "slippage", "target", "mult"]):
            candidates.add(w)
    except Exception:
        pass

print(f"Candidate ASCII strings ({len(candidates)}):")
for c in sorted(candidates)[:60]:
    print(" ", c)
