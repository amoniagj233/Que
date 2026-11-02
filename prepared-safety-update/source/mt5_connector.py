"""
MT5 Universal Connector
=======================
Thread-safe singleton connector to MetaTrader 5 terminal.
Provides high-level methods for account management, market data, and order execution.
"""

from __future__ import annotations

from execution_gateway import guarded_order_send
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

import pandas as pd
from config import settings

logger = logging.getLogger("MT5Connector")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1 if mt5 else 1,
    "M5": mt5.TIMEFRAME_M5 if mt5 else 5,
    "M15": mt5.TIMEFRAME_M15 if mt5 else 15,
    "M30": mt5.TIMEFRAME_M30 if mt5 else 30,
    "H1": mt5.TIMEFRAME_H1 if mt5 else 16385,
    "H4": mt5.TIMEFRAME_H4 if mt5 else 16388,
    "D1": mt5.TIMEFRAME_D1 if mt5 else 16408,
    "W1": mt5.TIMEFRAME_W1 if mt5 else 32769,
    "MN1": mt5.TIMEFRAME_MN1 if mt5 else 49153,
}

ACTION_MAP = {
    "BUY": mt5.ORDER_TYPE_BUY if mt5 else 0,
    "SELL": mt5.ORDER_TYPE_SELL if mt5 else 1,
    "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT if mt5 else 2,
    "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT if mt5 else 3,
    "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP if mt5 else 4,
    "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP if mt5 else 5,
}


