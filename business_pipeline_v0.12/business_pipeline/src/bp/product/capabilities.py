"""Paper capabilities: which frozen method a paper may call, when, and what it may say.

A capability is **not** a step in the pipeline.  It is a declaration that a
method exists, the kind of question it answers, the inputs it needs and the
claim it licenses.  The conductor resolves a brief against this catalogue and
then *decides* whether the paper carries a computation at all.  A brief that
matches nothing produces `selected: []`, which is a complete answer: no figures
are asked for, no computation section exists and the export gate requires none.

Rules this module keeps:

- deterministic: pure functions over (brief, framework, answers), no model,
  no network, no I/O, no clock;
- no formula and no number: the frozen core computes, this module only names
  what the core can do and when it applies;
- fail closed: an unknown key or an inapplicable framework is refused with the
  real options, never silently substituted;
- auditable: every selection records the rule that fired and the sentence it
  matched; the whole selection is hashed and stored with the case.
"""

import hashlib
import json
import re

FORMAT = "bp-capabilities/1"

#: Bump when a cue, a slot or a priority changes.  The value is stored in every
#: case, so a paper can always be re-derived against the catalogue it used.
CATALOGUE_VERSION = "1"

#: A paper may not carry more than this many computations; a fourth candidate is
#: reported as not included instead of quietly widening the paper.
MAX_COMPUTATIONS = 3

#: Frameworks that already carry their own computation section.  The break-even
#: analysis is part of the paper's shape, so it is not attached a second time.
_EMBEDDED = {"breakeven": "breakeven", "five_forces_breakeven": "breakeven"}

#: Every framework that retrieves evidence can carry a declared computation.
_EVIDENCE_FRAMEWORKS = ("pestel", "swot", "pestel_swot", "five_forces", "five_forces_breakeven",
                        "value_chain", "ansoff")


def _row(key, method, label, intent, cues, slot, needs_any=None, priority=20, applies=None,
         domain=None, integration=None, output=None, one_of=None, min_inputs=None):
    """One catalogue entry.  The licence and the limitation are read from the
    method's own description at resolve time, never restated here."""
    return key, {
        "key": key, "method": method, "label": label, "subject": "", "intent": intent,
        "priority": priority, "any_of": list(cues), "needs_any": list(needs_any or []),
        "applies_to": tuple(applies or _EVIDENCE_FRAMEWORKS), "slot": tuple(slot),
        "integration": integration or "Framework and Declared Figures",
        "needs": "scalar", "licenses": "", "not": "", "domain": domain,
        # some frozen methods return a bare value instead of a mapping; the
        # catalogue names the key it is recorded under
        "output": output,
        # a method that needs one of several declarations (a beta or two series;
        # a price or a yield) states the groups here, so no capability invents one
        "one_of": [list(group) for group in (one_of or [])],
        # a method whose inputs are all optional needs a minimum to be meaningful
        "min_inputs": min_inputs,
    }


