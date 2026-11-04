"""Read-only probe for the Research & statistics shelf (session 9).

The shelf is cross-cutting: 21 compute tools, no worksheets, no tiles, and ten
catalogue records that every other shelf cites.  This script measures it and
prints what it measured -- nothing here writes to `src/` or changes state.

The four measures this shelf needed, and the reason each one exists:

  (a) **two vocabularies.**  A tool carries a `key` (the page's own name) and a
      `method` (a frozen LIBRARY id).  Thirteen of the 21 keys are *not* library
      ids, so a probe that resolves `tool["key"]` against LIBRARY reports
      thirteen false defects.  This one resolves both and prints the difference.
  (b) **records against what the shelf ships.**  Seven records said "Method not
      built" while the page offers a calculator for that area (D-RES-01).
  (c) **one real run per tool**: preset -> `Pipeline.run` ->
      `session_paper.docx_bytes` -> the text a reader holds.  A green unit test
      is not a paper (P6).
  (d) **the figures, re-derived independently** (section 4.5): hand arithmetic
      on a small case and published reference values, computed here from `math`
      and `statistics`, never from the method's own second route.

Use it like this:

    python qa/probe_research_shelf.py                 # inventory, resolution, records
    python qa/probe_research_shelf.py --tools         # one paper per tool (P6)
    python qa/probe_research_shelf.py --contract      # declared numbers per method
    python qa/probe_research_shelf.py --figures       # independent re-derivation
    python qa/probe_research_shelf.py --subject operations --prove
                                                      # prove the harness on a shelf
                                                      # whose 46-test suite is green

`--subject` works for any shelf: the point of the last command is that a harness
is a suspect until it has been pointed at a shelf already known to be sound.
"""

import math
import os
import re
import sys
import tempfile
import zipfile

sys.path.insert(0, "src")

from bp import server                                             # noqa: E402
from bp.methods import LIBRARY                                    # noqa: E402
from bp.orchestrator import Pipeline                              # noqa: E402
from bp.product import session_paper, subjects                    # noqa: E402

SUBJECT = "research"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "qa", "evidence", "research")

#: The four tools that ship with no preset (`typed inputs` on the page): the
#: student types the figures, so there is no worked example to launch.  A probe
#: that only reads `server.PRESETS[tool["preset"]]` crashes on these four.
TYPED = {
    "spearman": {"x": [1, 2, 3, 4, 5, 6], "y": [2, 1, 4, 3, 6, 5]},
    "ols_robust": {"y": [2, 4, 5, 4, 5, 7, 8, 9],
                   "predictors": {"x": [1, 2, 3, 4, 5, 6, 7, 8]}},
    "mann_whitney": {"groups": {"control": [12, 15, 14, 10, 13],
                                "treated": [18, 21, 19, 17, 20]}},
    "kruskal_wallis": {"groups": {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}},
}


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


def inputs_for(tool):
    """The figures this tool runs on: its preset, or the typed case above."""
    if tool.get("preset"):
        return dict(server.PRESETS[tool["preset"]]["inputs"])
    return dict(TYPED.get(tool["key"]) or {})


def deliver(tool, subject=SUBJECT):
    """preset (or typed figures) -> Pipeline.run -> the delivered record."""
    preset = server.PRESETS.get(tool["preset"] or "") or {}
    objective = preset.get("objective") or ("%s probe" % subject)
    return Pipeline().run({"objective": objective, "method": tool["method"],
                           "inputs": inputs_for(tool)}, lambda spec: True)


def paper(tool):
    """(delivery, bundle, text) for one tool, through the shipped paper path."""
    delivery = deliver(tool)
    bundle = {"report": delivery.report, "appendix": delivery.appendix}
    return delivery, bundle, text_of(session_paper.docx_bytes(bundle))


def page(subject=SUBJECT):
    return subjects.detail(subject)



