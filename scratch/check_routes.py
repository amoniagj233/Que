with open('web_app.py', encoding='utf-8') as f:
    text = f.read()

print('GET overview in text:', 'elif url.path == "/api/ml/overview":' in text)
print('POST train in text:', 'elif url.path == "/api/ml/train":' in text)
