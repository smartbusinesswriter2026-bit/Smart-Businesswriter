p = "src/bp/product/tier1_tables.py"
text = open(p).read()
text = text.replace("S.RULES_SEED", "S._RULES_SEED")
open(p, "w").write(text)
print("fixed")
