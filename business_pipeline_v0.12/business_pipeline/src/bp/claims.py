"""Claim licensing: wording ceilings checked mechanically (section 7). Illustrative phrase lists."""
import re
CAUSAL_TRIGGERS = [r"\bif we\b", r"\beffect of\b", r"\bimpact of\b", r"\bcauses?\b", r"\bleads? to\b", r"\bdrives?\b"]
CEILING = {
    "descriptive": None,  # any plain statement of reconciled data
    "associational": {"forbid": CAUSAL_TRIGGERS},
    "predictive": {"forbid": CAUSAL_TRIGGERS},
    "causal": {"forbid": [r"\bcertain(ly)?\b", r"\bproves?\b", r"\bdefinitely\b"]},
    "prescriptive": {"forbid": [r"\bcertain(ly)?\b", r"\bproves?\b"]},
}
def auto_type(sentence: str, declared: str) -> str:
    """Intervention language is flagged causal regardless of declared type."""
    if declared in ("descriptive", "associational", "predictive") and any(
        re.search(p, sentence, re.I) for p in CAUSAL_TRIGGERS[:3]): return "causal"
    return declared
def license_check(sentence: str, declared: str) -> list[str]:
    rule = CEILING.get(declared); problems = []
    if auto_type(sentence, declared) != declared: problems.append(f"intervention language: typed as causal, declared {declared}")
    for p in (rule or {}).get("forbid", []):
        if re.search(p, sentence, re.I): problems.append(f"wording exceeds ceiling for {declared}: /{p}/")
    return problems
