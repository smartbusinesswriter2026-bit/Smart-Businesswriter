"""Paper families and archetypes for the Home chat conductor.

A paper type is not a bespoke pipeline. It is a preset inside a paper family,
and an archetype inside that family. The conductor resolves a brief to an
archetype, validates the archetype's completeness contract, and assembles the
paper from registered blocks.

Rules this module keeps:
- data only: no formula, no number, no I/O, no network, no clock;
- every archetype declares its family, sections, blocks, evidence policy,
  computation policy, chart policy, length bands, citation styles, rubric
  families and completeness contract;
- an unknown archetype is refused with the real options, never substituted;
- adding a paper type means adding data here, not a branch in chat, api or
  the served page.
"""

FORMAT = "bp-paper-families/1"

FAMILIES = {
    "analytical_report": {
        "label": "Analytical report",
        "genre": "analyse a company, industry, market or statement set",
        "evidence_policy": "external_plus_company_data",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["financial statement analysis", "ratio report", "company analysis", "industry analysis", "earnings quality", "ESG analysis"],
    },
    "case_analysis": {
        "label": "Case analysis",
        "genre": "analyse a case and recommend action",
        "evidence_policy": "case_facts_plus_external",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["Harvard case", "failure analysis", "success analysis", "ethics case", "comparative case"],
    },
    "plan_proposal": {
        "label": "Plan or proposal",
        "genre": "plan or propose a business, project or study",
        "evidence_policy": "market_evidence_plus_student_inputs",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["business plan", "marketing plan", "feasibility study", "project proposal", "research proposal"],
    },
    "financial_valuation": {
        "label": "Financial or valuation report",
        "genre": "value or appraise a company or project",
        "evidence_policy": "market_data_plus_company_data",
        "computation_policy": "required",
        "chart_policy": "optional",
        "examples": ["valuation", "equity research", "capital budgeting", "M&A", "LBO", "credit", "portfolio"],
    },
    "literature_synthesis": {
        "label": "Literature synthesis",
        "genre": "synthesise research",
        "evidence_policy": "scholarly_sources",
        "computation_policy": "none",
        "chart_policy": "none",
        "examples": ["literature review", "annotated bibliography", "critical review"],
    },
    "argumentative_essay": {
        "label": "Argumentative essay",
        "genre": "argue a position",
        "evidence_policy": "scholarly_or_practitioner",
        "computation_policy": "optional",
        "chart_policy": "none",
        "examples": ["position paper", "essay", "white paper"],
    },
    "memo_brief": {
        "label": "Memo or brief",
        "genre": "recommend to a stakeholder",
        "evidence_policy": "evidence_plus_stakeholder",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["policy memo", "business memo", "executive summary"],
    },
    "reflective": {
        "label": "Reflective paper",
        "genre": "connect concepts to experience",
        "evidence_policy": "student_experience",
        "computation_policy": "none",
        "chart_policy": "none",
        "examples": ["reflection", "internship report", "simulation reflection"],
    },
    "legal_regulatory": {
        "label": "Legal or regulatory paper",
        "genre": "apply law or standards",
        "evidence_policy": "legal_or_standards_sources",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["case brief", "contract analysis", "compliance", "tax memo"],
    },
    "empirical_research": {
        "label": "Empirical research paper",
        "genre": "test or investigate a question",
        "evidence_policy": "data_plus_literature",
        "computation_policy": "optional",
        "chart_policy": "optional",
        "examples": ["thesis", "research paper", "empirical accounting"],
    },
    "communication": {
        "label": "Business communication",
        "genre": "communicate professionally",
        "evidence_policy": "minimal",
        "computation_policy": "none",
        "chart_policy": "none",
        "examples": ["letter", "email", "press release", "pitch", "resume"],
    },
}

