p = r"C:\Users\amoni\OneDrive\Desktop\PATTEN.txt"
with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
print(f"PATTEN.txt length: {len(text)} chars, {len(text.splitlines())} lines")
print(text[:2000])
