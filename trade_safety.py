"""Broker-independent validation used by the dashboard's order router."""
import math
from decimal import Decimal, ROUND_FLOOR


MAX_OPEN_POSITIONS = 15
MAX_GROUP_RISK_PERCENT = 1.0


def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def floor_volume(requested, minimum, maximum, step):
    """Never increase requested exposure to satisfy the broker minimum."""
    requested = min(positive(requested, "Volume"), positive(maximum, "Maximum volume"))
    minimum = positive(minimum, "Minimum volume")
    step = positive(step, "Volume step")
    volume = float((Decimal(str(requested)) / Decimal(str(step))).to_integral_value(
        rounding=ROUND_FLOOR) * Decimal(str(step)))
    if volume < minimum - 1e-12:
        raise ValueError("Requested/risk-limited volume is below the broker minimum")
    return volume


def stop_loss_money(broker, order_type, symbol, volume, entry, stop):
    positive(volume, "Volume")
    positive(entry, "Entry")
    positive(stop, "Stop")
    result = broker.order_calc_profit(order_type, symbol, volume, entry, stop)
    if result is None or not math.isfinite(float(result)) or result >= 0:
        raise ValueError("Broker stop-risk calculation is unavailable or stop is not protective")
    return -float(result)


def limit_volume(broker, info, order_type, symbol, requested, entry, stop, budget, legs=1):
    budget = positive(budget, "Risk budget")
    volume = floor_volume(requested, info.volume_min, info.volume_max, info.volume_step)
    risk = stop_loss_money(broker, order_type, symbol, volume, entry, stop) * legs
    if risk > budget:
        volume = floor_volume(volume * budget / risk, info.volume_min,
                              info.volume_max, info.volume_step)
        risk = stop_loss_money(broker, order_type, symbol, volume, entry, stop) * legs
    if risk > budget + 1e-8:
        raise ValueError("Group stop exposure exceeds the risk budget")
    return volume


def validate_geometry(buy, bid, ask, stop, target, min_distance=0):
    positive(bid, "Bid")
    positive(ask, "Ask")
    positive(stop, "Stop")
    positive(target, "Target")
    if ask < bid:
        raise ValueError("Quote is crossed")
    valid = (stop < bid and target > bid and bid - stop >= min_distance
             and target - bid >= min_distance) if buy else (
                 stop > ask and target < ask and stop - ask >= min_distance
                 and ask - target >= min_distance)
    if not valid:
        raise ValueError("Protective SL/TP geometry is invalid at the current quote")


def deal_net(deal):
    return sum(float(getattr(deal, key, 0.0)) for key in
               ("profit", "commission", "swap", "fee"))
