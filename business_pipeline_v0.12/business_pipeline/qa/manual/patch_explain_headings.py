p = "src/bp/product/explain.py"
src = open(p, encoding="utf-8").read()

replacements = [
    ('_section("The question"', '_section("1. Problem"'),
    ('_section("What you declared"', '_section("2. Given Data"'),
    ('_section("Why this method"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("Common mistakes"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("What the engine returned"', '_section("5. Explanation"'),
    ('_section("What the result means"', '_section("5. Explanation"'),
    ('_section("Assumptions (as recorded)"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("Defaults the method applied"', '_section("3. Concepts, Formulas, and Assumptions"'),
    ('_section("Limits and what this does not prove"', '_section("6. Interpretation"'),
    ('_section("What this method is not for"', '_section("6. Interpretation"'),
    ('_section("If your professor asks"', '_section("6. Interpretation"'),
    ('_section("For the record"', '_section("2. Given Data"'),
]

for old, new in replacements:
    if old not in src:
        print("NOT FOUND:", old)
    else:
        src = src.replace(old, new, 1)

# Add "4. Solution Roadmap" section after "2. Given Data" section.
old_roadmap = '    sections = [\n        _section("1. Problem", paragraphs=[_text(objective)]),\n'
new_roadmap = ('    sections = [\n'
               '        _section("1. Problem", paragraphs=[_text(objective)]),\n'
               '        _section("4. Solution Roadmap", paragraphs=[\n'
               '            "Method: " + label + " (" + (contract.get("tier") or "recorded") + " method).",\n'
               '            "The frozen method performed the arithmetic. These are the values it recorded; "\n'
               '            "this document quotes them and does not recalculate them.",\n'
               '        ]),\n')
assert old_roadmap in src, "roadmap anchor not found"
src = src.replace(old_roadmap, new_roadmap, 1)

open(p, "w", encoding="utf-8").write(src)
print("patched explain.py headings")
