"""Framework, model, quantitative-method and theory registry (Build Charter Stage 6; catalogue v0.2).
Recommendations are suggestions, never automatic applications. The registry holds no claims about evidence beyond 'unreviewed'."""
import json, math, os, re
from .artifacts import sha

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "registry_v0_2.json")
TYPE_LABEL = {"F": "framework", "M": "diagnostic model", "Q": "quantitative method", "T": "supporting theory"}
EVIDENCE_STATUS = {"unreviewed", "source_checked", "reviewed", "disputed", "validated"}
PIPELINE_STATUS = {"catalogued", "specified", "prototyped", "tested", "approved", "deprecated"}   # charter 5.2 vocabulary (see decision B-023)

# [PROVISIONAL] routing policy: declared, versioned and part of the registry hash. Tuned on tests/fixtures/framework_requests.json only.
POLICY = {"status": "PROVISIONAL", "max_framework_suggestions": 4, "max_quant_suggestions": 2, "max_theory_suggestions": 2, "max_selected": 6, "min_score": 6.0, "min_concepts": 2, "q_single_min": 12.0, "relative_cutoff": 0.5,
          "weights": {"name": 3.0, "structures": 2.0, "discipline": 1.0, "evidence": 1.0}}

# Curated routing aid: groups of words treated as the same concept when matching a request to catalogue text. [PROVISIONAL]
SYNONYMS = [
    "compete competitor competition rival rivalry competitive", "customer client buyer consumer user patron shopper", "staff employee worker workforce personnel talent",
    "change transition transformation restructure reorganization", "risk hazard uncertainty failure", "strategy strategic positioning", "growth expand expansion scale",
    "product service offering", "decision choose choice option alternative", "process workflow procedure operational",
    "quality defect error", "supplier vendor procurement supply", "performance kpi metric measure indicator scorecard", "environment external macro",
    "startup venture entrepreneur", "price pricing", "profit profitability margin", "cost expense spending", "forecast projection predict", "invest investment capital",
]
STOP = set("a an the and or of to in on for with by at from as is are was were be been it its this that these those we our us you your i my me they their them not no do does did can could should would will may might have has had how what when where which who why if then than so such about into over under between among after before during each per via also more most much many some any other another own same very".split())

# Phrases in requests that the catalogue writes as acronyms or hyphenated terms. [PROVISIONAL routing aid]
EXPAND = [(r"net present value", "npv"), (r"internal rate of return", "irr"), (r"break[ -]even", "break-even"), (r"t[ -]tests?", "t-test"), (r"discounted cash flow", "npv dcf"),
          (r"cost[- ]benefit", "cost-benefit"), (r"customer lifetime value", "clv"), (r"a/b test(s|ing)?", "a/b")]
# Generic words that should not count as evidence of a topic on their own (half-weight, never a distinct concept). [PROVISIONAL]
WEAK = set("capital value point time rate flow cash level order group case model system plan process analysis analyze evaluate compare calculate describe explain identify design assess need needs help manage management new use using based factor factors affect affecting relate".split())

def _stem(w):
    w = w.lower()
    if len(w) > 4 and w.endswith("ies"): return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"): return w[:-3]
    if len(w) > 4 and w.endswith("ed"): return w[:-2]
    if len(w) > 4 and w.endswith("es"): return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"): return w[:-1]
    return w

_SYN = {}
for _i, _g in enumerate(SYNONYMS):
    for _w in _g.split(): _SYN[_stem(_w)] = f"~{_i}"

def tokens(text):
    out = {}
    for pat, rep in EXPAND: text = re.sub(pat, rep, text or "", flags=re.I)
    for w in re.findall(r"[A-Za-z][A-Za-z\-']+", text or ""):
        if w.lower() in STOP or len(w) < 3: continue
        s = _stem(w.strip("-'")); s = _SYN.get(s, s); out.setdefault(s, w.lower())
    return out        # stem-or-concept -> first original word

