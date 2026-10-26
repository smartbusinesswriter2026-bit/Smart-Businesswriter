# Known limitations (release blockers marked *)
- * Sandbox is partial (see Stage 5 increment 5): vetted T1 code runs in a guarded child process, but this is NOT a security boundary. T2/T3 (model-written code) still need an OS-level container. Untested on Windows.
- * No authentication, tenant/case isolation or retention; sessions are in memory only.
- * No model calls: intake, formalization and drafting are deterministic templates, not model-assisted.
- Only NPV and break-even are executable (T1). No T2/T3, accounting, statistics, research or framework registry.
- "Revise brief" is intentionally absent (not built). Reject is the only alternative to confirm.
- Claim-wording phrase lists are placeholders [UNVERIFIED].
- Missing sources: v0.3 manual, research-pipeline manuals, frameworks catalogue.
- Server is for local development, not production.

## Added at Stage 5
- Statistics: descriptive only, one variable. No inference, intervals, effect sizes, groups, weights, quartiles, .sav input.
- Golden fixtures are hand-verified; NIST and SPSS reference outputs have not been generated. Provenance of the NumAcc1-style case is [UNVERIFIED].
- env_hash now fingerprints the interpreter, platform and bp source; it does not pin third-party packages because none are used.
- Claim typing is still by phrase lists, not a reviewer model.
- Provenance tags on inputs are declared by the requester and not independently checked.
- Manual v0.3 features not built: case workspace (5.9), learning loop (10.1), ingestion controls, .sav/.sps handling, 15B items.

## Added with correlation
- Only two variables, one test; no multiple-comparison correction machinery beyond a declared "none".
- Normality screen is a skewness/kurtosis screen, not a formal test; linearity and independence are untested.
- Spearman interval and p-value are approximations; the interval formula is [UNVERIFIED].
- No power calculation, weights, clustering, partial correlation, or SPSS-default comparison (9B.4 register lists only our own defaults).

## Added with regression
- OLS only: numeric predictors, up to five; no categorical, interaction, polynomial, weighted, clustered or time-series models.
- Diagnostics are coarse screens with conventional limits [UNVERIFIED]; they may block valid data or pass flawed models.
- No out-of-sample validation, so no predictive claims (manual 7); associational ceiling only.
- No power or sample-size calculation; no multiple-comparison correction.

## Added with group comparison
- Two independent groups only: no paired data, more than two groups (ANOVA), proportions or counts (chi-square).
- Mann-Whitney interval and Hedges' g interval are approximations [UNVERIFIED against a published reference].
- Group-size minimum of three for Welch and about four for a Mann-Whitney interval.

## Added with the sandbox
- Guards are best-effort (patched socket, open, os and subprocess calls). Code using low-level calls (os.open, ctypes, native extensions) could bypass them. Do not run untrusted or model-written code on this layer.
- Memory cap uses the POSIX resource module; on Windows only the timeout applies. No CPU-time limit beyond the timeout.
- Developed and tested on Linux. The Windows path (python -S -s, SYSTEMROOT environment) is untested. If the sandbox fails there, runs block with "sandbox failure" and `--no-sandbox` is a development-only workaround.
- Builder patching is disabled when the sandbox is on (T1 only). Fallbacks still work.
- Re-performance compares outputs exactly or within 1e-12; results on another OS or Python version may differ in the last digits of float-derived values and are then reported as within tolerance, or as an environment difference.
- Unit tests run in-process for speed; sandbox behaviour is covered by tests/test_sandbox.py.

## Added with the registry
- Recommendations are lexical: they miss paraphrases and can suggest a loosely related item. They suggest; they never apply.
- Every record is "unreviewed". There is no limitations, contraindication or evidence data, so the system cannot yet say what a framework will miss or how well supported it is.
- No framework templates: selected frameworks guide a T4 text answer and are recorded in the spec; they do not yet drive a structured analysis.
- Theory citations must come from retrieved sources; the system has no retrieval of research literature, so supporting theories are pointers only.
- Evaluation set is small, author-written and not expert-reviewed.
- Edition and permission checks for standards are flagged, not performed.

