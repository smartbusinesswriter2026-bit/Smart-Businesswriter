html = open('web/admin-sbw.html', encoding='utf-8').read()
# Find the healFreeGen button
needle = 'id="healFreeGen"'
idx = html.find(needle)
result = repr(html[max(0,idx-60):idx+80])
open('genbtn_result.txt', 'w', encoding='utf-8').write(result)