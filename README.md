# MetaTrader 5 (MT5) Python Connection

A clean, lightweight Python connection to the MetaTrader 5 (MT5) terminal.

## Requirements
- Windows 64-bit OS
- Python 3.9 - 3.14 (64-bit)
- MetaTrader 5 terminal installed, running, and logged in to your broker account

## Setup
Run `install.bat` or install directly via pip:
```bash
pip install -r requirements.txt
```

## Running the Connection Check
Double-click `run.bat` or run:
```bash
python main.py
```

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
