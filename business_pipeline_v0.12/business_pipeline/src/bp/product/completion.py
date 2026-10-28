"""Complete a framework from an instruction and retrieved sources (product layer).

The first and only pilot is Porter's Five Forces.  The instruction supplies the
case; the source finder fills empty forces with real evidence.  A force with no
evidence is returned as a named gap.  No fact, rating or citation is invented.
"""

import datetime
import json
import os
import re

from . import docx, guard, paper, prose, sources as source_finder
from . import writing

TEMPLATE = "template_five_forces"

FORCES = [
    ("rivalry", "Industry rivalry", "competition rival market share price war"),
    ("entrants", "Threat of new entrants", "market entry barriers capital licence"),
    ("substitutes", "Threat of substitutes", "substitute alternative switching"),
    ("buyers", "Buyer power", "buyer customer bargaining concentration"),
    ("suppliers", "Supplier power", "supplier vendor procurement input"),
]

SHORT_QUERY = {"rivalry": "competition", "entrants": "entry barriers", "substitutes": "substitutes",
               "buyers": "consumer demand", "suppliers": "suppliers logistics"}
ALT_QUERY = {"rivalry": "retail rivalry", "entrants": "market entry", "substitutes": "alternative products",
             "buyers": "buyer power", "suppliers": "cold chain"}

COUNTRIES = [
    ("Iran", ("iran", "iranian")), ("Saudi Arabia", ("saudi arabia", "saudi")),
    ("United Arab Emirates", ("united arab emirates", "uae", "emirates", "dubai", "abu dhabi")),
    ("Qatar", ("qatar",)), ("China", ("china", "chinese")),
    ("United States", ("united states", "u.s.", "american")),
    ("United Kingdom", ("united kingdom", "uk", "britain")),
    ("Germany", ("germany",)), ("France", ("france",)), ("India", ("india", "indian")),
]


def _clean(value, limit=400):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _country(text):
    lower = (text or "").lower()
    for name, aliases in COUNTRIES:
        if any(re.search(r"\b" + re.escape(alias) + r"\b", lower) for alias in aliases):
            return name
    return ""


def _region(country):
    if country in ("Iran", "Saudi Arabia", "United Arab Emirates", "Qatar"):
        return "Middle East"
    if country == "China":
        return "China"
    if country in ("United States",):
        return "US"
    if country in ("United Kingdom", "Germany", "France"):
        return "Europe"
    return "Global"


STOP = set("a an the and or of to in on for with by at from as is are was were be been it its this that these those "
           "we our us you your i my me they their them not no do does did can could should would will may might have "
           "has had how what when where which who why if then than so such about into over under between among after "
           "before during each per via also more most much many some any other another own same very complete analysis "
           "five forces considering acquiring provider board case mid sized small large new local regional national "
           "international company companies firm firms business".split())


def _context_words(text):
    words = [word for word in re.findall(r"[a-z][a-z0-9']+", (text or "").lower())
             if len(word) >= 3 and word not in STOP]
    out = []
    for word in words:
        if word not in out:
            out.append(word)
    return out[:4]


def _first_sentence(source):
    text = _clean(source.get("abstract") or source.get("description"), 1200)
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:2])[:700]


def _rank(item, cues, country, context):
    text = (_clean(item.get("title"), 300) + " " + _clean(item.get("abstract") or item.get("description"), 900)).lower()
    words = set(re.findall(r"[a-z][a-z0-9'-]+", text))
    cue_hits = len(set(cues.split()) & words)
    context_hits = len(set(context) & words)
    if context and not context_hits:
        return -1
    if cue_hits == 0:
        return -1
    geo = 2 if country and country.lower() in text else 0
    tier = 2 if item.get("tier") in ("official", "data") else 1 if item.get("database") else 0
    return cue_hits * 2 + geo + tier + (item.get("credibility") or 0) / 100


def _source_text(item):
    try:
        return writing.reference(item, "apa")
    except Exception:
        return _clean(item.get("url") or item.get("doi") or item.get("title"), 300)


