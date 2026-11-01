content = open('web/index.html', encoding='utf-8', errors='ignore').read()
import re
# Find capabilityCard function
idx = content.find('function capabilityCard')
if idx != -1:
    print(content[idx:idx+1200])
else:
    print("capabilityCard not found")
    # Search differently
    for m in re.finditer(r'capabilityCard', content):
        print(m.group(0))
        start = max(0, m.start()-50)
        print(content[start:m.start()+200])
        break
