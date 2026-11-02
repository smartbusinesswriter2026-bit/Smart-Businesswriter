# QA defect ledger

**Living record.** One row per defect, gap or parked item. A fixed BLOCKER or MAJOR carries a
trap test committed with it and flips its E-row to PASS in `qa/manual/<subject>.md`.
`BLOCKED` means the fix needs an owner decision (frozen core, design convention); `GAP` means a
declared limitation that must not be built.

Severity: **BLOCKER** (wrong number, invented evidence, gate bypass, crash, a refusal that
silently succeeds) · **MAJOR** (feature unreachable, wrong refusal, stale doc claiming built) ·
**MINOR** (wording, count drift, layout) · **GAP** (declared/parked/owner-gated).
Class: FORMULA, UNITS, ROUNDING, VALIDATION, REFUSAL, GATE, HONESTY, DETERMINISM, WIRING, UI,
CATALOGUE, DOC-DRIFT, STORAGE, NETWORK.

## Session 7 — `project-management` (opening `84490ec`, 3084 tests, 40 failures, 6 errors)

Probes: `qa/probe_pm_shelf.py` (inventory, declared form, K1 registry audit, K5 refusals),
`qa/probe_pm_paper.py` (builds the `.docx` through the real path and reads `word/document.xml`).
Manual: `qa/manual/project-management.md` (62 E-rows).
Suite: `tests/test_subject_project_management_acceptance.py` (62 tests).

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-PM-01 | project-management | PM-05, PM-06, PM-09, PM-15, PM-16; E-pm-049, E-pm-050 | MAJOR | WIRING | `qa/probe_pm_shelf.py --blocks` reported `cues: ['evidence']` on every block of five profiles, and queries built from the raw block key (`scope_in evidence`, `work_packages evidence`) | the five profiles were inlined with placeholder search vocabulary: one shared cue word meant the gate could not attribute an item to a dimension, and the student's query was a snake_case token instead of the framework's language | `session 7` | `test_E_pm_049`, `test_E_pm_050` | FIXED |
| D-PM-02 | project-management | PM-10 RACI (shared with the people shelf); E-pm-058 | MAJOR | DECLARATION | `framework_profiles.get('template_raci')['subject']` → `'management'` while `R.get('PM-10')['template'] == 'template_raci'` and **both** pages list PM-10 | the profile was authored under the management shelf's vocabulary; nothing asserted the subject against the catalogue id | `session 7` | `test_E_pm_058` | FIXED |
| D-PM-03 | marketing (ledgered from this shelf) | `template_servqual` still; `template_customer_journey` repaired; E-pm-057 | MAJOR | DECLARATION | `sorted(set(T.CANVAS_BLOCKS) & set(T.MATRIX_META))` → both templates at session start; `['template_servqual']` after `2209822`/B-198 | a block may declare exactly ONE form. The customer journey half was repaired by the marketing lane during this session (D-MKT-04); SERVQUAL's grid is still in both maps and its tile is hidden until that is repaired | `2209822` (their half) | `test_E_pm_057` (asserts the measured pair) | **LEDGERED** — one kind still open, marketing shelf owns it |

| D-PM-04 | project-management | `case_decision` card; E-pm-014 | MINOR | DECLARATION | the card is `kind: compute` and `case_decision` is **not** in `bp.methods.LIBRARY` | it is a **T2 template** (registry `QNT-FIN-01`) that computes NPV inside the template path and delivers through `Pipeline` — declared `compute` is honest | — | `test_E_pm_014` | **NOT A DEFECT** (measured, pinned) |

### Session 7 — the shelf's declared gaps

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| G-pm-01 | project-management | every `probe`-profile worksheet; V-01/V-12 | MAJOR | HONESTY (owner policy) | `qa/probe_pm_paper.py` → **ten of ten** H2 blocks of the charter paper carry `background`, none carries a gap | `completion.py:381-390` fills an unsourced part with the framework's own background on the owner's instruction, and the paper discloses it | — | `test_E_pm_054`, `paper-read.json` | **GAP** (declared, disclosed) |
| G-pm-02 | all shelves | 17 profiles reachable from no subject page (K3) | MAJOR | WIRING | `qa/probe_pm_shelf.py` → `profiles on no subject page : 17` | none of them is on this shelf; adding worksheet rows changes the catalogue surface | — | — | **GAP** — owner decision |
| G-pm-03 | project-management | risk register figure; E-pm-047 | MINOR | WIRING | `matrix.layout_for('template_risk_register')` → `None`, while `layout_for('template_raci')` → a layout | the risk register's matrix is drawn by the `MATRIX_META` builder, not by a `matrix.LAYOUTS` figure geometry | — | `test_E_pm_047` | **GAP** (declared) |
| G-pm-04 | project-management | a rate entered as `6`; E-pm-040 | MINOR | VALIDATION | `Pipeline` delivers; `appendix['ambiguities']` says "the rate is taken as given" | the frozen core does not bound a rate; the run discloses the convention instead of rescaling it | — | `test_E_pm_040` | **GAP** (declared, disclosed) |

### Session 7 — the counts this shelf must not drift from

| Measure | Value | Where it is asserted |
|---|---:|---|
| Compute tools | 18 | `test_E_pm_001` |
| Worksheets / records / theories / glossary | 6 / 10 / 0 / 23 | `test_E_pm_002`…`004` |
| Declared tiles | 0 (fallback layout) | `test_E_pm_006` |
| Framework profiles overall | 75 | `test_E_pm_004` area |
| Registry kinds declared in two forms | 1 (`servqual`; customer journey repaired by D-MKT-04) | `test_E_pm_057` |
| Items on the shelf that complete from a brief | 6 of 16 | manual §2.2 |

