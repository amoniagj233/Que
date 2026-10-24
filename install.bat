@echo off
title Install MetaTrader 5 Connection Dependencies
echo Installing Python packages for MetaTrader 5 connection...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed. Make sure Python 64-bit is installed and on PATH.
) else (
    echo.
    echo [OK] All packages installed successfully. Run run.bat or python main.py.
)
pause
