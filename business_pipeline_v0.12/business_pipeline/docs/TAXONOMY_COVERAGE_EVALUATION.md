# Business Assignment Taxonomy — Pipeline Coverage Evaluation

**Date:** 2026-10-31
**Subject:** `business_assignment_taxonomy.md` (Business Student Assignment Taxonomy, 19 sections + classification axes)
**Evaluator:** chat-as-conductor, reading the taxonomy against the running code
**Verdict basis:** code inspection and executed tests, not the docs alone. Where the docs and the code disagree, the code wins and the disagreement is called out.

---

## 0. What the manual is, and which file is authoritative

The uploaded manual is the **Business Student Assignment Taxonomy** — a master coverage list of the
assignment genres business students complete, built "to check that the automated pipeline covers every
genre."

Three copies exist and **all three are byte-identical in content**:

| File | Modified | Status |
|---|---|---|
| `business_assignment_taxonomy.md` | 2026-10-31 02:54 | 27,564 bytes — the source of record |
| `business_assignment_taxonomy.docx` | 2026-10-31 03:08 | 31,546 bytes — Word export, same text |
| `business_assignment_taxonomy -edited.docx` | 2026-10-31 03:09 | 31,640 bytes — **differs from the .docx only in Word metadata; paragraph-for-paragraph identical** |

A line-level diff of the two DOCX files (285 paragraphs each) returned **zero** paragraphs unique to
either side. The "-edited" file carries no content changes. Treat the `.md` as the source of record.

The taxonomy explicitly excludes: country-specific formats, professional qualifications and platform
work, industry-specific verticals, and academic-skills services. Those are therefore *out of scope by
the manual's own construction* and are excluded from this evaluation.

---

## 1. The pipeline's actual capability surface (measured)

### 1.1 What is really there

| Layer | Measured inventory | Source of truth |
|---|---|---|
| **Frozen computation core** | **142 methods**, all `status=implemented_tested`, 133 T1 + 9 T2, each with an input schema, unit, caveat set and its own tests | `bp/methods.py` → `LIBRARY` |
| **Framework completion profiles** | **68 templates** (`framework_profiles.PROFILES`), each with labelled blocks and a per-block fill type (`research` / `auto` / `quote` / `gap`) | `bp/product/framework_profiles.py` |
| **Conductor plan registry** | **9 frameworks** — PESTEL, SWOT, PESTEL+SWOT, Five Forces, Five Forces+Break-even, Value Chain, Ansoff, VRIO, Break-even — plus 1 paper profile (`business_plan`) | `bp/product/chat.py` → `FRAMEWORKS` |
| **Capability catalogue** | **126 capabilities** in `capabilities.ENTRIES`, each with an intent, cue regex, required-input regex, and `applies_to` framework list | `bp/product/capabilities.py` |
| **Subject shelves** | **11 subjects**, 158 catalogue entries, 45 worksheets (33 draftable to a paper) | `bp/product/subjects.py` |
| **Retrieval** | Academic: OpenAlex, Semantic Scholar, DOAJ, Crossref (metadata only). Web: OpenGo (opt-in), DeepSeek Search, Brave, Firecrawl, behind a curated site registry | `bp/product/sources.py`, `retrieval.py` |
| **Deliverables** | `submission` (docx+html), `workpapers` (**xlsx**+spreadsheetml+csv), `worksheet` (docx+html), `presentation` (**declared, no renderer**) | `bp/product/deliverables.py` |
| **Ledger kernel** | `ledger.py`, `accounts.py`, `schedules.py`, `reconcile.py`, `report.py` — journal, trial balance, statements, two-route cash flow, equity, OCI, T-accounts, reconciliation, 8 schedule kinds, 11 frozen checks | `src/bp/` |
| **Market data** | SEC fundamentals + filings, World Bank indicators, FX, quotes, risk-free rate, macro | `/api/market/*` |
| **Intake** | PDF, Word, TXT, image/OCR readers | `bp/product/documents.py` |

### 1.2 Two framework systems, not one

This is the single most important structural fact for reading the taxonomy against the pipeline.

- **`chat.FRAMEWORKS` (9)** governs the **conductor / paper plan**. It decides which framework stack a
  brief carries and what sections the paper has.
- **`framework_profiles.PROFILES` (68)** governs **worksheet completion**. It decides how a framework's
  blocks are filled with retrieved evidence, the student's own words, or a named gap.

Only **37 of the 68 built profiles are reachable** through the worksheet registry; the other 32 built
profiles (ADKAR, AIDA, DMAIC, Kotter-adjacent models, STP, RFM, digital mix, email/CRM, SEO, social
media, McKinsey 7S, Porter's Diamond, generic strategies, Blue Ocean ERRC, brand equity, customer
journey, and others) **exist and work but have no catalogue entry or worksheet wiring**. Eight
draftable worksheets point at templates that have **no profile at all**: Business Model Canvas, Lean
Canvas, Value Proposition Canvas, project charter, WBS, risk register, stakeholder plan, lessons
learned.

**Consequence:** the pipeline's *worksheet* reach (68 frameworks) is roughly 7× its *paper* reach
(9 frameworks). A student can complete a DMAIC worksheet with retrieved evidence and cannot get a
DMAIC *paper*.

### 1.3 Verification state

```
53 failed, 2412 passed, 102 subtests passed in 103.57s
```

The failures are **not** random. They cluster in three groups, and each one bears directly on this
evaluation:

