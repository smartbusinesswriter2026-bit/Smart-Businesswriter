# Research & Evidence Workflow (REW) — living manual

**Formerly "Build Charter Stage 7".** Version 0.3 (2026-10-21). Supersedes `docs/STAGE7_BLOCKER.md` and `docs/STAGE7_API_DATABASE_PLAN.md` (merged here; git history keeps both). Status: **LIVING, owner-directed; R11 RATIFIED (2026-10-21)** — this manual is the working authority for REW and B-035 is closed. Everything still tagged `[PROPOSAL]`, `[2ND]` or `[OPEN]` is **not** ratified (R1–R10 remain open); read §3 before trusting any section.

## 0. What this document is, and is not

**Is:** the working definition of the research capability — from a research question, through literature and gap analysis, study design, data, analysis, to a manuscript or report — written so that any model or person editing this repo knows what the workflow must do, what it may never do, what is decided, and what is still open.

**Is not:** a recovered copy of the Smart Researcher research-pipeline manuals. Those were never supplied. The Build Charter (also not in this repo) forbids *reconstructing the pipeline from memory and presenting it as the original*. This manual honours that by never pretending: every section carries a provenance tag, and the stage list and taxonomies are marked `[PROPOSAL]` until the owner ratifies them (see §14). The manual's own authority is ratified (R11), but that ratifies *the document as the working reference*, not its proposals.

The literature retrieval/verification layer already exists and is governed by §9; it was never blocked.

## 1. Naming and authority

- **REW** = the product capability. "Stage 7" was a *build-sequence* label in the Build Charter (Stage 5 = method library, Stage 6 = catalogue, Stage 8 = management accounts), not a product name. It is renamed here so the capability can be discussed without build-order numbering.
- Authority order when rules conflict: (1) the owner's directives recorded in `docs/DECISIONS.md`; (2) the v0.3 business-pipeline manual (`docs/sources/business_pipeline_v0_3.md`) where it speaks; (3) this manual, **which is the working authority for REW by owner ratification R11 (2026-10-21), closing B-035**; (4) build reports.
- This manual is **living**: it is versioned in §16, and every material change bumps the version. Ratifying a `[PROPOSAL]` edits the tag in place and is logged in §16 and in `docs/DECISIONS.md`. A ratified item is not silently re-opened; if reality diverges, the divergence is logged, not the tag.

## 2. Non-negotiables (binding on everything below)

1. **No citation from memory, no invented sources.** A reference is either resolved-and-verified by a retrieval source or labelled unverified user-supplied. Never a silent memory citation.
2. **Synthetic data is never presented as observed.** The `synthetic` provenance tag and the `SYNTHETIC_NOTE` in the orchestrator are mandatory, not cosmetic.
3. **No computed number is retyped into narrative.** Manuscript numbers reference artifact ids; the pipeline's P1 rule applies unchanged.
4. **Claim wording never exceeds the method's claim ceiling** (`src/bp/claims.py`): descriptive / associational / predictive / causal / prescriptive.
5. **Every delivered result is re-performable** from a bundle (hashes, pinned environment, sandbox parity).
6. **Pre-declaration, not post-hoc.** Hypotheses, diagnostics and thresholds are frozen in the study spec before analysis; anything added later is a logged amendment and cannot weaken the verifier.
7. **The workflow ends in a reviewable draft**, never in an autonomous submission, filing or publication.

## 3. Provenance tags used in this manual

| Tag | Meaning | Binding? |
|---|---|---|
| `[OWNER]` | The owner said or directed it in session; recorded in `docs/DECISIONS.md` | Yes |
| `[REPO]` | Established by code, tests or docs in this repository (path cited) | Yes — it describes what exists |
| `[2ND]` | Quoted second-hand from the UI Review v0.1 / Build Charter as reported elsewhere in this repo; originals not available | Weak — names only, rules not binding |
| `[PROPOSAL]` | Written here for the owner to ratify (R-ids, §14) | No, until ratified |
| `[OPEN]` | Unresolved; needs an owner decision (Q-ids, §15) | No |

A section with no tag inherits the tag of its heading. **Nothing in this manual may be upgraded from `[PROPOSAL]` or `[2ND]` to binding except by an explicit owner ratification.**

## 4. Scope and output types

