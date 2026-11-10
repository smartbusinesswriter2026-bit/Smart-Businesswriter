import re
src = open('src/bp/product/subjects.py', encoding='utf-8', errors='ignore').read()
# Find subject definitions - look for subject ids and their worksheets
# Search for how subjects are defined
idx = src.find('SUBJECTS')
print('SUBJECTS at:', idx)
chunk = src[idx:idx+3000]
open('subjects_chunk.txt', 'w', encoding='utf-8').write(chunk)
print('written')