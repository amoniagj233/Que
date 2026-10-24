# OpenPendingShield 1.10: M1 / M5 real-tick backtests

No profitable preset is recommended from this search.

The best training candidate lost **USD 8.13** in training and returned **USD +3.39** in validation: **USD -4.74** across the two independent periods. Validation has only 27 trades; it is not enough to establish a durable edge.

Training: **5–9 October 2026** (exclusive end 10 October). Separate validation: **12–16 October 2026** (exclusive end 17 October). Eight parameter combinations, including defaults; winner selected by training net profit before viewing validation. No losses, stops or stored account state were changed in the live terminal.

All runs: isolated MT5 Strategy Tester, XAUUSDc, **100% real ticks**, simulated USD 1,000 deposit, leverage 1:100. Fixed **1.00 lot on the cent contract (size 1)** matches the Gold-price exposure of **0.01 lot on a standard contract (size 100)**. It does not mean 1.00 standard Gold lot. The account inspected earlier had standard contract size 100. Source defaults were retained except this explicit contract normalization and candidate parameters. Combined SL-risk cap 1% and daily equity-loss guard 5% stayed active.

## Separate-week M1 and M5 results

Win rate below means strictly positive net P/L divided by all closed trades; break-even trades remain in the denominator. In these reports MT5 included zero-profit exits in its Profit Trades count. The CSV preserves both percentages so they can be reconciled.

| Settings | Chart | Trades | Wins | Win rate | Net USD | Profit factor | Max equity DD |
|---|---|---:|---:|---:|---:|---:|---:|
| Current defaults | M1 | 434 | 146 | 33.64% | -207.20 | 0.33 | 20.72% |
| Training winner | M1 | 27 | 12 | 44.44% | +3.39 | 1.07 | 1.00% |
| Current defaults | M5 | 434 | 146 | 33.64% | -207.20 | 0.33 | 20.72% |
| Training winner | M5 | 27 | 12 | 44.44% | +3.39 | 1.07 | 1.00% |

Exact trade-by-trade M1/M5 equality: defaults **True**, candidate **True**. ATR is disabled and the code uses ticks, timers and price distances, with no chart-timeframe signal filter. M1 and M5 are chart displays for this strategy, not independent strategies. Their duplicate tests must not be pooled to pretend the sample size doubled.

Candidate win-rate 95% Wilson interval on the separate week: **27.6%–62.7%**. This interval describes sampling uncertainty only; it does not account for changing markets or repeated parameter searches.

## Training comparison

| Candidate | Trades | Win rate | Net USD | PF | Max equity DD |
|---|---:|---:|---:|---:|---:|
| train_broad | 32 | 46.88% | -8.13 | 0.86 | 2.01% |
| train_broadest | 29 | 48.28% | -10.01 | 0.85 | 3.29% |
| train_patient | 100 | 46.00% | -14.09 | 0.85 | 2.33% |
| train_wide | 131 | 51.15% | -31.25 | 0.78 | 3.68% |
| train_fixed_rr | 219 | 28.31% | -97.45 | 0.72 | 11.72% |
| train_balanced | 414 | 45.41% | -188.47 | 0.51 | 19.36% |
| train_reward | 385 | 26.49% | -207.67 | 0.40 | 21.01% |
| pilot_real | 436 | 31.65% | -225.50 | 0.29 | 22.67% |

Selected candidate: **train_broad**. Selection excluded tests with halts, incomplete reports or fewer than 30 trades. A high win rate alone was not the selection rule.

## Best tested parameters (research, not a live recommendation)

| Parameter | Value |
|---|---:|
| EntryDistance | 3.0 |
| StopDistance | 3.0 |
| TakeProfitDistance | 6.0 |
| TrailStart | 3.0 |
| TrailDistance | 1.5 |
| RepriceSeconds | 5 |
| EntryCooldownSeconds | 60 |
| MaxSpreadEntryRatio | 0.25 |
| AutoAdjustEntryDistance | true |
| UseATR | false |
| MaxCombinedRiskPercent | 1.0 |
| DailyEquityLossPercent | 5.0 |

Price distances are quote-price units. Entry distance can grow to satisfy the spread ratio, up to the existing 5.0 cap. The research presets deliberately have `EnableTrading=false`; they do not replace your installed working EA or authorize a live account change.

## Costs and limitations

Historical bid/ask spreads were included. Reported commission was zero; swaps, when present, are included in the reports and deal reconciliation. No realistic latency or extra slippage was imposed. The table below subtracts hypothetical extra costs from the candidate validation net; it is arithmetic sensitivity, not a new execution simulation.

| Hypothetical extra round-trip cost per trade at normalized exposure | Candidate validation net USD |
|---|---:|
| None beyond report | +3.39 |
| USD 0.07 commission | +1.50 |
| USD 0.07 commission + USD 0.20 adverse slippage | -3.90 |

This is ten trading days across two periods on one broker feed, not an exhaustive optimization or proof of future profitability. Contract normalization matches price exposure but cannot make different brokers’ spreads, fill rules, commissions and latency identical. Client-side opposite-order cancellation can still double-fill in live conditions.

The earlier June one-day generated-tick test checked execution. It did not establish profitability; the real-tick results here replace it as the relevant strategy evidence.

## Files and trading times

`all-results.csv`: every run and its settings. `validation-every-trade.csv`: each validation entry/exit timestamp, side, profit and win/loss. Times are **MT5 broker/server time**, not converted to Accra time because historical timezone offsets were not independently verified. `entry-hours-exploratory.csv` groups M1 entries by hour; it is descriptive only and no hour filter was fitted or enabled. M5 trades are the same underlying sample when equality is true.

Individual `.htm` reports, `.ini` inputs and tester journals are retained. Binary SHA-256: `3228131c2c0644562252ba6b8d437fe406cc0402c86073b57969f858a2e8f1d5`. Every closed trade was matched to an entry and totals were reconciled to MT5 net profit.

Method references: [MT5 Strategy Testing](https://www.metatrader5.com/en/terminal/help/algotrading/testing), [MT5 execution and spread simulation](https://www.metatrader5.com/en/terminal/help/algotrading/testing_features).
