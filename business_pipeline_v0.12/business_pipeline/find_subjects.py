import re
src = open('src/bp/product/subjects.py', encoding='utf-8', errors='ignore').read()
# Find WORKSHEETS entries
matches = re.findall(r'"id":\s*"([^"]+)"', src)
print('ids found:', len(matches))
# Find unique subject-like ids
unique = sorted(set(matches))
print(unique[:50])