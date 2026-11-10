src = open('src/bp/product/subjects.py', encoding='utf-8', errors='ignore').read()
idx = src.find('WORKSHEETS')
chunk = src[idx:idx+2000]
open('worksheets_chunk.txt', 'w', encoding='utf-8').write(chunk)
print('written')