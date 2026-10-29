"""Keep the chat on the right subject and the right kind of question.

Every conductor path calls this before it plans.  It is deliberately simple and
auditable: a subject vocabulary, a computation boundary, and a small industry
vocabulary for Five Forces.  It refuses with a reason the student can act on; it
never rewrites the brief.
"""

import re

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
    if any(hint in lower for hint in COMPUTATION) and subject not in ("accounting", "finance"):
        return False, ("This looks like an accounting or finance computation. Use the Accounting or Finance "
                       "shelf; the management chat would not answer it.")
    return True, None


def subject_fit(text, subject="management"):
    """Return (ok, message).  The message names the subject the brief belongs to."""
    ok, message = computation_boundary(text, subject)
    if not ok:
        return ok, message
    lower = (text or "").lower()
    words = _words(text)
    subject = subject or "management"
    if subject == "management":
        if not (words & SUBJECT_HINTS["management"]) and not any(word in lower for word in
                                                                 ("business", "company", "market", "industry",
                                                                  "five forces", "porter")):
            return False, ("This does not look like a management or strategy instruction. Name the firm, market, "
                           "industry or decision you want to analyse.")
        return True, None
    if words & SUBJECT_HINTS.get(subject, set()):
        return True, None
    for name, hints in SUBJECT_HINTS.items():
        if name != subject and words & hints:
            return False, ("This instruction looks like " + name.replace("-", " ") + ", not " +
                           subject.replace("-", " ") + ". Choose the matching subject in the rail.")
    return False, ("This does not name a " + subject.replace("-", " ") + " question. Add the concept, method "
                   "or decision you want to work on.")


def five_forces_fit(text, industry=""):
    """Five Forces needs an industry or market, not only a company and a country."""
    industry = (industry or industry_in(text) or "").strip()
    if not industry:
        return False, ("Porter's Five Forces analyses an industry, not a company on its own. Name the industry or "
                       "market (for example smartphones, grocery retail or banking).")
    return True, industry