---

## Session 1 — `accounting` (baseline `97544f7`, 2548 tests, 86 failures, 13 errors)


| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ACC-01 | accounting | Every capability paper; E-acc-043 | BLOCKER | UI/FORMAT | `python qa\probe_accounting_papers.py` before the fix: the loan and tax sections printed `payment: 4151.67104527080196364014…`, and the ratio section printed the whole `_appendix` dict | `src/bp/product/chat.py` defined `_capability_lines` **twice** (line 4060 the real prose formatter, line 4530 a `key: value` stub). The later definition shadowed the earlier one at import | this session (chat.py) | `test_E_acc_043__papers_read_as_prose_not_raw_decimals`; baseline `test_a_bespoke_formatter_reports_the_core_numbers_as_money`, `test_a_finance_paper_reports_the_cash_conversion_cycle`, `test_a_cohort_paper_takes_a_retention_matrix`, `test_a_currency_conversion_takes_codes_and_a_declared_rate` and 8 more `test_capabilities` cases | FIXED |
| D-ACC-02 | accounting | Chained inputs in a paper; E-acc-046 | MAJOR | HONESTY | `tests/test_plan_dependencies.py::…chained_input…` and `tests/test_plan_verifier.py::…export_states_where_a_chained_figure_came_from` failed | the same file defined `_declared_inputs_line` twice; the stub dropped `" (from the … result)"`, so a derived figure read as one the student typed | this session (chat.py) | `test_E_acc_046__a_chained_input_names_its_source` + those two baseline tests | FIXED |
| D-ACC-03 | accounting | Trend paper; E-acc-044 | MAJOR | WIRING | `chat.CAPABILITY_LINES["trend_analysis"] is chat.CAPABILITY_LINES["trend_forecast"]` returned **True**; the accounting trend paper would print forecast fields | `_trend_lines` was defined twice (forecast at 3077, trend at 3241); `CAPABILITY_LINES` is built before the second definition, so **both** entries captured the forecast formatter | this session (chat.py: renamed to `_forecast_lines`, remapped `trend_forecast`) | `test_E_acc_044__each_capability_uses_its_own_formatter` | FIXED |
| D-ACC-04 | accounting | Ratio / loan / tax papers; E-acc-043 | MAJOR | ROUNDING | `qa\probe_accounting_papers.py`: `asset turnover 1.66666666666666666666…`, `payment 4151.67104527…`, `eoq 353.55339059…` | `_ratio_lines` used `_fmt_exact` for plain ratios, and `loan_amortization` / `tax_declared` had no bespoke formatter, so `_generic_lines` printed the core's full Decimal | this session (chat.py: `_fmt_number` for ratios; new `_loan_lines`, `_tax_lines`) | `test_E_acc_043__papers_read_as_prose_not_raw_decimals` | FIXED |
| D-ACC-05 | accounting | Framework-chat routing; E-acc-049 | BLOCKER | GATE | `chat.start("Prepare the journal entries and the trial balance …", "any")["stage"]` returned `"clarify"` with framework `pestel` — an accounting computation wrapped in a PESTEL paper | `chat.start` computed `fits, message` and then ignored them: the `if not fits:` block was gone, and the `_fit` computation-boundary hunk was gone (documented in `docs/CONTINUATION_NOTE.md`, work order WO-1) | this session (chat.py) | `test_E_acc_049__a_pure_accounting_brief_is_refused_and_named`; baseline `test_open_pure_accounting_refused`, `test_a_computation_brief_is_refused_instead_of_forced_into_pestel` | FIXED |

### Fixed under owner approval (unfreezes B-179…B-181)

| ID | Subject | Feature / E-id | Severity | Class | Repro (before the fix) | Root cause | Decision | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ACC-06 | core (`methods.py`) | `tax_incidence` / `risk_metrics` / `social_welfare` units; E-acc-052 | MAJOR | UNITS | `qa\probe_shadowing.py`: `tax_incidence.typing("producer_share")` → `("currency", 2)`; `risk_metrics.typing("mean_return")` → `("periods", 2)`; `social_welfare.typing("n")` → `("rate", 4)` | six hooks under three names, each defined twice; the last definition wins, so every `Method(...)` captured another method's block | **B-179** (owner unfreeze) | `test_E_acc_052__each_method_owns_its_typing_hook` + `qa/probe_duplicates.py` (0 duplicates) | FIXED |
| D-ACC-07 | routing (`guard.py`, `chat.py`) | Subject-vocabulary refusal; E-acc-053 | MAJOR | REFUSAL | `tests/test_product_home_routing.py::test_shelf_mode_control` expected *"does not look like a management or strategy instruction"*; the brief was refused by `_fit`'s external-evidence rule instead | `guard.subject_fit()` returned `(True, None)` unconditionally | **B-180** (owner decision) | `test_E_acc_053__a_brief_for_another_shelf_is_refused_by_vocabulary` + the restored `test_shelf_mode_control` | FIXED |
| D-ACC-09 | core (`orchestrator.py`) | Unknown method; E-acc-051 | BLOCKER | GATE | `Pipeline().run({"method":"no_such_method","inputs":{}}, …)` → **`delivered`** with a T4 "no computed answer is given" report | `resume()` treated a missing `LIBRARY` entry as "escalate to framework-only" instead of refusing | **B-181** (owner unfreeze) | `test_E_acc_051__an_unknown_method_is_refused` | FIXED |