# Maps catalogue Q bullets to implemented, tested methods in bp.methods. Coverage is always stated; most items stay uncovered.
METHOD_LINK_RULES = [
    (r"^Capital budgeting:",
     ["npv", "irr", "discounted_payback", "project_metrics"],
     "NPV, IRR, discounted payback, the profitability index, MIRR, simple payback and the equivalent annual annuity "
     "are implemented; unequal-life ranking rules and real options are not implemented"),
    (r"^Cost and profitability:",
     ["breakeven", "multi_product_breakeven", "abc_costing", "sales_variances"],
     "single-product and multi-product break-even, activity-based costing and sales price/mix/yield variances are "
     "implemented; operating-leverage, relevant-cost and make-or-buy analysis are not implemented"),
    (r"^Financial performance:",
     ["ratio_analysis", "dupont_analysis", "working_capital"],
     "15 declared financial-statement ratios, the DuPont decomposition (three- and five-step), common-size ratios, "
     "one-period growth, multi-year trend analysis and the cash conversion cycle are implemented; industry benchmarks "
     "and restatements are not implemented"),
    (r"^Valuation and financing:",
     ["wacc", "capm", "dcf_valuation", "equity_bridge", "multiples_valuation", "bond_analysis"],
     "WACC, CAPM, discounted cash flow valuation, the enterprise-to-equity bridge, comparable multiples and bond "
     "pricing with duration are implemented; debt-capacity and real-option valuation are not implemented"),
    (r"^Management accounting:",
     ["management_accounts", "standard_cost_variances", "abc_costing"],
     "a declarative double-entry engagement is implemented (chart, opening balances, entries, schedules, trial "
     "balance, statements, routes for the cash flow, closing and bank reconciliation), together with material, "
     "labour and overhead standard-cost variances and activity-based costing; target, life-cycle and "
     "budget-variance topics named here are not implemented"),
    (r"^Unit economics:",
     ["unit_economics"],
     "contribution margin, acquisition payback and LTV/CAC are implemented; retention curves and cohort economics "
     "are not implemented"),
    (r"^Pricing and demand:",
     ["pricing_decision", "elasticity"],
     "cost-plus, target-margin, break-even and target-return prices are implemented, together with arc price "
     "elasticity between two observations; estimating a demand curve or willingness to pay is not implemented"),
    (r"^Market sizing \(TAM/SAM/SOM\)",
     ["market_sizing"],
     "top-down TAM, SAM and SOM from a declared population, spend and two shares are implemented; bottom-up "
     "segmentation, retrieved market data and a demand estimate are not implemented"),
    (r"^Market share, growth rates",
     ["growth_rate", "sales_funnel", "market_share"],
     "compound and period growth rates, market share with penetration and relative share, and stage-by-stage "
     "funnel conversion are implemented; market-data retrieval, an estimated competitor and funnel leakage across "
     "channels are not implemented"),
    (r"^Cohort retention",
     ["cohort_retention", "unit_economics", "clv_model"],
     "pooled cohort retention, churn, average lifetime, a single-rate LTV and a discounted customer lifetime value "
     "over a declared horizon are implemented; fitted survival curves, segment-level retention and expansion "
     "revenue are not implemented"),
    (r"^Demand forecasting",
     ["trend_forecast"],
     "a linear trend fit, forecast periods and a prediction interval are implemented; forecast-error measures, "
     "seasonality and backtesting are not implemented"),
    (r"^A/B test design",
     ["power_analysis", "ab_test_two_proportion"],
     "sample-size and power calculations, and a two-proportion comparison of two observed arms with its interval, "
     "are implemented; sequential or peeking-adjusted tests and more than two arms are not implemented"),
    (r"^Campaign performance and media efficiency",
     ["campaign_efficiency"],
     "click-through, cost per click and per thousand impressions, cost per acquisition, return on ad spend, "
     "advertising cost of sales and break-even return on ad spend are implemented from declared counts; platform "
     "reads, automated bidding, view-through and incrementality are not implemented"),
    (r"^Channel CAC, LTV and payback",
     ["channel_economics", "unit_economics"],
     "acquisition cost, payback, lifetime value and its ratio to acquisition cost by declared channel, with the "
     "blended acquisition cost and each channel's spend share, are implemented; shared-spend allocation, saturation "
     "and cross-channel incrementality are not implemented"),
    (r"^Attribution credit across touchpoints",
     ["attribution_split"],
     "first-click, last-click and linear shares are compared from declared credit counts, with the spread per "
     "channel; touchpoint logs, time-decay, position-based and data-driven models, and causal incrementality, are "
     "not implemented"),
    (r"^Two-proportion A/B test",
     ["ab_test_two_proportion", "power_analysis"],
     "the two-proportion comparison, its interval and the visitors each arm needs for a declared effect are "
     "implemented; sequential tests, more than two arms and causal claims are not implemented"),
    (r"^Email list health",
     ["email_list_health"],
     "list growth, unsubscribe and bounce rates, open and click rates, click-to-open and revenue per subscriber are "
     "implemented from declared counts; platform reads, deduplication, deliverability and consent are not implemented"),
    (r"^Social engagement and audience growth",
     ["social_engagement"],
     "engagement rate, frequency, cost per thousand impressions, cost per engagement, engagement per post and "
     "follower growth are implemented from declared counts; sentiment, bot filtering and sales attribution are not "
     "implemented"),
    (r"^Web traffic and conversion by channel",
     ["web_analytics"],
     "sessions, conversions, conversion rate, revenue per session and channel share are implemented, with organic "
     "click-through when impressions and clicks are declared; analytics-platform reads, cross-device identity and "
     "attribution windows are not implemented"),
    (r"^Customer groups based on recency, frequency and monetary value",
     ["rfm_scoring"],
     "quintile recency, frequency and monetary scores and the eleven named segments are computed from a declared "
     "customer list, with each segment's size and the mean scores; external benchmarks, clustering, segment "
     "stability over time and next-period value are not implemented"),
    (r"^Media planning",
     ["media_plan"],
     "reach, average frequency, gross impressions, gross rating points, cost per rating point, cost per thousand "
     "impressions and a combined reach under random duplication are computed from declared vehicles; measured "
     "audience overlap, effective frequency, scheduling and a recommended buy are not implemented"),
    (r"^Which touchpoints receive credit",
     ["attribution_split"],
     "first-click, last-click and linear shares are compared from declared credit counts, with the spread per "
     "channel; touchpoint logs, time-decay, position-based and data-driven models, holdouts and incrementality "
     "are not implemented"),
    (r"^The page or step to change",
     ["ab_test_two_proportion", "power_analysis"],
     "the two-proportion comparison, its interval and the sample each arm needs are implemented, with a separate "
     "sample-size and power method; sequential tests, more than two arms, qualitative research and a design "
     "recommendation are not implemented"),
    (r"^Customer profitability and contribution analysis",
     ["customer_profitability"],
     "revenue, declared cost, profit, margin and profit share by segment, with the totals, the profitable and "
     "unprofitable counts and a concentration count, are implemented; cost-allocation rules, fixed-cost absorption, "
     "customer-level profitability and significance tests are not implemented"),
    (r"^Data profiling, descriptive statistics", ["descriptive_stats"], "descriptive statistics for one variable only; cross-tabulation and visualization are not implemented"),
    (r"^Chi-square tests, t-tests, ANOVA",
     ["welch_t", "mann_whitney", "chi_square", "anova", "kruskal_wallis", "two_way_anova", "posthoc_pairwise",
      "paired_t", "one_sample_t"],
     "chi-square, Welch and Mann-Whitney, one-way and two-way ANOVA with Kruskal-Wallis, post-hoc pairwise, and "
     "paired and one-sample t-tests are implemented; ANCOVA is not implemented"),
    (r"^Correlation and regression",
     ["pearson", "spearman", "ols", "ols_robust", "logistic_regression"],
     "Pearson and Spearman correlation, OLS and robust OLS, and binary logistic regression are implemented; "
     "categorical predictors, interactions and non-linear terms are not implemented"),
    (r"^Sensitivity analysis, scenario analysis", ["npv", "scenario_analysis"],
     "decision-flip on the NPV discount rate and a declared low/high rate scenario are implemented; multi-input "
     "scenario analysis, Monte Carlo and expected-value decision trees are not implemented"),
    (r"^EOQ, reorder point, safety stock", ["inventory_policy"],
     "the economic order quantity, safety stock, reorder point and the annual ordering and holding cost are "
     "implemented; quantity discounts, variable lead times and multi-item constraints are not implemented"),
    (r"^Demand/lead-time forecasts", ["trend_forecast"],
     "a declared linear trend with an interval and an out-of-sample check is implemented; seasonal, causal and "
     "driver-based forecasts are not implemented"),
    (r"^Queueing models", ["queue_analysis", "capacity_analysis"],
     "a single-server M/M/1 queue and the multi-server M/M/c queue, with steady-state resource capacity and its "
     "bottleneck, are implemented; priorities, abandonment, scheduling and simulation are not implemented"),
    (r"^Throughput and constraint analysis", ["capacity_analysis", "queue_analysis"],
     "the bottleneck resource, its utilisation and the capacity gap are implemented; drum-buffer-rope scheduling "
     "and buffer management are not implemented"),
    (r"^Critical Path Method \(CPM\)", ["cpm_schedule"],
     "critical-path dates, total float, the critical path and a PERT expected duration with its variance are "
     "implemented; simulation is not implemented, and resource levelling, crashing and calendars are separate "
     "methods (`resource_leveling`, `project_crashing`, `calendar_schedule`) rather than part of this one"),
    (r"^Overall Equipment Effectiveness \(OEE\)", ["oee_analysis", "process_control"],
     "OEE from declared time and counts, an I-MR control chart and Cp/Cpk capability are implemented; the six big "
     "losses, subgroup charts, EWMA/CUSUM and measurement-system analysis are not implemented"),
    (r"common-cause and special-cause process variation", ["process_control"],
     "an I-MR control chart and Cp/Cpk capability are implemented; subgroup charts (X-bar/R, p, c, u), EWMA, "
     "CUSUM and measurement-system analysis are not implemented"),
    (r"^Cost.benefit and cost-effectiveness", ["cost_benefit", "cost_effectiveness"],
     "discounted cost-benefit (net present value and benefit-cost ratio) and cost-effectiveness (cost per unit of "
     "effect, incremental ratios and dominance) are implemented; non-market valuation, distributional weights and "
     "unmonetised effects are not implemented"),
    (r"^Discounting of costs and benefits", ["npv", "dcf_valuation"],
     "discounting of declared costs and benefits at a declared rate, with low/high-rate sensitivity, is implemented; "
     "a probabilistic sensitivity analysis over every valuation assumption is not implemented"),
    (r"^Difference-in-differences", ["difference_in_differences"],
     "a two-group, two-period difference-in-differences estimate with its standard error is implemented; parallel "
     "trends cannot be proven from the data, and staggered adoption, covariates and clustering are not implemented"),
    (r"^SROI-type estimates", ["sroi"],
     "a social return on investment ratio from declared benefits, investment and attribution inputs is implemented; "
     "deadweight, displacement and drop-off must be declared, and the result is assumption-sensitive"),
    # D-RES-01: these five records read "Method not built" while the page offers a
    # calculator for the area.  The rule states the part that ships and the part that
    # does not, so neither the registry nor the subject slice can deny a shipped method.
    (r"^Sampling, confidence intervals", ["power_analysis"],
     "power, sample size and the minimum detectable effect are implemented for one-sample and two-sample means; "
     "sampling design, confidence-interval planning and effect-size planning are not implemented"),
    (r"^Reliability assessment and factor analysis", ["reliability_alpha"],
     "Cronbach's alpha for internal consistency is implemented on complete item responses; factor analysis "
     "(exploratory or confirmatory) and test-retest reliability are not implemented"),
    (r"^Multiple-comparison correction", ["multiple_comparison", "missing_data_bounds"],
     "Holm and Bonferroni multiple-comparison correction and worst-case bounds for missing data are implemented; "
     "sensitivity analysis across missing-data assumptions and multiple imputation are not implemented"),
    (r"^Time-series forecasting", ["trend_forecast"],
     "a linear trend forecast with an out-of-sample backtest, a forecast interval and a drift statement is "
     "implemented; seasonal models, autoregressive (ARIMA) models and structural-break tests are not implemented"),
    (r"^Causal-inference designs", ["difference_in_differences", "regression_discontinuity",
                                    "instrumental_variables", "panel_regression"],
     "difference-in-differences, regression discontinuity, instrumental variables and panel regression are "
     "implemented on the Economics shelf, each with its identification assumptions disclosed; randomized "
     "experiments, matching and weighting are not implemented"),
]

