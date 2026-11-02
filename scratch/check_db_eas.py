import sqlite3

conn = sqlite3.connect("agent_settings/data/agent_settings.db")
cursor = conn.cursor()
cursor.execute("SELECT ea_id, name, magic FROM fleet_eas")
for r in cursor.fetchall():
    print(r)
conn.close()
