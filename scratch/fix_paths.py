import os
import sys

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Update xto_speeder_trader.py
xto_path = os.path.join(base, "xto_speeder_trader.py")
if os.path.exists(xto_path):
    with open(xto_path, "rb") as f:
        content = f.read().decode("utf-8")
    old_line = 'LOG_FILE        = r"c:\\Users\\amoni\\OneDrive\\Desktop\\Headway trader\\xto_speeder_trades.log"'
    new_line = 'LOG_FILE        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xto_speeder_trades.log")'
    if old_line in content:
        content = content.replace(old_line, new_line)
        with open(xto_path, "wb") as f:
            f.write(content.encode("utf-8"))
        print("[OK] Updated xto_speeder_trader.py")
    else:
        print("[SKIP] old_line not in xto_speeder_trader.py")

# 2. Update batch files
batch_files = [
    "run_xto_speeder.bat",
    "START_100_CHALLENGE.bat",
    "START_APEX_QUANTUM.bat",
    "START_DUAL_XTO.bat",
    "START_EVOLUTION_AGENT.bat",
    "START_XTO_247.bat"
]

for bf in batch_files:
    fp = os.path.join(base, bf)
    if os.path.exists(fp):
        with open(fp, "rb") as f:
            c = f.read().decode("utf-8", errors="replace")
        old_cd = 'cd /d "c:\\Users\\amoni\\OneDrive\\Desktop\\Headway trader"'
        new_cd = 'cd /d "%~dp0"'
        if old_cd in c:
            c = c.replace(old_cd, new_cd)
            with open(fp, "wb") as f:
                f.write(c.encode("utf-8"))
            print(f"[OK] Updated {bf}")
        else:
            print(f"[SKIP] old cd not in {bf}")

# 3. Update agent_settings.db to use relative paths
db_path = os.path.join(base, "agent_settings", "data", "agent_settings.db")
if os.path.exists(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT ea_id, script_path FROM fleet_eas")
    rows = cur.fetchall()
    updated = 0
    for ea_id, sp in rows:
        if sp and ("amoni" in sp or "\\" in sp):
            fname = os.path.basename(sp)
            cur.execute("UPDATE fleet_eas SET script_path = ? WHERE ea_id = ?", (fname, ea_id))
            updated += 1
    conn.commit()
    conn.close()
    print(f"[OK] Normalized {updated} paths in agent_settings.db to portable filenames")

print("[DONE] All fixes applied successfully.")
