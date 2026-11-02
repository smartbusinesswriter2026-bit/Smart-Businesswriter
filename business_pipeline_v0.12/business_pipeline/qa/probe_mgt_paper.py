"""Read-only probe: build the shelf's papers and READ them (P6, 2026-11-03).

Produces, under qa/evidence/management/:
  value-chain.docx / value-chain.txt        the draft paper, with the XML stripped
  value-chain-nosource.docx / .txt          the same paper when nothing is retrieved
  change-organization.docx / .txt           the change paper
  worksheet-export.docx / .txt              the deliverables export (P3)
  summary.txt                               every V-rule the reader can check

Nothing here writes to src/ or changes state.  The papers are built through the
real paths: completion.complete -> completion.draft -> completion.draft_bytes,
and deliverables.sections -> deliverables.write_export.
"""

import os
import re
import sys
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp import templates as T  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402
from bp.product import completion, deliverables  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "evidence", "management")

INDUSTRY = "grocery retail"
BRIEF = ("A grocery retailer is reviewing how its value chain creates value and where cost and "
         "differentiation come from, before deciding whether to open a new store format.")
CHANGE_BRIEF = ("A grocery retailer is planning to move its store rota and its stock-replenishment "
                "process onto one system, before deciding whether to run the change this year.")
BRIEFS = {"template_value_chain": BRIEF, "template_change_organization": CHANGE_BRIEF}

TITLES = {
    "firm infrastructure": "Overhead costs and administrative support functions in grocery retail",
    "human resource": "Recruitment and training practices in grocery retail",
    "technology": "Automation and digital technology adoption in grocery retail",
    "procurement": "Supplier sourcing and procurement in grocery retail",
    "inbound": "Inbound logistics and distribution centre handling in grocery retail",
    "operations": "Store operations and production processes in grocery retail",
    "outbound": "Outbound logistics and home delivery in grocery retail",
    "marketing": "Marketing and sales channels in grocery retail",
    "service": "Customer service and after-sales support in grocery retail",
}


def _title_for(query):
    for cue, title in TITLES.items():
        if cue in query.lower():
            return title
    return "Grocery retail evidence"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": _title_for(query),
        "abstract": "Evidence on the activity named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def nothing(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def run(template, sources=True):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic if sources else nothing), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, BRIEFS.get(template, BRIEF), industry=INDUSTRY)


def read_docx(path):
    """word/document.xml with the tags stripped: the sentences a reader sees."""
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())



def write(name, payload):
    path = os.path.join(OUT, name)
    with open(path, "wb") as stream:
        stream.write(payload)
    with open(os.path.splitext(path)[0] + ".txt", "w", encoding="utf-8") as stream:
        stream.write(read_docx(path) if name.endswith(".docx") else "")
    return path


def paper(template, sources, name):
    """Complete, draft and render one paper through the real paths."""
    result = run(template, sources=sources)
    result = dict(result, byline=["A Student", "Example University"])
    report = completion.draft(result, "apa", "draft", "mid")
    path = write(name, completion.draft_bytes(result, "apa", report, "draft", "mid"))
    return result, report, path


def deliverables_export():
    """The worksheet-submission deliverable, through the real export path."""
    delivery = Pipeline().run(T.EXAMPLES["template_value_chain"], lambda spec: True)
    bundle = {"id": "mgt-evidence", "title": "Value chain worksheet",
              "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
    path = os.path.join(OUT, "worksheet-export.docx")
    deliverables.write_export(bundle, "worksheet", "docx", path)
    with open(os.path.splitext(path)[0] + ".txt", "w", encoding="utf-8") as stream:
        stream.write(read_docx(path))
    return path, [heading for heading, _ in deliverables.sections(bundle, "worksheet")]


def main():
    os.makedirs(OUT, exist_ok=True)
    lines = []
    for template, name in (("template_value_chain", "value-chain"),
                           ("template_change_organization", "change-organization")):
        for sources, suffix in ((True, ""), (False, "-nosource")):
            result, report, path = paper(template, sources, name + suffix + ".docx")
            text = read_docx(path)
            lines.append("%s%s: %s" % (name, suffix, os.path.basename(path)))
            lines.append("  title      : %s" % report["title"])
            lines.append("  byline     : %s" % report["byline"])
            lines.append("  byline on the title page: %s"
                         % all(line in text for line in report["byline"]))
            lines.append("  headings   : %s" % [s["heading"] for s in report["sections"]])
            lines.append("  words      : %s" % report["words"])
            lines.append("  background disclosure: %s"
                         % ("No source was found for this part" in text))
            lines.append("  footer hits: %s"
                         % [f for f in ("How this was produced", "Specification hash", "Method: ")
                            if f in text])
            lines.append("  diagram promise: %s" % ("Diagram to draw" in text))
            lines.append("  digits in a background item: %s"
                         % any(char.isdigit() for block in result["blocks"]
                               for item in block["items"] if item.get("provenance") == "background"
                               for char in item["text"]))
    path, headings = deliverables_export()
    text = read_docx(path)
    lines.append("worksheet-export: %s" % os.path.basename(path))
    lines.append("  headings   : %s" % headings)
    lines.append("  footer hits: %s"
                 % [f for f in ("How this was produced", "Specification hash", "Method: ",
                                "can be re-run from the stored bundle") if f in text])
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
