import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
html = open(p, encoding='utf-8').read()
for m in re.finditer(r'data:image/(png|svg\+xml);base64,[A-Za-z0-9+/=]+', html):
    line = html[:m.start()].count('\n')+1
    kind = 'svg' if 'svg' in m.group(0)[:20] else 'png'
    # context: 90 chars before
    ctx = html[max(0,m.start()-160):m.start()]
    ctx = ctx.replace('\n',' ')[-120:]
    print(f'line {line} [{kind}] ...{ctx}')
