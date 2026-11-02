@echo off
title APEX AI TRADER - Setup & Environment Initializer
color 0B
cd /d "%~dp0"

echo =====================================================================
echo   🚀 APEX AI / HEADWAY MT5 TRADING STATION - NEW PC SETUP
echo =====================================================================
echo.
echo [1/4] Verifying Python Environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found on your PATH!
    echo Please install Python 3.10 - 3.14 (64-bit) from python.org and check
    echo "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)
python -c "import sys; print(f'  Detected: Python {sys.version.split()[0]} ({64 if sys.maxsize > 2**32 else 32}-bit)')"

echo.
echo [2/4] Installing Required Trading & AI Libraries...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] Some packages failed to install. Retrying with --prefer-binary...
    python -m pip install --prefer-binary -r requirements.txt
)

echo.
echo [3/4] Ensuring Project Folders & Storage...
if not exist "logs" mkdir "logs"
if not exist "data_cache" mkdir "data_cache"
if not exist "commander\data" mkdir "commander\data"
if not exist "agent_settings\data" mkdir "agent_settings\data"

echo.
echo [4/4] Auto-Detecting MetaTrader 5 Terminal...
python mt5_finder.py

echo.
echo =====================================================================
echo   ✅ SETUP COMPLETE!
echo =====================================================================
echo   To launch the entire autonomous 24/7 ecosystem:
echo     - Run 'RUN_APEX_247.bat' (Guardian + 10-Bot Single Trade Fleet)
echo     - Or run 'run.bat' for the Web Dashboard & Supreme Commander
echo     - Dashboard URL: http://127.0.0.1:8765/
echo =====================================================================
echo.
pause
