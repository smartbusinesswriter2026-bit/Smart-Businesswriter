"""Read-only probe for the Operations management shelf (session 8).

Prints the shelf inventory reconciled against the catalogue, the form each
worksheet declares and renders, the read-only records and the glossary, the
profiles no page reaches, the block provenance of one completion per worksheet,
and — the two measures this shelf needed — the **auto-fill trap** (what a probe
profile quotes out of a brief that merely mentions cost, quality or flow) and the
**papers themselves**: every worksheet's `.docx` written to
`qa/evidence/operations/` and read back from `word/document.xml`.

Nothing here writes to `src/` or changes state: it is the reproducible evidence
behind `qa/manual/operations.md`.

    python qa/probe_ops_shelf.py             # inventory, forms, records, glossary
    python qa/probe_ops_shelf.py --blocks    # per-block provenance, one run per worksheet
    python qa/probe_ops_shelf.py --auto      # the auto-fill trap (D-OPS-03)
    python qa/probe_ops_shelf.py --papers    # write and read the eleven papers (P6)
    python qa/probe_ops_shelf.py --tools     # the fourteen compute tools, paper by paper
"""

import os
import re
import sys
import tempfile
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp import registry as R, server, templates as T          # noqa: E402
from bp.orchestrator import Pipeline                           # noqa: E402
from bp.product import (completion, framework_profiles as P, paper,  # noqa: E402
                        session_paper, subjects)

SUBJECT = "operations"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "qa", "evidence", "operations")

#: The shelf's unit of analysis is a **process**, so every brief names one.
PROCESS = "the lunch service at the meal counter"
BRIEF = ("The lunch service at the meal counter takes an order, assembles and packs the meal, then the "
         "student collects and pays. At noon the queue reaches the gate, one oven bakes one tray at a "
         "time, and the supervisor re-times the wait from collection. The counter hands on a packed "
         "meal and a payment receipt. Bread arrives from one regional bakery every morning before "
         "opening.")

