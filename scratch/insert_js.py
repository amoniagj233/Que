with open('scratch/ml_js_controller.js', encoding='utf-8') as f:
    js_code = f.read()

with open('web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = "setInterval(() => { if (currentMainTab === 'gold') loadGoldDashboard(); }, 5000);"
replacement = js_code + "\n\n    setInterval(() => { if (currentMainTab === 'gold') loadGoldDashboard(); }, 5000);\n    setInterval(() => { if (currentMainTab === 'ml') loadMLDashboard(); }, 5000);"

if target in content and 'function loadMLDashboard' not in content:
    content = content.replace(target, replacement, 1)
    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: JS Controller inserted into web_app.py')
else:
    print('Target not found or already present')
