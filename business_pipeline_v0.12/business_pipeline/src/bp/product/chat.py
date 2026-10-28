"""Deterministic framework conductor (product layer).

This first conductor covers PESTEL and SWOT, separately or together.  It guides
a student with a fixed question bank, a confirmed plan, per-dimension source
retrieval, an evidence review and an APA/Harvard section.

It uses no model.  Every external evidence item is a sentence from a retrieved
source, with the source recorded; a dimension with no retrieved evidence is
reported as a gap.  Strengths and weaknesses are supplied by the student and are
never inferred.  The chat never writes a fact, a source or a number of its own.
"""

import datetime
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait

from . import docx, writing

FORMAT = "bp-chat/1"

#: A whole research pass may not outlast this, even if one provider hangs.
RESEARCH_DEADLINE = float(os.environ.get("BP_RESEARCH_DEADLINE", "20"))

DIMENSIONS = [
    ("political", "Political", "government policy sanctions regulation trade stability", "legal"),
    ("economic", "Economic", "economic growth inflation interest exchange demand", "economic"),
    ("social", "Social", "demographic population youth internet social cultural labour consumer behaviour", "social"),
    ("technological", "Technological", "technology innovation digital automation research", None),
    ("environmental", "Environmental", "climate environment sustainability emissions energy", None),
    ("legal", "Legal", "law legislation sanctions compliance export control regulation", "legal"),
]

SWOT_DIMENSIONS = [
    ("opportunities", "Opportunities", "growth demand consumer innovation investment digital expansion reform", None),
    ("threats", "Threats", "sanctions embargo regulation competition inflation risk restriction conflict", "legal"),
]

FRAMEWORKS = {
    "pestel": {"label": "PESTEL", "dimensions": DIMENSIONS, "internal": False},
    "swot": {"label": "SWOT", "dimensions": SWOT_DIMENSIONS, "internal": True},
    "pestel_swot": {"label": "PESTEL + SWOT", "dimensions": DIMENSIONS, "internal": True},
}

QUESTIONS = [
    {"id": "decision", "prompt": "What decision or question should this PESTEL analysis support?",
     "why": "The analysis should serve a decision, not sit on its own.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "geography", "prompt": "Which market or region should the evidence cover?",
     "why": "Political, economic and legal evidence is country-specific.",
     "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"},
    {"id": "period", "prompt": "How recent should the evidence be?",
     "why": "A current analysis needs dated evidence, not undated generalities.",
     "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                   ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"},
    {"id": "style", "prompt": "Which citation style should the section use?",
     "why": "The paper has to match the style your course requires.",
     "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"},
]

INTERNAL_QUESTIONS = [
    {"id": "decision", "prompt": "What decision or question should this SWOT analysis support?",
     "why": "The matrix should serve a decision, not sit on its own.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "strengths", "prompt": "What strengths does the case give you? Separate items with semicolons.",
     "why": "Strengths are internal facts about the firm; the system will not invent them.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "weaknesses", "prompt": "What weaknesses does the case give you? Separate items with semicolons.",
     "why": "Weaknesses are internal facts about the firm; the system will not invent them.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "geography", "prompt": "Which market or region should the external evidence cover?",
     "why": "Opportunities and threats are country-specific.",
     "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"},
    {"id": "period", "prompt": "How recent should the external evidence be?",
     "why": "A current analysis needs dated evidence, not undated generalities.",
     "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                   ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"},
    {"id": "style", "prompt": "Which citation style should the section use?",
     "why": "The paper has to match the style your course requires.",
     "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"},
]

FRAMEWORK_QUESTIONS = {"pestel": QUESTIONS, "swot": INTERNAL_QUESTIONS, "pestel_swot": INTERNAL_QUESTIONS}

#: Short, targeted search phrases.  Long cue lists return few results in the
#: scholarly indexes; these keep the query specific to the dimension.
SEARCH_TERMS = {
    "political": "sanctions policy government",
    "economic": "economy inflation currency",
    "social": "population youth internet",
    "technological": "digital technology internet",
    "environmental": "water climate drought",
    "legal": "sanctions law compliance",
    "opportunities": "market growth digital consumers",
    "threats": "sanctions conflict restrictions",
}

