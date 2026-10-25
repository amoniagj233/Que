"""
test_ml_trading_system.py
=========================
Comprehensive unit and integration test suite for the Machine Learning Trading Intelligence System.
"""

import os
import unittest
import numpy as np
import pandas as pd

from ml_trading_engine import (
    extract_features,
    generate_labels,
    detect_market_regime,
    analyze_multi_timeframe,
    evaluate_all_strategies,
    generate_ai_trade_recommendations,
    run_ml_backtest,
    evaluate_risk_gate,
    get_model_drift_analysis,
    load_ml_settings,
    save_ml_settings,
    MLTradingModel,
    FEATURE_NAMES,
    REGIMES,
    CACHE_DIR
)


class TestMLTradingSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load cached XAUUSD M15 data or generate synthetic
        m15_path = os.path.join(CACHE_DIR, "XAUUSD_M15_5000.csv")
        h1_path = os.path.join(CACHE_DIR, "XAUUSD_H1_5000.csv")
        if os.path.exists(m15_path):
            cls.df_m15 = pd.read_csv(m15_path)
        else:
            n = 1000
            dates = pd.date_range("2026-01-01", periods=n, freq="15min")
            cls.df_m15 = pd.DataFrame({
                "time": dates,
                "open": np.linspace(2650, 2750, n) + np.random.randn(n) * 2,
                "high": np.linspace(2652, 2753, n) + np.random.randn(n) * 2 + 3,
                "low": np.linspace(2648, 2748, n) + np.random.randn(n) * 2 - 3,
                "close": np.linspace(2650, 2751, n) + np.random.randn(n) * 2,
                "tick_volume": np.random.randint(1000, 5000, n)
            })

        if os.path.exists(h1_path):
            cls.df_h1 = pd.read_csv(h1_path)
        else:
            cls.df_h1 = None

    def test_01_feature_engineering(self):
        """Test feature extraction has all 28 features without breaking."""
        df_feat = extract_features(self.df_m15.head(500), self.df_h1)
        for feat in FEATURE_NAMES:
            self.assertIn(feat, df_feat.columns, f"Missing feature: {feat}")
        self.assertEqual(len(FEATURE_NAMES), 28)
        self.assertFalse(df_feat[FEATURE_NAMES].iloc[100:].isna().all().any())

    def test_02_zero_lookahead_labeling(self):
        """Test chronological labeling engine."""
        df_feat = extract_features(self.df_m15.head(400))
        labeled = generate_labels(df_feat, horizon_bars=12, tp_mult=1.5, sl_mult=1.0)
        self.assertIn('target', labeled.columns)
        self.assertIn('realized_r', labeled.columns)
        self.assertIn('bars_held', labeled.columns)
        # Check target values are 0 or 1
        unique_targets = set(labeled['target'].dropna().unique())
        self.assertTrue(unique_targets.issubset({0, 1}))

    def test_03_market_regime_detection(self):
        """Test 8 distinct market regimes classification."""
        regime = detect_market_regime(self.df_m15.tail(300), self.df_h1)
        self.assertIn(regime["regime_name"], REGIMES)
        self.assertIn("adx", regime)
        self.assertIn("atr_percentile", regime)
        self.assertIn("strategy_suitability", regime)
        self.assertIn("duration_bars", regime)
        self.assertIsInstance(regime["strategy_suitability"], dict)

    def test_04_multi_timeframe_matrix(self):
        """Test MTF analysis across W1 to M1."""
        df_dict = {"M15": self.df_m15.tail(200)}
        if self.df_h1 is not None:
            df_dict["H1"] = self.df_h1.tail(200)

        mtf = analyze_multi_timeframe(df_dict)
        self.assertIn("matrix", mtf)
        self.assertIn("confluence_percentage", mtf)
        self.assertIn("dominant_bias", mtf)
        self.assertIn("recommended_timeframe", mtf)
        self.assertTrue(0 <= mtf["confluence_percentage"] <= 100)
        self.assertIn(mtf["dominant_bias"], ["BULLISH", "BEARISH", "NEUTRAL"])

    def test_05_strategies_a_through_g(self):
        """Test Strategies A through G evaluators."""
        strategies = evaluate_all_strategies(self.df_m15.tail(300))
        self.assertEqual(len(strategies), 7)
        strat_codes = [s["code_letter"] for s in strategies]
        self.assertEqual(strat_codes, ["A", "B", "C", "D", "E", "F", "G"])
        for s in strategies:
            self.assertIn(s["direction"], ["BUY", "SELL", "NO TRADE"])
            self.assertTrue(s["baseline_win_rate"] > 0)
            self.assertTrue(s["ml_filtered_win_rate"] >= s["baseline_win_rate"])

    def test_06_model_training_and_calibration(self):
        """Test model training, calibration, Brier score, and ROC-AUC."""
        model = MLTradingModel(version="test_v1")
        meta = model.train(self.df_m15.head(1000), self.df_h1)
        self.assertTrue(model.is_trained)
        self.assertIn("accuracy", meta)
        self.assertIn("brier_score", meta)
        self.assertIn("roc_auc", meta)
        self.assertTrue(0.0 <= meta["brier_score"] <= 1.0)
        self.assertTrue(0.0 <= meta["accuracy"] <= 1.0)

        # Test prediction
        sample_row = extract_features(self.df_m15.tail(50))[FEATURE_NAMES].iloc[-1].values
        cls, prob, ev = model.predict(sample_row)
        self.assertIn(cls, [0, 1])
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertIsInstance(ev, float)

    def test_07_ai_trade_recommendations_24_fields(self):
        """Verify all 24 required structured fields and technical invalidations."""
        recs = generate_ai_trade_recommendations(self.df_m15.tail(400), self.df_h1)
        # Even if filters produce 0 recs for strict threshold, let's test with permissive settings
        if not recs:
            # Force generate with lower threshold
            settings = load_ml_settings()
            orig = settings["min_confidence_threshold"]
            settings["min_confidence_threshold"] = 0.50
            save_ml_settings(settings)
            recs = generate_ai_trade_recommendations(self.df_m15.tail(400), self.df_h1)
            settings["min_confidence_threshold"] = orig
            save_ml_settings(settings)

        self.assertTrue(len(recs) > 0, "Should generate at least 1 trade recommendation")
        r = recs[0]

        # Verify 24 required fields
        required_fields = [
            "symbol", "strategy_code", "strategy_name", "timeframe", "direction",
            "entry_price", "entry_zone", "stop_loss", "sl_points", "tp1", "tp2", "tp3",
            "risk_reward_ratio", "win_probability", "raw_model_score", "calibration_status",
            "expected_value_r", "market_regime", "mtf_confluence", "key_drivers",
            "primary_catalyst", "liquidity_target", "invalidation_condition", "recommended_lot_size"
        ]
        for f in required_fields:
            self.assertIn(f, r, f"Missing required 24-field attribute: {f}")

        # Check Option B smart profit chaser configuration
        self.assertIn("chaser_config", r)
        self.assertIn("Option B", r["chaser_config"]["recovery_rule"])

    def test_08_walk_forward_backtest(self):
        """Test walk-forward backtester comparing Baseline vs ML-Enhanced with spread & slippage."""
        result = run_ml_backtest(self.df_m15.head(1500), self.df_h1, min_confidence=0.55)
        self.assertIn("baseline_strategy", result)
        self.assertIn("ml_enhanced_strategy", result)
        self.assertIn("total_cost_per_trade_pts", result)
        self.assertEqual(result["total_cost_per_trade_pts"], 400)  # $3.80 spread + $0.20 slippage

        base = result["baseline_strategy"]
        ml = result["ml_enhanced_strategy"]
        self.assertIn("win_rate", base)
        self.assertIn("profit_factor", ml)
        self.assertIn("equity_curve", ml)

    def test_09_deterministic_risk_gate(self):
        """Test hard risk limits: 1 trade max, spread filter, circuit breaker."""
        setup = {"market_regime": "Strong Bullish Trend"}

        # Case A: Normal conditions
        passed, msg = evaluate_risk_gate({"balance": 10000, "equity": 10000}, setup, current_spread_pts=380, open_gold_positions_count=0)
        self.assertTrue(passed)

        # Case B: Max open trades cap reached (1 trade limit)
        passed, msg = evaluate_risk_gate({"balance": 10000, "equity": 10000}, setup, current_spread_pts=380, open_gold_positions_count=1)
        self.assertFalse(passed)
        self.assertIn("Open Gold trades", msg)

        # Case C: Excessive spread
        passed, msg = evaluate_risk_gate({"balance": 10000, "equity": 10000}, setup, current_spread_pts=500, open_gold_positions_count=0)
        self.assertFalse(passed)
        self.assertIn("spread", msg)

        # Case D: Account drawdown circuit breaker exceeded (e.g. 6% dd with 5% limit)
        passed, msg = evaluate_risk_gate({"balance": 10000, "equity": 9300}, setup, current_spread_pts=380, open_gold_positions_count=0)
        self.assertFalse(passed)
        self.assertIn("drawdown", msg)

    def test_10_model_drift_detector(self):
        """Test model drift detection logic."""
        drift = get_model_drift_analysis()
        self.assertIn("status", drift)
        self.assertIn("training_accuracy", drift)
        self.assertIn("accuracy_drift", drift)


if __name__ == "__main__":
    unittest.main()
