import re, base64, io, os
from PIL import Image
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
html = open(p, encoding='utf-8').read()
out = r'D:\SMART BUSINESSWRITER\.uitmp\fav_before'
os.makedirs(out, exist_ok=True)
pat = re.compile(r'<link[^>]*rel="(icon|apple-touch-icon)"[^>]*>')
for i, m in enumerate(pat.finditer(html)):
    tag = m.group(0)
    sizes = re.search(r'sizes="([^"]+)"', tag)
    href = re.search(r'href="([^"]+)"', tag)
    data = href.group(1)
    if data.startswith('data:image/png;base64,'):
        raw = base64.b64decode(data.split(',',1)[1])
        fn = os.path.join(out, f'{i}_{m.group(1)}_{sizes.group(1) if sizes else "na"}.png'.replace('x','x'))
        open(fn,'wb').write(raw)
        im = Image.open(io.BytesIO(raw))
        print(m.group(1), sizes.group(1) if sizes else 'na', im.size, im.mode, '->', fn)
