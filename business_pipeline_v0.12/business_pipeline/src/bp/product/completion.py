"""Complete a framework from an instruction and write its paper (product layer).

The framework is data: `bp.product.framework_profiles` supplies its dimensions,
the words that find evidence, its unit of analysis, its interpretive prose, and
its outline.  This module supplies the pipeline, once:

    instruction  -> unit of analysis -> per-dimension retrieval -> gate -> items
                 -> sourced item / student item / labelled assumption / named gap
                 -> review -> worksheet -> Draft or Full paper -> stored document
    -> Word file with a title page.

No fact, rating, number or citation is invented here, and the model that writes
the full paper is allowed to rephrase only.  A framework without a profile is not
completed at all, so an unfinished framework falls back to its plain worksheet
instead of producing a generic paper with the framework's name on it.
"""

import datetime
import json
import os
import re

from concurrent.futures import ThreadPoolExecutor, wait

from . import docx, framework_profiles, guard, matrix, paper, prose, retrieval, writing
from . import rubric as rubric_reader

NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
from .framework_registry import WORDS as FRAMEWORK_WORDS
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b")
CITATION = re.compile(r"\([^()]{1,140}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")
URL = re.compile(r"https?://|doi:", re.I)

#: One deadline for the whole completion, not one per dimension: a slow provider
#: must not hold the page, and an unfinished dimension is named as a gap.
RESEARCH_DEADLINE = float(os.environ.get("BP_RESEARCH_DEADLINE", "20"))

#: Backwards-compatible names for the Five Forces profile (older callers and
#: tests read these; there is still one copy of the words, in the profile).
FORCES = [(block["key"], block["label"], block["cues"])
          for block in framework_profiles.FIVE_FORCES["blocks"]]
FORCE_KEYS = [key for key, _label, _cues in FORCES]

DEFAULT_PROFILE = framework_profiles.FIVE_FORCES


def _profile(template=None):
    return framework_profiles.get(template or DEFAULT_PROFILE["template"]) or DEFAULT_PROFILE


def _clean(value, limit=400):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _country(text):
    return retrieval.country(text)


def _region(country):
    return retrieval.region(country)


def _words(text):
    return len(re.findall(r"[A-Za-z0-9'\u2019%-]+", str(text or "")))


def _singular(word):
    """One of `word`, in English: activities -> activity, dimensions -> dimension.

    ``rstrip("s")`` turned "activities" into "activitie", and the deterministic
    draft printed "a activitie for which no evidence is recorded" in every paper
    whose profile pluralises with -ies.  Read on the produced .docx, not in a unit
    test (2026-11-03).
    """
    text = str(word or "").strip()
    lower = text.lower()
    if lower.endswith("ies") and len(text) > 3:
        return text[:-3] + ("Y" if text[-3].isupper() else "y")
    if lower.endswith(("ses", "xes", "zes", "ches", "shes")):
        return text[:-2]
    if lower.endswith("s") and not lower.endswith("ss"):
        return text[:-1]
    return text


def _article(word):
    """`a` or `an`, from the word that follows it."""
    return "an" if str(word or "")[:1].lower() in "aeiou" else "a"


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split("\n") if part.strip()]


def _kind(item):
    provenance = str(item.get("provenance") or "").lower()
    if provenance == "sourced":
        return "sourced"
    if provenance == "background":
        return "background"
    if provenance in ("student", "user", "own"):
        return "student"
    return "assumption"


def _facts(blocks):
    return [{"key": block.get("key"), "label": block.get("label"),
             "items": [{"text": _clean(item.get("text"), 600), "kind": _kind(item)}
                       for item in block.get("items") or []]}
            for block in blocks]


def _source_text(item):
    try:
        text = writing.reference(item, "apa")
    except Exception:
        text = _clean(item.get("url") or item.get("doi") or item.get("title"), 300)
    # A scraped page carries its own furniture; it is not part of a citation.
    text = re.split(r"\s*(?:Title|Date Range|Table Data)\s*[-|]", str(text or ""))[0]
    return re.sub(r"(?:\.\.\.|\u2026)+\s*", " ", text).strip()


def _cite_from_source(source):
    """An in-text citation from a reference string, for items that arrive without one.

    The worksheet sends text, provenance and source; it has no citation field, so
    a paper generated from the page had references but no in-text citations.
    """
    text = str(source or "").strip()
    year = re.search(r"\((n\.d\.|\d{4})\)", text)
    year = year.group(1) if year else "n.d."
    author = re.split(r"\s*[,(]", text)[0].strip()
    return "(%s, %s)" % (author, year) if author else ""


def _source_cite(item):
    try:
        return writing.in_text(item, "apa")
    except Exception:
        return ""


# -- completion ----------------------------------------------------------------

def _unit(profile, instruction, unit_value):
    """The declared or detected unit of analysis, and the message when it is missing."""
    field = (profile.get("unit") or {}).get("field") or "industry"
    value = _clean(unit_value, 120)
    if field == "industry":
        ok, industry = guard.five_forces_fit(instruction, value)
        if not ok:
            raise ValueError(profile["unit"]["refuse"])
        return {"field": field, "value": industry, "context": industry}
    # A process: named by the student, never detected and never guessed.  The
    # context is the process plus the words the brief uses about it, because a
    # search for supplier or input evidence has to know what it is about.
    if field == "process":
        if not value:
            raise ValueError(profile["unit"]["refuse"])
        context = " ".join(part for part in (value, " ".join(retrieval.topic_words(instruction)[:3])) if part)
        return {"field": field, "value": value, "context": context,
                "region": _region(_country(instruction))}
    # A country or market: named, or explicitly Global.  Never guessed.
    if not value:
        value = _country(instruction)
    if not value:
        raise ValueError(profile["unit"]["refuse"])
    if value.lower() in ("global", "world", "international"):
        return {"field": field, "value": "Global", "country": "", "context": "",
                "region": "Global", "explicit_global": True}
    country = _country(value) or value
    return {"field": field, "value": country, "country": country, "region": _region(country),
            "context": country}


#: A sentence boundary that keeps "90 seconds" and "Pte. Ltd." whole enough for a
#: quoted line: the quote is the student's own sentence, not a paraphrase.
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")


#: At most this many of the student's own sentences are quoted into one part;
#: a block that needs more can be typed into the worksheet after the review.
QUOTE_ITEMS = 3


def _quote_block(profile, block, instruction):
    """The student's own sentences that describe this part of the process.

    A `quote` block takes the instruction word for word, so a student who has
    already written "the order is taken, the meal is assembled and packed" does
    not retype it into the worksheet.  Nothing is paraphrased, reworded or
    inferred: a sentence that does not mention the block's cues is not borrowed
    for it, and a part with no matching sentence is a named gap.

    **What may be borrowed is declared, not inferred from the retrieval cues.**
    `cues` is the vocabulary a *source* is accepted on, and it carries words every
    business brief uses ("change", "review", "cost", "quality", "flow"), so
    matching on it quoted "The manager reviews the change next term" into a cell
    asking what was standardised (D-OPS-03, the same class as D-MGT-03).  A block
    may declare `quote_cues`: the words that make a sentence *about this part*.
    When it does, only those are matched; an empty declaration means the part is
    never taken from the brief at all (it is a judgement or a figure), and the
    block falls through to the research path and then to a named gap.
    """
    declared = block.get("quote_cues")
    cues = set(str(block.get("cues") if declared is None else declared or "").lower().split())
    items = []
    for sentence in _SENTENCE.split(instruction):
        text = _clean(sentence, 600)
        if len(text) < 8:
            continue
        if cues & set(re.findall(r"[a-z][a-z0-9'-]*", text.lower())):
            items.append({"text": text, "provenance": "student", "source": None})
        if len(items) >= QUOTE_ITEMS:
            break
    return items