### Blocked and parked (not fixed, not faked)

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ACC-08 | accounting (docs) | Practice set Q3–Q4 | MINOR | DOC-DRIFT | `docs/ACCOUNTING_STUDENT_GUIDE.md` §"Practice set" asks a queueing question and a line-balancing question; the answers live on the Operations shelf (`OPERATIONS_GROUPS`) | the practice set was copied across shelves | — | — | **GAP** (G-acc-08) |
| D-ACC-10 | accounting | Tool cards; E-acc-018 | MINOR | CATALOGUE | `subjects.detail("accounting")["tools"][i]["need"] is None` for all 12 tools, while other shelves declare "what to gather" | `TOOL_NEEDS` has no accounting key | — | `test_E_acc_018__missing_need_text_falls_back_and_is_ledgered` (asserts the fallback) | **GAP** (G-acc-01) |

### Baseline failures this session repaired (root cause D-ACC-01…05)

`test_capabilities` (12), `test_plan_verifier` (2), `test_plan_dependencies` (1),
`test_conductor_frameworks` (1), `test_chat` (1), `test_product_home_routing` (1).
Opening list: `qa/baseline/failure_list.txt`. Closing count: `qa/QA_STATE.md`.

### Carried forward, deliberately (other shelves)

Every failure whose root cause is a worksheet profile, prompt or outline on another shelf —
value chain, RFM, SERVQUAL, STP (+STP evidence), TAM, Kano, CRO, digital mix, AIDA, BCG, brand

## Session 2 — `economics` (baseline `ab0be0d`, 2627 tests, 66 failures, 13 errors)

The shelf's computation layer is in good shape: **all 59 tools deliver through their preset, all
of their own checks pass, and every one of the 23 reproducible worked examples in
`docs/ECONOMICS_STUDENT_GUIDE.md` matches hand arithmetic** (`qa/baseline/econ_examples.txt`).
No economics test appears in the 79-item baseline failure list. The defects below are the ones
that survived that sweep.

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ECO-01 | economics | `labour` tool; E-eco-081 | MAJOR | UNITS | `LIBRARY["labour_market"].impl({nominal_wage:100, cpi:110, labour_productivity:50, unemployment_rate:0.06, vacancies:300})` → `wage_share_of_productivity=1.8181…`, `labour_market_tightness=5000`; `typing()` returned `("currency", 2)` for both, and for `vacancies` | `_labour_typing` (methods.py) named only `cpi`/`labour_productivity` (ratio) and `unemployment_rate` (rate); every other output fell through to `currency`, so a share and a ratio printed as money | this session (B-190, `_labour_typing`) | `test_E_eco_081__a_share_and_a_count_are_not_typed_as_money` | **FIXED** — paper now reads "the wage share of productivity is 0.7937" |
| D-ECO-02 | economics | `labour` tightness formula; E-eco-082 | MAJOR | FORMULA | same repro: `labour_market_tightness = vacancies / unemployment_rate = 300 / 0.06 = 5000`. Standard definition is vacancies per **unemployed person**; with 500 in the labour force at 6%, unemployed = 30, so tightness = 300/30 = **10** | `labour_market_impl` divides a count by a *rate*. The declared input is documented as "optional unemployment rate as a fraction for tightness", so the result is a count per unit-of-rate. `docs/OPEN_ISSUES.md` 11b/11c already names this | — | `qa/baseline/econ_labour_typing.txt` | **BLOCKED** — owner decision: which correct definition replaces it, and whether a new input enters the frozen schema. Owner ruled it must not fall back to dividing by a rate |
| D-ECO-03 | economics | `currency` tool; E-eco-083 | MAJOR | HONESTY | Preset `currency` (USD 1,000 → EUR at 0.92) delivered *"At the declared rate, **EUR** 1,000.00 converts to EUR 920.00."* The computation was right (920 EUR); the **source** amount was labelled with the target currency | `currency_convert`'s template rendered `tok("amount_from")` with the row's currency, not `from_currency`. The product formats correctly from the core, so the defect was the template's own words | this session (B-190, `_cc_template`) | `test_E_eco_083__the_conversion_never_mislabels_the_source_amount` | **FIXED** — paper now reads "At the declared rate, EUR 920.00 is the converted amount … recorded in the appendix" |
| D-ECO-04 | economics | 52 tool cards; E-eco-080 | MINOR | CATALOGUE | `subjects.detail("economics")["tools"][i]["need"] is None` for 52 of 59 tools | `TOOL_NEEDS` carries only the seven cross-shelf tools (`npv`, `forecast`, `descriptive`, `pearson`, `ols`, `chi_square`, `power`); every tile still carries a group-level `need`, so the student is not blind | — | `test_E_eco_080__a_missing_need_line_falls_back_and_is_ledgered` (asserts the fallback) | **GAP** (G-eco-01) |
| D-ECO-05 | economics | No worksheets, frameworks or theories on the shelf | GAP | — | `detail("economics")["worksheets"] == []`, `["theories"] == []`, and no record names a `template` | Declared scope: `CURRICULUM_MAP.md` places the shelf's coverage entirely in tools; `does_not` says it computes only what is declared | — | — | **GAP** (G-eco-02) |
| D-ECO-06 | economics | VAR, cointegration, unit-root tests | GAP | — | Not in `LIBRARY` | `PARKED_QUEUE.md` item 7; `CURRICULUM_MAP.md` named gaps; `ECONOMICS_STUDENT_GUIDE.md` "Not covered yet" | — | — | **GAP** (G-eco-03) |
| D-ECO-07 | economics | Diagram renderer, economics catalogue section | GAP | — | Not built | `ECONOMICS_STUDENT_GUIDE.md` "Not covered yet"; `CURRICULUM_MAP.md` named gaps | — | — | **GAP** (G-eco-04) |
| D-ECO-08 | economics (docs) | `CURRICULUM_MAP.md` tool count; E-eco-084 | MINOR | DOC-DRIFT | Row said "55 tools"; the catalogue has **59** | the shelf grew and the map did not | this session (`docs/CURRICULUM_MAP.md`) | `test_E_eco_084__the_curriculum_map_states_the_true_tool_count` | **FIXED** |
| D-ECO-09 | economics (verification) | Carried-forward D-ACC-06 `tax_incidence` units claim | MINOR | UNITS | `LIBRARY["tax_incidence"].typing("producer_share")` → `('ratio', 4)`; `typing("equilibrium_quantity_no_tax")` → `('units', 2)`; `typing("consumer_incidence")` → `('currency', 2)` — all **correct** at `ab0be0d`, contrary to session 1's repro | the session-1 observation no longer reproduces on this tree; the duplicate `_tax_typing` definitions remain (the shadowing bug class is real) but do not mislabel `tax_incidence` today | — | `qa/baseline/econ_tax_typing.txt` | **CLOSED — not reproducible** (D-ACC-06 stays open for the duplicate definitions themselves) |

