import psutil

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in p.info['name'].lower() and any(k in cmd for k in ['daemon', 'settings', 'apex', 'trader', 'pattern', 'crt', 'horizon']):
            print(f"{p.info['pid']}: {cmd}")
    except: pass