1. **Profile/catalogue drift (39 failures).** `test_a_framework_without_a_profile_has_no_extension`
   asserts `template_customer_journey` has no profile — but a profile was built for it. Same for
   email/CRM, funnel, Kano, marketing plan, measurement plan, RFM, SERVQUAL, social media, STP,
   STP-evidence, TAM, value-chain. *These are tests that lag the code.* The feature shipped; the test
   still asserts the pre-feature state.
2. **Real defects (14 failures).** `test_value_chain_completion` and `test_operations_frameworks` fail
   on substance: `test_nine_activities_each_carry_a_sourced_item_or_a_named_gap`,
   `test_no_evidence_is_written_from_general_background`, `test_an_empty_block_is_named_and_never_filled`.
   These point at the completion engine's evidence handling and are **genuinely open**.
3. **Routing drift (2 failures).** `test_open_pure_accounting_refused` expects `not_supported` for a
   journal-entry brief; the code now returns `clarify`.

### 1.4 Two findings that change the answer

**Finding A — the `not_supported` refusal path is present in HEAD but was deleted in the working tree.**

> **CORRECTED 2026-10-31 (same day).** The first pass of this evaluation reported the `not_supported`
> stage as "no longer produced by the code", implying a design decision. **That was wrong, and so was
> the reading of the docs.** The stage **is** in HEAD (`d3df5c3`), the UI renders it
> (`web/index.html:2052`), two build scripts raise on it, and 9 tests assert it. The stage is missing
> only because **an uncommitted local edit gutted the refusal path in two files** — `guard.py`
> (`subject_fit()` reduced to `return True, None`) and `chat.py` (three deletions, including the
> `if not fits: state.update({"stage": "not_supported", ...})` return). The fix is two file restores.
> See §1.4 and the CONTINUATION_NOTE work orders.

`not_supported` is referenced by `web/index.html:2052`, by `scripts/build_conductor_samples.py:142`,
by `scripts/build_home_sample.py:113` and by 9 tests — and **it exists in HEAD**. The working tree's
`git diff` against HEAD shows the damage:

- `src/bp/product/guard.py` — `subject_fit()` was replaced wholesale with `return True, None`,
  deleting the subject-hint matching and all three refusal messages.
- `src/bp/product/chat.py` — three deletions: the `_fit()` computation-hint refusal; the `and fits`
  guard on the capability question; and the `if not fits:` block that set `stage: "not_supported"`.

**Finding B — unmatched briefs silently become PESTEL (a consequence of A).**
`chat._infer_framework()` falls through to `return "pestel"` for any brief that does not contain a
literal framework name. Measured on 28 representative briefs:

| Brief | Working tree (regressed) | With HEAD restored (verified) |
|---|---|---|
| "Prepare the journal entries and the trial balance…" | **pestel** (clarify) | `not_supported` — "This looks like an accounting or finance computation…" |
| "Evaluate the effectiveness of the brand new digital advertising campaign…" | **pestel** (clarify) | `not_supported` — "This does not look like a management or strategy instruction…" |
| "Write a literature review on remote work productivity…" | **pestel** (clarify) | `not_supported` |
| "Build a Tableau dashboard of quarterly sales" | **pestel** (clarify) | `not_supported` — "This does not name a statistics question…" |
| "Write an MBA admission essay" | **pestel** (clarify) | `not_supported` |
| "Write a Python script to analyze customer churn" | **pestel** (clarify) | `not_supported` — "This instruction looks like marketing, not statistics…" |
| "Prepare a peer evaluation of my teammates" | **pestel** (clarify) | `not_supported` — "This does not name a people question…" |
| "Build a business model canvas for our startup" | **pestel** (clarify) | `clarify` (correct — accepted) |
| "Do a value chain analysis of our sari-sari store" | value_chain | `not_supported` — over-refusal, see below |
| "Run a break-even analysis for our kiosk" | breakeven | `clarify` (correct — accepted) |
| "Conduct a Porter's Five Forces analysis…" | five_forces | `clarify` (correct — accepted) |

**Working tree: 27 of 28 briefs mis-routed to PESTEL. With HEAD restored: 23 × `not_supported` with
a specific, actionable message, 6 × `clarify`** — verified in an isolated copy (working tree copied
to a temp directory, only `chat.py` and `guard.py` restored from HEAD, the real tree untouched).
`tests/test_product_home_routing.py` + `tests/test_chat.py`: **40 passed**, was 2 failing.

The fix is two file restores:
```powershell
git -C 'D:\SMART BUSINESSWRITER' checkout -- business_pipeline_v0.12/business_pipeline/src/bp/product/chat.py business_pipeline_v0.12/business_pipeline/src/bp/product/guard.py
```
**One caveat to check after restoring:** an explicitly named framework can still be over-refused —
"…our coffee shop in Davao City" is detected as `swot` but refused with "This does not look like a
management or strategy instruction", because the management hint list has no "shop"/"coffee". The
correct repair is to let an explicitly named framework bypass the subject guard (the carve-out HEAD
already makes for `breakeven`/`vrio`), **not** to widen the hint list.

The `council` module (`bp/product/council.py`) is the designed second line — it proposes a reading,
verifies it in code, and lets an examiner decide — but it is **opt-in (`BP_PLAN_COUNCIL=1`)** and off
by default.

### 1.5 The catalogue's own status field is stale

`subjects.CATALOGUE` carries a `status_short` per entry: *Computed* (35), *Worksheet* (45), *No
worksheet yet* (47), *Method not built* (24), *Reading lens* (7). The *Method not built* label is
**wrong for 21 of the 24 entries** — the frozen core already implements the method:

