# Gold Trend Burst 1.00

Independent MT5 Expert Advisor for Gold. Research software; historical tests do not establish future profitability. Read RESULTS.md before use. No trial, activation service, or license expiry.

## Installation

1. In MT5 choose File > Open Data Folder. Copy GoldTrendBurst.ex5 into MQL5/Experts and refresh Navigator.
2. Use a demo **hedging** account and your broker's Gold chart (for example XAUUSD or XAUUSDc). Attach one instance to M1 or M5. It always reads M5 trend and M1 entry data internally.
3. Review inputs and enable MT5 Algo Trading and Allow Algo Trading in EA properties when you intend to trade. EnableTrading is true in the supplied build; attaching it with permissions enabled can place orders.
4. Read the chart status and Experts log if no trade occurs. Signals, spread, sessions, margin, minimum lots and existing exposure can block new entries. It does not trade every tick or force three entries after a rejection.

## Strategy

Closed M5 EMA20/EMA50 alignment, EMA20 slope and price determine direction. An optional ADX threshold filters trend strength. A completed M1 candle must show momentum or an EMA9 pullback; the current bid must break its high/low in the trend direction. Overextended prices are excluded. ATR14 on completed M1 candles sizes exits.

One signal submits up to three sequential market orders with attached broker SL and TP. Orders are not atomic: spreads, rejections or an early exit may leave fewer than three. There is one basket at a time and no averaging or martingale. Each signal is consumed before submission; uncertain execution halts new entries rather than resubmitting blindly.

After a TP exit, remaining stops may trail, but only when price allows a stop beyond entry and broker distance rules permit it. Break-even price does not cover all fees. Positions also close on an opposite confirmed trend or the configured holding-time limit, including at a loss. Timer processing is once per second; missing quotes, disconnection, broker rejection or latency can delay exits. Broker-side SL/TP remain in place.

## Risk and controls

BasketRiskPercent is shared across all three orders, not applied three times. Sizing reserves 10% of the budget for fill drift. Gaps, slippage and fees can exceed planned loss. ExposureStepUnits=1 means one Gold unit: typically 0.01 standard lot with contract size 100, or 1 cent lot with contract size 1. The EA checks actual contract size and broker volume rules. It skips entries if the minimum lot is too large for the budget.

DailyLossPercent stops **new baskets**, measured from equity first observed that broker day. It does not liquidate every position or guarantee a maximum daily loss. Manual trades and cash flows affect account equity. The daily stop persists until the next broker day; existing EA positions remain managed. AllowNewEntries=false pauses entries while preserving management. EnableTrading=false stops all EA trading actions, including position management.

Execution halts persist across restarts. Reconcile broker history and exposure before using ClearExecutionHalt, then return that input to false. Keep the same Magic while managing an existing basket. Different magic numbers create independent instances and independent risk budgets. A file lock prevents duplicate active instances using the same account/magic. Do not change account or chart symbol with an open basket.

The EA refuses netting accounts because they merge same-symbol positions. Other/manual exposure or pending orders on the symbol block entries. Use only on Gold; input distances and exposure units were designed and tested for Gold. There is no economic-news filter in this version.

## Evidence

RESULTS.md and results.csv summarize testing. Evidence.zip contains MT5 reports, journals, inputs and parsed deals. Backtests use an isolated MT5 terminal, not the user's live charts. This package was not attached to a live account or used to place live orders during development.
