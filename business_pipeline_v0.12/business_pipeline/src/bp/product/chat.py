"""Deterministic framework conductor (product layer).

This first conductor covers PESTEL and SWOT, separately or together.  It guides
a student with a fixed question bank, a confirmed plan, per-dimension source
retrieval, an evidence review and an APA/Harvard section.

It uses no model.  Every external evidence item is a sentence from a retrieved
source, with the source recorded; a dimension with no retrieved evidence is
reported as a gap.  Strengths and weaknesses are supplied by the student and are
never inferred.  The chat never writes a fact, a source or a number of its own.
"""

import dataclasses
import datetime
import os
import re
import time
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor, wait

from . import audit as audit_mod, capabilities, council, docx, framework_profiles, guard, instruction_reading, matrix, paper, paper_contract, paper_families, prose, retrieval, rubric as rubric_reader, verify, writing

FORMAT = "bp-chat/1"

# Citation numbering for numbered styles (Vancouver, IEEE, OSCOLA, ...).  Set only
# while a draft is being composed; never a source of truth outside that scope.
_CITATION_NUMBERS = None

ExportBlocked = paper.ExportBlocked

#: A whole research pass may not outlast this, even if one provider hangs.
RESEARCH_DEADLINE = float(os.environ.get("BP_RESEARCH_DEADLINE", "20"))

DIMENSIONS = [
    ("political", "Political", "government policy sanctions regulation trade stability", "legal"),
    ("economic", "Economic", "economic growth inflation interest exchange demand", "economic"),
    ("social", "Social", "demographic population youth internet social cultural labour consumer behaviour", "social"),
    ("technological", "Technological", "technology innovation digital automation research", None),
    ("environmental", "Environmental", "climate environment sustainability emissions energy", None),
    ("legal", "Legal", "law legislation sanctions compliance export control regulation", "legal"),
]

SWOT_DIMENSIONS = [
    ("opportunities", "Opportunities", "growth demand consumer innovation investment digital expansion reform", None),
    ("threats", "Threats", "sanctions embargo regulation competition inflation risk restriction conflict", "legal"),
]

FIVE_DIMENSIONS = [
    ("rivalry", "Industry rivalry", "rivalry competitor competition market share price war", None),
    ("entrants", "Threat of new entrants", "entry entrant startup capital barrier licence license", None),
    ("substitutes", "Threat of substitutes", "substitute alternative switching", None),
    ("buyers", "Buyer power", "buyer customer client bargaining concentration", "economic"),
    ("suppliers", "Supplier power", "supplier vendor input procurement bargaining", "economic"),
]

#: The nine activities of Porter's value chain: five primary, four support.
VALUE_DIMENSIONS = [
    ("inbound", "Inbound logistics", "inbound logistics supplier receiving storage inventory handling", None),
    ("operations", "Operations", "operations production manufacturing assembly process quality", None),
    ("outbound", "Outbound logistics", "outbound distribution delivery warehousing order fulfilment", None),
    ("marketing", "Marketing and sales", "marketing sales branding pricing channel advertising customers", "economic"),
    ("service", "Service", "service support warranty installation maintenance after-sales", None),
    ("procurement", "Procurement", "procurement purchasing sourcing supplier contracts", "economic"),
    ("technology", "Technology development", "technology research development innovation automation digital", None),
    ("human", "Human resource management", "human resources training recruitment skills labour", "social"),
    ("infrastructure", "Firm infrastructure", "management finance planning legal quality governance", "legal"),
]

#: The four growth options of the Ansoff matrix.
ANSOFF_DIMENSIONS = [
    ("penetration", "Market penetration", "market share promotion pricing existing customers frequency", "economic"),
    ("development", "Market development", "new market export new segment expansion distribution", "economic"),
    ("product", "Product development", "new product innovation research development feature", None),
    ("diversification", "Diversification", "diversification new business acquisition unrelated", None),
]

GENERIC_DIMENSIONS = [
    ("evidence", "Evidence", "market industry evidence", None),
]

FRAMEWORKS = {
    "none": {"label": "No framework", "dimensions": GENERIC_DIMENSIONS, "internal": False},
    "pestel": {"label": "PESTEL", "dimensions": DIMENSIONS, "internal": False},
    "swot": {"label": "SWOT", "dimensions": SWOT_DIMENSIONS, "internal": True},
    "pestel_swot": {"label": "PESTEL + SWOT", "dimensions": DIMENSIONS, "internal": True},
    "five_forces": {"label": "Five Forces", "dimensions": FIVE_DIMENSIONS, "internal": False},
    "five_forces_breakeven": {"label": "Five Forces + Break-even", "dimensions": FIVE_DIMENSIONS, "internal": False},
    "value_chain": {"label": "Value Chain", "dimensions": VALUE_DIMENSIONS, "internal": False},
    "ansoff": {"label": "Ansoff Growth Matrix", "dimensions": ANSOFF_DIMENSIONS, "internal": False},
    "vrio": {"label": "VRIO", "dimensions": [], "internal": True, "evidence": False,
             "inputs": ["resources", "valuable", "rare", "costly", "organized"]},
    "breakeven": {"label": "Break-even", "dimensions": [], "internal": False, "evidence": False},
}

QUESTIONS = [
    {"id": "decision", "prompt": "What decision or question should this analysis support?",
     "why": "The analysis should serve a decision, not sit on its own.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "geography", "prompt": "Which market or region should the evidence cover?",
     "why": "Political, economic and legal evidence is country-specific.",
     "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"},
    {"id": "period", "prompt": "How recent should the evidence be?",
     "why": "A current analysis needs dated evidence, not undated generalities.",
     "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                   ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"},
    {"id": "style", "prompt": "Which citation style should the section use?",
     "why": "The paper has to match the style your course requires.",
     "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"},
]

INTERNAL_QUESTIONS = [
    {"id": "decision", "prompt": "What decision or question should this SWOT analysis support?",
     "why": "The matrix should serve a decision, not sit on its own.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "strengths", "prompt": "What strengths does the case give you? Separate items with semicolons.",
     "why": "Strengths are internal facts about the firm; the system will not invent them.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "weaknesses", "prompt": "What weaknesses does the case give you? Separate items with semicolons.",
     "why": "Weaknesses are internal facts about the firm; the system will not invent them.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "geography", "prompt": "Which market or region should the external evidence cover?",
     "why": "Opportunities and threats are country-specific.",
     "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"},
    {"id": "period", "prompt": "How recent should the external evidence be?",
     "why": "A current analysis needs dated evidence, not undated generalities.",
     "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                   ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"},
    {"id": "style", "prompt": "Which citation style should the section use?",
     "why": "The paper has to match the style your course requires.",
     "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"},
]

FIVE_QUESTIONS = [
    {"id": "decision", "prompt": "What decision should this Five Forces analysis support?",
     "why": "The analysis should serve a decision, not sit on its own.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "industry", "prompt": "Which industry or market should be analysed?",
     "why": "Five Forces analyses an industry, not a company on its own.",
     "type": "text", "default": ""},
    {"id": "geography", "prompt": "Which market or region should the evidence cover?",
     "why": "Industry conditions are country-specific.",
     "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"},
    {"id": "period", "prompt": "How recent should the evidence be?",
     "why": "A current analysis needs dated evidence.",
     "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                   ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"},
    {"id": "style", "prompt": "Which citation style should the paper use?",
     "why": "The paper has to match the course requirement.",
     "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"},
    {"id": "fixed", "prompt": "What is the declared total fixed cost for the break-even calculation?",
     "why": "Break-even needs a declared fixed cost; the system will not invent one.",
     "type": "number", "default": ""},
    {"id": "price", "prompt": "What is the declared price per unit?",
     "why": "The contribution margin depends on the selling price.",
     "type": "number", "default": ""},
    {"id": "variable", "prompt": "What is the declared variable cost per unit?",
     "why": "The contribution margin depends on the variable cost.",
     "type": "number", "default": ""},
    {"id": "expected", "prompt": "What is the expected sales volume? (optional)",
     "why": "Expected volume gives the margin of safety.",
     "type": "number", "allow_skip": True, "default": ""},
]

_GEOGRAPHY = {"id": "geography", "prompt": "Which market or region should the evidence cover?",
              "why": "Value-chain and growth evidence is country-specific.",
              "type": "choice", "choices": ["Global", "US", "Europe", "Middle East", "China"], "default": "Global"}
_PERIOD = {"id": "period", "prompt": "How recent should the evidence be?",
           "why": "A current analysis needs dated evidence, not undated generalities.",
           "type": "choice", "choices": [["2", "Last 2 years"], ["5", "Last 5 years"],
                                         ["10", "Last 10 years"], ["0", "No limit"]], "default": "10"}
_STYLE = {"id": "style", "prompt": "Which citation style should the paper use?",
          "why": "The paper has to match the style your course requires.",
          "type": "choice", "choices": [["apa", "APA 7"], ["harvard", "Harvard"]], "default": "apa"}

VALUE_QUESTIONS = [
    {"id": "decision", "prompt": "What decision should this value-chain analysis support?",
     "why": "The analysis should serve a decision, not describe the firm for its own sake.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "firm", "prompt": "Which firm or offer is being analysed?",
     "why": "A value chain belongs to one firm and one offer.",
     "type": "text", "default": ""},
    _GEOGRAPHY, _PERIOD, _STYLE,
]

ANSOFF_QUESTIONS = [
    {"id": "decision", "prompt": "What growth decision should this Ansoff analysis support?",
     "why": "The matrix is a way to compare growth options, not a forecast.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "firm", "prompt": "Which firm or product line is considering growth?",
     "why": "The four options are defined relative to a current product and market.",
     "type": "text", "default": ""},
    _GEOGRAPHY, _PERIOD, _STYLE,
]

VRIO_QUESTIONS = [
    {"id": "decision", "prompt": "What decision should this VRIO analysis support?",
     "why": "A resource is only an advantage relative to a decision.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "resources", "prompt": "Which resources or capabilities are you assessing? Separate items with semicolons.",
     "why": "The resources are facts about the firm; the system will not invent them.",
     "type": "items", "default": ""},
    {"id": "valuable", "prompt": "Which of them pass the valuable test, and why? One item per resource.",
     "why": "Value is your judgment; the system records it, it does not make it.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "rare", "prompt": "Which of them pass the rare test, and why? One item per resource.",
     "why": "Rarity is a claim about competitors that you must support.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "costly", "prompt": "Which of them are costly to imitate, and why? One item per resource.",
     "why": "Imitation cost is your judgment, not a measured quantity.",
     "type": "items", "allow_skip": True, "default": ""},
    {"id": "organized", "prompt": "Which of them is the firm organised to exploit, and why? One item per resource.",
     "why": "An advantage needs the organisation to capture it.",
     "type": "items", "allow_skip": True, "default": ""},
    _STYLE,
]

BREAKEVEN_QUESTIONS = [
    {"id": "decision", "prompt": "What decision should this break-even analysis support?",
     "why": "The calculation should answer a stated question.",
     "type": "text", "allow_skip": True, "default": ""},
    {"id": "fixed", "prompt": "What is the declared total fixed cost?",
     "why": "Break-even needs a declared fixed cost; the system will not invent one.",
     "type": "number", "default": ""},
    {"id": "price", "prompt": "What is the declared price per unit?",
     "why": "The contribution margin depends on the selling price.",
     "type": "number", "default": ""},
    {"id": "variable", "prompt": "What is the declared variable cost per unit?",
     "why": "The contribution margin depends on the variable cost.",
     "type": "number", "default": ""},
    {"id": "expected", "prompt": "What is the expected sales volume? (optional)",
     "why": "Expected volume gives the margin of safety.",
     "type": "number", "allow_skip": True, "default": ""},
    _STYLE,
]

#: Length is offered as three options, because a case does not always need a long
#: paper.  Each band has a range and a target the draft writes to; a number in the
#: brief or the box is read into the same bands, so the vocabulary never drifts.
LENGTH_BANDS = (
    ("short", "Short", 600, 1200, 600),
    ("mid", "Mid", 1200, 2500, 1200),
    ("long", "Long", 2500, 5000, 2500),
)
LENGTH_BY_KEY = {band[0]: band for band in LENGTH_BANDS}
MIN_WORDS = LENGTH_BANDS[0][2]
MAX_WORDS = LENGTH_BANDS[-1][3]
SHORT_WORDS = LENGTH_BANDS[0][4]
MID_WORDS = LENGTH_BANDS[1][4]
LONG_WORDS = LENGTH_BANDS[2][4]
#: At or above this a draft carries the full-report sections; at or above the
#: second the deep sections (per-dimension reading, appendix) join them.
MID_FLOOR = LENGTH_BANDS[1][2]
LONG_FLOOR = LENGTH_BANDS[2][2]

_WORD_TARGET = re.compile(r"\b(\d[\d,]*)\s*(?:-|to\s+)?\s*words?\b", re.I)


def parse_word_target(text):
    """The word count a brief asks for, or None.  It never guesses a number."""
    match = _WORD_TARGET.search(str(text or ""))
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


_LENGTH_NAME = re.compile(r"\b(short|mid|long)(?:[ -](?:length|report|paper))\b", re.I)


def parse_length_name(text):
    """The option a brief names ("mid-length", "long report"), or None."""
    match = _LENGTH_NAME.search(str(text or ""))
    return match.group(1).lower() if match else None


def length_band(words):
    """Which of the three options a word count belongs to."""
    words = int(words or 0)
    if words >= LONG_FLOOR:
        return "long"
    if words >= MID_FLOOR:
        return "mid"
    return "short"


def band_label(words):
    band = length_band(words or (SHORT_WORDS if not words else 0))
    return LENGTH_BY_KEY[band][1]


def band_target(key):
    """The default target for a named option, or 0 for an unknown key."""
    band = LENGTH_BY_KEY.get(str(key or "").strip().lower())
    return band[4] if band else 0


def check_word_target(value):
    """Read a requested length as an option name or a number, or 0 for short.

    Names ("short", "mid", "long") resolve to that option's target.  A number is
    accepted only inside the offered range, so the system never promises a paper
    it cannot write without padding.
    """
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    named = band_target(text)
    if named:
        return named
    match = re.search(r"\d+", text)
    if not match:
        raise ChatError("Choose short, mid or long, or give a word count between %d and %d."
                        % (MIN_WORDS, MAX_WORDS))
    words = int(match.group(0))
    if words < MIN_WORDS:
        raise ChatError("A paper below %d words cannot carry the framework, the evidence and the computation "
                        "properly. Choose the short option (%d-%d words) or a longer count."
                        % (MIN_WORDS, LENGTH_BANDS[0][2], LENGTH_BANDS[0][3]))
    if words > MAX_WORDS:
        raise ChatError("A report longer than %d words is more than one case can support; ask for %d or fewer."
                        % (MAX_WORDS, MAX_WORDS))
    return words


def target_words(state):
    """The requested length in words, or 0 for the short version."""
    return int((state.get("answers") or {}).get("length") or 0)


def _word_count(sections):
    """The body words of a draft, counted the way a course counts them."""
    total = 0
    for item in sections or []:
        for line in item.get("lines") or []:
            total += len(str(line or "").split())
    return total


FRAMEWORK_QUESTIONS = {"none": QUESTIONS, "pestel": QUESTIONS, "swot": INTERNAL_QUESTIONS, "pestel_swot": INTERNAL_QUESTIONS,
                       "five_forces": [q for q in FIVE_QUESTIONS if q["id"] != "expected"],
                       "five_forces_breakeven": FIVE_QUESTIONS,
                       "value_chain": VALUE_QUESTIONS, "ansoff": ANSOFF_QUESTIONS,
                       "vrio": VRIO_QUESTIONS, "breakeven": BREAKEVEN_QUESTIONS}
# ---------- business-plan profile (B-121) ----------
#: A paper profile is not a framework.  It composes sections of four kinds:
#: student input, evidence, computation and integration.  The same frozen core
#: runs the computations; this profile only decides which blocks a plan needs.
PROFILE_BUSINESS_PLAN = "business_plan"

# ---------- feasibility-study profile (B-122) ----------
PROFILE_FEASIBILITY_STUDY = "feasibility_study"

# ---------- marketing-plan profile (B-123) ----------
PROFILE_MARKETING_PLAN = "marketing_plan"

# ---------- project-proposal profile (B-124) ----------
PROFILE_PROJECT_PROPOSAL = "project_proposal"

PROJECT_LEVELS = {"shs": "Senior high school", "college": "College"}
PROJECT_MODES = {"strict": "Project-proposal convention", "open": "Open composition"}

PROJECT_DIMENSIONS = [
    ("problem", "Problem and Need", "problem need issue gap", None),
    ("objectives", "Objectives", "objective goal outcome", None),
    ("activities", "Activities and Work Plan", "activity task schedule", None),
    ("budget", "Budget", "budget cost resource", "economic"),
    ("monitoring", "Monitoring and Evaluation", "indicator baseline target", None),
]

PROJECT_FIELDS = {
    "project_description": [
        ("project_title", "the project title", "text", True),
        ("problem_statement", "the problem statement", "text", True),
        ("objectives", "the project objectives", "text", True),
        ("location", "where the project is located", "text", True),
        ("proponents", "who is proposing the project", "text", True),
    ],
    "work_plan": [
        ("activities", "the project activities", "text", True),
        ("timeline", "the project timeline", "text", True),
        ("deliverables", "the expected deliverables", "text", False),
    ],
    "budget": [
        ("total_budget", "the total budget", "text", True),
        ("budget_breakdown", "the budget breakdown", "text", True),
        ("funding_source", "the funding source", "text", False),
    ],
    "monitoring_evaluation": [
        ("indicators", "the success indicators", "text", True),
        ("baseline", "the baseline data", "text", False),
        ("targets", "the targets", "text", True),
    ],
    "risk": [
        ("risks", "at least one named risk", "items", True),
    ],
}

PROJECT_SECTIONS = [
    {"key": "executive_summary", "heading": "Executive Summary", "kind": "integration", "level": 1},
    {"key": "project_description", "heading": "Project Description", "kind": "input", "level": 1},
    {"key": "work_plan", "heading": "Work Plan and Timeline", "kind": "input", "level": 1},
    {"key": "budget", "heading": "Budget", "kind": "computation", "level": 1},
    {"key": "monitoring_evaluation", "heading": "Monitoring and Evaluation", "kind": "input", "level": 1},
    {"key": "risk", "heading": "Risk Analysis", "kind": "integration", "level": 1},
    {"key": "conclusion", "heading": "Conclusion", "kind": "integration", "level": 1},
    {"key": "references", "heading": "References", "kind": "references", "level": 1},
]

PROJECT_OPTIONAL = {"risk"}

PROJECT_BLOCKS = [
    {"key": "frommarket", "label": "Market Size and Target Sales", "method": "sales_from_market",
     "section": "budget", "level": "shs", "required": True,
     "what": "Target revenue and units from your declared market size, share and price."},
    {"key": "breakeven", "label": "Break-even", "method": "breakeven",
     "section": "budget", "level": "shs", "required": True,
     "what": "The quantity and revenue at which the declared price covers the declared costs."},
]

PROJECT_DIMENSIONS_LIST = [
    ("problem", "Problem and Need", "problem need issue gap", None),
    ("objectives", "Objectives", "objective goal outcome", None),
    ("activities", "Activities and Work Plan", "activity task schedule", None),
    ("budget", "Budget", "budget cost resource", "economic"),
    ("monitoring", "Monitoring and Evaluation", "indicator baseline target", None),
]


MARKETING_LEVELS = {"shs": "Senior high school", "college": "College"}
MARKETING_MODES = {"strict": "Marketing-plan convention", "open": "Open composition"}

MARKETING_DIMENSIONS = [
    ("audience", "Target Audience", "customer segment demographics psychographics", "social"),
    ("positioning", "Positioning", "positioning value proposition differentiation", None),
    ("channels", "Channels", "channels media digital traditional", None),
    ("budget", "Budget and ROI", "budget spend cac ltv roas", "economic"),
]

MARKETING_FIELDS = {
    "business_context": [
        ("business_name", "the business name", "text", True),
        ("product", "what the business sells", "text", True),
        ("customers", "who the customers are", "text", True),
        ("location", "where the business operates", "text", True),
    ],
    "audience_positioning": [
        ("target_audience", "the target audience", "text", True),
        ("positioning_statement", "the positioning statement", "text", True),
        ("value_proposition", "the value proposition", "text", True),
    ],
    "channels_tactics": [
        ("channels", "the marketing channels", "text", True),
        ("tactics", "the marketing tactics", "text", True),
        ("content_plan", "the content plan", "text", False),
    ],
    "budget_measurement": [
        ("budget", "the marketing budget", "text", True),
        ("kpis", "the key performance indicators", "text", True),
        ("measurement_plan", "the measurement plan", "text", False),
    ],
    "risk": [
        ("risks", "at least one named risk", "items", True),
    ],
}

MARKETING_SECTIONS = [
    {"key": "executive_summary", "heading": "Executive Summary", "kind": "integration", "level": 1},
    {"key": "business_context", "heading": "Business Context", "kind": "input", "level": 1},
    {"key": "audience_positioning", "heading": "Audience and Positioning", "kind": "input", "level": 1},
    {"key": "channels_tactics", "heading": "Channels and Tactics", "kind": "input", "level": 1},
    {"key": "budget_measurement", "heading": "Budget and Measurement", "kind": "computation", "level": 1},
    {"key": "risk", "heading": "Risk Analysis", "kind": "integration", "level": 1},
    {"key": "conclusion", "heading": "Conclusion", "kind": "integration", "level": 1},
    {"key": "references", "heading": "References", "kind": "references", "level": 1},
]

MARKETING_OPTIONAL = {"risk"}

MARKETING_BLOCKS = [
    {"key": "frommarket", "label": "Market Size and Target Sales", "method": "sales_from_market",
     "section": "budget_measurement", "level": "shs", "required": True,
     "what": "Target revenue and units from your declared market size, share and price."},
    {"key": "breakeven", "label": "Break-even", "method": "breakeven",
     "section": "budget_measurement", "level": "shs", "required": True,
     "what": "The quantity and revenue at which the declared price covers the declared costs."},
]

MARKETING_DIMENSIONS_LIST = [
    ("audience", "Target Audience", "customer segment demographics psychographics", "social"),
    ("positioning", "Positioning", "positioning value proposition differentiation", None),
    ("channels", "Channels", "channels media digital traditional", None),
    ("budget", "Budget and ROI", "budget spend cac ltv roas", "economic"),
]


FEASIBILITY_LEVELS = {"shs": "Senior high school", "college": "College"}
FEASIBILITY_MODES = {"strict": "Feasibility-study convention", "open": "Open composition"}

FEASIBILITY_DIMENSIONS = [
    ("market", "Market Feasibility", "market demand size growth competition", "economic"),
    ("technical", "Technical Feasibility", "technology equipment capacity process", None),
    ("management", "Management Feasibility", "team skills organisation capacity", None),
    ("legal", "Legal and Regulatory Feasibility", "permits licenses regulation compliance", "legal"),
    ("financial", "Financial Feasibility", "cost revenue funding cash flow", "economic"),
]

FEASIBILITY_FIELDS = {
    "project_description": [
        ("project_name", "the project name", "text", True),
        ("project_description", "what the project is about", "text", True),
        ("location", "where the project is located", "text", True),
        ("proponents", "who is proposing the project", "text", True),
    ],
    "market_feasibility": [
        ("target_market", "the target market", "text", True),
        ("demand_estimate", "the estimated demand", "text", True),
        ("competitors", "the competitors", "text", False),
    ],
    "technical_feasibility": [
        ("technology", "the technology or method", "text", True),
        ("capacity", "the capacity needed", "text", True),
        ("inputs", "the inputs or resources needed", "text", False),
    ],
    "management_feasibility": [
        ("team", "the management team", "text", True),
        ("skills", "the skills available", "text", False),
    ],
    "legal_feasibility": [
        ("permits", "the permits or licenses needed", "text", True),
        ("regulations", "the regulations that apply", "text", False),
    ],
    "financial_feasibility": [
        ("investment", "the total investment needed", "text", True),
        ("revenue", "the expected revenue", "text", True),
        ("costs", "the expected costs", "text", True),
    ],
    "risk": [
        ("risks", "at least one named risk", "items", True),
    ],
}

FEASIBILITY_SECTIONS = [
    {"key": "executive_summary", "heading": "Executive Summary", "kind": "integration", "level": 1},
    {"key": "project_description", "heading": "Project Description", "kind": "input", "level": 1},
    {"key": "market_feasibility", "heading": "Market Feasibility", "kind": "input", "level": 1},
    {"key": "technical_feasibility", "heading": "Technical Feasibility", "kind": "input", "level": 1},
    {"key": "management_feasibility", "heading": "Management Feasibility", "kind": "input", "level": 1},
    {"key": "legal_feasibility", "heading": "Legal and Regulatory Feasibility", "kind": "input", "level": 1},
    {"key": "financial_feasibility", "heading": "Financial Feasibility", "kind": "computation", "level": 1},
    {"key": "risk", "heading": "Risk Analysis", "kind": "integration", "level": 1},
    {"key": "conclusion", "heading": "Conclusion", "kind": "integration", "level": 1},
    {"key": "references", "heading": "References", "kind": "references", "level": 1},
]

FEASIBILITY_OPTIONAL = {"risk"}

FEASIBILITY_BLOCKS = [
    {"key": "frommarket", "label": "Market Size and Target Sales", "method": "sales_from_market",
     "section": "financial_feasibility", "level": "shs", "required": True,
     "what": "Target revenue and units from your declared market size, share and price."},
    {"key": "breakeven", "label": "Break-even", "method": "breakeven",
     "section": "financial_feasibility", "level": "shs", "required": True,
     "what": "The quantity and revenue at which the declared price covers the declared costs."},
    {"key": "proforma", "label": "Projected Financial Statements", "method": "proforma_statements",
     "section": "financial_feasibility", "level": "shs", "required": True,
     "what": "Projected income statement, cash flow and balance sheet from your declared drivers."},
    {"key": "sensitivity", "label": "Sensitivity", "method": "sensitivity_table",
     "section": "financial_feasibility", "level": "shs", "required": True,
     "what": "Profit across declared price and volume changes."},
]

FEASIBILITY_DIMENSIONS_LIST = [
    ("market", "Market Feasibility", "market demand size growth competition", "economic"),
    ("technical", "Technical Feasibility", "technology equipment capacity process", None),
    ("management", "Management Feasibility", "team skills organisation capacity", None),
    ("legal", "Legal and Regulatory Feasibility", "permits licenses regulation compliance", "legal"),
    ("financial", "Financial Feasibility", "cost revenue funding cash flow", "economic"),
]


PLAN_LEVELS = {"shs": "Senior high school", "college": "College"}
PLAN_MODES = {"strict": "Business-plan convention", "open": "Open composition"}

PLAN_DIMENSIONS = [
    ("market", "Market Size and Growth", "market size growth demand industry spending", "economic"),
    ("customers", "Customers and Segments", "consumer behaviour demand survey customers", "social"),
    ("competition", "Competition", "competition market share rival entrant", None),
    ("regulation", "Regulation and Policy", "regulation policy licence compliance permits", "legal"),
]

#: One field is one student input.  The student's words are reproduced, never
#: inferred.  `items` fields accept a list or semicolon-separated text.
PLAN_FIELDS = {
    "business_description": [
        ("business_name", "the business name", "text", True),
        ("product", "what the business sells", "text", True),
        ("customers", "who the customers are", "text", True),
        ("location", "where the business operates", "text", True),
    ],
    "marketing_plan": [
        ("positioning", "how the business is positioned", "text", True),
        ("channels", "how it will reach customers", "text", True),
        ("pricing_note", "the pricing approach", "text", True),
    ],
    "operations_plan": [
        ("operations", "how the business will operate", "text", True),
        ("suppliers", "the suppliers or inputs it depends on", "text", False),
        ("capacity_note", "the capacity it needs", "text", False),
    ],
    "management": [
        ("team", "who will run the business", "text", True),
        ("roles", "what each person is responsible for", "text", False),
    ],
    "risk": [
        ("risks", "at least one named risk", "items", True),
    ],
    "impact": [
        ("impact_summary", "a statement of the expected social or environmental impact", "text", True),
    ],
}

PLAN_SECTIONS = [
    {"key": "executive_summary", "heading": "Executive Summary", "kind": "integration", "level": 1},
    {"key": "business_description", "heading": "Business Description", "kind": "input", "level": 1},
    {"key": "market_analysis", "heading": "Market Analysis", "kind": "evidence", "level": 1},
    {"key": "marketing_plan", "heading": "Marketing Plan", "kind": "input", "level": 1},
    {"key": "operations_plan", "heading": "Operations Plan", "kind": "input", "level": 1},
    {"key": "management", "heading": "Management and Organisation", "kind": "input", "level": 1},
    {"key": "financial_plan", "heading": "Financial Plan", "kind": "computation", "level": 1},
    {"key": "funding", "heading": "Funding and Ownership", "kind": "computation", "level": 1,
     "min_level": "college"},
    {"key": "impact", "heading": "Social and Environmental Impact", "kind": "computation", "level": 1,
     "min_level": "college"},
    {"key": "risk", "heading": "Risk Analysis", "kind": "integration", "level": 1},
    {"key": "conclusion", "heading": "Conclusion", "kind": "integration", "level": 1},
    {"key": "references", "heading": "References", "kind": "references", "level": 1},
]

#: H2 computation blocks.  `section` names the H1 they sit under; the Financial
#: Plan is one H1 with its computations as H2s.  A block above the student's
#: level is not requested and is never shown as a gap.
COMPUTATION_BLOCKS = [
    {"key": "frommarket", "label": "Market Size and Target Sales", "method": "sales_from_market",
     "section": "financial_plan", "level": "shs", "required": True,
     "what": "Target revenue and units from your declared market size, share and price."},
    {"key": "breakeven", "label": "Break-even", "method": "breakeven",
     "section": "financial_plan", "level": "shs", "required": True,
     "what": "The quantity and revenue at which the declared price covers the declared costs."},
    {"key": "depreciation", "label": "Depreciation", "method": "depreciation_schedule",
     "section": "financial_plan", "level": "shs", "required": True,
     "what": "The period depreciation charge and the carrying amount of an asset."},
    {"key": "proforma", "label": "Projected Financial Statements", "method": "proforma_statements",
     "section": "financial_plan", "level": "shs", "required": True,
     "what": "Projected income statement, cash flow and balance sheet from your declared drivers."},
    {"key": "sensitivity", "label": "Sensitivity", "method": "sensitivity_table",
     "section": "financial_plan", "level": "shs", "required": True,
     "what": "Profit across declared price and volume changes."},
    {"key": "tax", "label": "Tax", "method": "tax_declared",
     "section": "financial_plan", "level": "college", "required": True,
     "what": "Income tax, VAT payable and deferred tax from declared rates."},
    {"key": "captable", "label": "Ownership After the Round", "method": "cap_table_round",
     "section": "funding", "level": "college", "required": True,
     "what": "Post-money value, new shares and the resulting ownership percentages."},
    {"key": "impact", "label": "Cost per Unit of Impact", "method": "cost_effectiveness",
     "section": "impact", "level": "college", "required": True,
     "what": "Incremental cost per unit of effect between your options."},
]


#: Short, targeted search phrases.  Long cue lists return few results in the
#: scholarly indexes; these keep the query specific to the dimension.
#: Search phrases for the conductor frameworks that have no worksheet profile yet.
#: A framework with a profile reads its phrases from `framework_profiles` instead,
#: so the worksheet and the chat cannot drift apart (PESTEL and Five Forces do).
SEARCH_TERMS = {
    "opportunities": "market growth digital consumers",
    "threats": "sanctions conflict restrictions",
}

EXTERNAL_HINTS = {
    "market", "industry", "country", "region", "regulation", "policy", "macro", "economy",
    "economic", "social", "technology", "technological", "environment", "environmental",
    "legal", "political", "competition", "trend", "demand", "export", "trade", "expansion",
    "entry", "business", "company", "firm", "startup", "organization", "product", "service",
}
COMPUTATION_HINTS = {
    "journal entry", "ledger", "trial balance", "balance sheet", "income statement", "npv",
    "irr", "depreciation", "amortization", "amortisation",
    "compute", "reconcile", "debit", "credit",
}


STOP = set(
    "a an the and or of to in on for with by at from as is are was were be been it its this that these those "
    "we our us you your i my me they their them not no do does did can could should would will may might have "
    "has had how what when where which who why if then than so such about into over under between among after "
    "before during each per via also more most much many some any other another own same very".split()
)


class ChatError(ValueError):
    """A conductor step was refused with a reason the student can act on."""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _clean(value, limit=2000):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _fit(brief, framework="none"):
    text = (brief or "").lower()
    if framework in ("breakeven", "vrio"):
        # A computation and an internal-resource audit need no external evidence.
        return True, None
    if any(hint in text for hint in COMPUTATION_HINTS) and not any(hint in text for hint in EXTERNAL_HINTS):
        # A pure computation is not a strategic analysis: the Accounting and Finance
        # shelves run the frozen methods for it, and the framework chat must say so
        # rather than wrap a trial balance in a PESTEL paper.
        return False, ("This looks like an accounting or finance computation, not a strategic analysis. "
                       "Use the Accounting or Finance shelf instead.")
    if framework == "pestel" and not any(hint in text for hint in EXTERNAL_HINTS):
        return False, ("This brief does not yet name an external question. Add the market, industry, country "
                       "or decision the analysis should support.")
    return True, None


def _items(value, limit=6):
    """Split a supplied list into clean items; the student's words are kept."""
    if isinstance(value, list):
        parts = value
    else:
        parts = re.split(r"[\n;]+", str(value or ""))
    return [item for item in (_clean(part, 200) for part in parts) if item][:limit]


def _infer_framework(brief):
    reading = instruction_reading.read_frameworks(brief)
    if reading.status == "resolved" and len(reading.selected) == 1:
        return reading.selected[0]
    # Ambiguous, conflicting, absent, or only negated/contrast mentions: the
    # student chooses.  The system never fills the gap with a default.
    return None


def _defaults(brief):
    text = (brief or "").lower()
    geography = "Global"
    for word, region in (("united states", "US"), ("u.s.", "US"), (" us ", "US"), ("america", "US"),
                         ("europe", "Europe"), ("european union", "Europe"), (" eu ", "Europe"), ("uk", "Europe"),
                         ("middle east", "Middle East"), ("saudi", "Middle East"), ("uae", "Middle East"),
                         ("qatar", "Middle East"), ("china", "China"), ("chinese", "China")):
        if word in text:
            geography = region
            break
    period = "10"
    match = re.search(r"(?:last|past|since)\s+(\d{1,2})\s+years?", text)
    if match:
        period = match.group(1)
    style = "apa"
    if "harvard" in text:
        style = "harvard"
    elif "chicago" in text and "notes" in text:
        style = "chicago_nb"
    elif "chicago" in text:
        style = "chicago_ad"
    elif "mla" in text:
        style = "mla"
    elif "vancouver" in text:
        style = "vancouver"
    elif "ieee" in text:
        style = "ieee"
    elif "oscola" in text:
        style = "oscola"
    return {"decision": _clean(brief, 500), "geography": geography, "period": period, "style": style}


