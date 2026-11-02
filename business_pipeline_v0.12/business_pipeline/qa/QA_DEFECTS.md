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

### Blocked and parked (not fixed, not faked)

| ID | Subject | Feature / E-id | Severity | Class | Repro | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|---|
| D-ACC-06 | accounting (core) | `tax_incidence` output units | MAJOR | UNITS | `qa\probe_shadowing.py`: `LIBRARY["tax_incidence"].typing("equilibrium_quantity_no_tax")` → `("currency", 2)`; `typing("producer_share")` → `("currency", 2)` | `src/bp/methods.py` defines `_tax_typing` twice (5164 for `tax_incidence`, 13953 for `tax_declared`); the second shadows the first and `tax_incidence`'s contract captures the shadowing one. `_risk_typing` (4616/12616) and `_social_typing` (6441/10066) are duplicated the same way | — | `qa\probe_shadowing.py` (recorded, deliberately not a test) | **BLOCKED** — frozen core (B-079); needs an owner unfreeze + B-number |
| D-ACC-07 | accounting (routing) | Subject-vocabulary refusal | MAJOR | REFUSAL | `tests/test_product_home_routing.py::test_shelf_mode_control` expects *"does not look like a management or strategy instruction"*; `chat.start(<marketing brief>, "management")` now refuses through `_fit`'s external-evidence rule instead | `guard.subject_fit()` returns `(True, None)` unconditionally. Two documents disagree: `docs/CONTINUATION_NOTE.md` says the vocabulary was deleted by accident and must be restored; the function's docstring says "Home is the macro conductor … the subject field is advisory" | — | — | **BLOCKED** — owner B-decision (design convention) |
| D-ACC-09 | all subjects (core) | Unknown method; E-acc-051 | BLOCKER | GATE | `Pipeline().run({"objective":"x","method":"no_such_method","inputs":{}}, …)` returns **`delivered`** with a T4 "no computed answer is given" report | `orchestrator.resume` treats `LIBRARY.get(method) is None` as "escalate to framework-only" instead of refusing, so a typo'd method silently becomes a structure-only paper — contrary to `HANDOFF.md` non-negotiable 4 | — | reproduction recorded here (a trap test would fail on today's tree) | **BLOCKED** — frozen stage contract (B-079) |
| D-ACC-08 | accounting (docs) | Practice set Q3–Q4 | MINOR | DOC-DRIFT | `docs/ACCOUNTING_STUDENT_GUIDE.md` §"Practice set" asks a queueing question and a line-balancing question; the answers live on the Operations shelf (`OPERATIONS_GROUPS`) | the practice set was copied across shelves | — | — | **GAP** (G-acc-08) |
| D-ACC-10 | accounting | Tool cards; E-acc-018 | MINOR | CATALOGUE | `subjects.detail("accounting")["tools"][i]["need"] is None` for all 12 tools, while other shelves declare "what to gather" | `TOOL_NEEDS` has no accounting key | — | `test_E_acc_018__missing_need_text_falls_back_and_is_ledgered` (asserts the fallback) | **GAP** (G-acc-01) |

### Baseline failures this session repaired (root cause D-ACC-01…05)

`test_capabilities` (12), `test_plan_verifier` (2), `test_plan_dependencies` (1),
`test_conductor_frameworks` (1), `test_chat` (1), `test_product_home_routing` (1).
Opening list: `qa/baseline/failure_list.txt`. Closing count: `qa/QA_STATE.md`.

### Carried forward, deliberately (other shelves)

Every failure whose root cause is a worksheet profile, prompt or outline on another shelf —
value chain, RFM, SERVQUAL, STP (+STP evidence), TAM, Kano, CRO, digital mix, AIDA, BCG, brand
equity, attribution, funnel, email/CRM, marketing automation, change organisation, operations
examples, the PESTEL refusal path, capability runner seeds and the registry import counts. They
belong to those shelves' sessions; the reason for each is recorded in `qa/QA_STATE.md`.

Network/ENV-dependent failures (retrieval timeouts, Brave→Firecrawl) are reported, never deleted.

