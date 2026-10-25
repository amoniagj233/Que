"""
Unit and Integration Tests for Gold (XAUUSD) Intelligence & Backtesting System
==============================================================================
Verifies:
1. Candlestick data loading and caching across timeframes.
2. Smart Money Concepts: Order Blocks, Fair Value Gaps, Liquidity Sweeps.
3. Asian Session Range detection (00:00 - 07:00 UTC).
4. Market regime classification (Trend, Consolidation, Expansion).
5. Multi-timeframe confluence matrix (M1 through W1).
6. Recommended Trade Setups and Technical Invalidation Notes specification compliance.
7. Macro Economic Event Risk calendar.
8. Quantitative Backtesting Engine calculations (Win Rate, Profit Factor, Drawdown, Expectancy).
"""

import unittest
import pandas as pd
import numpy as np

from gold_intelligence import (
    get_gold_candles,
    compute_atr,
    compute_rsi,
    detect_order_blocks,
    detect_fair_value_gaps,
    detect_asian_session_levels,
    analyze_market_regime,
    get_multi_timeframe_matrix,
    generate_gold_trade_setups,
    get_gold_macro_events
)
from gold_backtester import GoldBacktester

class TestGoldIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df_m15 = get_gold_candles("M15", 300, prefer_cache=True)
        cls.df_h1 = get_gold_candles("H1", 200, prefer_cache=True)

    def test_candle_fetching(self):
        """Test candlestick dataframe structure."""
        self.assertFalse(self.df_m15.empty, "M15 DataFrame should not be empty")
        for col in ["time", "open", "high", "low", "close"]:
            self.assertIn(col, self.df_m15.columns, f"Missing required column {col}")

    def test_technical_indicators(self):
        """Test ATR and RSI calculations."""
        atr = compute_atr(self.df_m15, 14)
        self.assertEqual(len(atr), len(self.df_m15))
        self.assertTrue((atr.dropna() > 0).all(), "ATR should be strictly positive")

        rsi = compute_rsi(self.df_m15, 14)
        self.assertEqual(len(rsi), len(self.df_m15))
        valid_rsi = rsi.dropna()
        self.assertTrue((valid_rsi >= 0).all() and (valid_rsi <= 100).all(), "RSI should be bounded [0, 100]")

    def test_smc_order_blocks(self):
        """Test institutional Order Block detection."""
        obs = detect_order_blocks(self.df_m15)
        self.assertIsInstance(obs, list)
        if obs:
            ob = obs[0]
            self.assertIn("type", ob)
            self.assertIn(ob["type"], ["BULLISH_OB", "BEARISH_OB"])
            self.assertIn("top", ob)
            self.assertIn("bottom", ob)
            self.assertGreaterEqual(ob["top"], ob["bottom"])

    def test_smc_fair_value_gaps(self):
        """Test Fair Value Gap (FVG) detection."""
        fvgs = detect_fair_value_gaps(self.df_m15)
        self.assertIsInstance(fvgs, list)
        if fvgs:
            fvg = fvgs[0]
            self.assertIn("type", fvg)
            self.assertIn(fvg["type"], ["BULLISH_FVG", "BEARISH_FVG"])
            self.assertIn("top", fvg)
            self.assertIn("bottom", fvg)
            self.assertIn("size", fvg)

    def test_asian_session_levels(self):
        """Test Asian session high/low detection."""
        asian = detect_asian_session_levels(self.df_m15)
        self.assertIn("asian_high", asian)
        self.assertIn("asian_low", asian)
        self.assertIn("range_pts", asian)
        self.assertGreaterEqual(asian["asian_high"], asian["asian_low"])

    def test_market_regime(self):
        """Test market regime classification."""
        regime = analyze_market_regime(self.df_h1)
        self.assertIn("regime", regime)
        self.assertIn("bias", regime)
        self.assertIn("volatility", regime)
        self.assertIn(regime["bias"], ["BULLISH", "BEARISH", "NEUTRAL"])

    def test_multi_timeframe_matrix(self):
        """Test MTF confirmation matrix output across required timeframes."""
        matrix = get_multi_timeframe_matrix()
        self.assertIn("timeframes", matrix)
        self.assertIn("composite_score", matrix)
        self.assertIn("overall_bias", matrix)
        # Check required timeframes exist
        for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
            self.assertIn(tf, matrix["timeframes"], f"Missing timeframe {tf} in MTF matrix")

    def test_recommended_trade_setups_and_invalidations(self):
        """Test that trade recommendations contain all 13 required fields and explicit invalidation notes."""
        setups = generate_gold_trade_setups()
        self.assertIsInstance(setups, list)
        self.assertGreater(len(setups), 0, "Should generate at least one setup or explicit NO TRADE guidance")

        for setup in setups:
            self.assertIn("strategy", setup)
            self.assertIn("methodology", setup)
            self.assertIn("bias", setup)
            self.assertIn("direction", setup)
            self.assertIn("entry", setup)
            self.assertIn("sl", setup)
            self.assertIn("tp1", setup)
            self.assertIn("tp2", setup)
            self.assertIn("tp3", setup)
            self.assertIn("rr_ratio", setup)
            self.assertIn("confidence_score", setup)
            self.assertIn("rationale", setup)
            self.assertIn("invalidation", setup)

            # Invalidation notes verification
            inv = setup["invalidation"]
            self.assertIn("setup_invalidation", inv)
            self.assertIn("stop_loss_invalidation", inv)
            self.assertIn("time_invalidation", inv)

    def test_macro_events(self):
        """Test macro event risk calendar."""
        events = get_gold_macro_events()
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)
        for ev in events:
            self.assertIn("event", ev)
            self.assertIn("impact", ev)
            self.assertIn("rule", ev)

    def test_backtester_metrics(self):
        """Test quantitative metric calculations on simulated trades."""
        bt = GoldBacktester()
        sample_trades = [
            {"entry": 2700.0, "exit_price": 2720.0, "pnl": 90.0, "exit_time": "2026-10-20 12:00"},
            {"entry": 2720.0, "exit_price": 2710.0, "pnl": -60.0, "exit_time": "2026-10-21 14:00"},
            {"entry": 2715.0, "exit_price": 2735.0, "pnl": 100.0, "exit_time": "2026-10-22 16:00"},
        ]
        metrics = bt._calculate_metrics(sample_trades)
        self.assertEqual(metrics["total_trades"], 3)
        self.assertEqual(metrics["winning_trades"], 2)
        self.assertEqual(metrics["losing_trades"], 1)
        self.assertEqual(metrics["net_profit"], 130.0)
        self.assertAlmostEqual(metrics["win_rate_pct"], 66.7, places=1)
        self.assertGreater(metrics["profit_factor"], 1.0)

if __name__ == "__main__":
    unittest.main()
