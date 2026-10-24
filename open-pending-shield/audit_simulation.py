"""Read-only checks against the actual MT5 tester journal, not a mock broker."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = Path(r"C:\Users\amoni\MT5_Tester\Tester\Agent-127.0.0.1-3000\logs\20261022.log")
saved = ROOT / "test-execution.log"
raw = saved.read_text(encoding="utf-8") if saved.exists() else LOG.read_bytes().decode("utf-16", errors="replace")
start = raw.rfind("OpenPendingShield 1.00: original EA; trading=true")
assert start >= 0, "No matching enabled simulation"
run = raw[start:]
assert "Test passed" in run, "Latest simulation did not finish successfully"
assert "EXECUTION HALTED" not in run, "Execution halt occurred"

entries = []
for line in run.splitlines():
    if ("\tTrade\t" not in line and "\tTrades\t" not in line) or "failed" in line:
        continue
    match = re.search(r"\b(buy|sell) stop ([\d.]+) \S+ at ([\d.]+) sl: ([\d.]+) tp: ([\d.]+)", line)
    if match:
        side, lot, price, sl, tp = match.groups()
        lot, price, sl, tp = map(float, (lot, price, sl, tp))
        assert lot == 0.01 and sl > 0 and tp > 0
        assert sl < price < tp if side == "buy" else tp < price < sl
        entries.append(match.groups())
assert entries, "No protected pending submissions observed"

previous = {}
trails = 0
for match in re.finditer(r"position modified \[#(\d+) (buy|sell) [\d.]+ \S+ [\d.]+ sl: ([\d.]+) tp: ([\d.]+)\]", run):
    ticket, side, sl, tp = match.groups()
    sl = float(sl)
    assert sl > 0 and float(tp) > 0
    if ticket in previous:
        assert sl >= previous[ticket] if side == "buy" else sl <= previous[ticket]
    previous[ticket] = sl
    trails += 1
assert trails > 0, "No actual position trailing observed"
cancels = run.count("order canceled [#")
assert cancels > 0, "No pending cancellation observed"
assert "stop loss triggered" in run or "take profit triggered" in run

report_bytes = (ROOT / "test-execution.htm").read_bytes()
report = report_bytes.decode("utf-16" if report_bytes.startswith(b"\xff\xfe") else "utf-8", errors="replace")
metrics = {}
for name in ("History Quality", "Total Net Profit", "Total Trades", "Profit Factor", "Equity Drawdown Maximal"):
    match = re.search(re.escape(name) + r":</td>\s*<td[^>]*>(.*?)</td>", report, re.S)
    if match:
        metrics[name] = re.sub(r"<[^>]+>", "", match[1]).strip()

(ROOT / "test-execution.log").write_text(run, encoding="utf-8")
result = {
    "checks": "PASS",
    "source_sha256": hashlib.sha256((ROOT / "OpenPendingShield.mq5").read_bytes()).hexdigest(),
    "binary_sha256": hashlib.sha256((ROOT / "OpenPendingShield.ex5").read_bytes()).hexdigest(),
    "protected_pending_submissions": len(entries),
    "monotone_trailing_updates": trails,
    "pending_cancellations": cancels,
    "report": metrics,
    "scope": "Generated historical ticks; execution smoke test, not proof of profitability or broker-atomic OCO.",
}
(ROOT / "test-execution.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
