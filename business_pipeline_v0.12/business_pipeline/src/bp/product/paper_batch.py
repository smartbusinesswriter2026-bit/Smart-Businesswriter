"""Automated testing: one real paper per subject tile, from a prefilled instruction.

The owner inspects how the writer writes by generating the product's own `.docx`
for a tile.  This module does **not** write a paper itself: it takes the tile's
published example (the preset objective and its declared figures), turns it into
the ideal instruction for that tile, and drives the conductor exactly as a
student run does - plan, declared computation, evidence, draft, Word renderer.

Two honest choices are made here and named in the paper:

* The paper is a **no-framework** paper.  A tile is a computation, not a
  strategic framework, so the analysis is not wrapped in a PESTEL or Five Forces
  paper it did not ask for.
* Evidence is the **owned corpus**, searched by the tile's own words.  A
  sentence is quoted only when it is in the page the corpus returned; a page
  that does not match the tile is not used, and an empty result is a named gap,
  never a filled citation.  No source, author or year is invented.

Runs are stored under ``state/paper_previews/<run_id>/`` so a batch can be
downloaded after the page is reloaded.  The design lane owns this module; the
frozen method library is only read.
"""

import io
import json
import os
import re
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone

from .. import methods
from . import capabilities
from . import chat as conductor
from . import paper
from . import session_paper
from . import sources as source_finder
from . import spreadsheets
from . import subjects as subject_index

FORMAT = "bp-paper-preview/1"

#: Injected by the server (the presets live in `server.py` next to the routes).
PRESETS = {}
_DESCRIBE = None
_RUN = None
_STATEMENTS = None

_STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                      "state", "paper_previews")
_STORE = os.path.normpath(_STORE)

_LOCK = threading.Lock()
_SECTIONS = None
_SECTIONS_LOCK = threading.Lock()

STOP = set(
    "the a an and or of to in for from with by on at as is are was were be been being this that these those "
    "it its their our your we you they he she them his her which who whom what when where why how not no "
    "than then so such can could may might will would should must do does did done have has had using use "
    "used per each any all both more most less least other than into over under between within without "
    "about across after before during before up down out off again further once here there".split()
)


def configure(run, describe=None, presets=None, statements=None):
    """Attach the frozen method runner, the published presets and the statements service."""
    global _RUN, _DESCRIBE, PRESETS, _STATEMENTS
    _RUN = run
    _DESCRIBE = describe
    _STATEMENTS = statements
    if presets is not None:
        PRESETS = presets
    if conductor.METHOD_RUN is None and run is not None:
        conductor.set_method_compute(run, describe)


# ───────────────────────────── catalogue ─────────────────────────────

def _preset_for(tool):
    preset = PRESETS.get(tool.get("preset") or "")
    if not isinstance(preset, dict):
        return None
    return preset


def _human(name):
    text = str(name or "").replace("_", " ").strip()
    return (text[:1].upper() + text[1:]) if text else "General"


def _tile_row(tool):
    preset = _preset_for(tool)
    service = tool.get("service") or ""
    supported = bool(tool.get("method")) and tool.get("method") in methods.LIBRARY
    if service == "statements":
        supported = True
    raw_group = tool.get("group") or "General"
    return {
        "key": tool.get("key") or tool.get("preset") or tool.get("method"),
        "label": tool.get("label") or tool.get("key") or "",
        "method": tool.get("method") or "",
        "service": service,
        "preset": tool.get("preset") or "",
        "what": tool.get("what") or "",
        "group": _human(raw_group),
        "group_key": raw_group,
        "supported": supported,
        "has_defaults": bool(supported and (service == "statements" or (preset and (preset.get("inputs") or {})))),
        "objective": (preset or {}).get("objective") or (tool.get("what") or tool.get("label") or ""),
        "defaults": (preset or {}).get("inputs") or {},
    }


def sections(refresh=False):
    """Every subject as a section, every tile group as a collapsible subsection."""
    global _SECTIONS
    with _SECTIONS_LOCK:
        if _SECTIONS is not None and not refresh:
            return _SECTIONS
        out = []
        for definition in subject_index.SUBJECT_DEFS:
            sid = definition.get("id")
            label = definition.get("label") or sid
            if not sid:
                continue
            try:
                detail = subject_index.detail(sid)
            except Exception as error:
                out.append({"id": sid, "label": label, "error": str(error)[:200], "groups": []})
                continue
            groups = OrderedDict()
            for tool in detail.get("tools") or []:
                row = _tile_row(tool)
                groups.setdefault(row["group_key"], []).append(row)
            if sid == "accounting":
                # The statements tile is a service, not a frozen preset, so it is
                # not in SUBJECT_DEFS tools.  It is added here so the Testing tab
                # (and the shared upload store) can exercise it like any other tile.
                groups.setdefault("Bookkeeping", []).append({
                    "key": "statements", "label": "Financial statements", "method": "",
                    "service": "statements", "preset": "",
                    "what": "Read the trial balance and prepare the journal, the statements and the notes.",
                    "group": "Bookkeeping", "group_key": "Bookkeeping",
                    "supported": True, "has_defaults": True,
                    "objective": "Read the trial balance and prepare the statements.",
                    "defaults": {},
                })
            out.append({
                "id": sid,
                "label": label,
                "icon": detail.get("icon") or "",
                "summary": detail.get("summary") or "",
                "groups": [{"key": name, "label": _human(name), "tiles": tiles}
                           for name, tiles in groups.items()],
            })
        _SECTIONS = {"format": FORMAT, "subjects": out}
        return _SECTIONS