ENTRIES = dict([
    _row("breakeven", "breakeven", "Break-even", "cost_cover",
         [r"break[\s-]?even", r"pay (?:for itself)", r"cover (?:its|the|our) costs?",
          r"how many units", r"fixed cost"],
         ("Financial Feasibility", "Break-even Analysis"),
         needs_any=[r"\bprice\b", r"per unit", r"\bvariable\b", r"unit cost", r"\bcosts?\b", r"\bunits?\b"],
         priority=20, integration="Framework and Financial Feasibility", domain="breakeven"),
    _row("npv", "npv", "Net present value", "appraisal",
         [r"net present value", r"\bnpv\b"],
         ("Financial Feasibility", "Net Present Value"),
         needs_any=[r"cash ?flows?", r"\boutlay\b", r"invest(?:ment)?"], priority=30, output="npv"),
    _row("irr", "irr", "Internal rate of return", "appraisal",
         [r"internal rate of return", r"\birr\b"],
         ("Financial Feasibility", "Internal Rate of Return"),
         needs_any=[r"cash ?flows?", r"\boutlay\b"], priority=25),
    _row("discounted_payback", "discounted_payback", "Discounted payback", "appraisal",
         [r"discounted payback", r"pay ?back period", r"when (?:will|does) (?:it|the investment) pay back"],
         ("Financial Feasibility", "Discounted Payback"),
         needs_any=[r"cash ?flows?", r"\boutlay\b"], priority=20),
    _row("project_metrics", "project_metrics", "Project metrics", "appraisal",
         [r"profitability index", r"project ranking", r"rank the projects?", r"equivalent annual"],
         ("Financial Feasibility", "Project Metrics"),
         needs_any=[r"cash ?flows?", r"\boutlay\b"], priority=15),
    _row("unit_economics", "unit_economics", "Unit economics", "unit_margin",
         [r"unit economics", r"contribution (?:margin )?per (?:unit|customer)", r"margin per (?:unit|customer)",
          r"acquisition cost"],
         ("Financial Feasibility", "Unit Economics"), priority=15),
    _row("wacc", "wacc", "Cost of capital", "cost_of_capital",
         [r"\bwacc\b", r"cost of capital", r"weighted average cost"],
         ("Financial Feasibility", "Cost of Capital"), priority=15),
    _row("return_on_investment", "return_on_investment", "Return on investment", "return",
         [r"return on (?:the )?investment", r"\broi\b"],
         ("Financial Feasibility", "Return on Investment"), priority=12),
    _row("market_sizing", "market_sizing", "Market size", "market_size",
         [r"market siz(?:e|ing)", r"how big is the market", r"addressable market"],
         ("Market Assessment", "Market Size"), priority=15),
    _row("market_share", "market_share", "Market share", "market_position",
         [r"market share"],
         ("Market Assessment", "Market Share"), priority=12),
    _row("startup_capital", "startup_capital", "Start-up capital", "funding_need",
         [r"start[\s-]?up (?:costs?|capital|funding)", r"(?:capital|funding|money) (?:is |will be )?(?:needed|required)",
          r"how much (?:capital|funding|money)"],
         ("Financial Feasibility", "Start-up Capital"), priority=15),
    _row("cash_runway", "cash_runway", "Cash runway", "runway",
         [r"\brunway\b", r"months of (?:cash|runway)", r"how long will (?:the )?cash last"],
         ("Financial Feasibility", "Cash Runway"), priority=15),
    _row("clv_model", "clv_model", "Customer lifetime value", "customer_value",
         [r"lifetime value", r"\bclv\b", r"\bltv\b(?!\s*/)"],
         ("Customer Economics", "Customer Lifetime Value"), priority=15),
    _row("campaign_efficiency", "campaign_efficiency", "Campaign efficiency", "campaign",
         [r"campaign (?:performance|efficiency|results)", r"cost per (?:click|acquisition)", r"\bctr\b"],
         ("Marketing Performance", "Campaign Efficiency"), priority=15),
    _row("elasticity", "elasticity", "Price elasticity of demand", "price_response",
         [r"elasticity", r"price sensitivity"],
         ("Market Response", "Price Elasticity of Demand"), priority=12),
    _row("earned_value", "earned_value", "Earned value", "delivery_status",
         [r"earned value", r"\bevm\b", r"schedule performance index", r"cost performance index"],
         ("Delivery Status", "Earned Value"), priority=15),
    _row("growth_rate", "growth_rate", "Growth rate", "growth",
         [r"growth rate", r"\bcagr\b", r"how fast did .* grow"],
         ("Economic Context", "Growth Rate"), priority=10),
    _row("inflation_cpi", "inflation_cpi", "Inflation", "inflation",
         [r"inflation rate", r"\bcpi\b", r"real (?:wage|interest)"],
         ("Economic Context", "Inflation"), priority=10),
    _row("tax_incidence", "tax_incidence", "Tax incidence", "tax_burden",
         [r"tax incidence", r"who bears the tax", r"burden of the tax"],
         ("Policy Impact", "Tax Incidence"), priority=12),
    _row("pricing_decision", "pricing_decision", "Pricing decision", "pricing",
         [r"what price", r"pricing (?:decision|strategy)", r"\bmarkup\b"],
         ("Pricing", "Pricing Decision"), priority=12),
    _row("cap_table_round", "cap_table_round", "Cap table", "ownership",
         [r"cap table", r"equity split", r"dilution"],
         ("Ownership", "Cap Table"), priority=12),
    _row("time_value", "time_value", "Time value of money", "time_value",
         [r"time value", r"future value", r"present value of (?:a )?(?:single|lump)"],
         ("Financial Feasibility", "Time Value of Money"), priority=12),
    _row("loan_amortization", "loan_amortization", "Loan amortization", "debt_service",
         [r"loan (?:amorti[sz]ation|payment|schedule)", r"monthly payment", r"amorti[sz]"],
         ("Financial Feasibility", "Loan Amortization"), priority=12),
    _row("leverage_analysis", "leverage_analysis", "Financial leverage", "leverage",
         [r"financial leverage", r"degree of financial leverage", r"interest cover"],
         ("Financial Feasibility", "Financial Leverage"), priority=10),
    _row("inventory_policy", "inventory_policy", "Inventory policy", "inventory",
         [r"economic order quantity", r"\beoq\b", r"inventory policy", r"reorder point"],
         ("Operations", "Inventory Policy"), priority=12),
    _row("purchase_intent", "purchase_intent", "Purchase intent", "demand_signal",
         [r"purchase intent", r"intent to (?:buy|purchase)"],
         ("Customer Evidence", "Purchase Intent"), priority=12),
    _row("sales_projection", "sales_projection", "Sales projection", "sales_plan",
         [r"sales projection", r"project the sales", r"projected units"],
         ("Financial Feasibility", "Sales Projection"), priority=12),
    _row("sales_from_market", "sales_from_market", "Target sales from the market", "sales_plan",
         [r"target (?:sales|revenue)", r"revenue target", r"market share target"],
         ("Financial Feasibility", "Target Sales from the Market"), priority=14),
    _row("depreciation_schedule", "depreciation_schedule", "Depreciation", "depreciation",
         [r"depreciation"],
         ("Financial Feasibility", "Depreciation"), priority=12),
    _row("tax_declared", "tax_declared", "Declared income tax", "tax_charge",
         [r"income tax on", r"after-?tax income", r"tax on the declared"],
         ("Financial Feasibility", "Declared Income Tax"), priority=10),
    _row("equity_bridge", "equity_bridge", "Equity bridge", "valuation",
         [r"equity bridge", r"equity value", r"enterprise value"],
         ("Financial Feasibility", "Equity Bridge"), priority=12),
    _row("multi_product_breakeven", "multi_product_breakeven", "Multi-product break-even",
         "cost_cover",
         [r"multi-?product (?:break[\s-]?even|cost)", r"product mix", r"break[\s-]?even.*\bmix\b"],
         ("Financial Feasibility", "Multi-product Break-even"),
         needs_any=[r"products?", r"\bmix\b"], priority=25),
    _row("capm", "capm", "Cost of equity (CAPM)", "required_return",
         [r"\bcapm\b", r"capital asset pricing", r"required return", r"cost of equity", r"\bbeta\b"],
         ("Financial Feasibility", "Cost of Equity (CAPM)"), priority=15,
         one_of=[["beta"], ["returns_asset", "returns_market"]]),
    _row("bond_analysis", "bond_analysis", "Bond price and yield", "bond",
         [r"\bbond\b", r"coupon rate", r"yield to maturity"],
         ("Financial Feasibility", "Bond Price and Yield"), priority=12,
         one_of=[["yield_to_maturity"], ["price"]]),
    _row("ratio_analysis", "ratio_analysis", "Ratio analysis", "ratios",
         [r"ratio analysis", r"financial ratios", r"current ratio", r"liquidity ratio",
          r"profitability ratio"],
         ("Financial Analysis", "Ratio Analysis"), priority=12, min_inputs=2),
    _row("dcf_valuation", "dcf_valuation", "Discounted cash flow valuation", "valuation",
         [r"\bdcf\b", r"discounted cash ?flows?", r"terminal (?:value|growth)"],
         ("Financial Feasibility", "Discounted Cash Flow Valuation"),
         needs_any=[r"cash ?flows?", r"free cash"], priority=20),
    _row("multiples_valuation", "multiples_valuation", "Comparable multiples valuation", "valuation",
         [r"comparable multiples", r"peer multiple", r"p/e ratio", r"ev/ebitda", r"multiples valuation"],
         ("Financial Feasibility", "Comparable Multiples Valuation"),
         needs_any=[r"multiple", r"earnings", r"ebitda", r"book value"], priority=15,
         one_of=[["comparables"], ["peer_multiple"]]),
    _row("option_pricing", "option_pricing", "Option price", "option",
         [r"option pric", r"black[- ]scholes", r"(?:call|put) option"],
         ("Financial Feasibility", "Option Price"), priority=10),
    _row("real_option", "real_option", "Real option value", "option",
         [r"real option", r"option to (?:delay|expand|abandon|wait)"],
         ("Financial Feasibility", "Real Option Value"), priority=12),
    _row("portfolio_analysis", "portfolio_analysis", "Portfolio return and risk", "portfolio",
         [r"portfolio (?:risk|return|analysis)", r"sharpe ratio"],
         ("Financial Feasibility", "Portfolio Return and Risk"), priority=10),
    _row("descriptive_stats", "descriptive_stats", "Descriptive statistics", "distribution",
         [r"descriptive statistics", r"summary statistics"],
         ("Data Analysis", "Descriptive Statistics"),
         needs_any=[r"sample|observations?|values|data"], priority=12),
    _row("pearson", "pearson", "Correlation", "association",
         [r"correlation between", r"\bpearson\b", r"correlated"],
         ("Data Analysis", "Correlation Analysis"),
         needs_any=[r"observations?|sample|series|pairs?|data"], priority=15),
    _row("welch_t", "welch_t", "Difference between two means", "difference",
         [r"\bwelch\b", r"two-sample t", r"compar(?:e|es|ing) (?:the )?means?"],
         ("Data Analysis", "Difference Between Two Means"),
         needs_any=[r"groups?|sample|observations?|treated|control"], priority=25),
    _row("anova", "anova", "Group comparison (ANOVA)", "difference",
         [r"\banova\b", r"compar(?:e|es|ing) (?:three |the )?groups?"],
         ("Data Analysis", "Group Comparison (ANOVA)"),
         needs_any=[r"groups?|sample|observations?"], priority=20),
    _row("chi_square", "chi_square", "Association between categories", "independence",
         [r"chi[\s-]?square", r"association between", r"contingency table"],
         ("Data Analysis", "Association Between Categories"),
         needs_any=[r"table|counts?|categories|groups?"], priority=15),
    _row("ols", "ols", "Multiple regression", "relationship_model",
         [r"\bols\b", r"regression", r"predict(?:s|ed) by"],
         ("Data Analysis", "Multiple Regression"),
         needs_any=[r"observations?|sample|data|predictors?|variables?"], priority=20),
    _row("queue_analysis", "queue_analysis", "Queue performance", "flow",
         [r"\bqueue", r"waiting (?:line|time)", r"service (?:rate|level)"],
         ("Operations", "Queue Performance"),
         needs_any=[r"arrival|service|queue|rate"], priority=15),
    _row("capacity_analysis", "capacity_analysis", "Capacity and bottleneck", "capacity",
         [r"\bcapacity\b", r"bottleneck", r"throughput"],
         ("Operations", "Capacity and Bottleneck"),
         needs_any=[r"demand|hours|units|resources?"], priority=15),
    _row("oee_analysis", "oee_analysis", "Equipment effectiveness", "equipment",
         [r"\boee\b", r"overall equipment effectiveness", r"downtime"],
         ("Operations", "Equipment Effectiveness"),
         needs_any=[r"production|downtime|units|cycle"], priority=15),
    _row("process_control", "process_control", "Process control", "quality",
         [r"\bspc\b", r"control chart", r"process (?:control|variation)"],
         ("Operations", "Process Control"),
         needs_any=[r"sample|values|observations|measurements"], priority=15),
    _row("line_balancing", "line_balancing", "Line balancing", "line_balance",
         [r"line balanc", r"assembly line", r"balance the line", r"station"],
         ("Operations", "Line Balancing"),
         needs_any=[r"tasks?|stations?|cycle"], priority=15),
    _row("demand_curve", "demand_curve", "Demand curve", "demand",
         [r"demand curve", r"price[- ]quantity", r"elasticity at (?:the )?mean"],
         ("Market Response", "Demand Curve"),
         needs_any=[r"prices?|quantities|points"], priority=14),
    _row("rfm_scoring", "rfm_scoring", "RFM segments", "segmentation",
         [r"\brfm\b", r"segment (?:the )?customers", r"recency.{0,30}frequency"],
         ("Customer Evidence", "RFM Segments"),
         needs_any=[r"customers?|segments?"], priority=12),
    _row("sales_funnel", "sales_funnel", "Sales funnel", "funnel",
         [r"\bfunnel\b", r"drop[- ]?off", r"conversion (?:through|from)"],
         ("Marketing Performance", "Sales Funnel"),
         needs_any=[r"stages?|visitors?|leads?|counts?"], priority=12),
    _row("ab_test_two_proportion", "ab_test_two_proportion", "A/B test", "experiment",
         [r"\ba/b test\b", r"a-b test", r"two[- ]proportion", r"conversion (?:difference|lift)"],
         ("Marketing Performance", "A/B Test"),
         needs_any=[r"visitors?|conversions?|sample"], priority=15),
    _row("social_engagement", "social_engagement", "Social engagement", "social",
         [r"social (?:media )?(?:engagement|performance)", r"engagement rate", r"\bcpm\b"],
         ("Marketing Performance", "Social Engagement"),
         needs_any=[r"impressions?|reach|followers?|platform"], priority=10),
    _row("reliability_alpha", "reliability_alpha", "Survey reliability", "reliability",
         [r"cronbach", r"reliability (?:alpha|coefficient)", r"internal consistency"],
         ("Data Analysis", "Survey Reliability"),
         needs_any=[r"items?|scale|questions?|respondents?"], priority=12),
    _row("weighted_summary", "weighted_summary", "Weighted summary", "weighted",
         [r"weighted (?:mean|average|summary)", r"\bweights?\b"],
         ("Data Analysis", "Weighted Summary"),
         needs_any=[r"values?|weights?"], priority=10),
    _row("power_analysis", "power_analysis", "Statistical power", "sample_size",
         [r"statistical power", r"power analysis", r"sample size", r"minimum detectable effect"],
         ("Data Analysis", "Statistical Power"),
         needs_any=[r"power|sample|effect"], priority=12),
    _row("cohort_retention", "cohort_retention", "Cohort retention", "retention",
         [r"cohort (?:retention|analysis)", r"retention (?:by|across) cohort"],
         ("Customer Evidence", "Cohort Retention"),
         needs_any=[r"cohorts?|retained|sizes?"], priority=12),
    _row("trend_forecast", "trend_forecast", "Trend forecast", "forecast",
         [r"trend forecast", r"forecast (?:the )?(?:series|sales|demand)", r"project the trend"],
         ("Data Analysis", "Trend Forecast"),
         needs_any=[r"series|values|periods|observations"], priority=12),
    _row("missing_data_bounds", "missing_data_bounds", "Missing data bounds", "data_quality",
         [r"missing data", r"how (?:much|many) (?:data|values) (?:is|are) missing", r"missing values?"],
         ("Data Analysis", "Missing Data Bounds"),
         needs_any=[r"missing|values|data"], priority=10),
    _row("media_plan", "media_plan", "Media plan", "media",
         [r"media plan", r"reach and frequency", r"\bgrp\b"],
         ("Marketing Performance", "Media Plan"),
         needs_any=[r"reach|insertions|vehicles|budget"], priority=12),
    _row("web_analytics", "web_analytics", "Web analytics", "web",
         [r"web analytics", r"channel (?:conversions|revenue)", r"sessions and conversions"],
         ("Marketing Performance", "Web Analytics"),
         needs_any=[r"sessions?|conversions?|channels?"], priority=12),
    _row("email_list_health", "email_list_health", "Email list health", "email",
         [r"email (?:list|campaign)", r"open rate", r"click[- ]to[- ]open"],
         ("Marketing Performance", "Email List Health"),
         needs_any=[r"opens?|clicks?|sends?|subscribers?"], priority=12),
    _row("customer_profitability", "customer_profitability", "Customer profitability", "segment_profit",
         [r"customer profitability", r"profit(?:ability)? by segment", r"segment profit"],
         ("Customer Economics", "Customer Profitability"),
         needs_any=[r"segments?|revenue|costs?"], priority=12),
    _row("channel_economics", "channel_economics", "Channel economics", "channel_unit",
         [r"channel economics", r"\bcac\b", r"ltv\s*/\s*cac", r"payback (?:per|by) channel"],
         ("Customer Economics", "Channel Economics"),
         needs_any=[r"spend|customers?|channels?"], priority=14),
    _row("attribution_split", "attribution_split", "Attribution split", "attribution",
         [r"attribution", r"first[- ]click", r"last[- ]click", r"linear attribution"],
         ("Marketing Performance", "Attribution Split"),
         needs_any=[r"channels?|clicks?|conversions?"], priority=12),
    _row("dupont_analysis", "dupont_analysis", "DuPont decomposition", "return_decomposition",
         [r"dupont", r"return on equity decompos", r"three[- ]step roe"],
         ("Financial Analysis", "DuPont Decomposition"),
         needs_any=[r"revenue|assets|equity|income"], priority=12),
    _row("trend_analysis", "trend_analysis", "Trend analysis", "trend",
         [r"trend analysis", r"common[- ]size", r"year[- ]on[- ]year (?:revenue|margin)"],
         ("Financial Analysis", "Trend Analysis"),
         needs_any=[r"years?|periods?|revenue|margins?"], priority=12),
    _row("working_capital", "working_capital", "Working capital cycle", "working_capital",
         [r"working capital", r"cash conversion cycle", r"economic order quantity", r"\beoq\b"],
         ("Financial Analysis", "Working Capital Cycle"),
         needs_any=[r"inventory|receivables|payables|demand"], priority=14),
    _row("scenario_analysis", "scenario_analysis", "Scenario analysis", "scenario",
         [r"scenario analysis", r"sensitivity to the (?:discount )?rate", r"rate sensitivity"],
         ("Financial Feasibility", "Scenario Analysis"),
         needs_any=[r"cash ?flows?|rate|discount"], priority=14),
    _row("risk_metrics", "risk_metrics", "Value at risk", "market_risk",
         [r"value at risk", r"\bvar\b", r"expected shortfall", r"risk metrics"],
         ("Financial Feasibility", "Value at Risk"),
         needs_any=[r"returns?|portfolio|confidence"], priority=14),
    _row("fx_parity", "fx_parity", "FX parity", "parity",
         [r"\bfx parity\b", r"interest[- ]rate parity", r"purchasing[- ]power parity", r"forward (?:rate|premium)"],
         ("Financial Feasibility", "FX Parity"),
         needs_any=[r"spot|forward|rates?|inflation"], priority=12),
    _row("currency_convert", "currency_convert", "Currency conversion", "conversion",
         [r"convert .* (?:to|into) ", r"currency conversion", r"exchange rate"],
         ("Financial Feasibility", "Currency Conversion"),
         needs_any=[r"amount|rate|currency"], priority=12),
    _row("ols_robust", "ols_robust", "Regression with robust errors", "relationship_model",
         [r"robust (?:standard errors?|errors|regression)", r"heteroske"],
         ("Data Analysis", "Regression with Robust Errors"),
         needs_any=[r"observations?|sample|data|predictors?"], priority=25),
])


