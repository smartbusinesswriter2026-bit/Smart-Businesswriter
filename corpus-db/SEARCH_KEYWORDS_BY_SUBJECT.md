# Search keywords by subject — for building the local corpus database

This document lists **search keywords (query phrases) per pipeline subject** to use when harvesting
open-access documents into the local corpus database described in `CORPUS_DB.md`.

The corpus is built by harvesting from:
- **OpenStax** (peer-reviewed open textbooks) — start here, bounded and hand-checkable
- **OpenAlex content API** (`has_content.pdf:true`, CC-BY filter) — full text + GROBID XML
- **DOAJ** (open-access journals)
- **NBER, SSRN, RePEc** (working papers in economics, finance, management)

The 11 subjects match the pipeline's own subject taxonomy (see
`business_pipeline_v0.12/business_pipeline/scripts/ui_smoke.py:29` and
`business_pipeline_v0.12/business_pipeline/src/bp/product/subjects.py` SUBJECT_DEFS).

> **Rule:** keywords map to the pipeline's *retrieval unit* — **dimensions** of frameworks and
> **methods** on each subject shelf. Each dimension/method already has query phrases in
> `framework_profiles.py` (the `queries` field) and in `chat.py` (`SEARCH_TERMS`). Harvest queries
> should reuse or closely mirror those phrases so the corpus content answers the same questions the
> pipeline will later search for. The corpus adapter (`_corpus()` in `sources.py`) must place the
> corpus **first** in the retrieval order (D-09: corpus → live academic APIs → curated web).

---

## 1. Accounting

**Pipeline shelf:** `accounting` — double entry, trial balance, statements, ratios, cost-volume-profit.
**Covered tools:** `management_accounts`, `trial_balance_check`, `ratio_analysis`, `standard_cost_variances`,
`abc_costing`, `sales_variances`, `tax_declared`, `breakeven`, `multi_product_breakeven`,
`working_capital`, `loan_amortization`, `trend_analysis`.

**Search keywords** (combine each phrase with: `"accounting"`, `"financial reporting"`, `"managerial accounting"`):

| Topic area | Search phrases (use as harvest queries) |
|---|---|
| Financial statements & double-entry | `financial statements preparation`, `double entry bookkeeping`, `debit credit rules`, `trial balance construction`, `general ledger posting` |
| Ratio analysis & financial analysis | `financial ratio analysis liquidity profitability solvency`, `duPont analysis return on equity`, `common size financial statements`, `trend analysis financial statements` |
| Cost accounting & CVP | `cost volume profit analysis`, `break even analysis fixed variable cost`, `standard costing variance analysis`, `activity based costing abc`, `absorption costing vs variable costing` |
| Management accounting | `management accounting decision making`, `relevant costs incremental analysis`, `budgeting and variance analysis`, `contribution margin ratio`, `margin of safety` |
| Inventory & working capital | `inventory costing methods FIFO LIFO weighted average`, `cash conversion cycle`, `working capital management`, `economic order quantity`, `accounts receivable days` |
| Loans & time value | `loan amortization schedule`, `time value of money accounting`, `present value future value`, `interest amortization effective rate` |
| Tax | `corporate income tax accounting`, `declared tax rate payable`, `deferred tax accounting`, `tax incidence business` |

**OpenStax targets:** *Principles of Accounting* vol. 1 (financial) and vol. 2 (managerial). CC BY.

---

## 2. Finance

**Pipeline shelf:** `finance` — corporate finance, valuation, investments, debt, risk, international.
**Covered tools:** time value, loan, bond, NPV, IRR, WACC, DCF, CAPM, portfolio, risk, options, FX, etc.

**Search keywords** (combine with `"corporate finance"`, `"investments"`, `"financial markets"`):

