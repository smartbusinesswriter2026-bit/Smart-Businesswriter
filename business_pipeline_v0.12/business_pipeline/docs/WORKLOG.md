# Worklog — append-only record of what was done

## 2026-10-21 — [computation] Equity bridge and mid-year DCF timing (B-078)

**Ask:** "go" for the valuation completion — the last unblocked computation item.
**Did:** two linked valuation pieces. New T2 **`equity_bridge`**: takes a declared enterprise value and subtracts declared net debt (debt minus cash), minority interest and preferred equity to report an equity value, plus a per-share value only when `shares_outstanding` is declared (no dilution, options or treasury method). Negative bridge components are refused as sign errors; a non-positive share count is refused; a **negative equity value is reported** because an EV that does not cover the declared claims is a real finding, not an input error. `dcf_valuation` gained a declared **mid-year timing convention** as an optional enum (`timing: end|mid`, default `end`): under `mid`, explicit flow t and the terminal value are discounted at exponent t−0.5 / n−0.5, so every flow is assumed mid-period; the default leaves every existing output, golden fixture and re-performance bundle unchanged. Five frozen checks for the bridge, a sixth check for the mid-year DCF path; presets `dcfmid`/`equitybridge`; sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-078, changelog 0.51, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 6 new tests — bridge arithmetic against an independent float route (equity value 1570939.14; net debt 150000; per-share 15.7093914), frozen checks declared and passing with and without a share count, refusals for negative components and bad share counts, pipeline delivery (9 artifacts, USD), mid-year DCF against an independent half-period loop, mid > end, invalid timing refused, presets and determinism. Full suite **615 tests OK**.
**Commit:** `this commit`.
**Open/next:** this drains the unblocked computation lane. What remains is owner-gated (open decisions B-005/B-028/B-032/B-052, REW R1–R10), frontier-model parked (B-075), or backend features that need a B-decision before build (AI-use disclosure export, reviewer workflow, case workspace/retention, versioning, model pinning/drift gate). The workbench UI is the design owner's domain (B-066) and the backend contract (routes, presets, JSON) is stable for it.

---

## 2026-10-21 — [computation] IRR and discounted payback (B-077)

**Ask:** "now what's next for you to do?" — with the docs-sync guardrail at MiniMax and the decision briefs also delegated, the next unblocked computation item was the gap map's capital-budgeting completion.
**Did:** two T1 methods, both on the `npv` timing convention (first cash flow at t=0, end-of-period after that). **`irr`**: the discount rate at which the declared cash flows have zero NPV, found by bracketing the NPV function over the declared range -99.99% to 1000% and bisecting (reference route: Newton-Raphson). A cash flow that never changes sign has no IRR and is refused; a cash flow with several sign changes can have several IRRs, so the method **refuses and lists the roots** rather than choosing one. **`discounted_payback`**: cumulative present values until the initial outlay is recovered, with the recovery interpolated linearly inside the recovering period; a positive first cash flow is refused and an outlay never recovered within the horizon blocks instead of reporting a number; `rate` is optional and defaults to 0 (ordinary payback). Both have declared-unit templates (IRR as a percentage), presets `irr`/`dpayback`, sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_investment.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-077, changelog 0.50, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — IRR matches its independent Newton route and the NPV-zero identity, crosses zero at the root, is scale-free; signless and multi-root cash flows refused; discounted payback matches the float route, equals the ordinary payback at rate 0, cannot shorten when the rate rises, is scale-free, and blocks when never recovered; pipeline delivery for both (percentage rendering; artifacts/test-set parity); presets and determinism. Full suite **609 tests OK**.
**Commit:** `this commit`.
**Open/next:** valuation completion remains the natural next unblocked item (equity bridge from enterprise to equity value, mid-year convention in `dcf_valuation`); everything else unblocked is either parked for the frontier-model lane (B-075) or gated on an owner decision (B-005/B-028/B-032/B-052, REW R1–R10).

---

## 2026-10-21 — [computation] XLSX sheet selection and merged-cell policy (B-076)

