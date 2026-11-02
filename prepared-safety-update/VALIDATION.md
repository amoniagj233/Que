# Validation — 2 November 2026

Status: prepared and tested; not deployed. Active Headway services remain running.

## Results

| Check | Result |
|---|---|
| Full isolated `source/tests` suite | 73 passed in 118.78 seconds |
| Final approval/refusal refinements and related Commander regression checks | 14 passed in 4.19 seconds |
| Review/apply utility tests | 6 passed in 3.02 seconds |
| Additional gateway/generator/backtester checks during development | 8 passed |
| Final prepared Python syntax checks | Passed |
| Direct broker-send audit outside shared gateway | Passed in full suite |
| Two-process competition for shared order capacity | Passed in full suite |
| Read-only deployment review | Completed; no changes applied |

Test groups overlap; the rows should not be summed. The final approval checks ran
after the full suite because the approval claim and permission rechecks were
strengthened during final review.

The tests use simulated broker data. The missing-history loader test replaces
the MetaTrader5 module with a stub. No test initializes the user's terminal,
places/closes orders, starts a trading bot, or stops a project service.

The deployment utility was tested against temporary directories for read-only
review, running-process refusal, source drift, artifact integrity, path traversal
and rollback after a failed replacement. Its real-project invocation was review
only, without `--apply`.

## Deployment findings

- Project Python processes are running, so deployment is refused.
- Active `web_app.py` differs from the captured baseline. Reconcile it before
  applying; neither the baseline nor the active file was changed to bypass this.
- Forty changed/new files are listed in `update_manifest.json`, with baseline
  and prepared SHA-256 hashes. Unchanged source files are included to make the
  isolated snapshot testable.
- No enabled execution policy is supplied. The example policy disables entries
  and live trading, and contains no guessed account identity.

## Remaining work

This completes preparation of the execution-safety phase and the identified
backtester corrections. It does not select a profitable strategy, establish an
out-of-sample edge, complete a demo trading period, or consolidate the whole
application. Those steps require separate evidence after a controlled rollout.
MQL5 EAs and existing running processes remain outside the prepared Python gate.
