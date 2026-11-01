content = open('web/index.html', encoding='utf-8', errors='ignore').read()
# Find ensureSubjects and caching
idx = content.find('function ensureSubjects')
if idx != -1:
    print(content[idx:idx+300])
print('====')
# Find subject detail rendering - does it cache?
idx = content.find('RENDERERS.subject')
if idx != -1:
    print(content[idx:idx+400])
