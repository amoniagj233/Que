"""
XTO Speeder Watchdog — 24/7 Auto-Restart Guardian
Keeps xto_speeder_trader.py alive forever.
Restarts on crash, MT5 disconnect, or any error.
Logs everything to xto_speeder_watchdog.log
"""
import subprocess
import time
import sys
import os
from datetime import datetime

LOG_FILE     = os.path.join(os.path.dirname(__file__), "xto_speeder_watchdog.log")
TRADER_SCRIPT = os.path.join(os.path.dirname(__file__), "xto_speeder_trader.py")
PYTHON_EXE   = sys.executable
RESTART_DELAY = 10   # seconds between restarts
MAX_RESTARTS  = 9999 # effectively infinite

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    log("=" * 60)
    log("  XTO SPEEDER WATCHDOG — 24/7 MODE ACTIVATED")
    log(f"  Trader: {TRADER_SCRIPT}")
    log(f"  Python: {PYTHON_EXE}")
    log(f"  Restart delay: {RESTART_DELAY}s | Max restarts: {MAX_RESTARTS}")
    log("=" * 60)

    restart_count = 0

    while restart_count < MAX_RESTARTS:
        restart_count += 1
        log(f">>> Starting XTO Speeder Trader [Run #{restart_count}]...")

        try:
            proc = subprocess.Popen(
                [PYTHON_EXE, TRADER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )

            # Stream output live
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log(f"  [BOT] {line}")

            proc.wait()
            exit_code = proc.returncode
            log(f">>> Trader exited with code {exit_code}")

        except FileNotFoundError:
            log(f"ERROR: Script not found: {TRADER_SCRIPT}")
        except Exception as e:
            log(f"ERROR: {type(e).__name__}: {e}")

        log(f">>> Restarting in {RESTART_DELAY} seconds... (total restarts: {restart_count})")
        time.sleep(RESTART_DELAY)

    log("MAX RESTARTS reached. Watchdog stopping.")

if __name__ == "__main__":
    main()