EXTERNAL_HINTS = {
    "market", "industry", "country", "region", "regulation", "policy", "macro", "economy",
    "economic", "social", "technology", "technological", "environment", "environmental",
    "legal", "political", "competition", "trend", "demand", "export", "trade", "expansion",
    "entry", "business", "company", "firm", "startup", "organization", "product", "service",
}
COMPUTATION_HINTS = {
    "journal entry", "ledger", "trial balance", "balance sheet", "income statement", "npv",
    "irr", "depreciation", "variance", "amortization", "amortisation", "regression", "calculate",
    "compute", "reconcile", "debit", "credit",
}


STOP = set(
    "a an the and or of to in on for with by at from as is are was were be been it its this that these those "
    "we our us you your i my me they their them not no do does did can could should would will may might have "
    "has had how what when where which who why if then than so such about into over under between among after "
    "before during each per via also more most much many some any other another own same very".split()
)


class ChatError(ValueError):
    """A conductor step was refused with a reason the student can act on."""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _clean(value, limit=2000):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _fit(brief, framework="pestel"):
    text = (brief or "").lower()
    if any(hint in text for hint in COMPUTATION_HINTS) and not any(hint in text for hint in EXTERNAL_HINTS):
        return False, ("This looks like an accounting or finance computation, not a strategic analysis. "
                       "Use the Accounting or Finance shelf instead.")
    if framework == "pestel" and not any(hint in text for hint in EXTERNAL_HINTS):
        return False, ("This brief does not yet name an external question. Add the market, industry, country "
                       "or decision the analysis should support.")
    return True, None


def _items(value, limit=6):
    """Split a supplied list into clean items; the student's words are kept."""
    if isinstance(value, list):
        parts = value
    else:
        parts = re.split(r"[\n;]+", str(value or ""))
    return [item for item in (_clean(part, 200) for part in parts) if item][:limit]


def _infer_framework(brief):
    text = (brief or "").lower()
    if "swot" in text and "pestel" in text:
        return "pestel_swot"
    if "swot" in text:
        return "swot"
    return "pestel"


def _defaults(brief):
    text = (brief or "").lower()
    geography = "Global"
    for word, region in (("united states", "US"), ("u.s.", "US"), (" us ", "US"), ("america", "US"),
                         ("europe", "Europe"), ("european union", "Europe"), (" eu ", "Europe"), ("uk", "Europe"),
                         ("middle east", "Middle East"), ("saudi", "Middle East"), ("uae", "Middle East"),
                         ("qatar", "Middle East"), ("china", "China"), ("chinese", "China")):
        if word in text:
            geography = region
            break
    period = "10"
    match = re.search(r"(?:last|past|since)\s+(\d{1,2})\s+years?", text)
    if match:
        period = match.group(1)
    style = "harvard" if "harvard" in text else "apa"
    return {"decision": _clean(brief, 500), "geography": geography, "period": period, "style": style}


def start(brief, subject="management", framework=None):
    """Create a conductor state.  No source is retrieved until the plan is confirmed."""
    brief = _clean(brief, 2000)
    if len(brief) < 15:
        raise ChatError("Describe the case or assignment in at least one sentence.")
    framework = (framework or "").strip().lower() or _infer_framework(brief)
    if framework not in FRAMEWORKS:
        raise ChatError("Choose PESTEL, SWOT, or PESTEL + SWOT.")
    fits, message = _fit(brief, framework)
    questions = [dict(question) for question in FRAMEWORK_QUESTIONS[framework]]
    answers = _defaults(brief)
    if FRAMEWORKS[framework]["internal"]:
        answers.update({"strengths": [], "weaknesses": []})
    state = {"format": FORMAT, "subject": subject or "management", "framework": framework, "brief": brief,
             "created_at": _now(), "updated_at": _now(), "stage": "clarify",
             "answers": answers, "questions": questions, "question_index": 0,
             "plan": None, "sources": [], "evidence": [], "gaps": [], "notes": [],
             "draft": None}
    if not fits:
        state.update({"stage": "not_supported", "message": message, "questions": [], "question_index": 0})
    return state


def current_question(state):
    index = state.get("question_index", 0)
    questions = state.get("questions") or []
    return questions[index] if index < len(questions) else None


