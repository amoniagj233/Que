"""
MT5 Universal AI Trading Bridge & API Server
===========================================
Main Application Entrypoint:
1. Initializes & verifies connection to MetaTrader 5 terminal.
2. Runs the high-performance FastAPI server for MT5 REST API & Web Dashboard.
"""

import sys
import uvicorn
from config import settings
from mt5_connector import mt5_connector

def main():
    print("=" * 65)
    print(" " * 15 + "MT5 UNIVERSAL AI TRADING BRIDGE")
    print("=" * 65)

    # Initialize connection to MT5
    print("\n[+] Checking MetaTrader 5 Terminal Connection...")
    if not mt5_connector.ensure_connected():
        print("[!] ERROR: Unable to connect to MetaTrader 5.")
        print("[!] Make sure the MT5 terminal is open and logged in.")
        sys.exit(1)

    acc = mt5_connector.get_account_info()
    print(f"[OK] Connected Successfully!")
    print(f"    - Terminal: {acc.get('terminal_name', 'Headway MT5')}")
    print(f"    - Company:  {acc.get('company', 'Headway')}")
    print(f"    - Login:   {acc.get('login')}")
    print(f"    - Broker:  {acc.get('server')} ({acc.get('trade_mode')})")
    print(f"    - Balance: ${acc.get('balance'):,.2f} {acc.get('currency')}")
    print(f"    - Equity:  ${acc.get('equity'):,.2f}")
    print(f"    - Trading: {'ENABLED' if acc.get('trade_allowed') else 'DISABLED'}")

    print("\n[+] Starting MT5 AI Bridge REST API & Web Dashboard...")
    print(f"    - Web Dashboard:    http://{settings.HOST}:{settings.PORT}")
    print(f"    - Interactive Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"    - AI Tools Schema:  http://{settings.HOST}:{settings.PORT}/api/ai/tools")
    print("=" * 65)
    print("Bridge is LIVE. Press Ctrl+C in this terminal to stop.\n")

    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
        reload=False,
    )

if __name__ == "__main__":
    main()
