# Framework writing spec: analytical rigor for competitive-position frameworks

**Status:** Proposed. No code is written until the owner approves this spec and
the task plan (`docs/FRAMEWORK_WRITING_PLAN.md`).
**Owner authority:** `docs/FRAMEWORK_WRITING_GUIDELINES.md`.
**Governing product manuals:** `docs/CONDUCTOR_MANUAL.md` (§4 non-negotiables,
§6 framework completion), `docs/HOME_CHAT_ORCHESTRATION_MANUAL.md` (§2 hard
rules, §7 stage contracts, §11 evidence ledger).
**Build:** to be numbered in `docs/CHANGELOG.md` when the first slice lands.

---

## 1. The problem this fixes

The pipeline already retrieves evidence and builds a paper for Five Forces,
Generic Strategies and Porter's Diamond, but it does not **write the framework**
to an analyst's standard:

| Gap | Evidence in the tree today |
|---|---|
| Generic interpretive prose | `framework_profiles.py` ships one short `analysis`/`qualify`/`short` note per dimension, written before any evidence is seen. Diamond's six dimensions share the identical sentence "This element describes a factor in the diamond" (lines 5164-5199). |
| No rating record | `ratings: True` is declared for Five Forces but no rating, driver, trend, confidence or profitability impact is produced, stored or printed. |
| No evidence tiers or recency | Retrieved items carry `text`, `source`, `citation`, `title`, `database`; `year`, `url`, `doi`, tier and recency are dropped in `completion._one_block`. |
| No claim audit | No [F]/[I]/[J], no source-ID table, no coverage/triangulation/quantification/bias checks, no verdict. |
| Wrong unit for two frameworks | Generic Strategies and Diamond both declare `unit.field = "industry"`. The guideline sets Generic Strategies at the firm/business unit and Diamond at the nation/region-industry pair. |
| No synthesis, forward look or interactions | The outline has context, dimensions, discussion, implications, limitations, conclusion only. |

## 2. Goal

For the three Porter frameworks named in the guidelines, the pipeline must
produce an analysis a senior reader could act on and challenge:

1. the unit of analysis is stated before any force/determinant is analysed;
2. every factual claim is sourced from a recorded item;
3. every rating has drivers, evidence, trend, profitability impact, rationale
   and a confidence level;
4. the module's components are synthesised, not merely listed;
5. contradictions, gaps and assumptions are named;
6. the evidence audit required by Modules 2 and 3 is complete and printed;
7. thin inputs produce a partial analysis that says so, never a polished paper
   with invented support.

## 3. Locked decisions (owner, 2026-11-09)

| Id | Decision | Consequence |
|---|---|---|
| D1 | Scope is the three Porter frameworks. The core rules are written framework-agnostically so other profiles can adopt them later. | No change to the other 100+ profiles in this build; the writing engine is shared, the module data is per profile. |
| D2 | The model writes the analytical prose from the recorded items; code builds the summary/audit tables and enforces the rails. The deterministic draft remains the fallback. | One model pass per dimension may return prose **and** a structured reading. Code validates both. A refused or unavailable model falls back to the evidence-led draft, never to invented analysis. |
| D3 | [F]/[I]/[J] labels and A-D tiers print in the evidence-audit section only. Body prose stays in academic register. | The audit section is an H1 before References. The body separates fact (sourced item), inference (model reasoning over items) and judgment (rating) by construction. |
| D4 | The system proposes ratings and confidence; the student confirms or overrides. | A reading is stored with `status: proposed`; the student's decision is recorded; the paper states the status. No rating is silently adopted. |
| D5 | Units are corrected: Generic Strategies = firm/business unit + market; Diamond = nation/region + industry. Five Forces stays industry-wide. | `unit.field` gains `firm` and `country_industry`; refusals and retrieval context change; the two existing tests that assert an industry unit are updated to the new contract. |
| D6 | An empty dimension keeps the product rule: uncited labelled background + named gap + what would resolve it. | The body never prints a bare "Insufficient evidence" paragraph; the audit table records "Insufficient evidence" in its Notes column. |
| D7 | Build one framework at a time, test-first: Five Forces end-to-end, then Generic Strategies + audit, then Diamond + audit. | Each slice keeps the full suite green and has its own acceptance criteria. |

