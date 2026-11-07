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
from decimal import Decimal, InvalidOperation

FORMAT = "bp-capabilities/1"

#: Bump when a cue, a slot or a priority changes.  The value is stored in every
#: case, so a paper can always be re-derived against the catalogue it used.
CATALOGUE_VERSION = "2"

#: A paper may not carry more than this many computations; a fourth candidate is
#: reported as not included instead of quietly widening the paper.
MAX_COMPUTATIONS = 3

#: Frameworks that already carry their own computation section.  The break-even
#: analysis is part of the paper's shape, so it is not attached a second time.
_EMBEDDED = {"breakeven": "breakeven", "five_forces_breakeven": "breakeven"}

#: Every framework that retrieves evidence can carry a declared computation.
#: Kept here as one import so a new framework is added in framework_registry.
from .framework_registry import EVIDENCE as _EVIDENCE_FRAMEWORKS

#: Inputs that a frozen method can supply from another frozen method's result.
#: Each entry is capability -> {input: (source capability, source output field, why)}.
#: Only a chain where both sides are in the catalogue and the units agree belongs
#: here: the point is to stop a student retyping a number the core already
#: computed, never to invent a method-to-method assumption.
NEEDS_FROM = {
    "npv": {"rate": ("wacc", "wacc", "the cost of capital the WACC method computes")},
    "dcf_valuation": {"discount_rate": ("wacc", "wacc",
                                        "the cost of capital the WACC method computes")},
    "market_share": {"firm_sales": ("sales_from_market", "target_revenue",
                                    "the target revenue the sales method computes")},
}


