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

from . import docx, framework_profiles, guard, paper, prose, retrieval, writing

NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
FRAMEWORK_WORDS = {"porter", "forces", "five", "swot", "pestel", "break", "even", "analysis", "pestel analysis"}
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
        return writing.reference(item, "apa")
    except Exception:
        return _clean(item.get("url") or item.get("doi") or item.get("title"), 300)


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


def _queries(block, context, region, country=""):
    """One query per phrase; the country is added once, never twice."""
    query_context = context or ""
    if country and country.lower() not in query_context.lower():
        query_context = " ".join(part for part in (country, query_context) if part)
    return [retrieval.build_query(phrase, query_context, region) for phrase in block.get("queries") or []]


def _one_block(profile, block, context, region, year_from, country=""):
    """Retrieve one dimension; failures are reported, never raised into the page."""
    try:
        found = retrieval.retrieve(
            key=block["key"], cues=block.get("cues"), queries=_queries(block, context, region, country),
            context=retrieval.context_words(context), geography=region, year_from=year_from,
            category=block.get("category"), gate=profile.get("gate"),
            sites=_sites(profile), providers=profile.get("providers"))
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


def complete(template, instruction, region=None, student_items=None, industry=None, country=None):
    """Fill a framework from the instruction.  Returns blocks with provenance."""
    if not framework_profiles.has(template):
        raise ValueError("Framework completion is not enabled for this worksheet. It runs for "
                         + " and ".join(sorted(p["label"] for p in framework_profiles.PROFILES.values()))
                         + ".")
    profile = framework_profiles.profile_for(template)
    instruction = _clean(instruction, 2000)
    if len(instruction) < 15:
        raise ValueError("Describe the case in at least one sentence.")
    ok, message = guard.computation_boundary(instruction, "management")
    if not ok:
        raise ValueError(message)
    declared = industry if (profile["unit"] or {}).get("field") == "industry" else country
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
    with ThreadPoolExecutor(max_workers=max(1, len(profile["blocks"]))) as pool:
        for block in profile["blocks"]:
            jobs[block["key"]] = pool.submit(_one_block, profile, block, context, region, year_from, country)
        done, pending = wait(jobs.values(), timeout=RESEARCH_DEADLINE)
        results, timed_out = [], set()
        for block in profile["blocks"]:
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
        for item in result["items"]:
            key = retrieval.key_of({"doi": None, "title": item.get("title")}) or item.get("text", "")[:80]
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
        if not items:
            gap = ("No evidence was found for this dimension before the research deadline."
                   if block["key"] in timed_out else
                   "No evidence was found for this dimension. It is returned as a gap, not filled.")
        else:
            gap = None
        if profile.get("assumption") == "probe" and gap:
            gap = gap + " " + _probe(profile, block)
        blocks.append({"key": block["key"], "label": block["label"], "items": items, "gap": gap,
                       "query": (found.get("queries") or [""])[0],
                       "dropped": found.get("dropped") or 0})
        if result["items"]:
            notes.append(block["label"] + ": " + str(len(result["items"])) + " sourced item(s).")
        if block["key"] in timed_out:
            notes.append(block["label"] + ": research timed out; returned as a gap.")
    gaps = [block["key"] for block in blocks if block["gap"] and not block["items"]]
    if gaps and profile.get("assumption") == "case":
        suggestions = _suggest(profile, gaps, instruction, unit, blocks)
        for block in blocks:
            if block["key"] in suggestions:
                block["items"] = block["items"] + [{"text": suggestions[block["key"]],
                                                    "provenance": "suggested", "source": ""}]
                block["gap"] = "No source was found; a case assumption is proposed for your review."
                notes.append(block["label"] + ": suggested case assumption.")
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()
    return {"format": "bp-framework-completion/1", "template": template,
            "framework": profile["label"], "unit": {k: v for k, v in unit.items() if k != "context"},
            "instruction": instruction, "country": _country(instruction), "region": region,
            "blocks": blocks, "notes": notes, "elapsed_s": round(elapsed, 2),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def _probe(profile, block):
    notes = (profile.get("notes") or {}).get(block["key"]) or {}
    probe = notes.get("probe") or block.get("probe") or "search for country-specific evidence on this dimension"
    return "What to look for: " + probe + "."


def _suggest(profile, gaps, instruction, unit, blocks):
    """One labelled case assumption per gap, only from the instruction.

    Only frameworks whose gaps can be answered analytically use this: an
    assumption about competitive dynamics is a reading of the case, while an
    assumption about a country would be an invented fact, which is why PESTEL
    returns a probe instead.
    """
    if not gaps or os.environ.get("BP_FRAMEWORK_SUGGEST", "1") == "0":
        return {}
    try:
        from . import prose as editor
        if not editor.available():
            return {}
        plural = (profile.get("voice") or {}).get("block_plural") or "dimensions"
        system = ("You are a business case analyst. For each " + plural.rstrip("s") + ", write one specific CASE "
                  "ASSUMPTION, in one or two sentences, that answers the question for this case, not a statement "
                  "that the " + plural.rstrip("s") + " is relevant. Use only the instruction and the named unit of "
                  "analysis. Do not add a source, citation, number, percentage, link or named fact not in the "
                  "instruction. Return ONLY a JSON object mapping the key to the sentence. No markdown.")
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
            out[key] = text
        return out
    except Exception:
        return {}


def missing(completion, profile=None):
    """The dimensions that carry neither evidence nor an acknowledged gap.

    A paper is refused while any dimension is unaccounted for: silence is not an
    empty finding.  Porter's worksheet can always offer an assumption, so a force
    without an item stays missing until the student accepts one; PESTEL's probe
    cannot invent a country fact, so an empty dimension must be ticked as a gap.
    """
    profile = profile or _profile((completion or {}).get("template"))
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
    "decision it frames. Write an introduction of {intro} words in {head_phrase} that closes with one sentence "
    "stating {thesis_question}. Write a case context of {context} words in one paragraph that defines the decision, "
    "the {unit_noun} and the evidence base in academic terms. Do not restate every item. Do not add facts, numbers, "
    "names, sources or citations beyond the items. Do not recommend a decision. Return only JSON: "
    "{\"introduction\":[\"...\"], \"thesis\":\"...\", \"context\":[\"...\"]}.")

