# Home Chat Orchestration Manual — Living Guide

**Status:** Living manual. Read before any work on the Home chat, the conductor, paper composition, evidence, audit, charts, or paper-type coverage. Append decisions; do not rewrite history.

**Owner:** Open — needs B-number ratification before each phase ships.

**Related repo:** `business_pipeline_v0.12/business_pipeline`

**Related docs:**
- `docs/CONDUCTOR_MANUAL.md` — frozen core, computation rules, export gate.
- `docs/HANDOFF.md` — current build, tests, open work.
- `.opencode/plan/HOME_CHAT_ARCHITECTURE.md` — earlier home-chat architecture discussion.
- `docs/TIPS_FINANCIAL_STATEMENTS.md` — statement preparation and generic layer.
- `docs/DEBUG_MANUAL.md` — statements pipeline debug/improvement guide.

**Companion files (to be created in build mode):**
- `docs/HOME_CHAT_ORCHESTRATION_MANUAL.md` (copy of this manual into the repo).
- `src/bp/product/paper_families.py` (paper family and archetype registry).
- `src/bp/product/paper_contract.py` (paper contract + validation).
- `src/bp/product/audit.py` (audit + repair loop).
- `tests/test_home_chat_orchestration.py` (orchestration contract tests).

---

## 1. How to use this manual

1. Read §2 (hard rules) and §3 (vocabulary).
2. Read §4 (what home chat is and is not).
3. Read §5 (current baseline) so you do not rebuild what exists.
4. Read §6 (paper families) and §7 (stage contracts) before designing any change.
5. Read §8–§12 (contracts and ledgers) before writing code.
6. Read §13 (charts) before touching figures or Word export.
7. Read §14 (guardrails) before touching the planner or any model call.
8. Read §15 (phased build plan) and §16 (tests) before coding.
9. Append to §19 (decision log) and §20 (change log) when you settle something.

---

## 2. Hard rules (non-negotiable)

These rules cannot be broken by any model, any phase, or any test.

1. **The model never does math.** No computation, estimation, rounding, interpolation, averaging, or invention of a number. All business computation is delegated to the frozen core and recorded as an artifact.
2. **No invented evidence, sources, numbers, citations, frameworks, methods, or charts.** If it is not in the catalogue or retrieved, it does not exist.
3. **A dimension with no citable evidence gets a labelled background paragraph.** It is drawn from the weak/orientation sources the retriever saw, is not evidence, and is never cited; if no background exists, the paragraph says so. Missing data is `NULL`, never an estimate.
4. **Student inputs stay student inputs.** Declared costs, volumes, figures, thesis and judgments are supplied by the student. The system may propose, never silently adopt.
5. **No silent framework substitution.** A framework may be added or replaced only when declared to the student and recorded in the plan.
6. **Computations come from the frozen core.** Call the method; do not reimplement or re-round in the product layer.
7. **A paper never contains template instructions.** No `(your analysis)`, `Not supplied yet`, placeholder prose, or template names.
8. **Export is blocked when the paper is incomplete.** HTTP 409 with the missing list.
9. **The model does not research.** It edits prose only after the deterministic draft exists.
10. **Stdlib only at runtime.** No new runtime dependencies.
11. **Do not turn Home into a subject picker.** One open composer; the archetype is inferred and shown as a hint.
12. **The planner is read-only.** It may propose a plan; it may not retrieve, compute, write the paper, or mutate state.
13. **The auditor is read-only.** It may flag; it may not edit.
14. **The thesis and decision belong to the student.** The system may propose; the student approves.
15. **No subject name, home exchange, or home country in the paper.** Global product; neutral places and USD (B-177).
16. **No generative image for data.** Charts are deterministic specs from stored artifacts only.

---

## 3. Vocabulary

- **Composer** — the open text box on Home where the student types, pastes or uploads a brief.
- **Paper contract** — the frozen agreement about what the paper is, who it serves, what it must contain, and what it must not contain.
- **Archetype** — a named paper shape with required and optional blocks, section order, evidence policy, computation policy, chart policy, length bands, citation styles, rubric families, and a completeness contract.
- **Paper family** — a group of archetypes sharing a genre (analytical report, case analysis, plan/proposal, literature synthesis, essay, memo, reflective, legal, empirical, communication).
- **Block** — one unit of the paper plan: framework, computation, evidence, chart, prose, or audit.
- **Block graph** — the ordered, dependency-aware set of blocks in a plan.
- **Evidence ledger** — the registry of retrieved sources, claims, numbers, citations, charts and gaps.
- **Claim-to-source map** — the link from every claim in the draft to its evidence, computation or student input.
- **Audit** — the read-only verification stage that checks the paper against the contract, the plan, the ledger and the rubric.
- **Repair** — the targeted fix stage that acts on audit findings.
- **Production check** — the dry run that proves the plan can be executed before research starts.
- **Completeness contract** — the genre-specific definition of what “complete” means for an archetype.

