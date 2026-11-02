<!-- Faithful Markdown rendering of the supplied source document. If formatting or interpretation differs, the original DOCX is authoritative. -->

# business_pipeline: Architecture Manual

Version: 0.3 (draft) · Date: 2026-10-19 · Status: living document

## 0. How to read and maintain this document

This manual defines a conversational system that helps users solve business problems with computation and write papers or reports from the results. It is written so that a human engineer or an AI model can build the system from it without having seen the design discussion that produced it.

- MUST, SHOULD and MAY are used in the normative sense.

- Status tags: [DECIDED] agreed in design discussion. [PROVISIONAL] a working choice expected to change with evidence. [OPEN] unresolved. [UNVERIFIED] a factual claim made from memory that must be checked before anyone relies on it.

- Update rule: never change a decision silently. Add an entry to the Decision Log (section 17) and the Change Log (section 18) stating what changed and why. Evaluation evidence outranks opinion.

- Until amended, this document wins over a builder’s convenience.

## 1. Purpose, users and scope

Purpose. Users bring business problems of any kind (finance, accounting, operations, strategy, forecasting) through a chat interface. The system formulates the problem, solves it with verified computation, and writes the resulting paper or report. Fixed dropdowns and hard-coded pipelines cannot cover the space of problems, so the interface is conversational and the solution method is composed per problem.

Users. Most users are non-accountants and non-specialists. Accountants and other experts will also use it, test it, and criticize it. The design MUST hold up under expert scrutiny. [DECIDED]

First users (v0.2, revised v0.3). The first users are students. Most problems are one-off: a dataset or case, a question, a paper or report, and then the student leaves. Some students return with the same company, for example a case study that runs through a whole course, and each later paper must agree with the earlier ones. [DECIDED] Consequences: (a) explanation matters as much as computation, because a student must understand and defend the work; (b) one-off use is the default path and depends on no stored state, while a case workspace serves returning cases (section 5.9); (c) statistical methods carry more weight than they would for a practitioner base, because coursework and theses rely heavily on survey and experimental analysis (section 9B); (d) academic conventions and institutional AI-use policies apply to the output (section 15B).

Stakes. Not yet defined. The cost of a wrong answer differs greatly between a student term paper and a capital allocation decision or a filing to a bank or authority. [OPEN] (see section 16). Until resolved, build for the stricter case.

Priorities, in order: robustness, usefulness, correctness. Implementation cost is not a constraint at this stage. [DECIDED]

Non-goals. The system is not an auditor and does not provide assurance. It does not file taxes. It does not give legal or investment advice. It does not promise correct answers to all problems (see 3).

What the system promises.

- Every number shown has a derivation that can be inspected.

- Every output is correct given its stated assumptions, or it is blocked.

- Assumptions, ambiguities and judgment calls are surfaced, not hidden.

- Each claim is worded no more strongly than its evidence allows.

- An error, when it occurs, can be traced to its cause quickly.

What it does not promise. That every answer is right. Wrong inputs, wrong problem formulation and wrong accounting classification can all survive every automated check.

## 2. Design principles

- P1. The model never produces a number. The model produces a problem spec and code. Numbers come only from execution. The same holds for text: figures in prose are injected from computed artifacts.

- P2. Correctness has three layers (section 3). The pipeline guarantees the first, surfaces the second, flags the third.

- P3. Tier by verifiability, not difficulty (section 5.3).

- P4. Deterministic spine, bounded agents. Code decides the order of stages and whether verification runs. Agents are subroutines whose output always passes a check they do not control.

- P5. Freeze before running. Spec and tests are fixed before execution. Changes are versioned amendments with reasons. A check failure may trigger an amendment. A result that merely “looks off” may trigger an investigation, and any change that follows is disclosed.

- P6. Claims earn their wording (section 7).

- P7. Ambiguity is a first-class output. Proceed under stated defaults and report their impact instead of blocking.

- P8. Fail closed. A failed check blocks or removes the output. It does not add a caveat.

- P9. Re-performable. An expert MUST be able to reproduce every number from the delivered files.

- P10. No runtime self-modification. The system never edits its own code, tests, verifiers or library at runtime. Improvement happens offline, driven by evaluations and human review.

- P11. Decision-flip is the filter for caveats. An unresolved item reaches the headline only if it can flip the recommendation within its plausible range.

## 3. The three correctness layers

| Layer | Question | What the pipeline can do |
| --- | --- | --- |
| Computational | Given the formulated problem, is the math right? | Guarantee, by tested methods, independent recomputation and invariants |
| Formulation | Is this the right model of the user’s situation? | Surface: spec confirmation, ambiguity register, reviewer pass. Cannot guarantee |
| Input | Are the data and assumptions right? | Flag: profiling, tie-outs, provenance tags, sensitivity. Cannot guarantee |



A system that is perfect on layer 1 can still deliver a wrong answer. User-facing design MUST show key inputs and assumptions next to every headline number, because a number derived correctly from a bad input will be perceived by users as a hallucination.

## 4. System overview

The orchestrator is deterministic code. It executes the stages below in order and cannot be skipped by any model.

| # | Stage | Executed by | Output |
| --- | --- | --- | --- |
| 1 | Intake and data profiling | Bounded agent plus deterministic profiler | Intake summary, data profile |
| 2 | Formalization | Model proposes, user confirms | Problem Spec (frozen, hashed) |
| 3 | Method selection | Deterministic router with model assist | Method plan with tier label |
| 4 | Test planning | Verifier model (different instance or model family from builder) | Test plan, frozen before execution |
| 5 | Execution | Deterministic sandbox | Hashed artifacts |
| 6 | Verification | Deterministic checks and invariants | Pass or fail, amendment log |
| 7 | Sensitivity | Deterministic | Ranges, decision-flip results |
| 8 | Drafting | Model writes templates, renderer fills numbers | Draft with reference tokens |
| 9 | Draft audit | Deterministic scans plus reviewer model | Claim typing and number matching |
| 10 | Delivery | Deterministic | Report, workbook, exports, provenance appendix |



