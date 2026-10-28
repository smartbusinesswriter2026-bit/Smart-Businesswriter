# Conductor manual: how the chat builds a paper

This is the operating manual for the Smart Business Writer chat. Read it before
adding a framework, a computation, a writer feature or a model-assisted step.
It records the goal, the division of responsibility, the non-negotiable rules
and the checklist for extending the working model.

## 1. The goal

The chat is the **macro conductor**. A student describes a decision or an
assignment; the chat decides which frameworks and computations the paper needs,
borrows them from the relevant subjects, and composes one coherent paper. It is
not a PESTEL worksheet, a SWOT form or a calculator with a chat skin.

The current working model is deliberately narrow:

| Area | Working now |
|---|---|
| Frameworks | PESTEL, SWOT, PESTEL + SWOT, Five Forces, Value Chain, Ansoff, VRIO, Break-even, and Five Forces + Break-even |
| Paper profiles | Business plan (SHS core; college adds tax, cap table and impact) |
| Computation | A **capability selected per paper** by the resolver in `bp/product/capabilities.py`. Break-even is the only registered capability today, so a framework paper carries it only when the brief needs it; a framework-only brief runs no computation. Five plan blocks at SHS and eight at college, through the frozen core |
| Output | APA 7 or Harvard `.docx`, hierarchy enforced |
| Evidence | Curated academic databases and vetted web domains; VRIO and Break-even retrieve none by design |
| Model prose | Optional, proposal only, DeepSeek V4.1 Flash by default |
| Framework completion | Porter's Five Forces pilot: instruction box, research per force, sourced/suggested/gap provenance |

Other frameworks and computations are being strengthened in the backend. They
must be wired into the chat one at a time, following this manual, not improvised
inside the writer.

## 2. Division of responsibility

### Chat owns

- the decision and the thesis;
- the framework stack and any computation;
- the paper plan: sections, levels, purpose, evidence allocation, student
  inputs and transitions;
- the export gate.

### Subject modules provide

- framework dimensions and question banks;
- computation methods with declared inputs and a frozen result;
- source registries and relevance rules.

### Writer and renderer only format

- `bp.product.writing` turns sources into citations and reference entries.
- `bp.product.explain` formats the computation companion from the recorded
  inputs, outputs and method contract. It does not decide a method, compute a
  figure or write new reasoning.
- `bp.product.docx` renders the supplied outline. It does not decide headings,
  sections or order.
- `bp.product.paper` holds the section shape and the structural checks.

### Model prose may only edit linking prose

- introduction, one linking sentence per dimension, integration and conclusion;
- never evidence paragraphs, references, numbers, citations or student
  implications;
- every proposal is validated and stored; the student accepts or discards it;
- the deterministic draft remains the fallback.

## 3. Paper hierarchy (Option A)

| Level | Heading |
|---|---|
| H1 | Introduction |
| H1 | PESTEL |
| H2 | Political, Economic, Social, Technological, Environmental, Legal |
| H1 | SWOT |
| H2 | Strengths, Weaknesses, Opportunities, Threats |
| H1 | Five Forces |
| H2 | Industry rivalry, Threat of new entrants, Threat of substitutes, Buyer power, Supplier power |
| H1 | Value Chain |
| H2 | Inbound logistics, Operations, Outbound logistics, Marketing and sales, Service, Procurement, Technology development, Human resource management, Firm infrastructure |
| H1 | Ansoff Growth Matrix |
| H2 | Market penetration, Market development, Product development, Diversification |
| H1 | VRIO |
| H2 | Resources, Valuable, Rare, Costly to imitate, Organised to capture value |
| H1 | Financial Feasibility |
| H2 | Break-even Analysis (or the named computation) |
| H1 | Discussion |
| H2 | Integration of the frameworks |
| H2 | Implications |
| H2 | Limitations |
| H1 | Conclusion |
| H1 | References / Bibliography |

A framework is level 1; its dimensions are level 2. A computation is a level 1
feasibility section with a level 2 method section. The Discussion carries the
integration, not a second framework heading.

### 3.1 A paper profile is not a framework

A **profile** composes a whole paper when no single framework is the paper. The
business plan is the first profile (`PROFILE_BUSINESS_PLAN` in
`bp/product/chat.py`). It has four kinds of section:

| Kind | What it supplies | Rule |
|---|---|---|
| `input` | the student's business description, marketing, operations, management and named risks | reproduced verbatim; never inferred or filled |
| `evidence` | market size and growth, customers, competition and regulation | retrieved and cited, or a named gap |
| `computation` | the plan-level blocks, each a core method | the frozen core runs it; the product formats the result |
| `integration` | executive summary, risk analysis, limitations, conclusion | only supplied facts and stored core results; no new claim |

The **Financial Plan is one H1**; each computation block is an H2 under it. A
college plan adds H1s for Funding and Ownership and Social and Environmental
Impact, with the cap table and impact ratio as their H2s. The SHS core blocks
are `sales_from_market`, `breakeven`, `depreciation_schedule`,
`proforma_statements` and `sensitivity_table`; college adds `tax_declared`,
`cap_table_round` and `cost_effectiveness`.

A profile follows the same rules as a framework: the plan is proposed and
confirmed before research or computation, the student's words stay theirs,
every gap is named and the export gate lists what is missing. Two entry points
share one engine: the Entrepreneurship page opens the **strict** convention,
which keeps every standard section; Home opens **open composition**, which may
leave an optional section out but changes no fact and no figure.

`proforma_statements` is a hard refusal at the opening balance sheet. An
unbalanced opening is rejected with the equity that would balance it, and the
refusal is named in the export gate; the product never plugs a difference.

## 4. Non-negotiable rules

1. **No invented evidence.** Every external claim is quoted or paraphrased from a
   retrieved source, with the source recorded. No invented source, number,
   citation or study.
2. **Gaps are named, never filled.** A dimension without evidence says it is a
   gap.
