# Framework writing plan: small tasks, each with acceptance criteria and allowed files

**Companion to:** `docs/FRAMEWORK_WRITING_SPEC.md` (the contract) and
`docs/FRAMEWORK_WRITING_GUIDELINES.md` (the writing authority).
**Build rule:** one task = one commit = tests + docs. Test-first: write the
failing test, run it red, implement, run it green, run the full suite, update
docs, commit. A task may touch **only** the files listed. If it needs another
file, stop and amend this plan first.

**Definition of a green task:** the new tests pass, the full suite passes with
the true count, no existing check is weakened, `tests/test_frozen_contract.py`
passes, and the docs named in the task are updated.

---

## Task T0 - Record the authority, the spec and the plan

**Goal.** Put the owner's guidelines, the spec and this plan in the repo before
any code.

**Allowed files**
- `docs/FRAMEWORK_WRITING_GUIDELINES.md` (new)
- `docs/FRAMEWORK_WRITING_SPEC.md` (new)
- `docs/FRAMEWORK_WRITING_PLAN.md` (new)

**Acceptance criteria**
- The guidelines preserve the owner's Part 0, Modules 1-3 and Part 4, including
  the driver checklists, audit tables and common errors.
- The spec records D1-D7 and SC1-SC11, the stack, the data contracts, the
  conflict table and the out-of-scope list.
- This plan names every task, its files and its acceptance criteria.
- No source file changes.

**Depends on:** nothing.

---

## Task T1 - Evidence metadata: source tier, recency, source ID, strength

**Goal.** Every accepted item carries enough metadata for an honest audit, and
the tier/recency/strength rules live in one place.