The user is a participant at two mandatory checkpoints: spec confirmation (stage 2) and, for accounting work, account mapping confirmation (section 9).

## 5. Stage specifications

### 5.1 Intake and data profiling

- Conversational loop extracts objective, constraints, available data, and decision context (who decides, what is at stake, by when).

- Ask only questions whose answers could change the decision. Otherwise choose a default and record it in the ambiguity register.

- Before formulating anything, profile every supplied file: merged cells, duplicate IDs, missing periods, unit and scale ambiguity, sign conventions, currency, outliers. Report anomalies to the user.

- Uploaded documents (PDF, scans, images) follow the ingestion controls in section 11, control 3.

- Statistical-package files (for example SPSS .sav) are read with variable labels, value labels and user-defined missing-value codes preserved, so that a code such as 99 is never treated as a real value (section 9B). [PROVISIONAL]

- On intake, check whether the problem belongs to an existing case workspace (section 5.9) and, if so, ask the user to confirm it before anything is reused. [PROVISIONAL]

### 5.2 Formalization and the Problem Spec

The model drafts a Problem Spec (Appendix A). The user confirms it. On confirmation the spec is hashed and frozen. Changing the question mid-way creates a new spec version. Results from earlier versions MUST NOT be silently reused.

The spec contains: objective; decision context; typed claims; inputs with provenance; assumptions each with a provenance tag, plausible range and citation where applicable; method; pre-declared checks; pre-declared sensitivity ranges; numeric thresholds for qualitative words (“significant”, “high risk”); ambiguity register; data requirements manifest (absent, obtainable later, proxyable); user-owned values (risk tolerance, time horizon, trade-off weights).

### 5.3 Method selection and verifiability tiers

| Tier | Description | Trust and handling |
| --- | --- | --- |
| T1 | Vetted method library: tested functions (NPV, break-even, EOQ, LP, regression, forecasting, schedules, statistical procedures per section 9B). The model fills parameters only | Highest. Labeled “standard method” |
| T2 | Bespoke code written by the model in the sandbox | Heavier verification: independent reimplementation, reconciliation to source. Labeled “custom analysis” |
| T3 | Bounded agentic exploration: no matching method, or T2 verification failed | Capped steps, fully logged. Labeled “exploratory” |
| T4 | Framework only: how to think about it and what data would be needed | No computed answer is given |



Escalation is triggered by verification failure or absence of a matching method. It is never triggered by the model’s sense of difficulty. [DECIDED]

Library promotion. A T2 solution that passes human expert review MAY be promoted to T1. This is the sanctioned growth mechanism. Promotion requires tests, documentation and a named reviewer. [DECIDED]

### 5.4 Execution

- Sandboxed, pinned environment (environment hash recorded), fixed random seeds, no network access during computation.

- Every output is stored as a hashed artifact (Appendix B). Artifacts are immutable.

- Decimal arithmetic, never binary floats, for monetary and accounting quantities. Statistical work may use floats but results are converted to typed quantities at the boundary.

### 5.5 Verification and amendment control

- The test plan is written from the spec before the code runs, ideally by a different model instance or family than the builder. Typical tests: reconciliation to source totals, boundary cases (zero discount rate equals sum of cash flows), monotonicity (raising costs lowers NPV), independent second implementation agrees within tolerance.

- If a test fails, the builder agent MAY patch the code. Every patch is a logged amendment: diff, failing test, reason.

- After N amendments (initial N = 3 [PROVISIONAL]) the run escalates to a human or to a lower tier.

- The builder MUST NOT modify tests, thresholds or the verifier. Tests change only by a spec amendment that is logged and disclosed in the final report.

- Tuning toward a plausible-looking result is prohibited. This is p-hacking by another name.

### 5.6 Sensitivity, multiverse and decision-flip

- Run the pre-declared sensitivity ranges for assumptions that drive the result. Report ranges and a tornado chart, not only a point estimate.

- Where several reasonable specifications exist, run the pre-declared set and report the spread (multiverse reporting).

- Decision-flip analysis. For every unresolved item (missing data, assumption, user value), compute whether the recommendation changes across its plausible range, and the threshold at which it flips. Flippers go in the headline. Non-flippers go in an appendix.

### 5.7 Drafting

- The model writes text containing typed reference tokens, for example {{ref:rev_q3}}. It does not write digits (section 11).

- The renderer substitutes artifact values, applying formatting and the accounting conventions in section 9.

- Tables and charts are generated by code from artifacts. The model never types a table cell.

- A methods section is generated from the actual run log, not written from the model’s recollection.

- Sources are retrieved and verified. The model MUST NOT cite from memory.

### 5.8 Delivery

Every delivery includes: the report; a workbook with live formulas where applicable; data and journal exports; the provenance appendix (every assumption, amendment, check result and tier label); a limitations page; and, for non-accountant users, a “take this to your accountant” list of judgment calls to confirm.

### 5.9 Case workspace (returning cases) [PROVISIONAL]

Some users return with the same company or case, for example a case study that runs through a course. A case workspace is an entity-scoped container that lets later work build on earlier work without relying on chat memory. It is scoped to the case, not to the user’s profile.