TEMPLATE_LINKS = {"STR-07": "template_swot", "STR-18": "template_swot", "STR-01": "template_five_forces",
                  "STR-15": "template_business_model_canvas", "STR-16": "template_lean_canvas",
                  "STR-17": "template_value_proposition_canvas", "MKT-02": "template_marketing_plan",
                  "STR-06": "template_pestel", "STR-03": "template_value_chain", "STR-09": "template_ansoff",
                  "STR-13": "template_blue_ocean_errc", "STR-04": "template_activity_system_fit",
                  "STR-14": "template_scenario_planning", "STR-12": "template_strategic_group_map",
                  "STR-08": "template_vrio",
                  "PM-05": "template_project_charter", "PM-06": "template_risk_register",
                  "PM-09": "template_wbs", "PM-10": "template_raci",
                  "PM-01": "template_balanced_scorecard",
                  "PM-02": "template_strategy_map", "PM-03": "template_kpi_tree",
                  "PM-04": "template_okrs",
                  "PM-15": "template_stakeholder_plan", "PM-16": "template_lessons_learned",
                  "MKT-04": "template_customer_journey", "MKT-06": "template_kano",
                  "MKT-07": "template_servqual", "MKT-15": "template_paid_media_plan",
                  "MKT-18": "template_measurement_plan",
                  "OPS-02": "template_sipoc", "OPS-03": "template_value_stream_map",
                  "OPS-05": "template_a3", "OPS-06": "template_toc",
                  "OPS-01": "template_scor", "OPS-04": "template_5s",
                  "OPS-07": "template_root_cause", "OPS-08": "template_fmea",
                  "OPS-10": "template_kraljic", "OPS-11": "template_sop",
                  "OPS-12": "template_pdca",
                  "PPL-03": "template_job_characteristics", "PPL-02": "template_kirkpatrick",
                  "PPL-01": "template_amo", "PPL-05": "template_tuckman",
                  "PPL-04": "template_nine_box",
                  "CHG-01": "template_kotter", "CHG-12": "template_competing_values",
                  "CHG-11": "template_org_design",
                  # The change, strategy and marketing worksheets.  Each one was
                  # written for the catalogue id it is linked to here.
                  "CHG-02": "template_adkar", "CHG-03": "template_lewin",
                  "CHG-04": "template_mckinsey_7s", "CHG-05": "template_burke_litwin",
                  "CHG-06": "template_galbraith_star", "CHG-07": "template_theory_of_change",
                  "CHG-08": "template_logic_model", "CHG-09": "template_pdsa",
                  "CHG-10": "template_dmaic", "CHG-13": "template_mintzberg",
                  "CHG-15": "template_change_organization",
                  "STR-02": "template_generic_strategies", "STR-05": "template_porters_diamond",
                  "STR-10": "template_bcg", "STR-11": "template_ge_mckinsey",
                  "STR-19": "template_strategic_positioning",
                  "MKT-01": "template_stp", "MKT-03": "template_aida",
                  "MKT-05": "template_funnel", "MKT-08": "template_rfm",
                  "MKT-09": "template_tam", "MKT-10": "template_utaut",
                  "MKT-11": "template_brand_equity", "MKT-12": "template_stp_evidence",
                  "MKT-13": "template_digital_mix", "MKT-14": "template_seo_content",
                  "MKT-16": "template_email_crm", "MKT-17": "template_social_media",
                  "MKT-19": "template_attribution", "MKT-20": "template_cro",
                  "MKT-21": "template_marketing_automation"}

