"""Read-only probe for the Project management shelf (session 7).

Prints the shelf inventory, the form each worksheet declares and renders, the
block provenance of one mocked completion run per worksheet, the registry-wide
double-declaration audit (K1) and the refusal contract of the decision tools
(K5).  Nothing here writes to src/ or changes state: it is the reproducible
evidence behind qa/manual/project-management.md.

    python qa/probe_pm_shelf.py              # inventory + forms + registry audit
    python qa/probe_pm_shelf.py --blocks     # per-block provenance, one run per worksheet
    python qa/probe_pm_shelf.py --refusals   # decision-tool refusal contract
"""

import sys
from unittest import mock

sys.path.insert(0, "src")

from bp import registry as R, templates as T          # noqa: E402
from bp.methods import DataError, LIBRARY              # noqa: E402
from bp.product import completion, framework_profiles, subjects  # noqa: E402

SUBJECT = "project-management"
INDUSTRY = "grocery retail"
BRIEF = ("A grocery retailer is replacing its paper-based shift roster with a scheduling system, "
         "and the store manager must show the board the plan, the cost and the risk before the "
         "pilot starts in the second quarter.")


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": INDUSTRY + " " + query[:70],
        "abstract": "Evidence on the activity named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "International Journal of Project Management",
        "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def inventory():
    page = subjects.detail(SUBJECT)
    print("project-management shelf")
    print("  tools      :", len(page["tools"]), [tool["key"] for tool in page["tools"]])
    print("  worksheets :", len(page["worksheets"]))
    print("  records    :", len(page.get("records") or []))
    print("  theories   :", len(page.get("theories") or []))
    print("  glossary   :", len(page.get("glossary") or []))
    print("  tiles      :", len(page.get("tiles") or []))
    print("  profiles overall:", len(framework_profiles.PROFILES))
    return page


def worksheet_table(page):
    print("\nWORKSHEETS (id | template | draftable | unit | gate | gap mode)")
    for sheet in page["worksheets"]:
        template = sheet["template"]
        profile = framework_profiles.get(template) or {}
        unit = (profile.get("unit") or {}).get("field")
        gate = profile.get("gate") or {}
        fills = {}
        for block in profile.get("blocks") or []:
            kind = framework_profiles.fill_of(block)
            fills[kind] = fills.get(kind, 0) + 1
        print("  %-6s %-28s draftable=%-5s unit=%-10s gate=%s fills=%s"
              % (sheet["catalogue_id"], template, bool(sheet.get("draftable")), unit,
                 "%s/%s/%s" % (int(bool(gate.get("title_cue"))),
                               int(bool(gate.get("title_context"))),
                               int(bool(gate.get("require_geography")))), fills))


def record_table(page):
    print("\nRECORDS (id | name | form | type | template)")
    for row in page.get("records") or []:
        print("  %-6s %-52s %-10s %-3s %s"
              % (row["id"], row["name"][:52], row.get("form"), row.get("type"),
                 row.get("template")))


def form_table(page):
    print("\nDECLARED FORM (bp.templates.describe is the registry's own declaration)")
    for sheet in page["worksheets"]:
        template = sheet["template"]
        described = T.describe(template)
        spec = T.TEMPLATES[template]
        print("  %-6s %-28s form_kind=%-8s tier=%s registry_ids=%s"
              % (sheet["catalogue_id"], template, described["form_kind"], spec.get("tier"),
                 spec.get("registry_ids")))
        blocks = described.get("blocks") or []
        for block in blocks:
            print("      %-30s %s" % (block.get("key"), block.get("label")))
        if not blocks:
            print("      (no canvas blocks: the matrix rows and columns are the form)")


def double_declaration_audit():
    """K1: a block may declare exactly ONE form across the whole registry."""
    both = sorted(set(T.CANVAS_BLOCKS) & set(T.MATRIX_META))
    print("\nK1 double-declaration audit")
    print("  canvas kinds :", len(T.CANVAS_BLOCKS))
    print("  matrix kinds :", len(T.MATRIX_META))
    print("  in BOTH      :", both or "none")
    print("  canvas_meta & matrix_meta:",
          sorted(set(T.CANVAS_META) & set(T.MATRIX_META)) or "none")
    print("  templates    :", len(T.TEMPLATES))
    owners = {}
    for name in T.TEMPLATES:
        owners.setdefault("canvas" if name in T.CANVAS_BLOCKS else
                          "matrix" if name in T.MATRIX_META else "other", []).append(name)
    for kind, names in sorted(owners.items()):
        print("  form=%-7s n=%d" % (kind, len(names)))
    return both


def reachability():
    """K3: which profiles no subject page reaches, and which are not draftable."""
    reached = set()
    pages = {}
    for definition in subjects.SUBJECT_DEFS:
        page = subjects.detail(definition["id"])
        pages[definition["id"]] = page
        reached |= {sheet["template"] for sheet in page["worksheets"]}
    everything = set(framework_profiles.PROFILES)
    print("\nK3 reachability")
    print("  profiles on no subject page :", len(everything - reached))
    print("  PM profiles reached         :", len(reached & {
        t for t in everything if (framework_profiles.get(t) or {}).get("subject") == SUBJECT}))
    print("  PM worksheets not draftable :", [s["catalogue_id"] for s in pages[SUBJECT]["worksheets"]
                                             if not s.get("draftable")])
    print("  worksheets not draftable overall:",
          len([s for page in pages.values() for s in page["worksheets"] if not s.get("draftable")]))
    return everything - reached