| Topic area | Search phrases |
|---|---|
| Time value of money | `time value of money present value`, `net present value npv`, `internal rate of return irr`, `future value compound interest` |
| Valuation | `discounted cash flow valuation dcf`, `wacc weighted average cost of capital`, `comparable company multiples valuation`, `enterprise value equity value`, `free cash flow valuation` |
| Bonds & fixed income | `bond pricing yield to maturity`, `bond duration convexity`, `yield curve term structure`, `credit risk default` |
| CAPM & cost of capital | `capital asset pricing model capm`, `cost of equity beta`, `cost of debt after tax`, `modigliani miller theorem` |
| Investments & portfolio | `portfolio theory efficient frontier`, `sharpe ratio treynor ratio`, `systematic risk unsystematic risk`, `modern portfolio theory markowitz` |
| Risk & options | `value at risk var`, `black scholes option pricing`, `risk adjusted return`, `volatility estimation finance` |
| International finance | `interest rate parity`, `purchasing power parity ppp`, `foreign exchange exposure hedging`, `currency translation` |

**OpenStax targets:** *Principles of Finance* (CC BY).

---

## 3. Economics

**Pipeline shelf:** `economics` — micro, macro, welfare, international, development, behavioural, game theory.
**Covered tools:** demand/supply equilibrium, elasticity, tax incidence, price control, market concentration,
cost curves, profit maximization, national income, money, fiscal, welfare, trade, game theory, etc.

**Search keywords** (combine with `"microeconomics"`, `"macroeconomics"`, `"development economics"`):

| Topic area | Search phrases |
|---|---|
| Microeconomics — demand & supply | `demand and supply market equilibrium`, `price elasticity of demand arc formula`, `consumer surplus producer surplus`, `market demand market supply` |
| Market structure | `monopoly pricing`, `perfect competition equilibrium`, `monopolistic competition`, `oligopoly cournot`, `market concentration hhi` |
| Costs & production | `production function isoquants`, `short run costs long run costs`, `marginal product average product`, `returns to scale economies of scale` |
| Market intervention | `tax incidence deadweight loss`, `price ceiling price floor`, `subsidy incidence market intervention`, `externalities pigouvian tax` |
| Macroeconomics — GDP & inflation | `gdp gross domestic product expenditure approach`, `inflation cpi deflator`, `gdp deflator vs cpi`, `real vs nominal gdp` |
| Macroeconomics — unemployment & money | `unemployment rate labor force`, `money multiplier fractional reserve`, `monetary policy transmission mechanism`, `quantity theory of money` |
| Macroeconomics — fiscal & public finance | `government spending multiplier`, `fiscal multiplier crowding out`, `budget deficit debt sustainability`, `tax progressivity incidence` |
| International & development | `comparative advantage gains from trade`, `tariff welfare effects deadweight loss`, `purchasing power parity exchange rate`, `terms of trade development` |
| Welfare & behavioural | `social welfare function utilitarian rawlsian`, `gini coefficient income inequality`, `poverty measures headcount gap`, `prospect theory loss aversion` |

**OpenStax targets:** *Principles of Economics* 2e (CC BY).

---

## 4. Management & Strategy

**Pipeline shelf:** `management` — structure evidence on competitive position, compare options.
**Covered tools:** `case_decision`; worksheets: Five Forces, PESTEL, SWOT, Value Chain, Business Model Canvas, etc.

**Search keywords** (combine with `"strategic management"`, `"business strategy"`, `"organizational strategy"`):

| Topic area | Search phrases |
|---|---|
| Industry analysis (Five Forces) | `porter five forces industry analysis`, `industry rivalry competition intensity`, `barriers to entry new entrants`, `threat of substitutes`, `buyer power bargaining`, `supplier power supply chain` |
| Macro-environment (PESTEL) | `pestel analysis political economic social`, `political risk regulation trade policy`, `economic growth inflation interest rate`, `demographic trends social change`, `technology adoption digital transformation`, `climate change environmental sustainability`, `regulatory compliance legal framework` |
| Strategic analysis (SWOT / VRIO) | `swot analysis strengths weaknesses opportunities`, `vrIO framework valuable rare inimitable`, `resource based view rbv firm resources`, `core competencies sustainable advantage` |
| Value chain & activities | `porter value chain primary activities support`, `inbound logistics operations outbound`, `marketing sales service procurement`, `firm infrastructure human resource technology` |
| Growth & diversification (Ansoff) | `an soff growth matrix market penetration`, `market development product development`, `diversification related unrelated`, `blue ocean strategy value innovation` |
| Strategy matrices | `bcg matrix stars cash cows`, `ge mckinsey matrix business portfolio`, `mckinsey 7s framework`, `porter generic strategies cost leadership differentiation focus` |
| Strategic choice | `game theory business strategy`, `nash equilibrium competitive strategy`, `prisoner dilemma oligopoly competition` |

