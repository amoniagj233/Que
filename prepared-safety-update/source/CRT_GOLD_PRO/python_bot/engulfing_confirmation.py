"""M2 Engulfing Candlestick Confirmation for CRT Gold Pro."""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from .liquidity_sweep import SweepEvent


@dataclass
class ConfirmationEvent:
    direction: str  # "BULLISH" or "BEARISH"
    confirmed: bool
    time: str
    entry_signal_price: float
    bars_elapsed: int


class EngulfingConfirmationDetector:
    def __init__(self, max_bars: int = 3, tolerance: float = 0.05):
        self.max_bars = max_bars
        self.tolerance = tolerance

    def check_confirmation(
        self,
        df_m2: pd.DataFrame,
        sweep: SweepEvent
    ) -> Optional[ConfirmationEvent]:
        """Examines the latest completed M2 candles to find valid engulfing pattern."""
        if df_m2 is None or len(df_m2) < 3 or sweep is None:
            return None

        # Look at the most recent completed M2 candle (index -2) and its predecessor (-3)
        prev_candle = df_m2.iloc[-3]
        cur_candle = df_m2.iloc[-2]

        p_open = float(prev_candle["open"])
        p_close = float(prev_candle["close"])
        c_open = float(cur_candle["open"])
        c_close = float(cur_candle["close"])
        c_time = str(cur_candle["time"])

        # Bullish Engulfing
        if sweep.direction == "BULLISH":
            prev_is_bearish = p_close < p_open
            cur_is_bullish = c_close > c_open
            body_engulfs = (c_open <= p_close + self.tolerance) and (c_close >= p_open - self.tolerance)

            if prev_is_bearish and cur_is_bullish and body_engulfs:
                return ConfirmationEvent(
                    direction="BULLISH",
                    confirmed=True,
                    time=c_time,
                    entry_signal_price=round(c_close, 2),
                    bars_elapsed=1
                )

        # Bearish Engulfing
        elif sweep.direction == "BEARISH":
            prev_is_bullish = p_close > p_open
            cur_is_bearish = c_close < c_open
            body_engulfs = (c_open >= p_close - self.tolerance) and (c_close <= p_open + self.tolerance)

            if prev_is_bullish and cur_is_bearish and body_engulfs:
                return ConfirmationEvent(
                    direction="BEARISH",
                    confirmed=True,
                    time=c_time,
                    entry_signal_price=round(c_close, 2),
                    bars_elapsed=1
                )

        return None
