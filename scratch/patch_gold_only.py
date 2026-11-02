def patch():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Define GOLD_ONLY_MODE = True
    target_mode = '# Asset Class Classifications for Portfolio Heat & Correlation Protection'
    replacement_mode = """# User Directive: Trade Only Gold Today
GOLD_ONLY_MODE = True

# Asset Class Classifications for Portfolio Heat & Correlation Protection"""

    content = content.replace(target_mode, replacement_mode)

    # 2. In run_scan_now, prioritize XAUUSD when GOLD_ONLY_MODE is True
    target_pool = """            # Candidate pool for Headway Quotes (Metals, Forex Majors, Crypto, Synthetic Indices)
            candidate_pool = ["""

    replacement_pool = """            # Candidate pool for Headway Quotes (Metals, Forex Majors, Crypto, Synthetic Indices)
            if GOLD_ONLY_MODE:
                candidate_pool = [
                    {"symbol": "XAUUSD", "category": "Metals (Exclusive Gold Intelligence Active)"}
                ]
            else:
                candidate_pool = ["""

    content = content.replace(target_pool, replacement_pool)

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched web_app.py for Gold Only Mode!")

if __name__ == '__main__':
    patch()