#: D-OPS-03: a brief that merely *mentions* cost, quality and flow.  Nothing in it
#: describes a framework's part; anything a cell quotes from it is the engine
#: mistaking a word it recognises for an answer to its own question.
TRAP_BRIEF = ("The counter must cut its cost per meal without losing quality, and the flow between the "
              "kitchen and the counter has to hold at the noon peak. The manager reviews the change "
              "next term.")


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query: the fair test of whether a block can
    accept evidence for the question it asks."""
    return {"results": [{
        "title": query[:120],
        "abstract": "Evidence on " + query[:110] + ". A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management",
        "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def empty(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def run(template, brief=BRIEF, sources=True, process=PROCESS):
    side = academic if sources else empty
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, brief, unit_value=process)


def text_of(payload):
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "paper.docx")
        with open(path, "wb") as stream:
            stream.write(payload)
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def sheets():
    return subjects.detail(SUBJECT)["worksheets"]


def tables(page):
    print("\nWORKSHEETS (id | template | draftable | form | fills | group)")
    for sheet in page["worksheets"]:
        template = sheet["template"]
        profile = P.get(template) or {}
        fills = {}
        for block in profile.get("blocks") or []:
            kind = P.fill_of(block)
            fills[kind] = fills.get(kind, 0) + 1
        print("  %-6s %-28s %-5s %-8s %-22s %s"
              % (sheet["catalogue_id"], template, bool(sheet.get("draftable")),
                 T.describe(template)["form_kind"], fills, sheet.get("group")))
    print("\nRECORDS (id | name | form | type | template | linked methods)")
    for row in page["records"]:
        print("  %-9s %-46s %-9s %-2s %-6s %s"
              % (row["id"], row["name"][:46], row.get("form"), row.get("type"),
                 row.get("template"), row.get("linked_methods")))
    print("\nGLOSSARY (%d terms)" % len(page["glossary"]))
    for term in page["glossary"]:
        print("  %-24s %s" % (term["term"], (term.get("definition") or "")[:90]))
    print("\nSHARED AND UNREACHED")
    reached = {}
    for row in subjects.catalogue()["subjects"]:
        for sheet in subjects.detail(row["id"])["worksheets"]:
            reached.setdefault(sheet["template"], []).append(row["id"])
    for sheet in page["worksheets"]:
        print("  %-6s also on: %s" % (sheet["catalogue_id"],
                                      [s for s in reached[sheet["template"]] if s != SUBJECT] or "-"))
    ours = {sheet["template"] for sheet in page["worksheets"]}
    print("  profiles on this shelf reached by no page: %s"
          % sorted(ours - set(reached)))


def forms(page):
    print("\nFORM AUDIT (declared canvas / matrix / both; registry form)")
    for sheet in page["worksheets"]:
        template = sheet["template"]
        described = T.describe(template)
        both = template in T.CANVAS_BLOCKS and template in T.MATRIX_META
        print("  %-6s %-28s form=%-8s canvas=%-5s matrix=%-5s both=%-5s registry=%-9s blocks=%d"
              % (sheet["catalogue_id"], template, described["form_kind"],
                 template in T.CANVAS_BLOCKS, template in T.MATRIX_META, both,
                 (R.get(sheet["catalogue_id"]) or {}).get("form"),
                 len(described["blocks"])))


def blocks(sources=True):
    """One mocked completion per worksheet: what each block accepted, and how."""
    print("\nBLOCK PROVENANCE (sources=%s)" % sources)
    for sheet in sheets():
        result = run(sheet["template"], sources=sources)
        print("  %-6s %-26s parts=%d filled=%d gaps=%d"
              % (sheet["catalogue_id"], sheet["template"], result["summary"]["parts"],
                 result["summary"]["filled"], result["summary"]["gaps"]))
        for block in result["blocks"]:
            kind = P.fill_of(next(b for b in P.PROFILES[sheet["template"]]["blocks"]
                                  if b["key"] == block["key"]))
            prov = [item.get("provenance") for item in block["items"]]
            print("    %-22s %-9s items=%-2d %-22s gap=%s"
                  % (block["key"], kind, len(block["items"]), prov,
                     (block.get("gap") or "-")[:60]))


def auto_trap():
    """D-OPS-03: a probe profile with no source falls back to the student's words.

    The question is not whether it quotes — it must, that is the contract — but
    whether the sentence it quotes answers the block's own prompt.  This prints
    every quote the trap brief produces, so a reader can judge each one.
    """
    print("\nAUTO-FILL TRAP — brief: %r" % TRAP_BRIEF)
    for sheet in sheets():
        template = sheet["template"]
        if not any(P.fill_of(b) == "auto" for b in P.PROFILES[template]["blocks"]):
            continue
        result = run(template, brief=TRAP_BRIEF, sources=False)
        print("  %-6s %-26s" % (sheet["catalogue_id"], template))
        for block in result["blocks"]:
            prompt = next(b["prompt"] for b in P.PROFILES[template]["blocks"] if b["key"] == block["key"])
            quoted = [item["text"] for item in block["items"] if item.get("provenance") == "student"]
            print("    %-20s <- %s" % (block["key"], quoted or "[nothing quoted]"))
            for text in quoted:
                print("        prompt: %s" % prompt[:96])
                print("        quoted: %s" % text[:96])


def inventory():
    page = subjects.detail(SUBJECT)
    entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == SUBJECT)
    print("operations shelf — measured %s" % "by this script")
    print("  tools      : %d  %s" % (len(page["tools"]), [t["key"] for t in page["tools"]]))
    print("  worksheets : %d  (not draftable: %s)"
          % (len(page["worksheets"]),
             [s["catalogue_id"] for s in page["worksheets"] if not s["draftable"]]))
    print("  records    : %d  %s" % (len(page["records"]), [r["id"] for r in page["records"]]))
    print("  theories   : %d" % len(page["theories"]))
    print("  glossary   : %d  (undefined: %s)"
          % (len(page["glossary"]), [t["term"] for t in page["glossary"] if not t.get("definition")]))
    print("  tiles      : %d  groups: %s"
          % (len(page.get("tiles") or []), sorted({s.get("group") for s in page["worksheets"]}, key=str)))
    print("  catalogue row: tools=%d worksheets=%d records=%d theories=%d counted=%d"
          % (entry["tool_count"], entry["worksheet_count"], entry["record_count"],
             entry["theory_count"], entry["catalogue_count"]))
    print("  profiles overall: %d" % len(P.PROFILES))
    return page


def papers():
    """P6: produce every worksheet's paper and read what a reader would hold."""
    os.makedirs(EVIDENCE, exist_ok=True)
    print("\nPAPERS (complete -> draft -> draft_bytes -> word/document.xml)")
    rows = []
    for sheet in sheets():
        result = dict(run(sheet["template"]), byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "mid")
        payload = completion.draft_bytes(result, "apa", report, "draft", "mid")
        name = "%s-%s" % (sheet["catalogue_id"].lower(), sheet["template"].replace("template_", ""))
        with open(os.path.join(EVIDENCE, name + ".docx"), "wb") as stream:
            stream.write(payload)
        text = text_of(payload)
        with open(os.path.join(EVIDENCE, name + ".txt"), "w", encoding="utf-8") as stream:
            stream.write(text)
        filled = sum(1 for block in result["blocks"] if block["items"])
        gaps = sum(1 for block in result["blocks"] if block["gap"])
        rows.append((sheet["catalogue_id"], report["words"], len(text), filled, gaps, name))
        print("  %-6s words=%-5d chars=%-6d filled=%-2d gaps=%-2d %s.docx"
              % (sheet["catalogue_id"], report["words"], len(text), filled, gaps, name))
    print("\n  %d papers and %d text reads in qa/evidence/operations/" % (len(rows), len(rows)))