### What this session deliberately did not do

- **Did not touch** `tests/fixtures/frozen_contract.json` or `docs/sources/**`.
- **Did not encode the three BLOCKED defects as failing tests.** A red suite hides the next real
  regression; each is reproduced with numbers in the ledger and in `qa/baseline/`.
- **Did not invent** the missing `need` text, a tightness denominator, or a currency label.
- **Did not weaken** any existing check: the 122 tests across the economics slice and the ten
  owner-contract files pass unchanged.
- **Skipped `finance`.** The recorded order has `finance` as session 2; the owner's work order for
  this session named `economics`. That is an explicit owner instruction, recorded in
  `qa/QA_STATE.md` — not a silent reordering. `finance` is still "not started".

equity, attribution, funnel, email/CRM, marketing automation, change organisation, operations
examples, the PESTEL refusal path, capability runner seeds and the registry import counts. They
belong to those shelves' sessions; the reason for each is recorded in `qa/QA_STATE.md`.

Network/ENV-dependent failures (retrieval timeouts, Brave→Firecrawl) are reported, never deleted.

## Session 2 — `finance` (baseline `ab0be0d`, 2630 tests, 66 failures, 13 errors)

*(A concurrent `economics` pass also calls its section "Session 2"; this one is finance's. See
`qa/QA_STATE.md` §1 for why the tree carries both.)*

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-FIN-01 | finance (core) | `dcfmid` tile; E-fin-007, E-fin-017 | BLOCKER | GATE | before: `Pipeline().run(server.PRESETS["dcfmid"], lambda s: True)` → `status="blocked"`, reason `"checks failed after 0 amendment(s): ['mid_year_convention_raises_the_value']…"`; now: `status="delivered"` | `src/bp/methods.py::_dcf_tests` built `mid = impl({**inp, "timing": "mid"})` and compared it with `base = impl(inp)`. The `dcfmid` preset already declares `timing="mid"`, so the two were equal and the strict `>` could never hold — the check compared the input with itself. The method was always correct (independent recomputation to 40 digits) | **B-183** (owner-approved unfreeze of the B-079 core contract) | `test_007__…` (no self-check fails on its own preset) and `test_017__…` (the mid-year tile delivers) | **FIXED** — `scripts/econ_shelf.py --check` still reports "frozen fixture: in sync" |
| D-FIN-02 | finance | Capability papers; E-fin-047, E-fin-048 | BLOCKER | ROUNDING / UI | `qa/probe_finance_papers.py` before the fix: *"future value 412169.50589505043384053371598616910344392272576332"*, *"recover the outlay in 3.0192500000000000000000000000000000000000000000000 periods"*, *"a profitability index of 1.2679461785397172324294788607335564510620859230927"* | `src/bp/product/chat.py` had no formatter for `time_value`, `leverage_analysis` or `equity_bridge` (they fell through to `_generic_lines`, which quotes the recorded output verbatim), and `_payback_lines`, `_project_metrics_lines` and `_unit_economics_lines` called `_fmt_exact` on computed non-integers, which returns the raw text by design | this session (`src/bp/product/chat.py`) | `test_047__capability_papers_print_money_at_two_decimals`, `test_048__every_finance_capability_has_a_formatter_or_a_ledgered_gap` | FIXED |
| D-FIN-03 | finance | `chat._generic_lines`; G-fin-08 | MINOR | HONESTY | any capability without a bespoke formatter still echoes the core's output verbatim | by design the fallback claims nothing beyond the recorded output, but it prints it at full precision | — | `test_048…` (asserts every *finance* capability now has one) | **GAP** (G-fin-08) |
| D-FIN-04 | finance | The missing manual | MAJOR | DOC-DRIFT | no `qa/manual/finance.md` existed | no acceptance manual had been written for this shelf | this session | the manual itself, §1–§10 | **CLOSED** (deliverable) |
| D-FIN-05 | finance | The missing acceptance suite | MAJOR | VALIDATION | `tests/test_subject_finance_acceptance.py` did not exist | no executable proof of the shelf's claims | this session | 50 tests, one per E-row | **CLOSED** (deliverable) |
| D-FIN-06 | finance | `tests/test_finance_additions.py::test_the_finance_page_groups_tools_and_carries_study_notes` | MINOR | DOC-DRIFT | `FAIL: … the finance grouping must not leak onto the economics page`; economics now declares its own groups (`market_basics`, `firm_behaviour`, …) | the assertion `all(tool["group"] is None for tool in economics["tools"])` encoded a time when economics had no grouping; the intent (no *finance* group name on the economics page) is still right | this session (`tests/test_finance_additions.py`) | the same test, now asserting no finance group name appears | FIXED |
| D-FIN-07 | finance | Market data, credit/liquidity risk, portfolio optimisation, real options; G-fin-01…04 | GAP | — | `detail("finance")["does_not"]`; `docs/CURRICULUM_MAP.md` named gaps | declared non-goals | — | `test_035__the_three_declared_non_goals_are_present` | **GAP** (declared) |
| D-FIN-08 | finance | `ols_robust` has no preset; G-fin-05 | MINOR | WIRING | `tool("ols_robust")["preset"] is None`; the frozen `server.PRESETS` (144) has no entry launching `ols_robust` | a preset is part of the frozen contract, so one cannot be added without an unfreeze; the schema-driven form still runs the method | — | `test_005__every_tool_except_ols_robust_has_a_matching_preset` | **GAP** (G-fin-05) |
| D-FIN-09 | finance | RSK-04 status wording; G-fin-06 | MINOR | CATALOGUE | RSK-04 says "not implemented" but `status_short` reads "No worksheet yet", because `FORM_SHORT["read_only"]` is a single label | two different facts share one short label | — | `test_029__a_not_implemented_record_is_read_only` (asserts the form, not the wording) | **GAP** (G-fin-06) |
| D-FIN-10 | finance | 25 of 35 tools have no "what to gather" text; G-fin-07 | MINOR | CATALOGUE | `[t["key"] for t in tools() if not t["need"]]` → 25 keys | `subjects.TOOL_NEEDS` has no finance keys; same class as accounting's G-acc-01 | — | `test_037__missing_need_text_is_named_as_the_recorded_gap` | **GAP** (G-fin-07) |
| D-FIN-11 | finance | `docs/CURRICULUM_MAP.md` said "33 tools … plus `trend_analysis`"; G-fin-09 | MINOR | DOC-DRIFT | the shelf has 35 tools | the count drifted when `case_decision` and the currency tool were added | this session (`docs/CURRICULUM_MAP.md`) | `test_001__catalogue_counts_match` | FIXED |
| D-FIN-12 | finance | Calculator router phrasing; E-fin-040 | MINOR | WIRING | `calc_router.plan("price this bond")["method"] is None` and `plan("what is the duration of my bond")["method"] is None`, while `plan("bond price")` reaches `bond_analysis` | `_score` needs ≥4 points and a two-token label overlap scores 2; the threshold is deliberately conservative | — | `test_040…` asserts the documented phrases route and that an unplaced sentence returns alternatives | **GAP** — parked: the threshold is shared by all 11 shelves, so it belongs to a cross-shelf routing session |
| D-FIN-13 | core (inherited) | `tests/test_pipeline.py::test_no_method_is_framework_only` | MAJOR | DOC-DRIFT | `FAIL: AssertionError: 'No computed answer' not found in ''` — the test expected `{"method": "mystery"}` to deliver a T4 framework-only paper | owner decision **B-181** ("an unknown method name fails closed") was in the tree uncommitted when this session opened, and the test still encoded the old behaviour. The core pass committed the unfreezes at 19:53 (`4e842f0`) and replaced the test, so the failure is gone from the closing set | `4e842f0` (the core pass, not this one) | the closing set has 0 new names and 2 fewer (`qa/QA_STATE.md` §1) | **CLOSED** — verified in `qa/baseline/fin_ci_failures.txt` |