---

## 4. What home chat is and is not

Home chat is the **single open entry point**. A student describes a decision or assignment; the chat decides which frameworks, computations, evidence, charts and prose the paper needs, borrows them from the relevant subjects, and composes one coherent paper.

Home chat is **not**:
- a subject picker;
- a form with a chat skin;
- a calculator with a chat skin;
- a free-roaming agent that writes the paper;
- a tool that does math.

The chat is the macro conductor. It owns the decision, the thesis, the framework stack, any computation, the paper plan and the export gate. Subject modules provide frameworks and computations; the writer and renderer only format.

---

## 5. Current baseline (do not rebuild)

These exist in the current tree. Do not re-implement them:

| Piece | Where | What it does |
|---|---|---|
| Open composer on Home | `web/index.html` `RENDERERS.home()` | Single `#objective` textarea, Attach files, Run button. Sends `subject: "any"`. |
| Subject detection | `src/bp/product/guard.py` `detect_subject()` | Scores brief words against subject hint vocabulary. |
| Open-mode fit | `src/bp/product/guard.py` `subject_fit()`, `computation_boundary()` | Both return `(True, None)` when subject is `"any"`. |
| Capability resolution | `src/bp/product/capabilities.py` `resolve()` | Matches brief intent cues against the catalogue. |
| Computation boundary | `src/bp/product/guard.py` `computation_boundary()` | Refuses computation briefs on framework shelves unless subject is accounting/finance. |
| Plan card | `web/index.html` `capabilityPanel()` | Shows selected computations, inputs, figure quotes, dependencies, drop buttons. |
| Figure normalisation | `src/bp/product/verify.py` `normalise_number()` | Parses written figures; refuses bad filings. |
| Reading verifier | `src/bp/product/verify.py` `verify_reading()` | Refuses unknown methods, non-substring quotes, figures without quotes, overclaims, missing rationale. |
| Recompute guard | `chat._recompute_guard` | Re-runs every computation from stored inputs at draft time. |
| Export gate | `src/bp/product/paper.check` | Rejects level jumps, missing conclusion/references, template text. |
| Attach files | `web/index.html` `bindAttachments()` | File attachment on the Home composer. |
| Plan council | `src/bp/product/council.py` | Opt-in LLM advocates, verifier and examiner. |
| Charts | `src/bp/product/charts.py` | Deterministic SVG from stored artifacts. |
| Profiles | `src/bp/product/framework_profiles.py` | Many frameworks as data. |
| Framework keys | `src/bp/product/chat.py` `FRAMEWORKS` | Nine conductor frameworks. |
| Profiles | `src/bp/product/chat.py` `PROFILE_*` | Business plan, feasibility, marketing plan, project proposal. |
| Computation blocks | `src/bp/product/chat.py` `COMPUTATION_BLOCKS` | Plan-level blocks for profiles. |
| Computation cap | `src/bp/product/capabilities.py` `MAX_COMPUTATIONS = 3` | At most three computations per paper. |
| Length | `src/bp/product/length.py`, `chat.py` | A body-word target (600–50,000), ±10% reported. The old short/mid/long names are legacy only; length is not an export gate. |
| Rubric support | `src/bp/product/rubric.py` | Rubric parsing and coverage. |
| Case store | `src/bp/product/cases.py`, `chat_store.py` | Durable case bundles. |
| DOCX export | `src/bp/product/docx.py` | Academic document with table figures. |

**Not built:** paper contract, block graph, evidence ledger, claim-to-source map, audit/repair loop, chart wiring into the paper, paper-family registry, production check, literature synthesis lane, empirical research lane.

---

## 6. Paper families and archetypes

Do not build 100 bespoke pipelines. Build a small set of paper families, each containing archetypes. A paper type is a preset inside a family.

### 6.1 Families

