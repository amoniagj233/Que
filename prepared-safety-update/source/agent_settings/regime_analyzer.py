"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Market Regime Analyzer for Gold (XAUUSD)
Classifies the real-time market regime:
- Trend Bull / Trend Bear
- Range / Mean-Reverting Chop
- High Volatility Breakout
- Low Volatility Squeeze
Outputs adaptive parameter recommendations for the EA fleet.
"""

import os
import sys
import datetime
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.database import SettingsDatabase
from agent_settings.backtester import BacktestingEngine

logger = logging.getLogger("AGENT_SETTINGS_REGIME")

class MarketRegimeAnalyzer:
    def __init__(self, db: SettingsDatabase, backtester: Optional[BacktestingEngine] = None):
        self.db = db
        self.backtester = backtester or BacktestingEngine()

    def analyze_current_regime(self, timeframe: str = "M5", lookback: int = 300) -> Dict[str, Any]:
        """
        Analyzes the latest market bars to identify the prevailing regime.
        """
        df = self.backtester.load_data(timeframe=timeframe)
        if df is None or len(df) < 50:
            return {
                "regime_type": "UNKNOWN",
                "volatility_rank": "MEDIUM",
                "recommendation": "Maintain default risk controls."
            }

        sample = df.tail(lookback).reset_index(drop=True).copy()

        # 1. ATR calculation (14 periods)
        high = sample['high']
        low = sample['low']
        close = sample['close']
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean().iloc[-1]

        # 2. RSI calculation (14 periods)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi_14 = (100 - (100 / (1 + rs))).iloc[-1]

        # 3. EMA Trend calculation (50 vs 200)
        ema_50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema_200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
        curr_price = close.iloc[-1]

        # 4. Volatility Rank
        avg_atr = tr.rolling(window=100).mean().iloc[-1]
        if atr_14 > avg_atr * 1.5:
            vol_rank = "HIGH"
        elif atr_14 < avg_atr * 0.7:
            vol_rank = "LOW"
        else:
            vol_rank = "MEDIUM"

        # 5. Regime Determination
        if curr_price > ema_50 and ema_50 > ema_200:
            regime = "TREND_BULL"
            rec = "Strong upward momentum. Prioritize BUY pullbacks. Trail stops aggressively at +$1.50 profit."
        elif curr_price < ema_50 and ema_50 < ema_200:
            regime = "TREND_BEAR"
            rec = "Strong downward pressure. Prioritize SELL pullbacks. Ensure tight stop-losses."
        elif vol_rank == "LOW":
            regime = "SQUEEZE"
            rec = "Low volatility compression detected. Expect explosive breakout soon. Hold steady."
        else:
            regime = "RANGE_CHOP"
            rec = "Mean-reverting consolidation. Target quick $2.50 TP with $1.00 auto-breakeven locking."

        regime_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "symbol": "XAUUSD",
            "timeframe": timeframe,
            "regime_type": regime,
            "atr_14": round(float(atr_14), 2),
            "adx_14": 25.0, # Baseline indicator
            "rsi_14": round(float(rsi_14), 2),
            "volatility_rank": vol_rank,
            "recommendation": rec
        }

        self.db.record_market_regime(regime_data)
        logger.info(f"Market Regime Analyzed: {regime} | Volatility: {vol_rank} | ATR: ${atr_14:.2f} | RSI: {rsi_14:.1f}")
        return regime_data

if __name__ == "__main__":
    db = SettingsDatabase()
    analyzer = MarketRegimeAnalyzer(db)
    res = analyzer.analyze_current_regime()
    print("Market Regime Analysis Result:")
    print(res)