def _infer_archetype(brief, framework=None, profile=None):
    wanted = (profile or "").strip().lower().replace(" ", "_")
    if wanted in ("business_plan", "businessplan", "plan", "feasibility_study",
                  "feasibilitystudy", "feasibility", "marketing_plan", "marketingplan",
                  "marketing", "project_proposal", "projectproposal", "proposal"):
        return "plan_proposal"
    text = (brief or "").lower()
    if any(word in text for word in ("case study", "case analysis", "post-mortem", "postmortem", "failure analysis")):
        return "case_analysis"
    if any(word in text for word in ("literature review", "annotated bibliography", "critical review")):
        return "literature_synthesis"
    if any(word in text for word in ("position paper", "white paper", "essay", "argumentative")):
        return "argumentative_essay"
    if any(word in text for word in ("policy memo", "business memo", "executive summary", "briefing paper")):
        return "memo_brief"
    if any(word in text for word in ("valuation", "dcf", "equity research", "stock pitch", "capital budgeting")):
        return "financial_valuation"
    if any(word in text for word in ("reflection", "reflective", "internship")):
        return "reflective"
    if any(word in text for word in ("compliance", "contract law", "case brief", "regulatory")):
        return "legal_regulatory"
    if any(word in text for word in ("research paper", "empirical", "thesis", "dissertation")):
        return "empirical_research"
    return "analytical_report"


def _refusal_state(brief, error, slots=()):
    """A short, human refusal for an instruction that cannot be repaired."""
    if error.code == "CATEGORY_ERROR":
        title = "Your instruction appears to ask for an attribute a framework does not have."
        hint = ("Start over and rephrase this as a valuation, a financial instrument, or a framework "
                "without a rate.")
    else:
        title = "Your instruction appears to be outside what this paper can analyse."
        hint = "Start over and rephrase the decision, the evidence you have, and what the paper should settle."
    return {
        "format": FORMAT,
        "brief": brief,
        "stage": "refused",
        "refusal": {
            "code": error.code,
            "title": title,
            "detail": error.why,
            "hint": hint,
            "found": error.found,
            "options": [dict(row) for row in error.repairs],
        },
        "questions": [],
        "answers": _defaults(brief),
        "slots": [dataclasses.asdict(slot) for slot in slots],
        "created_at": _now(),
        "updated_at": _now(),
    }


def _framework_choices(brief, archetype=None):
    """Suggested frameworks first, then "No framework", then the rest."""
    reading = instruction_reading.read_frameworks(brief)
    suggested = []
    for mention in reading.mentions:
        if mention.role in ("primary", "contrast") and mention.framework_id not in suggested:
            suggested.append(mention.framework_id)
    by_archetype = {
        "analytical_report": ["pestel", "five_forces", "value_chain", "swot"],
        "case_analysis": ["swot", "five_forces", "value_chain"],
        "plan_proposal": ["ansoff", "five_forces"],
        "financial_valuation": ["breakeven"],
        "argumentative_essay": [],
        "memo_brief": [],
        "literature_synthesis": [],
        "empirical_research": [],
    }
    for key in by_archetype.get(archetype or "analytical_report", []):
        if key not in suggested:
            suggested.append(key)
    return [("none", "No framework")] + [(key, FRAMEWORKS[key]["label"]) for key in suggested if key in FRAMEWORKS]


def start(brief, subject=None, framework=None, profile=None, level="shs", mode="strict",
          words=None, rubric=None, archetype=None, frameworks=None):
    """Create a conductor state.  No source is retrieved until the plan is confirmed.

    ``rubric`` is the marking guide the student attached — the text of the file, or the
    structure ``bp.product.rubric.parse`` already returned.  It is read **once, here**, and
    a rubric that cannot be read is refused: a run that accepted it and wrote the paper
    anyway would tell the student their rubric had been followed when nothing had been
    read from it.  The coverage is measured when the paper is drafted, not now.
    """
    brief = _clean(brief, 2000)
    if len(brief) < 15:
        raise ChatError("Describe the case or assignment in at least one sentence.")
    category_errors = instruction_reading.find_category_errors(brief)
    instruction_slots = instruction_reading.extract_slots(brief)
    if category_errors:
        return _refusal_state(brief, category_errors[0], instruction_slots)
    attached = _read_rubric(rubric) if rubric is not None else None
    wanted = (profile or framework or "").strip().lower().replace(" ", "_")
    if wanted in (PROFILE_BUSINESS_PLAN, "business_plan", "businessplan", "plan"):
        return _with_rubric(_start_plan(brief, subject, level, mode), attached)
    if wanted in (PROFILE_FEASIBILITY_STUDY, "feasibility_study", "feasibilitystudy", "feasibility"):
        return _with_rubric(_start_feasibility_study(brief, subject, level, mode), attached)
    if wanted in (PROFILE_MARKETING_PLAN, "marketing_plan", "marketingplan", "marketing"):
        return _with_rubric(_start_marketing_plan(brief, subject, level, mode), attached)
    if wanted in (PROFILE_PROJECT_PROPOSAL, "project_proposal", "projectproposal", "proposal"):
        return _with_rubric(_start_project_proposal(brief, subject, level, mode), attached)
    frameworks = [str(item).strip().lower() for item in (frameworks or []) if str(item).strip()]
    if frameworks:
        if any(item not in FRAMEWORKS for item in frameworks):
            raise ChatError("Choose PESTEL, SWOT, PESTEL + SWOT, Five Forces, Value Chain, Ansoff, VRIO, or Break-even.")
    else:
        framework = (framework or "").strip().lower() or _infer_framework(brief)
        council_result, council_note = None, None
        if council.available():
            # The council may change the reading of the brief, including the framework.
            # Its output is verified by code before it is used, and the resolver stays
            # the fallback whenever it cannot decide.
            try:
                council_result = council.advise(brief, capabilities.ENTRIES, tuple(FRAMEWORKS))
            except council.CouncilError as error:
                council_note = "the council could not decide: " + str(error)[:200]
            except Exception as error:  # a provider failure must never lose the brief
                council_note = "the council failed: " + str(error)[:200]
            if council_result and council_result.get("reading"):
                chosen = [name for name in council_result["reading"].get("frameworks") or []
                          if name in FRAMEWORKS]
                if chosen:
                    frameworks = chosen
        council_archetype = (council_result.get("reading") or {}).get("archetype") if isinstance(council_result, dict) else None
        if council_archetype in paper_families.ARCHETYPES:
            archetype = council_archetype
        if not frameworks and framework is not None:
            frameworks = [framework]
        if frameworks and any(item not in FRAMEWORKS for item in frameworks):
            raise ChatError("Choose PESTEL, SWOT, PESTEL + SWOT, Five Forces, Value Chain, Ansoff, VRIO, or Break-even.")
        framework = frameworks[0] if frameworks else None
    open_mode = guard.is_open(subject)
    detected_id = ""
    detected_cue = ""
    if open_mode:
        detected_id, detected_cue = guard.detect_subject(brief)
    if not open_mode:
        # The computation boundary runs first: it can name the shelf the brief belongs
        # to ("use the Accounting shelf"), which is more useful than the vocabulary's
        # generic refusal for the same brief.  The shelf checked is the one the student
        # named — nothing is invented here.  Defaulting an unnamed brief to
        # "management" and then refusing it for not being a management brief turned an
        # ordinary coffee-shop brief into `not_supported` (D-PLAN-03); an unnamed shelf
        # is not refused, a named one still is, with the shelf to use instead.
        fits, message = guard.computation_boundary(brief, subject or "")
        if fits:
            fits, message = guard.subject_fit(brief, subject or "")
        if not fits and framework in ("breakeven", "vrio"):
            # A break-even paper and a resource audit are not management briefs; the
            # framework is explicit, so the subject guard would refuse a legitimate paper.
            fits, message = True, None
        if fits:
            fits, message = _fit(brief, framework)
    else:
        fits, message = True, None
    if category_errors:
        error = category_errors[0]
        framework = None
        questions = [{"id": "category_error", "prompt": "What should the quantity do?",
                      "why": error.why,
                      "type": "choice",
                      "choices": [[row.get("method") or "ignore", row["option"]] for row in error.repairs],
                      "allow_skip": False}]
    elif framework is None:
        questions = [{"id": "framework", "prompt": "Which framework should this paper use?",
                      "why": "The framework organises the evidence and the firm's position; choose the one the assignment asks for, or choose no framework.",
                      "type": "choice",
                      "choices": _framework_choices(brief, archetype or _infer_archetype(brief, framework, profile)),
                      "allow_skip": False}]
    else:
        questions = [dict(question) for question in FRAMEWORK_QUESTIONS[framework]]
    answers = _defaults(brief)
    # A brief may name the option ("mid-length report") or give a count; either is
    # read here, before any question is put to the student.
    named = parse_length_name(brief)
    if named:
        answers["length"] = str(check_word_target(named))
    requested = parse_word_target(brief)
    if requested is not None:
        answers["length"] = str(check_word_target(str(requested)))
    # The Home composer's word box overrides the brief: what the student typed in
    # the box is the most recent statement of the length.
    if words not in (None, ""):
        answers["length"] = str(check_word_target(words))
    if framework is not None and FRAMEWORKS[framework].get("internal"):
        answers.update({"strengths": [], "weaknesses": []})
    for key in (FRAMEWORKS[framework].get("inputs") if framework is not None else []) or []:
        answers.setdefault(key, [])
    detected_label = ""
    if detected_id:
        try:
            from . import subjects as subject_index
            for definition in subject_index.SUBJECT_DEFS:
                if definition.get("id") == detected_id:
                    detected_label = definition.get("label") or detected_id
                    break
        except Exception:
            detected_label = detected_id
    state_subject = (detected_id if open_mode else (subject or "management"))
    if open_mode and not detected_id:
        state_subject = ""
    resolved_archetype = (archetype or "").strip().lower() or _infer_archetype(brief, framework, profile)
    state = {"format": FORMAT, "subject": state_subject, "framework": framework,
             "frameworks": [framework] if framework else [],
             "brief": brief, "archetype": resolved_archetype, "paper_contract": None, "audit": None,
             "blocks": None, "evidence_ledger": None, "chart_specs": None, "production_check": None,
             "created_at": _now(), "updated_at": _now(), "stage": "clarify",
             "answers": answers, "questions": questions, "question_index": 0,
             "category_errors": [dataclasses.asdict(error) for error in category_errors],
             "slots": [dataclasses.asdict(slot) for slot in instruction_slots],
             "plan": None, "sources": [], "evidence": [], "gaps": [], "notes": [],
             "computation": None, "draft": None,
             "selection": None, "computations": {}, "orientation_sources": []}
    if open_mode:
        state["subject_requested"] = "any"
        state["subject_detected"] = ({"id": detected_id, "label": detected_label, "cue": detected_cue}
                                    if detected_id else None)
    # Which capabilities this paper carries is decided from the brief, not from a
    # fixed list: a framework-only brief selects nothing and the paper runs as before.
    if council_result and council_result.get("reading"):
        selection = _selection_from_reading(council_result["reading"], framework, council_result)
        state["plan_figures"] = list(council_result["reading"].get("figures") or [])
        state["plan_models"] = [{"role": "council", "model": council.model_id()}]
    else:
        selection = capabilities.resolve(brief, framework, answers)
    _fill_capability_inputs(selection)
    state["selection"] = selection
    # Figures the brief already declares are offered as declared inputs; nothing
    # is run until the student asks the core to accept them.
    apply_figures(state)
    apply_dependencies(state)
    state["council"] = ({"format": council.FORMAT,
                         "approved": council_result.get("approved") if council_result else [],
                         "rejected": council_result.get("rejected") if council_result else [],
                         "verdict": council_result.get("verdict") if council_result else None}
                        if council_result else ({"note": council_note} if council_note else None))
    if open_mode and fits:
        lower_brief = brief.lower()
        pure_comp = any(hint in lower_brief for hint in COMPUTATION_HINTS)
        no_cap = not (selection.get("selected") or [])
        no_fw = (framework == "pestel")
        if pure_comp and no_cap and no_fw:
            if detected_id == "finance":
                message = ("This looks like a finance computation. Use the Finance shelf and its tools; "
                           "see GET /api/cases/subjects/finance.")
            else:
                message = ("This looks like an accounting computation. Use the Accounting shelf and its "
                           "ledger, trial-balance and check tools; see GET /api/cases/subjects/accounting.")
            fits = False
    if selection.get("question"):
        questions.insert(0, dict(selection["question"]))
        state["question_quote"] = selection.get("question_quote") or ""
    if not fits:
        # A refusal that has been decided must reach the student: `fits` and its
        # message are computed above (the subject fit, the external-evidence fit and
        # the pure-computation boundary), and silently returning `clarify` would send
        # a journal-entry or npv brief to PESTEL.  Fail closed, with the reason.
        state.update({"stage": "not_supported", "message": message, "questions": [],
                      "question_index": 0})
    return _with_rubric(state, attached)


def _read_rubric(value):
    """The attached marking guide, read once; a document that cannot be read is refused.

    The reader's own reason is raised, so the student is told what to fix — a rubric
    silently ignored would be a promise the product did not keep.
    """
    try:
        parsed = value if isinstance(value, dict) else rubric_reader.parse(value)
    except Exception as error:                                   # a reader must never crash a run
        raise ChatError("The rubric could not be read: " + str(error)[:200])
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        problems = (parsed or {}).get("problems") if isinstance(parsed, dict) else None
        raise ChatError(problems[0] if problems else
                        "The rubric could not be read. Attach it as a table or a numbered list.")
    return parsed


def _with_rubric(state, attached):
    """Carry the marking guide on the state it was attached to, and nowhere else.

    The parsed guide is stored as `rubric_record`; the **coverage** is measured when the
    paper is drafted and stored as `rubric`, which is the key `paper.missing` reads.  A
    run with no rubric is byte-identical to what it was before the guide existed.
    """
    if attached is None:
        return state
    state["rubric_record"] = attached
    state["rubric_gate"] = True
    state["updated_at"] = _now()
    return state


def _selection_from_reading(reading, framework, result=None):
    """Turn a verified reading into the selection every later step reads."""
    selected = []
    for item in reading.get("capabilities") or []:
        key = str((item or {}).get("key") or "") if isinstance(item, dict) else str(item)
        if key not in capabilities.ENTRIES:
            continue
        row = capabilities.ENTRIES[key]
        anchor = ""
        for candidate in reading.get("anchors") or []:
            if isinstance(candidate, dict) and candidate.get("quote"):
                anchor = candidate["quote"]
                break
        selected.append({
            "key": key, "method": row["method"], "label": row["label"],
            "subject": row.get("subject") or "", "slot": list(row["slot"]),
            "integration": row.get("integration") or "Framework and Declared Figures",
            "inputs_required": [], "inputs": {}, "one_of": [], "min_inputs": row.get("min_inputs"),
            "licenses": "", "not": "", "row_fields": {},
            "because": {"rule": "council:" + str(reading.get("stance") or "reading"), "quote": anchor},
        })
    payload = {"format": capabilities.FORMAT, "catalogue_version": capabilities.CATALOGUE_VERSION,
               "framework": framework,
               "selected": [{k: row[k] for k in ("key", "method", "slot")} for row in selected],
               "question": None}
    return {"format": capabilities.FORMAT, "catalogue_version": capabilities.CATALOGUE_VERSION,
            "frameworks": [framework], "selected": selected,
            "not_included": [dict(item) for item in reading.get("not_included") or []
                             if isinstance(item, dict)],
            "question": None, "question_quote": "", "hash": capabilities._hash(payload),
            "because": {"rule": "council", "quote": str(reading.get("why") or "")[:300]}}


def apply_figures(state):
    """Offer the figures the brief already declares as the declared inputs.

    A verified reading carries each figure with the text it came from.  This
    turns those figures into the canonical value the frozen schema expects and
    offers them to the capability whose input they name.  Nothing is computed
    here: the student still presses Validate and attach, and the core still
    decides whether the figures are acceptable.  A figure that cannot be read is
    refused and recorded with its reason, never guessed, and a figure no selected
    computation needs is recorded as unused rather than dropped silently.
    """
    applied, filings = {}, []
    figures = [figure for figure in state.get("plan_figures") or [] if isinstance(figure, dict)]
    selected = (state.get("selection") or {}).get("selected") or []
    schemas = {row["key"]: _schema_for(row.get("method") or "") for row in selected}
    for figure in figures:
        name = str(figure.get("input") or "")
        quote = str(figure.get("quote") or "")
        written = figure.get("written")
        if not name:
            filings.append({"input": "", "written": written, "quote": quote,
                            "refused": "the figure does not name the input it belongs to"})
            continue
        used = False
        for row in selected:
            schema = schemas.get(row["key"]) or {}
            if name not in schema:
                continue
            used = True
            kind = figure.get("kind") or verify.input_kind(name, schema.get(name) or {})
            try:
                value, steps = verify.normalise_number(written, kind)
            except verify.VerifyError as error:
                filings.append({"key": row["key"], "input": name, "written": written, "quote": quote,
                                "refused": str(error)})
                continue
            target = applied.setdefault(row["key"], {})
            if name in target and target[name] != value:
                # Two figures for one input is an ambiguity; the tool refuses it
                # rather than choosing a number on the student's behalf.
                target.pop(name, None)
                filings.append({"key": row["key"], "input": name, "written": written, "quote": quote,
                                "refused": "the reading gives more than one figure for this input"})
                continue
            target[name] = value
            filings.append({"key": row["key"], "input": name, "written": written, "quote": quote,
                            "value": value, "steps": steps})
        if not used:
            filings.append({"input": name, "written": written, "quote": quote,
                            "unused": "no selected computation takes an input named " + name})
    state["plan_figures_applied"] = applied
    state["figure_filings"] = filings
    if state.get("plan"):
        # The card shows what the brief supplied, so it is rebuilt with the plan.
        state["plan"] = _plan(state)
    return applied


def _chained_sources(state, key):
    """Which of a capability's inputs the plan took from another frozen result."""
    offered = (state.get("dependency_inputs") or {}).get(key) or {}
    rule = capabilities.NEEDS_FROM.get(key) or {}
    return {name: rule[name][0] for name in offered if name in rule}


def apply_dependencies(state):
    """Offer each selected capability the figures another one has computed.

    The chain is registered in `capabilities.NEEDS_FROM` — a discount rate from
    WACC, a firm's sales from the sales method — so no method-to-method
    assumption is invented here.  A value is offered only when the source
    capability is in this paper and has a recorded, successful result.  Nothing is
    run and nothing is overwritten: `run_capability` records which declared inputs
    came from which frozen result, and the recompute guard re-runs both.
    """
    rows = capabilities.dependencies(state.get("selection") or {}, state.get("computations") or {})
    offered = {}
    for row in rows:
        if row["selected"] and row["recorded"]:
            offered.setdefault(row["key"], {})[row["input"]] = row["value"]
    state["dependency_inputs"] = offered
    state["dependency_graph"] = rows
    if state.get("plan"):
        state["plan"] = _plan(state)
    return offered


def _fill_capability_inputs(selection):
    """Name the frozen inputs each selected capability needs, and quote the method
    library's own licence and limitation.  Nothing is restated by hand here."""
    for row in (selection or {}).get("selected") or []:
        schema = _schema_for(row.get("method") or "")
        row["inputs_required"] = [name for name, spec in schema.items() if spec.get("required", True)]
        row["inputs"] = {name: {"desc": spec.get("desc") or name,
                                "type": spec.get("type") or "",
                                "values": list(spec.get("values") or []),
                                "required": bool(spec.get("required", True)),
                                "fields": spec.get("fields") or {},
                                "min_items": spec.get("min_items") or 1}
                         for name, spec in schema.items()}
        if METHOD_DESCRIBE is not None and row.get("method"):
            try:
                info = METHOD_DESCRIBE(row["method"]) or {}
            except Exception:
                info = {}
            row["licenses"] = str(info.get("intended_use") or row.get("licenses") or "").strip()
            row["not"] = str(info.get("unsupported_use") or row.get("not") or "").strip()
        try:
            entry = capabilities.entry(row["key"])
        except KeyError:
            entry = {}
        forced = set(entry.get("require_inputs") or [])
        for name in forced:
            if name in row["inputs"]:
                row["inputs"][name]["required"] = True
        row["inputs_required"] = list(dict.fromkeys(
            list(row.get("inputs_required") or []) + sorted(forced)))
        row["one_of"] = [list(group) for group in entry.get("one_of") or []]
        row["min_inputs"] = entry.get("min_inputs")
        row["row_fields"] = {name: list(fields) for name, fields in (entry.get("row_fields") or {}).items()}
    return selection


def current_question(state):
    index = state.get("question_index", 0)
    questions = state.get("questions") or []
    return questions[index] if index < len(questions) else None


def answer(state, question_id, value):
    """Answer the current question; when the last is answered, build the plan."""
    question = current_question(state)
    if not question or question["id"] != question_id:
        raise ChatError("That is not the question waiting for an answer.")
    if question_id == "framework" and question.get("type") == "choice":
        if value not in FRAMEWORKS:
            raise ChatError("Choose one of: " + ", ".join(FRAMEWORKS))
        state["framework"] = value
        state["frameworks"] = [value]
        answers = dict(state.get("answers") or {})
        answers["framework"] = value
        answers.update(_defaults(state.get("brief") or ""))
        if FRAMEWORKS[value].get("internal"):
            answers.update({"strengths": [], "weaknesses": []})
        for key in FRAMEWORKS[value].get("inputs") or []:
            answers.setdefault(key, [])
        state["answers"] = answers
        state["questions"] = [dict(q) for q in FRAMEWORK_QUESTIONS[value]]
        state["question_index"] = 0
        state["updated_at"] = _now()
        return state
    if question_id == "category_error" and question.get("type") == "choice":
        slots = [dict(slot) for slot in (state.get("slots") or [])]
        for slot in slots:
            if slot.get("status") == "pending":
                slot["status"] = "dismissed" if value == "ignore" else "consumed"
                break
        state["slots"] = slots
        state["category_errors"] = []
        state["questions"] = [{"id": "framework", "prompt": "Which framework should this paper use?",
                               "why": "The framework organises the evidence and the firm's position.",
                               "type": "choice",
                               "choices": [[key, FRAMEWORKS[key]["label"]] for key in FRAMEWORKS],
                               "allow_skip": False}]
        state["question_index"] = 0
        state["updated_at"] = _now()
        return state
    if question["type"] == "choice":
        allowed = [choice[0] if isinstance(choice, list) else choice for choice in question["choices"]]
        if value not in allowed:
            raise ChatError("Choose one of: " + ", ".join(allowed))
        state["answers"][question_id] = value
        # The one ambiguity question decides whether the paper carries a
        # computation; the answer is recorded, and the plan explains it.
        if str(question_id).startswith("capability:"):
            state["selection"] = capabilities.apply_answer(state.get("selection") or {},
                                                           question_id, value)
            _fill_capability_inputs(state["selection"])
            apply_figures(state)
            apply_dependencies(state)
    elif question["type"] == "items":
        items = _items(value)
        if not items and not question.get("allow_skip"):
            raise ChatError("An answer is required for this question.")
        state["answers"][question_id] = items
    elif question["type"] == "number":
        text = _clean(value, 40)
        if not text and question.get("allow_skip"):
            state["answers"][question_id] = ""
            state["question_index"] = state.get("question_index", 0) + 1
            if current_question(state) is None:
                state["plan"] = _plan(state)
                state["stage"] = "plan"
            state["updated_at"] = _now()
            return state
        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ChatError("Enter a number, for example 250000.")
        if number < 0:
            raise ChatError("A cost or volume cannot be negative.")
        state["answers"][question_id] = str(number)
    else:
        text = _clean(value, 500)
        if not text and not question.get("allow_skip"):
            raise ChatError("An answer is required for this question.")
        state["answers"][question_id] = text or state["answers"].get(question_id, "")
    state["question_index"] = state.get("question_index", 0) + 1
    if current_question(state) is None:
        state["plan"] = _plan(state)
        state["stage"] = "plan"
    state["updated_at"] = _now()
    return state


def _topic(text, limit=10):
    words = [word for word in re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower())
             if len(word) >= 3 and word not in STOP]
    return words[:limit]


def _plan(state):
    answers = state["answers"]
    framework = state.get("framework") or "none"
    frameworks = state.get("frameworks") or [framework]
    config = FRAMEWORKS[framework]
    seen_keys = set()
    dimensions = []
    for fw in frameworks:
        cfg = FRAMEWORKS.get(fw) or config
        for key, label, cues, category in (cfg.get("dimensions") or []):
            if key in seen_keys:
                continue
            seen_keys.add(key)
            dimensions.append({"key": key, "label": label, "query": _query(state, key, cues), "cues": cues,
                               "category": category, "source_note": _source_note(category)})
    why = {
        "none": ("No named framework is used. The paper organises the retrieved evidence around the decision itself."),
        "pestel": ("PESTEL organizes the external political, economic, social, technological, environmental and "
                   "legal evidence around the decision."),
        "swot": ("SWOT places the strengths and weaknesses you supply against the opportunities and threats the "
                 "external evidence supports."),
        "pestel_swot": ("PESTEL explains the external environment; SWOT then places your internal strengths and "
                        "weaknesses against the opportunities and threats that environment creates."),
        "five_forces": ("Five Forces assesses the attractiveness of the industry through rivalry, entrants, substitutes, "
                        "buyer power and supplier power."),
        "five_forces_breakeven": ("Five Forces assesses the industry; break-even then tests whether the declared cost "
                                  "structure can support entry at the declared price."),
        "value_chain": ("The value chain separates the activities that create the offer, so each one can be examined "
                        "for the cost and the value it adds."),
        "ansoff": ("Ansoff places each growth option on the product and market it uses, so the risks of the four "
                   "options can be compared on one page."),
        "vrio": ("VRIO tests each resource you name against value, rarity, imitation cost and organisation, so a claim "
                 "of advantage rests on four explicit judgments."),
        "breakeven": ("Break-even tests whether the declared price covers the declared fixed and variable costs, and "
                      "how much volume that needs."),
    }[framework]
    misses = {
        "none": ("It does not impose a framework. The paper states the evidence and the limits of the evidence, and it does not invent an analytical structure the assignment did not ask for."),
        "pestel": ("It does not assess internal capabilities, competitors, costs, financial feasibility or a "
                   "recommended action; those need other frameworks or methods."),
        "swot": ("It does not weigh or rank the factors, test financial feasibility, or choose an action; it is a "
                 "structured summary, not a strategy."),
        "pestel_swot": ("It still does not weigh or rank the options, test financial feasibility, or choose an "
                        "action; those need other frameworks or methods."),
        "five_forces": ("It describes industry pressure but does not test the firm's cost structure, financial "
                        "feasibility or a recommended action; add a computation or a decision framework."),
        "five_forces_breakeven": ("The break-even result depends on the declared fixed cost, price and variable cost; it "
                                  "does not forecast demand or prove that the expected volume will be reached."),
        "value_chain": ("It maps activities but does not cost them, benchmark them against rivals or prove that any "
                        "one activity is a source of advantage."),
        "ansoff": ("It classifies options but does not size the market, estimate the risk or choose between them; the "
                   "evidence can support or undermine an option, not rank them."),
        "vrio": ("It records your four judgments; it does not test them, measure imitation cost or show that an "
                 "advantage is durable."),
        "breakeven": ("It does not forecast demand, apply tax or financing, or prove that the expected volume will be "
                      "reached; every input is yours."),
    }[framework]
    output = {
        "none": "A paper with an introduction, the retrieved evidence, a discussion with implications and limitations, a conclusion and one reference list.",
        "pestel": "A PESTEL paper with an introduction, six dimensions, a discussion with implications and limitations, a conclusion and one reference list.",
        "swot": "A SWOT paper with your strengths and weaknesses, retrieved opportunities and threats, a discussion with implications and limitations, a conclusion and one reference list.",
        "pestel_swot": ("A combined paper with the six PESTEL dimensions, your strengths and weaknesses, opportunities "
                        "and threats drawn from the accepted evidence, implications, limitations and one reference list."),
        "five_forces": "A Five Forces paper with five industry dimensions, a discussion, a conclusion and one reference list.",
        "five_forces_breakeven": ("A combined paper with the five industry forces, a break-even analysis from your "
                                  "declared figures, a discussion, a conclusion and one reference list."),
        "value_chain": ("A value-chain paper with the five primary and four support activities, your declared firm, a "
                        "discussion with limitations, a conclusion and one reference list."),
        "ansoff": ("An Ansoff paper with the four growth options, the evidence for each, a discussion with limitations, "
                   "a conclusion and one reference list."),
        "vrio": ("A VRIO paper with your resources and the four judgments you supply, a discussion with limitations and "
                 "a conclusion; no external evidence is retrieved."),
        "breakeven": ("A feasibility paper with a break-even analysis from your declared figures, a discussion with "
                      "limitations and a conclusion; no external evidence is retrieved."),
    }[framework]
    selection = state.get("selection") or {}
    selected = selection.get("selected") or []
    if selected:
        output = output + " The paper also carries " + ", ".join(
            row["label"].lower() for row in selected) + " from the figures you declare."
    return {
        "framework": config["label"],
        "framework_id": framework,
        "why": why,
        "misses": misses,
        "decision": answers.get("decision") or state["brief"],
        "country": _country(answers.get("decision") or state["brief"]),
        "geography": answers.get("geography") or "Global",
        "period": answers.get("period") or "10",
        "style": answers.get("style") or "apa",
        "dimensions": dimensions,
        "internal": config["internal"],
        "evidence": config.get("evidence", True),
        "inputs": list(config.get("inputs") or []),
        "swot": framework in ("swot", "pestel_swot"),
        "output": output,
        "capabilities": [{"key": row["key"], "label": row["label"], "slot": row.get("slot"),
                          "because": row.get("because"), "inputs_required": row.get("inputs_required") or [],
                          "inputs": row.get("inputs") or {},
                          "one_of": row.get("one_of") or [], "min_inputs": row.get("min_inputs"),
                          "row_fields": row.get("row_fields") or {},
                          "licenses": row.get("licenses"), "not": row.get("not"),
                          "figures": (state.get("plan_figures_applied") or {}).get(row["key"]) or {},
                          "figure_quotes": {str(figure.get("input")): str(figure.get("quote") or "")
                                            for figure in state.get("plan_figures") or []
                                            if isinstance(figure, dict)
                                            and str(figure.get("input") or "") in (row.get("inputs") or {})},
                          "chained": (state.get("dependency_inputs") or {}).get(row["key"]) or {},
                          "needs_from": [dict(item) for item in state.get("dependency_graph") or []
                                         if item.get("key") == row["key"]],
                          "status": _capability_status(state, row)} for row in selected],
        "available": [{"key": row["key"], "label": row["label"], "because": row.get("because"),
                       "slot": row.get("slot")}
                      for row in _available_capabilities(framework, selected)],
        "not_included": list(selection.get("not_included") or []),
        # A figure the brief declares but the paper cannot take is named, not dropped.
        "figure_problems": [dict(item) for item in state.get("figure_filings") or []
                            if item.get("refused") or item.get("unused")],
        "selection_hash": selection.get("hash"),
        "catalogue_version": selection.get("catalogue_version"),
        # The report length is part of the plan, so the card and the draft agree.
        "target_words": target_words(state) or SHORT_WORDS,
        "length_band": length_band(target_words(state)),
        "length_options": [{"key": key, "label": label, "low": low, "high": high, "target": target}
                           for key, label, low, high, target in LENGTH_BANDS],
        "full_report": (target_words(state) or SHORT_WORDS) >= MID_FLOOR,
        "min_words": MIN_WORDS,
        "max_words": MAX_WORDS,
        "checkpoints": ["Confirm this plan", "Review the retrieved evidence", "Review the drafted section"]
        if config.get("evidence", True) else ["Confirm this plan", "Review your inputs", "Review the drafted section"],
    }


def _query(state, key, cues):
    answers = state["answers"]
    geography = answers.get("geography") or "Global"
    geography = "" if geography == "Global" else geography
    country = retrieval.country(answers.get("decision") or "") or retrieval.country(state["brief"])
    industry = _clean(answers.get("industry"), 80)
    topic = " ".join(part for part in (country, industry) if part) or " ".join(_topic(answers.get("decision") or state["brief"]))
    if not topic:
        topic = _clean(state["brief"], 120)
    search = framework_profiles.phrase(key) or SEARCH_TERMS.get(key) or " ".join(cues.split()[:3])
    return retrieval.build_query(search, topic, geography)


def _source_note(category):
    return {
        "legal": "primary legal and policy sources",
        "economic": "official economic data and research",
        "social": "official social data and survey research",
        None: "academic and official sources",
    }[category]


def set_length(state, value):
    """Set the report length while the plan is open; 0 means the short version.

    The floor is enforced here as well as in the brief, so the plan card, the
    brief and the draft can never disagree about the length.
    """
    if state.get("stage") not in ("plan", "research_ready"):
        raise ChatError("Set the report length while the plan is open.")
    words = check_word_target(value)
    state["answers"]["length"] = str(words) if words else ""
    if state.get("plan"):
        state["plan"] = _plan(state)
    if state.get("draft"):
        state["draft"] = None
    state["updated_at"] = _now()
    return state


def accept_assist(state, key, text):
    """The student's answer to a cell, entered from a model proposal or typed.

    What is stored is the student's answer.  The model's wording is never
    stored in place of it: an empty `text` dismisses the proposal and changes
    nothing.
    """
    answers = state.setdefault("answers", {})
    items = list(answers.get(key) or [])
    text = str(text or "").strip()
    if text:
        items.append(text)
        answers[key] = items
    proposals = state.get("assist") or {}
    if key in proposals:
        proposals[key] = dict(proposals[key], accepted=text or None)
        state["assist"] = proposals
    return state


def _plan_blocks(state):
    """Build a block list from the current framework, selection and computations."""
    blocks = []
    frameworks = state.get("frameworks") or ([state.get("framework")] if state.get("framework") else [])
    for index, framework in enumerate(frameworks):
        if not framework or framework == "none":
            continue
        label = FRAMEWORKS.get(framework, {}).get("label") or str(framework).replace("_", " ")
        blocks.append({"id": "b_framework_%d" % index, "kind": "framework", "ref": framework,
                       "role": "analysis", "contribution": "analyses the case with " + label,
                       "requires": {"evidence": []}, "produces": {"sections": [label]}})
    selection = state.get("selection") or {}
    for index, row in enumerate(selection.get("selected") or []):
        blocks.append({"id": "b_cap_%d" % index, "kind": "computation", "ref": row.get("key"),
                       "role": "computation", "contribution": "computes " + str(row.get("label") or row.get("key")),
                       "requires": {"student_inputs": row.get("inputs_required") or []},
                       "produces": {"artifacts": [row.get("key")]}})
    if len([b for b in blocks if b["kind"] in ("framework", "computation")]) > 1:
        blocks.append({"id": "b_synthesis", "kind": "prose", "ref": "synthesis", "role": "synthesis",
                       "contribution": "reconciles the analysis blocks against the decision",
                       "requires": {"blocks": [b["id"] for b in blocks if b["kind"] in ("framework", "computation")]},
                       "produces": {"sections": ["Synthesis"]}})
    return blocks