def _find_tile(subject_id, tile_key):
    data = sections()
    subject = next((s for s in data["subjects"] if s["id"] == subject_id), None)
    if not subject:
        raise KeyError("no such subject: " + str(subject_id))
    for group in subject["groups"]:
        for tile in group["tiles"]:
            if tile["key"] == tile_key:
                return subject, group, tile
    raise KeyError("no such tile: " + str(tile_key))


# ───────────────────────────── formatting ─────────────────────────────

def _safe_name(text):
    text = re.sub(r'[\\/:*?"<>|]', "", str(text or ""))
    return re.sub(r"\s+", " ", text).strip(" .") or "paper"


def _fmt_value(value):
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            rows = []
            for index, row in enumerate(value[:5], start=1):
                parts = ["%s %s" % (str(k).replace("_", " "), v) for k, v in row.items()]
                rows.append("row %d: %s" % (index, ", ".join(parts)))
            if len(value) > 5:
                rows.append("%d further rows" % (len(value) - 5))
            return "; ".join(rows)
        return ", ".join(str(item) for item in value[:12])
    if isinstance(value, dict):
        return ", ".join("%s %s" % (str(k).replace("_", " "), v) for k, v in list(value.items())[:8])
    return str(value)


def _declared(inputs):
    return "; ".join("%s %s" % (str(name).replace("_", " "), _fmt_value(value))
                     for name, value in (inputs or {}).items())


def brief_for(subject_id, tile_key):
    """The prefilled instruction, objective and declared figures for one tile."""
    subject, _group, tile = _find_tile(subject_id, tile_key)
    preset = _preset_for({"preset": tile.get("preset")}) or {}
    objective = preset.get("objective") or tile.get("objective") or tile.get("label")
    inputs = preset.get("inputs") or {}
    return {"objective": objective, "inputs": inputs,
            "brief": _brief(subject, tile, objective, inputs),
            "tile": tile, "subject": subject}


def _brief(subject, tile, objective, inputs):
    declared = _declared(inputs)
    what = " ".join(str(tile.get("what") or "").split())[:400]
    pieces = [
        "A business is preparing a %s analysis." % subject["label"].lower(),
        "The question is: %s." % str(objective).rstrip(" .?!"),
    ]
    if what:
        pieces.append("The tile covers %s." % what.rstrip("."))
    if declared:
        pieces.append("The declared figures are: %s." % declared)
    pieces.append("Use %s in a competitive market and industry context, and report the method's result."
                  % tile["label"].lower())
    return " ".join(pieces)


def _cue_words(text):
    words = [w for w in re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower())
             if len(w) >= 3 and w not in STOP]
    out = []
    for word in words:
        if word not in out:
            out.append(word)
    return out[:24]


def _best_sentence(text, cues):
    """The sentence in the retrieved page that is most on the tile's words."""
    cue_set = set(cues)
    best, score = "", 0
    for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "")):
        sentence = sentence.strip()
        if not (40 <= len(sentence) <= 480):
            continue
        words = set(re.findall(r"[a-z][a-z0-9'-]+", sentence.lower()))
        hit = len(words & cue_set)
        if hit > score:
            best, score = sentence, hit
    return best, score