| Family | Genre | Evidence | Computations | Charts | Examples |
|---|---|---|---|---|---|
| Analytical report | Analyse a company, industry, market or statement set | External + company data | Ratios, DuPont, DCF, WACC, variance, sensitivity | Bar, line, table, waterfall | Financial statement analysis, ratio report, company analysis, industry analysis, earnings quality, ESG analysis |
| Case analysis | Analyse a case and recommend action | Case facts + external | Break-even, NPV, ratios, scenario | Table | Harvard case, failure, success, ethics, comparative case |
| Plan/proposal | Plan or propose a business, project or study | Market evidence + student inputs | Market sizing, break-even, proforma, sensitivity, cost | Bar, line, table | Business plan, marketing plan, feasibility, project proposal, research proposal |
| Financial/valuation | Value or appraise a company or project | Market data + company data | DCF, comps, WACC, IRR, sensitivity, risk | Waterfall, bar, table | Valuation, equity research, capital budgeting, M&A, LBO, credit, portfolio |
| Literature/synthesis | Synthesise research | Scholarly sources | None | Table | Literature review, annotated bibliography, critical review |
| Argumentative essay | Argue a position | Scholarly/practitioner | Optional | None | Position paper, essay, white paper |
| Memo/brief | Recommend to a stakeholder | Evidence + stakeholder | Optional cost-benefit | Table | Policy memo, business memo, executive summary |
| Reflective | Connect concepts to experience | Student experience | None | None | Reflection, internship, simulation |
| Legal/regulatory | Apply law or standards | Legal/standards sources | Tax, damages | Table | Case brief, contract, compliance, tax memo |
| Empirical/research | Test or investigate a question | Data + literature | Statistics/econometrics | Charts, tables | Thesis, research paper, empirical accounting |
| Communication | Communicate professionally | Minimal | None | None | Letter, email, press release, pitch, resume |

### 6.2 Readiness

| Family | Readiness | Main gap |
|---|---|---|
| Analytical report | Mostly ready | Needs archetype registry and chart wiring |
| Case analysis | Mostly ready | Needs case-framing block and rubric |
| Plan/proposal | Profiles exist | Needs archetype registry and multi-block plan |
| Financial/valuation | Computations exist | Needs archetype and chart wiring |
| Literature/synthesis | Not built | New lane: search plan, source appraisal, synthesis |
| Argumentative essay | Prose exists | Needs genre archetype and evidence ledger |
| Memo/brief | Prose exists | Needs short-form archetype |
| Reflective | Not built | Simple template lane |
| Legal/regulatory | Not built | Separate lane |
| Empirical/research | Partial | Needs research-design and results lane |
| Communication | Not built | Separate lane, not the paper pipeline |

### 6.3 “Complete” is genre-specific

A complete paper is not the same for every family. Each archetype defines its own completeness contract:

- Analytical report: thesis, context, analysis, evidence, synthesis, recommendation, limitations, references; at least one benchmark or baseline; at least one sensitivity or decomposition if a computation is present.
- Case analysis: problem, evidence, framework, alternatives, recommendation, implementation, risks.
- Literature review: question, search method, themes, gaps, debates, conclusion; no computation.
- Plan/proposal: market, operations, management, financials, risk, implementation, metrics.
- Memo/brief: issue, options, criteria, recommendation, next steps.

The audit checks the completeness contract, not a generic checklist.

---

## 7. Stage contracts

Each stage has a typed contract. A stage may not proceed unless its contract is satisfied.

### Stage 0 — Intake

- Inputs: brief, attachments, rubric, format constraints.
- Output: intake record with brief hash, attachment metadata, rubric metadata, format metadata.
- Rule: no judgment yet; only collection and hashing.

### Stage 1 — Paper contract

- Inputs: intake record + inferred archetype.
- Output: paper contract (frozen after approval).
- Rule: the student approves the thesis, scope, archetype, length, citation style and rubric. The contract is immutable after confirmation; changes are logged.

### Stage 2 — Plan

- Inputs: paper contract.
- Output: plan IR with blocks, dependencies, evidence needs, student inputs, chart specs, section order.
- Rule: the planner is read-only and may only reference registry IDs.

### Stage 3 — Production check

- Inputs: plan IR.
- Output: pass/fail with reasons.
- Checks: every block exists; every computation input is satisfiable; every evidence need has a retrieval plan; every chart has an artifact source; section order is valid; length is feasible; no forbidden combination; rubric coverage is feasible.
- Rule: if this fails, the plan is not confirmed.

