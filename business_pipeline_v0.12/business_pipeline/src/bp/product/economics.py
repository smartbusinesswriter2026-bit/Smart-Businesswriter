"""The economics service tiles: one selected problem type, declared figures, a solution.

The financial-statements tile is the model: the student states the problem, the
pipeline computes it and returns the working.  These tiles keep the problem type
explicit (a dropdown) because economics problems are too varied for a single
free-text classifier to be reliable.  A gate refuses an instruction that does not
match the selected type, so the solver never answers a different question from
the one the student asked.

The module holds no formula and no economic fact of its own.  Every computation
is the frozen method the Economics shelf already uses, injected through
``set_runner`` from ``bp.server`` (the product layer may not import the core).
"""

import re

from . import docx, paper, subjects

FORMAT = "bp-economics/1"

#: The problem types each service tile offers.  The keys are the shelf's own
#: tool keys, so the service and the individual calculator cannot drift.
SERVICES = {
    "macroeconomics": ["nationalincome", "growth", "inflation", "unemployment",
                       "moneymultiplier", "fiscal", "budgetdebt", "okun"],
    "microeconomics": ["equilibrium", "elasticity", "taxincidence", "pricecontrol",
                       "concentration", "costcurves", "profitmax", "marketpower",
                       "pricediscrimination", "cournot", "nash"],
    "managerial_economics": ["pricing", "demandcurve", "cba", "cea", "sroi",
                             "breakeven", "multibreakeven", "unitecon"],
}

LABELS = {
    "macroeconomics": "Macroeconomics",
    "microeconomics": "Microeconomics",
    "managerial_economics": "Managerial economics",
}

#: A word that carries no matching signal.  The gate is deliberately generous:
#: it refuses a clearly unrelated problem, not a paraphrase.
_STOP = frozenset(
    "the a an and or of for to in on at by with from is are be as its it this that "
    "what which who how when where why given find compute calculate solve show "
    "using use problem question case firm market".split())

RUN = None
DESCRIBE = None


class EconomicsError(ValueError):
    """The tile refuses the request; the message is what the student is shown."""


def set_runner(run, describe=None):
    """Inject the frozen core, exactly as the statements tile does."""
    global RUN, DESCRIBE
    RUN = run
    DESCRIBE = describe


def _describe(method):
    if DESCRIBE is None:
        return {}
    try:
        return dict(DESCRIBE(method) or {})
    except (KeyError, ValueError, TypeError):
        return {}


def _fields(method):
    schema = (_describe(method).get("input_schema") or {})
    out = []
    for key, spec in schema.items():
        spec = spec if isinstance(spec, dict) else {}
        out.append({"key": key, "label": spec.get("desc") or key.replace("_", " "),
                    "type": spec.get("type") or "decimal",
                    "required": bool(spec.get("required", True))})
    return out


def problem_types(service):
    """The labelled problem types one service tile offers, with their input fields."""
    key = str(service or "").strip().lower()
    if key not in SERVICES:
        raise EconomicsError("Unknown economics service: " + str(service))
    out = []
    for tool_key in SERVICES[key]:
        info = subjects.TOOL_INFO.get(tool_key) or {}
        if not info:
            continue
        out.append({"key": tool_key, "label": info.get("label") or tool_key,
                    "what": info.get("what") or "", "method": info.get("method"),
                    "fields": _fields(info.get("method"))})
    return out


def _tokens(text):
    return {word for word in re.findall(r"[a-z]{3,}", str(text or "").lower())
            if word not in _STOP}


def _matches(instruction, problem):
    """True when the instruction names the selected problem's own vocabulary.

    An empty instruction is not gated: the student may solve from the figures
    alone.  A non-empty instruction must share at least one significant word with
    the problem's label or description; otherwise the tile refuses rather than
    answering a different question.
    """
    text = _tokens(instruction)
    if not text:
        return True
    wanted = _tokens(problem.get("label")) | _tokens(problem.get("what"))
    return bool(text & wanted)


