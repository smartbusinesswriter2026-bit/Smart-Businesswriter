import io, sys
WEB = r'd:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
MARK = '<script id="tile-close-shim">'
h = io.open(WEB, encoding='utf-8').read()
def ln(p):
    return h.count('\n', 0, p) + 1
if MARK not in h:
    print('FAIL  no shim block found')
    sys.exit(1)
s = h.index(MARK)
body = h.rindex('</body>')
end = h.rindex('</html>')
opens = h.count('<script', 0, s)
closes = h.count('</script>', 0, s)
print('marker count        :', h.count('tile-close-shim'))
print('shim starts line    :', ln(s))
print('</body> line        :', ln(body))
print('inside a script?    :', opens != closes, '(opens', opens, 'closes', closes, 'before the shim)')
print('before </body>      :', s < body)
print('tags balanced       :', h.count('<script') == h.count('</script>'))
print('app boot() present  :', 'function boot(' in h and 'boot();' in h)
ok = (h.count('tile-close-shim') == 1 and opens == closes and s < body and s < end
      and h.count('<script') == h.count('</script>') and 'boot();' in h)
print('RESULT              :', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)