def _chart_specs_for(state):
    """Derive chart specs from recorded computations, without inventing numbers."""
    specs = []
    computations = state.get("computations") or {}
    for key, data in computations.items():
        if not isinstance(data, dict) or not data.get("ok"):
            continue
        result = data.get("result") or {}
        if not isinstance(result, dict):
            continue
        # Only chart a computation that produced at least one numeric artifact.
        numeric = [name for name, value in result.items() if isinstance(value, (int, float, str)) and _is_number(value)]
        if not numeric:
            continue
        specs.append({"format": "bp-chart/1", "kind": "bar", "title": str(key).replace("_", " ").title(),
                      "series": [{"artifact": name, "label": name.replace("_", " ")} for name in numeric[:6]],
                      "source_computation": key, "artifact_ids": numeric[:6]})
    return specs


def _is_number(value):
    try:
        float(str(value).replace(",", ""))
        return True
    except (TypeError, ValueError):
        return False


def _evidence_ledger_for(state):
    """Build an evidence ledger from the current state without inventing sources."""
    claims = []
    for item in (state.get("evidence") or []):
        if isinstance(item, dict):
            claims.append({"id": item.get("id"), "text": item.get("claim"),
                           "type": "external", "block": None,
                           "source_ids": [item.get("source_id")] if item.get("source_id") else [],
                           "quote": item.get("quote")})
    numbers = []
    for key, data in (state.get("computations") or {}).items():
        if isinstance(data, dict) and data.get("ok"):
            result = data.get("result") or {}
            if isinstance(result, dict):
                for name, value in result.items():
                    numbers.append({"id": key + ":" + name, "value": value, "unit": None,
                                    "computation": key, "artifact": name})
    charts = []
    for spec in (state.get("chart_specs") or []):
        if isinstance(spec, dict):
            charts.append({"id": spec.get("source_computation"), "kind": spec.get("kind"),
                           "artifact_ids": spec.get("artifact_ids") or []})
    return {"format": "bp-evidence/1", "sources": list(state.get("sources") or []),
            "claims": claims, "numbers": numbers, "citations": [], "charts": charts,
            "gaps": list(state.get("gaps") or [])}


def confirm_plan(state):
    if state.get("stage") != "plan":
        raise ChatError("There is no plan waiting for confirmation.")
    state["stage"] = "research_ready"
    state["plan_confirmed_at"] = _now()
    state["plan_record"] = _freeze_plan(state)
    state["blocks"] = _plan_blocks(state)
    state["chart_specs"] = _chart_specs_for(state)
    try:
        from . import audit as _audit
        state["production_check"] = _audit.production_check(state.get("paper_contract"), {"blocks": state["blocks"]})
    except Exception:
        state["production_check"] = None
    answers = state.get("answers") or {}
    decision = str(answers.get("decision") or state.get("brief") or "").strip()
    style = str(answers.get("style") or "apa").strip().lower()
    if style not in ("apa", "harvard"):
        style = "apa"
    length = str(state.get("answers", {}).get("length") or "mid").strip().lower()
    if length not in ("short", "mid", "long"):
        length = "mid"
    scope = {
        "object": str(state.get("brief") or "")[:120],
        "period": str(answers.get("period") or "10"),
        "geography": str(answers.get("geography") or "Global"),
        "currency": "USD",
        "unit_of_analysis": str(state.get("subject") or "case"),
    }
    try:
        contract = paper_contract.make_contract(
            state.get("brief"), state.get("archetype") or "analytical_report",
            thesis=decision, decision=decision, scope=scope, length=length,
            style=style, required_sections=paper_families.required_sections_for(
                state.get("archetype") or "analytical_report"),
            rubric=state.get("rubric"), approved=True, approved_at=_now())
        # The export gate already enforces framework/profile sections via paper.missing.
        # The contract records the archetype's completeness contract; it does not add a
        # second, conflicting section list on top of it.
        contract["required_sections"] = []
        contract["hash"] = paper_contract.contract_hash(contract)
        state["paper_contract"] = paper_contract.freeze_contract(contract, approved_at=_now())
    except (ValueError, Exception):
        state["paper_contract"] = None
    state["updated_at"] = _now()
    return state


def _freeze_plan(state):
    """Freeze what the paper will be made of, so it can be re-derived and compared."""
    selection = state.get("selection") or {}
    record = {
        "format": verify.FORMAT,
        "brief_hash": verify.brief_hash(state.get("brief")),
        "catalogue_version": selection.get("catalogue_version"),
        "frameworks": list(selection.get("frameworks") or []),
        "capabilities": [{"key": row["key"], "because": row.get("because"),
                          "from": _chained_sources(state, row["key"])}
                         for row in selection.get("selected") or []],
        "figures": list(state.get("plan_figures") or []),
        "models": list(state.get("plan_models") or []),
        "decided_at": _now(),
    }
    return verify.freeze(record)


def replay_check(state):
    """Prove the frozen plan still hashes to what it was decided as."""
    record = state.get("plan_record") or {}
    if not record:
        return {"match": False, "plan_hash": None, "recomputed": None,
                "reason": "no plan has been frozen for this case"}
    fresh = verify.freeze(record)
    return {"match": fresh["plan_hash"] == record.get("plan_hash"),
            "plan_hash": record.get("plan_hash"), "recomputed": fresh["plan_hash"]}


def _recompute_guard(state):
    """Re-run every recorded computation from its stored inputs.

    A paper whose figure no longer follows from its own declared inputs must not
    be drafted.  The core is deterministic, so a mismatch means the record and the
    code disagree and a person has to look.
    """
    problems = []
    recorded = state.get("computations") or {}
    for row in (state.get("selection") or {}).get("selected") or []:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            continue
        if METHOD_RUN is None:
            return []
        try:
            fresh = METHOD_RUN(row["method"], data.get("inputs") or {})
        except Exception as error:
            problems.append(row["label"] + ": the recorded figures are no longer accepted ("
                            + str(error)[:120] + ")")
            continue
        if isinstance(fresh, dict):
            fresh_map = {str(k): str(v) for k, v in fresh.items()}
        else:
            try:
                output_key = capabilities.entry(row["key"]).get("output") or "value"
            except KeyError:
                output_key = "value"
            fresh_map = {output_key: str(fresh)}
        if fresh_map != (data.get("result") or {}):
            problems.append(row["label"] + ": the recorded figure no longer reproduces from its inputs")
    return problems


def attach_computation(state, key="breakeven", values=None):
    """Declare the figures for a capability the paper already carries (API action)."""
    if (state.get("profile") or "") == PROFILE_BUSINESS_PLAN:
        raise ChatError("A business plan carries its own computation blocks; attach nothing to it here.")
    if state.get("framework") in ("breakeven", "five_forces_breakeven"):
        raise ChatError("This paper already carries the break-even analysis.")
    wanted = str(key or "breakeven").strip().lower()
    if not capabilities.carries(state.get("selection"), wanted):
        # Declaring figures through this action is the student adding the
        # capability: the plan records it, and the paper then carries it.
        state = set_capability(state, wanted, True, "the figures were declared")
    return run_capability(state, wanted, values)


def run_capability(state, key, values):
    """Validate declared figures against the frozen schema, then run the core once.

    The product layer never computes: it checks that every required input is
    declared, calls the frozen method and stores its result unchanged.  A refusal
    is stored with the core's own message so the paper can name the gap instead
    of reporting a figure.
    """
    entry_row = capabilities.entry(key)
    if not capabilities.carries(state.get("selection"), entry_row["key"]):
        # Fail closed: a capability the paper does not carry is never run, so a
        # figure can never appear in a paper that did not plan for it.
        raise ChatError("This paper does not include " + entry_row["label"].lower()
                        + ". Add it in the plan first.")
    if state.get("stage") not in ("plan", "research_ready", "evidence", "evidence_reviewed", "draft"):
        raise ChatError("Finish the questions before declaring the figures.")
    values = values if isinstance(values, dict) else {}
    if isinstance(values.get("values"), dict):
        values = values["values"]
    inputs, problem = _capability_inputs(entry_row, values)
    store = state.setdefault("computations", {})
    if problem:
        # Keep what was declared: a refusal must not cost the student the typing,
        # and the paper can name exactly what the core was asked for.
        store[entry_row["key"]] = {"ok": False, "method": entry_row["method"],
                                   "inputs": inputs, "error": problem}
        raise ChatError(problem)
    if METHOD_RUN is None:
        store[entry_row["key"]] = {"ok": False, "method": entry_row["method"], "inputs": inputs,
                                   "error": "the frozen core is not attached"}
        raise ChatError("The frozen core is not attached; no figure is computed in the product layer.")
    try:
        output = METHOD_RUN(entry_row["method"], inputs)
    except Exception as error:
        store[entry_row["key"]] = {"ok": False, "method": entry_row["method"], "inputs": inputs,
                                   "error": str(error)[:500]}
        raise ChatError(entry_row["label"] + " refused the declared figures: " + str(error)[:200])
    if isinstance(output, dict):
        recorded = {str(name): str(value) for name, value in output.items()}
    else:
        # some methods return a bare value; the catalogue names the key
        recorded = {entry_row.get("output") or "value": str(output)}
    # Which declared inputs came from another frozen result, so the paper can say so.
    chained = {}
    for name, value in ((state.get("dependency_inputs") or {}).get(entry_row["key"]) or {}).items():
        if str(inputs.get(name)) == str(value):
            chained[name] = capabilities.NEEDS_FROM[entry_row["key"]][name][0]
    store[entry_row["key"]] = {"ok": True, "method": entry_row["method"], "inputs": inputs,
                               "result": recorded, "from": chained}
    state["computation"] = {"key": entry_row["key"], "inputs": inputs}
    # A result may now be able to supply another selected capability's input.
    apply_dependencies(state)
    if state.get("draft"):
        # The paper changed; the old draft would report the previous figures.
        state["draft"] = None
        if state.get("stage") == "draft":
            state["stage"] = "evidence"
    if state.get("stage") != "clarify":
        state["plan"] = _plan(state)
    state["updated_at"] = _now()
    return state


def _capability_inputs(entry_row, values):
    """Read the declared figures through the frozen schema; no default is invented."""
    schema = _schema_for(entry_row["method"])
    if not schema:
        return {}, ("The declared inputs for " + entry_row["label"].lower()
                    + " are not available; the frozen core is not attached.")
    inputs = {}
    forced = set(entry_row.get("require_inputs") or [])
    for name, spec in schema.items():
        required = spec.get("required", True) or name in forced
        desc = spec.get("desc") or name
        raw = values.get(name, "")
        kind = str(spec.get("type") or "")
        if kind == "records":
            rows = raw if isinstance(raw, list) else []
            if not rows and not required:
                continue
            fields = spec.get("fields") or {}
            parsed_rows = []
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    return inputs, "Row " + str(index) + " of the " + desc + " must be a set of values."
                parsed_row = {}
                for field, field_type in fields.items():
                    value = _clean(str(row.get(field, "")), 80)
                    if not value:
                        return inputs, ("Row " + str(index) + " of the " + desc + " needs a " + field
                                    + ".")
                    if field_type == "decimal":
                        try:
                            value = str(Decimal(value))
                        except (InvalidOperation, ValueError):
                            return inputs, ("Row " + str(index) + ": the " + field + " must be a number.")
                    parsed_row[field] = value
                parsed_rows.append(parsed_row)
            minimum = int(spec.get("min_items") or 1)
            if len(parsed_rows) < minimum:
                return inputs, "Declare at least " + str(minimum) + " rows for the " + desc + "."
            inputs[name] = parsed_rows
            continue
        if kind == "rows" or kind == "object":
            rows = raw if isinstance(raw, list) else []
            if not rows and not required:
                continue
            declared = (entry_row.get("row_fields") or {}).get(name) or []
            parsed_rows = []
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    return inputs, "Row " + str(index) + " of the " + desc + " must be a set of values."
                parsed = {}
                fields = declared or list(row.keys())
                for position, field in enumerate(fields):
                    value = row.get(field)
                    if field in ("branches", "activities"):
                        text = str(value if value is not None else "").strip()
                        if text:
                            parsed[field] = text
                        elif declared and position == 0:
                            return inputs, ("Row " + str(index) + " of the " + desc + " needs a "
                                            + field.replace("_", " ") + ".")
                        continue
                    text = _clean(str(value if value is not None else ""), 200)
                    if not text:
                        if declared and position == 0:
                            return inputs, ("Row " + str(index) + " of the " + desc + " needs a "
                                            + field.replace("_", " ") + ".")
                        continue
                    try:
                        parsed[field] = str(Decimal(text))
                    except (InvalidOperation, ValueError):
                        parsed[field] = text
                if not declared:
                    legacy_name = _clean(str(row.get("name") or row.get("id") or ""), 60)
                    if legacy_name:
                        parsed["name"] = legacy_name
                if not parsed:
                    return inputs, "Row " + str(index) + " of the " + desc + " is empty."
                parsed_rows.append(parsed)
            minimum = int(spec.get("min_items") or 1)
            if len(parsed_rows) < minimum:
                return inputs, "Declare at least " + str(minimum) + " rows for the " + desc + "."
            inputs[name] = parsed_rows
            continue
        if kind == "column_map":
            columns = raw if isinstance(raw, dict) else {}
            if not columns:
                if required:
                    return inputs, "Declare the " + desc + "."
                continue
            parsed_columns = {}
            for column, series in columns.items():
                label = _clean(str(column), 40)
                if not label:
                    return inputs, "Every column of the " + desc + " needs a name."
                items = series if isinstance(series, list) else re.split(r"[\n,;]+", str(series or ""))
                cleaned = [_clean(str(item), 40) for item in items if str(item).strip()]
                if not cleaned:
                    return inputs, "The " + label + " column has no values."
                parsed_values = []
                for item in cleaned:
                    try:
                        parsed_values.append(str(Decimal(item)))
                    except (InvalidOperation, ValueError):
                        return inputs, ("Every value in the " + label + " column of the " + desc
                                        + " must be a number.")
                parsed_columns[label] = parsed_values
            inputs[name] = parsed_columns
            continue
        if kind == "count_table" or kind == "value_matrix":
            if isinstance(raw, list):
                rows = raw
            else:
                rows = [line for line in str(raw or "").splitlines() if line.strip()]
            if not rows or not any(str(row).strip() for row in rows):
                if required:
                    return inputs, "Declare the " + desc + "."
                continue
            parsed_rows = []
            for index, row in enumerate(rows, start=1):
                cells = row if isinstance(row, list) else re.split(r"[,\s]+", str(row or ""))
                row_values = []
                for cell in cells:
                    text = _clean(str(cell), 20)
                    if not text:
                        continue
                    try:
                        number = Decimal(text)
                    except (InvalidOperation, ValueError):
                        return inputs, ("Row " + str(index) + " of the " + desc
                                        + " must be numbers.")
                    if kind == "count_table" and (number != number.to_integral() or number < 0):
                        return inputs, ("Row " + str(index) + " of the " + desc
                                        + " must be non-negative whole numbers.")
                    row_values.append(str(int(number)) if kind == "count_table" else str(number))
                if row_values:
                    parsed_rows.append(row_values)
            minimum = int(spec.get("min_rows") or 1)
            if len(parsed_rows) < minimum:
                return inputs, "Declare at least " + str(minimum) + " rows for the " + desc + "."
            inputs[name] = parsed_rows
            continue
        if kind.endswith("_list"):
            items = raw if isinstance(raw, list) else re.split(r"[\n,;]+", str(raw or ""))
            cleaned = [_clean(str(item), 40) for item in items if str(item).strip()]
            if not cleaned:
                if required:
                    return inputs, "Declare the " + desc + "."
                continue
            parsed = []
            for item in cleaned:
                try:
                    parsed.append(str(Decimal(item)))
                except (InvalidOperation, ValueError):
                    return inputs, "Every value of the " + desc + " must be a number."
            inputs[name] = parsed
            continue
        if kind == "enum":
            choice = _clean(str(raw or ""), 40)
            allowed = [str(value) for value in spec.get("values") or []]
            if not choice:
                if required:
                    return inputs, "Declare the " + desc + " (" + ", ".join(allowed) + ")."
                continue
            if allowed and choice not in allowed:
                return inputs, "The " + desc + " must be one of: " + ", ".join(allowed) + "."
            inputs[name] = choice
            continue
        if kind in ("currency", "text"):
            text = _clean(str(raw or ""), 80)
            if not text:
                if required:
                    return inputs, "Declare the " + desc + "."
                continue
            inputs[name] = text.upper() if kind == "currency" else text
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            raw = str(raw)
        text = _clean(str(raw), 40) if raw is not None else ""
        if not text:
            if required:
                return inputs, "Declare the " + desc + "."
            continue
        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            return inputs, "The " + desc + " must be a number."
        inputs[name] = str(number)
    if entry_row.get("domain") == "breakeven":
        for name in ("fixed", "price", "variable"):
            if name in inputs and Decimal(inputs[name]) < 0:
                return inputs, "A price or cost cannot be negative."
    groups = entry_row.get("one_of") or []
    if groups and not any(all(name in inputs for name in group) for group in groups):
        options = " or ".join(" + ".join(name.replace("_", " ") for name in group) for group in groups)
        return inputs, "Declare " + options + "."
    minimum = entry_row.get("min_inputs")
    if minimum and len(inputs) < int(minimum):
        return inputs, ("Declare at least " + str(minimum) + " of the declared figures for the "
                        + entry_row["label"].lower() + ".")
    if entry_row["key"] == "multi_criteria":
        criteria = inputs.get("criteria") or []
        names = [str(criterion.get("name")) for criterion in criteria]
        coupled = []
        for index, alternative in enumerate(inputs.get("alternatives") or [], start=1):
            raw = str(alternative.get("scores") or "")
            parts = [part for part in re.split(r"[,\s]+", raw) if part.strip()]
            if len(parts) != len(names):
                return inputs, ("Alternative " + str(index) + " needs one score for each of the "
                                + str(len(names)) + " criteria, in the order the criteria are listed.")
            scores = {}
            for name, part in zip(names, parts):
                try:
                    scores[name] = str(Decimal(part))
                except (InvalidOperation, ValueError):
                    return inputs, ("Alternative " + str(index) + ": every score must be a number.")
            coupled.append({"name": alternative.get("name"), "scores": scores})
        inputs["alternatives"] = coupled
    if entry_row["key"] == "decision_tree":
        rows = inputs.get("tree")
        if not isinstance(rows, list) or len(rows) < 1:
            return inputs, "Declare at least one alternative for the decision tree."
        alternatives = []
        for index, row in enumerate(rows, start=1):
            name = str(row.get("name") or ("Alternative " + str(index)))
            branches = [part for part in re.split(r"[\n;]+", str(row.get("branches") or ""))
                        if part.strip()]
            value = str(row.get("value") or "").strip()
            if branches:
                chance = []
                for branch in branches:
                    fields = [part.strip() for part in branch.split(",")]
                    if len(fields) < 3:
                        return inputs, ("Alternative " + str(index) + ": every branch needs a name, "
                                        "a probability and a value, comma-separated.")
                    try:
                        probability = Decimal(fields[1])
                        outcome = Decimal(fields[2])
                    except (InvalidOperation, ValueError):
                        return inputs, ("Alternative " + str(index) + ": the branch probability and "
                                        "value must be numbers.")
                    chance.append({"probability": str(probability),
                                   "node": {"type": "terminal", "value": str(outcome)}})
                total = sum(Decimal(branch["probability"]) for branch in chance)
                if total != 1:
                    return inputs, ("The branch probabilities of alternative " + str(index)
                                    + " must sum to one (found " + str(total) + ").")
                node = {"type": "chance", "branches": chance}
            elif value:
                try:
                    node = {"type": "terminal", "value": str(Decimal(value))}
                except (InvalidOperation, ValueError):
                    return inputs, "Alternative " + str(index) + ": the value must be a number."
            else:
                return inputs, ("Alternative " + str(index) + " needs a value or at least one branch.")
            alternatives.append({"name": name, "node": node})
        inputs = {"tree": {"type": "decision", "alternatives": alternatives}}
    if entry_row["key"] == "multi_project_schedule":
        projects = inputs.get("projects") or []
        expanded = []
        for index, project in enumerate(projects, start=1):
            lines = [line for line in re.split(r"[\n;]+", str(project.get("activities") or ""))
                     if line.strip()]
            if not lines:
                return inputs, ("Project " + str(index) + " needs at least one activity, one per line: "
                                "id, duration, resource, demand (and optional predecessors).")
            activities = []
            for line in lines:
                fields = [part.strip() for part in line.split(",")]
                if len(fields) < 4:
                    return inputs, ("Project " + str(index) + ": every activity needs id, duration, "
                                    "resource and demand, comma-separated.")
                activity = {"id": fields[0], "duration": fields[1], "resource": fields[2],
                            "demand": fields[3]}
                if len(fields) > 4 and fields[4]:
                    activity["predecessors"] = fields[4]
                activities.append(activity)
            expanded.append({"name": project.get("name"), "priority": project.get("priority") or "1",
                             "activities": activities})
        inputs["projects"] = expanded
    return inputs, None


def set_capability(state, key, enabled=True, reason=""):
    """Add or drop one capability at the plan stage, recording the student's decision."""
    if (state.get("profile") or "") == PROFILE_BUSINESS_PLAN:
        raise ChatError("A business plan carries its own computation blocks.")
    framework = state.get("framework") or "none"
    if framework in ("breakeven", "five_forces_breakeven"):
        raise ChatError("This paper already carries the break-even analysis.")
    try:
        selection = capabilities.set_enabled(state.get("selection") or {}, framework, key,
                                             bool(enabled), reason)
    except KeyError:
        raise ChatError("Unknown computation: " + str(key))
    except ValueError as error:
        raise ChatError(str(error))
    state["selection"] = selection
    _fill_capability_inputs(selection)
    if capabilities.carries(selection, key):
        # A capability added later still gets the figures the brief declared.
        apply_figures(state)
        apply_dependencies(state)
    if not capabilities.carries(selection, key):
        state.setdefault("computations", {}).pop(key, None)
        if (state.get("computation") or {}).get("key") == key:
            state["computation"] = None
        if state.get("draft"):
            state["draft"] = None
            if state.get("stage") == "draft":
                state["stage"] = "evidence"
    if state.get("stage") != "clarify":
        state["plan"] = _plan(state)
    state["updated_at"] = _now()
    return state


def _capability_status(state, row):
    recorded = (state.get("computations") or {}).get(row["key"]) or {}
    if recorded.get("ok"):
        return "recorded"
    if recorded.get("error"):
        return "refused"
    return "needed"


def _available_capabilities(framework, selected):
    """Capabilities the student may still add to this paper (never the embedded ones)."""
    chosen = {row["key"] for row in selected or []}
    rows = []
    for key, row in capabilities.ENTRIES.items():
        if key in chosen or framework not in row["applies_to"]:
            continue
        rows.append({"key": key, "label": row["label"], "slot": list(row["slot"]),
                     "because": {"rule": "student:added", "quote": ""}})
    return sorted(rows, key=lambda row: row["key"])


# ---------- business-plan profile: plan, inputs and computation ----------
def _level_ok(level):
    return level in PLAN_LEVELS


def _blocks_for(state_or_level):
    """The computation blocks a plan at this level requires, in display order."""
    if isinstance(state_or_level, dict):
        level = state_or_level.get("level") or "shs"
        dropped = set(state_or_level.get("dropped_sections") or [])
        profile = state_or_level.get("profile") or PROFILE_BUSINESS_PLAN
    else:
        level, dropped, profile = state_or_level, set(), PROFILE_BUSINESS_PLAN
    if profile == PROFILE_FEASIBILITY_STUDY:
        blocks_list = FEASIBILITY_BLOCKS
    elif profile == PROFILE_MARKETING_PLAN:
        blocks_list = MARKETING_BLOCKS
    elif profile == PROFILE_PROJECT_PROPOSAL:
        blocks_list = PROJECT_BLOCKS
    else:
        blocks_list = COMPUTATION_BLOCKS
    out = []
    for block in blocks_list:
        if block["section"] in dropped:
            continue
        if block["level"] == "shs" or level == "college":
            out.append(dict(block))
    return out


def _sections_for(level, dropped=None):
    dropped = set(dropped or [])
    return [dict(item) for item in PLAN_SECTIONS
            if (item.get("min_level") != "college" or level == "college") and item["key"] not in dropped]


#: Sections that open composition may leave out.  The strict convention keeps
#: every one of them; a strict plan is not silently shortened.
OPTIONAL_SECTIONS = {"marketing_plan", "operations_plan", "management", "risk", "impact"}


def _start_plan(brief, subject, level, mode, profile=PROFILE_BUSINESS_PLAN):
    if len(brief) < 15:
        raise ChatError("Describe the business and the plan in at least one sentence.")
    level = (level or "shs").strip().lower()
    mode = (mode or "strict").strip().lower()
    if not _level_ok(level):
        raise ChatError("Choose the senior-high-school or college level.")
    _modes = FEASIBILITY_MODES if profile == PROFILE_FEASIBILITY_STUDY else PLAN_MODES
    if mode not in _modes:
        raise ChatError("Choose the strict convention or open composition.")
    answers = _defaults(brief)
    answers["inputs"] = {}
    state = {"format": FORMAT, "subject": subject or "entrepreneurship", "framework": None,
             "frameworks": [], "profile": profile, "archetype": "plan_proposal", "paper_contract": None,
             "audit": None, "blocks": None, "evidence_ledger": None, "chart_specs": None,
             "production_check": None,
             "brief": brief, "created_at": _now(), "updated_at": _now(),
             "stage": "plan", "level": level, "mode": mode, "answers": answers, "questions": [],
             "question_index": 0, "sources": [], "evidence": [], "orientation_sources": [], "gaps": [], "notes": [],
             "computations": {}, "draft": None}
    state["plan"] = _plan_profile(state)
    return state


def _start_feasibility_study(brief, subject, level, mode):
    return _start_plan(brief, subject, level, mode, profile=PROFILE_FEASIBILITY_STUDY)


def _start_marketing_plan(brief, subject, level, mode):
    return _start_plan(brief, subject, level, mode, profile=PROFILE_MARKETING_PLAN)


def _start_project_proposal(brief, subject, level, mode):
    return _start_plan(brief, subject, level, mode, profile=PROFILE_PROJECT_PROPOSAL)


def _plan_profile(state):
    profile = state.get("profile") or PROFILE_BUSINESS_PLAN
    level = state.get("level") or "shs"
    if profile == PROFILE_FEASIBILITY_STUDY:
        levels = FEASIBILITY_LEVELS
        modes = FEASIBILITY_MODES
        dimensions = FEASIBILITY_DIMENSIONS
        fields = FEASIBILITY_FIELDS
        sections_list = FEASIBILITY_SECTIONS
        blocks_list = FEASIBILITY_BLOCKS
        optional = FEASIBILITY_OPTIONAL
        label = "Feasibility study"
        why = ("The study tests whether the proposed project should proceed, across market, technical, management, "
               "legal and financial dimensions, before any commitment is made.")
        misses = ("It does not invent a market, a demand, a cost or a forecast. Every number comes from the "
                  "declared inputs through the frozen core, and every gap is named.")
        output = ("A feasibility study with an executive summary, project description, market, technical, management, "
                  "legal and financial feasibility, risk analysis, a conclusion with a verdict and one reference list.")
    elif profile == PROFILE_MARKETING_PLAN:
        levels = MARKETING_LEVELS
        modes = MARKETING_MODES
        dimensions = MARKETING_DIMENSIONS
        fields = MARKETING_FIELDS
        sections_list = MARKETING_SECTIONS
        blocks_list = MARKETING_BLOCKS
        optional = MARKETING_OPTIONAL
        label = "Marketing plan"
        why = ("The plan composes your own description, the target audience, positioning, channels, tactics and "
               "budget into a measurable marketing plan.")
        misses = ("It does not invent a market, a customer, a cost or a forecast. Every number comes from the "
                  "declared inputs through the frozen core, and every gap is named.")
        output = ("A marketing plan with an executive summary, business context, audience and positioning, channels "
                  "and tactics, budget and measurement, risk analysis and a conclusion.")
    elif profile == PROFILE_PROJECT_PROPOSAL:
        levels = PROJECT_LEVELS
        modes = PROJECT_MODES
        dimensions = PROJECT_DIMENSIONS
        fields = PROJECT_FIELDS
        sections_list = PROJECT_SECTIONS
        blocks_list = PROJECT_BLOCKS
        optional = PROJECT_OPTIONAL
        label = "Project proposal"
        why = ("The proposal presents a defined, time-bound project with a documented need, objectives, activities, "
               "budget and measurable results.")
        misses = ("It does not invent a need, an activity, a cost or a result. Every number comes from the "
                  "declared inputs through the frozen core, and every gap is named.")
        output = ("A project proposal with an executive summary, project description, work plan and timeline, budget, "
                  "monitoring and evaluation, risk analysis and a conclusion.")
    else:
        levels = PLAN_LEVELS
        modes = PLAN_MODES
        dimensions = PLAN_DIMENSIONS
        fields = PLAN_FIELDS
        sections_list = PLAN_SECTIONS
        blocks_list = COMPUTATION_BLOCKS
        optional = OPTIONAL_SECTIONS
        label = "Business plan"
        why = ("The plan composes your own description, the retrieved market evidence and the plan-level "
               "computations in the order a reader expects: the business, the market, how it operates, the "
               "numbers, the risks and the conclusion.")
        misses = ("It does not invent a market, a customer, a cost or a forecast. Every number comes from the "
                  "declared inputs through the frozen core, and every gap is named.")
        output = ("A business plan with an executive summary, business description, market analysis, marketing "
                  "and operations plans, management, a Financial Plan with its computation blocks, a risk "
                  "analysis, a conclusion and one reference list.")
    dropped = state.get("dropped_sections") or []
    blocks = [dict(b) for b in blocks_list
              if (b["level"] == "shs" or level == "college")
              and b["section"] not in dropped]
    for block in blocks:
        block["input_schema"] = _schema_for(block["method"])
    secs = [dict(s) for s in sections_list
            if (s.get("min_level") != "college" or level == "college")
            and s["key"] not in dropped]
    all_fields = []
    for section in secs:
        for key, lbl, kind, required in fields.get(section["key"], []):
            all_fields.append({"key": key, "label": lbl, "section": section["key"], "type": kind,
                           "required": required})
    return {
        "profile": profile,
        "label": label,
        "mode": state.get("mode") or "strict",
        "mode_label": modes.get(state.get("mode") or "strict"),
        "level": level,
        "level_label": levels.get(level, level),
        "decision": state["answers"].get("decision") or state["brief"],
        "geography": state["answers"].get("geography") or "Global",
        "period": state["answers"].get("period") or "10",
        "style": state["answers"].get("style") or "apa",
        "sections": secs,
        "blocks": blocks,
        "fields": all_fields,
        "dimensions": [{"key": key, "label": lbl, "query": _query(state, key, cues), "cues": cues,
                        "category": category, "source_note": _source_note(category)}
                       for key, lbl, cues, category in dimensions],
        "why": why,
        "misses": misses,
        "output": output,
        "checkpoints": ["Confirm this plan", "Supply your inputs and the declared figures",
                        "Review the retrieved evidence", "Review the drafted plan"],
    }


def _schema_for(method):
    if METHOD_DESCRIBE is None:
        return {}
    try:
        return dict(METHOD_DESCRIBE(method).get("input_schema") or {})
    except (KeyError, ValueError, TypeError):
        return {}


def customise(state, changes):
    """Change the plan's level, mode or optional sections before confirmation.

    Strict mode keeps the standard sections; open composition may drop an
    optional one.  Nothing here adds a framework or invents a section.
    """
    if (state.get("profile") or "") not in (PROFILE_BUSINESS_PLAN, PROFILE_FEASIBILITY_STUDY, PROFILE_MARKETING_PLAN, PROFILE_PROJECT_PROPOSAL):
        raise ChatError("This case is not a business plan, feasibility study, marketing plan or project proposal.")
    if state.get("stage") != "plan":
        raise ChatError("Customise the plan before confirming it.")
    if not isinstance(changes, dict):
        raise ChatError("Customisation must be an object.")
    level = changes.get("level", state.get("level") or "shs")
    mode = changes.get("mode", state.get("mode") or "strict")
    if not _level_ok(level):
        raise ChatError("Choose the senior-high-school or college level.")
    modes = FEASIBILITY_MODES if state.get("profile") == PROFILE_FEASIBILITY_STUDY else PLAN_MODES
    if mode not in modes:
        raise ChatError("Choose the strict convention or open composition.")
    dropped = list(state.get("dropped_sections") or [])
    if "sections" in changes:
        wanted = changes.get("sections")
        if not isinstance(wanted, list):
            raise ChatError("sections must be a list of section keys to leave out.")
        if state.get("profile") == PROFILE_FEASIBILITY_STUDY:
            optional = FEASIBILITY_OPTIONAL
        elif state.get("profile") == PROFILE_MARKETING_PLAN:
            optional = MARKETING_OPTIONAL
        elif state.get("profile") == PROFILE_PROJECT_PROPOSAL:
            optional = PROJECT_OPTIONAL
        else:
            optional = OPTIONAL_SECTIONS
        unknown = sorted(set(wanted) - optional)
        if unknown:
            raise ChatError("These sections cannot be left out: " + ", ".join(unknown))
        if mode == "strict" and wanted:
            raise ChatError("The strict business-plan convention keeps the standard sections; choose open "
                            "composition to leave one out.")
        dropped = sorted(set(wanted))
    state["level"] = level
    state["mode"] = mode
    state["dropped_sections"] = dropped
    state["plan"] = _plan_profile(state)
    state["updated_at"] = _now()
    return state


