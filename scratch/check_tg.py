import os
from datetime import datetime

td = r"C:\Users\amoni\Downloads\Telegram Desktop"
files = []
for f in os.listdir(td):
    p = os.path.join(td, f)
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(p))
        files.append((mtime, f, os.path.getsize(p)))
    except:
        pass
files.sort(key=lambda x: x[0], reverse=True)
for t, f, sz in files[:35]:
    clean_name = f.encode('ascii', errors='replace').decode('ascii')
    print(f"{t.strftime('%Y-%m-%d %H:%M')} | {sz:>10} bytes | {clean_name}")
