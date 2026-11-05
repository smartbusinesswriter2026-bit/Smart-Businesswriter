p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
bad = [(i+1, l) for i, l in enumerate(lines) if 1960 <= i+1 <= 2100 and '\\"' in l]
print("escaped-quote lines:", len(bad))
for b in bad[:15]:
    print(b[0], repr(b[1][:80]))
