# Project management for students

This guide explains what the **Project management** shelf is for, what level it assumes and how to use it
on a business-case, project-appraisal, scheduling or project-control assignment. It is written for **senior
high school ABM** students and **first- and second-year undergraduate** management students. Every number
below is produced by the method named, from the figures shown, in PHP, and can be reproduced in the app.

The shelf appraises a project, plans its schedule, tracks its delivery and records the delivery documents —
charter, WBS, RACI, risk register, stakeholder/communication plan and lessons learned — from figures and
evidence you declare. It does not level resources, score a risk or invent an owner.

## Reading the page

| Group | What it is for | Tiles |
|---|---|---|
| Appraise the business case | Is the project worth doing, what rate does it earn, how does it rank, what is the option to invest, and how uncertain is the result? | NPV, IRR, discounted payback, project ranking metrics, real option valuation, Monte Carlo simulation |
| Compare the options | Which assumption changes the decision, which declared alternative wins, and how does a decision tree or a weighted matrix rank them? | Scenario analysis, business-case decision, decision tree, weighted decision matrix |
| Project cost and benefit | What do the declared costs and benefits look like in later periods? | Trend forecast |
| Schedule and control | When can the project finish, what is critical, who is over capacity, what does speed cost, how do several projects share a crew, how uncertain is the finish, and are we ahead or behind? | Critical path and PERT, resource levelling, project crashing, calendar schedule, multi-project scheduling, schedule risk, earned value |

Six of the delivery frameworks now have worksheets: **PRINCE2** anchors the project charter, **WBS** and
**RACI** have their own, **PMBOK** anchors the risk register, and the stakeholder/communication plan and
lessons learned have dedicated sheets. The other ten — Balanced Scorecard, strategy map, KPI tree, OKRs,
Scrum, Kanban, COBIT, ITIL, DeLone–McLean and TOE — remain read-only records. The page gives the structure
and the evidence each one needs; it does not fill them in or score them.

## Worksheets

| Worksheet | What you record | What the worksheet checks |
|---|---|---|
| Project charter (PRINCE2) | Objective, scope in and out, deliverables, sponsor and governance, budget, milestones, success measures, assumptions and constraints | Every block you fill is reproduced verbatim; empty blocks and assumptions are named, not filled |
| Work breakdown structure | Level-1 deliverables, work packages, acceptance criteria and exclusions, with work packages linked to their deliverable | Every item appears once; the links resolve; an empty block or unlinked package is named; no total, tree or Gantt is drawn |
| RACI responsibility matrix | Activities against the roles you have confirmed, with R, A, C or I in each cell and an optional note | Every cell starts with R, A, C or I; each activity has exactly one A and at least one R; empty cells are named |
| Risk register (PMBOK) | Each risk with your likelihood and impact labels, the response and the owner | Every cell is reproduced; empty cells are named; no probability, expected value or risk score is computed |
| Stakeholder engagement and communication plan | Stakeholders, interests, evidenced influence, engagement approach, messages, channels, timing, owner and communication risks | Every item is reproduced; empty blocks are named; influence stays a declared label with its evidence, not a computed score |
| Lessons learned | What went well and what did not, the evidenced cause, the change for next time, its owner, the audience and the evidence | Every item is reproduced; a lesson without an action or an action without an owner is named; no blame, score or rank is derived |

The worksheets are T4: they place and audit your evidence and compute nothing. A RACI with two accountable
roles on one activity blocks rather than being silently corrected; a risk register with an empty owner names
the gap rather than filling it.

## Conventions

- **The first cash flow is the outlay**, entered as a negative figure at period 0. Later flows are
  end-of-period unless you are told otherwise.
- **The discount rate is your hurdle**, not the engine's. Declare it and justify it in the report; a
  different rate changes every appraisal measure.
- **NPV is the decision rule.** IRR is a rate, not a currency amount, and it can mislead when projects differ
  in scale or timing. PI, MIRR and EAA are ranking aids under their stated assumptions.
