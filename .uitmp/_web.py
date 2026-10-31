import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\src\bp\server.py'
for l in open(p, encoding='utf-8').read().splitlines():
    if re.search(r'^\s*WEB\s*=|^\s*ROOT\s*=|Path\(__file__\)', l):
        print(l.strip()[:180])