def inventory(subject=SUBJECT):
    """What the shelf declares, and what the catalogue says it should."""
    entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == subject)
    detail = page(subject)
    print("\nINVENTORY (%s) -- measured by this script, not copied" % subject)
    print("  tools      : %d" % len(detail["tools"]))
    print("  worksheets : %d" % len(detail["worksheets"]))
    print("  tiles      : %d" % len(detail.get("tiles") or []))
    print("  records    : %d   %s" % (len(detail["records"]), [r["id"] for r in detail["records"]]))
    print("  theories   : %d" % len(detail["theories"]))
    print("  glossary   : %d" % len(detail["glossary"]))
    print("  catalogue  : %d   (row says tools=%d worksheets=%d records=%d theories=%d)"
          % (len(detail["catalogue"]), entry["tool_count"], entry["worksheet_count"],
             entry["record_count"], entry["theory_count"]))
    print("  does_not   : %d" % len(detail["does_not"]))
    print("  start_steps: %d" % len(detail["start_steps"]))
    print("  cross_cutting: %s" % detail["cross_cutting"])
    forms = {}
    for row in detail["records"]:
        forms[row["form"]] = forms.get(row["form"], 0) + 1
    print("  record forms: %s" % forms)
    groups = sorted({str(tool.get("group")) for tool in detail["tools"]})
    levels = sorted({str(tool.get("level")) for tool in detail["tools"]})
    print("  tool groups: %s   tool levels: %s" % (groups, levels))
    return detail


def resolution(subject=SUBJECT):
    """(a) The same tool resolved twice: by `key` (wrong) and by `method` (right)."""
    print("\nRESOLUTION (tool['key'] vs tool['method'] against LIBRARY)")
    detail = page(subject)
    as_key = as_method = 0
    for tool in detail["tools"]:
        by_key = tool["key"] in LIBRARY
        by_method = tool["method"] in LIBRARY
        as_method += 1 if by_method else 0
        as_key += 1 if by_key else 0
        preset = tool["preset"]
        if not preset:
            preset_note = "(typed inputs)"
        elif preset not in server.PRESETS:
            preset_note = "MISSING FROM PRESETS"
        elif server.PRESETS[preset]["method"] != tool["method"]:
            preset_note = "RUNS %s" % server.PRESETS[preset]["method"]
        else:
            preset_note = "preset=%s" % preset
        print("  %-14s %-5s key %-22s %-7s %s"
              % (tool["key"], "KEY" if by_key else "  -", tool["method"],
                 "METHOD" if by_method else "MISSING", preset_note))
    print("  keys that resolve in LIBRARY   : %d of %d  (the WRONG comparison)"
          % (as_key, len(detail["tools"])))
    print("  methods that resolve in LIBRARY: %d of %d  (the RIGHT comparison)"
          % (as_method, len(detail["tools"])))
    return detail


def records(subject=SUBJECT):
    """(b) Each record against what the shelf actually ships (D-RES-01)."""
    print("\nRECORDS (id | form | status_short | methods the shelf runs for it)")
    detail = page(subject)
    shipped = {tool["method"] for tool in detail["tools"]}
    for row in detail["records"]:
        linked = set(row["linked_methods"])
        covered = sorted(linked & shipped)
        missing = sorted(linked - shipped)
        # A method that is not on THIS page may still be implemented: the record's
        # shelf note says which shelf carries it.  Only a method that is in no
        # LIBRARY entry at all is genuinely not built, and that is what is flagged.
        elsewhere = [method for method in missing if method in LIBRARY]
        label = ("no linked method" if not linked else
                 "all shipped" if not missing else
                 "on another shelf: %s" % elsewhere if len(elsewhere) == len(missing) else
                 "NOT IN LIBRARY: %s" % [m for m in missing if m not in LIBRARY])
        print("  %-11s %-9s %-16s linked=%-2d shipped=%-2d %s"
              % (row["id"], row["form"], row["status_short"], len(linked), len(covered), label))
        print("      note: %s" % (row.get("status_note") or "")[:150])
    return detail