ARCHETYPES = {
    "analytical_report": {
        "family": "analytical_report",
        "label": "Analytical report",
        "purpose": "analyse a company, industry, market or statement set and recommend",
        "required_sections": ["Introduction", "Context", "Analysis", "Synthesis", "Recommendation", "Limitations", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["framework", "evidence"],
        "optional_blocks": ["computation", "chart", "prose"],
        "length_bands": ["short", "mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "evidence_quality", "analysis_quality", "synthesis", "limitations", "format"],
        "completeness": [
            "states the question or decision",
            "names the evidence base",
            "analyses with at least one framework or computation",
            "compares to a benchmark or baseline where applicable",
            "synthesises rather than concatenates",
            "recommends with rationale",
            "names limitations",
            "cites sources",
        ],
        "status": "ready",
    },
    "case_analysis": {
        "family": "case_analysis",
        "label": "Case analysis",
        "purpose": "analyse a case and recommend action",
        "required_sections": ["Case Description", "Problem", "Evidence", "Analysis", "Alternatives", "Recommendation", "Implementation", "Risks", "Limitations", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["case_framing", "framework", "evidence"],
        "optional_blocks": ["computation", "chart", "prose"],
        "length_bands": ["short", "mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "evidence_quality", "analysis_quality", "alternatives", "recommendation", "implementation", "limitations", "format"],
        "completeness": [
            "states the decision or question",
            "describes the case and its constraints",
            "analyses with at least one framework",
            "evaluates alternatives against stated criteria",
            "recommends with rationale",
            "names implementation steps",
            "names risks",
            "names limitations",
        ],
        "status": "ready",
    },
    "plan_proposal": {
        "family": "plan_proposal",
        "label": "Plan or proposal",
        "purpose": "plan or propose a business, project or study",
        "required_sections": ["Executive Summary", "Business Description", "Market Analysis", "Marketing Plan", "Operations Plan", "Management and Organisation", "Financial Plan", "Risk Analysis", "Conclusion", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["profile", "evidence"],
        "optional_blocks": ["computation", "chart", "prose"],
        "length_bands": ["short", "mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "evidence_quality", "market_analysis", "financial_feasibility", "risk", "implementation", "limitations", "format"],
        "completeness": [
            "states the opportunity or problem",
            "analyses the market",
            "states the operating plan",
            "states the financial plan",
            "names risks",
            "names implementation steps",
            "names limitations",
            "cites sources",
        ],
        "status": "ready",
    },
    "financial_valuation": {
        "family": "financial_valuation",
        "label": "Financial or valuation report",
        "purpose": "value or appraise a company or project",
        "required_sections": ["Introduction", "Company and Industry", "Valuation Method", "Assumptions", "Results", "Sensitivity", "Recommendation", "Limitations", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["valuation_method", "computation", "evidence"],
        "optional_blocks": ["chart", "prose"],
        "length_bands": ["mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "evidence_quality", "method", "assumptions", "results", "sensitivity", "recommendation", "limitations", "format"],
        "completeness": [
            "states the valuation question",
            "names the method and its assumptions",
            "records the key inputs",
            "reports the result",
            "reports sensitivity",
            "recommends with rationale",
            "names limitations",
        ],
        "status": "planned",
    },
    "literature_synthesis": {
        "family": "literature_synthesis",
        "label": "Literature synthesis",
        "purpose": "synthesise research on a topic",
        "required_sections": ["Introduction", "Search Method", "Themes", "Gaps", "Debates", "Conclusion", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["search_plan", "source_appraisal", "synthesis"],
        "optional_blocks": ["prose"],
        "length_bands": ["mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "search_method", "source_quality", "synthesis", "gaps", "format"],
        "completeness": [
            "states the review question",
            "states the search method",
            "synthesises themes",
            "names gaps",
            "names debates",
            "concludes",
            "cites sources",
        ],
        "status": "planned",
    },
    "argumentative_essay": {
        "family": "argumentative_essay",
        "label": "Argumentative essay",
        "purpose": "argue a position on a business issue",
        "required_sections": ["Introduction", "Argument", "Counterargument", "Synthesis", "Conclusion", "References"],
        "optional_sections": [],
        "required_blocks": ["thesis", "evidence", "prose"],
        "optional_blocks": ["computation"],
        "length_bands": ["short", "mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "thesis", "evidence", "reasoning", "counterargument", "format"],
        "completeness": [
            "states a thesis",
            "supports it with evidence",
            "addresses a counterargument",
            "synthesises",
            "concludes",
            "cites sources",
        ],
        "status": "planned",
    },
    "memo_brief": {
        "family": "memo_brief",
        "label": "Memo or brief",
        "purpose": "recommend to a stakeholder",
        "required_sections": ["Issue", "Background", "Options", "Criteria", "Recommendation", "Next Steps", "References"],
        "optional_sections": [],
        "required_blocks": ["issue", "evidence", "prose"],
        "optional_blocks": ["computation"],
        "length_bands": ["short", "mid"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "clarity", "evidence", "options", "recommendation", "format"],
        "completeness": [
            "states the issue",
            "states the options",
            "states the criteria",
            "recommends with rationale",
            "names next steps",
        ],
        "status": "planned",
    },
    "reflective": {
        "family": "reflective",
        "label": "Reflective paper",
        "purpose": "connect concepts to experience",
        "required_sections": ["Experience", "Concepts", "Analysis", "Learning", "Conclusion"],
        "optional_sections": [],
        "required_blocks": ["reflection", "prose"],
        "optional_blocks": [],
        "length_bands": ["short", "mid"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "reflection", "concept_application", "learning", "format"],
        "completeness": [
            "describes the experience",
            "names the concepts",
            "analyses the connection",
            "states the learning",
            "concludes",
        ],
        "status": "planned",
    },
    "legal_regulatory": {
        "family": "legal_regulatory",
        "label": "Legal or regulatory paper",
        "purpose": "apply law or standards",
        "required_sections": ["Issue", "Rule", "Application", "Conclusion", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["legal_source", "prose"],
        "optional_blocks": ["computation"],
        "length_bands": ["short", "mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "issue", "rule", "application", "conclusion", "format"],
        "completeness": [
            "states the issue",
            "states the rule",
            "applies the rule",
            "concludes",
            "cites sources",
        ],
        "status": "planned",
    },
    "empirical_research": {
        "family": "empirical_research",
        "label": "Empirical research paper",
        "purpose": "test or investigate a question",
        "required_sections": ["Introduction", "Literature Review", "Method", "Results", "Discussion", "Conclusion", "References"],
        "optional_sections": ["Appendix"],
        "required_blocks": ["research_question", "literature", "method", "results", "discussion"],
        "optional_blocks": ["computation", "chart", "prose"],
        "length_bands": ["mid", "long"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "question", "literature", "method", "results", "discussion", "format"],
        "completeness": [
            "states the research question",
            "reviews the literature",
            "states the method",
            "reports results",
            "discusses findings",
            "concludes",
            "cites sources",
        ],
        "status": "planned",
    },
    "communication": {
        "family": "communication",
        "label": "Business communication",
        "purpose": "communicate professionally",
        "required_sections": ["Message"],
        "optional_sections": [],
        "required_blocks": ["message"],
        "optional_blocks": [],
        "length_bands": ["short"],
        "citation_styles": ["apa", "harvard"],
        "rubric_families": ["task_fidelity", "clarity", "tone", "format"],
        "completeness": [
            "states the message",
            "uses the required format",
        ],
        "status": "separate_lane",
    },
}

LENGTH_BANDS = {
    "short": {"low": 600, "high": 1200},
    "mid": {"low": 1200, "high": 2500},
    "long": {"low": 2500, "high": 5000},
}

from . import citation_styles

CITATION_STYLES = tuple(citation_styles.STYLES)


def families():
    return [dict(value, id=key) for key, value in FAMILIES.items()]


def archetypes():
    return [dict(value, id=key) for key, value in ARCHETYPES.items()]


def family(key):
    return FAMILIES.get(str(key or "").strip().lower())


def archetype(key):
    return ARCHETYPES.get(str(key or "").strip().lower())


def is_family(key):
    return str(key or "").strip().lower() in FAMILIES


def is_archetype(key):
    return str(key or "").strip().lower() in ARCHETYPES


def archetypes_for_family(family_key):
    family_key = str(family_key or "").strip().lower()
    return [dict(value, id=key) for key, value in ARCHETYPES.items() if value.get("family") == family_key]


def ready_archetypes():
    return [dict(value, id=key) for key, value in ARCHETYPES.items() if value.get("status") == "ready"]


def validate_archetype(key):
    key = str(key or "").strip().lower()
    if key not in ARCHETYPES:
        return ["unknown archetype " + str(key) + "; choose one of: " + ", ".join(sorted(ARCHETYPES))]
    return []


def validate_family(key):
    key = str(key or "").strip().lower()
    if key not in FAMILIES:
        return ["unknown family " + str(key) + "; choose one of: " + ", ".join(sorted(FAMILIES))]
    return []


def validate_length_band(key):
    key = str(key or "").strip().lower()
    if key not in LENGTH_BANDS:
        return ["unknown length band " + str(key) + "; choose one of: " + ", ".join(sorted(LENGTH_BANDS))]
    return []


def validate_citation_style(key):
    key = str(key or "").strip().lower()
    if key not in CITATION_STYLES:
        return ["unknown citation style " + str(key) + "; choose one of: " + ", ".join(CITATION_STYLES)]
    return []


def completeness_for(archetype_key):
    row = archetype(archetype_key)
    if not row:
        return []
    return list(row.get("completeness") or [])


def required_sections_for(archetype_key):
    row = archetype(archetype_key)
    if not row:
        return []
    return list(row.get("required_sections") or [])


def required_blocks_for(archetype_key):
    row = archetype(archetype_key)
    if not row:
        return []
    return list(row.get("required_blocks") or [])


def optional_blocks_for(archetype_key):
    row = archetype(archetype_key)
    if not row:
        return []
    return list(row.get("optional_blocks") or [])
