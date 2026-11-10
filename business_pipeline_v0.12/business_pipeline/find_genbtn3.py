html = open('web/admin-sbw.html', encoding='utf-8').read()
needle = "healFreeGen').addEventListener"
idx = html.find(needle)
# Find the matching closing - look for log.scrollTop = log.scrollHeight;\n}); after the healFreeGen handler
search = "  log.scrollTop = log.scrollHeight;\n});"
pos = html.find(search, idx)
print('found at:', pos)
result = repr(html[pos:pos+60])
open('genbtn3_result.txt', 'w', encoding='utf-8').write(result)