# OpenPendingShield 1.10 — corrected MT5 EA

## What stopped version 1.00

Your MT5 Experts log at 15:25:24 on 22 October 2026 recorded `OpenPendingShield (XAUEUR,M1)` with `trading=false` and `Disabled: EnableTrading=false`. Version 1.00 and its supplied preset were disabled by default. The EA did not attempt any order.

XAUEUR also had a 0.36 price spread when checked, above the old default allowance of 0.25 (1.0 entry distance multiplied by 0.25). Enabling the old build alone could still leave it waiting on that filter.

## Corrections

- `EnableTrading=true` by default, with an explicitly ready preset. MT5's toolbar and per-EA permission still control whether it may trade.
- `AutoAdjustEntryDistance=true`: move pending entries far enough from the market to satisfy the existing spread ratio. For a 0.36 spread, entry distance becomes 1.46 rather than 1.0. Maximum entry distance remains 5.0; maximum spread remains 2.0. Stop distance, fixed lot size and loss limits are unchanged. Moving the trigger changes entry timing and frequency; it is not a profitability claim.
- Pending orders use `ORDER_FILLING_RETURN`, as required by the [MQL5 pending-order specification](https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties).
- Chart messages identify missing toolbar permission, missing EA permission, invalid lot step, insufficient margin, risk-budget breaches, other symbol exposure and spread restrictions separately.
- Versioned filename avoids accidentally loading the old disabled binary. All source remains editable, with no trial or activation mechanism.

## Install the corrected file

1. In MT5, choose **File > Open Data Folder** and open `MQL5/Experts`. Copy `OpenPendingShield_1_10.ex5` from this Desktop folder there. The `.mq5` source is optional for running; copy it too if you want to edit it.
2. Refresh **Navigator > Expert Advisors**. Remove the old OpenPendingShield from the chart and attach **OpenPendingShield_1_10**. Start on a demo chart on the broker's actual Gold symbol, such as XAUEUR or XAUUSD.
3. In **Inputs**, click **Load** and choose this folder's `Ready-To-Trade.set`, or click **Reset** to use version 1.10 defaults. Confirm `EnableTrading=true`, `AllowNewEntries=true` and `AutoAdjustEntryDistance=true`. Do not load the old `Demo-Disabled.set`; it explicitly disables trading. MT5 remembers old input values, so merely overwriting an EX5 does not reliably reset them.
4. In the EA's **Common** tab, enable **Allow Algo Trading**. Turn on **Algo Trading** in MT5's toolbar.
5. Read the chart status and **Toolbox > Experts**. `Pending breakout orders protected by SL/TP` means orders were placed; a trade opens only when price reaches an order. If blocked, the displayed reason identifies the next action.

The update has been saved to Desktop, not automatically attached or enabled on a live chart. Copying it to Desktop does not update an EA already loaded in MT5.

## Remaining deliberate controls

The EA uses fixed 0.01 lots, a 1% combined estimated SL risk budget for both pending legs, and a 5% daily account-equity loss limit from first observed equity that broker day. A daily breach stays latched until the next broker day. It does not widen these limits to force a trade, round lots upward or place unprotected orders.

It will not start entries on a symbol with manual trades or another EA's orders/positions. The account inspected during this fix had existing manual XAUUSD positions; those can still block new Gold entries on XAUUSD. Use a separate demo account/symbol for testing; this delivery does not close or alter those trades. XAUEUR had no such exposure at the read-only check.

For entry pause while keeping position management, set `AllowNewEntries=false` and keep `EnableTrading=true`. Setting `EnableTrading=false` stops all EA transactions; existing broker orders retain their protection and expiration but are not cancelled by the disabled EA.

All distances are symbol price units, not account-currency profits. Broker minimum stop distances may increase SL/TP distances, with the estimated risk recalculated before entry. Stop execution can slip. Opposite-order cancellation is client-side and both legs can fill before cancellation, especially if MT5 disconnects. Pending orders expire after 120 seconds; the broker must support specified expiration. Existing owned positions are managed only by matching symbol and magic. Avoid sharing a symbol on netting accounts because manual trades can merge into an owned position.

Unknown broker results halt entries to avoid duplicate submission. Review actual broker orders, positions and history before using `ClearExecutionHalt=true` once, then return it to false. No stored halts or daily-loss baselines were cleared in your account during this fix.

## Evidence

`VALIDATION.md` describes the tests and their limits. `broker-preflight.json` contains successful broker validation of both XAUEUR pending-order requests with their stops, without submitting orders. Compilation and historical execution validate mechanics, not future profitability.