def _seed_corpus(state, subject, tile, objective):
    """Place corpus passages on the paper's one evidence dimension.

    The corpus is searched by the tile's own words.  A page is used only when a
    sentence in it matches the tile, and the quote is that sentence - never a
    summary, never a citation the corpus did not return.  Nothing found is a
    named gap.
    """
    cues = _cue_words(" ".join([tile.get("label") or "", objective or "",
                               tile.get("what") or "", subject.get("label") or ""]))
    queries = [
        " ".join([tile.get("label") or "", objective or "", " ".join(cues[:8])]),
        " ".join([tile.get("label") or "", subject.get("label") or "", "business"]),
    ]
    hits, errors = [], []
    seen_queries = set()
    for query in queries:
        query = " ".join(query.split())
        if not query or query in seen_queries:
            continue
        seen_queries.add(query)
        try:
            found = source_finder.search_academic(query, databases=["corpus"], limit=12)
        except Exception as error:
            errors.append(str(error)[:160])
            continue
        hits.extend(found.get("results") or [])
        if len(hits) >= 8:
            break

    scored, seen_docs, seen_titles = [], set(), set()
    for item in hits:
        doc_id = item.get("doc_id") or item.get("corpus_key") or item.get("title")
        if doc_id in seen_docs:
            continue
        text = item.get("abstract") or item.get("text") or ""
        quote, score = _best_sentence(text, cues)
        if not quote:
            continue
        title_key = re.sub(r"\W+", " ", (item.get("title") or "").lower()).strip()
        if title_key in seen_titles:
            continue
        seen_docs.add(doc_id)
        seen_titles.add(title_key)
        scored.append((score, item, quote))
    scored.sort(key=lambda row: -row[0])

    # A sentence that shares two or more of the tile's own words is citable.
    # A page that shares only one is background: the retriever saw it, but it
    # does not support a citation for this tile, so it is labelled as background
    # rather than attached to the paper as evidence.
    accepted = [row for row in scored if row[0] >= 2]
    weak = [row for row in scored if row[0] == 1]

    sources, evidence = [], []
    for score, item, quote in accepted[:4]:
        source_id = "S%d" % (len(sources) + 1)
        authors = str(item.get("authors") or "").strip()
        if authors.lower() in ("", "unknown"):
            authors = ""
        title = item.get("title") or ""
        year = item.get("year")
        if not year:
            # Some corpus titles carry the edition year in brackets; it is the
            # document's own statement, not something guessed here.
            match = re.search(r"\((19|20)\d{2}[a-z]?\)", title)
            if match:
                year = int(match.group(0)[1:5])
                title = (title[:match.start()] + title[match.end():]).strip(" ,.-")
        record = {
            "id": source_id,
            "title": title,
            "authors": authors,
            "authors_list": [part.strip() for part in authors.split(";") if part.strip()],
            "year": year,
            "venue": item.get("venue") or item.get("publisher") or "",
            "publisher": item.get("publisher") or "",
            "volume": item.get("volume") or "",
            "issue": item.get("issue") or "",
            "pages": item.get("pages") or "",
            "doi": item.get("doi") or item.get("url") or "",
            "database": "Proprietary corpus",
            "abstract": quote,
        }
        sources.append(record)
        evidence.append({
            "id": "E%d" % (len(evidence) + 1),
            "dimension": "evidence",
            "claim": quote,
            "quote": quote,
            "source_id": source_id,
            "status": "accepted",
        })

    background = []
    if not evidence:
        for score, item, quote in weak[:2]:
            title = item.get("title") or ""
            year = item.get("year")
            if not year:
                match = re.search(r"\((19|20)\d{2}[a-z]?\)", title)
                if match:
                    year = int(match.group(0)[1:5])
                    title = (title[:match.start()] + title[match.end():]).strip(" ,.-")
            background.append({"title": title, "year": year, "quote": quote,
                               "database": item.get("database") or "Proprietary corpus"})

    gaps = []
    if not evidence:
        gaps.append({"dimension": "evidence", "label": "Citable evidence",
                     "reason": "no corpus page matched this tile closely enough to cite; a labelled "
                               "background paragraph names what the retriever saw"})
    state.update({"sources": sources, "evidence": evidence, "gaps": gaps,
                  "background": background, "notes": [], "stage": "evidence"})
    return len(sources), errors, background


# ───────────────────────────── generation ─────────────────────────────

def _capability_row(tile, group):
    entry = None
    for candidate in capabilities.ENTRIES.values():
        if candidate.get("method") == tile.get("method"):
            entry = candidate
            break
    entry = entry or {}
    row = {
        "key": entry.get("key") or tile.get("preset") or tile["key"],
        "method": tile.get("method") or "",
        "label": tile.get("label") or entry.get("label") or tile["key"],
        "slot": list(entry.get("slot") or [group, tile.get("label") or tile["key"]])[:2],
        "integration": entry.get("integration") or "Framework and Declared Figures",
        "because": "the tile's prefilled instruction declares these figures",
        "not": entry.get("not") or "",
        "inputs_required": [],
        "inputs": {},
        "one_of": [],
        "min_inputs": entry.get("min_inputs"),
        "row_fields": {},
        "licenses": entry.get("licenses") or "",
        "output": entry.get("output"),
    }
    if len(row["slot"]) < 2:
        row["slot"].append(tile.get("label") or tile["key"])
    return row


def _run_method(tile, inputs):
    method = methods.LIBRARY.get(tile.get("method") or "")
    if method is None:
        raise ValueError("the method %r is not in the frozen core" % (tile.get("method"),))
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(str(e) for e in errors)[:300])
    return method.impl(inputs)


