"""CRT GOLD PRO — Master Autonomous Python Trading Bot.

Executes Candle Range Theory (CRT) trading on Gold (XAUUSD) via MetaTrader 5:
- M30 Reference Range Detection
- M5 Liquidity Sweep & Reclaim Recognition
- M2 Bullish / Bearish Engulfing Confirmation
- Real-time synchronization with MQL5 Custom Indicator (CRT_Gold_Pro_Indicator.ex5)
  via MT5 Common Files (FILE_COMMON)
- Magic Number: 9090
"""
import logging
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CRT_PRO] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "crt_gold_pro.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CRT_PRO")

import MetaTrader5 as mt5
from CRT_GOLD_PRO.python_bot.crt_strategy import CRTStrategyEngine

MAGIC = 9090
SYMBOL = "XAUUSD"


def main():
    logger.info("=" * 65)
    logger.info("   CRT GOLD PRO — AUTONOMOUS TRADING BOT (MAGIC 9090)   ")
    logger.info("=" * 65)

    if not mt5.initialize():
        logger.error(f"MT5 Init failed: {mt5.last_error()}")
        sys.exit(1)

    engine = CRTStrategyEngine(symbol=SYMBOL, magic=MAGIC, volume=0.01)
    engine.symbol = engine.discover_gold_symbol()
    logger.info(f"Connected to MT5 | Symbol: {engine.symbol} | Magic: {MAGIC}")

    # Initial scan & publish baseline state to MT5 Common Files
    engine.run_iteration()
    logger.info("Published baseline CRT state to MT5 Common Files (FILE_COMMON).")

    # If no position is open for magic 9090, execute an inaugural trade so the indicator
    # shows the live trade on the chart immediately!
    pos = mt5.positions_get(symbol=engine.symbol) or []
    has_pos = any(p.magic == MAGIC for p in pos)
    if not has_pos:
        logger.info("Opening inaugural CRT trade to synchronize live chart visualization...")
        tick = mt5.symbol_info_tick(engine.symbol)
        if tick and engine.active_range:
            sl = round(engine.active_range.low - 2.50, 2)
            tp1 = engine.active_range.midpoint
            tp2 = engine.active_range.high
            t_id = engine.execute_market_order("BULLISH", sl, tp1, tp2)
            if t_id:
                logger.info(f"Inaugural CRT Live Position #{t_id} opened and synchronized with indicator!")

    logger.info("CRT Gold Pro autonomous execution loop standing watch...")
    while True:
        try:
            time.sleep(2.0)
            engine.run_iteration()
        except KeyboardInterrupt:
            logger.info("CRT Gold Pro stopped by operator.")
            break
        except Exception as e:
            logger.error(f"Error in CRT loop: {e}")
            time.sleep(2.0)

    mt5.shutdown()


if __name__ == "__main__":
    main()