**Ask:** "do number 2" — the XLSX hardening item (multi-sheet selection + a declared merged-cell policy) from the proposed next-three list.
**Did:** `read_xlsx`/`read_table` now take `sheet` (exact case-sensitive name or 1-based position; default still the first sheet; unknown names/numbers refused listing the workbook's sheets) and report `sheets` + `sheet_index` on every XLSX table. Merged cells are **refused by default** with the ranges named and the declared alternative offered, because repeating an anchor across its range or blanking it would fabricate or lose data; `merged="top_left"` expands each range from its anchor, skips blank anchors, refuses overlapping/nested merges as malformed, and records `merged_cells` plus a provenance-note sentence calling the repetition a declared convention. `sheet`/`merged` are XLSX-only and refused for CSV/TSV. Wired through `POST /api/ingest` as optional fields and the CLI as `--sheet`/`--merged`. **Also fixed a latent bug:** the workbook relationship id was looked up with a malformed namespace, so every workbook silently fell back to `sheet1.xml` — harmless while only the first sheet was read, fatal for sheet selection; the fallback now applies only to the first sheet when the relationship is genuinely absent.
**Files:** `src/bp/ingest.py`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-076, changelog 0.49, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — select-by-name/index with metadata, unknown/invalid sheet refusals, CSV option refusals, default merged refusal naming the range, declared expansion (values + `merged_cells` + provenance note), malformed and overlapping merge refusals, merged-header duplicate refusal, API sheet selection and merged policy (including an invalid policy); CLI exercised by hand for default/sheet-by-name/sheet-by-number/unknown-sheet/merged-refuse/merged-top_left; full suite **598 tests OK**.
**Commit:** `this commit`.
**Open/next:** **[design]** the workbench ingestion card still sends only filename+base64 — exposing the new optional `sheet`/`merged` fields is presentation work for the design owner (B-066). Remaining ingestion gaps stay refused/declared: PDF/OCR/SPSS, and reading several sheets into one table (needs a declared concatenation rule).

---

## 2026-10-21 — [documentation] Parked frontier-model queue, and a truthful HANDOFF

**Ask:** "on those computations that require deepseek pro, write or park it in the manual or notes, as we will get back to them when we have enough credits."
**Did:** created `docs/PARKED_QUEUE.md` — the register for the six heavy statistics items reserved for the DeepSeek Pro lane (Tukey/Dunnett/Games-Howell, unbalanced two-way/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series). Each row states the blocker, the offline oracle already installed for goldens, and the output that would be accepted; the file also separates the *non*-frontier items (imputation, standards/filings/tax retrieval, PDF/OCR/SPSS ingest, breadth templates, REW) so they are not mistaken for the parked lane, and states the un-park trigger: an explicit owner grant of the frontier lane, not a general "continue". Recorded as B-075. **Fixed the stale handoff**: `HANDOFF.md` still said build 0.40 / 510 tests and listed as unbuilt everything finished since (paired/one-sample t, factorial/post-hoc, valuation, economics, appraisal, logistic/alpha, ingestion mapping); it now reports 0.48 / 588, carries the full method list, marks section A done, restates section C with what is built vs parked, and adds section H pointing at the parked queue. `HOME.md` gained the parked-queue rows and lost its stale "DCF/WACC … not built" line; `CONTRIBUTORS.md` links the queue and lists un-parking under "stop and ask".
**Files:** `docs/PARKED_QUEUE.md` (new), `docs/HANDOFF.md`, `docs/HOME.md`, `docs/CONTRIBUTORS.md`, `docs/DECISIONS.md` (B-075), `docs/WORKLOG.md`.
**Verified:** documentation-only increment; no code, test or fixture touched. Relative links in the new/edited files resolve; the suite is unchanged at **588 tests OK**.
**Commit:** `this commit`.
**Open/next:** the computation lane is caught up on everything buildable without the frontier model or an owner decision. Remaining work is owner-gated: parked queue (B-075, needs credits), B-005 reviewers, B-028 templates, B-032 ledger engine, B-052 taxation, REW R1–R10 ratification. Design/presentation is MiniMax's domain (B-066).

---

## 2026-10-21 — [computation] Logistic regression and Cronbach's alpha (B-074)

**Ask:** "correction, finish those you can do" — the remaining statistics items that do not need a frontier model or a new distribution.
**Did:** two T1 methods. `logistic_regression`: binary 0/1 outcome with up to five numeric predictors, Newton-Raphson (IRLS) at 1e-10 tolerance, no regularisation, Wald standard errors/p-values, odds ratios, log-likelihood, null log-likelihood and McFadden pseudo R-squared; non-convergence/separation, single-class outcomes, non-0/1 codes and collinear designs are refused. `reliability_alpha`: Cronbach's alpha from an items column map, listwise deletion with the excluded count, the classic k/(k-1)(1 − Σitem variances / total variance) formula. Goldens for the logistic model generated from `statsmodels.Logit` offline; five frozen checks each; presets `logit`/`alpha`; sandbox and session coverage.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_logit_reliability.py`, `tests/fixtures/logistic_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-074, changelog 0.48, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 9 new tests — all statsmodels goldens matched (coefficients, SEs, p-values, log-likelihood, pseudo R²), frozen checks, separation/single-class/bad-code refusals, alpha against an independently coded classic formula, refusals for single-item and zero-variance cases, pipeline delivery for both, contract/preset, determinism. **588 tests OK.**
**Commit:** `this commit`.
**Open/next (for the frontier model):** k-means clustering, factor analysis, unbalanced/ANCOVA/repeated-measures designs, Tukey/Dunnett/Games-Howell, non-linear time series. The offline oracles for these are installed (sklearn, factor_analyzer, statsmodels AnovaRM, scipy studentized_range/dunnett).

---

## 2026-10-21 — [computation] CBA, cost-effectiveness and SROI (B-073)

**Ask:** "go on: … CBA/CEA/SROI."
**Did:** three T2 appraisal methods. `cost_benefit`: discounted present values of declared costs and benefits, NPV and benefit-cost ratio (omitted when PV costs are zero); five frozen checks. `cost_effectiveness`: ICER for each option against the first-listed comparator, with incremental cost/effect and dominance flags; refuses a single option, negative costs and a zero effect difference. `sroi`: present value of declared social benefits over the declared investment, with net value; refuses a non-positive investment. All three are arithmetic on owner valuations — no effect is monetised by the system, no deadweight/additionality adjustment is invented, and no willingness-to-pay threshold is assumed.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_appraisal.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-073, changelog 0.47, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — present values against an independently written discounting loop, ICER/dominance arithmetic, SROI ratio identity, frozen checks, refusals for mismatched lengths, zero-effect comparators and non-positive investments, pipeline delivery for all three, contract/preset, determinism; sandbox and session coverage. **579 tests OK.**
**Commit:** `this commit`.
**Open/next:** remaining from the batch — ANCOVA / repeated measures / unbalanced designs, Tukey–Dunnett–Games-Howell, logistic regression, reliability/factor analysis, clustering, non-linear time series. The first three groups need either a ratified SS/design convention or distributions the standard library lacks (studentized range, multivariate t); logistic regression, reliability and clustering are feasible with declared conventions.

---

## 2026-10-21 — [computation] Ingestion mapping, unit economics and multi-product break-even (B-071, B-072)

**Ask:** "go on: … unit economics / multi-product break-even … ingestion→method mapping helper."
**Did:** `ingest.to_method_inputs` maps named columns into a method's declared inputs — `value_list`/`code_list` from one column, `column_map` from an object of name → column, cleaned through the method's own `validate_inputs` and `profile` so a bad mapping is refused before running; only list-shaped inputs (a scalar rate cannot come from a column), and the provenance note says the file hash identifies the source, not that the data is verified. Exposed as an optional `map` on `POST /api/ingest`. Then two T1 finance methods: `unit_economics` (margin, margin rate, payback, optional period-value LTV and LTV/CAC) and `multi_product_breakeven` (mix-weighted contribution margin, break-even units and revenue, per-product units), each with five frozen checks and declared assumptions (constant churn, fixed mix, no tax/discounting).
**Files:** `src/bp/ingest.py`, `src/bp/server.py`, `src/bp/methods.py`, `tests/test_economics.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-071/B-072, changelog 0.46, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — column→method mapping (value and column_map shapes), refusals for text/unknown/scalar/unmapped inputs, unit-economics arithmetic and refusals, multi-product break-even arithmetic (break-even 2000 units; 1500 coffee / 500 cake; revenue 10500) and refusals, frozen checks, pipeline delivery, contract/preset, determinism; sandbox and session coverage. **568 tests OK.**
**Commit:** `this commit`.
**Open/next:** CBA/CEA/SROI, reliability (Cronbach's α), logistic regression, clustering, non-linear time series; ANCOVA/repeated-measures/unbalanced designs and Tukey/Dunnett/Games-Howell need distributional work (studentized range / multivariate t) not in the standard library.

---

## 2026-10-21 — [computation] Factorial two-way ANOVA and post-hoc pairwise tests (B-070)

**Ask:** "go: factorial ANOVA + post-hoc pairwise tests."
**Did:** added two T1 methods. `two_way_anova`: balanced two-way factorial ANOVA on one numeric response — both main effects and the interaction, sums of squares, mean squares, F tests, degrees of freedom and partial eta-squared. Unbalanced designs and empty cells are **refused** (the SS type would be an unratified convention). Five frozen checks: independent float route, SS decomposition, F = MS/MS_error, shift invariance, scale equivariance of F. `posthoc_pairwise`: every unordered pair of independent groups compared with a Welch t-test, reporting the difference, raw p and adjusted p under a **declared** correction (Holm default, Bonferroni, or explicitly `none`), with `n_pairs`, `n_rejected` and the pair design recorded. Five frozen checks: independent float route, adjusted ≥ raw, declared correction reproduced step by step, pair count = k(k−1)/2, reversing group order negates differences and keeps p. Goldens generated offline with numpy/scipy; both wired into sandbox CASES, the session input map and presets `factorial`/`posthoc`; a `records` input type was added for the factorial design.
**Files:** `src/bp/methods.py` (records input type, both methods and contracts), `src/bp/server.py` (presets), `tests/test_factorial_posthoc.py`, `tests/fixtures/two_way_golden.json`, `tests/fixtures/posthoc_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-070, changelog 0.45, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 12 new tests — goldens against numpy/scipy for a main-effects and an interaction design, hand-computable exact SS/F values (8/32/0/8, F 4/16/0), frozen checks declared and passing, unbalanced/broken-design refusals, Welch+Holm goldens, adjustment-method behaviour, invalid-group refusals, full pipeline delivery for both, contract/preset assertions, determinism. **557 tests OK.**
**Commit:** `this commit`.
**Open/next:** unbalanced/ANCOVA/repeated-measures designs and Tukey/Dunnett procedures; then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Multi-currency: ISO 4217 registry, per-currency precision, declared-rate conversion (B-069)

**Ask:** "also allow it to use multi-currencies that include dollar, euro, and chinese yuan and other currencies of the world."
**Did:** `src/bp/currency.py` — a declared ISO 4217 table of 160+ currencies with their **minor units** (0 for JPY/KRW/VND/ISK, 3 for KWD/BHD/OMR, 4 for CLF, 2 for USD/EUR/CNY and most others), code normalisation and validation, and exact Decimal conversion at a rate the owner **declares** (with provenance `user`/`sourced`/`assumption`, a mandatory source for `sourced`, and an optional declared date). Wired into the computation layer: unknown currency codes are refused at intake; money artefacts default to the currency's minor units when the request states no precision (JPY prints no cents, KWD prints three); a management-accounts spec takes its `places` default from its currency; new T1 method `currency_convert` with five frozen checks (float second route, reciprocal-rate round trip, zero, sign symmetry, linearity); `GET /api/currencies` lists the registry; preset `currency`. No exchange rate is fetched, hard-coded or verified, and one engagement stays single-currency (no consolidation or translation).
**Files:** `src/bp/currency.py`, `src/bp/methods.py` (currency and text input types + method), `src/bp/orchestrator.py` (intake validation, per-currency precision), `src/bp/accounts.py` (currency validation, places default), `src/bp/server.py` (catalog endpoint, preset), `tests/test_currency.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-069, changelog 0.44, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 14 new tests — major/zero/three/four-decimal currencies, 160+ code coverage, normalisation and unknown refusals, conversion arithmetic, same-currency rule, provenance rules, invalid amounts/rates, pipeline delivery with the appendix recording codes/rate/provenance/date, per-currency precision through npv (JPY 0, KWD 3, USD 2), unknown-currency intake refusal, accounts `places` defaults, `/api/currencies`, contract/preset, determinism; sandbox and session coverage via the shared maps. **545 tests OK.**
**Commit:** `this commit`.
**Open/next:** FX retrieval/verification and statement translation/consolidation remain out (they need a rate source and a translation standard); statistics backlog resumes with factorial ANOVA + post-hoc, then unit economics / CBA.

---

## 2026-10-21 — [computation] Valuation: WACC and DCF (B-068)

**Ask:** "go. automate everything" — continue the computation backlog without waiting for instruction.
**Did:** two valuation methods. `wacc` (T1): weighted average cost of capital from declared market values of equity and debt and declared costs of equity and **after-tax** debt; reports the WACC and both weights; five frozen checks (float second route, weights sum to one, WACC between the two costs, scaling both values changes nothing, a higher cost of equity raises the WACC); no tax is computed. `dcf_valuation` (T2): declared end-of-period free cash flows discounted at a declared rate, optional Gordon-growth terminal value on the last flow; reports explicit PV, terminal PV, terminal value, enterprise value, terminal share and the inputs; five frozen checks (second route, linear scaling in the cash flows, higher rate lowers value, terminal value equals the Gordon formula, no growth means no terminal value); refuses growth at or above the rate, a rate at or below -100% and an empty forecast. Both wired into sandbox `CASES`, the session input map and presets `wacc`/`dcf`.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-068, changelog 0.43, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — arithmetic against an independently written discounting loop, five frozen checks each, refusals for invalid capital structures and DCF assumptions, full pipeline delivery for both with percentage/currency rendering, contract/preset assertions, determinism; sandbox parity and session coverage. **531 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA + post-hoc pairwise tests (using the existing `multiple_comparison`), then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Inference completion 1: paired and one-sample t-tests (B-067)

**Ask:** "go. automate everything" — work the computation backlog autonomously.
**Did:** added two T1 methods that close the manual's 9B.2 paired/one-sample gap. `paired_t`: within-pair differences (first column minus second), a pair dropped and counted when either side is missing, with mean difference, sd/se, t, df, two-sided p, confidence interval, Cohen's dz and both column means; five frozen checks (independent float route, swapping columns negates the difference and t but keeps p, shift/scale behaviour, row-order invariance, missing pairs dropped not imputed). `one_sample_t`: one mean against a declared reference `mu0`, with sd/se, t, df, p, CI, Cohen's d and excluded count; five frozen checks (second route, shift invariance, positive scale equivariance, row-order invariance, missing entries excluded not valued). Both default to two-sided, refuse constant data through the profile, and are wired into the sandbox `CASES` test, the session input map and workbench presets `paired`/`onesample`; goldens generated offline with scipy (test fixtures only).
**Files:** `src/bp/methods.py` (both methods + contracts), `src/bp/server.py` (presets), `tests/test_inference_more.py`, `tests/fixtures/inference_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-067, changelog 0.42, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — scipy goldens to 1e-9, frozen checks declared and passing, constant-data and missing-reference refusals, full pipeline delivery for both, contract/preset assertions, determinism; sandbox parity and session coverage via the shared maps. **520 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA and post-hoc pairwise tests (using the existing `multiple_comparison`), then DCF + WACC.

---

**Newest first. Never rewrite an entry.** One entry per increment (not per message): the ask, what changed, what verified it, the commit, and what is next. Link to the source of truth rather than restating it — `CHANGELOG.md` has the build detail, `DECISIONS.md` the reasoning, this file the narrative and the sequence.

---

## 2026-10-21 — 9B.3 upgrade: power and minimum-effect planning (B-061)

**Ask:** "go" — continue closing the open statistics items (after multiple-comparison correction).
**Did:** added the T1 method `power_analysis` for a two-sample or one-sample comparison of means under the **normal approximation**: power for a stated effect, and the smallest effect that reaches a declared target power, plus standard error, non-centrality and the z critical value. Inputs declare design, effect, sample sizes, standard deviations, alpha (default 0.05), tails (two-sided default) and target power (default 0.8); one-sample designs refuse `n2`/`sd2`; invalid numbers, alpha or sizes are refused at intake. Five frozen checks: erfc-based independent second route agrees to 1e-9, zero effect gives power = alpha, power rises with effect size and with sample size, minimum effect falls with sample size. The normal approximation and its limits (no noncentral t, no proportions, no clustering/weights/repeated measures, no multiplicity) are declared in the template, caveats and appendix. Golden fixture generated offline with `scipy.stats.norm`; no scipy at runtime. The draft-audit claim checker caught the first template draft using "effect of" (intervention language) — reworded rather than weakening the checker.
**Files:** `src/bp/methods.py` (core, reference route, checks, profile, typing, caveats, template, contract), `src/bp/server.py` (preset `power`), `tests/test_power.py`, `tests/fixtures/power_golden.json`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-061, changelog 0.36, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-061.
**Verified:** 8 new tests — scipy golden values (three designs) to 1e-9 relative, zero-effect = alpha, one-sided vs two-sided ordering, sample-size movements, five invalid-input refusals, full pipeline delivery with licensed report, contract/preset, determinism; sandbox parity and session coverage via shared maps. **465 tests OK.**
**Commit:** `this commit`.
**Open/next:** missing-data mechanism modelling and survey weights are the last 9B.3 items and need a declared convention choice (extreme-bounds vs imputation; design vs frequency weights); then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — [computation] Model-ownership split: computation vs design (B-066)

**Ask:** "we will divide the job… keep the computation part here; design/aesthetics goes to MiniMax. Put this rule in the manual that models can read that computation are exclusively your domain."
**Did:** recorded the division of labour as a binding rule in the two documents every model reads first: `docs/CONTRIBUTORS.md` **§1A** (new section) and `docs/HANDOFF.md` §2.9. Computation is exclusively the computation owner's (DeepSeek) domain — `src/bp/**`, `tests/**` and fixtures, the factual docs, every number/statistic/accounting figure, verification and audit logic, citation rules, type inference, claim ceilings and asserted wording, and any prompt affecting what is produced or validated. Design/aesthetics is exclusively the design owner's (MiniMax) domain — the workbench's presentation and look (`web/**` layout, CSS, typography, colour, spacing, iconography, responsiveness, component styling, visual report design) and behaviour-neutral interaction affordances. Boundary rules: design may not change numbers/claims/checks/schemas/tests; computation may not silently restyle (functional wiring only); neither owner edits the other's files, and cross-domain needs are noted here tagged `[computation]`/`[design]`; cross-domain features land as a computation commit then a design commit; conflicts escalate to the owner; the verification non-negotiables bind both.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` (B-066), `docs/CHANGELOG.md` (0.41). No code changed.
**Verified:** docs only; test suite untouched at 510 tests.
**Commit:** `this commit`.
**Open/next:** the computation backlog is now the only work in this conversation — next increment is the paired/one-sample t-test pair, then DCF + WACC.

---

## 2026-10-21 — Ingestion first slice: CSV/TSV and XLSX to a typed table with provenance (B-065)

**Ask:** "go" — the other P0 gatekeeper: ingestion.
**Did:** added `src/bp/ingest.py`, standard library only. CSV/TSV (delimiter sniffed; UTF-8/CP1252/Latin-1) and XLSX (first sheet, read as a zip of XML parts — `zipfile` + `xml.etree`, no third-party library) become a typed table: column names, inferred `number`/`date`/`text`/`mixed` types, present and missing counts, sample values, rows, and a table-level provenance pointer (file, SHA-256, data row i and column j, sheet) stating that nothing is imputed or retyped. Declared conventions: first non-empty row is the header; headers must be non-empty and unique; a mixed number/text column is labelled `mixed` rather than coerced; formula cells use the cached value the file stores; XLSX dates are normalised with the workbook date system (1900 leap-year adjustment); caps of 5 MB / 1000 rows / 50 columns are **refused, not truncated**. **PDF, scans, images and SPSS `.sav` are refused with explicit messages** — no OCR or PDF text extraction exists, so pretending to read them would be invention. Wired as `POST /api/ingest` (base64, 422 on refusal, separate request-size limit), a workbench "Data ingestion" card with file picker and summary, and `python -m bp.ingest <file>`.
**Files:** `src/bp/ingest.py`, `src/bp/server.py` (route, body size), `web/index.html`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-065, changelog 0.40, limitations, gap map, REW §8, HOME, README, CONTRIBUTORS).
**Decisions:** B-065.
**Verified:** 14 new tests — typed CSV with missing/date columns, delimiter and encoding detection, mixed-column labelling, header refusals, row cap, XLSX shared strings/numbers/date styles, corrupt and empty workbook refusals, PDF/PNG/SPSS refusals, API decoder validation, endpoint 200/422, UI card; CLI smoke printed the summary; **510 tests OK**.
**Commit:** `this commit`.
**Open/next:** ingestion remains partial by design — PDF/scan/OCR and SPSS are refused, multi-sheet/merged-cell handling and automatic column→method-input mapping are not built. Elsewhere: imputation and complex-design inference, standards/filings/tax retrieval sources, and the owner gates (B-005 reviewers, B-028 templates, B-032 ledger engine).

---

## 2026-10-21 — Retrieval failover and drift sweep (B-064)

**Ask:** "go" — close the retrieval extras (declared source priority/failover, drift monitoring).
**Did:** two pieces. **(a) Source priority and failover**: the declared order is Crossref then OpenAlex, the API's default source is now `auto`, and every attempt is recorded in the retrieval log as `resolved` / `not_found` / `error` with the error detail. A source error is never swallowed silently; the next source is tried; if **every** source errors the lookup fails closed (502) instead of labelling the DOI "unverified". **(b) Drift sweep**: `drift_check` re-verifies the most recent logged retrievals and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable` per entry with a summary, flagging changed citations for human re-check and never rewriting the log. Exposed as `GET /api/literature/drift?limit=` (cap 25), a workbench "Check drift" button, and `python -m bp.literature drift [log] [limit]`.
**Files:** `src/bp/literature.py` (failover resolver, attempts in log records, `drift_check`, CLI), `src/bp/server.py` (auto source, sources listing with declared priority, drift endpoint, validation), `web/index.html` (drift button and output), `tests/test_literature_failover.py`, `tests/test_literature_api.py`, docs (B-064, changelog 0.39, limitations, gap map, REW §9 + Q7, HOME, README, WORKLOG, CONTRIBUTORS).
**Decisions:** B-064.
**Verified:** 12 new tests — failover on error and on not-found, all-not-found stays unverified, all-error fails closed, attempts recorded in the log, drift hash_match/hash_differs/unresolvable/unreachable, empty log, drift source order, API auto-source response, drift endpoint and limit validation, UI button; live smoke resolved a real DOI through `default_sources()` with the attempt logged and the drift sweep returning `hash_match`, plus the CLI printing the summary. **496 tests OK.**
**Commit:** `this commit`.
**Open/next:** standards/filings/tax source families (needs a source/licensing decision, not code) and extra scholarly APIs; then ingestion (the other P0), and imputation / complex-design inference for the statistics.

---

## 2026-10-21 — 9B.3 upgrade: weighted summaries with a declared weight kind (B-063)

**Ask:** "go" — close the last statistics item on the open list.
**Did:** added the T1 method `weighted_summary`: weighted mean, weighted standard deviation, total weight, **effective sample size** `(Σw)²/Σw²` and **design effect** `n/n_eff`, with an overridable weight kind — `reliability` (default; unbiased weighted variance) or `frequency` (observations counted). One positive weight per value including missing entries (a missing value's weight drops with it); zero, negative, mismatched-length and blank weights are refused. **No inference**: no standard error, interval or test, because that needs a declared complex design (stratification, clustering, replicate weights) that is not implemented — and the honesty layer now says exactly that for this method instead of the generic "weights unsupported" line. Five frozen checks: float second route agrees, unit weights reproduce the ordinary sample summary, the mean is invariant to weight scaling, extra weight on larger values raises the mean, and the design effect is 1 for equal weights. The draft-audit claim checker again caught a template phrasing ("design effect of"); the template was reworded rather than the checker weakened.
**Files:** `src/bp/methods.py` (impl, stats helper, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty wording for the weighted method), `src/bp/server.py` (preset `weighted`), `tests/test_weighted.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-063, changelog 0.38, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-063.
**Verified:** 9 new tests — exact weighted mean and reliability/frequency sds, equal weights equal the ordinary summary, missing values drop their weights, all frozen checks, five invalid-input refusals, full delivery with the design disclaimer, contract/preset, determinism; sandbox parity and session coverage via shared maps. **484 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 row is closed except imputation and complex-design inference (each needs its own declared model/design). Next: retrieval extras (standards/filings/tax source families, automatic failover, drift monitoring) and ingestion (the other P0).

---

## 2026-10-21 — 9B.3 upgrade: missing-data bounds with a declared mechanism (B-062)

**Ask:** "go" — continue closing the open 9B.3 statistics items.
**Did:** added the T1 method `missing_data_bounds`. It reports how much of a variable is missing and **bounds** the complete-data mean by the extreme-case convention — every missing value at the observed minimum (lower bound) or maximum (upper bound) — alongside the observed mean, observed range and bound width. The missing-data mechanism (`unknown`/`mcar`/`mar`/`mnar`) is an input the owner **declares**; it is recorded with an explicit note that the system cannot verify it from the data, and it changes no bound. No imputation and no probabilistic missing-data model. Five frozen checks: bounds bracket the observed mean, independently recomputed extreme cases agree, adding missing entries cannot narrow the bounds, the reported share is missing/total, and with no missing values the bounds collapse to the observed mean. The generic honesty layer used to append its listwise-deletion warning to this method — which contradicted the method's own stronger convention — so that notice is now suppressed for it, and the method's own disclaimer is what the delivery carries.
**Files:** `src/bp/methods.py` (impl, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty suppression), `src/bp/server.py` (preset `missing`), `tests/test_missing.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-062, changelog 0.37, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-062.
**Verified:** 10 new tests — exact bound arithmetic, missing codes and blanks both counted, zero-width when nothing is missing, declared mechanism changes no number and is labelled, all frozen checks, three invalid-input refusals, full delivery without the contradictory notice, contract/preset, determinism; sandbox parity and session coverage via shared maps. **475 tests OK.**
**Commit:** `this commit`.
**Open/next:** survey weights are the last 9B.3 item; then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — 9B.3 upgrade: multiple-comparison correction (B-060)

**Ask:** "go on the still open, close them" — the statistical upgrades the honesty layer was only disclosing.
**Did:** closed the multiple-comparison item with a new T1 method `multiple_comparison`. It applies a declared correction to one family of raw p-values: **Holm** step-down (sort ascending, multiply the i-th smallest by k−i+1, running maximum, cap at 1) or **Bonferroni** (k·p capped at 1). Outputs are `p_adj_1..k`, `n_tests`, `n_rejected` at the declared alpha, with an appendix carrying the raw and adjusted values and the written definition. Five frozen checks: adjusted ≥ raw, bounded in [0,1], matches the declared definition (Holm monotone/Bonferroni formula), independent second route agrees to 1e-12, and order-invariance. Invalid p-values, alpha outside (0,1), an unknown method or a family of fewer than two values are refused at intake; a new `enum` input type covers declared method choices. The honesty layer now says a correction is available instead of only "not applied", and OLS's family-wise notice points to it. Existing methods and their goldens are untouched — no reported p-value changed silently.
**Files:** `src/bp/methods.py` (impl, checks, profile, caveats, template, contract, `enum` validation), `src/bp/orchestrator.py` (honesty wording for the correction method and OLS pointer), `src/bp/server.py` (preset `multicomp`), `tests/test_multicomp.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-060, changelog 0.35, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-060.
**Verified:** 10 new tests — published Holm example reproduced exactly (0.03/0.06/0.06/0.02), Bonferroni formula, order-invariance, all frozen checks, alpha-driven rejection counts, four invalid-input refusals, full pipeline delivery with licensed report and honesty block, contract/preset, determinism; sandbox parity and session-input coverage via the shared maps. **457 tests OK.**
**Commit:** `this commit`.
**Open/next:** power/MDE calculation, missing-data mechanism modelling and survey weights are the remaining 9B.3 items and need their own declared conventions (they change what is estimated or the input contract); retrieval still lacks standards/filings/tax source families, automatic failover and drift monitoring; ingestion is the other P0.

---

## 2026-10-21 — Citations: APA 7 and Harvard ratified and implemented (B-059)

**Ask:** "citation styles will be apa and harvard" — close the open citation item.
**Did:** replaced the provisional layout with the two ratified styles. Sources now map the bibliographic metadata the citation needs: Crossref supplies structured family/given names, volume, issue, pages, publisher and type; OpenAlex supplies volume/issue/pages and a type mapping but only display names. APA 7 renders `Family, I. (Year). Title. Journal, volume(issue), pages. https://doi.org/...` with APA's `&`/serial comma; Harvard renders `Family, I. and … (Year) 'Title', Journal, volume(issue), pp. pages. doi: ...`. Books have their own layout; any other source type gets a labelled generic layout instead of pretending it is fully styled. Rendering limits are declared in every citation's notice (plain text has no italics; titles are not case-converted; names are inverted only when the source supplies family/given, with a note when it does not). Unverified references stay prefixed `[unverified user-supplied…]` in both styles. API `cite` now accepts `apa`/`harvard`, the sources endpoint exposes both notices and the reference payload carries the new bibliographic fields; the workbench has a style selector and "Get citation".
**Files:** `src/bp/literature.py` (reference fields, source mappings, APA/Harvard formatters), `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-059, CHANGELOG 0.34, KNOWN_LIMITATIONS, REW manual §9 + Q9, HOME, README, CONTRIBUTORS, WORKLOG).
**Decisions:** B-059 (RESOLVED).
**Verified:** 5 new/updated tests — Crossref and OpenAlex field mapping, exact APA and Harvard strings, book and generic layouts, non-inverted-name note, unverified labelling in both styles, ratified style list, unknown style refused, API style selection; live smoke against Crossref rendered a real eight-author APA and Harvard citation. **447 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 statistical upgrades (multiple-comparison correction, power/MDE, missing-data mechanism modelling, survey weights), the remaining retrieval items (standards/filings/tax source families, failover policy, drift monitoring) and ingestion.

---

## 2026-10-21 — Retrieval layer second slice: durable log and provisional citation (B-058)

**Ask:** "GO" after the 9B.3 honesty layer — continue down the gap order at the P0 gatekeeper.
**Did:** two halves of the retrieval layer. **(a) Durable retrieval log**: every retrieval that reaches a source is appended to a local newline-delimited JSON file (source, DOI, supplied and resolved title, status, authors, year, container, UTC retrieval time, response SHA-256), flushed to disk **before** the reference is returned — an unwritable log raises and the retrieval fails closed, so an unaudited citation cannot be produced. `read_log` refuses a corrupt or unknown-format log; `reverify` re-checks a logged entry against the source and reports `hash_match` / `hash_differs` / `unresolvable_now`. **(b) Provisional citation layout**: one declared author-date format (authors as returned, year, title, container, DOI) with an explicit PROVISIONAL notice — no institutional style is claimed, because none has been ratified (REW Q9). Unverified references are formatted only with the `[unverified user-supplied…]` prefix and never as if checked. Wired into the API (`cite` parameter, `GET /api/literature/log`), the workbench (citation line, retrieval-log panel with the new "Get provisional citation" and "Show retrieval log" controls), and `.gitignore` so the runtime log cannot be committed. `BP_RETRIEVAL_LOG` sets the path; empty disables it.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `.gitignore`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-058, CHANGELOG 0.33, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, REW manual §9 + Q9/Q10, HOME, README, CONTRIBUTORS).
**Decisions:** B-058.
**Verified:** 17 new tests — log fields and single-line records, unverified retrievals logged honestly with resolved title, no logging without a retrieval, unwritable log fails closed, empty/corrupt/unknown-format log handling, append-only ordering, `reverify` states, citation structure and provisional notice, unverified labelling and mismatch note, placeholders instead of invented authors/years, unknown style refused, determinism; API tests for citation, style validation, log endpoint, limit validation and disabled state; UI strings asserted. **442 tests OK.** Live smoke: real Crossref retrieval logged with a genuine sha256, citation correctly labelled unverified for a deliberately wrong title, `reverify` returned `hash_match`.
**Commit:** `this commit`.
**Open/next:** retrieval-layer remainder — standards/filings/tax source families, source priority and failover, a ratified citation style (Q9) and drift monitoring; then the actual 9B.3 statistical upgrades or the next gap-map item.

---

## 2026-10-21 — 9B.3 honesty layer: disclosure and refusal, no numbers changed (B-057)

**Ask:** the other half of Slice 1 as agreed — the 9B.3 honesty pass on existing statistical outputs.
**Did:** scoped it honestly rather than overclaiming. The layer **discloses** what the system does not do, in every delivery: (a) missing values are excluded listwise and the missing-data mechanism (MCAR/MAR/MNAR) was not established; (b) multiple hypotheses are not corrected, with the family-wise exposure named for OLS coefficients and "one omnibus, no post-hoc comparisons" for ANOVA/Kruskal-Wallis; (c) no power or minimum-detectable-effect is reported, so precision must be read from the interval; (d) survey weights, clustering and repeated measures are unsupported, so every observation is treated as independent. These are both machine-readable (`appendix.honesty`) and plain sentences in the report. Separately, inputs that name an unsupported structure (`weights`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are now refused with a specific reason instead of a generic unknown-input error — a weighted or clustered dataset can no longer be passed in and silently analysed as independent observations. **No number changed.** The actual upgrades (Holm/Bonferroni, power/MDE, missing-data modelling, survey weights) are recorded as still open, so the layer cannot be mistaken for the fix.
**Files:** `src/bp/orchestrator.py` (honesty helper, appendix block, report sentences), `src/bp/methods.py` (unsupported-structure refusal in `validate_inputs`), `tests/test_honesty.py`, docs (DECISIONS B-057, CHANGELOG 0.32, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, REW manual §10, CONTRIBUTORS count).
**Decisions:** B-057.
**Verified:** 10 new tests — appendix block present for every delivered method, descriptive/omnibus/OLS disclosures, NPV and ratio methods report not-applicable rather than blank, determinism and JSON-safety, refusal of weights/clusters/strata with the specific reason, generic unknown-input message preserved; **425 tests OK** (no existing test changed behaviour).
**Commit:** this commit.
**Open/next:** the actual 9B.3 statistical upgrades are still the open row (correction, power, missing-data modelling, weights); the P0 gatekeeper (retrieval + citation: durable retrieval log + citation formatting) is the next build target.

---

## 2026-10-21 — Ratio analysis: the safe half of Slice 1

**Ask:** after the documentation spine, continue with Slice 1 as agreed — the risk-paired first gap closures (honesty upgrades + statement ratios).
**Did:** added the T1 method `ratio_analysis` (B-056). Fifteen declared ratios across liquidity (current, quick, cash), profitability (gross/operating/net margin, return on assets, return on equity), solvency (debt to equity, equity multiplier, interest cover) and efficiency (asset turnover, receivables/inventory/payables days) computed in Decimal from figures the owner supplies. Each ratio reports its definition, inputs and unit; a ratio with a missing figure or a zero denominator is listed in the appendix as not computed **with its reason** and never estimated; a negative denominator is computed and flagged; the balance-sheet identity is checked when assets, liabilities and equity are all supplied; supplied figures are verified to be used exactly as given. No benchmark, industry average, cut-off or good/bad verdict is applied — the manual forbids inventing ratings. The independent second route is exact rational arithmetic (`fractions.Fraction`), and the golden fixture is generated by a separately written Fraction re-implementation, not by the method itself. Added the `ratios` workbench preset; the `days` unit is no longer given a currency in the orchestrator.
**Files:** `src/bp/methods.py` (catalogue, impl, checks, profile, caveats, template, contract), `src/bp/orchestrator.py` (unit exemption), `src/bp/server.py` (preset), `tests/test_ratio.py`, `tests/fixtures/ratio_golden.json`, `tests/test_sandbox.py` `CASES`, `tests/test_session_api.py` input map, README, docs (DECISIONS B-056, CHANGELOG 0.31, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, CONTRIBUTORS count).
**Decisions:** B-056.
**Verified:** 15 new tests covering golden values, every frozen check, scale invariance, sign behaviour, missing-figure disclosure, zero denominators, negative equity, balance-sheet identity (holds / fails / not applicable), Decimal outputs, determinism, intake blocking, preset reachability and a full pipeline delivery with a licensed report; sandbox parity via the shared `CASES` test; **415 tests OK**.
**Commit:** this commit.
**Open/next:** the other half of Slice 1 — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison correction, power/precision statements, missing-data mechanism declaration, survey-weight/cluster detection), then retrieval + citation (P0 gatekeeper).

---

## 2026-10-21 — Documentation spine: contributors' manual, home map, this worklog

**Ask:** after the gap discussion, the owner asked for a log that traces the work, a manual for any model that will touch or fix the files, and an Obsidian-like map to find things — then "go".
**Did:** added three documents and wired them in: `docs/CONTRIBUTORS.md` (ten non-negotiables, the add-a-method checklist, bug-fix rules, boundary-change rules, the testing contract, environment traps, "where each fact belongs", rejection list, stop-and-ask list), `docs/HOME.md` (task view, module map, capability status, documentation spine, map conventions), and this `docs/WORKLOG.md`. Design choices confirmed with the owner: `CONTRIBUTORS.md` is a repo-level bridge (not part of the authority manual), `HOME.md` uses plain Markdown links rather than Obsidian wikilinks, and the worklog starts now with a backfill pointer rather than reconstructing history.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HOME.md`, `docs/WORKLOG.md`, `README.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md` (B-055).
**Verified:** docs only; suite unaffected (400 tests OK run in the previous increment). Links checked against the files present in the repo.
**Commit:** this commit.
**Open/next:** Slice 1 of the gap plan — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison, power/precision, missing-data mechanism, weights/clusters) as the risky half, paired with the safe half: financial-statement ratio analysis (T1 arithmetic on the ledger artifacts).

---

## 2026-10-21 — Retrieval audit: response SHA-256 and UTC time per reference

**Ask:** "okay do 3 first" — the cheapest REW increment, Q10 in the living manual: make the hash-audit claim true.
**Did:** `CrossrefSource`/`OpenAlexSource` capture the raw response bytes and record `response_hash` (SHA-256 of those exact bytes) plus `retrieved_at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) on every resolved retrieval; the fields travel through `POST /api/literature/verify` and show in the workbench References panel. A reference that never reached a source (no DOI, 404, source error) carries neither, fail-closed. Clock is injectable for deterministic tests. Hash is byte-level on purpose: the same semantic record received with different whitespace hashes differently, so the audit pins what was served.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_api.py`, docs (REW manual v0.3, DECISIONS B-054, CHANGELOG 0.29, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, README).
**Decisions:** B-054 (PROVISIONAL); REW manual Q10 marked answered.
**Verified:** five new tests (byte-level pin vs parsed record, injected clock, audit survives a title mismatch, no audit without retrieval, OpenAlex parity) plus API/UI assertions; **400 tests OK**; live smoke against Crossref recorded a real sha256 for DOI `10.1038/nature12373`.
**Commit:** `3189816`.
**Open/next:** no durable retrieval log yet (documented); citation formatting is still `[OPEN]` Q9.

---

## 2026-10-21 — Owner ratifies R11: the REW living manual is the working authority

**Ask:** "yes to R11".
**Did:** ratified R11. The manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) is now the working authority for the Research & Evidence Workflow; B-035 (blocked on the missing Smart Researcher manuals) is closed and B-053 resolved. Manual to v0.2, stating explicitly that R11 ratifies the **document**, not its proposals — R1–R10 (stage list, checkpoints, tiers, taxonomy, etc.) remain unratified.
**Files:** REW manual, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Decisions:** B-053 RESOLVED; B-035 SUPERSEDED.
**Verified:** docs only; no code changed.
**Commit:** `7d73b6d`.
**Open/next:** cheap code increment that makes the manual honest — the retrieval audit (Q10).

