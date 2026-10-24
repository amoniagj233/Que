"""
MT5 Universal AI Bridge Server (FastAPI)
========================================
Exposes MetaTrader 5 over REST API and provides standard LLM Function Calling tools
so any external AI agent (OpenAI, Claude, DeepSeek, AutoGen, CrewAI, LangChain, Ollama)
can read market data and execute trades safely.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from mt5_connector import mt5_connector
import ai_tools
from pinbar_strategy import scan_market, backtest_pinbar, execute_setup

logger = logging.getLogger("BridgeServer")

app = FastAPI(
    title=settings.SERVER_TITLE,
    version=settings.SERVER_VERSION,
    description="Universal REST API & AI Function Calling Bridge for MetaTrader 5",
)

# Allow CORS for all origins so any local or remote AI agent can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class MarketOrderRequest(BaseModel):
    symbol: str = Field(..., description="Symbol to trade (e.g. 'XAUUSD', 'EURUSD')")
    action: str = Field(..., description="'BUY' or 'SELL'")
    volume: float = Field(..., gt=0, description="Lot size (e.g. 0.01, 0.1)")
    stop_loss: Optional[float] = Field(None, description="Absolute stop loss price")
    take_profit: Optional[float] = Field(None, description="Absolute take profit price")
    comment: Optional[str] = Field("AI-Bridge", description="Order comment")
    magic: Optional[int] = Field(None, description="Magic number")


class PendingOrderRequest(BaseModel):
    symbol: str
    order_type: str = Field(..., description="'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'")
    price: float
    volume: float = Field(..., gt=0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = "AI-Pending"
    magic: Optional[int] = None


class ModifyPositionRequest(BaseModel):
    ticket: int = Field(..., description="Position ticket ID")
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class ClosePositionRequest(BaseModel):
    ticket: int = Field(..., description="Position ticket ID")
    volume: Optional[float] = Field(None, gt=0, description="Optional partial volume to close")


class CloseAllRequest(BaseModel):
    symbol: Optional[str] = Field(None, description="Optional symbol to filter positions to close")


class AIExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the AI tool to run")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tool arguments")


# ---------------------------------------------------------------------------
# Core System & Market Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Health check endpoint showing MT5 terminal status and account connectivity."""
    acc = mt5_connector.get_account_info()
    return {
        "status": "healthy" if acc.get("terminal_connected") else "disconnected",
        "mt5_connected": acc.get("terminal_connected", False),
        "login": acc.get("login"),
        "server": acc.get("server"),
        "balance": acc.get("balance"),
        "equity": acc.get("equity"),
    }


@app.get("/api/account")
def get_account():
    """Get full details of the connected MetaTrader 5 account."""
    acc = mt5_connector.get_account_info()
    if "error" in acc:
        raise HTTPException(status_code=503, detail=acc["error"])
    return acc


@app.get("/api/symbols")
def get_symbols(group: Optional[str] = None):
    """List available market symbols."""
    symbols = mt5_connector.get_symbols(group)
    return {"symbols": symbols, "count": len(symbols)}


@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    """Get live bid/ask/spread for a specific symbol."""
    res = mt5_connector.get_quote(symbol)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@app.get("/api/candles/{symbol}")
def get_candles(
    symbol: str,
    timeframe: str = Query("M15", description="Candle timeframe: M1, M5, M15, H1, D1"),
    count: int = Query(100, ge=1, le=1000, description="Number of candles"),
):
    """Retrieve historical OHLCV candle bars for technical analysis."""
    candles = mt5_connector.get_candles(symbol, timeframe, count)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }


# ---------------------------------------------------------------------------
# Trading Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/positions")
def get_positions(symbol: Optional[str] = None):
    """List all currently active open positions."""
    return {"positions": mt5_connector.get_open_positions(symbol)}


