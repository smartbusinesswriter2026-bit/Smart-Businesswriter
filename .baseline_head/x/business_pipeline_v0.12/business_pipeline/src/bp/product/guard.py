"""Keep the chat on the right subject and the right kind of question.

Every conductor path calls this before it plans.  It is deliberately simple and
auditable: a subject vocabulary, a computation boundary, and a small industry
vocabulary for Five Forces.  It refuses with a reason the student can act on; it
never rewrites the brief.
"""

import re

SUBJECT_OPEN = "any"


def is_open(subject):
    return (subject or "").strip().lower() == SUBJECT_OPEN
SUBJECT_HINTS = {

    "management": {"strategy", "market", "industry", "competition", "entry", "acquisition", "firm",
                   "company", "business", "organization", "organisation", "growth", "expansion",
                   "product", "service", "competitive", "positioning", "merger", "stakeholder", "acquire",
                   "acquisition", "entry", "industry"},
    "finance": {"npv", "irr", "valuation", "cash", "flow", "capital", "portfolio", "bond", "stock",
                "dividend", "loan", "interest", "wacc", "capm", "risk", "return", "investment",
                "financing", "debt", "equity", "option", "leverage", "budget"},
    "accounting": {"ledger", "journal", "trial", "balance", "debit", "credit", "depreciation",
                   "reconciliation", "reconcile", "statement", "invoice", "payable", "receivable",
                   "amortization", "amortisation", "variance", "inventory", "asset", "liability"},
    "economics": {"inflation", "gdp", "demand", "supply", "elasticity", "unemployment", "monetary",
                  "fiscal", "trade", "tariff", "market", "price", "wage", "tax", "growth", "policy"},
    "marketing": {"customer", "brand", "segmentation", "campaign", "advertising", "pricing",
                  "channel", "consumer", "promotion", "market", "product", "loyalty", "positioning"},
    "operations": {"process", "capacity", "inventory", "quality", "lean", "sigma", "scheduling",
                   "supply", "chain", "logistics", "throughput", "bottleneck", "forecast", "stock"},
    "project-management": {"project", "wbs", "gantt", "risk", "stakeholder", "raci", "earned",
                           "milestone", "schedule", "charter", "deliverable", "critical", "path"},
    "entrepreneurship": {"startup", "venture", "business", "model", "funding", "pitch", "founder",
                         "market", "customer", "product", "growth", "investor"},
    "people": {"employee", "recruitment", "performance", "compensation", "culture", "hrm",
               "training", "turnover", "engagement", "leadership", "team"},
    "research": {"hypothesis", "regression", "survey", "sample", "validity", "reliability",
                 "variable", "correlation", "experiment", "qualitative", "quantitative", "test"},
}

COMPUTATION = {"journal entry", "ledger", "trial balance", "balance sheet", "income statement", "npv",
               "irr", "depreciation", "variance", "amortization", "amortisation",
               "calculate", "compute", "reconcile", "debit", "credit"}

INDUSTRIES = {
    "smartphone", "smartphones", "consumer electronics", "electronics", "grocery", "groceries",
    "retail", "supermarket", "e-commerce", "ecommerce", "online retail", "banking", "bank",
    "insurance", "airline", "airlines", "aviation", "automotive", "car", "electric vehicle",
    "energy", "oil", "gas", "telecom", "telecommunications", "software", "cloud", "semiconductor",
    "healthcare", "hospital", "pharmaceutical", "education", "university", "food delivery",
    "logistics", "supply chain", "manufacturing", "agriculture", "tourism", "hospitality",
}


def _words(text):
    return set(re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower()))


def industry_in(text):
    lower = (text or "").lower()
    return next((item for item in sorted(INDUSTRIES, key=len, reverse=True) if item in lower), "")