### Session 2 — accepted with a named exception

The finance acceptance suite is **50 tests, 50 passed** (`qa/baseline/fin_acceptance.txt`), and the
finance slice of the existing suite is **147 passed** (`qa/baseline/fin_slice1.txt`). Two E-rows are not
`PASS` by test and are ledgered instead: **E-fin-005** (G-fin-05, no preset for `ols_robust`) and
**E-fin-007** (D-FIN-01, the frozen mid-year check). Both tests still run and pin the measured
behaviour, so a change in either is a red test rather than a silent drift.

## Session 6 — `entrepreneurship` (opening `b2987fc`, 2932 tests, 66 failures, 13 errors)


---

## Session 6 — `marketing` (started 2026-11-03; manual and full E-row table not written yet)

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-MKT-01 | marketing | All 16 completion test files; E-mkt-001…005 | MAJOR | DOC-DRIFT | `qa/baseline/mgt-completion-after.txt`: 27 failures, every one on marketing — `test_four_cells_each_carry_a_sourced_item_or_a_named_gap` expected `["segmentation", "targeting", "positioning", "product"]` from a profile that declares ten blocks (4 STP + the 7 Ps), and `outline["framework"]` expected "Kano" from a profile labelled "Kano Model" | the profiles and their forms grew (7 Ps, longer framework names) and the tests kept the old, shorter declarations; measured for **all 21** marketing profiles: profile keys == `templates.CANVAS_BLOCKS`/`MATRIX_META` keys, label == `outline.framework`, and the prompt names the label — so the tests were the only stale copy | this session (`tests/test_*_completion.py` ×16) | `test_E_mkt_001…005` in `tests/test_subject_marketing_acceptance.py` (the profile/form/paper/prompt agreement for all 21 profiles) | FIXED |
| G-mkt-01 | marketing | Manual, E-rows, click-through, ledger | GAP | — | `qa/manual/marketing.md` does not exist | session 6 is in progress: 24 tools, 29 records, 48 glossary terms and 21 profiles are more than one sitting | — | — | **GAP** (declared, next session) |