@app.post("/api/trade/market")
def place_market_order(req: MarketOrderRequest):
    """Place a live market BUY or SELL order."""
    res = mt5_connector.place_market_order(
        symbol=req.symbol,
        action=req.action,
        volume=req.volume,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        comment=req.comment,
        magic=req.magic,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Order failed"))
    return res


@app.post("/api/trade/pending")
def place_pending_order(req: PendingOrderRequest):
    """Place a limit or stop pending order."""
    res = mt5_connector.place_pending_order(
        symbol=req.symbol,
        order_type=req.order_type,
        price=req.price,
        volume=req.volume,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        comment=req.comment,
        magic=req.magic,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Pending order failed"))
    return res


@app.post("/api/trade/modify")
def modify_position(req: ModifyPositionRequest):
    """Modify SL / TP of an open position."""
    res = mt5_connector.modify_position(
        ticket=req.ticket,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Modification failed"))
    return res


@app.post("/api/trade/close")
def close_position(req: ClosePositionRequest):
    """Close an open position by ticket ID."""
    res = mt5_connector.close_position(ticket=req.ticket, volume=req.volume)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Close failed"))
    return res


@app.post("/api/trade/close-all")
def close_all_positions(req: Optional[CloseAllRequest] = None):
    """Close all open positions across all symbols or a specific symbol."""
    sym = req.symbol if req else None
    return mt5_connector.close_all_positions(symbol=sym)


@app.get("/api/history")
def get_history(days: int = Query(7, ge=1, le=90)):
    """Fetch closed deal history."""
    return {"deals": mt5_connector.get_history_deals(days=days)}


# ---------------------------------------------------------------------------
# Pin Bar + Trend + Key Level Strategy Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/pinbar/scan")
def api_pinbar_scan(
    symbol: str = Query("XAUUSD", description="Symbol to scan, e.g. XAUUSD, EURUSD"),
    timeframe: str = Query("M15", description="Candle timeframe, e.g. M5, M15, H1, H4, D1"),
    count: int = Query(300, ge=50, le=5000, description="Number of candles for analysis")
):
    """Scans the market for a triple-confirmed Pin Bar + Trend + Key Level setup."""
    res = scan_market(symbol=symbol, timeframe=timeframe, count=count)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.get("/api/pinbar/backtest")
def api_pinbar_backtest(
    symbol: str = Query("XAUUSD", description="Symbol to backtest"),
    timeframe: str = Query("M15", description="Timeframe"),
    count: int = Query(2500, ge=100, le=10000, description="Number of historical candles"),
    rr: float = Query(2.0, ge=1.0, le=10.0, description="Risk/Reward ratio")
):
    """Runs a backtest of the Pin Bar + Trend + Key Level strategy on MT5 historical data."""
    res = backtest_pinbar(symbol=symbol, timeframe=timeframe, count=count, rr=rr)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.post("/api/pinbar/execute")
def api_pinbar_execute(
    symbol: str = Query("XAUUSD", description="Symbol to trade"),
    timeframe: str = Query("M15", description="Timeframe to scan"),
    volume: float = Query(0.01, gt=0, description="Lot size")
):
    """Scans the latest closed bar and automatically fires an MT5 order if a valid setup exists."""
    res = execute_setup(symbol=symbol, timeframe=timeframe, volume=volume)
    return res


# ---------------------------------------------------------------------------
# Universal AI Integration Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/ai/tools")
def get_ai_tool_schemas(format: str = Query("openai", description="'openai', 'anthropic', or 'raw'")):
    """
    Returns tool specifications ready for integration into any LLM agent.
    Supported formats: 'openai' (function calling), 'anthropic' (Claude tools), 'raw'.
    """
    if format.lower() == "anthropic":
        return {"tools": ai_tools.get_anthropic_tools()}
    elif format.lower() == "raw":
        return {"tools": ai_tools.TOOLS_REGISTRY}
    return {"tools": ai_tools.get_openai_tools()}


@app.post("/api/ai/execute")
def execute_ai_tool(req: AIExecuteRequest):
    """
    Universal execution endpoint for LLM agents.
    The agent passes `tool_name` and `parameters`, and gets the result back.
    """
    res = ai_tools.execute_tool(req.tool_name, req.parameters or {})
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res)
    return res


# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index_page():
    """Serves the live interactive Web Dashboard and AI integration monitor."""
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>MT5 AI Bridge Server is Running! Visit <a href='/docs'>/docs</a> for API.</h2>")


@app.get("/deriv-bot", response_class=HTMLResponse)
def deriv_bot_page():
    """Serves the Deriv Digit Bot web app."""
    bot_file = Path(__file__).parent / "deriv_bot.html"
    if bot_file.exists():
        return HTMLResponse(content=bot_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Deriv Bot page not found</h2>")
