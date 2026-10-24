# OpenPendingShield 1.00

An independently written MT5 Expert Advisor with editable MQL5 source. No trial expiry, license key, activation server, account whitelist or broker lock. Tradivo's compiled files were not changed or decompiled. This is a different strategy implementation, not recovered Tradivo source or an exact clone.

## What it does

- Places a buy stop above the ask and a sell stop below the bid, with broker-side stop loss and take profit attached from submission.
- Reprices pending orders while flat; optionally derives entry distance from the previous closed M15 ATR bar.
- Cancels remaining pending orders when a position is detected and trails owned positions without loosening their stop.
- Uses fixed lots, spread limits, combined estimated SL risk across both pending legs, available margin checks, an entry cooldown and expiring pending orders.
- Stops new entries after a daily equity loss breach. The breach stays latched until the next broker day, including across restarts. Existing positions keep their SL/TP and trailing management.
- Halts new entries after unsuccessful broker operations, except explicit market-closed/no-quote rejections (cooldown), frozen orders (reconcile next quote), and rejected trailing-stop adjustments (retain existing protection). It does not blindly resubmit an uncertain request. Only after reviewing MT5 positions, orders and history should an operator restart once with `ClearExecutionHalt=true`, then return that setting to false.
- Refuses new entries when another strategy or manual trade has exposure on the same symbol. It manages only its own symbol and magic. An exclusive file lock prevents duplicate instances using the same account/magic on this computer.

## Installation and first use

1. In MT5 choose **File > Open Data Folder**. Copy `OpenPendingShield.mq5` and `OpenPendingShield.ex5` into a new `MQL5/Experts/OpenPendingShield` folder, then refresh Navigator.
2. Start in Strategy Tester on the broker's actual Gold symbol. `EnableTrading=true` is needed for simulated trades. The source default is false: attaching the EA with defaults submits no orders.
3. Review the report and conduct a demo forward test before considering live use. Compile success or a profitable historical test does not establish future profitability.
4. To stop entries while retaining position management, set `AllowNewEntries=false` and keep `EnableTrading=true`. This cancels owned pending orders. `EnableTrading=false` stops **all EA transactions**, including trailing and pending cancellation. Existing broker orders remain active until filled, cancelled manually or expired.

Do not reuse its magic number for another EA. Do not attach multiple copies with the same account/magic. No copy has been attached to a live chart or enabled for live trading by this delivery.

## Default inputs and units

| Input | Default | Meaning |
|---|---:|---|
| EnableTrading | false | Explicit operator control, not a vendor activation mechanism |
| Lots | 0.01 | Broker lot size; invalid sizes are rejected, never rounded upward |
| EntryDistance | 1.0 | Price distance outside ask/bid |
| StopDistance / TakeProfitDistance | 0.9 / 1.1 | Price distance from pending entry; not account-currency profit |
| MaxCombinedRiskPercent | 1.0 | Estimated loss at both pending stops as percentage of current account equity |
| DailyEquityLossPercent | 5.0 | Account equity loss from first observed equity of the broker day |
| MaxSpread / MaxSpreadEntryRatio | 2.0 / 0.25 | Both spread limits must pass |
| TrailStart / TrailDistance | 0.6 / 0.5 | Price movement before trailing / trailing distance |
| RepriceSeconds / RepriceThreshold | 5 / 0.2 | Minimum update interval / price movement needed |
| PendingLifetimeSeconds | 120 | Server-side expiration; broker must support specified expiration |
| EntryCooldownSeconds | 60 | Pause after an observed owned position closes |

All settings are editable. Broker minimum stop/freeze distances can increase effective distances. The combined risk estimate uses MT5 `OrderCalcProfit`; it excludes commissions and assumes execution at the stop price. Gaps, slippage and both orders filling before cancellation can exceed the estimate. Opposite-order cancellation is client-side, not a broker-atomic OCO guarantee. A disconnected terminal cannot cancel an opposite order; pending orders retain their 120-second expiration and attached SL/TP. On netting accounts, manual trades added after entry can merge into the same position; avoid sharing the symbol.

The daily baseline is account-wide equity at the first EA observation of each broker day, not midnight equity reconstructed from history. Other positions, deposits and withdrawals affect that measurement. Terminal global variables persist the baseline and latch; deleting them resets the stored state. Test runs isolate their baseline from live runs. No news filter, trend filter, AI agent or demonstrated predictive edge is claimed.

## Files and verification

- `OpenPendingShield.mq5`: complete editable source.
- `OpenPendingShield.ex5`: compiled MT5 binary.
- `compile.log`: actual MetaEditor compilation result.
- `tester-smoke.ini`: historical simulation settings, for the separate portable tester only. Live Expert trading is disabled in that terminal configuration; the tester enables simulated EA execution.
- `VALIDATION.md`: test results and limitations.

API references: [MT5 trade result checking](https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade/ctradeordermodify), [profit calculation](https://www.mql5.com/en/docs/trading/ordercalcprofit), [tester launch configuration](https://www.metatrader5.com/en/terminal/help/start_advanced/start).
