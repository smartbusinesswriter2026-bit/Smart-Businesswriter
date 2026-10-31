import re
p = r'D:\SMART BUSINESSWRITER\.uitmp\owner_docs.txt'
for i, l in enumerate(open(p, encoding='utf-8', errors='replace').read().splitlines(), 1):
    if re.search(r'favicon|icon|logo|mark', l, re.I):
        print(i, '|', l[:220])