## Added with framework templates
- Only SWOT (with STR-18 audit) and Five Forces have templates; the system cannot check that evidence is accurate or items are correctly classified.
- Evidence text is limited to 400 characters on one line, 60 items, 20 options, for safe verbatim reproduction.
- Reports quote your evidence; if it contains personal or confidential data, it appears in the report and bundle.
- TOWS pairing labels are derived, not judged; options themselves are yours.

## Added with the business-case slice
- The comparison is only as good as the facts, alternatives, cash flows and rates you enter; the system does not assess realism.
- NPV only, with certain cash flows; no risk weighting, probabilities, break-even comparison, or unequal-life adjustment.
- Decision rule "highest_npv" is the only rule; other rules (payback limits, budget constraints, multi-criteria weights) are not implemented.
- Default alternative ids are positional; supply ids to keep them stable when reordering.
- No model-assisted steps (no case reading, alternative generation or reviewer challenge).

## Added with the ledger spike
- The ledger kernel is a spike: not wired into the pipeline, no UI, no mapping-confirmation checkpoint, one period only, no schedules, no cash flow statement, no reconciliation, no standards retrieval.
- Flags (abnormal balance, contra-name heuristic, missing accrual) are heuristics that suggest items to confirm; they will miss problems and produce false alarms.
- Mid-year policy changes cannot be detected without a declared input.
- Beancount was not evaluated; the manual's statements about it are unverified.
- The research workflow (formerly Stage 7) has a **ratified living manual** but no built stages: `docs/RESEARCH_EVIDENCE_WORKFLOW.md` is the working authority for REW (B-053, R11 ratified), while its stages R0–R8, feasibility tiers and study taxonomy remain PROPOSAL/OPEN until the owner ratifies R1–R10; the ten original blocking questions are preserved there as Q1–Q12.
- Only the literature retrieval/verification boundary exists (src/bp/literature.py, PROVISIONAL; smoke-tested live against one DOI, not evaluated across sources or formats). It records a response SHA-256 + UTC retrieval time per resolved retrieval (B-054), but keeps no durable retrieval log, so a hash proves what the source served at verification time — not that its metadata is correct, nor that the DOI still resolves later.

## Added with the model provider
- Never run against a real model. The Anthropic, OpenAI-compatible and DeepSeek adapters are unit-tested with a fake opener only; no live call has been made.
- Proposal quality is unmeasured; no evaluation set of real cases exists yet (a scaffold with synthetic fixtures was added, `src/bp/evaluate.py`).
- The quote check prevents additions beyond submitted text but cannot stop quoted injected text; user review is the control.
- The PII scan is a heuristic. Text leaves the machine when assistance is used; personal data is allowed only with explicit acknowledgment (B-038).
- Proposals are not reproducible; only their hashes are recorded.
- Only three tasks (facts, alternatives, critique) and only the business-case flow use assistance; other methods and templates do not.
- Cost is capped by call count only; no price table.

## Added with ANOVA, Kruskal-Wallis and chi-square
- ANOVA covers three or more independent groups only; no post-hoc pairwise tests, repeated measures, factorial designs or Welch ANOVA (equal-variance failures switch to Kruskal-Wallis instead).
- Chi-square is independence-only on count tables; goodness of fit, Fisher's exact and Yates corrections are not implemented, and any expected count below the declared floor (5) blocks the analysis.
- Skew/kurtosis limits (2/7), Levene level (0.05), eta/epsilon cut-offs (0.01/0.06/0.14), Cramer's V cut-offs (0.1/0.3/0.5) and the expected-count floor (5) are conventions from memory [UNVERIFIED], declared and overridable (B-042).
- Kruskal-Wallis p-values and Cramer's V use approximations; no confidence interval is reported for the rank-based effect size.

## Added with trend forecasting
- The forecast is a linear trend only: no seasonality, cycles, external drivers, structural breaks, exponential smoothing or ARIMA, and it extrapolates beyond the observed range.
- The out-of-sample check holds out a quarter of the series (capped at 3 periods) and reports the recent-past error; it cannot measure future accuracy.
- The holdout-size rule, minimum series length (6), horizon cap (12) and small-sample wording threshold are placeholders (B-043).
- Prediction intervals assume independent, roughly normal errors around the trend.

