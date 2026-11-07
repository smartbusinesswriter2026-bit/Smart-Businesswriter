src = open("src/bp/finance_methods.py", encoding="utf-8").read()
src = src.replace('    _reg(name, fn, "advanced")', '    _reg(name, fn, "advanced", "financial statement computation")')
open("src/bp/finance_methods.py", "w", encoding="utf-8").write(src)
print("fixed")