def set_inputs(state, values):
    """Store student-supplied plan text.  Unknown fields are refused, not ignored."""
    if (state.get("profile") or "") not in (PROFILE_BUSINESS_PLAN, PROFILE_FEASIBILITY_STUDY, PROFILE_MARKETING_PLAN, PROFILE_PROJECT_PROPOSAL):
        raise ChatError("This case is not a business plan, feasibility study, marketing plan or project proposal.")
    if state.get("stage") not in ("plan", "research_ready", "inputs", "evidence", "evidence_reviewed", "computed"):
        raise ChatError("The plan is not accepting inputs at this stage.")
    if not isinstance(values, dict):
        raise ChatError("Inputs must be an object of field names and values.")
    if state.get("profile") == PROFILE_FEASIBILITY_STUDY:
        _fields = FEASIBILITY_FIELDS
    elif state.get("profile") == PROFILE_MARKETING_PLAN:
        _fields = MARKETING_FIELDS
    elif state.get("profile") == PROFILE_PROJECT_PROPOSAL:
        _fields = PROJECT_FIELDS
    else:
        _fields = PLAN_FIELDS
    allowed = {key: (label, kind) for section in _fields.values()
               for key, label, kind, _required in section}
    stored = dict(state["answers"].get("inputs") or {})
    for key, raw in values.items():
        if key not in allowed:
            raise ChatError("Unknown plan field %r." % key)
        label, kind = allowed[key]
        if kind == "items":
            items = _items(raw, limit=8)
            stored[key] = items
        else:
            text = _clean(raw, 2000)
            if text:
                stored[key] = text
            else:
                stored.pop(key, None)
    state["answers"]["inputs"] = stored
    state["draft"] = None
    state["updated_at"] = _now()
    return state


def _missing_fields(state):
    supplied = state["answers"].get("inputs") or {}
    missing = []
    profile = state.get("profile") or PROFILE_BUSINESS_PLAN
    if profile == PROFILE_FEASIBILITY_STUDY:
        sections_list = FEASIBILITY_SECTIONS
        fields = FEASIBILITY_FIELDS
    elif profile == PROFILE_MARKETING_PLAN:
        sections_list = MARKETING_SECTIONS
        fields = MARKETING_FIELDS
    elif profile == PROFILE_PROJECT_PROPOSAL:
        sections_list = PROJECT_SECTIONS
        fields = PROJECT_FIELDS
    else:
        sections_list = PLAN_SECTIONS
        fields = PLAN_FIELDS
    keys = {section["key"] for section in sections_list
            if (section.get("min_level") != "college" or level == "college")
            and section["key"] not in (state.get("dropped_sections") or [])}
    for section_key, flds in fields.items():
        if section_key not in keys:
            continue
        for key, label, _kind, required in flds:
            if required and not supplied.get(key):
                missing.append(label)
    return missing


def compute(state, values):
    """Run every required plan block through the attached frozen core.

    A block that refuses keeps its reason; the draft and the export gate then
    name it.  Nothing is computed in this module.
    """
    if (state.get("profile") or "") not in (PROFILE_BUSINESS_PLAN, PROFILE_FEASIBILITY_STUDY, PROFILE_MARKETING_PLAN, PROFILE_PROJECT_PROPOSAL):
        raise ChatError("This case is not a business plan, feasibility study, marketing plan or project proposal.")
    if not state.get("plan_confirmed_at"):
        raise ChatError("Confirm the plan before computing it.")
    if METHOD_RUN is None:
        raise ChatError("The frozen core is not attached; no plan figure is computed in the product layer.")
    if not isinstance(values, dict):
        raise ChatError("Computations must be an object of block keys and their inputs.")
    blocks = {block["key"]: block for block in _blocks_for(state)}
    unknown = sorted(set(values) - set(blocks))
    if unknown:
        raise ChatError("Unknown computation block(s): " + ", ".join(unknown))
    results = dict(state.get("computations") or {})
    for key, block in blocks.items():
        if key not in values:
            results.pop(key, None)
            continue
        inputs = values.get(key)
        if not isinstance(inputs, dict):
            results[key] = {"ok": False, "method": block["method"], "error": "the inputs must be an object"}
            continue
        try:
            output = METHOD_RUN(block["method"], inputs)
        except Exception as error:
            results[key] = {"ok": False, "method": block["method"], "inputs": inputs,
                            "error": str(error)[:500]}
            continue
        results[key] = {"ok": True, "method": block["method"], "inputs": inputs,
                        "result": {str(k): str(v) for k, v in dict(output).items()}}
    state["computations"] = results
    state["stage"] = "computed"
    state["draft"] = None
    state["updated_at"] = _now()
    return state



def _year_from(state):
    try:
        years = int(state["answers"].get("period", "10"))
    except (TypeError, ValueError):
        years = 10
    return datetime.datetime.now(datetime.timezone.utc).year - years if years > 0 else None


def _first_sentence(source):
    """The quote used as one evidence item (one sentence, as the conductor records it)."""
    return retrieval.first_sentence(source, sentences=1, limit=500)


#: The ranking and the country list live in the shared engine; these names stay
#: for callers that read them, so there is one implementation, not two.
_rank = retrieval.rank_item
_specific_words = retrieval.specific_words
_geo_words = retrieval.geo_words
_country = retrieval.country


def _research_one(state, dimension, corpus_doc_counts=None):
    """One dimension, through the shared retrieval engine.

    The worksheet completion calls the same function with the same gate, so the
    same brief returns the same evidence on both surfaces.
    """
    import time as _time
    started = _time.perf_counter()
    topic_words = set(_topic(state["answers"].get("decision") or state["brief"]))
    country = retrieval.country(state["answers"].get("decision") or "") or retrieval.country(state["brief"])
    context = set(country.lower().split()) if country else retrieval.specific_words(topic_words)
    geography = state["answers"].get("geography") or "Global"
    gate = _gate_for(state)
    found = retrieval.retrieve(
        key=dimension["key"], cues=dimension.get("cues") or "", queries=[dimension["query"]],
        context=sorted(context), geography=geography, year_from=_year_from(state),
        category=dimension.get("category"), gate=gate, max_items=3, academic_limit=4, web_limit=3,
        corpus_doc_cap=3, corpus_doc_counts=corpus_doc_counts)
    notice = "; ".join(found.get("notices") or []) or None
    return {"dimension": dimension, "found": found.get("items") or [],
            "errors": found.get("errors") or [], "skipped": found.get("skipped") or [],
            "notice": notice, "dropped": found.get("dropped") or 0,
            "elapsed": round(_time.perf_counter() - started, 2),
            "academic_cached": bool(found.get("academic_cached")),
            "web_cached": bool(found.get("web_cached")),
            "database_timings": found.get("database_timings") or {}}


#: The conductor's framework keys that own a profile, so the chat uses the same
#: gate as the worksheet instead of a second copy of the rules.
PROFILE_FOR = {"pestel": "template_pestel", "pestel_swot": "template_pestel",
               "five_forces": "template_five_forces",
               "five_forces_breakeven": "template_five_forces"}


def _gate_for(state):
    profile = framework_profiles.get(PROFILE_FOR.get(state.get("framework") or ""))
    return profile.get("gate") if profile else None


def research(state):
    """Retrieve per-dimension evidence.  The plan must be confirmed first."""
    if state.get("stage") != "research_ready":
        raise ChatError("Confirm the plan before retrieving sources.")
    sources, evidence, gaps, notes = [], [], [], []
    orientation = []
    seen_orientation = set()
    seen_sources, seen_evidence = set(), set()
    errors, skipped, notices = [], set(), set()
    dropped = 0
    started = time.perf_counter()

    # Q-16: one corpus document may not supply every dimension of a paper.
    # corpus_doc_counts is shared across dimensions so the cap holds per-paper.
    corpus_doc_counts = {}
    pool = ThreadPoolExecutor(max_workers=max(1, len(state["plan"]["dimensions"])))
    futures = {pool.submit(_research_one, state, dimension, corpus_doc_counts): dimension
               for dimension in state["plan"]["dimensions"]}
    done, pending = wait(futures, timeout=RESEARCH_DEADLINE)
    for future in pending:
        future.cancel()
    pool.shutdown(wait=False, cancel_futures=True)
    batches = []
    for future in done:
        try:
            batches.append(future.result())
        except Exception as error:
            dimension = futures[future]
            batches.append({"dimension": dimension, "found": [], "errors": [], "skipped": [],
                            "notice": "Research failed: " + str(error)[:160], "dropped": 0,
                            "elapsed": 0.0, "academic_cached": False, "web_cached": False,
                            "database_timings": {}})
    for future in pending:
        dimension = futures[future]
        batches.append({"dimension": dimension, "found": [], "errors": [], "skipped": [],
                        "notice": "Research timed out.", "dropped": 0,
                        "elapsed": RESEARCH_DEADLINE, "academic_cached": False,
                        "web_cached": False, "database_timings": {}, "timed_out": True})
    order = {d["key"]: index for index, d in enumerate(state["plan"].get("dimensions") or [])}
    batches.sort(key=lambda batch: order.get(batch["dimension"]["key"], 99))
    timed_out = False
    for batch in batches:
        dimension = batch["dimension"]
        errors.extend({**error, "dimension": dimension["key"]} for error in batch["errors"])
        skipped.update(item.get("database") for item in batch["skipped"] if item.get("database"))
        dropped += batch["dropped"]
        if batch.get("timed_out"):
            timed_out = True
        if batch["notice"]:
            notices.add(batch["notice"])
        placed = 0
        for item in batch["found"]:
            quote = _first_sentence(item)
            key = (item.get("doi") or _clean(item.get("title"), 120).lower())
            if not quote or not key or key in seen_evidence:
                continue
            seen_evidence.add(key)
            if key not in seen_sources:
                seen_sources.add(key)
                source = dict(item)
                source["id"] = "S" + str(len(sources) + 1)
                sources.append(source)
            source_id = next(source["id"] for source in sources
                             if (source.get("doi") or _clean(source.get("title"), 120).lower()) == key)
            evidence.append({"id": "E" + str(len(evidence) + 1), "dimension": dimension["key"],
                             "claim": quote, "quote": quote, "source_id": source_id,
                             "status": "proposed"})
            placed += 1
            if placed >= 3:
                break
        for item in (batch.get("orientation") or []):
            key = (item.get("doi") or _clean(item.get("title"), 120).lower())
            if key and key not in seen_orientation:
                seen_orientation.add(key)
                orientation.append(dict(item))
        if placed == 0:
            reason = ("Research timed out before this dimension returned evidence"
                      if batch.get("timed_out")
                      else "No retrieved source supplied an abstract sentence for this dimension")
            gaps.append({"dimension": dimension["key"], "label": dimension["label"], "reason": reason})
    if timed_out:
        notes.append("Research stopped after %d seconds; incomplete dimensions are named as gaps." % RESEARCH_DEADLINE)
    if notices:
        notes.extend(sorted(notices))
    if dropped:
        notes.append(str(dropped) + " retrieved source(s) were dropped as off-topic for the decision.")
    if skipped:
        notes.append("Skipped until configured: " + ", ".join(sorted(skipped)))
    if errors:
        notes.append("Some databases were unavailable: " + ", ".join(sorted({error["database"] for error in errors})))
    timings = {"total_s": round(time.perf_counter() - started, 2),
               "dimensions": {batch["dimension"]["key"]: batch["elapsed"] for batch in batches},
               "academic_cached": sum(1 for batch in batches if batch["academic_cached"]),
               "web_cached": sum(1 for batch in batches if batch["web_cached"])}
    state.update({"sources": sources, "evidence": evidence, "orientation_sources": orientation,
                  "gaps": gaps, "notes": notes,
                  "research_errors": errors, "researched_at": _now(), "stage": "evidence",
                  "timings": timings, "updated_at": _now()})
    return state


def _in_text(source, style, numbers=None):
    global _CITATION_NUMBERS
    if numbers is None:
        numbers = _CITATION_NUMBERS
    return writing.in_text(source, style, numbers=numbers)


def _reference(source, style, numbers=None):
    global _CITATION_NUMBERS
    if numbers is None:
        numbers = _CITATION_NUMBERS
    return writing.reference(source, style, numbers=numbers)


def _dimension_lines(dimension, evidence, by_id, style, target=0):
    key = dimension[0]
    items = [item for item in evidence if item["dimension"] == key]
    if not items:
        return ["No retrieved evidence covered this dimension."]
    lines = []
    for item in items:
        source = by_id.get(item["source_id"], {})
        lines.append(_clean(item["quote"], 500) + " " + _in_text(source, style) + ".")
    reading = _reading_line(dimension, evidence, target, by_id)
    if reading:
        lines.append(reading)
    return lines


def _internal_lines(answers, key, label, noun=None):
    items = answers.get(key) or []
    thing = noun or label.lower()
    if not items:
        return ["No " + thing + " were supplied."]
    return ["The case identifies the following " + thing + ": " + "; ".join(items) + "."]


def _figure_cells(answers, evidence, by_id, style, framework):
    """One cell per framework cell: the student's own words and the sources.

    An internal cell carries the student's own list entries.  An external cell
    carries the source's title and its citation - the identity of the evidence,
    not its prose, which the section below already quotes in full.
    """
    cells = {}
    if framework in ("swot", "pestel_swot"):
        for key, label in (("strengths", "Strengths"), ("weaknesses", "Weaknesses")):
            items = answers.get(key) or []
            cells[key] = {"label": label, "bullets": list(items),
                          "gap": None if items else
                          "No " + label.lower() + " were supplied."}
        if framework == "swot":
            external = {"opportunities": [], "threats": []}
            for item in evidence:
                dimension = item.get("dimension")
                if dimension in external:
                    external[dimension].append(item)
        else:
            external, _unclassified = _classify_external(evidence)
        for key, label in (("opportunities", "Opportunities"), ("threats", "Threats")):
            bullets = []
            for item in external.get(key) or []:
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "No retrieved evidence covered this quadrant. "
                          "not a finding."}
    if framework == "ansoff":
        for dimension in ANSOFF_DIMENSIONS:
            key, label = dimension[0], dimension[1]
            bullets = []
            for item in evidence:
                if item.get("dimension") != key:
                    continue
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "No retrieved evidence covered this option. "
                          "not a finding."}
    if framework == "value_chain":
        for dimension in VALUE_DIMENSIONS:
            key, label = dimension[0], dimension[1]
            bullets = []
            for item in evidence:
                if item.get("dimension") != key:
                    continue
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "No retrieved evidence covered this activity. "
                          "not a finding."}
    if framework == "vrio":
        for key, label, noun in (("valuable", "Valuable", "value judgments"),
                                 ("rare", "Rare", "rarity judgments"),
                                 ("costly", "Costly to imitate", "imitation-cost judgments"),
                                 ("organized", "Organised to capture value", "organisational judgments")):
            items = answers.get(key) or []
            cells[key] = {"label": label, "bullets": list(items),
                          "gap": None if items else
                          "No " + noun + " were supplied."}
    return cells


POSITIVE = {"growth", "demand", "innovation", "investment", "digital", "expansion", "reform",
            "opportunity", "recovery", "young", "urban", "internet", "trade", "agreement"}
NEGATIVE = {"sanction", "restriction", "inflation", "risk", "crisis", "decline", "conflict",
            "unemployment", "shortage", "control", "blackout", "barrier", "pressure", "uncertainty"}


def _classify_external(evidence):
    """Map accepted external evidence to opportunities or threats by keyword."""
    buckets = {"opportunities": [], "threats": []}
    unclassified = 0
    for item in evidence:
        words = set(re.findall(r"[a-z][a-z0-9'-]+", _clean(item.get("quote"), 1200).lower()))
        positive, negative = len(words & POSITIVE), len(words & NEGATIVE)
        if positive > 2 * negative:
            buckets["opportunities"].append(item)
        elif negative > positive:
            buckets["threats"].append(item)
        else:
            unclassified += 1
    return buckets, unclassified


def _mapped_lines(items, by_id, style, label):
    if not items:
        return ["The accepted evidence did not support this part of the matrix."]
    labels = {key: name for key, name, _cues, _category in DIMENSIONS}
    lines = []
    for item in items[:5]:
        source = by_id.get(item["source_id"], {})
        origin = labels.get(item["dimension"], item["dimension"])
        lines.append(_clean(item["quote"], 500) + " " + _in_text(source, style)
                     + " (from the " + origin + " dimension).")
    return lines


def _fmt_number(value):
    number = Decimal(str(value))
    return "{:,.0f}".format(number) if number == number.to_integral() else "{:,.2f}".format(number)


#: The break-even figure is computed by the frozen core, never in this module.
#: The server attaches the core callable at import; a product-only caller must
#: attach it explicitly or the draft refuses rather than reimplement the formula.
COMPUTE = None

#: Plan blocks run through the same attached core.  `METHOD_RUN` validates and
#: executes one method; `METHOD_DESCRIBE` supplies the declared input schema so
#: the plan can render a form without importing the method library here.
METHOD_RUN = None
METHOD_DESCRIBE = None


def set_method_compute(run, describe=None):
    global METHOD_RUN, METHOD_DESCRIBE
    METHOD_RUN = run
    if describe is not None:
        METHOD_DESCRIBE = describe


def set_compute(fn):
    global COMPUTE
    COMPUTE = fn


def _break_even_lines(answers, result=None):
    try:
        fixed = Decimal(str(answers.get("fixed", "")))
        price = Decimal(str(answers.get("price", "")))
        variable = Decimal(str(answers.get("variable", "")))
    except (InvalidOperation, ValueError):
        raise ChatError("The break-even inputs must be numbers.")
    declared = {"fixed": str(fixed), "price": str(price), "variable": str(variable)}
    expected = str(answers.get("expected") or "").strip()
    if expected:
        try:
            declared["expected_units"] = str(Decimal(expected))
        except (InvalidOperation, ValueError):
            raise ChatError("Expected volume must be a number.")
    if result is None:
        if COMPUTE is None:
            raise ChatError("The break-even engine is not attached; no figure is computed in the product layer.")
        try:
            result = COMPUTE(declared)
        except Exception as error:
            raise ChatError("Break-even could not be computed: " + str(error)[:200])
    lines = ["At a declared fixed cost of " + _fmt_number(fixed) + ", a price of " + _fmt_number(price)
             + " per unit and a variable cost of " + _fmt_number(variable) + " per unit, the break-even quantity is "
             + _fmt_number(result["breakeven_units"]) + " units and the break-even revenue is "
             + _fmt_number(result["breakeven_revenue"]) + "."]
    lines.append("The contribution margin is " + _fmt_number(result["contribution_margin"]) + " per unit ("
                 + "{:.1f}".format(float(result["contribution_margin_ratio"]) * 100) + "% of the price).")
    if "margin_of_safety_units" in result:
        lines.append("At the declared expected volume, the margin of safety is "
                     + _fmt_number(result["margin_of_safety_units"]) + " units.")
    return lines


#: One deterministic formatter per capability: it reads the frozen result and
#: prints it.  No capability branch, no formula and no default lives in `draft`.
#: A capability without a bespoke formatter falls back to `_generic_lines`, which
#: quotes the recorded output and claims nothing beyond it.
CAPABILITY_LINES = {"breakeven": lambda row, inputs, result: _break_even_lines(inputs, result),
                    "npv": lambda row, inputs, result: _npv_lines(row, inputs, result)}


def _npv_lines(row, inputs, result):
    """Net present value from the declared flows.  Arithmetic, never advice."""
    rate = Decimal(str(inputs.get("rate", "0")))
    flows = inputs.get("cashflows") or []
    figure = result.get("npv")
    lines = ["At a declared discount rate of " + _fmt_exact(rate * 100) + "% and the declared cash flows ("
             + "; ".join(_fmt_exact(value) for value in flows) + "), the net present value is "
             + _fmt_number(figure) + "."]
    lines.append("A positive net present value means the declared flows recover the declared discount rate; a "
                 "negative one means they do not. The figure is arithmetic on the declared flows and the "
                 "declared rate, not a forecast.")
    return lines


def _pct(value):
    """A declared rate or ratio as a percentage, rounded to the paper's two decimals."""
    try:
        return _fmt_number(Decimal(str(value)) * 100)
    except (InvalidOperation, ValueError):
        return str(value)


def _money(value):
    try:
        return _fmt_number(value)
    except (InvalidOperation, ValueError):
        return str(value)


def _irr_lines(row, inputs, result):
    flows = inputs.get("cashflows") or []
    roots = result.get("n_roots")
    lines = ["At the declared cash flows (" + "; ".join(_fmt_exact(value) for value in flows)
             + "), the internal rate of return is " + _pct(result.get("irr"))
             + " - the rate at which the declared flows have a net present value of zero (here "
             + _money(result.get("npv_at_irr")) + ")."]
    if roots is not None and str(roots) != "1":
        lines.append("The declared flows change sign " + str(roots)
                     + " times, so the rate is not unique; the figure is the rate the method reports.")
    lines.append("It is the rate the declared flows earn, not a forecast of what they will earn.")
    return lines


def _payback_lines(row, inputs, result):
    rate = Decimal(str(inputs.get("rate", "0")))
    flows = inputs.get("cashflows") or []
    period = result.get("discounted_payback")
    lines = ["At a declared discount rate of " + _fmt_exact(rate * 100) + "%, the declared cash flows ("
             + "; ".join(_fmt_exact(value) for value in flows) + ") recover the outlay in "
             + _fmt_number(period) + " periods (inside period "
             + _fmt_exact(result.get("recovered_in_period")) + ")."]
    lines.append("The figure is arithmetic on the declared flows and rate; it says nothing about flows "
                 "beyond the ones declared.")
    return lines


def _project_metrics_lines(row, inputs, result):
    rate = Decimal(str(inputs.get("rate", "0")))
    lines = ["At a declared discount rate of " + _fmt_exact(rate * 100) + "%, the declared project has a net "
             "present value of " + _money(result.get("npv")) + ", a profitability index of "
             + _fmt_number(result.get("profitability_index")) + ", a modified internal rate of return of "
             + _pct(result.get("mirr")) + " and an equivalent annual annuity of "
             + _money(result.get("equivalent_annual_annuity")) + "."]
    lines.append("Each figure is the frozen method's output for the declared flows and rate; none of them is a "
                 "forecast.")
    return lines


def _unit_economics_lines(row, inputs, result):
    margin = _money(result.get("unit_margin"))
    lines = ["At a declared price of " + _money(inputs.get("price")) + " and a variable cost of "
             + _money(inputs.get("variable_cost")) + ", the unit margin is " + margin + " ("
             + _pct(result.get("margin_pct")) + "% of the price)."]
    if result.get("payback_periods") not in (None, ""):
        lines.append("The declared acquisition cost of " + _money(inputs.get("acquisition_cost"))
                     + " is covered after " + _fmt_number(result.get("payback_periods"))
                     + " periods of that margin.")
    else:
        lines.append("No payback period is reported: the declared margin cannot recover the declared "
                     "acquisition cost.")
    return lines


def _wacc_lines(row, inputs, result):
    lines = ["With declared equity of " + _money(inputs.get("equity_value")) + " (weight "
             + _pct(result.get("weight_equity")) + "%) and debt of " + _money(inputs.get("debt_value"))
             + " (weight " + _pct(result.get("weight_debt")) + "%), the weighted average cost of capital is "
             + _pct(result.get("wacc")) + "%, from a declared cost of equity of "
             + _pct(result.get("cost_of_equity")) + "% and an after-tax cost of debt of "
             + _pct(result.get("cost_of_debt_after_tax")) + "%."]
    lines.append("Every rate is the student's declaration; the method weights them and does not estimate them.")
    return lines


def _cash_runway_lines(row, inputs, result):
    monthly = Decimal(str(inputs.get("monthly_net_cash_flow", "0")))
    opening = inputs.get("opening_cash")
    runway = result.get("runway_months")
    if runway in (None, ""):
        lines = ["With declared opening cash of " + _money(opening) + " and a monthly net cash flow of "
                 + _money(monthly) + ", the declared cash does not run out."]
    else:
        lines = ["With declared opening cash of " + _money(opening) + " and a monthly net cash flow of "
                 + _money(monthly) + ", the cash runway is " + _fmt_exact(runway) + " months."]
    if result.get("funding_gap") not in (None, ""):
        lines.append("At the declared target, the cash balance is " + _money(result.get("cash_at_target_month"))
                     + " and the funding gap is " + _money(result.get("funding_gap")) + ".")
    lines.append("The projection holds the declared monthly flow constant; it is not a forecast.")
    return lines


def _market_sizing_lines(row, inputs, result):
    lines = ["From a declared target population of " + _money(inputs.get("target_population"))
             + ", an annual spend per customer of " + _money(inputs.get("annual_spend_per_customer"))
             + " and declared shares of " + _pct(inputs.get("serviceable_share")) + "% and "
             + _pct(inputs.get("obtainable_share")) + "%, the total addressable market is "
             + _money(result.get("total_addressable_market")) + ", the serviceable available market is "
             + _money(result.get("serviceable_available_market")) + " and the serviceable obtainable market is "
             + _money(result.get("serviceable_obtainable_market")) + "."]
    lines.append("The three sizes are arithmetic on the declared population, spend and shares; the shares are "
                 "the student's assumption, not a retrieved estimate.")
    return lines


def _market_share_lines(row, inputs, result):
    lines = ["With declared firm sales of " + _money(inputs.get("firm_sales")) + " in a declared market of "
             + _money(inputs.get("market_sales")) + ", the market share is "
             + _pct(result.get("market_share")) + "%."]
    lines.append("The figure is the declared sales as a share of the declared market; neither number is retrieved.")
    return lines


def _clv_lines(row, inputs, result):
    lines = ["At a declared margin of " + _money(inputs.get("margin_per_period")) + " per period and a declared "
             "churn rate of " + _pct(inputs.get("churn_rate")) + "% per period, the undiscounted lifetime value is "
             + _money(result.get("clv_undiscounted")) + "."]
    if result.get("clv_discounted") not in (None, ""):
        lines.append("Discounted at the declared rate over the declared horizon, the lifetime value is "
                     + _money(result.get("clv_discounted")) + ".")
    lines.append("The figure follows from the declared margin and churn; the method does not estimate either.")
    return lines


def _earned_value_lines(row, inputs, result):
    lines = ["Against a declared planned value of " + _money(inputs.get("planned_value")) + " and an actual cost "
             "of " + _money(inputs.get("actual_cost")) + ", the declared earned value of "
             + _money(inputs.get("earned_value")) + " gives a schedule variance of "
             + _money(result.get("schedule_variance")) + " and a cost variance of "
             + _money(result.get("cost_variance")) + "."]
    lines.append("The schedule performance index is " + _fmt_exact(result.get("spi"))
                 + " and the cost performance index is " + _fmt_exact(result.get("cpi"))
                 + "; the estimate at completion is " + _money(result.get("estimate_at_completion")) + ".")
    lines.append("Every figure is computed from the declared values; none is measured or forecast.")
    return lines


def _multi_breakeven_lines(row, inputs, result):
    products = inputs.get("products") or []
    described = "; ".join(
        str(product.get("name", "")) + " at " + _money(product.get("price")) + " with a variable cost of "
        + _money(product.get("variable_cost")) + " and a mix of " + _fmt_exact(product.get("mix_units"))
        for product in products)
    lines = ["With declared fixed costs of " + _money(inputs.get("fixed_costs")) + " and "
             + str(len(products)) + " products (" + described + "), the weighted contribution is "
             + _money(result.get("weighted_contribution")) + " per unit of the mix."]
    units = []
    for product in products:
        value = result.get("units_" + str(product.get("name", "")))
        if value not in (None, ""):
            units.append(_fmt_number(value) + " of " + str(product.get("name", "")))
    lines.append("Break-even is " + _fmt_number(result.get("breakeven_total_units")) + " units in total"
                 + (" (" + ", ".join(units) + ")" if units else "") + ", for revenue of "
                 + _money(result.get("breakeven_revenue")) + ".")
    lines.append("The mix is the student's declaration; the method does not forecast demand for any product.")
    return lines


def _capm_lines(row, inputs, result):
    lines = ["At a declared risk-free rate of " + _pct(inputs.get("risk_free_rate")) + "% and an expected market "
             "return of " + _pct(inputs.get("market_return")) + "%, with a declared beta of "
             + _fmt_exact(result.get("beta")) + ", the cost of equity is "
             + _pct(result.get("cost_of_equity")) + "% (market risk premium "
             + _pct(result.get("market_risk_premium")) + "%)."]
    lines.append("The rate follows from the declared inputs; neither the beta nor the market return is "
                 "estimated by the paper.")
    return lines


def _bond_lines(row, inputs, result):
    coupon = _pct(inputs.get("coupon_rate"))
    if str(inputs.get("yield_to_maturity") or "").strip():
        head = ("With a declared face value of " + _money(inputs.get("face_value")) + ", a " + coupon
                + "% annual coupon and " + _fmt_exact(inputs.get("years_to_maturity"))
                + " years to maturity, a declared yield of " + _pct(inputs.get("yield_to_maturity"))
                + "% prices the bond at " + _money(result.get("price")) + ".")
    else:
        head = ("With a declared face value of " + _money(inputs.get("face_value")) + ", a " + coupon
                + "% annual coupon and " + _fmt_exact(inputs.get("years_to_maturity"))
                + " years to maturity, the declared price of " + _money(inputs.get("price"))
                + " solves to a yield of " + _pct(result.get("yield_to_maturity")) + "%.")
    lines = [head, "The Macaulay duration is " + _money(result.get("macaulay_duration"))
             + " years, the modified duration is " + _money(result.get("modified_duration"))
             + ", the convexity is " + _money(result.get("convexity"))
             + " and the DV01 is " + _money(result.get("dv01")) + "."]
    lines.append("Every figure is computed from the declared bond terms; nothing is retrieved from a market.")
    return lines


_RATIO_LABELS = (("current_ratio", "current ratio", "x"), ("quick_ratio", "quick ratio", "x"),
                 ("gross_margin", "gross margin", "%"), ("net_margin", "net margin", "%"),
                 ("return_on_assets", "return on assets", "%"), ("return_on_equity", "return on equity", "%"),
                 ("equity_multiplier", "equity multiplier", "x"), ("asset_turnover", "asset turnover", "x"),
                 ("inventory_days", "inventory days", "days"))


def _ratio_lines(row, inputs, result):
    parts = []
    for key, label, kind in _RATIO_LABELS:
        value = result.get(key)
        if value in (None, ""):
            continue
        if kind == "%":
            parts.append(label + " " + _pct(value) + "%")
        elif kind == "days":
            parts.append(label + " " + _fmt_number(value))
        else:
            # A ratio is reported at the paper's two decimals, never as the core's
            # full 50-digit Decimal: a marker reads a ratio, not a bit pattern.
            parts.append(label + " " + _fmt_number(value))
    count = result.get("n_computed")
    lines = ["From the declared figures, the method computes " + str(count or len(parts)) + " ratio(s)"
             + (": " + "; ".join(parts) if parts else "") + "."]
    lines.append("Each ratio is arithmetic on the declared statement figures; a ratio with a missing "
                 "declared input is not reported.")
    return lines


def _dcf_lines(row, inputs, result):
    rate = Decimal(str(inputs.get("discount_rate", "0")))
    flows = inputs.get("cashflows") or []
    lines = ["At a declared discount rate of " + _fmt_exact(rate * 100) + "%, the declared free cash flows ("
             + "; ".join(_fmt_exact(value) for value in flows) + ") have a present value of "
             + _money(result.get("pv_explicit")) + "."]
    if str(inputs.get("terminal_growth") or "").strip():
        lines.append("With a declared terminal growth of " + _pct(inputs.get("terminal_growth"))
                     + "%, the terminal value is " + _money(result.get("terminal_value"))
                     + ", worth " + _money(result.get("pv_terminal")) + " today ("
                     + _pct(result.get("terminal_share")) + "% of the total).")
    lines.append("The enterprise value is " + _money(result.get("enterprise_value")) + " on those declared "
                 "flows and that declared rate; it is arithmetic on the declarations, not a forecast.")
    return lines


def _multiples_lines(row, inputs, result):
    metric = str(inputs.get("metric") or "metric")
    count = result.get("n_comparables")
    lines = ["Applying a mean multiple of " + _fmt_exact(result.get("mean_multiple")) + "x to the declared "
             + metric.replace("_", " ") + " of " + _money(inputs.get("subject_value"))
             + (" across " + str(count) + " peer(s)" if count not in (None, "") else "")
             + " gives an implied enterprise value of " + _money(result.get("implied_enterprise_value"))
             + "."]
    if result.get("implied_equity_value") not in (None, ""):
        lines.append("After declared net debt of " + _money(inputs.get("net_debt") or "0")
                     + ", the implied equity value is " + _money(result.get("implied_equity_value"))
                     + (", or " + _money(result.get("per_share_value")) + " per share on the declared shares."
                        if result.get("per_share_value") not in (None, "") else "."))
    lines.append("The multiple is the student's declared peer or sector figure; the paper retrieves no market "
                 "multiple and does not recommend a price.")
    return lines


def _option_lines(row, inputs, result):
    lines = ["At a declared spot price of " + _money(inputs.get("spot_price")) + ", a strike of "
             + _money(inputs.get("strike_price")) + ", a volatility of " + _pct(inputs.get("volatility"))
             + "%, a risk-free rate of " + _pct(inputs.get("risk_free_rate")) + "% and "
             + _fmt_exact(inputs.get("time_to_maturity")) + " years to maturity, the declared "
             + str(inputs.get("option_type") or "call") + " option prices at "
             + _money(result.get("option_price")) + " (binomial check "
             + _money(result.get("binomial_price")) + ")."]
    lines.append("Delta is " + _money(result.get("delta")) + ", gamma is " + _money(result.get("gamma"))
                 + ", vega is " + _money(result.get("vega")) + ", theta is " + _money(result.get("theta"))
                 + " and rho is " + _money(result.get("rho")) + ".")
    lines.append("Every input is declared; the price is the model's output for those inputs, not a market quote.")
    return lines


def _real_option_lines(row, inputs, result):
    lines = ["With a declared underlying value of " + _money(inputs.get("underlying_value"))
             + ", an investment cost of " + _money(inputs.get("investment_cost"))
             + ", a volatility of " + _pct(inputs.get("volatility")) + "%, a risk-free rate of "
             + _pct(inputs.get("risk_free_rate")) + "% and " + _fmt_exact(inputs.get("steps"))
             + " declared steps, the " + str(inputs.get("exercise") or "european") + " "
             + str(inputs.get("option_type") or "call") + " real option is worth "
             + _money(result.get("option_value")) + " (intrinsic value "
             + _money(result.get("intrinsic_value")) + ")."]
    lines.append("The value follows from the declared inputs; the option's value is not a recommendation to "
                 "wait, expand or abandon.")
    return lines


def _portfolio_lines(row, inputs, result):
    lines = ["From the declared return series for two assets at a declared weight of "
             + _pct(inputs.get("weight_a")) + "% and a risk-free rate of "
             + _pct(inputs.get("risk_free_rate")) + "%, the portfolio return is "
             + _pct(result.get("portfolio_return")) + "% with a standard deviation of "
             + _pct(result.get("portfolio_sd")) + "%."]
    lines.append("The Sharpe ratio is " + _money(result.get("sharpe_ratio")) + ", the beta against the "
                 "declared market series is " + _money(result.get("beta")) + ", and the correlation "
                 "between the two return series is " + _money(result.get("correlation")) + ".")
    lines.append("Every series is declared by the student; no return or covariance is retrieved.")
    return lines