**OpenStax targets:** *Principles of Management* (CC BY-NC-SA — check licence per title before ingestion; G-17).

---

## 5. Project Management

**Pipeline shelf:** `project-management` — scope, business case, schedule, control, delivery documents.
**Covered tools:** NPV, IRR, payback, CPM, earned value, scenario analysis, decision tree, Monte Carlo.

**Search keywords** (combine with `"project management"`, `"project scheduling"`, `"earned value"`):

| Topic area | Search phrases |
|---|---|
| Project selection & business case | `project business case npv irr`, `project portfolio selection`, `cost benefit analysis projects`, `real options project valuation` |
| Scheduling & critical path | `critical path method cpm`, `pert analysis program evaluation`, `project scheduling network diagrams`, `crashing project schedule`, `resource leveling` |
| Earned value & control | `earned value management evm`, `schedule variance cost variance`, `spi cpi schedule performance`, `estimate at completion etc` |
| Risk & decision analysis | `project risk management`, `monte carlo simulation project risk`, `decision tree analysis projects`, `sensitivity analysis project` |
| Planning & governance | `work breakdown structure wbs`, `gantt chart project scheduling`, `project stakeholder management`, `project charter purpose`, `risk register pmbok` |

**OpenStax targets:** None directly in OpenStax business list; harvest from PM-focused OA journals via DOAJ/OpenAlex.

---

## 6. Entrepreneurship

**Pipeline shelf:** `entrepreneurship` — test a venture idea: market size, price, break-even, cash, capital.
**Covered tools:** market size, demand curve, purchase intent, funnel, cohort, pricing, breakeven, proforma,
cap table, NPV, IRR, SROI, cost-benefit, business plan profile.

**Search keywords** (combine with `"entrepreneurship"`, `"new venture"`, `"small business"`):

| Topic area | Search phrases |
|---|---|
| Market sizing & demand | `market sizing estimation`, `tam sam som market size`, `market penetration strategy`, `demand forecasting startup`, `market research methods entrepreneurship` |
| Customer & pricing | `price elasticity demand business`, `pricing strategy value based`, `customer lifetime value clv`, `churn rate retention cohort` |
| Financial planning | `startup cash flow projection`, `break even analysis startup`, `cash runway calculation`, `pro forma financial statements startup`, `sales forecast creation` |
| Funding & valuation | `startup funding stages`, `cap table dilution`, `venture capital valuation`, `term sheet negotiation`, `seed funding angel` |
| Business model & plan | `business model canvas`, `lean canvas startup`, `value proposition design`, `business plan executive summary`, `feasibility study business` |
| Social impact | `social return on investment sroi`, `cost benefit analysis social`, `impact measurement social enterprise`, `triple bottom line sustainability` |

**OpenStax targets:** *Principles of Economics* 2e (covers Entrepreneurship topics); supplemental via
OpenAlex content API filtered to `"entrepreneurship"`, `"small business"`, `"new venture"`.

---

## 7. Operations

**Pipeline shelf:** `operations` — process, capacity, flow, quality, inventory.
**Covered tools:** capacity_analysis, queue_analysis, inventory_policy, line_balancing, oee_analysis,
process_control, breakeven, trend_forecast.

**Search keywords** (combine with `"operations management"`, `"production management"`, `"process analysis"`):

| Topic area | Search phrases |
|---|---|
| Process & capacity | `process capacity bottleneck`, `capacity utilization operations`, `cycle time throughput`, `operations strategy`, `process design layout` |
| Inventory & planning | `inventory management eoq`, `economic order quantity`, `safety stock reorder point`, `just in time jit`, `bullwhip effect supply chain` |
| Queueing & waiting | `queueing theory mm1 mmn`, `waiting line analysis`, `service capacity utilization`, `queue discipline operations` |
| Quality & control | `statistical process control spc`, `control charts x bar r chart`, `process capability index cp cpk`, `six sigma defect rate`, `oee overall equipment effectiveness` |
| Line balancing | `assembly line balancing`, `line balancing heuristic`, `cycle time takt time`, `bottleneck precedence constraints` |