def _source_cite(item):
    try:
        return writing.in_text(item, "apa")
    except Exception:
        return ""


def _search(force_cues, country, region, year_from, industry, force_key):
    query = " ".join(part for part in (country, industry, SHORT_QUERY[force_key],
                                       "" if country or region == "Global" else region) if part)
    alt = " ".join(part for part in (country, industry, ALT_QUERY[force_key]) if part)
    academic = source_finder.search_academic(query, databases=["openalex", "semanticscholar", "doaj"],
                                             limit=4, year_from=year_from)
    if alt != query:
        academic2 = source_finder.search_academic(alt, databases=["openalex", "semanticscholar", "doaj"],
                                                  limit=3, year_from=year_from)
        academic["results"] = (academic.get("results") or []) + (academic2.get("results") or [])
    web = source_finder.search_web(query, region, 4, None, fast=True)
    found = list(academic.get("results") or [])
    for item in web.get("results") or []:
        found.append({"title": item.get("title"), "abstract": item.get("description"),
                      "authors": item.get("site"), "authors_list": [item.get("site")],
                      "year": item.get("year"), "venue": item.get("site"), "doi": None,
                      "url": item.get("url"), "database": "vetted web", "tier": item.get("tier"),
                      "credibility": 60, "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    seen, ranked = set(), []
    for item in found:
        key = item.get("doi") or _clean(item.get("title"), 120).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ranked.append((_rank(item, force_cues, country, industry.lower().split()), item))
    ranked.sort(key=lambda pair: -pair[0])
    return [item for score, item in ranked if score >= 2][:_MAX_ITEMS_PER_FORCE], query


_MAX_ITEMS_PER_FORCE = 5


def _suggest(gaps, instruction, sourced, industry):
    """One labelled case assumption per gap, only from the instruction."""
    if not gaps or os.environ.get("BP_FRAMEWORK_SUGGEST", "1") == "0":
        return {}
    try:
        from . import prose as editor
        if not editor.available():
            return {}
        system = ("You are a business case analyst. For each force, write one specific CASE ASSUMPTION, in one or two sentences, that answers "
                  "the force question for this industry and case, not a statement that the force is relevant. Bad: "
                  "'Rivalry is a relevant force.' Good: 'Existing grocery chains and cold-chain operators could "
                  "respond with price and service competition.' Use only the instruction and the named industry. Do "
                  "not add a source, citation, number, percentage, link or named fact not in the instruction. Return "
                  "ONLY a JSON object mapping force key to the sentence. No markdown.")
        user = json.dumps({"instruction": instruction, "industry": industry, "forces": gaps,
                           "sourced": sourced}, ensure_ascii=False)
        raw = editor._call([{"role": "system", "content": system}, {"role": "user", "content": user}])
        data = editor._parse(raw)
        out = {}
        for key in gaps:
            text = _clean(data.get(key), 700)
            if not text or re.search(r"\d|https?://|doi:|\(", text, re.I):
                continue
            out[key] = text
        return out
    except Exception:
        return {}


def complete(template, instruction, region=None, student_items=None, industry=None):
    """Fill Five Forces from the instruction.  Returns blocks with provenance."""
    if template != TEMPLATE:
        raise ValueError("Only Porter's Five Forces is enabled for completion.")
    instruction = _clean(instruction, 2000)
    if len(instruction) < 15:
        raise ValueError("Describe the case in at least one sentence.")
    country = _country(instruction)
    region = region or _region(country)
    industry_ok, industry = guard.five_forces_fit(instruction, industry)
    if not industry_ok:
        raise ValueError(industry)
    context = industry.lower().split()
    year_from = datetime.datetime.now(datetime.timezone.utc).year - 10
    supplied = {}
    for item in student_items or []:
        if not isinstance(item, dict):
            continue
        key = item.get("force")
        text = _clean(item.get("text"), 500)
        if key in {force[0] for force in FORCES} and text:
            supplied.setdefault(key, []).append({"text": text, "provenance": "student",
                                                 "source": _clean(item.get("source"), 300)})
    blocks, notes = [], []
    for key, label, cues in FORCES:
        items = list(supplied.get(key, []))
        found, query = _search(cues, country, region, year_from, industry, key)
        for source in found:
            quote = _first_sentence(source)
            if quote:
                items.append({"text": quote, "provenance": "sourced", "source": _source_text(source),
                              "citation": _source_cite(source),
                              "title": _clean(source.get("title"), 200), "database": source.get("database")})
        gap = None
        if not items:
            gap = "No evidence was found for this force. It is returned as a gap, not filled."
        blocks.append({"key": key, "label": label, "items": items, "gap": gap, "query": query})
        if found:
            notes.append(label + ": " + str(len(found)) + " sourced item(s).")
    gaps = [block["key"] for block in blocks if block["gap"]]
    if gaps:
        suggestions = _suggest(gaps, instruction, industry=industry, sourced=
                               {block["key"]: [item["text"] for item in block["items"]] for block in blocks})
        for block in blocks:
            if block["key"] in suggestions:
                block["items"] = block["items"] + [{"text": suggestions[block["key"]],
                                                    "provenance": "suggested", "source": ""}]
                block["gap"] = "No source was found; a case assumption is proposed for your review."
                notes.append(block["label"] + ": suggested case assumption.")
    return {"format": "bp-framework-completion/1", "template": template, "instruction": instruction,
            "country": country, "region": region, "blocks": blocks, "notes": notes,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}

def draft(result, style="apa"):
    """A Word-ready draft from a completion result; no new facts or ratings."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    instruction = _clean(result.get("instruction"), 500)
    blocks = result.get("blocks") or []
    sections = [paper.section("Introduction", 1, [
        "This draft responds to: " + instruction + ". It uses Porter's Five Forces to organise the industry evidence. "
        "Sourced items are cited; case assumptions are labelled; a force with no source is a named gap. The draft does "
        "not assign ratings or recommend a decision."
    ]), paper.section("Five Forces", 1)]
    sourced, assumptions, gaps = 0, 0, 0
    references, seen = [], set()
    for block in blocks:
        lines = []
        for item in block.get("items") or []:
            if item.get("provenance") == "sourced":
                cite = item.get("citation") or ""
                lines.append(_clean(item.get("text"), 600) + (" " + cite if cite else ""))
                sourced += 1
                ref = item.get("source")
                if ref and ref not in seen:
                    seen.add(ref)
                    references.append(ref)
            else:
                text = _clean(item.get("text"), 600)
                if not text.lower().startswith("case assumption"):
                    text = "Case assumption: " + text
                lines.append(text)
                assumptions += 1
        if not lines:
            lines = [block.get("gap") or "No evidence was found for this force."]
            gaps += 1
        sections.append(paper.section(block.get("label") or block.get("key"), 2, [" ".join(lines)]))
    sections += [
        paper.section("Discussion", 1),
        paper.section("What the evidence shows", 2, [
            "The five forces returned " + str(sourced + assumptions) + " item(s): " + str(sourced) +
            " sourced item(s), " + str(assumptions) + " case assumption(s) and " + str(gaps) + " named gap(s). "
            "The sourced items carry a citation; the assumptions are starting points for the student's own case, not evidence."
        ]),
        paper.section("Limitations", 2, [
            "The draft does not rate the forces, compute an overall attractiveness score or recommend a decision. "
            "A case assumption is not a source, and a gap is not a finding. The student must verify every assumption "
            "and add the judgment before submission."
        ]),
        paper.section("References" if style == "apa" else "Bibliography", 1, references or ["No sources were used."]),
    ]
    title = "Porter's Five Forces: " + _clean(instruction, 120)
    return {"title": title, "sections": sections, "style": style}


def draft_bytes(result, style="apa"):
    report = draft(result, style)
    return docx.render_academic(report["title"], report["sections"], report["style"])
