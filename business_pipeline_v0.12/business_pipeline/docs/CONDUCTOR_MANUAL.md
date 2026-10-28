# Conductor manual: how the chat builds a paper

This is the operating manual for the Smart Business Writer chat. Read it before
adding a framework, a computation, a writer feature or a model-assisted step.
It records the goal, the division of responsibility, the non-negotiable rules
and the checklist for extending the working model.

## 1. The goal

The chat is the **macro conductor**. A student describes a decision or an
assignment; the chat decides which frameworks and computations the paper needs,
borrows them from the relevant subjects, and composes one coherent paper. It is
not a PESTEL worksheet, a SWOT form or a calculator with a chat skin.

The current working model is deliberately narrow:

| Area | Working now |
|---|---|
| Frameworks | PESTEL, SWOT, PESTEL + SWOT, Five Forces, Value Chain, Ansoff, VRIO, Break-even, and Five Forces + Break-even |
| Paper profiles | Business plan (SHS core; college adds tax, cap table and impact) |
| Computation | A **capability selected per paper** by the resolver in `bp/product/capabilities.py`. Break-even is the only registered capability today, so a framework paper carries it only when the brief needs it; a framework-only brief runs no computation. Five plan blocks at SHS and eight at college, through the frozen core |
| Output | APA 7 or Harvard `.docx`, hierarchy enforced |
| Evidence | Curated academic databases and vetted web domains; VRIO and Break-even retrieve none by design |
| Model prose | Optional, proposal only, DeepSeek V4.1 Flash by default |
| Framework completion | Porter's Five Forces pilot: instruction box, research per force, sourced/suggested/gap provenance |

Other frameworks and computations are being strengthened in the backend. They
must be wired into the chat one at a time, following this manual, not improvised
inside the writer.

## 2. Division of responsibility

### Chat owns

- the decision and the thesis;
- the framework stack and any computation;
- the paper plan: sections, levels, purpose, evidence allocation, student
  inputs and transitions;
- the export gate.

### Subject modules provide

- framework dimensions and question banks;
- computation methods with declared inputs and a frozen result;
- source registries and relevance rules.

### Writer and renderer only format

- `bp.product.writing` turns sources into citations and reference entries.
- `bp.product.docx` renders the supplied outline. It does not decide headings,
  sections or order.
- `bp.product.paper` holds the section shape and the structural checks.

### Model prose may only edit linking prose

- introduction, one linking sentence per dimension, integration and conclusion;
- never evidence paragraphs, references, numbers, citations or student
  implications;
- every proposal is validated and stored; the student accepts or discards it;
- the deterministic draft remains the fallback.

## 3. Paper hierarchy (Option A)

| Level | Heading |
|---|---|
| H1 | Introduction |
| H1 | PESTEL |
| H2 | Political, Economic, Social, Technological, Environmental, Legal |
| H1 | SWOT |
| H2 | Strengths, Weaknesses, Opportunities, Threats |
| H1 | Five Forces |
| H2 | Industry rivalry, Threat of new entrants, Threat of substitutes, Buyer power, Supplier power |
| H1 | Value Chain |
| H2 | Inbound logistics, Operations, Outbound logistics, Marketing and sales, Service, Procurement, Technology development, Human resource management, Firm infrastructure |
| H1 | Ansoff Growth Matrix |
| H2 | Market penetration, Market development, Product development, Diversification |
| H1 | VRIO |
| H2 | Resources, Valuable, Rare, Costly to imitate, Organised to capture value |
| H1 | Financial Feasibility |
| H2 | Break-even Analysis (or the named computation) |
| H1 | Discussion |
| H2 | Integration of the frameworks |
| H2 | Implications |
| H2 | Limitations |
| H1 | Conclusion |
| H1 | References / Bibliography |

A framework is level 1; its dimensions are level 2. A computation is a level 1
feasibility section with a level 2 method section. The Discussion carries the
integration, not a second framework heading.

### 3.1 A paper profile is not a framework

A **profile** composes a whole paper when no single framework is the paper. The
business plan is the first profile (`PROFILE_BUSINESS_PLAN` in
`bp/product/chat.py`). It has four kinds of section:

| Kind | What it supplies | Rule |
|---|---|---|
| `input` | the student's business description, marketing, operations, management and named risks | reproduced verbatim; never inferred or filled |
| `evidence` | market size and growth, customers, competition and regulation | retrieved and cited, or a named gap |
| `computation` | the plan-level blocks, each a core method | the frozen core runs it; the product formats the result |
| `integration` | executive summary, risk analysis, limitations, conclusion | only supplied facts and stored core results; no new claim |