3. **Student inputs stay student inputs.** Strengths, weaknesses, implications,
   declared costs and expected volume are supplied by the student.
4. **No silent framework substitution.** If a brief names a framework that is
   not wired, refuse and say so. Never default to PESTEL and ignore the request.
5. **Computations come from the frozen core.** Call the method; do not
   reimplement or re-round it in the product layer.
6. **A paper never contains instructions.** No `(your analysis)`, “Not supplied
   yet”, “add your implications”, template names or placeholder prose.
7. **Export is blocked when the paper is incomplete.** Missing implications or
   missing SWOT internal factors return HTTP 409 with the missing list.
8. **The model does not research.** It edits prose only after the deterministic
   draft exists.

## 5. Adding a framework (checklist)

1. Add the framework id and label to `FRAMEWORKS` in `bp/product/chat.py`.
2. Define its dimensions as `(key, label, query cues, source category)`.
3. Add its question bank. Use `text`, `choice`, `items` or `number`; do not add
   a new question type without updating the API and UI.
4. Add the search terms to `SEARCH_TERMS`; keep them short and country-aware.
5. Add the plan wording: what it does, what it misses, expected output.
6. Add the draft branch: H1 framework, H2 dimensions, each dimension one
   paragraph from accepted evidence.
7. Add the Discussion integration when the framework is combined with another.
8. Nothing to add to a UI selector: the framework is inferred from the brief
   (`_infer_framework`); the chat has no framework picker.
   Add the cues `_infer_framework` needs so a student's words reach it.
9. Add tests: questions, plan, research with mocks, hierarchy, draft, export.
10. Add one APA and one Harvard sample built from the same structure.
11. Record the decision and changelog entry.

Do not add a framework by hard-coding its headings in the writer. The writer
only renders what the chat plan supplies.

## 6. Completing a framework from an instruction

The Five Forces pilot is the reference behaviour for future framework
auto-completion.

1. On the subject page, the student describes the case in **Describe your case or paste the instruction**; the matcher opens the suggested worksheet with that description already in the completion box. The subject-level source finder has been removed; research happens inside the worksheet.
2. `bp.product.completion` extracts the country and case context, builds one
   short query per force, retrieves academic and vetted web sources, and ranks
   them.
3. A force with sources gets one to three sourced items. Each item carries the
   citation in the form `text || reference`.
4. A force with no evidence gets a **suggested case assumption** from the model,
   labelled `suggested`, with no citation. It is not evidence and must be
   ticked by the student.
5. A force with neither gets a **named gap**.
6. The review lists every block and every item. The student ticks what the
   worksheet may use, then applies it.
7. The worksheet input accepts per-line `text || source`, so one block can carry
   several citations without losing them.
8. **Generate paper (Word)** stays hidden until all five forces have content, then
   appears at the bottom of the worksheet. It is also available on the results page
   after a run.
   - **Draft (evidence-led)** is deterministic: it quotes the accepted items, labels
     assumptions and names gaps.
   - **Full paper (model-assisted)** sends the same structured items to DeepSeek
     V4.1 Flash. One call writes the introduction, the thesis and the case
     context; seven calls then run in parallel for the five forces, the
     discussion with implications, and the limitations with the conclusion. The
     system appends the real citations afterwards. It may not add a citation,
     source, URL, number, percentage, named condition, actor, technology or
     country that is not in the items; an inference must read as an inference
     ("this suggests", "this implies"). A validator checks citations, links,
     numbers and mid-sentence proper nouns, retries once, and then refuses.
     **A failed full paper is never downloaded:** the page says the run failed
     and asks the student to choose Draft explicitly. Full is the default
     selection. A run takes 40-70 seconds and the button is disabled until it
     finishes.
   - Generation reads the case instruction typed at the top of the worksheet. A
     missing instruction, or the worksheet's own tool title, is refused rather
     than written into the title and introduction.
   - An item the student supplied as their own evidence stays student evidence.
     Only assumption-flagged items are labelled "Case assumption".
9. **Every paper is a full outline**, not a set of one-line sections. H1:
   Introduction, Five Forces, Discussion, Conclusion, References. H2: Case and
   industry context, the five forces, What the evidence shows, Implications for
   the decision, Limitations. The full version targets 1,800-2,200 words; word
   floors are enforced in code (introduction 150, each force 140, discussion
   130, implications 150, conclusion 110, total 1,400), and a paper below them is
   retried once and then refused. The deterministic Draft uses the same outline
   and is about 1,200 words.
10. **The title page is its own section and is centred vertically on the page**
   (section `vAlign=center`). The student's name, institution, course and
   instructor follow (four fields on the worksheet, remembered in the browser),
   then the date. The body is a second section, so it starts on a new page and is
   not centred; the title is repeated at the top of the first page of text. The
   title drops the raw instruction's trailing period. No placeholder such as
   `[your name]` is ever printed. The reference list starts on its own page, and
   the reported word count excludes it.
11. **The DOCX carries real Word structure**: `styles.xml` defines Heading 1/2/3
   with outline levels, body text is Times New Roman 12 double spaced with 1-inch
   margins, references hang, and the page number sits in the header, top right
   (APA 7), not the footer.
12. **Documents on Home.** Every generated paper is stored with its metadata and
   listed in the Documents card on Home beside the shipped samples, with title,
   framework, Draft/Full, words, size, date and a Download link. `GET
   /api/cases/documents` lists them; `GET /api/cases/documents/{id}` returns the
   Word bytes. Ids are validated and path traversal is refused. Nothing is
   recomputed on download: the stored bytes are served.

The model may not add a number, source, citation, link or named fact. A
suggestion that fails validation is dropped and the block remains a gap.

The pilot is deliberately limited to `template_five_forces`. Do not enable
other frameworks until the same behaviour has been reviewed for that framework.

## 7. Adding a computation (checklist)