SECTION_SYSTEM = (
    "You are writing one {block_singular} of a {name} analysis. The {block_singular} is {label}. Use only the case "
    "instruction, the thesis and the {block_plural} items. Write in formal academic English, third person, with no "
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
        "block_singular": (voice.get("block_plural") or "dimensions").rstrip("s"),
        "unit_noun": voice.get("unit_noun") or "market",
        "thesis_question": voice.get("thesis_question") or "whether the evidence supports the decision",
        "lens": voice.get("lens") or "the terms the framework supplies",
        "closing": voice.get("closing") or "identifies the strongest and the weakest evidenced dimension",
    }
    for key, value in slots.items():
        out = out.replace("{" + key + "}", value)
    return out


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
                ". Correct exactly that, keep the same evidence, and add no facts, names, numbers, sources or "
                "citations.")
    elif attempt:
        hint = (" The previous attempt exceeded the length or register limits; stay strictly within the word "
                "counts given and keep the academic register.")
    try:
        head = _ask(_system(HEAD_SYSTEM, profile, framework) + hint, base)
    except Exception as error:
        return _retry(result, style, attempt, "head: " + str(error)[:140])
    thesis = str((head or {}).get("thesis") or "").strip()
    if not thesis:
        return _retry(result, style, attempt, "no thesis")
    payload = dict(base, thesis=thesis)
    jobs = {"mid": lambda: _ask(_system(MID_SYSTEM, profile, framework) + hint, payload),
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
    try:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            running = {pool.submit(job): name for name, job in jobs.items()}
            for future in wait(running).done:
                answers[running[future]] = future.result()
    except Exception as error:
        return _retry(result, style, attempt, "call: " + str(error)[:140])
    merged = {"introduction": (head or {}).get("introduction") or [],
              "thesis": thesis,
              "context": (head or {}).get("context") or [],
              "lead": (framework.get("outline") or {}).get("lead") or "",
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
    problems = _problems(data, facts, instruction, length, keys,
                         allow=_allowed_names(framework, result))
    if problems:
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
    for block in profile.get("blocks") or []:
        words.update(re.findall(r"[a-z]{3,}", str(block.get("label") or "").lower()))
    unit = result.get("unit") or {}
    for token in re.findall(r"[a-z]{3,}", str(unit.get("value") or "").lower()):
        words.add(token)
    for value in (result.get("region"), result.get("country"), unit.get("region")):
        for token in REGION_WORDS.get(str(value or ""), ()):
            words.add(token)
    return words


def _problems(data, facts, instruction="", length="mid", keys=None, allow=None):
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
    if _words(data["lead"]) < 25:
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


def _title(instruction, profile=None):
    profile = profile or DEFAULT_PROFILE
    text = _clean(instruction, 160).strip()
    text = text.rstrip(" .,;:!?")
    if len(text) > 110:
        text = text[:110].rsplit(" ", 1)[0].rstrip(" .,;:!?")
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return profile["title_prefix"] + ": " + text


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
    strongest = labels[counts.index(max(counts))] if counts else "none of the dimensions"
    weakest = labels[counts.index(min(counts))] if counts else "none of the dimensions"
    plural = voice.get("block_plural") or "dimensions"
    singular = plural.rstrip("s")
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
             "that a " + singular + " for which no evidence is recorded cannot be treated as favourable. The "
             "conclusion returns to this proposition."),
        ],
        "context": [
            "The case concerns the following decision: " + instruction + ". " + (voice.get("context_frame") or ""),
            ("Evidence is limited to the accepted items. A " + singular + " without an accepted item is recorded as "
             "a gap, and an assumption is identified as such and is not treated as evidence. No aggregate score or "
             "recommendation is produced."),
        ],
        "lead": outline.get("lead") or "",
        "groups": {},
        "discussion": [
            ("The case supplies " + str(sourced + student + assumptions) + " accepted items across the " + plural +
             ": " + str(sourced) + " sourced items, " + str(student) + " items of the student's own evidence and " +
             str(assumptions) + " case assumptions. The " + plural + " carrying evidence are " + listed + ", while " +
             str(gaps) + " " + singular + "(s) are recorded as gaps."),
            ("Read together, the documented " + plural + " " + (voice.get("interaction") or "") + " A " + singular +
             " without evidence carries no weight in the assessment, because a gap is not a finding and cannot be "
             "read as either a strength or a weakness."),
        ],
        "implications": [
            ("The combined reading bears on the decision: the documented conditions must be answered by the "
             "proposed position, and the plan must show how each would be met. A " + singular + " that appears "
             "weak in the evidence is not thereby one that can be disregarded; it is a " + singular + " the case "
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
             "implies for the decision. The " + plural + " with evidence are " + listed + ", and " + strongest +
             " carries the most weight in the reading offered here, while " + weakest + " carries the least."),
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
            elif str(item.get("provenance") or "").lower() == "synthetic":
                lines.append("Illustrative: " + text)
            else:
                lines.append("Case assumption: " + text
                             if not text.lower().startswith("case assumption") else text)
        note = notes.get(key) or {}
        first = (" ".join(lines) if lines else
                 (block.get("gap") or "No evidence was found for this " + singular + ", so it is recorded as a gap."))
        if name == "short":
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
    sections = [paper.section("Introduction", 1, list(data["introduction"])),
                paper.section(outline.get("context") or "Case and context", 2, list(data["context"])),
                paper.section(outline.get("framework") or profile["label"], 1, [data["lead"]])]
    singular = ((profile.get("voice") or {}).get("block_plural") or "dimensions").rstrip("s")
    for block in blocks:
        key = block.get("key")
        paragraphs = list(data["groups"].get(key) or [])
        if not paragraphs:
            paragraphs = [block.get("gap") or "No evidence was found for this " + singular + "."]
        cites = citations.get(key) or []
        if cites and paragraphs:
            paragraphs[0] = paragraphs[0].rstrip() + " " + " ".join(cites)
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
    return sections


def draft(result, style="apa", version="draft", length="mid"):
    """A full paper from a completion result; no new facts, ratings or citations."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    blocks = result.get("blocks") or []
    model_used = False
    citations = {}
    if version == "full":
        generated = _model_sections(result, style, length=length)
        if not generated:
            raise ValueError("The model did not return a valid paper. Nothing was downloaded; choose Draft "
                             "(evidence-led) or try again.")
        data, citations = generated
        model_used = True
    else:
        data = _draft_data(result, length)
    profile = _profile(result.get("template"))
    # One shape, whichever path produced the prose: a payload written before the
    # profile existed may still say "forces" where the profile says "groups".
    data = _shape(data, [block["key"] for block in profile["blocks"]])
    sections = _sections(data, blocks, style, citations, result)
    words = sum(_words(" ".join(section.get("lines") or [])) for section in sections
                if section.get("heading") not in ("References", "Bibliography"))
    return {"title": _title(result.get("instruction"), profile), "sections": sections, "style": style,
            "version": version, "model_used": model_used, "words": words,
            "framework": profile["label"], "template": profile["template"],
            "length": _length_name(length), "length_label": _length(length)["label"],
            "length_range": _length(length)["range"],
            # The band is the Full paper's target.  A deterministic Draft reports
            # its own word count instead of claiming a length it does not reach.
            "length_applies_to": "full",
            "byline": [str(line).strip() for line in (result.get("byline") or []) if str(line or "").strip()]}


def draft_bytes(result, style="apa", report=None, version="draft", length="mid"):
    report = report or draft(result, style, version, length)
    return docx.render_academic(report["title"], report["sections"], report["style"],
                                byline=report.get("byline") or ())
