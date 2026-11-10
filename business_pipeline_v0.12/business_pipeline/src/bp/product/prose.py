"""Optional model-assisted prose for the paper (product layer).

The model is an editor, not a researcher.  It may rewrite the introduction,
add one linking sentence to a framework dimension, and rewrite the integration
and conclusion.  It may not add facts, sources, citations or numbers.  The
proposal is stored for the student to accept or discard; the deterministic draft
remains the fallback.
"""

import copy
import datetime
import json
import re
from . import providers

#: Kept for callers that read them; the live endpoint is resolved per call.
ENDPOINT = providers.OPENCODE_URL
DEFAULT_MODEL = providers.DEFAULT_MODEL_OPENCODE
META = ("(your analysis)", "not supplied yet", "further research is needed")
CITATION = re.compile(r"\([^()]{1,140}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")
NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
URL = re.compile(r"https?://|doi:", re.I)


class ProseError(ValueError):
    pass


class ProseRejected(ProseError):
    """The model wrote something the product refuses (a link, template text)."""


def available():
    """True when any gateway is configured: env, or a registered callable."""
    return providers.available()


def describe():
    """What would write right now, and why not when nothing would."""
    return providers.describe()


#: A suggested question may not carry a number, a source or a link: it is a prompt
#: for the student's own thinking, and a model that invents one is overruled.
BAD_SUGGESTION = re.compile(r"\d|https?://|doi:|www\.|et al\.|ibid|\{\{|\}\}", re.I)


def valid_suggestion(text):
    """Whether one model-proposed question may be shown to a student.

    A suggestion is advisory text beside the input.  It must be a question, short
    enough to read, and free of numbers, sources, links and template braces - any of
    which would turn authoring help into a fabricated fact.  Anything else is
    dropped and the framework's own authored question is shown instead.
    """
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text or len(text.split()) > 25 or not text.endswith("?"):
        return None
    if BAD_SUGGESTION.search(text):
        return None
    return text


def suggest_questions(framework, unit_label, unit_value, brief, blocks, limit=5, timeout=45):
    """Rephrase the authored questions in the student's own brief, or return {}.

    The model is a copy-editor here, exactly as it is for prose: it may rewrite a
    question this product already asks, and it may not add a fact, a number or a
    source.  Every returned string passes `valid_suggestion`; a block whose answer
    fails validation simply keeps the authored question.  No key, no problem: the
    caller gets an empty mapping and the deterministic advice is what the student
    sees.
    """
    wanted = [{"block": key, "question": question}
              for key, question in (blocks or {}).items() if question]
    if not wanted or not available():
        return {}
    payload = {
        "framework": framework,
        "unit": {"label": unit_label, "value": unit_value},
        "brief": str(brief or "")[:1200],
        "questions": wanted[:limit],
    }
    system = ("You rewrite questions for a student filling in a framework worksheet. "
              "Return only JSON: {\"questions\": [{\"block\": \"<key>\", \"question\": \"<one question>\"}]}. "
              "Keep each question under twenty-five words, end it with a question mark, and use the "
              "student's own words for the case. Never add a number, a statistic, a source, a citation, "
              "a link, a name or any fact the student did not supply. Never answer the question.")
    try:
        raw = _call([{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(payload)}], timeout=timeout,
                    max_tokens=800)
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except (ProseError, ValueError, TypeError):
        return {}
    out = {}
    for row in data.get("questions") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("block") or "").strip()
        clean = valid_suggestion(row.get("question"))
        if key in (blocks or {}) and clean:
            out[key] = clean
    return out


def model_id():
    return providers.model_id()


#: The portfolio commentary prompt.  It names the three things the product
#: refuses: a number that is not in the context, an invented fact, and advice.
PORTFOLIO_SYSTEM = (
    "You write one paragraph that interprets a portfolio snapshot for a student. "
    "Use only the figures, the selection criteria and the student's own words in the supplied context. "
    "Name no number that is not in that context, and do not turn a figure into a different one. "
    "Never give advice: no buy, no sell, no hold, no target price, no recommendation. "
    "Do not add a source, a citation, a link, a company fact, a forecast or a comparison the context does not hold. "
    "Return plain prose only: one paragraph, no heading, no bullet points, no markdown, "
    "and no mention of these instructions."
)


def propose_portfolio_paragraph(context, timeout=60):
    """One paragraph that interprets the supplied figures and names nothing else.

    The model is an editor here too: it may read the supplied context and write
    about it, and it may not add a figure, a fact or an advice.  The content
    rules that need the snapshot (the numbers, the recommendation) are applied
    by the caller, because only the caller knows what the record holds.

    Returns the paragraph as plain text.  A gateway failure raises
    :class:`ProseError`; text that breaks the generic rules raises
    :class:`ProseRejected`.
    """
    if not isinstance(context, dict) or not context:
        raise ProseError("the commentary context is empty")
    system = PORTFOLIO_SYSTEM
    user = json.dumps(context, ensure_ascii=False)
    raw = _call([{"role": "system", "content": system},
                 {"role": "user", "content": user}], timeout=timeout, max_tokens=900)
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    if not text:
        raise ProseError("the prose model returned no text")
    if URL.search(text):
        raise ProseRejected("the commentary introduced a link or DOI")
    if any(phrase in text.lower() for phrase in META):
        raise ProseRejected("the commentary contains template text")
    return text


