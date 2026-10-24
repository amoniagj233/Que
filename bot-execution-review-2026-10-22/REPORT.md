# Gold bot execution review — 22 October 2026

Reviewed bot: `C:\Users\amoni\.gemini\antigravity\scratch\mt5_trade_agent\run_liquidity_bot.py`, using the Headway MT5 terminal, XAUUSD, live execution, 0.01 lots and magic number 20260912. It initially ran M1; the process changed to M5 during review. The activation helper preserves the current M5 setting.

## Result

Execution code is fixed and **36 offline tests passed**. This task did not restart the live process. A different process appeared during review, started at 13:25:22 with M5 and publishing `protected-journal-v2`; it predates the final source edits and has no `execution_build` field. Therefore, complete activation of the final fixes is not yet verified. The final code publishes a source fingerprint captured at import, which the helper checks against `expected_execution_build.txt`.

The read-only M1 market check in `readonly_check.json` returned HOLD / waiting for confirmation on the last completed Gold candle. The later running M5 bot also reported HOLD / waiting for confirmation. No test or verification command submitted a broker order.

Three live Gold positions were observed with magic number 0 and no broker SL or TP. They are not owned by this bot. No stop prices were selected, no positions were modified or closed, and ownership was not reassigned. The reviewed entry router refuses to add exposure while account positions lack valid stop losses.

## Changes

- Removed the invalid-stops fallback that retried entries with SL=0 and TP=0. Every submitted entry retains protective stops, including after rounding to broker precision.
- Only an explicit unsupported-filling-mode rejection can try another filling mode. None, exceptions, or accepted-but-not-final responses become UNKNOWN and block new symbol entries until broker evidence reconciles them. Partial fills are recorded without automatically topping up the remainder.
- Added SQLite entry reservations keyed by account, magic, symbol, timeframe, completed signal bar, direction and batch leg. Reservations are atomic and persist across restarts. Confirmed rejections have bounded retries with a 30-second delay; confirmed fills cannot be sent again.
- Added an OS instance lock to prevent multiple reviewed launchers for the same terminal/magic.
- Checked position capacity again before every batch leg. A bot with three positions and a four-position cap can open only one more, not an unchecked pair.
- Opposing positions must actually close before a reversal entry. Failed protective closes do not free capacity. Failed stop modifications no longer change the local stop as though the broker accepted them.
- Position management runs even if new entries are halted by the configured drawdown threshold or entry-spread filter.
- Strategy evaluation now excludes forming M1 and M5 candles. The strategy's own SL/TP geometry reaches the router instead of being silently replaced by generic distances.
- Final entry checks verify advancing/current quotes, finite prices and sizes, broker volume steps and stop distances, trading permissions, account equity, free margin and money at the stop. The existing 0.5% per-trade setting is enforced against the current quote without increasing lot size or changing the strategy's stop.
- Quote monitoring can verify an advancing feed despite the observed broker/host clock offset. A frozen or unverifiable quote blocks entries.
- Failed broker position queries are errors, not an empty/flat account.
- Added per-symbol entry decisions, counters, atomic heartbeat files, execution-version markers and DEGRADED error status. Logs now use an absolute bot-folder path and rotate.

## Daily-loss setting

The existing 100% setting disables the session/daily drawdown circuit breaker. The user answered “all” when asked to choose a daily-loss percentage; that does not specify a percentage. This value was therefore left unchanged. A chosen value can be supplied explicitly with `MT5_MAX_DAILY_DRAWDOWN_PERCENT` before launching.

The underlying risk manager currently measures drawdown from its session-start equity, not a reconstructed calendar-day starting balance. No claim of calendar-day or restart-persistent daily protection is made.

The 0.5% stop-risk check is a pre-submission check, not a guarantee of realized loss: gaps, execution slippage, commissions and stop-fill behavior can change actual results. Position limits apply to bot-owned positions; manually owned positions are not adopted by the bot.

## Verification

Run from the bot directory:

```powershell
python -m unittest test_execution_safety test_agent -q
```

The safety test module replaces MetaTrader5 with an in-memory fake before importing the engine or connector. Its database files and decision logs are temporary. Tests cover eligible batches, per-order capacity, closed candles, original SL/TP routing, broker rejection handling, partial/unknown outcomes, reconciliation, concurrent reservations, restart deduplication, unavailable positions/quotes/risk data, failed closes/modifications, management during entry halts, manual unprotected positions, and the duplicate-instance lock.

Python sources compile successfully. PowerShell activation-script syntax was parsed without executing it. Reviewed file hashes are in `reviewed_sha256.json`; backups of the original edited files use the `.before` suffix in this folder.

## Apply to the real account

The final real-account restart must be performed by the user. First set chosen protective stops on any unprotected account positions in MT5; the activation helper refuses to proceed while such exposure exists.

Run:

```powershell
powershell -NoProfile -File "C:\Users\amoni\OneDrive\Desktop\trading\bot-execution-review-2026-10-22\activate_reviewed_bot.ps1"
```

The helper verifies source hashes, runs offline tests, checks the selected Headway-Real account, and asks the user to type ACTIVATE. Only then does it stop the verified matching old process and launch the reviewed bot with the same terminal, current XAUUSD M5 setting, 0.01 lots, 0.5% risk setting and four-position bot cap. It does not close positions. It checks the account again after stopping, requires a fresh `protected-journal-v2` heartbeat with the exact reviewed build fingerprint, and reports failure rather than silently launching another instance.

Use `live_telemetry.json`, `entry_decisions.jsonl`, `entry_execution.sqlite3` and `liquidity_bot.log` in the bot folder to distinguish FILLED, ALREADY_FILLED, HOLD, BLOCKED, REJECTED and UNKNOWN outcomes. Every eligible batch leg is routed; entries blocked by risk, capacity, missing confirmation or uncertain prior submissions are not forced through.

Successful offline execution tests do not establish strategy profitability or prove that this reviewed version has already traded on the live account.
