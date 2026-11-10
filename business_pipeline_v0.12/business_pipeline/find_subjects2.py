import re
src = open('src/bp/product/subjects.py', encoding='utf-8', errors='ignore').read()
# Find subject-related definitions
for keyword in ['subjects', 'SUBJECT', 'def subjects', 'subject_id', 'subject list']:
    idx = src.lower().find(keyword.lower())
    if idx != -1:
        print(f'{keyword} at {idx}: {src[idx:idx+80].replace(chr(10), " ")}')