A computation is a **capability**, not a step. The paper carries one only when
the brief asks a question that computation answers; a framework-only brief
selects nothing, asks for no figures and has no computation section.
`bp/product/capabilities.py` holds the catalogue and the resolver.

1. Confirm the method exists in the frozen core and has a declared input schema
   (`bp.methods.describe(method)["input_schema"]`); the product reads that
   schema, it never restates it.
2. Add one entry to `ENTRIES` in `bp/product/capabilities.py`:
   - `intent` — one group per question kind (for example `cost_cover`); at most
     one capability from a group is selected;
   - `any_of` — the intent cues in the student's words;
   - `needs_any` — at least one of the quantities the method needs. A bare
     "cost" must never start a computation;
   - `applies_to` — the frameworks it may ride on (do not include a framework
     that already carries the same analysis: `breakeven`,
     `five_forces_breakeven` are excluded from `applies_to`);
   - `slot` — the H1 and H2 it takes when selected; `integration` — the H2 of
     the Discussion paragraph that reads it against the framework;
   - `licenses` / `not` — the claim it supports and its own `unsupported_use`;
   - `domain` — the key of a domain check in `chat._capability_inputs` when the
     method needs one beyond the schema (break-even refuses negatives).
3. Register its formatter in `chat.CAPABILITY_LINES`, next to
   `_break_even_lines`. It reads the recorded core result and prints it; it
   must not compute, round or re-derive anything.
4. Add its teaching notes to `subjects.STUDENT_NOTES` - `formula`, `steps` and
   `common_mistakes`. The explainer reads them; a method without them is a
   declared gap in `explain.NOTES_GAPS`, not an invented derivation.
5. Nothing else: the draft, the gate and the plan are generic. Do not add a
   branch to `draft`, `paper.missing` or the UI for one method.
6. Test the five rows of the matrix (below) plus one APA and one Harvard sample.

The resolver is deterministic and must stay so: no model, no retrieval, no
clock. Ambiguity gets exactly one recorded question (`capability:<key>`) and the
answer selects or excludes the capability with a stated reason.

### 7.3 Registered capabilities (wave 1: scalar inputs only)