- Contents: entity identity and fiscal calendar; reporting framework; confirmed account mapping; source documents and data with provenance and retrieval dates; confirmed spec versions; baseline artifacts (hashed and immutable); assumption register; amendment history (Appendix C).

- Activation: the user names an existing case, or the system proposes a likely match and asks. A workspace is never applied without confirmation, and one-off runs need none. A workspace is created only when the user chooses to keep the case.

- Reuse rules: earlier results enter new work only as artifacts, tagged computed with a pointer to the originating run (section 6), never as remembered numbers (section 11, controls 5 and 6). On reuse the user re-confirms the account mapping and framework. A new spec version never silently reuses earlier results (section 5.2).

- Staleness: new period data, restated or re-retrieved sources, a changed assumption, a changed standard, or a new library or environment version marks dependent artifacts stale. Stale artifacts are recomputed, not patched, and the change is reported.

- Cross-deliverable tie-out: within a workspace, a metric for the same entity, period and scope MUST match across deliverables, or the difference is disclosed with its cause. A mismatch with no disclosed cause blocks delivery (P8).

- Ownership and retention: the workspace is user-owned, visible, exportable and deletable, and is not shared with other users. Deleting it removes the derived artifacts. The retention period is [OPEN] (section 15B). Team access, where a group works on one case, is [OPEN].

## 6. Provenance and typed quantities

Provenance tags. Every number in the system carries exactly one tag. Untagged numbers MUST be rejected.

- user: supplied by the user.

- sourced: retrieved from a cited source with date and supporting span.

- assumption: chosen explicitly, with rationale and plausible range.

- computed: produced by execution, with a pointer to its artifact.

Typed quantity. A number is a Decimal value plus unit, currency, period, scale (units, thousands, millions) and precision. Operations on mismatched types MUST raise an error. Display rounding is separate from stored precision. Totals must foot after rounding, with any rounding difference disclosed.

Reference metadata. Each artifact carries metric, period, entity and scope labels. A reference token in the draft declares the metric and period it intends. The renderer rejects a mismatch. This is the principal defense against citing the wrong artifact (section 15).

Lineage. Every displayed number links to its derivation: formula, inputs, code hash, source location.

## 7. Claim licensing

Every claim in the spec has a type. The type determines the evidence it must earn and the strongest wording the writing layer may use.

| Claim type | Example | Must earn |
| --- | --- | --- |
| Descriptive | “Revenue grew 12%” | Data reconciliation |
| Associational | “Loyalty members spend more” | Above, plus uncertainty quantification |
| Predictive | “Revenue will be X next year” | Out-of-sample backtest beating a naive baseline |
| Causal | “The program raised spend” | Stated identification strategy, its diagnostics, robustness and confounding-sensitivity analysis |
| Prescriptive | “We should expand” | Everything it depends on, plus user-owned values |



Accounting adds: mechanical (derived from records), estimate, policy choice (standards permit alternatives) and interpretation (standards must be read and applied).

Enforcement.

- Each type has an approved phrase ceiling (for example, “is associated with” for associational; “is estimated to cause, assuming X” for causal). The writing layer cannot exceed it. Verb strength is checked mechanically.

- A reviewer model independently types every sentence of the draft. Disagreement with the spec’s typing goes to the user.

- Intervention language (“if we do X”, “effect of”, “impact of”) is auto-flagged as causal regardless of how the spec typed it.

- If evidence fails the checklist, the claim is downgraded automatically and the report states what would settle it (for example, a holdout experiment).

- Causal claims never reach “certain”. Unmeasured confounding cannot be ruled out.

## 8. The four breakpoints

- Causal claims from observational data. Require a causal graph with named confounders, an identification strategy (experiment, difference-in-differences, instrumental variable, regression discontinuity, adjustment) and its diagnostics. Run confounding-sensitivity analysis. On failure, downgrade to association.

- Forecasts across regime change. Rolling-origin backtests including shock periods, structural-break tests, comparison to a naive baseline. If the model does not beat the baseline, downgrade. Deliver conditional scenarios with the stability assumption stated and named indicators that would signal failure. Label: valid only while conditions resemble the history.

- Data the user cannot supply. Maintain the data manifest. Use decision-flip to compute the threshold at which the missing value would change the decision. Proxies and benchmarks are allowed with citation, disclosed bias and the assumption tag.

- Judgment calls. Separate computation from values. Risk tolerance, horizon and trade-off weights are user-owned inputs, never model-chosen. Show the recommendation across their range and the boundary where it flips. For pure values questions, deliver an options-and-tradeoffs matrix and state that no recommendation is made.

## 9. Accounting module

Accounting is a closed, rule-governed system with built-in self-checks, so it can be verified more strongly than other domains. Its hard parts are classification, estimates and standards interpretation, which no invariant catches.

### 9.1 Layered design [DECIDED in structure; engine choice PROVISIONAL]

- Ledger kernel. The journal entry is the only way money moves. An unbalanced entry cannot be constructed. All statements derive from the journal.

- Declarative layer. For common cases the model emits a spec (for example, straight-line depreciation for these assets and dates; map these accounts to these lines). An interpreter executes it. The model cannot do anything unsafe here.

- Code layer. For the long tail the model writes bespoke code, but only through the kernel API. It can define a new schedule or ratio. It cannot create unbalanced entries or write directly to statements. Output is T2.

- Kernel components: chart of accounts and mapping layer (account to statement line, sign conventions, contra accounts); schedule engines (depreciation, amortization, loans, leases, revenue recognition, accruals, FX); statement generators (pure derived views); reconciliation engine (subledger to GL, bank to book, intercompany); analytics layer (ratios, common-size, variance decomposition, DuPont, forecasting, valuation).