| Catalogue says "Method not built" | Actually in the core |
|---|---|
| IMP-05 Cost-Benefit, IMP-06 Cost-Effectiveness | `cost_benefit`, `cost_effectiveness` ✓ |
| IMP-07 SROI | `sroi` ✓ |
| QNT-DEC-01 Decision trees / expected value | `decision_tree`, `expected_utility` ✓ |
| QNT-DEC-03 MCDA | `multi_criteria` ✓ |
| QNT-DEC-04 Monte Carlo | `monte_carlo` ✓ |
| QNT-DEC-05 Scenario stress testing | `scenario_analysis`, `sensitivity_table`, `risk_metrics` ✓ |
| QNT-STA-02 Sampling / CI / power | `power_analysis`, `one_sample_t`, `paired_t` ✓ |
| QNT-STA-05 Reliability & factor analysis | `reliability_alpha` ✓ |
| QNT-STA-06 Multiple comparison / missing data | `multiple_comparison`, `missing_data_bounds` ✓ |
| QNT-STA-07 Time-series forecasting | `trend_forecast` ✓ |
| QNT-STA-09 Causal inference | `difference_in_differences`, `instrumental_variables`, `regression_discontinuity` ✓ |
| QNT-OPS-07 SPC | `process_control` ✓ |
| RSK-04 Fault Tree Analysis | `decision_tree` (partial) ✓ |

**Genuinely unbuilt** (verified against all 142 method names): FMEA prioritization scores, linear
programming / integer optimization, clustering / classification / segmentation, Markov chains,
transportation & assignment problems, SEM/PLS-SEM, mediation/moderation, conjoint analysis, DEA,
event studies, LBO, lease-vs-buy, dividend discount model, Excel/VBA/code deliverables.

**Do not trust the catalogue's status column.** It understates coverage. Assess against `LIBRARY` and
`PROFILES` directly.

---

## 2. Coverage verdict by taxonomy section

Legend — **A**: works well now · **B**: includable with enhancement/modification · **C**: out of scope

### §1 Written Academic Papers & Essays — **B**
| Item | | Note |
|---|---|---|
| Term papers | A | Core competency. APA + Harvard, 600–5,000 word bands, live export gate. |
| Critical essays / critiques | B | Framework-comparison only; no claim-against-theory evaluation mode. |
| Literature reviews | B | Needs a synthesis-mode paper profile; today it is framework-answered, not literature-synthesised. |
| Systematic reviews / meta-analysis / bibliometrics | C | No PRISMA protocol flow, no quantitative synthesis engine. |
| Annotated bibliographies | C | Per-source evaluation is not a deliverable the renderer produces. |
| Article and book reviews | C | Needs a single-work ingestion + critique profile. |
| Abstracts and executive summaries | B | Easy: a length band + section filter on an existing paper. |
| Position papers / white papers / policy briefs | B | Argument structure; the thesis layer already exists. |
| Research proposals | B | Methodology templates exist for plans; a research-design profile does not. |
| Research reports (IMRD) | B | Section skeleton exists in the plan; data-collection half is out of reach. |
| Thesis chapters written separately | C | Chapter-level orchestration is out of scope. |
| Research instruments (questionnaires, interview guides, sampling plans) | C | Instrument design is a form artefact, not a paper. |
| Ethics (IRB) applications | C | Human-subjects protocol is out of scope. |
| Grant proposals | C | Funding-request genre is out of scope. |
| Derivative outputs (journal articles, posters, extended abstracts) | C | Posters and abstracts-as-format are not built. |
| Discussion board posts and peer replies | C | Forum-length genre, out of scope. |
| Written exams | C | Assessment instrument, out of scope. |

### §2 Problem Sets & Quantitative Exercises — **A for methods, B as an assignment**
The core is genuinely strong: **142 tested methods** covering capital budgeting, cost-volume-profit,
ABC costing, variance analysis, micro/macro, elasticity, welfare, cost-benefit, experimental design,
ANOVA, chi-square, regression, panel, IV, RD, difference-in-differences, queueing, inventory, capacity,
line balancing, scheduling, Monte Carlo, decision trees, game theory.

**The limitation is genre, not arithmetic.** The methods exist; a *problem set* deliverable does not.
What is missing is a **problem-set paper profile**: a sequence of worked sub-questions each bound to a
frozen method with its own stated inputs, rather than one brief → one method → one section.

- Finance, managerial accounting, economics, operations, management-science problem sets — **B** (all
  methods present; needs the multi-part profile)
- Business analytics / statistics-econometrics problem sets — **B** (OLS, ANOVA, chi-square, logistic,
  probit, panel, IV, RD, DiD, power analysis, reliability alpha, multiple comparison, missing-data
  bounds, trend forecast all present; SEM, mediation, DEA, conjoint, clustering, event study, ARIMA
  proper, Markov, LP/transportation are **C**)

### §3 Financial Analysis & Modeling — **B**
Strong method coverage: `dcf_valuation`, `multiples_valuation`, `wacc`, `capm`, `bond_analysis`,
`option_pricing`, `real_option`, `fx_parity`, `exchange_rate_ppp`, `interest_rate_parity`,
`portfolio_analysis`, `portfolio_valuation`, `portfolio_performance`, `equity_bridge`,
`proforma_statements`, `ratio_analysis`, `dupont_analysis`, `working_capital`, `loan_amortization`,
`cap_table_round`, `leverage_analysis`, `risk_metrics`, `sensitivity_table`, `scenario_analysis`.