| Capability (key) | Answers | Slot (H1 / H2) |
|---|---|---|
| `breakeven` | whether the declared price covers the declared costs | Financial Feasibility / Break-even Analysis |
| `npv` | the value of the declared cash flows at the declared rate | Financial Feasibility / Net Present Value |
| `irr` | the rate the declared cash flows earn | Financial Feasibility / Internal Rate of Return |
| `discounted_payback` | when the declared flows recover the outlay | Financial Feasibility / Discounted Payback |
| `project_metrics` | NPV, PI, MIRR, EAA and payback for one project | Financial Feasibility / Project Metrics |
| `unit_economics` | contribution per unit and acquisition payback | Financial Feasibility / Unit Economics |
| `wacc` | the declared cost of capital | Financial Feasibility / Cost of Capital |
| `return_on_investment` | return on the declared investment | Financial Feasibility / Return on Investment |
| `startup_capital` | the capital the venture needs | Financial Feasibility / Start-up Capital |
| `cash_runway` | how long the declared cash lasts | Financial Feasibility / Cash Runway |
| `market_sizing` | TAM, SAM and SOM from declared population and spend | Market Assessment / Market Size |
| `market_share` | the declared firm's share of the declared market | Market Assessment / Market Share |
| `clv_model` | lifetime value from declared margin and churn | Customer Economics / Customer Lifetime Value |
| `campaign_efficiency` | funnel rates and cost per outcome | Marketing Performance / Campaign Efficiency |
| `elasticity` | price elasticity from two declared points | Market Response / Price Elasticity of Demand |
| `earned_value` | SPI, CPI and estimate at completion | Delivery Status / Earned Value |
| `growth_rate` | growth between two declared values | Economic Context / Growth Rate |
| `inflation_cpi` | inflation between two declared CPIs | Economic Context / Inflation |
| `tax_incidence` | who bears a declared tax | Policy Impact / Tax Incidence |
| `pricing_decision` | a declared-cost price under a declared markup | Pricing / Pricing Decision |
| `cap_table_round` | the post-round ownership split | Ownership / Cap Table |
| `time_value` | future or present value of one declared amount | Financial Feasibility / Time Value of Money |
| `loan_amortization` | payment, interest and amortisation of a declared loan | Financial Feasibility / Loan Amortization |
| `leverage_analysis` | EPS, degree of financial leverage and interest cover | Financial Feasibility / Financial Leverage |
| `inventory_policy` | EOQ and the order policy for declared demand | Operations / Inventory Policy |
| `purchase_intent` | the declared intent rate from a survey split | Customer Evidence / Purchase Intent |
| `sales_projection` | units, revenue and profit per period from a declared start | Financial Feasibility / Sales Projection |
| `sales_from_market` | target revenue and units from a declared market share | Financial Feasibility / Target Sales from the Market |
| `depreciation_schedule` | the depreciation charge and carrying amount | Financial Feasibility / Depreciation |
| `tax_declared` | income tax at a declared rate | Financial Feasibility / Declared Income Tax |
| `equity_bridge` | equity value from a declared enterprise value | Financial Feasibility / Equity Bridge |
| `multi_product_breakeven` | break-even for two or more declared products | Financial Feasibility / Multi-product Break-even |
| `capm` | the cost of equity from a declared beta or two return series | Financial Feasibility / Cost of Equity (CAPM) |
| `bond_analysis` | the bond price from a declared yield, or the yield from a price | Financial Feasibility / Bond Price and Yield |
| `ratio_analysis` | the ratios the declared statement figures support | Financial Analysis / Ratio Analysis |
| `dcf_valuation` | enterprise value from declared free cash flows | Financial Feasibility / Discounted Cash Flow Valuation |
| `multiples_valuation` | implied value from a declared peer multiple | Financial Feasibility / Comparable Multiples Valuation |
| `option_pricing` | the option price for the declared terms | Financial Feasibility / Option Price |
| `real_option` | the value of a declared real option to wait or invest | Financial Feasibility / Real Option Value |
| `portfolio_analysis` | portfolio return, risk, beta and Sharpe ratio | Financial Feasibility / Portfolio Return and Risk |
| `descriptive_stats` | the summary of one declared sample | Data Analysis / Descriptive Statistics |
| `pearson` | the correlation between two declared series | Data Analysis / Correlation Analysis |
| `welch_t` | the difference between two declared group means | Data Analysis / Difference Between Two Means |
| `anova` | whether the declared group means differ | Data Analysis / Group Comparison (ANOVA) |
| `chi_square` | the association between two declared classifications | Data Analysis / Association Between Categories |
| `ols` | the regression of a declared series on declared predictors | Data Analysis / Multiple Regression |
| `queue_analysis` | utilisation and waiting from declared arrival and service rates | Operations / Queue Performance |
| `capacity_analysis` | maximum output and the bottleneck against declared demand | Operations / Capacity and Bottleneck |
| `oee_analysis` | availability, performance, quality and OEE | Operations / Equipment Effectiveness |
| `process_control` | the control limits and signals of a declared sample | Operations / Process Control |
| `demand_curve` | the fitted demand curve and its revenue-maximising point | Market Response / Demand Curve |
| `rfm_scoring` | RFM segments from declared customers | Customer Evidence / RFM Segments |
| `sales_funnel` | stage conversion, drop-off and cost per acquisition | Marketing Performance / Sales Funnel |
| `ab_test_two_proportion` | the lift and the two-proportion test | Marketing Performance / A/B Test |
| `social_engagement` | engagement rate, frequency, CPM and follower growth | Marketing Performance / Social Engagement |
| `reliability_alpha` | Cronbach's alpha for a declared survey | Data Analysis / Survey Reliability |
| `weighted_summary` | the weighted mean and effective sample size | Data Analysis / Weighted Summary |
| `power_analysis` | the power and minimum detectable effect of a design | Data Analysis / Statistical Power |
| `cohort_retention` | retention by declared cohort | Customer Evidence / Cohort Retention |
| `trend_forecast` | the declared series' trend and its projection | Data Analysis / Trend Forecast |
| `missing_data_bounds` | what the missing values could hide | Data Analysis / Missing Data Bounds |
| `media_plan` | impressions, GRP and blended CPM | Marketing Performance / Media Plan |
| `web_analytics` | sessions, conversions and revenue per session | Marketing Performance / Web Analytics |
| `email_list_health` | list growth and the open and click rates | Marketing Performance / Email List Health |
| `customer_profitability` | profit and margin by declared segment | Customer Economics / Customer Profitability |
| `channel_economics` | CAC, LTV/CAC and payback by channel | Customer Economics / Channel Economics |
| `attribution_split` | first-click, last-click and linear credit | Marketing Performance / Attribution Split |
| `line_balancing` | the stations and idle time for the declared tasks | Operations / Line Balancing |
| `dupont_analysis` | the three ratios behind the return on equity | Financial Analysis / DuPont Decomposition |
| `trend_analysis` | revenue and margin trends across the declared periods | Financial Analysis / Trend Analysis |
| `working_capital` | the cash conversion cycle and order quantity | Financial Analysis / Working Capital Cycle |
| `scenario_analysis` | the value at low, base and high rates | Financial Feasibility / Scenario Analysis |
| `risk_metrics` | value at risk and expected shortfall | Financial Feasibility / Value at Risk |
| `fx_parity` | the forward implied by parity, and the PPP rate | Financial Feasibility / FX Parity |
| `currency_convert` | a declared amount converted at a declared rate | Financial Feasibility / Currency Conversion |
| `ols_robust` | a regression with robust standard errors | Data Analysis / Regression with Robust Errors |
| `market_concentration` | the HHI, CR4 and effective number of firms | Market Structure / Market Concentration |
| `cost_curves` | total, average and marginal cost, and profit | Market Structure / Cost Curves |
| `market_power` | the markup and the Lerner index | Market Structure / Market Power |
| `proforma_statements` | projected revenue, profit and the balance check | Financial Feasibility / Pro-forma Statements |
| `sensitivity_table` | profit across declared price and volume changes | Financial Feasibility / Sensitivity Table |
| `sroi` | the social return on a declared investment | Impact / Social Return on Investment |
| `cost_benefit` | present values, net value and the benefit-cost ratio | Impact / Cost-Benefit Analysis |
| `cost_effectiveness` | the incremental cost per unit of effect | Impact / Cost-Effectiveness Analysis |
| `demand_supply_equilibrium` | the equilibrium price, quantity and surplus | Market Structure / Market Equilibrium |
| `price_control` | whether a declared ceiling or floor binds, and the gap | Market Structure / Price Control |
| `profit_maximization` | the profit-maximising price and quantity | Market Structure / Profit Maximisation |
| `price_discrimination` | price and quantity in two separated markets | Market Structure / Price Discrimination |
| `cournot_duopoly` | the duopoly quantities, price and profits | Market Structure / Cournot Duopoly |
| `nash_equilibrium` | the pure-strategy equilibria of a payoff matrix | Market Structure / Nash Equilibrium |
| `national_income` | GDP, GNP and net national product | Economic Context / National Income |
| `unemployment_rate` | the unemployment and participation rates | Economic Context / Unemployment |
| `labour_market` | the real wage against productivity | Economic Context / Real Wages |
| `money_multiplier` | the money multiplier and money supply | Economic Context / Money Multiplier |
| `fiscal_multiplier` | the spending, tax and balanced-budget multipliers | Economic Context / Fiscal Multiplier |
| `budget_debt` | the overall and primary balance, and debt to GDP | Economic Context / Budget and Debt |
| `output_gap_okun` | the output gap and its unemployment counterpart | Economic Context / Output Gap (Okun) |
| `externality_pigouvian` | the social optimum and the Pigouvian tax | Policy Impact / Externality and Pigouvian Tax |
| `public_good` | the efficient quantity of a declared public good | Policy Impact / Public Good |
| `optimal_pollution` | optimal emissions and the pollution tax | Policy Impact / Optimal Pollution |
| `social_welfare` | three welfare functions over the same incomes | Policy Impact / Social Welfare |
| `gini_coefficient` | the Gini coefficient and income shares | Policy Impact / Gini Coefficient |
| `poverty_measures` | headcount, gap and squared gap | Policy Impact / Poverty Measures |
| `tax_progressivity` | the progressivity gap between income and tax shares | Policy Impact / Tax Progressivity |
| `tariff_welfare` | the price, imports and deadweight loss of a tariff | Policy Impact / Tariff Welfare |
| `comparative_advantage` | opportunity costs and who holds the advantage | Economic Context / Comparative Advantage |
| `exchange_rate_ppp` | the PPP rate, the real rate and the misalignment | Economic Context / Purchasing-Power Parity |
| `interest_rate_parity` | the forward implied by covered parity | Economic Context / Interest-Rate Parity |
| `balance_of_payments` | the net balance and whether it balances | Economic Context / Balance of Payments |
| `hdi` | the three indices and the HDI | Economic Context / Human Development Index |
| `expected_utility` | expected value, utility, certainty equivalent | Data Analysis / Expected Utility |
| `prospect_theory` | the prospect value against the expected value | Data Analysis / Prospect Theory |
| `difference_in_differences` | the treated and control changes and the estimate | Data Analysis / Difference-in-Differences |
| `instrumental_variables` | the two-stage slope against OLS | Data Analysis / Instrumental Variables |
| `panel_regression` | the within slope and within R squared | Data Analysis / Panel Regression |
| `regression_discontinuity` | the jump at the declared cutoff | Data Analysis / Regression Discontinuity |
| `probit` | the slope, marginal effect and pseudo R squared | Data Analysis / Probit Model |
| `cpm_schedule` | the project duration and the critical path | Delivery Status / Critical Path |
| `resource_leveling` | the delay levelling costs and the peaks it removes | Delivery Status / Resource Levelling |
| `project_crashing` | the cost of reaching the declared target duration | Delivery Status / Project Crashing |
| `schedule_risk` | the duration range and the chance of meeting the target | Delivery Status / Schedule Risk |
| `calendar_schedule` | the finish in working periods, not calendar days | Delivery Status / Calendar Schedule |
| `multi_criteria` | the weighted ranking of the declared alternatives | Delivery Status / Weighted Decision Matrix |
| `monte_carlo` | the simulated range and the share of draws above zero | Delivery Status / Monte Carlo Range |
| `decision_tree` | the expected value and loss chance of each alternative | Delivery Status / Decision Tree |
| `multi_project_schedule` | the overall duration and each project's delay | Delivery Status / Multi-Project Schedule |

