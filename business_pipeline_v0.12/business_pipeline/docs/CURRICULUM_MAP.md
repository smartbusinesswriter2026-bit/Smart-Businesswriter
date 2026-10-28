# Curriculum coverage map (provisional)

This map ties each shelf to the topics a course usually examines, so a student or lecturer can see what
the app covers and what it does not. It is **evidence of coverage, not an official syllabus**: it is
inferred from the framework catalogue (`docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md`)
and from the assignments the shelves were built against. It has not been approved by, and does not name,
any external reviewer or teacher. Nothing here is credited on a student's submission: the paper carries
the student's work, the method's recorded checks, its stated limitations and the citation of how the
figures were produced.

**Level key:** SHS = senior high school ABM; UG1–2 = first/second-year undergraduate; UG3+ = later
undergraduate.

| Shelf | Typical course and level | Topics covered | Tools and worksheets | Named gaps |
|---|---|---|---|---|
| Accounting | FABM 1–2 (SHS); Financial Accounting (UG1–2); Management Accounting (UG2–3) | double entry, trial balance, statements, cash flow, closing, ratios, standard costing, ABC, sales variances | `management_accounts`, `trial_balance_check`, `ratio_analysis`, `standard_cost_variances`, `abc_costing`, `sales_variances`, `breakeven`, `multi_product_breakeven`, `working_capital`, `loan_amortization`, `trend_analysis` | tax and deferred tax, audit, consolidation, target/life-cycle costing, budget and planning variances, segment reporting |
| Finance | Business Finance (SHS); Financial Management (UG1–2); Investments (UG3+) | time value, loans, bonds, CAPM, WACC, DCF, multiples, working capital, portfolios, risk, options, FX | 33 tools from `time_value` to `fx_parity`, plus `trend_analysis` and the finance glossary | market data retrieval in the core, credit/liquidity risk, multi-asset optimisation, real options |
| Economics | Applied Economics (SHS); Micro/Macro (UG1–2); welfare, international, behavioural (UG3+) | demand and supply, elasticity, tax, price control, costs, market power, national income, money, fiscal, welfare, trade, game theory, econometrics | 55 tools from `demand_supply_equilibrium` to `probit`, plus the economics glossary | advanced time series (VAR, cointegration), the diagram renderer, retrieved macro data |
| Management & strategy | Business Management (SHS); Strategic Management (UG2–3) | competitive position, evidence audits, options | `case_decision`; worksheets: Five Forces, SWOT, Business Model Canvas, Lean Canvas, Value Proposition Canvas | PESTEL, VRIO, value chain, Ansoff, BCG/GE, Blue Ocean (catalogue only or matrix worksheets where built) |
| Project management | Business Management / Project Management (SHS–UG); PM electives | business case, scheduling, earned value, option comparison, delivery frameworks and governance | `cpm_schedule`, `earned_value`, NPV, IRR, discounted payback, project ranking metrics, scenario analysis, business-case decision, trend forecast; 14 read-only records (Balanced Scorecard, strategy map, KPI tree, OKRs, PRINCE2, PMBOK, Scrum, Kanban, WBS, RACI, COBIT, ITIL, DeLone–McLean, TOE) | project charter, WBS, RACI and risk-register worksheets; resource levelling, calendars, earned schedule and cost crashing |
| Entrepreneurship | Entrepreneurship (SHS ABM); New Venture Creation (UG1–2) | market size, pricing, break-even, projection, cash, capital, funding, funnel, retention, demand, intent, canvases | 36 tools, 5 worksheets, 34 glossary terms, `ENTREPRENEURSHIP_STUDENT_GUIDE.md` | term sheets, liquidation preference, anti-dilution, multi-round cap tables, conjoint, survival models, Monte Carlo |
| Operations | Operations Management (UG2–3) | capacity, bottleneck, queueing (M/M/c), inventory, OEE, control charts and capability, break-even, process evidence | `capacity_analysis`, `queue_analysis`, `inventory_policy`, `oee_analysis`, `process_control`, `breakeven`, `multi_product_breakeven`, `unit_economics`, `trend_forecast`, plus the evidence tools | scheduling, line balancing, subgroup charts, FMEA, simulation, multi-echelon inventory |
| Supply chain | Supply Chain and Logistics (UG2–3) | inventory policy, capacity and flow, demand planning | the operations tools with inventory, capacity and queueing | location, routing, transport optimisation, multi-echelon inventory, supplier risk |
| Marketing & customers | Principles of Marketing (SHS/UG1); Digital Marketing (UG2–3) | market size, demand, customer economics, funnel, cohorts, campaigns, attribution, channel economics, A/B tests | marketing tools plus the STP/4Ps worksheet | market share and penetration, RFM, Kano, SERVQUAL, customer-journey worksheet |
| People & organisation | HRM / Organisational Behaviour (UG1–3) | survey reliability, weighted summaries, group differences | `reliability_alpha`, `weighted_summary`, `descriptive_stats`, `chi_square`, `power_analysis`, `pearson`, `ols` | turnover, compensation, workforce planning, psychometric validation |
| Research & statistics | Practical Research (SHS); Research Methods (UG1–3) | description, association, group comparison, regression, power, missing data | every statistical method in the engine | panel/IV/RDD beyond the basic forms, SEM, factor analysis, qualitative coding |

## SHS ABM core, at a glance

| Subject | What an assignment usually needs | Where it lives |
|---|---|---|
| Fundamentals of Accountancy, Business and Management | journal to trial balance to statements; ratios | Accounting shelf |
| Business Mathematics | break-even, mark-up, interest, payroll, proportion | Finance and Entrepreneurship shelves (break-even, pricing, loan) |
| Business Finance | time value, loan, investment appraisal | Finance shelf |
| Applied Economics | demand/supply, elasticity, costs, market structure | Economics shelf |
| Entrepreneurship | feasibility study: market, price, break-even, cash, capital, return, canvas | Entrepreneurship shelf and guide |
| Principles of Marketing | STP, 4Ps, customer evidence | Marketing shelf and the marketing-plan worksheet |
| Practical Research | survey description, association, group differences | Research shelf |

## How to use this map

1. Find the row that matches the assignment's subject and level.
2. Open the named tile, or the worksheet, and supply your own figures.
3. If the requirement is in **Named gaps**, say so in your limitations section and show the method you
   used by hand. Do not force a number into the nearest tool.

## Keeping it honest

- A row may name a method only if it is implemented and tested; a worksheet only if it exists.
- A gap is named rather than left out; when a gap closes, move it to the covered column.
- The map does not claim that a course, school or examiner has approved the app, and it names no
  reviewer. Coverage is measured against the catalogue and typical assignments, nothing more.
