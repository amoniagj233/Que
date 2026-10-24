# Gold Trend Burst — backtest results

Testing uses XAUUSDc on HFMarketsGlobal-Live20 history, a $10,000 USD simulated hedging account, 1:100 leverage and real ticks. Contract size is 1 Gold unit per cent lot; exposure is normalized by contract size. These are historical simulations, not live results.

Training: October 5–9, 2026. Held-out validation: October 12–16, 2026. Default execution delay 150 ms; stress test 500 ms. M1 and M5 refer to attached chart timeframe; both use the same internal M5/M1 strategy.

Selection was fixed before validation: at least 30 training baskets, no execution halts, positive net after commission stress, profit factor above 1.1 and drawdown no greater than 8%; choose the most frequent qualifying candidate. If none passes, the highest-net functioning candidate is research-only.

Selected candidate: **train_blueprint**. Training qualification passed: **False**.

None of the six presets passed the training qualification. The original blueprint was the least losing training candidate and remains embedded. Faster/high-frequency alternatives are documented, not presented as profitable defaults. Smaller targets can reduce entries because the spread filter becomes stricter; the preset named fast did not produce the most trades.

| Test | Trades | Trade wins | Baskets | Basket wins | Net USD | PF | Drawdown | Mean basket seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train_blueprint | 82 | 48.78% | 28 | 50.00% | -143.54 | 0.75 | 2.97% | 117.1 |
| train_fast | 36 | 33.33% | 12 | 33.33% | -192.07 | 0.39 | 1.92% | 82.2 |
| train_momentum | 205 | 50.73% | 70 | 51.43% | -501.22 | 0.70 | 6.26% | 102.7 |
| train_strong | 153 | 39.22% | 52 | 40.38% | -918.89 | 0.41 | 9.64% | 67.5 |
| train_runner | 326 | 45.71% | 110 | 45.45% | -1307.00 | 0.61 | 13.32% | 132.0 |
| train_tight | 73 | 38.36% | 25 | 40.00% | -411.49 | 0.51 | 5.60% | 66.8 |
| validation_M1 | 211 | 49.29% | 71 | 50.70% | -875.41 | 0.51 | 10.23% | 99.3 |
| validation_M5 | 211 | 49.29% | 71 | 50.70% | -875.41 | 0.51 | 10.23% | 99.3 |
| delay_stress | 213 | 49.77% | 71 | 50.70% | -855.52 | 0.52 | 9.94% | 100.8 |
| disabled | 0 | 0.00% | 0 | 0.00% | 0.00 | 0.00 | 0.00% | 0.0 |
| daily_stop | 3 | 0.00% | 1 | 0.00% | -47.60 | 0.00 | 0.54% | 180.0 |

Win rate counts strictly positive closed trade P/L; break-even trades remain in the denominator. Basket win rate counts total P/L across its legs. Drawdown is MT5 maximal equity drawdown, including floating losses. Three correlated legs are not three independent signals.

## Cost stress and limitations

- validation_M1: net after an additional $7 per standard lot round-trip commission = $-958.15 (deducted $82.74). MT5 itself reported commission $0.00.
- validation_M5: net after an additional $7 per standard lot round-trip commission = $-958.15 (deducted $82.74). MT5 itself reported commission $0.00.
- delay_stress: net after an additional $7 per standard lot round-trip commission = $-939.10 (deducted $83.58). MT5 itself reported commission $0.00.

Only two historical weeks were evaluated. These results cannot establish robustness across market regimes. Spread is from the historical quotes; live execution, commission, liquidity and slippage may differ. No profitable setting is claimed unless both training criteria and independent validation survive costs. A research candidate that fails these checks is not recommended for live deployment.

## Embedded defaults

```
EnableTrading=true
AllowNewEntries=true
Magic=2026102303
BasketRiskPercent=0.75
DailyLossPercent=3.0
ExposureStepUnits=1.0
StopATR=1.0
Target1ATR=0.5
Target2ATR=0.75
Target3ATR=1.0
TrailATR=0.35
BreakBufferATR=0.05
MinBodyATR=0.25
MaxExtensionATR=2.0
MinADX=0.0
MaxSpreadTargetRatio=0.25
MaxSpreadPrice=1.0
CooldownSeconds=10
MaxHoldingSeconds=180
SlippagePoints=20
ClearExecutionHalt=false
```

## Verification

Compilation: 0 errors and 0 warnings (see compile.log). Each completed run reconciles basket P/L with MT5 net P/L, checks no duplicate signal basket, no more than three open positions and protected entry journal evidence. Full and partial baskets are recorded separately. The disabled and daily-stop runs are functional controls, not performance estimates. Broker disconnects and restart recovery were not exercised end-to-end.

The build is supplied for demo research. No live charts or live order permissions were changed.

Binary SHA-256: d05b8d375b790cf7913ab4230cc7d8bb33643429a8322544abab120fc0fccb00