Every entry is scalar: no table editor is needed to declare it. The **licence**
(`intended_use`) and the **limitation** (`unsupported_use`) are read from
`bp.methods.describe` when the selection is filled, so no capability restates
its method by hand in the product layer.

The appraisal family (`npv`, `irr`, `discounted_payback`, `project_metrics`)
shares one `intent` group, so a question that names two of them selects one (the
highest priority, NPV) and the others stay addable from the plan. The same rule
puts `multi_product_breakeven` above `breakeven` when the brief says "product
mix".

Declared shapes the panel can take, all validated server-side against the frozen
schema:

| Schema type | What the student sees | Refusal |
|---|---|---|
| `decimal`, `integer` | one field | the field's own description names the missing value |
| `decimal_list`, `value_list` | one number per line, period 0 first | "Every value of the cash flows ... must be a number." |
| `records` | one typed row per item, with the schema's own columns and an *Add row* button | "Row 2 of the products needs a price." / "Declare at least 2 rows ..." |
| `enum` | a select of exactly the values the schema declares | "The which multiple you are applying ... must be one of: earnings, ebitda, ..." |
| `column_map` | one named column per group or predictor, each with its own values | "Every value in the control column ... must be a number." |
| `count_table` | one row per line of comma-separated whole-number counts | "Row 2 ... must be non-negative whole numbers." |
| `value_matrix` | one row per line of comma-separated values | "Row 2 ... must be numbers." |
| `rows` | one row per task with name, time and optional predecessors | "Row 2 ... needs a name." / "the time must be a number." |
| `currency` | a short code, upper-cased (`usd` → `USD`) | "Declare the currency the amount is in." |
| `text` | a short free-text field (a source, a date) | "Declare the rate source." |

Two more declaration rules live in the catalogue, so no capability invents an
input:

- `one_of` — the method needs one of several declarations: `capm` takes a `beta`
  or both return series, `bond_analysis` takes a `yield_to_maturity` or a
  `price`, `multiples_valuation` takes peer `comparables` or a single
  `peer_multiple`. If no group is declared the request is refused, naming the
  options; if both are declared the method decides (the frozen implementation
  says so).
- `min_inputs` — for a method whose inputs are all optional (`ratio_analysis`),
  at least N figures must be declared, otherwise the request is refused.
- `require_inputs` — inputs the frozen core needs but its own schema marks
  optional (`proforma_statements` crashes without `interest` and
  `principal_repayment`). The catalogue names them, so the panel asks for them and
  the refusal is a sentence, not an exception. When the core's schema is corrected,
  delete the list.