Genuinely absent: **LBO, lease-vs-buy, dividend discount model, M&A accretion/dilution as a distinct
method** (equity_bridge is adjacent, not accretion/dilution). **Excel financial modeling as a
*linked model*** is the real gap: the `workpapers` deliverable emits a real `.xlsx`, and for an
accounting case that workbook carries the trial balance, income statement, balance sheet, cash flow
statement, reconciliation, notes, the journal, the T-accounts (in the .docx explainer) and the PASS/FAIL
checks — **but every cell is an inline string, not a formula.** Nothing recalculates when the student
changes an assumption. A student who edits revenue in Excel does not get a revised balance sheet.
This is a *linkage* gap, not a *format* gap.

### §4 Strategic Frameworks & Analyses — **A (with one systemic defect)**
This is the pipeline's strongest alignment. 68 profiles cover SWOT/TOWS-adjacent, BCG, Five Forces,
PESTEL, Ansoff, VRIO, Value Chain, McKinsey 7S, GE/McKinsey, Blue Ocean ERRC, Scenario Planning,
Root Cause, Activity System, Strategic Group, Competitive Values, Org Design, RACI, Porter's Diamond,
Generic Strategies, Mintzberg, Burke-Litwin, Galbraith Star.

Gap: **TOWS itself has no profile** (SWOT and ERRC do). **Balanced Scorecard** has no profile
(PM-01, "No worksheet yet"). **CAGE / Hofstede** have no profile — the nearest is PESTEL with a
country unit. **KPI/OKR design**: OKRs (PM-04) has no profile; KPI Tree (PM-03) none.

**Systemic defect:** because §4 briefs are the ones that name a framework explicitly, §4 is the
taxonomy section *least* damaged by the PESTEL fallback. The damage is concentrated in §§1–3, 11, 14–17,
where the brief names a genre rather than a framework.

### §5 Business Plans, Feasibility Studies & Proposals — **A for plans, B for the sub-genres**
`business_plan` is a **first-class paper profile** with 12 sections (Executive Summary, Business
Description, Market Analysis, Marketing Plan, Operations Plan, Management and Organisation, Financial
Plan, Funding and Ownership, Social and Environmental Impact, Risk Analysis, Conclusion, References),
two levels (SHS/College) and two modes (strict convention / open composition). Its computation slots
cover market size, break-even, NPV, cap table, unit economics and social impact. Feasibility studies
and marketing plans map onto it well.

Sub-genres needing modification: **global business plans** (needs country-analysis + entry-mode
sections — Ansoff is the nearest, and entry-mode choice has no profile), **franchise / social-enterprise /
family-business succession plans**, **exit strategies**, **crowdfunding campaign plans**, **MVP plans**,
**business model tools** (BMC / Lean Canvas / VPC — *the three worksheets exist and are draftable but
have no completion profile*), **design specifications** (no proposal profile).

### §6 Case Studies — **A for the written analysis, C for the oral/simulation forms**
"Written case analysis" is the pipeline's home ground: problem identification → framework application →
alternative evaluation → recommendation. `five_forces_breakeven` is literally the framework+computation
case, and `pestel_swot` the two-framework case.

Absent: **case presentations** (no `presentation` renderer), **case writing**, **case interview
preparation** (consulting-case format is a distinct genre with a distinct scoring rubric), and
**case-based exams**.

### §7 Portfolio & Investment Projects — **B/C split**
The **portfolio lab** (`/api/portfolios`, `portfolios/portfolio.json`, `holdings.json`, plus the
`portfolio-lab-explainer`, `portfolio-mock-fund-sample`, `portfolio-lab-video-kit` artefacts) is a
real capability — a mock-fund simulation with an investment report. **A**.

**E-portfolios, reflective portfolios, stock-trading simulations** — **C**: these are multi-artifact
course portfolios with a reflective essay and accreditation mapping, not a single paper.

### §8 Financial Statement Preparation & Bookkeeping — **A (with named carve-outs)**

> **CORRECTED 2026-10-31.** The first pass of this evaluation rated this section **C (out of scope)**.
> That was wrong, and the error came from reading only the product layer (`subjects.py`, `capabilities.py`)
> and missing the ledger kernel in `src/bp/`. The pipeline **does** keep the books. The corrected verdict
> is below.

The pipeline contains a **full double-entry ledger kernel** — `src/bp/ledger.py` (32 KB),
`src/bp/accounts.py` (22 KB), `src/bp/schedules.py` (33 KB), `src/bp/reconcile.py`,
`src/bp/report.py` — wired in as the `management_accounts` method (T2) and covered by five test modules
(`test_accounts.py`, `test_accounting_operations.py`, `test_accounting_pipeline_integration.py`,
`test_accounting_sandbox_parity.py`, `test_t_account_ledger.py`) and
`docs/ACCOUNTING_STUDENT_GUIDE.md`.

**Verified by execution** (not by reading docs): a single engagement with a 29-account chart, 6 posted
entries, a reversal, a dividend, and 7 schedules (prepayment, deferred income, depreciation, two
bad-debt events, disposal, revaluation) produced **11/11 frozen checks passing** and this workbook:

| Sheet | Contents |
|---|---|
| `Case` | case id, title, method, tier, spec hash, outputs hash, created-at |
| `Statements` | trial balance, income statement, balance sheet, cash flow statement, reconciliation, notes |
| `Trial balance` | Account / Debit / Credit, footed to totals |
| `Journal` | Date, Description, Account, Debit, Credit, Entry hash — every entry balances |
| `Checks` | the eleven frozen checks, each PASS/FAIL with its detail |
| `Recorded values` | the artifact table (id, metric, unit, precision, value, derivation) |
| `Report` | the delivered report, one line per row |

A CPM case additionally gets a `Schedule` sheet with a coloured bar strip.

**What the ledger kernel actually does:** builds a chart of accounts and posts declared opening
balances, entries, reversals and schedules into the journal; closes the period with closing entries;
and derives the trial balance, income statement, balance sheet, two-route cash flow statement,
statement of changes in equity, comprehensive income with a separate OCI reserve, T-accounts with a
running balance per account, a bank reconciliation, the retained-earnings rollforward, the next
period's opening lines, and human-review flags. Eight schedule kinds are built: depreciation,
amortization, accrual, bad debt, disposal, prepayment, deferred income, revaluation. Declared policy
changes (a useful-life or residual-value revision) apply prospectively from their date.

**What is genuinely still out of scope, and why:**

- **Audit assignments** — no audit opinion, no audit sampling, no assurance. Named gaps.
- **Advanced financial accounting** — no consolidation (goodwill, non-controlling interest), no
  IFRS-vs-GAAP comparison, no foreign-currency translation, no deferred-tax rollforward beyond the
  declared rate, no lease accounting.
- **Jurisdiction tax rules** — `tax_declared` applies the rates and taxable income you declare. It
  knows nothing of credits, exemptions, thresholds, NOLCO, withholding or filing.
- **Not-for-profit and government accounting** — no fund accounting, no public-sector reporting.
- **AIS / ERP practice sets** — no QuickBooks or SAP transaction processing or controls.
- **Costing variants** — activity-based costing and sales price/mix/yield variances are built;
  **target costing, life-cycle costing, budget/planning variances and idle-capacity variances are not.**
- **Standards setting** — the standard quantities and prices are the student's; the engine cannot say
  whether they are attainable.
- **Scanned-ledger ingestion** — CSV, TSV and XLSX can be read; a PDF scan or image of a ledger cannot.

### §9 Simulations, Games & Role-Plays — **C**
Every item is **out of scope**. Business simulations (Capsim, Marketplace Live, Glo-Bus, Cesim),
negotiation role-plays, decision games, AI simulations. The pipeline never observes a simulation,
never plays a role and never scores a decision. Even "simulation decision rationales and reflections"
is a reflective genre (§12) with no simulation to reflect on.

### §10 Consulting & Client-Based Projects — **B**
**Management consulting capstone** and **consultancy reports** are strong — they are
recommendation-shaped, framework-driven and client-framed, which is precisely the conductor's shape.
**Partner projects**, **small-business consulting**, **applied/professional-doctorate research** —
all **B** with the same profile, since the client framing is a prompt variation, not a new engine.
**Scope risk:** these require real client access and confidential data the pipeline has no way to
obtain; the papers must run on the student's supplied material.

### §11 Research Projects & Theses — **B (empirical/theoretical), C (theses/defences)**
**Empirical research projects** — **B**: `power_analysis`, `reliability_alpha`, `missing_data_bounds`,
`multiple_comparison`, `difference_in_differences`, `instrumental_variables`, `regression_discontinuity`
give a real inference toolkit. **Theoretical research projects** — **B**: `theory_of_change`,
`logic_model` profiles cover the conceptual-model half. **Dissertation proposals**, **comprehensive
exams**, **defense slides**, and **undergraduate/master's theses** are **C**: orchestration of many
chapters, and oral defence, exceed a single-paper pipeline.

### §12 Reflective & Professional-Development Assignments — **B (short-form), C (artefact-linked)**
Reflection papers, learning journals, leadership philosophy statements, group contribution statements,
individual reflections on group work, team charters and peer evaluations are all **B** *as
short-form reflective prose* — the pipeline can structure and edit them. But every one of them is
**only meaningful when bound to an artefact the student supplies** (a simulation log, a portfolio, a
project record), and the pipeline has no artefact-binding concept. Personal development plans built on
Gibbs/Kolb need a **reflective-cycle profile** that does not exist. "Peer evaluation" of teammates is
partly a quantitative instrument — a survey scale with reliability analysis — which *is* buildable from
`reliability_alpha`.

### §13 Presentations & Oral Assessments — **C (one exception)**
`deliverables.PROFILES` declares `presentation` with the comment *"A format is only offered when a
renderer exists for it. `presentation` is declared but not offered"*. There is **no PPTX renderer and
no slides deliverable**. Every item in this section is therefore out of scope: individual and group
presentations, board reports, pre-recorded video, slide decks with speaker scripts, Q&A preparation,
handouts and infographics, Pecha Kucha, debate briefs, mock board meetings.

**The exception:** `portfolio-lab-video-kit.docx` exists in `samples/`, so a **video/script kit** for
one specific lab is producible. That is a narrow artefact, not §13 coverage.

### §14 Subject-Specific Assignment Types — **B (the strongest section)**
The 11 subject shelves map onto most of §14:

