html = open('web/admin-sbw.html', encoding='utf-8').read()
needle = "healFreeGen').addEventListener('click', async () => {"
idx = html.find(needle)
result = repr(html[idx:idx+200])
open('genbtn2_result.txt', 'w', encoding='utf-8').write(result)