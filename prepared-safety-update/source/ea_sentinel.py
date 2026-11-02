"""
XTO Speeder EA Guardian & News Shield
=====================================
Specialized risk-management supervisor for XTO Speeder EA (Magic 1111):
- Tracks live DCA grid layers, lot progression, and net basket PnL.
- Enforces an emergency Max Basket Loss ($) stop to prevent runaway martingale blowouts.
- Monitors macro economic news blackout windows (CPI, NFP, FOMC) via Gold Intelligence.
- Provides immediate emergency basket liquidation if user or risk limits are breached.
"""

from __future__ import annotations

from execution_gateway import guarded_order_send
import os
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from gold_intelligence import get_gold_macro_events

MAGIC_NUMBER = 1111
SYMBOL = "XAUUSD"

class EASentinel:
    def __init__(self, max_basket_loss: float = 35.0, news_filter_mins: int = 30):
        self.max_basket_loss = abs(max_basket_loss)
        self.news_filter_mins = news_filter_mins
        self.is_connected = False
        self._ensure_mt5()

    def _ensure_mt5(self) -> bool:
        if mt5 is None:
            print("[!] Error: MetaTrader5 python library not installed.")
            return False
        if not mt5.initialize():
            # Try explicit Headway terminal path
            path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
            if not mt5.initialize(path=path):
                print(f"[!] Error: Could not connect to MT5 terminal: {mt5.last_error()}")
                self.is_connected = False
                return False
        self.is_connected = True
        return True

    def get_ea_positions(self) -> List[Any]:
        if not self._ensure_mt5():
            return []
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            return []
        # Filter by EA magic number (or comment tag if magic is unset)
        ea_pos = [p for p in positions if p.magic == MAGIC_NUMBER or "Zalo" in getattr(p, "comment", "")]
        return ea_pos

    def check_macro_news(self) -> Dict[str, Any]:
        """Checks if a high-impact news event is near."""
        events = get_gold_macro_events()
        now = datetime.now(timezone.utc)
        for ev in events:
            if ev.get("impact") in ["CRITICAL", "HIGH"]:
                ev_time_str = ev.get("time_utc", "")
                try:
                    ev_dt = datetime.strptime(ev_time_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
                    diff_mins = (ev_dt - now).total_seconds() / 60.0
                    if -15 <= diff_mins <= self.news_filter_mins:
                        return {
                            "active_blackout": True,
                            "event": ev.get("event"),
                            "diff_mins": round(diff_mins, 1),
                            "impact": ev.get("impact"),
                            "rule": ev.get("rule")
                        }
                except Exception:
                    pass
        return {"active_blackout": False, "event": None}

    def close_all_ea_positions(self, reason: str = "EMERGENCY_STOP") -> Dict[str, Any]:
        """Atomically liquidates all positions managed by XTO Speeder EA."""
        if not self._ensure_mt5():
            return {"success": False, "message": "MT5 not connected"}

        positions = self.get_ea_positions()
        if not positions:
            return {"success": True, "closed": 0, "message": "No active EA positions to close"}

        closed_count = 0
        total_pnl = 0.0
        errors = []

        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            return {"success": False, "message": "Could not fetch live tick quote"}

        print(f"\n[!] INITIATING BASKET LIQUIDATION ({len(positions)} orders) - Reason: {reason}")

        for p in positions:
            order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": p.volume,
                "type": order_type,
                "position": p.ticket,
                "price": price,
                "deviation": 50,
                "magic": 999111,
                "comment": f"Sentinel Close: {reason[:15]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }

            res = guarded_order_send(mt5, req)
            if res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                closed_count += 1
                total_pnl += p.profit
                print(f"  [OK] Closed #{p.ticket} ({'BUY' if p.type==0 else 'SELL'} {p.volume} lots) @ {price:.2f} | PnL: ${p.profit:.2f}")
            else:
                err_msg = getattr(res, "comment", "Unknown order failure") if res else "No response"
                errors.append(f"#{p.ticket}: {err_msg}")
                print(f"  [X] Failed closing #{p.ticket}: {err_msg}")

        return {
            "success": closed_count > 0,
            "closed": closed_count,
            "total_pnl": total_pnl,
            "errors": errors
        }

    def inspect_status(self) -> Dict[str, Any]:
        """Compiles complete health telemetry for the EA basket."""
        if not self._ensure_mt5():
            return {"error": "MT5 not connected"}

        acc = mt5.account_info()
        tick = mt5.symbol_info_tick(SYMBOL)
        positions = self.get_ea_positions()
        news = self.check_macro_news()

        buys = [p for p in positions if p.type == mt5.ORDER_TYPE_BUY]
        sells = [p for p in positions if p.type == mt5.ORDER_TYPE_SELL]

        buy_vol = sum(p.volume for p in buys)
        sell_vol = sum(p.volume for p in sells)
        tot_vol = buy_vol + sell_vol
        tot_pnl = sum(p.profit for p in positions)

        # Calculate weighted breakeven for dominant side
        buy_be = sum(p.price_open * p.volume for p in buys) / buy_vol if buy_vol > 0 else 0.0
        sell_be = sum(p.price_open * p.volume for p in sells) / sell_vol if sell_vol > 0 else 0.0

        buffer_remaining = self.max_basket_loss + tot_pnl if tot_pnl < 0 else self.max_basket_loss

        return {
            "login": acc.login if acc else "N/A",
            "server": acc.server if acc else "N/A",
            "balance": acc.balance if acc else 0.0,
            "equity": acc.equity if acc else 0.0,
            "margin_level": acc.margin_level if acc else 0.0,
            "bid": tick.bid if tick else 0.0,
            "ask": tick.ask if tick else 0.0,
            "orders_count": len(positions),
            "buy_orders": len(buys),
            "sell_orders": len(sells),
            "buy_volume": round(buy_vol, 2),
            "sell_volume": round(sell_vol, 2),
            "total_volume": round(tot_vol, 2),
            "total_pnl": round(tot_pnl, 2),
            "buy_breakeven": round(buy_be, 2),
            "sell_breakeven": round(sell_be, 2),
            "max_loss_limit": self.max_basket_loss,
            "buffer_remaining": round(buffer_remaining, 2),
            "news_status": news,
            "positions": positions
        }

    def print_hud(self, stat: Dict[str, Any]):
        os.system("cls" if os.name == "nt" else "clear")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print("=" * 75)
        print(" " * 18 + "XTO SPEEDER EA GUARDIAN & RISK SHIELD")
        print("=" * 75)
        print(f"Time: {now_str} | MT5: {stat.get('server')} (Acct #{stat.get('login')})")
        print(f"Account Balance: ${stat.get('balance'):.2f} | Live Equity: ${stat.get('equity'):.2f} | Margin: {stat.get('margin_level'):.1f}%")
        print(f"XAUUSD Market: Bid {stat.get('bid'):.2f} / Ask {stat.get('ask'):.2f}")
        print("-" * 75)

        cnt = stat.get("orders_count", 0)
        pnl = stat.get("total_pnl", 0.0)
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

        print(f"BASKET STATUS: {cnt} Active Orders | Total Exposure: {stat.get('total_volume')} Lots")
        print(f"  • BUY Grid:  {stat.get('buy_orders')} orders ({stat.get('buy_volume')} lots) | Breakeven: {stat.get('buy_breakeven')}")
        print(f"  • SELL Grid: {stat.get('sell_orders')} orders ({stat.get('sell_volume')} lots) | Breakeven: {stat.get('sell_breakeven')}")
        print(f"  • Floating P/L: {pnl_str}")
        print("-" * 75)

        # Risk Threshold Indicator
        buf = stat.get("buffer_remaining", 0.0)
        max_l = stat.get("max_loss_limit", 35.0)
        if pnl < 0:
            bar_len = 25
            used_pct = min(1.0, abs(pnl) / max_l)
            fill_len = int(bar_len * used_pct)
            bar = "#" * fill_len + "-" * (bar_len - fill_len)
            print(f"DRAWDOWN METER: [{bar}] {used_pct*100:.1f}% of Max Allowed (-${max_l:.2f})")
            print(f"Safety Buffer Remaining: ${buf:.2f}")
        else:
            print(f"DRAWDOWN METER: [-------------------------] 0.0% (Basket in Profit)")

        # News status
        news = stat.get("news_status", {})
        if news.get("active_blackout"):
            print(f"[!] MACRO WARNING: {news.get('event')} in {news.get('diff_mins')}m! [HIGH VOLATILITY]")
        else:
            print("[+] MACRO STATUS: No high-impact blackout events in immediate window [NORMAL]")

        print("=" * 75)
        print("Positions:")
        for p in stat.get("positions", []):
            d = "BUY" if p.type == 0 else "SELL"
            com = p.comment.encode("ascii", "replace").decode("ascii")
            print(f"  #{p.ticket}: {d} {p.volume:.2f} @ {p.price_open:.2f} | P/L: ${p.profit:+.2f} | Magic: {p.magic} | {com}")
        print("=" * 75)
        print("Press Ctrl+C to stop Guardian. (Runs continuously in background)")

    def run_guard_loop(self, interval: float = 2.0):
        print(f"[*] Starting XTO Speeder Guardian loop (Max Loss Cap: ${self.max_basket_loss:.2f})...")
        try:
            while True:
                stat = self.inspect_status()
                if "error" in stat:
                    print(f"[!] Telemetry error: {stat['error']}")
                    time.sleep(interval)
                    continue

                self.print_hud(stat)

                # Check Max Basket Loss Rule
                pnl = stat.get("total_pnl", 0.0)
                if pnl <= -self.max_basket_loss:
                    print(f"\n[ALERT] FLOATING DRAWDOWN (-${abs(pnl):.2f}) BREACHED MAX CAP (-${self.max_basket_loss:.2f})!")
                    res = self.close_all_ea_positions(reason=f"Max Basket Loss (-${abs(pnl):.2f}) Exceeded")
                    print(f"[RESULT] {res.get('message', 'Liquidated basket')} | Realized PnL: ${res.get('total_pnl', 0.0):.2f}")
                    time.sleep(5)

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Guardian monitor stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="XTO Speeder EA Guardian & News Shield")
    parser.add_argument("--max-loss", type=float, default=35.0, help="Max dollar drawdown before emergency basket close (default: $35.00)")
    parser.add_argument("--close-now", action="store_true", help="Instantly close all open XTO Speeder EA positions")
    parser.add_argument("--status", action="store_true", help="Print single snapshot status and exit")
    args = parser.parse_args()

    sentinel = EASentinel(max_basket_loss=args.max_loss)

    if args.close_now:
        res = sentinel.close_all_ea_positions(reason="Manual Emergency Close")
        print(res)
    elif args.status:
        stat = sentinel.inspect_status()
        sentinel.print_hud(stat)
    else:
        sentinel.run_guard_loop()

if __name__ == "__main__":
    main()
