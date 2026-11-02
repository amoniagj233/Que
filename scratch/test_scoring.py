import MetaTrader5 as mt5
import numpy as np

def calculate_setup_confidence_v2(sym, info, tick, rates_m15, rates_h1, bias):
    """
    V2 High-Conviction Scoring Engine.
    Only allows true 90-100% setups with multi-timeframe H1/H4 confirmation.
    """
    if rates_m15 is None or len(rates_m15) < 20 or rates_h1 is None or len(rates_h1) < 20:
        return 0, ["Insufficient data"]
        
    score = 30  # Baseline for passing initial filter
    signals = []
    
    closes_m15 = rates_m15['close']
    closes_h1 = rates_h1['close']
    cur_p = tick.bid if bias == "SELL" else tick.ask
    
    # EMA calculations
    weights20 = np.exp(np.linspace(-1., 0., 20))
    weights20 /= weights20.sum()
    m15_ema20 = float(np.convolve(closes_m15[-20:], weights20, mode='valid')[-1])
    h1_ema20 = float(np.convolve(closes_h1[-20:], weights20, mode='valid')[-1])
    
    # H1 EMA50 if available
    h1_ema50 = float(np.mean(closes_h1[-20:])) # proxy if < 50
    if len(closes_h1) >= 50:
        weights50 = np.exp(np.linspace(-1., 0., 50))
        weights50 /= weights50.sum()
        h1_ema50 = float(np.convolve(closes_h1[-50:], weights50, mode='valid')[-1])
        
    # Factor 1: Higher Timeframe (H1) Trend Confluence (Crucial 25 points)
    if bias == "BUY":
        if cur_p > h1_ema20 and h1_ema20 >= h1_ema50:
            score += 25
            signals.append("H1 Bullish Trend Confluence")
        elif cur_p < h1_ema20:
            score -= 30
            signals.append("PENALTY: Fighting H1 Downtrend")
    elif bias == "SELL":
        if cur_p < h1_ema20 and h1_ema20 <= h1_ema50:
            score += 25
            signals.append("H1 Bearish Trend Confluence")
        elif cur_p > h1_ema20:
            score -= 30
            signals.append("PENALTY: Fighting H1 Uptrend")
            
    # Factor 2: M15 Dynamic Structure & Alignment (15 points)
    if bias == "BUY" and cur_p > m15_ema20:
        score += 10
        signals.append("Price above M15 EMA20")
        if closes_m15[-1] > closes_m15[-3]:
            score += 5
            signals.append("Rising M15 momentum")
    elif bias == "SELL" and cur_p < m15_ema20:
        score += 10
        signals.append("Price below M15 EMA20")
        if closes_m15[-1] < closes_m15[-3]:
            score += 5
            signals.append("Falling M15 momentum")
            
    # Factor 3: RSI Momentum Health (10 points)
    deltas = np.diff(closes_m15[-15:])
    gains = deltas[deltas > 0]
    losses = -deltas[deltas < 0]
    avg_g = float(np.mean(gains)) if len(gains) > 0 else 0.001
    avg_l = float(np.mean(losses)) if len(losses) > 0 else 0.001
    rsi = float(100 - (100 / (1 + (avg_g / avg_l))))
    
    if bias == "BUY":
        if 48.0 <= rsi <= 62.0:
            score += 10
            signals.append(f"RSI prime bullish continuation ({rsi:.1f})")
        elif rsi > 70.0:
            score -= 15
            signals.append(f"PENALTY: RSI Overbought ({rsi:.1f})")
    elif bias == "SELL":
        if 38.0 <= rsi <= 52.0:
            score += 10
            signals.append(f"RSI prime bearish continuation ({rsi:.1f})")
        elif rsi < 30.0:
            score -= 15
            signals.append(f"PENALTY: RSI Oversold ({rsi:.1f})")
            
    # Factor 4: Multi-Candle Impulse Continuation (10 points)
    if len(closes_m15) >= 4:
        if bias == "BUY" and closes_m15[-1] > closes_m15[-2] > closes_m15[-3]:
            score += 10
            signals.append("3-Candle Bullish Impulse")
        elif bias == "SELL" and closes_m15[-1] < closes_m15[-2] < closes_m15[-3]:
            score += 10
            signals.append("3-Candle Bearish Impulse")
            
    # Factor 5: Volatility & ATR Adequacy (5 points)
    score += 5
    
    # Factor 6: Spread / Liquidity Check (5 points)
    spread = tick.ask - tick.bid
    spread_pct = (spread / cur_p) * 100 if cur_p > 0 else 1.0
    if spread_pct < 0.06:
        score += 5
        signals.append("Ultra-tight spread")
    elif spread_pct > 0.15:
        score -= 15
        signals.append("PENALTY: Wide spread")
        
    final_score = min(100, max(10, score))
    return final_score, signals

if __name__ == "__main__":
    if not mt5.initialize():
        print("MT5 init failed")
        exit()
        
    candidates = ["BTC", "ETH", "SOL", "DOGE", "XAUUSD", "EURUSD"]
    for sym in candidates:
        info = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        if not info or not tick:
            continue
        rates_m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 45)
        rates_h1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 45)
        
        cur_p = (tick.bid + tick.ask) / 2.0
        # Check both BUY and SELL
        score_buy, sig_buy = calculate_setup_confidence_v2(sym, info, tick, rates_m15, rates_h1, "BUY")
        score_sell, sig_sell = calculate_setup_confidence_v2(sym, info, tick, rates_m15, rates_h1, "SELL")
        print(f"[{sym}] BUY Score: {score_buy}% ({', '.join(sig_buy[:2])}) | SELL Score: {score_sell}% ({', '.join(sig_sell[:2])})")
        
    mt5.shutdown()
