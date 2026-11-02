"""Read-only probe for the Management & strategy shelf (session 4).

Prints the shelf inventory and, for each profile on the shelf, what one
mocked completion run puts in each block.  Nothing here writes to src/ or
changes state: it is the reproducible evidence behind qa/manual/management.md.

    python qa/probe_mgt_shelf.py            # inventory + value chain / change org run
    python qa/probe_mgt_shelf.py --blocks   # per-block provenance for one template
"""

import sys
from unittest import mock

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, subjects  # noqa: E402

INDUSTRY = "grocery retail"
BRIEF = ("A grocery retailer is reviewing how its value chain creates value and where cost and "
         "differentiation come from, before deciding whether to open a new store format.")


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": INDUSTRY + " " + query[:70],
        "abstract": "Evidence on the activity named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def inventory():
    page = subjects.detail("management")
    print("management shelf")
    print("  tools      :", len(page["tools"]), [tool["key"] for tool in page["tools"]])
    print("  worksheets :", len(page["worksheets"]))
    print("  records    :", len(page.get("records") or []))
    print("  theories   :", len(page.get("theories") or []))
    print("  glossary   :", len(page.get("glossary") or []))
    templates = sorted({sheet["template"] for sheet in page["worksheets"]})
    print("  templates  :", len(templates))
    for template in templates:
        profile = framework_profiles.get(template)
        print("    %-42s %s" % (template, (profile or {}).get("label") or "NO PROFILE"))
    print("profiles overall:", len(framework_profiles.PROFILES))


def run(template, brief=BRIEF, industry=INDUSTRY, sources=True):
    side = academic if sources else (lambda *a, **k: {"results": [], "errors": [], "skipped": []})
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, brief, industry=industry)


def block_report(template, sources=True):
    result = run(template, sources=sources)
    print("\n%s (%s) unit=%s" % (template, result["framework"], result["unit"]))
    for block in result["blocks"]:
        kinds = [item["provenance"] for item in block["items"]]
        print("  %-26s items=%-28s gap=%s" % (block["key"], kinds or "[]",
                                              (block["gap"] or "")[:70]))
        print("      query=%s" % (block["query"],))


def main(argv):
    inventory()
    for template in ("template_value_chain", "template_change_organization"):
        for sources in (True, False):
            try:
                block_report(template, sources=sources)
            except Exception as error:                                # noqa: BLE001
                print("\n%s (sources=%s) REFUSED: %s" % (template, sources, error))


if __name__ == "__main__":
    main(sys.argv[1:])
