"""
Trade Referee: Dual Bot Performance Tracker
Tracks the 20-Trade Duel between:
  - Bot 1: Magic 1111 (XTO Speeder Rebuilt - Fixed 60pts DCA)
  - Bot 2: Magic 2222 (XTO Speeder Upgrade 1 - Dynamic ATR Pro)
Duel Starting Deal ID: 850841460 (19:29:45 UTC)
"""
import MetaTrader5 as mt5
import time
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

START_DEAL_ID = 850841460
TARGET_TRADES = 20
LOG_FILE      = "duel_live_scorecard.txt"

def get_stats():
    if not mt5.initialize():
        return None
        
    # Query last 24 hours to capture all duel deals since START_DEAL_ID
    from_t = datetime.now() - timedelta(hours=24)
    to_t   = datetime.now() + timedelta(days=2)
    deals  = mt5.history_deals_get(from_t, to_t)
    mt5.shutdown()
    
    if deals is None:
        return None
        
    # Filter exit deals (entry == 1) strictly belonging to the duel (ticket >= START_DEAL_ID)
    b1_exits = [d for d in deals if d.magic == 1111 and d.entry == 1 and d.ticket >= START_DEAL_ID]
    b2_exits = [d for d in deals if d.magic == 2222 and d.entry == 1 and d.ticket >= START_DEAL_ID]
    
    b1_profit = sum(d.profit for d in b1_exits)
    b2_profit = sum(d.profit for d in b2_exits)
    
    b1_wins = len([d for d in b1_exits if d.profit > 0])
    b2_wins = len([d for d in b2_exits if d.profit > 0])
    
    total_completed = len(b1_exits) + len(b2_exits)
    
    return {
        'total_completed': total_completed,
        'target_trades': TARGET_TRADES,
        'is_finished': total_completed >= TARGET_TRADES,
        'bot1': {
            'magic': 1111,
            'name': 'XTO Speeder Rebuilt (Fixed 60pts)',
            'closed_deals': len(b1_exits),
            'profit': b1_profit,
            'wins': b1_wins,
            'losses': len(b1_exits) - b1_wins,
            'win_rate': (b1_wins / len(b1_exits) * 100) if len(b1_exits) > 0 else 0.0
        },
        'bot2': {
            'magic': 2222,
            'name': 'XTO Upgrade 1 (Dynamic ATR Pro)',
            'closed_deals': len(b2_exits),
            'profit': b2_profit,
            'wins': b2_wins,
            'losses': len(b2_exits) - b2_wins,
            'win_rate': (b2_wins / len(b2_exits) * 100) if len(b2_exits) > 0 else 0.0
        }
    }

def print_scoreboard(stats):
    b1 = stats['bot1']
    b2 = stats['bot2']
    total = stats['total_completed']
    target = stats['target_trades']
    
    out = []
    out.append("=" * 72)
    out.append(f"  🏆 BOT DUEL LIVE SCORECARD: TARGET {target} TRADES")
    out.append(f"  Progress: {total} / {target} Closed Trades ({total/target*100:.1f}%)")
    out.append("=" * 72)
    out.append(f"{'METRIC':<25} | {'BOT 1 (Fixed 60pts)':<20} | {'BOT 2 (Dynamic ATR)':<20}")
    out.append("-" * 72)
    out.append(f"{'Magic Number':<25} | {b1['magic']:<20} | {b2['magic']:<20}")
    out.append(f"{'Closed Deals':<25} | {b1['closed_deals']:<20} | {b2['closed_deals']:<20}")
    out.append(f"{'Realized P/L ($)':<25} | ${b1['profit']:>+8.2f}            | ${b2['profit']:>+8.2f}")
    out.append(f"{'Win Rate (%)':<25} | {b1['win_rate']:>7.1f}%            | {b2['win_rate']:>7.1f}%")
    out.append(f"{'Wins / Losses':<25} | {b1['wins']}W / {b1['losses']}L               | {b2['wins']}W / {b2['losses']}L")
    out.append("=" * 72)
    
    if total >= target:
        winner = "BOT 1 (Fixed 60pts)" if b1['profit'] > b2['profit'] else "BOT 2 (Dynamic ATR Pro)"
        out.append(f"🏁 DUEL COMPLETED! WINNER: {winner} (Realized: ${max(b1['profit'], b2['profit']):+.2f})")
    else:
        current_leader = "TIE"
        if b1['profit'] > b2['profit']:
            current_leader = f"BOT 1 (+${b1['profit']:.2f})"
        elif b2['profit'] > b1['profit']:
            current_leader = f"BOT 2 (+${b2['profit']:.2f})"
        out.append(f"Status: IN PROGRESS ({total}/{target} trades) | Current Leader: {current_leader}")
    out.append("=" * 72)
    
    text = "\n".join(out)
    print(text)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(text)

if __name__ == "__main__":
    stats = get_stats()
    if stats:
        print_scoreboard(stats)