def _tidy(state, tile, objective, source_count, background=None):
    """Name the paper for the tile and remove framework phrasing it does not use."""
    draft = state.get("draft") or {}
    draft["title"] = "%s: %s" % (tile.get("label") or tile["key"], str(objective).rstrip(" .?!"))
    outline = draft.get("outline") or []
    background = background or []
    evidence_text = (
        "The cited sources are the corpus pages that matched this tile's subject. They describe the method "
        "and its business context in general; they do not measure this firm's own figures. The computation "
        "above uses only the declared inputs, and a figure that does not follow from them is not reported."
        if source_count else
        ("No corpus page matched this tile closely enough to cite. The pages the retriever saw are listed "
         "under Background Reading; they are background only, not evidence for the result."
         if background else
         "No corpus page matched this tile's subject, so the reference list is empty. The gap is named in "
         "the limitations rather than filled with a source the corpus does not hold.")
    )
    intro = (
        "The decision under analysis is: %s. The paper applies %s to the declared figures and reports the "
        "frozen method's result. %s" % (
            str(objective).rstrip(" .?!"), str(tile.get("label") or "").lower(),
            "The evidence section records what the corpus supports and what it does not."
            if source_count else
            "No corpus page matched the tile, so the reference list is empty and the gap is named."
        )
    )
    reading = (
        "The computation above is arithmetic on the declared inputs. It holds only for those inputs and "
        "does not test whether they are achievable."
    )
    change_text = (
        "The result follows from the declared figures. Changing any one of them changes the result, and a "
        "different set would have to be declared and run again rather than inferred from this one. A "
        "firm-level study would test the position more directly than the market-level sources above."
    )
    for section in outline:
        heading = str(section.get("heading") or "")
        if heading == "Introduction":
            section["lines"] = [intro]
        elif heading in ("Framework and Declared Figures", "Framework and declared figures") \
                or heading.startswith("Framework and "):
            section["heading"] = "Reading the result"
            section["lines"] = [reading]
        elif heading == "What the Evidence Shows Together":
            section["lines"] = [evidence_text]
        elif heading == "What Would Change the Answer":
            section["lines"] = [change_text]
        cleaned = []
        for line in section.get("lines") or []:
            line = str(line)
            line = line.replace("No framework", "no named framework")
            line = line.replace("no Framework", "no named framework")
            line = line.replace(". No named framework is used.", ".")
            line = line.replace("No named framework is used. ", "")
            cleaned.append(line)
        section["lines"] = cleaned
    if background:
        lines = [
            "The corpus returned the following pages for this tile's words. None shared enough of the tile's "
            "vocabulary to be cited, so they are background reading only; the result does not rely on them."
        ]
        for row in background:
            title = str(row.get("title") or "").strip()
            year = row.get("year")
            if year:
                title += " (%s)" % year
            quote = str(row.get("quote") or "").strip()
            if quote:
                lines.append((title + ". " + quote).strip())
        insert_at = len(outline)
        for index, section in enumerate(outline):
            if str(section.get("heading") or "") in ("References", "Bibliography", "Works Cited"):
                insert_at = index
                break
        outline.insert(insert_at, paper.section("Background Reading (not cited)", paper.H1, lines))
    draft["outline"] = outline
    draft["sections"] = paper.flatten(outline)
    state["draft"] = draft
    # The framework draft scanned the declared input names for claim words; the
    # evidence paragraph above no longer lists them, so the scan is redone on the
    # text the paper actually carries.  A claim the tile really makes is still
    # caught; a field name such as "definitely_would_buy" is not a claim.
    try:
        state["claim_problems"] = conductor._claim_scan(outline)
    except Exception:
        pass
    return state


def _workbook_bundle(subject, tile, objective, inputs, recorded):
    """The tile's recorded computation in the shape the workbook writer reads."""
    artifacts = [{"id": str(name), "metric": str(name), "value": value,
                  "unit": "", "precision": None, "derivation": ""}
                 for name, value in (recorded or {}).items()
                 if not str(name).startswith("_")]
    return {
        "id": "tile-%s-%s" % (subject.get("id") or "subject", tile.get("key") or "tile"),
        "title": "%s: %s" % (tile.get("label") or tile.get("key"), str(objective).rstrip(" .?!")),
        "method": tile.get("method") or "",
        "tier": "",
        "created_at": _now(),
        "delivery": {"appendix": {"artifacts": artifacts}},
        "reperform": {"inputs": inputs or {}, "outputs": recorded or {}},
    }


def _result_sentence(tile, inputs, recorded):
    """One honest sentence: what the method gives on the declared figures."""
    method = methods.LIBRARY.get(tile.get("method") or "")
    label = str(tile.get("label") or tile.get("key") or "").rstrip(" .?!").lower()
    pairs = [(name, value) for name, value in (recorded or {}).items()
             if not str(name).startswith("_")]
    if not pairs:
        return ("Run on the declared figures, the %s records no result. "
                "The inputs above are what it used." % label)
    text = "; ".join(session_paper._render(name, value, method)
                     for name, value in pairs[:4])
    return "Run on the declared figures, the %s gives %s." % (label, text)


