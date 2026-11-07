p = "src/bp/product/explain.py"
text = open(p, encoding="utf-8").read()

replacements = [
    ('"The method, in plain language"', '"3. Concepts, Formulas, and Assumptions"'),
    ('"What the engine returned"', '"5. Explanation"'),
    ('"Defaults the method applied"', '"3. Concepts, Formulas, and Assumptions"'),
    ('"If your professor asks"', '"6. Interpretation"'),
]

for old, new in replacements:
    if old not in text:
        print("NOT FOUND:", old)
    else:
        text = text.replace(old, new, 1)

open(p, "w", encoding="utf-8").write(text)
print("done")
