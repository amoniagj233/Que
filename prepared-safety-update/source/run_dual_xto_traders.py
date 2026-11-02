"""
Dual XTO Speeder 24/7 Supervisor (Non-blocking I/O)
Runs BOTH trading engines simultaneously in isolated processes:
  - Bot 1: XTO Speeder Rebuilt (Magic 1111 | Fixed 60pts DCA)
  - Bot 2: XTO Speeder Upgrade 1 (Magic 2222 | Dynamic ATR Volatility Grid)
Outputs logged directly to disk files to avoid OS pipe buffer blocking.
"""
import subprocess
import time
import sys
import os
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PYTHON_EXE = sys.executable
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
BOT1_PATH  = os.path.join(BASE_DIR, "bot_slot_1.py")
BOT2_PATH  = os.path.join(BASE_DIR, "bot_slot_2.py")
LOG_DIR    = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

BOT1_LOG   = os.path.join(LOG_DIR, "bot1_magic1111.log")
BOT2_LOG   = os.path.join(LOG_DIR, "bot2_magic2222.log")
MAIN_LOG   = os.path.join(BASE_DIR, "dual_xto_traders.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(MAIN_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def start_bot(script_path, name, log_path):
    log(f"Starting {name} -> Logging to {os.path.basename(log_path)}...")
    log_fp = open(log_path, "a", encoding="utf-8", buffering=1)
    return subprocess.Popen(
        [PYTHON_EXE, "-u", script_path],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

def main():
    log("=" * 65)
    log("  [DUAL] DUAL XTO SPEEDER 24/7 TRADING STATION (NON-BLOCKING)")
    log("  Bot 1: Magic 1111 | Fixed 60pts DCA Scalp")
    log("  Bot 2: Magic 2222 | Dynamic ATR Spacing")
    log("=" * 65)

    p1 = start_bot(BOT1_PATH, "Champion Slot 1 (Magic 1111)", BOT1_LOG)
    p2 = start_bot(BOT2_PATH, "Challenger Slot 2 (Magic 2222)", BOT2_LOG)

    mtime1 = os.path.getmtime(BOT1_PATH) if os.path.exists(BOT1_PATH) else 0
    mtime2 = os.path.getmtime(BOT2_PATH) if os.path.exists(BOT2_PATH) else 0

    while True:
        try:
            # Check for Evolutionary Hot-Swap in Slot 1
            if os.path.exists(BOT1_PATH):
                new_mtime1 = os.path.getmtime(BOT1_PATH)
                if new_mtime1 != mtime1:
                    log("[HOT-SWAP] AI Evolution Agent deployed new Champion into Slot 1! Restarting Bot 1...")
                    p1.terminate()
                    time.sleep(2)
                    p1 = start_bot(BOT1_PATH, "Champion Slot 1 (Magic 1111)", BOT1_LOG)
                    mtime1 = new_mtime1

            # Check for Evolutionary Hot-Swap in Slot 2
            if os.path.exists(BOT2_PATH):
                new_mtime2 = os.path.getmtime(BOT2_PATH)
                if new_mtime2 != mtime2:
                    log("[HOT-SWAP] AI Evolution Agent deployed new Challenger into Slot 2! Restarting Bot 2...")
                    p2.terminate()
                    time.sleep(2)
                    p2 = start_bot(BOT2_PATH, "Challenger Slot 2 (Magic 2222)", BOT2_LOG)
                    mtime2 = new_mtime2

            # Check process health
            if p1.poll() is not None:
                log(f"[WARN] Slot-1 exited (code {p1.returncode}). Restarting...")
                time.sleep(3)
                p1 = start_bot(BOT1_PATH, "Champion Slot 1 (Magic 1111)", BOT1_LOG)

            if p2.poll() is not None:
                log(f"[WARN] Slot-2 exited (code {p2.returncode}). Restarting...")
                time.sleep(3)
                p2 = start_bot(BOT2_PATH, "Challenger Slot 2 (Magic 2222)", BOT2_LOG)

            time.sleep(3)

        except KeyboardInterrupt:
            log("Stopping both bots safely...")
            p1.terminate()
            p2.terminate()
            break
        except Exception as e:
            log(f"Supervisor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
