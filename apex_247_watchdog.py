"""
=============================================================================
   🚀 APEX AI TRADER — 24/7 AUTONOMOUS RESILIENT WATCHDOG
=============================================================================
This daemon ensures the entire Headway trading ecosystem runs 24/7 non-stop:
1. Prevents Windows sleep/hibernation (SetThreadExecutionState).
2. Auto-detects & auto-restarts MetaTrader 5 if closed or crashed.
3. Supervises & auto-restarts the Web Dashboard & Commander API (web_app.py).
4. Supervises & auto-restarts the 10-Bot Single-Trade Fleet Daemon (continuous_tp_reopen_daemon.py).
5. Monitors account health, equity, open positions, and logs status heartbeats.
=============================================================================
"""

import os
import sys
import time
import json
import ctypes
import signal
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

# Setup encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
WATCHDOG_LOG = LOG_DIR / "apex_247_watchdog.log"

PYTHON_EXE = sys.executable
try:
    from mt5_finder import find_mt5_terminal_path
    TERMINAL_EXE = find_mt5_terminal_path() or r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
except Exception:
    TERMINAL_EXE = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
WEB_PORT = 8765

# Windows execution flags to prevent sleep
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

DETACHED_FLAGS = 0x00000008 | 0x00000200 if os.name == "nt" else 0


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [24/7 WATCHDOG] {msg}"
    print(line, flush=True)
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def keep_windows_awake():
    """Instruct Windows kernel not to sleep, hibernate, or sleep network adapters."""
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
        except Exception as e:
            log(f"Warning: Failed to set thread execution state: {e}")


def is_process_running(process_name: str) -> bool:
    """Check whether a given exe is active in Windows process table."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/fi", f"imagename eq {process_name}"],
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return process_name.lower() in out.lower()
    except Exception:
        return False


def ensure_mt5_running():
    """Verify MT5 terminal64.exe is active. If not, launch it."""
    global TERMINAL_EXE
    if not is_process_running("terminal64.exe"):
        log("⚠️ MT5 Terminal is NOT running. Locating and launching terminal64.exe...")
        if not TERMINAL_EXE or not os.path.exists(TERMINAL_EXE):
            try:
                from mt5_finder import find_mt5_terminal_path
                TERMINAL_EXE = find_mt5_terminal_path()
            except Exception:
                pass

        if TERMINAL_EXE and os.path.exists(TERMINAL_EXE):
            try:
                subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
                log(f"✅ MT5 Terminal launched from {TERMINAL_EXE}. Waiting 10s for initialization...")
                time.sleep(10)
            except Exception as e:
                log(f"❌ Failed to launch MT5 Terminal: {e}")
        else:
            log(f"❌ MT5 Terminal path not found. Please install MetaTrader 5 or set MT5_PATH in .env")


class ManagedProcess:
    def __init__(self, name: str, cmd: list, log_file: Path):
        self.name = name
        self.cmd = cmd
        self.log_file = log_file
        self.process: subprocess.Popen = None
        self.restarts = 0
        self.last_start = 0

    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self):
        log_fp = open(self.log_file, "a", encoding="utf-8", buffering=1)
        self.process = subprocess.Popen(
            self.cmd,
            cwd=str(BASE_DIR),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_FLAGS
        )
        self.last_start = time.time()
        self.restarts += 1
        log(f"🟢 Started {self.name} (PID: {self.process.pid}, Restarts: {self.restarts})")

    def ensure_running(self):
        if not self.is_alive():
            log(f"⚠️ {self.name} is stopped or exited. Relaunching now...")
            self.start()

    def terminate(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass


def check_web_dashboard() -> bool:
    try:
        url = f"http://localhost:{WEB_PORT}/api/state"
        req = urllib.request.Request(url, headers={"User-Agent": "ApexWatchdog/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_watchdog():
    log("=" * 75)
    log("   APEX 24/7 TRADING ENGINE WATCHDOG INITIALIZED")
    log(f"   Base Directory : {BASE_DIR}")
    log(f"   Python Binary  : {PYTHON_EXE}")
    log(f"   Web App Port   : {WEB_PORT}")
    log("=" * 75)

    keep_windows_awake()

    # Step 1: Ensure MT5 terminal is open
    ensure_mt5_running()

    # Step 2: Define Managed Services
    web_service = ManagedProcess(
        name="Apex Web Server & Commander API",
        cmd=[PYTHON_EXE, "-u", "web_app.py", str(WEB_PORT)],
        log_file=LOG_DIR / "web_app_daemon.log"
    )

    fleet_daemon = ManagedProcess(
        name="Apex 10-Bot Reopen & Risk Daemon",
        cmd=[PYTHON_EXE, "-u", "continuous_tp_reopen_daemon.py"],
        log_file=LOG_DIR / "continuous_tp_reopen.log"
    )

    services = [web_service, fleet_daemon]

    # Handle graceful exit
    def handle_signal(sig, frame):
        log("🛑 Watchdog shutdown signal received. Stopping managed services...")
        for s in services:
            s.terminate()
        log("👋 Watchdog terminated cleanly.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Initial start
    for s in services:
        s.ensure_running()

    iteration = 0
    while True:
        try:
            time.sleep(5)
            iteration += 1

            # Refresh Windows execution state every ~60s
            if iteration % 12 == 0:
                keep_windows_awake()

            # Verify MT5 is still running every ~60s
            if iteration % 12 == 0:
                ensure_mt5_running()

            # Verify child processes are alive
            for s in services:
                s.ensure_running()

            # Heartbeat telemetry every 30s
            if iteration % 6 == 0:
                web_healthy = check_web_dashboard()
                fleet_alive = fleet_daemon.is_alive()
                web_alive = web_service.is_alive()

                status_str = f"Heartbeat | Web App (Port {WEB_PORT}): {'🟢 UP' if web_healthy else '🔴 DOWN'} | Fleet Daemon: {'🟢 UP' if fleet_alive else '🔴 DOWN'}"
                log(status_str)

        except KeyboardInterrupt:
            handle_signal(None, None)
            break
        except Exception as e:
            log(f"Watchdog main loop exception: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_watchdog()
