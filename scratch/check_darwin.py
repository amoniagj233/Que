import json

with open("latest_discovery.json", "r") as f:
    d = json.load(f)

print("=== LATEST DISCOVERY ===")
print("Timestamp:", d.get("timestamp"))
print("Is New:", d.get("is_new"))
champ = d.get("champion", {})
print("Champion Name:", champ.get("name"))
print("Net Profit: $", champ.get("net_profit"))
print("Win Rate:", champ.get("win_rate"), "%")
print("Profit Factor:", champ.get("profit_factor"))
print("Max DD:", champ.get("max_drawdown_pct"), "%")
print("ROI:", champ.get("roi_pct"), "%")

with open("strategy_leaderboard.json", "r") as f:
    lb = json.load(f)

print("\n=== TOP 5 LEADERBOARD ===")
print("Generation:", lb.get("generation"), "| Total Evaluated:", lb.get("total_evaluated"))
for i, s in enumerate(lb.get("top_strategies", [])[:5], 1):
    print(f"#{i} {s.get('name')}: Net ${s.get('net_profit', 0):.2f} | WR {s.get('win_rate', 0)}% | PF {s.get('profit_factor', 0)} | Trades: {s.get('total_trades', 0)}")
