import urllib.request, json

def inspect_activity():
    # Check commander audit logs if there is an endpoint or direct DB query
    import sqlite3, os
    db_path = os.path.join("commander", "data", "commander.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        print("=== RECENT AUDIT LOGS (last 15) ===")
        for r in cur.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 15"):
            print(f"[{r['ts']}] {r['actor']} -> {r['action']} : {r['detail']}")
            
        print("\n=== RECENT MESSAGES ON BUS (last 10) ===")
        for r in cur.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 10"):
            print(f"[{r['ts']}] From: {r['sender']} -> To: {r['recipient']} ({r['type']}): {r['body']}")

        print("\n=== RECENT TASKS ===")
        for r in cur.execute("SELECT * FROM tasks ORDER BY updated DESC LIMIT 10"):
            print(f"Task #{r['id']} [{r['state']}] Owner: {r['owner']} | Title: {r['title']}")
        conn.close()
    else:
        print("commander.db not found at:", db_path)

if __name__ == "__main__":
    inspect_activity()