- Scenarios are overlays of extra entries on the base ledger, with a diff showing what moved.

- Forecasts run drivers to entries to statements, so they balance by construction. Plugging cash is prohibited. Circularities (interest on average debt) are resolved by iteration with a convergence check.

### 9.2 Ledger engine decision [OPEN, spike required]

Beancount is a candidate. Findings so far:

- Version 3 is modular (query tool and importers are separate packages). Licensed GPLv2-only. Maintenance rated sustainable by a third-party scanner.

- Fits: balance enforcement, declared accounts, Decimal amounts [UNVERIFIED], plain-text ledger that hashes and diffs cleanly, plugin system, query language.

- Gaps [UNVERIFIED unless noted]: no native accrual or depreciation schedules, subledgers, consolidation or framework-aware statements; sign convention stores liabilities, equity and income as negatives; balance tolerance is inferred from input precision and must be set explicitly and strictly; investment-oriented lot booking adds unneeded surface area; it does not detect misclassification.

- Licensing: GPLv2 is copyleft. Hosted use generally does not trigger distribution obligations, but distributing software that includes it does. Obtain legal review before any on-prem or embedded distribution.

- Policy: if used, Beancount is a swappable ledger of record behind a thin adapter. The model MUST construct entries through data structures, not generate ledger text.

- Spike. Implement the trap cases below on Beancount and on a minimal custom kernel. Compare the number caught by construction, glue code required, and accountant readability of exports. Decide from the results and record it in the Decision Log.

### 9.3 Invariants (run on every output, a failure blocks delivery)

- Trial balance debits equal credits.

- Assets equal liabilities plus equity.

- Retained earnings rollforward ties to net income and dividends.

- Cash flow statement ending cash equals balance sheet cash.

- Opening balances equal prior closing balances.

- Subledger totals equal control accounts.

- Intercompany balances eliminate on consolidation.

- Key figures are independently recomputed by a second route (for example, direct versus indirect cash flow).

### 9.4 Mandatory checkpoints and inputs

- Account mapping confirmation by the user before statements are generated. Mapping errors are the most common silent failure.

- Reporting framework (IFRS, US GAAP, local) is a required input, never a default.

- Standards interpretation (lease classification, revenue timing, impairment, capitalization): retrieve the current standard text, cite it, present the treatment as interpretation with alternatives and the facts that would decide it. Do not rely on model memory of recent amendments.

- Estimates (allowances, useful lives, fair values) are explicit assumptions with provenance and decision-flip analysis.

- Tax is jurisdiction-specific and fast-changing. Keep it out of the autonomous path, or gate it behind retrieved sources and a clear label.

### 9.5 Positioning and presentation

Position the output as management accounts and analysis, not “GAAP-compliant financial statements” (which would require notes and disclosures) and not assurance. Get conventions right: statement ordering, parentheses for negatives, normal balances. Cosmetic errors destroy credibility with accountants even when the math is correct. Provide re-performable support: journal export, tie-out schedules, live-formula workbook, cited standards paragraph.

## 9B. Statistics module [PROVISIONAL]

Inferential statistics (t-tests, ANOVA, regression, factor analysis and similar) is a different kind of computation from accounting, and the verification that works for ledgers does not transfer. It is specified as a separate module. The section is lettered 9B so that existing cross-references are not renumbered.

### 9B.1 How statistics differs from accounting and other business computation

| Family | Question it answers | Where uncertainty sits | How it is verified | Statistical packages (SPSS-type)? |
| --- | --- | --- | --- | --- |
| Accounting and financial arithmetic (ledgers, schedules, statements, NPV) | What is the recorded or derived amount under stated rules? | Not in sampling: inputs are treated as exact. The risk is classification, estimates and interpretation. | Invariants (debits equal credits, assets equal liabilities plus equity), independent recomputation, tie-outs | No |
| Decision and optimization models (break-even, EOQ, LP, scenarios) | What is best given these parameters? | In the parameters, handled by sensitivity and decision-flip. | Boundary cases, second implementation | No |
| Inferential statistics (t-test, ANOVA, regression, factor analysis, logistic regression) | What does this sample tell us about something beyond it? | Built in: sampling error, model assumptions, researcher choices. | Assumption checks, reference outputs, resampling, effect sizes, claim licensing | Yes |



A complete ledger is a census, not a sample. Applying a significance test to every transaction of one company-year is a category error, because there is no wider population to infer to. Statistics enters accounting only at the edges: audit sampling, estimating allowances from loss history, anomaly detection and forecasting. Elsewhere in business it covers surveys, experiments, driver analysis and segmentation.

Accounting-style invariants do not protect statistical work. A regression can be arithmetically exact and still wrong because its assumptions fail or because the claim is really causal. Statistical results are therefore governed first by claim licensing (section 7) and the breakpoints (section 8), and second by the checks below.

Where SPSS is used. SPSS is widely used in academic, social-science, market-research and health settings. Finance and accounting practitioners more often use Excel, R, Python, Stata or EViews. [UNVERIFIED] This is a general-knowledge impression, not a measured market fact. Because the first users are students (section 1), SPSS compatibility is a version 1 consideration.

### 9B.2 Procedure scope

The T1 library SHOULD grow in the order below, each procedure with tests and a documented set of defaults. The version 1 subset is [OPEN] (section 16).

- Descriptive statistics, cross-tabulation and chi-square, correlation.

- t-tests (independent, paired, one-sample) and nonparametric alternatives.

- One-way and factorial ANOVA, ANCOVA, repeated measures, post-hoc tests.

- Linear and logistic regression, with diagnostics.