#: What the product can do with a record today.  Kept separate from the
#: catalogue's evidence vocabulary (all 140 records are still `unreviewed`):
#: this is a product fact, not a claim about the quality of the framework.
FORM_LABEL = {"computed": "computed method", "worksheet": "worksheet",
              "read_only": "read-only record", "theory": "supporting theory"}


def form(r):
    """The delivery form of a loaded record, derived from what actually exists."""
    if r["type"] == "T":
        return "theory"
    if r.get("template"):
        return "worksheet"
    if r.get("linked_methods"):
        return "computed"
    return "read_only"


def _implementation_status(r):
    """One honest sentence: what the product can do with this record today.

    A record can carry both a worksheet and a runnable method.  When it does,
    the sentence has to name both: saying only "partial" hides a worksheet the
    student can actually use, and saying only "worksheet" hides a method the
    student can actually run.
    """
    if r["type"] == "T":
        return "supporting theory: an interpretive lens, not a worksheet by design"
    worksheet = r.get("template")
    methods = r.get("linked_methods")
    if worksheet and methods:
        return ("worksheet available: structure and evidence audit only; the evidence is yours. "
                "A computed method is also registered for this record: " + methods[0]["note"])
    if methods:
        return "partial: " + methods[0]["note"]
    if worksheet:
        return "worksheet available: structure and evidence audit only; the evidence is yours"
    if r["type"] == "Q":
        return "not implemented"
    return "read-only record: no worksheet yet"