def answer(state, question_id, value):
    """Answer the current question; when the last is answered, build the plan."""
    question = current_question(state)
    if not question or question["id"] != question_id:
        raise ChatError("That is not the question waiting for an answer.")
    if question["type"] == "choice":
        allowed = [choice[0] if isinstance(choice, list) else choice for choice in question["choices"]]
        if value not in allowed:
            raise ChatError("Choose one of: " + ", ".join(allowed))
        state["answers"][question_id] = value
    elif question["type"] == "items":
        items = _items(value)
        if not items and not question.get("allow_skip"):
            raise ChatError("An answer is required for this question.")
        state["answers"][question_id] = items
    else:
        text = _clean(value, 500)
        if not text and not question.get("allow_skip"):
            raise ChatError("An answer is required for this question.")
        state["answers"][question_id] = text or state["answers"].get(question_id, "")
    state["question_index"] = state.get("question_index", 0) + 1
    if current_question(state) is None:
        state["plan"] = _plan(state)
        state["stage"] = "plan"
    state["updated_at"] = _now()
    return state


def _topic(text, limit=10):
    words = [word for word in re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower())
             if len(word) >= 3 and word not in STOP]
    return words[:limit]


def _plan(state):
    answers = state["answers"]
    framework = state.get("framework") or "pestel"
    config = FRAMEWORKS[framework]
    dimensions = [{"key": key, "label": label, "query": _query(state, key, cues), "cues": cues,
                   "category": category, "source_note": _source_note(category)}
                  for key, label, cues, category in config["dimensions"]]
    why = {
        "pestel": ("PESTEL organizes the external political, economic, social, technological, environmental and "
                   "legal evidence around the decision."),
        "swot": ("SWOT places the strengths and weaknesses you supply against the opportunities and threats the "
                 "external evidence supports."),
        "pestel_swot": ("PESTEL explains the external environment; SWOT then places your internal strengths and "
                        "weaknesses against the opportunities and threats that environment creates."),
    }[framework]
    misses = {
        "pestel": ("It does not assess internal capabilities, competitors, costs, financial feasibility or a "
                   "recommended action; those need other frameworks or methods."),
        "swot": ("It does not weigh or rank the factors, test financial feasibility, or choose an action; it is a "
                 "structured summary, not a strategy."),
        "pestel_swot": ("It still does not weigh or rank the options, test financial feasibility, or choose an "
                        "action; those need other frameworks or methods."),
    }[framework]
    output = {
        "pestel": "A PESTEL section with an introduction, six dimensions, implications (yours), limitations and one reference list.",
        "swot": "A SWOT section with your strengths and weaknesses, retrieved opportunities and threats, implications, limitations and one reference list.",
        "pestel_swot": ("A combined paper with the six PESTEL dimensions, your strengths and weaknesses, opportunities "
                        "and threats drawn from the accepted evidence, implications, limitations and one reference list."),
    }[framework]
    return {
        "framework": config["label"],
        "framework_id": framework,
        "why": why,
        "misses": misses,
        "decision": answers.get("decision") or state["brief"],
        "country": _country(answers.get("decision") or state["brief"]),
        "geography": answers.get("geography") or "Global",
        "period": answers.get("period") or "10",
        "style": answers.get("style") or "apa",
        "dimensions": dimensions,
        "internal": config["internal"],
        "swot": framework in ("swot", "pestel_swot"),
        "output": output,
        "checkpoints": ["Confirm this plan", "Review the retrieved evidence", "Review the drafted section"],
    }


def _query(state, key, cues):
    answers = state["answers"]
    geography = answers.get("geography") or "Global"
    geography = "" if geography == "Global" else geography
    country = _country(answers.get("decision") or state["brief"])
    topic = country or " ".join(_topic(answers.get("decision") or state["brief"]))
    if not topic:
        topic = _clean(state["brief"], 120)
    search = SEARCH_TERMS.get(key, " ".join(cues.split()[:3]))
    return _clean(" ".join(part for part in (topic, search, geography) if part), 300)


def _source_note(category):
    return {
        "legal": "primary legal and policy sources",
        "economic": "official economic data and research",
        "social": "official social data and survey research",
        None: "academic and official sources",
    }[category]


