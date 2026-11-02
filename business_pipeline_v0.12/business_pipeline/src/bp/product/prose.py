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
import os
import re
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("BP_PROSE_URL") or "https://opencode.ai/inference/go/openai/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4.1-flash"
META = ("(your analysis)", "not supplied yet", "further research is needed")
CITATION = re.compile(r"\([^()]{1,140}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")
NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
URL = re.compile(r"https?://|doi:", re.I)


class ProseError(ValueError):
    pass


def available():
    return bool(os.environ.get("BP_OPENGO_API_KEY"))


def model_id():
    return os.environ.get("BP_PROSE_MODEL") or os.environ.get("BP_LLM_MODEL", DEFAULT_MODEL)


def _call(messages, timeout=60):
    key = os.environ.get("BP_OPENGO_API_KEY")
    if not key:
        raise ProseError("Model-assisted prose is not configured: no OpenCode Go key.")
    payload = {"model": model_id(), "messages": messages, "temperature": 0.2, "max_tokens": 4000}
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "smart-business-writer/1.0", "x-opencode-session": "bp-prose"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ProseError("The prose model answered HTTP %s." % error.code)
    except Exception as error:
        raise ProseError("The prose model could not be reached: " + str(error)[:160])
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ProseError("The prose model returned an unreadable response.")


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