def _gap_note(profile, block):
    notes = (profile.get("notes") or {}).get(block["key"]) or {}
    probe = notes.get("probe") or block.get("probe")
    fill = framework_profiles.fill_of(block)
    if fill == "gap":
        # D-OPS-04: the sentence says the part is the student's, but a gap must also
        # say *what* to state (V-02).  Both `gap` blocks in the corpus are the value
        # stream map's judgement and proposal cells, and both declare a probe that
        # never reached the paper.
        return ("This part is a judgement or a proposal only you can state, so it is left for you and never "
                "filled by the pipeline."
                + ((" What to state: " + probe + ".") if probe else ""))
    background = (profile.get("assumption") == "probe"
                  and all(framework_profiles.fill_of(item) == "research" for item in profile["blocks"]))
    if background:
        return "No source was found for this part; it is written from general background and is not cited."
    return ("No evidence was found for this part, and the instruction does not describe it."
            + ((" What to state: " + probe + ".") if probe else ""))


def _queries(block, context, region, country=""):
    """One query per phrase; the country is added once, never twice."""
    query_context = context or ""
    if country and country.lower() not in query_context.lower():
        query_context = " ".join(part for part in (country, query_context) if part)
    return [retrieval.build_query(phrase, query_context, region) for phrase in block.get("queries") or []]


def _one_block(profile, block, context, region, year_from, country="", corpus_doc_counts=None):
    """Retrieve one dimension; failures are reported, never raised into the page."""
    try:
        found = retrieval.retrieve(
            key=block["key"], cues=block.get("cues"), queries=_queries(block, context, region, country),
            context=retrieval.context_words(context), geography=region, year_from=year_from,
            category=block.get("category"), gate=profile.get("gate"),
            sites=_sites(profile), providers=profile.get("providers"),
            corpus_doc_cap=3, corpus_doc_counts=corpus_doc_counts,
            topic=context or profile.get("subject") or "")
    except Exception as error:
        found = {"items": [], "queries": _queries(block, context, region, country), "dropped": 0,
                 "errors": [{"database": "retrieval", "error": str(error)[:160]}],
                 "skipped": [], "notices": [], "timed_out": False}
    items = []
    for source in found.get("items") or []:
        quote = retrieval.first_sentence(source, sentences=2)
        if not quote:
            continue
        items.append({"text": quote, "provenance": "sourced", "source": _source_text(source),
                      "citation": _source_cite(source), "title": _clean(source.get("title"), 200),
                      "database": source.get("database")})
    return {"block": block, "items": items, "found": found}


def _sites(profile):
    if profile.get("sites") == "industry":
        from . import sources as source_finder
        return source_finder.INDUSTRY_SITES
    return None


