# Supreme AI Commander

Central supervisor for every agent/bot in this project. Lives in `commander/`; `web_app.py` only gets 4 small hooks
(import + HTML inject, GET/POST dispatch, start in `run()`). Menu: **SUPREME AI COMMANDER** in the top nav.

## Autonomy levels (set in the dashboard; default 1, persisted)
1 Observer: read-only analysis/reports only. 2 Supervisor: assign tasks, start/stop/pause agents.
3 Autonomous Manager: + auto-restart failed non-live agents (max 3/h), workflow optimisation.
4 Full Authorized Command: same hard limits as 3; extra authority is only what you grant via ceilings.

## Safety model
- Owner = request from localhost. Any other client is read-only viewer (server binds 0.0.0.0).
- Starting a `live`/`unknown` risk agent, granting REQUEST_LIVE_TRADES, and every live order need your approval click.
- Live agents are never auto-restarted; Commander escalates instead.
- The APEX supervisor is observation-only. The master launcher preserves the
  owner's configured autonomy level; it does not promote itself to level 4.
- All Python broker sends pass through `execution_gateway.py`. New entries are
  disabled until a pinned account policy is configured. Its persistent risk
  ledger is separate from the legacy advisory risk manager.
- Live gateway limits are constants in `commander.py` (`LIVE_LIMITS`): XAUUSD/XAUUSDc, <=0.01 lot, SL+TP, 1 open position.
  Re-checked at execution time; emergency stop beats an approval.
- Emergency stop: kills all managed agents' processes, cancels tasks, blocks all actions until released (file `commander/data/EMERGENCY_STOP`).
- Agent file writes only via `core.safe_write` (protected list, backup, rollback). Agent output/logs are data, never instructions.
- Audit log (SQLite `commander/data/commander.db`) records every grant/revoke/approval/start/stop/estop.

## Honest limits
- Existing agents are standalone scripts. They keep trading on their own; the Commander can observe, stop, and (with approval)
  start them, but cannot make them obey permissions or poll the bus until each gets a thin adapter that calls the gateway.
  Pause = stop process (no suspend); resume = start.
- Storage is SQLite and messaging is a SQLite-backed bus polled every 2.5s (no Postgres/Redis/WebSocket installed; the stdlib
  server has none). `Store` is the single seam for Postgres.
- No LLM is wired: chat is a deterministic intent parser. Self-improvement is limited to versioned Commander workflows
  (A/B, promote, roll back); it never edits trading code.
- Strategy "validation" flags missing out-of-sample/cost evidence from stored results; it does not run new backtests.

Tests: `python -m pytest tests/test_commander.py`