def _tile_delivery(tile, inputs, recorded):
    """The record the real tile download renders, built from the frozen method.

    The preview and the student's download now go through the same renderer
    (`session_paper`), so the paper is the same document in both places: the
    result, what was declared and computed, the assumptions, the limitations
    and how the figures were checked.  No framework section, and no reference
    list unless a source was actually declared.
    """
    method = methods.LIBRARY.get(tile.get("method") or "")
    precision = getattr(method, "output_precision", {}) or {}
    units = getattr(method, "output_units", {}) or {}
    artifacts = [{"id": str(name), "metric": str(name), "value": value,
                  "unit": units.get(name, ""), "precision": precision.get(name),
                  "derivation": ""}
                 for name, value in (recorded or {}).items()
                 if not str(name).startswith("_")]
    appendix = {
        "method": {"id": getattr(method, "name", None) or tile.get("method") or ""},
        "reperform": {"inputs": inputs or {}, "outputs": recorded or {}},
        "assumptions": list(getattr(method, "assumptions", ()) or ()),
        "limitations": list(getattr(method, "limitations", ()) or ()),
        "tests": list(getattr(method, "test_names", ()) or ()),
        "honesty": {},
        "artifacts": artifacts,
    }
    return {"report": _result_sentence(tile, inputs, recorded), "appendix": appendix}


STATEMENTS_BRIEF = (
    "The following trial balance was extracted at 31 December 2026.\n"
    "Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
    "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
    "Sales 9,000\nPurchases 4,000\nRent 1,000"
)


def _statements_preview(subject, tile, group, format="docx"):
    """The Financial statements tile in the Testing tab.

    The statements service is attached by the server (it reaches the frozen core
    and the model reader).  The preview uses a deterministic sample trial balance,
    so it needs no model and no API spend: the journal, trial balance and
    statements are built from the figures in the brief.
    """
    if _STATEMENTS is None:
        return {"tile_key": tile.get("key") or "statements",
                "label": tile.get("label") or "Financial statements",
                "group": group.get("label") or "",
                "status": "needs_input",
                "error": "the statements service is not attached; start through the server",
                "duration_ms": 0}
    import time as _time
    started = _time.perf_counter()
    record = _STATEMENTS(STATEMENTS_BRIEF)
    shown = record.get("statements") or {}
    paper_sections = []
    docx_sections = []
    for key, heading in (("income_statement", "Income statement"),
                         ("balance_sheet", "Balance sheet"),
                         ("equity", "Statement of changes in equity"),
                         ("notes", "Notes"),):
        text = str(shown.get(key) or "").strip()
        if text:
            lines = [line for line in text.splitlines() if line.strip()]
            paper_sections.append(paper.section(heading, paper.H1, lines))
            docx_sections.append((heading, lines))
    if not docx_sections:
        lines = ["The statements service returned no statement for this brief."]
        paper_sections.append(paper.section("Statements", paper.H1, lines))
        docx_sections.append(("Statements", lines))
    from . import docx
    title = "%s: the statements for the sample trial balance" % (tile.get("label") or "Financial statements")
    data = docx.render_bytes(title, docx_sections)
    xlsx = None
    if str(format or "docx").lower() in ("xlsx", "both", "excel"):
        appendix = (record.get("core") or {}).get("appendix") or {}
        try:
            xlsx = spreadsheets.to_xlsx({
                "id": "statements-preview",
                "title": title,
                "delivery": {"appendix": {"accounts": appendix}},
            })
        except Exception:
            xlsx = None
    base = _safe_name("%s - %s" % (subject["label"], tile.get("label") or "statements"))
    return {
        "tile_key": tile.get("key") or "statements",
        "label": tile.get("label") or "Financial statements",
        "group": group.get("label") or "",
        "status": "ok",
        "objective": "Read the trial balance and prepare the statements.",
        "brief": STATEMENTS_BRIEF,
        "filename": base + ".docx",
        "bytes": data,
        "xlsx_filename": base + ".xlsx",
        "xlsx": xlsx,
        "sections": paper_sections,
        "title": title,
        "sources": 0,
        "background": 0,
        "gaps": 0,
        "evidence_errors": [],
        "computation": {},
        "inputs": {},
        "duration_ms": int((_time.perf_counter() - started) * 1000),
    }


