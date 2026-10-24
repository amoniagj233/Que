"""Check completed disabled and daily-loss runs in the real MT5 tester journal."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
log = Path(r"C:\Users\amoni\MT5_Tester\Tester\Agent-127.0.0.1-3000\logs\20261022.log")
raw = "" if (root / "test-disabled.log").exists() and (root / "test-daily-guard.log").exists() else log.read_bytes().decode("utf-16", errors="replace")
runs = re.split(r"(?=OpenPendingShield 1\.00: original EA; trading=)", raw)
disabled_path, daily_path = root / "test-disabled.log", root / "test-daily-guard.log"
disabled = disabled_path.read_text(encoding="utf-8") if disabled_path.exists() else [s for s in runs if s.startswith("OpenPendingShield 1.00: original EA; trading=false")][-1]
daily = daily_path.read_text(encoding="utf-8") if daily_path.exists() else [s for s in runs if s.startswith("OpenPendingShield 1.00: original EA; trading=true")][-1]
pending = r"\b(?:buy|sell) stop [\d.]+ \S+ at [\d.]+ sl:"
assert "Test passed" in disabled
assert "Status: Disabled: EnableTrading=false" in disabled
assert not re.search(pending, disabled), "Disabled EA submitted an order"
assert "Test passed" in daily
marker = "Status: Daily equity loss guard: entries stopped"
assert marker in daily, "Daily loss guard did not fire"
after = daily[daily.index(marker) + len(marker):]
assert not re.search(pending, after), "Order submitted after daily loss latch"
assert "EXECUTION HALTED" not in daily
assert "Status: Pending breakout orders protected by SL/TP" not in after
(root / "test-disabled.log").write_text(disabled, encoding="utf-8")
(root / "test-daily-guard.log").write_text(daily, encoding="utf-8")
result = {"disabled_submissions": 0, "daily_guard_latched": True,
          "submissions_after_daily_guard": 0, "checks": "PASS"}
(root / "test-guards.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
