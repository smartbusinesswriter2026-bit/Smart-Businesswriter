def explain(record):
    """Generate a teach-the-student explanation document from a stored record.

    Returns (title, sections) where sections is a list of (heading, lines) tuples
    suitable for docx_export.render_bytes.
    """
    title = "Explanation: " + str(record.get("problem_type", "Financial Statements")).replace("_", " ").title()
    sections = []

    # Problem statement
    instruction = record.get("instruction", "")
    sections.append(("Problem", [instruction]))

    # What was solved
    why = record.get("why", "")
    if why:
        sections.append(("Approach", [why]))

    problem_type = record.get("problem_type", "")
    reading_source = record.get("reading_source", "")
    sections.append(("Solution Summary", [
        "Problem type: " + problem_type.replace("_", " ").title(),
        "Reading source: " + reading_source,
        "Solved: " + str(record.get("solved", False)),
    ]))

    # Key figures
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        lines = []
        for key, val in scalars.items():
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {val}")
        sections.append(("Key Figures", lines))

    # Verification checks (formulas)
    checks = record.get("checks") or []
    if checks:
        lines = []
        for ch in checks:
            if isinstance(ch, dict):
                name = ch.get("name", "")
                ok = "PASS" if ch.get("ok") else "FAIL"
                detail = ch.get("detail", "")
                lines.append(f"{name}: {ok}")
                if detail:
                    lines.append(f"  Formula: {detail}")
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                lines.append(f"{ch[0]}: {'PASS' if ch[1] else 'FAIL'}")
                if len(ch) > 2:
                    lines.append(f"  Formula: {ch[2]}")
        sections.append(("Verification (formulas & checks)", lines))

    # Step-by-step solution
    statements_only = record.get("statements_only", "")
    if statements_only:
        sections.append(("Step-by-Step Solution", statements_only.splitlines()))

    # Assumptions
    reading = record.get("reading") or {}
    assumptions = reading.get("assumptions") or []
    if assumptions:
        lines = []
        for a in assumptions:
            if isinstance(a, dict):
                lines.append(a.get("text", str(a)))
            else:
                lines.append(str(a))
        sections.append(("Assumptions", lines))

    # Missing items (gaps)
    missing = (record.get("working") or {}).get("missing") or []
    if missing:
        lines = []
        for m in missing:
            if isinstance(m, dict):
                lines.append(f"{m.get('what', '')}: {m.get('why', '')}")
            else:
                lines.append(str(m))
        sections.append(("Gaps / Missing Items", lines))

    # Tier-1 gaps (self-healing)
    tier1_gaps = record.get("tier1_gaps") or []
    if tier1_gaps:
        lines = []
        for g in tier1_gaps:
            if isinstance(g, dict):
                lines.append(f"{g.get('what', '')}: {g.get('why', '')}")
            else:
                lines.append(str(g))
        sections.append(("Tier-1 Reading Gaps (self-healing)", lines))

    return title, sections
