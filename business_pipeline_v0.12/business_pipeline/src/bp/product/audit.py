"""Audit and repair helpers for the Home chat conductor.

The audit stage is read-only: it checks a draft against the paper contract, the
plan, the evidence ledger and the rubric, and returns findings. It never edits.
The repair stage acts on those findings with targeted changes.

Rules this module keeps:
- deterministic checks first; the LLM auditor is optional and read-only;
- no formula and no number invented by the model;
- fail closed: an unresolved finding blocks export;
- no silent repair: every repair is named and re-audited.
"""

FORMAT = "bp-audit/1"

SEVERITY = ("info", "warning", "blocking")


def _normalise(text):
    return " ".join(str(text or "").split()).strip()


def _lower_list(value):
    return [str(item).strip().lower() for item in (value or []) if str(item).strip()]


def _word_count(text):
    return len(str(text or "").split())


def _flatten_sections(sections):
    lines = []
    headings = []
    for item in sections or []:
        if isinstance(item, dict):
            headings.append(str(item.get("heading") or "").strip())
            for line in item.get("lines") or []:
                lines.append(str(line))
            figure = item.get("figure")
            if figure:
                lines.append(str(figure.get("caption") or ""))
                lines.append(str(figure.get("note") or ""))
        elif isinstance(item, (list, tuple)) and item:
            headings.append(str(item[0]))
            for line in (item[1] if len(item) > 1 else []) or []:
                lines.append(str(line))
    return headings, lines


def _overclaim_words():
    return ("proves", "proven", "guarantees", "definitely", "conclusive",
            "confirms that", "demonstrates that", "establishes that")


