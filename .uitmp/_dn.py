import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\DESIGN_NOTES.md'
src = open(p, encoding='utf-8').read().splitlines()
for i, l in enumerate(src, 1):
    if re.search(r'favicon|mark\.png|icon|logo', l, re.I):
        print(i, '|', l[:200])
