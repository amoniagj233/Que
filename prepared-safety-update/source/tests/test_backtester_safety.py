import numpy as np
import pandas as pd
import pytest
import sys
from types import SimpleNamespace

from commander.backtester import BacktestingValidationAI


@pytest.mark.parametrize("direction", [1, -1])
def test_bar_touching_both_exits_counts_stop_first(direction):
    # No terminal connection/data loader involved.
    bt = BacktestingValidationAI(default_spread=0, default_commission=0, default_slippage=0)
    df = pd.DataFrame(dict(open=[100, 100, 100], high=[100, 100, 110],
                           low=[100, 100, 90], close=[100, 100, 100]))
    result = bt.run_event_driven_backtest(df, np.array([0, direction, 0]), tp_dollars=4, sl_dollars=3)
    assert result["total_trades"] == 1
    assert result["net_profit"] == -3
    assert result["ambiguous_bar_policy"] == "stop_first"


def test_synthetic_series_is_labelled():
    bt = BacktestingValidationAI()
    df = bt._generate_synthetic_gold_bars(bars=20)
    assert df.attrs["data_source"] == "synthetic"
    result = bt.run_event_driven_backtest(df, np.zeros(20))
    assert result["data_source"] == "synthetic"


def test_no_market_data_requires_explicit_synthetic_opt_in(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "MetaTrader5", SimpleNamespace(initialize=lambda: False))
    monkeypatch.setattr("commander.backtester.DATA_CACHE_DIR", str(tmp_path))
    bt = BacktestingValidationAI()
    with pytest.raises(ValueError, match="synthetic fallback is disabled"):
        bt.load_gold_data(bars=20)
    assert bt.load_gold_data(bars=20, allow_synthetic=True).attrs["data_source"] == "synthetic"


def test_window_consistency_alone_cannot_qualify_a_strategy(monkeypatch):
    bt = BacktestingValidationAI()
    monkeypatch.setattr(bt, "run_event_driven_backtest", lambda *args: {"profit_factor": 3, "win_rate": 90})
    df = pd.DataFrame({"close": list(range(12))})
    result = bt.walk_forward_validation(df, lambda chunk: np.zeros(len(chunk)))
    assert result["consistency_passed"] is True
    assert result["qualification_passed"] is False