- **Payback is a liquidity measure**, not a value measure: it ignores every flow after recovery.
  Discounted payback counts the time value but still ignores the later flows.
- **MIRR assumes positive flows are reinvested at the declared finance rate** and negative flows are
  financed at the discount rate. Change the finance rate and MIRR changes; NPV does not.
- **Scenario analysis assigns no probabilities.** It reports NPV across the rate range you declare and the
  rate at which the decision flips.
- **The critical path has zero total float.** Durations are deterministic, or the expected value of the
  three-point PERT estimate; the schedule does not model calendars, resource limits or uncertainty beyond
  the PERT variance. A critical path is not automatically the riskiest one.
- **Earned value compares one status date.** PV, EV and AC are cumulative figures you declare; the method
  does not derive them from the schedule. Choose one EAC convention (budget / CPI, or AC plus the remaining
  budget at the budgeted rate) and keep it for the report.
- **The business-case decision compares declared alternatives with declared facts.** It does not invent an
  option, weight the criteria or choose for you.
- **The forecast is a linear trend on your own series.** It is not a demand model, a seasonal model or a
  promise about the future.
- **The RACI letter is the assignment.** R does the work, A owns the outcome, C is consulted, I is informed;
  every activity needs exactly one A and at least one R.
- **Levelling is serial and non-preemptive.** The order is early start, then longest duration, then id; one
  resource per activity; whole-period durations and demands. A different priority rule gives a different,
  equally valid plan.
- **Crashing is greedy and linear.** It buys one period at a time on the cheapest critical activity; it is
  not a linear-programming optimum, and shared or non-linear costs are not modelled.
- **The calendar is a declared list of working periods.** No weekends, holidays or shifts are inferred, and
  one calendar applies to the whole project.
- **Multi-project scheduling follows your priority.** Lower priority number first, then early start; the
  higher-priority project takes the shared resource and the lower one waits.
- **Schedule risk is a seeded sample, not a forecast.** Percentiles move with the seed; the P80 is not a
  guarantee, and independent triangular durations are a declared convention.
- **The decision tree is yours.** Probabilities and terminal values are declared; expected value ignores risk
  aversion, so read the loss probability and range beside it.
- **A real option is a model, not a market price.** The lattice value depends on the declared volatility,
  rate and steps; there is no continuous hedging or observable price.
- **Weighted totals are judgement.** Criteria, weights and scores are yours, every score uses one common
  scale where higher is better, and a different weighting can reorder the alternatives.
- **Monte Carlo is a seeded sample of two declared models.** It simulates NPV of uncertain cash flows or
  profit from uncertain price, cost and volume; inputs are independent and fixed, uniform or triangular.
  A different seed changes the percentiles, and the result is not a forecast or a guarantee.
- **The risk labels are yours.** Likelihood and impact are labels you declare; no probability, expected loss
  or score is computed.
- **The WBS records the hierarchy you declare.** It does not draw a tree, sum estimates or prove that the
  breakdown is complete.

## Your assignment requirement, and the tool that answers it

