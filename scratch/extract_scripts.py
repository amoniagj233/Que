import re

with open('web_app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract script blocks
scripts = re.findall(r'<script>(.*?)</script>', text, re.DOTALL)
print(f"Found {len(scripts)} inline script blocks.")

for i, s in enumerate(scripts):
    filename = f"scratch/script_{i}.js"
    with open(filename, 'w', encoding='utf-8') as sf:
        sf.write(s)
    print(f"Wrote {filename} ({len(s)} chars)")