class RegistryError(ValueError): pass
_CACHE = {}

def load(path=DATA):
    if path in _CACHE: return _CACHE[path]
    raw = json.load(open(path, encoding="utf-8")); recs = raw["records"]
    for r in recs:
        r["linked_methods"] = []
        # A quantitative record may sit in a framework section (RFM is MKT-08), so the
        # link rules are tried for every record the catalogue types as Q, not only QNT ids.
        if r["type"] == "Q":
            for pat, methods, note in METHOD_LINK_RULES:
                if re.search(pat, r["summary"]): r["linked_methods"] = [{"method_id": m, "coverage": "partial", "note": note} for m in methods]
        r["template"] = TEMPLATE_LINKS.get(r["id"])
        r["form"] = form(r)
        r["implementation_status"] = _implementation_status(r)
    reg = {"schema_version": raw["schema_version"], "registry_version": raw["registry_version"], "source": raw["source"], "import_warnings": raw["import_warnings"], "records": recs,
           "policy": POLICY, "by_id": {}}
    for r in recs:
        reg["by_id"][r["id"]] = r
        for a in r["also_listed_as"]: reg["by_id"][a] = r
    reg["hash"] = sha({"records": recs, "policy": POLICY, "synonyms": SYNONYMS, "links": METHOD_LINK_RULES, "template_links": TEMPLATE_LINKS, "source": raw["source"]})
    # document statistics for scoring
    docs = {r["id"]: _fields(r) for r in recs}; df = {}
    for f in docs.values():
        for t in set().union(*f.values()): df[t] = df.get(t, 0) + 1
    reg["_docs"] = docs; reg["_idf"] = {t: math.log(1 + len(recs) / n) for t, n in df.items()}
    _CACHE[path] = reg; return reg

