# Stage 5 Build Brief: Quantitative Method and Verification Library

**Version:** 0.1  
**Date:** 2026-10-20  
**Status:** [PROVISIONAL] implementation addendum  
**Source authority:** `business_pipeline: Architecture Manual`, Version 0.3 (draft), dated 2026-10-19.

> This brief supplements the v0.3 manual; it does not replace or silently revise it. “Stage 5” here means Stage 5 of the **Build Charter** (Quantitative Method and Verification Library), not section 5 of the business-pipeline manual.

## 1. Copy-ready instruction to the coding model

You are implementing Stage 5 of the Initial Build Charter: the Quantitative Method and Verification Library. Before coding, read `business_pipeline_v0.3.docx` or `business_pipeline_v0.3.md` together with this brief. Inspect the repository, existing methods, tests, data contracts, sandboxing, logs, UI integration, and the current Stage 0–4 work. Do not assume the repository matches the manuals.

Implement the smallest tested increment that adds or formalizes a reusable quantitative method through the existing deterministic orchestration path. Each method needs validated inputs, explicit assumptions/defaults, a controlled implementation, generated artifacts, and independent verification appropriate to risk. Preserve T1–T4, frozen specifications, predeclared tests, amendment logging, provenance, typed quantities, fail-closed behavior, and offline promotion rules.

Do not implement all methods at once, the full framework registry, or the full accounting engine. Reuse sound existing code. If something required is missing, record it and proceed only with supported work. Report changed files, exact tests run/results, limitations, open decisions, and the next step. Never claim unexecuted tests passed.

## 2. In scope versus out of scope

**In scope:** quantitative-method registry/execution interface; typed input/output contracts; method formulas/defaults/assumptions; test fixtures; verification; artifacts/provenance; accurate T1/T2/T3/T4 status.

**Out of scope unless already required by existing code:** complete framework registry (Build Charter Stage 6); accounting ledger, journal and full statement engine (Stage 8); every statistical procedure; regression/forecasting production support without validation; runtime self-modification.

## 3. Binding rules from v0.3

- **P1:** Model proposes specs/code; all reported numeric results come from execution artifacts.
- **P3:** Tier by verifiability: T1 vetted library; T2 bespoke code with stronger verification; T3 bounded exploration; T4 framework/data-needs response with no computed answer.
- **P4 / Section 4:** deterministic code controls stage order and mandatory checks; agents cannot choose to skip verification.
- **P5 / Section 5.5:** freeze specification and tests before execution; log patches/amendments; builder cannot weaken verifier/thresholds silently.
- **P8:** failed required checks block/remove affected outputs.
- **P9:** numbers are re-performable from delivered files.
- **P10 / Section 10.1:** no runtime self-modification; offline proposals require regression/held-out tests and human review.
- **Section 5.4:** use the existing pinned sandbox; record hashes; computation network policy stays as specified.
- **Section 6:** preserve provenance (user, sourced, assumption, computed) and typed quantity metadata (value, unit, currency, period, scale, precision). Keep synthetic data explicitly distinct from observations.
- **Sections 5.6–5.7:** predeclare sensitivity ranges; render reports/tables from artifacts rather than model-typed numbers.
- **Sections 7–8:** match claim strength to evidence; quantitative results do not automatically justify causal or prescriptive conclusions.
- **Section 14:** maintain core, trap, held-out, adversarial, and regression tests.

## 4. Audit before coding

1. Locate the active repository, branch, entry points, runtime, dependencies, config, persistence, sandbox and test commands.
2. Inventory every existing quantitative method and its implementation/tests/output contract/status.
3. Confirm whether specs, plan freezing, provenance, typed quantities, run/artifact records, sandboxing, verification and tier labels already exist.
4. Run the baseline tests and record exact commands and results.
5. Compare implementation with source manual; create a gap register instead of wholesale replacement.

## 5. Provisional method order

Choose after the audit; reuse tested code rather than duplicate it.