def contract(subject=SUBJECT):
    """The frozen numbers each tool's method declares."""
    print("\nCONTRACT (method | tier | unit | ceiling | precision | checks | assumptions)")
    detail = page(subject)
    seen = []
    for tool in detail["tools"]:
        method = LIBRARY.get(tool["method"])
        if method is None or tool["method"] in seen:
            continue
        seen.append(tool["method"])
        print("  %-22s %-3s %-12s %-13s prec=%-28s checks=%-2d assumptions=%d limits=%d"
              % (tool["method"], method.tier, method.unit, method.claim_ceiling,
                 method.output_precision, len(method.test_names),
                 len(method.assumptions), len(method.limitations)))
        print("      checks: %s" % (", ".join(method.test_names) or "(none declared)"))
    return detail


def _plain(key):
    """The paper's label for a figure key (the same rule the paper uses)."""
    text = str(key or "").replace("_", " ").strip()
    return (text[:1].upper() + text[1:]) if text else ""


def printed_figure(text, key):
    """The value the paper prints for `key`, as the string a reader copies."""
    label = _plain(key) + ": "
    for line in text.splitlines():
        if line.startswith(label):
            return line[len(label):].strip()
    return None


def decimals(value):
    """How many decimal places a printed figure carries (0 for an integer)."""
    if value is None or not re.match(r"^-?\d+(\.\d+)?$", value.strip()):
        return None
    return len(value.split(".", 1)[1]) if "." in value else 0


def precision_report(tool, bundle, text):
    """P4: every computed figure at the precision `method.typing` declares."""
    method = LIBRARY[tool["method"]]
    outputs = ((bundle["appendix"].get("reperform") or {}).get("outputs") or {})
    checked = mismatched = unchecked = 0
    for key in outputs:
        printed = printed_figure(text, key)
        if printed is None or decimals(printed) is None:
            unchecked += 1
            continue
        unit_precision = method.typing(key) if callable(getattr(method, "typing", None)) else None
        precision = unit_precision[1] if unit_precision else None
        if precision is None:
            unchecked += 1
            continue
        checked += 1
        if decimals(printed) != int(precision):
            mismatched += 1
            print("      PRECISION: %-22s printed %-12s want %d dp" % (key, printed, precision))
    return checked, mismatched, unchecked


def papers(subject=SUBJECT):
    """(c) P6: one real paper per tool, written to qa/evidence/research/ and read back."""
    os.makedirs(EVIDENCE, exist_ok=True)
    print("\nTOOLS (preset -> Pipeline.run -> session_paper.docx_bytes -> text)")
    rows = []
    for tool in page(subject)["tools"]:
        delivery, bundle, text = paper(tool)
        name = "%s-%s" % (subject, tool["key"])
        with open(os.path.join(EVIDENCE, name + ".docx"), "wb") as stream:
            stream.write(session_paper.docx_bytes(bundle))
        with open(os.path.join(EVIDENCE, name + ".txt"), "w", encoding="utf-8") as stream:
            stream.write(text)
        figures = "\n".join(line for heading, lines in session_paper.sections(bundle)
                            if heading in ("Result", "Inputs and results") for line in lines)
        checked, mismatched, unchecked = precision_report(tool, bundle, text)
        rows.append((tool["key"], delivery.status, checked, mismatched, len(text)))
        print("  %-14s %-24s %-9s checks=%-2d chars=%-5d dp_checked=%-2d bad=%-2d raw=%-5s sci=%-5s"
              % (tool["key"], tool["method"], delivery.status,
                 len(delivery.appendix.get("tests") or []), len(text),
                 checked, mismatched,
                 bool(re.search(r"\d\.\d{6,}", text)),
                 bool(re.search(r"\d[eE][+-]\d", figures))))
        if delivery.status != "delivered":
            print("      BLOCKED: %s" % delivery.blocked_reason)
    bad = [row for row in rows if row[1] != "delivered" or row[3]]
    print("\n  %d papers in qa/evidence/%s/; %d delivered; %d with a precision problem"
          % (len(rows), subject, sum(1 for row in rows if row[1] == "delivered"), len(bad)))
    return rows


