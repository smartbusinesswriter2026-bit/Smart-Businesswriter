"""The eval rubric: score a delivered paper by code, not by a model.

Every check here is a **decision the code makes about the document**, not a
judgement the model makes about it.  The rubric reuses the product's own
tools rather than re-implementing them, so a rubric that disagreed with the
paper path would be visible in the code, not hidden in it:

* the readable text of a .docx and of a .xlsx: `case_runner._docx_text`,
  `case_runner._xlsx_text`;
* whether a computed value appears in the text: `case_runner._paper_has_value`;
* what counts as a template instruction: `paper.META`;
* what the corpus returned for a tile: `paper_batch._seed_corpus`.

**What the RAG checks can and cannot prove.**  The corpus layer fails open:
when the index is down it returns an empty list and no error, so "no
evidence found" and "no corpus" look the same.  The rubric therefore asks the
index first, and when it is down the RAG score is ``not measured`` — never a
pass.  When the index is up, the rubric checks the pages the tile's own
vocabulary matched:

* a cited page carries the corpus's own title and database, so it resolves
  to a page the corpus returned;
* the quote is a **complete sentence**, not a fragment and not a summary;
* the quote carries the tile's vocabulary, so a quote that could have been
  written by anything else is caught;
* a page that matched only weakly is **background**, and a background page is
  never cited;
* when nothing is citable, the gap is named rather than filled.

The quote is a sentence from the page **by construction**: the product's
extractor returns a sentence of the page's own text and nothing else.  That
extractor is proved by a test in the same file, so the capability is checked
rather than assumed.

**The length of a tile paper is an observation, not a defect.**  A tile paper
is the computation record - the result, the declared figures, the computed
figures, the assumptions, the limitations and the checks - and it is short by
design.  The rubric records the word count and the band so the owner can see
it, and it does not fail a tile paper for being short.
"""

import re

from . import case_runner
from . import paper
from . import paper_batch

#: The sections a tile paper must carry.  This is the contract the case store
#: writes into every seeded case, and the tile path renders it.
TILE_CONTRACT_SECTIONS = ("Result", "Inputs and results", "How the figures were checked")

#: The older phrases a case written before the paper became the computation
#: record may still ask for, and the heading the paper now carries.
LEGACY_PHRASES = {"Declared inputs": "What you declared",
                  "References": None, "Bibliography": None, "Works Cited": None}

#: A quote is a sentence when it ends like one and carries words.  A summary
#: with a colon, or a fragment, is not.
_SENTENCE_END = (".", "!", "?", "…")


def _is_sentence(text):
    """Is this a complete sentence rather than a fragment or a summary?"""
    value = str(text or "").strip()
    if len(value.split()) < 4:
        return False
    if value.endswith(":"):
        return False
    return value.endswith(_SENTENCE_END)


def _numeric_values(computed):
    """The computed values worth looking for in the paper.

    The same rule the case checker uses: the numbers the method returned,
    the first three, and never a zero that is only padding.
    """
    out = []
    for value in (computed or {}).values():
        if not case_runner._is_number(value):
            continue
        try:
            if abs(float(str(value).replace(",", ""))) <= 1e-12:
                continue
        except (TypeError, ValueError):
            pass
        out.append(value)
    return out[:3]


def score_sections(text, contract=None, contains=None):
    """Are the required sections in the paper?

    `contract` names the sections explicitly.  `contains` is the older,
    looser phrase list a case written before the paper became the
    computation record may still carry.
    """
    text = str(text or "")
    missing = []
    for section in (contract or {}).get("sections") or []:
        if section and section not in text:
            missing.append(section)
    for phrase in contains or []:
        if not phrase:
            continue
        wanted = LEGACY_PHRASES.get(phrase, phrase)
        if wanted is None:
            continue
        if wanted not in text:
            missing.append(phrase)
    return {"ok": not missing, "missing": missing}


def score_values(text, computed, workbook_text=""):
    """Do the computed values appear in the paper and in the workbook?"""
    values = _numeric_values(computed)
    in_paper = False
    in_workbook = None
    if values:
        in_paper = any(case_runner._paper_has_value(text, value) for value in values)
        if workbook_text:
            in_workbook = any(case_runner._paper_has_value(workbook_text, value)
                              for value in values)
    return {
        "ok": in_paper,
        "values": [str(value)[:24] for value in values],
        "in_paper": in_paper,
        "in_workbook": in_workbook,
    }


def score_template_instructions(text):
    """Does the paper still carry a template instruction?"""
    low = str(text or "").lower()
    found = [phrase for phrase in paper.META if phrase in low]
    return {"ok": not found, "found": found}


def score_length(text, target=0):
    """The paper's word count, the band it falls in, and whether it met the target.

    The word count is the body text of the rendered document.  For a tile
    paper the answer is an observation, not a verdict: the tile paper is the
    computation record and is short by design, so ``scored`` is False.
    """
    words = len(re.findall(r"\b[\w'-]+\b", str(text or "")))
    from . import chat
    band = chat.length_band(words)
    met = False
    if target:
        met = abs(words - int(target)) <= max(50, int(target) * 0.25)
    return {"words": words, "band": band, "target": int(target or 0),
            "met_target": met, "scored": False,
            "note": "a tile paper is the computation record and is short by design"}


