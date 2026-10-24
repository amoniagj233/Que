import os
from typing import Optional
from pydantic import BaseModel

class Settings(BaseModel):
    HOST: str = os.getenv("BRIDGE_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("BRIDGE_PORT", "8000"))
    MT5_PATH: str = os.getenv("MT5_PATH", r"C:\Program Files\Headway MT5 Terminal\terminal64.exe")
    MT5_SERVER: Optional[str] = os.getenv("MT5_SERVER", "Headway-Real")
    DEFAULT_MAGIC: int = int(os.getenv("DEFAULT_MAGIC", "202601"))
    DEFAULT_SLIPPAGE: int = int(os.getenv("DEFAULT_SLIPPAGE", "20"))
    MAX_POSITION_RISK_PERCENT: float = float(os.getenv("MAX_POSITION_RISK_PERCENT", "5.0"))
    DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "M15")
    ONLY_USE_QUOTE_SYMBOLS: bool = os.getenv("ONLY_USE_QUOTE_SYMBOLS", "True").lower() in ("true", "1", "yes")
    SERVER_TITLE: str = "Headway MT5 Universal AI Trading Bridge"
    SERVER_VERSION: str = "1.0.0"

settings = Settings()
