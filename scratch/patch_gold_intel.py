def patch_gold_intel():
    with open('gold_intelligence.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add atr_h1 and min_gold_stop after line 501
    target = """    cur_p = float(df_m15["close"].iloc[-1])
    atr_m15 = float(compute_atr(df_m15, 14).iloc[-1])
    rsi_m15 = float(compute_rsi(df_m15["close"], 14).iloc[-1])
    
    h1_regime = analyze_market_regime(df_h1)"""

    replacement = """    cur_p = float(df_m15["close"].iloc[-1])
    atr_m15 = float(compute_atr(df_m15, 14).iloc[-1])
    atr_h1 = float(compute_atr(df_h1, 14).iloc[-1]) if len(df_h1) >= 15 else 10.0
    # Robust noise floor on Gold: at least $5.00/oz or 1.8x H1 ATR
    min_gold_stop = max(5.00, atr_h1 * 1.8)
    rsi_m15 = float(compute_rsi(df_m15["close"], 14).iloc[-1])
    
    h1_regime = analyze_market_regime(df_h1)"""

    content = content.replace(target, replacement)

    # Model 1 Bull
    content = content.replace(
        'sl = round(ob["bottom"] - 1.5 * atr_m15, 2)',
        'sl = round(min(ob["bottom"] - 1.5 * atr_m15, entry - min_gold_stop), 2)'
    )

    # Model 1 Bear
    content = content.replace(
        'sl = round(ob["top"] + 1.5 * atr_m15, 2)',
        'sl = round(max(ob["top"] + 1.5 * atr_m15, entry + min_gold_stop), 2)'
    )

    # Model 2 Bull
    content = content.replace(
        'sl = round(sweep["sweep_low"] - 1.0 * atr_m15, 2)',
        'sl = round(min(sweep["sweep_low"] - 1.0 * atr_m15, entry - min_gold_stop), 2)'
    )

    # Model 2 Bear
    content = content.replace(
        'sl = round(sweep["sweep_high"] + 1.0 * atr_m15, 2)',
        'sl = round(max(sweep["sweep_high"] + 1.0 * atr_m15, entry + min_gold_stop), 2)'
    )

    # Model 3 Bull
    content = content.replace(
        'sl = round(ema50_m15 - 2.0 * atr_m15, 2)',
        'sl = round(min(ema50_m15 - 2.0 * atr_m15, cur_p - min_gold_stop), 2)'
    )

    # Model 3 Bear
    content = content.replace(
        'sl = round(ema50_m15 + 2.0 * atr_m15, 2)',
        'sl = round(max(ema50_m15 + 2.0 * atr_m15, cur_p + min_gold_stop), 2)'
    )

    with open('gold_intelligence.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("gold_intelligence.py updated successfully!")

if __name__ == '__main__':
    patch_gold_intel()