The **Financial Plan is one H1**; each computation block is an H2 under it. A
college plan adds H1s for Funding and Ownership and Social and Environmental
Impact, with the cap table and impact ratio as their H2s. The SHS core blocks
are `sales_from_market`, `breakeven`, `depreciation_schedule`,
`proforma_statements` and `sensitivity_table`; college adds `tax_declared`,
`cap_table_round` and `cost_effectiveness`.

A profile follows the same rules as a framework: the plan is proposed and
confirmed before research or computation, the student's words stay theirs,
every gap is named and the export gate lists what is missing. Two entry points
share one engine: the Entrepreneurship page opens the **strict** convention,
which keeps every standard section; Home opens **open composition**, which may
leave an optional section out but changes no fact and no figure.

`proforma_statements` is a hard refusal at the opening balance sheet. An
unbalanced opening is rejected with the equity that would balance it, and the
refusal is named in the export gate; the product never plugs a difference.

## 4. Non-negotiable rules

1. **No invented evidence.** Every external claim is quoted or paraphrased from a
   retrieved source, with the source recorded. No invented source, number,
   citation or study.
2. **Gaps are named, never filled.** A dimension without evidence says it is a
   gap.
3. **Student inputs stay student inputs.** Strengths, weaknesses, implications,
   declared costs and expected volume are supplied by the student.
4. **No silent framework substitution.** If a brief names a framework that is
   not wired, refuse and say so. Never default to PESTEL and ignore the request.
5. **Computations come from the frozen core.** Call the method; do not
   reimplement or re-round it in the product layer.
6. **A paper never contains instructions.** No `(your analysis)`, “Not supplied
   yet”, “add your implications”, template names or placeholder prose.
7. **Export is blocked when the paper is incomplete.** Missing implications or
   missing SWOT internal factors return HTTP 409 with the missing list.
8. **The model does not research.** It edits prose only after the deterministic
   draft exists.

## 5. Adding a framework (checklist)

1. Add the framework id and label to `FRAMEWORKS` in `bp/product/chat.py`.
2. Define its dimensions as `(key, label, query cues, source category)`.
3. Add its question bank. Use `text`, `choice`, `items` or `number`; do not add
   a new question type without updating the API and UI.
4. Add the search terms to `SEARCH_TERMS`; keep them short and country-aware.
5. Add the plan wording: what it does, what it misses, expected output.
6. Add the draft branch: H1 framework, H2 dimensions, each dimension one
   paragraph from accepted evidence.
7. Add the Discussion integration when the framework is combined with another.
8. Nothing to add to a UI selector: the framework is inferred from the brief
   (`_infer_framework`); the chat has no framework picker.
   Add the cues `_infer_framework` needs so a student's words reach it.
9. Add tests: questions, plan, research with mocks, hierarchy, draft, export.
10. Add one APA and one Harvard sample built from the same structure.
11. Record the decision and changelog entry.

Do not add a framework by hard-coding its headings in the writer. The writer
only renders what the chat plan supplies.

## 6. Completing a framework from an instruction

The Five Forces pilot is the reference behaviour for future framework
auto-completion.

1. On the subject page, the student describes the case in **Describe your case or paste the instruction**; the matcher opens the suggested worksheet with that description already in the completion box. The subject-level source finder has been removed; research happens inside the worksheet.
2. `bp.product.completion` extracts the country and case context, builds one
   short query per force, retrieves academic and vetted web sources, and ranks
   them.
3. A force with sources gets one to three sourced items. Each item carries the
   citation in the form `text || reference`.
4. A force with no evidence gets a **suggested case assumption** from the model,
   labelled `suggested`, with no citation. It is not evidence and must be
   ticked by the student.
5. A force with neither gets a **named gap**.
6. The review lists every block and every item. The student ticks what the
   worksheet may use, then applies it.
7. The worksheet input accepts per-line `text || source`, so one block can carry
   several citations without losing them.