### Stage 4 — Evidence

- Inputs: plan IR + paper contract.
- Output: evidence ledger.
- Rule: retrieval is deterministic; every retrieved source is recorded with provenance; every gap is named.

### Stage 5 — Compute

- Inputs: plan IR + evidence ledger + student inputs.
- Output: computations ledger with frozen results and artifacts.
- Rule: computations run in dependency order; every result is re-runnable; every artifact is recorded.

### Stage 6 — Draft

- Inputs: plan IR + evidence ledger + computations ledger.
- Output: draft sections + claim-to-source map + chart specs.
- Rule: prose is assembled deterministically; the LLM may polish transitions only after the draft exists.

### Stage 7 — Audit

- Inputs: paper contract + plan IR + evidence ledger + computations ledger + draft.
- Output: audit report with findings and severity.
- Rule: the auditor is read-only; it may flag, never edit.

### Stage 8 — Repair

- Inputs: audit report + draft.
- Output: repaired draft + re-audit.
- Rule: repairs are targeted; if unresolved findings remain, export is blocked.

### Stage 9 — Export

- Inputs: repaired draft + all ledgers.
- Output: DOCX/PDF + appendix.
- Rule: export gate must pass; no unresolved finding, no missing section, no unresolved claim, number or chart.

---

## 8. Paper contract schema

```json
{
  "format": "bp-paper-contract/1",
  "brief_hash": "sha256:...",
  "archetype": "analytical_report",
  "family": "analytical_report",
  "thesis": { "text": "...", "source": "student_approved" },
  "decision": "...",
  "audience": "...",
  "scope": {
    "object": "...",
    "period": "...",
    "geography": "...",
    "currency": "USD",
    "unit_of_analysis": "..."
  },
  "length": "mid",
  "style": "apa",
  "required_sections": ["Introduction", "Analysis", "Synthesis", "Recommendation", "Limitations", "References"],
  "evidence_policy": "external_plus_company_data",
  "computation_policy": "optional",
  "chart_policy": "optional",
  "rubric": { "source": "course_or_product", "coverage": [] },
  "deliverables": ["docx", "pdf"],
  "constraints": {
    "no_invented_evidence": true,
    "no_invented_numbers": true,
    "no_silent_substitution": true,
    "global_product": true,
    "no_template_text": true
  },
  "approved": true,
  "approved_at": "..."
}
```

---

## 9. Block registry contract

Every block must declare:

```json
{
  "key": "ratio_analysis",
  "kind": "computation",
  "label": "Ratio analysis",
  "subject": "accounting",
  "question_answered": "How liquid, profitable, leveraged and efficient is the firm?",
  "role": "financial_analysis",
  "inputs": ["revenue", "net_income", "total_assets", "current_assets", "current_liabilities"],
  "needs_any": ["statement figures"],
  "evidence_required": false,
  "student_inputs_required": true,
  "produces": { "artifacts": ["liquidity_ratios", "profitability_ratios", "leverage_ratios", "efficiency_ratios"] },
  "chart_kinds": ["bar", "table"],
  "does_not": "It does not assess strategy, market position or future performance.",
  "applies_to": ["pestel", "swot", "five_forces", "value_chain", "ansoff", "breakeven"],
  "integration": "Framework and Declared Figures",
  "limitation": "Ratios describe; they do not explain or predict."
}
```

Rules:
- The planner may only reference block keys that exist in the registry.
- A block that does not exist is refused, never substituted.
- A block must state what it does not settle.
- A block must state its chart kinds; a chart may only use a kind the block allows.

---

## 10. Plan IR schema

```json
{
  "format": "bp-plan/1",
  "archetype": "market_entry",
  "thesis": { "text": "...", "source": "student_approved" },
  "decision": "...",
  "blocks": [
    {
      "id": "b1",
      "kind": "framework",
      "ref": "pestel",
      "role": "external_context",
      "contribution": "names the external conditions the decision depends on",
      "requires": { "evidence": ["political", "economic", "legal", "technological", "environmental", "social"] },
      "produces": { "sections": ["PESTEL"] },
      "chart_specs": []
    },
    {
      "id": "b2",
      "kind": "computation",
      "ref": "breakeven",
      "role": "financial_feasibility",
      "requires": { "student_inputs": ["price", "variable_cost", "fixed_cost"] },
      "produces": { "artifacts": ["breakeven_units", "margin_of_safety"] },
      "chart_specs": [{ "kind": "bar", "source_artifacts": ["breakeven_units"] }]
    },
    {
      "id": "b3",
      "kind": "prose",
      "ref": "synthesis",
      "role": "synthesis",
      "contribution": "reconciles b1 and b2 against the decision",
      "requires": { "blocks": ["b1", "b2"] },
      "produces": { "sections": ["Synthesis"] }
    }
  ],
  "dependencies": [["b2", "b1"]],
  "evidence_needs": [],
  "student_inputs": [],
  "chart_specs": [],
  "section_order": ["Introduction", "PESTEL", "Financial Feasibility", "Synthesis", "Recommendation", "Limitations", "References"],
  "hash": "sha256:..."
}
```

