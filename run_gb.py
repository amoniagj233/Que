from gold_backtester import GoldBacktester
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

gb = GoldBacktester()
res = gb.run_all_strategies(count=5000)
print("=== GOLD_BACKTESTER LEADERBOARD ===")
for s in res['leaderboard']:
    print(f"{s['name']:38} | Win Rate: {s['win_rate']:5.1f}% | Net Profit: ${s['net_profit']:10.2f} | PF: {s['profit_factor']:4.2f} | Trades: {s['total_trades']:4}")
