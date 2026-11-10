html = open('web/admin-sbw.html', encoding='utf-8').read()
needle = 'class="rail" id="rail"'
idx = html.find(needle)
result = repr(html[idx:idx+300])
open('rail8_result.txt', 'w', encoding='utf-8').write(result)