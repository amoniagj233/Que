import os
import sys
import unittest
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from CRT_GOLD_PRO.python_bot.candle_detector import CandleRangeDetector, CRTRange
from CRT_GOLD_PRO.python_bot.liquidity_sweep import LiquiditySweepDetector, SweepEvent
from CRT_GOLD_PRO.python_bot.engulfing_confirmation import EngulfingConfirmationDetector, ConfirmationEvent
from CRT_GOLD_PRO.python_bot.indicator_bridge import bridge


class TestCRTGoldPro(unittest.TestCase):
    def setUp(self):
        self.range_detector = CandleRangeDetector()
        self.sweep_detector = LiquiditySweepDetector(tick_size=0.01)
        self.confirm_detector = EngulfingConfirmationDetector(max_bars=3)

    def test_m30_range_detection(self):
        # Create synthetic M30 bars
        dates = pd.date_range("2026-06-01 08:00", periods=5, freq="30min")
        df_m30 = pd.DataFrame({
            "time": dates,
            "open": [3355.0, 3352.0, 3354.0, 3350.0, 3360.0],
            "high": [3365.0, 3360.0, 3362.0, 3370.0, 3375.0],
            "low": [3350.0, 3348.0, 3350.0, 3350.0, 3358.0],
            "close": [3360.0, 3358.0, 3351.0, 3365.0, 3372.0],
            "tick_volume": [500, 600, 700, 800, 900]
        })

        rng = self.range_detector.update(df_m30)
        self.assertIsNotNone(rng)
        # Completed candle at index -2 has high=3370, low=3350
        self.assertEqual(rng.high, 3370.0)
        self.assertEqual(rng.low, 3350.0)
        self.assertEqual(rng.midpoint, 3360.0)
        self.assertEqual(rng.range_size, 20.0)

    def test_bullish_sweep_detection(self):
        crt_range = CRTRange(
            id="M30_TEST", time_open="2026-06-01 09:30", time_close="2026-06-01 10:00",
            open=3355.0, high=3370.0, low=3350.0, close=3365.0, midpoint=3360.0, range_size=20.0, atr=15.0
        )

        dates = pd.date_range("2026-06-01 10:00", periods=5, freq="5min")
        # Completed M5 candle at index -2 sweeps below 3350 to 3346.50, then closes back inside at 3353.00
        df_m5 = pd.DataFrame({
            "time": dates,
            "open": [3365.0, 3360.0, 3355.0, 3352.0, 3354.0],
            "high": [3368.0, 3362.0, 3358.0, 3355.0, 3356.0],
            "low": [3362.0, 3354.0, 3351.0, 3346.50, 3353.0],
            "close": [3366.0, 3356.0, 3352.0, 3353.00, 3355.0],
            "tick_volume": [200, 250, 300, 650, 400]
        })

        sweep = self.sweep_detector.check_sweep(df_m5, crt_range)
        self.assertIsNotNone(sweep)
        self.assertEqual(sweep.direction, "BULLISH")
        self.assertEqual(sweep.sweep_price, 3346.50)
        self.assertEqual(sweep.reclaim_close, 3353.00)

    def test_bullish_engulfing_confirmation(self):
        sweep = SweepEvent(
            direction="BULLISH", sweep_price=3346.50, reclaim_close=3353.00,
            time="2026-06-01 10:20", atr_m5=2.0, min_sweep=0.20, candle_index=3
        )

        dates = pd.date_range("2026-06-01 10:20", periods=4, freq="2min")
        # Index -3 is bearish candle (open=3354.0, close=3352.0)
        # Index -2 is bullish engulfing candle (open=3351.8, close=3355.5)
        df_m2 = pd.DataFrame({
            "time": dates,
            "open": [3353.0, 3354.0, 3351.8, 3356.0],
            "high": [3355.0, 3354.5, 3356.0, 3358.0],
            "low": [3352.0, 3351.5, 3351.5, 3355.0],
            "close": [3354.0, 3352.0, 3355.5, 3357.0],
            "tick_volume": [100, 150, 450, 200]
        })

        confirm = self.confirm_detector.check_confirmation(df_m2, sweep)
        self.assertIsNotNone(confirm)
        self.assertTrue(confirm.confirmed)
        self.assertEqual(confirm.direction, "BULLISH")
        self.assertEqual(confirm.entry_signal_price, 3355.5)

    def test_indicator_bridge_serialization(self):
        payload = {
            "version": "1.0.0",
            "bot_name": "CRT GOLD PRO",
            "magic": 9090,
            "symbol": "XAUUSD",
            "timestamp_utc": "2026-11-02 01:20:00 UTC",
            "state": "SWEEP_CONFIRMED",
            "bot_status": "RUNNING",
            "crt_range": {"high": 3370.0, "low": 3350.0, "midpoint": 3360.0},
            "sweep": {"confirmed": True, "direction": "BULLISH", "sweep_price": 3346.50}
        }
        ok = bridge.publish_state(payload)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
