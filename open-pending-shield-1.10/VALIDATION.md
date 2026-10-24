# Version 1.10 validation — 22 October 2026

## Actual cause, not an inferred execution failure

The installed version 1.00 logged `trading=false` and `Disabled: EnableTrading=false` on XAUEUR,M1 at 15:25:24. Its default and delivered preset disabled execution. A read-only quote check also showed XAUEUR spread 0.36, exceeding the original default spread/entry allowance of 0.25. Version 1.10 corrects the enabled default and adapts entry distance without relaxing the spread ratio, fixed lots or loss limits.

## Completed checks

- MetaEditor compilation: **0 errors, 0 warnings** (`compile.log`).
- Broker `order_check` on the user's running terminal for XAUEUR: **both buy-stop and sell-stop requests returned 0 / Done**, with 0.01 lots, SL/TP attached, `ORDER_FILLING_RETURN`, and specified expiration. Observed spread was 0.36; calculated entry distance was 1.46. This validates requests only; **zero live orders were submitted** (`broker-preflight.json`).
- MT5 Strategy Tester, **XAUUSDc / M1, 22–23 June 2026**, generated ticks, USD 1,000 simulated deposit, leverage 1:100: completed successfully with **all strategy inputs equal to source defaults**. Unlike version 1.00's execution test, this did not widen the spread ratio. The full explicit defaults are in `tester-defaults.ini`; the audit asserts their equality to source declarations.
- Archived journal checks: **104 protected pending submissions**, **217 monotone trailing-stop updates**, **47 pending cancellations**, stop/TP execution observed, and **no execution halt**.
- Disabled-input test: explicit `EnableTrading=false` produced **zero submissions**.
- Daily-loss test: the stop latched and **zero pending submissions occurred after the daily guard status**. This deliberately used `Lots=1.0` and `DailyEquityLossPercent=0.0001` in the simulator to force a measurable breach. These are not the delivered trading defaults.

Historical execution report: **46 trades**, USD **+0.13** net, profit factor **2.00**, maximum equity drawdown USD **0.06 (0.01%)**. History quality is **n/a**, generated ticks were used, and reported transaction costs were zero. The cent-contract test symbol differs from standard XAUEUR/XAUUSD contracts. These figures test execution mechanics and do not establish strategy profitability, realistic returns or suitability for live funds.

`audit_simulation.py` and `audit_guards.py` are read-only scripts that verify the archived journal evidence; `test-execution.json` records the exact source/binary SHA-256 identifiers. Early interrupted or remembered-disabled test runs are not counted as successful execution tests. The completed run explicitly supplied every source default to avoid MT5's remembered input values.

## Boundaries

No live account orders were placed, no existing positions were closed, no broker loss settings were raised, and no stored loss baseline or execution halt was cleared. The installed live chart binary was not hot-replaced or enabled. The corrected build is delivered on Desktop for the user to install and attach deliberately.

Manual XAUUSD positions were present at the read-only account check and remain a deliberate new-entry blocker for that symbol. XAUEUR had no exposure at that check. Permission checks, risk and margin constraints can still prevent an entry; the chart now identifies those reasons.

This is independent source, not modified Tradivo code. There are no license keys, trial expiry, activation servers or broker/account whitelists. Broker-side pending-order expiration is retained for order safety. Client-side opposite-order cancellation cannot prevent every double fill. Gaps, fees and slippage can exceed estimated SL risk. ATR mode, terminal-crash recovery and every broker-specific rejection path were not exhaustively tested. Longer real-tick tests with realistic costs and demo forward observation remain necessary for evaluating the strategy itself.
