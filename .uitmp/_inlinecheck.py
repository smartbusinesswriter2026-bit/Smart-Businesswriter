"""Confirm the inlined data URIs in index.html decode to the generated PNGs."""
import base64
import hashlib
import io
import re

import numpy as np
from PIL import Image

PAGE = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
ASSETS = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets'

html = open(PAGE, encoding='utf-8').read()
links = re.findall(
    r'<link rel="(?:icon|apple-touch-icon)"[^>]*?sizes="(\d+x\d+)"[^>]*?href="data:image/png;base64,([^"]*)"',
    html,
)
print('icon links found in the page:', len(links))

for sizes, b64 in links:
    size = int(sizes.split('x')[0])
    raw = base64.b64decode(b64)
    on_disk = open(rf'{ASSETS}\favicon-{size}.png', 'rb').read()
    same = hashlib.sha256(raw).hexdigest() == hashlib.sha256(on_disk).hexdigest()
    im = Image.open(io.BytesIO(raw))
    a = np.asarray(im.convert('RGBA'))
    corners = [tuple(int(v) for v in a[y, x]) for (x, y) in
               ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
    print('  %-6s bytes=%-6d matches file on disk=%s  mode=%s size=%s corners=%s'
          % (sizes, len(raw), same, im.mode, im.size, corners))

# the old icons must be gone
old = re.findall(r'<link rel="(?:icon|apple-touch-icon)"[^>]*?>(?!<)', html)
print('total icon link tags:', len(re.findall(r'<link rel="(?:icon|apple-touch-icon)"', html)))

# wordmark must not be in the favicon
print('wordmark "Smart BusinessWriter" bytes inside any favicon payload:',
      any(b'Smart BusinessWriter' in base64.b64decode(b) for _, b in links))