class MT5Connector:
    _instance: Optional[MT5Connector] = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MT5Connector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.lock = threading.RLock()
        self.is_connected = False
        self._initialize_terminal()
        self._initialized = True

    def _initialize_terminal(self) -> bool:
        with self.lock:
            if mt5 is None:
                logger.error("MetaTrader5 package is not available in Python environment.")
                self.is_connected = False
                return False

            init_path = getattr(settings, "MT5_PATH", None)
            init_success = False

            if init_path:
                logger.info(f"Connecting to Headway MT5 terminal at: {init_path}")
                init_success = mt5.initialize(path=init_path)

            if not init_success:
                if init_path:
                    logger.warning(f"Could not connect via explicit path '{init_path}', attempting fallback initialize()...")
                init_success = mt5.initialize()

            if not init_success:
                err = mt5.last_error()
                logger.error(f"Failed to initialize MT5 terminal: {err}")
                self.is_connected = False
                return False
            
            acc = mt5.account_info()
            if acc is None:
                logger.warning("MT5 initialized but no active account is logged in.")
                self.is_connected = False
                return False

            term = mt5.terminal_info()
            term_name = term.name if term else "MT5"

            self.is_connected = True
            logger.info(f"Connected to {term_name} successfully! Login: {acc.login}, Server: {acc.server}, Balance: {acc.balance} {acc.currency}")
            return True

    def ensure_connected(self) -> bool:
        with self.lock:
            if not self.is_connected:
                return self._initialize_terminal()
            # Quick ping via account_info
            if mt5.account_info() is None:
                logger.warning("MT5 connection lost, re-initializing...")
                return self._initialize_terminal()
            return True

    def get_account_info(self) -> Dict[str, Any]:
        """Returns structured details of the connected trading account."""
        with self.lock:
            if not self.ensure_connected():
                return {"error": "MT5 terminal not connected"}
            acc = mt5.account_info()
            if acc is None:
                return {"error": f"Failed to retrieve account info: {mt5.last_error()}"}
            
            d = acc._asdict()
            term = mt5.terminal_info()
            term_dict = term._asdict() if term else {}
            return {
                "login": d.get("login"),
                "trade_mode": "Demo" if d.get("trade_mode") == 0 else "Real",
                "name": d.get("name"),
                "server": d.get("server"),
                "company": d.get("company") or term_dict.get("company", "Headway"),
                "terminal_name": term_dict.get("name", "Headway MT5 Terminal"),
                "currency": d.get("currency"),
                "balance": round(d.get("balance", 0.0), 2),
                "equity": round(d.get("equity", 0.0), 2),
                "profit": round(d.get("profit", 0.0), 2),
                "margin": round(d.get("margin", 0.0), 2),
                "free_margin": round(d.get("margin_free", 0.0), 2),
                "margin_level": round(d.get("margin_level", 0.0), 2),
                "leverage": d.get("leverage"),
                "trade_allowed": d.get("trade_allowed"),
                "trade_expert": d.get("trade_expert"),
                "terminal_connected": True,
            }

    def is_symbol_on_quotes(self, symbol: str) -> bool:
        """Returns True if symbol exists and is selected/visible in Headway MT5 Quotes (Market Watch)."""
        with self.lock:
            if not self.ensure_connected():
                return False
            s = mt5.symbol_info(symbol)
            return bool(s and getattr(s, "visible", False))

    def get_symbols(self, group: Optional[str] = None) -> List[str]:
        """Returns list of visible symbols currently in Headway MT5 Quotes (Market Watch)."""
        with self.lock:
            if not self.ensure_connected():
                return []
            symbols = mt5.symbols_get(group) if group else mt5.symbols_get()
            if not symbols:
                return []
            return [s.name for s in symbols if s.visible]

    # Alias for convenience
    get_quote_symbols = get_symbols

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Returns contract specification and pricing data for a symbol on Quotes."""
        with self.lock:
            if not self.ensure_connected():
                return None
            if getattr(settings, "ONLY_USE_QUOTE_SYMBOLS", True):
                if not self.is_symbol_on_quotes(symbol):
                    logger.warning(f"get_symbol_info rejected '{symbol}': not active on Quotes.")
                    return None
            elif not mt5.symbol_select(symbol, True):
                return None

            s = mt5.symbol_info(symbol)
            if s is None:
                return None
            tick = mt5.symbol_info_tick(symbol)
            return {
                "symbol": s.name,
                "description": s.description,
                "bid": tick.bid if tick else s.bid,
                "ask": tick.ask if tick else s.ask,
                "spread_points": s.spread,
                "digits": s.digits,
                "point": s.point,
                "min_lot": s.volume_min,
                "max_lot": s.volume_max,
                "step_lot": s.volume_step,
                "filling_mode": s.filling_mode,
                "trade_mode": s.trade_mode,
                "tick_size": getattr(s, "trade_tick_size", 0.0) or s.point,
                "tick_value": getattr(s, "trade_tick_value", 0.0),
                "contract_size": getattr(s, "trade_contract_size", 0.0),
                "stops_level": getattr(s, "trade_stops_level", 0),
            }

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Returns live bid, ask, and spread for a symbol on Quotes."""
        with self.lock:
            if not self.ensure_connected():
                return {"error": "MT5 terminal not connected"}
            if getattr(settings, "ONLY_USE_QUOTE_SYMBOLS", True):
                if not self.is_symbol_on_quotes(symbol):
                    return {"error": f"Symbol '{symbol}' is not present in Headway Quotes. Only symbols active on Quotes are permitted."}
            elif not mt5.symbol_select(symbol, True):
                return {"error": f"Symbol '{symbol}' not found or cannot be selected"}

            tick = mt5.symbol_info_tick(symbol)
            s_info = mt5.symbol_info(symbol)
            if tick is None or s_info is None:
                return {"error": f"Could not fetch tick for '{symbol}'"}
            
            spread_price = round(tick.ask - tick.bid, s_info.digits)
            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread_points": s_info.spread,
                "spread_price": spread_price,
                "time": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat(),
                "digits": s_info.digits,
                "point": s_info.point,
            }

    def get_candles(self, symbol: str, timeframe: str = "M15", count: int = 100) -> List[Dict[str, Any]]:
        """Fetches historical OHLCV candle bars for a symbol on Quotes."""
        with self.lock:
            if not self.ensure_connected():
                return []
            if getattr(settings, "ONLY_USE_QUOTE_SYMBOLS", True):
                if not self.is_symbol_on_quotes(symbol):
                    logger.warning(f"get_candles rejected '{symbol}': not active on Quotes.")
                    return []
            elif not mt5.symbol_select(symbol, True):
                return []

            tf = TIMEFRAME_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M15)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                return []
            
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            return df[["time", "open", "high", "low", "close", "tick_volume"]].to_dict(orient="records")

    def _determine_filling_mode(self, symbol_info) -> int:
        """Derives the appropriate filling mode supported by the broker for this symbol."""
        filling = symbol_info.filling_mode
        # ORDER_FILLING_FOK = 1, ORDER_FILLING_IOC = 2, ORDER_FILLING_RETURN = 0
        if filling & 2:
            return mt5.ORDER_FILLING_IOC
        if filling & 1:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

    def place_market_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = "AI-Order",
        magic: Optional[int] = None,
        slippage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a live market BUY or SELL order on MT5.
        
        Args:
            symbol: e.g. 'EURUSD', 'XAUUSD', 'Volatility 75 Index'
            action: 'BUY' or 'SELL'
            volume: Lot size (e.g. 0.01)
            stop_loss: Absolute stop loss price
            take_profit: Absolute take profit price
            comment: Order comment string
            magic: EA / Agent identifier number
            slippage: Maximum allowed slippage in points
        """
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}
            
            action_norm = action.upper().strip()
            if action_norm not in ("BUY", "SELL"):
                return {"success": False, "error": f"Invalid action '{action}'. Must be 'BUY' or 'SELL'"}

            if getattr(settings, "ONLY_USE_QUOTE_SYMBOLS", True):
                if not self.is_symbol_on_quotes(symbol):
                    return {"success": False, "error": f"Symbol '{symbol}' is not present in Headway Quotes. Orders are restricted to Quotes symbols only."}
            elif not mt5.symbol_select(symbol, True):
                return {"success": False, "error": f"Symbol '{symbol}' not found or cannot be selected"}

            s_info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if not s_info or not tick:
                return {"success": False, "error": f"Failed to get price data for '{symbol}'"}

            # Validate volume against symbol contract steps
            step = s_info.volume_step or 0.01
            vol_min = s_info.volume_min or 0.01
            vol_max = s_info.volume_max or 100.0
            
            # Clamp or round volume
            volume = round(round(volume / step) * step, 8)
            if volume < vol_min:
                return {"success": False, "error": f"Volume {volume} is below minimum allowed lot size ({vol_min})"}
            if volume > vol_max:
                return {"success": False, "error": f"Volume {volume} exceeds maximum allowed lot size ({vol_max})"}

            order_type = mt5.ORDER_TYPE_BUY if action_norm == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if action_norm == "BUY" else tick.bid
            filling_mode = self._determine_filling_mode(s_info)

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": float(price),
                "deviation": slippage or settings.DEFAULT_SLIPPAGE,
                "type_filling": filling_mode,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": comment or "AI-Bridge",
                "magic": magic or settings.DEFAULT_MAGIC,
            }

            if stop_loss is not None and stop_loss > 0:
                req["sl"] = round(float(stop_loss), s_info.digits)
            if take_profit is not None and take_profit > 0:
                req["tp"] = round(float(take_profit), s_info.digits)

            # Send order
            res = guarded_order_send(mt5, req)
            if res is None:
                err = mt5.last_error()
                return {"success": False, "error": f"Order send failed: {err}"}

            if res.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "retcode": res.retcode,
                    "comment": res.comment,
                    "error": f"Broker rejected order: {res.comment} (code {res.retcode})",
                    "request": req,
                }

            return {
                "success": True,
                "order_ticket": res.order,
                "deal_ticket": res.deal,
                "symbol": symbol,
                "action": action_norm,
                "volume": res.volume,
                "price": res.price,
                "stop_loss": req.get("sl"),
                "take_profit": req.get("tp"),
                "comment": res.comment,
                "time": datetime.now(timezone.utc).isoformat(),
            }

    def place_pending_order(
        self,
        symbol: str,
        order_type: str,
        price: float,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = "AI-Pending",
        magic: Optional[int] = None,
        expiration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Places a limit or stop pending order. expiration = unix timestamp (optional)."""
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}
            
            ot_norm = order_type.upper().strip()
            if ot_norm not in ACTION_MAP:
                return {"success": False, "error": f"Invalid order type '{order_type}'"}

            if getattr(settings, "ONLY_USE_QUOTE_SYMBOLS", True):
                if not self.is_symbol_on_quotes(symbol):
                    return {"success": False, "error": f"Symbol '{symbol}' is not present in Headway Quotes. Orders are restricted to Quotes symbols only."}
            elif not mt5.symbol_select(symbol, True):
                return {"success": False, "error": f"Symbol '{symbol}' not found or cannot be selected"}

            s_info = mt5.symbol_info(symbol)
            if not s_info:
                return {"success": False, "error": f"Symbol '{symbol}' not found"}

            filling_mode = self._determine_filling_mode(s_info)
            req = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": float(volume),
                "type": ACTION_MAP[ot_norm],
                "price": round(float(price), s_info.digits),
                "type_filling": filling_mode,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": comment or "AI-Pending",
                "magic": magic or settings.DEFAULT_MAGIC,
            }
            if stop_loss:
                req["sl"] = round(float(stop_loss), s_info.digits)
            if take_profit:
                req["tp"] = round(float(take_profit), s_info.digits)
            if expiration:
                req["type_time"] = mt5.ORDER_TIME_SPECIFIED
                req["expiration"] = int(expiration)

            res = guarded_order_send(mt5, req)
            if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                err_msg = res.comment if res else str(mt5.last_error())
                return {"success": False, "error": err_msg, "retcode": getattr(res, "retcode", None)}

            return {
                "success": True,
                "order_ticket": res.order,
                "symbol": symbol,
                "order_type": ot_norm,
                "price": res.price,
                "volume": res.volume,
            }

    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns active pending (limit/stop) orders."""
        with self.lock:
            if not self.ensure_connected():
                return []
            orders = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
            return [{"ticket": o.ticket, "symbol": o.symbol, "type": o.type, "price": o.price_open,
                     "volume": o.volume_current, "sl": o.sl, "tp": o.tp, "magic": o.magic, "comment": o.comment}
                    for o in (orders or [])]

    def cancel_order(self, ticket: int) -> Dict[str, Any]:
        """Deletes a pending order."""
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}
            res = guarded_order_send(mt5, {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})
            if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "error": res.comment if res else str(mt5.last_error())}
            return {"success": True, "ticket": ticket}

    def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modifies the Stop Loss or Take Profit of an existing position."""
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}

            pos = mt5.positions_get(ticket=ticket)
            if not pos:
                return {"success": False, "error": f"Position ticket {ticket} not found"}

            p = pos[0]
            s_info = mt5.symbol_info(p.symbol)
            digits = s_info.digits if s_info else 2

            req = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": p.symbol,
                "sl": round(float(stop_loss), digits) if stop_loss is not None else p.sl,
                "tp": round(float(take_profit), digits) if take_profit is not None else p.tp,
            }

            res = guarded_order_send(mt5, req)
            if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                err_msg = res.comment if res else str(mt5.last_error())
                return {"success": False, "error": err_msg, "retcode": getattr(res, "retcode", None)}

            return {"success": True, "ticket": ticket, "sl": req["sl"], "tp": req["tp"]}

    def close_position(self, ticket: int, volume: Optional[float] = None) -> Dict[str, Any]:
        """Closes an open position by ticket, optionally with partial volume."""
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}

            pos = mt5.positions_get(ticket=ticket)
            if not pos:
                return {"success": False, "error": f"Position #{ticket} not found"}

            p = pos[0]
            s_info = mt5.symbol_info(p.symbol)
            tick = mt5.symbol_info_tick(p.symbol)
            if not s_info or not tick:
                return {"success": False, "error": f"Could not get tick for {p.symbol}"}

            close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
            close_vol = volume if (volume and volume < p.volume) else p.volume
            filling_mode = self._determine_filling_mode(s_info)

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": p.symbol,
                "volume": float(close_vol),
                "type": close_type,
                "price": float(price),
                "deviation": settings.DEFAULT_SLIPPAGE,
                "type_filling": filling_mode,
                "comment": "AI-Close",
            }

            res = guarded_order_send(mt5, req)
            if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                err_msg = res.comment if res else str(mt5.last_error())
                return {"success": False, "error": err_msg, "retcode": getattr(res, "retcode", None)}

            return {
                "success": True,
                "closed_ticket": ticket,
                "deal": res.deal,
                "closed_volume": res.volume,
                "close_price": res.price,
            }

    def close_all_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Closes all open positions, optionally filtered by symbol."""
        with self.lock:
            if not self.ensure_connected():
                return {"success": False, "error": "MT5 terminal not connected"}

            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if not positions:
                return {"success": True, "closed_count": 0, "message": "No positions to close"}

            results = []
            for p in positions:
                r = self.close_position(p.ticket)
                results.append({"ticket": p.ticket, "symbol": p.symbol, "success": r.get("success", False)})

            return {
                "success": True,
                "closed_count": len([r for r in results if r["success"]]),
                "total_count": len(positions),
                "details": results,
            }

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of currently open positions."""
        with self.lock:
            if not self.ensure_connected():
                return []

            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if not positions:
                return []

            out = []
            for p in positions:
                out.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "price_open": p.price_open,
                    "price_current": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": round(p.profit, 2),
                    "swap": p.swap,
                    "magic": p.magic,
                    "comment": p.comment,
                    "time": datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
                })
            return out

    # Alias for convenience
    get_positions = get_open_positions

    def get_history_deals(self, days: int = 7) -> List[Dict[str, Any]]:
        """Returns closed deal history for past N days."""
        with self.lock:
            if not self.ensure_connected():
                return []

            from_date = datetime.now(timezone.utc) - timedelta(days=days)
            to_date = datetime.now(timezone.utc) + timedelta(days=1)
            deals = mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            out = []
            for d in deals:
                out.append({
                    "ticket": d.ticket,
                    "order": d.order,
                    "position_id": d.position_id,
                    "symbol": d.symbol,
                    "type": "BUY" if d.type == 0 else "SELL",
                    "entry": "IN" if d.entry == 0 else "OUT" if d.entry == 1 else "INOUT",
                    "volume": d.volume,
                    "price": d.price,
                    "profit": round(d.profit, 2),
                    "commission": round(d.commission, 2),
                    "swap": round(d.swap, 2),
                    "magic": d.magic,
                    "comment": d.comment,
                    "time": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
                })
            return out

    # Alias for convenience
    get_positions = get_open_positions


# Global singleton instance
mt5_connector = MT5Connector()
