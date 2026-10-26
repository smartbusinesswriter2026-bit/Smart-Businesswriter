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
- The research workflow (formerly Stage 7) has a **living manual** but no built stages: `docs/RESEARCH_EVIDENCE_WORKFLOW.md` proposes stages R0–R8, feasibility tiers and a study taxonomy, all tagged PROPOSAL/OPEN until the owner ratifies them (R1–R11); the ten original blocking questions are preserved there as Q1–Q12.
- Only the literature retrieval/verification boundary exists (src/bp/literature.py, PROVISIONAL; smoke-tested live against one DOI, not evaluated across sources or formats) and it does **not** yet store a retrieval response hash or date per reference.

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

## Deferred areas
- Taxation (B-052): out of scope — the pipeline can hold tax balances (accounts + declared entries) but computes no VAT/GST, income tax, deferred tax, capital allowances or tax-aware appraisal, and does not file. Deferred by the owner; see `docs/DECISIONS.md` B-052 for the resume conditions.
