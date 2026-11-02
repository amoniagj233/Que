with open('web_app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "txt.innerText = 'ENABLED (ACTIVE)';"
replacement = "txt.innerText = 'AUTO-TRADING ACTIVE (1 Symbol at a Time)';"

if target in text:
    text = text.replace(target, replacement, 1)
    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('SUCCESS')
else:
    print('Target not found')