def _p_text(value):
    """A p-value as the paper states it: three decimals, or 'below 0.001'."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if number < Decimal("0.001"):
        return "below 0.001"
    return "{:.3f}".format(number)


def _descriptive_lines(row, inputs, result):
    excluded = result.get("n_missing")
    lines = ["From the declared sample of " + _fmt_exact(result.get("n")) + " observation(s)"
             + (", with " + _fmt_exact(excluded) + " excluded as missing" if str(excluded or "0") != "0" else "")
             + ", the mean is " + _money(result.get("mean")) + ", the median is "
             + _money(result.get("median")) + " and the standard deviation is "
             + _money(result.get("sd")) + ", over a declared range of " + _money(result.get("minimum"))
             + " to " + _money(result.get("maximum")) + "."]
    lines.append("The summary describes the declared values only; it says nothing about a wider population.")
    return lines


def _pearson_lines(row, inputs, result):
    level = Decimal(str(result.get("confidence_level") or "0.95"))
    lines = ["Across " + _fmt_exact(result.get("n_pairs")) + " declared pair(s), the correlation between the "
             "two series is r = " + _money(result.get("r")) + " (r squared " + _money(result.get("r_squared"))
             + "), with a " + _fmt_number(level * 100) + "% confidence interval of "
             + _money(result.get("ci_lower")) + " to " + _money(result.get("ci_upper"))
             + " and p = " + _p_text(result.get("p_value")) + "."]
    lines.append("A correlation measures association between the declared series; it does not show that one "
                 "series causes the other.")
    return lines


def _welch_lines(row, inputs, result):
    lines = ["The declared control group (n = " + _fmt_exact(result.get("n_control")) + ", mean "
             + _money(result.get("mean_control")) + ", sd " + _money(result.get("sd_control"))
             + ") and the declared treatment group (n = " + _fmt_exact(result.get("n_treated")) + ", mean "
             + _money(result.get("mean_treated")) + ", sd " + _money(result.get("sd_treated"))
             + ") differ by " + _money(result.get("diff")) + " (Welch t = " + _money(result.get("t_stat"))
             + ", df " + _money(result.get("df")) + ", p = " + _p_text(result.get("p_value")) + ")."]
    lines.append("Hedges' g for the difference is " + _money(result.get("hedges_g"))
                 + ". The test compares the two declared means; it does not establish what caused the gap.")
    return lines


def _anova_lines(row, inputs, result):
    lines = ["The declared " + _fmt_exact(result.get("n_groups")) + " group(s), " + _fmt_exact(result.get("n_total"))
             + " observations in all, give F = " + _money(result.get("f_stat")) + " (df "
             + _fmt_exact(result.get("df_between")) + ", " + _fmt_exact(result.get("df_within"))
             + ") with p = " + _p_text(result.get("p_value")) + "; eta squared is "
             + _money(result.get("eta_squared")) + "."]
    lines.append("The test compares the declared group means; it does not say which groups differ in practice "
                 "or why.")
    return lines


def _chi_square_lines(row, inputs, result):
    lines = ["Across the declared " + _fmt_exact(result.get("n_total")) + " counts, chi-square is "
             + _money(result.get("chi_squared")) + " (df " + _fmt_exact(result.get("df")) + ") with p = "
             + _p_text(result.get("p_value")) + "; Cramer's V is " + _money(result.get("cramers_v")) + "."]
    lines.append("The test measures the association between the two declared classifications; it does not "
                 "establish that one causes the other.")
    return lines


def _ols_lines(row, inputs, result):
    fit = ("F = " + _money(result.get("f_stat")) + " with p = " + _p_text(result.get("p_f"))
           if result.get("f_stat") not in (None, "") else
           "no F statistic is reported for this variant")
    lines = ["On " + _fmt_exact(result.get("n")) + " declared observation(s) and "
             + _fmt_exact(result.get("k")) + " predictor(s), the regression has R squared "
             + _money(result.get("r_squared")) + " (adjusted " + _money(result.get("adj_r_squared"))
             + "), " + fit + " and a residual standard error of "
             + _money(result.get("residual_se")) + "."]
    pieces = []
    for name in (inputs.get("predictors") or {}):
        coefficient = result.get("coef_" + str(name))
        if coefficient in (None, ""):
            continue
        pieces.append(str(name) + " " + _money(coefficient) + " (se " + _money(result.get("se_" + str(name)))
                      + ", p " + _p_text(result.get("p_" + str(name))) + ")")
    if pieces:
        lines.append("The declared coefficients are: " + "; ".join(pieces) + ".")
    lines.append("A coefficient is an association measured in the declared sample; it is not a causal effect "
                 "and it does not predict outside the declared values.")
    return lines


def _queue_lines(row, inputs, result):
    lines = ["At a declared arrival rate of " + _fmt_number(inputs.get("arrival_rate")) + " and a declared service "
             "rate of " + _fmt_number(inputs.get("service_rate")) + " per period, utilisation is "
             + _pct(result.get("utilisation")) + "%, with " + _money(result.get("average_in_queue"))
             + " waiting on average, " + _money(result.get("average_wait_in_queue"))
             + " periods in the queue, and a " + _pct(result.get("probability_waiting"))
             + "% chance that an arrival waits."]
    lines.append("The figures assume the declared rates stay constant and arrivals are random; they are not a "
                 "forecast of a real queue.")
    return lines


def _capacity_lines(row, inputs, result):
    resources = inputs.get("resources") or []
    index = result.get("bottleneck_index")
    bottleneck = ""
    try:
        position = int(Decimal(str(index))) - 1
        if 0 <= position < len(resources):
            bottleneck = str(resources[position].get("name") or "")
    except (InvalidOperation, ValueError):
        bottleneck = ""
    gap = Decimal(str(result.get("capacity_gap") or "0"))
    if gap < 0:
        against = ("the declared capacity is " + _money(abs(gap)) + " units short of the declared demand of "
                   + _money(inputs.get("demand")) + ".")
    else:
        against = ("the declared capacity leaves " + _money(gap) + " units of headroom over the declared "
                   "demand of " + _money(inputs.get("demand")) + ".")
    lines = ["With the declared resources, the maximum output is " + _money(result.get("max_output"))
             + " units per period" + (" and the bottleneck is " + bottleneck if bottleneck else "")
             + "; " + against]
    lines.append("The bottleneck's utilisation is " + _pct(result.get("bottleneck_utilisation"))
                 + "% of its declared hours; the method does not improve the plan, it measures it.")
    return lines


def _oee_lines(row, inputs, result):
    lines = ["On a declared planned production time of " + _money(inputs.get("planned_production_time"))
             + " minutes and " + _money(inputs.get("downtime")) + " minutes of downtime, availability is "
             + _pct(result.get("availability")) + "%, performance " + _pct(result.get("performance"))
             + "% and quality " + _pct(result.get("quality")) + "%, giving an overall equipment effectiveness of "
             + _pct(result.get("oee")) + "%."]
    lines.append("The measure composes the declared time, output and quality figures; it does not say what "
                 "caused the losses.")
    return lines


def _process_control_lines(row, inputs, result):
    lines = ["From the declared sample of " + _fmt_exact(result.get("n")) + " measurement(s), the mean is "
             + _money(result.get("mean")) + " with an estimated sigma of " + _money(result.get("sigma_estimate"))
             + ", giving control limits of " + _money(result.get("lower_control_limit")) + " to "
             + _money(result.get("upper_control_limit")) + "."]
    if str(result.get("out_of_control") or "0") != "0":
        lines.append(str(result.get("out_of_control")) + " declared point(s) fall outside those limits, so the "
                     "method reports the process as out of control.")
    else:
        lines.append("No declared point falls outside those limits; the method reports no out-of-control signal.")
    lines.append("The limits describe the declared sample; the method does not identify a cause for any signal.")
    return lines


def _demand_curve_lines(row, inputs, result):
    lines = ["Fitting the declared price and quantity points gives a demand curve with an intercept of "
             + _money(result.get("intercept")) + " and a slope of " + _money(result.get("slope"))
             + " (r squared " + _money(result.get("r_squared")) + "); elasticity at the mean point is "
             + _money(result.get("elasticity_at_mean")) + "."]
    if result.get("revenue_max_price") not in (None, ""):
        lines.append("The revenue-maximising point of that fitted curve is a price of "
                     + _money(result.get("revenue_max_price")) + " at "
                     + _money(result.get("revenue_max_quantity")) + " units, for revenue of "
                     + _money(result.get("revenue_max_revenue")) + ".")
    lines.append("The curve describes the declared points only; it is not a market forecast and the declared "
                 "prices need not cover costs.")
    return lines


_RFM_LABELS = (("champions", "champions"), ("loyal", "loyal customers"),
               ("potential_loyalist", "potential loyalists"), ("new", "new customers"),
               ("promising", "promising"), ("need_attention", "need attention"),
               ("at_risk", "at risk"), ("about_to_sleep", "about to sleep"),
               ("hibernating", "hibernating"), ("cannot_lose", "cannot lose"),
               ("lost", "lost"))


def _rfm_lines(row, inputs, result):
    parts = []
    for key, label in _RFM_LABELS:
        value = result.get("count_" + key)
        if value in (None, "") or str(value) == "0":
            continue
        parts.append(str(value) + " " + label)
    lines = ["Across " + _fmt_exact(result.get("total_customers")) + " declared customers, the RFM scores place: "
             + ("; ".join(parts) if parts else "no customer in a named segment") + "."]
    lines.append("The segments come from the declared recency, frequency and monetary values; the method does "
                 "not target, contact or value a customer beyond that scoring.")
    return lines


def _funnel_lines(row, inputs, result):
    lines = ["On the declared funnel, the last declared stage holds " + _fmt_exact(result.get("customers"))
             + " customer(s), a conversion of " + _pct(result.get("overall_conversion"))
             + "% from the first declared stage, with " + _money(result.get("drop_off"))
             + " people not carried through."]
    if result.get("cac") not in (None, ""):
        lines.append("At the declared spend, the cost per acquired customer is " + _money(result.get("cac")) + ".")
    lines.append("The rates are arithmetic on the declared stage counts; the method does not explain the "
                 "drop-off.")
    return lines


def _abtest_lines(row, inputs, result):
    lines = ["Variant A converted " + _pct(result.get("rate_a")) + "% of "
             + _fmt_exact(inputs.get("visitors_a")) + " declared visitors and variant B converted "
             + _pct(result.get("rate_b")) + "%; the absolute lift is " + _pct(result.get("absolute_lift"))
             + " points, the relative lift " + _pct(result.get("relative_lift"))
             + "%, and the two-proportion test gives z = "
             + _money(result.get("z")) + " with p = " + _p_text(result.get("p_value")) + "."]
    lines.append("The test compares the two declared proportions; it does not show that the change caused the "
                 "difference or that the result would repeat.")
    return lines


def _social_lines(row, inputs, result):
    lines = ["On " + _money(inputs.get("impressions")) + " declared impressions and "
             + _money(inputs.get("reach")) + " people reached, the engagement rate is "
             + _pct(result.get("engagement_rate")) + "%, at a frequency of " + _money(result.get("frequency"))
             + " and a CPM of " + _money(result.get("cpm")) + "."]
    lines.append("The cost per engagement is " + _money(result.get("cost_per_engagement"))
                 + " and follower growth over the period is " + _pct(result.get("follower_growth"))
                 + "%. The figures are arithmetic on the declared platform numbers; no platform is connected.")
    return lines


def _alpha_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("k_items")) + " declared item(s) and "
             + _fmt_exact(result.get("n")) + " respondent(s), reliability (Cronbach's alpha) is "
             + _money(result.get("alpha")) + "."]
    lines.append("Alpha describes the internal consistency of the declared responses; the method does not "
                 "establish that the items measure the intended construct.")
    return lines


def _weighted_lines(row, inputs, result):
    lines = ["With the declared weights (total " + _money(result.get("sum_weights")) + "), the weighted mean is "
             + _money(result.get("weighted_mean")) + " with a weighted standard deviation of "
             + _money(result.get("weighted_sd")) + "; the effective sample size is "
             + _money(result.get("n_eff")) + " and the design effect "
             + _money(result.get("design_effect")) + "."]
    lines.append("The means follow from the declared values and weights; the method does not infer a population "
                 "from them.")
    return lines


def _power_lines(row, inputs, result):
    lines = ["At a declared effect of " + _money(inputs.get("effect")) + ", " + _fmt_exact(inputs.get("n1"))
             + " observation(s) per group and a declared alpha of " + _pct(result.get("alpha"))
             + "%, the statistical power is " + _pct(result.get("power"))
             + "% and the minimum detectable effect is " + _money(result.get("mde")) + "."]
    lines.append("The figure depends entirely on the declared effect, spread and sample; it is a design "
                 "calculation, not evidence about the case.")
    return lines


def _named_row(inputs, index):
    rows = inputs.get("channels") or inputs.get("segments") or inputs.get("vehicles") or []
    try:
        row = rows[index]
        return str(row.get("name") or ("row " + str(index + 1)))
    except (IndexError, TypeError, AttributeError):
        return "row " + str(index + 1)


def _cohort_lines(row, inputs, result):
    periods = [key for key in sorted(result) if key.startswith("retention_")]
    retained = ", ".join(_pct(result[key]) + "%" for key in periods)
    lines = ["Across " + _fmt_exact(len(inputs.get("cohort_sizes") or [])) + " declared cohort(s), retention is "
             + retained + " at successive periods (average " + _pct(result.get("average_retention"))
             + "%), with an average lifetime of " + _money(result.get("average_lifetime")) + " periods."]
    lines.append("The curve follows the declared cohort sizes and retained counts; the method does not predict "
                 "future retention.")
    return lines


def _forecast_lines(row, inputs, result):
    """The trend-forecast capability: the declared series, its trend and its interval.

    Distinct from `_trend_lines`, which reports the accounting shelf's common-size
    and trend analysis.  The two capabilities used to share one name, so whichever
    definition came last silently formatted the other's paper.
    """
    horizon = int(Decimal(str(result.get("horizon") or "1")))
    points = []
    for step in range(1, horizon + 1):
        value = result.get("forecast_%d" % step)
        if value in (None, ""):
            continue
        points.append(_money(value) + " (" + _money(result.get("ci_lower_%d" % step)) + " to "
                      + _money(result.get("ci_upper_%d" % step)) + ")")
    lines = ["The declared series of " + _fmt_exact(result.get("n_fitted")) + " period(s) has a trend of "
             + _money(result.get("slope")) + " per period (r squared " + _money(result.get("r_squared"))
             + ", p = " + _p_text(result.get("p_slope")) + "), and the method projects "
             + "; ".join(points) + " over the declared horizon."]
    lines.append("The projection extends the declared trend with its interval; it is not a market forecast and "
                 "it assumes the declared pattern continues.")
    return lines


def _missing_lines(row, inputs, result):
    lines = ["Of the declared values, " + _fmt_exact(result.get("n_valid")) + " are valid and "
             + _fmt_exact(result.get("n_missing")) + " missing (" + _pct(result.get("pct_missing"))
             + "%); the observed mean is " + _money(result.get("mean_observed")) + "."]
    lines.append("Under the declared mechanism the mean can lie between " + _money(result.get("bound_low"))
                 + " and " + _money(result.get("bound_high")) + ", a width of "
                 + _money(result.get("bound_width")) + "; the bounds state what the missing values could hide.")
    return lines


def _media_lines(row, inputs, result):
    vehicles = inputs.get("vehicles") or []
    first = ""
    if vehicles:
        first = (" The largest single declared reach is " + _pct(result.get("reach_pct_1")) + "% of the declared "
                 "population (" + str(vehicles[0].get("name") or "the first vehicle") + ").")
    lines = ["With " + _fmt_exact(result.get("vehicles") or len(vehicles)) + " declared vehicle(s), the plan "
             "delivers " + _money(result.get("total_impressions")) + " impressions (GRP "
             + _money(result.get("total_grp")) + ") at a blended CPM of " + _money(result.get("blended_cpm"))
             + " for a declared cost of " + _money(result.get("total_cost")) + "." + first]
    lines.append("Reach and frequency are arithmetic on the declared populations and insertions; no audience "
                 "data is retrieved.")
    return lines


def _web_lines(row, inputs, result):
    channels = inputs.get("channels") or []
    best = ""
    try:
        counts = [(str(channel.get("name")), Decimal(str(result.get("conversions_%d" % (index + 1)))))
                  for index, channel in enumerate(channels)]
        if counts:
            name, value = max(counts, key=lambda pair: pair[1])
            best = " The most conversions come from " + name + " (" + _fmt_exact(value) + ")."
    except (InvalidOperation, ValueError):
        best = ""
    lines = ["Across the declared channels, " + _money(result.get("total_sessions")) + " sessions produced "
             + _money(result.get("total_conversions")) + " conversions ("
             + _pct(result.get("blended_conversion_rate")) + "%), for revenue of "
             + _money(result.get("total_revenue")) + " and revenue per session of "
             + _money(result.get("revenue_per_session")) + "." + best]
    lines.append("The rates are arithmetic on the declared channel figures; no analytics platform is connected.")
    return lines


def _email_lines(row, inputs, result):
    lines = ["From a declared list of " + _money(inputs.get("list_start")) + ", the list ends at "
             + _money(result.get("list_end")) + " (" + _pct(result.get("growth_rate")) + "% growth, "
             + _pct(result.get("churn_rate")) + "% churn); the open rate is "
             + _pct(result.get("open_rate")) + "%, the click rate " + _pct(result.get("click_rate"))
             + "% and click-to-open " + _pct(result.get("click_to_open")) + "%."]
    lines.append("Revenue per subscriber is " + _money(result.get("revenue_per_subscriber"))
                 + " and per send " + _money(result.get("revenue_per_send"))
                 + "; the figures are arithmetic on the declared sends and responses.")
    return lines


def _segment_lines(row, inputs, result):
    shares = []
    for index in range(len(inputs.get("segments") or [])):
        share = result.get("profit_share_%d" % (index + 1))
        if share in (None, ""):
            continue
        shares.append(_named_row(inputs, index) + " " + _pct(share) + "%")
    lines = ["Across " + _fmt_exact(result.get("segments")) + " declared segment(s), revenue of "
             + _money(result.get("total_revenue")) + " and cost of " + _money(result.get("total_cost"))
             + " leave profit of " + _money(result.get("total_profit")) + " ("
             + _pct(result.get("overall_margin")) + "% margin)."]
    if shares:
        lines.append("Profit is concentrated as: " + "; ".join(shares) + " of the total.")
    lines.append("The margins follow from the declared revenue and costs; the method does not reassign the "
                 "allocated cost.")
    return lines


def _channel_lines(row, inputs, result):
    parts = []
    for index in range(len(inputs.get("channels") or [])):
        cac = result.get("cac_%d" % (index + 1))
        if cac in (None, ""):
            continue
        ratio = result.get("ltv_cac_%d" % (index + 1))
        parts.append(_named_row(inputs, index) + " CAC " + _money(cac)
                     + (", LTV/CAC " + _money(ratio) if ratio not in (None, "") else ""))
    lines = ["Across the declared channels, " + _money(result.get("total_spend")) + " of spend acquired "
             + _money(result.get("total_customers")) + " customers at a blended CAC of "
             + _money(result.get("blended_cac")) + "."]
    if parts:
        lines.append("By channel: " + "; ".join(parts) + ".")
    lines.append("The ratios use the declared spend, customers, contribution margin and churn; the method does "
                 "not retrieve acquisition costs.")
    return lines


def _attribution_lines(row, inputs, result):
    parts = []
    for index in range(len(inputs.get("channels") or [])):
        first = result.get("first_share_%d" % (index + 1))
        if first in (None, ""):
            continue
        parts.append(_named_row(inputs, index) + " first " + _pct(first) + "%, last "
                     + _pct(result.get("last_share_%d" % (index + 1))) + "%, linear "
                     + _pct(result.get("linear_share_%d" % (index + 1))) + "%")
    lines = ["Across the declared channels the credit totals " + _money(result.get("total_first_click"))
             + " first-click, " + _money(result.get("total_last_click")) + " last-click and "
             + _money(result.get("total_linear")) + " linear."]
    if parts:
        lines.append("By channel: " + "; ".join(parts) + ".")
    lines.append("The three rules are alternative allocations of the same declared credit; the method does not "
                 "say which rule is right.")
    return lines


def _line_lines(row, inputs, result):
    lines = ["The declared tasks total " + _money(result.get("total_time")) + " minutes per unit; at a declared "
             "cycle time of " + _money(result.get("cycle_time")) + " minutes the line balances into "
             + _fmt_exact(result.get("stations")) + " station(s) (lower bound "
             + _fmt_exact(result.get("lower_bound_stations")) + "), with "
             + _fmt_exact(result.get("idle_time")) + " minutes of idle time and an efficiency of "
             + _pct(result.get("efficiency")) + "%."]
    loads = []
    for index in range(1, int(Decimal(str(result.get("stations") or "0"))) + 1):
        load = result.get("load_%d" % index)
        if load not in (None, ""):
            loads.append("station " + str(index) + " " + _money(load) + " minutes")
    if loads:
        lines.append("The declared loads are: " + "; ".join(loads) + ".")
    lines.append("The balance follows the chosen rule and the declared times; the method does not level the "
                 "line itself or estimate the times.")
    return lines


def _dupont_lines(row, inputs, result):
    lines = ["From a declared revenue of " + _money(inputs.get("revenue")) + ", net income of "
             + _money(inputs.get("net_income")) + ", total assets of " + _money(inputs.get("total_assets"))
             + " and equity of " + _money(inputs.get("equity")) + ", the net margin is "
             + _pct(result.get("net_margin")) + "%, asset turnover "
             + _money(result.get("asset_turnover")) + " and the equity multiplier "
             + _money(result.get("equity_multiplier")) + "x, giving a return on equity of "
             + _pct(result.get("return_on_equity")) + "% (return on assets "
             + _pct(result.get("return_on_assets")) + "%)."]
    lines.append("The decomposition multiplies the three declared ratios; it does not judge whether the "
                 "leverage is prudent.")
    return lines


def _trend_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("n_periods")) + " declared period(s), revenue grew at "
             + _pct(result.get("revenue_cagr")) + "% a year (latest "
             + _pct(result.get("revenue_growth_latest")) + "%), and net income at "
             + _pct(result.get("net_income_cagr")) + "% a year."]
    lines.append("The latest gross margin is " + _pct(result.get("gross_margin_latest"))
                 + "%, the operating margin " + _pct(result.get("operating_margin_latest"))
                 + "% and the net margin " + _pct(result.get("net_margin_latest"))
                 + "%; the method describes the declared series and does not forecast the next period.")
    return lines


def _working_capital_lines(row, inputs, result):
    lines = ["With declared revenue of " + _money(inputs.get("revenue")) + " and cost of sales of "
             + _money(inputs.get("cost_of_sales")) + ", the days sales outstanding are "
             + _money(result.get("dso")) + ", days inventory " + _money(result.get("dio"))
             + " and days payables " + _money(result.get("dpo")) + ", giving a cash conversion cycle of "
             + _money(result.get("cash_conversion_cycle")) + " days and net working capital of "
             + _money(result.get("net_working_capital")) + "."]
    lines.append("At the declared annual demand and order cost, the economic order quantity is "
                 + _money(result.get("eoq")) + " units and the cost of the declared trade credit is "
                 + _pct(result.get("cost_of_trade_credit")) + "% a year.")
    lines.append("The cycle measures are arithmetic on the declared balances; the method does not judge the "
                 "credit or ordering policy.")
    return lines


def _loan_lines(row, inputs, result):
    """The loan amortisation: the level payment, what the borrowing costs, and the first split."""
    lines = ["On a declared principal of " + _money(inputs.get("principal")) + " at an annual rate of "
             + _pct(inputs.get("annual_rate")) + "%, repaid over " + _fmt_exact(result.get("n_payments"))
             + " payments, the level payment is " + _money(result.get("payment")) + " per payment."]
    lines.append("The payments total " + _money(result.get("total_paid")) + ", of which "
                 + _money(result.get("total_interest")) + " is interest; the first payment is "
                 + _money(result.get("first_interest")) + " interest and "
                 + _money(result.get("first_principal")) + " principal.")
    lines.append("The schedule assumes one fixed rate for the whole term and a payment at the end of each "
                 "declared period; it does not model fees, a rate change or an early repayment.")
    return lines


def _tax_lines(row, inputs, result):
    """Declared-rate tax: income tax, VAT payable and deferred tax, from the declared rates only."""
    lines = ["On declared taxable income of " + _money(result.get("taxable_income"))
             + " at a declared rate of " + _pct(result.get("income_tax_rate")) + "%, the income tax is "
             + _money(result.get("income_tax")) + " and the after-tax income is "
             + _money(result.get("net_income_after_tax")) + "."]
    if result.get("vat_payable") not in (None, ""):
        lines.append("VAT payable is output tax of " + _money(result.get("vat_output_tax"))
                     + " less input tax of " + _money(result.get("vat_input_tax")) + ", which is "
                     + _money(result.get("vat_payable")) + ".")
    if result.get("deferred_tax") not in (None, ""):
        lines.append("The deferred tax is the declared temporary difference of "
                     + _money(result.get("temporary_difference")) + " at the declared rate of "
                     + _pct(result.get("deferred_tax_rate")) + "%, which is "
                     + _money(result.get("deferred_tax")) + ".")
    lines.append("The total tax charge is " + _money(result.get("total_tax_charge")) + ".")
    lines.append("Every rate and the taxable income are the student's declared figures; the method applies "
                 "no jurisdiction's tax law, credits, exemptions, thresholds or filing rules.")
    return lines


def _scenario_lines(row, inputs, result):
    lines = ["At a declared discount rate of " + _pct(inputs.get("discount_rate"))
             + "%, the declared cash flows have a net present value of " + _money(result.get("npv_base"))
             + "; at the declared low rate of " + _pct(result.get("rate_low")) + "% it is "
             + _money(result.get("npv_at_low_rate")) + " and at the high rate of "
             + _pct(result.get("rate_high")) + "% it is " + _money(result.get("npv_at_high_rate"))
             + ", a swing of " + _money(result.get("swing")) + "."]
    if result.get("breakeven_rate") not in (None, ""):
        lines.append("The rate at which the declared flows break even is " + _pct(result.get("breakeven_rate"))
                     + "%.")
    lines.append("Only the discount rate moves between the scenarios; every other declared input is held.")
    return lines


def _risk_lines(row, inputs, result):
    confidence = Decimal(str(result.get("confidence") or "0.95"))
    lines = ["On the declared return series, the mean return is " + _pct(result.get("mean_return"))
             + "% with a standard deviation of " + _pct(result.get("sd_return"))
             + "%; at the declared " + _fmt_number(confidence * 100) + "% confidence over "
             + _fmt_exact(result.get("horizon_days")) + " day(s), the parametric value at risk is "
             + _pct(result.get("parametric_var")) + "% of the declared portfolio value and the historical "
             "figure is " + _pct(result.get("historical_var")) + "%."]
    lines.append("In money, the value at risk on the declared portfolio is " + _money(result.get("var_amount"))
                 + " and the expected shortfall beyond it is " + _money(result.get("cvar_amount"))
                 + "; the estimate describes the declared history, not a guarantee about the future.")
    return lines


def _fx_lines(row, inputs, result):
    lines = ["At a declared spot rate of " + _fmt_exact(inputs.get("spot_rate")) + " and declared interest rates "
             "of " + _pct(inputs.get("domestic_rate")) + "% and " + _pct(inputs.get("foreign_rate"))
             + "%, interest-rate parity implies a forward rate of " + _money(result.get("interest_rate_parity_forward"))
             + ", and the declared inflation rates imply " + _money(result.get("ppp_expected_spot"))
             + " under purchasing-power parity."]
    if result.get("forward_rate") not in (None, ""):
        lines.append("The parity forward of " + _money(result.get("forward_rate"))
                     + " stands " + _pct(result.get("forward_premium")) + "% away from the declared spot rate.")
    lines.append("Both rates are arithmetic on the declared inputs; neither is a forecast of the spot rate.")
    return lines


def _convert_lines(row, inputs, result):
    lines = ["Converting a declared " + _money(result.get("amount_from")) + " "
             + str(inputs.get("from_currency")) + " at the declared rate of "
             + _fmt_exact(result.get("rate")) + " gives " + _money(result.get("amount")) + " "
             + str(inputs.get("to_currency")) + "."]
    provenance = str(inputs.get("rate_provenance") or "")
    lines.append("The rate is the student's declared figure"
                 + (" (provenance: " + provenance + ")" if provenance else "")
                 + "; the paper retrieves no exchange rate and no date is implied beyond the one declared.")
    return lines


def _concentration_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("n_firms")) + " declared firm(s) with total revenue of "
             + _money(result.get("total_revenue")) + ", the Herfindahl-Hirschman index is "
             + _money(result.get("hhi")) + " on the 0-10,000 scale, the four-firm ratio is "
             + _fmt_exact(result.get("cr4")) + "% and the effective number of firms is "
             + _money(result.get("effective_n")) + "."]
    lines.append("The index follows from the declared revenues; the method does not define the market or "
                 "retrieve shares.")
    return lines


def _cost_curve_lines(row, inputs, result):
    lines = ["At a declared quantity of " + _money(result.get("quantity")) + ", total cost is "
             + _money(result.get("total_cost")) + " (fixed " + _money(result.get("fixed_cost"))
             + ", variable " + _money(result.get("variable_cost")) + "), so average cost is "
             + _money(result.get("average_cost")) + " and marginal cost is "
             + _money(result.get("marginal_cost")) + "."]
    lines.append("At the declared price of " + _money(result.get("price")) + ", revenue is "
                 + _money(result.get("total_revenue")) + " and profit is " + _money(result.get("profit"))
                 + "; the method reports the shutdown position on the declared figures.")
    return lines


def _market_power_lines(row, inputs, result):
    lines = ["At a declared price of " + _money(result.get("price")) + " and marginal cost of "
             + _money(result.get("marginal_cost")) + ", the markup is " + _money(result.get("markup"))
             + " and the Lerner index is " + _pct(result.get("lerner_index"))
             + "%, implying a demand elasticity of " + _money(result.get("implied_demand_elasticity"))
             + " at that point."]
    lines.append("The index is arithmetic on the declared price and cost; it says nothing about why the "
                 "power exists.")
    return lines


def _proforma_lines(row, inputs, result):
    periods = len(inputs.get("revenue") or [])
    lines = ["Over " + str(periods) + " declared period(s), revenue totals "
             + _money(result.get("total_revenue")) + " and net income totals "
             + _money(result.get("total_net_income")) + "; in period 1, revenue is "
             + _money(result.get("revenue_1")) + " and operating profit "
             + _money(result.get("operating_profit_1")) + "."]
    lines.append("The projected statements use the declared revenue, margin, operating costs, depreciation, "
                 "interest and loan repayment; the method checks that the balance sheet balances.")
    return lines


def _sensitivity_lines(row, inputs, result):
    prices = inputs.get("price_changes") or []
    volumes = inputs.get("volume_changes") or []
    cells = [(name, Decimal(str(value))) for name, value in (result or {}).items()
             if str(name).startswith("profit_")]
    lines = ["At the declared base case, profit is " + _money(result.get("base_profit")) + "."]
    if cells:
        low, high = min(cells, key=lambda pair: pair[1]), max(cells, key=lambda pair: pair[1])
        low_i, low_j = (int(part) - 1 for part in low[0].split("_")[1:])
        high_i, high_j = (int(part) - 1 for part in high[0].split("_")[1:])
        lines.append("Across the declared changes, profit ranges from " + _money(low[1])
                     + " at a price change of " + _pct(prices[low_i]) + "% and a volume change of "
                     + _pct(volumes[low_j]) + "%, to " + _money(high[1])
                     + " at a price change of " + _pct(prices[high_i]) + "% and a volume change of "
                     + _pct(volumes[high_j]) + "%.")
    lines.append("Each cell applies the declared change to the base price and volume and holds every other "
                 "input at the base case.")
    return lines


def _sroi_lines(row, inputs, result):
    lines = ["A declared investment of " + _money(result.get("investment")) + " against benefits with a "
             "present value of " + _money(result.get("pv_benefits")) + " gives a social return on "
             "investment of " + _money(result.get("sroi_ratio")) + " to 1, a net value of "
             + _money(result.get("net_value")) + " over " + _fmt_exact(result.get("n_periods"))
             + " period(s)."]
    lines.append("The ratio depends entirely on the declared benefits and the declared discount rate; the "
                 "method does not value an outcome.")
    return lines


def _cba_lines(row, inputs, result):
    lines = ["With declared costs and benefits, the present value of costs is "
             + _money(result.get("pv_costs")) + " and of benefits " + _money(result.get("pv_benefits"))
             + ", giving a net present value of " + _money(result.get("net_present_value"))
             + " and a benefit-cost ratio of " + _money(result.get("benefit_cost_ratio")) + "."]
    lines.append("Both streams are the student's declaration, discounted at the declared rate; the method does "
                 "not decide whether the benefits should count.")
    return lines


def _cea_lines(row, inputs, result):
    lines = ["Against the declared comparator (cost " + _money(result.get("comparator_cost")) + ", effect "
             + _money(result.get("comparator_effect")) + "), the incremental cost per unit of effect is "
             + _money(result.get("icer_b")) + "."]
    dominant = result.get("dominant_b")
    if str(dominant or "").lower() in ("true", "yes", "1"):
        lines.append("The option is dominant on the declared figures: it costs less and delivers more.")
    lines.append("The comparison uses the declared costs and effects; the method does not choose between the "
                 "options.")
    return lines


def _equilibrium_lines(row, inputs, result):
    lines = ["From the declared demand and supply curves, the equilibrium price is "
             + _money(result.get("equilibrium_price")) + " at a quantity of "
             + _money(result.get("equilibrium_quantity")) + ", with consumer surplus of "
             + _money(result.get("consumer_surplus")) + ", producer surplus of "
             + _money(result.get("producer_surplus")) + " and total surplus of "
             + _money(result.get("total_surplus")) + "."]
    lines.append("The curves are the student's declaration; the method does not estimate demand or supply.")
    return lines


def _price_control_lines(row, inputs, result):
    binding = "binding" if str(result.get("binding")).lower() in ("true", "yes", "1") else "not binding"
    lines = ["A declared control price of " + _money(result.get("control_price")) + " against an equilibrium of "
             + _money(result.get("equilibrium_price")) + " is " + binding + "; the quantity traded is "
             + _money(result.get("quantity_traded")) + " against demand of "
             + _money(result.get("quantity_demanded_at_control")) + " and supply of "
             + _money(result.get("quantity_supplied_at_control")) + "."]
    gap = result.get("quantity_gap")
    if gap not in (None, "") and Decimal(str(gap)) != 0:
        lines.append("The resulting shortfall in quantity is " + _money(abs(Decimal(str(gap)))) + ".")
    lines.append("The result follows from the declared curves and the declared control; the method does not "
                 "assess whether the policy is desirable.")
    return lines


def _profit_max_lines(row, inputs, result):
    lines = ["The declared demand and cost curves give a profit-maximising quantity of "
             + _money(result.get("profit_maximizing_quantity")) + " at a price of "
             + _money(result.get("profit_maximizing_price")) + ", with profit of "
             + _money(result.get("profit")) + " and a markup of " + _money(result.get("markup"))
             + " (Lerner index " + _pct(result.get("lerner_index")) + "%)."]
    lines.append("The optimum is arithmetic on the declared curves; no market price is retrieved.")
    return lines


def _discrimination_lines(row, inputs, result):
    lines = ["Charging separately in the two declared markets gives quantities of "
             + _money(result.get("quantity_1")) + " at " + _money(result.get("price_1")) + " and "
             + _money(result.get("quantity_2")) + " at " + _money(result.get("price_2"))
             + ", for total revenue of " + _money(result.get("total_revenue")) + " and profit of "
             + _money(result.get("total_profit")) + "."]
    lines.append("The two demands and the marginal cost are declared; the method does not test whether the "
                 "markets can be separated.")
    return lines


def _cournot_lines(row, inputs, result):
    lines = ["In the declared duopoly, the two firms produce " + _money(result.get("quantity_1")) + " and "
             + _money(result.get("quantity_2")) + " units, giving a price of " + _money(result.get("price"))
             + " and profits of " + _money(result.get("profit_1")) + " and "
             + _money(result.get("profit_2")) + "."]
    lines.append("The equilibrium follows from the declared demand and the two declared marginal costs.")
    return lines


def _nash_lines(row, inputs, result):
    found = []
    for i in (1, 2):
        for j in (1, 2):
            if str(result.get("nash_%d%d" % (i, j))).lower() in ("true", "yes", "1"):
                found.append("(row " + str(i) + ", column " + str(j) + ")")
    lines = ["On the declared payoff matrix the method finds " + _fmt_exact(result.get("nash_count"))
             + " pure-strategy Nash equilibrium point(s)"
             + (": " + "; ".join(found) if found else "") + "."]
    lines.append("The payoffs are the student's declaration; the method does not predict how players behave.")
    return lines


def _national_income_lines(row, inputs, result):
    lines = ["From the declared components, GDP is " + _money(result.get("gdp")) + ", GNP "
             + _money(result.get("gnp")) + " and net national product " + _money(result.get("nnp"))
             + ", with net exports of " + _money(result.get("net_exports")) + "."]
    lines.append("The identity is applied to the declared figures; no national account is retrieved.")
    return lines


def _unemployment_lines(row, inputs, result):
    lines = ["On a declared labour force of " + _money(result.get("labour_force")) + " and "
             + _money(result.get("employed")) + " employed, unemployment is "
             + _money(result.get("unemployed")) + " people, an unemployment rate of "
             + _pct(result.get("unemployment_rate")) + "% and a participation rate of "
             + _pct(result.get("labour_force_participation_rate")) + "%."]
    lines.append("The rates are arithmetic on the declared counts; the method does not define who counts as "
                 "unemployed.")
    return lines


def _real_wage_lines(row, inputs, result):
    lines = ["At a declared nominal wage of " + _money(result.get("nominal_wage")) + " and a CPI of "
             + _money(result.get("cpi")) + ", the real wage is " + _money(result.get("real_wage"))
             + ", which is " + _pct(result.get("wage_share_of_productivity"))
             + "% of the declared labour productivity."]
    lines.append("The comparison uses the declared price index and productivity; the method does not measure "
                 "either.")
    return lines


def _money_multiplier_lines(row, inputs, result):
    lines = ["With a declared monetary base of " + _money(result.get("monetary_base")) + " and a reserve ratio "
             "of " + _pct(result.get("reserve_ratio")) + "%, the simple money multiplier is "
             + _money(result.get("simple_money_multiplier")) + " and the extended one "
             + _money(result.get("extended_money_multiplier")) + ", giving a money supply of "
             + _money(result.get("money_supply_extended")) + "."]
    lines.append("The multiplier assumes the declared ratios hold; the method does not model central-bank "
                 "behaviour.")
    return lines


def _fiscal_multiplier_lines(row, inputs, result):
    lines = ["At a declared marginal propensity to consume of " + _money(result.get("mpc"))
             + ", the government spending multiplier is "
             + _money(result.get("government_spending_multiplier")) + " and the tax multiplier "
             + _money(result.get("tax_multiplier")) + "."]
    change = result.get("output_change")
    if change not in (None, "") and Decimal(str(change)) != 0:
        lines.append("On the declared changes, output changes by " + _money(change) + ".")
    lines.append("The multipliers follow from the declared propensities; they are not an estimate of the actual "
                 "economy.")
    return lines


def _budget_lines(row, inputs, result):
    lines = ["With declared revenue of " + _money(result.get("government_revenue")) + " and total spending of "
             + _money(result.get("total_spending")) + ", the overall balance is "
             + _money(result.get("overall_balance")) + " and the primary balance "
             + _money(result.get("primary_balance")) + "."]
    if result.get("debt_to_gdp") not in (None, ""):
        lines.append("On the declared debt and GDP, debt is " + _pct(result.get("debt_to_gdp"))
                     + "% of GDP.")
    lines.append("The balances are arithmetic on the declared figures; no fiscal rule is applied.")
    return lines


def _okun_lines(row, inputs, result):
    lines = ["At a declared actual GDP of " + _money(inputs.get("actual_gdp")) + " against potential of "
             + _money(inputs.get("potential_gdp")) + ", the output gap is "
             + _pct(result.get("output_gap")) + "%, which the declared Okun coefficient links to a "
             + _money(result.get("predicted_unemployment_change_pp"))
             + " percentage-point change in unemployment"
             + (" (a predicted rate of " + _pct(result.get("predicted_unemployment_rate")) + "%)"
                if result.get("predicted_unemployment_rate") not in (None, "") else "") + "."]
    lines.append("The link is the declared coefficient, not an estimated relationship.")
    return lines


def _externality_lines(row, inputs, result):
    lines = ["With a declared external cost of " + _money(result.get("external_cost")) + " per unit, the market "
             "produces " + _money(result.get("market_quantity")) + " units at "
             + _money(result.get("market_price")) + " against a social optimum of "
             + _money(result.get("social_quantity")) + " units."]
    lines.append("The Pigouvian tax that would close the gap is " + _money(result.get("pigouvian_tax"))
                 + " per unit, and the deadweight loss at the market quantity is "
                 + _money(result.get("deadweight_loss")) + ".")
    lines.append("The optimum is arithmetic on the declared curves and the declared external cost.")
    return lines


def _public_good_lines(row, inputs, result):
    lines = ["Summing the two declared marginal-benefit curves against the declared marginal cost gives an "
             "efficient quantity of " + _money(result.get("efficient_quantity")) + " units, a social marginal "
             "benefit of " + _money(result.get("social_marginal_benefit")) + " and a net benefit of "
             + _money(result.get("net_benefit")) + "."]
    lines.append("The curves are declared; the method does not value the good or estimate demand.")
    return lines


def _pollution_lines(row, inputs, result):
    lines = ["Where the declared marginal damage meets the declared marginal abatement cost, optimal emissions "
             "are " + _money(result.get("optimal_emissions")) + " units, with a Pigouvian tax of "
             + _money(result.get("pollution_tax")) + " per unit, damage of "
             + _money(result.get("total_damage")) + " and abatement cost of "
             + _money(result.get("total_abatement_cost")) + "."]
    lines.append("The optimum uses the declared damage and abatement curves only.")
    return lines


def _welfare_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("n")) + " declared incomes with a mean of "
             + _money(result.get("mean_income")) + ", utilitarian welfare is "
             + _money(result.get("utilitarian_welfare")) + ", Rawlsian "
             + _money(result.get("rawlsian_welfare")) + " and Nash "
             + _money(result.get("nash_welfare")) + "."]
    lines.append("Each figure is one declared welfare function applied to the same incomes; the method does not "
                 "say which is right.")
    return lines


def _gini_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("n")) + " declared incomes with a mean of "
             + _money(result.get("mean_income")) + ", the Gini coefficient is "
             + _money(result.get("gini")) + "; the poorest person holds "
             + _pct(result.get("poorest_share")) + "% of the total income and the richest "
             + _pct(result.get("richest_share")) + "%."]
    lines.append("The coefficient describes the declared incomes; the method does not infer the wider "
                 "population.")
    return lines


def _poverty_lines(row, inputs, result):
    lines = ["Against a declared poverty line, " + _fmt_exact(result.get("poor_count")) + " of "
             + _fmt_exact(result.get("n")) + " people are poor, a headcount ratio of "
             + _pct(result.get("headcount_ratio")) + "%, a poverty gap of "
             + _pct(result.get("poverty_gap")) + "% and a squared gap of "
             + _pct(result.get("squared_gap")) + "%."]
    lines.append("The measures use the declared line and incomes; the method does not set the line.")
    return lines


def _progressivity_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("n")) + " declared incomes and taxes, the average tax rate is "
             + _pct(result.get("average_tax_rate")) + "%; the top earner holds "
             + _pct(result.get("top_income_share")) + "% of income and pays "
             + _pct(result.get("top_tax_share")) + "% of the tax, a progressivity gap of "
             + _pct(result.get("progressivity_gap")) + " points."]
    lines.append("The measure compares the declared distributions; it does not judge the tax system.")
    return lines


def _tariff_lines(row, inputs, result):
    lines = ["At a declared world price plus a tariff of " + _money(inputs.get("tariff_per_unit")) + ", the "
             "domestic price is " + _money(result.get("domestic_price")) + ", imports fall to "
             + _money(result.get("imports")) + " from " + _money(result.get("imports_free_trade"))
             + " free-trade units, and the tariff raises " + _money(result.get("tariff_revenue")) + "."]
    lines.append("The deadweight loss is " + _money(result.get("total_dwloss"))
                 + " (production " + _money(result.get("production_dwloss")) + ", consumption "
                 + _money(result.get("consumption_dwloss")) + "); the welfare arithmetic uses the declared "
                 "curves.")
    return lines


def _advantage_lines(row, inputs, result):
    countries = inputs.get("countries") or []
    first = str((countries[0] or {}).get("name") if countries else "the first country")
    second = str((countries[1] or {}).get("name") if len(countries) > 1 else "the second country")
    lines = ["From the declared hours per unit, " + first + " gives up "
             + _money(result.get("oc_a_good1")) + " units of good 2 per unit of good 1 (and "
             + _money(result.get("oc_a_good2")) + " the other way round); " + second + " gives up "
             + _money(result.get("oc_b_good1")) + " units of good 2 per unit of good 1 (and "
             + _money(result.get("oc_b_good2")) + " the other way round)."]
    if str(result.get("a_has_advantage_good1")).lower() in ("true", "yes", "1"):
        lines.append(first + " has the comparative advantage in good 1 and " + second + " in good 2.")
    else:
        lines.append(second + " has the comparative advantage in good 1 and " + first + " in good 2.")
    lines.append("The comparison uses the declared labour requirements only.")
    return lines


def _ppp_lines(row, inputs, result):
    lines = ["At declared prices of " + _money(inputs.get("price_domestic")) + " and "
             + _money(inputs.get("price_foreign")) + " and a declared nominal rate of "
             + _fmt_exact(inputs.get("nominal_rate")) + ", purchasing-power parity implies a rate of "
             + _money(result.get("ppp_rate")) + "; the real exchange rate is "
             + _money(result.get("real_exchange_rate")) + " and the misalignment "
             + _pct(result.get("misalignment")) + "%."]
    lines.append("The comparison uses the declared prices and rate; no market rate is retrieved.")
    return lines


def _irp_lines(row, inputs, result):
    lines = ["At a declared spot rate of " + _fmt_exact(inputs.get("spot_rate")) + " and interest rates of "
             + _pct(inputs.get("domestic_rate")) + "% and " + _pct(inputs.get("foreign_rate"))
             + "%, covered interest parity implies a forward rate of "
             + _money(result.get("implied_forward")) + ", a premium of "
             + _pct(result.get("forward_premium")) + "%."]
    lines.append("The forward is arithmetic on the declared rates; it is not a forecast of the spot rate.")
    return lines


def _bop_lines(row, inputs, result):
    balanced = "balances" if str(result.get("balanced")).lower() in ("true", "yes", "1") else "does not balance"
    lines = ["With the declared current, capital and financial accounts, the net balance is "
             + _money(result.get("net_balance")) + ", so the statement " + balanced
             + " before any declared errors and omissions."]
    lines.append("The accounts are the student's declaration; the method does not reconcile them for you.")
    return lines


def _hdi_lines(row, inputs, result):
    lines = ["From the declared life expectancy, schooling and income, the health index is "
             + _money(result.get("life_index")) + ", the education index "
             + _money(result.get("education_index")) + " and the income index "
             + _money(result.get("income_index")) + ", giving a human development index of "
             + _money(result.get("hdi")) + "."]
    lines.append("The index is the declared formula on the declared indicators; the data are not retrieved.")
    return lines


def _expected_utility_lines(row, inputs, result):
    lines = ["On the declared outcomes and probabilities, the expected value is "
             + _money(result.get("expected_value")) + " and the expected utility "
             + _money(result.get("expected_utility")) + "; the certainty equivalent is "
             + _money(result.get("certainty_equivalent")) + " and the risk premium "
             + _money(result.get("risk_premium")) + "."]
    lines.append("The utility function and the declared probabilities drive the result; the method does not "
                 "estimate preferences.")
    return lines


def _prospect_lines(row, inputs, result):
    lines = ["On the declared outcomes around the declared reference point, prospect theory gives a value of "
             + _money(result.get("prospect_value")) + " against an expected value of "
             + _money(result.get("expected_value")) + "."]
    lines.append("The gap comes from the declared loss aversion, curvature and probability weighting; the "
                 "method does not measure those parameters.")
    return lines


def _did_lines(row, inputs, result):
    lines = ["The treated group changed by " + _money(result.get("treated_change")) + " and the control group by "
             + _money(result.get("control_change")) + ", so the difference-in-differences estimate is "
             + _money(result.get("did_estimate")) + "."]
    lines.append("The estimate assumes the two groups would have moved together without the intervention; that "
                 "assumption is the student's, not the method's.")
    return lines


def _iv_lines(row, inputs, result):
    lines = ["With the declared instrument, the two-stage estimate of the slope is "
             + _money(result.get("iv_slope")) + " against an ordinary least-squares slope of "
             + _money(result.get("ols_slope")) + "; the first-stage slope is "
             + _money(result.get("first_stage_slope")) + " on " + _fmt_exact(result.get("n"))
             + " observation(s)."]
    lines.append("The estimate is only as good as the declared instrument; the method does not test exclusion.")
    return lines


def _panel_lines(row, inputs, result):
    lines = ["On " + _fmt_exact(result.get("n_obs")) + " observation(s) across "
             + _fmt_exact(result.get("n_entities")) + " entity(ies) and "
             + _fmt_exact(result.get("n_periods")) + " period(s), the within slope is "
             + _money(result.get("slope")) + " with a within R squared of "
             + _money(result.get("within_r2")) + "."]
    lines.append("The model absorbs the declared entity effects; it does not establish causation.")
    return lines


def _rdd_lines(row, inputs, result):
    lines = ["Around the declared cutoff, the jump estimate is " + _money(result.get("estimate"))
             + ", from " + _fmt_exact(result.get("n_left")) + " observation(s) below and "
             + _fmt_exact(result.get("n_right")) + " above."]
    lines.append("The estimate assumes the declared running variable is continuous at the cutoff; the method "
                 "does not test that assumption.")
    return lines


def _probit_lines(row, inputs, result):
    lines = ["The declared binary outcomes give a probit slope of " + _money(result.get("slope"))
             + " with a pseudo R squared of " + _money(result.get("pseudo_r2"))
             + " and a marginal effect at the mean of "
             + _money(result.get("marginal_effect_at_mean")) + "."]
    lines.append("The model describes the declared sample; a coefficient is not a causal effect.")
    return lines


def _cpm_lines(row, inputs, result):
    critical = []
    for activity in inputs.get("activities") or []:
        name = str(activity.get("id") or "")
        if name and str(result.get("critical_" + name)) in ("1", "True", "true"):
            critical.append(name)
    lines = ["On the declared activities, the project duration is "
             + _money(result.get("project_duration")) + " periods across "
             + _fmt_exact(result.get("activity_count")) + " activity(ies)"
             + ("; the critical path runs through " + ", ".join(critical) if critical else "") + "."]
    lines.append("The dates and floats are the method's output for the declared durations and predecessors; "
                 "they are not a committed schedule.")
    return lines


def _levelling_lines(row, inputs, result):
    lines = ["The declared activities give a critical-path duration of "
             + _money(result.get("cpm_duration")) + " and a levelled duration of "
             + _money(result.get("levelled_duration")) + ", a levelling delay of "
             + _money(result.get("levelling_delay")) + " periods."]
    lines.append("Overallocated periods fall from "
                 + _fmt_exact(result.get("overallocated_periods_before")) + " to "
                 + _fmt_exact(result.get("overallocated_periods_after")) + ", and peak demand from "
                 + _money(result.get("peak_demand_before")) + " to "
                 + _money(result.get("peak_demand_after")) + " against the declared capacities.")
    return lines


def _crashing_lines(row, inputs, result):
    lines = ["Crashing from the declared normal duration of " + _money(result.get("normal_duration"))
             + " to " + _money(result.get("crashed_duration")) + " periods costs "
             + _money(result.get("total_crash_cost")) + " on the declared crash costs."]
    target = result.get("target_duration")
    if target not in (None, ""):
        lines.append("The declared target was " + _money(target) + " periods.")
    lines.append("The method reports the cheapest declared way to shorten the work; it does not judge whether "
                 "the target is worth its cost.")
    return lines


def _schedule_risk_lines(row, inputs, result):
    lines = ["Across " + _fmt_exact(result.get("iterations")) + " seeded simulations, the project duration has a "
             "mean of " + _money(result.get("mean_duration")) + " periods, a P50 of "
             + _money(result.get("p50_duration")) + ", a P80 of " + _money(result.get("p80_duration"))
             + " and a P90 of " + _money(result.get("p90_duration")) + "."]
    probability = result.get("probability_within_target")
    if probability not in (None, ""):
        lines.append("The probability of finishing within the declared target is "
                     + _pct(probability) + "%.")
    lines.append("The range follows from the declared three-point estimates and the declared seed; it is not a "
                 "forecast of the real project.")
    return lines


def _calendar_lines(row, inputs, result):
    lines = ["On the declared working periods (" + str(result.get("working_periods") or "")
             + "), the project runs for " + _money(result.get("project_duration"))
             + " working periods across " + _fmt_exact(result.get("activity_count"))
             + " activity(ies), with " + _fmt_exact(result.get("critical_count"))
             + " on the critical path."]
    lines.append("The dates follow from the declared durations and the declared working periods; the method "
                 "does not know the real calendar.")
    return lines


def _matrix_lines(row, inputs, result):
    names = [str(criterion.get("name")) for criterion in inputs.get("criteria") or []]
    ranking = []
    for index in range(1, int(Decimal(str(result.get("alternative_count") or "0"))) + 1):
        total = result.get("total_%d" % index)
        if total in (None, ""):
            continue
        alternative = ""
        rows = inputs.get("alternatives") or []
        if index - 1 < len(rows):
            alternative = str(rows[index - 1].get("name") or "")
        ranking.append(str(result.get("rank_%d" % index)) + ". " + alternative + " ("
                       + _money(total) + ")")
    lines = ["Scoring " + _fmt_exact(result.get("alternative_count")) + " alternative(s) against "
             + _fmt_exact(result.get("criteria_count")) + " weighted criteria (weights summing to "
             + _money(result.get("weight_sum")) + "), the ranking is: " + "; ".join(ranking) + "."]
    lines.append("The highest weighted score is " + _money(result.get("best_total"))
                 + ". The scores and the weights are the student's declaration; the method does not measure "
                 "either.")
    return lines


def _monte_carlo_lines(row, inputs, result):
    probability = result.get("probability_positive")
    lines = ["Across " + _fmt_exact(result.get("iterations")) + " seeded draws, the simulated result has a "
             "mean of " + _money(result.get("mean_result")) + ", a P10 of "
             + _money(result.get("p10_result")) + ", a P50 of " + _money(result.get("p50_result"))
             + " and a P90 of " + _money(result.get("p90_result")) + "."]
    if probability not in (None, ""):
        lines.append("The share of draws above zero is " + _pct(probability) + "%.")
    lines.append("The range follows from the declared distributions and the declared seed; it is not a "
                 "forecast of the case.")
    return lines


def _decision_tree_lines(row, inputs, result):
    alternatives = (inputs.get("tree") or {}).get("alternatives") or []
    parts = []
    for index in range(1, int(Decimal(str(result.get("alternative_count") or "0"))) + 1):
        value = result.get("ev_%d" % index)
        if value in (None, ""):
            continue
        name = ""
        if index - 1 < len(alternatives):
            name = str(alternatives[index - 1].get("name") or "")
        probability = result.get("loss_probability_%d" % index)
        parts.append(name + " " + _money(value)
                     + (" (chance of a loss " + _pct(probability) + "%"
                        if probability not in (None, "") else "") + ")")
    lines = ["On the declared tree, " + "; ".join(parts) + "; the best expected value is "
             + _money(result.get("expected_value")) + " on alternative "
             + _fmt_exact(result.get("best_index")) + "."]
    lines.append("The values and the branch probabilities are the student's declaration; the tree does not "
                 "choose for them.")
    return lines


def _multi_project_lines(row, inputs, result):
    projects = inputs.get("projects") or []
    parts = []
    for project in projects:
        name = str(project.get("name") or "")
        finish = result.get("finish_" + name)
        if finish in (None, ""):
            continue
        parts.append(name + " finishes at " + _money(finish) + " (delay "
                     + _money(result.get("delay_" + name)) + " periods)")
    lines = ["Scheduling the declared projects against the declared shared capacity gives an overall duration of "
             + _money(result.get("overall_duration")) + " periods across "
             + _fmt_exact(result.get("project_count")) + " project(s): " + "; ".join(parts) + "."]
    lines.append("The order follows the declared priorities; the method reports the delays that order causes.")
    return lines


def _time_value_lines(row, inputs, result):
    """Time value of money: the future value, the payments' present value and the EAR.

    Every figure is the frozen method's output for the declared inputs; nothing is
    estimated here, and each number is printed at the paper's two-decimal precision
    (D-FIN-02).
    """
    periods = _fmt_exact(result.get("n_periods"))
    lines = ["At a declared present value of " + _money(inputs.get("present_value"))
             + ", a declared payment of " + _money(inputs.get("payment") or "0")
             + " per period and a declared rate of " + _pct(inputs.get("rate")) + "% over "
             + periods + " periods (" + str(inputs.get("compounding") or "annual")
             + " compounding, payments at the " + str(inputs.get("timing") or "end") + "), the "
             "future value is " + _money(result.get("future_value")) + " and the present value "
             "of the payments is " + _money(result.get("present_value_payments")) + "."]
    lines.append("The rate actually applied per period is " + _pct(result.get("periodic_rate"))
                 + "%, so the effective annual rate is "
                 + _pct(result.get("effective_annual_rate")) + "%.")
    lines.append("Every figure is arithmetic on your declared inputs; the method chooses no rate and "
                 "assumes the payment is level.")
    return lines


def _leverage_lines(row, inputs, result):
    """EPS, the leverage degree, the tax shield, the Z-score and the indifference EBIT."""
    lines = ["On declared EBIT of " + _money(inputs.get("ebit")) + " and interest of "
             + _money(inputs.get("interest_expense")) + ", earnings per share are "
             + _money(result.get("eps")) + ", the degree of financial leverage is "
             + _fmt_number(result.get("degree_of_financial_leverage"))
             + " and interest cover is " + _fmt_number(result.get("interest_cover")) + " times."]
    lines.append("The interest tax shield at the declared rate is "
                 + _money(result.get("interest_tax_shield")) + " and debt to equity is "
                 + _fmt_number(result.get("debt_to_equity")) + ".")
    if result.get("altman_z") not in (None, ""):
        lines.append("The five-term Altman Z is " + _fmt_number(result.get("altman_z"))
                     + ". The score is reported; no zone cut-off is applied, because the boundaries "
                     "are a convention the method does not choose for you.")
    if result.get("indifference_ebit") not in (None, ""):
        lines.append("The two declared financing plans give the same earnings per share at an EBIT of "
                     + _money(result.get("indifference_ebit")) + " ("
                     + _money(result.get("eps_at_indifference")) + " per share).")
    return lines


def _equity_bridge_lines(row, inputs, result):
    """Enterprise value to equity value, through net debt and the declared claims."""
    lines = ["From a declared enterprise value of " + _money(inputs.get("enterprise_value"))
             + " and net debt of " + _money(result.get("net_debt")) + ", the equity value is "
             + _money(result.get("equity_value")) + "."]
    if result.get("per_share_value") not in (None, ""):
        lines.append("Across the declared " + _fmt_exact(inputs.get("shares_outstanding"))
                     + " shares, that is " + _money(result.get("per_share_value")) + " per share.")
    lines.append("The bridge subtracts only the claims you declared; minority interest, preferred "
                 "equity and any other claim are your own figures, not estimates.")
    return lines


CAPABILITY_LINES.update({
    "time_value": _time_value_lines,
    "leverage_analysis": _leverage_lines,
    "equity_bridge": _equity_bridge_lines,

    "irr": _irr_lines,
    "discounted_payback": _payback_lines,
    "project_metrics": _project_metrics_lines,
    "unit_economics": _unit_economics_lines,
    "wacc": _wacc_lines,
    "cash_runway": _cash_runway_lines,
    "market_sizing": _market_sizing_lines,
    "market_share": _market_share_lines,
    "clv_model": _clv_lines,
    "earned_value": _earned_value_lines,
    "multi_product_breakeven": _multi_breakeven_lines,
    "capm": _capm_lines,
    "bond_analysis": _bond_lines,
    "ratio_analysis": _ratio_lines,
    "dcf_valuation": _dcf_lines,
    "multiples_valuation": _multiples_lines,
    "option_pricing": _option_lines,
    "real_option": _real_option_lines,
    "portfolio_analysis": _portfolio_lines,
    "descriptive_stats": _descriptive_lines,
    "pearson": _pearson_lines,
    "welch_t": _welch_lines,
    "anova": _anova_lines,
    "chi_square": _chi_square_lines,
    "ols": _ols_lines,
    "queue_analysis": _queue_lines,
    "capacity_analysis": _capacity_lines,
    "oee_analysis": _oee_lines,
    "process_control": _process_control_lines,
    "demand_curve": _demand_curve_lines,
    "rfm_scoring": _rfm_lines,
    "sales_funnel": _funnel_lines,
    "ab_test_two_proportion": _abtest_lines,
    "social_engagement": _social_lines,
    "reliability_alpha": _alpha_lines,
    "weighted_summary": _weighted_lines,
    "power_analysis": _power_lines,
    "cohort_retention": _cohort_lines,
    "trend_forecast": _forecast_lines,
    "missing_data_bounds": _missing_lines,
    "media_plan": _media_lines,
    "web_analytics": _web_lines,
    "email_list_health": _email_lines,
    "customer_profitability": _segment_lines,
    "channel_economics": _channel_lines,
    "attribution_split": _attribution_lines,
    "line_balancing": _line_lines,
    "dupont_analysis": _dupont_lines,
    "trend_analysis": _trend_lines,
    "working_capital": _working_capital_lines,
    "loan_amortization": _loan_lines,
    "tax_declared": _tax_lines,
    "scenario_analysis": _scenario_lines,
    "risk_metrics": _risk_lines,
    "fx_parity": _fx_lines,
    "currency_convert": _convert_lines,
    "ols_robust": _ols_lines,
    "market_concentration": _concentration_lines,
    "cost_curves": _cost_curve_lines,
    "market_power": _market_power_lines,
    "proforma_statements": _proforma_lines,
    "sensitivity_table": _sensitivity_lines,
    "sroi": _sroi_lines,
    "cost_benefit": _cba_lines,
    "cost_effectiveness": _cea_lines,
    "demand_supply_equilibrium": _equilibrium_lines,
    "price_control": _price_control_lines,
    "profit_maximization": _profit_max_lines,
    "price_discrimination": _discrimination_lines,
    "cournot_duopoly": _cournot_lines,
    "nash_equilibrium": _nash_lines,
    "national_income": _national_income_lines,
    "unemployment_rate": _unemployment_lines,
    "labour_market": _real_wage_lines,
    "money_multiplier": _money_multiplier_lines,
    "fiscal_multiplier": _fiscal_multiplier_lines,
    "budget_debt": _budget_lines,
    "output_gap_okun": _okun_lines,
    "externality_pigouvian": _externality_lines,
    "public_good": _public_good_lines,
    "optimal_pollution": _pollution_lines,
    "social_welfare": _welfare_lines,
    "gini_coefficient": _gini_lines,
    "poverty_measures": _poverty_lines,
    "tax_progressivity": _progressivity_lines,
    "tariff_welfare": _tariff_lines,
    "comparative_advantage": _advantage_lines,
    "exchange_rate_ppp": _ppp_lines,
    "interest_rate_parity": _irp_lines,
    "balance_of_payments": _bop_lines,
    "hdi": _hdi_lines,
    "expected_utility": _expected_utility_lines,
    "prospect_theory": _prospect_lines,
    "difference_in_differences": _did_lines,
    "instrumental_variables": _iv_lines,
    "panel_regression": _panel_lines,
    "regression_discontinuity": _rdd_lines,
    "probit": _probit_lines,
    "cpm_schedule": _cpm_lines,
    "resource_leveling": _levelling_lines,
    "project_crashing": _crashing_lines,
    "schedule_risk": _schedule_risk_lines,
    "calendar_schedule": _calendar_lines,
    "multi_criteria": _matrix_lines,
    "monte_carlo": _monte_carlo_lines,
    "decision_tree": _decision_tree_lines,
    "multi_project_schedule": _multi_project_lines,
})


def _fmt_exact(value):
    """Print a recorded value without inventing precision or losing it."""
    text = str(value)
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return text
    if number == number.to_integral():
        return "{:,.0f}".format(number)
    if abs(number) >= 1 and number.as_tuple().exponent >= -2:
        return "{:,.2f}".format(number)
    return text


def _generic_lines(row, inputs, result):
    """The honest fallback: the declared inputs and the recorded output, in prose.

    The core echoes the declared inputs in its result; those are dropped here so
    the paragraph reports what the method produced, not what the student typed.
    """
    declared = "; ".join((name.replace("_", " ") + " " + _fmt_exact(value))
                         for name, value in (inputs or {}).items())
    computed = {name: value for name, value in (result or {}).items()
                if name not in (inputs or {}) and not str(name).startswith("_")}
    produced = "; ".join((name.replace("_", " ") + " " + _fmt_exact(value))
                         for name, value in computed.items())
    head = ("From the declared inputs (" + declared + "), ") if declared else ""
    if produced:
        lines = [head + "the frozen " + row["label"].lower() + " method returns " + produced + "."]
    else:
        lines = [head + "the frozen " + row["label"].lower()
                 + " method recorded no output beyond the declared inputs."]
    lines.append("The figures are the method's recorded output; they are not a forecast and they "
                 "hold only for the inputs the student declared.")
    return lines


def _capability_lines(row, recorded):
    """Format one recorded capability for the draft; a gap is named, never filled."""
    key = row["key"]
    if recorded.get("ok"):
        formatter = CAPABILITY_LINES.get(key)
        try:
            if formatter is None:
                return _generic_lines(row, recorded.get("inputs") or {}, recorded.get("result") or {})
            return formatter(row, recorded.get("inputs") or {}, recorded.get("result") or {})
        except (KeyError, TypeError, InvalidOperation, ValueError) as error:
            # A formatter that cannot read the recorded result must say so, not crash
            # the draft and not print a half-built sentence.
            return ["The " + row["label"].lower() + " result could not be read from the recorded output ("
                    + str(error)[:120] + "); no figure is reported."]
    if recorded.get("error"):
        return ["The " + row["label"].lower() + " analysis was refused: " + str(recorded["error"])
                + " No figure is reported."]
    return ["The " + row["label"].lower() + " analysis has not been run, so no figure is reported; "
            "this is a named gap, not a result."]


def _declared_inputs_line(recorded):
    """The declared inputs of one computation, as the paper states them.

    An input that came from another frozen result says so, so a chained figure is
    never mistaken for one the student typed or the paper invented.
    """
    inputs = (recorded or {}).get("inputs") or {}
    if not inputs:
        return ""
    sources = (recorded or {}).get("from") or {}
    pieces = []
    for name, value in inputs.items():
        source = ""
        if name in sources:
            try:
                source = " (from the " + capabilities.entry(sources[name])["label"].lower() + " result)"
            except KeyError:
                source = " (from a frozen result)"
        if isinstance(value, list):
            pieces.append(name.replace("_", " ") + " " + "; ".join(str(item) for item in value) + source)
        elif isinstance(value, dict):
            pieces.append(name.replace("_", " ") + " (" + ", ".join(str(k) for k in value) + ")" + source)
        else:
            pieces.append(name.replace("_", " ") + " " + _fmt_exact(value) + source)
    return "Declared inputs: " + "; ".join(pieces) + "."


def _plan_input(state, key):
    value = (state["answers"].get("inputs") or {}).get(key)
    if isinstance(value, list):
        return "; ".join(value)
    return _clean(value, 2000)


def _pct_sign(value):
    try:
        return "{:.1f}%".format(float(Decimal(str(value))) * 100)
    except (InvalidOperation, ValueError):
        return str(value)


def _plan_block(state, key):
    return (state.get("computations") or {}).get(key)


def _block_lines(state, block):
    """Format one stored core result.  No formula or rounding is repeated here."""
    data = _plan_block(state, block["key"])
    if not data:
        return ["This computation has not been run, so no figure is reported."]
    if not data.get("ok"):
        return ["This computation was refused: " + str(data.get("error")) + " No figure is reported."]
    result, inputs = data.get("result") or {}, data.get("inputs") or {}
    key = block["key"]
    if key == "frommarket":
        return ["A declared target share of " + _pct_sign(inputs.get("target_share")) + " of a market of "
                + _fmt_number(inputs.get("market_size")) + " at a price of " + _fmt_number(inputs.get("price"))
                + " gives target revenue of " + _fmt_number(result.get("target_revenue")) + " and "
                + _fmt_number(result.get("target_units")) + " units."]
    if key == "breakeven":
        return _break_even_lines(inputs, result)
    if key == "depreciation":
        return ["Depreciation on a cost of " + _fmt_number(result.get("cost")) + " to a salvage value of "
                + _fmt_number(result.get("salvage")) + " over " + _fmt_number(result.get("life"))
                + " periods totals " + _fmt_number(result.get("total_depreciation"))
                + ", leaving a carrying amount of " + _fmt_number(result.get("final_carrying")) + "."]
    if key == "proforma":
        periods = len(inputs.get("revenue") or [])
        lines = []
        for period in range(1, periods + 1):
            lines.append("In period " + str(period) + ", revenue is " + _fmt_number(result.get("revenue_%d" % period))
                         + ", net income is " + _fmt_number(result.get("net_income_%d" % period))
                         + " and closing cash is " + _fmt_number(result.get("closing_cash_%d" % period)) + ".")
        lines.append("Over the declared periods, revenue totals " + _fmt_number(result.get("total_revenue"))
                     + " and net income totals " + _fmt_number(result.get("total_net_income"))
                     + ", closing with cash of " + _fmt_number(result.get("closing_cash_final"))
                     + " and equity of " + _fmt_number(result.get("closing_equity_final")) + ".")
        sales = _plan_block(state, "frommarket")
        if sales and sales.get("ok"):
            target = Decimal(str(sales["result"].get("target_revenue")))
            first = Decimal(str(result.get("revenue_1")))
            if first == target:
                lines.append("The declared period-1 revenue matches the " + _fmt_number(target)
                             + " target revenue from the declared market share.")
            else:
                lines.append("The declared period-1 revenue is " + _fmt_number(first) + ", against target revenue of "
                             + _fmt_number(target) + " from the declared market share.")
        lines.append("The projected balance sheet balances at the opening date and at the end of every period, "
                     "as the method checks.")
        return lines
    if key == "sensitivity":
        prices, volumes = inputs.get("price_changes") or [], inputs.get("volume_changes") or []
        cells = [(name, Decimal(str(value))) for name, value in result.items() if name.startswith("profit_")]
        lines = ["At the declared base case, profit is " + _fmt_number(result.get("base_profit")) + "."]
        if cells:
            low, high = min(cells, key=lambda pair: pair[1]), max(cells, key=lambda pair: pair[1])
            low_i, low_j = (int(part) - 1 for part in low[0].split("_")[1:])
            high_i, high_j = (int(part) - 1 for part in high[0].split("_")[1:])
            lines.append("Across the declared changes, profit ranges from " + _fmt_number(low[1])
                         + " at a price change of " + _pct_sign(prices[low_i]) + " and a volume change of "
                         + _pct_sign(volumes[low_j]) + ", to " + _fmt_number(high[1])
                         + " at a price change of " + _pct_sign(prices[high_i]) + " and a volume change of "
                         + _pct_sign(volumes[high_j]) + ".")
        lines.append("Each cell is the profit identity at the changed price and volume; the unit cost and the "
                     "fixed cost stay at the base case.")
        return lines
    if key == "tax":
        lines = ["Income tax at the declared rate is " + _fmt_number(result.get("income_tax"))
                 + " and the after-tax income is " + _fmt_number(result.get("net_income_after_tax")) + "."]
        if "vat_payable" in result:
            lines.append("VAT payable is " + _fmt_number(result.get("vat_payable")) + ".")
        if "deferred_tax" in result:
            lines.append("The deferred tax charge is " + _fmt_number(result.get("deferred_tax"))
                         + " and the total tax charge is " + _fmt_number(result.get("total_tax_charge")) + ".")
        return lines
    if key == "captable":
        return ["After the round the post-money value is " + _fmt_number(result.get("post_money_valuation"))
                + ", the price per share is " + _fmt_number(result.get("price_per_share"))
                + ", the new shares number " + _fmt_number(result.get("new_shares"))
                + ", the investor holds " + _pct_sign(result.get("investor_pct"))
                + " and the founders hold " + _pct_sign(result.get("founder_pct")) + "."]
    if key == "impact":
        lines = []
        for name, value in result.items():
            if name.startswith("icer_"):
                lines.append("Against the comparator, the incremental cost per unit of effect for "
                             + name[5:].replace("_", " ") + " is " + _fmt_number(value) + ".")
        return lines or ["The cost-effectiveness result has no incremental ratio to report."]
    return ["The computation returned a result."]


def _plan_reference_section(state, evidence, style, numbers=None):
    """One reference list, built from the evidence the student accepted (B-182).

    Every plan profile ships the same list: a source is cited once (DOI or title),
    and a plan with no accepted evidence says so rather than printing nothing.
    """
    references, seen = [], set()
    for source in state["sources"]:
        if source["id"] not in {item["source_id"] for item in evidence}:
            continue
        key = source.get("doi") or _clean(source.get("title"), 120).lower()
        if key in seen:
            continue
        seen.add(key)
        references.append(_reference(source, style, numbers))
    from . import citation_styles
    heading = citation_styles.reference_heading(style)
    return paper.section(heading, paper.H1, references or ["No sources were used."])


def _store_plan_draft(state, sections, style, accepted, title, profile):
    """Store a plan draft the way every plan profile must.

    The business plan did this and the other three did not: they stored `sections`
    alone, so `draft["title"]`, `draft["outline"]` and `draft["missing"]` were absent
    — the export crashed reading the title instead of naming what was missing, and
    the page's "complete the plan" gate had nothing to read.  One shape, one writer.
    """
    state["claim_problems"] = _claim_scan(sections)
    state["draft"] = {"title": title, "sections": paper.flatten(sections), "outline": sections,
                      "style": style, "profile": profile,
                      "level": state.get("level") or "shs",
                      "accepted": sorted(accepted), "missing": paper.missing(state),
                      "created_at": _now()}
    state["stage"] = "draft"
    state["updated_at"] = _now()
    return state


def _draft_plan(state, accepted_ids=None, style=None):
    """Compose the business plan from student inputs, accepted evidence and stored core results."""
    if state.get("stage") not in ("evidence", "evidence_reviewed", "computed", "inputs", "draft"):
        raise ChatError("Confirm the plan and supply its inputs before drafting.")
    plan = state.get("plan") or {}
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    sections = []
    name = _plan_input(state, "business_name")
    product = _plan_input(state, "product")
    customers = _plan_input(state, "customers")
    location = _plan_input(state, "location")

    # -- executive summary (integration, from supplied facts and stored results)
    intro = ["This plan sets out " + (name or "the business") + "."]
    if product:
        intro.append("It sells " + product + ".")
    if customers:
        intro.append("Its customers are " + customers + ".")
    if location:
        intro.append("It operates in " + location + ".")
    sales = _plan_block(state, "frommarket")
    if sales and sales.get("ok"):
        result = sales["result"]
        intro.append("From the declared market and share, target revenue is "
                     + _fmt_number(result.get("target_revenue")) + " and target volume is "
                     + _fmt_number(result.get("target_units")) + " units.")
    proforma = _plan_block(state, "proforma")
    if proforma and proforma.get("ok"):
        intro.append("Across the projected periods, revenue totals "
                     + _fmt_number(proforma["result"].get("total_revenue")) + " and net income totals "
                     + _fmt_number(proforma["result"].get("total_net_income")) + ".")
    sections.append(paper.section("Executive Summary", paper.H1, [paper.paragraph(intro)]))

    # -- business description (student input)
    description = []
    if name:
        description.append("The business is " + name + ".")
    if product:
        description.append("It sells " + product + ".")
    if customers:
        description.append("Its customers are " + customers + ".")
    if location:
        description.append("It operates in " + location + ".")
    sections.append(paper.section("Business Description", paper.H1,
                                  [paper.paragraph(description or ["The business description has not been supplied."])]))

    # -- market analysis (evidence, or a named gap per dimension)
    sections.append(paper.section("Market Analysis", paper.H1))
    for dimension in plan.get("dimensions") or []:
        tuple_dimension = (dimension["key"], dimension["label"], dimension.get("cues") or "", dimension.get("category"))
        lines = _dimension_lines(tuple_dimension, evidence, by_id, style)
        sections.append(paper.section(dimension["label"], paper.H2, [paper.paragraph(lines)]))

    # -- marketing, operations and management (student input)
    marketing = []
    for key, lead in (("positioning", "The business is positioned as "),
                      ("channels", "It will reach customers through "),
                      ("pricing_note", "Its pricing approach is ")):
        text = _plan_input(state, key)
        if text:
            marketing.append(lead + text.rstrip(".") + ".")
    sections.append(paper.section("Marketing Plan", paper.H1,
                                  [paper.paragraph(marketing or ["The marketing plan has not been supplied."])]))
    operations = []
    for key, lead in (("operations", "The business will operate as follows: "),
                      ("suppliers", "It depends on "),
                      ("capacity_note", "Its capacity requirement is ")):
        text = _plan_input(state, key)
        if text:
            operations.append(lead + text.rstrip(".") + ".")
    sections.append(paper.section("Operations Plan", paper.H1,
                                  [paper.paragraph(operations or ["The operations plan has not been supplied."])]))
    management = []
    team = _plan_input(state, "team")
    roles = _plan_input(state, "roles")
    if team:
        management.append("The business will be run by " + team.rstrip(".") + ".")
    if roles:
        management.append("Responsibilities are: " + roles.rstrip(".") + ".")
    sections.append(paper.section("Management and Organisation", paper.H1,
                                  [paper.paragraph(management or ["The management team has not been supplied."])]))

    # -- the Financial Plan: one H1 with its computation blocks as H2s
    sections.append(paper.section("Financial Plan", paper.H1))
    for block in plan.get("blocks") or []:
        if block.get("section") != "financial_plan":
            continue
        sections.append(paper.section(block["label"], paper.H2, [paper.paragraph(_block_lines(state, block))]))

    # -- college blocks
    funding = [block for block in plan.get("blocks") or [] if block.get("section") == "funding"]
    if funding:
        sections.append(paper.section("Funding and Ownership", paper.H1))
        for block in funding:
            sections.append(paper.section(block["label"], paper.H2, [paper.paragraph(_block_lines(state, block))]))
    impact = [block for block in plan.get("blocks") or [] if block.get("section") == "impact"]
    if impact:
        sections.append(paper.section("Social and Environmental Impact", paper.H1))
        text = _plan_input(state, "impact_summary")
        if text:
            sections.append(paper.section("Expected Impact", paper.H2, [paper.paragraph([text])]))
        for block in impact:
            sections.append(paper.section(block["label"], paper.H2, [paper.paragraph(_block_lines(state, block))]))

    # -- risk analysis (integration)
    sections.append(paper.section("Risk Analysis", paper.H1))
    sensitivity = next((block for block in plan.get("blocks") or [] if block["key"] == "sensitivity"), None)
    if sensitivity:
        sections.append(paper.section("Sensitivity of Profit", paper.H2,
                                      [paper.paragraph(_block_lines(state, sensitivity))]))
    risks = (state["answers"].get("inputs") or {}).get("risks") or []
    risk_lines = (["The owner names the following risks: " + "; ".join(risks) + "."] if risks
                  else ["No risks were supplied."])
    sections.append(paper.section("Risks Named by the Owner", paper.H2, [paper.paragraph(risk_lines)]))

    gaps = [gap["label"] for gap in state.get("gaps") or []]
    limits = []
    if gaps:
        limits.append("No evidence was retrieved for: " + ", ".join(gaps) + ".")
    limits.append("The business description, marketing, operations, management and risks are the student's "
                  "input; the system did not verify them.")
    limits += ["The financial figures are arithmetic on the declared drivers, not a demand forecast.",
               "The market size, share, price, costs and opening balances are declarations, not retrieved facts."]
    if any(block["key"] == "sensitivity" for block in plan.get("blocks") or []):
        limits.append("The sensitivity table changes price and volume only; unit cost and fixed cost stay at the "
                      "base case.")
    if any(block["key"] == "tax" for block in plan.get("blocks") or []):
        limits.append("Tax follows the declared rates, not a jurisdiction's tax law.")
    if any(block["key"] == "impact" for block in plan.get("blocks") or []):
        limits.append("The impact ratio compares declared options; it is not a recommendation.")
    sections.append(paper.section("Limitations", paper.H2, [paper.paragraph(limits)]))

    # -- conclusion (integration, no new evidence)
    conclusion = ["The plan proposes " + (name or "the business") + "."]
    if sales and sales.get("ok"):
        conclusion.append("The declared market share supports target revenue of "
                          + _fmt_number(sales["result"].get("target_revenue")) + ".")
    if proforma and proforma.get("ok"):
        conclusion.append("The projected statements report net income of "
                          + _fmt_number(proforma["result"].get("total_net_income"))
                          + " over the declared periods from the declared drivers.")
    conclusion.append("The named risks and the limitations qualify the plan; every figure in it is a declared "
                      "input or a core computation, not a forecast.")
    sections.append(paper.section("Conclusion", paper.H1, [paper.paragraph(conclusion)]))

    # -- one reference list
    sections.append(_plan_reference_section(state, evidence, style))

    return _store_plan_draft(state, sections, style, accepted,
                             "Business plan: " + (name or _clean(plan.get("decision"), 180)),
                             PROFILE_BUSINESS_PLAN)



def _draft_feasibility_study(state, accepted_ids=None, style=None):
    """Compose the feasibility study from student inputs, accepted evidence and stored core results."""
    if state.get("stage") not in ("evidence", "evidence_reviewed", "computed", "inputs", "draft"):
        raise ChatError("Confirm the plan and supply its inputs before drafting.")
    plan = state.get("plan") or {}
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    sections = []
    name = _plan_input(state, "project_name")
    desc = _plan_input(state, "project_description")
    location = _plan_input(state, "location")
    proponents = _plan_input(state, "proponents")

    # -- executive summary (integration, from supplied facts and stored results)
    intro = ["This feasibility study tests whether " + (name or "the proposed project") + " should proceed."]
    if desc:
        intro.append(desc)
    if location:
        intro.append("It is located in " + location + ".")
    if proponents:
        intro.append("It is proposed by " + proponents + ".")
    sales = _plan_block(state, "frommarket")
    if sales and sales.get("ok"):
        result = sales["result"]
        intro.append("From the declared market and share, target revenue is "
                     + _fmt_number(result.get("target_revenue")) + " and target volume is "
                     + _fmt_number(result.get("target_units")) + " units.")
    proforma = _plan_block(state, "proforma")
    if proforma and proforma.get("ok"):
        intro.append("Across the projected periods, revenue totals "
                     + _fmt_number(proforma.get("result", {}).get("total_revenue")) + ".")
    sections.append(paper.section("Executive Summary", paper.H1, [paper.paragraph(intro)]))

    # -- project description
    lines = []
    if name:
        lines.append("Project: " + name + ".")
    if desc:
        lines.append(desc)
    if location:
        lines.append("Location: " + location + ".")
    if proponents:
        lines.append("Proponents: " + proponents + ".")
    sections.append(paper.section("Project Description", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- market feasibility
    target_market = _plan_input(state, "target_market")
    demand = _plan_input(state, "demand_estimate")
    competitors = _plan_input(state, "competitors")
    lines = []
    if target_market:
        lines.append("Target market: " + target_market + ".")
    if demand:
        lines.append("Estimated demand: " + demand + ".")
    if competitors:
        lines.append("Competitors: " + competitors + ".")
    sections.append(paper.section("Market Feasibility", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- technical feasibility
    technology = _plan_input(state, "technology")
    capacity = _plan_input(state, "capacity")
    inputs = _plan_input(state, "inputs")
    lines = []
    if technology:
        lines.append("Technology or method: " + technology + ".")
    if capacity:
        lines.append("Capacity needed: " + capacity + ".")
    if inputs:
        lines.append("Inputs or resources needed: " + inputs + ".")
    sections.append(paper.section("Technical Feasibility", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- management feasibility
    team = _plan_input(state, "team")
    skills = _plan_input(state, "skills")
    lines = []
    if team:
        lines.append("Management team: " + team + ".")
    if skills:
        lines.append("Skills available: " + skills + ".")
    sections.append(paper.section("Management Feasibility", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- legal feasibility
    permits = _plan_input(state, "permits")
    regulations = _plan_input(state, "regulations")
    lines = []
    if permits:
        lines.append("Permits or licenses needed: " + permits + ".")
    if regulations:
        lines.append("Regulations that apply: " + regulations + ".")
    sections.append(paper.section("Legal and Regulatory Feasibility", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- financial feasibility (computation)
    sections.append(paper.section("Financial Feasibility", paper.H1))
    for block in plan.get("blocks") or []:
        data = _plan_block(state, block["key"])
        if not data:
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation has not been run, so no figure is reported."]))
            continue
        if not data.get("ok"):
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation was refused: " + str(data.get("error"))
                                          + " No figure is reported."]))
            continue
        result = data.get("result") or {}
        inputs_data = data.get("inputs") or {}
        lines = [paper.paragraph([_declared_inputs_line(data)])] if _declared_inputs_line(data) else []
        lines.append(paper.paragraph(_capability_lines(block, data)))
        sections.append(paper.section(block["label"], paper.H2, lines))

    # -- risk
    risks = _plan_input(state, "risks")
    if risks:
        sections.append(paper.section("Risk Analysis", paper.H1, [paper.paragraph([risks])]))

    # -- conclusion and verdict
    verdict = "The feasibility of this project depends on the evidence and figures above."
    sections.append(paper.section("Conclusion", paper.H1, [verdict]))

    # -- references
    sections.append(_plan_reference_section(state, evidence, style))

    return _store_plan_draft(state, sections, style, accepted,
                             "Feasibility study: " + (name or _clean(plan.get("decision"), 180)),
                             PROFILE_FEASIBILITY_STUDY)


def _draft_marketing_plan(state, accepted_ids=None, style=None):
    """Compose the marketing plan from student inputs, accepted evidence and stored core results."""
    if state.get("stage") not in ("evidence", "evidence_reviewed", "computed", "inputs", "draft"):
        raise ChatError("Confirm the plan and supply its inputs before drafting.")
    plan = state.get("plan") or {}
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    sections = []
    name = _plan_input(state, "business_name")
    product = _plan_input(state, "product")
    customers = _plan_input(state, "customers")
    location = _plan_input(state, "location")

    # -- executive summary
    intro = ["This marketing plan sets out how " + (name or "the business") + " will reach its customers."]
    if product:
        intro.append("It sells " + product + ".")
    if customers:
        intro.append("Its customers are " + customers + ".")
    if location:
        intro.append("It operates in " + location + ".")
    sales = _plan_block(state, "frommarket")
    if sales and sales.get("ok"):
        result = sales["result"]
        intro.append("From the declared market and share, target revenue is "
                     + _fmt_number(result.get("target_revenue")) + " and target volume is "
                     + _fmt_number(result.get("target_units")) + " units.")
    sections.append(paper.section("Executive Summary", paper.H1, [paper.paragraph(intro)]))

    # -- business context
    lines = []
    if name:
        lines.append("Business: " + name + ".")
    if product:
        lines.append("Product: " + product + ".")
    if customers:
        lines.append("Customers: " + customers + ".")
    if location:
        lines.append("Location: " + location + ".")
    sections.append(paper.section("Business Context", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- audience and positioning
    target_audience = _plan_input(state, "target_audience")
    positioning = _plan_input(state, "positioning_statement")
    value_prop = _plan_input(state, "value_proposition")
    lines = []
    if target_audience:
        lines.append("Target audience: " + target_audience + ".")
    if positioning:
        lines.append("Positioning: " + positioning + ".")
    if value_prop:
        lines.append("Value proposition: " + value_prop + ".")
    sections.append(paper.section("Audience and Positioning", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- channels and tactics
    channels = _plan_input(state, "channels")
    tactics = _plan_input(state, "tactics")
    content_plan = _plan_input(state, "content_plan")
    lines = []
    if channels:
        lines.append("Channels: " + channels + ".")
    if tactics:
        lines.append("Tactics: " + tactics + ".")
    if content_plan:
        lines.append("Content plan: " + content_plan + ".")
    sections.append(paper.section("Channels and Tactics", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- budget and measurement
    sections.append(paper.section("Budget and Measurement", paper.H1))
    for block in plan.get("blocks") or []:
        data = _plan_block(state, block["key"])
        if not data:
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation has not been run, so no figure is reported."]))
            continue
        if not data.get("ok"):
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation was refused: " + str(data.get("error"))
                                          + " No figure is reported."]))
            continue
        declared = _declared_inputs_line(data)
        result_lines = ([paper.paragraph([declared])] if declared else []) + \
                       [paper.paragraph(_capability_lines(block, data))]
        sections.append(paper.section(block["label"], paper.H2, result_lines))

    budget = _plan_input(state, "budget")
    kpis = _plan_input(state, "kpis")
    measurement = _plan_input(state, "measurement_plan")
    lines = []
    if budget:
        lines.append("Budget: " + budget + ".")
    if kpis:
        lines.append("KPIs: " + kpis + ".")
    if measurement:
        lines.append("Measurement plan: " + measurement + ".")
    if lines:
        sections.append(paper.section("Budget Details", paper.H2, [paper.paragraph(lines)]))

    # -- risk
    risks = _plan_input(state, "risks")
    if risks:
        sections.append(paper.section("Risk Analysis", paper.H1, [paper.paragraph([risks])]))

    # -- conclusion
    sections.append(paper.section("Conclusion", paper.H1, ["The marketing plan above is based on the declared inputs and computations."]))

    # -- references
    sections.append(_plan_reference_section(state, evidence, style))

    return _store_plan_draft(state, sections, style, accepted,
                             "Marketing plan: " + (name or _clean(plan.get("decision"), 180)),
                             PROFILE_MARKETING_PLAN)



def _draft_project_proposal(state, accepted_ids=None, style=None):
    """Compose the project proposal from student inputs, accepted evidence and stored core results."""
    if state.get("stage") not in ("evidence", "evidence_reviewed", "computed", "inputs", "draft"):
        raise ChatError("Confirm the plan and supply its inputs before drafting.")
    plan = state.get("plan") or {}
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    sections = []
    title = _plan_input(state, "project_title")
    problem = _plan_input(state, "problem_statement")
    objectives = _plan_input(state, "objectives")
    location = _plan_input(state, "location")
    proponents = _plan_input(state, "proponents")

    # -- executive summary
    intro = ["This project proposal sets out " + (title or "a defined project") + "."]
    if problem:
        intro.append("The problem it addresses: " + problem + ".")
    if objectives:
        intro.append("Its objectives: " + objectives + ".")
    if location:
        intro.append("It will be implemented in " + location + ".")
    if proponents:
        intro.append("Proposed by " + proponents + ".")
    sales = _plan_block(state, "frommarket")
    if sales and sales.get("ok"):
        result = sales["result"]
        intro.append("From the declared market and share, target revenue is "
                     + _fmt_number(result.get("target_revenue")) + " and target volume is "
                     + _fmt_number(result.get("target_units")) + " units.")
    sections.append(paper.section("Executive Summary", paper.H1, [paper.paragraph(intro)]))

    # -- project description
    lines = []
    if title:
        lines.append("Project title: " + title + ".")
    if problem:
        lines.append("Problem statement: " + problem + ".")
    if objectives:
        lines.append("Objectives: " + objectives + ".")
    if location:
        lines.append("Location: " + location + ".")
    if proponents:
        lines.append("Proponents: " + proponents + ".")
    sections.append(paper.section("Project Description", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- work plan
    activities = _plan_input(state, "activities")
    timeline = _plan_input(state, "timeline")
    deliverables = _plan_input(state, "deliverables")
    lines = []
    if activities:
        lines.append("Activities: " + activities + ".")
    if timeline:
        lines.append("Timeline: " + timeline + ".")
    if deliverables:
        lines.append("Deliverables: " + deliverables + ".")
    sections.append(paper.section("Work Plan and Timeline", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- budget
    sections.append(paper.section("Budget", paper.H1))
    for block in plan.get("blocks") or []:
        data = _plan_block(state, block["key"])
        if not data:
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation has not been run, so no figure is reported."]))
            continue
        if not data.get("ok"):
            sections.append(paper.section(block["label"], paper.H2,
                                         ["This computation was refused: " + str(data.get("error"))
                                          + " No figure is reported."]))
            continue
        declared = _declared_inputs_line(data)
        result_lines = ([paper.paragraph([declared])] if declared else []) + \
                       [paper.paragraph(_capability_lines(block, data))]
        sections.append(paper.section(block["label"], paper.H2, result_lines))

    total_budget = _plan_input(state, "total_budget")
    budget_breakdown = _plan_input(state, "budget_breakdown")
    funding_source = _plan_input(state, "funding_source")
    lines = []
    if total_budget:
        lines.append("Total budget: " + total_budget + ".")
    if budget_breakdown:
        lines.append("Budget breakdown: " + budget_breakdown + ".")
    if funding_source:
        lines.append("Funding source: " + funding_source + ".")
    if lines:
        sections.append(paper.section("Budget Details", paper.H2, [paper.paragraph(lines)]))

    # -- monitoring and evaluation
    indicators = _plan_input(state, "indicators")
    baseline = _plan_input(state, "baseline")
    targets = _plan_input(state, "targets")
    lines = []
    if indicators:
        lines.append("Indicators: " + indicators + ".")
    if baseline:
        lines.append("Baseline: " + baseline + ".")
    if targets:
        lines.append("Targets: " + targets + ".")
    sections.append(paper.section("Monitoring and Evaluation", paper.H1, [paper.paragraph(lines or ["Not supplied."])]))

    # -- risk
    risks = _plan_input(state, "risks")
    if risks:
        sections.append(paper.section("Risk Analysis", paper.H1, [paper.paragraph([risks])]))

    # -- conclusion
    sections.append(paper.section("Conclusion", paper.H1, ["The project proposal above is based on the declared inputs and computations."]))

    # -- references
    sections.append(_plan_reference_section(state, evidence, style))

    return _store_plan_draft(state, sections, style, accepted,
                             "Project proposal: " + (title or _clean(plan.get("decision"), 180)),
                             PROFILE_PROJECT_PROPOSAL)



def _claim_scan(sections):
    """The paper's own sentences that claim more than any frozen method licenses.

    Source sentences (they carry an in-text citation) and the contract's own
    limitation wording are attributed, not asserted by the paper, so they are not
    scanned; the limitations section exists to name limits.
    """
    claims, seen = [], set()
    for item in sections:
        if str(item.get("heading") or "").strip().lower() in ("limitations", "references"):
            continue
        for line in item.get("lines") or []:
            if verify.CITATION.search(str(line or "")):
                continue
            for problem in verify.overclaims(line):
                key = (problem["sentence"], problem["claim"])
                if key in seen:
                    continue
                seen.add(key)
                claims.append(item.get("heading", "the paper") + ": the word \""
                              + problem["claim"] + "\" claims more than any method licenses: "
                              + problem["sentence"])
    return claims


#: What each dimension is about, for the fuller reading a full report carries.
_FULL_READING = {
    "political": "the political conditions around trade, sanctions and entry",
    "economic": "the economic conditions that shape trade and demand",
    "social": "the population and social conditions the offer would meet",
    "technological": "the technology environment the firm would operate in",
    "environmental": "the environmental conditions that affect cost and production",
    "legal": "the legal framework the decision would be judged under",
    "opportunities": "the opportunities the external evidence supports",
    "threats": "the threats the external evidence supports",
    "rivalry": "the intensity of competition among existing firms",
    "entrants": "the height of the barriers a new entrant faces",
    "substitutes": "the pressure from substitute offers",
    "buyers": "the bargaining position of buyers",
    "suppliers": "the bargaining position of suppliers",
    "inbound": "the supply and inbound-logistics conditions",
    "operations": "the production and operations conditions",
    "outbound": "the distribution and fulfilment conditions",
    "marketing": "the marketing and sales conditions",
    "service": "the service and after-sales conditions",
    "procurement": "the procurement and sourcing conditions",
    "technology": "the technology-development conditions",
    "human": "the labour and skills conditions",
    "infrastructure": "the management, finance and governance conditions",
    "penetration": "the case for selling more to existing customers",
    "development": "the case for taking the offer to a new market",
    "product": "the case for a new product in the existing market",
    "diversification": "the case for a new offer in a new market",
}


#: What would change the reading of a dimension, in its own terms.
_FULL_READING_CHANGE = {
    "political": "a settlement that lifts the sanctions, which no source here anticipates",
    "economic": "a household-income or retail-spending series for the city, which the sources do not report",
    "social": "an adoption or willingness-to-pay study for this offer, which the sources do not contain",
    "technological": "a ruling or licence that changes what the store's channels may do",
    "environmental": "a utility or water tariff for the location, which the case would have to declare",
    "legal": "a change in the sanctions instrument that alters what entry requires",
    "rivalry": "a price or capacity announcement from an existing rival",
    "entrants": "a licensing change or a new entrant's announcement",
    "substitutes": "a substitute offer priced below the declared price",
    "buyers": "a buyer contract that fixes volume or price",
    "suppliers": "a supplier quote for the inputs the store would buy",
}

#: What going wrong in each dimension would mean for the decision, in its terms.
_FULL_READING_RISK = {
    "political": "the political conditions tighten before the store opens, raising the cost of entry",
    "economic": "demand is weaker than the economic evidence implies, so fewer units are sold",
    "social": "the customers the sources describe do not adopt this offer at this price",
    "technological": "the controls described extend to the store's channels, raising distribution cost",
    "environmental": "water or energy constraints raise the store's operating cost",
    "legal": "the legal basis changes, and with it the permissions and payment channels entry needs",
    "opportunities": "the opportunity the evidence supports is smaller than the evidence implies",
    "threats": "the threat materialises before entry, and the industry becomes less attractive",
    "rivalry": "rivalry holds prices down while the cost structure stays as declared",
    "entrants": "entry barriers fall and new capacity arrives after the store opens",
    "substitutes": "a substitute takes the demand the store's volume depends on",
    "buyers": "buyers concentrate and press the declared price down",
    "suppliers": "suppliers raise input costs above the declared variable cost",
}


def _reading_line(dimension, evidence, target, by_id=None):
    """One honest paragraph of reading per dimension, for a full report only.

    It states what the paper does with the dimension (a condition of entry), what
    going wrong there would mean for the decision and what would change the
    reading.  It adds no fact and no figure.
    """
    if target not in (0, None) and target < SHORT_WORDS:
        return ""
    items = [item for item in evidence if item["dimension"] == dimension[0]]
    if not items:
        return ""
    clause = _FULL_READING.get(dimension[0]) or "the conditions this dimension describes"
    risk = _FULL_READING_RISK.get(dimension[0]) or ("the condition it describes does not hold when the decision "
                                                    "is taken")
    change = _FULL_READING_CHANGE.get(dimension[0]) or ("a study of this firm in this market would replace the "
                                                        "market-level sources with a direct measurement")
    venues, seen = [], set()
    years, databases = [], []
    for item in items:
        source = (by_id or {}).get(item.get("source_id")) or {}
        year = str(source.get("year") or "").strip()
        name = str(source.get("venue") or source.get("publisher") or source.get("database") or "").strip()
        if name:
            label = name + (" (" + year + ")" if year else "")
            if label not in seen:
                seen.add(label)
                venues.append(label)
        years.extend(int(found) for found in re.findall(r"\d{4}", year))
        database = str(source.get("database") or "").strip()
        if database and database not in databases:
            databases.append(database)
    from_text = (" The sources are " + "; ".join(venues) + ".") if venues else ""
    state_text = ""
    if years:
        span = str(min(years)) if min(years) == max(years) else str(min(years)) + " to " + str(max(years))
        state_text = (" The material was published " + span
                      + ((" and is indexed in " + ", ".join(databases)) if databases else "") + ".")
    return ("Read as a whole, this dimension sets " + clause + "." + from_text + state_text
            + " For the decision, the risk is that " + risk + ". What would change this reading is " + change + ".")


def _source_mix(sources):
    """How the accepted sources divide by database, and their year span."""
    counts = {}
    years = []
    for source in sources:
        name = str(source.get("database") or source.get("item_type") or "other").strip() or "other"
        counts[name] = counts.get(name, 0) + 1
        year = str(source.get("year") or "")
        digits = re.findall(r"\d{4}", year)
        if digits:
            years.append(int(digits[0]))
    parts = [name + " " + str(count) for name, count in sorted(counts.items())]
    return parts, (min(years) if years else None), (max(years) if years else None)


def _scope_section(state, evidence, target, style):
    """The question, the plan, the checks and the length: a method section."""
    answers = state.get("answers") or {}
    plan = state.get("plan") or {}
    decision = _clean(answers.get("decision") or state.get("brief"), 500).rstrip(" .?!")
    geography = answers.get("geography") or "Global"
    period = answers.get("period") or "10"
    period_text = ("the last " + period + " years") if period not in ("0", "") else "all available years"
    label = FRAMEWORKS.get(state.get("framework") or "none", {}).get("label", "the framework")
    why = str(plan.get("why") or "").strip()
    geo_text = "the " + geography if geography not in ("Global", "") else "the global market"
    decision_line = _clean(answers.get("decision") or state.get("brief"), 500).rstrip()
    if not decision_line.endswith(("?", "!", ".")):
        decision_line += "."
    paragraphs = [
        "This report addresses the decision: " + decision_line + " The analysis uses " + label + "."
        + ((" " + why) if why else ""),
        str(len(evidence)) + " accepted evidence item" + ("" if len(evidence) == 1 else "s")
        + " support the dimensions below, drawn from " + geo_text + " over " + period_text
        + ". A source was used when it addressed the decision in that market and was published within the "
        "period; anything else was not used, and a dimension left without a source is reported as a gap rather "
        "than filled.",
    ]
    selected = (state.get("selection") or {}).get("selected") or []
    if selected:
        labels = ", ".join(row["label"].lower() for row in selected)
        paragraphs.append(
            "The report carries the " + labels + " computation. Each computation is run once by the frozen method from the "
            "inputs shown with it, and the recorded figure is reproduced from those inputs before the paper is "
            "drafted; a figure that does not reproduce is not reported.")
    else:
        paragraphs.append("No computation is carried: the question is answered from the framework and the "
                          "evidence, and no financial figure is reported.")
    framework = state.get("framework") or "none"
    others = [name for name in ("SWOT", "Five Forces", "Value Chain", "VRIO", "Ansoff") if name != label]
    if others:
        paragraphs.append(
            "The question is about the conditions the decision faces rather than about the firm's own resources "
            "or the structure of one industry, so " + label + " answers it more directly than "
            + ", ".join(others[:-1]) + " or " + others[-1] + " would.")
    paragraphs.append("All figures are in the case's own currency; the report applies no conversion.")
    paragraphs.append(
        "The analysis reads each dimension against the decision rather than summarising it, and every citation "
        "supports the sentence it is attached to. Each dimension is treated as a condition of entry, not as a "
        "cost the firm has measured; the financial test uses only the figures the case declares.")
    paragraphs.append(
        "The report was planned at " + str(target) + " words. Sections are included only where the record "
        "supports them; where it does not, the gap is named instead of filled.")
    return paper.section("Scope and Method", paper.H1, [paper.paragraph(paragraphs)])


def _evidence_base_section(state, evidence, target):
    """The evidence base: composition, coverage, and how a quotation is used."""
    sources = [source for source in state.get("sources") or []
               if source["id"] in {item["source_id"] for item in evidence}]
    parts, first, last = _source_mix(sources)
    span = ((" The publication years run from " + str(first) + " to " + str(last) + ".")
            if first is not None and last is not None and first != last
            else ((" The sources were published in " + str(first) + ".") if first is not None else ""))
    paragraphs = [
        "The analysis rests on " + str(len(sources)) + " cited source" + ("" if len(sources) == 1 else "s")
        + (" (" + ", ".join(parts) + ")." if parts else ".") + span,
    ]
    coverage = []
    for dimension in state.get("plan", {}).get("dimensions") or []:
        count = len([item for item in evidence if item["dimension"] == dimension["key"]])
        coverage.append(dimension["label"] + " " + str(count))
    if coverage:
        paragraphs.append("Items per dimension: " + "; ".join(coverage) + ".")
        paragraphs.append("A source that informs more than one dimension is counted in each; the quotations above "
                          "show which sentence supports which.")
        paragraphs.append("The newest source sets the currency of the evidence; anything published after it is not "
                          "covered here.")
    # Which source informs which dimension, in short form: the full record is the
    # reference list, and repeating it here would only pad the report.
    rows = []
    for source in sources:
        labels = []
        for dimension in state.get("plan", {}).get("dimensions") or []:
            if any(item["source_id"] == source["id"] and item["dimension"] == dimension["key"]
                   for item in evidence):
                labels.append(dimension["label"])
        venue = _clean(source.get("venue") or source.get("publisher") or source.get("database"), 90)
        cited = _in_text(source, "apa").strip("()")
        rows.append(cited + (", " + venue if venue else "") + " - " + (", ".join(labels) or "no dimension") + ".")
    if rows:
        paragraphs.append("Sources and the dimensions they inform (full records in the reference list): "
                          + " ".join(rows))
    paragraphs.append(
        "Every quotation in the analysis above is a sentence from the source it cites. The source's own claim "
        "is not independently verified here, and a source that speaks about a market does not by itself measure "
        "the firm's costs or demand.")
    return paper.section("Evidence Base", paper.H1, [paper.paragraph(paragraphs)])


def _discussion_full_section(state, evidence, target):
    """What the dimensions show together, and what the computation adds."""
    if target < MID_FLOOR:
        return None
    plan = state.get("plan") or {}
    dimensions = plan.get("dimensions") or []
    counts = []
    for dimension in dimensions:
        count = len([item for item in evidence if item["dimension"] == dimension["key"]])
        counts.append((dimension["key"], dimension["label"], count))
    covered = [label for _key, label, count in counts if count]
    thin = [label for _key, label, count in counts if count == 1]
    empty = [label for _key, label, count in counts if not count]
    by_key = {key: count for key, _label, count in counts}
    paragraphs = []
    if covered:
        paragraphs.append(
            "The dimensions are not independent: the political and legal evidence sets what entry is permitted, "
            "the economic and social evidence sets who could buy, and the technological and environmental "
            "evidence sets how the offer would have to operate. Read together, they describe the conditions the "
            "decision faces before any figure is computed.")
        for name, keys, bearing in (
                ("Permission and cost", ("political", "legal"),
                 "act on the cost of entry before any unit is sold"),
                ("Demand", ("economic", "social"),
                 "act on the volume the case can expect"),
                ("Operations", ("technological", "environmental"),
                 "act on the operating cost the store would carry")):
            if any(by_key.get(key) for key in keys):
                paragraphs.append("Under " + name.lower() + ", the sources " + bearing + ".")
    paragraphs.append("Those links are the reading the report draws between the evidence and the financial "
                      "test: they are not figures the sources report, and the case has to supply the figures.")
    paragraphs.append("The decision is taken before those conditions can be measured again, so the report "
                      "treats them as the conditions of entry rather than as inputs to a forecast.")
    if thin:
        paragraphs.append("The evidence is thinnest in " + ", ".join(thin)
                          + ": one source per dimension, so the position there rests on a single record.")
    paragraphs.append("That is also the main weakness of the evidence base: it describes the market in general, "
                      "not this store's own costs, so the report cannot say how the firm's figures compare with "
                      "the declared ones.")
    paragraphs.append("The report therefore treats the decision as conditional on the declared figures and on the "
                      "conditions the sources describe, and it does not extend the position beyond them.")
    paragraphs.append("It does not rank the dimensions, because the sources do not measure their relative weight "
                      "for this decision.")
    if empty:
        paragraphs.append("No accepted source covers " + ", ".join(empty)
                          + ", so the report treats those dimensions as open rather than settled.")
    selected = (state.get("selection") or {}).get("selected") or []
    recorded = state.get("computations") or {}
    for row in selected:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            paragraphs.append("The " + row["label"].lower() + " has no recorded result, so the financial side "
                              "of the discussion is a named gap.")
            continue
        inputs = data.get("inputs") or {}
        paragraphs.append(
            "The " + row["label"].lower() + " adds a figure the evidence cannot supply: it is computed from the "
            "declared figures (" + ", ".join(name.replace("_", " ") for name in inputs)
            + "). The two readings have to be "
            "held together, because a favourable market does not by itself cover a cost structure that needs "
            "more volume than the case expects.")
    if not paragraphs:
        return None
    return paper.section("What the Evidence Shows Together", paper.H2, [paper.paragraph(paragraphs)])


def _computation_reading(state, target):
    """A short reading of each recorded computation, for a full report."""
    if target < LONG_FLOOR:
        return None
    recorded = state.get("computations") or {}
    paragraphs = []
    for row in (state.get("selection") or {}).get("selected") or []:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            continue
        result = data.get("result") or {}
        pairs = []
        for name, value in list(result.items())[:6]:
            if name in (data.get("inputs") or {}):
                continue
            label = name.replace("_", " ").replace("breakeven", "break-even")
            if name.endswith("ratio") or name.endswith("rate"):
                shown = "{:,.1f}%".format(Decimal(str(value)) * 100)
            else:
                shown = _fmt_number(value)
            pairs.append(label + " " + shown)
        if not pairs:
            continue
        paragraphs.append(
            "The " + row["label"].lower() + " reports " + "; ".join(pairs) + ". These figures follow from the "
            "declared inputs and nothing else; the method does not forecast demand, price or cost, so the "
            "reading is a test of the declared case rather than a prediction of the outcome. Figures are shown to "
            "two decimal places, and the declared inputs are shown as they were declared.")
    if not paragraphs:
        return None
    return paper.section("Reading the Result", paper.H2, [paper.paragraph(paragraphs)])


def _assumptions_section(state, target):
    """The method's own assumptions, limits and claim ceiling, quoted not invented."""
    if target < LONG_FLOOR or METHOD_DESCRIBE is None:
        return None
    paragraphs = []
    for row in (state.get("selection") or {}).get("selected") or []:
        if not (state.get("computations") or {}).get(row["key"], {}).get("ok"):
            continue
        try:
            info = METHOD_DESCRIBE(row["method"]) or {}
        except Exception:
            info = {}
        assumptions = [str(item).rstrip(".").replace("_", " ").replace("breakeven", "break-even")
                       for item in info.get("assumptions") or [] if str(item).strip()]
        limitations = [str(item).rstrip(".").replace("_", " ").replace("breakeven", "break-even")
                       for item in info.get("limitations") or [] if str(item).strip()]
        ceiling = str(info.get("claim_ceiling") or "").strip()
        if not (assumptions or limitations):
            continue
        sentence = row["label"] + " assumes "
        sentence += "; ".join(item[0].lower() + item[1:] for item in assumptions) if assumptions else "the inputs as declared"
        if limitations:
            sentence += ". Its stated limits are " + "; ".join(item[0].lower() + item[1:] for item in limitations)
        if ceiling:
            sentence += ". It supports " + ceiling + " claims and no stronger ones"
        paragraphs.append(sentence + ".")
    if not paragraphs:
        return None
    return paper.section("What the Figures Assume", paper.H2, [paper.paragraph(paragraphs)])