def score_rag(subject, tile_key, objective=None, corpus_up=None):
    """The retrieval score for one tile.

    The score is about what the corpus returned for the tile's own words: the
    pages that could be cited, the pages that are background, and whether a
    background page was ever cited.  When the corpus index is down the score
    is ``not measured`` — a down corpus is not a green corpus.
    """
    if corpus_up is None:
        from . import eval_runner
        corpus_up = eval_runner.corpus_available()
    state = {}
    try:
        subject_row, group, tile = paper_batch._find_tile(subject, tile_key)
    except Exception as error:
        return {"measured": False, "reason": "no such tile: %s" % str(error)[:120],
                "accepted": 0, "background": 0, "corpus_available": bool(corpus_up)}
    if objective is None:
        preset = paper_batch._preset_for({"preset": tile.get("preset")})
        objective = (preset or {}).get("objective") or tile.get("objective") or tile.get("label")

    try:
        count, errors, background_rows = paper_batch._seed_corpus(state, subject_row, tile, objective)
    except Exception as error:
        return {"measured": False, "reason": "the retrieval failed: %s" % str(error)[:160],
                "accepted": 0, "background": 0, "corpus_available": bool(corpus_up)}

    sources = state.get("sources") or []
    background = state.get("background") or []
    gaps = state.get("gaps") or []

    if not corpus_up:
        return {"measured": False, "reason": "the corpus index is not reachable",
                "accepted": len(sources), "background": len(background),
                "corpus_available": False, "gaps": len(gaps),
                "errors": list(errors or [])[:3]}

    cues = paper_batch._cue_words(" ".join([tile.get("label") or "", objective or "",
                                            tile.get("what") or "",
                                            subject_row.get("label") or ""]))
    cue_set = {word.lower() for word in cues}

    problems = []
    cited_titles = set()
    for source in sources:
        title = str(source.get("title") or "").strip()
        quote = str(source.get("abstract") or "").strip()
        if not title:
            problems.append("a cited page carries no title, so it resolves to nothing")
        if source.get("database") != "Proprietary corpus":
            problems.append("a cited page did not come from the corpus")
        if not _is_sentence(quote):
            problems.append("a quote is not a sentence from its page: %r" % quote[:60])
        shared = cue_set & {word.lower() for word in re.findall(r"\b[\w'-]+\b", quote)}
        if len(shared) < 2:
            problems.append("a quote does not carry the tile's own words: %r" % quote[:60])
        cited_titles.add(re.sub(r"\W+", " ", title.lower()).strip())

    for row in background:
        title = re.sub(r"\W+", " ", str(row.get("title") or "").lower()).strip()
        if title and title in cited_titles:
            problems.append("a background page is cited as evidence: %r"
                            % str(row.get("title") or "")[:60])

    if not sources and not gaps:
        problems.append("no page was cited and no gap was named")

    return {
        "measured": True,
        "corpus_available": True,
        "accepted": len(sources),
        "background": len(background),
        "gaps": len(gaps),
        "cited": [{"title": str(s.get("title") or "")[:120],
                   "year": s.get("year"),
                   "quote": str(s.get("abstract") or "")[:120]} for s in sources],
        "problems": problems,
        "errors": list(errors or [])[:3],
    }


def score_paper(text, computed=None, workbook_text="", contract=None, contains=None,
                length_target=0, rag=None):
    """The whole rubric for one delivered paper."""
    sections = score_sections(text, contract=contract, contains=contains)
    values = score_values(text, computed, workbook_text=workbook_text)
    template = score_template_instructions(text)
    length = score_length(text, target=length_target)

    problems = []
    if not sections["ok"]:
        problems.append("the paper does not carry the %s section"
                        % ", ".join(sections["missing"][:3]))
    if not values["ok"]:
        problems.append("the paper does not show any of the computed values")
    if not template["ok"]:
        problems.append("the paper still carries a template instruction: %r"
                        % template["found"][0])
    if rag is not None and rag.get("problems"):
        problems.extend(rag["problems"][:3])

    return {
        "passed": not problems,
        "problems": problems,
        "checks": {
            "sections": sections,
            "values": values,
            "template_instructions": template,
            "length": length,
            "rag": rag,
        },
    }


def score_case(case, result, rag=None):
    """The rubric for one replayed case.

    The case's own contract and phrase list are used when it has them; the
    tile contract is the fallback.
    """
    text = case_runner._docx_text(result.get("bytes") or b"")
    workbook = result.get("xlsx") or b""
    workbook_text = case_runner._xlsx_text(workbook) if workbook else ""
    expected = (case or {}).get("expected") or {}
    computed = result.get("computation") or {}
    return score_paper(text, computed=computed, workbook_text=workbook_text,
                       contract=expected.get("contract"),
                       contains=expected.get("contains"),
                       length_target=0, rag=rag)
