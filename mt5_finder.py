"""
MT5 Universal Discovery & Initialization Helper
================================================
Auto-discovers MetaTrader 5 terminal executable paths and MQL5 data directories
across any Windows PC without hardcoded user or drive paths.
"""

from __future__ import annotations
import glob
import logging
import os
import subprocess
import sys
from typing import List, Optional

logger = logging.getLogger("MT5_FINDER")

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


def get_candidate_terminal_paths() -> List[str]:
    """Generates a prioritized list of probable MT5 terminal64.exe locations."""
    candidates = []

    # 1. User-defined environment variable overrides
    env_paths = [os.getenv("MT5_PATH"), os.getenv("MT5_TERMINAL_PATH"), os.getenv("TERMINAL64_PATH")]
    for p in env_paths:
        if p and p.strip():
            candidates.append(p.strip().strip('"'))

    # 2. Check running process via tasklist / wmic
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            line = line.strip()
            if line and line.lower().endswith("terminal64.exe") and os.path.isfile(line):
                candidates.append(line)
    except Exception:
        pass

    # 3. Standard Program Files locations
    prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    known_subdirs = [
        r"Headway MT5 Terminal\terminal64.exe",
        r"MetaTrader 5\terminal64.exe",
        r"Headway MT5\terminal64.exe",
        r"MetaTrader 5 IC Markets\terminal64.exe",
        r"FTMO MetaTrader 5\terminal64.exe",
        r"Pepperstone MetaTrader 5\terminal64.exe",
        r"Exness MT5 Terminal\terminal64.exe",
    ]

    for base in [prog_files, prog_files_x86]:
        if base and os.path.exists(base):
            for sub in known_subdirs:
                candidates.append(os.path.join(base, sub))

    # Also glob search in Program Files for any directory containing terminal64.exe
    for base in [prog_files, prog_files_x86]:
        if base and os.path.exists(base):
            try:
                for match in glob.glob(os.path.join(base, "*", "terminal64.exe")):
                    candidates.append(match)
            except Exception:
                pass

    # 4. User local appdata programs
    if local_appdata and os.path.exists(local_appdata):
        try:
            for match in glob.glob(os.path.join(local_appdata, "Programs", "*", "terminal64.exe")):
                candidates.append(match)
        except Exception:
            pass

    # Deduplicate while preserving order
    seen = set()
    result = []
    for c in candidates:
        norm = os.path.normpath(c).lower()
        if norm not in seen:
            seen.add(norm)
            result.append(c)
    return result


def find_mt5_terminal_path() -> Optional[str]:
    """Returns the first verified, existing path to terminal64.exe."""
    for path in get_candidate_terminal_paths():
        try:
            if os.path.isfile(path):
                return os.path.abspath(path)
        except Exception:
            continue
    return None


def find_mt5_data_dir() -> str:
    """Discovers the active MT5 MQL5 data directory across any PC."""
    # 1. Explicit override
    override = os.getenv("MT5_DATA_DIR")
    if override and os.path.isdir(override):
        return os.path.abspath(override)

    # 2. Live MT5 terminal_info query if MT5 is initialized
    if mt5 is not None:
        try:
            term = mt5.terminal_info()
            if term and getattr(term, "data_path", None):
                mql5_dir = os.path.join(term.data_path, "MQL5")
                if os.path.isdir(mql5_dir):
                    return mql5_dir
        except Exception:
            pass

    # 3. Dynamic scan across %APPDATA%\MetaQuotes\Terminal\*\MQL5
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        terminal_root = os.path.join(appdata, "MetaQuotes", "Terminal")
        if os.path.isdir(terminal_root):
            # Find directories with Experts subfolder
            candidates = glob.glob(os.path.join(terminal_root, "*", "MQL5"))
            for cand in candidates:
                if os.path.isdir(os.path.join(cand, "Experts")):
                    return os.path.abspath(cand)
            if candidates:
                return os.path.abspath(candidates[0])

    # 4. Fallback to local project folder MQL5
    workspace = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.join(workspace, "MQL5")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def smart_initialize_mt5(path: Optional[str] = None, **kwargs) -> bool:
    """Robust MT5 initialization helper for any PC."""
    if mt5 is None:
        logger.error("MetaTrader5 package is not installed.")
        return False

    # 1. If explicit or discovered path exists, try it
    target_path = path or find_mt5_terminal_path()
    if target_path and os.path.isfile(target_path):
        try:
            if mt5.initialize(path=target_path, **kwargs):
                logger.info(f"Connected to MT5 at: {target_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed init at {target_path}: {e}")

    # 2. Fallback to plain initialize() - attaches to running terminal or registry default
    try:
        if mt5.initialize(**kwargs):
            logger.info("Connected to MT5 via default initialize().")
            return True
    except Exception as e:
        logger.warning(f"Default initialize() failed: {e}")

    # 3. Try each discovered candidate in order
    for candidate in get_candidate_terminal_paths():
        if os.path.isfile(candidate) and candidate != target_path:
            try:
                if mt5.initialize(path=candidate, **kwargs):
                    logger.info(f"Connected to MT5 at candidate: {candidate}")
                    return True
            except Exception:
                continue

    err = mt5.last_error() if mt5 else "MT5 not imported"
    logger.error(f"All MT5 initialization attempts failed. Last error: {err}")
    return False


if __name__ == "__main__":
    print("Candidate MT5 paths:")
    for p in get_candidate_terminal_paths():
        exists = os.path.isfile(p)
        print(f"  [{'FOUND' if exists else 'MISSING'}] {p}")
    found = find_mt5_terminal_path()
    print(f"\nBest Discovered Terminal: {found}")
    print(f"Discovered MQL5 Data Dir: {find_mt5_data_dir()}")
    if mt5:
        ok = smart_initialize_mt5()
        print(f"Smart Initialize OK: {ok}")
        if ok:
            acc = mt5.account_info()
            term = mt5.terminal_info()
            print(f"Connected Terminal: {term.name if term else 'N/A'}")
            print(f"Account: {acc.login if acc else 'N/A'} (${acc.balance if acc else 0:,.2f})")
            mt5.shutdown()
