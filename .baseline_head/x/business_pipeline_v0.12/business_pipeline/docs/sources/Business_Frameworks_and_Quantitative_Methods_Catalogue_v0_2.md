# Smart Researcher
## Curated Business Frameworks and Quantitative Methods Catalogue

**Version:** 0.4  
**Date:** October 28, 2026  
**Status:** Living catalogue — candidate inventory, not an implementation commitment  
**Scope:** Business and related disciplines, including the quantitative methods needed to apply frameworks rigorously

---

## 1. Purpose

This catalogue identifies structured frameworks, operational models, and calculation techniques that may help the business pipeline analyze cases, diagnose problems, compare alternatives, design interventions, and evaluate results.

The goal is not to store every management theory. The goal is to maintain a curated set of reusable analytical structures that the pipeline can recognize and apply when they fit a user's problem.

**Important:** Inclusion here means a method is a candidate for structured use; it does not mean that it is scientifically proven, universally applicable, or ready for automatic use. Each item still needs source checking, scope limits, evidence review, and evaluation on appropriate cases.

## 2. Inclusion rules and taxonomy

Use these labels consistently:

| Label | Category | Include when... | Example |
|---|---|---|---|
| **F — Framework / structured process** | A repeatable set of dimensions, steps, questions, or outputs organizes the analysis. | It can guide a user or pipeline through a recognizable sequence or fixed sections. | Porter's Five Forces, PESTEL, Kotter's 8-Step Model, DMAIC |
| **M — Operational model / diagnostic tool** | A defined set of constructs, categories, relationships, or indicators supports diagnosis, classification, or measurement. | It can produce a structured assessment, and the limits of that assessment can be stated. | VRIO, Kano Model, SERVQUAL, DeLone–McLean IS Success Model |
| **Q — Quantitative / calculation method** | It uses data, formulas, statistical estimation, simulation, or optimization to calculate or compare outcomes. | It supplies numerical evidence required by a framework or answers a quantitative business question. | NPV, regression, EOQ, Monte Carlo simulation |
| **T — Supporting theory / explanatory lens** | It primarily explains behavior or relationships but does not, by itself, prescribe a repeatable analysis structure. | It is useful background for interpretation but does not warrant a default pipeline template. | Transformational leadership theory, agency theory, self-determination theory |

### Rule for the core library

The core library should prioritize **F** items and carefully selected **M** items. **Q** methods belong in a connected methods catalogue because frameworks often need calculations. **T** theories are not core entries by default; they may be retrieved from the knowledge base when they help explain a case, interpret evidence, or justify a hypothesis.

A theory can inform a framework without becoming a separate operational template. For example, the Resource-Based View can inform strategy discussion, while VRIO gives the pipeline a structured set of questions about value, rarity, imitability, and organization. Similarly, transformational leadership can inform a discussion of a manager's behavior, but it should not automatically trigger a fixed leadership-analysis template.

### Do not confuse these categories

- A framework is not automatically a validated predictive model.
- A model with a fixed set of constructs is not necessarily a full methodology.
- A formula is not a framework, even when it is essential to the analysis.
- An attractive matrix or score does not make a judgment objective. Criteria, weights, assumptions, and data quality must be visible.
- A named framework should not be forced onto every problem. The pipeline should select it only when it fits the user's question.

---