**Allowed files**
- `src/bp/product/framework_writing.py` (new)
- `src/bp/product/completion.py` (only `_one_block`'s item construction)
- `tests/test_framework_writing.py` (new)

**Acceptance criteria**
- `tier_for(item)` returns A, B, C or D by the declared convention; an unknown
  database is C, never A; no source is D.
- `recency_for(item, now)` returns `current`, `stale` or `undated` using the
  3-year rule.
- `source_id` assigns `S1`, `S2`, ... in first-appearance order across the paper.
- `strength_for(tier, recency, quantified)` returns Strong/Moderate/Weak by the
  declared rule; a cost/differentiation claim without a figure caps at Moderate.
- `_one_block` keeps `year`, `database`, `url`, `doi`, `tier`, `recency` on the
  item; the existing `text`, `provenance`, `source`, `citation`, `title` are
  unchanged.
- A test fails on the old code (the old item has no tier) and passes on the new.
- No public payload field is removed.

**Depends on:** T0.

---

## Task T2 - Correct the unit of analysis for Generic Strategies and Diamond

**Goal.** Generic Strategies analyses a firm/business unit in a market; Diamond
analyses a nation/region and an industry; Five Forces stays industry-wide.

**Allowed files**
- `src/bp/product/framework_profiles.py` (`GENERIC_STRATEGIES`, `PORTERS_DIAMOND`,
  `FIVE_FORCES` only if the shared wording needs it)
- `src/bp/product/completion.py` (`_unit`, `complete` signature/plumbing)
- `src/bp/product/api.py` (read `firm` and `country` from the request)
- `src/bp/product/chat.py` (pass the unit fields for these templates)
- `web/index.html` (send the profile's unit field; no redesign)
- `tests/test_generic_strategies_completion.py`
- `tests/test_porters_diamond_completion.py`
- `tests/test_framework_profiles.py`
- `tests/test_pestel_completion.py` (only if the shared unit contract requires
  it; the same-evidence invariant must stay intact)

**Acceptance criteria**
- Generic Strategies `unit.field == "firm"`; a brief with no firm/business unit
  is refused with an actionable sentence; a named firm plus market produces a
  unit with both.
- Diamond `unit.field == "country_industry"`; both parts are required; `Global`
  is refused; a named country/region plus industry produces retrieval context
  that contains both.
- Five Forces is unchanged: an industry is still required and no firm is asked.
- The chat and worksheet still return the same sources for the same brief, unit
  and region (`tests/test_pestel_completion.py::SameEvidenceTest`).
- The two old tests that assert an industry unit for Generic Strategies and
  Diamond are updated to the new contract, with the reason recorded in the test
  docstring; no other assertion is weakened.
- A test fails on the old code for each of the two new units.

**Depends on:** T1.

---

## Task T3 - The reading contract and its validator

**Goal.** The model can return a structured rating with the dimension prose, and
code can refuse a reading that invents support.

**Allowed files**
- `src/bp/product/framework_writing.py`
- `src/bp/product/completion.py` (the section call and `_ask_section`; no change
  to the retrieval path)
- `tests/test_framework_writing.py`

**Acceptance criteria**
- The allowed enums are declared once: rating `Low/Moderate/High`, trend
  `Rising/Stable/Falling`, confidence `High/Medium/Low`, type `F/I/J`,
  strength `Strong/Moderate/Weak`.
- `validate_reading(reading, items, unit, allowed_names)` refuses: an enum
  outside the list; a driver index outside `items`; a driver `F/I` with no
  evidence; a driver `J` that states a number/name/link/citation not in the
  items; an empty `so_what`, `rationale` or `confidence_reason`; a rating on an
  empty block.
- A valid reading is stored on the block as
  `{"...": ..., "status": "proposed"}`; an invalid one is dropped and the block
  records `reading: {"status": "absent", "reason": "..."}`.
- The section call still returns `paragraphs`; a reply without `reading` is
  accepted for profiles that do not declare a writing module.
- A reading is stored without a second model call (assert one call per
  dimension in the test).
- A test fails on the old code (no `reading` is stored).

**Depends on:** T1.

---

## Task T4 - Five Forces: the module data

**Goal.** Five Forces declares its driver checklists, its writing sections and
its audit needs, with no boilerplate.

**Allowed files**
- `src/bp/product/framework_profiles.py` (`FIVE_FORCES` only)
- `tests/test_five_forces_writing.py` (new)

**Acceptance criteria**
- Each of the five forces declares the guideline's driver checklist for that
  force, with the checklist words kept as data.
- The profile declares `writing.sections` in the guideline order: scope,
  summary, dimensions, synthesis, forward, implications, limitations,
  conclusion, audit.
- The profile declares the headings the spec names, and the unit is still an
  industry.
- No two forces share an identical `analysis` or `qualify` note; each note names
  the force's own mechanism.
- `profile_for("template_five_forces")` still passes its completeness check.
- A test fails on the old code (no `writing` block, no checklists).

**Depends on:** T2.

---

## Task T5 - Five Forces: scope, rating prose, summary table and fallback

**Goal.** The Draft and Full papers carry the guideline's shape for Five Forces.

**Allowed files**
- `src/bp/product/completion.py` (prompt slots, `_shape`, `_draft_data`,
  `_sections`; the shared prompt safety rules stay in one place)
- `src/bp/product/framework_writing.py` (`scope_lines`, `summary_table`,
  `dimension_lines`)
- `tests/test_five_forces_writing.py`
- `tests/test_completion.py` (only if a shared assertion must track the new
  section list; no safety assertion is removed)

**Acceptance criteria**
- A Full paper contains, in order: Introduction, Scope of the analysis, the
  five force sections (each with rating, drivers, trend, profitability impact,
  rationale and confidence), Synthesis and interactions, Forward-looking
  shifts, Implications, Limitations, Conclusion, Evidence audit, References.
- A Draft paper contains the same headings; a dimension without a reading says
  "not rated" and why; no rating is invented.
- The summary table has the columns Force | Rating | Trend | Confidence |
  One-line rationale and one row per force; a missing reading prints "not
  rated".
- The synthesis names the strongest and weakest evidenced force and at least one
  interaction; the forward look names 2-4 shifts and a direction.
- Implications name the force they answer.
- The paper contains no template instruction; `paper.check` passes.
- A test fails on the old code (no scope, no summary, no forward look).

**Depends on:** T3, T4.

---

## Task T6 - The audit table, checks and verdict (shared)

**Goal.** Code builds the evidence audit from the record, with the checks the
guideline requires, and the DOCX prints it.

**Allowed files**
- `src/bp/product/framework_writing.py` (`audit`, `checks`, `verdict`,
  `audit_table`)
- `src/bp/product/completion.py` (insert the audit section; no new fact)
- `src/bp/product/docx.py` (render `section["table"]` in the academic paper)
- `src/bp/product/paper.py` (scan a section table for template text)
- `tests/test_framework_writing.py`
- `tests/test_paper_documents.py` (only if the renderer contract is asserted
  there)

**Acceptance criteria**
- One row per material claim: number, claim, dimension, source ID, tier,
  recency, type, strength, notes.
- The checks are computed, not asserted: coverage (distinct areas/required),
  triangulation (distinct sources), quantification (figure present), bias
  (classified or "not classified"), contradiction log, gap list.
- The verdict is one of Well-supported / Partially supported / Weakly supported,
  with a one-paragraph reason; "insufficient evidence" appears in a row's notes,
  never as a bare body paragraph.
- The audit note states the tier, recency and strength conventions, so a reader
  can challenge them.
- The Word file contains a real table with the declared columns and rows; the
  plain-text fallback is readable when a table is not rendered.
- A section table is scanned for template text; no placeholder can hide in it.
- A test fails on the old code (no table render, no verdict).

**Depends on:** T5.

---

## Task T7 - Generic Strategies: module data, classification and audit

**Goal.** Generic Strategies analyses a firm/business unit, classifies the
strategy with a fit table, tests coherence and sustainability, and carries the
Module 2 audit.

**Allowed files**
- `src/bp/product/framework_profiles.py` (`GENERIC_STRATEGIES` only)
- `src/bp/product/framework_writing.py` (the Generic Strategies module slots and
  the value-chain area list)
- `src/bp/product/completion.py` (only the module's prompt slots and shape)
- `tests/test_generic_strategies_completion.py`
- `tests/test_generic_strategies_writing.py` (new)

**Acceptance criteria**
- The output carries: Scope, Strategy fit summary (Strong/Partial/Weak/None for
  each of the four), Classification and reasoning, Coherence and sustainability,
  Stuck-in-the-middle assessment, Implications and recommendations, Evidence
  audit.
- The primary strategy is named, or the paper says "unclear" with the reason.
- Low price alone never proves cost leadership; a premium alone never proves
  differentiation; a firm's own marketing is marked as bias.
- The audit runs the coverage (three value-chain areas), triangulation,
  quantification, bias, contradiction and gap checks, and prints the verdict.
- Recommendations are 2-4, tied to the chosen strategy; the paper does not
  recommend whether to proceed.
- An empty dimension carries the labelled background and the named gap.
- A test fails on the old code (no fit table, no audit).

**Depends on:** T6.

---

## Task T8 - Diamond: module data, outcome evidence and audit

**Goal.** Diamond analyses a nation/region and an industry, establishes the
competitiveness outcome, analyses the determinants and their interactions, and
carries the Module 3 audit.

**Allowed files**
- `src/bp/product/framework_profiles.py` (`PORTERS_DIAMOND` only)
- `src/bp/product/framework_writing.py` (the Diamond module slots and the
  determinant list)
- `src/bp/product/completion.py` (only the module's prompt slots and shape)
- `tests/test_porters_diamond_completion.py`
- `tests/test_porters_diamond_writing.py` (new)

**Acceptance criteria**
- The output carries: Scope (nation/region, industry, time), Competitiveness
  outcome evidence, Diamond summary table (Determinant | Condition | Confidence
  | One-line rationale), Determinants plus government and chance, Interaction
  analysis, Overall assessment and sustainability, Implications, Evidence audit.
- Government and chance are analysed as influences on the four determinants,
  never as a fifth and sixth determinant.
- The audit runs the outcome-evidence, determinant-coverage (Tier A/B),
  correlation-vs-causation, industry-specificity, counter-evidence and recency
  checks; when there is no outcome evidence the analysis is labelled
  "explanatory hypothesis".
- Basic factors are not credited as a sustainable advantage.
- A test fails on the old code (no outcome section, no interaction analysis, no
  audit).

**Depends on:** T7.

---

## Task T9 - Student confirmation of the readings

**Goal.** A rating is proposed, then confirmed or overridden by the student, and
the paper says which.

**Allowed files**
- `src/bp/product/api.py` (`POST /api/cases/frameworks/readings`)
- `src/bp/product/chat.py` (carry the confirmed readings into the draft)
- `src/bp/product/completion.py` (accept confirmed/overridden readings)
- `web/index.html` (a confirm/override control on the review; no redesign)
- `tests/test_framework_readings.py` (new)
- `tests/test_product_subjects.py` (only for the new control)

**Acceptance criteria**
- The review payload exposes each block's reading with its status, criteria and
  evidence references.
- `POST /api/cases/frameworks/readings` accepts `confirmed`, `overridden` (with
  a value from the allowed scale) or `dropped`, and records the student's choice
  and the time.
- The paper prints the confirmed value; an override is printed as the student's
  and the proposal is kept in the record; a dropped reading prints "not rated".
- The silent Home run records proposals as `proposed` and the audit says the
  student has not confirmed them.
- An unknown block, an unknown rating or a payload without a status is refused
  with a sentence, not silently ignored.
- No reading is ever printed as the student's own without a recorded
  confirmation.
- A test fails on the old code (no endpoint, no status).

**Depends on:** T5.

---

## Task T10 - Docs, samples, full suite and browser verification

**Goal.** Close the increment honestly and prove it in the running app.

**Allowed files**
- `docs/CHANGELOG.md`
- `docs/WORKLOG.md`
- `docs/DECISIONS.md` (the tier, recency, strength and rating conventions)
- `docs/KNOWN_LIMITATIONS.md`
- `docs/CONDUCTOR_MANUAL.md` (§6 checklist: how a writing module is added)
- `docs/PRODUCT_GAP_MAP.md` (only if the gap is named there)
- `tests/test_sample_papers.py` (one APA and one Harvard sample for each
  framework, built from the same structure)
- `tests/test_conductor_frameworks.py` (only if the conductor contract needs the
  new sections)

**Acceptance criteria**
- The full suite passes; the true count is reported in `WORKLOG.md`.
- One APA and one Harvard sample per framework are generated and read; the
  sample tests assert the guideline headings, the summary table and the audit.
- The app is opened in a browser: a real Five Forces, Generic Strategies and
  Diamond paper is generated from a sample brief; the page and the downloaded
  Word file are read; the audit table and the ratings are present.
- Security review: no secret in the repo, no new dependency, no unbounded input,
  no path traversal in the new endpoint, no model output used without
  validation.
- Simplification review: one rule per concept, no duplicated enum, no dead
  branch; the diff is smaller after the review than before it.
- `docs/CHANGELOG.md`, `WORKLOG.md`, `DECISIONS.md`, `KNOWN_LIMITATIONS.md` and
  `CONDUCTOR_MANUAL.md` are updated in the same commit.

**Depends on:** T8, T9.

---

## Slice 2 tasks (portfolio, growth and canvas frameworks)

### Task T11 - The H claim type and the assumption register

**Allowed files**
- `src/bp/product/framework_writing.py`
- `src/bp/product/completion.py` (prompt slots only)
- `tests/test_framework_writing.py`
- `tests/test_five_forces_writing.py` (one regression assertion)

**Acceptance criteria**
- `CLAIM_TYPES` includes `H`; a reading driver may be `H`; an H driver must name
  a test in its `driver` text or the reading is refused.
- The audit table prints `H` in the Type column and the conventions note says H
  is a forward-looking claim, not a fact.
- `assumption_register(blocks, columns)` returns a section table with the
  module's declared columns; a module without a register gets no table.
- The existing F/I/J readings and audits are unchanged.

### Task T12 - Canvas layouts

**Allowed files**
- `src/bp/product/matrix.py` (data only)
- `tests/test_matrix_completion.py` (layout assertions)

**Acceptance criteria**
- `LAYOUTS` gains `template_business_model_canvas`, `template_lean_canvas` and
  `template_value_proposition_canvas` in the standard layout order; each block
  key maps to an existing profile block.
- The renderer and the writer are unchanged.
- A test asserts the BMC nine cells, the Lean nine cells and the VPC two halves.

### Task T13 - Ansoff writing module

**Allowed files**
- `src/bp/product/framework_profiles.py` (`ANSOFF` only)
- `src/bp/product/framework_writing.py` (risk scale and module slots)
- `tests/test_ansoff_completion.py`
- `tests/test_ansoff_writing.py` (new)

**Acceptance criteria**
- Unit = firm/business unit + market; the quadrants are market penetration,
  product development, market development, diversification; diversification
  distinguishes related and unrelated.
- Each option is assessed for growth logic, capabilities, risks, investment and
  evidence strength; the summary table is Quadrant | Risk | Confidence |
  One-line rationale; the quadrant is a risk sort, not a recommendation.
- Output: scope, classification rules, matrix summary, detailed options,
  prioritisation, sequencing, gaps.
- A generic label ("enter new markets") is refused by the validator.

### Task T14 - Blue Ocean ERRC writing module

**Allowed files**
- `src/bp/product/framework_profiles.py` (`ERRC` only)
- `src/bp/product/framework_writing.py` (impact scale and register)
- `tests/test_errc_completion.py`
- `tests/test_errc_writing.py` (new)

**Acceptance criteria**
- Unit = industry + focal offering; target buyers and non-customers are named.
- The four actions each carry factor, rationale, evidence or H, cost impact and
  buyer-value impact; Eliminate/Reduce are not skipped.
- The assumption register prints the declared columns; the focus/divergence/
  tagline test and the validation plan are sections.
- No evidence audit is printed (the guideline declares none).

### Task T15 - The three canvases

**Allowed files**
- `src/bp/product/framework_profiles.py` (`BMC`, `LEAN_CANVAS`,
  `VALUE_PROPOSITION_CANVAS` only)
- `src/bp/product/framework_writing.py` (block-confidence scale, register)
- `tests/test_business_model_canvas_completion.py`
- `tests/test_lean_canvas_completion.py`
- `tests/test_value_proposition_canvas_completion.py`
- `tests/test_canvas_writing.py` (new)

**Acceptance criteria**
- BMC: nine blocks in the standard order, one business model, as-is vs to-be,
  the consistency checks printed; the assumption register is printed.
- Lean: nine blocks plus existing alternatives, high-level concept and early
  adopters; problem-solution fit, ranked risks and experiments.
- VPC: Customer Profile built first, ranked jobs/pains/gains, Value Map mapped
  item by item, a fit table with Strong/Partial/None, gaps and noise, and the
  three fit stages with the evidence level.
- Vague entries ("everyone", "high quality") are refused; a canvas for several
  models is refused with the reason.

### Task T16 - Portfolio reader and calculation adapter

**Allowed files**
- `src/bp/product/portfolio_reader.py` (new)
- `src/bp/product/framework_calc.py` (new)
- `src/bp/product/completion.py` (attach the core, call the adapter)
- `src/bp/product/api.py` (`attach_methods` also attaches the core to completion)
- `tests/test_portfolio_reader.py` (new)
- `tests/test_framework_calc.py` (new)

**Acceptance criteria**
- `portfolio_reader.read(text)` reads a table with Unit / Market / Growth /
  Own share / Top competitor share / Revenue; a missing field is returned by
  name; no figure is guessed.
- `framework_calc.bcg(rows, cutoff)` calls `market_share` and `growth_rate` for
  each unit, returns relative share, growth and quadrant, and flags a unit
  within 10-15% of the cutoff.
- `framework_calc.ge(units, weights)` calls `weighted_summary` per axis and
  returns the weighted totals and the zone; weights must sum to 100.
- The adapter is the only caller of the core in the framework path; the model
  never computes.

### Task T17 - BCG and GE-McKinsey writing modules

**Allowed files**
- `src/bp/product/framework_profiles.py` (`BCG`, `GE_MCKINSEY` only)
- `src/bp/product/framework_writing.py` (calculation table and audit slots)
- `src/bp/product/completion.py` (calculation record into the paper)
- `tests/test_bcg_completion.py`
- `tests/test_ge_mckinsey_completion.py`
- `tests/test_bcg_ge_writing.py` (new)

**Acceptance criteria**
- BCG: scope, market definitions, metric definitions, calculation table, matrix
  summary, per-unit assessment, portfolio balance, strategic hypotheses,
  evidence audit with the sensitivity test.
- GE: scope, factors/weights/anchors, scoring tables, weighted totals, zone
  placement, sensitivity, per-unit posture, portfolio view, evidence audit with
  the coverage and double-counting checks.
- Every figure is the core's recorded output; the paper never prints a
  model-computed relative share or weighted score.

### Task T18 - Docs, samples, suite and browser

**Allowed files**
- `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`,
  `docs/KNOWN_LIMITATIONS.md`, `docs/CONDUCTOR_MANUAL.md`,
  `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`
- `tests/test_sample_papers.py`

**Acceptance criteria**
- The full suite passes; the true count is recorded.
- One APA and one Harvard sample per framework are generated and read.
- The app is opened; a real Ansoff, BMC and BCG paper is generated and read.

## Slice 3 tasks (quality frameworks and chart tie-up)

### Task T19 - Framework figure adapter

**Allowed files**
- `src/bp/product/framework_figures.py` (new)
- `src/bp/product/framework_writing.py` (chart contract/validator)
- `tests/test_framework_figures.py` (new)

**Acceptance criteria**
- `build(chart, caption)` uses `visuals.source_bundle`, `visuals.spec_for`,
  `figures.make/render/stamp` for bar/line/pie/pareto/waterfall/stacked-bar, and
  `diagrams` for a tree.
- The caption is digit-free; the spec title may carry the figure.
- `validate_chart(chart, items, calculation)` refuses an unknown kind, a missing
  label, a non-numeric value, a pareto without a cumulative, and a value not in
  the items/calculation.
- A valid chart is a normal figure with a digest and a table fallback.

### Task T20 - Quality table reader

**Allowed files**
- `src/bp/product/quality_reader.py` (new)
- `tests/test_quality_reader.py` (new)

**Acceptance criteria**
- Reads an FMEA worksheet (ID, failure mode, S, O, D, RPN, action), a Five-S
  scorecard (S, criterion, score, maximum) and a PDCA measure table (measure,
  baseline, target, result) from the brief.
- A missing column is returned by name; no figure is guessed.
- The reader does no arithmetic.

### Task T21 - Root Cause Analysis module

**Allowed files**
- `src/bp/product/framework_profiles.py` (`ROOT_CAUSE` only)
- `src/bp/product/framework_writing.py` (root-cause scale)
- `tests/test_root_cause_completion.py`
- `tests/test_root_cause_writing.py` (new)

**Acceptance criteria**
- Sections: scope and problem, containment, evidence, fishbone/structured causes,
  why-chains, root causes, actions, effectiveness check, verification audit.
- Every cause has a status (Verified/Plausible/Unverified); a why-chain is a
  tree; the verdict is one of the three; no chain stops at human error.
- The verification audit table prints with the guideline columns.

### Task T22 - FMEA module and RPN

**Allowed files**
- `src/bp/product/framework_profiles.py` (`FMEA` only)
- `src/bp/product/framework_calc.py` (`fmea` using the core)
- `src/bp/methods.py` (`fmea_rpn` only, with tests)
- `tests/test_fmea_completion.py`
- `tests/test_fmea_writing.py` (new)

**Acceptance criteria**
- Sections: scope and type, scales and anchors, worksheet, prioritisation,
  actions, re-scoring (Projected if not run), calculation audit.
- RPN is S x O x D from the core, never the model; severity 9-10 is a priority.
- The Pareto chart plots the core's RPN rows; the worksheet table prints.

### Task T23 - PDCA module

**Allowed files**
- `src/bp/product/framework_profiles.py` (`PDCA` only)
- `src/bp/product/framework_figures.py` (line/bar from measures)
- `tests/test_pdca_completion.py`
- `tests/test_pdca_writing.py` (new)

**Acceptance criteria**
- Sections: scope and status, Plan, Do, Check, Act, cycle log, next cycle and
  sustainment, assumption register, required checks.
- Each stage is Completed/In progress/Planned; no result is written for a step
  that did not run; the register prints.
- A measure series draws a line or bar; no values means no chart.

### Task T24 - Five-S module

**Allowed files**
- `src/bp/product/framework_profiles.py` (`FIVE_S` only)
- `src/bp/product/framework_calc.py` (`five_s` using the core)
- `src/bp/methods.py` (`five_s_score` only, with tests)
- `tests/test_five_s_completion.py`
- `tests/test_five_s_writing.py` (new)

**Acceptance criteria**
- Sections: scope and evidence, scorecard, score calculation and trend,
  findings, safety, recurring causes, actions, follow-up, required checks.
- Scores are from the core; unassessed criteria are excluded; safety is separate.
- A bar chart plots the five S scores; the scorecard and findings tables print.

### Task T25 - Cross-framework chart wiring and docs

**Allowed files**
- `src/bp/product/framework_figures.py`
- `src/bp/product/completion.py` (deterministic BCG/GE charts)
- `src/bp/product/framework_profiles.py` (chart declarations)
- `tests/test_bcg_ge_writing.py`
- `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`,
  `docs/KNOWN_LIMITATIONS.md`, `docs/CONDUCTOR_MANUAL.md`, `docs/HANDOFF.md`,
  `docs/HOME.md`, `docs/CONTRIBUTORS.md`

**Acceptance criteria**
- BCG plots relative share by unit; GE plots the weighted axis totals.
- Five-S, FMEA, PDCA and RCA attach their chart where the record holds values.
- A framework without a numeric record says no chart applies.
- The full suite passes; the app is opened and a quality paper is read.

## Test-first protocol (every task)

1. Write the failing test in the task's test file.
2. Run it alone and confirm it fails for the right reason (not an import error).
3. Implement the smallest change that makes it pass.
4. Run the task's tests, then the full suite:
   `$env:PYTHONPATH="src"; python -m unittest discover -s tests`
   Read the final `OK` line, not the PowerShell exit code.
5. If the suite is red, stop and fix; do not edit an expected value to go green.
6. Update the docs named in the task.
7. Commit with what changed, what verifies it, and the test count.

## What would make this plan wrong

- The owner changes a locked decision (D1-D7) -> amend the spec first.
- A task needs a file outside its list -> amend the plan before touching it.
- A guideline requirement cannot be met without inventing evidence -> name the
  conflict and ask; do not paper over it.
- The model cannot produce a valid reading reliably -> keep the reading
  optional, print "not rated", and record the refusal; never relax the
  validator.
