p = r"C:\Users\amoni\OneDrive\Desktop\PATTEN.txt"
with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
print(text[2000:].encode('ascii', errors='replace').decode('ascii'))
