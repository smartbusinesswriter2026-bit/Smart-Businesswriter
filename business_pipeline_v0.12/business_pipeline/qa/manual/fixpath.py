src = open("qa/manual/patch_portfolios.py").read()
src = src.replace('open(p, "w", encoding="utf-8").write(src)', 'open("src/bp/product/portfolios.py", "w", encoding="utf-8").write(src)')
open("qa/manual/patch_portfolios.py", "w").write(src)
print("fixed")
