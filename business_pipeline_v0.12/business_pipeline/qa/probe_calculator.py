"""Read-only probe for the Business Calculator rail panel (`#panel-calculator`).

The calculator is not a subject: it is a *view* over the union of every subject's
compute tools (148 of them) plus a presentation taxonomy of 8 groups (206 entries).
Nothing in this file writes to `src/` or changes state -- it launches each tool
exactly the way the panel does and reads the paper a student would hold.

The four traps this probe is built around, kept where a reader can see them:

  1. **131 of the 148 keys are not method ids.**  A tool carries a `key` (the page's
     own name, `welch`) and a `method` (a frozen `LIBRARY` id, `welch_t`).  A probe
     that resolves `tool["key"]` against `LIBRARY` reports 131 false defects.  This
     one resolves both and prints the difference (`resolution`).
  2. **4 tools ship with no preset** (`kruskal_wallis`, `mann_whitney`, `ols_robust`,
     `spearman`).  Anything that indexes `PRESETS[tool["preset"]]` crashes on them;
     they are driven with typed figures (`TYPED`) and `inputs: {}` must not crash.
  3. **31 keys live in more than one group** (`chi_square` in 5, `forecast` in 6).
     One method, one answer -- launching from each group must give identical bytes.
  4. **A statistical "pass" is a number reproduced by hand.**  `--units` re-reads the
     declared unit/precision of every figure; `--prove` points the whole harness at a
     shelf whose own suite is already green.
"""

import os
import re
import sys
import tempfile
import zipfile
from decimal import Decimal, InvalidOperation

sys.path.insert(0, "src")

from bp import server                                             # noqa: E402
from bp.methods import LIBRARY                                    # noqa: E402
from bp.orchestrator import Pipeline                              # noqa: E402
from bp.product import session_paper, subjects                    # noqa: E402

SUBJECT = "calculator"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "qa", "evidence", "calculator")

#: The four tools that ship with no preset (`typed inputs` on the page).  The student
#: types the figures, so there is no worked example on `server.PRESETS` to launch; a
#: probe that only reads the preset crashes here.  These are hand-sized cases whose
#: answers are small enough to reproduce by hand (see `qa/manual/calculator.md`).
TYPED = {
    "spearman": {"x": [1, 2, 3, 4, 5, 6], "y": [2, 1, 4, 3, 6, 5]},
    "ols_robust": {"y": [2, 4, 5, 4, 5, 7, 8, 9],
                   "predictors": {"x": [1, 2, 3, 4, 5, 6, 7, 8]}},
    "mann_whitney": {"groups": {"control": [12, 15, 14, 10, 13],
                                "treated": [18, 21, 19, 17, 20]}},
    "kruskal_wallis": {"groups": {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}},
}

#: A number printed with 6 or more decimals is the B-190 / P4 failure: the core stores
#: a Decimal, the paper must print it at the method's declared precision.
SIX_DECIMALS = re.compile(r"\d\.\d{6,}")
#: Scientific notation never belongs in a student's paper.
SCIENTIFIC = re.compile(r"(?<![\w.])\d(?:\.\d+)?[eE][+-]?\d+")
#: A Python repr (`{'text': …}`, `['a', …]`) is P4's other half.
PY_REPR = re.compile(r"[{\[]\s*['\"]")


def text_of(payload):
    """The sentences a reader sees: word/document.xml with the tags stripped."""
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "paper.docx")
        with open(path, "wb") as stream:
            stream.write(payload)
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _plain(name):
    """A machine name as the paper prints it: `npv` -> `Npv`, `cash_flow` -> `Cash flow`."""
    text = str(name or "").replace("_", " ").strip()
    return (text[:1].upper() + text[1:]) if text else ""


def case_for(tool):
    """The figures this tool runs on: its preset, or the typed case for the four."""
    if tool.get("preset"):
        return dict(server.PRESETS[tool["preset"]]["inputs"])
    return dict(TYPED.get(tool["key"]) or {})


def inputs_for(tool):
    """The `inputs` the panel sends.  A preset-less tool sends `{}` (W-06) -- so the
    typed cases live beside it, never inside it."""
    return case_for(tool)


def deliver(tool, subject=None):
    """preset (or typed figures) -> `Pipeline.run` -> the delivered record."""
    preset = server.PRESETS.get(tool.get("preset") or "") or {}
    objective = preset.get("objective") or ("%s probe" % (subject or SUBJECT))
    return Pipeline().run({"objective": objective, "method": tool["method"],
                           "inputs": inputs_for(tool)}, lambda spec: True)


