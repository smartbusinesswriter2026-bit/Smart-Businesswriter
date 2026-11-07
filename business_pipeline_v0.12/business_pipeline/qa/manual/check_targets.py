src = open("src/bp/product/explain.py", encoding="utf-8").read()
targets = ['_section("The method, in plain language"', '_section("Common mistakes"', '_section("What the result means"', '_section("The question"', '_section("What you declared"', '_section("Why this method"']
for t in targets:
    print(t, "->", t in src)
