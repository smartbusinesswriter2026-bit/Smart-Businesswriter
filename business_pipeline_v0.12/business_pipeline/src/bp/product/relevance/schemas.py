"""RRA schemas: EvidenceRecord, CoverageRow, GapSpec, WatchItem.

Stdlib only.  Every record is a plain dict-friendly dataclass so it can be
serialised to JSONL without conversion.  Validation helpers reject records
that violate the strict gates (G1, G6, etc.).
"""
import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

TIER_T1 = "T1"
TIER_T2 = "T2"
TIER_T3 = "T3"
VALID_TIERS = (TIER_T1, TIER_T2, TIER_T3)

ACCESS_OPEN = "open"
ACCESS_PAYWALLED = "paywalled"
VALID_ACCESS = (ACCESS_OPEN, ACCESS_PAYWALLED)

STATUS_COVERED = "covered"
STATUS_PARTIAL = "partial"
STATUS_MISSING = "missing"
STATUS_PARKED = "parked"
STATUS_AT_RISK = "at-risk"
VALID_STATUSES = (STATUS_COVERED, STATUS_PARTIAL, STATUS_MISSING, STATUS_PARKED, STATUS_AT_RISK)

GAP_STATUS_OPEN = "open"
GAP_STATUS_APPROVED = "approved"
GAP_STATUS_REJECTED = "rejected"
GAP_STATUS_DEFERRED = "deferred"
VALID_GAP_STATUSES = (GAP_STATUS_OPEN, GAP_STATUS_APPROVED, GAP_STATUS_REJECTED, GAP_STATUS_DEFERRED)

PRIORITY_P0 = "P0"
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
VALID_PRIORITIES = (PRIORITY_P0, PRIORITY_P1, PRIORITY_P2)

EFFORT_S = "S"
EFFORT_M = "M"
EFFORT_L = "L"
VALID_EFFORTS = (EFFORT_S, EFFORT_M, EFFORT_L)

OWNER_COMPUTATION = "computation"
OWNER_DESIGN = "design"
VALID_OWNERS = (OWNER_COMPUTATION, OWNER_DESIGN)

# Categories from manual §8.3 (A–J)
CATEGORY_LABELS = {
    "A": "Analytical frameworks not in the conductor or profiles",
    "B": "Computation methods not in the method registry or capability list",
    "C": "Evidence sources missing or stale in the vetted registry",
    "D": "Paper types / archetypes not supported",
    "E": "Retrieval/verification techniques",
    "F": "Self-healing/repair techniques",
    "G": "Growth-loop design",
    "H": "Obsolescence",
    "I": "Accessibility/usability of the admin console and research workflow",
    "J": "Ethics/governance of AI-assisted academic writing",
}
VALID_CATEGORIES = tuple(CATEGORY_LABELS.keys())

REGION_LABELS = ("US", "Europe", "other")
VALID_REGIONS = REGION_LABELS

# Wikipedia and same-class domains — blocked at fetch time
BLOCKED_DOMAINS = frozenset({
    "wikipedia.org", "wikimedia.org", "wikiwand.com", "dbpedia.org",
    "fandom.com", "baidu.com", "about.com", "answers.com", "ehow.com",
    "quora.com", "reddit.com", "slideshare.net",
})