8. **Generate paper (Word)** stays hidden until all five forces have content, then
   appears at the bottom of the worksheet. It is also available on the results page
   after a run.
   - **Draft (evidence-led)** is deterministic: it quotes the accepted items, labels
     assumptions and names gaps.
   - **Full paper (model-assisted)** sends the same structured items to DeepSeek
     V4.1 Flash. The model writes the introduction, one paragraph per force, the
     discussion and the conclusion; the system appends the real citations
     afterwards. It may not add a citation, source, URL, number, percentage,
     named condition, actor, technology or country that is not in the items; an
     inference must read as an inference ("this suggests", "this implies"). A
     validator checks citations, links, numbers and mid-sentence proper nouns,
     retries once, and then refuses. **A failed full paper is never downloaded:**
     the page says the run failed and asks the student to choose Draft
     explicitly. Full is the default selection.
   - Generation reads the case instruction typed at the top of the worksheet. A
     missing instruction, or the worksheet's own tool title, is refused rather
     than written into the title and introduction.
   - An item the student supplied as their own evidence stays student evidence.
     Only assumption-flagged items are labelled "Case assumption".

The model may not add a number, source, citation, link or named fact. A
suggestion that fails validation is dropped and the block remains a gap.

The pilot is deliberately limited to `template_five_forces`. Do not enable
other frameworks until the same behaviour has been reviewed for that framework.

## 7. Adding a computation (checklist)

A computation is a **capability**, not a step. The paper carries one only when
the brief asks a question that computation answers; a framework-only brief
selects nothing, asks for no figures and has no computation section.
`bp/product/capabilities.py` holds the catalogue and the resolver.

1. Confirm the method exists in the frozen core and has a declared input schema
   (`bp.methods.describe(method)["input_schema"]`); the product reads that
   schema, it never restates it.
2. Add one entry to `ENTRIES` in `bp/product/capabilities.py`:
   - `intent` — one group per question kind (for example `cost_cover`); at most
     one capability from a group is selected;
   - `any_of` — the intent cues in the student's words;
   - `needs_any` — at least one of the quantities the method needs. A bare
     "cost" must never start a computation;
   - `applies_to` — the frameworks it may ride on (do not include a framework
     that already carries the same analysis: `breakeven`,
     `five_forces_breakeven` are excluded from `applies_to`);
   - `slot` — the H1 and H2 it takes when selected; `integration` — the H2 of
     the Discussion paragraph that reads it against the framework;
   - `licenses` / `not` — the claim it supports and its own `unsupported_use`;
   - `domain` — the key of a domain check in `chat._capability_inputs` when the
     method needs one beyond the schema (break-even refuses negatives).
3. Register its formatter in `chat.CAPABILITY_LINES`, next to
   `_break_even_lines`. It reads the recorded core result and prints it; it
   must not compute, round or re-derive anything.
4. Nothing else: the draft, the gate and the plan are generic. Do not add a
   branch to `draft`, `paper.missing` or the UI for one method.
5. Test the five rows of the matrix (below) plus one APA and one Harvard sample.

The resolver is deterministic and must stay so: no model, no retrieval, no
clock. Ambiguity gets exactly one recorded question (`capability:<key>`) and the
answer selects or excludes the capability with a stated reason.

### 7.3 Registered capabilities (wave 1: scalar inputs only)

| Capability (key) | Answers | Slot (H1 / H2) |
|---|---|---|
| `breakeven` | whether the declared price covers the declared costs | Financial Feasibility / Break-even Analysis |
| `npv` | the value of the declared cash flows at the declared rate | Financial Feasibility / Net Present Value |
| `irr` | the rate the declared cash flows earn | Financial Feasibility / Internal Rate of Return |
| `discounted_payback` | when the declared flows recover the outlay | Financial Feasibility / Discounted Payback |
| `project_metrics` | NPV, PI, MIRR, EAA and payback for one project | Financial Feasibility / Project Metrics |
| `unit_economics` | contribution per unit and acquisition payback | Financial Feasibility / Unit Economics |
| `wacc` | the declared cost of capital | Financial Feasibility / Cost of Capital |
| `return_on_investment` | return on the declared investment | Financial Feasibility / Return on Investment |
| `startup_capital` | the capital the venture needs | Financial Feasibility / Start-up Capital |
| `cash_runway` | how long the declared cash lasts | Financial Feasibility / Cash Runway |
| `market_sizing` | TAM, SAM and SOM from declared population and spend | Market Assessment / Market Size |
| `market_share` | the declared firm's share of the declared market | Market Assessment / Market Share |
| `clv_model` | lifetime value from declared margin and churn | Customer Economics / Customer Lifetime Value |
| `campaign_efficiency` | funnel rates and cost per outcome | Marketing Performance / Campaign Efficiency |
| `elasticity` | price elasticity from two declared points | Market Response / Price Elasticity of Demand |
| `earned_value` | SPI, CPI and estimate at completion | Delivery Status / Earned Value |
| `growth_rate` | growth between two declared values | Economic Context / Growth Rate |
| `inflation_cpi` | inflation between two declared CPIs | Economic Context / Inflation |
| `tax_incidence` | who bears a declared tax | Policy Impact / Tax Incidence |
| `pricing_decision` | a declared-cost price under a declared markup | Pricing / Pricing Decision |
| `cap_table_round` | the post-round ownership split | Ownership / Cap Table |