- `row_fields` — the columns of a `rows` input, which the schema does not declare
  (`cpm_schedule` takes `id`, `duration`, `predecessors`; `resource_leveling`
  takes two row sets). The panel renders exactly these columns and the parser
  coerces each value; a missing column is refused by row and column name. A
  column named `branches` or `activities` is a multi-line list, written one item
  per line and expanded into the nested shape the method expects: the decision
  tree turns `branch, probability, value` lines into chance nodes, and the
  multi-project schedule turns `id, duration, resource, demand` lines into a
  project's activities. `object` inputs are rendered and parsed the same way.

Methods not registered yet are simply not curated: each needs its cue pair, its
slot and a formatter. Every input shape the catalogue supports now exists
(scalar, list, rows, enum, column map, count table, either/or, minimum), so
adding one is the §7 checklist and a matrix row — not new mechanism.

The statistics family is held to a tighter rule than the rest: its cue pair must
name the analysis *and* the data ("correlation between" + "observations"), and its
formatter states n, the statistic and the p-value and then says, in the paper
itself, that an association is not a cause and a coefficient is not a causal
effect. `guard.COMPUTATION` no longer lists "regression": a regression over
declared observations is a legitimate strategic paper now, and the capability
catalogue decides whether the paper carries one.

Formatting: `CAPABILITY_LINES` holds a bespoke formatter per capability where the
prose matters (break-even today). Everything else uses `_generic_lines`, which
prints the declared inputs and the method's recorded outputs verbatim and says
the figure is not a forecast. Replacing a generic formatter with a bespoke one is
a normal, isolated change: register it under the same key, add its matrix row.

### 7.4 The capability state (what every later step reads)

```
selection: {format, catalogue_version, hash, frameworks[], selected[], not_included[], question}
  selected row: {key, method, label, subject, slot, integration, inputs_required,
                 inputs{name:{desc,required}}, licenses, not,
                 because{rule, quote}}
computations: {key: {ok, method, inputs, result, error}}
```

- `resolve()` runs once in `chat.start`. The rules that fired and the sentence
  they matched are stored, and the selection is hashed, so a paper can be
  re-derived against the catalogue version it used.
- `set_capability()` is the student's add/drop from the plan; a drop is a named
  exclusion, never a silent change.
- `run_capability()` is the only caller of the frozen method for a paper: it
  validates the declared figure through the schema, calls the core, stores the
  result unchanged, and stores a refusal with the core's own message.
- `paper.missing` requires the figures of a selected capability and nothing
  once it is recorded; dropping it removes the requirement.

### 7.5 Test matrix (one row per capability, not one file per method)

| Row | Expectation |
|---|---|
| not selected | brief without the cue → `selected: []`, no computation H1/H2, gate asks no figures |
| selected, valid | selected; figures run through the core; the draft prints the core's numbers; gate passes |
| selected, refused | price ≤ variable cost (break-even) → refusal stored, no figure in the paper, gate blocks |
| selected, no figures | gate requires "the <label> figures"; nothing is estimated |
| ambiguity | cue without quantities → one question; "yes" selects, "no" excludes with the reason |

The reference implementation is break-even: `bp.methods.breakeven` is called from
`chat.run_capability`; the product formats the result but does not recompute it.
A plan block follows the same route: `chat.compute` calls the attached core,
stores the declared inputs and the core result, and `_block_lines` formats them.
Adding a plan block means adding the method to `COMPUTATION_BLOCKS`, declaring
its level and section, and letting the core run it — never writing its formula
in the product layer or the writer.

### 7.6 The reading verifier and the frozen plan

`bp/product/verify.py` is **code, not opinion**. Anything that proposes a reading
of the brief — a person, the resolver, or later a panel of advocates — passes
through it before a paper is built.

- `input_kind(name, spec)` classifies a declared input as `amount`, `rate` or
  `count` from its own schema (`desc`/type), so a percent cannot be filed as an
  amount.
- `normalise_number(written, kind, currency)` reads the ways people write figures
  — `40,000`, `SAR 1.2m`, `1.2 million`, `about 40k`, `12%` — and returns the
  canonical string plus the audit steps. It refuses: a bare rate above one, a
  percentage for an amount, a currency the case does not use, two numbers in one
  figure, and text with no number.
- `verify_reading(reading, entries, frameworks, brief, currency)` refuses a
  reading that names a method outside the catalogue, a method that does not fit
  the framework, a quote that is not an exact substring of the brief, a figure
  without a quote, a bad filing, a rationale that claims more than a method
  licenses (`will`, `prove`, `causes`, `recommend`), or a reading that does not
  say what is missing.
- `freeze(record)` adds `plan_hash`. `chat.confirm_plan` stores the frozen
  record — brief hash, catalogue version, frameworks, the selected capabilities
  and their reasons, the figures, the models used — and `chat.replay_check`
  re-hashes it, so a case can prove its plan has not drifted.

Two guards keep the paper's numbers honest after the plan is frozen:

- `chat._recompute_guard` re-runs every recorded computation from its stored
  inputs at draft time. A mismatch is written into `recompute_problems` and
  `paper.missing` turns it into a blocked export — a paper whose figure no
  longer follows from its own inputs cannot be downloaded.
- Each computation section now opens with a **Declared inputs** paragraph built
  from the stored inputs, not from the prose, and a formatter that cannot read
  the recorded result says so instead of printing a half-built sentence.

`chat.apply_figures` carries the reading's verified figures into the plan. Each
figure names an input; the input is matched against a *selected* capability's
schema, normalised with the audit trail, and offered in the plan card together
with the sentence it came from (`fixed 40000 (“fixed cost 40000”)`). It is an
offer, not a result: the student still validates, the core still decides, and a
figure the student already declared is never swapped out. Three cases are refused
and named in `plan.figure_problems` rather than dropped: a figure that does not
normalise (a percentage for an amount, a currency the case does not use), two
different figures for one input, and a figure no selected computation takes. A
brief whose figures are all read produces a paper whose declared inputs are the
brief's own numbers, quoted.

`tests/test_plan_corpus.py` is the resolver's contract: forty-one real briefs with the
reading a person expects, so a cue or priority change fails by name.
`tests/test_plan_verifier.py` covers the normaliser, the verifier's refusals, the
frozen record, replay and the recompute guard.