def confirm_plan(state):
    if state.get("stage") != "plan":
        raise ChatError("There is no plan waiting for confirmation.")
    state["stage"] = "research_ready"
    state["plan_confirmed_at"] = _now()
    state["updated_at"] = _now()
    return state


def _year_from(state):
    try:
        years = int(state["answers"].get("period", "10"))
    except (TypeError, ValueError):
        years = 10
    return datetime.datetime.now(datetime.timezone.utc).year - years if years > 0 else None


def _first_sentence(source):
    abstract = _clean(source.get("abstract") or source.get("description"), 1200)
    if not abstract:
        return ""
    return re.split(r"(?<=[.!?])\s+", abstract)[0][:500]


GEO_WORDS = {
    "US": {"united states", "u.s.", "america", "american", "federal", "washington"},
    "Europe": {"europe", "european", "eu", "eurozone", "uk", "britain", "germany", "france",
               "italy", "spain", "netherlands", "poland"},
    "Middle East": {"middle east", "gulf", "gcc", "saudi", "saudi arabia", "uae", "emirates",
                    "qatar", "kuwait", "bahrain", "oman", "israel", "turkey", "egypt", "jordan",
                    "lebanon", "iraq", "iran"},
    "China": {"china", "chinese", "prc", "beijing", "shanghai", "shenzhen"},
}

COUNTRIES = [
    ("Iran", ("iran", "iranian")),
    ("Saudi Arabia", ("saudi arabia", "saudi")),
    ("United Arab Emirates", ("united arab emirates", "uae", "emirates", "dubai", "abu dhabi")),
    ("Qatar", ("qatar", "qatari")),
    ("China", ("china", "chinese")),
    ("United States", ("united states", "u.s.", "american")),
    ("United Kingdom", ("united kingdom", "uk", "britain", "british")),
    ("Germany", ("germany", "german")),
    ("France", ("france", "french")),
    ("Israel", ("israel", "israeli")),
    ("Turkey", ("turkey", "turkish")),
    ("Egypt", ("egypt", "egyptian")),
]


def _country(text):
    lower = (text or "").lower()
    for name, aliases in COUNTRIES:
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", lower):
                return name
    return ""


def _geo_words(geography):
    return set(GEO_WORDS.get(geography, set()))


GENERIC_TOPIC = {"market", "markets", "business", "company", "firm", "firms", "entry", "enter",
                 "product", "products", "service", "services", "industry", "global", "international"}


def _specific_words(topic_words):
    out = set()
    for word in topic_words - GENERIC_TOPIC:
        out.add(word)
        if word.endswith("ian") and len(word) > 4:
            out.add(word[:-3])
    return out


def _relevance(item, topic_words, cue_words, geo_words, specific_words):
    text = _clean((item.get("title") or "") + " " + (item.get("abstract") or item.get("description") or ""), 2000)
    words = set(re.findall(r"[a-z][a-z0-9'-]+", text.lower()))
    lower = text.lower()
    geo_hits = sum(1 for phrase in geo_words if phrase in lower)
    cue_hits = len(cue_words & words)
    specific_hits = len(specific_words & words)
    score = 2 * cue_hits + 2 * (1 if geo_hits else 0) + specific_hits
    return score, geo_hits, cue_hits, specific_hits