def _fields(r):
    return {"name": set(tokens(" ".join([r["name"]] + r["aliases"] + r["members"]))), "structures": set(tokens(r["summary"] + " " + r["structures"])),
            "discipline": set(tokens(" ".join(r["disciplines"]))), "evidence": set(tokens(r["evidence_needs"]))}

def validate(reg=None):
    reg = reg or load(); errs, seen = [], set()
    for r in reg["records"]:
        for k in ("id", "name", "type", "disciplines", "evidence_status", "pipeline_status", "source_ref", "version"):
            if not r.get(k): errs.append(f"{r.get('id')}: missing {k}")
        if r["id"] in seen: errs.append(f"duplicate id {r['id']}")
        seen.add(r["id"])
        if r["type"] not in TYPE_LABEL: errs.append(f"{r['id']}: bad type {r['type']}")
        if any(t not in TYPE_LABEL or t == r["type"] for t in r["secondary_types"]): errs.append(f"{r['id']}: bad secondary types")
        if r["evidence_status"] not in EVIDENCE_STATUS: errs.append(f"{r['id']}: bad evidence_status")
        if r["pipeline_status"] not in PIPELINE_STATUS: errs.append(f"{r['id']}: bad pipeline_status")
        for a in r["also_listed_as"]:
            if a in seen and a != r["id"] and a in {x["id"] for x in reg["records"]}: errs.append(f"{r['id']}: alias id {a} is also a record")
        if r.get("template"):
            from .templates import TEMPLATES
            if r["template"] not in TEMPLATES or r["id"] not in TEMPLATES[r["template"]]["registry_ids"]: errs.append(f"{r['id']}: template link {r['template']} is not consistent with the template's registry ids")
        if r["type"] == "T" and r["linked_methods"]: errs.append(f"{r['id']}: a theory cannot link to runnable methods")
        if r["type"] == "T" and r.get("template"): errs.append(f"{r['id']}: a theory cannot carry a worksheet template")
        if r.get("form") not in FORM_LABEL: errs.append(f"{r['id']}: bad form {r.get('form')}")
        if r["linked_methods"]:
            from .methods import LIBRARY
            for l in r["linked_methods"]:
                if l["method_id"] not in LIBRARY: errs.append(f"{r['id']}: links to missing method {l['method_id']}")
    return errs

def get(rid):
    reg = load()
    try: return reg["by_id"][rid]
    except KeyError: raise KeyError(f"unknown registry id {rid}")