def paper(tool, subject=None):
    """(delivery, bundle, text) for one tool, through the shipped paper path."""
    delivery = deliver(tool, subject)
    bundle = {"report": delivery.report, "appendix": delivery.appendix}
    return delivery, bundle, text_of(session_paper.docx_bytes(bundle))


def groups():
    """The panel's groups, in business-function order, as (id, label, [keys])."""
    return [(group["id"], group["label"], list(group["tools"]))
            for group in subjects.CALCULATOR_GROUPS]


def group_count(group_tools):
    """{key: how many groups list it} -- the `shared keys` measure (W-03)."""
    counts = {}
    for _id, _label, keys in group_tools:
        for key in set(keys):
            counts[key] = counts.get(key, 0) + 1
    return counts




def inventory():
    """The panel's own taxonomy, measured (8 groups / 206 entries / 148 distinct)."""
    ordered = groups()
    tools = subjects.compute_tools()
    counts = group_count(ordered)
    shared = [key for key, count in sorted(counts.items()) if count > 1]
    print("\nINVENTORY (calculator) -- measured by this script, not copied")
    print("  compute_tools()      : %d" % len(tools))
    print("  groups               : %d" % len(ordered))
    print("  entries (with repeats): %d" % sum(len(keys) for _i, _l, keys in ordered))
    print("  distinct keys        : %d" % len(counts))
    print("  shared keys (>1 group): %d" % len(shared))
    distribution = sorted(__import__("collections").Counter(counts.values()).items())
    print("  sharing distribution  : %s  (keys -> in that many groups)"
          % ", ".join("%d keys in %d" % (n, k) for k, n in distribution))
    print("  typed tools (no preset): %d  %s"
          % (len([t for t in tools if not t["preset"]]),
             sorted(t["key"] for t in tools if not t["preset"])))
    print("  keys that are not LIBRARY ids: %d of %d"
          % (len([t for t in tools if t["key"] not in LIBRARY]), len(tools)))
    print("  in order:")
    for group_id, label, keys in ordered:
        print("    %-18s %-14s %3d" % (group_id, label[:14], len(keys)))
    # W-01 / W-02, printed as a measurement so the guard's union is visible.
    on_pages = {tool["key"] for tool in tools}
    print("  page tools missing from a group : %d %s"
          % (len(on_pages - set(counts)), sorted(on_pages - set(counts))))
    print("  group keys not on a page        : %d %s"
          % (len(set(counts) - on_pages), sorted(set(counts) - on_pages)))
    print("  union of groups == compute_tools(): %s"
          % (set(counts) == on_pages))
    return {"tools": len(tools), "groups": len(ordered),
            "entries": sum(len(keys) for _i, _l, keys in ordered),
            "distinct": len(counts), "shared": len(shared)}


def resolution():
    """Every tool resolved twice: the wrong way (`key`) and the right way (`method`).

    This is trap 1 made visible.  `key` is the page's name; `method` is the frozen id.
    A defect here is only ever a `method` that is missing from LIBRARY, or a preset
    whose `method` is not the tool's.
    """
    tools = subjects.compute_tools()
    key_hits = method_hits = 0
    problems = []
    rows = []
    for tool in tools:
        key_in_library = tool["key"] in LIBRARY
        method_in_library = tool["method"] in LIBRARY
        preset = server.PRESETS.get(tool.get("preset") or "")
        preset_method = preset.get("method") if preset else None
        key_hits += 1 if key_in_library else 0
        method_hits += 1 if method_in_library else 0
        if tool["preset"] and preset is None:
            problems.append((tool["key"], "preset %r missing" % tool["preset"]))
        elif tool["preset"] and preset_method != tool["method"]:
            problems.append((tool["key"], "preset method %r != %r"
                             % (preset_method, tool["method"])))
        if not method_in_library and tool["method"] != "case_decision":
            problems.append((tool["key"], "method %r not in LIBRARY" % tool["method"]))
        rows.append((tool["key"], tool["method"], tool.get("preset"),
                     key_in_library, method_in_library, preset_method))
    print("\nRESOLUTION -- key (wrong) vs method (right)")
    print("  tools                    : %d" % len(tools))
    print("  key in LIBRARY (wrong)   : %d   <- the 131-trap" % key_hits)
    print("  method in LIBRARY (right): %d" % method_hits)
    print("  keys that are not methods: %d" % (len(tools) - key_hits))
    print("  preset method == tool    : %d of %d non-typed"
          % (sum(1 for r in rows if r[2] and r[5] == r[1]),
             len([r for r in rows if r[2]])))
    print("  problems                 : %d %s" % (len(problems), problems[:5]))
    return {"key_hits": key_hits, "method_hits": method_hits, "problems": problems}