---

## Session 4 — `management` (baseline `211b672`, 2932 tests, 66 failures, 13 errors)

Probes: `qa/probe_mgt_shelf.py` (inventory, one mocked run per profile), `qa/probe_mgt_paper.py`
(builds the papers and reads `word/document.xml` back — P6). Manual: `qa/manual/management.md`
(46 E-rows). Suite: `tests/test_subject_management_acceptance.py` (46 tests).

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-MGT-01 | management | Every profile; E-mgt-040 | BLOCKER | WIRING | rename the temp file and run `python -c "import bp.product.framework_profiles"` → `FileNotFoundError` | `framework_profiles.py` ran `exec(open(r"C:/tmp/profiles_out.py").read())` at import time; eight profiles (BMC, Lean Canvas, VPC, Project Charter, WBS, Risk Register, Stakeholder Plan, Lessons Learned) existed only in that file and `PROFILES` named them, so the module could not import on any machine without it | `29d0509` | `test_E_mgt_040__the_profiles_module_imports_nothing_outside_the_repository` | FIXED |
| D-MGT-02 | management | Value-chain figure; E-mgt-015 | MAJOR | WIRING | `qa/probe_mgt_paper.py` before: the Figure 1 grid drew nine labelled boxes with no bullet and no gap | the chain layout in `matrix.LAYOUTS` keys its nine bands by short names while the profile and `templates.CANVAS_BLOCKS` key them by the long names, and `matrix.ALIASES` had no `template_value_chain` entry, so every lookup returned `{}` | `29d0509` | `test_E_mgt_015__the_canvas_figure_carries_one_bullet_per_activity` | FIXED |
| D-MGT-03 | management | Value-chain cells; E-mgt-016, E-mgt-017 | BLOCKER | HONESTY | `qa/probe_mgt_shelf.py` with no sources: `procurement items=['student']` fed from a brief sentence containing the word “cost”; the other eight cells empty | the nine blocks were `fill: "auto"`, which falls back to quoting the brief into any block whose cue appears anywhere in it, and which excludes the block from the background/gap policy that `probe` profiles rely on | `29d0509` | `test_E_mgt_017__a_cell_with_no_source_says_so_in_the_paper` | FIXED |
| D-MGT-04 | management | firm infrastructure; E-mgt-016 | BLOCKER | WIRING | with a realistic title (“Overhead costs and administrative support functions in grocery retail”) the block accepted nothing; only a title echoing the query passed | the block asked “firm infrastructure and overhead” with cues `infrastructure planning finance legal quality governance management`: no cue for overhead, support, administrative or firm, and the gate needs a cue **and** the industry in the title | `29d0509` | `test_E_mgt_016__firm_infrastructure_accepts_real_overhead_evidence` | FIXED |
| D-MGT-05 | management | Porter's Value Chain; E-mgt-014 | MAJOR | DETERMINISM | `Select-String VALUE_CHAIN = {` returned two; the first (short keys) was dead | the module declared the framework twice and the second assignment won, so the file read as if it declared the short names the tests used | `29d0509` | `test_E_mgt_041__every_profile_is_declared_once_in_the_module` | FIXED |
| D-MGT-06 | management | Change and Organization; E-mgt-023 | MAJOR | VALIDATION | `completion.complete("template_change_organization", …, industry="healthcare")` raised “Name the change you are planning” for every brief | the profile declared `unit.field = "process"`, so the industry was never the unit of analysis and the refusal did not name the market | `29d0509` | `test_E_mgt_023__the_unit_of_analysis_is_the_industry` | FIXED |

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ENT-01 | entrepreneurship | A marking guide attached to the business plan; E-ent-075…079, E-ent-101 | MAJOR | WIRING | before: `chat.start(BRIEF, profile="business_plan", rubric=RUBRIC)` raised `TypeError: start() got an unexpected keyword argument 'rubric'`; the plan drafted 22 sections with no coverage table, and `paper.missing` never saw a rubric | the rubric was wired into `completion.complete` (the worksheet path) only. The plan is a **second engine** that runs through `chat.start`, which took no `rubric`, stored none, and `_draft_plan` measured nothing — while `paper.missing` already read `state["rubric"]` | this session (`src/bp/product/chat.py`, `api.py`, `web/index.html`) | `test_e_ent_075…077`, `test_e_ent_101` | FIXED |
| D-ENT-02 | entrepreneurship | A plan block's columns through the dataset mapper; E-ent-102…104 | MAJOR | REFUSAL | before: `intake.mapped_request(id, "proforma_statements", {"revenue": "revenue", "operating_costs": …})` → `IngestError: the mapped columns do not form a valid request … missing required input 'gross_margin_rate'` | `bp.ingest.to_method_inputs` refused a mapping that left a required **scalar** out, although the plan block it serves mixes list columns with typed drivers. A partial proposal is what the product asks for; only what a mapping gets wrong should refuse | this session (`src/bp/ingest.py`) | `test_e_ent_102`, `test_e_ent_103` (refusal kept), `test_e_ent_104` (nothing executes) | FIXED |
| D-ENT-03 | rubric (surfaced on this shelf) | A list rubric's word budget and a criterion's stem; E-ent-105…106, E-ent-075 | MAJOR | VALIDATION | before: `rubric.parse("…\nWord limit: 2,500 words +/- 10%\n")` returned **six** criteria, the sixth named `Word limit: 2,500 words +/` with weight 10, and `total_weight` 110; `_covers("References", "Referencing")` was False | `_read_list` read the tolerance's `%` as a weight; `_covers` compared whole tokens only, so a gerund criterion never matched the noun heading. A phantom weighted criterion blocks a complete paper for ever, and a false gap does the same | this session (`src/bp/product/rubric.py`) | `test_e_ent_105`, `test_e_ent_106` | FIXED |
| D-ENT-04 | core (inherited, all shelves) | Eight presets that declare no period; E-ent-007, E-ent-012/019/020 | BLOCKER | GATE | before: `Pipeline().run(server.PRESETS["descriptive"])` → `blocked: reference failure: RefMismatch('token wants n/None, artifact is n/None')` — identical on both sides; `pearson` raised `TypeError: replace() argument 2 must be str, not None`. Now 46 of 46 entrepreneurship tools deliver | the period was passed to the method's template as `None`, which the template wrote into its reference token as the **text** `None`; `ArtifactStore.resolve` then compared that text with a real `None`. `corr_template` additionally called `str.replace` with a non-string. Eight presets across accounting, finance/research and this shelf were blocked, three of them on this shelf | this session (`src/bp/artifacts.py`, `src/bp/orchestrator.py`) | `test_e_ent_007` (all 46), `test_e_ent_011…056` | FIXED |
| D-ENT-05 | entrepreneurship | The engine that read a brief; E-ent-098 | MINOR | HONESTY | `POST /api/cases/brief` with an image read by the vision model returned `method: image_ocr_model` and **no** `engine`, no `filename`, and the plan page said only "Brief read from image_ocr_model" | the route returned the reader's result unchanged while the intake record (a different path) did carry `engine`. B-191 says the file says what read it; the caller could not | this session (`src/bp/product/api.py`, `intake.py`, `web/index.html`) | `test_e_ent_098` | FIXED |
| D-ENT-06 | entrepreneurship | Term sheets, liquidation preference, anti-dilution, multi-round cap tables, conjoint, survival models, Monte Carlo; G-ent-01, G-ent-02 | GAP | — | `CURRICULUM_MAP` *Named gaps*; `KNOWN_LIMITATIONS.md` | declared non-goals | — | `test_e_ent_047` covers the single round only | **GAP** (declared) |
| D-ENT-07 | entrepreneurship | 36 of the 46 tools declare no `need` text; G-ent-03 | MINOR | CATALOGUE | `[t["key"] for t in tools if not t["need"]]` → 36 keys | `subjects.TOOL_NEEDS` has no entrepreneurship keys; same class as accounting's G-acc-01 and finance's G-fin-07 | — | `test_e_ent_003` asserts the fields that do exist | **GAP** (G-ent-03) |
| D-ENT-08 | entrepreneurship | No theory row on the shelf; G-ent-04 | MINOR | CATALOGUE | `detail("entrepreneurship")["theories"] == []` | a reading lens is reached by naming it in a brief, not by a tile — the same rule the economics shelf follows | — | `test_e_ent_001`, `test_e_ent_086` | **GAP** (G-ent-04) |
| D-ENT-09 | entrepreneurship | No dataset picker on a plan block; G-ent-05 | MINOR | WIRING | the plan form takes typed values only; a mapping is consumed in the Calculator form | B-192 declares the picker surface open; this session fixed the mapper's refusal, not the surface | — | `test_e_ent_102` proves the proposal exists | **GAP** (G-ent-05) |
| D-ENT-10 | core (`server.PRESETS`) | `case` (no `method` key) and `unsupported` (a deliberately unknown method); G-ent-06 | MINOR | CATALOGUE | `server.PRESETS["case"]` has no `method`; `unsupported` blocks with "unknown method 'monte_carlo_valuation'" | both are fixtures for B-181's fail-closed test, not tools; no shelf offers them | — | `test_e_ent_005` iterates the shelf's own presets | **GAP** (G-ent-06) |
| D-ENT-11 | entrepreneurship (docs) | `CURRICULUM_MAP.md` said "5 worksheets"; `KNOWN_LIMITATIONS.md` said "the only structured worksheet on the shelf is the SWOT evidence review (STR-18)" | MINOR | DOC-DRIFT | the shelf has **6** worksheets, five of them draftable | the shelf grew the canvases (B-106/B-107) and the counts were not carried forward | this session (`docs/CURRICULUM_MAP.md`, `docs/KNOWN_LIMITATIONS.md`) | `test_e_ent_001` (inventory) | FIXED |