def brief(r, **extra):
    return {"id": r["id"], "name": r["name"], "type": r["type"], "type_label": TYPE_LABEL[r["type"]], "secondary_types": r["secondary_types"], "disciplines": r["disciplines"],
            "structures": r["summary"], "evidence_needs": r["evidence_needs"], "evidence_status": r["evidence_status"], "pipeline_status": r["pipeline_status"],
            "form": r["form"], "form_label": FORM_LABEL[r["form"]],
            "implementation_status": r["implementation_status"], "template": r.get("template"), "linked_methods": r["linked_methods"], "also_listed_as": r["also_listed_as"],
            "verify_edition_and_permissions": r.get("verify_edition_and_permissions", False), "limitations": r["limitations"], **extra}

def _score(reg, qtok, r):
    f, idf, w = reg["_docs"][r["id"]], reg["_idf"], reg["policy"]["weights"]; s, hits = 0.0, {}
    for t, word in qtok.items():
        best = max(((w[k], k) for k in f if t in f[k]), default=None)
        if not best: continue
        weak = word in WEAK or _stem(word) in WEAK
        s += idf.get(t, 1.0) * best[0] * (0.4 if weak else 1.0)
        if not weak: hits[word] = best[1]          # only non-generic words count as distinct concepts
    return s, hits

def _norm_text(t): return " " + re.sub(r"[^a-z0-9]+", " ", t.lower()).strip() + " "

def named_in(text):
    reg = load(); nt = _norm_text(text); found = []
    for r in reg["records"]:
        cands = [r["name"], *r["aliases"], *r["members"]]
        cands += [re.sub(r"\([^)]*\)", "", r["name"]).strip()]
        for c in cands:
            n = _norm_text(c).strip()
            if len(n) >= 3 and f" {n} " in nt and r["type"] != "Q": found.append((r, c)); break
    return found

def search(q, type=None, limit=10):
    reg = load(); qtok = tokens(q); out = []
    if not qtok: return out
    nq = _norm_text(q)
    for r in reg["records"]:
        if type and r["type"] != type: continue
        s, hits = _score(reg, qtok, r)
        if any(f" {_norm_text(c).strip()} " in nq for c in [r["name"], *r["aliases"]] if len(c) >= 3): s += 20
        if s > 0: out.append((s, r["id"], r, hits))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [brief(r, score=round(s, 2), matched_terms=sorted(h)) for s, _, r, h in out[:limit]]

def recommend(text):
    reg = load(); pol = reg["policy"]; qtok = tokens(text); scored = {"FM": [], "Q": [], "T": []}
    for r in reg["records"]:
        s, hits = _score(reg, qtok, r)
        if s > 0: scored["Q" if r["type"] == "Q" else "T" if r["type"] == "T" else "FM"].append((s, r["id"], r, hits))
    named = named_in(text); named_ids = {r["id"] for r, _ in named}
    def pick(items, cap, floor):
        items.sort(key=lambda x: (-x[0], x[1]))
        # admissible only if at least two distinct concepts match; a single stray word is not evidence (exact names are handled by named_in)
        items = [i for i in items if i[0] >= floor and i[1] not in named_ids and (len(i[3]) >= pol["min_concepts"] or (i[2]["type"] == "Q" and len(i[3]) >= 1 and i[0] >= pol["q_single_min"]))]
        return [i for i in items if items and i[0] >= pol["relative_cutoff"] * items[0][0]][:cap]
    def why(r, hits, kind):
        terms = ", ".join(sorted(hits)); what = r["summary"] or r["name"]
        return f"Suggested because your request mentions {terms}, which this {TYPE_LABEL[r['type']]} addresses: {what}"
    def build(items): return [brief(r, score=round(s, 2), matched_terms=sorted(h), why=why(r, h, r["type"]), status="suggested") for s, _, r, h in items]
    out = {"frameworks": build(pick(scored["FM"], pol["max_framework_suggestions"], pol["min_score"])), "quantitative": build(pick(scored["Q"], pol["max_quant_suggestions"], pol["min_score"])),
           "theories": build(pick(scored["T"], pol["max_theory_suggestions"], pol["min_score"] * 0.8))}
    for r in out["theories"]: r["why"] += ". A theory informs interpretation; it is not an analysis template. Retrieve the original research and cite it."
    nm = []
    for r, matched in named:
        own = set(tokens(" ".join([r["name"], *r["aliases"]]))); s, hits = _score(reg, {t: w for t, w in qtok.items() if t not in own}, r)   # fit is judged on the rest of the request, not on the name itself
        fit = "Named in your request." if s >= pol["min_score"] * 0.5 and hits else "Named in your request, but nothing else in it clearly points to this item; confirm that it addresses your question."
        nm.append(brief(r, score=round(s, 2), matched_terms=sorted(hits), why=fit, status="named_by_user"))
    out["named"] = nm
    out["none_reason"] = None if (out["frameworks"] or out["quantitative"] or nm) else "No catalogued framework or method fits this request well enough to suggest one. Proceed without a named framework, or search the library."
    out["policy"] = pol; out["registry"] = {"version": reg["registry_version"], "catalogue_version": reg["source"]["catalogue_version"], "hash": reg["hash"]}
    return out

