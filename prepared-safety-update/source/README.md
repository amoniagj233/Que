# Headway Trading Workstation

A Python workstation for MT5 gold-strategy research, monitoring and controlled
execution. The project includes standalone bots, an HTTP dashboard and Commander.
New Python trade entries require the account policy described below.

## Requirements
- Windows 64-bit OS
- Python 3.9 - 3.14 (64-bit)
- MetaTrader 5 terminal installed, running, and logged in to your broker account

## Setup
Run `install.bat` or install directly via pip:
```bash
pip install -r requirements.txt
```

## Running the Workstation
Double-click `run.bat` or run:
```bash
python main.py
```

The workstation normally opens on `http://127.0.0.1:8765/`. The older `--bridge`
mode references `server.py`, which is absent in this checkout; use the workstation
entry point. Do not use a launcher just to check installation: some launchers
start multiple bots or install boot autostart.

## Execution policy

Entries fail closed until `execution_policy.example.json` is copied to
`execution_policy.json` and explicitly configured with an intended demo login,
exact server name and `enabled: true`. Live entries remain disabled by default.
Standalone bots cannot place real-account entries; the Commander approval path
and an explicit live policy are both required. The shared gateway caps projected
trade risk at 0.25%, combined risk at 1%, volume at 0.01 lot and positions/orders
at one across the account. Existing grid strategies will hit these limits.

SQLite risk state lives in `commander/data/execution_risk.db`. It preserves loss
baselines, latched circuit breakers and unresolved submissions across restarts.
Do not remove that state to bypass a rejection. Closes and protective stop
tightening remain available while entries are disabled. MQL5 EAs and already
running processes do not acquire this gate merely because source files changed.

Offline tests: `python -m pytest tests -q` after installing
`requirements-dev.txt`. Gateway tests use a fake broker, not an MT5 account.

## Programmatic Usage in Python
```python
from mt5_connector import mt5_connector

# 1. Check connection
if mt5_connector.ensure_connected():
    # 2. Get account info
    acc = mt5_connector.get_account_info()
    print("Balance:", acc["balance"], acc["currency"])

    # 3. Get live quote
    quote = mt5_connector.get_quote("XAUUSD")
    print("XAUUSD Bid:", quote["bid"], "Ask:", quote["ask"])

    # 4. Get historical candles
    df = mt5_connector.get_candles("XAUUSD", timeframe="M15", count=100)
    print(df.tail())

    # 5. Place market order
    # res = mt5_connector.place_market_order(
    #     symbol="XAUUSD",
    #     action="BUY",
    #     volume=0.01,
    #     stop_loss=4080.0,
    #     take_profit=4120.0
    # )
```
