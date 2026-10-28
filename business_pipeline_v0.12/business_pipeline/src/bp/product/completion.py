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

FORCE_KEYS = ["rivalry", "entrants", "substitutes", "buyers", "suppliers"]

ANALYSIS = {
    "rivalry": (
        "Rivalry of this kind shapes returns through price and non-price competition. Where manufacturers "
        "compete on both price and features, an entrant's margin depends on differentiating the offer rather "
        "than matching rivals on cost alone. The relevant question for the decision is whether the planned "
        "position can be defended against competitors that already compete on the same dimensions. The "
        "assessment would be strengthened by evidence on the number and size of rivals in the market, which "
        "the case does not supply."),
    "entrants": (
        "Entry conditions determine how quickly new capacity reaches the market. Where entrants must secure "
        "distribution and build a brand, incumbents gain time to respond, but the same requirement applies to "
        "the entrant under consideration. The relevant question for the decision is whether entry can meet "
        "those requirements at a cost the plan can carry. Evidence on the cost and time needed to secure "
        "distribution and recognition would sharpen the assessment, and the case does not provide it."),
    "substitutes": (
        "Substitutes place a ceiling on what buyers will pay for the product itself. When alternatives cover "
        "part of the need, demand shifts at the margin rather than disappearing, so pricing power is bounded by "
        "the next best option. The relevant question for the decision is how much of the need the offer must "
        "serve to keep buyers from switching. The assessment would be strengthened by evidence on how often "
        "buyers actually choose those alternatives, which the case does not supply."),
    "buyers": (
        "Buyer power determines how far cost increases can be passed on. Where buyers compare specifications "
        "and prices before switching, the offer must compete on visible value rather than on habit or lock-in. "
        "The relevant question for the decision is whether the planned offer gives buyers a reason to choose it "
        "on the terms they already use to compare. Evidence on how concentrated buyers are and how easily they "
        "can switch would sharpen the assessment, and the case does not provide it."),
    "suppliers": (
        "Supplier power determines the cost and reliability of critical inputs. Where capacity in key inputs is "
        "scarce, input terms can absorb the margin an entrant expects to earn. The relevant question for the "
        "decision is whether supply can be secured on terms that keep the plan viable. Evidence on the number of "
        "alternative suppliers and on the duration of contracts would sharpen the assessment, and the case does "
        "not provide it."),
}


def _words(text):
    return len(re.findall(r"[A-Za-z0-9'\u2019%-]+", str(text or "")))


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split("\n") if part.strip()]


def _facts(blocks):
    facts = []
    for block in blocks:
        facts.append({"key": block.get("key"), "label": block.get("label"),
                      "items": [{"text": _clean(item.get("text"), 600), "kind": _kind(item)}
                                for item in block.get("items") or []]})
    return facts


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


LEAD = ("Porter's Five Forces assesses the attractiveness of an industry through five sources of competitive "
        "pressure. Each force is treated in turn, first through the evidence accepted for the case and then through "
        "what that evidence implies for the decision.")

HEAD_SYSTEM = (
    "You are writing the opening of a Porter's Five Forces paper for a business student. "
    "Use only the case instruction and the force items. Write an introduction of 190 to 230 words in two "
    "paragraphs: the first introduces the case and the industry, the second states the approach and ends with a "
    "single-sentence thesis saying what the evidence implies about the strength of the forces (do not claim that "
    "the framework is useful). Write a case context of 130 to 170 words in one paragraph that sets out the "
    "decision and the industry. Do not restate every force item. Do not add facts, numbers, names, sources or "
    "citations beyond the items. Do not recommend a decision. Return only JSON: "
    "{\"introduction\":[\"...\",\"...\"], \"thesis\":\"...\", \"context\":[\"...\"]}.")

FORCE_SYSTEM = (
    "You are writing one section of a Porter's Five Forces paper for a business student. The force is {label}. "
    "Use only the case instruction, the thesis and the force items. Write two paragraphs of 190 to 220 words in total: the "
    "first says what the evidence shows, the second says what it implies for the decision. "
    "Do not add facts, numbers, names, sources or citations beyond the items. Do not recommend a decision. "
    "Return only JSON: {\"paragraphs\":[\"...\",\"...\"]}.")

MID_SYSTEM = (
    "You are writing the discussion of a Porter's Five Forces paper for a business student. "
    "Use only the case instruction, the thesis and the force items. Write the discussion (170 to 200 words in two "
    "paragraphs) reading the forces together, then the implications (190 to 220 words in two paragraphs) stating what the "
    "combined reading means for the decision without making the decision. "
    "Do not add facts, numbers, names, sources or citations beyond the items. "
    "Return only JSON: {\"discussion\":[\"...\",\"...\"], \"implications\":[\"...\",\"...\"]}.")

