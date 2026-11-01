content = open('web/index.html', encoding='utf-8', errors='ignore').read()
import re
idx = content.find('$$("[data-worksheet]", out)')
if idx != -1:
    print(content[idx:idx+200])