def _lower_first(text):
    """Lower a sentence-opening capital unless the word is a name or acronym."""
    value = str(text or "").strip()
    if len(value) > 1 and value[0].isupper() and value[1].islower():
        return value[0].lower() + value[1:]
    return value


def _recommendation_section(state, position, target):
    """The position the record supports, and the condition it rests on."""
    if target < LONG_FLOOR or not str(position or "").strip():
        return None
    paragraphs = ["On the record above, the position this report supports is that "
                  + _lower_first(str(position).strip().rstrip(".")) + "."]
    recorded = state.get("computations") or {}
    for row in (state.get("selection") or {}).get("selected") or []:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            continue
        paragraphs.append(
            "That position is conditional on the declared figures in the " + row["label"].lower()
            + ". If any of them changes, the method has to be run again on the new figures; the position here "
            "does not carry over to a case those figures do not describe.")
    paragraphs.append(
        "If the fixed cost is committed before the price is tested in the market the sources describe, the case "
        "carries the risk they describe without the demand the model assumes.")
    paragraphs.append(
        "The alternative is to hold the decision until the named gaps in the evidence are covered, because the "
        "sources describe conditions rather than this firm's costs and demand. Either way, the figures in the "
        "report are the ones a reviewer can re-run.")
    return paper.section("Recommendation", paper.H1, [paper.paragraph(paragraphs)])


