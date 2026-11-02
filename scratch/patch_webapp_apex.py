with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """from commander.dashboard import inject as _commander_inject
HTML_PAGE = _commander_inject(HTML_PAGE)"""

replacement = """from commander.dashboard import inject as _commander_inject
from commander.apex_dashboard import inject_apex as _apex_inject
HTML_PAGE = _commander_inject(HTML_PAGE)
HTML_PAGE = _apex_inject(HTML_PAGE)"""

if target in text:
    text = text.replace(target, replacement)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Injected apex_dashboard into web_app.py successfully!")
else:
    print("Target not found in web_app.py")
