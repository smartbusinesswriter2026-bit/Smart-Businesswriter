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
- Stage 7 is blocked for the pipeline definition (docs/STAGE7_BLOCKER.md); only the literature retrieval/verification boundary exists (src/bp/literature.py, PROVISIONAL, untested against the live APIs).

## Added with the model provider
- Never run against a real model. The Anthropic, OpenAI-compatible and DeepSeek adapters are unit-tested with a fake opener only; no live call has been made.
- Proposal quality is unmeasured; no evaluation set of real cases exists.
- The quote check prevents additions beyond submitted text but cannot stop quoted injected text; user review is the control.
- The PII scan is a heuristic. Text leaves the machine when assistance is used.
- Proposals are not reproducible; only their hashes are recorded.
- Only three tasks (facts, alternatives, critique) and only the business-case flow use assistance; other methods and templates do not.
- Cost is capped by call count only; no price table.