Rules:
- Every block has a role and a contribution to the thesis.
- A block with no contribution is excluded with a reason, like `not_included` today.
- Dependencies must be acyclic.
- The synthesis block is mandatory for any paper with more than one analysis block.

---

## 11. Evidence ledger schema

```json
{
  "format": "bp-evidence/1",
  "sources": [
    { "id": "s1", "title": "...", "year": "...", "database": "...", "url": "...", "retrieved_at": "...", "query": "..." }
  ],
  "claims": [
    { "id": "c1", "text": "...", "type": "external", "block": "b1", "source_ids": ["s1"], "quote": "..." }
  ],
  "numbers": [
    { "id": "n1", "value": "12000", "unit": "USD", "computation": "breakeven", "artifact": "breakeven_units" }
  ],
  "citations": [
    { "source_id": "s1", "style": "apa", "rendered": "..." }
  ],
  "charts": [
    { "id": "ch1", "kind": "bar", "spec": { "format": "bp-chart/1" }, "artifact_ids": ["breakeven_units"], "hash": "sha256:..." }
  ],
  "gaps": [
    { "id": "g1", "block": "b1", "dimension": "environmental", "reason": "no evidence retrieved" }
  ]
}
```

Rules:
- Only retrieved sources may be cited.
- Every external claim must cite at least one source and quote it.
- Every number must trace to a computation artifact or a student-declared input.
- Every chart must trace to stored artifacts.
- A dimension with no citable evidence carries a labelled background paragraph; it is not evidence and it is not cited.

### 11.1 Retrieval order (2026-11-07)


The conductor retrieves in three layers, cheapest first:

```text
1. Corpus / Meilisearch      cited; searched alone; fastest
2. Web                       only on a corpus miss; vetted pages may be cited,
                             Wikipedia/explainers are orientation only
3. Journal APIs              only when neither the corpus nor the vetted web
                             supplied a citable source; slowest
```

- If the corpus answers a dimension, the web and the journal APIs are **not called**.
- Orientation pages never enter `evidence`, `sources`, references, citations or the
  claim-to-source map. They are stored in `orientation_sources` and shown as
  **Background reading (not cited)**.
- Every source any layer saw is written to the corpus learning log, with `used` = 1 only
  for the items the paper actually cites. The enrichment worker turns the rest into
  candidates, so a future run can answer from the corpus instead of the API.
- A dimension with no source is a named gap. No source is invented.
- The evidence view shows the query and the per-layer counts (`Corpus / web / journal
  APIs`) under **What was searched**, so "no results" and "irrelevant results" are
  distinguishable.
- The web layer is not an open web search. `sources.sites_for(topic)` selects a ranked
  vetted list from the paper's subject (or from the query when the subject is absent);
  see `docs/VETTED_SOURCES.md`.

### 11.2 Attached files (2026-11-07)

The Home composer carries four attach buttons, and each is a different contract:

| Button | What it is | How the pipeline treats it |
|---|---|---|
| **Instruction files** | the assignment, brief or rules the paper must follow | extracted text is appended to the brief in the order attached; the paper follows it |
| **Sources** | source documents the student wants prioritised | stored with `role: sources`; text is extracted so it can be read; the plan lists them |
| **Data** | figures for a computation | `.xlsx`, `.xlsm`, `.csv`, `.tsv` or `.txt` only; ingested into a typed table, never treated as prose |
| **Rubric** | the marking guide | parsed into criteria; the paper carries a coverage table and the download is blocked while a weighted criterion is unaddressed |

Each intake record carries its role, and the chat state records the ids in
`attached_files` and the counts in `proposal.attachments`.  A source is not
silently promoted to evidence: a data file is a table, a source file is a
student-supplied document, and only the retrieval layers produce citable
evidence.  The UI says which is which rather than blurring the four.