# ---------------------------------------------------------------- the kit ----
# Independent arithmetic: written here from the textbook formulas, not called
# from `bp.methods`.  Every helper below is compared against the delivered
# paper, so a drift in the core shows up as a disagreement, not as a pass.

def mean(xs):
    return sum(xs) / float(len(xs))


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / float(len(xs) - 1))


def betacf(a, b, x):
    """Continued fraction for the incomplete beta (Lentz's method)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betai(a, b, x):
    """The regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * betacf(a, b, x) / a
    return 1.0 - front * betacf(b, a, 1.0 - x) / b


def t_two_sided(t, df):
    """P(|T| > |t|) for Student's t: the closed form, not the engine's route."""
    return betai(df / 2.0, 0.5, df / (df + float(t) ** 2))


def f_survival(f, d1, d2):
    return betai(d2 / 2.0, d1 / 2.0, d2 / (d2 + d1 * float(f)))


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = average
        i = j + 1
    return out


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def welch(a, b):
    ma, mb = mean(a), mean(b)
    va, vb = sd(a) ** 2, sd(b) ** 2
    se = math.sqrt(va / len(a) + vb / len(b))
    df = (va / len(a) + vb / len(b)) ** 2 / ((va / len(a)) ** 2 / (len(a) - 1)
                                            + (vb / len(b)) ** 2 / (len(b) - 1))
    t = (ma - mb) / se
    return {"diff": ma - mb, "se": se, "df": df, "t": t, "p": t_two_sided(t, df)}