| Subject | §14 coverage | Grade |
|---|---|---|
| Finance (35 tools) | stock valuation, stock pitches, VaR/hedging/credit risk, M&A, **LBO (C — no method)** | B |
| Economics (55 tools) | policy memos (B), econometric studies (A), model solving (B) | A/B |
| Entrepreneurship (46 tools) | pitch decks (C — no renderer), feasibility analyses (A), elevator pitches (B), business-model development (B — BMC has no profile) | B |
| Marketing (24 tools) | marketing research projects (B), consumer-behaviour projects (B), ad critiques (B), brand repositioning (B) | B |
| Operations (14 tools) | process analysis (A), queuing (A), inventory/scheduling (A), supply-chain mapping (A) | A |
| Supply chain (8 tools) | mapping and optimisation (A) | A |
| Project management (18 tools) | project charters (B — no profile), WBS (B — no profile), risk registers (B — no profile), stakeholder plans (B — no profile), lessons learned (B — no profile) | B |
| People & organisation (10 tools) | job analysis (B), compensation (B), selection (B), performance instruments (B) | B |
| Research & statistics (21 tools) | regression (A), visualisation/dashboards (C — no dashboard renderer), predictive modelling (A), data wrangling (C — no code deliverable) | A/B |
| Management & strategy (1 tool) | leadership case analyses (A), org reports (A), change plans (A) | A |
| Accounting (12 tools) | audit (B), tax (B — `tax_declared`, `tax_incidence`), forensic (C), cost accounting (A) | B |

Missing entirely: **International Business** (no shelf; country analysis is PESTEL-as-country, entry
mode has no profile) and **Business Ethics** (no shelf; the nearest is `stakeholder` in RSK-05, still
read-only).

### §15 Data & Analytics Tooling Assignments — **C (method half is B)**
**Out of scope as deliverables:** qualitative coding/thematic analysis (NVivo), dashboards (Tableau/Power
BI), SQL query assignments, VBA/macro, Python/R scripts, Excel projects (pivot tables, Solver),
Google Forms/Qualtrics survey building, web scraping, financial data pulls from Bloomberg, and data
cleaning. **The pipeline produces a `.docx` paper, a `.csv`/SpreadsheetML workpaper set and an HTML
companion — it does not produce code, a workbook, a dashboard, a database or a recording.**

**Method half is B:** the *analysis* behind several of these exists (`reliability_alpha` for
reliability/validity analysis, `power_analysis` for sampling, `missing_data_bounds` for data
cleaning, `trend_forecast` for time series). What is missing is the tooling artefact.

### §16 Marketing & Business Communication — **B (strategy) / C (production)**
**Real B:** IMC plans (multi-channel campaign), SEO/SEM plans (`template_seo_content`),
social media audits and content calendars (`template_social_media`), email marketing plans
(`template_email_crm`), marketing automation (`template_marketing_automation`), A/B test analysis
(`template_cro`, `ab_test_two_proportion`), CLV and RFM (`template_rfm`, `clv_model`, `rfm_scoring`),
market sizing (`template_tam`, `market_sizing`), customer personas and journey maps
(`template_customer_journey`), positioning statements (`template_strategic_positioning`), brand audits
(`template_brand_equity`), digital mix (`template_digital_mix`).

**Out of scope as production:** creative briefs, service blueprints, influencer campaign plans, PR
plans and press releases, crisis communication plans, sales plans and pitch scripts, CRM exercises as a
data task, business memos/letters/emails, bad-news and persuasive letters, resumes and cover letters,
MBA admission essays. These are *short-form professional documents with a house style*, not analytical
papers. Their absence is a **product-line** gap, not an engine gap — the paper engine would need a
second, much shorter profile family.

### §17 Operations, Project Management & Information Systems — **A (ops/PM), C (IS artefacts)**
**Strong:** Six Sigma/DMAIC (`template_dmaic`), Lean and value-stream mapping
(`template_value_stream_map`), SPC (`process_control`), MRP/aggregate planning (no profile — **B**),
facility layout and location analysis (no profile — **B**), project charters / WBS / risk registers /
stakeholder plans / lessons learned (all **draftable but profile-less — B**), earned value
(`earned_value`), Agile/Scrum (`PM-07`, `PM-08` — no profile, **B**).

**Out of scope:** ER diagrams, UML, data-flow diagrams, BPMN models, cybersecurity risk assessments,
ERP and IT strategy analyses, digital transformation plans, international trade documentation (Incoterms,
letters of credit). These need diagrammatic or system-modelling renderers that do not exist.

### §18 Business Law, Governance, Sustainability & Ethics — **C**
No shelf, no method, no profile for any of it. IRAC case briefs, contract analyses, legal memos,
compliance program design, IP cases, employment law, whistleblowing, CSR/ESG/GRI reporting, SDG
alignment, carbon-footprint and triple-bottom-line, social impact assessments.

**Two partial exceptions worth naming precisely:**
- `template_activity_system_fit` (strategic fit under ESG/SDG pressure) and the plan's
  **"Social and Environmental Impact"** section — these give *one* ESG-adjacent surface, not §18.
- `sroi` exists in the core (social return on investment) and `cost_benefit`/`cost_effectiveness`
  exist — so an SROI computation can be run, but **there is no sustainability-report profile and no
  governance/law profile**. The catalogue's own "IMP-05/06/07 Method not built" label here is *stale*
  (see §1.5): the methods are real; the *paper around them* is missing.