MAX_EXCERPT_WORDS = 25


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _sha256(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _word_count(text):
    return len(str(text or "").split())


def _is_blocked_domain(domain):
    domain = str(domain or "").lower().strip()
    for blocked in BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith("." + blocked):
            return True
    return False


# ── EvidenceRecord ─────────────────────────────────────────────────────────────

@dataclass
class EvidenceRecord:
    """One retrieved source with provenance.  G1 requires url, timestamp, sha256, tier, excerpt."""
    id: str = ""
    run_id: str = ""
    school_or_body: str = ""
    region: str = "other"
    program_level: str = ""
    source_url: str = ""
    retrieved_at_utc: str = ""
    sha256: str = ""
    tier: str = TIER_T3
    access: str = ACCESS_OPEN
    published_or_effective_date: str = ""
    excerpt: str = ""
    topic_tags: List[str] = field(default_factory=list)
    #: The taxonomy topics whose name appears on the page.  This is a derived
    #: fact, not a copy of the page: it is what lets the control set see a
    #: page whose 25-word excerpt does not happen to carry the name.
    mentions: List[str] = field(default_factory=list)
    taxonomy_family: str = ""
    superseded_by: Optional[str] = None

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError):
            return None

    def validate(self):
        """Return (ok, reason).  G1: url, timestamp, sha256, tier, excerpt all present."""
        if not self.source_url or not str(self.source_url).strip():
            return False, "source_url is required (G1)"
        if not self.retrieved_at_utc or not str(self.retrieved_at_utc).strip():
            return False, "retrieved_at_utc is required (G1)"
        if not self.sha256 or not str(self.sha256).strip():
            return False, "sha256 is required (G1)"
        if self.tier not in VALID_TIERS:
            return False, "tier must be T1/T2/T3 (G1)"
        if not self.excerpt or not str(self.excerpt).strip():
            return False, "excerpt is required (G1)"
        if _word_count(self.excerpt) > MAX_EXCERPT_WORDS:
            return False, "excerpt must be under %d words (G1)" % MAX_EXCERPT_WORDS
        if self.region not in VALID_REGIONS:
            return False, "region must be US/Europe/other"
        if self.access not in VALID_ACCESS:
            return False, "access must be open/paywalled"
        # Blocked domain check
        domain = self._domain()
        if domain and _is_blocked_domain(domain):
            return False, "blocked domain (Wikipedia and same-class sources are never retrieved)"
        return True, ""

    def _domain(self):
        url = str(self.source_url or "").lower()
        # strip scheme
        for prefix in ("https://", "http://"):
            if url.startswith(prefix):
                url = url[len(prefix):]
        # take host
        host = url.split("/")[0].split("?")[0]
        # strip port
        host = host.split(":")[0]
        return host

    def make_id(self):
        """Generate a stable id from url + retrieved_at."""
        raw = "%s|%s" % (self.source_url, self.retrieved_at_utc)
        return "ev_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ── CoverageRow ─────────────────────────────────────────────────────────────────

@dataclass
class CoverageRow:
    """Coverage of one taxonomy item against the pipeline's catalogue."""
    taxonomy_item: str = ""
    pipeline_artefact_id: str = ""   # capability/profile/method id, if any
    status: str = STATUS_MISSING
    evidence_ids: List[str] = field(default_factory=list)
    independent_t1_count: int = 0
    last_verified_at: str = ""
    skeptic_notes: str = ""
    #: The page type the evidence must come from: "course_catalogue" for a
    #: framework, "core_list" for a subject, "standards" for a standard.
    evidence_page: str = ""
    #: The taxonomy item's own id, so the control set can match on it.
    taxonomy_id: str = ""

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError):
            return None

    def validate(self):
        if not self.taxonomy_item or not str(self.taxonomy_item).strip():
            return False, "taxonomy_item is required"
        if self.status not in VALID_STATUSES:
            return False, "status must be covered/partial/missing/parked/at-risk"
        if self.independent_t1_count < 0:
            return False, "independent_t1_count must be >= 0"
        return True, ""


# ── GapSpec ─────────────────────────────────────────────────────────────────────