def generate_one(subject_id, tile_key, style="apa", length=1200, evidence="corpus", format="docx",
                 inputs=None, instruction=None):
    """Generate one tile's paper and, when asked, its workbook.

    `format` is ``docx`` (the paper), ``xlsx`` (the recorded computation as a
    workbook) or ``both``.  The paper is always composed because its computation
    is the record the workbook carries; the format decides what is returned and
    saved, not how the figure is computed.

    `inputs` and `instruction` let a stored case replay its own figures and its
    own problem.  Without them the tile's published preset is used, which is what
    a plain preview wants.
    """
    subject, group, tile = _find_tile(subject_id, tile_key)
    if tile.get("service") == "statements":
        return _statements_preview(subject, tile, group, format)
    started = time.perf_counter()
    # A case carries its own figures.  The published preset is only the fallback for a
    # preview with no inputs, so a tile without defaults can still replay a stored case:
    # refusing here made every accounting case unreplayable even when its figures were
    # complete and correct.
    supplied = isinstance(inputs, dict) and bool(inputs)
    if not tile.get("has_defaults") and not supplied:
        reason = ("this tile has no published default inputs" if tile.get("supported")
                  else "this tile is a decision framework, not a frozen computation")
        return {"tile_key": tile_key, "label": tile.get("label") or tile_key,
                "status": "needs_input", "error": reason, "duration_ms": 0}
    preset = _preset_for({"preset": tile.get("preset")})
    objective = (preset or {}).get("objective") or tile.get("objective") or tile.get("label")
    declared = inputs if isinstance(inputs, dict) and inputs else ((preset or {}).get("inputs") or {})
    brief = str(instruction or "").strip() or _brief(subject, tile, objective, declared)

    state = conductor.start(brief, subject="any", framework="pestel")
    if state.get("stage") == "not_supported":
        raise ValueError("the tile instruction was refused: " + str(state.get("message"))[:300])
    answers = {"decision": objective, "geography": "Global", "period": "5",
               "style": style, "length": str(length)}
    guard = 0
    while conductor.current_question(state):
        question = conductor.current_question(state)
        value = answers.get(question["id"], question.get("default") or "")
        if (value in (None, "") and str(question.get("type") or "") == "choice"):
            choices = question.get("choices") or []
            if choices:
                first = choices[0]
                value = first[0] if isinstance(first, (list, tuple)) else first
        state = conductor.answer(state, question["id"], value)
        guard += 1
        if guard > 30:
            raise ValueError("the tile instruction did not finish its questions")

    # A tile is a computation, not a strategic framework: keep the paper
    # focused on the method and do not carry the framework wrapper.
    state["answers"]["length"] = str(length)
    state["answers"]["framework"] = "none"
    state["framework"] = "none"
    state["frameworks"] = ["none"]
    row = _capability_row(tile, group["label"])
    row["method"] = tile["method"]
    selection = state.setdefault("selection", {})
    selection["selected"] = [row]
    selection["not_included"] = []
    state["plan"] = conductor._plan(state)
    state = conductor.confirm_plan(state)

    output = _run_method(tile, declared)
    if isinstance(output, dict):
        recorded = {str(name): str(value) for name, value in output.items()}
    else:
        recorded = {str(row.get("output") or "value"): str(output)}
    state.setdefault("computations", {})[row["key"]] = {
        "ok": True, "method": tile["method"], "inputs": declared,
        "result": recorded, "from": {},
    }
    source_count, errors, background = _seed_corpus(state, subject, tile, objective)
    if str(evidence or "corpus").lower() == "none":
        state.update({"sources": [], "evidence": [], "background": [],
                      "gaps": [{"dimension": "evidence", "label": "Evidence",
                                "reason": "evidence retrieval was switched off for this preview"}],
                      "stage": "evidence"})
        source_count, background = 0, []
    implications = ("The result is the frozen method's output for the declared figures; it does not "
                    "forecast any figure the inputs do not contain.")
    state = conductor.draft(state, implications=implications)
    state = _tidy(state, tile, objective, source_count, background)
    # The download and the preview are the same paper: render the tile's record
    # through the renderer the student's download uses, so the sections are the
    # result, the declared/computed figures, the assumptions, the limitations and
    # the checks.  The framework outline the conductor builds is not printed.
    delivery = _tile_delivery(tile, declared, recorded)
    title = "%s: %s" % (tile.get("label") or tile_key, str(objective).rstrip(" .?!"))
    paper_sections = session_paper.sections(delivery, title=title)
    data = session_paper.docx_bytes(delivery, title=title)
    xlsx = None
    if str(format or "docx").lower() in ("xlsx", "both", "excel"):
        try:
            xlsx = spreadsheets.to_xlsx(
                _workbook_bundle(subject, tile, objective, declared, recorded))
        except Exception:
            xlsx = None
    return {
        "tile_key": tile_key,
        "label": tile.get("label") or tile_key,
        "group": group["label"],
        "status": "ok",
        "objective": objective,
        "brief": brief,
        "filename": _safe_name("%s - %s" % (subject["label"], tile.get("label") or tile_key)) + ".docx",
        "bytes": data,
        "xlsx_filename": _safe_name("%s - %s" % (subject["label"], tile.get("label") or tile_key)) + ".xlsx",
        "xlsx": xlsx,
        "sections": [paper.section(heading, paper.H1, lines) for heading, lines in paper_sections],
        "title": title,
        "sources": len(state.get("sources") or []),
        "background": len(background),
        "gaps": len(state.get("gaps") or []),
        "evidence_errors": errors,
        "computation": recorded,
        "inputs": declared,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }


# ───────────────────────────── runs ─────────────────────────────

def _now():
    return datetime.now(timezone.utc).isoformat()


def _manifest_path(run_id):
    return os.path.join(_STORE, run_id, "manifest.json")