- **Capability** `[PROPOSAL]`: take a research problem, establish whether it is researchable and at what cost, design the study, obtain and tag the data, analyse with verified methods, and assemble a manuscript consistent with the evidence base.
- **First users are students** `[REPO]` (manual §1, line 25): coursework, theses and dissertations. Output types to confirm `[OPEN]` Q8 (manual §16, line 558).
- **Two output families**: academic paper (needs citation conventions and AI-use disclosure) and business report (needs decision framing). They share stages R0–R6 and diverge at R7. `[PROPOSAL]`
- **Out of scope for v1** `[PROPOSAL]`: ethics-approval filing, consent management, plagiarism detection, journal submission, peer review, and any analysis of qualitative transcripts beyond owner-supplied organisation (see §7).

## 5. Pipeline stages — v0.1 proposal

All of §5 is `[PROPOSAL]`. Stages are R0–R8 (R = research, to avoid colliding with the build stages S0–S8). Every stage has a frozen output; a stage that cannot meet its block conditions stops the run (fail-closed).

| Stage | Purpose | Inputs | Outputs | Checkpoint / blocks |
|---|---|---|---|---|
| **R0 Intake** | Frame the question | Research question, course/venue constraints, output type, citation style, institution AI-use policy | Frozen **research spec**: question, scope, output type, style, constraints, declared permissions (synthetic/ethics) | Owner confirms spec (same pause/resume contract as business specs) |
| **R1 Literature search** | Build the evidence base | Research spec; query plan | Retrieval log (source, query, date, hash), deduped reference list, screening log (include/exclude + reason) | Every reference labelled `verified` / `unverified_user_supplied` (§9). **Checkpoint C1: owner accepts the evidence base** |
| **R2 Gap & feasibility** | Decide if and how the gap is researchable | Evidence base; data requirements | Gap statement (what is known, what is missing), feasibility tier (§6), data manifest (available / obtainable / proxyable / impossible), risk register | Tier cannot be upgraded later without a new spec version |
| **R3 Study design** | Freeze the method before data | Gap statement, tier, data manifest | Frozen **study spec**: design type (§7), population/sample plan, instruments, pre-declared hypotheses, diagnostics and thresholds, power/precision statement, missing-data plan, analysis plan | **Checkpoint C2: owner freezes the design.** Any later change is a logged amendment |
| **R4 Data acquisition** | Get defensible data | Study spec | Typed dataset with provenance per value (user / sourced / assumption / synthetic), codebook, ingestion log, missing-data report | Refuses untagged values; synthetic requires explicit permission from R0 |
| **R5 Analysis** | Compute under verification | Dataset, frozen analysis plan | Method results with effect sizes and intervals, assumption checks, fallbacks taken, claim ceiling per result, frozen checks | Only methods in the verified library; every number has an independent second route; no number from a model |
| **R6 Interpretation** | Relate results to evidence | R1 base, R5 results, gap statement | Findings with wording licensed by claim ceiling, comparison with literature, limitations, what would change the conclusion, threats to validity | No causal language from associational designs; no conclusion outside the frozen hypotheses without being labelled exploratory |
| **R7 Manuscript** | Assemble the deliverable | R6, style rules, run log | Manuscript/report draft: methods generated from the run log, results by artifact reference, citations from §9, evidence appendix, AI-use disclosure summary | **Checkpoint C3: owner reviews draft.** Every number resolves to an artifact |
| **R8 Delivery** | Make it re-performable | R7 draft | Delivery bundle, hashes, re-performance check, disclosure export, open-questions/limitations register | Re-run must reproduce; otherwise delivery blocks |

Design rules that follow from the stages `[PROPOSAL]`:
- **Three mandatory checkpoints** (C1 evidence base, C2 frozen design, C3 draft) — fewer would let an unreviewed evidence base or design leak into a paper.
- **Freeze before compute**: R3 precedes R4/R5 always. No "look at the data, then choose the test".
- **Divergence at R7**: academic papers add citation formatting and disclosure; business reports add a decision section and stop before academic conventions.

## 6. Research-gap feasibility tiers — v0.1

Names `[2ND]` (UI Review v0.1, via the old blocker doc): **literature-only**, **existing public data**, **computational end to end**, **new empirical work**. Rules `[PROPOSAL]`.

| Tier | Work required | What the manuscript may claim | Cost/risk |
|---|---|---|---|
| **T-A Literature-only** | Structured synthesis of verified sources; no new data | Descriptive/associational claims about what the literature says; gap statement | Low; the main risk is citation quality |
| **T-B Existing public data** | Retrieve and clean published/secondary data (filings, statistical series, open datasets) | Associational/predictive claims defensible for that data; never causal without a design | Medium; provenance and licence risk |
| **T-C Computational end to end** | Simulate/modelling with declared assumptions (no new observations) | Model-conditional results, labelled as such; no empirical claims | Medium; assumption risk |
| **T-D New empirical work** | New collection — survey, experiment, interviews | Whatever the design licenses; ethics/consent becomes binding | High; out of v1 unless owner approves |

