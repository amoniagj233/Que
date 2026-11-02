p = r"C:\Users\amoni\OneDrive\Desktop\andoio app.txt"
with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
print(f"andoio app.txt length: {len(text)} chars")
print(text[:1500].encode('ascii', errors='replace').decode('ascii'))