def _row(key, method, label, intent, cues, slot, needs_any=None, priority=20, applies=None,
         domain=None, integration=None, output=None, one_of=None, min_inputs=None,
         require_inputs=None, row_fields=None):
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
        # inputs the frozen core requires but its own schema marks optional;
        # named here so the form asks for them and the refusal is not a crash
        "require_inputs": list(require_inputs or []),
        # `rows` inputs do not declare their columns; the catalogue does
        "row_fields": {name: list(fields) for name, fields in (row_fields or {}).items()},
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
         needs_any=[r"cash ?flows?", r"\boutlay\b", r"invest(?:ment)?",
                    r"\breturns?\b", r"a year|per year|annually",
                    r"\bcosts?\b", r"\bpay(?:s|back)?\b"],
         priority=30, output="npv"),
    _row("irr", "irr", "Internal rate of return", "appraisal",
         [r"internal rate of return", r"\birr\b"],
         ("Financial Feasibility", "Internal Rate of Return"),
         needs_any=[r"cash ?flows?", r"\boutlay\b", r"\breturns?\b",
                    r"a year|per year|annually", r"\bcosts?\b"], priority=25),
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
         [r"(?<!social )return on (?:the )?investment", r"\broi\b"],
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
         [r"inflation rate", r"consumer price index", r"price index"],
         ("Economic Context", "Inflation"), priority=10),
    _row("tax_incidence", "tax_incidence", "Tax incidence", "tax_burden",
         [r"tax incidence", r"who bears the tax", r"burden of the tax"],
         ("Policy Impact", "Tax Incidence"), priority=12),
    _row("pricing_decision", "pricing_decision", "Pricing decision", "pricing",
         [r"what price", r"pricing (?:decision|strategy)", r"price (?:the|our) (?:product|line)"],
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
         needs_any=[r"tasks?|stations?|cycle"], priority=15,
         row_fields={"tasks": ["name", "time", "predecessors"]}),
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
    _row("market_concentration", "market_concentration", "Market concentration", "market_structure",
         [r"market concentration", r"\bhhi\b", r"herfindahl", r"four[- ]firm"],
         ("Market Structure", "Market Concentration"),
         needs_any=[r"revenues?|shares?|firms?"], priority=14),
    _row("cost_curves", "cost_curves", "Cost curves", "cost_structure",
         [r"cost curve", r"average cost", r"shut ?down"],
         ("Market Structure", "Cost Curves"),
         needs_any=[r"costs?|quantity|output"], priority=12),
    _row("market_power", "market_power", "Market power", "market_power",
         [r"market power", r"lerner"],
         ("Market Structure", "Market Power"),
         needs_any=[r"price|marginal cost"], priority=12),
    _row("proforma_statements", "proforma_statements", "Pro-forma statements", "projection",
         [r"pro-?forma", r"project(?:ed)? (?:financial )?statements", r"projected balance sheet"],
         ("Financial Feasibility", "Pro-forma Statements"),
         needs_any=[r"revenue|margin|costs?"], priority=14,
         require_inputs=["interest", "principal_repayment"]),
    _row("sensitivity_table", "sensitivity_table", "Sensitivity table", "sensitivity",
         [r"sensitivity (?:table|analysis)", r"what if (?:the )?(?:price|volume)"],
         ("Financial Feasibility", "Sensitivity Table"),
         needs_any=[r"price|units|profit"], priority=14),
    _row("sroi", "sroi", "Social return on investment", "social_value",
         [r"social return on investment", r"\bsroi\b"],
         ("Impact", "Social Return on Investment"),
         needs_any=[r"investment|benefits"], priority=14),
    _row("cost_benefit", "cost_benefit", "Cost-benefit analysis", "social_appraisal",
         [r"cost[- ]benefit analysis", r"\bcba\b"],
         ("Impact", "Cost-Benefit Analysis"),
         needs_any=[r"costs?|benefits?"], priority=20),
    _row("cost_effectiveness", "cost_effectiveness", "Cost-effectiveness analysis", "social_appraisal",
         [r"cost[- ]effectiveness", r"\bicer\b"],
         ("Impact", "Cost-Effectiveness Analysis"),
         needs_any=[r"costs?|effects?|options?"], priority=15),
    # ---- economics: market structure and price theory -------------------
    _row("demand_supply_equilibrium", "demand_supply_equilibrium", "Market equilibrium", "market_model",
         [r"market equilibrium", r"equilibrium (?:price|quantity)", r"demand and supply"],
         ("Market Structure", "Market Equilibrium"),
         needs_any=[r"demand|supply|slope|intercept"], priority=30),
    _row("price_control", "price_control", "Price control", "market_model",
         [r"price (?:ceiling|floor|control)", r"minimum wage", r"price cap"],
         ("Market Structure", "Price Control"), priority=24),
    _row("profit_maximization", "profit_maximization", "Profit maximisation", "market_model",
         [r"profit[- ]maximi[sz]", r"monopolist", r"maximum profit"],
         ("Market Structure", "Profit Maximisation"), priority=25),
    _row("price_discrimination", "price_discrimination", "Price discrimination", "market_model",
         [r"price discrimination", r"third[- ]degree", r"two markets"],
         ("Market Structure", "Price Discrimination"), priority=18),
    _row("cournot_duopoly", "cournot_duopoly", "Cournot duopoly", "market_model",
         [r"cournot", r"duopoly"],
         ("Market Structure", "Cournot Duopoly"), priority=20),
    _row("nash_equilibrium", "nash_equilibrium", "Nash equilibrium", "market_model",
         [r"nash", r"game theory", r"payoff matrix"],
         ("Market Structure", "Nash Equilibrium"), priority=15),
    # ---- economics: macro ------------------------------------------------
    _row("national_income", "national_income", "National income", "national_accounts",
         [r"national income", r"\bgdp\b", r"\bgnp\b"],
         ("Economic Context", "National Income"),
         needs_any=[r"consumption|investment|exports|government"], priority=15),
    _row("unemployment_rate", "unemployment_rate", "Unemployment", "labour_stats",
         [r"unemployment rate", r"participation rate", r"labour force"],
         ("Economic Context", "Unemployment"), priority=15),
    _row("labour_market", "labour_market", "Real wages", "wages",
         [r"real wage", r"wage share", r"labour productivity"],
         ("Economic Context", "Real Wages"), priority=12),
    _row("money_multiplier", "money_multiplier", "Money multiplier", "monetary",
         [r"money multiplier", r"reserve ratio", r"monetary base"],
         ("Economic Context", "Money Multiplier"), priority=12),
    _row("fiscal_multiplier", "fiscal_multiplier", "Fiscal multiplier", "fiscal",
         [r"fiscal multiplier", r"government spending multiplier", r"tax multiplier"],
         ("Economic Context", "Fiscal Multiplier"), priority=12),
    _row("budget_debt", "budget_debt", "Budget and debt", "fiscal_debt",
         [r"budget (?:balance|deficit)", r"public debt", r"debt[- ]to[- ]gdp"],
         ("Economic Context", "Budget and Debt"), priority=14),
    _row("output_gap_okun", "output_gap_okun", "Output gap (Okun)", "output_gap",
         [r"output gap", r"okun"],
         ("Economic Context", "Output Gap (Okun)"), priority=12),
    # ---- economics: welfare ---------------------------------------------
    _row("externality_pigouvian", "externality_pigouvian", "Externality and Pigouvian tax", "welfare_external",
         [r"externality", r"pigouvian", r"external cost"],
         ("Policy Impact", "Externality and Pigouvian Tax"), priority=15),
    _row("public_good", "public_good", "Public good", "public_good",
         [r"public good", r"free[- ]rider", r"marginal benefit of (?:two|both)"],
         ("Policy Impact", "Public Good"), priority=12),
    _row("optimal_pollution", "optimal_pollution", "Optimal pollution", "pollution",
         [r"optimal pollution", r"marginal damage", r"abatement cost"],
         ("Policy Impact", "Optimal Pollution"), priority=12),
    _row("social_welfare", "social_welfare", "Social welfare", "welfare",
         [r"social welfare", r"welfare function", r"utilitarian|rawlsian"],
         ("Policy Impact", "Social Welfare"), priority=12),
    _row("gini_coefficient", "gini_coefficient", "Gini coefficient", "inequality",
         [r"\bgini\b", r"income inequality"],
         ("Policy Impact", "Gini Coefficient"), priority=14),
    _row("poverty_measures", "poverty_measures", "Poverty measures", "poverty",
         [r"poverty (?:line|rate|measure|gap)", r"headcount"],
         ("Policy Impact", "Poverty Measures"), priority=14),
    _row("tax_progressivity", "tax_progressivity", "Tax progressivity", "progressivity",
         [r"tax progressiv", r"average tax rate", r"tax incidence across"],
         ("Policy Impact", "Tax Progressivity"), priority=12),
    _row("tariff_welfare", "tariff_welfare", "Tariff welfare", "trade_policy",
         [r"tariff", r"import duty"],
         ("Policy Impact", "Tariff Welfare"), priority=14),
    # ---- economics: trade and international ------------------------------
    _row("comparative_advantage", "comparative_advantage", "Comparative advantage", "trade_advantage",
         [r"comparative advantage", r"opportunity cost of (?:good|production)"],
         ("Economic Context", "Comparative Advantage"), priority=12),
    _row("exchange_rate_ppp", "exchange_rate_ppp", "Purchasing-power parity", "parity",
         [r"purchasing[- ]power parity", r"\bppp\b"],
         ("Economic Context", "Purchasing-Power Parity"), priority=15),
    _row("interest_rate_parity", "interest_rate_parity", "Interest-rate parity", "parity",
         [r"interest[- ]rate parity", r"covered interest"],
         ("Economic Context", "Interest-Rate Parity"), priority=15),
    _row("balance_of_payments", "balance_of_payments", "Balance of payments", "external_accounts",
         [r"balance of payments", r"current account", r"financial account"],
         ("Economic Context", "Balance of Payments"), priority=12),
    _row("hdi", "hdi", "Human development index", "development",
         [r"human development", r"\bhdi\b", r"life expectancy.{0,40}schooling"],
         ("Economic Context", "Human Development Index"), priority=12),
    # ---- economics: decision and evidence --------------------------------
    _row("expected_utility", "expected_utility", "Expected utility", "decision_under_risk",
         [r"expected utility", r"certainty equivalent", r"risk premium"],
         ("Data Analysis", "Expected Utility"), priority=18),
    _row("prospect_theory", "prospect_theory", "Prospect theory", "decision_under_risk",
         [r"prospect theory", r"loss aversion"],
         ("Data Analysis", "Prospect Theory"), priority=20),
    _row("difference_in_differences", "difference_in_differences", "Difference-in-differences", "relationship_model",
         [r"difference[- ]in[- ]differences", r"\bdid\b estimate"],
         ("Data Analysis", "Difference-in-Differences"), priority=18),
    _row("instrumental_variables", "instrumental_variables", "Instrumental variables", "relationship_model",
         [r"instrumental variable", r"\b2sls\b"],
         ("Data Analysis", "Instrumental Variables"), priority=20),
    _row("panel_regression", "panel_regression", "Panel regression", "relationship_model",
         [r"panel (?:data|regression)", r"fixed effects"],
         ("Data Analysis", "Panel Regression"), priority=22),
    _row("regression_discontinuity", "regression_discontinuity", "Regression discontinuity", "relationship_model",
         [r"regression discontinuity", r"\brdd\b"],
         ("Data Analysis", "Regression Discontinuity"), priority=22),
    _row("probit", "probit", "Probit model", "relationship_model",
         [r"\bprobit\b", r"binary (?:outcome|choice) model"],
         ("Data Analysis", "Probit Model"), priority=15),
    # ---- project management: schedules -----------------------------------
    _row("cpm_schedule", "cpm_schedule", "Critical path", "schedule",
         [r"critical path", r"\bcpm\b", r"float (?:of|on) the activities"],
         ("Delivery Status", "Critical Path"),
         needs_any=[r"activit|duration|predecessor"], priority=15,
         row_fields={"activities": ["id", "duration", "predecessors"]}),
    _row("resource_leveling", "resource_leveling", "Resource levelling", "schedule",
         [r"resource level", r"overallocat", r"levell?ing"],
         ("Delivery Status", "Resource Levelling"),
         needs_any=[r"activit|resource|capacit"], priority=15,
         row_fields={"activities": ["id", "duration", "resource", "demand", "predecessors"],
                     "resources": ["name", "capacity"]}),
    _row("project_crashing", "project_crashing", "Project crashing", "schedule",
         [r"project crash", r"crash(?:ing)? the (?:project|schedule)", r"compress the schedule"],
         ("Delivery Status", "Project Crashing"),
         needs_any=[r"activit|duration|crash"], priority=15,
         row_fields={"activities": ["id", "normal_duration", "crash_duration", "crash_cost",
                                    "predecessors"]}),
    _row("schedule_risk", "schedule_risk", "Schedule risk", "schedule",
         [r"schedule risk", r"\bpert\b", r"probability of finishing"],
         ("Delivery Status", "Schedule Risk"),
         needs_any=[r"activit|optimistic|pessimistic|duration|three[- ]point|estimat"], priority=15,
         row_fields={"activities": ["id", "optimistic", "most_likely", "pessimistic",
                                    "predecessors"]}),
    _row("calendar_schedule", "calendar_schedule", "Calendar schedule", "schedule",
         [r"calendar (?:schedule|days)", r"working (?:days|periods)", r"working-day"],
         ("Delivery Status", "Calendar Schedule"),
         needs_any=[r"activit|working|calendar|duration"], priority=12,
         row_fields={"activities": ["id", "duration", "predecessors"]}),
    _row("multi_criteria", "multi_criteria", "Weighted decision matrix", "decision_matrix",
         [r"multi[- ]criteria", r"weighted decision matrix", r"decision matrix", r"score the options"],
         ("Delivery Status", "Weighted Decision Matrix"),
         needs_any=[r"criteria|weights?|alternatives?|options?|scores?"], priority=15,
         row_fields={"criteria": ["name", "weight"], "alternatives": ["name", "scores"]}),
    _row("monte_carlo", "monte_carlo", "Monte Carlo range", "simulation",
         [r"monte carlo", r"simulat(?:e|ion) the (?:range|outcome)", r"probability distribution of"],
         ("Delivery Status", "Monte Carlo Range"),
         priority=15,
         row_fields={"cashflows": ["name", "period", "distribution", "value", "low", "mode", "high"],
                     "variables": ["name", "distribution", "value", "low", "mode", "high"]}),
    _row("decision_tree", "decision_tree", "Decision tree", "decision_tree",
         [r"decision tree", r"expected value of the (?:options|alternatives)", r"chance node"],
         ("Delivery Status", "Decision Tree"),
         needs_any=[r"decision|alternatives?|chance|probabilit"], priority=15,
         row_fields={"tree": ["name", "value", "branches"]}),
    _row("multi_project_schedule", "multi_project_schedule", "Multi-project schedule", "multi_project",
         [r"multi[- ]project", r"several projects", r"shared resources across projects"],
         ("Delivery Status", "Multi-Project Schedule"),
         needs_any=[r"projects?|resources?|capacit"], priority=15,
         row_fields={"projects": ["name", "priority", "activities"],
                     "resources": ["name", "capacity"]}),
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
    if enabled:
        # a capability may only be added where it fits the paper; a drop is always
        # allowed, because excluding something is the student's decision, recorded.
        if framework and framework not in entry_row["applies_to"]:
            raise ValueError(entry_row["label"] + " does not fit a " + framework + " paper.")
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