**OpenStax targets:** *Principles of Management* (covers operations management basics).

---

## 8. Supply Chain

**Pipeline shelf:** `supply-chain` — inventory, capacity, demand planning, sourcing, distribution.
**Covered tools:** Same as operations + supply-chain-specific worksheets (SCOR, SIPOC, value stream).

**Search keywords** (combine with `"supply chain"`, `"logistics management"`, `"distribution"`):

| Topic area | Search phrases |
|---|---|
| Supply chain design | `supply chain network design`, `facility location planning`, `distribution network optimization`, `supply chain strategy alignment` |
| Inventory & replenishment | `inventory management safety stock`, `economic order quantity eoq`, `multi echelon inventory`, `vendor managed inventory vmi`, `inventory turnover ratio` |
| Demand planning & forecasting | `demand forecasting methods`, `sales and operations planning s&op`, `forecast accuracy measure`, `statistical forecasting time series` |
| Sourcing & procurement | `procurement strategy supplier management`, `strategic sourcing process`, `supplier selection evaluation`, `purchase order management`, `kraljic matrix procurement portfolio` |
| Transportation & distribution | `transportation management systems`, `distribution strategy third party logistics`, `warehouse operations layout`, `reverse logistics returns` |
| Supply chain risk & sustainability | `supply chain risk management`, `supply chain disruption resilience`, `sustainable supply chain`, `carbon footprint logistics` |

**OpenStax targets:** No dedicated OA textbook; harvest from DOAJ/OpenAlex filtered to `"supply chain"`,
`"logistics"`, `"production and operations management"`.

---

## 9. Marketing & Customers

**Pipeline shelf:** `marketing` — plan marketing and measure it: market size, demand, customer economics,
campaign/channel performance, surveys and tests.
**Covered tools:** market_sizing, demand_curve, elasticity, unit_economics, cohort_retention, rfm_scoring,
clv_model, campaign_efficiency, attribution_split, web_analytics, ab_test_two_proportion, etc.

**Search keywords** (combine with `"marketing management"`, `"digital marketing"`, `"consumer behaviour"`):

| Topic area | Search phrases |
|---|---|
| Market sizing & segmentation | `market sizing estimation methodology`, `market segmentation targeting positioning`, `sam som tam market size`, `market share calculation growth` |
| Consumer behaviour & demand | `consumer behaviour decision making`, `price elasticity of demand`, `demand curve estimation`, `purchase intent survey`, `willingness to pay` |
| Customer economics | `customer lifetime value clv calculation`, `rfm segmentation methodology`, `cohort retention analysis`, `customer acquisition cost cac`, `ltv cac ratio` |
| Marketing mix & strategy | `4ps marketing mix`, `product market fit`, `brand equity measurement`, `pricing strategy penetration skimming`, `value proposition design` |
| Digital marketing & channels | `digital marketing channel attribution`, `seo search engine optimization`, `social media engagement metrics`, `email marketing campaign`, `ppc advertising roi` |
| Campaign measurement & testing | `campaign efficiency roi`, `ab testing statistical significance`, `conversion rate optimization cro`, `funnel analysis conversion`, `marketing attribution models` |
| Market research & analytics | `survey design sampling`, `conjoint analysis market research`, `customer satisfaction measurement`, `net promoter score nps` |

**OpenStax targets:** *Principles of Marketing* (CC BY-NC-SA — check licence per title; G-17).

---

## 10. People & Organisation

**Pipeline shelf:** `people` — design the job, develop people, read the organisation.
**Covered tools:** reliability_alpha, weighted_summary, descriptive_stats, chi_square, power_analysis,
pearson, ols; frameworks: ADKAR, Kotter change, competing values, job characteristics, AMO, Tuckman, etc.

**Search keywords** (combine with `"organizational behaviour"`, `"human resource management"`, `"hrm"`):

