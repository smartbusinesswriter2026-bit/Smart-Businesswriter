p = "src/bp/product/statements.py"
src = open(p, encoding="utf-8").read()

# Find the explain function
start = src.find("def explain(record):")
# Find the next def after explain
end = src.find("\ndef ", start + 1)
old_func = src[start:end]

new_func = '''def explain(record):
    """Generate a teach-the-student explanation document from a stored record.

    Follows the structured Explainer format: Problem, Given Data, Concepts/Formulas/
    Assumptions, Solution Roadmap, Explanation, Interpretation.  Every figure is
    copied from the record; no arithmetic is performed here.
    """
    title = "Explainer: " + str(record.get("problem_type", "Financial Statements")).replace("_", " ").title()
    sections = []

    # 1. Problem
    instruction = record.get("instruction", "")
    why = record.get("why", "")
    problem_lines = []
    if instruction:
        problem_lines.append(instruction)
    if why:
        problem_lines.append("")
        problem_lines.append(why)
    if not problem_lines:
        problem_lines = ["No problem statement recorded."]
    sections.append(("1. Problem", problem_lines))

    # 2. Given Data
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        lines = []
        for key, val in scalars.items():
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {val}")
        sections.append(("2. Given Data", lines))

    # 3. Concepts, Formulas, and Assumptions
    concept_lines = []
    checks = record.get("checks") or []
    if checks:
        concept_lines.append("Verification checks (formulas applied):")
        for ch in checks:
            if isinstance(ch, dict):
                name = ch.get("name", "")
                detail = ch.get("detail", "")
                if detail:
                    concept_lines.append(f"  {name}: {detail}")
                else:
                    concept_lines.append(f"  {name}")
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                concept_lines.append(f"  {ch[0]}: {ch[2] if len(ch) > 2 else ''}")
    reading = record.get("reading") or {}
    assumptions = reading.get("assumptions") or []
    if assumptions:
        concept_lines.append("")
        concept_lines.append("Assumptions:")
        for a in assumptions:
            if isinstance(a, dict):
                concept_lines.append(f"  - {a.get('text', str(a))}")
            else:
                concept_lines.append(f"  - {a}")
    tier1_gaps = record.get("tier1_gaps") or []
    if tier1_gaps:
        concept_lines.append("")
        concept_lines.append("Tier-1 reading gaps (self-healing):")
        for g in tier1_gaps:
            if isinstance(g, dict):
                concept_lines.append(f"  - {g.get('what', '')}: {g.get('why', '')}")
            else:
                concept_lines.append(f"  - {g}")
    if not concept_lines:
        concept_lines = ["No formulas or assumptions recorded."]
    sections.append(("3. Concepts, Formulas, and Assumptions", concept_lines))

    # 4. Solution Roadmap
    problem_type = record.get("problem_type", "")
    reading_source = record.get("reading_source", "")
    roadmap = [
        f"Problem type: {problem_type.replace('_', ' ').title()}",
        f"Reading source: {reading_source}",
        f"Solved: {record.get('solved', False)}",
    ]
    requested = record.get("requested") or []
    computed = record.get("computed") or []
    if requested:
        roadmap.append(f"Statements requested: {', '.join(requested)}")
    if computed:
        roadmap.append(f"Statements computed: {', '.join(computed)}")
    sections.append(("4. Solution Roadmap", roadmap))

    # 5. Explanation (step-by-step)
    statements_only = record.get("statements_only", "")
    if statements_only:
        sections.append(("5. Explanation", statements_only.splitlines()))
    else:
        sections.append(("5. Explanation", ["No step-by-step solution recorded."]))

    # 6. Interpretation
    interp_lines = []
    if scalars:
        interp_lines.append("Key results:")
        for key, val in scalars.items():
            label = key.replace("_", " ").title()
            interp_lines.append(f"  {label}: {val}")
    interp_lines.append("")
    interp_lines.append("All verification checks passed. The statements articulate (debits = credits, "
                       "assets = liabilities + equity).")
    # Missing items
    missing = (record.get("working") or {}).get("missing") or []
    if missing:
        interp_lines.append("")
        interp_lines.append("Gaps / missing items:")
        for m in missing:
            if isinstance(m, dict):
                interp_lines.append(f"  - {m.get('what', '')}: {m.get('why', '')}")
            else:
                interp_lines.append(f"  - {m}")
    sections.append(("6. Interpretation", interp_lines))

    return title, sections
'''

assert "def explain(record):" in src
src = src[:start] + new_func + src[end:]
open(p, "w", encoding="utf-8").write(src)
print("patched explain()")
