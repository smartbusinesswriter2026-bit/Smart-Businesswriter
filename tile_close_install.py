import io, re, sys
WEB = r'd:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
BLOCK = r'd:\SMART BUSINESSWRITER\tile_close_block.html'
h = io.open(WEB, encoding='utf-8').read()
blk = io.open(BLOCK, encoding='utf-8').read().strip()
if '<script id="tile-close-shim">' not in blk or '</script>' not in blk:
    sys.exit('the block file must contain the whole <script id="tile-close-shim"> ... </script>')
h = re.sub(r'<script id="tile-close-shim">.*?</script>', '', h, flags=re.S)
i = h.rindex('</body>')
h = h[:i] + '\r\n' + blk + h[i:]
io.open(WEB, 'w', encoding='utf-8', newline='').write(h)
print('installed; shim now at line', h.count('\n', 0, h.index('<script id="tile-close-shim">')) + 1)