def _method_appendix(state, target):
    """How each computation was checked: method, inputs, result, reproduction."""
    if target < LONG_FLOOR:
        return None
    recorded = state.get("computations") or {}
    selected = (state.get("selection") or {}).get("selected") or []
    if not selected:
        return None
    paragraphs = [
        "Each computation in this report is a frozen method run once from the inputs the case declares. The "
        "method is named with its result, the declared inputs are listed with it, and the figure is reproduced "
        "from those inputs before the paper is drafted; a figure that does not reproduce is not reported.",
        "The declared figures were read in the method's units, and the method's own refusal would have stopped "
        "the computation before a result was stored. The report's sentences were checked against the claims the "
        "methods license: a sentence claiming proof or certainty, or a forecast, would have blocked the export.",
    ]
    for row in selected:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            paragraphs.append(row["label"] + ": no recorded result, so there is nothing to reproduce.")
            continue
        inputs = data.get("inputs") or {}
        declar = "; ".join(name.replace("_", " ") + " " + _fmt_exact(value)
                           for name, value in inputs.items())
        paragraphs.append("The " + row["label"].lower() + " computation runs the "
                          + str(row.get("method") or row["key"]).replace("_", " ")
                          + " method with the declared figures (" + declar
                          + "). Re-running the method with those inputs returns the recorded figures above.")
    return paper.section("Appendix: How the Computations Were Checked", paper.H1,
                         [paper.paragraph(paragraphs)])