## 4. Success criteria (observable and testable)

**SC1 - Unit of analysis first.** Each paper opens with a Scope statement that
names the unit, the geography and the time frame, or says plainly which is not
stated. Five Forces names an industry; Generic Strategies names a firm/business
unit and a market; Diamond names a nation/region and an industry. A missing
required unit is refused with an actionable sentence, not defaulted.

**SC2 - No unsourced fact.** Every factual sentence in the body traces to a
recorded item with a source; a model paragraph that adds a number, name, link or
citation outside the items is refused and the deterministic reading replaces it.
No invented source, ever.

**SC3 - Every rating is complete.** A printed rating carries: the rating
(Low/Moderate/High), at least one driver with its evidence, the trend
(Rising/Stable/Falling) and its cause, the profitability/advantage impact, a
one-line rationale and a confidence (High/Medium/Low) with its reason. A rating
without a stored reading is not printed; the paper says the evidence does not
support a rating.

**SC4 - Audit is complete.** The audit section contains: the module's summary
table; one row per material claim with claim, dimension, source ID, tier,
recency, type [F]/[I]/[J], strength and notes; the coverage, triangulation,
quantification, bias, contradiction and gap checks; and an overall verdict
(Well-supported / Partially supported / Weakly supported) with a justification.

**SC5 - Synthesis, not a list.** Five Forces carries a synthesis that names the
forces that matter most and how they interact, plus 2-4 forward-looking shifts.
Diamond carries an interaction analysis of the determinants. Generic Strategies
carries coherence, sustainability and a stuck-in-the-middle assessment.