def tools():
    """The fourteen compute tools: preset -> Pipeline.run -> session_paper -> text."""
    os.makedirs(EVIDENCE, exist_ok=True)
    print("\nTOOLS (preset -> Pipeline.run -> session_paper.docx_bytes -> text)")
    for tool in subjects.detail(SUBJECT)["tools"]:
        preset = server.PRESETS[tool["preset"]]
        delivery = Pipeline().run({"objective": preset.get("objective") or "operations probe",
                                   "method": preset["method"], "inputs": dict(preset["inputs"])},
                                  lambda spec: True)
        bundle = {"report": delivery.report, "appendix": delivery.appendix}
        payload = session_paper.docx_bytes(bundle)
        text = text_of(payload)
        name = "tool-" + tool["key"]
        with open(os.path.join(EVIDENCE, name + ".docx"), "wb") as stream:
            stream.write(payload)
        with open(os.path.join(EVIDENCE, name + ".txt"), "w", encoding="utf-8") as stream:
            stream.write(text)
        figures = "\n".join(line for heading, lines in session_paper.sections(bundle)
                            if heading in ("Result", "Inputs and results") for line in lines)
        print("  %-14s %-24s status=%-9s checks=%-2d chars=%-5d raw_decimal=%-5s sci=%-5s"
              % (tool["key"], preset["method"], delivery.status,
                 len(delivery.appendix.get("tests") or []), len(text),
                 bool(re.search(r"\d\.\d{6,}", text)),
                 bool(re.search(r"\d[eE][+-]\d", figures))))
        if delivery.status != "delivered":
            print("      BLOCKED: %s" % delivery.blocked_reason)


def main(argv):
    page = inventory()
    tables(page)
    forms(page)
    flags = set(argv)
    if "--blocks" in flags or not flags:
        blocks(sources=True)
        blocks(sources=False)
    if "--auto" in flags:
        auto_trap()
    if "--papers" in flags:
        papers()
    if "--tools" in flags:
        tools()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