### 7.7 The plan council (opt-in, `BP_PLAN_COUNCIL=1`)

Ambiguity in a set case is deliberate, so the conductor can convene a small
council instead of guessing by priority.  `bp/product/council.py`:

1. **Advocates** (two or three model calls, different stances — narrowest
   reading, the reading a marker expects, the reading the others will miss)
   propose a *reading*: frameworks, capabilities, the figures it found **with
   the text they came from**, what is missing, what is excluded.  They choose
   only from the closed catalogue and quote the brief.
2. **The verifier is code** (`bp/product/verify.py`) and vetoes a reading that
   leaves the catalogue, quotes something the brief does not say, files a figure
   wrongly, overclaims, or does not name what is missing.
3. **An examiner that did not propose** ranks only the approved readings and
   returns a verdict, its criteria, the dissent and its confidence.
4. **The registrar** freezes the verdict into `plan_record` (see §7.6), so the
   paper is built from a record and never from a conversation.

Rules that keep it honest:

- no reading reaches the plan unless `verify` approved it;
- the examiner cannot pick a reading that was not approved;
- three unreadable or unapproved answers mean **ask one question**, not guess;
- a provider failure falls back to the deterministic resolver and records the
  reason in `state["council"]`; the brief is never lost to a model outage;
- `BP_PLAN_COUNCIL=1` plus a configured key is the only way to enable it; with
  neither, the resolver decides exactly as before.

`tests/test_plan_council.py` drives all of this with a fake provider: approval,
rejection by the verifier, the lone-reading path, the unreadable answer, the
examiner's clamp to the approved set, the flag-off path, the failure fallback and
the frozen record.

### 7.8 Replay a case (`python -m bp.product.replay case.json`)

A saved case is the JSON the case returns. `bp/product/replay.py` re-derives it:

- `plan`: the frozen record re-hashes to the value it was stored with
  (`chat.replay_check`);
- `brief`: the current brief hashes to the brief the plan was frozen against;
- `recompute`: every recorded computation still reproduces from its declared
  inputs (`chat._recompute_guard`);
- `claims`: the paper's own prose contains no unlicensed claim (`_claim_scan`).

It prints the report and exits `0` only when all four hold, `1` when something
drifted (naming it on stderr) and `2` on a usage or read error. Replay never
repairs: a case that has drifted says so, which is what a marker or an appeals
process needs in order to trust the paper. `tests/test_plan_replay.py` drives the
command itself, including the tampered figure, the changed brief and the draft
overclaim.

### 7.9 Chained computations (`NEEDS_FROM`)

Two frozen methods may feed one another: a discount rate is the WACC result, a
firm's sales are the sales method's target revenue. The chain is **registered** in
`capabilities.NEEDS_FROM` (`capability -> {input: (source capability, output
field, why)}`), and nothing outside that registry is ever offered, so the product
cannot invent that one method's output is another's input.

- `capabilities.dependencies(selection, computations)` reports, per selected
  capability and input, the source, its label, whether the source is in this
  paper, whether it has a recorded successful result and the value (canonicalised:
  `0.09`, not fifty trailing digits).
- `chat.apply_dependencies` offers those values to the capability that needs them;
  the plan card pre-fills the input and says where it came from. A figure the
  student declared still wins.
- `chat.run_capability` records `from: {input: source}` on the computation when
  the declared value is the offered one, and the paper's **Declared inputs** line
  then reads `rate 0.09 (from the cost of capital result)`. A typed value is not
  marked as chained.
- `confirm_plan` stores the same source map in the frozen record, so replay shows
  which figures were chained, and the recompute guard re-runs both methods.

Adding a chain is a catalogue change, not a product change: register the pair in
`NEEDS_FROM`, confirm the units agree, and add a row to
`tests/test_plan_dependencies.py`.

### 7.10 Report length (`write about 2500 words`)

A report is planned in words, and three entry points share one validation:

- the **Report length** box under the Home composer, sent as `words` with the
  start request (`chat.start(..., words=...)`);
- a count in the brief itself (`2500 words`, `2,500 words`);
- the **Report length** box on the plan card, which posts to
  `/api/cases/chat/{id}/length` and re-renders the plan.

The floor is 1,500 words and an empty box is the short version (about 900 words).
The plan carries `target_words`, `full_report` and `min_words`, so the Home box,
the plan card and the draft can never disagree; `set_length` drops a stale draft
when the target changes.
- `check_word_target` enforces the floor: below **1,500 words** the request is
  refused, because the framework, the evidence and the computation cannot be
  written properly in less, and the system does not pad. Above 10,000 words it is
  refused for the opposite reason.
- `draft` reads the target once. A short report is unchanged. A full report adds
  the sections the record supports: `Scope and Method`, a per-dimension reading
  with the dimension's risk, `Evidence Base` (composition, coverage, which source
  informs which dimension), `What the Evidence Shows Together`, `Reading the
  Result`, `What the Figures Assume` (the method's own assumptions and limits,
  quoted), expanded `Limitations`, `What Would Change the Answer`,
  `Recommendation` and `Appendix: How the Computations Were Checked`.
- the draft reports `words`, `target_words` and `met_target`. A full report that
  cannot reach the target says so; it never fills the gap with invented material.

The full report writes nothing the record does not hold: figures are the frozen
method's, limitations are the method's own words, and the evidence base is the
sources' own metadata.

## 8. Coherence and export gate

`bp.product.paper.check` must pass before a `.docx` is produced. It rejects:

- a level jump or a level 2 heading before a level 1;
- a missing Conclusion or reference list;
- instructional/template text;
- missing implications or missing SWOT strengths/weaknesses.

The export route returns `409` with `missing` when the gate fails. The UI hides
the Download button and names what is missing.

Three number-and-claim guards travel with the gate:

- `recompute_problems`: a recorded figure that no longer follows from its own
  declared inputs (`chat._recompute_guard`);
- `claim_problems`: a sentence the paper asserts that no frozen method licenses —
  `verify.overclaims` flags `proves`, `guarantees`, `definitely`, `conclusive`,
  `confirms/demonstrates/establishes that`, `leads to`, unless the same clause
  negates it (`does not prove`, `not a guarantee`, `cannot establish`). Sentences
  that carry an in-text citation belong to the source, and the Limitations
  section states limits by design, so neither is scanned;
- `paper.check`'s structural rules below.

All three are named in `missing`, so a blocked export says which sentence or
figure is the reason.

Coherence expectations for every paper:

- the Introduction states the decision and the thesis;
- every dimension has evidence or a named gap;
- the Discussion integrates the frameworks instead of repeating them;
- the Conclusion answers the thesis and introduces no new evidence;
- every reference is cited in the body;
- combined papers name the origin of each mapped item.

## 9. Sources and search order

- Academic: OpenAlex, Semantic Scholar, DOAJ; Crossref only as metadata.
- Web order: OpenGo (headless OpenCode, opt-in because it is slow), DeepSeek
  Search, Brave, Firecrawl.
- Only the curated registry may return a web source.
- Search results are precision-ranked (relevance, title cue, country anchor,
  source tier, recency, credibility) before placement.

## 10. Model configuration

- Default model for model-assisted prose: `deepseek-v4.1-flash`.
- `PROSE_MODEL` overrides the prose model without changing the search model.
- DeepSeek Pro is available for a final polish; it is slower and uses the Go
  allowance faster.
- Regardless of model, the same validation applies: no new number, citation,
  link, heading or template text.

## 11. Adding a new model or opening a new chat

A new model or session should:

1. Read this manual and `docs/HANDOFF.md`.
2. Run the conductor tests before changing code.
3. Inspect `bp/product/chat.py`, `bp/product/paper.py` and
   `bp/product/prose.py` before touching the paper flow.
4. Keep the framework/computation registry as the single source of truth.
5. Never fix a missing framework by editing the sample builder or the DOCX
   renderer.
6. Add a sample only after the conductor can produce the same structure.
7. Update `CHANGELOG.md`, `DECISIONS.md`, `HOME.md`, `HANDOFF.md` and
   `CONTRIBUTORS.md` digits with the build.

## 12. Reference files

- `src/bp/product/chat.py` — conductor, framework registry, questions, draft.
- `src/bp/product/paper.py` — levels, paragraph joining, export gate.
- `src/bp/product/prose.py` — model proposal and validation.
- `src/bp/product/docx.py` — H1/H2/H3 rendering.
- `src/bp/product/writing.py` — citations and references.
- `src/bp/product/explain.py` — the computation explainer (recorded data only);
  `explain_html.py` — its print-ready HTML; `data/explain_contracts_v0_1.json`
  — the committed method-contract slice.
- `src/bp/product/sources.py` — academic and web retrieval.
- `src/bp/product/api.py` — routes.
- `src/bp/product/documents.py` — PDF, Word `.docx`, TXT and image readers.
- `web/index.html` — Chat panel, business-plan builder and framework selector.
- `tests/test_chat.py`, `tests/test_prose.py`, `tests/test_writing.py` — the
  conductor contract.
- `tests/test_business_plan_profile.py` — the plan profile, brief readers and
  export gate.
- `samples/` — the current APA/Harvard examples, including the four generated by `scripts/build_conductor_samples.py` (see `docs/SAMPLE_PAPERS.md`).

## 13. Current limits

- Eight single frameworks and two combinations: PESTEL + SWOT, and Five Forces + Break-even. Any other pairing of two frameworks is refused rather than approximated.
- A **paper carries a computation only when the brief needs one.** The catalogue
  in `bp/product/capabilities.py` resolves the brief at `chat.start`; a
  framework-only brief selects nothing and has no computation section. Only
  break-even is registered today, so a PESTEL/SWOT/Five Forces/Value Chain/
  Ansoff/VRIO paper can carry a break-even analysis
  (`POST /api/cases/chat/{id}/computation`, validated by the frozen
  `breakeven` method). Registering the next capability is the §7 checklist, not
  a new branch in the draft.
- Framework auto-completion is enabled for Porter's Five Forces only; other worksheets are still manual.
- Other frameworks are refused, not silently replaced.
- VRIO and Break-even retrieve **no external evidence**: VRIO records the student's resources and four judgments, and Break-even runs the declared figures. Their papers say so.
- Value Chain and Ansoff dimensions are supported by retrieved evidence placed by keyword; they do not collect internal cost data or benchmark activities against rivals.
- The business plan is the only paper profile; it is not a framework and cannot be combined with one.
- Plan-level methods use annual periods, one product and one currency; they do not forecast demand, apply a jurisdiction's tax law or model disposals.
- Open composition changes which optional sections appear, not the facts, figures or the export gate.
- OpenGo search is opt-in and slow; DeepSeek Search is the fast default.
- Model prose is linking prose, not a full rewrite.
- APA and Harvard sample papers for the four frameworks added in B-151 are generated by `scripts/build_conductor_samples.py` (see `docs/SAMPLE_PAPERS.md`); PESTEL and SWOT keep their earlier samples.
- The title page byline is the student's own list of lines and is omitted when empty; the product does not invent a name or an institution.
- A paper that carries a recorded computation downloads with a computation
  companion in one ZIP (`<title>-explainer.docx`); a paper without one keeps the
  plain download. The companion explains the recorded figures and the method's
  steps; it does not recompute. Ten statistics tools still lack catalogue notes
  and are named as gaps. A true server-side PDF is not produced; the HTML
  companion is printed to PDF in the browser.
- The sample papers demonstrate the target; the live conductor can still show
  named gaps when the sources are thin.
