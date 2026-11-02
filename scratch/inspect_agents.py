import urllib.request, json

def inspect_agents():
    try:
        req = urllib.request.urlopen('http://localhost:8765/api/commander/overview')
        data = json.loads(req.read().decode())
    except Exception as e:
        print("Failed to reach commander:", e)
        return

    print("COMMANDER LEVEL:", data.get("level_name"))
    print("TOTAL AGENTS:", data.get("counts", {}).get("total"))
    print("COUNTS:", data.get("counts"))
    print("-" * 70)
    
    by_team = {}
    for a in data.get("agents", []):
        team = a.get("team", "Other")
        by_team.setdefault(team, []).append(a)

    for team, agent_list in by_team.items():
        print(f"\n### TEAM: {team.upper()} ({len(agent_list)} agents)")
        for a in agent_list:
            aid = a.get("id")
            name = a.get("name")
            status = a.get("status")
            purpose = a.get("purpose")
            pids = a.get("pids", [])
            task = a.get("current_task") or "None"
            failures = a.get("failures", 0)
            score = a.get("performance", {}).get("score", "--")
            print(f"  • {name} [{aid}]")
            print(f"    Status: {status} | Score: {score} | Failures: {failures} | PIDs: {pids}")
            print(f"    Purpose: {purpose}")
            if task != "None":
                print(f"    Active Task: {task}")

if __name__ == "__main__":
    inspect_agents()