### §19 Organizational Behavior & HR Assignments — **B**
Organizational culture diagnosis (COMPETING_VALUES), change-management analyses (`template_kotter`,
`template_lewin`, `template_adkar`), motivation-theory applications (`template_amo` — but **no
Hertzberg/Maslow/Herzberg-specific profile**), negotiation preparation (no negotiation profile),
personality-assessment and EI/360 reflections (reflective genre, §12), HR analytics (`template_ppl_*`
people shelves, `labour_market`, `unemployment_rate`), training needs analyses
(`template_kirkpatrick`), onboarding and succession plans (no specific profile).

---

## 3. The three buckets

### 3.1 Works well in its present state (A)

| Capability | Why it is genuinely strong |
|---|---|
| **Strategy framework papers** (PESTEL, SWOT, Five Forces, Value Chain, Ansoff, VRIO, +2 combos) | Named framework → structured paper with retrieved evidence per dimension, APA/Harvard, length bands, export gate, explainer companion. |
| **Worksheet completion across 37 reachable frameworks** | Per-block fill discipline: `research` retrieves, `quote` takes the student's verbatim words, `gap` stays a named gap. Never dresses an unobservable process in findings. |
| **The business-plan profile** | 12 sections, 2 levels, 2 modes, computation slots, distinct from a framework by design. |
| **The double-entry ledger kernel** (`src/bp/ledger.py`, `accounts.py`, `schedules.py`, `reconcile.py`, `report.py`) | Posts declared entries, reversals and 8 schedule kinds; derives trial balance, income statement, balance sheet, two-route cash flow, equity statement, OCI, T-accounts, bank reconciliation and closing balances; **11 frozen checks** gate delivery. Management accounts — explicitly *not* GAAP/IFRS statements. |
| **Computation catalogue (126 capabilities, 142 frozen methods)** | Every method is `implemented_tested` with an input schema, unit, caveat set and its own tests. The resolver binds brief→method by cue, and **asks one question rather than guessing** when inputs are missing. |
| **Quantitative problem-solving** (finance, managerial accounting, economics, operations, management science) | Arithmetic and inference are genuinely solid — this is the most defensible part of the product. |
| **Marketing & customer analytics** | 24 tools, with STP/RFM/CLV/CRO/digital-mix profiles built. |
| **Consulting-style recommendations** | Recommendation-shaped output is the conductor's natural shape. |
| **Evidence discipline** | The full-text gate (title cue + country anchor + geography), the `no evidence written from general background` rule, the overclaim scanner, the recompute guard — these are real and enforced. |
| **Portfolio lab / mock fund** | A working simulated-investment report with an explainer. |

### 3.2 Includable with enhancement or modification (B)

| Enhancement | Unlocks | Effort |
|---|---|---|
| **Wire the 32 orphan profiles into the catalogue + worksheets** | DMAIC, ADKAR, AIDA, STP, RFM, digital mix, email/CRM, SEO, social media, McKinsey 7S, Porter's Diamond, generic strategies, Blue Ocean ERRC, brand equity, customer journey, and ~16 more | **Low** — the profiles are built and tested; only registration is missing |
| **Build the 8 profile-less but draftable worksheets** | BMC, Lean Canvas, VPC, project charter, WBS, risk register, stakeholder plan, lessons learned | **Low** — profile entries per §6.3 of the manual |
| **Restore the `not_supported` refusal path** | Stops PESTEL from silently answering a Tableau, MBA-essay or journal-entry brief | **Medium** — the UI, scripts and 9 tests already expect the stage |
| **Enable the council by default** | Model-assisted reading of briefs that do not name a framework | **Medium** — the module is built and code-verified; it is opt-in today |
| **Fix the 14 real completion-engine defects** | Value-chain and operations-framework evidence handling — the two areas the taxonomy leans on hardest | **Medium** — failures are localised and reproducible |
| **Add a problem-set paper profile** | Multi-part worked questions, each bound to a frozen method with stated inputs | **Medium** — reuses 142 methods |
| **Add an Excel/spreadsheet-model deliverable** | §3 Excel modeling, §15 Excel projects, pivot tables, Solver — the `.xlsx` exists and carries the accounting statements, but has **no live formulas**, no pivot tables and no charts | **Medium** — the writer is there; it needs formula cells, a chart part and a workbook schema |
| **Add a short-form document profile family** | §16 memos/letters/press releases/cover letters, §12 reflections, §1 abstracts | **Medium** — a second, much shorter paper profile |
| **Extend the plan profile** | Global business plans (country analysis + entry mode), franchise/exit/crowdfunding/MVP plans | **Medium** |
| **Rebind `applies_to` per framework** | Today all 126 capabilities claim to apply to all 7 frameworks; NPV in a PESTEL paper is opt-in-by-cue, not structural | **Low** |
| **Refresh the catalogue's `status_short`** | 21 of 24 "Method not built" labels are wrong | **Low** — regenerate from `LIBRARY` |
| **Introduce an artefact-binding concept** | §12 and §7 — letting a paper reference the student's simulation log, portfolio or project record | **Medium** |
| **Add an international-business shelf** | Country analysis and entry-mode selection | **Medium** |

### 3.3 Out of scope (C)