---

## 2026-10-21 — Living manual for the research workflow (REW), replacing "Stage 7"

**Ask:** the owner believed Stage 7 had already been built; asked "what are these: reviewers, next templates, ledger engine, Stage 7 manuals?" and "create a living stage 7 manual and probably, rename that appropriately".
**Did:** explained the four owner asks (B-005 reviewers, B-028 next templates, B-032 ledger engine, B-035 missing research-pipeline manuals) and corrected the record: what existed was the Stage 7 **blocker** document plus the literature retrieval/verification boundary, not the workflow definition. Created `docs/RESEARCH_EVIDENCE_WORKFLOW.md` as a living manual, renamed the capability **Research & Evidence Workflow (REW)** — "Stage 7" was a build-order label, not a product name. Merged and removed `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md`; updated every reference. The manual refuses to pretend it is the lost Smart Researcher manual: every section is tagged `[OWNER]`, `[REPO]`, `[2ND]`, `[PROPOSAL]` (R1–R11) or `[OPEN]` (Q1–Q12), with stages R0–R8 proposed, three mandatory checkpoints, feasibility tiers, study taxonomy, retrieval/citation rules, claim rules, synthetic-data and AI-use policy, an honest inventory, and a ratification register.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (new), two Stage 7 docs (removed), `README.md`, `docs/DECISIONS.md` (B-035 superseded, B-040 pointer, B-053), `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`, `src/bp/literature.py` docstring.
**Decisions:** B-053 created; B-035 superseded.
**Verified:** docs only; **395 tests OK**.
**Commit:** `896372e`.
**Open/next:** owner ratification of the register (R11 asked first).

