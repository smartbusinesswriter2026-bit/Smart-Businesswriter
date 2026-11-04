content = open('web/index.html', encoding='utf-8', errors='ignore').read()
import re
# Find the renderSubject function's binding section
idx = content.find('bindSubjectCards(out)')
if idx != -1:
    start = max(0, idx-500)
    print(content[start:idx+300])
