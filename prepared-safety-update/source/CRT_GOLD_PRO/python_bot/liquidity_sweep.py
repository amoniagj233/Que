"""M5 Liquidity Sweep & Reclaim Detector for CRT Gold Pro."""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from .candle_detector import CRTRange


@dataclass
class SweepEvent:
    direction: str  # "BULLISH" or "BEARISH"
    sweep_price: float
    reclaim_close: float
    time: str
    atr_m5: float
    min_sweep: float
    candle_index: int


class LiquiditySweepDetector:
    def __init__(self, tick_size: float = 0.01):
        self.tick_size = tick_size
        self.active_sweep: Optional[SweepEvent] = None

    def calculate_m5_atr(self, df_m5: pd.DataFrame, period: int = 14) -> float:
        if df_m5 is None or len(df_m5) < period + 1:
            return 1.50
        highs = df_m5["high"].to_numpy()[:-1]
        lows = df_m5["low"].to_numpy()[:-1]
        closes = df_m5["close"].to_numpy()[:-1]
        tr = np.maximum(highs[1:] - lows[1:], np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
        atr = float(np.mean(tr[-period:])) if len(tr) >= period else 1.50
        return round(atr, 2)

    def check_sweep(self, df_m5: pd.DataFrame, crt_range: CRTRange) -> Optional[SweepEvent]:
        """Examines the latest completed M5 candle (index -2) relative to the active M30 range."""
        if df_m5 is None or len(df_m5) < 3 or crt_range is None:
            return None

        candle = df_m5.iloc[-2]
        c_high = float(candle["high"])
        c_low = float(candle["low"])
        c_close = float(candle["close"])
        c_time = str(candle["time"])

        atr_m5 = self.calculate_m5_atr(df_m5)
        min_sweep = max(2 * self.tick_size, 0.10 * atr_m5)

        # Reject double-sided sweeps
        if c_low < crt_range.low - min_sweep and c_high > crt_range.high + min_sweep:
            return None

        # 1. Bullish Sweep (Swept low and closed back inside range)
        if c_low < (crt_range.low - min_sweep) and (crt_range.low < c_close < crt_range.high):
            self.active_sweep = SweepEvent(
                direction="BULLISH",
                sweep_price=round(c_low, 2),
                reclaim_close=round(c_close, 2),
                time=c_time,
                atr_m5=atr_m5,
                min_sweep=round(min_sweep, 2),
                candle_index=len(df_m5) - 2
            )
            return self.active_sweep

        # 2. Bearish Sweep (Swept high and closed back inside range)
        if c_high > (crt_range.high + min_sweep) and (crt_range.low < c_close < crt_range.high):
            self.active_sweep = SweepEvent(
                direction="BEARISH",
                sweep_price=round(c_high, 2),
                reclaim_close=round(c_close, 2),
                time=c_time,
                atr_m5=atr_m5,
                min_sweep=round(min_sweep, 2),
                candle_index=len(df_m5) - 2
            )
            return self.active_sweep

        return None