def _declared(method, key, recorded):
    """(unit, precision) the paper must use for one figure: typing first, record second."""
    if method is not None and getattr(method, "typing", None):
        try:
            unit, precision = method.typing(key)
            if precision is not None:
                return unit, int(precision)
        except Exception:                                    # noqa: BLE001
            pass
    pair = recorded.get(str(key)) or (None, None)
    return pair[0], (int(pair[1]) if pair[1] is not None else None)




def _recorded(appendix):
    """{key: (unit, precision)} the core recorded, for keys no `typing` hook covers."""
    out = {}
    analysis = (appendix or {}).get("analysis") or {}
    for entry in (analysis.get("artifacts") or []) if isinstance(analysis, dict) else []:
        if not isinstance(entry, dict) or entry.get("precision") is None:
            continue
        try:
            pair = (entry.get("unit"), int(entry["precision"]))
        except (TypeError, ValueError):
            continue
        for key in (entry.get("id"), entry.get("metric")):
            if key:
                out.setdefault(str(key), pair)
    return out


def gates(tool, delivery, text, appendix=None):
    """Every gate V/P requires, read on the paper a reader holds.  Returns failures."""
    appendix = appendix if appendix is not None else delivery.appendix
    failures = []
    if delivery.status != "delivered":
        reason = (delivery.blocked_reason or "").strip()
        if not reason:
            failures.append("blocked with no reason (W-09)")
        if not text:
            failures.append("blocked and no paper at all")
        return failures
    # The honesty block, the assumptions and the limitations are truthful sentences the
    # method declares ("Float reference comparison tolerance is 1e-9 relative"), not
    # figures.  Scanning them for number shape reported a false defect on two shelves,
    # so the shape gates read the report and the figure lines only.
    prose = set()
    for key, value in (appendix.get("honesty") or {}).items():
        if value:
            prose.add("%s: %s" % (key.replace("_", " "), value))
    for line in (appendix.get("assumptions") or []):
        prose.add(str(line).strip())
    for line in (appendix.get("limitations") or []):
        prose.add(str(line).strip())
    for name in (appendix.get("tests") or []):
        prose.add(_plain(name) + ".")
    scanned = [line for line in text.splitlines() if line not in prose]
    body = "\n".join(scanned)
    # --- precision: every figure prints at its declared precision (W-08) ------
    method_id = ((appendix.get("method") or {}).get("id")
                 or ((appendix.get("reperform") or {}).get("method") or {}).get("id"))
    method = LIBRARY.get(method_id) if method_id else None
    recorded = _recorded(appendix)
    record = appendix.get("reperform") or {}
    #: A figure the core rendered *at its declared precision* is legitimate even when
    #: that precision is 6 -- `currency_convert.rate` and `real_option.delta` both
    #: declare ratio/6 dp.  The ban is on printing MORE decimals than declared.
    declared_ok = set()
    for section in ("inputs", "outputs"):
        for key, value in (record.get(section) or {}).items():
            unit, precision = _declared(method, key, recorded)
            if precision is None:
                continue
            printed = _quantize(value, precision)
            if printed is None:
                continue
            declared_ok.add(printed)
            if ("%s: %s" % (_plain(key), printed)) not in body:
                failures.append("figure not at %d dp: %s (want %s)"
                                % (precision, key, printed))
    # --- P4 / B-190: the shape of every number -------------------------------
    # D-RES-05 / B-214 settled this house rule: six or more decimals in a paper reads as an
    # unrounded Decimal, and the *declaration* is the thing to fix.  Two tools still declare
    # ratio/6 dp (`currency_convert.rate`, `real_option.delta`) -- those are D-CALC-01/02.
    for match in SIX_DECIMALS.finditer(body):
        failures.append("6+ decimal figure: %r" % match.group(0))
        break
    for match in SCIENTIFIC.finditer(body):
        failures.append("scientific notation: %r" % match.group(0))
        break
    if PY_REPR.search(body):
        failures.append("Python repr in a paper: %r" % PY_REPR.search(body).group(0)[:24])
    # --- checks: every declared check printed, exactly once -------------------
    declared_checks = [name for name in (appendix.get("tests") or []) if str(name).strip()]
    if not declared_checks:
        failures.append("no checks declared (W-07)")
    for name in declared_checks:
        phrase = _plain(name) + "."
        count = text.count(phrase)
        if count == 0:
            failures.append("check not printed: %s (W-07)" % name)
        elif count > 1:
            failures.append("check printed %d times: %s" % (count, name))
    # --- assumptions and limitations are published, not implied ---------------
    for name, lines in (("assumption", appendix.get("assumptions")),
                        ("limitation", appendix.get("limitations"))):
        for line in (lines or []):
            line = str(line).strip()
            if line and line not in text:
                failures.append("%s not printed: %s" % (name, line[:40]))
    return failures