Every entry is scalar: no table editor is needed to declare it. The **licence**
(`intended_use`) and the **limitation** (`unsupported_use`) are read from
`bp.methods.describe` when the selection is filled, so no capability restates
its method by hand in the product layer.

The appraisal family (`npv`, `irr`, `discounted_payback`, `project_metrics`)
shares one `intent` group, so a question that names two of them selects one (NPV
by priority) and the others stay addable from the plan. They take a declared
series: `decimal_list` renders as one number per line (period 0 first) and is
parsed and validated server-side, so a list can never arrive as prose.

Methods whose inputs include `records` (multi-product break-even, CPM, leveling,
Monte Carlo, regression and friends) are **not registered**: they need a typed
table editor in the chat first, and registering them behind a text box would
break the "no invented input" rule.

Formatting: `CAPABILITY_LINES` holds a bespoke formatter per capability where the
prose matters (break-even today). Everything else uses `_generic_lines`, which
prints the declared inputs and the method's recorded outputs verbatim and says
the figure is not a forecast. Replacing a generic formatter with a bespoke one is
a normal, isolated change: register it under the same key, add its matrix row.

### 7.4 The capability state (what every later step reads)

```
selection: {format, catalogue_version, hash, frameworks[], selected[], not_included[], question}
  selected row: {key, method, label, subject, slot, integration, inputs_required,
                 inputs{name:{desc,required}}, licenses, not,
                 because{rule, quote}}
computations: {key: {ok, method, inputs, result, error}}
```

- `resolve()` runs once in `chat.start`. The rules that fired and the sentence
  they matched are stored, and the selection is hashed, so a paper can be
  re-derived against the catalogue version it used.
- `set_capability()` is the student's add/drop from the plan; a drop is a named
  exclusion, never a silent change.
- `run_capability()` is the only caller of the frozen method for a paper: it
  validates the declared figure through the schema, calls the core, stores the
  result unchanged, and stores a refusal with the core's own message.
- `paper.missing` requires the figures of a selected capability and nothing
  once it is recorded; dropping it removes the requirement.

### 7.5 Test matrix (one row per capability, not one file per method)

| Row | Expectation |
|---|---|
| not selected | brief without the cue → `selected: []`, no computation H1/H2, gate asks no figures |
| selected, valid | selected; figures run through the core; the draft prints the core's numbers; gate passes |
| selected, refused | price ≤ variable cost (break-even) → refusal stored, no figure in the paper, gate blocks |
| selected, no figures | gate requires "the <label> figures"; nothing is estimated |
| ambiguity | cue without quantities → one question; "yes" selects, "no" excludes with the reason |

The reference implementation is break-even: `bp.methods.breakeven` is called from
`chat.run_capability`; the product formats the result but does not recompute it.
A plan block follows the same route: `chat.compute` calls the attached core,
stores the declared inputs and the core result, and `_block_lines` formats them.
Adding a plan block means adding the method to `COMPUTATION_BLOCKS`, declaring
its level and section, and letting the core run it — never writing its formula
in the product layer or the writer.

## 8. Coherence and export gate

`bp.product.paper.check` must pass before a `.docx` is produced. It rejects:

- a level jump or a level 2 heading before a level 1;
- a missing Conclusion or reference list;
- instructional/template text;
- missing implications or missing SWOT strengths/weaknesses.

The export route returns `409` with `missing` when the gate fails. The UI hides
the Download button and names what is missing.

Coherence expectations for every paper:

- the Introduction states the decision and the thesis;
- every dimension has evidence or a named gap;
- the Discussion integrates the frameworks instead of repeating them;
- the Conclusion answers the thesis and introduces no new evidence;
- every reference is cited in the body;
- combined papers name the origin of each mapped item.