def _write_manifest(run_dir, manifest):
    path = os.path.join(run_dir, "manifest.json")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def _read_manifest(run_id):
    path = _manifest_path(run_id)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def start_run(subject_id, tile_keys, style="apa", evidence="corpus", length=1200, format="docx"):
    """Create a run directory and start generating the selected tiles in background."""
    subject, _group, _tile = _find_tile(subject_id, tile_keys[0] if tile_keys else "")
    keys = []
    for key in tile_keys or []:
        try:
            _find_tile(subject_id, key)
        except KeyError:
            continue
        if key not in keys:
            keys.append(key)
    if not keys:
        raise ValueError("select at least one tile")
    run_id = uuid.uuid4().hex[:12]
    run_dir = os.path.join(_STORE, run_id)
    os.makedirs(run_dir, exist_ok=True)
    manifest = {
        "format": FORMAT,
        "run_id": run_id,
        "subject": subject["id"],
        "label": subject["label"],
        "created_at": _now(),
        "style": "harvard" if str(style).lower().startswith("harv") else "apa",
        "evidence": "corpus" if evidence != "none" else "none",
        "output": str(format or "docx").lower(),
        "length": int(length or 1200),
        "status": "running",
        "total": len(keys),
        "completed": 0,
        "results": [{"tile_key": key, "label": "", "status": "queued", "error": ""} for key in keys],
    }
    _write_manifest(run_dir, manifest)
    worker = threading.Thread(target=_run, args=(run_id, run_dir, manifest, keys),
                              name="paper-preview-" + run_id, daemon=True)
    worker.start()
    return {"run_id": run_id, "subject": subject["id"], "total": len(keys)}


def _run(run_id, run_dir, manifest, keys):
    completed_sections = []
    try:
        for index, key in enumerate(keys):
            if manifest.get("status") == "stopped":
                break
            try:
                result = generate_one(manifest["subject"], key,
                                      style=manifest["style"], length=manifest["length"],
                                      evidence=manifest.get("evidence") or "corpus",
                                      format=manifest.get("output") or "docx")
            except Exception as error:
                result = {"tile_key": key, "label": key, "status": "error",
                          "error": str(error)[:500], "duration_ms": 0}
            data = result.pop("bytes", None)
            xlsx = result.pop("xlsx", None)
            outline = result.pop("sections", None)
            title = result.pop("title", "")
            output = manifest.get("output") or "docx"
            if data and output in ("docx", "both"):
                path = os.path.join(run_dir, result["filename"])
                with open(path, "wb") as handle:
                    handle.write(data)
                result["size"] = len(data)
                if outline:
                    completed_sections.append((title or result.get("label") or key, outline))
            if xlsx and output in ("xlsx", "both", "excel"):
                path = os.path.join(run_dir, result["xlsx_filename"])
                with open(path, "wb") as handle:
                    handle.write(xlsx)
                result["xlsx_size"] = len(xlsx)
            manifest["results"][index] = result
            manifest["completed"] = index + 1
            _write_manifest(run_dir, manifest)
        manifest["status"] = "done"
        manifest["finished_at"] = _now()
    except Exception as error:
        manifest["status"] = "error"
        manifest["error"] = str(error)[:500]
        manifest["finished_at"] = _now()
    finally:
        try:
            _build_combined(run_dir, manifest, completed_sections)
        except Exception as error:
            manifest["combined_error"] = str(error)[:300]
        _write_manifest(run_dir, manifest)


def _build_combined(run_dir, manifest, collected):
    if not collected:
        return
    sections = []
    for title, outline in collected:
        sections.append(paper.section(title, paper.H1))
        sections.extend(outline)
    data = paper_docx(manifest.get("label") or "Tile previews", sections)
    path = os.path.join(run_dir, "combined.docx")
    with open(path, "wb") as handle:
        handle.write(data)
    manifest["combined"] = "combined.docx"
    manifest["combined_size"] = len(data)


def paper_docx(title, sections):
    """Render a combined preview through the product's Word formatter."""
    from . import docx
    return docx.render_academic(title, sections, "apa",
                                byline=["Smart Business Writer", "Tile previews"])


def status(run_id):
    path = _manifest_path(run_id)
    if not os.path.exists(path):
        raise KeyError("no such run")
    manifest = _read_manifest(run_id)
    # The bytes never leave the result rows; the download route serves them.
    for row in manifest.get("results") or []:
        row.pop("sections", None)
    manifest["progress"] = (float(manifest.get("completed") or 0) / manifest["total"]
                            if manifest.get("total") else 0.0)
    return manifest


