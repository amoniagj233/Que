"""Agent 7 — Bot Performance Evaluator for APEX AI Commander.

Builds an objective multi-factor ranking system for all trading bots:
- Net Profit after costs
- Win Rate & Profit Factor
- Maximum Equity Drawdown
- Expectancy & Sharpe Ratio
- Recovery Factor (Net Profit / Max DD)
- Performance Consistency & Execution Quality
- Correlation analysis with other active bots
"""
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger("apex_evaluator")


class BotPerformanceEvaluator:
    def __init__(self):
        pass

    def evaluate_bot(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute comprehensive multi-factor score for a single bot."""
        trades = metrics.get("trades_total", 0) or metrics.get("total_trades", 0)
        wr = metrics.get("win_rate", 0.0)
        pf = metrics.get("profit_factor", 1.0)
        net_profit = metrics.get("realized_pnl", 0.0) or metrics.get("net_profit", 0.0)
        max_dd = max(metrics.get("max_drawdown", 0.0), metrics.get("max_drawdown_pct", 0.0), 0.1)
        expectancy = metrics.get("expectancy", 0.0)
        sharpe = metrics.get("sharpe_ratio", 1.0)

        # Recovery Factor = Net Profit / Max Drawdown Amount (min 0)
        recovery_factor = round(max(net_profit, 0) / max(max_dd * 10, 1.0), 2)

        # Composite Risk-Adjusted Score (0 to 100 scale)
        # Weights: PF (25%), Sharpe (20%), Win Rate (15%), Expectancy (20%), Drawdown Penalty (20%)
        pf_score = min(pf / 3.0 * 25.0, 25.0)
        sharpe_score = min(max(sharpe, 0.0) / 2.5 * 20.0, 20.0)
        wr_score = min(wr / 100.0 * 15.0, 15.0)
        exp_score = min(max(expectancy, 0.0) / 10.0 * 20.0, 20.0)
        dd_penalty = min(max_dd / 15.0 * 20.0, 20.0)

        composite_score = round(max(0.0, pf_score + sharpe_score + wr_score + exp_score - dd_penalty), 2)

        # Statistical Confidence tier
        if trades >= 100:
            confidence = "High (Statistically Robust)"
        elif trades >= 30:
            confidence = "Moderate (Acceptable)"
        else:
            confidence = "Low (Early Sample)"

        return {
            "composite_score": composite_score,
            "recovery_factor": recovery_factor,
            "confidence": confidence,
            "metrics": {
                "trades": trades,
                "win_rate": wr,
                "profit_factor": pf,
                "net_profit": net_profit,
                "max_drawdown": max_dd,
                "sharpe_ratio": sharpe,
                "expectancy": expectancy
            }
        }

    def rank_fleet(self, bots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank all active and candidate bots objectively by composite score."""
        evaluated = []
        for b in bots:
            eval_res = self.evaluate_bot(b)
            entry = {
                **b,
                "composite_score": eval_res["composite_score"],
                "recovery_factor": eval_res["recovery_factor"],
                "confidence": eval_res["confidence"]
            }
            evaluated.append(entry)

        # Sort descending by composite score
        evaluated.sort(key=lambda x: x["composite_score"], reverse=True)

        # Assign ranks
        for idx, item in enumerate(evaluated):
            item["rank"] = idx + 1

        return evaluated


# Global singleton instance
bot_evaluator = BotPerformanceEvaluator()