def _quantize(value, precision):
    """The figure as the paper prints it at `precision`, or None if it is not a number."""
    try:
        quantum = Decimal(1).scaleb(-int(precision))
        return format(Decimal(str(value)).quantize(quantum), "f")
    except (InvalidOperation, ValueError, TypeError):
        return None


def shared_keys():
    """The keys the panel deliberately lists in more than one group (W-03)."""
    return [key for key, count in sorted(group_count(groups()).items()) if count > 1]


def tools_report(write_evidence=False):
    """One row per tool: resolution, the paper, and every gate read on it."""
    tools = subjects.compute_tools()
    if write_evidence:
        os.makedirs(EVIDENCE, exist_ok=True)
    bad = []
    print("\nTOOLS -- one paper per tool, gates read on the artefact (P6)")
    print("  %-22s %-24s %-14s %s" % ("key", "method", "preset", "gates"))
    for tool in tools:
        try:
            delivery, bundle, text = paper(tool)
        except Exception as error:                        # noqa: BLE001
            bad.append((tool["key"], ["crash: %s: %s" % (type(error).__name__, error)]))
            print("  %-22s %-24s %-14s CRASH %s"
                  % (tool["key"], tool["method"], tool.get("preset"), error))
            continue
        failures = gates(tool, delivery, text)
        if write_evidence:
            # A text transcript, not the .docx: the paper bytes embed the core's code
            # hash, so any edit under `src/bp/**` rewrites nearly every file and the
            # evidence churns without a number changing.  The transcript is the
            # sentences a reader holds, it diffs, and it matches the research shelf's
            # `qa/evidence/research/*.txt` precedent.
            path = os.path.join(EVIDENCE, "paper_" + re.sub(r"\W+", "_", tool["key"]) + ".txt")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(text + "\n")
        if failures:
            bad.append((tool["key"], failures))
            print("  %-22s %-24s %-14s FAIL (%d)"
                  % (tool["key"], tool["method"], tool.get("preset") or "-", len(failures)))
        else:
            print("  %-22s %-24s %-14s ok"
                  % (tool["key"], tool["method"], tool.get("preset") or "-"))
    print("\n  tools: %d | pass: %d | fail: %d" % (len(tools), len(tools) - len(bad), len(bad)))
    for key, failures in bad:
        print("  - %s:" % key)
        for failure in failures[:6]:
            print("      %s" % failure)
    return bad


def determinism():
    """Two runs -> identical bytes, for every tool."""
    bad = []
    for tool in subjects.compute_tools():
        first = session_paper.docx_bytes({"report": deliver(tool).report,
                                          "appendix": deliver(tool).appendix})
        second = session_paper.docx_bytes({"report": deliver(tool).report,
                                           "appendix": deliver(tool).appendix})
        if first != second:
            bad.append(tool["key"])
    total = len(subjects.compute_tools())
    print("\nDETERMINISM -- two runs, identical bytes")
    print("  tools: %d | identical: %d | differ: %d %s"
          % (total, total - len(bad), len(bad), bad[:8]))
    return bad


def shared_report():
    """The multi-group keys: one method, one answer, from every group that lists it."""
    keys = shared_keys()
    tool_by_key = {tool["key"]: tool for tool in subjects.compute_tools()}
    counts = group_count(groups())
    bad = []
    for key in keys:
        tool = tool_by_key[key]
        baseline = None
        for group_id, _label, group_keys in groups():
            if key not in group_keys:
                continue
            delivery = deliver(tool)
            payload = session_paper.docx_bytes({"report": delivery.report,
                                                "appendix": delivery.appendix})
            if baseline is None:
                baseline = payload
            elif payload != baseline:
                bad.append((key, group_id))
    print("\nSHARED KEYS -- %d keys in more than one group" % len(keys))
    for key in keys:
        print("  %-22s in %d groups  %s" % (key, counts[key],
              [gid for gid, _l, ks in groups() if key in ks]))
    print("  disagreements: %d %s" % (len(bad), bad[:8]))
    return bad