---

## 12. Claim-to-source map

The draft is generated with a claim-to-source map. Every paragraph or claim in the draft references IDs from the evidence ledger.

The export gate blocks export if:
- a claim has no source;
- a number has no computation or student input;
- a citation key does not resolve;
- a chart spec does not resolve to artifacts;
- a gap is written as if it were a finding;
- a template instruction appears.

---

## 13. Charts

Charts are first-class blocks, not decorations.

Rules:
- A chart spec must reference stored artifacts only. `charts.py` already enforces this.
- A chart may only use a kind that the source block allows.
- A chart title, label, axis label or note may not contain digits; numbers come only from artifacts.
- A chart must be reproducible from the bundle and the spec.
- The same bundle + spec must produce byte-identical SVG.
- If no candidate chart passes verification, fall back to the deterministic render.

### DOCX limitation

`docx.py` currently renders table-based figures, not SVG or PNG images. Therefore:

- Phase 1: charts appear in the web preview and as data tables in Word.
- Phase 2: add a chart-to-DOCX path. This needs an owner decision on native Word chart XML, SVG embedding, or rasterisation. Rasterisation may violate the stdlib-only runtime rule.

Do not promise charts in the downloaded paper until this path is chosen.

---

## 14. Guardrails for models

These guardrails exist so models do not drift.

1. **The model never does math.** No number is computed, estimated, rounded or invented by the model.
2. **The planner is read-only.** It proposes a plan; it does not retrieve, compute, write or mutate state.
3. **The auditor is read-only.** It flags; it does not edit.
4. **Only registry IDs.** The planner may only reference block keys, archetype keys, framework keys, computation keys, chart kinds and section names that exist in the registry.
5. **No execution during planning.** The ideation/planning stage does not run tools, code, benchmarks or exploratory computation.
6. **No silent substitution.** Unknown keys are refused with the real options.
7. **No invented inputs.** If a required input is missing, ask or name a gap.
8. **No assumption of missing evidence.** The model must not fill a gap with a plausible-sounding claim.
9. **No subject name in the paper.** The detected subject is a routing hint only.
10. **No home exchange or home country.** Global product; neutral places and USD.
11. **No template text in the paper.** No placeholders, instructions or template names.
12. **No changing the contract.** The paper contract is frozen after approval. Changes are logged, not silent.
13. **No scope creep.** The paper must answer the assignment, not a different or larger question.
14. **No rubric gaming.** The audit checks for dropped required sections, changed citation style, changed word count, and evaluation-protocol tampering.
15. **No generative image for data.** Charts are deterministic specs from artifacts only.
16. **Human approval at every gate.** Thesis, plan, evidence, prose and final paper require student approval.

---

## 15. Phased build plan

### Phase 0 — Contracts and inventory (no UI change)

- Create the paper-family registry.
- Create the block registry.
- Create the paper contract schema.
- Create the plan IR schema.
- Create the evidence ledger schema.
- Create the completeness contracts.
- Write tests for all schemas and validators.

Done when: a plan can be validated without running the pipeline.

### Phase 1 — Multi-block plan for one framework

- Extend the current single-framework state to a block list.
- Keep single-framework papers working unchanged.
- Add the production check.
- Add the evidence ledger.
- Add the claim-to-source map.
- Add the audit and repair loop.
- Wire chart blocks into the plan and web preview.

Done when: one framework + multiple computations + charts can be planned, validated, executed and audited.

### Phase 2 — Multi-framework papers

- Allow multiple framework blocks with roles and integration rules.
- Extend `FRAMEWORKS` to all `framework_profiles`.
- Add archetype-specific section order and synthesis.
- Add composition tests.

Done when: PESTEL + Five Forces + SWOT + computation can be composed into one paper.

### Phase 3 — LLM planner behind a flag

- Extend the council to propose a full plan IR.
- Verify every ID, dependency, evidence claim and input.
- Fall back to the deterministic resolver when the LLM is unavailable or fails verification.

Done when: the planner proposes plans that pass the production check.

### Phase 4 — UI and evidence experience

- Plan card as a block graph.
- Evidence ledger view with source, claim, number, citation and gap.
- Student input collection per block.
- Chart preview.
- Synthesis approval.

Done when: a student can plan, inspect, approve and export a multi-block paper.

### Phase 5 — Paper families