## Added with the Stage 8 schedule engines
- Schedules cover straight-line depreciation, level- or fixed-payment loan amortization, and straight accruals only; no declining-balance or units-of-production depreciation, no variable-rate loans, no prepayments.
- Rounding rules are declared: depreciation's final period absorbs the remainder; interest rounds half-even; a payment never exceeds the balance due (so a large fixed payment repays early); the level annuity rounds up. Amounts beyond the currency places are rejected, never silently rounded.
- Schedule specs are validated data, but the module is not yet wired into the pipeline, the sandbox, or the workbench, and there is no account-mapping confirmation checkpoint yet.
- Management accounts only; not GAAP/IFRS-compliant statements (manual 9.5).

## Added with the cash flow statement
- The cash flow statement covers the period's movements only (opening balances excluded) and its two-route check guards the total change in cash, not the operating/investing/financing split.
- Activity classification is a declared heuristic: explicit account activity tags win; otherwise income/expense defaults to operating, assets to investing, liabilities/equity to financing. Mixed-counterpart entries are classified operating-first and flagged; cash-to-cash transfers are flagged. The manual's account-mapping checkpoint should replace these defaults.
- The cash flow check is a separate `cash_flow()` result, not part of the six frozen ledger invariants.

## Added with multi-period closing
- Closing moves income, expense and declared dividend balances into retained earnings through generated entries the caller posts; accounts with abnormal balances block closing until a human decides.
- The retained-earnings rollforward (B-034 resolved) and the zero-after-closing check are separate checks, not part of the six frozen ledger invariants.
- Multi-period support chains one period into the next (closing balances → opening entry → opening-balances invariant), but output is still per-period: no comparative multi-column statements.
- `statements` omits zero-net accounts, so a closed income/expense account or a fully repaid loan shows nothing rather than zero.

## Added with the declarative engagement
- The engagement method is T2 custom analysis pending the engine decision (B-032) and a named expert review; the report and the appendix state this.
- The spec must declare `prior_closing` balances ({} for a first period) and a reporting framework; the kernel posts only what the owner declares (entries, schedules, closing) and never posts silently.
- Structured results (statements, trial balance, cash flow, flags, export) travel in the appendix; the narrative report carries only scalar totals.

## Added with the reconciliation engine
- Matching pairs a book movement with a statement line of the same signed amount only; several lines with the same amount are paired first-unused and flagged `ambiguous_match`. No date or reference matching is implemented.
- Unrecorded statement items (for example bank charges) are listed for the owner to book; they are action items, not failures. The reconciliation ties once the disclosed adjustments are shown.
- The reconciliation checks are "not applicable" when the engagement supplies no reconciliation; they are counted in `checks_na` rather than silently passing.
- Reconciliation runs on the engagement's period only; opening balances come from the opening entries and must equal the statement's opening balance.

## Added with the account-mapping checkpoint
- The second mandatory checkpoint pauses after the spec is frozen and before anything is posted; the owner confirms a mapping table of code, name, type, statement line, role, activity and contra, plus three mapping checks. Rejecting blocks with nothing posted.
- `Pipeline.run` is a convenience path that confirms both checkpoints automatically (documented); the interactive path through the session/API honours the pause.
- The checkpoint is logged under the formalization stage (`checkpoint: account_mapping`) rather than as a new stage, so the stage list is unchanged for every method.
- Mapping checks are structural only (a statement line per account, a cash account, one retained-earnings account); they do not verify that the owner picked the right account for a transaction.

## Added with the policy-change input
- Only depreciation supports a computed policy change (useful-life and residual-value revisions); other estimate changes are disclosure-only, and retrospective restatement is not implemented (it blocks).
- A change is applied prospectively from the period containing its date; earlier periods are never restated.
- An UNDECLARED change remains undetectable from the journal alone — the spike's mid-year-change trap is unchanged; the declared input is the only way the system learns of it.
- The change total remains exact: the final period absorbs the rounding remainder, so accumulated depreciation still equals cost minus the final residual.

