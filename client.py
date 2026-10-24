"""
MT5 AI Client SDK
=================
Lightweight, full-featured Python client for other AI projects, scripts, or LLM agents
to communicate with the MT5 Universal Bridge.
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List, Optional


class MT5Client:
    """
    Python SDK for external AIs to access MetaTrader 5 via the REST API Bridge.
    
    Example:
        >>> from client import MT5Client
        >>> ai = MT5Client("http://127.0.0.1:8000")
        >>> acc = ai.get_account()
        >>> print(acc["balance"], acc["equity"])
        >>> order = ai.buy("XAUUSD", volume=0.01, stop_loss=4100.0)
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def health(self) -> Dict[str, Any]:
        """Check bridge health and MT5 connection status."""
        r = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_account(self) -> Dict[str, Any]:
        """Fetch current account balances, equity, margin, and connection status."""
        r = self.session.get(f"{self.base_url}/api/account", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_symbols(self) -> List[str]:
        """Get list of active trading symbols."""
        r = self.session.get(f"{self.base_url}/api/symbols", timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("symbols", [])

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get live bid, ask, and spread for a symbol."""
        r = self.session.get(f"{self.base_url}/api/quote/{symbol}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_candles(self, symbol: str, timeframe: str = "M15", count: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent historical OHLCV candle bars."""
        r = self.session.get(
            f"{self.base_url}/api/candles/{symbol}",
            params={"timeframe": timeframe, "count": count},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("candles", [])

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active open positions."""
        params = {"symbol": symbol} if symbol else {}
        r = self.session.get(f"{self.base_url}/api/positions", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("positions", [])

    def buy(
        self,
        symbol: str,
        volume: float = 0.01,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = "AI-Buy",
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a market BUY order."""
        payload = {
            "symbol": symbol,
            "action": "BUY",
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": comment,
            "magic": magic,
        }
        r = self.session.post(f"{self.base_url}/api/trade/market", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def sell(
        self,
        symbol: str,
        volume: float = 0.01,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = "AI-Sell",
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a market SELL order."""
        payload = {
            "symbol": symbol,
            "action": "SELL",
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": comment,
            "magic": magic,
        }
        r = self.session.post(f"{self.base_url}/api/trade/market", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def modify(self, ticket: int, stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Modify Stop Loss and/or Take Profit of an existing position."""
        payload = {"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit}
        r = self.session.post(f"{self.base_url}/api/trade/modify", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def close(self, ticket: int, volume: Optional[float] = None) -> Dict[str, Any]:
        """Close an open position by ticket."""
        payload = {"ticket": ticket, "volume": volume}
        r = self.session.post(f"{self.base_url}/api/trade/close", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def close_all(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Close all open positions."""
        payload = {"symbol": symbol} if symbol else {}
        r = self.session.post(f"{self.base_url}/api/trade/close-all", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch past closed deals."""
        r = self.session.get(f"{self.base_url}/api/history", params={"days": days}, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("deals", [])

    def execute_ai_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run an arbitrary tool by name (ideal for LLM agent function calling)."""
        payload = {"tool_name": tool_name, "parameters": parameters}
        r = self.session.post(f"{self.base_url}/api/ai/execute", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