- Reliability (for example Cronbach’s alpha) and factor analysis for survey instruments.

- Clustering for segmentation; time-series forecasting under the regime-change controls in section 8.

### 9B.3 Assumption checks and fallbacks

- Assumption checks (for example normality, homogeneity of variance, independence, multicollinearity, linearity) are pre-declared tests in the test plan (section 5.5) and run before results are reported.

- Each check has a pre-declared fallback (for example a robust or nonparametric alternative) written into the spec before execution. A failed check triggers the fallback as a logged amendment, never as a silent switch.

- Every inferential result reports an effect size and an interval, not only a p-value. Statistical significance and practical importance are stated separately.

- Multiple comparisons: when several tests are run, the correction method is declared in the spec and the multiverse set (section 5.6) is reported in full.

- Missing data: the assumed mechanism and the handling method (for example listwise deletion or imputation) are ambiguity-register items, with their impact reported.

- Sample size: a power or precision statement accompanies each headline result. Small samples downgrade the claim wording.

- Survey weights and clustered data, where present, are declared inputs. Ignoring them is a failed check, not a default.

### 9B.4 Software defaults register

Statistical packages make silent choices, and different packages can give different answers on the same data. Examples, to be confirmed from documentation [UNVERIFIED]: how missing values are handled in a given procedure, which type of sums of squares an ANOVA uses by default, and which extraction and rotation methods a factor analysis uses. Each choice that affects a result is an entry in the ambiguity register (P7), with the default taken and the impact of the alternative. When a user reports that a result differs from SPSS or another package, the system compares these registered choices first.

### 9B.5 SPSS compatibility policy [PROVISIONAL]

- No embedded SPSS and no standing SPSS license in version 1. The procedures are standard and have open-source implementations. A hosted service is unlikely to be permitted under an ordinary license, and IBM’s terms MUST be checked before assuming either way [UNVERIFIED]. The pinned, offline sandbox (section 5.4) also cannot depend on license servers or user accounts.

- Procedures are implemented as T1 methods in open-source libraries (for example Python statistics packages or R). Output is labeled “computed with an open-source implementation, validated against reference results”, never “computed by SPSS”.

- Validation by golden set: datasets with reference outputs, compared within a declared tolerance. Sources: (a) certified reference datasets published by NIST for statistical software accuracy [UNVERIFIED]; (b) SPSS outputs generated once, offline, using a free trial or a one-month subscription during the module build, if the trial or license terms allow this use; (c) published textbook examples with printed SPSS output. Reference generation is an offline activity (D-008).

- Reference price information, unverified: a third-party listing dated October 2025 shows roughly USD 99 per user per month for the base subscription and USD 79 per add-on per month, and IBM states that its free trial includes all add-ons. Confirm with IBM before any purchase decision. [UNVERIFIED]

- Input: .sav files are read with labels and missing-value definitions preserved (section 5.1), using an open-source reader (for example pyreadstat [UNVERIFIED]).

- Output for SPSS users: the delivery bundle MAY include SPSS syntax (.sps) next to the analysis code, so a user or instructor who owns SPSS can re-perform the analysis (P9). The system cannot execute SPSS, so generated syntax is labeled untested unless it has been validated against the golden set. It is not a second source of numbers.

- PSPP, a free GPL-licensed program that reads much SPSS syntax [UNVERIFIED], MAY serve as a cross-check. It carries the same copyleft questions as Beancount (section 9.2) and needs the same legal review before any distribution.

- Wording that names SPSS in marketing or in output MUST be reviewed by counsel, because the name is a third-party trademark.

### 9B.6 Presentation for students

- Tables and results are rendered by code from artifacts (section 11), in a user-selected academic style (for example APA). [PROVISIONAL]

- Each method comes with a plain-language explanation of what it does, why it was chosen, which assumptions were checked and how to word the result, so the student can defend it.

- The report states which claim type each result earns (section 7). Associational results never use causal verbs.

## 10. Role of agents

Permitted, as bounded subroutines: mapping messy charts of accounts; data profiling of odd files; diagnosing failed invariants; standards and literature retrieval; T3 exploration; builder-side code patching under amendment control.

Forbidden: deciding whether verification runs; modifying tests, thresholds or verifiers; writing the final numbers; any step where the agent grades its own work.

All agent runs have step caps, are logged, and their outputs pass through a check the agent does not control. Builder and verifier SHOULD be different model instances, and preferably different model families, to decorrelate errors. Spend the strongest models on formalization, spec review and verification. Use cheaper models for drafting and formatting.

### 10.1 Learning loop (offline self-improvement) [PROVISIONAL]

The pipeline improves from its own runs, but never at runtime (P10, D-008). Improvement flows through three channels with different levels of autonomy. The design follows the publicly described pattern of self-improving agents (outcome, verifier, reflection, skills, memory, consolidation), with this pipeline’s invariants, tie-outs and reference tests serving as the verifiers.

- Channel 1: case workspace (runtime, user-owned). Within a case that spans several sessions or deliverables, the system keeps the contents of the case workspace (section 5.9): confirmed account mappings, spec versions, framework choices, sources, baseline artifacts and format preferences. The user does not repeat them, and later papers stay consistent with earlier ones. It is versioned, provenance-tagged and visible to the user. It is scoped to the case, not to the user’s profile, and does not carry across unrelated cases. One-off use remains the default path and depends on no stored state. [PROVISIONAL]

- Channel 2: proposal queue (offline, agent-assisted). A reflection agent reads failed or user-corrected runs and their traces, clusters the failures, and drafts proposals: new test cases, candidate T1 methods, playbook and prompt edits, mapping heuristics. It only proposes. Learning across users uses de-identified traces and requires user consent and a retention rule (section 15B).