def computation_boundary(text, subject="management"):
    """Refuse a computation brief on a framework shelf, with the shelf to use.

    The boundary is separate from the subject vocabulary: a worksheet is already
    on the right shelf, but a trial balance still cannot be completed by PESTEL.
    """
    lower = (text or "").lower()
    if is_open(subject):
        return True, None
    if any(hint in lower for hint in COMPUTATION) and subject not in ("accounting", "finance"):
        return False, ("This looks like an accounting or finance computation. Use the Accounting or Finance "
                       "shelf; the management chat would not answer it.")
    return True, None


#: What each shelf is called in a refusal.  The label is the shelf's own name, so the
#: student is told which shelf the brief belongs to rather than that it is "invalid".
SUBJECT_LABELS = {
    "management": "management or strategy",
    "finance": "finance",
    "accounting": "accounting",
    "economics": "economics",
    "marketing": "marketing",
    "operations": "operations",
    "supply-chain": "supply chain",
    "project-management": "project management",
    "entrepreneurship": "entrepreneurship",
    "people": "people and organisation",
    "research": "research or statistics",
}

#: Naming one of these is the stronger statement of intent: the student has said what
#: the paper is, so the shelf vocabulary does not re-litigate it.  This is the same
#: carve-out `chat.start` already makes for break-even and VRIO.
FRAMEWORK_WORDS = ("five forces", "value chain", "pestel", "swot", "vrio", "ansoff",
                   "break-even", "breakeven", "break even", "business model canvas",
                   "lean canvas", "business plan", "feasibility study", "marketing plan",
                   "project proposal")


def subject_fit(text, subject="management"):
    """Return (ok, message): the brief must look like work for **this** shelf.

    A shelf is a promise about the kind of question it answers, so a brief that belongs
    to another shelf is refused here with the shelf to use instead — that is the
    "no silent framework substitution" rule at the routing layer (B-180).  The check is
    deliberately generous: one recognised word is enough, and naming a framework (or
    opening the composer on "any") bypasses it entirely, because over-refusing a real
    brief is its own defect.
    """
    if not subject or is_open(subject):
        return True, None
    hints = SUBJECT_HINTS.get(subject)
    if not hints:
        # A shelf the vocabulary does not describe cannot be checked from words alone.
        return True, None
    lower = (text or "").lower()
    if any(word in lower for word in FRAMEWORK_WORDS):
        return True, None
    if _words(text) & set(hints):
        return True, None
    label = SUBJECT_LABELS.get(subject, subject)
    # "an entrepreneurship instruction", not "a entrepreneurship": the shelf's own name
    # decides the article, and the label is what the student reads.
    article = "an" if str(label)[:1].lower() in "aeiou" else "a"
    return False, ("This does not look like %s %s instruction. Name the %s question, or open "
                   "the shelf the brief belongs to." % (article, label, label))


def five_forces_fit(text, industry=""):
    """Five Forces needs an industry or market, not only a company and a country."""
    industry = (industry or industry_in(text) or "").strip()
    if not industry:
        return False, ("Porter's Five Forces analyses an industry, not a company on its own. Name the industry or "
                       "market (for example smartphones, grocery retail or banking).")
    return True, industry
def detect_subject(text):
    """Score the brief's words against every subject's hints.

    Returns (subject_id, cue_word) for the best match, or ("", "") when
    nothing matches.  Ties are broken by the fixed key order of
    SUBJECT_HINTS.
    """
    words = _words(text)
    lower = (text or "").lower()
    best_id = ""
    best_cue = ""
    best_score = 0
    for subject_id, hints in SUBJECT_HINTS.items():
        matched = words & set(hints)
        score = len(matched)
        if score > best_score:
            best_score = score
            best_id = subject_id
            positions = []
            for hint in matched:
                idx = lower.find(hint)
                positions.append((idx if idx >= 0 else len(lower), hint))
            positions.sort()
            best_cue = positions[0][1] if positions else ""
    if best_score <= 0:
        return "", ""
    return best_id, best_cue