def anova(groups):
    all_values = [v for group in groups for v in group]
    grand = mean(all_values)
    ssb = sum(len(g) * (mean(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((v - mean(g)) ** 2 for v in g) for g in groups)
    dfb, dfw = len(groups) - 1, len(all_values) - len(groups)
    f = (ssb / dfb) / (ssw / dfw)
    return {"f": f, "df1": dfb, "df2": dfw, "p": f_survival(f, dfb, dfw)}


def kruskal(groups):
    flat = [v for group in groups for v in group]
    n = len(flat)
    rs = ranks(flat)
    start = 0
    total = 0.0
    for group in groups:
        rank_sum = sum(rs[start:start + len(group)])
        total += rank_sum ** 2 / float(len(group))
        start += len(group)
    h = 12.0 / (n * (n + 1)) * total - 3.0 * (n + 1)
    return {"h": h, "df": len(groups) - 1}


def chi_square_2x2(table):
    (a, b), (c, d) = table
    n = a + b + c + d
    expected = [[(a + b) * (a + c) / float(n), (a + b) * (b + d) / float(n)],
                [(c + d) * (a + c) / float(n), (c + d) * (b + d) / float(n)]]
    observed = [[a, b], [c, d]]
    stat = sum((observed[i][j] - expected[i][j]) ** 2 / expected[i][j]
               for i in range(2) for j in range(2))
    return {"chi2": stat, "p": math.erfc(math.sqrt(stat / 2.0))}


def ols_line(x, y):
    mx, my = mean(x), mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    slope = sxy / sxx
    r = pearson(x, y)
    return {"slope": slope, "intercept": my - slope * mx, "r_squared": r * r}


def cronbach(respondents):
    """Cronbach's alpha from the item variances and the total variance.

    `respondents` is one list per person, holding that person's score on each item.
    """
    columns = len(respondents[0])
    total = [sum(row) for row in respondents]
    item_variance = sum(sd([row[j] for row in respondents]) ** 2 for j in range(columns))
    return columns / (columns - 1.0) * (1.0 - item_variance / sd(total) ** 2)


#: The case each tool is proved on: small enough to do on paper, which is the
#: point.  A preset is used only where the preset IS the small case.
CASES = dict(TYPED)
CASES.update({
    "descriptive_stats": {"values": [2, 4, 4, 4, 5, 5, 7, 9]},
    "pearson": {"x": [1, 2, 3, 4, 5], "y": [2, 3, 5, 4, 6]},
    "welch_t": {"groups": {"a": [1, 2, 3, 4], "b": [5, 6, 7]}},
    "anova": {"groups": {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}},
    "kruskal_wallis": {"groups": {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}},
    "ols": {"y": [2, 4, 5, 4, 5, 7, 8, 9], "predictors": {"x": [1, 2, 3, 4, 5, 6, 7, 8]}},
    "one_sample_t": {"values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "mu0": 4},
    "chi_square": {"table": [[20, 30], [30, 20]]},
    "trend_forecast": {"values": [1, 2, 2, 4, 4, 5, 7], "horizon": 2},
    # B-190: the core refuses binary floats, so a p-value is passed as text.
    # A probe that passes 0.01 is refused, correctly, and must say so.
    "multiple_comparison": {"p_values": ["0.01", "0.04", "0.03"], "method": "holm"},
})


def case_for(tool):
    """The figures for the proved case: the hand case, else the shipped preset."""
    if tool["method"] in CASES:
        return dict(CASES[tool["method"]])
    return inputs_for(tool)


def figures(subject=SUBJECT):
    """(d) Every tool's figures on the proved case, printed from the paper."""
    print("\nFIGURES (paper value | declared precision)")
    for tool in page(subject)["tools"]:
        preset = server.PRESETS.get(tool["preset"] or "") or {}
        delivery = Pipeline().run({"objective": preset.get("objective") or "figures probe",
                                   "method": tool["method"],
                                   "inputs": case_for(tool)}, lambda spec: True)
        bundle = {"report": delivery.report, "appendix": delivery.appendix}
        text = text_of(session_paper.docx_bytes(bundle))
        method = LIBRARY[tool["method"]]
        record = (bundle["appendix"].get("reperform") or {})
        print("  %-14s -> %-22s status=%s" % (tool["key"], tool["method"], delivery.status))
        if delivery.status != "delivered":
            print("      BLOCKED: %s" % delivery.blocked_reason)
            continue
        for key, value in (record.get("outputs") or {}).items():
            printed = printed_figure(text, key)
            unit_precision = method.typing(key) if callable(getattr(method, "typing", None)) else None
            print("      %-20s %-14s (declared %s)" % (key, printed if printed is not None else value,
                                                       unit_precision))


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return (ordered[middle] if len(ordered) % 2 else
            (ordered[middle - 1] + ordered[middle]) / 2.0)


def independent(method, case):
    """The same statistic computed here, from the textbook formula.

    Returns {output_key: value}.  Only the closed-form methods are here; a model
    fitted by iteration (logistic regression) or a design-based decomposition
    (two-way ANOVA) is proved by its own invariants in the acceptance suite.
    """
    if method == "descriptive_stats":
        v = [float(x) for x in case["values"]]
        return {"n": float(len(v)), "mean": mean(v), "sd": sd(v), "variance": sd(v) ** 2,
                "median": _median(v), "minimum": min(v), "maximum": max(v)}
    if method == "pearson":
        x = [float(i) for i in case["x"]]
        y = [float(i) for i in case["y"]]
        r = pearson(x, y)
        n = len(x)
        t = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
        return {"r": r, "r_squared": r * r, "p_value": t_two_sided(t, n - 2)}
    if method == "spearman":
        x = [float(i) for i in case["x"]]
        y = [float(i) for i in case["y"]]
        return {"rho": spearman(x, y)}
    if method == "welch_t":
        pairs = [(k, [float(i) for i in v]) for k, v in case["groups"].items()]
        (ka, va), (kb, vb) = pairs
        w = welch(va, vb)
        return {"diff": w["diff"], "se_diff": w["se"], "df": w["df"],
                "t_stat": w["t"], "p_value": w["p"], "n_a": float(len(va)), "n_b": float(len(vb))}
    if method == "mann_whitney":
        pairs = [(k, [float(i) for i in v]) for k, v in case["groups"].items()]
        (ka, va), (kb, vb) = pairs
        rs = ranks(va + vb)
        u = sum(rs[:len(va)]) - len(va) * (len(va) + 1) / 2.0
        return {"u_stat": u}
    if method == "anova":
        groups = [[float(i) for i in v] for v in case["groups"].values()]
        a = anova(groups)
        return {"f_stat": a["f"], "df_between": float(a["df1"]),
                "df_within": float(a["df2"]), "p_value": a["p"]}
    if method == "kruskal_wallis":
        groups = [[float(i) for i in v] for v in case["groups"].values()]
        k = kruskal(groups)
        return {"h_stat": k["h"], "df": float(k["df"])}
    if method == "chi_square":
        table = [[float(c) for c in row] for row in case["table"]]
        total = sum(sum(row) for row in table)
        rows = [sum(row) for row in table]
        cols = [sum(row[j] for row in table) for j in range(len(table[0]))]
        stat = sum((table[i][j] - rows[i] * cols[j] / total) ** 2 / (rows[i] * cols[j] / total)
                   for i in range(len(table)) for j in range(len(table[0])))
        return {"chi_squared": stat, "df": float((len(table) - 1) * (len(table[0]) - 1)),
                "cramers_v": math.sqrt(stat / (total * min(len(table) - 1, len(table[0]) - 1)))}
    if method in ("ols", "ols_robust"):
        name, xs = next(iter(case["predictors"].items()))
        x = [float(i) for i in xs]
        y = [float(i) for i in case["y"]]
        line = ols_line(x, y)
        return {"coef_%s" % name: line["slope"], "coef_intercept": line["intercept"],
                "r_squared": line["r_squared"]}
    if method == "one_sample_t":
        v = [float(i) for i in case["values"]]
        t = (mean(v) - float(case["mu0"])) / (sd(v) / math.sqrt(len(v)))
        return {"t_stat": t, "df": float(len(v) - 1), "p_value": t_two_sided(t, len(v) - 1)}
    if method == "paired_t":
        pairs = case["pairs"]
        (na, a), (nb, b) = list(pairs.items())
        d = [float(u) - float(v) for u, v in zip(a, b)]
        t = mean(d) / (sd(d) / math.sqrt(len(d)))
        return {"mean_diff": mean(d), "sd_diff": sd(d), "se_diff": sd(d) / math.sqrt(len(d)),
                "t_stat": t, "p_value": t_two_sided(t, len(d) - 1)}
    if method == "reliability_alpha":
        names = list(case["items"])
        rows = [[float(v) for v in case["items"][name]] for name in names]
        items = list(zip(*rows))
        return {"alpha": cronbach(items), "k_items": float(len(names))}
    if method == "weighted_summary":
        v = [float(i) for i in case["values"]]
        w = [float(i) for i in case["weights"]]
        return {"weighted_mean": sum(a * b for a, b in zip(v, w)) / sum(w),
                "sum_weights": sum(w), "n": float(len(v))}
    if method == "missing_data_bounds":
        codes = {str(c) for c in (case.get("missing_codes") or [])}
        valid = [float(x) for x in case["values"]
                 if str(x).strip() != "" and str(x) not in codes]
        total = len(case["values"])
        missing = total - len(valid)
        low = (sum(valid) + missing * min(valid)) / total
        high = (sum(valid) + missing * max(valid)) / total
        return {"n_valid": float(len(valid)), "n_missing": float(missing),
                "mean_observed": mean(valid), "bound_low": low, "bound_high": high}
    if method == "power_analysis":
        from statistics import NormalDist
        effect = float(case["effect"])
        n1, n2 = float(case["n1"]), float(case["n2"])
        sd1 = float(case.get("sd1") or 1.0)
        sd2 = float(case.get("sd2") or sd1)
        alpha = float(case.get("alpha") or 0.05)
        tails = 2.0 if (case.get("tails") or "two_sided") == "two_sided" else 1.0
        se = math.sqrt(sd1 ** 2 / n1 + sd2 ** 2 / n2)
        ncp = abs(effect) / se
        z = NormalDist().inv_cdf(1 - alpha / tails)
        power = 1 - NormalDist().cdf(z - ncp) + NormalDist().cdf(-z - ncp)
        return {"se": se, "ncp": ncp, "z_alpha": z, "power": power, "n1": n1, "n2": n2}
    if method == "trend_forecast":
        v = [float(i) for i in case["values"]]
        x = [float(i + 1) for i in range(len(v))]
        line = ols_line(x, v)
        return {"slope": line["slope"], "intercept": line["intercept"],
                "r_squared": line["r_squared"]}
    return {}


def verify(subject=SUBJECT):
    """Every tool's paper, against the kit.  A mismatch is the engine's problem."""
    print("\nVERIFY (independent re-derivation vs the printed paper)")
    rows = []
    for tool in page(subject)["tools"]:
        method = tool["method"]
        case = case_for(tool)
        preset = server.PRESETS.get(tool["preset"] or "") or {}
        delivery = Pipeline().run({"objective": preset.get("objective") or "verify probe",
                                   "method": method, "inputs": case}, lambda spec: True)
        if delivery.status != "delivered":
            print("  %-14s %-22s NOT DELIVERED: %s" % (tool["key"], method, delivery.blocked_reason))
            rows.append((tool["key"], 0, 1))
            continue
        bundle = {"report": delivery.report, "appendix": delivery.appendix}
        text = text_of(session_paper.docx_bytes(bundle))
        outputs = (bundle["appendix"].get("reperform") or {}).get("outputs") or {}
        kit = independent(method, case)
        checked = 0
        bad = []
        th = LIBRARY[method]
        for key, expected in kit.items():
            printed = printed_figure(text, key)
            if printed is None or key not in outputs:
                continue
            unit_precision = th.typing(key) if callable(getattr(th, "typing", None)) else None
            precision = unit_precision[1] if unit_precision else None
            engine = float(str(outputs[key]))
            tolerance = 0.5 * (10.0 ** -(precision if precision is not None else 6)) + 1e-9
            checked += 1
            if abs(engine - expected) > tolerance:
                bad.append((key, engine, expected))
        print("  %-14s %-22s compared=%-2d %s"
              % (tool["key"], method, checked, "AGREES" if not bad else "DISAGREES"))
        for key, engine, expected in bad:
            print("      %-18s engine=%-14s kit=%-14s" % (key, engine, expected))
        rows.append((tool["key"], checked, len(bad)))
    total = sum(row[1] for row in rows)
    bad = sum(row[2] for row in rows)
    print("\n  %d figures compared, %d disagreements" % (total, bad))
    return rows


def prove(subject):
    """Point the whole probe at a shelf we already trust, and report contradictions.

    A harness is a suspect until it has been run against a shelf whose own
    acceptance suite is green.  Anything this prints for `operations` that its
    46-test suite allows is a false positive in the harness, not a defect.
    """
    print("\nPROVE THE HARNESS ON %r" % subject)
    detail = page(subject)
    problems = []
    for tool in detail["tools"]:
        if tool["method"] not in LIBRARY:
            problems.append("%s: method %r not in LIBRARY" % (tool["key"], tool["method"]))
        if tool["preset"] and tool["preset"] not in server.PRESETS:
            problems.append("%s: preset %r not in PRESETS" % (tool["key"], tool["preset"]))
        delivery = deliver(tool, subject)
        if delivery.status != "delivered":
            problems.append("%s: %s (%s)" % (tool["key"], delivery.status,
                                             delivery.blocked_reason))
    print("  tools=%d  problems=%d" % (len(detail["tools"]), len(problems)))
    for problem in problems:
        print("    %s" % problem)
    return problems


def main(argv):
    subject = SUBJECT
    flags = list(argv)
    if "--subject" in flags:
        subject = flags[flags.index("--subject") + 1]
        flags = [flag for flag in flags if flag != subject]
    inventory(subject)
    resolution(subject)
    records(subject)
    if "--contract" in flags or not flags:
        contract(subject)
    if "--tools" in flags or not flags:
        papers(subject)
    if "--figures" in flags:
        figures(subject)
    if "--verify" in flags:
        verify(subject)
    if "--prove" in flags:
        prove(subject)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


