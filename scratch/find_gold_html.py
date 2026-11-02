with open('web_app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="goldSection"')
if idx != -1:
    print("Found goldSection at:", idx)
    print(text[idx:idx+1500])
else:
    idx2 = text.find('goldTab')
    print("Found goldTab at:", idx2)
    print(text[idx2:idx2+1500])