## 9. Sources and search order

- Academic: OpenAlex, Semantic Scholar, DOAJ; Crossref only as metadata.
- Web order: OpenGo (headless OpenCode, opt-in because it is slow), DeepSeek
  Search, Brave, Firecrawl.
- Only the curated registry may return a web source.
- Search results are precision-ranked (relevance, title cue, country anchor,
  source tier, recency, credibility) before placement.

## 10. Model configuration

- Default model for model-assisted prose: `deepseek-v4.1-flash`.
- `PROSE_MODEL` overrides the prose model without changing the search model.
- DeepSeek Pro is available for a final polish; it is slower and uses the Go
  allowance faster.
- Regardless of model, the same validation applies: no new number, citation,
  link, heading or template text.

## 11. Adding a new model or opening a new chat

A new model or session should:

1. Read this manual and `docs/HANDOFF.md`.
2. Run the conductor tests before changing code.
3. Inspect `bp/product/chat.py`, `bp/product/paper.py` and
   `bp/product/prose.py` before touching the paper flow.
4. Keep the framework/computation registry as the single source of truth.
5. Never fix a missing framework by editing the sample builder or the DOCX
   renderer.
6. Add a sample only after the conductor can produce the same structure.
7. Update `CHANGELOG.md`, `DECISIONS.md`, `HOME.md`, `HANDOFF.md` and
   `CONTRIBUTORS.md` digits with the build.

## 12. Reference files

- `src/bp/product/chat.py` — conductor, framework registry, questions, draft.
- `src/bp/product/paper.py` — levels, paragraph joining, export gate.
- `src/bp/product/prose.py` — model proposal and validation.
- `src/bp/product/docx.py` — H1/H2/H3 rendering.
- `src/bp/product/writing.py` — citations and references.
- `src/bp/product/sources.py` — academic and web retrieval.
- `src/bp/product/api.py` — routes.
- `src/bp/product/documents.py` — PDF, Word `.docx`, TXT and image readers.
- `web/index.html` — Chat panel, business-plan builder and framework selector.
- `tests/test_chat.py`, `tests/test_prose.py`, `tests/test_writing.py` — the
  conductor contract.
- `tests/test_business_plan_profile.py` — the plan profile, brief readers and
  export gate.
- `samples/` — the current APA/Harvard examples, including the four generated by `scripts/build_conductor_samples.py` (see `docs/SAMPLE_PAPERS.md`).

## 13. Current limits

- Eight single frameworks and two combinations: PESTEL + SWOT, and Five Forces + Break-even. Any other pairing of two frameworks is refused rather than approximated.
- A **paper carries a computation only when the brief needs one.** The catalogue
  in `bp/product/capabilities.py` resolves the brief at `chat.start`; a
  framework-only brief selects nothing and has no computation section. Only
  break-even is registered today, so a PESTEL/SWOT/Five Forces/Value Chain/
  Ansoff/VRIO paper can carry a break-even analysis
  (`POST /api/cases/chat/{id}/computation`, validated by the frozen
  `breakeven` method). Registering the next capability is the §7 checklist, not
  a new branch in the draft.
- Framework auto-completion is enabled for Porter's Five Forces only; other worksheets are still manual.
- Other frameworks are refused, not silently replaced.
- VRIO and Break-even retrieve **no external evidence**: VRIO records the student's resources and four judgments, and Break-even runs the declared figures. Their papers say so.
- Value Chain and Ansoff dimensions are supported by retrieved evidence placed by keyword; they do not collect internal cost data or benchmark activities against rivals.
- The business plan is the only paper profile; it is not a framework and cannot be combined with one.
- Plan-level methods use annual periods, one product and one currency; they do not forecast demand, apply a jurisdiction's tax law or model disposals.
- Open composition changes which optional sections appear, not the facts, figures or the export gate.
- OpenGo search is opt-in and slow; DeepSeek Search is the fast default.
- Model prose is linking prose, not a full rewrite.
- APA and Harvard sample papers for the four frameworks added in B-151 are generated by `scripts/build_conductor_samples.py` (see `docs/SAMPLE_PAPERS.md`); PESTEL and SWOT keep their earlier samples.
- The title page byline is the student's own list of lines and is omitted when empty; the product does not invent a name or an institution.
- The sample papers demonstrate the target; the live conductor can still show
  named gaps when the sources are thin.
