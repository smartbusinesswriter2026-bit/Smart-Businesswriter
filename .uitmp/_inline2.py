import re, base64, io
from PIL import Image
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
html = open(p, encoding='utf-8').read()
for m in re.finditer(r'data:image/png;base64,([A-Za-z0-9+/=]+)', html):
    if len(m.group(1)) < 3000: continue
    raw = base64.b64decode(m.group(1))
    im = Image.open(io.BytesIO(raw))
    line = html[:m.start()].count('\n')+1
    print('line', line, im.size, im.mode)