**SC6 - Implications are tied.** Strategic implications name the specific force,
determinant or strategy they answer. A generic recommendation ("improve
quality") is refused.

**SC7 - Thin inputs stay honest.** With no citable item, the dimension carries
the labelled background and the named gap; the audit records insufficient
evidence; the paper is still exportable if every other gate passes. No rating is
proposed for an empty dimension.

**SC8 - Student control.** A reading is `proposed` until confirmed. The student
can accept, override or drop it; the paper prints the confirmed value and records
the override. The silent Home run records proposals as `proposed` and the audit
says so.

**SC9 - Deterministic fallback.** With no model configured or a refused model
reply, the Draft paper is complete: scope, segments, deterministic reading,
tables with "not rated" where no reading exists, audit rows for sourced items,
verdict, references. Nothing model-written ships unvalidated.

**SC10 - Product rules hold.** No template instructions; export gate unchanged;
global product (no home country, home exchange or Philippine example); stdlib
only; no computation reimplemented; no test weakened.

**SC11 - Regression.** The targeted tests and the full suite pass. Existing
single-framework papers and the chat/worksheet evidence invariant still pass.

## 5. Stack

| Layer | Choice | Constraint |
|---|---|---|
| Runtime | Python 3.14, standard library only | No new dependency; `tests/test_frozen_contract.py` must pass |
| Tests | `unittest` discovery (`python -m unittest discover -s tests`) | Full suite green; no skipped or loosened checks |
| Retrieval | Existing `bp.product.retrieval`, `sources` | Same retriever on chat and worksheet; no new provider |
| Model | Existing `bp.product.prose` adapter (OpenCode Go, DeepSeek V4.1 Flash by default) | Proposals only; validated before storage |
| Paper | Existing `bp.product.paper`, `docx`, `matrix`, `tables`, `figures` | The writer only formats; the plan supplies structure |
| UI | Vanilla JS in `web/index.html`, JSON API | No framework, no build step |
| Docs | Markdown in `docs/` | Every increment updates CHANGELOG, WORKLOG, DECISIONS |

## 6. Architecture

### 6.1 New shared module

`src/bp/product/framework_writing.py` - one module for the three frameworks.
It holds **rules and formatters, never evidence**:

- the guideline prompt block and the per-module slots;
- the source-tier and recency read (`tier_for`, `recency_for`);
- the reading contract and `validate_reading`;
- the summary-table, audit-table, checks and verdict builders;
- the source-ID assignment (`[S1]`, `[S2]`, ... in first-appearance order);
- the deterministic fallback rows.

Nothing here writes a fact. Every string it prints is either the framework's own
declared label, a count, an item's recorded identity, or a stored reading.

### 6.2 Data contracts

**Item metadata** (extended in `completion._one_block`; stored with the item):

```json
{"text": "...", "provenance": "sourced", "source": "...", "citation": "...",
 "title": "...", "database": "OpenAlex", "year": 2024, "url": "...", "doi": "...",
 "tier": "B", "recency": "current", "source_id": "S2"}
```

**Analysis reading** (per block; `status` is `proposed`, `confirmed`,
`overridden`, `absent`):

```json
{"key": "rivalry", "label": "Industry rivalry",
 "rating": "High", "rating_scale": ["Low", "Moderate", "High"],
 "drivers": [{"driver": "price competition", "evidence": 1, "type": "F",
              "area": "pricing", "bias": "unclassified"}],
 "trend": "Rising", "trend_reason": "...",
 "profitability_impact": "...", "confidence": "Medium",
 "confidence_reason": "...", "so_what": "...", "rationale": "...",
 "status": "proposed", "confirmed_by": null, "override": null}
```

`evidence` is a zero-based index into the block's items, or `null` for a
judgment. A driver with `evidence: null` must have `type: "J"`. A driver with an
index must have `type: "F"` or `"I"`.

**Claim audit row** (built from items and readings):

```json
{"n": 1, "claim": "...", "dimension": "Industry rivalry", "source_id": "S2",
 "tier": "B", "recency": "current", "type": "F", "strength": "Moderate",
 "notes": "..."}
```

**Module audit**:

```json
{"coverage": {"areas": ["pricing", "operations"], "required": 3, "pass": false},
 "triangulation": {"sources": 2, "pass": true},
 "quantification": {"quantified": false, "cap": "Moderate"},
 "bias": [{"source_id": "S3", "bias": "firm"}],
 "contradictions": [{"claim": "...", "source_id": "S4", "note": "..."}],
 "gaps": ["Buyer power: no citable evidence"],
 "verdict": "Partially supported", "verdict_reason": "..."}
```

### 6.3 Where each part is produced

| Part | Producer | File |
|---|---|---|
| Scope statement | Deterministic from `unit`, `period`, `country`, `industry`; model may not add a fact | `framework_writing.scope_lines` |
| Dimension prose | Model, from the recorded items and the reading; validated | `completion._model_sections` |
| Rating | Model proposal, validated; student confirms | `framework_writing.validate_reading` |
| Summary table | Code, from readings; "not rated" when absent | `framework_writing.summary_table` |
| Audit table and checks | Code, from items, readings and a declared convention | `framework_writing.audit` |
| Synthesis / forward look / implications | Model, from the readings and items; validated; deterministic fallback | `completion` + profile `writing` slots |
| Deterministic fallback | Code, from items and profile notes | `completion._draft_data` |
| DOCX table | Existing renderer, extended to accept a section table | `docx.py` |

### 6.4 Prompt and validation

The model receives, per dimension: the case instruction, the unit, the label,
the items **with their source IDs**, and the driver checklist. It returns:

```json
{"paragraphs": ["..."], "reading": {"rating": "...", "drivers": [...],
 "trend": "...", "trend_reason": "...", "profitability_impact": "...",
 "confidence": "...", "confidence_reason": "...", "so_what": "...",
 "rationale": "..."}}
```

`validate_reading` refuses, with a named reason:

- a value outside the allowed enum;
- a driver that cites an item index outside the block;
- a driver marked `F`/`I` with no evidence, or `J` with an invented fact;
- a number, link, DOI, citation or mid-sentence proper noun not in the items or
  the declared unit (the existing `_problems`/`_allowed_names` rules apply);
- an empty `so_what`, `rationale` or `confidence_reason`;
- a rating proposed for an empty block.

A refused reading is dropped; the paragraph is replaced by the deterministic
reading, and the block is recorded as `reading: absent` with the reason.

### 6.5 Source tier and recency (declared convention)

This is a product convention, recorded as a B-decision, and printed in the audit
note so a reader can challenge it:

| Tier | Rule |
|---|---|
| A | A source the record identifies as a filing, regulator, official statistic, audited financial or company-reported metric. |
| B | Peer-reviewed or scholarly index (`OpenAlex`, `Crossref`, `Semantic Scholar`, `DOAJ`), a proprietary-corpus book, or a vetted-web industry/quality-journalism source. |
| C | A vetted-web press release, vendor page, blog, opinion piece, undated page, or an unclassified database. |
| D | No source, model prior knowledge, anonymous or uncited material. |

Recency: `current` when `year >= current_year - 3`; `stale` when older;
`undated` when no year. The current year is read from the clock at run time and
recorded in the audit. A stale or undated source is flagged, never dropped and
never silently upgraded.

**Strength rule** (printed in the audit note):

- **Strong:** tier A/B, current, and a quantified figure for a cost or
  differentiation claim.
- **Moderate:** tier A/B current without quantification, or tier B stale.
- **Weak:** tier C/D, undated, or no source.

The rule is deterministic; the audit says it is the product's convention, not
the source's own claim.

### 6.6 Unit rules

| Framework | `unit.field` | Required | Refusal |
|---|---|---|---|
| Five Forces | `industry` | the industry | unchanged, actionable |
| Generic Strategies | `firm` | the firm or business unit and the market | "Porter's generic strategies are chosen by a firm or business unit in a market. Name both." |
| Diamond | `country_industry` | the nation/region and the specific industry | "Porter's Diamond explains a nation's or region's industry. Name both; Global is not a nation." |

`period` is optional. When absent, the Scope statement says "the period is not
stated; the evidence is dated <earliest>-<latest>". No period is invented.

### 6.7 Outline additions (profile-declared, not hard-coded)

The generic `_sections` reads a profile `writing` block:

```python
"writing": {
  "summary_heading": "Force ratings",
  "synthesis_heading": "Synthesis and interactions",
  "forward_heading": "Forward-looking shifts",
  "audit_heading": "Evidence audit",
  "scope_heading": "Scope of the analysis",
  "sections": ["scope", "summary", "dimensions", "synthesis", "forward",
               "implications", "limitations", "conclusion", "audit"],
}
```

A profile without `writing` keeps today's outline exactly. A profile with it
gets the module sections in the declared order. The audit section is an H1
before References.

## 7. Conflict resolution (guideline vs product rule)

| Guideline says | Product rule says | Resolution |
|---|---|---|
| Print "Insufficient evidence" in the body | A dimension with no evidence carries labelled background + named gap | D6: body keeps the product rule; the audit row says "Insufficient evidence" and names what would resolve it. |
| Label every claim [F]/[I]/[J] | A paper never contains template instructions; academic register | D3: labels print in the audit section only; the body separates them by construction. |
| Cite [S3] for every fact | APA 7 / Harvard citations in the body | Body uses the style's citation; the audit uses [S#] and maps it to the citation. |
| Recommend 2-4 actions | The decision remains the student's; the model may not recommend | The paper states conditional actions tied to the chosen strategy, marked [J]; it does not recommend whether to proceed. |
| Ratings are the analyst's | Student inputs stay student inputs | D4: the system proposes, the student confirms or overrides; both are recorded. |

## 8. Out of scope

- Any framework other than Five Forces, Generic Strategies and Diamond.
- New retrieval providers, new computation methods, or changes to the frozen
  core.
- A redesign of the Home or worksheet UI; only the controls needed to confirm a
  reading are added.
- Charts beyond the existing tables.
- Changing the citation styles or the export gate.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The model invents support for a rating | Structured reading + the existing number/name/citation validator; a refused reading is dropped and the deterministic reading is used. |
| Ratings are subjective and could mislead | Marked [J], criteria shown, confidence stated, student confirms, audit prints the convention and the evidence. |
| A tier mapping is itself a judgment | Declared in the audit note, recorded as a B-decision, default is C (weak), never A. |
| Cost and latency rise | One call per dimension already exists; the reading rides in the same call. No extra round trip. Module synthesis uses the existing mid call. |
| Existing tests break on the unit change | The two affected test files are updated to the new contract in the same slice; all other tests must stay green. |
| Thin evidence produces a thin paper | The paper says so; the audit verdict is "Weakly supported"; no rating is invented. |

## 10. Open questions

None. The seven decisions are locked in §3. A new question that appears during
the build is recorded as a B-decision and blocks only the task that needs it.

## 11. Slice 2 - portfolio, growth and canvas frameworks (owner instruction, 2026-11-09)

The owner supplied two further instruction sets:
`portfolio_growth_frameworks_instructions.json` (Ansoff, BCG, GE-McKinsey,
Blue Ocean ERRC) and `canvas_frameworks_instructions.json` (Business Model
Canvas, Lean Canvas, Value Proposition Canvas). They add three mechanisms:

- **H (hypothesis)** as a fourth claim type, for forward-looking claims in
  Ansoff, ERRC and the canvases;
- **shown calculations** for BCG (relative share) and GE-McKinsey (weighted
  scores);
- an **assumption register** and standard **canvas layouts**.

### Locked decisions

| Id | Decision | Consequence |
|---|---|---|
| D8 | Add `H` to the claim types globally, not per framework. | The reading contract, the audit table and the prompts accept H; the existing F/I/J behaviour is unchanged. |
| D9 | The arithmetic is the frozen core's, not a new formula. `market_share` already returns `relative_market_share`; `growth_rate` returns CAGR; `weighted_summary` returns `weighted_mean`. | No duplicate core method and no frozen-fixture change. A thin product adapter, `framework_calc.py`, calls the attached core and classifies the result (BCG quadrant, GE zone) from declared cutoffs. The model never divides, averages or scores. |
| D10 | The portfolio is read from the brief's own table; a missing field is asked for by name. | A parser (`portfolio_reader.py`) reads Unit / Market / Growth / Own share / Top competitor share / Revenue; a missing figure stays a named gap, never a guess. |
| D11 | Add the standard BMC, Lean and VPC grids to `matrix.LAYOUTS`, and one shared assumption register. | The renderer is unchanged; the layouts are data. The register is a section table (Assumption | Block | Why it matters | Evidence so far | Test | Confidence). |
| D12 | Build order: shared mechanics (H, register, layouts) -> Ansoff, ERRC, canvases -> BCG/GE (adapter + portfolio reader). | Each slice keeps the suite green; BCG/GE do not ship until the adapter and parser are tested. |

### New success criteria

**SC16 - H is honest.** A forward-looking claim may be labelled H; an H claim
must name the test that would confirm or reject it, and is never printed as a
fact.

**SC17 - Calculations are reproducible.** Every BCG relative share and every GE
weighted score is the frozen core's recorded output, with the declared inputs
shown. No model-computed figure appears.

**SC18 - Borderline is reported.** A BCG unit within 10-15% of a threshold, or a
GE unit whose zone changes under the sensitivity test, is flagged.

**SC19 - The portfolio is explicit.** Each unit's served market, period and
currency are stated; a unit that cannot be placed is a named gap.

**SC20 - Ansoff sorts, it does not choose.** Each option is concrete, assessed
for growth logic, capabilities, risks, investment and evidence strength; the
quadrant is not presented as the recommendation.

**SC21 - ERRC is a hypothesis set.** Every Eliminate/Reduce/Raise/Create action
has a rationale, a cost impact, a buyer-value impact and either evidence or an
H label; the assumption register carries the test.

**SC22 - Canvas blocks are specific and consistent.** No "everyone", "high
quality" or "online marketing"; every segment has a value proposition, a channel
and a revenue stream; the consistency checks are printed.

**SC23 - Fit is not overclaimed.** The Value Proposition Canvas states which of
problem-solution, product-market and business-model fit has behavioural evidence
and which is still a hypothesis.

**SC24 - The visual rule holds.** A canvas is drawn as its standard grid; if a
supplied layout exists, it is used; content the layout cannot hold goes to the
notes, never dropped.

**SC25 - The register is complete.** ERRC and the three canvases print the
assumption register with the module's declared columns.

**SC26 - Stage fit is stated.** The paper says whether the canvas suits the
business stage and recommends a different one when it does not.

## 12. Definition of done

- [ ] Five Forces, Generic Strategies and Diamond each produce the guideline's
      output shape, with the audit where the module requires one.
- [ ] Every success criterion SC1-SC11 has a test that fails on the old code.
- [ ] The full suite passes, with the true count reported.
- [ ] The app is opened in a browser; a real paper is generated and read; the
      DOCX and the audit table are checked.
- [ ] The code is simplified after review (no dead branch, no duplicated rule).
- [ ] `docs/CHANGELOG.md`, `WORKLOG.md`, `DECISIONS.md` (tier/rating
      conventions), `KNOWN_LIMITATIONS.md` and `CONDUCTOR_MANUAL.md` are updated.

## 13. Slice 3 - quality frameworks and chart tie-up (owner instruction, 2026-11-09)

The owner supplied `quality_improvement_frameworks_instructions.json` (Root Cause
Analysis, FMEA, PDCA, Five-S audit) and asked that frameworks tie up with the
charts already created, across frameworks.

### Locked decisions

| Id | Decision | Consequence |
|---|---|---|
| D13 | Use the existing chart and diagram modules: `charts` (bar, line, pie, pareto, waterfall, stacked bar), `diagrams` (tree, process, matrix), `visuals` (declared points to a chart spec) and `figures` (render/stamp). | No new chart engine and no model-drawn image. A framework chart is a normal figure with a spec, a digest and a table fallback. |
| D14 | The chart is built only from values the record holds: the brief's table, the frozen core's calculation, or a stored reading. The model may propose the chart shape and labels, never a new number. | A chart value that is not in the items/calculation is refused; the paper says no chart was recorded rather than drawing an invented one. |
| D15 | A framework declares `writing.chart` and `writing.chart_caption`; the caption is digit-free because `figures.make` refuses a digit in a caption. | The chart title may carry a figure inside the spec; the caption is the module's own words. |
| D16 | Quality modules keep the owner's required tables: RCA verification audit, FMEA worksheet and calculation audit, PDCA cycle log and register, Five-S scorecard and findings table. A chart is additional, never a replacement for the record. | The paper carries both the table and the chart where both apply. |

### New success criteria

**SC27 - Root cause is a system cause.** The problem statement is quantified and
free of causes; no chain stops at human error; each root cause has forward and
reverse tests and at least one action; the verdict is one of Root cause
established / probable / not established.

**SC28 - FMEA arithmetic is reproducible.** Every RPN is the frozen core's
output from declared S, O and D; severity 9-10 is a priority regardless of RPN;
projected re-scores are labelled Projected.

**SC29 - PDCA status is honest.** Each stage is Completed, In progress or
Planned from the record; no result is written for a step that did not run; the
cycle log and the assumption register print.

**SC30 - Five-S is scored from evidence.** Criteria, anchors, scores and the
calculation print; an unassessed criterion is excluded with a note; safety is
reported separately; the findings table carries an action per finding.

**SC31 - A framework chart uses the existing modules.** At least one of bar,
line, pie, pareto, waterfall, stacked bar or tree; the spec is data, the figure
is stamped, and Word embeds the PNG or falls back to the value table.

**SC32 - Chart values are traceable.** Every plotted value is in the items, the
calculation record or a stored reading; an untraceable value refuses the chart.

**SC33 - Chart tie-up is cross-framework.** BCG and GE plot the core's
calculation rows; Five-S plots its S scores; FMEA plots RPN; PDCA plots the
measure series; RCA draws the why-chain tree. A framework without a numeric
record keeps its matrix or text and says no chart applies.

**SC34 - No silent absence.** When a chart is applicable but no values are
recorded, the paper says so in one sentence; it never prints an empty figure.