def run(template, brief=BRIEF, industry=INDUSTRY, sources=True, unit=None):
    side = academic if sources else (lambda *a, **k: {"results": [], "errors": [], "skipped": []})
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, brief, industry=industry, unit_value=unit)


#: The five `unit`-typed worksheets refuse without a declared unit of analysis
#: (a designed refusal).  This is the unit the probe declares for them.
UNIT = "the shift-roster replacement project at a grocery retailer"


def block_report(template, sources=True):
    profile = framework_profiles.get(template) or {}
    unit = UNIT if (profile.get("unit") or {}).get("field") == "unit" else None
    result = run(template, sources=sources, unit=unit)
    print("\n%s (%s) unit=%s gaps=%d"
          % (template, result["framework"], result["unit"], len(result.get("notes") or [])))
    for block in result["blocks"]:
        kinds = [item["provenance"] for item in block["items"]]
        print("  %-26s items=%-30s gap=%s" % (block["key"], kinds or "[]",
                                              (block.get("gap") or "")[:80]))
    return result



def refusal_report():
    """K5: a decision tool must REFUSE, never default a probability, weight or score."""
    cases = (
        ("decision_tree", "a branch with no probability",
         {"tree": {"type": "decision", "alternatives": [
             {"name": "Launch", "node": {"type": "chance", "branches": [
                 {"probability": "", "node": {"type": "terminal", "value": "100"}},
                 {"probability": "0.4", "node": {"type": "terminal", "value": "-20"}}]}}]}}),
        ("decision_tree", "chance probabilities that do not sum to one",
         {"tree": {"type": "decision", "alternatives": [
             {"name": "Launch", "node": {"type": "chance", "branches": [
                 {"probability": "0.6", "node": {"type": "terminal", "value": "100"}},
                 {"probability": "0.6", "node": {"type": "terminal", "value": "-20"}}]}}]}}),
        ("real_option", "no declared volatility",
         {"underlying_value": "100", "investment_cost": "100", "volatility": "",
          "risk_free_rate": "0.05", "steps": "5"}),
        ("multi_criteria", "a criterion with no declared weight",
         {"criteria": [{"name": "cost", "weight": ""}],
          "alternatives": [{"name": "A", "scores": {"cost": "9"}},
                           {"name": "B", "scores": {"cost": "6"}}]}),
        ("scenario_analysis", "no declared scenario range",
         {"cashflows": ["-1000", "400", "400"], "discount_rate": "0.10",
          "rate_low": "", "rate_high": ""}),
        ("monte_carlo", "a distribution with no bounds",
         {"model": "npv", "iterations": "100", "seed": "1", "discount_rate": "0.10",
          "cashflows": [{"name": "outlay", "period": "0", "distribution": "fixed",
                         "value": "-1000"},
                        {"name": "y1", "period": "1", "distribution": "triangular"}]}),
    )
    print("\nK5 decision-tool refusal contract")
    for method_id, label, inputs in cases:
        method = LIBRARY[method_id]
        try:
            method.impl(inputs)
        except DataError as error:
            print("  %-16s REFUSED   %-46s %s" % (method_id, label, str(error)[:90]))
        except Exception as error:                                     # noqa: BLE001
            print("  %-16s %-9s %-46s %s" % (method_id, type(error).__name__, label,
                                             str(error)[:90]))
        else:
            print("  %-16s ACCEPTED  %-46s a default was invented (DEFECT)"
                  % (method_id, label))

    print("\nK5 decision-tool refusal contract")
    for method_id, label, inputs in cases:
        method = LIBRARY[method_id]
        try:
            method.impl(inputs)
        except DataError as error:
            print("  %-16s REFUSED   %-20s %s" % (method_id, label, str(error)[:100]))
        except Exception as error:                                     # noqa: BLE001
            print("  %-16s %-9s %-20s %s" % (method_id, type(error).__name__, label,
                                             str(error)[:100]))
        else:
            print("  %-16s ACCEPTED  %-20s a default was invented (DEFECT)"
                  % (method_id, label))


def main(argv):
    page = inventory()
    worksheet_table(page)
    record_table(page)
    form_table(page)
    double_declaration_audit()
    reachability()
    if "--blocks" in argv:
        for sheet in page["worksheets"]:
            for sources in (True, False):
                try:
                    block_report(sheet["template"], sources=sources)
                except Exception as error:                             # noqa: BLE001
                    print("\n%s (sources=%s) REFUSED: %s"
                          % (sheet["template"], sources, error))
    if "--refusals" in argv:
        refusal_report()


if __name__ == "__main__":
    main(sys.argv[1:])