def _change_section(state, by_id, target):
    """What would move the answer, named from the recorded inputs and gaps."""
    selected = (state.get("selection") or {}).get("selected") or []
    recorded = state.get("computations") or {}
    paragraphs = []
    for row in selected:
        data = recorded.get(row["key"]) or {}
        if not data.get("ok"):
            paragraphs.append("The " + row["label"].lower() + " computation has not been recorded, so no figure "
                              "from it can be revisited yet.")
            continue
        inputs = data.get("inputs") or {}
        names = ", ".join(name.replace("_", " ") for name in inputs)
        paragraphs.append(
            "The " + row["label"].lower() + " result follows from the declared figures (" + names
            + "). Changing any one of them changes the result, and a different set would have to be declared and "
            "run again rather than inferred from this one.")
    gaps = [gap.get("label") for gap in state.get("gaps") or [] if gap.get("label")]
    if gaps:
        paragraphs.append("A source that covers " + ", ".join(gaps) + " would test the position where the "
                          "retrieved evidence was thin.")
    else:
        paragraphs.append("A firm-level cost or demand study would test the position more directly than the "
                          "market-level sources above, which describe conditions rather than the firm's own figures.")
    if not paragraphs:
        return None
    return paper.section("What Would Change the Answer", paper.H1, [paper.paragraph(paragraphs)])


def declare_sources(state, citations):
    """Record the student's own citations for the paper (B-182: cited, never evidence).

    They are kept apart from the retrieved `sources` list on purpose: a declared citation can
    never satisfy an evidence gate, and the paper shows it in its own section.
    """
    state["declared_sources"] = [str(line).strip() for line in (citations or []) if str(line).strip()]
    state["updated_at"] = _now()
    return state


def _append_declared_sources(state):
    """Add the student's own citations as their own section, headed *not evidence*."""
    declared = [str(line).strip() for line in (state.get("declared_sources") or []) if str(line).strip()]
    if not declared:
        return state
    draft = state.get("draft") or {}
    heading = "Sources you declared (not evidence)"
    lead = ("These are the sources you declared. They are your citations, this system has not "
            "verified them, and they are not evidence: a part of the paper with no retrieved "
            "evidence still names that gap.")
    sections = draft.get("sections") or []
    if any(isinstance(item, (list, tuple)) and item and item[0] == heading for item in sections):
        return state
    sections.append([heading, [lead] + declared])
    draft["sections"] = sections
    outline = draft.get("outline")
    if isinstance(outline, list) and all(isinstance(item, dict) for item in outline):
        outline.append(paper.section(heading, paper.H1, [lead] + declared))
    state["draft"] = draft
    return state


def draft(state, accepted_ids=None, implications="", style=None):
    """Compose the paper, then attach the student's own citations (B-182) and the rubric audit."""
    state = _append_declared_sources(_draft_dispatch(state, accepted_ids, implications, style))
    state = _apply_rubric(state)
    try:
        claims = []
        for item in (state.get("evidence") or []):
            if isinstance(item, dict):
                claims.append({"id": item.get("id"), "type": "external",
                               "source_ids": [item.get("source_id")] if item.get("source_id") else [],
                               "text": item.get("claim")})
        state["chart_specs"] = _chart_specs_for(state)
        state["blocks"] = state.get("blocks") or _plan_blocks(state)
        ledger = _evidence_ledger_for(state)
        state["evidence_ledger"] = ledger
        state["audit"] = audit_mod.audit(
            state.get("paper_contract"), {"blocks": state["blocks"]},
            ledger, state.get("computations"), state.get("draft"),
            rubric_coverage=(state.get("rubric") or {}).get("coverage") if isinstance(state.get("rubric"), dict) else None,
            forbidden_terms=["PSE", "PSEi"])
        state["audit_error"] = None
    except Exception as error:
        state["evidence_ledger"] = None
        state["audit"] = None
        state["audit_error"] = str(error)
    global _CITATION_NUMBERS
    _CITATION_NUMBERS = None
    return state


#: The heading the coverage table carries, in both paper paths.
RUBRIC_HEADING = "Rubric coverage"


def _apply_rubric(state):
    """Measure the finished paper against the marking guide the student attached.

    The coverage is measured on the paper **before** the table exists, so the table can
    never satisfy the criterion it reports on — the same rule the completed worksheet
    follows.  `state["rubric"]` is the key `paper.missing` reads, so a criterion the
    guide weights and the paper does not address blocks the download and is named there;
    nothing here writes the missing section.  A paper with no attached guide is returned
    unchanged.
    """
    attached = state.get("rubric_record")
    draft = state.get("draft") or {}
    outline = draft.get("outline")
    if not attached or not isinstance(outline, list) or not outline:
        return state
    if not all(isinstance(item, dict) for item in outline):
        return state
    if any(str(item.get("heading") or "") == RUBRIC_HEADING for item in outline):
        return state
    coverage = rubric_reader.coverage(attached, outline)
    insert_at = len(outline)
    for position, item in enumerate(outline):
        if str(item.get("heading") or "") in ("References", "Bibliography"):
            insert_at = position
            break
    outline = outline[:insert_at] + [paper.rubric_section(coverage)] + outline[insert_at:]
    draft["outline"] = outline
    draft["sections"] = paper.flatten(outline)
    draft["rubric"] = coverage
    state["draft"] = draft
    state["rubric"] = coverage
    # The table is the paper's own sentence now, so the claim guard reads it too.
    state["claim_problems"] = _claim_scan(outline)
    draft["missing"] = paper.missing(state, draft.get("implications", ""))
    try:
        claims = []
        for item in (state.get("evidence") or []):
            if isinstance(item, dict):
                claims.append({"id": item.get("id"), "type": "external",
                               "source_ids": [item.get("source_id")] if item.get("source_id") else [],
                               "text": item.get("claim")})
        state["chart_specs"] = _chart_specs_for(state)
        state["blocks"] = state.get("blocks") or _plan_blocks(state)
        ledger = _evidence_ledger_for(state)
        state["evidence_ledger"] = ledger
        state["audit"] = audit_mod.audit(
            state.get("paper_contract"), {"blocks": state["blocks"]},
            ledger, state.get("computations"), state.get("draft"),
            rubric_coverage=(state.get("rubric") or {}).get("coverage") if isinstance(state.get("rubric"), dict) else None,
            forbidden_terms=["PSE", "PSEi"])
    except Exception as error:
        state["evidence_ledger"] = None
        state["audit"] = None
        state["audit_error"] = str(error)
    state["stage"] = "draft"
    state["updated_at"] = _now()
    return state


def _draft_dispatch(state, accepted_ids=None, implications="", style=None):
    """Compose the paper from accepted evidence.  It invents nothing."""
    if (state.get("profile") or "") == PROFILE_BUSINESS_PLAN:
        return _draft_plan(state, accepted_ids, style)
    if (state.get("profile") or "") == PROFILE_FEASIBILITY_STUDY:
        return _draft_feasibility_study(state, accepted_ids, style)
    if (state.get("profile") or "") == PROFILE_MARKETING_PLAN:
        return _draft_marketing_plan(state, accepted_ids, style)
    if (state.get("profile") or "") == PROFILE_PROJECT_PROPOSAL:
        return _draft_project_proposal(state, accepted_ids, style)
    if state.get("stage") not in ("evidence", "evidence_reviewed", "draft"):
        raise ChatError("Retrieve the evidence before drafting.")
    accepted = set(accepted_ids) if accepted_ids is not None else {item["id"] for item in state["evidence"]}
    evidence = [item for item in state["evidence"] if item["id"] in accepted]
    by_id = {source["id"]: source for source in state["sources"]}
    style = style or state["answers"].get("style") or "apa"
    from . import citation_styles
    global _CITATION_NUMBERS
    _CITATION_NUMBERS = None
    numbers = None
    if citation_styles.is_numbered(style):
        numbers = {}
        counter = 1
        accepted_sources = {item.get("source_id") for item in evidence if item.get("source_id")}
        for item in evidence:
            source = by_id.get(item.get("source_id"), {})
            key = source.get("id") or source.get("doi") or source.get("title")
            if key and key not in numbers:
                numbers[key] = counter
                counter += 1
        # any accepted source not reached by an evidence item still gets a number
        for source in state.get("sources") or []:
            if source.get("id") in accepted_sources or not accepted_sources:
                key = source.get("id") or source.get("doi") or source.get("title")
                if key and key not in numbers:
                    numbers[key] = counter
                    counter += 1
        _CITATION_NUMBERS = numbers
    answers = state["answers"]
    framework = state.get("framework") or "none"
    label = FRAMEWORKS[framework]["label"]
    decision = answers.get("decision") or state["brief"]
    geography = answers.get("geography") or "Global"
    period = answers.get("period") or "10"
    period_text = "the last " + period + " years" if period not in ("0", "") else "all available years"
    position = _clean(implications, 1200)
    target = target_words(state)
    decision_text = _clean(decision, 500).rstrip(" .?!")
    if framework in ("breakeven", "vrio"):
        intro = ("The decision under analysis is: " + decision_text + ". The paper uses " + label
                 + " and the inputs you supplied; no external evidence is retrieved for this framework.")
    else:
        geo_text = geography if geography in ("Global", "") else "the " + geography
        intro = ("The decision under analysis is: " + decision_text + ". The paper examines " + geo_text
                 + " over " + period_text + " and uses " + label + " to organise the evidence and the firm's position.")
    if position:
        intro += " The paper argues that " + position.rstrip(".") + "."
    sections = [paper.section("Introduction", paper.H1, [intro])]
    if target >= MID_FLOOR:
        sections.append(_scope_section(state, evidence, target, style))
    frameworks = state.get("frameworks") or [framework]
    for framework in frameworks:
        figure_cells = _figure_cells(answers, evidence, by_id, style, framework)
        if framework in ("pestel", "pestel_swot"):
            sections.append(paper.section("PESTEL", paper.H1))
            for dimension in DIMENSIONS:
                lines = _dimension_lines(dimension, evidence, by_id, style, target)
                sections.append(paper.section(dimension[1], paper.H2, [paper.paragraph(lines)]))
        if framework in ("swot", "pestel_swot"):
            sections.append(paper.section("SWOT", paper.H1,
                                          figure=matrix.build("template_swot", figure_cells,
                                                              caption="SWOT matrix")))
            sections.append(paper.section("Strengths", paper.H2,
                                          [paper.paragraph(_internal_lines(answers, "strengths", "Strengths"))]))
            sections.append(paper.section("Weaknesses", paper.H2,
                                          [paper.paragraph(_internal_lines(answers, "weaknesses", "Weaknesses"))]))
        unclassified = 0
        buckets = {"opportunities": [], "threats": []}
        if framework == "swot":
            for dimension in SWOT_DIMENSIONS:
                lines = _dimension_lines(dimension, evidence, by_id, style, target)
                sections.append(paper.section(dimension[1], paper.H2, [paper.paragraph(lines)]))
        elif framework == "pestel_swot":
            buckets, unclassified = _classify_external(evidence)
            sections.append(paper.section("Opportunities", paper.H2,
                                          [paper.paragraph(_mapped_lines(buckets["opportunities"], by_id, style, "Opportunities"))]))
            sections.append(paper.section("Threats", paper.H2,
                                          [paper.paragraph(_mapped_lines(buckets["threats"], by_id, style, "Threats"))]))
        if framework in ("five_forces", "five_forces_breakeven"):
            sections.append(paper.section("Five Forces", paper.H1))
            for dimension in FIVE_DIMENSIONS:
                lines = _dimension_lines(dimension, evidence, by_id, style, target)
                sections.append(paper.section(dimension[1], paper.H2, [paper.paragraph(lines)]))
        if framework == "value_chain":
            sections.append(paper.section("Value Chain", paper.H1,
                                          figure=matrix.build("template_value_chain", figure_cells,
                                                              caption="Porter's value chain")))
            for dimension in VALUE_DIMENSIONS:
                lines = _dimension_lines(dimension, evidence, by_id, style, target)
                sections.append(paper.section(dimension[1], paper.H2, [paper.paragraph(lines)]))
        if framework == "ansoff":
            sections.append(paper.section("Ansoff Growth Matrix", paper.H1,
                                          figure=matrix.build("template_ansoff", figure_cells,
                                                              caption="Ansoff growth matrix")))
            for dimension in ANSOFF_DIMENSIONS:
                lines = _dimension_lines(dimension, evidence, by_id, style, target)
                sections.append(paper.section(dimension[1], paper.H2, [paper.paragraph(lines)]))
        if framework == "vrio":
            sections.append(paper.section("VRIO", paper.H1,
                                          figure=matrix.build("template_vrio", figure_cells,
                                                              caption="VRIO analysis")))
            sections.append(paper.section("Resources", paper.H2,
                                          [paper.paragraph(_internal_lines(answers, "resources", "Resources"))]))
            for key, heading, noun in (("valuable", "Valuable", "value judgments"),
                                       ("rare", "Rare", "rarity judgments"),
                                       ("costly", "Costly to imitate", "imitation-cost judgments"),
                                       ("organized", "Organised to capture value", "organisational judgments")):
                sections.append(paper.section(heading, paper.H2,
                                              [paper.paragraph(_internal_lines(answers, key, heading, noun))]))
        if framework == "breakeven":
            sections.append(paper.section("Financial Feasibility", paper.H1))
            sections.append(paper.section("Break-even Analysis", paper.H2, [paper.paragraph(_break_even_lines(answers))]))
        if framework == "five_forces_breakeven":
            sections.append(paper.section("Financial Feasibility", paper.H1))
            sections.append(paper.section("Break-even Analysis", paper.H2, [paper.paragraph(_break_even_lines(answers))]))
    framework = state.get("framework") or "none"
    recorded = state.get("computations") or {}
    selected_caps = (state.get("selection") or {}).get("selected") or []
    rendered_sections = set()
    for row in selected_caps:
        slot = list(row.get("slot") or ["Computation", row.get("label") or row["key"]])[:2]
        while len(slot) < 2:
            slot.append(row.get("label") or row["key"])
        heading, subheading = slot
        if heading not in rendered_sections:
            sections.append(paper.section(heading, paper.H1))
            rendered_sections.add(heading)
        declared = _declared_inputs_line(recorded.get(row["key"]) or {})
        lines = ([paper.paragraph([declared])] if declared else []) + \
                [paper.paragraph(_capability_lines(row, recorded.get(row["key"]) or {}))]
        sections.append(paper.section(subheading, paper.H2, lines))
    reading = _computation_reading(state, target)
    if reading:
        sections.append(reading)
    assumptions = _assumptions_section(state, target)
    if assumptions:
        sections.append(assumptions)
    if target >= MID_FLOOR:
        sections.append(_evidence_base_section(state, evidence, target))
    sections.append(paper.section("Discussion", paper.H1))
    if framework == "pestel_swot":
        integration = ("PESTEL identifies the external conditions that frame the decision, and SWOT places the "
                       "student's internal strengths and weaknesses against the opportunities and threats drawn from "
                       "that evidence. The matrix maps " + str(len(buckets["opportunities"])) + " accepted item(s) to "
                       "opportunities and " + str(len(buckets["threats"])) + " to threats, and each item keeps its "
                       "PESTEL origin. Read together, the two frameworks connect the external environment to the "
                       "firm's position; the implications below state the resulting judgment.")
        sections.append(paper.section("Integration of PESTEL and SWOT", paper.H2, [integration]))
    elif framework == "five_forces_breakeven":
        integration = ("Five Forces assesses whether the industry is attractive enough to enter; the break-even "
                       "calculation tests whether the declared cost structure can support entry at the declared price. "
                       "Read together, the industry pressures qualify the financial result: a break-even volume is only "
                       "useful if the expected volume can be reached under those pressures. The implications below state "
                       "the resulting judgment.")
        sections.append(paper.section("Industry Attractiveness and Financial Feasibility", paper.H2, [integration]))
    elif selected_caps:
        names = ", ".join(row["label"].lower() for row in selected_caps)
        integration = ("The framework above organises the case; the " + names + " analysis tests the declared "
                       "figures through the frozen method. Read together, the analysis qualifies the result: a "
                       "computed figure holds only for the inputs the student declared, and it does not prove "
                       "that the expected volume or price will be reached. The implications below state the "
                       "resulting judgment.")
        heading = selected_caps[0].get("integration") or "Framework and Declared Figures"
        sections.append(paper.section(heading, paper.H2, [integration]))
    together = _discussion_full_section(state, evidence, target)
    if together:
        sections.append(together)
    if position:
        sections.append(paper.section("Implications", paper.H2, [position]))
    gaps = [gap["label"] for gap in state.get("gaps") or []]
    limits = []
    if gaps:
        limits.append("No evidence was retrieved for: " + ", ".join(gaps) + ".")
    if framework in ("swot", "pestel_swot"):
        limits.append("Strengths and weaknesses are the student's input; the system did not verify them.")
    if framework == "vrio":
        limits.append("The resources and the four judgments are the student's input; the system did not verify them "
                      "and measured no imitation cost.")
    if framework == "five_forces_breakeven":
        limits.append("The break-even result depends on the declared fixed cost, price and variable cost; it does not "
                      "forecast demand or prove that the expected volume will be reached.")
    if selected_caps:
        for row in selected_caps:
            # The method's own limitation is quoted; its full stop is not doubled.
            wording = str(row.get("not") or "").strip().rstrip(".")
            if wording:
                limits.append(row["label"] + ": " + wording + ".")
    if framework == "pestel_swot":
        limits.append("Opportunities and threats are mapped from the accepted PESTEL evidence by keyword; the "
                      "mapping is stated in each item.")
        if unclassified:
            limits.append(str(unclassified) + " accepted evidence item(s) could not be mapped to an opportunity or "
                                              "a threat and are not shown in the SWOT block.")
    if target >= MID_FLOOR:
        limits += [
            "The sources are market-level: they describe conditions, not this firm's costs, prices or volumes.",
            "Each source is quoted once; the report does not survey the literature on any dimension.",
            "The reading of a dimension is the author's, and a different reader could weigh the same sources "
            "differently.",
        ]
    limits += ["Placement uses keyword cues; a source can be relevant to more than one dimension.",
               "The paper quotes sources; it does not verify the claims inside them.",
               "No financial figure is computed in this paper."
               if framework not in ("breakeven", "five_forces_breakeven") and not selected_caps
               else "Every financial figure is the frozen method's result from the inputs the student declared."]
    sections.append(paper.section("Limitations", paper.H2, [paper.paragraph(limits)]))
    if position:
        asked = _clean(decision, 500).rstrip()
        if not asked.endswith(("?", "!", ".")):
            asked += "."
        conclusion = ("The paper set out to address: " + asked + " The evidence and the implications "
                      "above support the position that " + _lower_first(position.rstrip(".")) + ".")
    else:
        conclusion = ("The paper assessed " + _clean(decision, 500) + " and set out the evidence above. The "
                      "implications required to state a position have not been supplied.")
    if target >= MID_FLOOR:
        change = _change_section(state, by_id, target)
        if change:
            sections.append(change)
        recommendation = _recommendation_section(state, position, target)
        if recommendation:
            sections.append(recommendation)
    if target >= MID_FLOOR:
        conclusion += (" The position is stated with its condition: it holds for the declared figures and the "
                       "conditions the sources describe, and not beyond them.")
    sections.append(paper.section("Conclusion", paper.H1, [conclusion]))
    appendix = _method_appendix(state, target)
    if appendix:
        sections.append(appendix)
    references, seen = [], set()
    for source in state["sources"]:
        if source["id"] not in {item["source_id"] for item in evidence}:
            continue
        key = source.get("doi") or _clean(source.get("title"), 120).lower()
        if key in seen:
            continue
        seen.add(key)
        references.append(_reference(source, style, numbers))
    from . import citation_styles
    heading = citation_styles.reference_heading(style)
    sections.append(paper.section(heading, paper.H1, references or ["No sources were used."]))
    title_label = label
    if selected_caps:
        title_label = label + " and " + " and ".join(row["label"].lower() for row in selected_caps)
    elif (state.get("computation") or {}).get("key") == "breakeven" \
            and framework != "five_forces_breakeven":
        title_label = label + " and break-even"
    recompute = _recompute_guard(state)
    state["recompute_problems"] = recompute
    # The gate reads the paper's own sentences, not attributed quotations.
    state["claim_problems"] = _claim_scan(sections)
    missing = paper.missing(state, position)
    words = _word_count(sections)
    state["draft"] = {"title": title_label + " analysis: " + _clean(decision, 180),
                      "sections": paper.flatten(sections), "outline": sections,
                      "style": style, "framework": framework,
                      "accepted": sorted(accepted), "implications": position,
                      "words": words, "target_words": target or SHORT_WORDS,
                      "length_band": length_band(target or SHORT_WORDS),
                      "met_target": target == 0 or words >= target,
                      "missing": missing, "created_at": _now()}
    state["stage"] = "draft"
    state["updated_at"] = _now()
    return state


def set_rubric_gate(state, enabled=True):
    """The student's own switch on the marking guide's gate.

    A rubric can name a section this profile does not carry — a marker's "Referencing"
    against the plan's own "References" — and then the gate would honour the document
    against a paper that can never satisfy it.  Turning it off is recorded, the rows stay
    in the coverage table as gaps, and the download is allowed: the student accepts the
    gap rather than the system pretending it is closed.
    """
    if not state.get("rubric") and not state.get("rubric_record"):
        raise ChatError("Attach a marking guide before changing its gate.")
    state["rubric_gate"] = bool(enabled)
    state["rubric_gate_set_at"] = _now()
    draft = state.get("draft")
    if isinstance(draft, dict):
        draft["missing"] = paper.missing(state, draft.get("implications", ""))
    state["updated_at"] = _now()
    return state


def docx_bytes(state, byline=None):
    """The drafted paper as a Word document (APA or Harvard)."""
    draft = state.get("draft")
    if not draft:
        raise ChatError("Draft the paper before exporting it.")
    required = paper.missing(state, draft.get("implications", ""))
    if required:
        raise ExportBlocked(required)
    outline = draft.get("outline") or paper.flatten(draft.get("sections") or [])
    report = paper.check(outline, state.get("framework") or "none",
                         draft.get("implications", ""), state.get("answers") or {}, state=state)
    if not report["pass"]:
        raise ExportBlocked([issue["detail"] for issue in report["issues"] if issue["severity"] == "high"])
    lines = byline if byline is not None else state.get("byline") or ()
    return docx.render_academic(draft["title"], outline, draft.get("style", "apa"), byline=lines)


def polish(state):
    """Ask the model for a prose proposal.  Nothing is applied until confirmed."""
    draft = state.get("draft")
    if not draft:
        raise ChatError("Draft the paper before polishing it.")
    try:
        state["prose_proposal"] = prose.propose(state, draft)
    except prose.ProseError as error:
        raise ChatError(str(error))
    state["updated_at"] = _now()
    return state


def apply_prose(state):
    """Apply the proposed prose after the student accepts it."""
    proposal = state.get("prose_proposal")
    if not proposal:
        raise ChatError("There is no prose proposal waiting for confirmation.")
    state["draft"] = prose.apply(state["draft"], proposal)
    state["prose_proposal"] = None
    state["updated_at"] = _now()
    return state


def discard_prose(state):
    state["prose_proposal"] = None
    state["updated_at"] = _now()
    return state


def summary(state):
    """A compact view for the chat UI; no hidden reasoning, no invented text."""
    question = current_question(state)
    return {"id": state.get("id"), "stage": state.get("stage"), "brief": state.get("brief"),
            "profile": state.get("profile"), "level": state.get("level"), "mode": state.get("mode"),
            "answers": state.get("answers"), "question": question, "plan": state.get("plan"),
            "selection": state.get("selection"),
            "plan_record": state.get("plan_record"),
            "replay": replay_check(state),
            "recompute_problems": state.get("recompute_problems"),
            "computations": state.get("computations"), "missing_inputs": _missing_fields(state)
            if state.get("profile") == PROFILE_BUSINESS_PLAN else [],
            "sources": state.get("sources"), "evidence": state.get("evidence"),
            "gaps": state.get("gaps"), "notes": state.get("notes"), "draft": state.get("draft"),
            "timings": state.get("timings"), "message": state.get("message"),
            "prose_available": prose.available(), "prose_proposal": state.get("prose_proposal")}
