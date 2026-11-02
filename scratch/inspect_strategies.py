with open('gold_intelligence.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'MODEL |strategy":', text)]
for idx in matches:
    print(text[idx-20:idx+80].split('\n')[0])
