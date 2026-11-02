"""Debug harness: drive every Management & strategy profile through the real paths.

Not a test file: a measure. For each of the shelf's 30 templates it runs

    completion.complete -> completion.draft -> completion.draft_bytes

twice (once with evidence, once with none), strips word/document.xml and checks the
paper a reader would hold. It prints one row per template and every violation it finds,
so a failure names the template, the block and the sentence.

    python qa/probe_mgt_debug.py            # the whole shelf
    python qa/probe_mgt_debug.py template_value_chain

Nothing here writes to src/ or changes state.
"""

import os
import re
import sys
import tempfile
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp.product import api, completion, framework_profiles as P, paper, subjects  # noqa: E402

INDUSTRY = "grocery retail"
BRIEFS = {
    "industry": ("A grocery retailer is reviewing its position in the market before deciding whether to "
                 "open a new store format next year."),
    "process": ("The store is moving its rota and its stock-replenishment process onto one system before "
                "deciding whether to run the change this year."),
    "country": "A supermarket chain in Iran is weighing its options before entering the market.",
    "unit": "The campus shop is reviewing its offer before deciding whether to change it.",
}
LONG = re.compile(r"\d\.\d{6,}")
REPR = ("{'", "['", "('", "'}", "']", "')")
TITLES = (
    "Overhead costs and administrative support functions in grocery retail",
    "Recruitment and training practices in grocery retail",
    "Automation and digital technology adoption in grocery retail",
    "Supplier sourcing and procurement in grocery retail",
    "Inbound logistics and distribution centre handling in grocery retail",
    "Store operations and production processes in grocery retail",
    "Outbound logistics and home delivery in grocery retail",
    "Marketing and sales channels in grocery retail",
    "Customer service and after-sales support in grocery retail",
)


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query: the fair test of 'can this block accept
    evidence for the question it asks?'.  A block that still finds nothing here has a cue
    set that does not match its own query."""
    return {"results": [{
        "title": query[:120],
        "abstract": "Evidence on " + query[:110] + ". A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Strategy", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def realistic(query, databases=None, limit=10, year_from=None):
    """A plausible real title: the block's first cue word and the industry, nothing more.
    This is the honest measure of the live gate, kept separate from the correctness one."""
    words = [word for word in str(query).split() if word.isalpha()]
    stem = " ".join(words[:2])
    return {"results": [{
        "title": "%s in grocery retail" % stem.title(),
        "abstract": "A study of %s in the grocery retail market. A second sentence follows." % stem,
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Strategy", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def empty(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def run(template, sources=True):
    profile = P.PROFILES[template]
    field = (profile.get("unit") or {}).get("field") or "industry"
    kwargs = {}
    if field == "industry":
        kwargs["industry"] = INDUSTRY
    elif field == "process":
        kwargs["unit_value"] = "the store rota and stock-replenishment change"
    elif field == "country":
        kwargs["country"] = "Iran"
    else:
        kwargs["unit_value"] = "the campus shop offer"
    side = academic if sources else empty
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, BRIEFS.get(field, BRIEFS["industry"]), **kwargs)


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


def check(template, sources, problems):
    profile = P.PROFILES[template]
    label = profile["label"]
    try:
        result = run(template, sources=sources)
    except Exception as error:                                  # noqa: BLE001
        problems.append((template, "sources=%s" % sources, "COMPLETE RAISED: %s" % error))
        return None, None, None
    tag = "sources=%s" % sources

    if result.get("framework") != label:
        problems.append((template, tag, "framework %r != label %r" % (result.get("framework"), label)))
    declared = [block["key"] for block in profile["blocks"]]
    got = [block["key"] for block in result["blocks"]]
    if got != declared:
        problems.append((template, tag, "block keys %r != declared %r" % (got, declared)))
    for block in result["blocks"]:
        if not block["items"] and not block["gap"]:
            problems.append((template, block["key"], "V-12: no item and no named gap"))
        for item in block["items"]:
            if item.get("provenance") == "sourced":
                if not item.get("source"):
                    problems.append((template, block["key"], "sourced item has no source"))
                if not item.get("citation"):
                    problems.append((template, block["key"], "sourced item has no citation"))
    background = [block["key"] for block in result["blocks"]
                  if block["items"] and all(i["provenance"] == "background" for i in block["items"])]

    with_byline = dict(result, byline=["A Student", "Example University"])
    report = completion.draft(with_byline, "apa", "draft", "mid")
    payload = completion.draft_bytes(with_byline, "apa", report, "draft", "mid")
    text = text_of(payload)

    headings = [section["heading"] for section in report["sections"]]
    if headings[0] != "Introduction":
        problems.append((template, "paper", "first heading is %r" % headings[0]))
    if headings[-2:] != ["Conclusion", "References"]:
        problems.append((template, "paper", "last headings are %r" % headings[-2:]))
    levels = [int(section["level"]) for section in report["sections"]]
    for previous, level in zip(levels, levels[1:]):
        if level > previous + 1:
            problems.append((template, "paper", "heading level jump %d -> %d" % (previous, level)))
    if "A Student" not in text:
        problems.append((template, "paper", "byline missing from the title page"))
    for placeholder in paper.META:
        if placeholder in text.lower():
            problems.append((template, "paper", "placeholder %r printed" % placeholder))
    if "Diagram to draw" in text:
        problems.append((template, "paper", "promises a diagram"))
    for fragment in ("How this was produced", "Specification hash", "Code hash", "Method: "):
        if fragment in text:
            problems.append((template, "paper", "specification footer %r" % fragment))
    hit = LONG.search(text)
    if hit:
        problems.append((template, "paper", "raw decimal %r" % hit.group(0)))
    for mark in REPR:
        if mark in text:
            problems.append((template, "paper", "Python repr %r in the paper" % mark))
    for weak in (r"\ba activitie\b", r"\bA activitie\b", r"\ba entrie\b", r"\bA entrie\b",
                 r"\ba element\b", r"\ba assumption\b", r"\ba outcome\b"):
        if re.search(weak, text):
            problems.append((template, "paper", "article/singular %r" % weak))
    if not sources and background and "No source was found for this part" not in text:
        problems.append((template, "paper", "background printed without disclosure"))
    if report["words"] < 400:
        problems.append((template, "paper", "only %d words" % report["words"]))

    figure = next((section["figure"] for section in report["sections"] if section.get("figure")), None)
    if figure:
        cells = [cell for grid in figure["grids"] for row in grid["rows"] for cell in row]
        blank = [cell["label"] for cell in cells if not cell["bullets"] and not cell["gap"]]
        if blank:
            problems.append((template, "figure", "empty cells: %s" % blank[:4]))
    deep(template, result, report, text, problems, sources)
    return result, report, payload



def deep(template, result, report, text, problems, sources=True):
    """What a reader can check beyond the shape: evidence, references, the figure."""
    profile = P.PROFILES[template]
    sourced = [(block["key"], item) for block in result["blocks"]
               for item in block["items"] if item.get("provenance") == "sourced"]
    if sourced:
        # V-01 + one source may not fill two dimensions
        sources = [item.get("source") for _key, item in sourced]
        if len(sources) != len(set(sources)):
            problems.append((template, "evidence", "%d sourced items share %d sources"
                             % (len(sources), len(set(sources)))))
        # V-13: every reference printed is cited in the body
        references = report["sections"][-1]["lines"] if report["sections"] else []
        body = "\n".join("\n".join(section["lines"]) for section in report["sections"][:-1])
        for reference in references:
            if reference == "No sources were used.":
                continue
            author = re.split(r"\s*[,(]", str(reference))[0].strip()
            if author and author not in body:
                problems.append((template, "references", "reference not cited in the body: %r"
                                 % str(reference)[:80]))
        # every sourced item's citation reaches its own section
        for section in report["sections"]:
            for block in result["blocks"]:
                if (block.get("label") or "").upper() == section["heading"].upper():
                    cites = [item.get("citation") for item in block["items"]
                             if item.get("provenance") == "sourced" and item.get("citation")]
                    section_text = " ".join(section["lines"])
                    for cite in dict.fromkeys(cites):
                        if cite not in section_text:
                            problems.append((template, block["key"],
                                             "citation %r missing from its section" % cite))
    elif sources:
        problems.append((template, "evidence", "no sourced item reached the paper"))

    # a named gap must say what to state, not just that something is missing
    for block in result["blocks"]:
        if block.get("gap") and not block.get("items"):
            note = (profile.get("notes") or {}).get(block["key"]) or {}
            probe = note.get("probe") or block.get("probe") or ""
            if probe and probe.lower() not in block["gap"].lower() and "What to state" not in block["gap"]:
                problems.append((template, block["key"], "gap does not say what to state: %r"
                                 % block["gap"][:90]))

    # the figure's labels must be the block labels, not a second vocabulary
    figure = next((section["figure"] for section in report["sections"] if section.get("figure")), None)
    if figure:
        labels = {cell["label"] for grid in figure["grids"] for row in grid["rows"] for cell in row}
        declared = {block["label"] for block in profile["blocks"]}
        strays = sorted(label for label in labels if label not in declared)
        if strays:
            problems.append((template, "figure", "labels that are not block labels: %s" % strays[:4]))
        if len(labels) != len(declared):
            problems.append((template, "figure", "%d figure labels for %d blocks"
                             % (len(labels), len(declared))))

    # the words the paper must never contain
    for phrase in ("No evidence was found for this part, and the instruction does not describe it",
                   "not supplied", "add your"):
        if phrase in text.lower():
            problems.append((template, "paper", "instructional wording %r" % phrase))


def determinism(template, problems):
    first = check(template, True, [])[2]
    second = check(template, True, [])[2]
    if first is not None and second is not None and first != second:
        problems.append((template, "paper", "two identical runs produced different bytes"))


def routes(problems):
    template = "template_value_chain"
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                     {"template": template, "instruction": BRIEFS["industry"],
                                      "industry": INDUSTRY})
    if status != 200:
        problems.append((template, "route", "/complete returned %s: %s" % (status, payload)))
        return
    result = payload.get("completion") if isinstance(payload, dict) and payload.get("completion") else payload
    status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                 {"completion": result, "version": "draft"})
    if status != 200:
        problems.append((template, "route", "/report returned %s: %s" % (status, str(payload)[:120])))
    # a brief that names its industry needs no industry argument: the guard reads it
    status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                 {"template": template, "instruction": BRIEFS["industry"]})
    if status != 200:
        problems.append((template, "route", "a brief naming the industry was refused: %s" % status))
    # a brief with no industry anywhere in it must be refused, with a reason that names the market
    status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                 {"template": template,
                                  "instruction": "A firm is reviewing its activities and needs the value chain."})
    if status == 200:
        problems.append((template, "route", "a brief with no industry was accepted"))
    elif "market" not in str(payload).lower():
        problems.append((template, "route", "the refusal does not name the market: %s" % str(payload)[:100]))
    # an accounting brief on a framework shelf must be refused, not dressed in evidence
    status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                 {"template": template,
                                  "instruction": "Prepare the trial balance and the journal entries for the month.",
                                  "industry": INDUSTRY})
    if status == 200:
        problems.append((template, "route", "an accounting brief was accepted"))
    # an unknown template must be refused, not silently defaulted
    status, _payload = api.handle("POST", "/api/cases/frameworks/complete",
                                  {"template": "template_nope", "instruction": BRIEFS["industry"]})
    if status == 200:
        problems.append((template, "route", "an unknown template was accepted"))


def main(argv):
    shelf = {sheet["template"] for sheet in subjects.detail("management")["worksheets"]}
    templates = argv or sorted(shelf)
    problems = []
    print("%-34s %-8s %7s %6s" % ("template", "state", "blocks", "words"))
    for template in templates:
        result, report, _payload = check(template, True, problems)
        check(template, False, problems)
        determinism(template, problems)
        if report:
            print("%-34s %-8s %7d %6d" % (template, "ok", len(result["blocks"]), report["words"]))
    routes(problems)
    print("\n%d problem(s)" % len(problems))
    for template, where, what in problems:
        print("  %-34s %-12s %s" % (template, where[:12], what[:150]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

