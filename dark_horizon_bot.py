"""XAU DARK HORIZON SCALP AI — GOLD MARKET DECISION ENGINE
Ported directly from institutional chart telemetry:
- 01 Direction Matrix: Bullish/Bearish expansion bias via 9/21/200 EMA confluence
- 02 Impulse Meter: Body-to-ATR expansion velocity scoring (0-100%)
- 03 Horizon Turn Radar: Reversal confidence score based on wick rejection & exhaustion
- 04 Flow Telemetry: Buyer/Seller energy balance, volume activity, and momentum
- 05 Scalp Command: BUY PRIME / SELL PRIME execution on demand confirmation
- 06 Risk Pulse: Mandatory ATR stop loss and measured recovery take profit

Magic Number: 1010 | Asset: XAUUSD | Timeframe: M1 / M5
"""
import logging
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DarkHorizon] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "dark_horizon_bot.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DarkHorizon")

import MetaTrader5 as mt5

MAGIC = 1010
BOT_NAME = "XAU Dark Horizon Scalp AI"
SYMBOL = "XAUUSD"
LOT_SIZE = 0.01
TIMEFRAME = mt5.TIMEFRAME_M1


class DarkHorizonEngine:
    def __init__(self, magic: int = MAGIC, symbol: str = SYMBOL, lot: float = LOT_SIZE):
        self.magic = magic
        self.symbol = symbol
        self.lot = lot
        self.tp_atr_mult = 2.0
        self.sl_atr_mult = 1.6
        self.last_trade_time = 0.0

    def get_symbol_name(self) -> str:
        for s in ["XAUUSD", "XAUUSDm", "GOLD"]:
            if mt5.symbol_info(s):
                return s
        return "XAUUSD"

    def fetch_bars(self, n: int = 150) -> Optional[pd.DataFrame]:
        rates = mt5.copy_rates_from_pos(self.symbol, TIMEFRAME, 0, n)
        if rates is None or len(rates) < 50:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def compute_telemetry(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute the 6 Horizon telemetry metrics from price & volume."""
        closes = df["close"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        opens = df["open"].to_numpy()
        volumes = df["tick_volume"].to_numpy()
        n = len(df)

        # 1. EMAs for Direction Matrix
        ema9 = pd.Series(closes).ewm(span=9, adjust=False).mean().iloc[-1]
        ema21 = pd.Series(closes).ewm(span=21, adjust=False).mean().iloc[-1]
        ema200 = pd.Series(closes).ewm(span=200, adjust=False).mean().iloc[-1]

        # ATR 14
        tr = np.maximum(highs[1:] - lows[1:], np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
        atr14 = float(np.mean(tr[-14:])) if len(tr) >= 14 else 1.50

        # 01 Direction Matrix
        cur_close = closes[-1]
        is_bullish_bias = cur_close > ema200 and ema9 > ema21
        is_bearish_bias = cur_close < ema200 and ema9 < ema21

        # 02 Impulse Meter (Bar Body vs ATR)
        last_body = abs(cur_close - opens[-1])
        impulse_grade = min(100.0, (last_body / max(atr14, 0.5)) * 50.0)

        # 03 Horizon Turn Radar & Rejection Wick
        candle_range = max(highs[-1] - lows[-1], 0.01)
        lower_wick = min(opens[-1], cur_close) - lows[-1]
        upper_wick = highs[-1] - max(opens[-1], cur_close)
        wick_pressure_pct = (lower_wick / candle_range) * 100.0

        # Liquidity Sweep Check: Did current low breach prior 20-bar low?
        prior_20_low = np.min(lows[-21:-1])
        prior_20_high = np.max(highs[-21:-1])
        sweep_low = lows[-1] < prior_20_low and cur_close > prior_20_low
        sweep_high = highs[-1] > prior_20_high and cur_close < prior_20_high

        # Turn Radar Score (0-100)
        reversal_confidence = min(95.0, (wick_pressure_pct * 0.5) + (35.0 if sweep_low else 10.0))

        # 04 Flow Telemetry
        buyer_energy = round((cur_close - lows[-1]) / candle_range * 100.0, 1)
        seller_energy = round(100.0 - buyer_energy, 1)
        avg_vol = np.mean(volumes[-20:])
        volume_activity = (volumes[-1] / max(avg_vol, 1.0)) * 100.0

        # 05 Scalp Command Decision
        signal = 0
        signal_reason = "Holding - Telemetry scanning"

        if is_bullish_bias and (sweep_low or (buyer_energy > 70.0 and reversal_confidence > 75.0)):
            signal = 1
            signal_reason = f"BUY PRIME: Liquidity Sweep Complete | Demand Confirmed (Confidence {reversal_confidence:.0f}%, Energy {buyer_energy}%)"
        elif is_bearish_bias and (sweep_high or (seller_energy > 70.0 and wick_pressure_pct < 25.0)):
            signal = -1
            signal_reason = f"SELL PRIME: Supply Confirmed (Confidence {reversal_confidence:.0f}%, Seller Energy {seller_energy}%)"

        return {
            "signal": signal,
            "reason": signal_reason,
            "atr": atr14,
            "direction_bias": "BULLISH" if is_bullish_bias else ("BEARISH" if is_bearish_bias else "NEUTRAL"),
            "impulse_grade": round(impulse_grade, 1),
            "reversal_confidence": round(reversal_confidence, 1),
            "buyer_energy": buyer_energy,
            "seller_energy": seller_energy,
            "volume_activity": round(volume_activity, 1)
        }

    def has_open_position(self) -> bool:
        pos = mt5.positions_get(symbol=self.symbol)
        if pos:
            return any(p.magic == self.magic for p in pos)
        return False

    def execute_scalp(self, signal: int, atr: float, reason: str) -> bool:
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return False

        is_buy = signal == 1
        price = tick.ask if is_buy else tick.bid
        tp_dist = round(max(atr * self.tp_atr_mult, 1.50), 2)
        sl_dist = round(max(atr * self.sl_atr_mult, 2.00), 2)

        tp_price = round(price + tp_dist, 2) if is_buy else round(price - tp_dist, 2)
        sl_price = round(price - sl_dist, 2) if is_buy else round(price + sl_dist, 2)

        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 25,
            "magic": self.magic,
            "comment": "DarkHorizon | Asymmetric",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"[ORDER EXECUTED] Ticket #{res.order} {'BUY' if is_buy else 'SELL'} {self.lot} @ {res.price} | TP: {tp_price} | SL: {sl_price} | {reason}")
            self.last_trade_time = time.time()
            return True
        else:
            err = res.comment if res else str(mt5.last_error())
            logger.error(f"[ORDER REJECTED] {err}")
            return False

    def run_cycle(self) -> None:
        if self.has_open_position():
            return

        df = self.fetch_bars(150)
        if df is None:
            return

        t = self.compute_telemetry(df)
        if t["signal"] != 0:
            logger.info(f"Telemetry Signal Triggered: {t['reason']}")
            self.execute_scalp(t["signal"], t["atr"], t["reason"])


def main():
    logger.info("=" * 65)
    logger.info(f"   {BOT_NAME} (Magic {MAGIC}) INITIALIZED   ")
    logger.info("=" * 65)

    if not mt5.initialize():
        logger.error(f"MT5 Init failed: {mt5.last_error()}")
        sys.exit(1)

    engine = DarkHorizonEngine()
    engine.symbol = engine.get_symbol_name()
    logger.info(f"Active Symbol: {engine.symbol} | Magic: {MAGIC} | Lot: {LOT_SIZE}")

    # Initial force inaugural trade if no position
    if not engine.has_open_position():
        logger.info("Opening inaugural Dark Horizon test scalp trade...")
        df = engine.fetch_bars(150)
        atr = 1.50
        if df is not None:
            t = engine.compute_telemetry(df)
            atr = t["atr"]
        engine.execute_scalp(1, atr, "Inaugural Dark Horizon Launch Trade")

    while True:
        try:
            time.sleep(3.0)
            engine.run_cycle()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(2.0)

    mt5.shutdown()


if __name__ == "__main__":
    main()