- Channel 3: promotion gate (human plus evaluation). A proposal enters the library, playbooks or prompts only after it passes the regression set and held-out cases, has a named reviewer, and has been rolled out to a small share of traffic first. Items are versioned, and consolidation (remove duplicates, retire stale items) happens here. This is the same mechanism as T2 to T1 promotion (section 5.3).

- Deferred: reinforcement learning or fine-tuning on verifiable tasks. The invariants make it possible, but it needs data volume and carries reward-hacking and memory-poisoning risk. Revisit once the evaluation set (section 14) exists. [OPEN]

- Guardrail: evaluations and human approval gate every update. The learning loop MUST NOT modify tests, thresholds or verifiers (section 5.5, item 4).

### 10.2 Coverage of the AI-engineering stack [PROVISIONAL]

This design was checked against the six commonly described stages of AI engineering: prompt, context, harness, multi-agent, evals and self-improving agents. The middle column lists what this document already covers. The right column lists additions to specify before build.

| Stage | Already covered | To add |
| --- | --- | --- |
| Prompt | Problem Spec schema, typed outputs, reference tokens (sections 5.2, 5.7) | Prompts versioned and evaluated like code |
| Context | Frozen spec as the saved plan; typed artifacts instead of chat memory (sections 5.2, 6) | A context budget and compaction rule. Compaction MUST carry artifact references, never numbers |
| Harness | Deterministic orchestrator, sandbox, step caps, fail-closed behavior, user checkpoints (sections 4, 5.4, 10) | Checkpoint and resume for long runs; tool allow-lists per stage |
| Multi-agent | Builder and verifier split; bounded subagents (sections 5.5, 10) | The verifier receives the spec and artifacts, not the builder’s reasoning, to decorrelate errors |
| Evals | Core set, trap set, red team, held-out discipline (section 14) | Stored traces; graders calibrated against human labels; canary rollout; a scorecard covering cost and latency as well as correctness |
| Self-improving | T2 to T1 promotion, D-008 (sections 5.3, 10) | The learning loop in section 10.1 |



## 11. Numeric hallucination guardrails

Leak types: (a) number typed from the model’s head; (b) real number copied wrongly; (c) number misread from a document or image; (d) rate or threshold from memory; (e) mental arithmetic; (f) chat follow-ups answered from conversation memory; (g) vague quantifiers that hide numbers.

- Digits are unspeakable. Model output uses reference tokens. Raw numeric literals, apart from a whitelist (years, section numbers), are rejected and regenerated. A post-hoc scan of the rendered text runs as a second layer.

- No mental arithmetic. Even simple derived figures come from a calculator tool whose calls are logged as artifacts.

- Distrust ingestion. For documents: extract twice with independent methods and reconcile. Require tie-outs (line items to subtotals, trial balance balances). Store each value’s source location and reject values absent from the source text layer. Show the user the extracted table beside the source and require confirmation.

- Typed quantities (section 6).

- No numeric facts from memory. External figures come from retrieval with source, date and span, stored as sourced. If retrieval fails, the field is unresolved and the system asks the user.

- Chat follow-ups require a query tool. No tool call, no digits. Earlier numbers in the conversation are context, not a source.

- Vague quantifiers (“nearly doubled”) are allowed only when bound to a computed ratio with a spec-defined threshold.

- Charts and tables are code-generated from artifacts.

- The orchestrator reports run status. The model never asserts that a check ran. It receives run records.

- Resist user pressure. If a user asserts a different figure, the system does not defer. It re-runs from source and shows the derivation. A number changes only when the trace finds a bad input.

- Click-through lineage on every displayed number.

- Fail closed. Deliver verified parts, remove or mark unverified claims, and say so.

- Metamorphic and adversarial tests. Perturb inputs and assert all dependent outputs change correctly. Inject odd tool values and check the prose uses them exactly. Probe sycophancy with asserted wrong figures.

- Feedback loop. A “this number is wrong” control turns each report into a regression case.

## 12. Conversation behavior

- Push back when the user’s premise is wrong. Do not flatter, and do not apologize and change a number under pressure.

- State confidence honestly. Distinguish verified, assumed and unknown.

- When a question cannot be answered computationally, say so and deliver T4 (framework and data needed).

- Surface ambiguities with the default taken and the impact of the alternative.

- Explain, do not only compute. Because users are mostly students, each method, assumption and result comes with a plain-language explanation the student can defend. [PROVISIONAL]

## 13. User-facing labels

Every output shows its tier label (T1 to T4), the claim level of each headline claim, and a limitations page. Judgment calls and interpretation items are listed explicitly. Plain-language explanations are provided for non-accountants, with conservative defaults on treatment questions.

## 14. Evaluation plan

- Core set. Collect 30 to 50 real, messy business problems already solved by experts. Run the pipeline and classify every failure as input, formulation, code or prose. This tells us which layer to harden.

- Trap set. Seeded cases: dataset with known confounder; series with planted structural break; critical missing input; pure values question; trial balance with flipped sign; misclassified contra account; missing accrual; unbalanced input; mid-year policy change.

- Metrics. Not only answer accuracy: correct downgrade, labeling and flagging rates; over-hedging rate (downgrading claims the evidence supported); numeric-claim match rate; invariant catch rate; mapping accuracy on real messy charts of accounts (tested separately, expected weakest stage).

- Expert red team. Pay one or two accountants to attack the system with their own cases before launch. Convert every real error into a regression test.

- Held-out discipline. Improvements are made offline against the evaluation set and confirmed on held-out cases.

