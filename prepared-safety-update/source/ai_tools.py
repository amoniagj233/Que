"""
AI Tool Registry & Schema Provider
==================================
Provides standardized tool/function definitions for external AI agents:
- OpenAI Function Calling schema
- Anthropic Claude Tool use schema
- Universal dispatcher to execute AI tool calls safely against MT5
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from mt5_connector import mt5_connector


TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_account_info": {
        "description": "Fetch current trading account details: balance, equity, free margin, profit, leverage, and connection status.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": lambda params: mt5_connector.get_account_info(),
    },
    "get_open_positions": {
        "description": "Get all currently open positions with ticket numbers, open prices, floating profits, stop losses, and take profits.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Optional symbol to filter positions (e.g. 'XAUUSD', 'EURUSD'). Leave empty for all."}
            },
            "required": [],
        },
        "handler": lambda params: mt5_connector.get_open_positions(symbol=params.get("symbol")),
    },
    "get_live_quote": {
        "description": "Fetch real-time bid, ask, and spread for a specific symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The market symbol to query (e.g. 'XAUUSD', 'EURUSD', 'Volatility 75 Index')."}
            },
            "required": ["symbol"],
        },
        "handler": lambda params: mt5_connector.get_quote(symbol=params["symbol"]),
    },
    "get_market_candles": {
        "description": "Retrieve recent historical OHLCV candle bars for technical analysis and strategy decision-making.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name (e.g. 'XAUUSD', 'EURUSD')."},
                "timeframe": {
                    "type": "string",
                    "enum": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
                    "description": "Candle timeframe. Default is 'M15'.",
                },
                "count": {"type": "integer", "description": "Number of candle bars to return (e.g. 50, 100). Default is 100."},
            },
            "required": ["symbol"],
        },
        "handler": lambda params: mt5_connector.get_candles(
            symbol=params["symbol"],
            timeframe=params.get("timeframe", "M15"),
            count=int(params.get("count", 100)),
        ),
    },
    "place_market_order": {
        "description": "Execute a live market BUY or SELL trade immediately on MetaTrader 5.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol to trade (e.g. 'XAUUSD', 'EURUSD', 'Volatility 75 Index')."},
                "action": {"type": "string", "enum": ["BUY", "SELL"], "description": "Trade direction: 'BUY' or 'SELL'."},
                "volume": {"type": "number", "description": "Lot size (e.g. 0.01, 0.1)."},
                "stop_loss": {"type": "number", "description": "Optional absolute stop loss price."},
                "take_profit": {"type": "number", "description": "Optional absolute take profit price."},
                "comment": {"type": "string", "description": "Optional comment string for trade identification (e.g. 'AI-Agent-1')."},
            },
            "required": ["symbol", "action", "volume"],
        },
        "handler": lambda params: mt5_connector.place_market_order(
            symbol=params["symbol"],
            action=params["action"],
            volume=float(params["volume"]),
            stop_loss=float(params["stop_loss"]) if params.get("stop_loss") else None,
            take_profit=float(params["take_profit"]) if params.get("take_profit") else None,
            comment=params.get("comment", "AI-Order"),
        ),
    },
    "modify_position": {
        "description": "Update Stop Loss and/or Take Profit for an open trade ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket": {"type": "integer", "description": "Position ticket ID to modify."},
                "stop_loss": {"type": "number", "description": "New stop loss price."},
                "take_profit": {"type": "number", "description": "New take profit price."},
            },
            "required": ["ticket"],
        },
        "handler": lambda params: mt5_connector.modify_position(
            ticket=int(params["ticket"]),
            stop_loss=float(params["stop_loss"]) if params.get("stop_loss") else None,
            take_profit=float(params["take_profit"]) if params.get("take_profit") else None,
        ),
    },
    "close_position": {
        "description": "Close an open trade position on MT5 by ticket ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket": {"type": "integer", "description": "Position ticket ID to close."},
                "volume": {"type": "number", "description": "Optional partial volume to close. Leave empty to close entire position."},
            },
            "required": ["ticket"],
        },
        "handler": lambda params: mt5_connector.close_position(
            ticket=int(params["ticket"]),
            volume=float(params["volume"]) if params.get("volume") else None,
        ),
    },
    "close_all_positions": {
        "description": "Emergency or bulk action to close all open trades across all symbols or a specific symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Optional symbol to close trades for. If empty, closes all positions."},
            },
            "required": [],
        },
        "handler": lambda params: mt5_connector.close_all_positions(symbol=params.get("symbol")),
    },
    "get_history": {
        "description": "Fetch recently closed deal history and net realized profit/loss.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of past days to query. Default is 7."},
            },
            "required": [],
        },
        "handler": lambda params: mt5_connector.get_history_deals(days=int(params.get("days", 7))),
    },
}


def get_openai_tools() -> List[Dict[str, Any]]:
    """Returns tools formatted for OpenAI function calling (GPT-4o, ChatGPT, etc.)."""
    tools = []
    for name, item in TOOLS_REGISTRY.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": item["description"],
                "parameters": item["parameters"],
            }
        })
    return tools


def get_anthropic_tools() -> List[Dict[str, Any]]:
    """Returns tools formatted for Anthropic Claude tool use."""
    tools = []
    for name, item in TOOLS_REGISTRY.items():
        tools.append({
            "name": name,
            "description": item["description"],
            "input_schema": item["parameters"],
        })
    return tools


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Universal dispatcher to execute an AI tool call."""
    if tool_name not in TOOLS_REGISTRY:
        return {
            "success": False,
            "error": f"Unknown tool '{tool_name}'. Available tools: {list(TOOLS_REGISTRY.keys())}",
        }
    
    handler = TOOLS_REGISTRY[tool_name]["handler"]
    try:
        res = handler(arguments or {})
        return {"success": True, "tool": tool_name, "result": res}
    except Exception as e:
        return {"success": False, "tool": tool_name, "error": str(e)}
