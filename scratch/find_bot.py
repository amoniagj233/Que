import os
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=7)
print("Checking C:\\Users\\amoni\\Downloads...")
dl = r"C:\Users\amoni\Downloads"
if os.path.exists(dl):
    for f in os.listdir(dl):
        p = os.path.join(dl, f)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(p))
            if mtime > cutoff or 'tik' in f.lower() or 'talk' in f.lower() or 'bot' in f.lower() or 'ea' in f.lower():
                print(f"DL: {mtime.strftime('%Y-%m-%d %H:%M:%S')} | {f}")
        except Exception as e:
            pass

print("\nChecking CCXT Terminal files...")
ccxt = r"C:\Users\amoni\OneDrive\Desktop\CCXT Terminal"
if os.path.exists(ccxt):
    for f in os.listdir(ccxt):
        print("CCXT:", f)

print("\nSearching entire C:\\Users\\amoni for filenames with 'tik' or 'tiktalk' or 'tiktok'...")
for dp, dn, fn in os.walk(r"C:\Users\amoni"):
    if any(s in dp for s in ['AppData\\Local\\Microsoft', 'AppData\\Local\\Google', 'AppData\\Local\\Package']):
        continue
    for f in fn:
        fl = f.lower()
        if 'tiktalk' in fl or 'tiktok' in fl:
            print("FOUND TIKTOK FILE:", os.path.join(dp, f))
