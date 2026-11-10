"""Full guide-section papers for the plan profiles (product layer).

The business plan has a deterministic writer of its own.  Marketing plans,
feasibility studies and project proposals are guide-shaped documents whose
narrative depends on the brief; this module fills each guide section from the
brief and the working notes already produced by the profile builder.  Numbers
are checked against the supplied material, and a failed section falls back to
the deterministic note for that heading; nothing is invented.
"""

import json
import re

from . import prose

PROFILES = {
    "marketing_plan": {
        "audience": "marketing plan",
        "sections": (
            "Executive Summary",
            "Situation Analysis",
            "Marketing Objectives and KPIs",
            "Target Market: Segmentation, Targeting and Positioning",
            "Marketing Strategy and Marketing Mix",
            "Channel Plan and Tactics",
            "Content and Campaign Plan",
            "Funnel, Conversion and Retention",
            "Budget and Projections",
            "Measurement and Optimization",
            "Implementation Timeline and Responsibilities",
            "Risks and Contingencies",
            "Appendices",
        ),
    },
    "feasibility_study": {
        "audience": "feasibility study",
        "sections": (
            "Executive Summary",
            "Introduction and Project Background",
            "Market Feasibility",
            "Technical Feasibility",
            "Management and Organizational Feasibility",
            "Legal and Regulatory Feasibility",
            "Financial Feasibility",
            "Socio-Economic Feasibility",
            "Environmental Feasibility",
            "Risk Assessment",
            "Alternatives Analysis",
            "Conclusion and Recommendation",
            "Appendices",
        ),
    },
    "project_proposal": {
        "audience": "project proposal",
        "sections": (
            "Executive Summary",
            "Background and Needs Statement",
            "Goal, Objectives and Theory of Change",
            "Project Description",
            "Implementation Plan",
            "Organizational Capacity and Project Team",
            "Budget and Financial Plan",
            "Monitoring, Evaluation and Learning",
            "Risk Management and Assumptions",
            "Sustainability and Exit Strategy",
            "Expected Results and Benefits",
            "Conclusion and Request",
            "Appendices",
        ),
    },
}

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
URL = re.compile(r"https?://|doi:|www\.", re.I)
BAD = ("not stated", "does not state", "not provided", "does not include",
       "not include", "not reported", "no data", "not supplied",
       "wikipedia", "as an ai", "i cannot", "lorem ipsum")


def _canon(token):
    return str(token).replace(",", "")


def _allowed(text):
    return {_canon(token) for token in NUMBER.findall(text)}


def _lines(raw):
    try:
        data = prose._parse(raw)
    except prose.ProseError:
        text = str(raw or "").strip()
        if not text or "{" in text or "}" in text:
            raise
        return [part.strip() for part in text.split("\n\n") if part.strip()]
    lines = data.get("lines") if isinstance(data, dict) else None
    if isinstance(lines, str):
        lines = [lines]
    if not isinstance(lines, list):
        raise ValueError("the model returned no lines")
    return [re.sub(r"\s+", " ", str(line or "")).strip() for line in lines if str(line or "").strip()]


def _check(lines, allowed):
    text = " ".join(lines)
    if URL.search(text):
        raise ValueError("link")
    lowered = text.lower()
    if any(phrase in lowered for phrase in BAD):
        raise ValueError("template or blocked text")
    for token in NUMBER.findall(text):
        if _canon(token) not in allowed:
            raise ValueError("new number " + token)
    words = len(text.split())
    if words < 60:
        raise ValueError("too short")
    if words > 900:
        raise ValueError("too long")
    return lines


def write(state, brief, profile, timeout=90):
    """The guide sections, or None when the model is not configured."""
    spec = PROFILES.get(profile)
    if not spec or not prose.available():
        return None
    notes = (state.get("draft") or {}).get("sections") or []
    material = {
        "brief": str(brief or ""),
        "facts": state.get("profile_facts") or {},
        "working_notes": [[str(heading), [str(line) for line in lines]]
                          for heading, lines in notes],
        "computations": {key: {k: str(v) for k, v in (value.get("result") or {}).items()
                               if not isinstance(v, (dict, list))}
                         for key, value in (state.get("computations") or {}).items()
                         if isinstance(value, dict) and value.get("ok")},
    }
    allowed = _allowed(json.dumps(material, ensure_ascii=False, default=str))
    sections = []
    for title in spec["sections"]:
        try:
            raw = prose._call([
                {"role": "system", "content":
                    "You write one section of a " + spec["audience"] + ". Use only the facts and "
                    "numbers in the supplied material. Never invent a statistic, source, competitor, "
                    "name, date or number. Where the material is thin, write the plan in general terms "
                    "without inventing a specific figure or name; never write a gap sentence such as "
                    "'not stated', 'not provided' or 'not reported'. Do not print these instructions "
                    "or a heading. Return only JSON: "
                    "{\"lines\": [\"paragraph\", \"another paragraph\"]}."},
                {"role": "user", "content": json.dumps({"section": title, "material": material},
                                                       ensure_ascii=False)}],
                timeout=timeout, max_tokens=1400)
            lines = _check(_lines(raw), allowed)
            sections.append([title, lines])
        except Exception:
            fallback = next((lines for heading, lines in notes if heading == title), [])
            if fallback:
                sections.append([title, [str(line) for line in fallback]])
    if not sections:
        return None
    title = (state.get("draft") or {}).get("title") or spec["audience"].title()
    return {
        "title": title,
        "sections": sections,
        "style": (state.get("draft") or {}).get("style") or "apa",
        "accepted": [],
        "missing": [],
        "words": sum(len(line.split()) for _heading, lines in sections for line in lines),
    }
