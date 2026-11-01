import io, re, sys
WEB = r'd:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
h = io.open(WEB, encoding='utf-8').read()
m = re.search(r'<script id="tile-close-shim">.*?</script>', h, re.S)
if not m:
    sys.exit('no shim block found - insert the v3 block first, then rerun this')
blk = m.group(0)
h = h[:m.start()] + h[m.end():]
i = h.rindex('</body>')
h = h[:i] + '\r\n' + blk + h[i:]
io.open(WEB, 'w', encoding='utf-8', newline='').write(h)
print('moved; shim now at line', h.count('\n', 0, h.index('<script id="tile-close-shim">')) + 1)