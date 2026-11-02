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
| D-ECO-01 | economics | `labour` tool; E-eco-081 | MAJOR | UNITS | `LIBRARY["labour_market"].impl({nominal_wage:100, cpi:110, labour_productivity:50, unemployment_rate:0.06, vacancies:300})` → `wage_share_of_productivity=1.8181…`, `labour_market_tightness=5000`; `typing()` returns `("currency", 2)` for both, and for `vacancies` | `_labour_typing` (methods.py:7579) names only `cpi`/`labour_productivity` (ratio) and `unemployment_rate` (rate); every other output falls through to `currency`. A share and a tightness ratio therefore print as money in the delivered paper | — | `qa/baseline/econ_labour_typing.txt` (recorded, deliberately not a test) | **BLOCKED** — frozen core (B-079) |
| D-ECO-02 | economics | `labour` tightness formula; E-eco-082 | MAJOR | FORMULA | same repro: `labour_market_tightness = vacancies / unemployment_rate = 300 / 0.06 = 5000`. Standard definition is vacancies per **unemployed person**; with 500 in the labour force at 6%, unemployed = 30, so tightness = 300/30 = **10** | `labour_market_impl` (methods.py:7538) divides a count by a *rate*. The declared input is documented as "optional unemployment rate as a fraction for tightness", so the result is a count per unit-of-rate, not vacancies per unemployed person. `docs/OPEN_ISSUES.md` 11b/11c already names this | — | `qa/baseline/econ_labour_typing.txt` | **BLOCKED** — frozen core (B-079); needs an owner decision on the denominator (add an `unemployed` input, or retype/drop the output) |
| D-ECO-03 | economics | `currency` tool; E-eco-083 | MAJOR | HONESTY | Preset `currency` (USD 1,000 → EUR at 0.92) delivers *"At the declared rate, **EUR** 1,000.00 converts to EUR 920.00."* The computation is right (920 EUR); the **source** amount is labelled with the target currency | `currency_convert`'s own template (methods.py:2013) renders `tok("amount_from")` with the row's currency, not `from_currency`. The product formats correctly from the core, so the defect is in the template text | — | `qa/baseline/econ_reports.txt` | **BLOCKED** — frozen core (B-079) |
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
| D-FIN-01 | finance (core) | `dcfmid` tile; E-fin-007, E-fin-017 | BLOCKER | GATE | `Pipeline().run(server.PRESETS["dcfmid"], lambda s: True)` → `status="blocked"`, reason `"checks failed after 0 amendment(s): ['mid_year_convention_raises_the_value']…"`; `qa/baseline/fin_dcf_midyear.txt` | `src/bp/methods.py::_dcf_tests` builds `mid = impl({**inp, "timing": "mid"})` and compares it with `base = impl(inp)`. The `dcfmid` preset already declares `timing="mid"`, so the two are equal and the strict `>` fails. The *method* is correct: an independent recomputation matches it to 40 digits (end 1,750,939.14; mid 1,836,400.47; ratio 1.0488088481701515) | — (frozen core) | `test_007…` pins the single failing check; `test_017…` pins the correct numbers | **BLOCKED** — needs an owner unfreeze (B-079). Suggested fix: compare against the *other* convention when the input already declares one — `mid = impl({**inp, "timing": "end" if inp.get("timing") == "mid" else "mid"})` with the comparison direction following |
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



