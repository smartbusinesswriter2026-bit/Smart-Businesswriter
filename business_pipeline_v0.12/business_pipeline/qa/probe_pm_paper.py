"""Build one project-management worksheet paper and read the .docx back (P6).

The paper is produced through the real product path
(``completion.complete`` -> ``completion.draft_bytes``), unzipped, and the XML
of ``word/document.xml`` is read against V-01..V-20 of
docs/VALIDATION_HARNESS.md §5.  Findings are written as
"V-12 failed at H2 <block>" - a named rule and a location, never a verdict.

    python qa/probe_pm_paper.py            # writes qa/evidence/project-management/
"""

import io
import json
import os
import re
import sys
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp.product import completion  # noqa: E402

OUT = os.path.join("qa", "evidence", "project-management")
UNIT = "the shift-roster replacement project at a grocery retailer"
BRIEF = ("A grocery retailer is replacing its paper-based shift roster with a scheduling "
         "system, and the store manager must show the board the plan, the cost and the risk "
         "before the pilot starts in the second quarter.")
TEMPLATE = "template_project_charter"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": "grocery retailer " + query[:60],
        "abstract": ("The paper reports how the project was run and what it delivered. "
                     "A second sentence follows it."),
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "International Journal of Project Management", "doi": "10.1/pm",
        "url": "https://doi.org/10.1/pm", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def build(template=TEMPLATE, sources=True):
    side = academic if sources else (lambda *a, **k: {"results": [], "errors": [], "skipped": []})
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        result = completion.complete(template, BRIEF, industry="grocery retail",
                                     unit_value=UNIT)
    return result, completion.draft_bytes(result)


def xml_of(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        raw = archive.read("word/document.xml").decode("utf-8")
    text = re.sub(r"<w:p[ >]", "\n<w:p ", raw)
    text = re.sub(r"<[^>]+>", "", text)
    return raw, text


def headings(text):
    return [line.strip() for line in text.splitlines()
            if line.strip() and len(line.strip()) < 90 and line.strip()[:1].isupper()
            and not line.strip().endswith(".")]


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {"template": TEMPLATE, "findings": [], "files": []}

    result, blob = build()
    path = os.path.join(OUT, "project-charter.docx")
    with open(path, "wb") as handle:
        handle.write(blob)
    report["files"].append(path)
    raw, text = xml_of(blob)

    # ---- V-01 / V-02 / V-12: sources or named gaps, never an empty cell
    for block in result["blocks"]:
        where = "H2 " + (block.get("label") or block["key"])
        kinds = [item["provenance"] for item in block["items"]]
        if not kinds and not block.get("gap"):
            report["findings"].append({"rule": "V-12", "where": where,
                                       "detail": "the block carries no item and no named gap"})
        if kinds == ["background"] and not block.get("gap"):
            report["findings"].append({
                "rule": "V-01", "where": where,
                "detail": "filled from the framework's own background with no source and no gap"})

    # ---- V-06 / V-20: no instructions, no template tokens, no placeholder byline
    proofs = {
        "V-06": ("diagram to draw", "lorem ipsum", "{{", "}}", "[insert", "<insert",
                 "TODO", "TBD", "placeholder"),
        "V-05": ("method:", "specification hash", "version 1.0.0", "can be re-run"),
        "V-20": ("student name", "your name", "author name"),
    }
    for rule, needles in proofs.items():
        hits = [needle for needle in needles if needle in text.lower()]
        if hits:
            report["findings"].append({"rule": rule, "where": "word/document.xml",
                                       "detail": "found " + ", ".join(hits)})

    # ---- V-09/V-10/V-11: a conclusion, a reference list, no heading jump
    lower = text.lower()
    for rule, needle in (("V-10", "conclusion"), ("V-11", "reference")):
        if needle not in lower:
            report["findings"].append({"rule": rule, "where": "the paper",
                                       "detail": "no " + needle + " heading"})

    report["headings"] = headings(text)
    report["words"] = len(text.split())
    report["blocks"] = [{"key": b["key"], "items": [i["provenance"] for i in b["items"]],
                         "gap": bool(b.get("gap"))} for b in result["blocks"]]

    # ---- the no-source twin must name its gaps instead of writing background
    _, nosrc = build(sources=False)
    _, nosrc_text = xml_of(nosrc)
    nosrc_path = os.path.join(OUT, "project-charter-nosource.docx")
    with open(nosrc_path, "wb") as handle:
        handle.write(nosrc)
    report["files"].append(nosrc_path)
    report["nosource_disclosed"] = "general background" in nosrc_text.lower()
    if not report["nosource_disclosed"]:
        report["findings"].append({"rule": "V-02", "where": "the no-source twin",
                                   "detail": "background is printed without saying so"})

    with open(os.path.join(OUT, "paper-read.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps(report, indent=1)[:4000])


if __name__ == "__main__":
    main()