- Statistics validation. Golden-set tests for each T1 procedure (section 9B.5). Statistics trap cases: violated assumptions (for example unequal variances), many tests without correction, user-missing codes read as real values, a result that differs from an SPSS output because of a software default, and a small sample presented with strong wording.

- Returning-case validation. Re-running a saved case later reproduces the same numbers (metamorphic test). A changed input marks all dependent artifacts stale. The same metric for the same entity and period matches across two deliverables. A restated source triggers disclosure of the difference. Reuse without mapping re-confirmation is rejected.

## 15. Known residual risks

- Wrong-but-valid reference: the draft cites a real artifact that is the wrong one (Q2 instead of Q3). Mitigated by reference metadata matching and reviewer pass, not eliminated.

- Verified but wrong: bad input or misclassification produces a perfectly derived wrong number.

- Shared blind spots between builder and reviewer models, even across families.

- Identification strategies are judgment calls. Passing diagnostics does not prove validity.

- Label neglect: users may quote the strong sentence and ignore the caveats. Headline structure reduces this but cannot control it.

- Standards drift: accounting standards and tax rules change after any model’s training. Retrieval is mandatory.

## 15B. Additional areas to specify [OPEN]

Added in v0.2 from design review. Each item needs an owner and a decision before launch.

- Security and hostile content. Uploaded files may contain sensitive data and hidden instructions (prompt injection). Requirements: tenant isolation, encryption, retention and deletion rules, and treating all document content as data, never as instructions. Applicable privacy law (for example the Philippine Data Privacy Act) needs counsel review. [UNVERIFIED]

- Model version drift. The code environment is pinned (section 5.4) but the model is not. Model versions MUST be pinned, and the regression set MUST pass before switching versions. [PROVISIONAL]

- Academic integrity and AI-use policy. Students’ institutions may restrict AI assistance or require disclosure of it. The system SHOULD provide a disclosure-ready summary of what the tool did (methods, run log, assumptions) with every delivery. Survey data may contain personal information about third parties, and the student remains responsible for ethics approval and consent. [OPEN]

- Similarity across students. If a class analyzes the same case, outputs built from the same sources and methods can look near-identical, and instructors may flag the similarity. Decide how drafting and presentation can vary by user without altering any computed number or claim wording, and how the disclosure-ready summary helps. [OPEN]

- Shared source caching. Many students may analyze the same public company, so caching retrieved filings at the source level could cut cost and speed retrieval. It raises licensing and cache-integrity questions. If adopted, only source documents are cached, never user data or derived results, each with a hash and a retrieval date. [OPEN]

- Workspace retention and privacy. A persistent case workspace needs retention limits, deletion on request and encryption, under the privacy review above. [OPEN]

- Multi-period work and corrections. Comparatives, restated prior periods, reruns after the user fixes data, and report versioning with diffs. These are handled within the case workspace (section 5.9). New spec versions never silently reuse earlier results (section 5.2).

- Liability and terms. Terms of use, disclaimers and professional-claims language depend on open question 1.

- Data connectors. Direct import from accounting or survey tools lowers ingestion risk compared with PDFs and scans. Lower priority for one-off student use.

- Reviewer workflow. A formal expert sign-off role with an audit trail, beyond the “take this to your accountant” list (section 5.8). For students, an export suited to instructor review is a candidate. [OPEN]

- Budgets and observability. Per-run cost and time caps, timeouts and alerting, even though cost is not a constraint at this stage (section 1).

## 16. Open questions

- First users are students with mostly one-off problems (section 1). What is the cost of a wrong answer for them (graded coursework, theses, possible publication)? Do any outputs go to banks, tax authorities or auditors? [OPEN]

- Will users upload structured files only, or also PDFs, scans and photos? This determines the weight of ingestion controls. For students, structured files (CSV, Excel, SPSS .sav) are the likely core; instructor-supplied case packs in PDF would add weight to ingestion controls. Confirm. [OPEN]

- Ledger engine choice (section 9.2 spike). [OPEN]

- Which frameworks and jurisdictions are in scope for version 1? Initial proposal: management accounts, three statements, five or six schedule types, one framework. [PROVISIONAL]

- Meaning of “papers”: users are students, so papers are most likely coursework, theses or dissertations, which follow institutional conventions (citation style, AI-use disclosure). Confirm which output types are in version 1. [PROVISIONAL]

- Amendment budget N and tolerance values for second-route recomputation. [PROVISIONAL]

- Names and process for the expert reviewers who gate T2 to T1 promotion. [OPEN]

- Which statistical procedures are in version 1, and which software defaults are mirrored? [OPEN]

- Do IBM’s terms allow generating reference outputs from a trial or short subscription for use as test fixtures, and do they allow any hosted use? [OPEN]

- Which privacy law, retention rule and academic-integrity position apply (section 15B)? [OPEN]

- How often do users return with the same company, and are cases mostly real public companies (filings retrievable) or instructor-supplied case packs? This sets the weight of the case workspace (section 5.9), source caching and ingestion. Measure after launch. [OPEN]

## 17. Decision log