def units():
    """The unit sweep (B-190): a share is not money, a ratio is not a count.

    For every figure the calculator prints, the `typing` hook and the method's own
    `output_units`/`output_precision` declaration must say the same thing.  Where a
    hook and a declaration disagree, the paper prints one and the contract says the
    other -- the exact class of defect B-190 records.
    """
    seen, disagreements = {}, []
    for tool in subjects.compute_tools():
        delivery = deliver(tool)
        appendix = delivery.appendix
        method_id = ((appendix.get("method") or {}).get("id")
                     or ((appendix.get("reperform") or {}).get("method") or {}).get("id"))
        method = LIBRARY.get(method_id) if method_id else None
        if method is None:
            continue
        record = appendix.get("reperform") or {}
        for section in ("inputs", "outputs"):
            for key in (record.get(section) or {}):
                typing_unit = typing_precision = None
                if getattr(method, "typing", None):
                    try:
                        typing_unit, typing_precision = method.typing(key)
                    except Exception:                        # noqa: BLE001
                        typing_unit = typing_precision = None
                declared_unit = (method.output_units or {}).get(key)
                declared_precision = (method.output_precision or {}).get(key)
                if typing_unit is not None:
                    seen[typing_unit] = seen.get(typing_unit, 0) + 1
                if (typing_unit and declared_unit and typing_unit != declared_unit):
                    disagreements.append((tool["key"], key, "unit",
                                          typing_unit, declared_unit))
                if (typing_precision is not None and declared_precision is not None
                        and int(typing_precision) != int(declared_precision)):
                    disagreements.append((tool["key"], key, "precision",
                                          typing_precision, declared_precision))
    print("\nUNIT SWEEP -- declared unit/precision vs the hook the paper prints from")
    print("  units seen: %s" % sorted(seen.items()))
    print("  disagreements: %d" % len(disagreements))
    for row in disagreements[:20]:
        print("    %s.%s: %s typing=%r declared=%r" % (row[0], row[1], row[2], row[3], row[4]))
    return disagreements


def prove(subject):
    """Point the whole harness at a shelf whose own suite is already green.

    A harness is a suspect until it has been aimed at a shelf it did not build.  This
    prints the same gates for `subject`'s own tools; every failure here is either a real
    defect on that shelf or a false positive in this probe -- and a false positive is
    the bug to fix first.
    """
    detail = subjects.detail(subject)
    tools = detail["tools"]
    bad = []
    print("\nPROVE (%s) -- %d tools, gates read on each paper" % (subject, len(tools)))
    for tool in tools:
        try:
            delivery, bundle, text = paper(tool, subject)
        except Exception as error:                        # noqa: BLE001
            bad.append((tool["key"], ["crash: %s" % error]))
            print("  %-22s CRASH %s" % (tool["key"], error))
            continue
        failures = gates(tool, delivery, text)
        if failures:
            bad.append((tool["key"], failures))
            print("  %-22s FAIL (%d)" % (tool["key"], len(failures)))
        else:
            print("  %-22s ok" % tool["key"])
    print("\n  tools: %d | pass: %d | fail: %d" % (len(tools), len(tools) - len(bad), len(bad)))
    for key, failures in bad:
        print("  - %s:" % key)
        for failure in failures[:6]:
            print("      %s" % failure)
    return bad


def main(argv):
    flags = list(argv)
    subject = SUBJECT
    if "--subject" in flags:
        index = flags.index("--subject")
        subject = flags[index + 1]
    if "--prove" in flags:
        prove(subject)
        return 0
    inventory()
    resolution()
    if "--tools" in flags:
        tools_report(write_evidence=True)
    if "--determinism" in flags:
        determinism()
    if "--shared" in flags:
        shared_report()
    if "--units" in flags:
        units()
    if not any(flag in flags for flag in
               ("--tools", "--determinism", "--shared", "--units")):
        print("\n(run with --tools, --determinism, --shared, --units, or --prove)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


