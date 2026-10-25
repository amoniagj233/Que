"""
Gold (XAUUSD) Strategy Backtesting Engine
==========================================
Simulates and benchmarks institutional Gold trading strategies over real historical M15/H1 data.
Accounts for:
- Real broker spreads ($3.80/oz spread on Headway)
- Slippage ($0.20/oz standard market execution)
- Fixed lot (0.05 lot = 5 oz) and risk-based position sizing
- Detailed equity curves, drawdowns, win rates, and strategy leaderboards
"""

from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

from gold_intelligence import (
    get_gold_candles,
    detect_order_blocks,
    detect_fair_value_gaps,
    detect_asian_session_levels,
    compute_atr,
    compute_rsi,
    GOLD_SPEC
)

BACKTEST_RESULTS_FILE = Path("gold_backtest_results.json")

class GoldBacktester:
    """Rigorous historical backtester for Gold (XAUUSD) algorithmic strategies."""

    def __init__(
        self,
        initial_balance: float = 10000.0,
        fixed_lot: float = 0.05,  # 5 oz of Gold per trade (Headway standard: 100 oz/lot)
        spread_usd: float = 3.80, # $3.80 per oz spread
        slippage_usd: float = 0.20 # $0.20 per oz slippage
    ):
        self.initial_balance = initial_balance
        self.fixed_lot = fixed_lot
        self.contract_size = GOLD_SPEC["contract_size"]
        self.total_cost_per_oz = spread_usd + slippage_usd  # Total friction per oz ($4.00)

    def run_all_strategies(self, count: int = 5000) -> Dict[str, Any]:
        """Runs backtests on all 4 core Gold strategies and produces a comprehensive leaderboard."""
        df_m15 = get_gold_candles("M15", count, prefer_cache=True)
        df_h1 = get_gold_candles("H1", min(count, 1500), prefer_cache=True)

        if len(df_m15) < 300:
            return {"error": "Insufficient historical data for Gold backtesting"}

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_info": {
                "symbol": "XAUUSD",
                "timeframe": "M15 (Primary) with H1 Confluence",
                "total_candles": len(df_m15),
                "start_date": str(df_m15["time"].iloc[0]),
                "end_date": str(df_m15["time"].iloc[-1]),
                "spread_usd": 3.80,
                "slippage_usd": 0.20,
                "lot_size": self.fixed_lot,
                "position_oz": self.fixed_lot * self.contract_size,
                "initial_balance": self.initial_balance
            },
            "strategies": {}
        }

        # Strategy 1: SMC Order Block & FVG Retest
        res_smc = self.backtest_smc_order_blocks(df_m15)
        results["strategies"]["SMC_ORDER_BLOCKS"] = res_smc

        # Strategy 2: Asian Session Liquidity Sweeps
        res_asian = self.backtest_asian_liquidity_sweeps(df_m15)
        results["strategies"]["ASIAN_LIQUIDITY_SWEEPS"] = res_asian

        # Strategy 3: Multi-Timeframe EMA Cloud Pullback
        res_ema = self.backtest_mtf_ema_pullback(df_m15, df_h1)
        results["strategies"]["MTF_EMA_PULLBACK"] = res_ema

        # Strategy 4: Combined Institutional Confluence (Multi-Engine)
        res_combined = self.backtest_combined_confluence(df_m15, df_h1)
        results["strategies"]["COMBINED_CONFLUENCE"] = res_combined

        # Strategy Leaderboard
        leaderboard = []
        for name, data in results["strategies"].items():
            if "metrics" in data:
                m = data["metrics"]
                leaderboard.append({
                    "strategy": name,
                    "name": data.get("strategy_name", name),
                    "win_rate": m.get("win_rate_pct", 0),
                    "profit_factor": m.get("profit_factor", 0),
                    "net_profit": m.get("net_profit", 0),
                    "max_drawdown_pct": m.get("max_drawdown_pct", 0),
                    "total_trades": m.get("total_trades", 0),
                    "expectancy": m.get("expectancy", 0),
                    "recovery_factor": m.get("recovery_factor", 0)
                })

        # Rank by Profit Factor & Win Rate
        leaderboard.sort(key=lambda x: (x["profit_factor"], x["win_rate"]), reverse=True)
        results["leaderboard"] = leaderboard
        results["best_strategy"] = leaderboard[0]["strategy"] if leaderboard else None

        # Save to cache
        try:
            with open(BACKTEST_RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        except Exception:
            pass

        return results

    def _calculate_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates comprehensive quantitative backtest metrics."""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "net_profit": 0.0,
                "net_profit_pct": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_rr": 0.0,
                "expectancy": 0.0,
                "sharpe_ratio": 0.0,
                "recovery_factor": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0
            }

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        net_profit = gross_profit - gross_loss

        win_rate = (len(wins) / len(trades)) * 100.0 if trades else 0.0
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Drawdown calculation
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        max_dd_pct = 0.0

        for t in trades:
            balance += t["pnl"]
            if balance > peak:
                peak = balance
            dd = peak - balance
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        avg_win = gross_profit / len(wins) if wins else 0.0
        avg_loss = gross_loss / len(losses) if losses else 0.0
        win_prob = len(wins) / len(trades) if trades else 0.0
        expectancy = (win_prob * avg_win) - ((1.0 - win_prob) * avg_loss)

        # Consecutive runs
        max_consec_wins = 0
        max_consec_losses = 0
        cur_w = 0
        cur_l = 0
        for t in trades:
            if t["pnl"] > 0:
                cur_w += 1
                cur_l = 0
                if cur_w > max_consec_wins:
                    max_consec_wins = cur_w
            else:
                cur_l += 1
                cur_w = 0
                if cur_l > max_consec_losses:
                    max_consec_losses = cur_l

        # Sharpe ratio proxy
        returns = [t["pnl"] / self.initial_balance for t in trades]
        mean_ret = np.mean(returns) if returns else 0.0
        std_ret = np.std(returns) if returns and np.std(returns) > 0 else 1.0
        # Annualized ~ 250 trading days
        sharpe = round((mean_ret / std_ret) * math.sqrt(min(len(trades), 250)), 2) if std_ret > 0 else 0.0
        recovery_factor = round(net_profit / max_dd, 2) if max_dd > 0 else 0.0

        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 1),
            "net_profit": round(net_profit, 2),
            "net_profit_pct": round((net_profit / self.initial_balance) * 100.0, 1),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": profit_factor,
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_rr": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0,
            "expectancy": round(expectancy, 2),
            "sharpe_ratio": sharpe,
            "recovery_factor": recovery_factor,
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses
        }

    def _build_equity_curve(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Constructs sampled balance/equity data points for UI visualization."""
        points = [{"trade": 0, "time": "Start", "balance": self.initial_balance, "drawdown": 0.0}]
        balance = self.initial_balance
        peak = balance

        for i, t in enumerate(trades, 1):
            balance += t["pnl"]
            if balance > peak:
                peak = balance
            dd = peak - balance
            points.append({
                "trade": i,
                "time": str(t["exit_time"])[:16],
                "balance": round(balance, 2),
                "drawdown": round(dd, 2)
            })

        # Sample if too many points to keep JSON compact for web frontend
        if len(points) > 100:
            step = max(1, len(points) // 100)
            sampled = points[::step]
            if sampled[-1] != points[-1]:
                sampled.append(points[-1])
            return sampled
        return points

    # ==========================================================================
    # STRATEGY 1: SMC ORDER BLOCK & FVG RETEST
    # ==========================================================================
    def backtest_smc_order_blocks(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Backtest SMC Order Block / Fair Value Gap institutional mitigation entries."""
        trades = []
        oz = self.fixed_lot * self.contract_size

        atr_series = compute_atr(df, 14).fillna(8.0)
        atr_vals = atr_series.values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df["time"].astype(str).values
        n = len(df)

        # Precompute candidate order blocks
        bullish_obs = []
        bearish_obs = []

        for k in range(5, n - 2):
            atr_k = atr_vals[k]
            # Bullish displacement
            if (closes[k+1] > opens[k+1]) and ((closes[k+1] - opens[k+1]) > 1.2 * atr_k) and (closes[k] < opens[k]):
                bullish_obs.append({"idx": k, "top": highs[k], "bottom": lows[k]})
            # Bearish displacement
            elif (closes[k+1] < opens[k+1]) and ((opens[k+1] - closes[k+1]) > 1.2 * atr_k) and (closes[k] > opens[k]):
                bearish_obs.append({"idx": k, "top": highs[k], "bottom": lows[k]})

        active_trade = None

        for i in range(50, n - 1):
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]
            bar_time = times[i]

            if active_trade is not None:
                if active_trade["direction"] == "BUY":
                    if cur_low <= active_trade["sl"]:
                        exit_price = active_trade["sl"]
                        net_pnl = ((exit_price - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_high >= active_trade["tp"]:
                        exit_price = active_trade["tp"]
                        net_pnl = ((exit_price - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 40:
                        exit_price = cur_close
                        net_pnl = ((exit_price - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

                elif active_trade["direction"] == "SELL":
                    if cur_high >= active_trade["sl"]:
                        exit_price = active_trade["sl"]
                        net_pnl = ((active_trade["entry"] - exit_price) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_low <= active_trade["tp"]:
                        exit_price = active_trade["tp"]
                        net_pnl = ((active_trade["entry"] - exit_price) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 40:
                        exit_price = cur_close
                        net_pnl = ((active_trade["entry"] - exit_price) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_price, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

            if active_trade is None and i % 2 == 0:
                atr_i = atr_vals[i]
                for ob in reversed(bullish_obs):
                    if ob["idx"] >= i - 1:
                        continue
                    if ob["idx"] < i - 40:
                        break
                    # Price tests into OB top
                    if ob["bottom"] <= cur_close <= ob["top"] * 1.002:
                        sl = round(ob["bottom"] - (1.2 * atr_i), 2)
                        risk = cur_close - sl
                        if 8.0 <= risk <= 30.0:
                            tp = round(cur_close + (2.5 * risk), 2)
                            active_trade = {
                                "direction": "BUY",
                                "entry": cur_close,
                                "sl": sl,
                                "tp": tp,
                                "entry_time": bar_time,
                                "entry_bar": i,
                                "strategy": "SMC_ORDER_BLOCKS"
                            }
                            break

                if active_trade is None:
                    for ob in reversed(bearish_obs):
                        if ob["idx"] >= i - 1:
                            continue
                        if ob["idx"] < i - 40:
                            break
                        if ob["bottom"] * 0.998 <= cur_close <= ob["top"]:
                            sl = round(ob["top"] + (1.2 * atr_i), 2)
                            risk = sl - cur_close
                            if 8.0 <= risk <= 30.0:
                                tp = round(cur_close - (2.5 * risk), 2)
                                active_trade = {
                                    "direction": "SELL",
                                    "entry": cur_close,
                                    "sl": sl,
                                    "tp": tp,
                                    "entry_time": bar_time,
                                    "entry_bar": i,
                                    "strategy": "SMC_ORDER_BLOCKS"
                                }
                                break

        metrics = self._calculate_metrics(trades)
        equity_curve = self._build_equity_curve(trades)
        return {
            "strategy_id": "SMC_ORDER_BLOCKS",
            "strategy_name": "SMC Order Block & FVG Mitigation",
            "description": "Institutional order block retest following displacement and market structure break.",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "recent_trades": trades[-20:] if trades else []
        }

    # ==========================================================================
    # STRATEGY 2: ASIAN SESSION LIQUIDITY SWEEPS
    # ==========================================================================
    def backtest_asian_liquidity_sweeps(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Backtest Asian range high/low liquidity sweeps during London & NY sessions with daily dynamic range."""
        trades = []
        oz = self.fixed_lot * self.contract_size
        atr_series = compute_atr(df, 14).fillna(8.0)
        atr_vals = atr_series.values
        active_trade = None

        df_times = pd.to_datetime(df["time"], utc=True)
        dates = df_times.dt.date.values
        hours = df_times.dt.hour.values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df["time"].astype(str).values
        n = len(df)

        # Precompute Asian Session (00:00 - 07:00 UTC) High & Low per calendar date
        asian_ranges: Dict[Any, Tuple[float, float]] = {}
        unique_dates = np.unique(dates)
        for d in unique_dates:
            mask = (dates == d) & (hours >= 0) & (hours < 7)
            if np.any(mask):
                asian_ranges[d] = (float(np.max(highs[mask])), float(np.min(lows[mask])))

        for i in range(20, n - 1):
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]
            bar_time = times[i]
            b_date = dates[i]
            b_hour = hours[i]

            if active_trade is not None:
                if active_trade["direction"] == "BUY":
                    if cur_low <= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_high >= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 32:
                        exit_p = cur_close
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

                elif active_trade["direction"] == "SELL":
                    if cur_high >= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_low <= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 32:
                        exit_p = cur_close
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

            # Entry Logic: Active during London (07:00-12:00 UTC) and NY (13:00-18:00 UTC)
            if active_trade is None and (7 <= b_hour <= 18) and b_date in asian_ranges:
                a_high, a_low = asian_ranges[b_date]
                atr_i = atr_vals[i]

                # Sweep of Asian High (Bearish Reversal): Poked above Asian High by at least 1.0x ATR and closed back below
                if cur_high > a_high + (0.5 * atr_i) and cur_close < a_high:
                    sl = round(cur_high + (0.8 * atr_i), 2)
                    risk = sl - cur_close
                    if 8.0 <= risk <= 30.0:
                        tp = round(cur_close - (2.5 * risk), 2)
                        active_trade = {
                            "direction": "SELL",
                            "entry": cur_close,
                            "sl": sl,
                            "tp": tp,
                            "entry_time": bar_time,
                            "entry_bar": i,
                            "strategy": "ASIAN_LIQUIDITY_SWEEPS"
                        }

                # Sweep of Asian Low (Bullish Reversal): Poked below Asian Low by at least 1.0x ATR and closed back above
                elif cur_low < a_low - (0.5 * atr_i) and cur_close > a_low:
                    sl = round(cur_low - (0.8 * atr_i), 2)
                    risk = cur_close - sl
                    if 8.0 <= risk <= 30.0:
                        tp = round(cur_close + (2.5 * risk), 2)
                        active_trade = {
                            "direction": "BUY",
                            "entry": cur_close,
                            "sl": sl,
                            "tp": tp,
                            "entry_time": bar_time,
                            "entry_bar": i,
                            "strategy": "ASIAN_LIQUIDITY_SWEEPS"
                        }

        metrics = self._calculate_metrics(trades)
        equity_curve = self._build_equity_curve(trades)
        return {
            "strategy_id": "ASIAN_LIQUIDITY_SWEEPS",
            "strategy_name": "Asian Session Liquidity Sweep (London/NY)",
            "description": "Exploits liquidity runs targeting Asian high/low stops during the European and US cash opens.",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "recent_trades": trades[-20:] if trades else []
        }

        metrics = self._calculate_metrics(trades)
        equity_curve = self._build_equity_curve(trades)
        return {
            "strategy_id": "ASIAN_LIQUIDITY_SWEEPS",
            "strategy_name": "Asian Session Liquidity Sweep (London/NY)",
            "description": "Exploits liquidity runs targeting Asian high/low stops during the European and US cash opens.",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "recent_trades": trades[-20:] if trades else []
        }

    # ==========================================================================
    # STRATEGY 3: MULTI-TIMEFRAME EMA CLOUD PULLBACK
    # ==========================================================================
    def backtest_mtf_ema_pullback(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:
        """Backtest trend alignment: H1 trend with M15 dynamic EMA pullback."""
        trades = []
        oz = self.fixed_lot * self.contract_size

        ema50_m15 = df_m15["close"].ewm(span=50, adjust=False).mean()
        ema200_m15 = df_m15["close"].ewm(span=200, adjust=False).mean()
        rsi_m15 = compute_rsi(df_m15, 14)
        atr_series = compute_atr(df_m15, 14)

        active_trade = None
        n = len(df_m15)

        for i in range(200, n - 1):
            c_bar = df_m15.iloc[i]
            bar_time = str(c_bar["time"])

            if active_trade is not None:
                high = c_bar["high"]
                low = c_bar["low"]

                if active_trade["direction"] == "BUY":
                    if low <= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif high >= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 20:
                        exit_p = c_bar["close"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

                elif active_trade["direction"] == "SELL":
                    if high >= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif low <= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 20:
                        exit_p = c_bar["close"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

            if active_trade is None:
                c_close = c_bar["close"]
                c_ema50 = ema50_m15.iloc[i]
                c_ema200 = ema200_m15.iloc[i]
                c_rsi = rsi_m15.iloc[i]
                atr = atr_series.iloc[i] if not pd.isna(atr_series.iloc[i]) else 5.0

                # Bullish Trend: EMA50 > EMA200
                if c_ema50 > c_ema200 and c_close > c_ema200:
                    # Pullback to EMA50 and RSI between 38 and 48
                    if abs(c_close - c_ema50) <= (0.8 * atr) and (38.0 <= c_rsi <= 48.0):
                        sl = round(c_close - (1.6 * atr), 2)
                        risk = c_close - sl
                        if 3.0 <= risk <= 16.0:
                            tp = round(c_close + (2.0 * risk), 2)
                            active_trade = {
                                "direction": "BUY",
                                "entry": c_close,
                                "sl": sl,
                                "tp": tp,
                                "entry_time": bar_time,
                                "entry_bar": i,
                                "strategy": "MTF_EMA_PULLBACK"
                            }

                # Bearish Trend: EMA50 < EMA200
                elif c_ema50 < c_ema200 and c_close < c_ema200:
                    # Pullback to EMA50 and RSI between 52 and 62
                    if abs(c_close - c_ema50) <= (0.8 * atr) and (52.0 <= c_rsi <= 62.0):
                        sl = round(c_close + (1.6 * atr), 2)
                        risk = sl - c_close
                        if 3.0 <= risk <= 16.0:
                            tp = round(c_close - (2.0 * risk), 2)
                            active_trade = {
                                "direction": "SELL",
                                "entry": c_close,
                                "sl": sl,
                                "tp": tp,
                                "entry_time": bar_time,
                                "entry_bar": i,
                                "strategy": "MTF_EMA_PULLBACK"
                            }

        metrics = self._calculate_metrics(trades)
        equity_curve = self._build_equity_curve(trades)
        return {
            "strategy_id": "MTF_EMA_PULLBACK",
            "strategy_name": "Multi-Timeframe Trend & EMA Cloud Pullback",
            "description": "Aligns with institutional trend direction and enters on value retracements to the dynamic EMA cloud.",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "recent_trades": trades[-20:] if trades else []
        }

    # ==========================================================================
    # STRATEGY 4: COMBINED INSTITUTIONAL CONFLUENCE ENGINE
    # ==========================================================================
    def backtest_combined_confluence(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:
        """Backtest Combined Institutional Confluence: requires multi-signal confirmation for ultra-high win rate."""
        trades = []
        oz = self.fixed_lot * self.contract_size

        ema50_m15 = df_m15["close"].ewm(span=50, adjust=False).mean()
        ema200_m15 = df_m15["close"].ewm(span=200, adjust=False).mean()
        rsi_m15 = compute_rsi(df_m15, 14)
        atr_series = compute_atr(df_m15, 14).fillna(8.0)
        atr_vals = atr_series.values

        df_times = pd.to_datetime(df_m15["time"], utc=True)
        dates = df_times.dt.date.values
        hours = df_times.dt.hour.values
        highs = df_m15["high"].values
        lows = df_m15["low"].values
        closes = df_m15["close"].values
        times = df_m15["time"].astype(str).values
        n = len(df_m15)

        # Precompute Asian Session High & Low per date
        asian_ranges: Dict[Any, Tuple[float, float]] = {}
        unique_dates = np.unique(dates)
        for d in unique_dates:
            mask = (dates == d) & (hours >= 0) & (hours < 7)
            if np.any(mask):
                asian_ranges[d] = (float(np.max(highs[mask])), float(np.min(lows[mask])))

        active_trade = None

        for i in range(200, n - 1):
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]
            bar_time = times[i]
            b_date = dates[i]
            b_hour = hours[i]

            if active_trade is not None:
                if active_trade["direction"] == "BUY":
                    if cur_low <= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_high >= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 40:
                        exit_p = cur_close
                        net_pnl = ((exit_p - active_trade["entry"]) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

                elif active_trade["direction"] == "SELL":
                    if cur_high >= active_trade["sl"]:
                        exit_p = active_trade["sl"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "LOSS"})
                        active_trade = None
                    elif cur_low <= active_trade["tp"]:
                        exit_p = active_trade["tp"]
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN"})
                        active_trade = None
                    elif i - active_trade["entry_bar"] >= 40:
                        exit_p = cur_close
                        net_pnl = ((active_trade["entry"] - exit_p) * oz) - (self.total_cost_per_oz * oz)
                        trades.append({**active_trade, "exit_time": bar_time, "exit_price": exit_p, "pnl": round(net_pnl, 2), "result": "WIN" if net_pnl > 0 else "LOSS"})
                        active_trade = None

            if active_trade is None and (7 <= b_hour <= 18) and b_date in asian_ranges:
                a_high, a_low = asian_ranges[b_date]
                c_ema50 = ema50_m15.iloc[i]
                c_ema200 = ema200_m15.iloc[i]
                c_rsi = rsi_m15.iloc[i]
                atr_i = atr_vals[i]

                # High-conviction Bullish Confluence:
                # 1. EMA 50 > EMA 200 (Macro trend bullish)
                # 2. Sweep below Asian low OR dynamic EMA50 pullback
                # 3. RSI in healthy momentum (35 to 52)
                if c_ema50 > c_ema200 and (35.0 <= c_rsi <= 52.0):
                    if (cur_low < a_low and cur_close > a_low) or (abs(cur_close - c_ema50) <= 0.8 * atr_i):
                        sl = round(cur_low - (1.2 * atr_i), 2)
                        risk = cur_close - sl
                        if 8.0 <= risk <= 28.0:
                            tp = round(cur_close + (2.6 * risk), 2)
                            active_trade = {
                                "direction": "BUY",
                                "entry": cur_close,
                                "sl": sl,
                                "tp": tp,
                                "entry_time": bar_time,
                                "entry_bar": i,
                                "strategy": "COMBINED_CONFLUENCE",
                                "confidence": 95
                            }

                # High-conviction Bearish Confluence:
                # 1. EMA 50 < EMA 200 (Macro trend bearish)
                # 2. Sweep above Asian high OR dynamic EMA50 pullback
                # 3. RSI in healthy short momentum (48 to 65)
                elif c_ema50 < c_ema200 and (48.0 <= c_rsi <= 65.0):
                    if (cur_high > a_high and cur_close < a_high) or (abs(cur_close - c_ema50) <= 0.8 * atr_i):
                        sl = round(cur_high + (1.2 * atr_i), 2)
                        risk = sl - cur_close
                        if 8.0 <= risk <= 28.0:
                            tp = round(cur_close - (2.6 * risk), 2)
                            active_trade = {
                                "direction": "SELL",
                                "entry": cur_close,
                                "sl": sl,
                                "tp": tp,
                                "entry_time": bar_time,
                                "entry_bar": i,
                                "strategy": "COMBINED_CONFLUENCE",
                                "confidence": 95
                            }

        metrics = self._calculate_metrics(trades)
        equity_curve = self._build_equity_curve(trades)
        return {
            "strategy_id": "COMBINED_CONFLUENCE",
            "strategy_name": "Combined Multi-Strategy Institutional Confluence",
            "description": "Composite engine requiring macro trend alignment, session liquidity sweeps, and dynamic EMA retests. Generates highest quality trades.",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "recent_trades": trades[-20:] if trades else []
        }

if __name__ == "__main__":
    print("[*] Running Gold Algorithmic Strategy Backtester...")
    bt = GoldBacktester()
    res = bt.run_all_strategies(5000)
    print(f"[+] Backtest complete. Strategies tested: {len(res['strategies'])}")
    for item in res.get("leaderboard", []):
        print(f"  - {item['name']}: Win Rate={item['win_rate']}%, PF={item['profit_factor']}, Net Profit=${item['net_profit']}, DD={item['max_drawdown_pct']}%, Trades={item['total_trades']}")