- Add analytical report, case analysis and plan/proposal archetypes.
- Add financial/valuation archetype.
- Add literature synthesis lane.
- Add empirical research lane.
- Add legal/regulatory and communication lanes later.

Done when: the registry covers the paper families in §6.1.

---

## 16. Test strategy

Add `tests/test_home_chat_orchestration.py` with at least these cases:

1. A plan with an unknown block key is refused.
2. A plan with a dependency cycle is refused.
3. A computation whose inputs are neither declared nor chained is refused.
4. A chart whose source artifact does not exist is refused.
5. A paper with two frameworks that answer the same question is refused.
6. A paper with a framework whose required inputs are absent is refused.
7. Every block in the plan appears in the paper.
8. Every paper section traces to a block.
9. Every chart traces to an artifact.
10. Every citation traces to the evidence ledger.
11. Every claim traces to a source, computation or student input.
12. A dimension with no citable evidence carries a labelled, uncited background paragraph; it is never filled with invented evidence.
13. The production check catches an unsatisfiable plan.
14. The audit blocks export on an unresolved finding.
15. The repair loop resolves a targeted finding.
16. Single-framework papers still pass all existing tests.
17. The planner’s output is verified before use.
18. The fallback resolver works when the LLM is unavailable.
19. No subject name, home exchange or home country appears in the paper.
20. No template instruction appears in the paper.

Also add a composition corpus: 40–100 briefs with expected archetype and block sets, and tests that invalid combinations are refused.

---

## 17. Open questions (need owner decision)

| Id | Question | Recommendation |
|---|---|---|
| O-1 | Is the thesis student-supplied and approved, or model-proposed? | Student-approved, model-proposed. |
| O-2 | Maximum blocks per length band? | Short 1 framework + 0–1 computation; mid 1–2 + 0–2; long 2–3 + 0–3. |
| O-3 | Which archetypes ship first? | Analytical report, case analysis, plan/proposal. |
| O-4 | Charts in Word: table-only acceptable, or must be images? | Table-only in phase 1; decide images in phase 2. |
| O-5 | Should the LLM planner be on by default or opt-in? | Opt-in behind a flag, like `BP_PLAN_COUNCIL`. |
| O-6 | How much cross-subject borrowing is allowed in one paper? | Allowed; subject labels appear only in the plan, never in the paper. |
| O-7 | Should thesis/dissertation/capstone be supported? | Defer; current length max is 5,000 words. |
| O-8 | Should business communication be part of this pipeline? | No; separate lane. |
| O-9 | Should peer review be part of this pipeline? | No; separate workflow. |
| O-10 | Should the product propose a rubric when the course gives none? | Yes, but student-approved. |

---

## 18. Decision log (append-only)

| B-number | Date | Decision | Rationale |
|---|---|---|---|
| (pending) | 2026-11-06 | Add paper contract before plan | Task spec is the strongest idea from the orchestration paper |
| (pending) | 2026-11-06 | Add claim-to-source ledger and audit/repair loop | Provenance is the trust layer |
| (pending) | 2026-11-06 | Model paper types as families and archetypes | Avoids combinatorial explosion |
| (pending) | 2026-11-06 | Planner is read-only | No execution during planning |
| (pending) | 2026-11-06 | Auditor is read-only | No edit during audit |
| (pending) | 2026-11-06 | Charts are deterministic specs from artifacts | No generative image for data |
| (pending) | 2026-11-06 | Baselines, ablations and post-hoc blocks for business papers | Strengthens claims |
| (pending) | 2026-11-06 | No math by the model | Frozen core computes; model never computes or invents numbers |
| (pending) | 2026-11-06 | Typed instruction reading with framework roles and slots | Removes silent framework defaults and preserves every quantity |
| (pending) | 2026-11-06 | Universal metric-to-entity category gate | Refuses cross-domain nonsense without example-specific rules |
| (pending) | 2026-11-06 | Plan proposal and guarded edit | The student sees and controls the interpretation without drifting |
| (pending) | 2026-11-06 | No-framework papers are valid | Not every paper has a framework; never force PESTEL/SWOT |
| (pending) | 2026-11-06 | PESTEL/SWOT only when named or selected | No hardcoded framework, no fallback |

---

## 19. Change log (append-only)

