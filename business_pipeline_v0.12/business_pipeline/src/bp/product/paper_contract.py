"""Paper contracts for the Home chat conductor.

A paper contract is the frozen agreement about what a paper is, who it serves,
what it must contain and what it must not contain. It is created before the
plan and frozen once the student approves it. Changes after freezing are
logged, not silent.

Rules this module keeps:
- pure functions over dicts, no I/O, no network, no clock except where a
  timestamp is explicitly supplied by the caller;
- no formula and no number: it validates and records, it does not compute;
- fail closed: an unknown archetype, family, length band or citation style is
  refused with the real options, never substituted;
- the contract is immutable once approved.
"""

import hashlib
import json

from . import paper_families

FORMAT = "bp-paper-contract/1"

IMMUTABLE_CONSTRAINTS = {
    "no_invented_evidence": True,
    "no_invented_numbers": True,
    "no_silent_substitution": True,
    "global_product": True,
    "no_template_text": True,
    "no_math_by_model": True,
}

REQUIRED_FIELDS = (
    "archetype",
    "thesis",
    "decision",
    "scope",
    "length",
    "style",
    "required_sections",
    "evidence_policy",
    "rubric",
    "deliverables",
)


def _normalise(text):
    return " ".join(str(text or "").split()).strip()


def make_contract(brief, archetype, thesis="", decision="", scope=None, length="mid",
                  style="apa", required_sections=None, evidence_policy=None,
                  computation_policy=None, chart_policy=None, rubric=None,
                  deliverables=None, audience="", approved=False, approved_at=None,
                  target_words=None, word_tolerance=None):
    """Build a paper contract dict. Nothing is frozen until approved is True."""
    scope = dict(scope or {})
    row = paper_families.archetype(archetype)
    if required_sections is None:
        required_sections = list(row.get("required_sections") or []) if row else []
    if evidence_policy is None:
        evidence_policy = row.get("evidence_policy") if row else None
    if computation_policy is None:
        computation_policy = row.get("computation_policy") if row else None
    if chart_policy is None:
        chart_policy = row.get("chart_policy") if row else None
    if rubric is None:
        rubric = {"source": "product", "coverage": []}
    if deliverables is None:
        deliverables = ["docx"]
    contract = {
        "format": FORMAT,
        "brief_hash": _brief_hash(brief),
        "archetype": str(archetype or "").strip().lower(),
        "family": row.get("family") if row else None,
        "thesis": {"text": _normalise(thesis), "source": "student" if _normalise(thesis) else "proposed"},
        "decision": _normalise(decision),
        "audience": _normalise(audience),
        "scope": {
            "object": _normalise(scope.get("object")),
            "period": _normalise(scope.get("period")),
            "geography": _normalise(scope.get("geography")),
            "currency": _normalise(scope.get("currency") or "USD") or "USD",
            "unit_of_analysis": _normalise(scope.get("unit_of_analysis")),
        },
        "length": str(length or "mid").strip().lower(),
        # A word count is the real length now; the band above is kept only for
        # older readers.  Both are recorded so a frozen contract cannot drift.
        "target_words": int(target_words) if target_words else None,
        "word_tolerance": float(word_tolerance) if word_tolerance is not None else None,
        "style": str(style or "apa").strip().lower(),
        "required_sections": [str(item).strip() for item in (required_sections or []) if str(item).strip()],
        "evidence_policy": evidence_policy,
        "computation_policy": computation_policy,
        "chart_policy": chart_policy,
        "rubric": rubric,
        "deliverables": [str(item).strip().lower() for item in (deliverables or []) if str(item).strip()],
        "constraints": dict(IMMUTABLE_CONSTRAINTS),
        "approved": bool(approved),
        "approved_at": approved_at,
    }
    contract["hash"] = contract_hash(contract)
    return contract


def _brief_hash(brief):
    raw = " ".join(str(brief or "").split()).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def contract_hash(contract):
    payload = {key: value for key, value in (contract or {}).items() if key not in ("hash", "approved_at")}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def validate_contract(contract):
    """Return a list of problems. An empty list means the contract is valid."""
    problems = []
    if not isinstance(contract, dict):
        return ["contract must be an object"]
    if contract.get("format") not in (None, FORMAT):
        problems.append("unsupported contract format " + str(contract.get("format")))
    for field in REQUIRED_FIELDS:
        if field not in contract:
            problems.append("missing field: " + field)
    archetype_key = str(contract.get("archetype") or "").strip().lower()
    problems.extend(paper_families.validate_archetype(archetype_key))
    row = paper_families.archetype(archetype_key)
    if row is not None:
        if contract.get("family") not in (None, row.get("family")):
            problems.append("family does not match archetype")
        if contract.get("required_sections") and not set(contract.get("required_sections") or []).issubset(set(row.get("required_sections") or [])):
            # required_sections may be a subset chosen by the student, but not outside the archetype
            extra = set(contract.get("required_sections") or []) - set(row.get("required_sections") or [])
            if extra:
                problems.append("required_sections outside the archetype: " + ", ".join(sorted(extra)))
    problems.extend(paper_families.validate_length_band(contract.get("length")))
    problems.extend(paper_families.validate_citation_style(contract.get("style")))
    if not isinstance(contract.get("thesis"), dict):
        problems.append("thesis must be an object")
    else:
        if not str(contract["thesis"].get("text") or "").strip() and contract.get("approved"):
            problems.append("an approved contract needs a thesis")
    if not str(contract.get("decision") or "").strip() and contract.get("approved"):
        problems.append("an approved contract needs a decision")
    if not isinstance(contract.get("scope"), dict):
        problems.append("scope must be an object")
    else:
        if not str(contract["scope"].get("currency") or "").strip():
            problems.append("scope.currency is required")
    if not isinstance(contract.get("required_sections"), list):
        problems.append("required_sections must be a list")
    if not isinstance(contract.get("rubric"), dict):
        problems.append("rubric must be an object")
    if not isinstance(contract.get("deliverables"), list) or not contract.get("deliverables"):
        problems.append("deliverables must be a non-empty list")
    if contract.get("constraints") != IMMUTABLE_CONSTRAINTS and contract.get("constraints") is not None:
        if contract.get("constraints") != IMMUTABLE_CONSTRAINTS:
            problems.append("constraints must equal the immutable constraints")
    if contract.get("approved") is True:
        if contract.get("hash") != contract_hash(contract):
            problems.append("approved contract hash does not match")
    return problems


def freeze_contract(contract, approved_at=None):
    """Return a frozen copy with approved=True and a fresh hash."""
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    problems = validate_contract(contract)
    if problems:
        raise ValueError("cannot freeze an invalid contract: " + "; ".join(problems))
    frozen = json.loads(json.dumps(contract))
    frozen["approved"] = True
    frozen["approved_at"] = approved_at
    frozen["constraints"] = dict(IMMUTABLE_CONSTRAINTS)
    frozen["hash"] = contract_hash(frozen)
    return frozen


def is_approved(contract):
    return isinstance(contract, dict) and contract.get("approved") is True and not validate_contract(contract)


def rehash(contract):
    if not isinstance(contract, dict):
        return None
    return contract_hash(contract)