TAIL_SYSTEM = (
    "You are closing a Porter's Five Forces paper for a business student. "
    "Use only the case instruction, the thesis and the force items. Write the limitations (100 to 140 words in one "
    "paragraph) and the conclusion (140 to 170 words in two paragraphs) that answers the stated thesis and names the "
    "strongest and the weakest evidenced force. Do not add facts, numbers, names, sources or citations beyond the items. "
    "Do not recommend a decision. Return only JSON: {\"limitations\":[\"...\"], \"conclusion\":[\"...\",\"...\"]}.")


def _ask(system, payload, timeout=180):
    raw = prose._call([{"role": "system", "content": system},
                       {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                      timeout=timeout, max_tokens=6000)
    if not str(raw or "").strip():
        raise ValueError("empty response")
    return prose._parse(raw)


def _ask_force(label, payload, timeout=180):
    return _ask(FORCE_SYSTEM.replace("{label}", str(label)), payload, timeout)


def _shape(raw):
    raw = raw if isinstance(raw, dict) else {}
    forces = raw.get("forces") if isinstance(raw.get("forces"), dict) else {}
    return {
        "introduction": _as_list(raw.get("introduction")),
        "context": _as_list(raw.get("context")),
        "lead": str(raw.get("lead") or "").strip(),
        "forces": {key: _as_list(forces.get(key)) for key in FORCE_KEYS},
        "discussion": _as_list(raw.get("discussion")),
        "implications": _as_list(raw.get("implications")),
        "limitations": _as_list(raw.get("limitations")),
        "conclusion": _as_list(raw.get("conclusion")),
    }


def _model_sections(result, style="apa", attempt=0):
    """A thesis call, then seven small calls in parallel; thin or invented prose is refused."""
    global LAST_REJECT
    if not attempt:
        LAST_REJECT = None
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
    base = {"instruction": instruction, "forces": facts}
    try:
        head = _ask(HEAD_SYSTEM, base)
    except Exception as error:
        return _retry(result, style, attempt, "head: " + str(error)[:140])
    thesis = str((head or {}).get("thesis") or "").strip()
    if not thesis:
        return _retry(result, style, attempt, "no thesis")
    payload = dict(base, thesis=thesis)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    jobs = {"mid": lambda: _ask(MID_SYSTEM, payload),
            "tail": lambda: _ask(TAIL_SYSTEM, payload)}
    for block in blocks:
        label = block.get("label") or block.get("key")
        items = [{"text": _clean(item.get("text"), 600), "kind": _kind(item)}
                 for item in block.get("items") or []]
        force_payload = {"instruction": instruction, "thesis": thesis, "force": label, "items": items}
        jobs[block.get("key")] = (lambda label=label, fp=force_payload: _ask_force(label, fp))
    answers = {}
    try:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            running = {pool.submit(job): name for name, job in jobs.items()}
            for future in as_completed(running):
                answers[running[future]] = future.result()
    except Exception as error:
        return _retry(result, style, attempt, "call: " + str(error)[:140])
    merged = {"introduction": (head or {}).get("introduction") or [],
              "thesis": thesis,
              "context": (head or {}).get("context") or [],
              "lead": LEAD,
              "forces": {block.get("key"): (answers.get(block.get("key")) or {}).get("paragraphs") or []
                         for block in blocks},
              "discussion": (answers.get("mid") or {}).get("discussion") or [],
              "implications": (answers.get("mid") or {}).get("implications") or [],
              "limitations": (answers.get("tail") or {}).get("limitations") or [],
              "conclusion": (answers.get("tail") or {}).get("conclusion") or []}
    data = _shape(merged)
    for name in ("introduction", "context", "discussion", "implications", "limitations", "conclusion"):
        data[name] = [CITATION.sub("", part) for part in data[name]]
    data["lead"] = CITATION.sub("", data["lead"])
    data["forces"] = {key: [CITATION.sub("", part) for part in parts]
                      for key, parts in data["forces"].items()}
    citations_by_key = {}
    for block in blocks:
        cites = [item.get("citation") for item in block.get("items") or []
                 if item.get("provenance") == "sourced" and item.get("citation")]
        citations_by_key[block.get("key")] = list(dict.fromkeys(cite for cite in cites if cite))
    problems = _problems(data, facts, instruction)
    if problems:
        return _retry(result, style, attempt, "; ".join(problems[:3]))
    return (data, citations_by_key)


def _problems(data, facts, instruction=""):
    problems = []
    floors = [("introduction", 150), ("context", 110), ("discussion", 130),
              ("implications", 150), ("limitations", 70), ("conclusion", 110)]
    for name, floor in floors:
        if _words(" ".join(data[name])) < floor:
            problems.append("%s short (%d)" % (name, _words(" ".join(data[name]))))
    if len(data["introduction"]) < 2:
        problems.append("introduction is one paragraph")
    if _words(data["lead"]) < 25:
        problems.append("lead short")
    for key in FORCE_KEYS:
        parts = data["forces"].get(key) or []
        if len(parts) < 2:
            problems.append("%s is one paragraph" % key)
        if _words(" ".join(parts)) < 140:
            problems.append("%s short (%d)" % (key, _words(" ".join(parts))))
    total = sum(_words(" ".join(data[name])) for name in
                ("introduction", "context", "discussion", "implications", "limitations", "conclusion"))
    total += _words(data["lead"]) + sum(_words(" ".join(parts)) for parts in data["forces"].values())
    if total < 1400:
        problems.append("paper short (%d words)" % total)
    text = " ".join([data["lead"]] + [part for name in
                    ("introduction", "context", "discussion", "implications", "limitations", "conclusion")
                    for part in data[name]] +
                    [part for parts in data["forces"].values() for part in parts])
    if URL.search(text):
        problems.append("link")
    supplied_items = " ".join(item["text"] for force in facts for item in force["items"])
    extra = set(NUMBER.findall(text)) - set(NUMBER.findall(supplied_items))
    if extra:
        problems.append("number " + ",".join(sorted(extra)))
    supplied = (str(instruction or "") + " " + supplied_items).lower()
    supplied_words = set(re.findall(r"[a-z]{4,}", supplied))
    for name in set(PROPER.findall(text)):
        low = name.lower()
        if low in supplied_words or low in FRAMEWORK_WORDS:
            continue
        if any(low.startswith(word) or word.startswith(low) for word in supplied_words):
            continue
        problems.append("name " + name)
    return problems


def _retry(result, style, attempt, reason):
    if not attempt:
        return _model_sections(result, style, 1)
    return _reject(reason)


def _title(instruction):
    text = _clean(instruction, 160).strip()
    text = text.rstrip(" .,;:!?")
    if len(text) > 110:
        text = text[:110].rsplit(" ", 1)[0].rstrip(" .,;:")
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return "Porter's Five Forces: " + text


def _draft_data(result):
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
    listed = ", ".join("%s (%d)" % (label, count) for label, count in zip(labels, counts)) or "no force"
    strongest = labels[counts.index(max(counts))] if counts else "none of the forces"
    weakest = labels[counts.index(min(counts))] if counts else "none of the forces"
    data = {
        "introduction": [
            "This paper examines the competitive structure of the industry identified in the case using Porter's "
            "Five Forces. The decision under examination is whether to proceed with the course of action set out "
            "in the brief. The analysis is confined to the evidence accepted for the case, and it treats the "
            "industry, rather than the firm in isolation, as the unit of assessment.",
            "The paper first sets out the case and the industry that frames it. It then assesses each of the five "
            "forces in turn: rivalry among existing competitors, the threat of new entrants, the threat of "
            "substitutes, buyer power and supplier power. Each force is presented through the evidence accepted "
            "for it and through the implications of that evidence for the decision.",
            "The argument developed below is that the forces that carry evidence in this case determine how much "
            "room an entrant has to earn a return, and that a force recorded as a gap cannot be read as "
            "favourable. The conclusion returns to this argument and states how far the evidence supports it."],
        "context": [
            "The case concerns the following decision: " + instruction + ". The industry is the market in which "
            "the product or service competes, and the analysis treats that market as the relevant arena because "
            "the five forces describe industry structure rather than the record of a single company.",
            "The evidence base is limited to the items accepted for the case. A force with no accepted item is "
            "recorded as a gap rather than filled by assumption, and an item supplied as a case assumption is "
            "identified as an assumption rather than as evidence. The paper does not rate the forces, compute an "
            "attractiveness score or recommend a decision."],
        "lead": ("Porter's Five Forces assesses the attractiveness of an industry through five sources of "
                 "competitive pressure. Each force is treated in turn, first through the evidence accepted for "
                 "the case and then through what that evidence implies for the decision."),
        "forces": {},
        "discussion": [
            "The case supplies " + str(sourced + student + assumptions) + " accepted items across the five "
            "forces: " + str(sourced) + " sourced items, " + str(student) + " items of the student's own evidence "
            "and " + str(assumptions) + " case assumptions. The forces that carry evidence are " + listed +
            ", while " + str(gaps) + " force(s) are recorded as gaps.",
            "Read together, the forces that carry evidence describe a setting in which the pressures supported by "
            "items interact rather than operate separately. A force with no item places no weight on the "
            "assessment, because a gap is not a finding and cannot be treated as either a strength or a "
            "weakness. The reading that follows is therefore a judgement about the accepted evidence, not a "
            "verdict on the decision."],
        "implications": [
            "The combined reading carries consequences for the decision. The pressures that the evidence supports "
            "have to be answered in the plan itself: a competitive offer, a route to buyers and access to the "
            "inputs the operation needs. A force that appears weak in the evidence is not thereby a force that "
            "can be ignored; it is a force the case has not documented.",
            "The practical implication is that the case for proceeding cannot rest on the forces that are thin in "
            "evidence, because those forces are unmeasured rather than benign. It must be argued from the "
            "pressures that are documented, and the plan must show how each of them would be met. The decision "
            "itself, and the justification offered for it, remain the student's."],
        "limitations": [
            "The analysis does not rate the forces, compute an overall attractiveness score or recommend a "
            "decision, because the accepted items do not support a quantitative comparison across forces. A case "
            "assumption is not a source, and a gap is not a finding. Several forces rest on a single item, so the "
            "weight given to them is limited by what that item supports. The student must verify every item "
            "before submission."],
        "conclusion": [
            "The paper set out to assess the industry through the five forces and to state what the accepted "
            "evidence implies for the decision. The forces with evidence are " + listed + ", and " + strongest +
            " carries the most weight in the reading offered here, while " + weakest + " carries the least.",
            "On that basis the industry presents a competitive setting that the decision must answer force by "
            "force, and the argument stated in the introduction is supported only as far as the items reach. The "
            "paper does not make the decision; it sets out the pressures that the decision has to justify."],
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
            elif str(item.get("provenance") or "").lower() == "synthetic":
                lines.append("Illustrative: " + text)
            else:
                lines.append("Case assumption: " + text
                             if not text.lower().startswith("case assumption") else text)
        first = (" ".join(lines) if lines else
                 (block.get("gap") or "No evidence was found for this force, so the force is recorded as a gap."))
        data["forces"][key] = [first, ANALYSIS.get(key, "")]
    return data


def _sections(data, blocks, style, citations, result):
    references, seen = [], set()
    for block in blocks:
        for item in block.get("items") or []:
            if _kind(item) == "sourced" and item.get("source"):
                if item["source"] not in seen:
                    seen.add(item["source"])
                    references.append(item["source"])
    sections = [paper.section("Introduction", 1, list(data["introduction"])),
                paper.section("Case and industry context", 2, list(data["context"])),
                paper.section("Five Forces", 1, [data["lead"]])]
    for block in blocks:
        key = block.get("key")
        paragraphs = list(data["forces"].get(key) or [])
        if not paragraphs:
            paragraphs = [block.get("gap") or "No evidence was found for this force."]
        cites = citations.get(key) or []
        if cites and paragraphs:
            paragraphs[0] = paragraphs[0].rstrip() + " " + " ".join(cites)
        sections.append(paper.section(block.get("label") or key, 2, paragraphs))
    sections += [
        paper.section("Discussion", 1),
        paper.section("What the evidence shows", 2, list(data["discussion"])),
        paper.section("Implications for the decision", 2, list(data["implications"])),
        paper.section("Limitations", 2, list(data["limitations"])),
        paper.section("Conclusion", 1, list(data["conclusion"])),
        paper.section("References" if style == "apa" else "Bibliography", 1,
                      references or ["No sources were used."]),
    ]
    return sections


def draft(result, style="apa", version="draft"):
    """A full paper from a completion result; no new facts, ratings or citations."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    blocks = result.get("blocks") or []
    model_used = False
    citations = {}
    if version == "full":
        generated = _model_sections(result, style)
        if not generated:
            raise ValueError("The model did not return a valid paper. Nothing was downloaded; choose Draft "
                             "(evidence-led) or try again.")
        data, citations = generated
        model_used = True
    else:
        data = _draft_data(result)
    sections = _sections(data, blocks, style, citations, result)
    words = sum(_words(" ".join(section.get("lines") or [])) for section in sections)
    return {"title": _title(result.get("instruction")), "sections": sections, "style": style,
            "version": version, "model_used": model_used, "words": words,
            "byline": [str(line).strip() for line in (result.get("byline") or []) if str(line or "").strip()]}


def draft_bytes(result, style="apa", report=None, version="draft"):
    report = report or draft(result, style, version)
    return docx.render_academic(report["title"], report["sections"], report["style"],
                                byline=report.get("byline") or ())
