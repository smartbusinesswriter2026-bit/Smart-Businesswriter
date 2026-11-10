import re
src = open('src/bp/product/subjects.py', encoding='utf-8', errors='ignore').read()
# Find worksheet entries with subject and title
# Look for patterns like "subject": "accounting" and nearby "title" or "label"
# Let's find the WORKSHEETS dict structure
idx = src.find('WORKSHEETS')
print('WORKSHEETS at:', idx)
# Find all subject->tile mappings
# Look for "subject" key followed by tile info
pattern = re.compile(r'"subject":\s*"([^"]+)"', re.MULTILINE)
subjects = pattern.findall(src)
print('subject references:', len(subjects))
from collections import Counter
print(Counter(subjects))