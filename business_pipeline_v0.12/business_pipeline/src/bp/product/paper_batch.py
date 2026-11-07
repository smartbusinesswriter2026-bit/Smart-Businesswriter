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
from . import sources as source_finder
from . import subjects as subject_index

FORMAT = "bp-paper-preview/1"

#: Injected by the server (the presets live in `server.py` next to the routes).
PRESETS = {}
_DESCRIBE = None
_RUN = None

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


def configure(run, describe=None, presets=None):
    """Attach the frozen method runner and the published presets."""
    global _RUN, _DESCRIBE, PRESETS
    _RUN = run
    _DESCRIBE = describe
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
    supported = bool(tool.get("method")) and tool.get("method") in methods.LIBRARY
    raw_group = tool.get("group") or "General"
    return {
        "key": tool.get("key") or tool.get("preset") or tool.get("method"),
        "label": tool.get("label") or tool.get("key") or "",
        "method": tool.get("method") or "",
        "preset": tool.get("preset") or "",
        "what": tool.get("what") or "",
        "group": _human(raw_group),
        "group_key": raw_group,
        "supported": supported,
        "has_defaults": bool(supported and preset and (preset.get("inputs") or {})),
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


def generate_one(subject_id, tile_key, style="apa", length=1200, evidence="corpus"):
    """Generate one tile's paper.  Returns a result dict; raises on a hard failure."""
    subject, group, tile = _find_tile(subject_id, tile_key)
    started = time.perf_counter()
    if not tile.get("has_defaults"):
        reason = ("this tile has no published default inputs" if tile.get("supported")
                  else "this tile is a decision framework, not a frozen computation")
        return {"tile_key": tile_key, "label": tile.get("label") or tile_key,
                "status": "needs_input", "error": reason, "duration_ms": 0}
    preset = _preset_for({"preset": tile.get("preset")})
    objective = (preset or {}).get("objective") or tile.get("objective") or tile.get("label")
    inputs = (preset or {}).get("inputs") or {}
    brief = _brief(subject, tile, objective, inputs)

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

    output = _run_method(tile, inputs)
    if isinstance(output, dict):
        recorded = {str(name): str(value) for name, value in output.items()}
    else:
        recorded = {str(row.get("output") or "value"): str(output)}
    state.setdefault("computations", {})[row["key"]] = {
        "ok": True, "method": tile["method"], "inputs": inputs,
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
    data = conductor.docx_bytes(state, byline=["Smart Business Writer", "Tile preview"])
    return {
        "tile_key": tile_key,
        "label": tile.get("label") or tile_key,
        "group": group["label"],
        "status": "ok",
        "objective": objective,
        "brief": brief,
        "filename": _safe_name("%s - %s" % (subject["label"], tile.get("label") or tile_key)) + ".docx",
        "bytes": data,
        "sections": state["draft"].get("outline") or [],
        "title": state["draft"].get("title") or "",
        "sources": len(state.get("sources") or []),
        "background": len(background),
        "gaps": len(state.get("gaps") or []),
        "evidence_errors": errors,
        "computation": recorded,
        "inputs": inputs,
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


def start_run(subject_id, tile_keys, style="apa", evidence="corpus", length=1200):
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
                                      evidence=manifest.get("evidence") or "corpus")
            except Exception as error:
                result = {"tile_key": key, "label": key, "status": "error",
                          "error": str(error)[:500], "duration_ms": 0}
            data = result.pop("bytes", None)
            outline = result.pop("sections", None)
            title = result.pop("title", "")
            if data:
                path = os.path.join(run_dir, result["filename"])
                with open(path, "wb") as handle:
                    handle.write(data)
                result["size"] = len(data)
                if outline:
                    completed_sections.append((title or result.get("label") or key, outline))
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
            if name.endswith(".docx"):
                archive.write(os.path.join(run_dir, name), arcname=name)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        archive.writestr("index.html", _index_html(manifest))
        archive.writestr("instructions.md", _instructions_md(manifest))
    return buffer.getvalue()


def _instructions_md(manifest):
    """The prefilled instruction behind each paper, so the tile's behaviour is inspectable."""
    lines = ["# %s - prefilled tile instructions" % (manifest.get("label") or "Tile previews"),
             "", "Generated %s. Each paper is the writer's own output for the instruction below."
             % (manifest.get("created_at") or ""), ""]
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
        filename = row.get("filename") or ""
        if row.get("status") == "ok" and filename:
            rows.append('<li><a href="%s">%s</a> - %s - %s bytes</li>' % (
                _escape(filename), _escape(filename), _escape(row.get("group") or ""),
                row.get("size") or 0))
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