**Accepted with a named exception.** The acceptance suite is **106 tests, 106 passed**
(`qa/baseline/ent_acceptance.txt`). Two rows are not `PASS` by test and are ledgered instead:
**E-ent-098** depends on the owner's OCR key being configured, so the test mocks the endpoint and
proves the wiring, not a live read; **E-ent-056** exercises the composite template through its
preset, not through `LIBRARY` (it is a template). Both tests still run and pin the measured
behaviour.


| D-MGT-07 | management | Model prompt; E-mgt-029…031 | MAJOR | HONESTY | `completion._system(HEAD_SYSTEM, …, _profile("template_bcg"))` contained no “industry” at all, and BCG's prompt began “with the portfolio” | `HEAD_SYSTEM` had no slot for the declared unit of analysis, so a profile could write an industry paper while the model was told nothing about the industry | `29d0509` | `test_E_mgt_031__every_industry_prompt_names_the_industry` | FIXED |
| D-MGT-08 | Every computation paper (`Npv`, `Facts`, `Alternatives`); E-mgt-039 | MAJOR | ROUNDING | `qa/probe_mgt_paper.py`: `Npv A1: 2586.4733808644797823276713689760481408096100978284` | four methods (`npv`, `pearson`, `spearman`, `descriptive_stats`) declared no `typing` hook, and `case_decision` is a template rather than a `Method`, so the product had no declared precision to print; `_render` also joined a list of dicts with `str()`, printing `Facts: {'text': '…'}` | this session — core hooks in `methods.py` (B-197 unfreeze) and `session_paper` reading the core's recorded precision | `test_E_mgt_039__every_method_declares_its_precision_and_no_paper_prints_a_raw_decimal` | FIXED |
| D-MGT-09 | management | Shelf catalogue count; E-mgt-046 | MINOR | CATALOGUE | `subjects.catalogue()` reports `catalogue_count: 28` while the same shelf lists 31 worksheet rows | STR-01, STR-07 and STR-18 are shown as worksheets but absent from `SUBJECT_DEFS["management"]["catalogue_ids"]` | — | `test_E_mgt_046__the_shelf_catalogue_count_omits_three_of_its_own_worksheets` | **BLOCKED** — the number is on the page: which side moves is the owner's call |
| D-MGT-10 | management | Every `-ies` profile's paper; E-mgt-018, E-mgt-020 | MAJOR | WORDING | the produced `.docx` read “that a activitie for which no evidence is recorded” and “A activitie without an accepted item” | `_draft_data` and `_sections` built the singular with `plural.rstrip("s")`, and the article was hard-coded as “a” | `29d0509` | `test_E_mgt_018__the_outline_headings_are_present_in_declared_order`, read back with `qa/probe_mgt_paper.py` | FIXED |
| D-MGT-11 | management | Every deliverable export; E-mgt-013, E-mgt-035 | BLOCKER | HONESTY (P3) | `deliverables.sections(bundle, "submission")` still returned the heading “How this was produced” with “Method: … (version 1.0.0)” and “Specification hash: …” | the footer was deleted from `session_paper` but `deliverables.block("citation")` printed the same block for every profile that listed it | `29d0509` | `test_E_mgt_035__no_paper_path_prints_a_specification_footer` | FIXED |

