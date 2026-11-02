# Prepared safety update — not deployed

The active Headway services were left running as requested. The revised Python
sources are in `source/`. No MT5 orders were placed or closed during preparation.
Do not run a launcher in this folder: it is a review/test snapshot, not a second
trading installation. The active bots still use their existing safeguards.

## What changes

- The APEX supervisor only observes; it cannot restart bots. Commander Health
  remains the sole automatic recovery mechanism and excludes live/unknown code.
- The master launcher preserves the owner's autonomy level instead of forcing L4.
- Python broker submissions (including the evolution agent's generated template)
  use `execution_gateway.py`. A source audit test rejects direct broker send calls.
- Entries require a pinned login/server and an enabled policy. Demo is the default;
  real/contest entries additionally require `allow_live: true` and a fresh owner
  approval through Commander's existing trade approval path. Standalone bots
  cannot use policy opt-in alone to submit real-account entries.
- The gate uses broker account-currency profit/margin calculations and current
  quotes. It checks mandatory SL/TP, gold allowlist, spread, quote age, volume,
  position/pending-order counts, proposed trade risk and combined stop exposure.
- SQLite persists daily/weekly/peak baselines and latches a breached circuit
  breaker. UTC calendar boundaries apply. Limits are evaluated on attempted
  entries; this is not a continuous liquidation/mark-to-market service.
- A committed submission reservation prevents competing processes or an uncertain
  broker result from reusing account capacity. Explicit broker rejections release
  it; accepted tickets reconcile when visible in the position snapshot. If an
  order fills and closes before it is observed, or the outcome is unknown, entries
  stay blocked pending operator reconciliation. No timer silently frees capacity.
- Verified closes, cancellations, and protective stop tightening remain available
  with entries disabled. Stop removal/loosening, pending entries/modifications,
  and unsupported action types are refused.
- The legacy advisory risk manager includes proposed exposure in portfolio risk.
- Commander reports refused trades as not executed.
- Approval decisions are claimed atomically so competing clicks cannot execute
  one approval twice. Trade execution rechecks permissions and autonomy after
  approval, so revocations and a return to observer mode take effect.
- The Commander backtester uses stop-first treatment for ambiguous OHLC bars,
  labels data origin, and requires explicit opt-in to synthetic data.
  Sequential-window consistency alone no longer qualifies a strategy for live
  deployment; genuine independent held-out validation remains required.

## Limits and compatibility

Hard maximums: 0.25% projected stop risk per trade, 1% combined stop risk, 2% daily
loss, 6% weekly loss, 10% observed peak drawdown, 0.01 lot and one account-wide
position/pending order. Policy can tighten these ceilings. Only XAUUSD/XAUUSDc
entries are allowed. Risk projections reserve requested deviation but cannot
guarantee an execution price in a gap; broker calculations exclude future fees.
Existing grid/multiple-position strategies will be refused rather than exempted.

The gate is an application control, not a sandbox against code with local file
access. MQL5 EAs, manual MT5 trades, external terminals and already-running Python
processes are outside this update. Existing broker positions/pending orders count
toward the gate's limits, but the gate does not liquidate them. Persistent halts
and unresolved reservations require a deliberate, broker-verified operator review;
do not delete the database to get trading to resume.

The backtester is still an OHLC simulator. These corrections do not establish
strategy profitability, implement tick execution, or replace independent held-out
validation. Strategy selection, demo evaluation and broad code consolidation
remain subsequent work. No live policy has been enabled.

## Offline verification

From `source/`:

```powershell
python -m pytest tests/test_execution_gateway.py tests/test_supervisor_safety.py tests/test_backtester_safety.py tests/test_commander.py -q
```

Gateway tests use a fake broker; none initializes MT5. The concurrency test uses
two real local Python processes against the same temporary SQLite ledger.

## Deployment boundary

`review_update.py` reports source drift and running project processes without
changing the active project. `review_update.py --apply` is a separate, explicit
deployment step and refuses to apply while project Python processes are running
or any file to be replaced differs from its recorded baseline. It backs up
replaced files and rolls back completed replacements if copying fails.

Because the live evolution workers keep rewriting slot bots, those files may
already conflict with this snapshot. Stop services at an agreed maintenance
point, review/rebase the generated slot changes, regenerate the baseline only
after reviewing the differences, then deploy. The installer never stops services,
starts bots, enables entries, or changes MT5 positions.

The read-only deployment check during preparation also detected source drift in
the active `web_app.py`. That file must be reconciled before deployment; this
package will not overwrite those changes silently.

After deployment, copy `execution_policy.example.json` to `execution_policy.json`,
pin the intended demo login and exact server, then explicitly enable demo entries.
No account identity is guessed from whichever terminal happens to be open.
Validate demo behavior before considering live policy changes. Keep the persistent
ledger with the installation when restarting or updating it.
