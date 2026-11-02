import re

def apply_patch():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    print(f"Original web_app.py length: {len(content)} chars")
    
    # 1. Replace calculate_setup_confidence and insert asset classes and compute_robust_stop_distance
    target_1 = """def calculate_setup_confidence(sym_info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist):
    \"\"\"
    Rigorous Multi-Factor Confidence Scoring (Rule 2):
      Evaluates trend confirmation, market structure, momentum/RSI, liquidity/spread, and risk ratio.
      Returns (score: int, signals: list).
      Only exceptional setups with multi-indicator alignment reach 88-100%.
    \"\"\"
    score = 65  # Base score for passing initial M15 boundary scan
    signals = []
    
    cur_p = tick.bid if bias == "SELL" else tick.ask
    
    # Factor 1: Trend Confirmation & EMA alignment
    if bias == "SELL" and cur_p < ema20:
        score += 8
        signals.append("Price below EMA20")
        if len(closes) >= 4 and closes[-1] < closes[-3]:
            score += 5
            signals.append("Negative EMA slope")
    elif bias == "BUY" and cur_p > ema20:
        score += 8
        signals.append("Price above EMA20")
        if len(closes) >= 4 and closes[-1] > closes[-3]:
            score += 5
            signals.append("Positive EMA slope")
            
    # Factor 2: Momentum & RSI Sweet Spot
    if bias == "SELL" and 40.0 <= rsi <= 55.0:
        score += 8
        signals.append(f"RSI in prime short momentum zone ({rsi:.1f})")
    elif bias == "BUY" and 45.0 <= rsi <= 60.0:
        score += 8
        signals.append(f"RSI in prime long momentum zone ({rsi:.1f})")
        
    # Factor 3: Liquidity & Spread Tolerance
    spread = tick.ask - tick.bid
    spread_pct = (spread / cur_p) * 100 if cur_p > 0 else 1.0
    if spread_pct < 0.05:
        score += 7
        signals.append(f"Ultra-low spread ({spread_pct:.3f}%)")
    elif spread_pct < 0.15:
        score += 4
        signals.append(f"Tight spread ({spread_pct:.3f}%)")
        
    # Factor 4: Volatility & ATR Adequacy
    if atr > 0:
        score += 5
        signals.append(f"Healthy ATR volatility ({atr:.2f})")

    # Factor 5: Multi-Candle Trend Momentum Confluence (Enables 90-100% High Conviction)
    if len(closes) >= 5:
        if bias == "BUY" and closes[-1] > closes[-2] > closes[-3]:
            score += 7
            signals.append("Bullish 3-candle momentum continuation")
        elif bias == "SELL" and closes[-1] < closes[-2] < closes[-3]:
            score += 7
            signals.append("Bearish 3-candle impulse continuation")
        
    score = min(100, max(50, score))
    return score, signals"""

    replacement_1 = """# Asset Class Classifications for Portfolio Heat & Correlation Protection
CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "LTC", "BTCUSD", "ETHUSD", "DOGEUSD", "XRPUSD", "SOLUSD", "LTCUSD", "ADAUSD"}
METALS_SYMBOLS = {"XAUUSD", "XAGUSD", "GOLD", "SILVER"}
FOREX_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "USDCHF"}
INDICES_SYMBOLS = {"US500", "DJ30", "NASDAQ-100", "VOL_20", "VOL_10", "BOOM_100", "CRASH_100"}

def compute_robust_stop_distance(sym, tick, info, m15_atr=0.0, h1_atr=0.0):
    \"\"\"
    Computes an asset-class calibrated protective stop loss distance outside market noise.
    Prevents microscopic noise stop-outs (e.g. 0.28% on crypto) that caused repeated losses.
    \"\"\"
    cur_p = (tick.bid + tick.ask) / 2.0 if (tick.bid > 0 and tick.ask > 0) else 1.0
    digits = info.digits
    point = info.point or (10 ** -digits)
    spread = tick.ask - tick.bid
    broker_min = max(info.trade_stops_level * point, spread * 1.5, point * 50)
    
    sym_upper = sym.upper()
    if sym_upper in CRYPTO_SYMBOLS or any(c in sym_upper for c in ["BTC", "ETH", "DOGE", "SOL", "XRP", "ADA", "LTC"]):
        # Crypto: Minimum 2.0% price distance or 2.5x H1 ATR
        dist = max(cur_p * 0.020, h1_atr * 2.2, m15_atr * 2.5, broker_min)
    elif sym_upper in METALS_SYMBOLS or any(c in sym_upper for c in ["XAU", "GOLD", "XAG"]):
        # Metals / Gold: Minimum $5.00/oz for Gold or 2.0x H1 ATR
        gold_floor = 5.00 if ("XAU" in sym_upper or "GOLD" in sym_upper) else 0.35
        dist = max(gold_floor, h1_atr * 2.0, m15_atr * 2.2, broker_min)
    elif sym_upper in FOREX_SYMBOLS or any(c in sym_upper for c in ["EUR", "GBP", "USD", "JPY", "CAD", "AUD", "NZD", "CHF"]):
        # Forex: Minimum 28 pips or 1.8x H1 ATR
        pip_dist = point * 280 if digits >= 4 else point * 28
        dist = max(pip_dist, h1_atr * 1.8, m15_atr * 2.0, broker_min)
    else:
        dist = max(cur_p * 0.012, h1_atr * 2.0, m15_atr * 2.2, broker_min)
        
    return dist

def calculate_setup_confidence(sym_info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist, rates_h1=None):
    \"\"\"
    Rigorous Multi-Factor Confidence Scoring (Rule 2 & High-Conviction Gate):
      Evaluates Higher Timeframe (H1) alignment, market structure, momentum/RSI, spread, and multi-candle impulse.
      Returns (score: int, signals: list).
      Only exceptional setups with multi-timeframe and multi-indicator alignment reach 90-100%.
      Counter-trend setups fighting H1 trend receive severe penalties and are rejected.
    \"\"\"
    score = 30  # Disciplined base score (no artificial inflation)
    signals = []
    
    cur_p = tick.bid if bias == "SELL" else tick.ask
    
    # Factor 1: Higher Timeframe (H1) Trend Confluence (Crucial 25 points / -30 penalty)
    if rates_h1 is not None and len(rates_h1) >= 20:
        closes_h1 = rates_h1['close']
        weights20 = np.exp(np.linspace(-1., 0., 20))
        weights20 /= weights20.sum()
        h1_ema20 = float(np.convolve(closes_h1[-20:], weights20, mode='valid')[-1])
        h1_ema50 = float(np.mean(closes_h1[-20:]))
        if len(closes_h1) >= 50:
            weights50 = np.exp(np.linspace(-1., 0., 50))
            weights50 /= weights50.sum()
            h1_ema50 = float(np.convolve(closes_h1[-50:], weights50, mode='valid')[-1])
            
        if bias == "BUY":
            if cur_p > h1_ema20 and h1_ema20 >= h1_ema50:
                score += 25
                signals.append("H1 Bullish Trend Confluence")
            elif cur_p < h1_ema20:
                score -= 30
                signals.append("PENALTY: Counter-trend to H1 Downtrend")
        elif bias == "SELL":
            if cur_p < h1_ema20 and h1_ema20 <= h1_ema50:
                score += 25
                signals.append("H1 Bearish Trend Confluence")
            elif cur_p > h1_ema20:
                score -= 30
                signals.append("PENALTY: Counter-trend to H1 Uptrend")
    
    # Factor 2: M15 Trend Confirmation & EMA alignment (15 points)
    if bias == "SELL" and cur_p < ema20:
        score += 10
        signals.append("Price below M15 EMA20")
        if len(closes) >= 4 and closes[-1] < closes[-3]:
            score += 5
            signals.append("Negative M15 EMA slope")
    elif bias == "BUY" and cur_p > ema20:
        score += 10
        signals.append("Price above M15 EMA20")
        if len(closes) >= 4 and closes[-1] > closes[-3]:
            score += 5
            signals.append("Positive M15 EMA slope")
            
    # Factor 3: Momentum & RSI Sweet Spot (10 points / -15 penalty for extreme exhaustion)
    if bias == "SELL":
        if 38.0 <= rsi <= 52.0:
            score += 10
            signals.append(f"RSI prime short momentum ({rsi:.1f})")
        elif rsi < 30.0:
            score -= 15
            signals.append(f"PENALTY: RSI Oversold exhaustion ({rsi:.1f})")
    elif bias == "BUY":
        if 48.0 <= rsi <= 62.0:
            score += 10
            signals.append(f"RSI prime long momentum ({rsi:.1f})")
        elif rsi > 70.0:
            score -= 15
            signals.append(f"PENALTY: RSI Overbought exhaustion ({rsi:.1f})")
        
    # Factor 4: Liquidity & Spread Tolerance (5 points / -15 penalty for wide spread)
    spread = tick.ask - tick.bid
    spread_pct = (spread / cur_p) * 100 if cur_p > 0 else 1.0
    if spread_pct < 0.05:
        score += 5
        signals.append(f"Ultra-low spread ({spread_pct:.3f}%)")
    elif spread_pct > 0.15:
        score -= 15
        signals.append(f"PENALTY: Wide spread ({spread_pct:.3f}%)")
        
    # Factor 5: Volatility & ATR Adequacy (5 points)
    if atr > 0:
        score += 5
        signals.append(f"Healthy ATR volatility ({atr:.2f})")

    # Factor 6: Multi-Candle Trend Momentum Confluence (10 points)
    if len(closes) >= 4:
        if bias == "BUY" and closes[-1] > closes[-2] > closes[-3]:
            score += 10
            signals.append("Bullish 3-candle momentum continuation")
        elif bias == "SELL" and closes[-1] < closes[-2] < closes[-3]:
            score += 10
            signals.append("Bearish 3-candle impulse continuation")
        
    score = min(100, max(10, score))
    return score, signals"""

    # Normalize CRLF for matching
    content_norm = content.replace('\r\n', '\n')
    target_1_norm = target_1.replace('\r\n', '\n')
    replacement_1_norm = replacement_1.replace('\r\n', '\n')
    
    if target_1_norm not in content_norm:
        print("ERROR: target_1_norm not found!")
        return False
        
    content_norm = content_norm.replace(target_1_norm, replacement_1_norm)
    print("SUCCESS: Target 1 replaced.")
    
    # 2. In run_scan_now: update rates copy, H1 ATR, robust stop_dist, H1 passing to calculate_setup_confidence, and asset correlation gates
    target_2 = """                rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 45)
                if rates is None or len(rates) < 20:
                    filtered_reasons[sym] = "Insufficient M15 candle history"
                    continue

                closes = rates['close']
                highs = rates['high']
                lows = rates['low']

                # Compute ATR 14
                tr = np.maximum(highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1]))
                tr = np.maximum(tr, np.abs(lows[1:] - closes[:-1]))
                atr = float(np.mean(tr[-14:]))
                digits = info.digits
                point = info.point or (10 ** -digits)
                if atr <= (point * 0.5):
                    atr = point * 15.0

                # Compute EMA20
                if np is not None:
                    weights20 = np.exp(np.linspace(-1., 0., 20))
                    weights20 /= weights20.sum()
                    ema20 = float(np.convolve(closes[-20:], weights20, mode='valid')[-1])
                else:
                    ema20 = float(sum(closes[-20:]) / 20)

                # Compute RSI 14
                deltas = np.diff(closes[-15:])
                gains = deltas[deltas > 0]
                losses = -deltas[deltas < 0]
                avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
                avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
                rs = avg_gain / avg_loss
                rsi = float(100 - (100 / (1 + rs)))

                cur_p = (tick.bid + tick.ask) / 2.0 if (tick.bid > 0 and tick.ask > 0) else closes[-1]
                stop_dist = max(atr * 1.5, point * 50)"""

    replacement_2 = """                rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 45)
                if rates is None or len(rates) < 20:
                    filtered_reasons[sym] = "Insufficient M15 candle history"
                    continue

                rates_h1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 45)
                h1_atr = 0.0
                if rates_h1 is not None and len(rates_h1) >= 14:
                    tr_h1 = np.maximum(rates_h1['high'][1:] - rates_h1['low'][1:], np.abs(rates_h1['high'][1:] - rates_h1['close'][:-1]))
                    tr_h1 = np.maximum(tr_h1, np.abs(rates_h1['low'][1:] - rates_h1['close'][:-1]))
                    h1_atr = float(np.mean(tr_h1[-14:]))

                closes = rates['close']
                highs = rates['high']
                lows = rates['low']

                # Compute ATR 14
                tr = np.maximum(highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1]))
                tr = np.maximum(tr, np.abs(lows[1:] - closes[:-1]))
                atr = float(np.mean(tr[-14:]))
                digits = info.digits
                point = info.point or (10 ** -digits)
                if atr <= (point * 0.5):
                    atr = point * 15.0

                # Compute EMA20
                if np is not None:
                    weights20 = np.exp(np.linspace(-1., 0., 20))
                    weights20 /= weights20.sum()
                    ema20 = float(np.convolve(closes[-20:], weights20, mode='valid')[-1])
                else:
                    ema20 = float(sum(closes[-20:]) / 20)

                # Compute RSI 14
                deltas = np.diff(closes[-15:])
                gains = deltas[deltas > 0]
                losses = -deltas[deltas < 0]
                avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
                avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
                rs = avg_gain / avg_loss
                rsi = float(100 - (100 / (1 + rs)))

                cur_p = (tick.bid + tick.ask) / 2.0 if (tick.bid > 0 and tick.ask > 0) else closes[-1]
                # Calibrated robust protective stop distance outside market noise
                stop_dist = compute_robust_stop_distance(sym, tick, info, m15_atr=atr, h1_atr=h1_atr)"""

    target_2_norm = target_2.replace('\r\n', '\n')
    replacement_2_norm = replacement_2.replace('\r\n', '\n')
    if target_2_norm not in content_norm:
        print("ERROR: target_2_norm not found!")
        return False
    content_norm = content_norm.replace(target_2_norm, replacement_2_norm)
    print("SUCCESS: Target 2 replaced.")

    # 3. In run_scan_now: call calculate_setup_confidence with rates_h1
    target_3 = """                # Compute Multi-Factor Confidence Score (Rule 2)
                confidence_score, signals_list = calculate_setup_confidence(
                    info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist
                )"""

    replacement_3 = """                # Compute Multi-Factor Confidence Score (Rule 2 & High Conviction Gate)
                confidence_score, signals_list = calculate_setup_confidence(
                    info, tick, closes, highs, lows, ema20, rsi, atr, bias, stop_dist, rates_h1=rates_h1
                )"""

    target_3_norm = target_3.replace('\r\n', '\n')
    replacement_3_norm = replacement_3.replace('\r\n', '\n')
    if target_3_norm not in content_norm:
        print("ERROR: target_3_norm not found!")
        return False
    content_norm = content_norm.replace(target_3_norm, replacement_3_norm)
    print("SUCCESS: Target 3 replaced.")

    # 4. In run_scan_now: add Portfolio Correlation & Loss Cooldown Gates before execution
    target_4 = """                # ULTRA-HIGH CONFIDENCE AUTOMATIC EXECUTION (Rule 3: 90-100% Threshold Only - Exactly 1 Trade Per Symbol)
                if is_open and confidence_score >= 90 and self.auto_trade_enabled:
                    # Policy: Take trade automatically one symbol at a time per scan pass
                    if auto_trade_executed_this_pass:
                        setup_obj["notes"] += " [Queued: Taking 1 symbol at a time policy]"
                        valid_setups.append(setup_obj)
                        continue
                    # Risk gate: Disallow automatic execution on Priority 5 (AVOID) symbols with severe historical losses
                    if setup_obj.get("symbol_perf", {}).get("priority_num") == 5:
                        filtered_reasons[sym] = f"Auto-Execution blocked: {sym} has historical Priority 5 (AVOID) status (Severe Loss Skew/Drawdown). Manual confirmation required."
                        valid_setups.append(setup_obj)
                        continue"""

    replacement_4 = """                # ULTRA-HIGH CONFIDENCE AUTOMATIC EXECUTION (Rule 3: 90-100% Threshold Only - Exactly 1 Trade Per Symbol)
                if is_open and confidence_score >= 90 and self.auto_trade_enabled:
                    # Policy: Take trade automatically one symbol at a time per scan pass
                    if auto_trade_executed_this_pass:
                        setup_obj["notes"] += " [Queued: Taking 1 symbol at a time policy]"
                        valid_setups.append(setup_obj)
                        continue

                    # Portfolio Correlation Protection Gate
                    sym_u = sym.upper()
                    open_crypto = sum(1 for p in positions if p.symbol.upper() in CRYPTO_SYMBOLS or any(c in p.symbol.upper() for c in ["BTC", "ETH", "DOGE", "SOL", "XRP", "ADA", "LTC"]))
                    open_metals = sum(1 for p in positions if p.symbol.upper() in METALS_SYMBOLS or any(c in p.symbol.upper() for c in ["XAU", "GOLD", "XAG"]))
                    open_forex = sum(1 for p in positions if p.symbol.upper() in FOREX_SYMBOLS or any(c in p.symbol.upper() for c in ["EUR", "GBP", "USD", "JPY", "CAD", "AUD", "NZD", "CHF"]))

                    if (sym_u in CRYPTO_SYMBOLS or any(c in sym_u for c in ["BTC", "ETH", "DOGE", "SOL", "XRP", "ADA", "LTC"])) and open_crypto >= 1:
                        filtered_reasons[sym] = f"Auto-Execution blocked: Portfolio Correlation Gate - Max 1 active Crypto trade allowed ({open_crypto} currently open)"
                        setup_obj["notes"] += " [Blocked by Crypto Correlation Gate]"
                        valid_setups.append(setup_obj)
                        continue

                    if (sym_u in METALS_SYMBOLS or any(c in sym_u for c in ["XAU", "GOLD", "XAG"])) and open_metals >= 1:
                        filtered_reasons[sym] = f"Auto-Execution blocked: Portfolio Correlation Gate - Max 1 active Metals trade allowed ({open_metals} currently open)"
                        setup_obj["notes"] += " [Blocked by Metals Correlation Gate]"
                        valid_setups.append(setup_obj)
                        continue

                    if (sym_u in FOREX_SYMBOLS or any(c in sym_u for c in ["EUR", "GBP", "USD", "JPY", "CAD", "AUD", "NZD", "CHF"])) and open_forex >= 2:
                        filtered_reasons[sym] = f"Auto-Execution blocked: Portfolio Correlation Gate - Max 2 active Forex trades allowed ({open_forex} currently open)"
                        setup_obj["notes"] += " [Blocked by Forex Correlation Gate]"
                        valid_setups.append(setup_obj)
                        continue

                    # Symbol Loss Cooldown: avoid repeated entries on symbol that stopped out in last 45 minutes
                    recent_losses = getattr(self, "recent_losses", {})
                    last_loss_ts = recent_losses.get(sym, 0)
                    if time.time() - last_loss_ts < 2700:
                        rem_m = int((2700 - (time.time() - last_loss_ts)) / 60)
                        filtered_reasons[sym] = f"Auto-Execution blocked: 45-min Loss Cooldown active on {sym} ({rem_m}m remaining)"
                        setup_obj["notes"] += " [Blocked by Loss Cooldown]"
                        valid_setups.append(setup_obj)
                        continue

                    # Risk gate: Disallow automatic execution on Priority 5 (AVOID) symbols with severe historical losses
                    if setup_obj.get("symbol_perf", {}).get("priority_num") == 5:
                        filtered_reasons[sym] = f"Auto-Execution blocked: {sym} has historical Priority 5 (AVOID) status (Severe Loss Skew/Drawdown). Manual confirmation required."
                        valid_setups.append(setup_obj)
                        continue"""

    target_4_norm = target_4.replace('\r\n', '\n')
    replacement_4_norm = replacement_4.replace('\r\n', '\n')
    if target_4_norm not in content_norm:
        print("ERROR: target_4_norm not found!")
        return False
    content_norm = content_norm.replace(target_4_norm, replacement_4_norm)
    print("SUCCESS: Target 4 replaced.")

    # 5. In execute_multi_tp_group: update stop loss calculation to compute_robust_stop_distance and enforce correlation cap
    target_5 = """            point = positive(info.point, "Symbol point")
            minimum = max(info.trade_stops_level * point, spread * 1.5, point * 50)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15)
            # Retain the existing mean-candle-range calculation and targets.
            scale = (sum(float(r["high"] - r["low"]) for r in rates) / len(rates)
                     if rates is not None and len(rates) >= 5 else minimum * 2)
            if not math.isfinite(scale):
                raise ValueError("Non-finite candle range")
            if scale <= point:
                scale = minimum * 2
            distance = max(minimum, scale * 1.8)
            shared_sl = round(max(0.00001, entry - distance) if action == "BUY"
                              else entry + distance, info.digits)
            requested = default_lot if custom_lots is None else custom_lots
            lot = limit_volume(mt5, info, order_type, symbol, requested,
                               entry, shared_sl, budget, legs=1)
        except (ValueError, TypeError, OverflowError) as exc:
            return reject(str(exc))

        executed, errors, uncertain = [], [], None
        reservation = None
        used_risk = 0.0
        group_id = f"GRP-{time.time_ns()}-{symbol.replace(' ', '')[:6]}"
        import random
        # RULES 1 & 2: Keep 2 TPs only (1.8x & 4.0x), open ONE trade per symbol and randomly allocate one of the two TPs
        tp_choices = [
            (1, 1.8, "TP1-Conservative"),
            (2, 4.0, "TP2-Runner")
        ]
        chosen_leg, chosen_multiple, chosen_label = random.choice(tp_choices)

        target_distance = max(minimum, scale * chosen_multiple)"""

    replacement_5 = """            point = positive(info.point, "Symbol point")
            minimum = max(info.trade_stops_level * point, spread * 1.5, point * 50)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25)
            rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 25)
            m15_atr = 0.0
            if rates is not None and len(rates) >= 14:
                tr_m = np.maximum(rates['high'][1:] - rates['low'][1:], np.abs(rates['high'][1:] - rates['close'][:-1]))
                tr_m = np.maximum(tr_m, np.abs(rates['low'][1:] - rates['close'][:-1]))
                m15_atr = float(np.mean(tr_m[-14:]))
            h1_atr = 0.0
            if rates_h1 is not None and len(rates_h1) >= 14:
                tr_h = np.maximum(rates_h1['high'][1:] - rates_h1['low'][1:], np.abs(rates_h1['high'][1:] - rates_h1['close'][:-1]))
                tr_h = np.maximum(tr_h, np.abs(rates_h1['low'][1:] - rates_h1['close'][:-1]))
                h1_atr = float(np.mean(tr_h[-14:]))

            # Calibrated robust protective stop distance outside market noise
            distance = compute_robust_stop_distance(symbol, tick, info, m15_atr=m15_atr, h1_atr=h1_atr)
            shared_sl = round(max(0.00001, entry - distance) if action == "BUY"
                              else entry + distance, info.digits)
            requested = default_lot if custom_lots is None else custom_lots
            lot = limit_volume(mt5, info, order_type, symbol, requested,
                               entry, shared_sl, budget, legs=1)
        except (ValueError, TypeError, OverflowError) as exc:
            return reject(str(exc))

        executed, errors, uncertain = [], [], None
        reservation = None
        used_risk = 0.0
        group_id = f"GRP-{time.time_ns()}-{symbol.replace(' ', '')[:6]}"
        import random
        # RULES 1 & 2: Keep 2 TPs only (1.8x & 4.0x), open ONE trade per symbol and randomly allocate one of the two TPs
        tp_choices = [
            (1, 1.8, "TP1-Conservative"),
            (2, 4.0, "TP2-Runner")
        ]
        chosen_leg, chosen_multiple, chosen_label = random.choice(tp_choices)

        # Target distance respects 1.8R and 4.0R multiples of the protective stop distance
        target_distance = max(minimum, distance * chosen_multiple)"""

    target_5_norm = target_5.replace('\r\n', '\n')
    replacement_5_norm = replacement_5.replace('\r\n', '\n')
    if target_5_norm not in content_norm:
        print("ERROR: target_5_norm not found!")
        return False
    content_norm = content_norm.replace(target_5_norm, replacement_5_norm)
    print("SUCCESS: Target 5 replaced.")

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content_norm)
    print("web_app.py updated successfully!")
    return True

if __name__ == '__main__':
    apply_patch()