### Session 4 — the shelf's declared gaps

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| G-mgt-01 | management | Records, theories, glossary; E-mgt-004 | GAP | — | `detail("management")["records"] == []` | the shelf has no read-only record set by design | — | `test_E_mgt_004__…` | **GAP** (declared) |
| G-mgt-02 | management | Change and Organization reachability; E-mgt-043 | MAJOR | WIRING | collecting every shelf's worksheets, `template_change_organization` appears in none | the profile and its tests exist but no `WORKSHEETS` row was ever added, so no page reaches it; adding one changes the catalogue surface | — | `test_E_mgt_043__the_unreachable_profiles_are_the_measured_seventeen` | **GAP** — owner decision (catalogue surface) |
| G-mgt-03 | management | Six non-draftable worksheets; E-mgt-006, E-mgt-045 | GAP | — | `[s["catalogue_id"] for s in detail("management")["worksheets"] if not s["draftable"]]` | declared: the flag governs the student button, not the capability | — | `test_E_mgt_045__a_non_draftable_profile_still_produces_a_paper` | **GAP** (declared) |
| G-mgt-04 | management | `docs/VALIDATION_HARNESS.md` §7.2 said 22 unreachable profiles | MINOR | DOC-DRIFT | `test_E_mgt_043` measures **17** | the number moved as profiles were wired; the doc records a dated measurement, not a contract | this session (`docs/VALIDATION_HARNESS.md`) | `test_E_mgt_043__…` | FIXED (doc corrected) |
| G-mgt-05 | management | A no-source cell prints the framework's background | GAP | — | `qa/probe_mgt_paper.py` value-chain-nosource | owner policy for `probe` profiles (harness §6.5); the paper now discloses it before printing it | — | `test_E_mgt_017__…` | **GAP** (declared, disclosed) |

### Session 4 — the counts this shelf must not drift from

| Measure | Value | Where it is asserted |
|---|---:|---|
| Compute tools | 1 | `test_E_mgt_001` |
| Worksheets / catalogue ids on the shelf | 31 / 31 | `test_E_mgt_002` |
| Distinct worksheet templates | 30 (`template_swot` twice) | `test_E_mgt_007` |
| Framework profiles overall | 75 | `test_E_mgt_003` |
| Records / theories / glossary | 0 / 0 / 0 | `test_E_mgt_004` |
| Non-draftable worksheets on the shelf | 6 | `test_E_mgt_006` |
| Profiles no subject page reaches | 17 | `test_E_mgt_043` |
| Non-draftable profiles overall | 12 | `test_E_mgt_045` |


