"""Centralized MT5 Gold Bridge for APEX AI Commander.

Provides robust connection, symbol discovery, account metrics, order routing,
position reconciliation, and deal history.
"""
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("apex_mt5_bridge")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class MT5GoldBridge:
    def __init__(self, target_account: Optional[int] = 6278930):
        self.target_account = target_account
        self.connected = False
        self.terminal_name = ""
        self.gold_symbol = "XAUUSD"
        self.symbol_info: Dict[str, Any] = {}
        self.margin_mode = 2  # Default Retail Hedging
        self.last_error = ""
        self.last_reconcile_ts = 0.0

    def initialize(self) -> bool:
        if not MT5_AVAILABLE:
            self.last_error = "MetaTrader5 python package not installed"
            return False

        try:
            # Try plain initialize first (attaches to already running terminal)
            if not mt5.initialize():
                # Try dynamic discovery via mt5_finder
                try:
                    from mt5_finder import get_candidate_terminal_paths
                    paths = get_candidate_terminal_paths()
                except Exception:
                    paths = [
                        r"C:\Program Files\Headway MT5 Terminal\terminal64.exe",
                        r"C:\Program Files\MetaTrader 5\terminal64.exe"
                    ]
                init_ok = False
                for p in paths:
                    if os.path.exists(p):
                        if mt5.initialize(path=p):
                            init_ok = True
                            break
                if not init_ok:
                    self.last_error = f"mt5.initialize failed: {mt5.last_error()}"
                    return False

            term = mt5.terminal_info()
            if term:
                self.terminal_name = term.name
            
            acc = mt5.account_info()
            if acc:
                self.margin_mode = acc.margin_mode
                self.connected = True
            else:
                self.last_error = f"account_info failed: {mt5.last_error()}"
                return False

            self.gold_symbol = self.discover_gold_symbol()
            self._cache_symbol_info(self.gold_symbol)
            return True
        except Exception as e:
            self.last_error = str(e)
            self.connected = False
            return False

    def discover_gold_symbol(self) -> str:
        """Auto-discover broker-specific gold symbol."""
        if not MT5_AVAILABLE or not self.connected:
            return "XAUUSD"

        candidates = ["XAUUSD", "XAUUSDm", "XAUUSDc", "GOLD", "XAUT", "XAUAUD"]
        symbols = mt5.symbols_get()
        if not symbols:
            return "XAUUSD"

        available = {s.name for s in symbols}
        # Check standard candidates in priority order
        for c in candidates:
            if c in available:
                mt5.symbol_select(c, True)
                return c

        # Fallback to any symbol containing XAU or GOLD
        for s in symbols:
            name_u = s.name.upper()
            if "XAU" in name_u or "GOLD" in name_u:
                mt5.symbol_select(s.name, True)
                return s.name

        return "XAUUSD"

    def _cache_symbol_info(self, symbol: str) -> None:
        if not MT5_AVAILABLE:
            return
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
        if info:
            self.symbol_info = {
                "name": info.name,
                "point": info.point,
                "digits": info.digits,
                "spread": info.spread,
                "trade_tick_value": info.trade_tick_value,
                "trade_tick_size": info.trade_tick_size,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
                "bid": info.bid,
                "ask": info.ask
            }

    def get_account_summary(self) -> Dict[str, Any]:
        """Fetch real-time MT5 account metrics."""
        if not MT5_AVAILABLE or not self.connected:
            if not self.initialize():
                return {
                    "connected": False,
                    "login": self.target_account,
                    "balance": 0.0,
                    "equity": 0.0,
                    "margin": 0.0,
                    "margin_free": 0.0,
                    "margin_level": 0.0,
                    "profit": 0.0,
                    "margin_mode": "UNKNOWN",
                    "error": self.last_error
                }

        acc = mt5.account_info()
        if not acc:
            return {"connected": False, "error": f"Failed to get account info: {mt5.last_error()}"}

        margin_mode_name = "RETAIL_HEDGING" if acc.margin_mode == 2 else ("RETAIL_NETTING" if acc.margin_mode == 1 else "EXCHANGE")

        return {
            "connected": True,
            "login": acc.login,
            "server": acc.server,
            "currency": acc.currency,
            "balance": round(acc.balance, 2),
            "equity": round(acc.equity, 2),
            "margin": round(acc.margin, 2),
            "margin_free": round(acc.margin_free, 2),
            "margin_level": round(acc.margin_level, 2) if acc.margin > 0 else 0.0,
            "profit": round(acc.profit, 2),
            "margin_mode": margin_mode_name,
            "gold_symbol": self.gold_symbol,
            "terminal": self.terminal_name
        }

    def get_open_positions(self, symbol: Optional[str] = None, magic: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all open positions with optional symbol and magic number filters."""
        if not MT5_AVAILABLE or not self.connected:
            if not self.initialize():
                return []

        try:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if positions is None:
                return []

            result = []
            for p in positions:
                if magic is not None and p.magic != magic:
                    continue
                result.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": round(p.volume, 2),
                    "price_open": round(p.price_open, 2),
                    "sl": round(p.sl, 2) if p.sl else 0.0,
                    "tp": round(p.tp, 2) if p.tp else 0.0,
                    "price_current": round(p.price_current, 2),
                    "profit": round(p.profit, 2),
                    "swap": round(p.swap, 2),
                    "magic": p.magic,
                    "comment": p.comment,
                    "time": p.time
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return []

    def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        magic: int = 1000,
        comment: str = "Apex Commander",
        deviation: int = 25
    ) -> Dict[str, Any]:
        """Place market order with verified broker confirmation."""
        if not MT5_AVAILABLE or not self.connected:
            if not self.initialize():
                return {"ok": False, "error": f"MT5 not connected: {self.last_error}"}

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"ok": False, "error": f"Failed to get tick for {symbol}"}

        is_buy = action.upper() in ("BUY", "0")
        price = tick.ask if is_buy else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if sl is not None and sl > 0:
            request["sl"] = float(sl)
        if tp is not None and tp > 0:
            request["tp"] = float(tp)

        t0 = time.time()
        result = mt5.order_send(request)
        latency_ms = round((time.time() - t0) * 1000, 1)

        if result is None:
            return {"ok": False, "error": f"order_send failed: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "ok": False,
                "retcode": result.retcode,
                "error": f"Broker rejected: {result.comment} (retcode {result.retcode})",
                "latency_ms": latency_ms
            }

        return {
            "ok": True,
            "order": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "bid": result.bid,
            "ask": result.ask,
            "retcode": result.retcode,
            "comment": result.comment,
            "latency_ms": latency_ms
        }

    def close_position(self, ticket: int, deviation: int = 25) -> Dict[str, Any]:
        """Close an active position cleanly by ticket."""
        if not MT5_AVAILABLE or not self.connected:
            if not self.initialize():
                return {"ok": False, "error": "MT5 not connected"}

        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"ok": False, "error": f"Position #{ticket} not found"}

        p = pos[0]
        tick = mt5.symbol_info_tick(p.symbol)
        if not tick:
            return {"ok": False, "error": f"Failed to get tick for {p.symbol}"}

        close_type = mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY
        price = tick.bid if p.type == 0 else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": close_type,
            "price": price,
            "deviation": deviation,
            "magic": p.magic,
            "comment": "Apex Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else str(mt5.last_error())
            return {"ok": False, "error": f"Close rejected: {err}"}

        return {"ok": True, "deal": result.deal, "price": result.price, "volume": result.volume}

    def get_closed_deals_today(self) -> List[Dict[str, Any]]:
        """Fetch all closed deals for today."""
        if not MT5_AVAILABLE or not self.connected:
            if not self.initialize():
                return []

        now_ts = time.time()
        start_ts = now_ts - 86400  # Past 24 hours
        deals = mt5.history_deals_get(int(start_ts), int(now_ts))
        if deals is None:
            return []

        out = []
        for d in deals:
            if d.entry == 1:  # DealEntryOut
                out.append({
                    "ticket": d.ticket,
                    "order": d.order,
                    "time": d.time,
                    "symbol": d.symbol,
                    "type": "SELL" if d.type == 1 else "BUY",
                    "volume": round(d.volume, 2),
                    "price": round(d.price, 2),
                    "profit": round(d.profit, 2),
                    "commission": round(d.commission, 2),
                    "swap": round(d.swap, 2),
                    "magic": d.magic,
                    "comment": d.comment
                })
        return out


# Global singleton instance
bridge = MT5GoldBridge()