def _research_one(state, dimension):
    from . import sources as source_finder
    started = time.perf_counter()
    query = dimension["query"]
    topic_words = set(_topic(state["answers"].get("decision") or state["brief"]))
    specific_words = _specific_words(topic_words)
    cue_words = set((dimension.get("cues") or "").split())
    geography = state["answers"].get("geography") or "Global"
    geo_words = _geo_words(geography)
    # Academic and curated-web retrieval are independent: run them together so a
    # slow web fallback cannot add its latency to the academic indexes.
    with ThreadPoolExecutor(max_workers=2) as pool:
        academic_future = pool.submit(source_finder.search_academic, query,
                                      databases=["openalex", "semanticscholar", "doaj"],
                                      limit=4, year_from=_year_from(state))
        web_future = pool.submit(source_finder.search_web, query,
                                 geography, 3, dimension.get("category"))
        results = academic_future.result()
        web = web_future.result()
    found = list(results.get("results") or [])
    for item in web.get("results") or []:
        found.append({"title": item.get("title"), "abstract": item.get("description"),
                      "authors": item.get("site"), "authors_list": [item.get("site")],
                      "year": None, "venue": item.get("site"), "doi": None, "url": item.get("url"),
                      "database": "vetted web", "item_type": "webpage", "kind": "web",
                      "retrieved_at": _now()})
    scored = []
    for item in found:
        score, geo_hits, cue_hits, specific_hits = _relevance(item, topic_words, cue_words, geo_words, specific_words)
        if cue_hits == 0:
            continue
        if specific_words and specific_hits == 0:
            continue
        if geography != "Global" and geo_hits == 0:
            continue
        if score >= 3:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    web_notice = web.get("notice")
    if not web_notice and web.get("provider"):
        web_notice = "Web search used " + str(web["provider"]) + "."
    return {"dimension": dimension, "found": [item for _score, item in scored],
            "errors": results.get("errors") or [], "skipped": results.get("skipped") or [],
            "notice": web_notice, "dropped": len(found) - len(scored),
            "elapsed": round(time.perf_counter() - started, 2),
            "academic_cached": bool(results.get("cached")),
            "web_cached": bool(web.get("cached")),
            "database_timings": results.get("timings") or {}}


def research(state):
    """Retrieve per-dimension evidence.  The plan must be confirmed first."""
    if state.get("stage") != "research_ready":
        raise ChatError("Confirm the plan before retrieving sources.")
    sources, evidence, gaps, notes = [], [], [], []
    seen_sources, seen_evidence = set(), set()
    errors, skipped, notices = [], set(), set()
    dropped = 0
    started = time.perf_counter()

    pool = ThreadPoolExecutor(max_workers=max(1, len(state["plan"]["dimensions"])))
    futures = {pool.submit(_research_one, state, dimension): dimension
               for dimension in state["plan"]["dimensions"]}
    done, pending = wait(futures, timeout=RESEARCH_DEADLINE)
    for future in pending:
        future.cancel()
    pool.shutdown(wait=False, cancel_futures=True)
    batches = []
    for future in done:
        try:
            batches.append(future.result())
        except Exception as error:
            dimension = futures[future]
            batches.append({"dimension": dimension, "found": [], "errors": [], "skipped": [],
                            "notice": "Research failed: " + str(error)[:160], "dropped": 0,
                            "elapsed": 0.0, "academic_cached": False, "web_cached": False,
                            "database_timings": {}})
    for future in pending:
        dimension = futures[future]
        batches.append({"dimension": dimension, "found": [], "errors": [], "skipped": [],
                        "notice": "Research timed out.", "dropped": 0,
                        "elapsed": RESEARCH_DEADLINE, "academic_cached": False,
                        "web_cached": False, "database_timings": {}, "timed_out": True})
    order = {key: index for index, (key, _label, _cues, _category) in enumerate(DIMENSIONS)}
    batches.sort(key=lambda batch: order.get(batch["dimension"]["key"], 99))
    timed_out = False
    for batch in batches:
        dimension = batch["dimension"]
        errors.extend({**error, "dimension": dimension["key"]} for error in batch["errors"])
        skipped.update(item.get("database") for item in batch["skipped"] if item.get("database"))
        dropped += batch["dropped"]
        if batch.get("timed_out"):
            timed_out = True
        if batch["notice"]:
            notices.add(batch["notice"])
        placed = 0
        for item in batch["found"]:
            quote = _first_sentence(item)
            key = (item.get("doi") or _clean(item.get("title"), 120).lower())
            if not quote or not key or key in seen_evidence:
                continue
            seen_evidence.add(key)
            if key not in seen_sources:
                seen_sources.add(key)
                source = dict(item)
                source["id"] = "S" + str(len(sources) + 1)
                sources.append(source)
            source_id = next(source["id"] for source in sources
                             if (source.get("doi") or _clean(source.get("title"), 120).lower()) == key)
            evidence.append({"id": "E" + str(len(evidence) + 1), "dimension": dimension["key"],
                             "claim": quote, "quote": quote, "source_id": source_id,
                             "status": "proposed"})
            placed += 1
            if placed >= 3:
                break
        if placed == 0:
            reason = ("research timed out before this dimension returned evidence"
                      if batch.get("timed_out")
                      else "no retrieved source supplied an abstract sentence for this dimension")
            gaps.append({"dimension": dimension["key"], "label": dimension["label"], "reason": reason})
    if timed_out:
        notes.append("Research stopped after %d seconds; incomplete dimensions are named as gaps." % RESEARCH_DEADLINE)
    if notices:
        notes.extend(sorted(notices))
    if dropped:
        notes.append(str(dropped) + " retrieved source(s) were dropped as off-topic for the decision.")
    if skipped:
        notes.append("Skipped until configured: " + ", ".join(sorted(skipped)))
    if errors:
        notes.append("Some databases were unavailable: " + ", ".join(sorted({error["database"] for error in errors})))
    timings = {"total_s": round(time.perf_counter() - started, 2),
               "dimensions": {batch["dimension"]["key"]: batch["elapsed"] for batch in batches},
               "academic_cached": sum(1 for batch in batches if batch["academic_cached"]),
               "web_cached": sum(1 for batch in batches if batch["web_cached"])}
    state.update({"sources": sources, "evidence": evidence, "gaps": gaps, "notes": notes,
                  "research_errors": errors, "researched_at": _now(), "stage": "evidence",
                  "timings": timings, "updated_at": _now()})
    return state


