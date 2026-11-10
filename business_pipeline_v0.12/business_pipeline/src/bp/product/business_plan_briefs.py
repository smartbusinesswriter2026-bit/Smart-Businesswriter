"""The uploaded guide's Part 6 extracted as data: what each section must contain.

These are the template's instructions, kept as a contract for the writer and the
checker.  They are never printed into a paper.  The headings match the paper's
narrative sections exactly, so a written section can replace one deterministic
section and nothing else.
"""

#: heading -> the brief the model is given and the checker enforces.
BRIEFS = {
    "Executive Summary": {
        "purpose": "Let a busy reader understand the whole business and decide whether to read on.",
        "pull": ["every other section", "the financial model"],
        "must_include": [
            "the business in one or two sentences: name, what it sells, where, legal form, stage",
            "the problem and the solution",
            "the target market and its size, with the obtainable figure",
            "the competitive advantage",
            "the business model: price, volume and margin",
            "one sentence on management's relevant strengths",
            "financial highlights: Year 1-3 revenue, net income, gross margin, break-even, payback and returns",
            "the funding request: amount, type, terms and use of funds",
            "milestones for the next twelve months",
        ],
        "rules": [
            "it must stand alone",
            "lead with the strongest point for the reader",
            "do not write it as a table of contents",
            "every figure must match the model exactly and must not be re-derived",
        ],
        "words": (250, 500),
    },
    "Company Description": {
        "purpose": "Establish who the business is and where it is going.",
        "pull": ["the user's inputs"],
        "must_include": [
            "name, location and legal structure, with one reason for the form chosen",
            "an ownership table whose shares sum to one hundred percent",
            "mission in one sentence: what the business does, for whom, how",
            "vision in one or two sentences",
            "three to five values, each with a short meaning",
            "business status: idea, startup or operating",
            "three to six SMART objectives, short-term and long-term",
        ],
        "rules": [
            "objectives must be consistent with the sales forecast and milestones",
            "state facts only, with no marketing language",
            "never claim a registration or permit that is not held",
        ],
        "words": (250, 600),
    },
    "Market Analysis": {
        "purpose": "Prove there is a real, reachable market and show the competition is understood.",
        "pull": ["user research", "cited external sources", "operational capacity"],
        "must_include": [
            "industry size, growth and three to five trends, each cited",
            "target segments and a primary customer persona",
            "the customer's problem, current alternatives and willingness to pay",
            "market size computed bottom-up: TAM, SAM and SOM with each input and source",
            "three to five competitors, or the competitor types with a verification tag",
            "a comparison of competitor, channel, price, strengths, weaknesses and differentiation",
            "a SWOT of three to five items per quadrant, linked to strategy",
        ],
        "rules": [
            "never target everyone",
            "the obtainable share must be realistic and within capacity",
            "never claim a market share that cannot be shown bottom-up",
            "separate cited facts from labelled inferences",
        ],
        "words": (600, 1500),
    },
    "Products and Services": {
        "purpose": "Describe the offer and why customers will pick it.",
        "pull": ["the user's inputs", "unit-cost data", "pricing"],
        "must_include": [
            "each product or service line, with customer benefits",
            "a table of name, description, price, unit cost and gross margin",
            "a value proposition in the form for this customer, who needs this, we provide this, unlike this",
            "the pricing method and how price covers cost and yields the target margin",
            "intellectual property and its status, or the plan to protect the brand",
            "a development roadmap with timing and any material cost",
        ],
        "rules": [
            "prices and costs must equal the assumptions register",
            "never present a planned feature as existing",
            "each product line needs its unit economics: price minus unit cost equals margin",
        ],
        "words": (300, 900),
    },
    "Marketing and Sales Plan": {
        "purpose": "Show how customers will be reached and converted at a known cost.",
        "pull": ["market analysis", "products and services", "the marketing budget"],
        "must_include": [
            "a positioning statement and the key messages",
            "a channel table: channel, segment, activity, monthly cost, expected output, conversion and customers",
            "the sales process from lead to after-sales, and who sells",
            "customer retention activities and the target repeat rate",
            "the marketing budget for Year 1 and by year after",
        ],
        "rules": [
            "cover the four Ps, extended to seven for services",
            "tie every activity to a goal, a cost and a metric",
            "the marketing budget must equal the marketing line in the operating budget",
        ],
        "words": (600, 1200),
    },
    "Operations Plan": {
        "purpose": "Prove the business can deliver the product at the planned volume and quality.",
        "pull": ["the user's inputs", "quotations", "supplier terms"],
        "must_include": [
            "the location and facilities, with rent and the reason for the site",
            "an equipment table: item, quantity, unit cost, total cost, useful life and salvage value",
            "suppliers, payment terms, lead times and the inventory policy",
            "the production or service-delivery flow and the staff role at each step",
            "capacity and the utilisation target by period",
            "quality control and the customer feedback loop",
            "required legal registrations, permits and licences, with cost and status",
        ],
        "rules": [
            "capacity caps the sales forecast",
            "every cost here must appear in the startup budget or the operating budget",
            "never assert that a permit is obtained unless the case says so",
        ],
        "words": (600, 1200),
    },
    "Management and Organisation": {
        "purpose": "Show that the team can execute.",
        "pull": ["the user's inputs", "the staffing plan"],
        "must_include": [
            "the organisation structure and reporting lines",
            "short biographies of owners and key managers, using only supplied facts",
            "a staffing table: position, headcount, monthly salary, start month and employer costs",
            "advisors and outside professionals",
            "an honest statement of the skill gaps and how each will be filled",
        ],
        "rules": [
            "never invent credentials, employers or advisors",
            "where no biography was supplied, write the role and mark the biography as owner-supplied",
            "show owner compensation explicitly",
        ],
        "words": (300, 900),
    },
    "Financial Plan": {
        "purpose": "Demonstrate viability, the return of capital and survival under stress.",
        "pull": ["the assumptions register", "every financial table in the record"],
        "must_include": [
            "the key assumptions and what drives them",
            "startup costs and funding, with sources equal to uses",
            "the sales forecast and its gross margin",
            "the operating expense budget",
            "the projected income statement, cash flow and balance sheet",
            "break-even: units, sales, the month reached and the margin of safety",
            "returns: payback, return on investment, net present value and internal rate of return",
            "key ratios: liquidity, profitability, leverage, debt service and efficiency",
            "sensitivity and the best, expected and worst cases",
            "the funding request, its terms and its allocation",
        ],
        "rules": [
            "after every table, interpret what drives the result instead of restating it",
            "explain the why behind growth, margin changes and cash dips",
            "if Year 1 loses money or burns cash, say so and show when it turns",
            "every figure must match the model exactly",
        ],
        "words": (1200, 3000),
    },
    "Risk Analysis and Mitigation": {
        "purpose": "Show what could go wrong and the plan for it.",
        "pull": ["sensitivity", "operations", "market", "legal status"],
        "must_include": [
            "a risk register: risk, category, likelihood, impact, mitigation, owner and early-warning indicator",
            "market, competition, operational, financial, legal, technology, people and external risks",
            "at least eight risks, ranked by likelihood times impact",
            "the top three risks linked to the sensitivity scenarios",
        ],
        "rules": [
            "every risk needs a specific mitigation, not merely close monitoring",
            "be candid: do not list only trivial risks",
        ],
        "words": (250, 700),
    },
    "Implementation Timeline and Milestones": {
        "purpose": "Show the path from today to launch and early growth.",
        "pull": ["funding timing", "pre-opening costs", "cash flow", "permit lead times"],
        "must_include": [
            "a milestone table: milestone, start, end, owner, cost, dependency and success criterion",
            "pre-launch milestones: funding, registration, permits, lease, equipment, hiring, soft launch and launch",
            "post-launch targets at month three, six and twelve",
            "Year 2 and Year 3 expansion",
        ],
        "rules": [
            "every milestone is verifiable",
            "dates must be consistent with funding, costs, cash flow and permit lead times",
            "use relative months when no start date is given",
        ],
        "words": (250, 500),
    },
    "Appendices": {
        "purpose": "Carry the supporting material the main text references.",
        "pull": ["the record's tables", "documents the owner supplied"],
        "must_include": [
            "the detailed monthly financial schedules the workbook holds",
            "the documents supplied by the owner, listed with their appendix letter",
            "each missing attachment named as one the owner must supply",
        ],
        "rules": [
            "never fabricate a document",
            "each appendix has a letter, a title and an in-text reference",
        ],
        "words": (100, 500),
    },
}


def headings():
    """The eleven narrative headings, in the guide's order."""
    return list(BRIEFS)


def brief(heading):
    return BRIEFS.get(heading) or {}
