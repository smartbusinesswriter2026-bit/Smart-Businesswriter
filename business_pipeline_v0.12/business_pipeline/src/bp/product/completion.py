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

NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
FRAMEWORK_WORDS = {"porter", "forces", "five", "swot", "pestel", "five", "break", "even"}
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b")
CITATION = re.compile(r"\([^()]{1,140}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")
URL = re.compile(r"https?://|doi:", re.I)

TEMPLATE = "template_five_forces"

FORCES = [
    ("rivalry", "Industry rivalry", "competition competitive rival market share price war"),
    ("entrants", "Threat of new entrants", "market entry barriers capital licence"),
    ("substitutes", "Threat of substitutes", "substitute alternative switching"),
    ("buyers", "Buyer power", "buyer customer consumer bargaining concentration"),
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
    title = _clean(item.get("title"), 300).lower()
    text = (title + " " + _clean(item.get("abstract") or item.get("description"), 900)).lower()
    words = set(re.findall(r"[a-z][a-z0-9'-]+", text))
    title_words = {word.rstrip("s") if len(word) > 4 else word
                   for word in re.findall(r"[a-z][a-z0-9'-]+", title)}
    cue_words = {word.rstrip("s") if len(word) > 4 else word for word in cues.split()}
    context_words = {word.rstrip("s") if len(word) > 4 else word for word in (context or [])}
    cue_hits = len(cue_words & {word.rstrip("s") if len(word) > 4 else word for word in words})
    title_cues = len(cue_words & title_words)
    title_context = len(context_words & title_words)
    if context_words and not title_context:
        return -1
    if cue_hits == 0 or title_cues == 0:
        return -1
    if any(word in title for word in ("biosensor", "patients", "clinical", "depressive", "anxiety",
                                      "athletes", "food contaminant", "intervention", "childhood",
                                      "therapy")) and "health" not in (context or []):
        return -1
    geo = 2 if country and country.lower() in text else 0
    tier = 2 if item.get("tier") in ("official", "data") else 1 if item.get("database") else 0
    return title_cues * 3 + cue_hits * 2 + geo + tier + (item.get("credibility") or 0) / 100


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

def _kind(item):
    provenance = str(item.get("provenance") or "").lower()
    if provenance == "sourced":
        return "sourced"
    if provenance in ("student", "user", "own"):
        return "student"
    return "assumption"


LAST_REJECT = None


def _reject(reason):
    global LAST_REJECT
    LAST_REJECT = reason
    try:
        import os, tempfile, time
        path = os.path.join(tempfile.gettempdir(), "bp_model_reject.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + str(reason) + "\n")
    except Exception:
        pass
    return None


def _model_sections(result, style="apa", attempt=0):
    """Ask the model for coherent prose; citations are appended deterministically."""
    global LAST_REJECT
    if not attempt:
        LAST_REJECT = None
    try:
        from . import prose as editor
        if not editor.available():
            return _reject("model unavailable")
    except Exception:
        return _reject("model import")
    blocks = result.get("blocks") or []
    citations_by_key, forces = {}, []
    for block in blocks:
        citations = []
        for item in block.get("items") or []:
            if item.get("provenance") == "sourced" and item.get("citation"):
                if item["citation"] not in citations:
                    citations.append(item["citation"])
        citations_by_key[block.get("key")] = citations
        forces.append({"key": block.get("key"), "label": block.get("label"),
                       "items": [{"text": _clean(item.get("text"), 600), "kind": _kind(item)}
                                 for item in block.get("items") or []]})
    if not forces:
        return _reject("no items")
    system = ("You are an academic analyst writing a concise Porter's Five Forces paper for a business student. "
              "Use only the instruction and force items. Write in third person, as a finished paper, not as a "
              "commentary on your sources. Never mention supplied items, provided material, the draft, the model, "
              "the system, this paragraph, the available evidence or the drafting process. Synthesise the items into "
              "an argument about the industry. An item marked student is the student's own case evidence: present it as "
              "evidence for this case without attributing it to a published source. An item marked assumption is a case "
              "assumption: distinguish it by wording, not by meta-commentary. Introduce no new market condition, "
              "mechanism, cost, actor, technology, country, company or example beyond the items; an inference must be "
              "phrased as an inference for this case (this suggests, this implies, this points to), never as a new "
              "finding. Do not recommend a decision. Do NOT write any citation, parenthetical reference, marker, "
              "source name, URL, number or percentage; the system adds citations afterwards. Return ONLY JSON with "
              'this shape: {"introduction":"...", "forces":{"rivalry":"...", "...":"..."}, "discussion":"...", '
              '"conclusion":"..."}. One paragraph per force. No headings, markdown or bullets.')
    user = json.dumps({"instruction": result.get("instruction"), "forces": forces}, ensure_ascii=False)
    try:
        raw = editor._call([{"role": "system", "content": system}, {"role": "user", "content": user}],
                           timeout=90)
        data = editor._parse(raw)
    except Exception as error:
        return _retry(result, style, attempt, "call: " + str(error)[:120])
    if not isinstance(data, dict) or not data.get("introduction") or not data.get("conclusion") \
            or not isinstance(data.get("forces"), dict):
        return _retry(result, style, attempt, "shape")
    text = " ".join([str(data.get("introduction", "")),
                     " ".join(str(value) for value in (data.get("forces") or {}).values()),
                     str(data.get("discussion", "")), str(data.get("conclusion", ""))])
    data["introduction"] = CITATION.sub("", str(data.get("introduction", "")))
    data["discussion"] = CITATION.sub("", str(data.get("discussion", "")))
    data["conclusion"] = CITATION.sub("", str(data.get("conclusion", "")))
    data["forces"] = {key: CITATION.sub("", str(value)) for key, value in (data.get("forces") or {}).items()}
    text = CITATION.sub("", text)
    if URL.search(text):
        return _retry(result, style, attempt, "url")
    supplied_items = " ".join(_clean(item.get("text"), 600) for block in blocks
                              for item in block.get("items") or [])
    allowed_numbers = set(NUMBER.findall(supplied_items))
    extra = set(NUMBER.findall(text)) - allowed_numbers
    if extra:
        return _retry(result, style, attempt, "numbers: " + ",".join(sorted(extra)))
    supplied = (str(result.get("instruction") or "") + " " + supplied_items).lower()
    supplied_words = set(re.findall(r"[a-z]{4,}", supplied))
    for name in set(PROPER.findall(text)):
        low = name.lower()
        if low in supplied or low in FRAMEWORK_WORDS:
            continue
        if any(low.startswith(word) or word.startswith(low) for word in supplied_words):
            continue
        return _retry(result, style, attempt, "name: " + name)
    return (data, text, citations_by_key)


def _retry(result, style, attempt, reason):
    if not attempt:
        return _model_sections(result, style, 1)
    return _reject(reason)

def draft(result, style="apa", version="draft"):
    """A Word-ready draft from a completion result; no new facts or ratings."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    instruction = _clean(result.get("instruction"), 500)
    blocks = result.get("blocks") or []
    generated = _model_sections(result, style) if version == "full" else None
    model = generated[0] if generated else None
    sections = [paper.section("Introduction", 1, [
        (model.get("introduction") if model and model.get("introduction") else
         "This paper analyses the following case with Porter's Five Forces: " + instruction.rstrip(".") + ". Each force is set out "
         "from the evidence held for the case. Sourced items carry a citation, the student's own items are presented as "
         "case evidence, and a force without evidence is named as a gap. The paper does not assign ratings or recommend "
         "a decision.")
    ]), paper.section("Five Forces", 1)]
    sourced, student_items, assumptions, gaps = 0, 0, 0, 0
    references, seen = [], set()
    for block in blocks:
        lines = []
        for item in block.get("items") or []:
            kind = _kind(item)
            text = _clean(item.get("text"), 600)
            if kind == "sourced":
                cite = item.get("citation") or ""
                lines.append(text + (" " + cite if cite else ""))
                sourced += 1
                ref = item.get("source")
                if ref and ref not in seen:
                    seen.add(ref)
                    references.append(ref)
            elif kind == "student":
                lines.append(text)
                student_items += 1
            elif str(item.get("provenance") or "").lower() == "synthetic":
                lines.append("Illustrative: " + text)
                assumptions += 1
            else:
                if not text.lower().startswith("case assumption"):
                    text = "Case assumption: " + text
                lines.append(text)
                assumptions += 1
        if not lines:
            lines = [block.get("gap") or "No evidence was found for this force."]
            gaps += 1
        model_text = ((model.get("forces") or {}).get(block.get("key")) if model else None)
        if model_text:
            cites = generated[2].get(block.get("key")) or []
            if cites:
                model_text = model_text.rstrip() + " " + " ".join(cites)
        sections.append(paper.section(block.get("label") or block.get("key"), 2,
                                      [model_text if model_text else " ".join(lines)]))
    sections += [
        paper.section("Discussion", 1),
        paper.section("What the evidence shows", 2, [
            (model.get("discussion") if model and model.get("discussion") else
             "The five forces returned " + str(sourced + student_items + assumptions) + " item(s): " + str(sourced) +
             " sourced item(s), " + str(student_items) + " item(s) from the student's own case evidence, " +
             str(assumptions) + " case assumption(s) and " + str(gaps) + " named gap(s). The sourced items carry a "
             "citation; a case assumption is a starting point for the student's own case, not evidence.")
        ]),
        paper.section("Limitations", 2, [
            "The paper does not rate the forces, compute an overall attractiveness score or recommend a decision. "
            "A case assumption is not a source, and a gap is not a finding. The student must verify every assumption "
            "and add the judgment before submission."
        ]),
        paper.section("Conclusion", 1, [
            (model.get("conclusion") if model and model.get("conclusion") else
             "The paper sets out the five forces; the decision and its justification remain the student's.")
        ]),
        paper.section("References" if style == "apa" else "Bibliography", 1, references or ["No sources were used."]),
    ]
    title = "Porter's Five Forces: " + _clean(instruction, 120)
    return {"title": title, "sections": sections, "style": style, "version": version,
            "model_used": bool(model)}


def draft_bytes(result, style="apa", report=None, version="draft"):
    report = report or draft(result, style, version)
    return docx.render_academic(report["title"], report["sections"], report["style"])
