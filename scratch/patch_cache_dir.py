import os

p = os.path.join(os.getcwd(), 'continuous_tp_reopen_daemon.py')
with open(p, 'rb') as f:
    c = f.read().decode('utf-8')

old = 'with open(os.path.join(BASE_DIR, "data_cache", "fleet_live_status.json"), "w", encoding="utf-8") as sf:'
new = 'os.makedirs(os.path.join(BASE_DIR, "data_cache"), exist_ok=True)\n                with open(os.path.join(BASE_DIR, "data_cache", "fleet_live_status.json"), "w", encoding="utf-8") as sf:'

if old in c:
    c = c.replace(old, new)
    with open(p, 'wb') as f:
        f.write(c.encode('utf-8'))
    print('[OK] Updated continuous_tp_reopen_daemon.py data_cache safety')
else:
    print('[SKIP] pattern not found')
