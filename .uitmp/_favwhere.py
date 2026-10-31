import re, glob, os
files = [
 r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html',
 r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\preview.html',
 r'D:\SMART BUSINESSWRITER\miniapps\rail-label-options\miniapp\client\index.html',
]
for p in files:
    if not os.path.exists(p):
        print('MISSING', p); continue
    html = open(p, encoding='utf-8').read()
    hits = re.findall(r'<link[^>]*rel="[^"]*(?:icon|apple-touch)[^"]*"[^>]*>', html, re.I)
    print(os.path.basename(p), '->', len(hits), 'icon link(s)')
    for h in hits:
        print('   ', re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,<DATA>', h)[:200])
