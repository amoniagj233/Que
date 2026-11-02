import re

path = r"C:\Users\amoni\AppData\Roaming\MetaQuotes\Terminal\0A509A325471F5C180C55A7585ABD80D\MQL5\Experts\XTO Speeder EA.ex5"
with open(path, "rb") as f:
    data = f.read()

decoded = data.decode("utf-16le", errors="ignore")
lines = [l.strip() for l in decoded.split("\x00") if len(l.strip()) >= 3]

keywords = ["lot", "step", "grid", "martingale", "profit", "trailing", "stop", "magic", "time", "filter", "zalo", "speeder", "xto", "multiplier", "tp", "sl", "distance", "input", "pip", "max", "target", "risk", "take", "breakeven", "candle", "rsi", "ema", "trend"]

matches = []
seen = set()
for l in lines:
    clean = l.encode("ascii", "replace").decode("ascii")
    for kw in keywords:
        if kw in clean.lower():
            if clean not in seen and len(clean) < 100:
                seen.add(clean)
                matches.append(clean)
            break

print(f"Total matched parameter/string lines: {len(matches)}")
for m in matches[:60]:
    print("->", m)
