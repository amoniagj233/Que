import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('scratch/xto_doc.html', 'r', encoding='utf-8') as f:
    html = f.read()

links = set(re.findall(r'href=[\"\'](.*?)[\"\']', html))
print('Links found:', links)

body = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
body = re.sub(r'<style.*?</style>', '', body, flags=re.DOTALL)
clean = re.sub(r'<[^>]+>', '\n', body)
lines = [l.strip() for l in clean.splitlines() if l.strip()]
print(f'Lines count: {len(lines)}')
for i, l in enumerate(lines[:100]):
    print(f'{i}: {l}')