## 3. Strategy, competition, and business models

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| STR-01 | Porter's Five Forces | F | Industry rivalry, threat of entrants and substitutes, buyer power, supplier power | Market structure, competitor evidence, switching costs, industry economics; mostly qualitative unless data are available |
| STR-02 | Porter's Generic Strategies | F | Cost leadership, differentiation, and focus choices | Cost position, willingness to pay, segment economics, evidence of trade-offs |
| STR-03 | Porter's Value Chain | F | How primary and support activities contribute to cost or differentiation | Activity costs, margin/cost drivers, process data where available |
| STR-04 | Porter's Strategic Positioning / Activity-System Fit | F | The chosen position and fit among the activities supporting it | Competitor comparisons and evidence of mutually reinforcing activities |
| STR-05 | Porter's Diamond | F | National/industry competitiveness through factor conditions, demand conditions, related industries, and firm rivalry/context | Industry, trade, workforce, supplier, demand and policy data where relevant |
| STR-06 | PESTEL | F | Political, economic, social, technological, environmental and legal context | Dated, cited external evidence; identify uncertainty and time horizon |
| STR-07 | SWOT / TOWS | F | Internal strengths/weaknesses and external opportunities/threats; TOWS turns them into options | Evidence for each item; strategic options must follow from the analysis rather than be generic |
| STR-08 | VRIO | M | Whether a resource/capability is valuable, rare, hard to imitate, and organizationally supported | Evidence about resources, competitors, imitation, and organizational use; avoid unsupported yes/no scoring |
| STR-09 | Ansoff Matrix | F | Market penetration, market development, product development, diversification | Growth potential, risks, capability requirements, market/customer evidence |
| STR-10 | BCG Growth-Share Matrix | M | Portfolio positioning using market growth and relative market share | Definitions and estimates of market growth and relative share; disclose boundaries and limitations |
| STR-11 | GE–McKinsey Portfolio Matrix | M | Portfolio assessment using industry attractiveness and business strength | Explicit criteria and weights; sensitivity to scoring and weight changes |
| STR-12 | Strategic Group Mapping | M | Competitor groups by selected strategic dimensions | Comparable competitor data; axis choice must be justified |
| STR-13 | Blue Ocean Strategy Canvas / ERRC Grid | F | Current competitive factors and possible eliminate-reduce-raise-create choices | Customer evidence, competitor benchmarks, cost and value hypotheses; validate with customers |
| STR-14 | Scenario Planning | F | Several plausible futures, their drivers, implications, and robust choices | Sources for drivers, scenario assumptions, sensitivity analysis; scenarios are not forecasts |
| STR-15 | Business Model Canvas | F | Nine connected business-model blocks covering customers, value, delivery, resources, activities, partners, costs and revenue | Customer evidence, revenue logic, cost estimates, and consistency across blocks |
| STR-16 | Lean Canvas | F | Startup problem, customer, value proposition, solution, channels, revenue/cost, metrics and advantage assumptions | Customer validation, unit economics, explicit hypotheses |
| STR-17 | Value Proposition Canvas | F | Customer jobs, pains and gains compared with pain relievers and gain creators | Customer interviews/observations and validation; a canvas is a hypothesis, not proof of product-market fit |
| STR-18 | SWOT evidence-to-action review | F | Audit each SWOT item for evidence, materiality, and resulting strategic options | Evidence traceability and prioritization; use as a quality layer on SWOT/TOWS, not a separate theory |
| STR-19 | Strategic positioning review | F | The place claimed in the market, the difference it rests on, the value promised and the segment it is aimed at | Evidence that the difference is valued by the segment and that the segment is reachable; a positioning claim is a hypothesis to test |
| STR-20 | Strategy framework: perspective, position, plan and pattern | F | A strategy read through its perspective, the position it claims, the plan that delivers it and the pattern of behaviour it creates | Evidence that the plan produces the intended pattern and that the position holds in the market; a strategy is read, not scored |

**Notes:** Porter's frameworks should be kept as separate entries because they answer different questions. SWOT, Five Forces, and the Value Chain should not be merged into one generic “strategy analysis.” A user may need one, several, or none of them.

---

## 4. Change, organization design, and implementation

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| CHG-01 | Kotter's 8-Step Change Model | F | A sequence for mobilizing, implementing and sustaining organizational change | Stakeholder evidence, progress measures, adoption and outcome indicators |
| CHG-02 | ADKAR | M | Individual change readiness/barriers: Awareness, Desire, Knowledge, Ability, Reinforcement | Employee input or structured assessment; avoid treating self-report scores as objective facts |
| CHG-03 | Lewin's Three-Stage Model | F | Unfreezing, changing and stabilizing new practices | Diagnosis of current norms, transition actions, reinforcement measures; use as a simplifying lens, not a universal law |
| CHG-04 | McKinsey 7-S | F | Alignment among strategy, structure, systems, shared values, skills, style and staff | Evidence across the seven dimensions and their alignment; no single score is inherently authoritative |
| CHG-05 | Burke–Litwin Organizational Performance and Change Model | M | Relationships among external environment, leadership, mission/strategy, culture, systems and performance | Organizational data and stakeholder evidence; causal relationships require caution |
| CHG-06 | Galbraith Star Model | F | Alignment of strategy, structure, processes, rewards and people practices | Operating model, roles, process and reward evidence |
| CHG-07 | Theory of Change | F | Causal pathway from activities to outputs, outcomes and impact, including assumptions | Outcome indicators, assumptions, contextual evidence, and evaluation design; links are hypotheses to test |
| CHG-08 | Logic Model | F | Inputs, activities, outputs, outcomes and impact | Measurable indicators, data sources, time horizons; distinguish activities from outcomes |
| CHG-09 | Plan–Do–Study–Act (PDSA) | F | Small, iterative tests of change | Baseline, defined prediction, measures, results, and decision for the next cycle |
| CHG-10 | DMAIC | F | Define, Measure, Analyze, Improve, Control for process/problem improvement | Baseline data, valid measures, root-cause evidence and control measures |
| CHG-11 | Organizational Design: Star/fit review | F | Check alignment among strategy, decision rights, structure, processes, people and incentives | Operating data and clear mapping of responsibilities |
| CHG-12 | Competing Values Framework | M | Organizational culture through competing value orientations | Survey/observation evidence; treat profiles as diagnostic, not immutable types |
| CHG-13 | Mintzberg Organizational Configurations | M | Compare organizational structure/configuration patterns | Evidence about coordination, key parts, decision authority and context |
| CHG-14 | RACI responsibility matrix | F | Responsible, Accountable, Consulted and Informed roles | Role clarity and stakeholder confirmation; usually no calculations required |
| CHG-15 | Change and organization review | F | The kind of change, the readiness of the organization, the points of resistance and the support the change needs | Evidence about readiness and resistance from the people affected and from comparable changes; no readiness score is computed |