| Date | Change | Author |
|---|---|---|
| 2026-11-06 | Initial manual: paper contract, block graph, evidence ledger, audit/repair, charts, paper families, guardrails, phased build plan, tests | Model session |
| 2026-11-06 | Added typed instruction reading, universal category gate, no-framework papers, plan proposal, guarded edit, citation styles and the five-instruction stress test | Model session |

---

## 20. Placement and findability

This manual lives at `business_pipeline_v0.12/business_pipeline/docs/HOME_CHAT_ORCHESTRATION_MANUAL.md`.

1. It is linked from `AGENTS.md` under the home chat reading list, alongside `CONDUCTOR_MANUAL.md` and `HANDOFF.md`.
2. Add a short pointer in `docs/HOME.md` if the surface changes.
3. Keep the decision log and change log append-only.

---

## 21. Typed instruction reading, plan proposal and guarded edit

This layer was added after the first build. It handles valid instructions and refuses nonsense before the conductor plans anything.

### 21.1 Typed instruction reading

`src/bp/product/instruction_reading.py` returns:

- `FrameworkReading` with status `resolved`, `ambiguous`, `absent` or `conflict`.
- Every framework mention with a role: `primary`, `negated`, `contrast` or `incidental`.
- Alias normalisation (`5 forces`, `Porter's model`, `growth matrix`, `PESTLE`, etc.).
- `Slot` records for quantities: value, span, kind, period, compounding and status `pending`, `consumed` or `dismissed`.
- `CategoryError` for a metric bound to an entity that cannot carry it.
- `next_question()` for dependency-ordered clarification.

No framework is inferred by default. PESTEL and SWOT appear only when the instruction names them, the student selects them, or the proposal offers them as an option.

### 21.2 Universal category gate

The category gate is a table, not a list of examples:

- `METRIC_LEXICON` maps each metric to the entity types that may carry it.
- `ENTITY_LEXICON` maps named frameworks, theories, artefacts and role documents to their type.
- A metric asked of a framework, theory, artefact or role document is a `CATEGORY_ERROR`.

This catches cross-domain nonsense such as EBITDA margin of a SWOT analysis, beta of the 4Ps, discount rate of Maslow, payback period of a BCG matrix, CPI of a fishbone diagram, and safety stock of a job description. The gate must remain universal; do not add one-off phrase checks.

### 21.3 No-framework papers

`none` is a valid framework:

- The framework question always includes `No framework`.
- `none` uses a generic evidence dimension.
- The draft carries no framework sections.
- PESTEL/SWOT are never inserted as a fallback.

### 21.4 Plan proposal

`src/bp/product/plan_proposal.py` builds a proposal with:

- reading summary (decision, status, mentions, slots);
- framework options, with suggested ones marked;
- computations with reasons;
- proposed claims/arguments, marked proposed or conditional;
- evidence needs;
- structure;
- gaps;
- scope terms and numbers for the guard.

The UI replaces “Your brief” with **How I read your instruction**; the original instruction is inside a collapsible.

### 21.5 Guarded edit

`chat.refine_plan()` and `POST /api/cases/chat/{id}/refine` enforce:

- no number outside the brief;
- no framework outside the proposed options;
- no unknown framework;
- edits are recorded, not silently applied.

### 21.6 Refusal

A refused instruction returns `stage: "refused"` with:

- `code`;
- `title`;
- `detail`;
- `hint`;
- `found`;
- `options`.

The UI shows the brief summary, a **Start over** pill and a human notification below it. No questions, plan, retrieval or computation run for a refused instruction.

### 21.7 Citation styles

Implemented styles: APA 7, Harvard, Chicago author-date, MLA 9, Vancouver, IEEE, OSCOLA and Chicago notes-bibliography. Numbered styles render numbered in-text citations and numbered reference lists; author-date styles render author-date citations.

### 21.8 Tests

- `tests/test_instruction_reading.py` — aliases, roles, negation, comparison, slots, category errors, planner.
- `tests/test_chat.py` — proposal, refusal, guarded refine, no-framework.
- `tests/test_product_subjects.py` — proposal/refusal UI.
- Stress prompts: the five valid instructions in the owner’s test set are accepted; cross-domain nonsense is refused.

---

## 22. Final instruction to any model

Read this manual before touching home chat. Do not improvise a framework, a method, a number, a source, a citation or a chart. Do not do math. If a required input, evidence item or block is missing, ask or name the gap. If a plan does not pass the production check, do not confirm it. If an audit finding is unresolved, block export. Append decisions and changes to the logs. Do not rewrite history.