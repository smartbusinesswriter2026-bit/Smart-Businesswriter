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
| Frameworks | PESTEL, SWOT, PESTEL + SWOT, Five Forces, Five Forces + Break-even |
| Computation | Break-even only, through the frozen core |
| Output | APA 7 or Harvard `.docx`, hierarchy enforced |
| Evidence | Curated academic databases and vetted web domains |
| Model prose | Optional, proposal only, DeepSeek V4.1 Flash by default |

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
8. Add the framework to the Chat selector.
9. Add tests: questions, plan, research with mocks, hierarchy, draft, export.
10. Add one APA and one Harvard sample built from the same structure.
11. Record the decision and changelog entry.

Do not add a framework by hard-coding its headings in the writer. The writer
only renders what the chat plan supplies.

## 6. Adding a computation (checklist)

1. Confirm the method exists in the frozen core and has a declared input schema.
2. Add the numeric questions to the framework's question bank.
3. Call the frozen function. Do not copy the formula into the product layer.
4. Record the inputs and the core result in the draft, for audit.
5. Render one H1 feasibility section and one H2 method section.
6. State the assumptions in Limitations: declared inputs, no demand forecast,
   no tax, financing or synergies unless the core method supports them.
7. Test a valid case and a refused case (for example price ≤ variable cost).
8. Never describe the computed result as a forecast or a recommendation.

Break-even is the reference implementation: `bp.methods.breakeven` is called
from `bp/product/chat.py`; the product formats the result but does not recompute
it.

## 7. Coherence and export gate

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

## 8. Sources and search order

- Academic: OpenAlex, Semantic Scholar, DOAJ; Crossref only as metadata.
- Web order: OpenGo (headless OpenCode, opt-in because it is slow), DeepSeek
  Search, Brave, Firecrawl.
- Only the curated registry may return a web source.
- Search results are precision-ranked (relevance, title cue, country anchor,
  source tier, recency, credibility) before placement.

## 9. Model configuration

- Default model for model-assisted prose: `deepseek-v4.1-flash`.
- `PROSE_MODEL` overrides the prose model without changing the search model.
- DeepSeek Pro is available for a final polish; it is slower and uses the Go
  allowance faster.
- Regardless of model, the same validation applies: no new number, citation,
  link, heading or template text.

## 10. Adding a new model or opening a new chat

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

## 11. Reference files

- `src/bp/product/chat.py` — conductor, framework registry, questions, draft.
- `src/bp/product/paper.py` — levels, paragraph joining, export gate.
- `src/bp/product/prose.py` — model proposal and validation.
- `src/bp/product/docx.py` — H1/H2/H3 rendering.
- `src/bp/product/writing.py` — citations and references.
- `src/bp/product/sources.py` — academic and web retrieval.
- `src/bp/product/api.py` — routes.
- `web/index.html` — Chat panel and framework selector.
- `tests/test_chat.py`, `tests/test_prose.py`, `tests/test_writing.py` — the
  conductor contract.
- `samples/` — the current APA/Harvard examples.

## 12. Current limits

- Five Forces + Break-even is the only non-PESTEL/SWOT combination.
- Other frameworks are refused, not silently replaced.
- Break-even is the only computation wired into chat.
- OpenGo search is opt-in and slow; DeepSeek Search is the fast default.
- Model prose is linking prose, not a full rewrite.
- The sample papers demonstrate the target; the live conductor can still show
  named gaps when the sources are thin.
