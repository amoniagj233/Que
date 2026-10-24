"""
Headway MT5 Institutional Trading Station & AI Bridge
=====================================================
Main Entrypoint:
- Default: Runs the Institutional Trading Station & Analytics on http://127.0.0.1:8765/
- With --bridge: Runs the FastAPI AI REST API Bridge on http://localhost:8000/
"""

import sys
from config import settings
from mt5_connector import mt5_connector
from web_app import run as run_station

def main():
    if "--bridge" in sys.argv:
        import threading
        import webbrowser
        import uvicorn
        
        print("=" * 65)
        print(" " * 15 + "HEADWAY MT5 AI TRADING BRIDGE")
        print("=" * 65)

        if not mt5_connector.ensure_connected():
            print("[!] ERROR: Unable to connect to Headway MT5.")
            sys.exit(1)

        acc = mt5_connector.get_account_info()
        print(f"[OK] Connected Successfully!")
        print(f"    - Terminal: {acc.get('terminal_name', 'Headway MT5')}")
        print(f"    - Login:   {acc.get('login')}")
        print(f"    - Broker:  {acc.get('server')} ({acc.get('trade_mode')})")
        
        web_url = f"http://localhost:{settings.PORT}"
        print(f"\n[+] Starting FastAPI Bridge on {web_url}...")
        threading.Timer(1.2, lambda: webbrowser.open(web_url)).start()
        uvicorn.run("server:app", host=settings.HOST, port=settings.PORT, log_level="info")
    else:
        # Default: Launch the Institutional Workstation on port 8765
        run_station(port=8765)

if __name__ == "__main__":
    main()
