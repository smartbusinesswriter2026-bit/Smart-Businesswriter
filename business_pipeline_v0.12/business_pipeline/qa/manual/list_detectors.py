import re
src = open("src/bp/statement_detect.py").read()
for m in re.finditer(r'Detector\("([^"]+)"', src):
    print(m.group(1))