def audit(contract, plan=None, evidence=None, computations=None, draft=None,
          rubric_coverage=None, forbidden_terms=None):
    """Return an audit report. An empty findings list means the paper passes."""
    findings = []
    contract = contract or {}
    plan = plan or {}
    evidence = evidence or {}
    computations = computations or {}
    draft = draft or {}
    sections = draft.get("sections") if isinstance(draft, dict) else draft
    headings, lines = _flatten_sections(sections)
    text = "\n".join(lines)

    # 1. Contract approval.
    if not contract.get("approved"):
        findings.append({"severity": "blocking", "code": "contract_not_approved",
                         "message": "the paper contract is not approved"})

    # 2. Required sections.
    required = contract.get("required_sections") or []
    for section in required:
        if section not in headings:
            findings.append({"severity": "blocking", "code": "missing_section",
                             "message": "missing required section: " + str(section)})

    # 3. Template text.
    template_markers = ("(your analysis)", "not supplied yet", "template", "placeholder", "lorem ipsum")
    low = text.lower()
    for marker in template_markers:
        if marker in low:
            findings.append({"severity": "blocking", "code": "template_text",
                             "message": "template text found: " + marker})

    # 4. Overclaims.
    for word in _overclaim_words():
        if word in low:
            findings.append({"severity": "warning", "code": "overclaim",
                             "message": "possible overclaim: " + word})

    # 5. Length band.
    length = str(contract.get("length") or "").strip().lower()
    bands = {"short": (600, 1200), "mid": (1200, 2500), "long": (2500, 5000)}
    if length in bands:
        low_bound, high_bound = bands[length]
        count = _word_count(text)
        if count < low_bound:
            findings.append({"severity": "warning", "code": "too_short",
                             "message": "draft is shorter than the " + length + " band (" + str(count) + " words)"})
        if count > high_bound:
            findings.append({"severity": "warning", "code": "too_long",
                             "message": "draft is longer than the " + length + " band (" + str(count) + " words)"})

    # 6. Forbidden terms (subject names, home exchange, home country).
    forbidden = forbidden_terms or []
    for term in forbidden:
        term = str(term).strip()
        if not term:
            continue
        # Word-boundary match so "PSE" does not fire on "DeepSeek" and
        # "PSEi" does not fire on an ordinary word containing those letters.
        import re
        if re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", low):
            findings.append({"severity": "blocking", "code": "forbidden_term",
                             "message": "forbidden term found: " + term})

    # 7. Rubric coverage.
    coverage = rubric_coverage or (contract.get("rubric") or {}).get("coverage") or []
    for item in coverage:
        if isinstance(item, dict) and not item.get("covered"):
            findings.append({"severity": "warning", "code": "rubric_gap",
                             "message": "rubric item not covered: " + str(item.get("item") or item)})

    # 8. Plan completeness.
    blocks = plan.get("blocks") if isinstance(plan, dict) else None
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if not str(block.get("contribution") or "").strip() and block.get("kind") not in ("prose",):
                findings.append({"severity": "warning", "code": "block_no_contribution",
                                 "message": "block has no contribution to the thesis: " + str(block.get("id") or block.get("ref"))})
        # synthesis required when more than one analysis block
        analysis_blocks = [b for b in blocks if isinstance(b, dict) and b.get("kind") in ("framework", "computation")]
        synthesis_blocks = [b for b in blocks if isinstance(b, dict) and b.get("kind") == "prose" and b.get("ref") == "synthesis"]
        if len(analysis_blocks) > 1 and not synthesis_blocks:
            findings.append({"severity": "blocking", "code": "missing_synthesis",
                             "message": "a paper with more than one analysis block needs a synthesis block"})

    # 9. Evidence ledger resolution.
    claims = evidence.get("claims") if isinstance(evidence, dict) else None
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if not claim.get("source_ids") and claim.get("type") == "external":
                findings.append({"severity": "blocking", "code": "unresolved_claim",
                                 "message": "external claim has no source: " + str(claim.get("id"))})
    numbers = evidence.get("numbers") if isinstance(evidence, dict) else None
    if isinstance(numbers, list):
        for number in numbers:
            if not isinstance(number, dict):
                continue
            if not number.get("computation") and not number.get("student_input"):
                findings.append({"severity": "blocking", "code": "unresolved_number",
                                 "message": "number has no computation or student input: " + str(number.get("id"))})
    charts = evidence.get("charts") if isinstance(evidence, dict) else None
    if isinstance(charts, list):
        for chart in charts:
            if not isinstance(chart, dict):
                continue
            if not chart.get("artifact_ids"):
                findings.append({"severity": "blocking", "code": "unresolved_chart",
                                 "message": "chart has no artifact source: " + str(chart.get("id"))})

    # 10. Completeness contract.
    archetype_key = str(contract.get("archetype") or "").strip().lower()
    from . import paper_families
    completeness = paper_families.completeness_for(archetype_key)
    # The completeness list is a checklist for the student/author; here we only
    # record that it exists and is non-empty for a known archetype.
    if archetype_key and not completeness:
        findings.append({"severity": "info", "code": "no_completeness_contract",
                         "message": "archetype has no completeness contract: " + archetype_key})

    blocking = [f for f in findings if f.get("severity") == "blocking"]
    return {
        "format": FORMAT,
        "passed": not blocking,
        "blocking_count": len(blocking),
        "findings": findings,
    }


def repair_suggestions(report):
    """Return a list of targeted repair actions for an audit report."""
    actions = []
    for finding in (report or {}).get("findings") or []:
        code = finding.get("code")
        if code == "missing_section":
            actions.append("add the missing section: " + str(finding.get("message")))
        elif code == "template_text":
            actions.append("remove template text: " + str(finding.get("message")))
        elif code == "unresolved_claim":
            actions.append("attach a source to the claim or remove it: " + str(finding.get("message")))
        elif code == "unresolved_number":
            actions.append("declare the figure or remove the number: " + str(finding.get("message")))
        elif code == "unresolved_chart":
            actions.append("attach an artifact to the chart or remove it: " + str(finding.get("message")))
        elif code == "missing_synthesis":
            actions.append("add a synthesis block that reconciles the analysis blocks")
        elif code == "overclaim":
            actions.append("soften the overclaim: " + str(finding.get("message")))
        elif code == "forbidden_term":
            actions.append("remove the forbidden term: " + str(finding.get("message")))
        elif code == "contract_not_approved":
            actions.append("approve the paper contract before drafting")
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique.append(action)
    return unique


