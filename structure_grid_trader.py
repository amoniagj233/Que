"""
StructureGrid Pro (Golden Combo Edition)
========================================
Institutional Market Structure (H1 Trend + M15 Fractal Structure) + M1 Precision Entry.
- Macro H1 Filter: Trend direction via H1 50-EMA & H1 Swing Pivots.
- Intraday M15 Structure: Identifies confirmed Higher Highs (HH)/Higher Lows (HL) vs Lower Lows (LL)/Lower Highs (LH).
- Golden Confluence Gate: Orders only fire when BOTH H1 and M15 are strictly aligned.
- Precision Entry (M1/M5): Enters Layer 1 on pullback confirmation candle.
- Smart Adaptive Averaging: Max 3 layers (0.01, 0.01, 0.02) spaced by >= 1.2x ATR. Never blind.
- Hard Structural Stop Loss: Placed directly on the broker server at the confirmed M15 swing pivot.
- Basket Take Profit: Liquidates all layers at +$3.50 target profit.
- Emergency Max Basket Loss: -$25.00 hard stop.
- Macro News Blackout: 30-min blackout window before high-impact USD events.
"""

from __future__ import annotations
import os
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

import pandas as pd
import numpy as np

from gold_intelligence import get_gold_macro_events, compute_atr

MAGIC_NUMBER = 778899
SYMBOL = "XAUUSD"