def _canonical(value):
    """A method's output as an input a person could read: 0.09, not 0.0900000000."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    return format(number.normalize(), "f")


def dependencies(selection, computations=None):
    """The inputs that a selected capability can take from another one.

    Returns one row per (capability, input) pair: where the figure can come from,
    whether that source capability is in this paper, and the value the source has
    actually produced (only from a recorded, successful run).  An offer, not a
    substitution: the caller may use the value or declare its own.
    """
    computations = computations or {}
    selected = [row["key"] for row in (selection or {}).get("selected") or []]
    rows = []
    for key in selected:
        for name, (source, output, why) in sorted((NEEDS_FROM.get(key) or {}).items()):
            data = computations.get(source) or {}
            value = (data.get("result") or {}).get(output) if data.get("ok") else None
            try:
                source_label = ENTRIES[source]["label"]
            except KeyError:
                source_label = source.replace("_", " ")
            rows.append({"key": key, "input": name, "from": source, "output": output,
                         "from_label": source_label, "why": why, "selected": source in selected,
                         "recorded": value is not None,
                         "value": None if value is None else _canonical(value)})
    return rows


ENTRY_INTENT = {key: row["intent"] for key, row in ENTRIES.items()}
ENTRY_PRIORITY = {key: row["priority"] for key, row in ENTRIES.items()}