def complete(template, instruction, region=None, student_items=None, industry=None, country=None,
             unit_value=None, rubric=None, byline=None):
    """Fill a framework from the instruction.  Returns blocks with provenance.

    Each part is completed the way its profile says: researched where external
    evidence can exist, quoted from the student's own words where the fact is
    theirs, and returned as a named gap where only the owner of the process can
    state it.  The pipeline never observes the case, times a step or reads a
    machine, so nothing here is measured.

    ``rubric`` is the marking guide the student attached, as the text of the file
    or already parsed by ``bp.product.rubric.parse``.  It is read once, here, and a
    rubric that cannot be read is **refused**: a run that silently ignored it would
    tell the student their rubric was followed when it was not.  The rubric changes
    no block and invents no evidence; it is measured against the finished paper by
    ``draft`` (coverage) and enforced by ``paper.check`` (the export gate).
    """
    if not framework_profiles.has(template):
        raise ValueError("Framework completion is not enabled for this worksheet. It runs for "
                         + " and ".join(sorted(p["label"] for p in framework_profiles.PROFILES.values()))
                         + ".")
    profile = framework_profiles.profile_for(template)
    instruction = _clean(instruction, 2000)
    if len(instruction) < 15:
        raise ValueError("Describe the case in at least one sentence.")
    ok, message = guard.computation_boundary(instruction, profile.get("subject") or "management")
    if not ok:
        raise ValueError(message)
    # The rubric is read before anything is researched: a marking guide that cannot
    # be read must cost a sentence, not a full run whose paper silently ignores it.
    attached = _read_rubric(rubric) if rubric is not None else None
    unit_field = (profile["unit"] or {}).get("field") or "industry"
    declared = unit_value if unit_value not in (None, "") else (
        industry if unit_field == "industry" else country)
    unit = _unit(profile, instruction, declared)
    region = region or unit.get("region") or _region(_country(instruction))
    context = unit.get("context") or ""
    if not context:
        context = " ".join(retrieval.topic_words(instruction)[:4])
    supplied = {}
    for item in student_items or []:
        if not isinstance(item, dict):
            continue
        key = item.get("block") or item.get("force") or item.get("dimension")
        text = _clean(item.get("text"), 500)
        if key in {block["key"] for block in profile["blocks"]} and text:
            provenance = "student" if str(item.get("provenance") or "user").lower() in (
                "student", "user", "own") else str(item.get("provenance"))
            supplied.setdefault(key, []).append({"text": text, "provenance": provenance,
                                                 "source": _clean(item.get("source"), 300)})
    year_from = datetime.datetime.now(datetime.timezone.utc).year - 10
    jobs, notes = {}, []
    started = datetime.datetime.now(datetime.timezone.utc)
    country = _country(instruction)
    # Only a `research` block is sent to the databases.  A `quote` block takes
    # the student's own words and a `gap` block is stated only by the student:
    # searching outside evidence for either would dress a process the pipeline
    # cannot observe in findings it cannot support.
    researched = [block for block in profile["blocks"]
                  if framework_profiles.fill_of(block) in ("research", "auto")]
    # Q-16: one corpus document may not supply every dimension of a paper.
    # corpus_doc_counts is shared across dimensions so the cap holds per-paper.
    corpus_doc_counts = {}
    with ThreadPoolExecutor(max_workers=max(1, len(researched))) as pool:
        for block in researched:
            jobs[block["key"]] = pool.submit(_one_block, profile, block, context, region,
                                             year_from, country, corpus_doc_counts)
        done, pending = wait(jobs.values(), timeout=RESEARCH_DEADLINE) if jobs else (set(), set())
        results, timed_out = [], set()
        for block in profile["blocks"]:
            if block["key"] not in jobs:
                results.append({"block": block, "items": [], "found": {
                    "queries": [], "notices": [], "errors": [], "skipped": [], "dropped": 0}})
                continue
            future = jobs[block["key"]]
            if future in pending:
                timed_out.add(block["key"])
                results.append({"block": block, "items": [], "found": {
                    "queries": _queries(block, context, region, country), "notices": [], "errors": [],
                    "skipped": [], "dropped": 0}})
                continue
            try:
                results.append(future.result())
            except Exception as error:
                results.append({"block": block, "items": [], "found": {
                    "queries": _queries(block, context, region, country), "notices": [str(error)[:160]],
                    "errors": [], "skipped": [], "dropped": 0}})
    blocks, seen = [], set()
    for result in results:
        block, found = result["block"], result["found"]
        items = list(supplied.get(block["key"], []))
        # A source is deduplicated across the whole framework: one paper must
        # not cite the same study twice.  A quoted sentence is deduplicated
        # inside its own block only, because the same sentence of the brief can
        # honestly describe two parts of a process map, and dropping it from
        # the second would leave that part a gap the student had already
        # filled in words.
        block_seen = set()
        for item in result["items"]:
            key = retrieval.key_of({"doi": None, "title": item.get("title")}) or item.get("text", "")[:80]
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
        if not items and framework_profiles.fill_of(block) in ("quote", "auto"):
            quoted = _quote_block(profile, block, instruction)
            for item in quoted:
                key = item["text"][:80]
                if key in block_seen:
                    continue
                block_seen.add(key)
                items.append(item)
            if quoted:
                notes.append(block["label"] + ": " + str(len(quoted)) + " item(s) taken from your own words.")
        if not items:
            background = (framework_profiles.fill_of(block) == "research"
                          and profile.get("assumption") == "probe"
                          and all(framework_profiles.fill_of(item) == "research"
                                  for item in profile["blocks"]))
            notes_for_block = (profile.get("notes") or {}).get(block["key"]) or {}
            filler = _clean(notes_for_block.get("analysis"), 700) if background else ""
            if filler:
                # A part with no source is filled with the framework's own general
                # background (uncited), never left as a notice (owner instruction).
                items = [{"text": filler, "provenance": "background", "source": ""}]
        if not items:
            gap = ("No evidence was found for this part before the research deadline."
                   if block["key"] in timed_out else _gap_note(profile, block))
        else:
            gap = None
        background = (profile.get("assumption") == "probe"
                      and all(framework_profiles.fill_of(item) == "research" for item in profile["blocks"]))
        if (not background and framework_profiles.fill_of(block) in ("research", "auto")
                and profile.get("assumption") == "probe" and gap):
            gap = gap + " " + _probe(profile, block)
        blocks.append({"key": block["key"], "label": block["label"], "items": items, "gap": gap,
                       "fill": framework_profiles.fill_of(block),
                       "query": (found.get("queries") or [""])[0],
                       "dropped": found.get("dropped") or 0})
        if result["items"]:
            notes.append(block["label"] + ": " + str(len(result["items"])) + " sourced item(s).")
        if block["key"] in timed_out:
            notes.append(block["label"] + ": research timed out; returned as a gap.")
    gaps = [block["key"] for block in blocks if block["gap"] and not block["items"]]
    if gaps and profile.get("assumption") in ("case", "probe"):
        question = profile.get("assumption") != "case"
        suggestions = _suggest(profile, gaps, instruction, unit, blocks,
                               mode="question" if question else "assumption")
        for block in blocks:
            proposal = suggestions.get(block["key"])
            if not proposal:
                continue
            if question:
                # A question is not evidence.  It is recorded as a proposal on
                # the block and folded into the named gap, so the cell reads as
                # a gap with a way forward rather than as a finding, and the
                # paper never presents it as a case assumption.
                block["proposal"] = {"text": proposal, "provenance": "question"}
                block["gap"] = block["gap"] + " A line of enquiry is proposed: " + proposal
                notes.append(block["label"] + ": suggested line of enquiry.")
            else:
                block["items"] = block["items"] + [{"text": proposal,
                                                    "provenance": "suggested", "source": ""}]
                block["gap"] = "No source was found; a case assumption is proposed for your review."
                notes.append(block["label"] + ": suggested case assumption.")
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()
    # Authoring help rides WITH the block, never inside it.  `contains` and `ask` are
    # the framework's own teaching text; `tailored` is that same question rewritten in
    # the student's words by the model lane, validated or dropped.  None of it can
    # become an item, so an empty cell still reads as a gap and a suggestion can never
    # be presented as evidence (V-01, V-03, V-08).
    advice = {block["key"]: framework_profiles.advice_for(template, block["key"])
              for block in blocks}
    tailored = {}
    # "Unanswered" means no sourced and no student item: a block holding only the
    # framework's own background is exactly the cell the student is stuck on, so that
    # is where the model lane is asked to reword the question.
    unanswered = [block["key"] for block in blocks
                  if not any(item.get("provenance") in ("sourced", "student")
                             for item in block.get("items") or [])]
    asked = {key: advice[key]["ask"][0] for key in unanswered
             if (advice.get(key) or {}).get("ask")}
    if asked and os.environ.get("BP_FRAMEWORK_SUGGEST", "1") != "0":
        try:
            tailored = prose.suggest_questions(
                profile.get("label") or template,
                (profile.get("unit") or {}).get("label") or "unit",
                (unit or {}).get("value") or "", instruction, asked)
        except Exception:                                            # noqa: BLE001
            tailored = {}
    for block in blocks:
        row = advice.get(block["key"]) or {"contains": [], "ask": []}
        row["tailored"] = tailored.get(block["key"]) or ""
        row["model_used"] = bool(row["tailored"])
        block["advice"] = row
    if tailored:
        notes.append("Authoring questions were reworded for your case by the model lane; "
                     "they are prompts, not evidence.")

    # The counts the page shows are computed here, on the server: the client
    # never counts, sums or works out a progress figure of its own.
    filled = [block for block in blocks if block["items"]]
    completed = {"format": "bp-framework-completion/1", "template": template,
                 "framework": profile["label"], "unit": {k: v for k, v in unit.items() if k != "context"},
                 "instruction": instruction, "country": _country(instruction), "region": region,
                 "blocks": blocks, "notes": notes, "elapsed_s": round(elapsed, 2),
                 "summary": {"parts": len(blocks), "filled": len(filled),
                             "gaps": len(blocks) - len(filled)},
                 "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    # V-20: the title page carries the student's OWN lines, or nothing at all.  A
    # name is never invented and never defaulted: an empty byline is a paper with
    # no byline block, which is honest, and the student can add one and re-draft.
    lines = [str(line).strip() for line in (byline or []) if str(line or "").strip()]
    if lines:
        completed["byline"] = lines[:6]
    if attached is not None:
        completed["rubric"] = attached
    return completed


def _read_rubric(value):
    """The attached rubric, read once; a rubric that cannot be read is refused.

    A run that accepted an unreadable rubric and wrote the paper anyway would tell
    the student their marking guide had been followed when nothing had been read
    from it.  So the reader's own reason is raised, and the caller shows it.
    """
    parsed = value if isinstance(value, dict) else rubric_reader.parse(value)
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        problems = (parsed or {}).get("problems") if isinstance(parsed, dict) else None
        raise ValueError(problems[0] if problems else
                         "The rubric could not be read. Attach it as a table or a numbered list.")
    return parsed


def _probe(profile, block):
    notes = (profile.get("notes") or {}).get(block["key"]) or {}
    probe = notes.get("probe") or block.get("probe") or "search for country-specific evidence on this dimension"
    return "What to look for: " + probe + "."


def _suggest(profile, gaps, instruction, unit, blocks, mode="assumption"):
    """One proposal per gap, drawn only from the instruction and the unit.

    Two modes, two different promises:

    - ``assumption`` writes one CASE ASSUMPTION for the gap.  Only frameworks
      whose gaps can be answered analytically use this: an assumption about
      competitive dynamics is a reading of the case, while an assumption about
      a country would be an invented fact.
    - ``question`` writes a LINE OF ENQUIRY: a sharp, case-specific question
      the student can answer from their own position.  This is what a probe
      profile gets, so a student who is unsure is asked rather than left with
      an empty cell and no way forward.

    A reply that carries a number, a link, a DOI or a parenthesis is refused:
    a proposal may not introduce a fact of any kind.  In ``question`` mode a
    reply must also end in a question mark, and in ``assumption`` mode it must
    not be a question - each mode keeps its own promise.
    """
    if not gaps or os.environ.get("BP_FRAMEWORK_SUGGEST", "1") == "0":
        return {}
    try:
        from . import prose as editor
        if not editor.available():
            return {}
        plural = (profile.get("voice") or {}).get("block_plural") or "dimensions"
        system = _suggest_prompt(mode, plural)
        user = json.dumps({"instruction": instruction, "unit": unit.get("value"),
                           "blocks": gaps,
                           "sourced": {block["key"]: [item["text"] for item in block["items"]]
                                       for block in blocks}}, ensure_ascii=False)
        raw = editor._call([{"role": "system", "content": system}, {"role": "user", "content": user}])
        data = editor._parse(raw)
        out = {}
        for key in gaps:
            text = _clean(data.get(key), 700)
            if not text or re.search(r"\d|https?://|doi:|\(", text, re.I):
                continue
            question = text.endswith("?")
            if question != (mode == "question"):
                continue
            out[key] = text
        return out
    except Exception:
        return {}


def _suggest_prompt(mode, plural):
    """The system prompt for one proposal mode."""
    noun = _singular(plural)
    if mode == "question":
        return ("You are a business case tutor. For each " + noun + ", write ONE "
                "specific question that the student can answer from their own position, using only the "
                "instruction and the named unit of analysis. The question must be about THIS case and "
                "must be answerable with a fact the student already has; it must not be a statement, a "
                "conclusion, a recommendation or a fact about the firm. Do not add a source, citation, "
                "number, percentage, link or named fact not in the instruction. Return ONLY a JSON "
                "object mapping the key to the question. No markdown.")
    return ("You are a business case analyst. For each " + noun + ", write one specific CASE "
            "ASSUMPTION, in one or two sentences, that answers the question for this case, not a statement "
            "that the " + noun + " is relevant. Use only the instruction and the named unit of "
            "analysis. Do not add a source, citation, number, percentage, link or named fact not in the "
            "instruction. Return ONLY a JSON object mapping the key to the sentence. No markdown.")


def missing(completion, profile=None):
    """The dimensions that still block a paper.

    Owner instruction (2026-10-29): not every field has to be cited.  On a probe
    profile (PESTEL, Value Chain) a field with no accepted evidence is written by
    the Full paper as general background, with no citation, and by the Draft with
    its named-gap wording, so nothing blocks.  A student-supplied profile keeps the
    acknowledgement gate: those fields are the student's own words, not background.
    """
    profile = profile or _profile((completion or {}).get("template"))
    if (profile.get("assumption") == "probe"
            and all(framework_profiles.fill_of(block) == "research" for block in profile["blocks"])):
        return []
    acknowledged = set((completion or {}).get("acknowledged_gaps") or [])
    labels = []
    for block in (completion or {}).get("blocks") or []:
        if block.get("items"):
            continue
        if block.get("key") in acknowledged:
            continue
        labels.append(block.get("label") or block.get("key"))
    declared = {block["key"]: block["label"] for block in profile["blocks"]}
    for key, label in declared.items():
        if not any(block.get("key") == key for block in (completion or {}).get("blocks") or []):
            if key not in acknowledged:
                labels.append(label)
    return labels


class Incomplete(ValueError):
    """The worksheet cannot become a paper yet, and names what is missing."""

    def __init__(self, missing_labels):
        self.missing = list(missing_labels)
        super().__init__("The paper needs every dimension: " + ", ".join(self.missing))


# -- paper ---------------------------------------------------------------------

LENGTHS = {
    "short": {"label": "Short", "range": "600-1,200", "total": 800, "cap": 1300, "paras": 1,
              "head_paras": 1, "section_paras": 1,
              "intro": (110, 140), "context": (70, 100), "section": (85, 115),
              "discussion": (95, 125), "implications": (95, 125),
              "limitations": (55, 75), "conclusion": (80, 105)},
    "mid": {"label": "Mid", "range": "1,200-2,500", "total": 1300, "cap": 2600, "paras": 2,
            "head_paras": 2, "section_paras": 2,
            "intro": (160, 190), "context": (110, 140), "section": (150, 180),
            "discussion": (150, 180), "implications": (150, 180),
            "limitations": (80, 100), "conclusion": (110, 140)},
    "long": {"label": "Long", "range": "2,500-5,000", "total": 2500, "cap": 5200, "paras": 2,
             "head_paras": 2, "section_paras": 3,
             "intro": (240, 280), "context": (180, 220), "section": (260, 320),
             "discussion": (220, 260), "implications": (260, 320),
             "limitations": (120, 160), "conclusion": (180, 220)},
}


def _length_name(value):
    key = str(value or "").lower()
    return key if key in LENGTHS else "mid"


def _length(value):
    return LENGTHS[_length_name(value)]


def _range(profile, key):
    low, high = profile[key]
    return "%d to %d" % (low, high)


def _reject(reason):
    global LAST_REJECT
    LAST_REJECT = reason
    try:
        import tempfile, time
        path = os.path.join(tempfile.gettempdir(), "bp_model_reject.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + str(reason) + "\n")
    except Exception:
        pass
    return None


LAST_REJECT = None

#: The prompt templates, once for every framework.  The framework's own words
#: arrive as slots; the rules a model may not break are written here, once, so a
#: new profile cannot drop them.
HEAD_SYSTEM = (
    "You are an academic analyst writing the opening of a {name} paper. Use only the case instruction and the "
    "{block_plural} items. Write in formal academic English, third person, with no contractions, no rhetorical "
    "questions, no first or second person, and no reference to this paper, the analysis, the model, the reader or "
    "the drafting process. Do not open with 'This paper' or 'The case concerns'; begin with the {unit_noun} and the "
    "decision it frames. Keep the unit of analysis in view: {unit_rule}. Write an introduction of {intro} words in "
    "{head_phrase} that closes with one sentence "
    "stating {thesis_question}. Write a case context of {context} words in one paragraph that defines the decision, "
    "the {unit_noun} and the evidence base in academic terms. Do not restate every item. Do not add facts, numbers, "
    "names, sources or citations beyond the items. Do not recommend a decision. Return only JSON: "
    "{\"introduction\":[\"...\"], \"thesis\":\"...\", \"context\":[\"...\"]}.")

SECTION_SYSTEM = (
    "You are writing one {block_singular} of a {name} analysis. The {block_singular} is {label}. Use only the case "
    "instruction, the thesis and the {block_plural} items. If no items are supplied for this {block_singular}, write "
    "a general academic paragraph about it from background knowledge: cite nothing, name no source and add no "
    "figures. Write in formal academic English, third person, with no "
    "contractions, no first or second person, and no reference to this paper or the analysis. Write {section} "
    "words. {layout} Do not add facts, numbers, names, sources or citations beyond the items. Do not recommend a "
    "decision. Return only JSON: {\"paragraphs\":[\"...\"]}.")

LAYOUT = {
    1: ("Write exactly one paragraph that states what the evidence shows about this {block_singular} and "
        "interprets its {lens} for the decision."),
    2: ("Write exactly two paragraphs: the first establishes what the evidence shows about this "
        "{block_singular}; the second interprets it in {lens} and its effect on the decision."),
    3: ("Write exactly three paragraphs: the first establishes what the evidence shows; the second interprets "
        "it in {lens}; the third qualifies the reading by what the evidence does not establish."),
}

MID_SYSTEM = (
    "You are writing the discussion of a {name} analysis. Use only the case instruction, the thesis and the "
    "{block_plural} items. Formal academic English, third person, no contractions, no first or second person, no "
    "reference to this paper or the analysis. Write the discussion in {discussion} words over {paras_phrase}, "
    "reading the {block_plural} together and explaining how they interact to shape the decision, rather than "
    "repeating each in turn. Then write the implications in {implications} words over {paras_phrase}, stating the "
    "conditions a viable position must satisfy; do not make the decision. Do not add facts, numbers, names, "
    "sources or citations beyond the items. Return only JSON: {\"discussion\":[\"...\"], \"implications\":[\"...\"]}.")

TAIL_SYSTEM = (
    "You are closing a {name} analysis. Use only the case instruction, the thesis and the {block_plural} items. "
    "Formal academic English, third person, no contractions, no first or second person, no reference to this paper "
    "or the analysis. Write the limitations in {limitations} words in one paragraph, naming what the evidence "
    "cannot support. Write the conclusion in {conclusion} words over {paras_phrase} that answers the stated thesis "
    "and {closing}. Do not recommend a decision. Do not add facts, numbers, names, sources or citations beyond the "
    "items. Return only JSON: {\"limitations\":[\"...\"], \"conclusion\":[\"...\"]}.")


#: One rule, in every prompt.  The proper-noun guard refuses a capitalised word
#: that is not in the items, and a model that writes "Big Data" or "Net Zero" for
#: a generic term is refused on both attempts (2026-10-29: "name Big; name Net").
#: Lower-case generic terms fix that at the source; the guard itself stays as
#: strict as it was.
CASE_RULE = (" Write generic terms in lower case (for example big data, net zero, supply chain) and capitalise "
             "only a name that appears in the items.")


#: A framework-overview lead that is nothing but its own key is a placeholder,
#: not a paragraph: eight profiles ship ``'lead': 'lead'``.
_PLACEHOLDER_LEAD = re.compile(r"^[a-z][a-z_]{0,19}$")


def _lead_of(outline):
    """The framework-overview paragraph, or '' when the profile declares a placeholder.

    The five project-management worksheets and three canvases ship
    ``'lead': 'lead'`` - the key repeated as its own value - so the paper printed
    the literal token ``lead`` under the framework heading while the pipeline's
    own check reported "lead short".  A placeholder is a declared absence: the
    paragraph is omitted, never filled with invented prose, and the profile's
    author owns the wording (a presentation decision, not the code's).
    """
    lead = _clean((outline or {}).get("lead") or "", 1200)
    return "" if _PLACEHOLDER_LEAD.match(lead) else lead


def _unit_noun(framework):
    """The unit of analysis in the profile's own words, as a noun phrase.

    The prompt must name what the paper analyses: a profile that declares an
    industry writes an industry paper, and a model asked to "begin with the
    portfolio" while the unit is an industry drifts into another framework's
    vocabulary.  The profile's own label is used verbatim, lower-cased at the
    first letter only, so nothing is invented here.
    """
    unit = framework.get("unit") or {}
    noun = _clean(unit.get("label") or unit.get("field") or "market", 60)
    return (noun[:1].lower() + noun[1:]) if noun else "market"


def _system(template, length_profile, framework):
    """Fill the shared prompt with the framework's words and the length band."""
    voice = framework.get("voice") or {}
    out = template
    for key in ("intro", "context", "section", "discussion", "implications", "limitations", "conclusion"):
        out = out.replace("{" + key + "}", _range(length_profile, key))
    words = {1: "one paragraph", 2: "two paragraphs", 3: "three paragraphs"}
    out = out.replace("{head_phrase}", words.get(int(length_profile.get("head_paras", 2)), "two paragraphs"))
    out = out.replace("{paras_phrase}", words.get(int(length_profile.get("section_paras", 2)), "two paragraphs"))
    out = out.replace("{layout}", LAYOUT.get(int(length_profile.get("section_paras", 2)), LAYOUT[2]))
    slots = {
        "name": framework["label"],
        "block_plural": voice.get("block_plural") or "dimensions",
        "block_singular": _singular(voice.get("block_plural") or "dimensions"),
        "unit_noun": voice.get("unit_noun") or "market",
        "unit_rule": _unit_noun(framework),
        "thesis_question": voice.get("thesis_question") or "whether the evidence supports the decision",
        "lens": voice.get("lens") or "the terms the framework supplies",
        "closing": voice.get("closing") or "identifies the strongest and the weakest evidenced dimension",
    }
    for key, value in slots.items():
        out = out.replace("{" + key + "}", value)
    # The JSON contract stays the last instruction the model reads.
    marker = " Return only JSON:"
    if marker in out:
        head, tail = out.split(marker, 1)
        return head + CASE_RULE + marker + tail
    return out + CASE_RULE


def _ask(system, payload, timeout=180, attempts=2):
    """One model call, retried once when the reply is not the JSON we asked for.

    A provider sometimes answers with prose or a truncated thought instead of the
    JSON object; that is a transport failure, not a reason to refuse the paper, so
    the call is repeated before the dimension is given up.
    """
    last = None
    for attempt in range(max(1, int(attempts))):
        instruction = system if not attempt else (
            system + " Your previous reply was not the JSON object. Reply with the JSON object only, "
                     "no other text before or after it.")
        raw = None
        try:
            raw = prose._call([{"role": "system", "content": instruction},
                               {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                              timeout=timeout)
            return prose._parse(raw)
        except Exception as error:
            last = error
            if os.environ.get("BP_PROSE_DUMP") == "1":
                try:
                    import tempfile
                    path = os.path.join(tempfile.gettempdir(), "bp_prose_dump.txt")
                    with open(path, "a", encoding="utf-8") as handle:
                        handle.write("--- attempt %d: %s\n%r\n" % (attempt, error, (raw or "")[:2000]))
                except Exception:
                    pass
    raise last


def _ask_section(label, payload, system, attempt=0, timeout=180):
    if attempt:
        payload = dict(payload, note=("Stay strictly within the word count and keep the academic register; the "
                                      "previous attempt broke a limit."))
    raw = _ask(system, payload, timeout)
    return raw if isinstance(raw, dict) else {}


def _shape(raw, keys):
    raw = raw if isinstance(raw, dict) else {}
    groups = raw.get("groups") if isinstance(raw.get("groups"), dict) else {}
    forces = raw.get("forces") if isinstance(raw.get("forces"), dict) else {}
    merged = dict(groups)
    merged.update(forces)
    return {"introduction": _as_list(raw.get("introduction")),
            "context": _as_list(raw.get("context")),
            "lead": str(raw.get("lead") or "").strip(),
            "groups": {key: _as_list(merged.get(key)) for key in keys},
            "discussion": _as_list(raw.get("discussion")),
            "implications": _as_list(raw.get("implications")),
            "limitations": _as_list(raw.get("limitations")),
            "conclusion": _as_list(raw.get("conclusion"))}


def _has_name(text, names):
    return any(re.search(r"\b" + re.escape(name) + r"\b", str(text or "")) for name in names)


def _without_names(data, result, length, problems):
    """Replace the sections that carry an unlisted name with the deterministic reading.

    A student will legitimately write "net zero" and a model will sometimes
    capitalise it; refusing the whole paper for that frustrates the student and
    banning the word corrupts a valid sentence.  The paper is kept: only the
    paragraphs that carry a name the items do not have are replaced with the
    profile's own evidence-led prose, which cannot invent an entity.
    """
    names = [problem.split(" ", 1)[1] for problem in problems if problem.startswith("name ")]
    fallback = _draft_data(result, length)
    out = dict(data)
    for field in ("introduction", "context", "discussion", "implications", "limitations", "conclusion"):
        if any(_has_name(part, names) for part in data.get(field) or []):
            out[field] = list(fallback.get(field) or [])
    out["groups"] = {}
    for key, parts in (data.get("groups") or {}).items():
        if any(_has_name(part, names) for part in parts):
            out["groups"][key] = list((fallback.get("groups") or {}).get(key) or [])
        else:
            out["groups"][key] = list(parts)
    return out


def _model_sections(result, style="apa", attempt=0, length="mid", note=""):
    """A thesis call, then one call per dimension and two more, in parallel."""
    global LAST_REJECT
    if not attempt:
        LAST_REJECT = None
    profile = dict(_length(length))
    framework = _profile(result.get("template"))
    keys = [block["key"] for block in framework["blocks"]]
    voice = framework.get("voice") or {}
    try:
        if not prose.available():
            return _reject("model unavailable")
    except Exception:
        return _reject("model import")
    blocks = result.get("blocks") or []
    facts = _facts(blocks)
    if not facts:
        return _reject("no items")
    instruction = _clean(result.get("instruction"), 500)
    base = {"instruction": instruction, "blocks": facts}
    hint = ""
    if note:
        hint = (" The previous attempt was rejected for this reason: " + note[:300] +
                " Any word named there is not in the accepted items: do not introduce a policy instrument, "
                "technology, organisation or place that the items do not name; rewrite that sentence without the "
                "unsupported reference. Keep the same evidence and add no facts, numbers, sources or citations.")
    elif attempt:
        hint = (" The previous attempt exceeded the length or register limits; stay strictly within the word "
                "counts given and keep the academic register.")
    # The opening runs in parallel with the sections.  The thesis the sections
    # use comes from the profile, so no call has to finish before another starts:
    # that serial round was the 60-120 s wait.
    thesis = ("The analysis examines " +
              (voice.get("thesis_question") or "whether the evidence supports the decision") + ".")
    payload = dict(base, thesis=thesis)
    jobs = {"head": lambda: _ask(_system(HEAD_SYSTEM, profile, framework) + hint, base),
            "mid": lambda: _ask(_system(MID_SYSTEM, profile, framework) + hint, payload),
            "tail": lambda: _ask(_system(TAIL_SYSTEM, profile, framework) + hint, payload)}
    for block in blocks:
        label = block.get("label") or block.get("key")
        items = [{"text": _clean(item.get("text"), 600), "kind": _kind(item)}
                 for item in block.get("items") or []]
        section_payload = {"instruction": instruction, "thesis": thesis, "label": label, "items": items}
        jobs[block.get("key")] = (
            lambda label=label, sp=section_payload:
            _ask_section(label, sp, _system(SECTION_SYSTEM, profile, framework).replace("{label}", label), attempt))
    answers = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        running = {pool.submit(job): name for name, job in jobs.items()}
        for future in wait(running).done:
            name = running[future]
            try:
                answers[name] = future.result()
            except Exception:
                # One failed part must not cancel the others; the validator
                # decides whether the paper is complete.
                answers[name] = {}
    head = answers.get("head") or {}
    merged = {"introduction": (head or {}).get("introduction") or [],
              "thesis": thesis,
              "context": (head or {}).get("context") or [],
              "lead": _lead_of(framework.get("outline") or {}),

              "groups": {block.get("key"): (answers.get(block.get("key")) or {}).get("paragraphs") or []
                         for block in blocks},
              "discussion": (answers.get("mid") or {}).get("discussion") or [],
              "implications": (answers.get("mid") or {}).get("implications") or [],
              "limitations": (answers.get("tail") or {}).get("limitations") or [],
              "conclusion": (answers.get("tail") or {}).get("conclusion") or []}
    data = _shape(merged, keys)
    for name in ("introduction", "context", "discussion", "implications", "limitations", "conclusion"):
        data[name] = [CITATION.sub("", part) for part in data[name]]
    data["lead"] = CITATION.sub("", data["lead"])
    data["groups"] = {key: [CITATION.sub("", part) for part in parts]
                      for key, parts in data["groups"].items()}
    citations_by_key = {}
    for block in blocks:
        cites = [item.get("citation") for item in block.get("items") or []
                 if item.get("provenance") == "sourced" and item.get("citation")]
        citations_by_key[block.get("key")] = list(dict.fromkeys(cite for cite in cites if cite))
    # A field with no accepted evidence is written from general background (owner
    # instruction): its names are not checked against items it does not have, but
    # numbers, links and citations still are.
    background = any(not (block.get("items") or []) for block in blocks)
    problems = _problems(data, facts, instruction, length, keys,
                         allow=_allowed_names(framework, result), skip_names=background)
    if problems:
        if attempt and all(problem.startswith("name ") for problem in problems):
            # The model keeps naming something the items do not carry.  Keep the
            # paper and replace those paragraphs with the deterministic reading;
            # never refuse the student over a word, and never ship the name.
            patched = _without_names(data, result, length, problems)
            problems = _problems(patched, facts, instruction, length, keys,
                                 allow=_allowed_names(framework, result), skip_names=background)
            if not problems:
                return (patched, citations_by_key)
        return _retry(result, style, attempt, "; ".join(problems[:3]))
    return (data, citations_by_key)


#: Region vocabulary a paper may use without it being an invented fact: it comes
#: from the region the retrieval actually used.
REGION_WORDS = {
    "Europe": ("europe", "european"),
    "US": ("united", "states", "america", "american", "us", "u.s."),
    "Middle East": ("middle", "east", "gulf", "gcc"),
    "China": ("china", "chinese"),
    "Global": (),
}


def _allowed_names(profile, result):
    """Words that are the framework's own or the declared unit's, not new facts.

    A PESTEL section is headed "Social" and its prose says "Social conditions";
    without this, the proper-noun guard read the dimension's own name as an
    invented name and refused the paper.  The same applies to the region the
    search used ("European" for a Europe brief).
    """
    words = set()
    # The framework's own name is not an invented fact: a paper that says
    # "Porter's Value Chain" is naming the method, not a new source.  The
    # profile carries the name, so every framework gets this without a branch.
    for field in ("label", "title_prefix"):
        words.update(re.findall(r"[a-z]{3,}", str(profile.get(field) or "").lower()))
    for block in profile.get("blocks") or []:
        words.update(re.findall(r"[a-z]{3,}", str(block.get("label") or "").lower()))
    unit = result.get("unit") or {}
    for token in re.findall(r"[a-z]{3,}", str(unit.get("value") or "").lower()):
        words.add(token)
    for value in (result.get("region"), result.get("country"), unit.get("region")):
        for token in REGION_WORDS.get(str(value or ""), ()):
            words.add(token)
    return words


def _problems(data, facts, instruction="", length="mid", keys=None, allow=None, skip_names=False):
    profile = _length(length)
    keys = list(keys or FORCE_KEYS)
    allowed = {str(word).lower() for word in (allow or set())}
    problems = []
    floors = [("introduction", profile["intro"][0] - 10), ("context", profile["context"][0] - 10),
              ("discussion", profile["discussion"][0] - 15),
              ("implications", profile["implications"][0] - 15),
              ("limitations", profile["limitations"][0] - 10),
              ("conclusion", profile["conclusion"][0] - 10)]
    for name, floor in floors:
        count = _words(" ".join(data[name]))
        if count < floor:
            problems.append("%s short (%d)" % (name, count))
        high = profile["intro" if name == "introduction" else name][1]
        if count > high * 1.5:
            problems.append("%s long (%d)" % (name, count))
    if len(data["introduction"]) != int(profile.get("head_paras", 2)):
        problems.append("introduction has %d paragraph(s)" % len(data["introduction"]))
    if data["lead"] and _words(data["lead"]) < 25:
        problems.append("lead short")

    for key in keys:
        parts = data["groups"].get(key) or []
        if len(parts) != int(profile.get("section_paras", 2)):
            problems.append("%s has %d paragraph(s)" % (key, len(parts)))
        count = _words(" ".join(parts))
        if count < profile["section"][0] - 15:
            problems.append("%s short (%d)" % (key, count))
        if count > profile["section"][1] * 1.5:
            problems.append("%s long (%d)" % (key, count))
    total = sum(_words(" ".join(data[name])) for name in
                ("introduction", "context", "discussion", "implications", "limitations", "conclusion"))
    total += _words(data["lead"]) + sum(_words(" ".join(parts)) for parts in data["groups"].values())
    if total < profile["total"]:
        problems.append("paper short (%d words)" % total)
    if total > profile["cap"]:
        problems.append("paper long (%d words, cap %d)" % (total, profile["cap"]))
    text = " ".join([data["lead"]] + [part for name in
                    ("introduction", "context", "discussion", "implications", "limitations", "conclusion")
                    for part in data[name]] +
                    [part for parts in data["groups"].values() for part in parts])
    if URL.search(text):
        problems.append("link")
    supplied_items = " ".join(item["text"] for group in facts for item in group["items"])
    extra = set(NUMBER.findall(text)) - set(NUMBER.findall(supplied_items))
    if extra:
        problems.append("number " + ",".join(sorted(extra)))
    supplied = (str(instruction or "") + " " + supplied_items).lower()
    supplied_words = set(re.findall(r"[a-z]{4,}", supplied))
    if skip_names:
        return problems
    for name in set(PROPER.findall(text)):
        low = name.lower()
        if low in supplied_words or low in FRAMEWORK_WORDS or low in allowed:
            continue
        if any(low.startswith(word) or word.startswith(low) for word in supplied_words):
            continue
        problems.append("name " + name)
    return problems


def _retry(result, style, attempt, reason, length="mid"):
    if not attempt:
        return _model_sections(result, style, 1, length, note=reason)
    return _reject(reason)


#: Where a case instruction stops being the case and starts being a wish list
#: ("... and needs the political, economic, social...").  Cutting mid-clause is
#: what produced "…and needs the political" as a paper title (2026-10-29).
TITLE_BREAKS = (" and needs", " and requires", " and wants", " and must", " and should",
                " and is", " and where", " and how", " and what", " before ", " because ",
                " so that ", " in order to ", " while ")


#: APA 7 title case: capitalise major words; keep articles, coordinating
#: conjunctions and prepositions of three letters or fewer lower case; always
#: capitalise the first word and the first word after a colon.
TITLE_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor",
               "of", "on", "or", "per", "so", "the", "to", "up", "via", "yet"}


def _title_word(word):
    """One word in title case, including hyphenated compounds (Solar-Panel)."""
    built = []
    for index, part in enumerate(str(word).split("-")):
        letters = part.strip("()[]{}.,;:!?\"'\u201c\u201d\u2019")
        if not letters:
            built.append(part)
            continue
        if index > 0 and letters.lower() in TITLE_SMALL:
            built.append(part)
        elif letters[:1].isupper():
            built.append(part)
        else:
            position = part.find(letters)
            built.append(part[:position] + letters[:1].upper() + letters[1:])
    return "-".join(built)


def _apa_title(text):
    words = str(text or "").split(" ")
    out = []
    for index, word in enumerate(words):
        first = index == 0
        after_colon = index > 0 and words[index - 1].endswith(":")
        last = index == len(words) - 1
        core = word.strip("()[]{}.,;:!?\"'\u201c\u201d\u2019").lower()
        if not first and not after_colon and not last and core in TITLE_SMALL:
            out.append(word[:1].lower() + word[1:] if word[:1].isupper() else word)
        else:
            out.append(_title_word(word))
    return " ".join(out)


def _title(instruction, profile=None, unit=""):
    profile = profile or DEFAULT_PROFILE
    text = _clean(instruction, 300).strip()
    if ". " in text:
        text = text.split(". ", 1)[0]
    text = text.strip().rstrip(" .,;:!?")
    lower = text.lower()
    cuts = [lower.find(marker) for marker in TITLE_BREAKS] + [lower.find(", ")]
    cuts = [index for index in cuts if 30 <= index <= 110]
    if cuts:
        text = text[:min(cuts)].strip().rstrip(" .,;:!?")
        if len(text) < 20:
            # The cut left a stub; name the unit rather than a fragment.
            text = _clean(unit, 80).strip().rstrip(" .,;:!?") or text
    if len(text) > 110:
        # No clause ends inside the band: name the unit of analysis rather
        # than print a truncated sentence as a title.
        text = _clean(unit, 80).strip().rstrip(" .,;:!?") or text
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return _apa_title(profile["title_prefix"] + ": " + text)


def _background_note(profile, block):
    """What a cell filled from general background must say about itself.

    A paragraph that no source supports is not evidence.  The cell states that
    before it states the paragraph, so a reader cannot take the framework's own
    general knowledge for a finding (V-12).
    """
    note = _gap_note(profile, block)
    if "general background" in note:
        return note
    return ("No source was found for this part; it is written from general background "
            "and is not cited.")


def _draft_data(result, length="mid"):
    """Deterministic prose from the accepted items and the profile's own notes.

    The framework supplies what each dimension means and what it does not
    establish; this function only arranges it around the counts and the items.
    """
    name = _length_name(length)
    profile = _length(name)
    framework = _profile(result.get("template"))
    voice = framework.get("voice") or {}
    outline = framework.get("outline") or {}
    notes = framework.get("notes") or {}
    instruction = _clean(result.get("instruction"), 500).strip().rstrip(" .,;:")
    blocks = result.get("blocks") or []
    labels, counts = [], []
    sourced = student = assumptions = gaps = 0
    for block in blocks:
        items = block.get("items") or []
        if not items:
            gaps += 1
            continue
        labels.append(block.get("label") or block.get("key"))
        counts.append(len(items))
        for item in items:
            kind = _kind(item)
            if kind == "sourced":
                sourced += 1
            elif kind == "student":
                student += 1
            else:
                assumptions += 1
    listed = ", ".join("%s (%d)" % (label, count) for label, count in zip(labels, counts)) or "no dimension"
    #: How the accepted items are spread over the parts.  This line used to read
    #: "X carries the most weight ... while X carries the least": it ranked the
    #: parts, which the shelf declares it never does, and `index(max())` and
    #: `index(min())` name the *same* part whenever every count is equal — which is
    #: what an operations completion usually produces, one item per part.  A count
    #: of items is a fact; "weight" was a claim, so the fact is what is printed.
    if not counts:
        spread = ""
    elif max(counts) == min(counts):
        spread = ("Each of them carries the same number of accepted items, so on this "
                  "evidence none is better supported than another.")
    else:
        spread = ("%s carries the most accepted items (%d) and %s the fewest (%d); a count "
                  "of items is not a measure of how much each one settles."
                  % (labels[counts.index(max(counts))], max(counts),
                     labels[counts.index(min(counts))], min(counts)))
    plural = voice.get("block_plural") or "dimensions"
    singular = _singular(plural)
    interaction = (voice.get("interaction") or "").strip()
    if not interaction.lower().startswith("read together"):
        interaction = ("Read together, the documented " + plural + " " + interaction).strip()
    data = {
        "introduction": [
            ("The decision under examination is whether to proceed with the course of action set out in the "
             "brief. " + (voice.get("intro_frame") or "") + " The evidence base is confined to the items accepted "
             "for the case."),
            ("The analysis treats each of the " + str(len(blocks)) + " " + plural + " in turn: " + ", ".join(
                (block.get("label") or block.get("key") or "").lower() for block in blocks) + ". Each is "
                "established from the accepted evidence and then interpreted, with attention to its effect on "
                "the decision."),
            ("The argument advanced is that the " + plural + " supported by evidence constrain the decision, and "
             "that " + _article(singular) + " " + singular + " for which no evidence is recorded cannot be "
             "treated as favourable. The "
             "conclusion returns to this proposition."),
        ],
        "context": [
            "The case concerns the following decision: " + instruction + ". " + (voice.get("context_frame") or ""),
            ("Evidence is limited to the accepted items. " + _article(singular).capitalize() + " " + singular +
             " without an accepted item is recorded as "
             "a gap, and an assumption is identified as such and is not treated as evidence. No aggregate score or "
             "recommendation is produced."),
        ],
        "lead": _lead_of(outline),

        "groups": {},
        "discussion": [
            ("The case supplies " + str(sourced + student + assumptions) + " accepted items across the " + plural +
             ": " + str(sourced) + " sourced items, " + str(student) + " items of the student's own evidence and " +
             str(assumptions) + " case assumptions. The " + plural + " carrying evidence are " + listed + ", while " +
             str(gaps) + " " + singular + "(s) are recorded as gaps."),
            (interaction +
             " " + _article(singular).capitalize() + " " + singular +
             " without evidence carries no weight in the assessment, because a gap is not a "
             "finding and cannot be read as either a strength or a weakness."),
        ],
        "implications": [
            ("The combined reading bears on the decision: the documented conditions must be answered by the "
             "proposed position, and the plan must show how each would be met. " + _article(singular).capitalize() +
             " " + singular + " that appears "
             "weak in the evidence is not thereby one that can be disregarded; it is " + _article(singular) +
            " " + singular + " the case "
             "has not documented."),
            (voice.get("implication_frame") or "") + " The decision itself remains the student's.",
        ],
        "limitations": [
            ("The analysis does not rate the " + plural + ", compute an aggregate score or recommend a decision, "
             "because the accepted items do not support a quantitative comparison across them. Several " + plural +
             " may rest on a single item, which limits the weight they can bear; an assumption is not a source and "
             "a gap is not a finding. The student must verify every item before submission."),
        ],
        "conclusion": [
            ("The analysis set out to establish, " + singular + " by " + singular + ", what the accepted evidence "
             "implies for the decision. The " + plural + " with evidence are " + listed + "."
             + ((" " + spread) if spread else "")),
            ("The proposition advanced in the introduction is supported only to the extent that the items reach. "
             "The paper does not make the decision; it identifies the conditions that any justification must "
             "address."),
        ],
    }
    for block in blocks:
        key = block.get("key")
        lines = []
        for item in block.get("items") or []:
            text = _clean(item.get("text"), 600)
            kind = _kind(item)
            if kind == "sourced":
                cite = item.get("citation") or ""
                lines.append(text + (" " + cite if cite else ""))
            elif kind == "student":
                lines.append(text)
            elif kind == "background":
                lines.append(text)
            elif str(item.get("provenance") or "").lower() == "synthetic":
                lines.append("Illustrative: " + text)
            else:
                lines.append("Case assumption: " + text
                             if not text.lower().startswith("case assumption") else text)
        note = notes.get(key) or {}
        has_background = any(_kind(item) == "background" for item in block.get("items") or [])
        first = (" ".join(lines) if lines else
                 (block.get("gap") or "No evidence was found for this " + singular + ", so it is recorded as a gap."))
        if has_background:
            # V-12 at the paper: the paragraph below is the framework's own general
            # background, written from knowledge rather than from a retrieved source.
            # Printed bare it posed as a finding, so the cell says what it is first.
            # The completion payload keeps its item and its (absent) gap: the
            # worksheet shows the run, the paper says what the run cannot support.
            paragraphs = [_background_note(framework, block), first]
        elif name == "short":
            paragraphs = [first + " " + (note.get("short") or "")]
        elif name == "long":
            paragraphs = [first, note.get("analysis") or "", note.get("qualify") or ""]
        else:
            paragraphs = [first, note.get("analysis") or ""]
        data["groups"][key] = [part for part in paragraphs if part]
    if name == "short":
        data["introduction"] = data["introduction"][:2]
        data["context"] = data["context"][:1]
        data["discussion"] = data["discussion"][:1]
        data["implications"] = data["implications"][:1]
        data["conclusion"] = data["conclusion"][:1]
    return data


def _figure_cells(blocks):
    """One cell per block: the block's own items, never a blank.

    A cell carries the *identity* of each item - the source's title for a
    retrieved item, the student's own sentence for their own - so the grid
    reads as a summary and the prose below carries the full evidence.
    """
    cells = {}
    for block in blocks or []:
        bullets = []
        for item in block.get("items") or []:
            text = str(item.get("title") or item.get("text") or "").strip()
            if not text:
                continue
            citation = str(item.get("citation") or "").strip()
            if citation:
                text = text + " " + citation
            bullets.append(text)
        cells[block.get("key")] = {
            "label": block.get("label") or block.get("key"),
            "bullets": bullets,
            "gap": block.get("gap") or None,
        }
    return cells


def _sections(data, blocks, style, citations, result):
    profile = _profile(result.get("template"))
    outline = profile.get("outline") or {}
    references, seen = [], set()
    for block in blocks:
        for item in block.get("items") or []:
            if _kind(item) == "sourced" and item.get("source"):
                if item["source"] not in seen:
                    seen.add(item["source"])
                    references.append(item["source"])
    figure = matrix.build(result.get("template"), _figure_cells(blocks),
                          caption=profile.get("label"))
    headings = [paper.section("Introduction", 1, list(data["introduction"])),
                paper.section(outline.get("context") or "Case and context", 2,
                              list(data["context"]))]
    # A profile whose lead is a placeholder gets no framework-overview paragraph at
    # all - never the token - and keeps the section only when the framework has a
    # figure that lives there.
    if data["lead"] or figure:
        headings.append(paper.section(outline.get("framework") or profile["label"], 1,
                                      [data["lead"]] if data["lead"] else [],
                                      figure=figure))
    sections = headings

    singular = _singular((profile.get("voice") or {}).get("block_plural") or "dimensions")
    for block in blocks:
        key = block.get("key")
        paragraphs = list(data["groups"].get(key) or [])
        if not paragraphs:
            paragraphs = [block.get("gap") or "No evidence was found for this " + singular + "."]
        cites = citations.get(key) or []
        if not cites:
            cites = [item.get("citation") or _cite_from_source(item.get("source"))
                     for item in block.get("items") or []
                     if _kind(item) == "sourced" and item.get("source")]
        cites = list(dict.fromkeys(cite for cite in cites if cite))
        if cites and paragraphs:
            # The block's own item lines already carry their citation (a sourced
            # item is printed as text + citation above).  Appending the block's
            # citations again printed "(Lovelace, 2024) (Lovelace, 2024)" in every
            # evidenced cell of every framework paper: a reader sees a doubled
            # reference, and the second copy is the product talking, not the source.
            # A citation that is genuinely missing is still added, so the guarantee
            # that every reference reaches its own section has not moved.
            line = paragraphs[0].rstrip()
            missing = [cite for cite in cites if cite not in line]
            if missing:
                paragraphs[0] = line + " " + " ".join(missing)
        sections.append(paper.section(block.get("label") or key, 2, paragraphs))
    sections += [
        paper.section("Discussion", 1),
        paper.section(outline.get("discussion") or "What the evidence shows", 2, list(data["discussion"])),
        paper.section(outline.get("implications") or "Implications for the decision", 2,
                      list(data["implications"])),
        paper.section(outline.get("limitations") or "Limitations", 2, list(data["limitations"])),
        paper.section(outline.get("conclusion") or "Conclusion", 1, list(data["conclusion"])),
        paper.section(outline.get("reference_heading") or
                      ("References" if style == "apa" else "Bibliography"), 1,
                      references or ["No sources were used."]),
    ]
    return [dict(section, heading=_apa_title(section.get("heading"))) for section in sections]


def draft(result, style="apa", version="draft", length="mid"):
    """A full paper from a completion result; no new facts, ratings or citations."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    blocks = result.get("blocks") or []
    model_used = False
    fallback = ""
    citations = {}
    if version == "full":
        generated = _model_sections(result, style, length=length)
        if generated:
            data, citations = generated
            model_used = True
        else:
            # A model that cannot produce a valid paper must not cost the student
            # the work: the same evidence-led draft they could have chosen is
            # generated instead, and the report says so.  Nothing model-written is
            # shipped unvalidated.
            data = _draft_data(result, length)
            fallback = "draft"
    else:
        data = _draft_data(result, length)
    profile = _profile(result.get("template"))
    # One shape, whichever path produced the prose: a payload written before the
    # profile existed may still say "forces" where the profile says "groups".
    data = _shape(data, [block["key"] for block in profile["blocks"]])
    sections = _sections(data, blocks, style, citations, result)
    words = sum(_words(" ".join(section.get("lines") or [])) for section in sections
                if section.get("heading") not in ("References", "Bibliography"))
    attached = result.get("rubric") if isinstance(result.get("rubric"), dict) else None
    coverage = None
    if attached:
        # Measured against the paper that was actually written, **before** the
        # appendix that reports on it exists — otherwise the report could satisfy
        # the criterion it is reporting on.
        coverage = rubric_reader.coverage(attached, sections)
        sections = sections[:-1] + [_rubric_section(coverage)] + sections[-1:]
    report = {"title": _title(result.get("instruction"), profile,
                              (result.get("unit") or {}).get("value") or result.get("country") or ""),
              "sections": sections, "style": style,
              "version": version, "model_used": model_used, "fallback": fallback, "words": words,
              "framework": profile["label"], "template": profile["template"],
              "length": _length_name(length), "length_label": _length(length)["label"],
              "length_range": _length(length)["range"],
              # The band is the Full paper's target.  A deterministic Draft reports
              # its own word count instead of claiming a length it does not reach.
              "length_applies_to": "full",
              "byline": [str(line).strip() for line in (result.get("byline") or []) if str(line or "").strip()]}
    if coverage is not None:
        report["rubric"] = coverage
        # The gate is the student's switch: coverage saying "blocked" only stops a
        # paper when they have not turned the gate off for this run.
        report["rubric_gate"] = ("blocked" if coverage["gate"] == "blocked"
                                 and result.get("rubric_gate", True) is not False else "clear")
        report["word_target"] = _word_target(attached, words)
    return report


def rubric_blockers(report):
    """The criteria a finished paper does not address, as blocking sentences.

    Read from the report the paper itself produced, so what blocks the download names
    exactly the rows the appendix shows.  An empty list means nothing blocks.
    """
    if not isinstance(report, dict) or report.get("rubric_gate") != "blocked":
        return []
    names = ((report.get("rubric") or {}).get("blocking") or [])
    return ["the '" + str(name) + "' criterion your rubric states" for name in names]


def _word_target(parsed, words):
    """The rubric's stated length beside the paper's own count; never a verdict on quality.

    A tolerance the rubric states is applied as written.  When the rubric states a
    number of words with no tolerance, ``met`` is ``None``: a bare count does not
    say whether it is a floor or a ceiling, and guessing one would be inventing a
    requirement.
    """
    budget = (parsed or {}).get("word_budget") or {}
    target = budget.get("words")
    if not target:
        return None
    actual, tolerance = int(words), budget.get("tolerance")
    if tolerance:
        low = int(round(target * (1 - tolerance)))
        high = int(round(target * (1 + tolerance)))
        return {"words": target, "tolerance": tolerance, "actual": actual,
                "met": bool(low <= actual <= high), "range": [low, high],
                "note": "the rubric states %d words plus or minus %g%%"
                        % (target, tolerance * 100)}
    return {"words": target, "tolerance": None, "actual": actual, "met": None, "range": None,
            "note": "the rubric states %d words without a tolerance; the paper's length is "
                    "reported for you to judge" % target}


def _rubric_section(coverage):
    """The mechanical coverage table: what the rubric asked for, and what the paper does."""
    return paper.rubric_section(coverage)


def draft_bytes(result, style="apa", report=None, version="draft", length="mid"):
    report = report or draft(result, style, version, length)
    return docx.render_academic(report["title"], report["sections"], report["style"],
                                byline=report.get("byline") or ())