class GoldenComboTrader:
    def __init__(
        self,
        base_lot: float = 0.01,
        max_layers: int = 3,
        layer_lots: List[float] = None,
        target_basket_profit: float = 3.50,
        max_basket_loss: float = 25.00,
        news_filter_mins: int = 30
    ):
        self.base_lot = base_lot
        self.max_layers = max_layers
        self.layer_lots = layer_lots or [0.01, 0.01, 0.02]
        self.target_basket_profit = target_basket_profit
        self.max_basket_loss = abs(max_basket_loss)
        self.news_filter_mins = news_filter_mins
        
        self.is_connected = False
        self.cycle_count = 0
        self.realized_pnl = 0.0
        self._init_mt5()

    def _init_mt5(self) -> bool:
        if mt5 is None:
            print("[!] Error: MetaTrader5 library not installed.")
            return False
        if not mt5.initialize():
            path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
            if not mt5.initialize(path=path):
                print(f"[!] Error: Could not connect to MT5: {mt5.last_error()}")
                self.is_connected = False
                return False
        self.is_connected = True
        return True

    def get_h1_trend(self) -> Dict[str, Any]:
        """Analyzes H1 candles for macro institutional trend alignment."""
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
        if rates is None or len(rates) < 60:
            return {"trend": "NEUTRAL", "ema50": 0.0}

        df = pd.DataFrame(rates)
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        curr_price = df['close'].iloc[-1]
        curr_ema = df['ema50'].iloc[-1]
        prev_ema = df['ema50'].iloc[-5]
        
        ema_slope_up = curr_ema > prev_ema
        price_above = curr_price > curr_ema

        if price_above and ema_slope_up:
            return {"trend": "BULLISH", "ema50": round(curr_ema, 2), "price": round(curr_price, 2)}
        elif not price_above and not ema_slope_up:
            return {"trend": "BEARISH", "ema50": round(curr_ema, 2), "price": round(curr_price, 2)}
        else:
            return {"trend": "NEUTRAL", "ema50": round(curr_ema, 2), "price": round(curr_price, 2)}

    def get_m15_structure(self, lookback_bars: int = 5) -> Dict[str, Any]:
        """Analyzes M15 fractal swing pivots to determine intraday HH/HL vs LL/LH."""
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 120)
        if rates is None or len(rates) < 30:
            return {"regime": "INSUFFICIENT_DATA", "allowed_side": "NONE"}

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        half = lookback_bars // 2
        swing_highs = []
        swing_lows = []

        for i in range(half, len(df) - half):
            curr_h = df['high'].iloc[i]
            curr_l = df['low'].iloc[i]
            if all(df['high'].iloc[i-j] < curr_h and df['high'].iloc[i+j] < curr_h for j in range(1, half+1)):
                swing_highs.append({'price': curr_h, 'time': df['time'].iloc[i], 'idx': i})
            if all(df['low'].iloc[i-j] > curr_l and df['low'].iloc[i+j] > curr_l for j in range(1, half+1)):
                swing_lows.append({'price': curr_l, 'time': df['time'].iloc[i], 'idx': i})

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"regime": "SCANNING", "allowed_side": "NONE"}

        sh2, sh1 = swing_highs[-2], swing_highs[-1]
        sl2, sl1 = swing_lows[-2], swing_lows[-1]

        is_hh = sh1['price'] > sh2['price']
        is_hl = sl1['price'] > sl2['price']
        is_ll = sl1['price'] < sl2['price']
        is_lh = sh1['price'] < sh2['price']

        atr_val = compute_atr(df, period=14).iloc[-1] if len(df) > 15 else 3.5

        if is_hh and is_hl:
            return {
                "regime": "BULLISH",
                "allowed_side": "BUY",
                "last_high": sh1['price'],
                "last_low": sl1['price'],
                "invalidation_level": sl1['price'] - 0.50, # 50 cents below Higher Low
                "atr": atr_val
            }
        elif is_ll and is_lh:
            return {
                "regime": "BEARISH",
                "allowed_side": "SELL",
                "last_high": sh1['price'],
                "last_low": sl1['price'],
                "invalidation_level": sh1['price'] + 0.50, # 50 cents above Lower High
                "atr": atr_val
            }
        else:
            return {
                "regime": "CHOP",
                "allowed_side": "NONE",
                "last_high": sh1['price'],
                "last_low": sl1['price'],
                "invalidation_level": None,
                "atr": atr_val
            }

    def get_golden_combo_matrix(self) -> Dict[str, Any]:
        """Combines H1 Macro Trend + M15 Intraday Structure."""
        h1 = self.get_h1_trend()
        m15 = self.get_m15_structure()
        
        h1_trend = h1.get("trend")
        m15_regime = m15.get("regime")
        
        # Confluence Check: Both must agree!
        if h1_trend == "BULLISH" and m15_regime == "BULLISH":
            confluence = "STRONG_BULLISH_CONFLUENCE"
            allowed_side = "BUY"
        elif h1_trend == "BEARISH" and m15_regime == "BEARISH":
            confluence = "STRONG_BEARISH_CONFLUENCE"
            allowed_side = "SELL"
        else:
            confluence = f"DIVERGENT (H1 {h1_trend} vs M15 {m15_regime})"
            allowed_side = "NONE"

        return {
            "confluence": confluence,
            "allowed_side": allowed_side,
            "h1_trend": h1_trend,
            "h1_ema50": h1.get("ema50"),
            "m15_regime": m15_regime,
            "last_high": m15.get("last_high", 0.0),
            "last_low": m15.get("last_low", 0.0),
            "invalidation_level": m15.get("invalidation_level"),
            "atr": m15.get("atr", 3.5)
        }

    def check_macro_news(self) -> Dict[str, Any]:
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
                            "diff_mins": round(diff_mins, 1)
                        }
                except Exception:
                    pass
        return {"active_blackout": False, "event": None}

    def get_open_basket(self) -> List[Any]:
        if not self._init_mt5():
            return []
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            return []
        return [p for p in positions if p.magic == MAGIC_NUMBER]

    def open_layer(self, side: str, layer_idx: int, invalidation_level: float) -> Optional[int]:
        if not self._init_mt5():
            return None

        tick = mt5.symbol_info_tick(SYMBOL)
        info = mt5.symbol_info(SYMBOL)
        if not tick or not info:
            return None

        vol = self.layer_lots[min(layer_idx, len(self.layer_lots) - 1)]
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "BUY" else tick.bid
        sl_price = round(float(invalidation_level), info.digits) if invalidation_level > 0 else 0.0

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": vol,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": 0.0,
            "deviation": 40,
            "magic": MAGIC_NUMBER,
            "comment": f"GC-L{layer_idx+1}-{side}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        res = mt5.order_send(req)
        if res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
            ticket = int(res.order)
            print(f"[+] Filled Golden Layer {layer_idx+1} {side} {vol} lots @ {price:.2f} | Hard SL @ {sl_price:.2f} (Ticket #{ticket})")
            return ticket
        else:
            err = getattr(res, "comment", "Order send failed") if res else "No response"
            print(f"[!] Order rejected: {err}")
            return None

    def close_entire_basket(self, reason: str = "TARGET_PROFIT") -> float:
        basket = self.get_open_basket()
        if not basket:
            return 0.0

        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            return 0.0

        closed_pnl = 0.0
        print(f"\n[*] CLOSING ENTIRE BASKET ({len(basket)} orders) -> Reason: {reason}")
        
        for p in basket:
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
                "magic": MAGIC_NUMBER,
                "comment": f"GC-Exit: {reason[:12]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }

            res = mt5.order_send(req)
            if res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
                closed_pnl += p.profit
                print(f"  [OK] Closed #{p.ticket} ({'BUY' if p.type==0 else 'SELL'} {p.volume} lot) @ {price:.2f} | P/L: ${p.profit:+.2f}")
            else:
                err = getattr(res, "comment", "Failed") if res else "Unknown"
                print(f"  [X] Failed closing #{p.ticket}: {err}")

        self.cycle_count += 1
        self.realized_pnl += closed_pnl
        return closed_pnl

    def print_hud(self, matrix: Dict[str, Any], basket: List[Any], news: Dict[str, Any]):
        os.system("cls" if os.name == "nt" else "clear")
        acc = mt5.account_info() if self._init_mt5() else None
        tick = mt5.symbol_info_tick(SYMBOL) if self._init_mt5() else None
        
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print("=" * 78)
        print(" " * 15 + "STRUCTUREGRID PRO : GOLDEN COMBO (H1 + M15 + M1)")
        print("=" * 78)
        print(f"Time: {now_str} | MT5: {acc.server if acc else 'N/A'} (Acct #{acc.login if acc else 'N/A'})")
        print(f"Balance: ${acc.balance if acc else 0:.2f} | Equity: ${acc.equity if acc else 0:.2f} | Realized: ${self.realized_pnl:+.2f}")
        print(f"XAUUSD Quote -> Bid: {tick.bid if tick else 0:.2f} | Ask: {tick.ask if tick else 0:.2f}")
        print("-" * 78)

        confluence = matrix.get("confluence", "UNKNOWN")
        allowed = matrix.get("allowed_side", "NONE")
        inv_lvl = matrix.get("invalidation_level")
        atr = matrix.get("atr", 3.5)

        print(f"MULTI-TIMEFRAME CONFLUENCE: [{confluence}]")
        print(f"  • H1 Macro Trend:    {matrix.get('h1_trend')} (EMA50 at {matrix.get('h1_ema50'):.2f})")
        print(f"  • M15 Intraday Flow: {matrix.get('m15_regime')} (High: {matrix.get('last_high'):.2f} | Low: {matrix.get('last_low'):.2f})")
        print(f"  • Execution Direction: [{allowed}] | Hard SL Pivot: {inv_lvl if inv_lvl else 'N/A'}")
        print(f"  • Volatility ATR(14): ${atr:.2f}")
        print("-" * 78)

        total_vol = sum(p.volume for p in basket)
        total_pnl = sum(p.profit for p in basket)
        pnl_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"

        print(f"BASKET STATUS: {len(basket)} / {self.max_layers} Active Layers | Total Volume: {total_vol:.2f} Lots")
        print(f"  • Target Profit: +${self.target_basket_profit:.2f} | Max Basket Loss Cap: -${self.max_basket_loss:.2f}")
        print(f"  • Current Floating P/L: {pnl_str}")

        if basket:
            be_price = sum(p.price_open * p.volume for p in basket) / total_vol
            print(f"  • Weighted Breakeven: {be_price:.2f}")
            print("\n  Open Orders:")
            for p in basket:
                d = "BUY" if p.type == 0 else "SELL"
                print(f"    #{p.ticket}: {d} {p.volume:.2f} @ {p.price_open:.2f} | P/L: ${p.profit:+.2f} | SL: {p.sl:.2f}")
        else:
            print("  • Basket Empty (Standing by for H1+M15 confluence alignment)")

        print("-" * 78)
        if news.get("active_blackout"):
            print(f"[!] MACRO BLACKOUT: {news.get('event')} in {news.get('diff_mins')}m! [AUTOTRADER PAUSED]")
        else:
            print("[+] MACRO STATUS: Green (No economic blackout events in immediate window)")
        print("=" * 78)
        print("Press Ctrl+C to stop trading station.")

    def run(self):
        print("[*] Starting Golden Combo Autonomous Trading Station...")
        try:
            while True:
                if not self._init_mt5():
                    time.sleep(3)
                    continue

                matrix = self.get_golden_combo_matrix()
                basket = self.get_open_basket()
                news = self.check_macro_news()
                tick = mt5.symbol_info_tick(SYMBOL)

                self.print_hud(matrix, basket, news)

                if not tick:
                    time.sleep(2)
                    continue

                curr_price = (tick.bid + tick.ask) / 2.0
                total_pnl = sum(p.profit for p in basket)

                # --- 1. EXIT EVALUATION ---
                if basket:
                    # A. Target Profit
                    if total_pnl >= self.target_basket_profit:
                        self.close_entire_basket(reason=f"TARGET_PROFIT_REACHED (+${total_pnl:.2f})")
                        time.sleep(3)
                        continue

                    # B. Hard Dollar Max Loss Stop
                    if total_pnl <= -self.max_basket_loss:
                        self.close_entire_basket(reason=f"MAX_BASKET_LOSS_STOP (-${abs(total_pnl):.2f})")
                        time.sleep(5)
                        continue

                    # C. Structural Invalidation
                    side = "BUY" if basket[0].type == mt5.ORDER_TYPE_BUY else "SELL"
                    inv_level = matrix.get("invalidation_level")
                    if inv_level:
                        if side == "BUY" and curr_price < inv_level:
                            self.close_entire_basket(reason=f"BULLISH_INVALIDATION_CUT (Price < {inv_level:.2f})")
                            time.sleep(4)
                            continue
                        elif side == "SELL" and curr_price > inv_level:
                            self.close_entire_basket(reason=f"BEARISH_INVALIDATION_CUT (Price > {inv_level:.2f})")
                            time.sleep(4)
                            continue

                    # D. Smart Averaging Layer Evaluation (Confluence must hold!)
                    if len(basket) < self.max_layers and not news.get("active_blackout"):
                        allowed = matrix.get("allowed_side", "NONE")
                        if allowed == side: # Only add if confluence still agrees!
                            last_order = basket[-1]
                            dist = abs(curr_price - last_order.price_open)
                            min_dist = max(1.80, matrix.get("atr", 3.50) * 1.2)

                            is_pullback = (side == "BUY" and curr_price <= last_order.price_open - min_dist) or \
                                          (side == "SELL" and curr_price >= last_order.price_open + min_dist)

                            if is_pullback:
                                m1_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 3)
                                if m1_rates is not None and len(m1_rates) >= 2:
                                    last_m1 = m1_rates[-2]
                                    is_bounce = (side == "BUY" and last_m1['close'] > last_m1['open']) or \
                                                (side == "SELL" and last_m1['close'] < last_m1['open'])

                                    if is_bounce:
                                        self.open_layer(side, len(basket), inv_level or 0.0)
                                        time.sleep(3)

                # --- 2. ENTRY EVALUATION (If basket is empty) ---
                else:
                    if not news.get("active_blackout"):
                        allowed = matrix.get("allowed_side", "NONE")
                        inv_level = matrix.get("invalidation_level")

                        if allowed in ["BUY", "SELL"] and inv_level is not None:
                            # M1/M5 Precision Trigger: Candle confirmation
                            m1_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 2)
                            if m1_rates is not None and len(m1_rates) >= 1:
                                curr_m1 = m1_rates[-1]
                                m1_aligned = (allowed == "BUY" and curr_m1['close'] >= curr_m1['open']) or \
                                             (allowed == "SELL" and curr_m1['close'] <= curr_m1['open'])

                                if m1_aligned:
                                    print(f"[*] Golden Confluence Trigger: {allowed} (H1 {matrix.get('h1_trend')} + M15 {matrix.get('m15_regime')})")
                                    self.open_layer(allowed, 0, inv_level)
                                    time.sleep(3)

                time.sleep(2)

        except KeyboardInterrupt:
            print("\n[*] Golden Combo Trader stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="StructureGrid Pro Golden Combo Edition")
    parser.add_argument("--base-lot", type=float, default=0.01)
    parser.add_argument("--target-tp", type=float, default=3.50)
    parser.add_argument("--max-loss", type=float, default=25.00)
    args = parser.parse_args()

    trader = GoldenComboTrader(
        base_lot=args.base_lot,
        target_basket_profit=args.target_tp,
        max_basket_loss=args.max_loss
    )
    trader.run()

if __name__ == "__main__":
    main()
