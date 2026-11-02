"""M30 Reference Candle Range Detector for CRT Gold Pro."""
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class CRTRange:
    id: str
    time_open: str
    time_close: str
    open: float
    high: float
    low: float
    close: float
    midpoint: float
    range_size: float
    atr: float


class CandleRangeDetector:
    def __init__(self):
        self.current_range: Optional[CRTRange] = None

    def update(self, df_m30: pd.DataFrame) -> Optional[CRTRange]:
        """Evaluates completed M30 candles (ignores the actively forming candle at index -1)."""
        if df_m30 is None or len(df_m30) < 2:
            return None

        # Completed M30 candle is at index -2
        candle = df_m30.iloc[-2]
        c_time_open = str(candle["time"])
        c_open = float(candle["open"])
        c_high = float(candle["high"])
        c_low = float(candle["low"])
        c_close = float(candle["close"])

        midpoint = round((c_high + c_low) / 2.0, 2)
        range_size = round(c_high - c_low, 2)

        # Approximate ATR of M30 from last 14 completed bars
        highs = df_m30["high"].to_numpy()[:-1]
        lows = df_m30["low"].to_numpy()[:-1]
        atr = round(float(pd.Series(highs - lows).rolling(14).mean().iloc[-1]), 2) if len(highs) >= 14 else range_size

        range_id = f"M30_{c_time_open.replace(' ', '_').replace(':', '')}"

        self.current_range = CRTRange(
            id=range_id,
            time_open=c_time_open,
            time_close=str(df_m30.iloc[-1]["time"]),
            open=c_open,
            high=c_high,
            low=c_low,
            close=c_close,
            midpoint=midpoint,
            range_size=range_size,
            atr=atr
        )
        return self.current_range