def _call(messages, timeout=60, max_tokens=4000):
    try:
        return providers.complete(messages, timeout=timeout, max_tokens=max_tokens,
                                  temperature=0.2)
    except providers.GatewayError as error:
        raise ProseError(str(error))


def _payload(state, draft):
    outline = draft.get("outline") or []
    sections = []
    for item in outline:
        heading = item.get("heading")
        if heading in ("References", "Bibliography"):
            continue
        sections.append({"heading": heading, "level": item.get("level", 1),
                         "text": " ".join(item.get("lines") or [])})
    decision = (state.get("answers") or {}).get("decision") or state.get("brief") or ""
    return {"decision": decision, "thesis": draft.get("implications") or "",
            "sections": sections}


def _parse(raw):
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ProseError("The prose model did not return JSON.")
        try:
            data = json.loads(text[start:end + 1])
        except ValueError:
            raise ProseError("The prose model did not return valid JSON.")
    if not isinstance(data, dict):
        raise ProseError("The prose model returned the wrong shape.")
    return data


def _validate(proposal, draft):
    original = " ".join(" ".join(item.get("lines") or []) for item in draft.get("outline") or [])
    allowed_numbers = set(NUMBER.findall(original + " " + str(draft.get("implications") or "")))
    allowed_citations = set(CITATION.findall(original))
    texts = [proposal.get("introduction", ""), proposal.get("integration", ""),
             proposal.get("conclusion", "")]
    leads = proposal.get("leads") or {}
    if not isinstance(leads, dict):
        raise ProseError("The prose proposal has no usable section links.")
    texts.extend(str(value) for value in leads.values())
    for text in texts:
        text = str(text or "")
        if not text.strip():
            continue
        if len(text) > 1400:
            raise ProseError("A proposed section is too long.")
        if URL.search(text):
            raise ProseError("The prose proposal introduced a link or DOI.")
        if any(phrase in text.lower() for phrase in META):
            raise ProseError("The prose proposal contains template text.")
        if not set(NUMBER.findall(text)) <= allowed_numbers:
            raise ProseError("The prose proposal introduced a number that is not in the evidence.")
        if not set(CITATION.findall(text)) <= allowed_citations:
            raise ProseError("The prose proposal introduced a citation that is not in the evidence.")
    if not str(proposal.get("introduction", "")).strip():
        raise ProseError("The prose proposal has no introduction.")
    if not str(proposal.get("conclusion", "")).strip():
        raise ProseError("The prose proposal has no conclusion.")
    return proposal


def propose(state, draft):
    """Ask the model for a proposal.  Nothing is applied here."""
    payload = _payload(state, draft)
    system = ("You are an academic editor. Improve coherence without changing the evidence. "
              "Use only the facts, names, citations and numbers in the supplied sections and thesis. "
              "Never add a source, a citation, a number, a statistic or a recommendation. "
              "Keep quoted evidence verbatim; your additions are linking prose only. "
              "Do not begin a lead with 'This section', 'The introduction', 'The conclusion' or the section name; make a substantive link to the decision. "
              "Return ONLY JSON with this shape: "
              '{"introduction": "...", "leads": {"Section heading": "one linking sentence"}, '
              '"integration": "...", "conclusion": "..."}. '
              "The introduction must state the decision and the thesis. Each lead must connect that section to the "
              "decision without repeating its evidence. The integration must connect the external analysis to the "
              "internal position. The conclusion must answer the decision and use the thesis. "
              "Do not return headings, markdown, bullets, links or template text.")
    user = json.dumps(payload, ensure_ascii=False)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last = None
    for _attempt in range(2):
        raw = _call(messages)
        try:
            parsed = _parse(raw)
            proposal = {"introduction": str(parsed.get("introduction", "")).strip(),
                        "leads": {str(key): str(value).strip() for key, value in (parsed.get("leads") or {}).items()},
                        "integration": str(parsed.get("integration", "")).strip(),
                        "conclusion": str(parsed.get("conclusion", "")).strip(),
                        "model": model_id(),
                        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            return _validate(proposal, draft)
        except ProseError as error:
            last = error
            messages = messages[:2] + [
                {"role": "assistant", "content": str(raw)[:6000]},
                {"role": "user", "content": "That reply was not usable (%s). Return ONLY one valid JSON object with "
                                            "the keys introduction, leads, integration and conclusion. No markdown, no prose."
                                            % error}]
    raise last


def apply(draft, proposal):
    """Apply an accepted proposal; evidence paragraphs and references stay intact."""
    result = copy.deepcopy(draft)
    outline = result.get("outline") or []
    for item in outline:
        heading = item.get("heading")
        if heading == "Introduction" and proposal.get("introduction"):
            item["lines"] = [proposal["introduction"]]
        elif heading == "Integration of PESTEL and SWOT" and proposal.get("integration"):
            item["lines"] = [proposal["integration"]]
        elif heading == "Conclusion" and proposal.get("conclusion"):
            item["lines"] = [proposal["conclusion"]]
        elif heading in (proposal.get("leads") or {}) and item.get("level") == 2 and item.get("lines"):
            item["lines"] = [proposal["leads"][heading] + " " + item["lines"][0]] + item["lines"][1:]
    result["sections"] = [[item["heading"], item["lines"]] for item in outline]
    result["prose"] = {"model": proposal.get("model"), "applied_at": proposal.get("created_at")}
    return result