def production_check(contract, plan):
    """Dry-run a plan against its contract. Return an audit-style report."""
    findings = []
    contract = contract or {}
    plan = plan or {}
    blocks = plan.get("blocks") if isinstance(plan, dict) else None
    if not isinstance(blocks, list) or not blocks:
        findings.append({"severity": "blocking", "code": "no_blocks", "message": "the plan has no blocks"})
        blocks = blocks or []
    allowed_kinds = {"framework", "computation", "chart", "evidence", "prose", "audit", "profile"}
    ids = set()
    for block in blocks:
        if not isinstance(block, dict):
            findings.append({"severity": "blocking", "code": "bad_block", "message": "a block must be an object"})
            continue
        if not str(block.get("id") or "").strip():
            findings.append({"severity": "blocking", "code": "missing_block_id", "message": "a block is missing an id"})
        else:
            if block["id"] in ids:
                findings.append({"severity": "blocking", "code": "duplicate_block_id", "message": "duplicate block id: " + str(block["id"])})
            ids.add(block["id"])
        kind = str(block.get("kind") or "").strip().lower()
        if kind not in allowed_kinds:
            findings.append({"severity": "blocking", "code": "unknown_block_kind", "message": "unknown block kind: " + str(block.get("kind"))})
        if not str(block.get("ref") or "").strip():
            findings.append({"severity": "blocking", "code": "missing_block_ref", "message": "block is missing a ref: " + str(block.get("id"))})
        if not str(block.get("role") or "").strip():
            findings.append({"severity": "blocking", "code": "missing_block_role", "message": "block is missing a role: " + str(block.get("id"))})
        if not str(block.get("contribution") or "").strip() and kind not in ("prose", "audit"):
            findings.append({"severity": "warning", "code": "block_no_contribution", "message": "block has no contribution: " + str(block.get("id"))})
        # chart legality
        if kind == "chart":
            spec = block.get("spec") or {}
            if not isinstance(spec, dict) or not spec:
                findings.append({"severity": "blocking", "code": "missing_chart_spec", "message": "chart block is missing a spec: " + str(block.get("id"))})
            if not (block.get("source_artifacts") or (spec.get("source_artifacts") if isinstance(spec, dict) else None)):
                findings.append({"severity": "blocking", "code": "chart_no_artifact", "message": "chart block has no source artifact: " + str(block.get("id"))})
    # dependency cycle check
    dependencies = plan.get("dependencies") if isinstance(plan, dict) else None
    if isinstance(dependencies, list):
        graph = {}
        for edge in dependencies:
            if isinstance(edge, (list, tuple)) and len(edge) >= 2:
                graph.setdefault(str(edge[1]), set()).add(str(edge[0]))
        # detect cycle via DFS
        state = {}
        def visit(node):
            if state.get(node) == 1:
                return True
            if state.get(node) == 2:
                return False
            state[node] = 1
            for dep in graph.get(node, ()):
                if visit(dep):
                    return True
            state[node] = 2
            return False
        for node in list(graph):
            if visit(node):
                findings.append({"severity": "blocking", "code": "dependency_cycle", "message": "the plan has a dependency cycle"})
                break
    # required sections
    required = contract.get("required_sections") if isinstance(contract, dict) else None
    section_order = plan.get("section_order") if isinstance(plan, dict) else None
    if isinstance(required, list) and isinstance(section_order, list):
        missing_sections = [s for s in required if s not in section_order]
        for section in missing_sections:
            findings.append({"severity": "warning", "code": "missing_section_in_order", "message": "required section not in section_order: " + str(section)})
    # length feasibility
    length = str((contract or {}).get("length") or "").strip().lower()
    if length and length not in ("short", "mid", "long"):
        findings.append({"severity": "blocking", "code": "bad_length", "message": "unknown length band: " + length})
    blocking = [f for f in findings if f.get("severity") == "blocking"]
    return {"format": FORMAT, "passed": not blocking, "blocking_count": len(blocking), "findings": findings}


def is_clean(report):
    return isinstance(report, dict) and not any(f.get("severity") == "blocking" for f in (report.get("findings") or []))
