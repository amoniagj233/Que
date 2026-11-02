import os

for fname in ['run_dual_xto_traders.py', 'xto_upgrade_atr.py']:
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as f:
            content = f.read()
        replacements = {'🚀': '[DUAL]', '💰': '[TP]', '🚨': '[ALERT]', '✅': '[OK]', '❌': '[FAIL]', '⚠️': '[WARN]'}
        for em, txt in replacements.items():
            content = content.replace(em, txt)
        # Ensure utf-8 stdout is at very top
        header = "import sys\nsys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
        if "sys.stdout.reconfigure" not in content:
            content = header + content
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Sanitized {fname}")