def _in_text(source, style):
    return writing.in_text(source, style)


def _reference(source, style):
    return writing.reference(source, style)


def _dimension_lines(dimension, evidence, by_id, style):
    key, label = dimension[0], dimension[1]
    items = [item for item in evidence if item["dimension"] == key]
    if not items:
        return ["No evidence was retrieved for this dimension. This is a gap, not a finding."]
    lines = [str(len(items)) + " retrieved source(s) were placed in this dimension."]
    for item in items:
        source = by_id.get(item["source_id"], {})
        lines.append("• " + _clean(item["quote"], 500) + " " + _in_text(source, style) + ".")
    return lines


def _internal_lines(answers, key, label):
    items = answers.get(key) or []
    if not items:
        return ["No " + label.lower() + " were supplied. This is a gap, not a finding."]
    return ["The following " + label.lower() + " were supplied by you:"] + ["• " + item for item in items]


POSITIVE = {"growth", "demand", "innovation", "investment", "digital", "expansion", "reform",
            "opportunity", "recovery", "young", "urban", "internet", "trade", "agreement"}
NEGATIVE = {"sanction", "restriction", "inflation", "risk", "crisis", "decline", "conflict",
            "unemployment", "shortage", "control", "blackout", "barrier", "pressure", "uncertainty"}


def _classify_external(evidence):
    """Map accepted external evidence to opportunities or threats by keyword."""
    buckets = {"opportunities": [], "threats": []}
    unclassified = 0
    for item in evidence:
        words = set(re.findall(r"[a-z][a-z0-9'-]+", _clean(item.get("quote"), 1200).lower()))
        positive, negative = len(words & POSITIVE), len(words & NEGATIVE)
        if positive > 2 * negative:
            buckets["opportunities"].append(item)
        elif negative > positive:
            buckets["threats"].append(item)
        else:
            unclassified += 1
    return buckets, unclassified


def _mapped_lines(items, by_id, style, label):
    if not items:
        return ["No accepted evidence was mapped to " + label.lower() + ". This is a gap, not a finding."]
    lines = [str(len(items)) + " accepted evidence item(s) were mapped here by keyword."]
    labels = {key: name for key, name, _cues, _category in DIMENSIONS}
    for item in items[:5]:
        source = by_id.get(item["source_id"], {})
        origin = labels.get(item["dimension"], item["dimension"])
        lines.append("• " + _clean(item["quote"], 500) + " " + _in_text(source, style)
                     + " [mapped from " + origin + "]")
    return lines