| What the assignment asks for | Tool | What you supply |
|---|---|---|
| Should we invest in this project? | `npv` | the outlay, the later cash flows and the hurdle rate |
| What rate of return does it earn? | `irr` | the same cash flows; the method refuses several sign changes |
| How long until the outlay is recovered? | `discounted_payback` | the cash flows and the discount rate |
| How does it rank on PI, MIRR, payback and EAA? | `projectmetrics` | the cash flows, the hurdle rate and a finance (reinvestment) rate |
| How sensitive is the decision to the discount rate? | `scenario` | the cash flows, the base rate and a low/high range |
| Which of two or three declared options should be compared? | `case_decision` | the facts, the alternatives, their cash flows and provenance |
| When can the project finish, and what is critical? | `cpm` | each activity's id, duration and predecessors; optional three-point estimates |
| Who is over capacity, and how late does the plan become? | `leveling` | activities with resource, demand and duration; each resource's capacity |
| What does it cost to finish earlier? | `crashing` | normal and crash durations, the crash cost and the target duration |
| What dates result when non-working periods are skipped? | `calendar` | the working period numbers and the activities |
| How do several projects share one crew? | `multiproject` | each project's priority, activities, resource and demand, and the shared capacities |
| How uncertain is the finish? | `schedrisk` | optimistic, most likely and pessimistic durations, iterations, a seed and an optional target |
| Which alternative has the best expected value? | `decisiontree` | the decision, chance and terminal nodes, with your probabilities and values |
| What is the option to invest or abandon worth? | `realoption` | the project value, investment, volatility, rate, steps and option type |
| Which alternative scores best on our criteria? | `mcda` | the criteria, weights and scores, with weights summing to one |
| How uncertain is the NPV or the profit? | `montecarlo` | the model, the distribution of every uncertain input, iterations and a seed |
| Are we ahead or behind, and what will it cost? | `evm` | cumulative PV, EV and AC, the budget at completion and the EAC convention |
| What do cost and benefit look like in later periods? | `forecast` | a series in period order and the horizon |
| What is the project authorised to do? | project charter (`template_project_charter`) | objective, scope in and out, deliverables, governance, budget, milestones, success measures, assumptions, constraints |
| What work has to be done? | WBS (`template_wbs`) | deliverables, work packages, acceptance tests, exclusions and the package-to-deliverable links |
| Who is accountable and responsible? | RACI (`template_raci`) | activities, confirmed roles, and R, A, C or I in each cell |
| What could go wrong, and who owns it? | risk register (`template_risk_register`) | risks, your likelihood and impact labels, the response and the owner |

## Worked example

### 1. Appraise the business case

A project costs **PHP 1,000,000** now and returns **PHP 300,000** a year for five years. The hurdle rate is
**10%**; the finance rate for MIRR is **8%**.

- NPV = **PHP 137,236.03** (the present value of the inflows is PHP 1,137,236.03)
- IRR = **15.24%**
- Profitability index = **1.1372**
- MIRR = **11.97%**
- Equivalent annual annuity = **PHP 36,202.52**
- Simple payback = **3.33 years**
- Discounted payback at 10% = **4.26 years**, during year 5

**How to read it.** On every value measure the project clears the 10% hurdle: NPV is positive, IRR and MIRR
are above 10%, and PI is above one. Payback is inside the five-year life, but discounted payback uses almost
all of it, so the project has little room for a cost overrun. That is a sentence for the report, not a
number the engine wrote.

**Common mistakes.** Entering the outlay as a positive flow and adding it to the benefits; discounting at
the 8% finance rate and calling it the hurdle; reporting IRR as "the return we will earn"; comparing the
NPV of projects with different lives without EAA; and reading payback as proof of profitability.

### 2. Plan the schedule

Activities: **A** 3 days, no predecessor; **B** 4 days after A; **C** 2 days after A; **D** 5 days after B
and C.

- Early dates: A 0–3, B 3–7, C 3–5, D 7–12
- Project duration = **12 periods**
- Critical path = **A → B → D** (zero float); C has **2 periods of float**

**Common mistakes.** Adding the durations of every activity instead of the longest path; spending C's float
twice; and reading the critical path as the riskiest work rather than the one that sets the finish date.

### 3. Control the delivery

At one status date: planned value **PHP 100,000**, earned value **PHP 90,000**, actual cost **PHP 95,000**,
budget at completion **PHP 200,000**, EAC convention **budget / CPI**.

- Schedule variance = **PHP (10,000)**; cost variance = **PHP (5,000)**
- SPI = **0.9000**; CPI = **0.9474**
- EAC = **PHP 211,111.11**; ETC = **PHP 116,111.11**; VAC = **PHP (11,111.11)**
- TCPI = **1.0476**

**How to read it.** The project is behind schedule and over cost at the same time: EV is below both PV and
AC. At the current cost efficiency the remaining work needs a cost performance index of about 1.05 to land
on the original budget, which is a sentence for the report. The figures are yours; the method does not
know whether the plan or the scope was right.

### 4. Record the delivery documents