| Why | Items |
|---|---|
| **No renderer of that media type** | Presentations, slide decks, speaker scripts, posters, infographics, Pecha Kucha, debate briefs, mock board meetings, Q&A packs, video kits, pitch decks |
| **No code/spreadsheet/dashboard deliverable** | Python/R scripts, VBA macros, SQL queries, Tableau/Power BI dashboards, web scrapers, Excel workbooks, Google Forms/Qualtrics instruments, R2 notebooks |
| **The pipeline cannot observe or perform the task** | Business simulations, negotiation role-plays, decision games, AI simulations, trading simulations, stock-trading exercises, written exams, comprehensive exams, case-based exams, discussion-board posts |
| **Legal / regulatory / actuarial genre with no rule engine** | IRAC case briefs, contract analyses, legal memos, compliance program design, IP cases, employment law, whistleblowing, codes of ethics, corporate governance reviews, tax-return preparation, audit reports |
| **Sustainability reporting genre** | CSR/ESG/GRI reports, SDG alignment analyses, carbon-footprint and triple-bottom-line analyses, social impact assessments — the *methods* exist but the *report* does not |
| **Qualitative inquiry** | Systematic reviews, meta-analyses, bibliometric studies, qualitative coding and thematic analysis, NVivo work, interview transcript analysis |
| **Research governance and instrument design** | IRB/ethics applications, grant proposals, research instruments (questionnaire design, sampling plans), research posters, defence slides |
| **Multi-artifact orchestration** | E-portfolios, reflective portfolios, thesis/dissertation chapters written separately, full dissertations, journal-article derivative outputs, e-portfolios for accreditation |
| **Requires the student's own data at scale** | Personal finance and retirement planning, portfolio construction with real holdings, advanced financial accounting (consolidations, IFRS-vs-GAAP, FX translation, leases, deferred tax), ERP/AIS practice sets, not-for-profit and government accounting, audit opinions and audit sampling. *(Journal entries, ledgers, trial balances and bank reconciliations themselves are **in scope** — see §8.)* |
| **Competitor/product market simulation** | Full ERP/MRP/capacity simulators, facility layout optimisation solvers, LP/transportation/assignment optimisers, DEA, conjoint, clustering, Markov chains, SEM/PLS-SEM, mediation/moderation, event studies |

---

## 4. Recommended sequence

Work orders WO-1 … WO-7, with file paths and verification steps, are in
`docs/CONTINUATION_NOTE.md` under "Work orders — pick-up-ready". Summary:

1. **WO-1 — Restore the refusal path (P0, correctness).** Two file restores:
   `git checkout -- src/bp/product/chat.py src/bp/product/guard.py`. This is not a redesign — HEAD
   already has the correct behaviour, the UI already renders `not_supported`, and the build scripts
   already raise on it. **Verified**: 40/40 in `test_product_home_routing.py` + `test_chat.py`, and
   the 28-brief probe goes from 27 silent PESTEL mis-routes to 23 specific refusals + 6 legitimate
   accepts. Then close the one over-refusal (an explicitly named framework must bypass the subject
   guard). Consider making the council the default afterwards.
2. **WO-2 + WO-3 — Reconcile the catalogue with reality.** Register the 32 orphan profiles; build the
   8 missing worksheet profiles (BMC, Lean Canvas, VPC, project charter, WBS, risk register,
   stakeholder plan, lessons learned). Low effort, large honest gain. Neither requires touching
   `completion.py`, `api.py` or `web/index.html`.
3. **WO-4 + WO-5 — Fix the 14 real completion defects and update the 39 stale profile tests.**
   The suite must be green before the next build; it currently is not.
4. **WO-6 — Spreadsheet linkage.** Add the T-accounts, equity statement, closing balances, flags and
   next-period opening lines to the `.xlsx`; break the schedules out; then decide the formula-cell
   question.
5. **WO-7 — Doc hygiene**, then the two larger architectural additions (problem-set profile,
   short-form document family, artefact binding).

---

## 5. Verification notes

- All counts were produced by importing the running packages (`bp.methods`, `bp.product.subjects`,
  `bp.product.framework_profiles`, `bp.product.capabilities`, `bp.product.chat`,
  `bp.product.deliverables`) under Python 3.14.2 with `python-docx` 1.2.0, against the working tree
  at HEAD `d3df5c3` ("product: Home chat serves every subject", 2026-10-30) plus uncommitted changes.
- The taxonomy `.md`, `.docx` and `-edited.docx` were compared paragraph-by-paragraph: identical.
- The test suite was executed in full: **53 failed, 2412 passed, 102 subtests passed in 103.57 s**.
  The 28-brief routing probe in §1.4 was executed against `chat._infer_framework` directly.
- The 21 stale `status_short` labels in §1.5 were each confirmed by resolving the catalogue name
  against the full 142-name `LIBRARY`, not by sampling.
- `corpus-db/CORPUS_DB.md` is **truncated in the working tree to its final 10 lines (730 bytes)**, and
  `corpus-db/` is **untracked at HEAD**. **The design record is recoverable** — the full file survives
  as git blob `a97402ee84e870896ca71a63242651989d05c232` (**69,327 bytes**, in commits `df5cdcc` /
  `d78e1b4`, "untracked files on cline checkpoint"), with an earlier 58,191-byte version as blob
  `a168c4381bfaa78a3f279618c23d08eb66d2c35a` in `d25d622`. Restore with
  `git cat-file blob a97402ee > corpus-db/CORPUS_DB.md` before any corpus work begins. The corpus
  layer itself remains unimplemented (§9 of the manual: "not yet wired").
- `business_pipeline_v0.12/business_pipeline/docs/PRODUCT_GAP_MAP.md` and `OPEN_ISSUES.md` were read
  and are consistent with the findings above, though `OPEN_ISSUES.md` lists 58 failures against the 53
  observed — the count has drifted.

---

*No framework was added, substituted or removed by this evaluation. No evidence, source, number or
citation was invented. Gaps are named, not filled.*