def selection_records(ids):
    """Validate user-chosen ids. Returns records in the order given; raises on unknown ids."""
    out, seen = [], set()
    for i in ids:
        r = get(i)
        if r["id"] not in seen: seen.add(r["id"]); out.append(r)
    return out

def framework_only_report(selected, objective=""):
    """T4 output: how to think about it and what data is needed. No computed answer (manual 5.3)."""
    lines = ["No computed answer is given. This is a framework-only (T4) response: how to structure the question and what evidence or data is needed."]
    fw = [r for r in selected if r["type"] in ("F", "M")]; q = [r for r in selected if r["type"] == "Q"]; th = [r for r in selected if r["type"] == "T"]
    if not selected: lines.append("No framework was selected. Describe the decision, the data you hold, and the output you need, or choose one from the library.")
    for r in fw:
        lines.append(f"{r['name']} ({TYPE_LABEL[r['type']]}): structures {r['summary']}. Evidence and data needed: {r['evidence_needs'] or 'not specified in the catalogue'}.")
        if r.get("verify_edition_and_permissions"): lines.append(f"Before relying on {r['name']}, verify the current edition and permitted use.")
    for r in q:
        impl = r["implementation_status"]; ids = ", ".join(l["method_id"] for l in r["linked_methods"])
        lines.append(f"Quantitative method: {r['summary']} Pipeline status: {impl}" + (f" (available: {ids})." if ids else "."))
    for r in th:
        lines.append(f"Supporting theory ({r['name']}): use to interpret evidence, not as a template; retrieve the original research or a reliable synthesis, state what it explains and note its limitations.")
    lines.append("Frameworks organize the analysis; they do not by themselves prove which course of action will work, and any scores or weights are measurement choices that need justification.")
    return " ".join(lines)


def evaluate(cases):
    """Run fixture cases; returns per-case pass/fail with reasons (used by tests and by documentation)."""
    res = []
    for c in cases:
        r = recommend(c["text"]); fw = [x["id"] for x in r["frameworks"]]; q = [x["id"] for x in r["quantitative"]]; nm = [x["id"] for x in r["named"]]; th = [x["id"] for x in r["theories"]]
        why = []
        if c.get("expect_framework_any") and not set(c["expect_framework_any"]) & set(fw): why.append(f"expected one of {c['expect_framework_any']} in frameworks, got {fw}")
        if c.get("expect_quant_any") and not set(c["expect_quant_any"]) & set(q): why.append(f"expected one of {c['expect_quant_any']} in quantitative, got {q}")
        if c.get("expect_linked_methods_any"):
            linked = {l["method_id"] for x in r["quantitative"] for l in x["linked_methods"]}
            if not set(c["expect_linked_methods_any"]) & linked: why.append(f"expected linked methods {c['expect_linked_methods_any']}, got {sorted(linked)}")
        if c.get("expect_named_all") and not set(c["expect_named_all"]) <= set(nm): why.append(f"expected named {c['expect_named_all']}, got {nm}")
        if c.get("expect_named_any") and not set(c["expect_named_any"]) & set(nm + th): why.append(f"expected {c['expect_named_any']} named or as theory, got {nm + th}")
        if c.get("forbid_in_frameworks") and set(c["forbid_in_frameworks"]) & set(fw): why.append("a theory was offered as a framework template")
        if c.get("expect_none") and (fw or q or nm or th): why.append(f"expected no suggestion, got {fw + q + nm + th}")
        res.append({"id": c["id"], "split": c["split"], "passed": not why, "reasons": why})
    return res
