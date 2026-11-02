import os
from typing import Optional
from pydantic import BaseModel

try:
    from mt5_finder import find_mt5_terminal_path
    _DEFAULT_MT5_PATH = find_mt5_terminal_path() or r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
except Exception:
    _DEFAULT_MT5_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"

class Settings(BaseModel):
    HOST: str = os.getenv("BRIDGE_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BRIDGE_PORT", "8000"))
    MT5_PATH: str = os.getenv("MT5_PATH", _DEFAULT_MT5_PATH)
    MT5_SERVER: Optional[str] = os.getenv("MT5_SERVER", "Headway-Real")
    DEFAULT_MAGIC: int = int(os.getenv("DEFAULT_MAGIC", "202601"))
    DEFAULT_SLIPPAGE: int = int(os.getenv("DEFAULT_SLIPPAGE", "20"))
    MAX_POSITION_RISK_PERCENT: float = float(os.getenv("MAX_POSITION_RISK_PERCENT", "5.0"))
    DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "M15")
    ONLY_USE_QUOTE_SYMBOLS: bool = os.getenv("ONLY_USE_QUOTE_SYMBOLS", "True").lower() in ("true", "1", "yes")
    SERVER_TITLE: str = "Headway MT5 Universal AI Trading Bridge"
    SERVER_VERSION: str = "1.0.0"

settings = Settings()
