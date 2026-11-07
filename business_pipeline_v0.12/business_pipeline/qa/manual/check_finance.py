import re
src = open("src/bp/finance_methods.py", encoding="utf-8").read()
funcs = re.findall(r"def (\w+)", src)
print("total functions:", len(funcs))
ids = re.findall(r'_reg\("([^"]+)"', src)
print("registered methods:", len(ids))
print(ids)
