p = "src/bp/product/explain.py"
text = open(p, encoding="utf-8").read()

replacements = [
    ('_section("The method, in plain language"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("Defaults the method applied"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("If your professor asks"', '_section("6. Interpretation"'),
]

for old, new in replacements:
    if old not in text:
        print("NOT FOUND:", old)
    else:
        text = text.replace(old, new, 1)

open(p, "w", encoding="utf-8").write(text)
print("done")
