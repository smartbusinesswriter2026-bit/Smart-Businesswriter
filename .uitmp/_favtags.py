import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
html = open(p, encoding='utf-8').read()
for m in re.finditer(r'<link[^>]*rel="[^"]*(icon|manifest)[^"]*"[^>]*>', html, re.I):
    t = m.group(0)
    print('LINE', html[:m.start()].count('\n')+1, '|', re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,<...>', t)[:260])
