with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """def save_multi_tp_groups(groups):
    # Commit the complete file; never expose a partially written JSON document.
    pending = MULTI_TP_FILE.with_suffix(".json.tmp")
    pending.write_text(json.dumps(groups, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(pending, MULTI_TP_FILE)"""

replacement = """def save_multi_tp_groups(groups):
    # Commit the complete file; resilient against OneDrive file-locking on Windows
    payload = json.dumps(groups, indent=2, allow_nan=False)
    pending = MULTI_TP_FILE.with_suffix(".json.tmp")
    try:
        pending.write_text(payload, encoding="utf-8")
        for _ in range(5):
            try:
                os.replace(pending, MULTI_TP_FILE)
                return
            except PermissionError:
                time.sleep(0.05)
    except Exception:
        pass
    # Fallback direct write if os.replace is locked by OneDrive
    try:
        MULTI_TP_FILE.write_text(payload, encoding="utf-8")
        if pending.exists():
            pending.unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning saving multi_tp_groups: {e}")"""

if target in text:
    text = text.replace(target, replacement, 1)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: Updated save_multi_tp_groups with OneDrive resilience.")
else:
    print("Target not found directly, checking normalized...")
    norm_text = text.replace("\r\n", "\n")
    norm_target = target.replace("\r\n", "\n")
    norm_replacement = replacement.replace("\r\n", "\n")
    if norm_target in norm_text:
        norm_text = norm_text.replace(norm_target, norm_replacement, 1)
        with open("web_app.py", "w", encoding="utf-8") as f:
            f.write(norm_text)
        print("SUCCESS (normalized line endings)")
    else:
        print("Target not found.")