def _number(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _fmt(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    number = _number(value)
    if number is not None:
        if abs(number - round(number)) < 1e-9:
            return "{:,.0f}".format(number)
        return "{:,.4f}".format(number).rstrip("0").rstrip(".")
    return str(value)


def _label_for(problem, key):
    for field in problem.get("fields") or []:
        if field.get("key") == key:
            return field.get("label") or key
    return str(key).replace("_", " ").capitalize()


def _clean_label(field):
    label = str((field or {}).get("label") or "").strip()
    for marker in (", default", " (optional)", "(optional)"):
        if marker in label:
            label = label.split(marker, 1)[0].strip()
    return label


def _labels(field):
    """The names a student may use for one field, longest first."""
    key = str((field or {}).get("key") or "")
    out = []
    label = _clean_label(field)
    if label:
        out.append(label)
    words = key.replace("_", " ").strip()
    if words and words not in out:
        out.append(words)
    from . import problem_reader
    for alias in problem_reader.SYNONYMS.get(key, ()):
        if alias not in out:
            out.append(alias)
    return sorted(out, key=len, reverse=True)


def _read_figures(problem, instruction):
    """Read the declared figures from the instruction, by the field's own name.

    This is deterministic: a figure is read only when its field label (or the
    field key written as words) is immediately followed by a number.  It never
    guesses which number belongs to which field, and a field it cannot find stays
    a named gap.
    """
    text = str(instruction or "")
    found = {}
    if not text:
        return found
    for field in sorted(problem.get("fields") or [], key=lambda row: len(_clean_label(row)), reverse=True):
        if field.get("key") in found:
            continue
        for label in _labels(field):
            pattern = (r"(?i)\b" + re.escape(label) + r"\b\s*(?:[:=]|is|of|was|are)?\s*"
                       r"(-?[\d,]+(?:\.\d+)?)")
            match = re.search(pattern, text)
            if match:
                found[field["key"]] = match.group(1).replace(",", "")
                break
    return found


def _result_lines(problem, result, inputs=None):
    inputs = inputs or {}
    if isinstance(result, dict):
        lines = []
        for key, value in result.items():
            if key.startswith("_") or value is None or key in inputs:
                continue
            if isinstance(value, (dict, list)):
                continue
            lines.append(_label_for(problem, key) + ": " + _fmt(value))
        return lines or ["The method returned no printable value."]
    return [_fmt(result)]


def _sections(problem, service, inputs, result, instruction):
    described = _describe(problem.get("method"))
    label = problem.get("label") or problem.get("key")
    title = LABELS.get(service, "Economics") + ": " + label
    sections = []

    problem_text = ("The problem is a " + label.lower() + " question. "
                    + (instruction.strip() + " " if str(instruction or "").strip() else "")
                    + (described.get("intended_use") or problem.get("what") or ""))
    sections.append(paper.section("Problem", paper.H1, [paper.paragraph([problem_text])]))

    method_text = ("The method is " + label + ". "
                   + (described.get("intended_use") or problem.get("what") or "")
                   + " It is run once by the frozen core from the figures you declared.")
    sections.append(paper.section("Method", paper.H1, [paper.paragraph([method_text])]))

    declared = [(_label_for(problem, key) + ": " + _fmt(value)) for key, value in inputs.items()]
    sections.append(paper.section("Declared figures", paper.H2, [paper.paragraph(declared or ["No figures were declared."])]))

    result_lines = _result_lines(problem, result, inputs)
    sections.append(paper.section("Computation and result", paper.H1,
                                  [paper.paragraph(result_lines)]))

    interpretation = (described.get("intended_use") or problem.get("what")
                      or "The result is the method's own answer to the declared figures.")
    interpretation += (" Read it at the method's own claim level: "
                       + str(described.get("claim_ceiling") or "descriptive") + ".")
    sections.append(paper.section("Economic interpretation", paper.H1,
                                  [paper.paragraph([interpretation])]))

    assumptions = list(described.get("assumptions") or [])
    limitations = list(described.get("limitations") or [])
    if assumptions:
        sections.append(paper.section("Assumptions", paper.H1, [paper.paragraph(assumptions)]))
    if limitations:
        sections.append(paper.section("Limitations", paper.H1, [paper.paragraph(limitations)]))

    sections.append(paper.section("References", paper.H1, ["No sources were used."]))
    return title, sections, interpretation, assumptions, limitations


def solve(service, problem_key, figures=None, instruction=""):
    """Run one selected problem type and return the solution and its Word file."""
    key = str(service or "").strip().lower()
    if key not in SERVICES:
        raise EconomicsError("Unknown economics service: " + str(service))
    types = {row["key"]: row for row in problem_types(key)}
    problem = types.get(str(problem_key or "").strip())
    if problem is None:
        raise EconomicsError("Choose one of the problem types this tile offers: "
                             + ", ".join(sorted(types)))
    if instruction and not _matches(instruction, problem):
        raise EconomicsError("The instruction does not look like " + problem["label"]
                             + ". Choose the matching problem type, or rephrase the problem "
                               "so it names what you are solving.")
    parsed = _read_figures(problem, instruction)
    inputs = dict(parsed)
    for field_key, value in (figures or {}).items():
        if value not in (None, ""):
            inputs[str(field_key)] = str(value).strip()
    missing = [(_clean_label(field) or field["key"]) for field in problem.get("fields") or []
               if field.get("required") and field["key"] not in inputs]
    if missing:
        raise EconomicsError("The instruction does not state: " + "; ".join(missing)
                             + ". Add those figures, or enter them under Enter figures manually.")
    if RUN is None:
        raise EconomicsError("The computation core is not attached on this server.")
    try:
        result = RUN(problem["method"], inputs)
    except Exception as error:
        raise EconomicsError(str(error)[:400])
    title, sections, interpretation, assumptions, limitations = _sections(problem, key, inputs, result, instruction)
    data = docx.render_academic(title, sections)
    return {"format": FORMAT, "service": key, "label": LABELS[key],
            "problem": problem["key"], "problem_label": problem["label"],
            "method": problem["method"], "inputs": inputs, "read": parsed,
            "result": _jsonable(result), "lines": _result_lines(problem, result, inputs),
            "interpretation": interpretation, "assumptions": assumptions,
            "limitations": limitations, "title": title,
            "docx": {"filename": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") + ".docx",
                     "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "data": __import__("base64").b64encode(data).decode("ascii")}}


def _jsonable(value):
    import json
    return json.loads(json.dumps(value, default=str))


def handle(verb, segments, body=None):
    """Dispatch `/api/cases/economics/{service}`.  Returns `(status, payload)`."""
    body = body if isinstance(body, dict) else {}
    if not segments:
        return 404, {"error": "name an economics service: macroeconomics, microeconomics or managerial_economics"}
    service = str(segments[0] or "").strip().lower()
    try:
        types = problem_types(service)
    except EconomicsError as error:
        return 404, {"error": str(error)}
    if len(segments) == 1:
        if verb == "GET":
            return 200, {"service": service, "label": LABELS.get(service), "types": types}
        if verb == "POST":
            try:
                return 200, solve(service, body.get("problem") or body.get("type"),
                                  body.get("figures") or body.get("inputs") or {},
                                  body.get("instruction") or "")
            except EconomicsError as error:
                return 400, {"error": str(error)}
        return 405, {"error": "method %s is not allowed on an economics service" % verb}
    return 404, {"error": "unknown economics route"}