def catalogue():
    """A copy of the catalogue, for the API and the UI.  Never mutated by callers."""
    return [dict(entry) for entry in ENTRIES.values()]


def entry(key):
    found = ENTRIES.get(str(key or "").strip().lower())
    if not found:
        raise KeyError("Unknown capability: " + str(key))
    return found


def _normalise(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _sentence_with(text, match):
    """The student's own sentence around a cue, for the audit trail."""
    start = max(text.rfind(".", 0, match.start()), text.rfind("?", 0, match.start()),
                text.rfind("!", 0, match.start()), text.rfind("\n", 0, match.start()))
    end = len(text)
    for mark in (".", "?", "!", "\n"):
        found = text.find(mark, match.end())
        if found != -1:
            end = min(end, found + 1)
    return _normalise(text[start + 1:end])[:300]


def _first_match(entry_row, text):
    for pattern in entry_row["any_of"]:
        match = re.search(pattern, text, re.I)
        if match:
            return match
    return None


def _needs_match(entry_row, text):
    if not entry_row["needs_any"]:
        return True
    return any(re.search(pattern, text, re.I) for pattern in entry_row["needs_any"])


def _selected(entry_row, rule, quote):
    return {
        "key": entry_row["key"],
        "method": entry_row["method"],
        "label": entry_row["label"],
        "subject": entry_row["subject"],
        "slot": list(entry_row["slot"]),
        "integration": entry_row.get("integration") or "Framework and Declared Figures",
        "inputs_required": [],
        "licenses": entry_row["licenses"],
        "not": entry_row["not"],
        "because": {"rule": rule, "quote": quote},
    }


def _not_included(entry_row, reason):
    return {"key": entry_row["key"], "label": entry_row["label"], "reason": reason}


def _hash(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def resolve(brief, framework, answers=None):
    """Decide which capabilities, if any, this paper carries.

    `selected` is empty when the brief does not ask a question a computation
    answers — the paper then uses its framework only.  `question` is set when a
    cue matched but the quantities the method needs are absent; the conductor
    asks that one question instead of guessing.
    """
    framework = str(framework or "").strip().lower()
    text = _normalise(brief)
    selected, not_included, ambiguous = [], [], []
    carried = _EMBEDDED.get(framework)
    for entry_row in ENTRIES.values():
        match = _first_match(entry_row, text)
        if not match:
            continue
        quote = _sentence_with(text, match)
        if entry_row["key"] == carried:
            not_included.append(_not_included(entry_row, "the " + framework + " paper already "
                                                               "carries this analysis"))
            continue
        if framework and framework not in entry_row["applies_to"]:
            not_included.append(_not_included(entry_row, "it does not fit a " + framework + " paper"))
            continue
        if not _needs_match(entry_row, text):
            ambiguous.append((entry_row, quote))
            continue
        selected.append(_selected(entry_row, "cue:" + entry_row["intent"], quote))
    # one capability per intent: the strongest priority wins, the rest are named
    by_intent = {}
    for row in selected:
        intent = ENTRY_INTENT[row["key"]]
        current = by_intent.get(intent)
        if current is None:
            by_intent[intent] = row
            continue
        loser = row if ENTRY_PRIORITY[row["key"]] <= ENTRY_PRIORITY[current["key"]] else current
        winner = current if loser is row else row
        by_intent[intent] = winner
        not_included.append({"key": loser["key"], "label": loser["label"],
                             "reason": "another capability already answers this question"})
    ordered = sorted(by_intent.values(), key=lambda row: (-ENTRY_PRIORITY[row["key"]], row["key"]))
    for row in ordered[MAX_COMPUTATIONS:]:
        not_included.append({"key": row["key"], "label": row["label"],
                             "reason": "the paper carries at most %d computations" % MAX_COMPUTATIONS})
    selected = ordered[:MAX_COMPUTATIONS]
    question = None
    quote = ""
    if ambiguous and not selected:
        entry_row, quote = ambiguous[0]
        question = {
            "id": "capability:" + entry_row["key"],
            "prompt": "Should this paper include a " + entry_row["label"].lower() + " analysis?",
            "why": ("You wrote: \"" + quote + "\". The paper can test the declared figures against the "
                    "frozen method, but only from figures you declare."),
            "type": "choice",
            "choices": [["yes", "Yes, include the " + entry_row["label"].lower()],
                        ["no", "No, the analysis only"]],
            "allow_skip": False,
        }
    payload = {"format": FORMAT, "catalogue_version": CATALOGUE_VERSION, "framework": framework,
               "selected": [{k: row[k] for k in ("key", "method", "slot")} for row in selected],
               "question": question["id"] if question else None}
    return {"format": FORMAT, "catalogue_version": CATALOGUE_VERSION,
            "frameworks": [framework] if framework else [], "selected": selected,
            "not_included": not_included, "question": question, "question_quote": quote,
            "hash": _hash(payload)}


def apply_answer(selection, question_id, value):
    """Record the student's answer to the one ambiguity question.

    Deterministic: only the recorded "yes" adds the capability, only "no" drops
    it, and the reason is stored so the plan can explain itself.
    """
    prefix = "capability:"
    key = str(question_id or "")
    if not key.startswith(prefix):
        return selection
    key = key[len(prefix):]
    answer = str(value or "").strip().lower()
    try:
        entry_row = entry(key)
    except KeyError:
        return selection
    selection = dict(selection or {})
    selected = [dict(row) for row in selection.get("selected") or []]
    not_included = [dict(row) for row in selection.get("not_included") or []]
    selection["question"] = None
    if answer == "yes":
        if not any(row["key"] == key for row in selected) and len(selected) < MAX_COMPUTATIONS:
            row = _selected(entry_row, "student:confirmed", selection.get("question_quote") or "")
            selected.append(row)
        not_included = [row for row in not_included if row["key"] != key]
    elif answer == "no":
        not_included = [row for row in not_included if row["key"] != key]
        not_included.append(_not_included(entry_row, "you chose not to include it"))
        selected = [row for row in selected if row["key"] != key]
    selection["selected"] = selected
    selection["not_included"] = not_included
    selection["hash"] = _hash({"format": FORMAT, "catalogue_version": CATALOGUE_VERSION,
                               "selected": [{k: row[k] for k in ("key", "method", "slot")}
                                            for row in selected],
                               "question": None})
    return selection


def set_enabled(selection, framework, key, enabled, reason=""):
    """Add or drop one capability after the plan is shown.

    The student's decision is recorded: a drop is a named exclusion, not a silent
    change, and an add names what licenses it.
    """
    entry_row = entry(key)
    selection = dict(selection or {"selected": [], "not_included": []})
    selected = [dict(row) for row in selection.get("selected") or []]
    not_included = [dict(row) for row in selection.get("not_included") or []]
    if framework and framework not in entry_row["applies_to"]:
        raise ValueError(entry_row["label"] + " does not fit a " + framework + " paper.")
    if enabled:
        if any(row["key"] == key for row in selected):
            return selection
        if len(selected) >= MAX_COMPUTATIONS:
            raise ValueError("A paper carries at most %d computations." % MAX_COMPUTATIONS)
        selected.append(_selected(entry_row, "student:added", _normalise(reason)[:300]))
        not_included = [row for row in not_included if row["key"] != key]
    else:
        selected = [row for row in selected if row["key"] != key]
        not_included = [row for row in not_included if row["key"] != key]
        not_included.append(_not_included(entry_row, _normalise(reason)[:200] or "you removed it"))
    selection["selected"] = selected
    selection["not_included"] = not_included
    selection["hash"] = _hash({"format": FORMAT, "catalogue_version": CATALOGUE_VERSION,
                               "selected": [{k: row[k] for k in ("key", "method", "slot")}
                                            for row in selected],
                               "question": None})
    return selection


def carries(selection, key):
    return any(row["key"] == key for row in (selection or {}).get("selected") or [])


ENTRY_INTENT = {key: row["intent"] for key, row in ENTRIES.items()}
ENTRY_PRIORITY = {key: row["priority"] for key, row in ENTRIES.items()}