| Topic area | Search phrases |
|---|---|
| Job design & work design | `job design characteristics`, `hackman oldham job characteristics`, `job analysis job description`, `job enrichment job enlargement`, `skill variety task identity` |
| Motivation & engagement | `motivation theories maslow herzberg mclean`, `expectancy theory motivation`, `employee engagement measurement`, `motivation hygiene factors`, `intrinsic extrinsic motivation` |
| Team dynamics & development | `team development stages tuckman forming`, `team effectiveness google aristotle`, `group dynamics team performance`, `psychological safety teams`, `team roles belbin` |
| Leadership & change | `kotter 8 step change model`, `organizational culture edgar schein`, `leadership styles transformational transactional`, `change management adkar`, `resistance to change` |
| Organizational design & culture | `organizational design structure`, `organizational culture types competing values`, `organizational learning senge`, `organizational climate engagement`, `organizational justice fairness` |
| Performance & reward | `performance appraisal 360 feedback`, `compensation strategy pay for performance`, `job evaluation methods`, `employee turnover retention`, `hr analytics` |
| HRM & analytics | `human resource management strategic hrm`, `workforce planning`, `training evaluation kirkpatrick`, `hr metrics analytics`, `employee selection assessment` |

**OpenStax targets:** *Organizational Behavior* and *Principles of Management* (covers OB/HRM basics).

---

## 11. Research & Statistics

**Pipeline shelf:** `research` — cross-cutting method shelf: every statistical method.
**Covered tools:** descriptive_stats, pearson, spearman, ols, welch, mann_whitney, anova, kruskal_wallis,
chi_square, logistic, reliability_alpha, multiple_comparison, power_analysis, missing_data_bounds, etc.

**Search keywords** (combine with `"research methodology"`, `"statistics"`, `"research methods"`):

| Topic area | Search phrases |
|---|---|
| Descriptive statistics & graphs | `descriptive statistics measures central tendency`, `standard deviation variance`, `frequency distribution histogram`, `missing data handling listwise pairwise` |
| Correlation analysis | `pearson correlation coefficient`, `spearman rank correlation`, `correlation vs causation`, `scatter plot relationship` |
| Regression analysis | `linear regression ols`, `multiple regression predictors`, `regression diagnostics residuals`, `heteroskedasticity robust standard errors`, `logistic regression binary outcome` |
| Group comparison (t-tests & ANOVA) | `t test independent samples`, `welch t test unequal variance`, `anova analysis of variance`, `post hoc tests tukey bonferroni`, `kruskal wallis nonparametric` |
| Chi-square & categorical | `chi square test independence`, `contingency table analysis`, `crosstabulation categorical data` |
| Research design & inference | `research methodology hypothesis testing`, `statistical significance p value`, `confidence interval interpretation`, `type i type ii error`, `power analysis sample size` |
| Survey & measurement | `survey design questionnaire construction`, `cronbach alpha reliability`, `validity construct content criterion`, `sampling methods probability vs non probability`, `response bias survey` |
| Advanced methods | `difference in differences research`, `instrumental variables endogeneity`, `regression discontinuity design`, `propensity score matching`, `panel data fixed effects` |

**OpenStax targets:** OpenStax does not publish a dedicated statistics textbook in the business set;
harvest from DOAJ/OpenAlex filtered to `"statistics"`, `"research methods"`, `"quantitative methods"`,
and from NBER/SSRN/RePEc for econometrics working papers.

---

## Harvest order & licence notes (from CORPUS_DB.md §4.5)

1. **OpenStax first** — bounded, hand-checkable, covers most subjects. **Check the licence per title**
   (CC BY on Finance, Economics, Accounting; CC BY-NC-SA on Management, Marketing — G-17). NC-SA titles
   need an owner decision before ingestion into a commercial corpus (Q-12).
2. **OpenAlex content API** — filter by `has_content.pdf:true` and `best_oa_location.license` for CC-BY;
   scope to the pipeline subject filters above. Downloads are metered (G-18); track against the free
   daily allowance.
3. **DOAJ** — open-access journal articles already in layer 2; reuse as corpus layer 1 for page-exact
   quoting.
4. **NBER, SSRN, RePEc** — working papers in economics, finance and management; free to read.

**Per-title licence must be recorded** alongside `metadata_source` in `documents.metadata_source` and
a new `licence` column (G-17). Never assume a source's licence from its publisher.

**Subject scope boundary (C-08):** the corpus taxonomy reuses the pipeline's 11 subject ids exactly.
No new taxonomy is invented. The harvest query set above is the join between each subject's
dimensions/methods and the open-access sources.