@dataclass
class GapSpec:
    """A proposed capability gap that survived the skeptic stage."""
    id: str = ""
    title: str = ""
    category: str = ""
    general_capability_statement: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    why_not_already_covered: str = ""
    authoritative_reference: str = ""
    owner_lane: str = OWNER_DESIGN
    proposed_acceptance_criterion: str = ""
    trap_test_idea: str = ""
    constraint_check: Dict[str, bool] = field(default_factory=dict)
    priority: str = PRIORITY_P2
    effort: str = EFFORT_M
    risk: str = ""
    status: str = GAP_STATUS_OPEN
    created_at: str = ""

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError):
            return None

    def validate_strict(self):
        """Strict checklist G1–G7.  Return (ok, list_of_failures)."""
        failures = []
        # G1: evidence meets tier rule (at least one T1 or T2)
        if not self.evidence_ids:
            failures.append("G1: no evidence ids")
        # G2: not a duplicate — checked externally (catalogue snapshot)
        # G3: every non-negotiable passes
        if self.constraint_check:
            for rule, passed in self.constraint_check.items():
                if not passed:
                    failures.append("G3: non-negotiable violated: %s" % rule)
        else:
            failures.append("G3: constraint_check is empty (must evaluate all non-negotiables)")
        # G4: acceptance criterion testable
        if not self.proposed_acceptance_criterion or not str(self.proposed_acceptance_criterion).strip():
            failures.append("G4: proposed_acceptance_criterion is empty")
        # G5: authoritative reference exists (standard/statute/published method, not a blog)
        if not self.authoritative_reference or not str(self.authoritative_reference).strip():
            failures.append("G5: authoritative_reference is empty")
        # G6: jurisdiction-neutral
        # (checked by content review; flag if empty)
        if not self.general_capability_statement or not str(self.general_capability_statement).strip():
            failures.append("G6: general_capability_statement is empty")
        # G7: owner lane named
        if self.owner_lane not in VALID_OWNERS:
            failures.append("G7: owner_lane must be computation or design")
        # Category valid
        if self.category not in VALID_CATEGORIES:
            failures.append("category must be A–J")
        # Priority valid
        if self.priority not in VALID_PRIORITIES:
            failures.append("priority must be P0/P1/P2")
        # Effort valid
        if self.effort not in VALID_EFFORTS:
            failures.append("effort must be S/M/L")
        # Title
        if not self.title or not str(self.title).strip():
            failures.append("title is required")
        # Status
        if self.status not in VALID_GAP_STATUSES:
            failures.append("status must be open/approved/rejected/deferred")
        return (len(failures) == 0, failures)

    def make_id(self):
        raw = "%s|%s" % (self.title, self.category)
        return "gap_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ── WatchItem ──────────────────────────────────────────────────────────────────

@dataclass
class WatchItem:
    """An obsolescence watch item with a trigger date."""
    item: str = ""
    why_at_risk: str = ""
    signal_to_monitor: str = ""
    trigger_date: str = ""
    migration_path: str = ""
    last_checked_at: str = ""
    status: str = "watching"

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError):
            return None

    def validate(self):
        if not self.item or not str(self.item).strip():
            return False, "item is required"
        if not self.why_at_risk or not str(self.why_at_risk).strip():
            return False, "why_at_risk is required"
        return True, ""


# ── Run record ─────────────────────────────────────────────────────────────────

@dataclass
class RunRecord:
    """One RRA sweep run."""
    run_id: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: str = "running"  # running, completed, failed, stopped
    school_count: int = 0
    url_count: int = 0
    evidence_count: int = 0
    coverage_count: int = 0
    gap_count: int = 0
    watchitem_count: int = 0
    cost_tokens: int = 0
    notes: str = ""
    #: The measurement's own control result: {held, total, ratio, passed, ...}
    controls: Dict[str, Any] = field(default_factory=dict)
    #: How many candidate gaps were withheld because the controls failed.
    withheld_count: int = 0

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError):
            return None


def make_run_id():
    raw = _now_iso()
    return "run_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def validate_tier_rule(evidence_ids, evidence_lookup):
    """G1 tier rule: at least one T1 or T2 evidence in the list."""
    for eid in (evidence_ids or []):
        rec = evidence_lookup.get(eid)
        if rec and getattr(rec, "tier", None) in (TIER_T1, TIER_T2):
            return True
    return False
