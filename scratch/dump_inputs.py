import re

path = r"C:\Users\amoni\AppData\Roaming\MetaQuotes\Terminal\0A509A325471F5C180C55A7585ABD80D\MQL5\Experts\XTO Speeder EA.ex5"
with open(path, "rb") as f:
    data = f.read()

# Look for UTF-16 strings that look like input parameters
# In MQL5, input parameters often appear as strings, e.g. "Inp...", "InpLot...", "InpGrid...", or user-facing labels
decoded_u16 = data.decode("utf-16le", errors="ignore")
words = re.findall(r"[A-Za-z0-9_]{3,30}", decoded_u16)

candidates = set()
for w in words:
    lower = w.lower()
    if any(k in lower for k in ["inp", "lot", "grid", "step", "trail", "profit", "magic", "risk", "stop", "time", "filter", "max", "tp", "sl", "news", "spread", "slippage", "target", "mult"]):
        candidates.add(w)

print("Candidate Input / Config Names found in EX5:")
for c in sorted(candidates):
    print(" ", c)