Rules `[PROPOSAL]`: the tier is assigned at R2, recorded in the study spec, and it *caps* the claim ceiling from §10. **Do not conflate the feasibility tier with the method tiers T1–T4** — the charter says they classify different things (tier T1–T4 is a method's verification/claim strength; T-A..T-D is the work's data/effort requirement). A T1 method used on T-D data is still T-D work.

## 7. Study-type taxonomy — v0.1 skeleton

`[PROPOSAL]`, except where marked. Types: quantitative (survey/cross-sectional, experiment, quasi-experiment, secondary data, simulation) and qualitative/exploratory (interviews, focus groups, case study, document/content analysis), plus mixed methods.

- **Quantitative** types map onto the existing verified statistics library `[REPO]`; the design must name its pre-declared diagnostics and fallbacks at R3.
- **Qualitative/exploratory** `[OPEN]` Q6: the original instruments and coding conventions are unknown. Until they arrive, qualitative material is **owner-supplied evidence organised structurally** (T4, like the SWOT/Five Forces templates `[REPO]`): the system may organise, quote verbatim and audit, but may not generate codes, themes, ratings or interpretations. A model may propose candidate codes only as proposals that the owner confirms, never as findings.
- **Mixed methods** must state which claims come from which strand; no cross-strand causal claim.

## 8. Data, artifacts and schemas

`[REPO]` for what exists, `[PROPOSAL]`/`[OPEN]` for what a research workflow still needs.

Existing artifact discipline that REW must reuse:
- **Typed values with provenance**: `src/bp/quantity.py` (`PROVENANCE = {user, sourced, assumption, computed, synthetic}`, Decimal only); templates and `case_decision` carry the same tags.
- **Structured method results**: a method returns `_appendix` (dict → delivery appendix) and `_checks` (frozen list of `(name, ok, detail)`), popped by the orchestrator and the sandbox child `[REPO]`.
- **Run log + provenance appendix + delivery bundle** with hashes; re-performance via `src/bp/reperform.py` `[REPO]`.
- **Statement exports** are deterministic plain text `[REPO]` (B-051); there is no PDF/XLSX writer.

Still needed for research `[OPEN]` Q4: analysis-table/CSV export schema, codebook schema, screening-log schema, dataset-versioning rules, and the ingestion path for structured data (CSV/XLSX/SPSS) — ingestion is a P0 gap in `docs/PRODUCT_GAP_MAP.md`. **A useful schema proposal must include, per variable: name, type, unit, allowed range, provenance allowed, missing-code policy.**

## 9. Literature retrieval, citation and verification

`[OWNER]` decision B-040 (retrieval boundary approved), implementation `[REPO]`, rules marked below as **PROVISIONAL** are `[OPEN]` for the manuals that no longer exist.

**Sources.** Crossref primary, OpenAlex fallback; both keyless. Optional `BP_CROSSREF_MAILTO` for a polite User-Agent. Source priority and failover policy, and whether to add arXiv/PubMed/Semantic Scholar/Europe PMC, are `[OPEN]` Q7.

**Verification rule (PROVISIONAL).** A reference is `verified` only when (a) a DOI resolves at the source **and** (b) the returned title equals the supplied title after case/punctuation/whitespace normalisation. Everything else — no DOI, unresolvable DOI, title mismatch, source error — is `unverified_user_supplied` (fail-closed, never retried silently, never upgraded by guesswork). Source errors are mapped, not swallowed.

**Labels in output.** `verified: DOI + source` · `unverified_user_supplied` · `declared by you (not verified)` for any rule or figure the user asserts. The manuscript and appendix must show which is which; a verified-looking citation is never manufactured.

**Citation formatting** `[OPEN]` Q9: not implemented, and deliberately so — the manual defines the institution's style. References stay structured records until a style is ratified.

**Retrieval audit** `[REPO]` (B-054; Q10 answered): every retrieval that reaches a source records the **SHA-256 of the exact response bytes received** and a **UTC retrieval timestamp**, both carried with the reference to the API and shown in the workbench. The hash is over raw bytes, not a re-serialised object, so it pins what the source actually served at that moment — it is not proof that the metadata is correct. A reference that never reached a source (no DOI, unresolvable DOI) records neither, fail-closed. **Still open:** the audit is returned with the response but not persisted in a durable retrieval log, so a submission still needs re-verification rather than a stored hash alone.

