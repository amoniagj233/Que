# CRT GOLD PRO — CANDLE RANGE THEORY SPECIFICATION

## Overview
Candle Range Theory (CRT) exploits institutional liquidity sweeps around the boundaries of higher-timeframe reference candles.

## Timeframe Hierarchy
- **M30 Reference Timeframe:** Establishes `CRT_HIGH`, `CRT_LOW`, and `CRT_MIDPOINT = (CRT_HIGH + CRT_LOW) / 2`.
- **M5 Liquidity Sweep Timeframe:** Detects liquidity sweeps outside the M30 boundary and strictly reclaims the range.
- **M2 / M1 Confirmation Timeframe:** Confirms market structure shift via completed engulfing candlesticks within 6 minutes (3 bars).

## Entry & Risk Rules
### Bullish CRT Setup
1. Completed M30 candle defines reference range.
2. M5 candle sweeps below `CRT_LOW - MIN_SWEEP` and closes inside (`CRT_LOW < M5_CLOSE < CRT_HIGH`). Saves `SWEEP_LOW`.
3. M2 candle forms completed Bullish Engulfing within 3 bars.
4. Entry: Market BUY at Ask.
5. `SL = SWEEP_LOW - max(2 * tick_size, 0.15 * ATR_M5_14)`.
6. `TP1 = CRT_MIDPOINT` (50% volume close, move SL to breakeven).
7. `TP2 = CRT_HIGH` (remaining 50% volume). Minimum R:R for TP2 is 1.5R.

### Bearish CRT Setup
1. Completed M30 candle defines reference range.
2. M5 candle sweeps above `CRT_HIGH + MIN_SWEEP` and closes inside (`CRT_LOW < M5_CLOSE < CRT_HIGH`). Saves `SWEEP_HIGH`.
3. M2 candle forms completed Bearish Engulfing within 3 bars.
4. Entry: Market SELL at Bid.
5. `SL = SWEEP_HIGH + max(2 * tick_size, 0.15 * ATR_M5_14)`.
6. `TP1 = CRT_MIDPOINT` (50% volume close, move SL to breakeven).
7. `TP2 = CRT_LOW` (remaining 50% volume). Minimum R:R for TP2 is 1.5R.

## Shared State Machine (18 States)
`WAITING_FOR_RANGE`, `RANGE_READY`, `POTENTIAL_SWEEP`, `SWEEP_CONFIRMED`, `WAITING_FOR_ENGULFING`, `SIGNAL_READY`, `TRADE_BLOCKED`, `ORDER_SUBMITTED`, `ORDER_FILLED`, `POSITION_ACTIVE`, `TP1_REACHED`, `STOP_MOVED`, `TP2_REACHED`, `SL_HIT`, `TRADE_CLOSED`, `SETUP_EXPIRED`, `BOT_DISCONNECTED`, `RISK_SUSPENDED`.