| Priority | Candidate | Why | Essential verification |
|---|---|---|---|
| A | Break-even and contribution margin | Useful, deterministic, explainable | Units/currency consistency; zero/negative contribution; boundary cases; independent formula check |
| A | NPV and cash-flow scenarios | Useful for investment and case analysis | Rate 0 equals sum of cash flows; time-period and sign conventions; reference examples; precision policy |
| A | Sensitivity / decision-flip analysis | Exposes assumptions and decision boundaries | Freeze ranges before running; scenario-grid checks; thresholds and artifact lineage |
| B | Descriptive statistics and cross-tabulation | Useful for student research and business data | Missing values; empty/singleton data; golden references; units/labels |
| C | Correlation/regression with diagnostics | Valuable, but higher inferential risk | Reference outputs; assumptions/diagnostics; intervals/effect sizes; no unsupported causal wording |
| Later | Forecasting, optimization and broader inference | Larger verification burden | Out-of-sample baselines; feasibility/constraints; assumptions, sample size, multiplicity and fallback rules |

Do not build all methods at once. Implement one method end-to-end, then add the next after acceptance tests pass.

## 6. Minimum method contract

Each method should define:

- stable `method_id`, version, discipline/category, status, intended/unsupported use and tier;
- typed input schema, units, currency/period/precision, preconditions, missing-value policy and provenance;
- formula/algorithm, defaults, rounding/precision rules, assumptions and limitations;
- typed output schema, interpretation limits and artifact references;
- frozen tests: reference/golden cases, boundaries, invalid inputs, and metamorphic/property cases where appropriate;
- run metadata: method version, code/environment/spec/input hashes, run ID, check results and artifact IDs;
- promotion/review status. T1 requires vetted code and tests; T2 remains custom until promotion criteria are met; T3 is bounded exploratory; T4 must not claim computed results.

## 7. Registry behavior

Use repository conventions if already present. Otherwise propose the smallest interface for discovery, schema validation, execution, verification and artifact return. Discovery must not execute a method. Invalid inputs must fail with actionable errors. Execution occurs only after the spec and test plan are frozen. Verification returns explicit pass/fail/blocked outcomes. Failed checks do not silently substitute defaults; critical missing inputs trigger a user question or T4 downgrade. Generated reports/tables consume saved artifact values and references.

## 8. Testing and Stage 5 exit gate

Require unit/reference tests, boundary tests, metamorphic tests where meaningful, independent recomputation where required, integration tests from request through delivery gate, negative-path tests, regression cases and held-out examples.

Stage 5 can be called complete only when:

1. At least one priority method works end-to-end in the actual repository.
2. Numeric output comes only from execution artifacts and carries required type/provenance metadata.
3. Frozen tests and specs are enforced; failures/amendments are logged; failed mandatory checks block delivery.
4. Method tier/status accurately reflects validation; no unreviewed method is silently labeled T1.
5. Regression and integration results are reported honestly.
6. Developer docs, known limitations, decisions and change log are updated.

## 9. Stop conditions

- Do not rewrite the whole business or research manual to fit current code.
- Do not confuse a framework with a quantitative method.
- Never present synthetic values as observed data.
- Stop for owner review before weakening invariants, changing tier definitions, migrating data, or making material security/licensing decisions.
- If no relevant codebase is available, produce a method contract and scaffold proposal rather than inventing implementation status.

## 10. Completion report

Report: stage/scope; source sections used; files changed; methods reused/built; exact tests and outcomes; acceptance gate; unresolved issues; risks; recommended next step; and whether Stage 5 is complete or partial.

## 11. Source map

| Source section | Stage 5 implications |
|---|---|
| Section 2, P1–P10 | Numeric execution, tiering, deterministic control, frozen tests, fail-closed behavior, reproducibility, offline improvement |
| Section 4 | Deterministic stage order/checkpoints |
| Section 5.3 | T1–T4 and promotion rules |
| Sections 5.4–5.7 | Sandbox, verification/amendment, sensitivity, artifact-based drafting |
| Section 6 | Provenance, typed quantities, lineage |
| Sections 7–8 | Claim licensing and inference/forecast/judgment safeguards |
| Section 9 | Accounting-specific engine; not the whole of Stage 5 |
| Section 9B | Statistics methods, assumptions/fallbacks, intervals/effect sizes, reference validation |
| Section 10 / 10.1 | Agent boundaries and offline proposal/promotion loop |
| Section 11 | Numeric hallucination guardrails |
| Section 14 | Core/trap/held-out evaluation and method validation |
| Sections 16–18 | Open decisions, decision log and change log |

## 12. Change rule

This brief is **[PROVISIONAL]**. Where the v0.3 manual defines a requirement, it controls. If test evidence justifies a change, submit the reason, alternatives, risks, test plan/results and affected documents. Do not change either living document silently.
