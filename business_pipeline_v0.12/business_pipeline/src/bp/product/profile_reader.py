"""Read the labelled facts a marketing, feasibility or project brief states.

The model writer already reads the whole brief.  This reader gives it the same
facts in a stable shape, so the sections agree on the name, place, offer,
customers, problem, objectives and budget.  It reads only explicit labels and
never infers a value.
"""

import re

FIELDS = {
    "name": (r"(?:business|company|project|plan)\s+name", r"^name"),
    "location": (r"location", r"site", r"address"),
    "product": (r"(?:product|service|offer)s?", r"what it sells"),
    "customers": (r"(?:target\s+)?customers?", r"target market", r"beneficiaries"),
    "problem": (r"problem", r"need", r"issue"),
    "objectives": (r"objectives?", r"goals?"),
    "budget": (r"(?:total\s+)?budget", r"funding required", r"project cost"),
    "timeline": (r"timeline", r"duration", r"implementation period"),
    "channels": (r"channels?", r"promotion", r"distribution"),
    "tax": (r"(?:income |corporate |effective )?tax(?:\s+rate)?",),
    "project_type": (r"project type", r"type of project", r"business type"),
    "capacity": (r"capacity", r"output", r"scale"),
    "equipment": (r"equipment", r"machinery", r"assets"),
    "permits": (r"permits?", r"licen[cs]es?", r"registrations?"),
    "alternatives": (r"alternatives?", r"options?"),
    "beneficiaries": (r"beneficiaries", r"participants", r"beneficiary group"),
    "activities": (r"activities", r"work plan", r"implementation"),
    "duration": (r"duration", r"implementation period"),
}


def _label(text, patterns):
    for pattern in patterns:
        match = re.search(pattern + r"\s*[:\-]\s*([^\n.;]{2,160})", text, re.I | re.M)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


PROSE = {
    "name": (r"(?:called|named)\s+([A-Z][\w&'\- ]{2,60})",
             r"(?:business|company|project)\s+(?:name\s+)?is\s+([A-Z][\w&'\- ]{2,60})"),
    "location": (r"(?:located|based)\s+in\s+([^.,;\n]{2,60})",),
    "product": (r"(?:sells|offers|provides)\s+([^.;\n]{3,100})",),
    "customers": (r"(?:customers?|target market|beneficiaries)\s+(?:are|is|include)\s+([^.;\n]{3,120})",),
    "problem": (r"(?:problem|need)\s+(?:is|addresses)\s+([^.;\n]{3,120})",),
    "objectives": (r"(?:aims?|objectives?)\s+(?:to|are)\s+([^.;\n]{3,120})",),
    "budget": (r"budget\s+(?:of|is)\s*([\d,]+)",),
    "channels": (r"(?:through|channels?)\s+([^.;\n]{3,100})",),
}


def _prose(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
    return ""


def read(brief):
    text = str(brief or "")
    facts = {}
    for key, patterns in FIELDS.items():
        value = _label(text, patterns) or _prose(text, PROSE.get(key, ()))
        if value:
            facts[key] = value
    return facts