---

## 2026-10-21 — Product gap map

**Ask:** "what else in business have we overlooked?" (after the taxation discussion).
**Did:** wrote `docs/PRODUCT_GAP_MAP.md`: what the catalogue/manual call for versus what is built, ordered P0 gatekeepers (retrieval+citation, ingestion, decision dependencies), P1 statistics completion and finance/valuation, P2 catalogue breadth, plus the non-computational gaps in manual §15B/§16; with tier/verification notes and a recommended order.
**Files:** `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Verified:** docs only; cross-checked against `DECISIONS.md` and module inventory.
**Commit:** `8c71814`.
**Open/next:** decide which gap to close first (the recommended order was discussed, not started).

---

## 2026-10-21 — Taxation recorded as deferred

**Ask:** "does the jobs you did in creating the pipeline include taxation?" → no; "put it in your memory".
**Did:** recorded **B-052 DEFERRED**: the manual makes tax a non-goal and a jurisdiction-specific area to keep out of the autonomous path or gate behind retrieved sources; resume conditions (VAT/GST, income tax in the accounts, after-tax appraisal, filing) and the evidence lines from the manual are in the decision.
**Files:** `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
**Decisions:** B-052.
**Verified:** read-only analysis against `docs/sources/business_pipeline_v0_3.md` and `src/bp/methods.py`.
**Commit:** `efa9404`.
**Open/next:** product gap map.

---

## Backfill — earlier increments (v0.13 … 0.25)

Earlier work predates this log. The full ordered record is `docs/CHANGELOG.md` (0.13–0.25) and the stage reports; do not duplicate it here. In short: deterministic pipeline + spec/freeze (Stage 0–4), method library and golden fixtures (Stage 5), catalogue registry and T4 templates (Stage 6), model-provider boundary with evaluation scaffold (B-031/B-036/B-038/B-039), literature retrieval boundary (B-040), statistics increments (B-042), forecasting (B-043), and the Stage 8 accounting chain — schedules, two-route cash flow, closing/rollforward, declarative engagement, reconciliation, account-mapping checkpoint, policy changes, statement exports (B-044–B-051). The first commit in this repository is `1ab1d05`; the last pre-worklog increment is `efa9404`.
