import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\scripts\ci.py'
src = open(p, encoding='utf-8').read()
print(len(src.splitlines()), 'lines')
for m in re.finditer(r'def (\w+)\(', src):
    print('  def', m.group(1))