**Never** (binding, §2): cite from memory; invent a study or a DOI; silently "correct" a reference's metadata; treat a retrieved sketch as an established fact without opening it.

## 10. Claim and verification rules for research outputs

`[REPO]` unless marked.
- Every result carries its method tier and claim ceiling (`src/bp/claims.py`; `license_check`). The manuscript's wording is generated from the ceiling, not chosen by the writer.
- **Pre-declared analysis plan** at R3; deviations are logged amendments.
- **Cross-cutting honesty** `[REPO]` (B-057): every delivered computation **states** the 9B.3 limits — missing values excluded listwise with no established mechanism, the number of uncorrected hypotheses and its family-wise exposure, no power/MDE calculation, and independence assumed because weights/clusters/repeated measures are unsupported — and inputs naming an unsupported structure are refused at intake. The *upgrades* themselves (correction, power, mechanism modelling, weight estimation) are still missing `[OPEN]` Q5: the disclosure makes the gap visible, it does not close it.
- **Independent verification**: floats checked on a second route, golden fixtures, wrong-implementation blocking tests, sandbox parity `[REPO]`.
- **No model-authorised numbers**: a model may propose, never compute (`docs/MODEL_PROVIDER_REPORT.md`).

## 11. Synthetic and illustrative data

Binding from the charter (as reported) and `[REPO]` (tag vocabulary + `SYNTHETIC_NOTE` in `src/bp/orchestrator.py`):

- Synthetic values are labelled at the value, in the appendix and in the manuscript's methods.
- Synthetic results may never be presented as observations, and may not carry `causal` or empirical claims; they demonstrate method, not reality.
- A synthetic dataset in a paper requires: permission recorded at R0, a labelled data provenance table, and an explicit "illustrative only" statement in the abstract and methods.
- Mixing synthetic and observed values in one analysis is blocked unless every cell's provenance is visible in the appendix.

## 12. AI-use, ethics and privacy

- **Model boundary** `[REPO]`: proposals only — exact-excerpt facts, digit-free alternatives, critique — all code-validated and owner-confirmed (B-037); personal data may be sent only after explicit acknowledgement (B-038, `pii_acknowledged`); privacy notice in `src/bp/llm.py`.
- **AI-use disclosure-ready summary** `[REPO]` manual §15B (line 530) requires one with every delivery; **the export is not built** `[OPEN]` (also §E of the gap map).
- **Ethics and consent** remain the student's responsibility `[REPO]` (manual line 530); REW provides no ethics-approved workflow and must not imply otherwise.
- **Retention, deletion, shared source caching** `[OPEN]` (manual §15B lines 526, 534, 536) — not designed, not claimed.
- **Security** `[REPO]`: retrieved and uploaded content is data, never instructions (same rule as the model boundary).

## 13. What exists in code today

| Piece | Where | Status |
|---|---|---|
| Literature retrieval + DOI/title verification | `src/bp/literature.py`, `tests/test_literature.py`, `tests/test_literature_api.py`, API `/api/literature/*`, workbench References panel | Built, PROVISIONAL rules, live smoke-tested on one DOI (and again live for the audit); one test caught a real mismatch bug. Each resolved retrieval carries a response SHA-256 + UTC time (B-054); no durable log yet |
| Typed provenance, Decimal quantities | `src/bp/quantity.py` | Built |
| Claim ceilings and licensing | `src/bp/claims.py` | Built |
| Verified statistics (the R5 toolset) | `src/bp/methods.py` (descriptive, correlation, regression, two-group, ANOVA/KW, chi-square, linear trend) | Built, tier-gated |
| Structure-only evidence templates | `src/bp/templates.py` (SWOT, Five Forces), `case_decision` | Built, T4/T2 |
| Sandbox, re-performance bundles, run log | `src/bp/sandbox.py`, `reperform.py`, orchestrator | Built |
| Stage list, checkpoints, research spec, screening log, study spec | — | **Not built** (this manual proposes them) |
| Manuscript assembly, citation formatting | — | **Not built** |
| Ingestion from PDF/scan/Excel/SPSS | — | **Not built** (gap map P0) |
| AI-use disclosure export | — | **Not built** |
| Qualitative instruments | — | **Unknown / OPEN** Q6 |

No REW stage is wired into the pipeline. The method library, templates, sandbox, claims and provenance artefacts are reusable as-is; the stage contracts in §5 are not implemented.

