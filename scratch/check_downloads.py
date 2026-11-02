import os
from datetime import datetime, timedelta

dl = r"C:\Users\amoni\Downloads"
print(f"Listing Downloads directory: {dl}")
if os.path.exists(dl):
    files = []
    for f in os.listdir(dl):
        p = os.path.join(dl, f)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(p))
            files.append((mtime, f, os.path.getsize(p) if os.path.isfile(p) else 0, os.path.isdir(p)))
        except:
            pass
    files.sort(key=lambda x: x[0], reverse=True)
    print(f"Total items in Downloads: {len(files)}")
    for mtime, name, sz, is_d in files[:30]:
        kind = "DIR" if is_d else "FILE"
        print(f"{mtime.strftime('%Y-%m-%d %H:%M:%S')} | {kind:4} | {sz:>10} bytes | {name}")
else:
    print("Downloads does not exist")