| ID | Date | Decision | Status | Rationale |
| --- | --- | --- | --- | --- |
| D-001 | 2026-10-19 | Model never produces numbers; numbers come only from execution | DECIDED | Prevents fluent silent arithmetic failure |
| D-002 | 2026-10-19 | Tier by verifiability (T1 to T4), escalate on failed verification or no method | DECIDED | Difficulty is a poor trigger; verifiability is checkable |
| D-003 | 2026-10-19 | Deterministic orchestrator; agents bounded and never self-grading | DECIDED | An agent that decides whether to verify will sometimes skip it |
| D-004 | 2026-10-19 | Frozen spec and tests; logged amendments; multiverse reporting | DECIDED | Guards against tuning to plausible results |
| D-005 | 2026-10-19 | Claim licensing with wording ceilings, plus decision-flip as caveat filter | DECIDED | Prevents both overclaiming and caveat noise |
| D-006 | 2026-10-19 | Accounting via typed ledger kernel, declarative layer, constrained code layer | DECIDED | Flexibility by composition, not enumeration |
| D-007 | 2026-10-19 | Beancount as candidate ledger engine behind an adapter, pending spike | PROVISIONAL | Saves parser and ecosystem, not the hard parts |
| D-008 | 2026-10-19 | No recursive self-improvement at runtime; improvement offline with human review | DECIDED | Self-edited checks invite Goodhart failures |
| D-009 | 2026-10-19 | Digits prevented via reference tokens, with post-hoc scan as second layer | DECIDED | Prevention is stronger than detection |
| D-010 | 2026-10-19 | Reporting framework is a required input | DECIDED | Defaults hide a major source of error |
| D-011 | 2026-10-19 | First users are students with mostly one-off problems; per-client memory not built in version 1 | DECIDED; memory part superseded by D-016 | Stated by product owner; changes memory and explanation priorities |
| D-012 | 2026-10-19 | No embedded SPSS or standing license; open-source implementations validated against reference results; .sav input; optional .sps export | PROVISIONAL | Math is standard; license and sandbox constraints; owner has no license |
| D-013 | 2026-10-19 | Separate statistics module (9B): pre-declared assumption checks with fallbacks, defaults register, effect sizes and intervals | PROVISIONAL | Accounting invariants do not protect inferential work |
| D-014 | 2026-10-19 | Learning loop in three channels (project memory, offline proposal queue, gated promotion); RL deferred | PROVISIONAL | Keeps D-008; reuses existing verifiers |
| D-015 | 2026-10-19 | Pin model versions; rerun regression set before switching | PROVISIONAL | Environment is pinned but model behavior otherwise drifts |
| D-016 | 2026-10-19 | Case workspace: entity-scoped memory for returning cases; one-off use stays the default path; supersedes the memory part of D-011 | PROVISIONAL | Case studies bring users back to the same company; later papers must stay consistent |



## 18. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-19 | Initial draft consolidating design discussion: verifiability tiers, amendment control, claim licensing, decision-flip, breakpoints, accounting kernel, agent policy, numeric guardrails, evaluation plan |
| 0.2 | 2026-10-19 | Added statistics module (9B) and SPSS compatibility policy; student user base and one-off usage; learning loop (10.1); AI-engineering stack coverage (10.2); additional areas (15B); statistics validation in the evaluation plan; updated open questions; decisions D-011 to D-015. Sections 9B and 15B are lettered to avoid renumbering existing cross-references. |
| 0.3 | 2026-10-19 | Added case workspace for returning cases (5.9, Appendix C); revised first-user description (section 1), learning loop channel 1 (10.1) and intake (5.1); expanded 15B (similarity across students, shared source caching, workspace retention); returning-case validation (section 14); revised open questions; D-016, with the memory part of D-011 marked superseded. |



## Appendix A. Problem Spec (schema sketch)

```yaml
problem_spec:
  id: string
  version: integer
  hash: sha256 of frozen content
  objective: string
  decision_context: {decider: string, stakes: string, deadline: date}
  claims:
    - {id: string, text: string, type: descriptive|associational|predictive|causal|prescriptive|mechanical|estimate|policy_choice|interpretation}
  inputs:
    - {id: string, source: string, provenance: user|sourced|assumption|computed, quantity: Quantity}
  assumptions:
    - {id: string, value: Quantity, provenance: tag, rationale: string, plausible_range: [min, max], citation: string|null}
  method: {tier: T1|T2|T3|T4, name: string, library_ref: string|null}
  checks: [list of pre-declared tests]
  sensitivity: [{assumption_id: string, range: [min, max]}]
  thresholds: {qualitative_term: numeric definition}
  ambiguity_register: [{question: string, default_chosen: string, impact: string}]
  data_manifest: [{item: string, status: absent|obtainable|proxyable}]
  user_values: [{id: string, value: Quantity}]
  framework: IFRS|US_GAAP|local|null   # required for accounting work
```

## Appendix B. Artifact record and Quantity (schema sketch)

```yaml
Quantity: {value: Decimal, unit: string, currency: string|null, period: string|null, scale: units|thousands|millions, precision: integer}

artifact:
  id: string
  spec_hash: sha256
  code_hash: sha256
  env_hash: sha256
  inputs_hash: sha256
  value: Quantity|table|chart_data
  labels: {metric: string, period: string, entity: string, scope: string}
  derivation: formula and input artifact ids
  produced_by: tool or agent id
  created_at: timestamp
  immutable: true
```

## Appendix C. Case workspace (schema sketch)

```yaml
case_workspace:
  id: string
  owner: user id
  entity: {name: string, type: public_company|private_company|instructor_case|other, identifiers: [string]}
  framework: IFRS|US_GAAP|local|null
  fiscal_calendar: {year_end: string}
  periods: [string]
  sources: [{id: string, kind: filing|case_pack|user_file, retrieved_at: date, hash: sha256}]
  account_mapping: {version: integer, confirmed_by_user: boolean, confirmed_at: timestamp}
  spec_versions: [sha256]
  baseline_artifacts: [artifact id]
  assumption_register: [assumption id]
  stale_flags: [{artifact_id: string, reason: string}]
  retention: {delete_after: date|null}
  created_at: timestamp
  updated_at: timestamp
```