**Scope note:** Theories about how people experience change (for example, Bridges' transition model) can be used as explanatory lenses when useful. They need not be separate core entries unless we define a reproducible diagnostic or intervention protocol around them.

---

## 5. Marketing, customers, and service design

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| MKT-01 | Segmentation–Targeting–Positioning (STP) | F | Customer segments, target selection, and desired market position | Segment size/profitability, needs and fit, competition, segment-selection criteria |
| MKT-02 | Marketing Mix: 4Ps / Services Mix: 7Ps | F | Product, Price, Place, Promotion; services add People, Process and Physical Evidence | Customer, competitor and cost evidence; price and channel economics as appropriate |
| MKT-03 | AIDA | M | Attention, Interest, Desire, Action as a simplified communication journey | Funnel/conversion data if available; avoid assuming all customers move linearly through stages |
| MKT-04 | Customer Journey Mapping | F | Customer goals, actions, touchpoints, experiences, pain points and opportunities | Interviews, observations, service logs, funnel metrics, customer feedback |
| MKT-05 | Marketing / Sales Funnel | M | Conversion through defined stages | Stage definitions, conversion rates, cohort/time windows, leakage analysis |
| MKT-06 | Kano Model | M | Product/service attributes by their relationship to customer satisfaction | Appropriate survey design and customer samples; classifications can vary by segment and time |
| MKT-07 | SERVQUAL | M | Service-quality assessment using defined dimensions and perception/expectation measures | Survey instrument, sampling and scoring choices; validity and context need review |
| MKT-08 | RFM Segmentation | Q/M | Customer groups based on recency, frequency and monetary value | Transaction data, window definitions, scoring method and checks for biased segments |
| MKT-09 | Technology Acceptance Model (TAM) | M | Perceived usefulness/ease of use and related technology-acceptance constructs | Validated scales and appropriate study design if used for empirical assessment |
| MKT-10 | UTAUT | M | Structured constructs associated with technology acceptance and use | Validated measurement scales and research design; not a generic checklist for all adoption problems |
| MKT-11 | Brand Equity Assessment | M | Selected dimensions of brand knowledge, associations, perceived quality and loyalty | Customer research and clearly defined measurement; choose a specified model rather than mixing variants |
| MKT-12 | STP-to-positioning evidence check | F | Check that target choice, customer evidence and positioning claim align | Research on target segments and competitive alternatives |
| MKT-13 | Digital marketing mix: owned, earned and paid channels | F | The channels you control, the channels others create and the channels you pay for, with the role and budget of each | Channel inventory, audience and reach evidence, cost data and a declared objective for each channel |
| MKT-14 | SEO and content marketing plan | F/M | The content that answers a search or customer question, the keywords it targets and the page that carries it | Keyword and search-demand evidence, page inventory, content calendar, ranking and traffic data |
| MKT-15 | Paid media plan: search, social and display | F/M | Campaign objective, audience, placement, budget and bid, by paid channel | Platform cost data, audience definitions, creative variants and a declared conversion definition |
| MKT-16 | Email, CRM and lifecycle marketing | M | List growth, segmentation, journey stages and the message sent at each stage | List and consent records, send/open/click counts, unsubscribe and bounce counts, revenue by journey |
| MKT-17 | Social media and influencer marketing | M | Owned posts, community activity and creator partnerships, with the metric each is judged on | Reach, engagement and follower data; creator terms, fees and disclosure requirements |
| MKT-18 | Web and app analytics measurement plan | F | The events, metrics and dimensions that make a journey measurable, and the question each answers | A defined event taxonomy, tool access, consent and data-quality checks |
| MKT-19 | Attribution and campaign measurement | Q/M | Which touchpoints receive credit, under which rule, and what the campaign changed | UTM discipline, touchpoint logs, conversion definitions, a declared attribution model and, for causality, a holdout or experiment |
| MKT-20 | Conversion-rate optimisation and landing-page testing | Q/M | The page or step to change, the hypothesis and the test that decides it | Baseline conversion counts, traffic split, test duration and a declared minimum detectable effect |
| MKT-21 | Marketing automation and lead scoring | F/M | The rules that move a lead between stages and the score that qualifies it | Lead-source and behaviour data, stage definitions (MQL/SQL), sales feedback and score validation |

**Supporting theories not core by default:** Diffusion of Innovations, consumer choice theory, and Jobs-to-Be-Done theory can inform market analysis. A structured JTBD interview protocol or adoption assessment may be catalogued as a method, but the explanatory theory alone does not automatically require a pipeline template.

---

## 6. Operations, process improvement, and supply chain

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| OPS-01 | SCOR Digital Standard | F/M | Supply-chain processes, capabilities and performance measures | Defined process scope, metrics, data definitions and benchmarks; verify the applicable version and permitted use |
| OPS-02 | SIPOC | F | Suppliers, Inputs, Process, Outputs, Customers | Process-owner confirmation, scope and customer requirements |
| OPS-03 | Value Stream Mapping | F | Material/information flow, delay, work-in-progress and value-adding/non-value-adding steps | Cycle time, lead time, inventory and process observations |
| OPS-04 | 5S | F | Sort, Set in order, Shine, Standardize, Sustain | Workplace observations, audit criteria and sustaining measures |
| OPS-05 | Lean problem-solving / A3 | F | Problem, current condition, target, cause, countermeasures, implementation and follow-up | Baseline and outcome measures; evidence that root causes were tested |
| OPS-06 | Theory of Constraints — Five Focusing Steps | F | Identify, exploit, subordinate, elevate and reassess the system constraint | Throughput, capacity, queue and bottleneck data; distinguish this procedure from the broader theory alone |
| OPS-07 | Root Cause Analysis: 5 Whys / Fishbone | F | Organize candidate causes and investigate contributing factors | Evidence testing each causal hypothesis; a diagram alone does not establish cause |
| OPS-08 | Failure Mode and Effects Analysis (FMEA) | M | Potential failure modes, effects, causes and controls | Severity/occurrence/detection criteria; score products are prioritization aids, not precise probabilities |
| OPS-09 | Statistical Process Control (SPC) | Q/M | Distinguish common-cause and special-cause process variation | Time-ordered observations, suitable control charts, stable-process assumptions |
| OPS-10 | Kraljic Purchasing Portfolio Matrix | M | Supplier categories based on supply risk and profit/impact | Purchasing-spend, supply risk and strategic-impact evidence; criteria must be defined |
| OPS-11 | Sales and Operations Planning (S&OP) | F | Reconcile demand, supply, inventory, capacity and financial plans | Forecasts, capacity and inventory data, scenario comparisons |
| OPS-12 | PDCA / PDSA | F | Iterative improvement cycle | Measures before and after intervention; see also change catalogue |

---

## 7. Risk, decision analysis, and governance

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| RSK-01 | ISO 31000 Risk Management Process | F | Establish context; identify, analyze, evaluate, treat, monitor and communicate risk | Risk criteria, evidence, owners, treatment plans and monitoring measures; check current edition before use |
| RSK-02 | COSO Enterprise Risk Management | F | Integrate risk with governance, strategy, performance and review | Strategy/objective mapping, risk appetite, ownership and performance evidence; use authoritative current materials |
| RSK-03 | Bow-Tie Analysis | F/M | Threats, preventive controls, top event, consequences and mitigative controls | Incident/engineering evidence; probability estimates only where supported |
| RSK-04 | Fault Tree Analysis | Q/M | Logical combinations of failures that can lead to a top event | System logic and failure probabilities if quantitative; assumptions must be explicit |
| RSK-05 | Stakeholder Analysis / Power–Interest Matrix | F | Identify stakeholders, interests, influence, impacts and engagement response | Source-supported stakeholder facts; power/interest classifications are judgments |
| RSK-06 | Materiality Assessment | F/M | Prioritize issues by their importance to affected stakeholders and/or enterprise impacts | Defined methodology, stakeholder evidence and current reporting requirements where applicable |
| RSK-07 | Red-Team / Premortem Review | F | Challenge a proposed plan and identify how it could fail | Independent reviewers, documented challenge prompts and resolutions |
| RSK-08 | Dialectical Inquiry / Devil's Advocate | F | Deliberately develop and test competing interpretations or strategies | Shared criteria, balanced evidence and explicit handling of unresolved disagreement |
| RSK-09 | Multi-Criteria Decision Analysis (MCDA) | F/Q | Compare options against criteria and explicit weights | Score definitions, weights, normalization, sensitivity analysis and user-owned value judgments |

**Critical guardrail:** A risk matrix or MCDA score must not turn subjective estimates into false precision. Where weights, probabilities or ratings are uncertain, show the impact of changing them.

---

## 8. Performance management, projects, and technology governance

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| PM-01 | Balanced Scorecard | F | Objectives and measures across financial, customer/stakeholder, internal-process and organizational-capacity perspectives | Strategy-linked metrics, targets, initiatives, time windows and data owners |
| PM-02 | Strategy Map | F | Hypothesized links among strategic objectives and outcomes | Evidence for causal links; describe these as hypotheses until tested |
| PM-03 | KPI Tree / Driver Tree | F | Link a top-level outcome to measurable drivers and sub-drivers | Metric definitions, decomposition checks and source lineage |
| PM-04 | Objectives and Key Results (OKRs) | F | Objectives and measurable key results over a defined period | Baselines, targets, owners, measurement cadence and gaming risks |
| PM-05 | PRINCE2 | F | Project governance, roles, stages, business justification, controls and tailoring | Project evidence and governance decisions; use an appropriate, authorized level of detail |
| PM-06 | PMBOK / PMI project management standards | F/reference standard | Project-management knowledge areas, principles and performance domains depending on edition | Version-specific guidance; it is not one fixed universal checklist |
| PM-07 | Scrum | F | Defined accountabilities, events, artifacts and empirical product-development cycle | Sprint goals, increments, backlog and outcome evidence |
| PM-08 | Kanban Method | F | Visualize workflow, manage work in progress, control flow and improve delivery | Work-item and flow data; lead time, throughput and WIP measures when suitable |
| PM-09 | Work Breakdown Structure (WBS) | F | Break down project scope into manageable deliverables/work packages | Scope statement and deliverable acceptance criteria |
| PM-10 | RACI / responsibility assignment | F | Clarify responsibility and accountability | Confirmed roles and decision rights |
| PM-11 | COBIT | F/reference framework | Governance and management of enterprise information and technology | Current version, objectives, capability measures and organizational context |
| PM-12 | ITIL | F/reference framework | IT service management practices and service value system | Service outcomes, incidents, service levels and operational data; apply the appropriate version |
| PM-13 | DeLone–McLean IS Success Model | M | Relationships among system quality, information quality, use, satisfaction and net benefits | Defined constructs and validated measures; causal interpretations require suitable evidence |
| PM-14 | Technology-Organization-Environment (TOE) Framework | F | Technology, organizational and environmental context for adoption decisions | Evidence for each context dimension; not a universal numerical score |
| PM-15 | Stakeholder engagement and communication plan | F | Who is affected, what each stakeholder needs, and how, when and by whom the project will communicate with them | Confirmed stakeholders, interests, influence, messages, channels, frequency and owners |
| PM-16 | Lessons learned | F | What worked, what did not, why, and what the next project should change | Project records, incident and change evidence, and the people who did the work |

---

## 9. People, talent, and learning: only operationalized entries

Keep this section narrower than a textbook of organizational behavior. Standalone leadership and motivation theories are supporting knowledge, not default case templates.

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| PPL-01 | Ability–Motivation–Opportunity (AMO) Framework | F/M | Diagnose whether performance constraints relate to ability, motivation or opportunity to contribute | Job and performance evidence; categories should lead to testable interventions |
| PPL-02 | Kirkpatrick Training Evaluation Model | M | Training evaluation across reaction, learning, behavior and results | Baselines, appropriate follow-up intervals and outcome measures; satisfaction is not proof of learning or impact |
| PPL-03 | Job Characteristics Model | M | Job design through skill variety, task identity, task significance, autonomy and feedback | Job analysis and validated measures if scores are used |
| PPL-04 | Nine-Box Talent Grid | M | Structured discussion of performance and potential | Consistent criteria, calibration and bias safeguards; not an objective measure of future success |
| PPL-05 | Team development review using Tuckman's stages | M — optional | Organize discussion of team development and possible needs | Use only as a reflective heuristic; do not assume all teams pass through fixed stages |

**Not core entries by default:** Transformational leadership theory; Maslow's hierarchy; Herzberg's Two-Factor Theory; McClelland's needs theory; expectancy and equity theories; self-determination theory; social identity theory; psychological-contract theory; servant leadership; and authentic leadership. Retrieve these when they help explain a specific problem. Promote a derived diagnostic into the core only after specifying its questions, measures, evidence base and evaluation method.

---

## 10. Public, nonprofit, and impact evaluation

| ID | Item | Type | What it structures | Calculation or evidence needs |
|---|---|---|---|---|
| IMP-01 | Theory of Change | F | Causal pathway, assumptions, contextual factors and intended outcomes/impact | Outcomes, indicators and evaluation design; pathways are hypotheses |
| IMP-02 | Logic Model | F | Inputs, activities, outputs, outcomes and impacts | Indicator definitions, data sources and time horizons |
| IMP-03 | Results-Based Management | F | Objectives, indicators, monitoring, reporting and learning | Baselines, targets, attribution/contribution limits and data quality |
| IMP-04 | Evaluation design matrix | F | Evaluation questions, indicators, sources, methods, timing and responsibilities | Fit between question and evidence; bias and ethical requirements |
| IMP-05 | Cost–Benefit Analysis (CBA) | Q/process | Compare monetized benefits and costs over a defined horizon | Discounting, opportunity costs, sensitivity and non-monetized effects |
| IMP-06 | Cost-Effectiveness Analysis (CEA) | Q/process | Compare costs per unit of defined outcome | Outcome comparability, incremental costs and uncertainty |
| IMP-07 | Social Return on Investment (SROI) | Q/process | Estimate social value relative to investment | Attribution, deadweight, displacement, drop-off and monetization assumptions; results are assumption-sensitive |

---

## 11. Quantitative and calculation methods catalogue

These methods are deliberately included even though they are not all frameworks. A framework may require one or more of these techniques; the router should select only methods that fit the question, data and evidence requirements.

### 11.1 Finance, accounting, and managerial economics

- **Capital budgeting:** NPV, IRR, discounted cash flow, profitability index, payback period, discounted payback.
- **Cost and profitability:** cost–volume–profit analysis, break-even, contribution margin, operating leverage, relevant-cost analysis, make-or-buy analysis.
- **Financial performance:** liquidity/leverage/profitability/activity ratios, common-size analysis, trend analysis, DuPont decomposition, cash conversion cycle, working-capital analysis.
- **Valuation and financing:** WACC, CAPM, debt capacity, valuation scenarios; these require explicit model assumptions and appropriate domain review.
- **Management accounting:** standard-cost variance analysis, activity-based costing, target costing, life-cycle costing, budget variance and responsibility accounting.
- **Unit economics:** customer acquisition cost (CAC), customer lifetime value (CLV/LTV), contribution per customer/order, payback on acquisition, retention/cohort economics.
- **Pricing and demand:** price elasticity, marginal revenue/cost, break-even volume, price/volume/mix analysis.

### 11.2 Market and customer analytics

- Market sizing (TAM/SAM/SOM) with source-backed inputs and clearly labeled assumptions.
- Market share, growth rates, penetration, conversion rates and funnel leakage.
- Cohort retention, churn, repeat-purchase rate and customer lifetime analysis.
- RFM Segmentation. Explain the scoring boundaries and the stability of the segments.
- Demand forecasting and forecast error measures; compare with a naive baseline.
- A/B test design, sample-size/power calculations, confidence intervals and effect sizes.
- Customer profitability and contribution analysis by segment, product, channel or cohort.
- **Campaign performance and media efficiency:** spend, impressions, clicks, conversions and revenue by campaign, with click-through rate, cost per click, cost per thousand impressions, cost per acquisition, return on ad spend, advertising cost of sales and break-even return on ad spend; declare the attribution rule.
- **Channel CAC, LTV and payback:** acquisition cost, contribution margin and churn by channel, with blended CAC and the LTV/CAC ratio; cross-channel incrementality is not implied.
- **Attribution credit across touchpoints:** first-click, last-click, linear and position-based credit from declared touchpoint logs; credit allocation is not causation.
- **Two-proportion A/B test:** conversion counts for two arms, absolute and relative lift, a pooled test, an interval and the sample needed for a declared effect; one test at a time.
- **Email list health and lifecycle performance:** list growth, unsubscribe and bounce rates, open and click rates, engaged-list size and revenue per subscriber.
- **Social engagement and audience growth:** reach, frequency, engagement rate, cost per engagement and follower growth from declared platform counts.
- **Web traffic and conversion by channel:** sessions, conversions and revenue by acquisition channel, with channel share, conversion rate, revenue per session and organic-search click-through.
- **Media planning:** reach, average frequency, gross impressions, gross rating points, cost per rating point and a net-reach estimate under random duplication; declare the target population and each vehicle's reach, insertions and cost.

### 11.3 Statistics and empirical research

- Data profiling, descriptive statistics, cross-tabulation and visualization.
- Sampling, confidence intervals, effect sizes, hypothesis tests and power/precision analysis.
- Chi-square tests, t-tests, ANOVA/ANCOVA and appropriate nonparametric alternatives.
- Correlation and regression (linear, logistic and related models), with diagnostics.
- Reliability assessment and factor analysis for instruments when the data and sample support them.
- Multiple-comparison correction, missing-data analysis and sensitivity checks.
- Time-series forecasting, backtesting, forecast intervals, drift and structural-break checks.
- Clustering, classification and segmentation with suitable validation.
- Causal-inference designs: randomized experiments, difference-in-differences, regression discontinuity, instrumental variables and matching/weighting—only with explicit identification assumptions and diagnostics.
- Mediation/moderation and structural equation modeling where appropriate, with model assumptions and sample-size limitations made explicit.

### 11.4 Operations, logistics, and optimization

- EOQ, reorder point, safety stock and inventory-service-level calculations.
- Demand/lead-time forecasts; inventory turns, stockout rates and service levels.
- Linear programming, integer optimization, scheduling and network optimization.
- Queueing models, throughput, cycle/lead time, utilization and capacity analysis.
- Critical Path Method (CPM), PERT estimates and schedule-risk analysis.
- Overall Equipment Effectiveness (OEE), process capability and control charts.
- SPC and measurement-system checks where data assumptions are satisfied.
- Throughput and constraint analysis; process time, work-in-progress and bottleneck calculations.

### 11.5 Decision analysis and risk quantification

- Decision trees, expected value and expected utility; show probabilities and whose utility is represented.
- Sensitivity analysis, scenario analysis, break-even thresholds and decision-flip analysis.
- Multi-criteria decision analysis: weighted sum, AHP, TOPSIS and other methods where justified. Show criteria, weights, scales, normalization and rank sensitivity.
- Monte Carlo simulation with documented distributions, dependence assumptions and model validation.
- Expected loss, risk exposure and scenario-based stress testing.
- Fault-tree probability calculations when component probabilities and logical relationships are defensible.
- FMEA prioritization scores; do not interpret a Risk Priority Number as a calibrated probability unless validated.

### 11.6 Program and impact evaluation

- Cost–benefit and cost-effectiveness calculations.
- Discounting of costs and benefits, sensitivity to valuation assumptions.
- Difference-in-differences and other impact-estimation methods when assumptions and data support them.
- Outcome rates, reach, adoption, completion and drop-off measures.
- SROI-type estimates only with transparent attribution, deadweight, displacement, drop-off and monetization assumptions.

### Quantitative-method safeguard

Numbers must come from executed calculations or traced sources, not from model-generated prose. The pipeline should record inputs, units, periods, assumptions, formulas/code, versions, checks, and output artifacts. A technically correct calculation does not prove that the chosen business model or recommendation is appropriate.

---

## 12. Explanatory theories: supporting knowledge, not core templates

Do not store these as default, standalone analytical pipelines unless a specific, reproducible instrument or method is defined and evaluated. They can be retrieved, cited and used to interpret evidence when relevant.

Examples include:

- Transformational, transactional, servant and authentic leadership theories.
- Maslow, Herzberg, McClelland, expectancy theory, equity theory and self-determination theory.
- Resource-Based View and Dynamic Capabilities Theory (with VRIO and capability assessment as operational tools where appropriate).
- Agency Theory, Stewardship Theory, Stakeholder Theory, Resource Dependence Theory and Transaction Cost Economics.
- Institutional Theory, Organizational Ecology, Social Identity Theory, Social Exchange Theory and Psychological Contract Theory.
- Diffusion of Innovations Theory, Disruptive Innovation Theory and other explanatory accounts of innovation.
- Prospect Theory and other behavioral-economics theories, when relevant to a decision problem.

This is not a claim that these theories are unimportant. It is a design choice: a theory should inform analysis without automatically generating a rigid template. If a theory is needed, retrieve the original research or a reliable synthesis, state what it explains, note limitations and avoid presenting contested claims as universal laws.

---

## 13. Selection rules for future pipeline use

1. **Start with the problem, not the framework name.** Identify the question, decision context, data, constraints and expected output before selecting a template.
2. **Select the minimum sufficient set.** Do not run every strategy framework on every strategy question. Redundant analyses add length without necessarily adding insight.
3. **Separate diagnosis from recommendation.** A framework may identify an issue without proving which intervention will work.
4. **Link calculations to decisions.** Use quantitative methods only when their data and assumptions match the decision. Show sensitivity when results materially depend on uncertain inputs.
5. **Distinguish facts, assumptions, inference and values.** User priorities and trade-offs must not be silently chosen by the model.
6. **Challenge framework fit.** State why the selected framework fits and what it will miss. Permit T4/framework-only output where evidence is insufficient for a computed answer.
7. **Do not treat scores as truth.** Weighting schemes, maturity scores, survey scales and risk rankings are measurement choices requiring justification.
8. **Preserve provenance.** Record source, version, retrieval date, inputs, assumptions, computations, method choices and limitations.
9. **Verify current editions and permissions.** Standards and commercial frameworks can change. Check official sources and permitted use before embedding licensed materials or reproducing templates.
10. **Evaluate usefulness empirically.** Test whether the framework improves diagnosis, decision quality, explanation, consistency or user learning against a simpler baseline.

---

## 14. Suggested record template for each catalogue item

Every item should eventually have a compact record with these fields:

- **ID and canonical name**
- **Type:** F, M, Q or T
- **Discipline and use cases**
- **Question it helps answer**
- **Required inputs and evidence**
- **Steps, dimensions or constructs**
- **Expected outputs**
- **Calculation methods or data requirements**
- **Assumptions and known limitations**
- **Evidence status:** original source, research support, validation status and known disputes
- **When not to use it**
- **Related frameworks and potential conflicts**
- **Source/version/license notes**
- **Pipeline status:** candidate, reviewed, prototype, validated, approved, retired
- **Evaluation cases and observed results**

---

## 15. Initial priorities for future review — not implementation decisions

A reasonable first review batch, because these can apply to many student and business cases, is:

1. PESTEL, Five Forces, Value Chain, SWOT/TOWS and VRIO for strategy.
2. Business Model Canvas, Lean Canvas and Value Proposition Canvas for business-model/customer problems.
3. Kotter, ADKAR, 7-S, Theory of Change and Logic Model for change and intervention planning.
4. STP, customer journey mapping, 4Ps/7Ps and Kano for marketing cases.
5. SIPOC, DMAIC, value-stream mapping, FMEA and Theory of Constraints for operations.
6. Balanced Scorecard, KPI trees and scenario planning for strategy execution.
7. ISO 31000, MCDA, sensitivity analysis and decision trees for risk/choice problems.
8. Quantitative-method validation for NPV/CVP, regression and standard statistical tests, forecasting, inventory/optimization, and CLV/unit economics.

These are a review order only. Actual inclusion in a production pipeline should depend on problem coverage, evidence, feasibility, and evaluation results.

---

## 16. Seed references for naming and source verification

Use official or originator sources where possible. This short list is a seed for checking names and scope; it is not a complete evidence review of every catalogue item.

- Harvard Business School, Institute for Strategy and Competitiveness — Porter's Five Forces and strategy frameworks: https://www.isc.hbs.edu/strategy/business-strategy/Pages/the-five-forces.aspx
- Strategyzer — Business Model Canvas: https://www.strategyzer.com/library/the-business-model-canvas
- Strategyzer — Value Proposition Canvas: https://www.strategyzer.com/library/the-value-proposition-canvas
- Prosci — ADKAR is an individual change model, not a complete change-management methodology: https://www.prosci.com/blog/adkar-is-a-change-management-model-not-a-methodology
- ASCM — SCOR Digital Standard: https://www.ascm.org/corporate-solutions/standards-tools/scor-ds/open-access-guidance/
- ISO — ISO 31000:2018 Risk Management Guidelines: https://www.iso.org/standard/65694.html
- Balanced Scorecard Institute — Balanced Scorecard perspectives: https://balancedscorecard.org/bsc-basics/articles-videos/the-four-perspectives-of-the-balanced-scorecard/

**Version-control note:** Standards, editions, brand names, licenses and authoritative guidance can change. Verify the currently applicable edition and permissions before the pipeline is built around a specific standard or proprietary method. For example, ISO has published information about work on a future revision of ISO 31000; do not hard-code the 2018 edition as permanently current.

---

## Change log

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-10-20 | Initial broad inventory of business frameworks, models, theories and calculation methods. |
| 0.2 | 2026-10-20 | Separated structured frameworks (F), diagnostic models (M), quantitative methods (Q), and supporting theories (T); added curation, evidence, provenance and evaluation rules. |
