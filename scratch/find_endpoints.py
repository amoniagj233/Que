with open('web_app.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'path.startswith(' in line or 'path == ' in line:
            print(f"{i}: {line.strip()[:100]}")