The **charter** states the objective, scope in and out, deliverables, sponsor, budget, milestones, success
measures, assumptions and constraints. The **WBS** breaks the scope into deliverables and work packages,
gives each an acceptance test, records exclusions and links each package to its deliverable. The **RACI**
gives every activity exactly one A and at least one R. The **risk register** records each risk with your
likelihood and impact labels, the response and the owner. The **stakeholder/communication plan** records who
is affected, what they need, how and when you will communicate, and who owns it. **Lessons learned** records
what worked, what did not, the evidenced cause and the change for next time. These six are evidence
worksheets: they name empty blocks and cells, refuse a RACI with two accountable roles, and compute no
total, probability, score or blame.

## Practice set

1. Keep the same project and move the hurdle rate. What is NPV at 5% and at 20%, and at what rate does the
   decision flip?
2. What is the discounted payback at 10%, and in which year is the outlay recovered?
3. A series of 12 monthly volumes is 10, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22. Forecast the next
   three periods.
4. A second project costs PHP 500,000 and returns PHP 150,000 a year for five years. At a 12% hurdle the
   NPV is positive (about PHP 40,716), yet the project-ranking tool blocks. Why?
5. Activities: A 2 days, no predecessor; B 3 days after A; C 4 days after A; D 2 days after B and C. What
   is the duration, the critical path and B's float?
6. At a status date PV is PHP 80,000, EV PHP 70,000, AC PHP 75,000 and BAC PHP 160,000. Find SV, CV, SPI,
   CPI, EAC (budget / CPI) and VAC.

### Answer key

1. NPV at 5% = **PHP 298,843.00**; at 20% = **PHP -102,816.36**; the decision flips at **15.24%**, the IRR.
2. **4.26 years**, during **year 5**; the later flows do not enter the measure.
3. **22.11, 23.11 and 24.11** units; the 95% intervals are about 19.37–24.84, 20.28–25.94 and 21.18–27.05.
4. Its MIRR is **11.97%**, below the 12% hurdle, so the frozen MIRR check fails. The engine blocks the
   bundle instead of delivering a contradictory report: report the NPV and the failed check, or correct the
   inputs. A positive NPV alone is not a complete appraisal.
5. Duration **8 periods**; critical path **A → C → D**; B has **1 period of float**.
6. SV = **PHP (10,000)**; CV = **PHP (5,000)**; SPI = **0.8750**; CPI = **0.9333**; EAC =
   **PHP 171,428.57**; VAC = **PHP (11,428.57)**.

## Charts and the schedule workbook

Once a CPM case is saved, open **Charts and exports** and choose **gantt (CPM schedule)**. Each bar is the
stored early start and early finish, red is the critical path, the thin line after a bar is its float, and the
arrows are the predecessors you declared. The browser draws the same spec from the stored values; the server
render and export remain authoritative. The same case exports to XLSX or SpreadsheetML with a **Schedule**
sheet listing the early and late dates, float and the critical flag; the XLSX sheet also carries a coloured
bar strip (critical red, normal blue) when every date is a whole period. The Gantt and the sheet are renderings
of the stored artifacts: no date is recomputed, no dependency is inferred and no resource is levelled.

## What is not built

- **No dependency arrows on the Gantt.** Multi-project scheduling and schedule risk are built, but the
  multi-project rule is priority-ordered and greedy, and the risk simulation assumes independent triangular
  durations with no resource limits or calendars. Decision trees, real options, a weighted decision matrix and
  a generic NPV/profit Monte Carlo are built; arbitrary formulas, correlation and fitted distributions are not.
- **No Monte Carlo, decision tree, real-option model or multi-criteria scoring.**
- **No probability on a scenario** and no recommendation by the engine.
- **Seven appraisal and forecast tiles are shared with Finance**, and critical path/PERT and earned value
  are shared with the scheduling and project-control methods; the PM shelf adds no second arithmetic path,
  and the same stored case can appear under both shelves.

If your assignment needs one of these, say so in the limitations section and show the method you used by
hand. Do not force a number into the nearest tool.
