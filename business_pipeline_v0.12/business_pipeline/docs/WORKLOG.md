# Worklog — append-only record of what was done

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
