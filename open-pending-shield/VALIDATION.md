# Validation — 22 October 2026

## Completed

- MetaEditor x64 build 6255 compilation: **0 errors, 0 warnings**. See `compile.log`.
- Actual MT5 Strategy Tester execution run on **XAUUSDc / M1, 22–23 June 2026**, generated ticks (`Model=0`), USD 1,000 simulated deposit, leverage 1:100. Local agent only; cloud and remote testing disabled.
- Journal checks passed for **339 pending submissions with nonzero SL/TP on the correct side**, **804 monotone trailing updates**, and **168 pending cancellations**. Stop/TP executions were observed. There was no execution halt in the completed run.
- Disabled-input test passed: `EnableTrading=false` produced **zero submissions** over the same historical interval.
- Daily-loss test passed: after the daily loss latch fired, **zero new pending submissions** occurred for the remainder of the broker day.
- Read-only Python journal audits and JSON summaries are included. Run `python audit_simulation.py` and `python audit_guards.py` to recheck the archived evidence. These scripts do not connect to a trading account or send orders.

## Results and interpretation

The execution smoke test reported **161 closed trades**, **USD +0.33 net**, **1.70 profit factor**, and **USD 0.07 (0.01%) maximum equity drawdown**. This broker's cent-symbol contract size is different from standard Gold contracts. The report's history quality is **n/a**; this was a generated-tick execution test, not a real-tick strategy evaluation. Reported transaction costs were zero. These figures establish neither a predictive edge nor expected live results.

Test overrides are explicit in `tester-smoke.ini`: `EnableTrading=true` and `MaxSpreadEntryRatio=1.0` (source default 0.25). The wider ratio deliberately exercises order handling on this broker's historical spread. It is not a recommendation to relax live spread limits. Other strategy inputs retained source defaults.

The daily-loss test deliberately uses `Lots=1.0` and `DailyEquityLossPercent=0.0001` to force a measurable loss breach in the simulator. Those are **test-only overrides**, not proposed live settings. The disabled test uses `EnableTrading=false`. Simulated currency USD avoids an unavailable USD/USC conversion history series; the early cent-currency attempt could not validate execution. `test-initial-no-trades.htm` is retained only as an initial diagnostic, not as validation of the final build.

During development, tests found that market-closed and frozen-stop responses unnecessarily halted future trading. The final build checks broker sessions and treats explicit session/quote/freeze rejections separately from uncertain execution results. The completed execution run and guard tests used the final compiled binary; see SHA-256 identifiers in `test-execution.json`.

## Limits of verification

No live chart attachment, live order, account risk-setting change or existing Tradivo modification was performed. No claim of an exact Tradivo clone is made.

ATR mode, persistent state across a terminal crash, disconnected execution, netting-account interference, duplicate-instance locking under concurrent startup, and broker-specific rejection paths were reviewed in source but were not exhaustively exercised by these historical runs. Client-side OCO can fill both legs before cancellation; gaps, fees and slippage can exceed calculated risk. Broker-side expiration is a safety timeout, not an EA license expiry. Review the README before demo use.

No profitability optimization or out-of-sample validation was performed. The original strategy needs longer real-tick tests, realistic costs and demo forward observation before any live-use decision.