## 14. Ratification register

Each item needs the owner's yes/no; ratifying edits the tag in this file and logs it in §16 and `docs/DECISIONS.md`. **Ratified: R11 (2026-10-21).** The rest remain proposals; a proposal is not binding merely because the manual is authoritative.

| Id | Item | Default until ratified |
|---|---|---|
| R1 | Stage list R0–R8, as written in §5 | PROPOSAL — do not build stages as if frozen |
| R2 | Three mandatory checkpoints (C1 evidence base, C2 design freeze, C3 draft review) | PROPOSAL |
| R3 | Feasibility tiers T-A..T-D names and rules (§6) | PROPOSAL (names are second-hand) |
| R4 | Study-type taxonomy, including the qualitative restriction (§7) | PROPOSAL |
| R5 | Divergence at R7 between academic paper and business report | PROPOSAL |
| R6 | Freeze-before-compute rule and amendment procedure (§5) | PROPOSAL |
| R7 | Qualitative materials are T4 owner-evidence only until instruments arrive | PROPOSAL |
| R8 | Claim-ceiling → wording enforcement applies to manuscripts, not just reports (§10) | PROPOSAL |
| R9 | Synthetic-data rules for papers (§11) | PROPOSAL — charter wording is binding; the paper-specific additions are not |
| R10 | Pre-declared honesty statements where 9B.3 upgrades are absent (§10) | PROPOSAL |
| R11 | This manual itself as the working authority for REW, superseding B-035 | **RATIFIED 2026-10-21 (owner: "yes to R11")** — this manual is the working reference; B-035 is closed. It ratifies the document's authority only, not R1–R10 |

## 15. Open questions (preserved from the old blocker, plus new)

Answers can arrive as owner statements, old chat exports, or later retrieval; each answer gets a decision id. Answered questions **stay** in the register with the answer in the Question cell and `—` in Blocks, so the trail is visible; they are never deleted.

| Id | Question | Blocks |
|---|---|---|
| Q1 | Exact original stage list from research problem to proposal and paper, with inputs, outputs and checkpoints? | R1 (ours is a proposal) |
| Q2 | Exact feasibility-tier names and assignment rules? | R3 |
| Q3 | How do tiers relate to the business manual's T1–T4 without conflation? | R3 (rule proposed, needs confirmation) |
| Q4 | Data-output schemas: what statistical/CSV outputs are expected, and what must the manuscript contain? | R5, §8 |
| Q5 | Cross-cutting statistics gaps (multiple comparison, power, missing-data mechanisms, weights) — which are in v1? | R5 |
| Q6 | Qualitative/exploratory study taxonomy and instruments? | R4, §7 |
| Q7 | Which sources, in what priority, with what failover? | R1 |
| Q8 | Do "papers" mean academic papers, business reports, or both in v1? | R0, R7 |
| Q9 | Citation style(s) to support, and the exact verification/match threshold? | R1, R7 |
| Q10 | Hash-audit requirement: response hash + retrieval date per reference — implement now or after the design? **ANSWERED 2026-10-21 (B-054):** each resolved retrieval carries the response SHA-256 and a UTC retrieval time; unresolved/no-DOI carry neither | — answered; follow-up: durable retrieval log |
| Q11 | Synthetic-data paper rules beyond the label (§11)? | R9 |
| Q12 | Institution AI-use / ethics / privacy requirements to show? | R7, §12 |
| Q13 | Which research-gap path to build first (T-A is the cheapest real end-to-end slice)? | sequencing |

## 16. Change log

- **0.3 (2026-10-21):** Q10 answered in code (B-054): every retrieval that reaches a source now records the SHA-256 of the exact response bytes and a UTC retrieval timestamp; the fields travel through the API to the workbench, and a reference that never reached a source records neither. Live-smoked against Crossref. §9, §13 and §15 updated; the remaining gap (no durable retrieval log) is stated rather than glossed.
- **0.2 (2026-10-21):** R11 **ratified by the owner** — this manual is the working authority for REW; B-035 closed (B-053 resolved). Header, §0, §1 and §14 updated to say exactly what that does and does not ratify (the document, not R1–R10). R1–R10 remain proposals.
- **0.1 (2026-10-21):** created as the living REW manual, merging and replacing `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md` (owner direction). Marked everything not already established as `[PROPOSAL]`/`[2ND]`/`[OPEN]`; preserved the ten original blocking questions (Q1–Q12 after merge); stated the one honest gap in the retrieval layer (no response hash yet). No code changed.