def draft(state, accepted_ids=None, implications="", style=None):
    """Compose the section from accepted evidence.  It invents nothing."""
    if state.get("stage") not in ("evidence", "evidence_reviewed", "draft"):
        raise ChatError("Retrieve the evidence before drafting.")
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    answers = state["answers"]
    framework = state.get("framework") or "pestel"
    label = FRAMEWORKS[framework]["label"]
    decision = answers.get("decision") or state["brief"]
    geography = answers.get("geography") or "Global"
    period = answers.get("period") or "10"
    period_text = "the last " + period + " years" if period not in ("0", "") else "all available years"
    sections = [("Introduction", [
        "This " + label + " analysis supports: " + _clean(decision, 500) + ".",
        "It examines " + geography + " over " + period_text + ".",
        "The external evidence below was retrieved from the source finder and is quoted from the sources; no fact "
        "or number was added by the system. Internal strengths and weaknesses are yours.",
    ])]
    if framework in ("pestel", "pestel_swot"):
        for dimension in DIMENSIONS:
            sections.append((dimension[1], _dimension_lines(dimension, evidence, by_id, style)))
    if framework in ("swot", "pestel_swot"):
        sections.append(("Strengths", _internal_lines(answers, "strengths", "Strengths")))
        sections.append(("Weaknesses", _internal_lines(answers, "weaknesses", "Weaknesses")))
    unclassified = 0
    if framework == "swot":
        for dimension in SWOT_DIMENSIONS:
            sections.append((dimension[1], _dimension_lines(dimension, evidence, by_id, style)))
    elif framework == "pestel_swot":
        buckets, unclassified = _classify_external(evidence)
        sections.append(("Opportunities", _mapped_lines(buckets["opportunities"], by_id, style, "Opportunities")))
        sections.append(("Threats", _mapped_lines(buckets["threats"], by_id, style, "Threats")))
    sections.append(("Implications (your analysis)", [
        _clean(implications, 1200) if implications else
        "Not supplied yet. The system does not infer a strategy from the evidence; add your implications before submitting."
    ]))
    gaps = [gap["label"] for gap in state.get("gaps") or []]
    limits = []
    if gaps:
        limits.append("No evidence was retrieved for: " + ", ".join(gaps) + ".")
    if framework in ("swot", "pestel_swot"):
        limits.append("Strengths and weaknesses are your input; the system did not verify them.")
    if framework == "pestel_swot":
        limits.append("Opportunities and threats are mapped from the accepted PESTEL evidence by keyword; review "
                      "the mapping before submitting.")
        if unclassified:
            limits.append(str(unclassified) + " accepted evidence item(s) could not be mapped to an opportunity or "
                                              "a threat and are not shown in the SWOT block.")
    limits += ["Placement uses keyword cues; a source can be relevant to more than one dimension.",
               "The section quotes sources; it does not verify the claims inside them.",
               "No financial figure is computed in this section.",
               state.get("notes")[0] if state.get("notes") else "The search may be incomplete."]
    sections.append(("Limitations", limits))
    references, seen = [], set()
    for source in state["sources"]:
        if source["id"] not in {item["source_id"] for item in evidence}:
            continue
        key = source.get("doi") or _clean(source.get("title"), 120).lower()
        if key in seen:
            continue
        seen.add(key)
        references.append(_reference(source, style))
    heading = "References" if style == "apa" else "Bibliography"
    sections.append((heading, references or ["No sources were used."]))
    state["draft"] = {"title": label + " analysis: " + _clean(decision, 180), "sections": sections,
                      "style": style, "framework": framework,
                      "accepted": sorted(accepted), "implications": _clean(implications, 1200),
                      "created_at": _now()}
    state["stage"] = "draft"
    state["updated_at"] = _now()
    return state


def docx_bytes(state):
    """The drafted section as a Word document (APA or Harvard)."""
    draft = state.get("draft")
    if not draft:
        raise ChatError("Draft the section before exporting it.")
    return docx.render_academic(draft["title"], draft["sections"], draft.get("style", "apa"))


def summary(state):
    """A compact view for the chat UI; no hidden reasoning, no invented text."""
    question = current_question(state)
    return {"id": state.get("id"), "stage": state.get("stage"), "brief": state.get("brief"),
            "answers": state.get("answers"), "question": question, "plan": state.get("plan"),
            "sources": state.get("sources"), "evidence": state.get("evidence"),
            "gaps": state.get("gaps"), "notes": state.get("notes"), "draft": state.get("draft"),
            "timings": state.get("timings"), "message": state.get("message")}