def _zip_bytes(run_id):
    run_dir = os.path.join(_STORE, run_id)
    manifest = _read_manifest(run_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(os.listdir(run_dir)):
            if name.endswith((".docx", ".xlsx")):
                archive.write(os.path.join(run_dir, name), arcname=name)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        archive.writestr("index.html", _index_html(manifest))
        archive.writestr("instructions.md", _instructions_md(manifest))
        archive.writestr("explainer.docx", _explainer_docx(manifest))
    return buffer.getvalue()


def _explainer_docx(manifest):
    """The tile, its instruction, its figures, its result and its evidence, as a Word file."""
    from . import docx
    title = "%s - tile explainer" % (manifest.get("label") or "Tile previews")
    sections = []
    lead = ["Generated %s." % (manifest.get("created_at") or ""),
            "Output format: %s." % (manifest.get("output") or "docx")]
    sections.append(("About this run", lead))
    for row in manifest.get("results") or []:
        heading = str(row.get("label") or row.get("tile_key") or "")
        lines = []
        if row.get("group"):
            lines.append("Subsection: %s" % row["group"])
        if row.get("objective"):
            lines.append("Objective: %s" % row["objective"])
        if row.get("brief"):
            if lines:
                lines.append("")
            lines.append("Instruction:")
            lines.append(str(row["brief"]))
        inputs = row.get("inputs") or {}
        if inputs:
            if lines:
                lines.append("")
            lines.append("Declared inputs:")
            lines.extend("- %s: %s" % (str(name).replace("_", " "), value)
                         for name, value in inputs.items())
        computed = row.get("computation") or {}
        if computed:
            if lines:
                lines.append("")
            lines.append("Computed result:")
            lines.extend("- %s: %s" % (str(name).replace("_", " "), value)
                         for name, value in computed.items())
        if lines:
            lines.append("")
        lines.append("Evidence: %s cited source(s), %s background page(s), %s named gap(s)."
                     % (row.get("sources") or 0, row.get("background") or 0, row.get("gaps") or 0))
        lines.append("Generation: %s%s" % (
            row.get("status") or "unknown",
            (" - " + str(row.get("error") or "")) if row.get("error") else ""))
        sections.append((heading or "Tile", lines))
    return docx.render_bytes(title, sections)


def _instructions_md(manifest):
    """The prefilled instruction behind each paper, so the tile's behaviour is inspectable."""
    lines = ["# %s - prefilled tile instructions" % (manifest.get("label") or "Tile previews"),
             "", "Generated %s. Each paper is the writer's own output for the instruction below."
             % (manifest.get("created_at") or ""),
             "Output format: %s." % (manifest.get("output") or "docx"), ""]
    for row in manifest.get("results") or []:
        lines.append("## %s" % (row.get("label") or row.get("tile_key") or ""))
        if row.get("group"):
            lines.append("")
            lines.append("Subsection: %s" % row["group"])
        if row.get("objective"):
            lines.append("")
            lines.append("Objective: %s" % row["objective"])
        if row.get("brief"):
            lines.append("")
            lines.append("Instruction:")
            lines.append("")
            lines.append("> %s" % row["brief"])
        if row.get("status") != "ok":
            lines.append("")
            lines.append("Status: %s - %s" % (row.get("status"), row.get("error") or ""))
        lines.append("")
    return "\n".join(lines)


def _index_html(manifest):
    rows = []
    for row in manifest.get("results") or []:
        if row.get("status") == "ok":
            for label, filename, size in (
                    ("DOCX", row.get("filename"), row.get("size")),
                    ("XLSX", row.get("xlsx_filename"), row.get("xlsx_size"))):
                if filename and size:
                    rows.append('<li><a href="%s">%s</a> - %s - %s bytes</li>' % (
                        _escape(filename), _escape(filename), label, size))
        else:
            rows.append("<li>%s - %s: %s</li>" % (
                _escape(row.get("label") or row.get("tile_key") or ""),
                _escape(row.get("status") or ""), _escape(row.get("error") or "")))
    return ("<!doctype html><meta charset='utf-8'><title>%s</title>"
            "<h1>%s - tile previews</h1><p>Generated %s</p><ul>%s</ul>" % (
                _escape(manifest.get("label") or "Tile previews"),
                _escape(manifest.get("label") or "Tile previews"),
                _escape(manifest.get("created_at") or ""), "".join(rows)))


def _escape(text):
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def download(run_id, fmt="zip"):
    """Return (bytes, filename) for one completed run."""
    if not os.path.exists(_manifest_path(run_id)):
        raise KeyError("no such run")
    manifest = _read_manifest(run_id)
    label = _safe_name(manifest.get("label") or "tile-previews")
    if fmt == "docx":
        path = os.path.join(_STORE, run_id, "combined.docx")
        if not os.path.exists(path):
            raise KeyError("the combined document is not ready")
        with open(path, "rb") as handle:
            return handle.read(), "%s - tile previews.docx" % label
    if fmt == "explainer":
        return _explainer_docx(manifest), "%s - explainer.docx" % label
    return _zip_bytes(run_id), "%s - tile previews.zip" % label


def runs(limit=20, subject=None):
    """Recent runs, newest first, without the per-tile payloads."""
    if not os.path.isdir(_STORE):
        return []
    found = []
    for name in os.listdir(_STORE):
        path = os.path.join(_STORE, name, "manifest.json")
        if not os.path.exists(path):
            continue
        try:
            manifest = _read_manifest(name)
        except Exception:
            continue
        if subject and manifest.get("subject") != subject:
            continue
        manifest.pop("results", None)
        found.append(manifest)
    found.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return found[:limit]