## Added with the statement exports
- Exports are plain text only (no PDF, XLSX or DOCX); fixed-width formatting is designed for a monospace view and a text download.
- The income statement is rendered from pre-closing figures while the balance sheet is post-closing, which is the correct pairing for a closed period; the trial balance omits zero-net rows.
- The cash flow statement presents the direct-route line items and the three activity totals; the indirect route appears only as its agreement check.
- Statements are management accounts prepared from the declared entries; they are not a GAAP/IFRS presentation and are not assurance.

## Added with retrieval failover and the drift sweep (B-064)
- Failover covers only the two configured literature sources (Crossref, then OpenAlex). If both are unreachable the lookup fails with a 502 rather than silently marking the DOI unverified; if both report "not found", the reference stays unverified.
- The drift sweep is **manual**, bounded (API default 10, cap 25) and network-bound: it re-resolves recent logged DOIs and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable`. There is no scheduled or automatic re-check, and it never rewrites the log.
- A `hash_differs` result means the source served different bytes since the citation was logged — it is a prompt for a human to re-check the metadata and the citation, not an automatic correction. `hash_match` proves the bytes are identical, not that the record is correct.
- The sweep uses the same priority order as verification, so a source that is down can make entries `unreachable` even though the log itself is intact.
- Standards, company-filing and tax source families are still not implemented, and no additional scholarly APIs (arXiv, PubMed, Semantic Scholar, Europe PMC) are configured; adding them needs a source/licensing decision, not more code.

## Added with the weighted summary (B-063)
- `weighted_summary` produces **summaries only**: weighted mean, weighted standard deviation, effective sample size and design effect. There is **no standard error, confidence interval or test**, because design-based inference needs a declared complex design (stratification, clustering, replicate weights) that is not implemented. The delivery says this explicitly.
- The weight kind must be declared: `reliability` (precision-style, unbiased weighted variance) or `frequency` (counts of observations). The two give different standard deviations; the convention is stated in the appendix.
- Weights are not validated. A wrong design weight is used as given, and unequal weights reduce the effective sample size — the design effect shows by how much. Zero, negative, mismatched-length and blank weights are refused rather than silently dropped.
- This is the only method that accepts weights. Other statistical methods still refuse a `weights` input with a specific reason, so a weighted dataset cannot be analysed as if it were a simple random sample elsewhere.

## Added with the missing-data bounds (B-062)
- `missing_data_bounds` reports **extreme-case bounds** for the complete-data mean: every missing value at the observed minimum or maximum. The bounds are honest but can be very wide, and a wide bound is the correct answer when little can be assumed.
- There is **no imputation** and **no MAR/MCAR/MNAR model**. The `mechanism` input is the owner's declaration: it is recorded with a note that it cannot be verified from the data, and it changes no number.
- The bounds cover the mean only. They say nothing about other statistics, about which mechanism actually holds, or about the direction of bias in an association.
- The generic missing-data disclosure (listwise deletion) is suppressed for this method because its own convention is stronger; the method's own disclaimer is delivered instead.

## Added with the power and minimum-effect method (B-061)
- `power_analysis` uses the **normal approximation**: exact when the standard deviations are known or planned, but with sds estimated from a pilot the exact power is somewhat lower (noncentral t is not implemented). This is declared in the template, the caveats and the appendix.
- It covers a two-sample or one-sample comparison of means only: no proportions, no cluster/weighted/repeated designs, no multiplicity (a family needs a smaller per-test alpha; use `multiple_comparison`), and no correlation or regression power.
- Power is a property of the planned design, not evidence about a result; a low-power study can still be significant and a high-power one can still fail. The reported "smallest effect at target power" is not a licence to ignore smaller effects.

## Added with the multiple-comparison correction (B-060)
- `multiple_comparison` corrects a family the user has already declared: it does not decide what the family should be, and choosing the family after seeing the p-values cannot be undone by a correction.
- Only Holm and Bonferroni are implemented. Both control the family-wise error rate under arbitrary dependence; neither models dependence, and there is no false-discovery-rate control (Benjamini-Hochberg) or resampling correction.
- The correction changes the reported p-values, not the design: a biased sample, a violated test assumption or a badly specified model stays biased or violated after correction.
- The existing statistical methods do **not** apply a correction automatically; their honesty block says so and points to `multiple_comparison`. There is no facility to assemble a family across several separate method runs.
- Power/MDE calculation, missing-data mechanism modelling/imputation and survey weights remain unimplemented (B-057 disclosure still applies to them).

## Added with the retrieval log and provisional citations (B-058)
- The retrieval log is **local and append-only** (one JSONL file, default `retrieval_log.jsonl`, `BP_RETRIEVAL_LOG` overrides): it is not a shared cache, is not encrypted, has no rotation or retention policy yet, and has no locking between concurrent server instances. It holds DOIs, titles and hashes, not case text.
- The log records **what the source served at that moment**, not that the metadata is correct, and the source may change afterwards. `reverify` is manual — there is no scheduled drift check.
- Citations follow the owner-ratified styles **APA 7** and **Harvard (Cite Them Right)** (B-059), but in plain text: italics (journal names, volumes) are not representable, titles are printed as the source returns them rather than case-converted, and author names are inverted only when the source supplies family and given names (Crossref does; OpenAlex returns display names only, and its citations carry a note saying so). There is no bibliography ordering or de-duplication and no in-text citation numbering.
- Only journal articles and books are fully styled. Any other source type (report, chapter, thesis, dataset) gets a declared generic layout with a note naming the source type, rather than a style that would imply it was handled properly.
- An unverified reference is always formatted with the `[unverified user-supplied…]` prefix in either style; the system cannot stop that text being pasted elsewhere, but the label is in the text itself.
- The workbench citation and log views are read-only conveniences over the API; the durable record is the file itself.

## Added with the 9B.3 honesty layer (B-057) — disclosure only, not the fix
- Every delivered computation now **states** the 9B.3 limits in the report and in an `appendix.honesty` block: missing values are excluded listwise without an established mechanism; multiple hypotheses are not corrected; no power or minimum-detectable-effect is computed; weights, clusters and repeated measures are unsupported and observations are treated as independent.
- **No number changes.** The actual upgrades are NOT implemented: there is no Holm/Bonferroni or other multiple-comparison correction, no power/MDE calculation, no missing-data mechanism modelling or imputation, and no survey-weight or clustered-data estimation. The disclosure makes the gap visible; it does not close it.
- Inputs that name an unsupported structure (`weights`, `weight`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are refused with a specific reason at intake, so such a dataset cannot be passed in and silently analysed as independent observations.
- Single-method runs test one hypothesis (OLS tests one per coefficient, with the family-wise exposure named); there is no facility to combine several methods into one corrected family. Post-hoc pairwise tests do not exist yet, so no correction is applied to comparisons that are not made.

## Added with ratio analysis (B-056)
- `ratio_analysis` is purely descriptive arithmetic on figures the owner supplies: no benchmark, industry average, cut-off or good/bad verdict is applied, because none is supplied or verified. A ratio being high or low is for the reader and the context to judge.
- Period-end balances and a 365-day year are declared conventions; average balances or a 360-day year would give different efficiency ratios.
- A ratio with a missing figure or a zero denominator is reported as not computed with its reason and never estimated; a negative denominator (for example negative equity) is computed and flagged, not hidden or reinterpreted.
- The supplied figures are not validated against a trial balance here, and no tax computation is performed (net income is used exactly as supplied). Multi-period comparatives, segment and multi-currency analysis are not supported; use `management_accounts` for the bookkeeping-level check.

## Deferred areas
- Taxation (B-052): out of scope — the pipeline can hold tax balances (accounts + declared entries) but computes no VAT/GST, income tax, deferred tax, capital allowances or tax-aware appraisal, and does not file. Deferred by the owner; see `docs/DECISIONS.md` B-052 for the resume conditions.
