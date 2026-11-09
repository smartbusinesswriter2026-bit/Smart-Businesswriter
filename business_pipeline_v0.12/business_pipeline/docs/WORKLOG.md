## 2026-11-10 - [design] The research ledger is on the page

**Ask.** The research layer of the last increment stored a ledger per
dimension: what was cited for each part, and why every other candidate was
refused. It was in the payload and nowhere else, so the student could not see
it.

**Did.** `web/index.html` gained a collapsible **Research ledger** panel. It
sits above the review of a framework completion and under the evidence of a
chat paper. One row per dimension: the part's name, a badge (`cited`, `needs an
official or data source`, `background only`, `gap`) and a count of what was
cited, refused and kept as background. Expanding the row shows the cited items
with their citation, the framework's own background paragraph marked *not
cited*, and every refused candidate with the reason it was refused.

**The boundary that matters.** The panel reads the record the server stored. It
fetches nothing, decides nothing and invents no source. The reasons it prints
are the closed set the server uses, so the page and the run always say the same
thing. No new route and no change in `src/bp/**` beyond the build marker.

**Next.** The ledger is now visible in the review and in the chat evidence step.

## 2026-11-10 - [computation] Research is framework-aware, and every dimension has a ledger

**Ask.** The research layer returned generic pages: a PESTEL political
dimension and a Five Forces rivalry dimension were searched the same way, so a
correct source for one dimension was often not a source for it at all. The
owner asked for research customised to the pipeline's frameworks, not a general
search engine.

**Did.** A profile may now declare a `research` block: the topic each dimension
belongs to, the source-tier order it prefers, a query budget, the research needs
it serves and the tiers that make it citable. `bp.product.research_contract`
holds the closed vocabularies and the ledger; `retrieval.retrieve` consumes the
block (topic routing, tier ranking, query budget) and returns a ledger with the
reason every candidate was refused. `completion` and `chat` call the same block
and apply the same grading rule, so the same brief still returns the same
evidence on both surfaces. PESTEL is the first slice, Five Forces the second,
the business plan the third, the quality modules the fourth, the
portfolio/canvas modules the fifth, the strategy/management batch the sixth,
the marketing batch the seventh, the people/change batch the eighth, the
project/operations batch the ninth and the leadership/culture/ethics batch the
tenth; the plan is a profile, so its block lives beside its four evidence
dimensions in `chat.PLAN_RESEARCH`.

**The boundary that matters.** The source tier (official/data/research/news) and
the audit tier (A/B/C/D) are different vocabularies; the source tier is kept
beside the audit tier as `source_tier`, so a C-grade source is never mistaken
for a news source. A known tier outside the required list becomes background and
the dimension is a named gap; an item with no source tier is kept, which is why
the existing behaviour is unchanged. No model call, no new source and no
computation changed.

**Next.** Five Forces, the business-plan evidence blocks, the quality modules,
the portfolio/canvas modules, then the remaining profiles, one slice at a time.

## 2026-11-10 - [design] The Relevance Research Agent checks itself, and the framework question is settled

**Ask.** Build the RRA end to end, then use it to find the capability gaps the
system may have overlooked.  The research phase had left one question open —
the framework question — and three dates unverified.

**Did.** Three things.

**(1) The chain.**  The model-driven stages went in: URL discovery (a better
search query, never a URL the search did not return), reading (the passage
that matters, checked verbatim by code — a paraphrase is discarded), and the
gap spec (each field validated; an invalid lane, priority, effort or category
dropped).  Per-stage models (D-4) let those three stages read and write with
different models, while the two stages that *decide* — the skeptic and the
evaluator — stay deterministic and never call a model.

**(2) The control set.**  `qa/relevance/controls.json` holds what the system
**already has**, and every sweep runs it against what it read.  A framework
control holds only when its name appears in an **evidence excerpt**; a
capability or retrieval control holds on the catalogue.  Below 75 % held, the
measurement **failed and no gap is promoted** — the candidates are withheld
and the run says why.

This exists because the research phase measured the same thing the hard way.
Reading the sampling frame's core-course lists produced **zero** hits for
every framework — *including the seven the system already has*.  Two of the
three methods tried failed exactly that way and nothing reported it, because
nothing was carrying a control.

**(3) The findings.**  `docs/RRA_FINDINGS_PHASE1.md`, from the primary
documents: the AACSB 2026 Global Standards are **effective 1 July 2026** (the
first sweep's "ratified 14 Apr 2026" was T2/T3 and is withdrawn), 4.3 is
**Digital Agility** with AI named inside it, IFRS 18 is effective for annual
periods beginning on or after **1 January 2027**, the revised ESRS were
**adopted 3 July 2026**, and HBS's own curriculum page names **Data Science &
AI for Leaders** as required — that claim moves from T2/T3 to T1.

The framework question is settled, and the way it was settled matters: the
**accreditor names no framework at all**, and the core-course lists name
**subjects**.  The evidence lives in the **course catalogues**.  Balanced
Scorecard, McKinsey 7S and Three Horizons are taught at two or more
independent schools — the same standing as the frameworks the system already
has.

**Measured.**  75 searches, 176 school pages read.  The controls held at the
mentioned level (5 of 7) and one held at the taught level, so the candidates
were read *against the controls* rather than against zero: Balanced Scorecard
is taught at 3 schools, Business Model Canvas — already in the catalogue — at
4.

**Bugs found on the way.**  The `llm` import pointed one level too shallow
(`bp.product` instead of `bp`), so every model call raised; the domain match
rejected a registry subdomain against its allowlist host, so 24 of 25 schools
were never searched; and the RRA had no search credentials of its own, because
the product's web layer expects them exported.

**Tests.**  120 RRA tests in seven `unittest.TestCase` files, so the canonical
`python -m unittest discover -s tests` runs them and the documented count
sees them.

## 2026-11-09 - [design] The Relevance Research Agent: the pipeline looks outward

**Ask.** The repair loop detects breakage and the growth loop creates
capability, but neither looks outward. The owner wanted a system that fills
the capability gaps it may have overlooked, that stays relevant, and that does
not become obsolete.

**Did.** A new product-backend package, `src/bp/product/relevance/`, with
eight sequential stages and a deterministic gate on each: scope, scout,
discover, read, map, skeptic, design, evaluate, gate. The registries the owner
edits live in `qa/relevance/`: the sampling frame, the source allowlist, the
taxonomy, the back-test set and a catalogue snapshot with a drift check.

**The boundary that matters.** The model proposes; code decides. It may draft
a search query, pick the passage that matters, and draft the spec fields. A URL
the search did not return is never read, an excerpt that is not a literal
substring of the fetched page is discarded, and an invalid lane, priority,
effort or category is dropped. There is no apply endpoint: a gap leaves the
queue only through a recorded human decision, and an approved gap reaches the
growth loop through `ops_log.log_finding(rule="capability_gap", source=
"relevance")`, so it appears in the Validation panel under the filter that
already existed.

**Measured.** The back-test seeds twelve known gaps and eleven present items.
On a live run over a T1 source: recall 12/12, 0 false flags, PASS against the
owner's threshold of 8 of 10 with 0 false flags. Two of the twelve are parked
items, and recognising them as parked counts as a correct identification
rather than a proposal to build them.

**Where it stops.** No file in the package lives in `src/bp/**`; no
frozen-core entry, computation or paper-path import changed. The write path is
confined to `state/relevance/` and `qa/relevance/`. Wikipedia and its class are
blocked at fetch time. `BP_RELEVANCE_AUTOSTART` defaults to 0.

**Tests.** 106 new tests in six files, written as `unittest.TestCase` so the
canonical `python -m unittest discover -s tests` runs them and the documented
suite count sees them. Suite 4834.

## 2026-11-09 - [product] Chart window: frameworks and a project timeline

**Ask.** Business students make more than bar and line charts: SWOT, BCG, Ansoff,
stakeholder maps, org charts, process flowcharts, business model canvases, sales
funnels, customer journeys, WBS and Gantt timelines. The Chart window only
offered the seven numeric chart kinds.

**Did.**

- **Diagram source.** `visuals.py` accepts `source.kind = "diagram"` and
  validates a `bp-diagram/1` spec with the existing `diagrams.py` renderer. The
  visual stores, previews, exports (SVG/PNG/Word/PowerPoint/PDF) and combines on
  a figure sheet like any other visual.
- **Gantt source.** `source.kind = "gantt"` builds a project timeline from
  declared task names and day numbers or ISO dates. The date text is a stored
  display artifact; the bars use day offsets. A task that ends before it starts
  is refused.
- **The window.** The Chart window gains "A framework or diagram" with process,
  matrix2x2, pyramid, funnel, tree, board, journey and WBS, plus "A project
  timeline". Each has a live "I understood" report and a try-an-example button.
- **The rule.** Diagram labels stay text-only (write "Marketing mix", not "4Ps");
  a digit is refused with that hint.
- **Statistical charts.** The reader also accepts area, scatter (`label, x, y`)
  and candlestick (`label, open, high, low, close`) lines. A scatter needs an x
  on every point; a candlestick refuses a high below its low or an open/close
  outside the high-low range. `charts.py` gained the three renderers, and the
  window's kind list and "I read" table show x and the four prices.

**Measured.** `tests/test_product_visuals.py` 42 (diagram build/list/preview/export,
the digit refusal, Gantt build/export, the end-before-start refusal, and the
area/scatter/candlestick builds and refusals), `test_visual_input.py` 43,
`test_product_charts.py` 23. Live browser check of the SWOT 2x2, the business
model board and the dated Gantt.

## 2026-11-09 - [product] The Portfolio Lab carries dated screenshot evidence

**Ask.** A professor wants proof that a student really looked up the price on the date they recorded,
not only a number the app says is sourced. The screenshot had to live inside the pipeline, be
convenient, and never block a snapshot.

**Did.**

- `src/bp/product/evidence_capture.py` (new): `quote_url(symbol)` and `capture(url)`. The capture is
  an optional Playwright headless-Chromium screenshot, restricted to an allowlist of public https
  hosts (no SSRF), with a plain `EvidenceCaptureUnavailable` when the browser is missing or the page
  fails. `requirements-optional.txt` documents `pip install playwright` +
  `playwright install chromium`.
- `portfolios.save_evidence` stores PNG/JPEG/PDF (≤2 MB) under `evidence/<date>/` with SHA-256 and
  capture time; `save_snapshot` validates referenced evidence exists and its hash still matches, so a
  swapped file is refused. Routes: `POST /api/portfolios/{id}/evidence` (base64) and
  `POST /api/portfolios/{id}/evidence/capture` (symbol).
- Page: **Open quote page ↗** and **Capture** per holding on *Prices and snapshot*; an
  **Evidence (optional)** card with attach/remove; the snapshot summary names the evidence count or
  the named gap.
- `portfolio_docx.render` gains a **Price evidence** table and embeds image evidence; no evidence
  prints as a named gap. `docx.render_note` learned optional inline images.
- Clutter: the empty *Your books* card, the create-book explainer and the before-you-buy explainer
  are removed; *Learn by example* is collapsed and its kicker is dark green.
- Manual: `docs/PORTFOLIO_LAB_STUDENT_GUIDE.md` gains the two evidence paths, a professor-verification
  bullet, a troubleshooting row and the glossary term. Tests: `test_product_portfolios.py` (19; the
  evidence route and a swapped-hash refusal), `test_portfolio_student_guide.py`,
  `test_product_instruments.py`.

## 2026-11-09 - [product] The feasibility study gets its deck, and the product boundary declares its optional browser

**Ask.** Fix the one boundary failure the full suite named, then take the next step.

**Did.**

- `chat._feasibility_deck` (new): a five-slide deck from the three-table study (title,
  executive-summary claim, market and demand, investment and operating cost, returns).
  It names the same cells the paper prints, carries the section prose as speaker notes,
  and computes nothing. `pptx_bytes`/`pdf_bytes` route the study to it;
  `paper_bytes(state, "bundle")` adds `<slug>-deck.pptx` beside the docx, workbook and PDF.
- `tests/test_product_boundary.py`: `playwright` is now a declared optional dependency of
  `evidence_capture.py`, exactly as the optional document readers and renderers are
  declared. That module already imports the browser lazily inside `capture` and raises a
  named gap when it is absent, so the product still imports with the standard library
  alone. No check was removed, loosened or skipped.

**Proof.** `tests/test_silent_home.py` `SilentFeasibilityTest` (6: detection, three tables,
frozen values, the workbook and deck in one ZIP, the deck's tables, a revision that keeps
the tables), `tests/test_product_boundary.py` (8, green); the lane files (81) and the
profile/figure/chart/deck/export files (112) green. A live deck render is five pages and
carries `Declared demand`, `Total investment`, `Break-even volume` and `Margin of safety`.

**Open.** No proforma, sensitivity or payback in the three-table route; the deck's only
chart is the project Gantt.

## 2026-11-09 - [product] The project plan travels as a deck, feasibility gets three tables, and the door starts its document

**Ask.** Both follow-ups: a PowerPoint for the project plan's chart, and the simplified
three-table feasibility route. Also: the Project management shelf already has a
**Build the complete project plan** door and it must actually start that lane.

**Did.**

- `chat._project_deck` (new) builds the paper as a claim deck: title, executive-summary
  sentence, the **Schedule chart** slide (stored Gantt PNG), then WBS, schedule, cost,
  RACI and risk table slides. Claims are the paper's own first sentences, tables name the
  same figure ids, speaker notes carry the section prose. `pptx_bytes`/`pdf_bytes` route a
  project plan to it; the one ZIP now also carries `<slug>-deck.pptx`.
- `src/bp/product/feasibility_reader.py` (new): reads a labelled project, a market table
  (`Item | Value`) and a cost table (`Item | Amount`), classifying rows by their own labels
  and filling nothing.
- `src/bp/product/feasibility_plan.py` (new): validates, sums the declared investment, runs
  the **frozen `breakeven`** with the declared demand, and builds the market, cost and
  returns tables. `feasibility_workbook.py` (new) writes Project/Market/Costs/Returns.
- `chat._read_feasibility_record` / `_draft_feasibility_simple`: a table-shaped
  feasibility brief takes the three-table route, skips research and skips the profile
  writer; a narrative brief keeps the guide route. `paper._plan_missing` gates the simple
  route on its own record.
- Web: `startPlan` records the chosen document, `startChat` posts `profile` and `mode` for
  that run and clears the choice; the door now reaches the lane even when the brief does
  not name it. `project_reader` takes a short first line as the title when no label does.

**Proof.** `tests/test_feasibility_reader.py` (5), `tests/test_feasibility_plan.py` (6),
`tests/test_project_reader.py` (11), `tests/test_silent_home.py` (project 8, feasibility 5),
`tests/test_document_profile_doors.py`; 59 lane tests green, profile/figure/chart/deck/export
files 112 green. Live 8021: the Project management door's **Start the project plan** opened
Home, a brief with no "project plan" words produced the project paper (title "Kitchen
project, opening in June"), the ZIP held docx + workbook + pdf + an 8-slide deck with
`ppt/media/image1.png`; the feasibility brief produced Market/Financial/Returns tables with
no gap line, and its ZIP held docx + workbook (Project, Market, Costs, Returns) + pdf.

**Open.** The feasibility route has no proforma/sensitivity/payback; the deck has no
animations; the door is one-shot by design.

## 2026-11-09 - [product] A project plan is one silent paper from the brief's tables, charted in Word and PDF

**Ask.** Home should finish a project-management brief the way it finishes a
business plan: no card, no questions, one paper. The paper must carry the WBS,
schedule, cost, RACI and risk tables, download once, and put the schedule chart in
the document the reader gets.

**Did.**

- `src/bp/product/project_reader.py` (new): reads the charter labels and classifies
  the brief's tables from their own column names (WBS, activities, resources, RACI
  direct or matrix, risks). It fills only named columns or labelled lines; the only
  derivations are position ids, a dotted parent that exists, and activity→WBS by id
  or name. `tests/test_project_reader.py` (10).
- `chat._detect_profile` recognises a project plan / project-management plan / work
  breakdown structure / WBS / titled WBS table (proposal cues first).
  `chat._read_project_record` stores `state["project"]`, and the project lane skips
  `research()`: the record is the source, so there is no web evidence to fetch.
- `_draft_project_plan` builds the tables as `table` figures on their sections;
  `paper_view` appends them as `| ... |` lines that bypass the missing-input filter,
  so a missing cell prints as declared. `paper.table_grid`/`table_lines` is the one
  reader used by the pane, Word and PDF. No Gaps section, no checks summary.
- `chat._schedule_figure` draws the Gantt from the stored early start/finish/float/
  critical values, with digit-free labels; it is a separate level-2 **Schedule chart**
  block because the Schedule section already carries its table. Word embeds the PNG,
  PDF the inline SVG, the browser pane nothing.
- `paper_bytes(state, "bundle")` returns one ZIP: the paper's `.docx`, its
  `-workbook.xlsx` and, with Chrome, the `.pdf`. `project_workbook.py` (new) writes
  Charter, WBS, Schedule, Cost, RACI and Risks sheets.
- `revise` records `{paper, outline}` per history entry; `_rebuild_outline` reattaches
  each section's stored figure and strips model-echoed table rows; `undo` restores
  the outline (older plain-paper entries still undo).
- Docs: `HOME_CHAT_ORCHESTRATION_MANUAL.md` §21.11, `HANDOFF.md`, `KNOWN_LIMITATIONS.md`,
  `DECISIONS.md` B-252.

**Proof.** `tests/test_project_reader.py` (10), `tests/test_project_plan.py` (14),
`tests/test_silent_home.py` `SilentProjectPlanTest` (8); the document-profile,
figure and chart files (75) green; full suite 4618 + 7 skipped, with one unrelated
trial-balance tile failure in another lane. Live at 8021: the WBS brief returns the
paper with nine tables and no Gaps; one Download saves
`project-plan-the-riverside-community-kitchen.zip` (160,200 bytes) holding the docx
(nine tables, `word/media/figure5.png`, "Project schedule"), the workbook with the six
sheets, and the PDF.

**Open.** PowerPoint for the chart, calendar dates and resource levelling, and the
simplified three-table feasibility route (deferred).

## 2026-11-10 - [framework-writing] FMEA RPN and Five-S score in the frozen core

**Ask.** Close the "declared, not recomputed" limit on the quality modules.

**Did.** Added `fmea_rpn` (S x O x D) and `five_s_score` (sum over the declared
maximum) to `src/bp/methods.py`, with their profile/tests/caveats/templates; the
frozen fixture, catalogue and calc-inputs were regenerated (218 methods).
`quality_reader.py` reads the FMEA worksheet, Five-S scorecard and PDCA measure
table from the brief. `framework_calc.fmea`/`five_s` call the core, rank RPN into
a Pareto and the S scores into a bar, and `completion.complete` attaches the
calculation and chart to the paper.

**Verified.** Live FMEA: Seal leaks 7/4/3 -> 84.00 and Wrong part 4/6/2 -> 48.00,
Pareto cumulative 84/132. `test_quality_reader.py` (4), `test_framework_calc.py`
(11), `test_quality_writing.py` (7), method inventory/contracts, frozen fixture
and boundary tests green.

**Left.** PDCA measures are read but not yet charted from a pasted table; the
five S categories are matched by name (a renamed category is a named gap).

## 2026-11-09 - [framework-writing] Quality modules and chart tie-up

**Ask.** The owner supplied the quality guideline (RCA, FMEA, PDCA, Five-S) and
asked that frameworks tie up with the charts already created, across frameworks.

**Did.** Added `framework_figures.py`, an adapter over `visuals`, `charts`,
`diagrams` and `figures` (bar, line, pie, pareto, waterfall, stacked bar, tree);
a generic `tables` contract for a module's own worksheet; writing modules for
RCA, FMEA, PDCA and Five-S, each with a `tables` and a `chart` part; BCG and GE
charts from the frozen calculation rows. The chart values are only what the
record holds, the figure is stamped, and Word embeds the PNG or falls back to the
value table.

**Verified.** `test_framework_figures.py` (6), `test_quality_writing.py` (4),
`test_bcg_ge_writing.py` (5), the operations acceptance suite, and 247 quality
and framework tests green.

**Left.** The RPN and Five-S scores are declared in the module record and audited
by the paper; a frozen `fmea_rpn` / `five_s_score` method is the next computation
slice. The model supplies the FMEA/scorecard/cycle-log tables; a deterministic
reader for those tables is the next refinement.

## 2026-11-09 - [framework-writing] Portfolio, growth and canvas modules

**Ask.** Two further owner instruction sets: portfolio/growth (Ansoff, BCG,
GE-McKinsey, ERRC) and canvas (BMC, Lean, VPC). They add H, shown calculations
and an assumption register.

**Did.** Added H to the claim types with a required test for every H driver; the
assumption register; the standard canvas grids in `matrix.LAYOUTS`; writing
modules for Ansoff, ERRC, BMC, Lean and VPC; `portfolio_reader` (the brief's unit
table) and `framework_calc` (calls the frozen `market_share`, `growth_rate` and
`weighted_summary`, then classifies the BCG quadrant / GE zone). BCG and GE
writing modules read the calculation record; the model never computes. Corrected
the units for all seven profiles; Ansoff and ERRC are draftable.

**Verified.** `test_portfolio_canvas_writing` (6), `test_canvas_writing` (3),
`test_portfolio_reader` (4), `test_framework_calc` (6), `test_bcg_ge_writing`
(4), the four existing profile tests updated to the new units, and 379 framework
and product tests green.

**Left.** GE-McKinsey's factor/weight/score table is not parsed from a brief yet;
the adapter accepts the structured axes and the paper names the gap when they
are absent. The GE sensitivity test is stated in the module but not computed.

## 2026-11-09 - [framework-writing] The three Porter frameworks are written to the owner's guideline

**Ask.** The owner supplied a writing guideline for competitive-position frameworks
(Five Forces, Generic Strategies, Porter's Diamond) and asked the pipeline to write
the frameworks properly: facts, inferences and judgments separated; every rating
with drivers, trend, profitability impact and confidence; the module's output
shape; and an evidence audit.

**Did.**

- `src/bp/product/framework_writing.py` (new) holds the rules and formatters:
  source tier A-D, recency (3-year window), strength by a declared rule, stable
  `S1` source IDs, the reading contract and validator, the scope statement, the
  summary table, the reading paragraph, the audit rows/checks/verdict and the
  confirmation state.
- Five Forces, Generic Strategies and Diamond declare a `writing` module in
  `framework_profiles.py`: section order, headings, scale (intensity/fit/
  condition), driver checklists, summary/audit columns and the mid-call directive.
- `completion.py` asks for the structured reading in the same per-dimension model
  call, validates it, and builds the module sections; the deterministic draft
  prints "not rated" and stays the fallback.
- The two units are corrected: Generic Strategies = firm/business unit + market;
  Diamond = nation/region + industry (`Global` refused).
- `POST /api/cases/frameworks/readings` records confirm/override/drop; the review
  page carries the control, and the paper prints the status.
- `docx.py` renders a section table, and `paper.check` scans it for template text.

**Verified.** `tests/test_framework_writing.py` (33), `test_five_forces_writing.py`
(14), `test_generic_strategies_writing.py` (9), `test_porters_diamond_writing.py`
(8), `test_framework_readings.py` (9); the full suite is reported below. Existing
framework, conductor, PESTEL, paper-document and drafting tests remain green.

**Left.** The reading is only as good as the accepted items: a thin run prints
"not rated" and the audit says the evidence is insufficient. The tier/recency/
strength rule is a product convention, printed in the audit note; it is not a
claim the source makes.

## 2026-11-09 - [product] Bulk case reconciliation: method_contract 506 -> 0 recurrences

**Ask.** Close the `method_contract` class (506 recurrences) that the concurrent core changes
left behind, without spending model tokens.

**Did.**

- **Re-seeded the 246 preset cases** from the current frozen methods (`POST
  /api/ops/cases/seed` with overwrite), so every preset expectation tracks the method it
  tests.
- **Reconciled the authored/uploaded cases** token-free: for each case, the method is run on
  the case's own inputs and the expected result is refreshed — a renamed key is mapped when
  the value agrees, a scalar output (`value` -> `npv`) is mapped to the method's output key,
  and a key the method no longer emits is dropped.  The stale cases (npv, elasticity,
  equilibrium, growth, nationalincome, ...) now match the current outputs.
- **Inconsistent case inputs are now invalid, not failed.** `case_invariants` prefixes its
  messages `invalid input:`; `case_runner` marks a case whose only problems are invariants
  as `invalid`, closes its open error as `input.unbalanced`, and spends no model call.  The
  nine accounting/ratios uploads whose figures were all 15.0 close this way.
- **Detection accuracy:** `input too large` is its own `input.too_large` cause (it used to be
  mis-read as `parser_shape` because the message says "could not read this as a journal"),
  and state errors ("Confirm the plan before retrieving sources.") map to `input.validation`.
- **Recorded the fix** with `ops_log.log_cause_fix` for `pipeline.case_expectation` and
  `pipeline.method_contract` (artifact `case_expectation`), with a note that a future method
  output change must update its cases in the same commit.

**Measured.** Cause ledger: `fixed_pct` 75% (3 fixed, 0 recurring, 0 unfixed, one legacy
`pipeline.unknown` closed as an instance); open errors 0.

## 2026-11-09 - [product] Multi-agent verifier, paper contracts, capability scaffolds

**Ask.** Make the fix robust for any issue: detect accurately, fix structurally, learn from
the mistake, and grow capabilities from out-of-scope topics (semi-autonomous, human review).

**Did.**

- **`src/bp/product/verifier.py`**: an independent verifier.  The solver's replay is a
  proposal; a **different model** that sees only the problem and the answer must agree before
  a fix is called verified.  Tiers run beam-free -> minimax-flash -> deepseek-v4-pro (env
  `BP_VERIFY_MODEL_TIER1/2/3`) and stop when two agree; no verifier answer is an instance
  close, not a durable fix.
- **`auto_resolve`**: wired the verifier into the replay loop; a rejected answer keeps the
  error open and tries the escalation model.
- **`chat_heal`**: a solved problem is now an error when the verifier rejects it, so a wrong
  answer cannot pass its own check.
- **Paper contracts**: a case can declare `contract.sections`; `case_runner._check` fails a
  paper that does not carry them.  New seeded/uploaded cases get the standard contract.
- **Capability gaps**: `chat.start`'s `not_supported` path (non-routing refusals) and the
  case runner's "no method" path write a `capability_gap` finding; the Validation source
  filter now offers `capability_gap`, and a gap row has a **Scaffold** button.
- **`src/bp/product/scaffold.py`**: writes five PROVISIONAL files into
  `qa/scaffolds/<subject>/<tile>/` (method stub, capability entry, preset, test sketch,
  README).  It calls `error_db.growth_brief` first and puts the known mistakes and the
  local-first research order at the top; nothing is wired into the running system.
- **Routes**: `POST /api/ops/findings/scaffold`.
- **Tests**: `tests/test_verifier.py`, `tests/test_scaffold.py`, contract tests in
  `tests/test_product_case_loop.py`.

**Measured.** A verifier rejection keeps the error open; an agreement writes the
golden_case artifact; no verifier is an instance close.  A capability_gap finding shows the
Scaffold button, and clicking it writes the five files (verified in the browser).

## 2026-11-09 - [product] Chart window: one reader, a visible field, and an honest report

**Ask.** The Chart window asked students to know a `label, value` format; a bare
number was refused, a space separator was refused, and the caret could be painted
outside the box at a fractional Windows zoom. The owner asked for a forgiving
input, an instruction-file upload that says what it understood, a guard against
invalid figures, and a chart window a student can use without learning a format.

**Did.**

- **One reader.** `src/bp/product/visual_input.py` reads lines and tables. It
  accepts comma/tab/semicolon/colon/pipe/spaces, currency, thousands, decimal
  commas, parentheses negatives and `%`; it auto-labels a bare number and marks
  it; it skips a header with its line number; it refuses two values without a
  label; a pareto needs a supplied running total and is never summed.
- **One route.** `POST /api/cases/visuals/read` returns the points, columns,
  skipped lines, warnings, needs and a "what I will do" plan. It reads
  CSV/TSV/XLSX/XLSM/TXT through the frozen `bp.ingest` and PDF/DOCX/DOCM/TXT/MD
  through `documents`; Word tables are read structurally, a headerless file keeps
  its first row, and a scanned PDF or a file with no figures is refused.
- **Provenance.** `visuals._declared(points, source_file)` labels a file-backed
  series "Figures read from <file>", keeps the name/hash/columns and records
  "edited after reading" when the student changed the text.
- **The window.** Upload data, upload instruction, try an example, sample files,
  a live "I understood this" table, a plan and column dropdowns.
- **The caret.** The chart fields get a visible white box; the global `zoom:.9`
  is removed and the rail heights use `100vh - 56px`.

**Measured.** `tests/test_visual_input.py` 29; `tests/test_product_visuals.py`
31; the inline script parses and the static snapshot matches. The live workbench
was checked in the browser: typed separators, the example, a CSV upload, a DOCX
instruction upload, a blocked no-figures input, a calculation and a created
visual. The caret now sits inside the field.

## 2026-11-09 - [product] Capability fallback, stale cases refreshed, and the error database

**Ask.** Close the remaining open errors, then create a database of mistakes and fixes so
the growth loop starts with the learning.

**Did.**

- **Capability fallback**: `run_capability` uses the selection row when
  `capabilities.entry(key)` raises, so a tile whose method is in the frozen core but has no
  catalogue entry runs instead of refusing with "Unknown capability".  The twelve cases
  (posthoc, paired, onesample, multicomp, logit, factorial, portfolioval, portfolioperf, scv,
  salesvar, accounts, abc) now pass.
- **Stale case expectations refreshed**: renamed/removed method outputs were reconciled in
  the unemployment, equilibrium and elasticity cases (`participation_rate` ->
  `labour_force_participation_rate`, `percentage_change_*` -> `pct_change_*`,
  `price_elasticity_of_demand` -> `absolute_elasticity`, `revenue_N` -> `total_revenue_N`;
  a removed key is dropped).  `expected_refreshed_at` marks the change.
- **`_same_number`** accepts a display-rounded expectation (0.0713 for 0.0712986...).
- **`src/bp/product/error_db.py`** and **`qa/errors/error_registry.jsonl`**: the mistake
  database.  The registry is the reviewable source (symptom, trigger, fix, artifact, files,
  tests, avoid); the SQLite cache at `state/error_db.sqlite3` adds the live error log, the
  cause ledger and the golden cases.  `growth_brief(subject, tile, text)` is what the growth
  loop reads before it scaffolds a capability.  Routes `/api/ops/error-db`,
  `/api/ops/error-db/search`, `/api/ops/error-db/rebuild`; the Tools tab has the card.
- **`docs/CAUSE_LOOP.md`** documents the database.

**Measured.** Open errors 24 -> 0.  The database holds 12 lessons, 290 error records,
4 causes (1 fixed) and 6 golden cases; search "comma" returns the separator lesson.

## 2026-11-09 - [product] Generate runs the fix chain; Resolve waits; the loop learns a cause

**Ask.** In Errors & fixes, Generate should be responsive and carry the chain of fixes
automatically; Resolve/Ignore clicked during a Generate should say to wait; and the repair
loop must not say "sleeping" while the open count drops.

**Did.**

- **Generate** now runs the whole chain in one click: generate -> solve one by one ->
  propose improvements -> apply the pending proposal held out against the problems just
  solved -> re-check the source error.  A `healBusy` flag disables the workflow buttons for
  the duration and is cleared in `finally`.
- **Resolve / Dismiss / Propose / Apply / Auto-fix** refuse while `healBusy`, with the
  notification "Wait for the Generate run to finish first".
- **`autoresearch`** no longer sleeps after every error: it continues immediately when
  another unattended cause is waiting, and the pause is labelled "idle - no unattended cause
  left; the stored case suite replays in Ns".  The Autoresearch panel explains that the open
  count also falls while idle because input/transient records are closed as non-defects and a
  fixed cause is not retried.
- **Learning test**: `tests/test_causes.py` now proves that after a durable fix
  (`golden_case`), another open error of the same cause is skipped by the picker and answered
  without a replay (no model call).

**Measured.** The picker returns `None` and `resolve` reports "already fixed" for the second
instance of a fixed cause; `tests/test_causes.py` passes.

## 2026-11-08 - [product] Fix a cause once: the loop skips what it already fixed

**Ask.** The loop kept re-fixing the same issue, burning credits.  It should fix once,
learn, and not spend again on that class.

**Did.**

- **`cause_ledger.fixed_causes()` / `covered_causes()` / `attended_causes()`**: the loop can
  ask which causes already carry a durable artifact and which need a human.
- **`autoresearch._pick_highest_impact_error`** now skips an error when its cause is
  transient or input (not a defect), already fixed with a durable artifact, or waiting for a
  human remedy.  The status line explains how many were skipped instead of looping silently.
- **`auto_resolve.resolve`** short-circuits a cause already fixed by an artifact and marks
  the instance attended, so a direct call spends no model tokens either.
- **`ops_log.log_error`** writes one open record per message: the same failure arriving
  while it is still open is the same instance, not a new id for the loop to re-fix.
- **`tests/test_causes.py`** gains the durable cases for the reader fixes (comma separator,
  Debit/Credit marker, qualified account name).

**Measured.** `cause_ledger` reports the per-cause status; the picker returns `None` with a
"need no repair" status when only fixed, attended or input/transient causes remain.

## 2026-11-08 - [product] Read Debit/Credit trial balances; keep input errors out of the log

**Ask.** Generated problems still failed: "the model could not read this as a journal" /
"declares none of the figures it needs".

**Did.**

- **`problem_norm.split_inline_accounts`** no longer splits a thousands separator: "Credit
  Accounts Payable 5,200" stays one amount.  It split on every comma and turned 5,200 into 5
  and 200, which made a balanced trial balance look unbalanced.
- **`statements.classify`** treats "Debit Cash 12,500; Credit Capital 40,000" as a trial
  balance (marker in front), not as an adjustment narrative.
- **`statements.parse_rows` / `_line_pieces`** split on semicolons and on a marker that
  starts a new account, and strip a leading Debit/Credit from the label; `_side` reads
  "Debit"/"Credit" as D/C.
- **`statements.place`** falls back to the label without its leading qualifier when the full
  label matches nothing, so "Kitchen Equipment" places as equipment instead of being skipped
  (the skipped row is what made Harvest Catering look unbalanced).
- **`chat_heal.solve_problems`** logs a failure only when `causes.is_defect` says it is a
  pipeline cause, per docs/CAUSE_LOOP.md.  Transient and input failures are answered to the
  caller and stay out of the error list.

**Measured.** The user's five problems now solve 4/5 (was 0/5).  The one failure is an
`accounts`-tile narrative whose figures are not in the structured engagement the tile takes;
that is an input problem, not a pipeline defect, and it is no longer written to the log.

## 2026-11-08 - [product] Problem generation: drop reasoning fragments, retry when too few

**Ask.** Generate was stuck and returned the model's thinking as problems ("Need ensure...",
"Problem 1: Narrative with GST? Need tax?..."), so every item failed as "names no
transaction".

**Did.**

- **`chat_heal._looks_like_reasoning` / `_looks_like_problem`**: a candidate must be a
  complete problem (40+ chars, a figure, and an ask such as prepare/compute/determine, and
  no planning cue such as "Need ", "Output only", "JSON", "Problem 1:", "Ensure ").
  Reasoning that leaked into the JSON array is dropped.
- **`generate_problems`** now retries when fewer than two valid problems survive, and merges
  the retry's valid problems.  The prompt says each item must be a complete problem
  statement, never a note about how to generate problems.
- The existing balance and figure checks still drop invalid fixtures.

**Measured.** A live 3-problem generation returned three real problems (no fragments) in 27s;
the reasoning shapes from the report are dropped by the filter.

## 2026-11-08 - [product] Provider timeouts are transient, not error-list noise

**Ask.** Many errors like "the model could not read this as a journal: could not reach the
provider: TimeoutError".

**Did.**

- **`statements._read_journal`** retries the model read once after a 2s pause on a
  transient provider failure (timeout, unreachable, rate limit, connection), so a slow
  OpenCode Go call is recovered instead of logged.
- **`chat_heal.solve_problems`** no longer writes a transient provider failure to the error
  log.  It is still retried by the fallback path and still shown in the run log; it is not a
  pipeline defect and must not appear as a bug.
- **Cleared the backlog**: open errors whose message was a provider timeout were dismissed
  with "transient provider timeout; not a pipeline defect. Re-run the problem to retry."
  The open list went from 20 to 8, with zero timeout-like entries.
- Provider probe: `opencode / deepseek-v4.1-flash` answered in 1.6s at the 120s timeout.

**Measured.** Open errors 20 -> 8, timeout-like open 0; 119 tests pass.

## 2026-11-08 - [product] Testing: per-tile docx/xlsx/explainer downloads

**Ask.** The Financial statements tile in Automated Testing did not download Excel and had
no explainer.

**Did.**

- The statements workbook is now **always built** (not only when the run format is
  xlsx/both); the run saves it for the statements service even on a Word run.
- **Per-tile explainer**: every tile result writes `<label> - explainer.docx` and the result
  records `explainer_file`, so one tile's reasoning can be opened without the whole run.
- **Download column** in the Testing result table: **docx**, **xlsx** (when present) and
  **explainer** links, served by a new route
  `GET /api/ops/papers/batch/{id}/file/{name}` (path-checked, names URL-decoded).
- **`docs/HANDOFF.md`** section 8.10 spells out the per-tile links and the always-built
  statements workbook.

**Measured.** A Word-format statements run now has `xlsx_size` 32091, an `explainer_file`,
and the three per-tile links each return PK bytes; the ZIP also carries
`Financial statements - explainer.docx`.

## 2026-11-08 - [product] Generated problems must be valid; provider timeout raised

**Ask.** Self-healing generated 10 problems from an unbalanced-trial-balance error and 7
failed: figure-less narratives, copied unbalanced totals, and provider timeouts.

**Did.**

- **`chat_heal.generate_problems_from_error`**: the error is now framed as a defect report,
  not a problem to solve.  The instruction requires fully declared figures, a balanced trial
  balance, and fresh numbers (never the error's totals).
- **`chat_heal._valid_problems`**: drops a problem that declares no figure, carries no
  accounting cue, states unequal debit/credit totals, or parses to an unbalanced trial
  balance.  These are invalid fixtures, not pipeline defects, so they no longer count as
  failures.
- **`llm`**: the provider timeout is now 120s (env `BP_LLM_TIMEOUT`), up from 60s, so a slow
  OpenCode Go call is not reported as "could not reach the provider: TimeoutError".
- **Admin**: the per-problem solve abort is now 300s, up from 120s, so a retried call no
  longer ends as "TIMEOUT - signal is aborted without reason".
- The fixer already treats a timeout as transient and an unbalanced trial balance as wrong
  input; both are unchanged and now reach it less often.

**Measured.** The new filter keeps a balanced trial balance and drops the user's two bad
shapes (figure-less narrative, debits 26,420 / credits 26,500).  Provider timeout reads 120.

## 2026-11-08 - [product] Statements get an Excel workbook; explainers are Word

**Ask.** Include Excel when applicable (financial statements), and make the explainer a docx,
not a markdown file.

**Did.**

- **Statements workbook**: the Financial statements preview now builds the statements
  workbook from the record's statements appendix through `spreadsheets.to_xlsx`, so the tile
  writes `Accounting - Financial statements.xlsx` beside the docx.  `xlsx` and `both` formats
  work like every other tile.
- **Explainer as Word**: `paper_batch._explainer_docx` renders the tile explainer with the
  product's Word writer; the ZIP entry, the download at `?format=explainer` and the case
  explainers are all `.docx` now.  `case_runner` writes `<case>_explainer.docx` and a
  run-level `explainer.docx`, and the server serves the explainer as Word.
- **Tests** updated to the docx explainer.
- **`docs/HANDOFF.md`** sections 8.8 and 8.10 updated.

**Measured.** A batch for statements + break-even writes docx and xlsx for both tiles, the
ZIP carries `explainer.docx`, `?format=explainer` returns Word (PK), and a case run writes
`finance_tvm_001_explainer.docx` plus `explainer.docx`.

## 2026-11-08 - [product] Financial statements in Testing; the repair runs on OpenCode Go

**Ask.** Add Financial statements to the Testing tab, and use OpenCode Go in the repair.

**Did.**

- **Testing tab** now lists the Financial statements service tile.  `paper_batch.sections()`
  appends it to Accounting / Bookkeeping with `service: statements`, `supported: true` and
  `has_defaults: true`.  `generate_one` special-cases the service and calls the statements
  pipeline the server injects through `configure(..., statements=...)`, using a deterministic
  sample trial balance so the preview needs no model and no API spend.  The paper carries the
  income statement, balance sheet, equity statement and notes.  `case_store.seed` skips the
  service tile, so no bogus case is seeded.
- **Repair provider**: removed the `BP_ENABLE_DEEPSEEK` gate from `auto_resolve._fix_models`,
  `chat_heal._call_fallback` and `chat_heal._solve_with_fallback`.  The fix ladder is
  `deepseek-v4.1-flash` -> `deepseek-v4-pro` on the OpenCode Go provider (`opencode`, the
  owner's OpenCode Go key); `BP_ENABLE_DEEPSEEK` now only gates the platform.deepseek.com
  calls (statements LLM fallback, hallucination deep-check, DeepSeek search).
- **`docs/HANDOFF.md`** gains section 8.10 recording both.

**Measured.** The statements tile appears in `/api/ops/papers/tiles` (Bookkeeping), a batch
run writes `Accounting - Financial statements.docx` with the four statements, and the repair
config resolves to provider `opencode`, fix models `deepseek-v4.1-flash`/`deepseek-v4-pro`.

## 2026-11-08 - [product] Tile paper is the computation record; preview and download are one document

**Ask.** The tile preview still printed the framework outline — awkward sections, a "no named
framework" paragraph, and a References list over an empty corpus.  The test download and the
actual tile download must be the same paper.

**Did.**

- **`paper_batch.generate_one`** now builds the record the real download renders
  (`_tile_delivery`) and passes it through the **same renderer** (`session_paper.docx_bytes`).
  The paper is: Result, Inputs and results (What you declared / What was computed),
  Assumptions made, Limitations, How the figures were checked.  No framework section, no
  Scope and Method, no Evidence Base, no Discussion, no reference list.
- **`_result_sentence`** prints the computed figures at the method's declared precision.
- **`combined.docx`** is built from the same sections, so it matches the individual papers.
- **`case_store` / `case_upload` / `case_upload_bundle`** default expectations move to
  "What you declared" and "How the figures were checked".
- **`case_runner._check`** maps the two legacy phrases in old case files: `Declared inputs`
  becomes `What you declared`; `References`/`Bibliography`/`Works Cited` are no longer
  required.  All 643 existing case files were migrated; 246 preset cases re-seeded.
- **`docs/HANDOFF.md`** gains section 8.9 recording the structure and the sync.

**Measured.** A Finance TVM preview and the ZIP's combined docx both carry the five headings
and no References; 246 cases re-seeded; samples across every subject pass 30/30 and 20/20.

## 2026-11-08 - [deploy] The local server serves the site Cloudflare publishes

**Ask.** Harmonise local access with the published Cloudflare site: one tree, one set of URLs.

**Did.**

- **The gap, named.** Cloudflare Pages publishes the whole `web/` directory, but the local
  workbench answered only `/`, `/account.html`, `/admin-sbw.html`, `/pricing.html` and
  `/assets/*`. The page's own fallback - `/subjects.json`, the baked subject snapshots the
  published site reads when no API answers - was a 404 at `127.0.0.1:8000`, and every other
  file the site carries was unreachable locally.
- **One route, after the API.** `bp/server.py` serves any file that exists under `web/`,
  matched after every `/api/` route, so a file can never shadow an API route. The name is
  resolved and checked to stay inside `web/`, so a traversal attempt reads nothing else on
  the machine; a missing file is the same JSON 404 an unknown path already gave.
- **The content type comes from the kind.** HTML, JSON, JavaScript, CSS, text, XML, Markdown
  and the three image kinds are declared; anything else is served as bytes, because a file the
  browser cannot render is still the file the site has.

**Did not move.** No API route, no page, no file under `web/` changed: the route only adds the
files that were already published. Nothing about the frozen core or a computed number moved.

**Verified.**

- `/subjects.json` (13,588 bytes), `/subject-economics.json` (133,614) and `/preview.html`
  (179,021) answer 200 with the right content type at the local port, byte-equal to the file.
- An encoded traversal (`/..%2Fsrc%2Fbp%2Fbuild.py`) answers 404 and leaks nothing; an unknown
  `/api/` route still answers `{"error": "not found"}`.
- Four tests in `tests/test_session_api.py` pin all of it. Suite: 4341 tests, 0 failures,
  2 skipped.

**Note.** `web/` also carries `index.html.bak-tileclose`, `_snap_before.html` and
`DESIGN_NOTES.md`. Cloudflare publishes them and the local server now serves them too, which is
consistent but probably not wanted in public: moving them out of the published directory is the
owner's call, not a side effect of this increment.

## 2026-11-08 - [product] Drag-and-drop uploads, explainers, and the growth-loop decision

**Ask.** One upload facility for both testers, with drag-and-drop; Excel and explainer
downloads; and a manual note on whether a growth loop complements the repair loop.

**Did.**

- **web/admin-sbw.html**: the Uploads tab gains a dropzone (`#uploadDrop`) and one handler
  `uploadTestFiles(subject, tile, files)` that both the picker and a drop use.  A drop
  outside the zone is cancelled so the browser cannot navigate away from the console.
  Multiple files are gated one by one, so a bad file does not discard the good ones.  The
  accepted list shows file, case id and date; the paper-preview result table links
  **paper**, **xlsx** and **explainer**, while the Cases result table shows pass/fail only.
- **src/bp/product/case_runner.py**: every case run writes `<case>_explainer.md` per
  result and a run-level `explainer.md`; the result carries `explainer_file`.
- **src/bp/product/paper_batch.py** and **src/bp/server.py**: `?format=explainer`
  returns the Markdown explainer, and the ZIP carries `explainer.md`.
- **docs/HANDOFF.md**: section 8.7 (the unified upload store), 8.8 (the explainer), a
  refreshed section 9, and a new section 10 recording the growth-loop decision: a
  human-gated growth loop is sound because the human supplies the reference
  implementation; the autonomous version and the agent factory are not to be built.

**Why it matters.** The two testers now read one store, so an uploaded file is tested once
and used twice.  Section 10 pins the trust boundary: gap logging plus a scaffold generator
is design lane, and the method logic stays with the computation owner.

## 2026-11-08 - [product] Cases replay on every tile; the authoring brief

**Ask.** An instruction block for another model to write ten cases per accounting tile.

**Did.**

- **Found the blocker.** `paper_batch.generate_one` refused any tile without published defaults before reading the case's inputs, so all 18 accounting cases replayed as `needs_input`. The case now supplies its own figures; the preset is only the fallback for a preview.
- **`docs/CASE_AUTHORING_BRIEF.md`** — the contract, the ten-case design, the tile/method table, the statements-service exception, the acceptance commands.
- **Corrected the refusal shape** while testing it: the tile-case path produces `status: "error"`, not `blocked`, so the brief says so.
- **Measured** — accounting cases 18/18 pass; a preview with no inputs still asks for them.

**Left open.** The brief asks for ten cases per tile (about 170 cases); only the 18 seeded ones exist today.

## 2026-11-08 - [product] Finance and economics read the problem; every file is named for its shelf

**Ask.** "Apply the same robustness of accounting in finance and economics so it could handle all cases and problems within its scope." And: file names should read `subject_subtile_NNN` on every file.

**Did.**

- **`problem_reader.py`** â€” one deterministic reader for any method's schema: the field's `desc` label, the key as words, or a registered synonym must sit next to the number; `%` becomes a decimal only for rate fields and only with the sign; typed figures win; unread required fields are named gaps; numbers no field claimed are counted. It computes nothing.
- **`POST /api/cases/solve/read`** â€” the route, attached to the frozen core's own descriptor.
- **Finance tool page** â€” a "Paste the problem" card with *Read the figures*; it fills the fields it proved and says what is still not stated.
- **Economics** â€” the same synonym table, so a problem worded with "hurdle rate" is read rather than refused.
- **`downloadName`** â€” `subject_subtile_NNN.ext`, with a per-subject-and-subtile counter in the browser; every save on every surface uses it.
- **Measured** â€” NPV read to rate 0.1 and four cash flows, ran, saved `Finance_Capital budgeting_001.xlsx`; `Economics_Inflation and real interest_001.docx`; `Accounting_Statements_001.docx`; `Accounting_Trial balance check_002.xlsx`.

**Left open.** Finance has no automatic problem-type classifier: the student still chooses the tool, so the reader's scope is the chosen method's own schema. Extending the classifier across the shelf is a separate build.

## 2026-11-08 - [product] The page loses its explanatory padding; Method folds away

**Ask.** "UI must be clean and neat." Delete the unnecessary text under sections â€” the shelf sentence ("Ledger, statements, ratios and the cost-volume-profit questions built on them."), the tile note ("The tile does the bookkeepingâ€¦"), the objective line and the worked-example sentence under "Tool - Standard-cost variances" â€” everywhere, and collapse Method. Also: "go" on the trial-balance check download offered at the end of the last round.

**Did.**

- **`subjectCard` / `renderSubject`** â€” no shelf summary. `shelfSummary` is deleted; the catalogue keeps its summaries for the API.
- **`subjectTiles`** â€” no `tile.note`, no "Catalogued frameworks with no worksheet yetâ€¦" paragraph, no reading-lens paragraph. The card badges and the level headings carry the meaning.
- **`renderNew`** â€” the objective subtitle, the "Before you start" card and the management-accounts figures copy are deleted. "Clear the example figures" moves into the header row. `figuresCopy` is deleted outright.
- **Method** â€” a collapsed `<details class="studynote">` like *Draft work plan*.
- **`runCheck` / `checkReport`** â€” the check's result ends with the download row (spreadsheet, check Word, explainer), and the session is kept so the Word route has one.
- **Tests** â€” three stale presence guards updated to the new rule instead of the old line.
- **Measured** â€” served page: no summary, no note, no worked-example line, no Method card; the check's three downloads answered 200.

**Left open.** The statements tile still prints its own long hints inside the analysis boxes (the working-capital field note, the trend note); they explain inputs rather than restate a heading, so they were left.

## 2026-11-08 - [product] The accounting downloads actually download

**Ask.** "Users cannot download the result of their computation in accounting." The management-accounts tile had a download row, but the statements button did nothing.

**Did.**

- **Found it.** The button posted to `/api/cases//export` â€” the case id was empty because the accounting flow never saved a case â€” with `destination: "exports/statements.html"`, a server-side path. The route answered 422 and the page toasted a path on the server. This is E-dl-001 again, in the one panel that had not been converted.
- **`deliverables`** â€” a new `statements` profile: blocks `["statements"]`, formats `docx` and `html`. The statements, without the workings, checks or report that the submission profile adds.
- **`exportStatements`** â€” saves the case through `ensureSavedCase`, then asks the route for `{kind: "docx", deliverable: "statements", download: true}` and turns the bytes into a file with `saveDownload`.
- **`renderAccounts`** â€” each of the four buttons is guarded separately, so one missing element cannot disable the rest; the label now says "Download the statements (Word)".
- **Dead markup** â€” the `#tostats` button in the results panel is removed: `renderResults` replaces that markup, so it never rendered.
- **`renderNew`** â€” a delivered run now renders its report and its download row on the tool page itself (the statements button too for management accounts), instead of leaving the page silent once the engine delivers.
- **`.btn.dl`** â€” every download control is solid black with white bold text: the result card trio, the calculator, the tool page, the management-accounts panel, the case report, the statements tile, and the chat/plan/economics paper buttons.
- **Measured** â€” a live engagement: statements.docx (18 KB), workpapers.xlsx, the session paper and the explainer each answered 200 with a filename; the download buttons compute to black/white/700.

**Left open.** The trial-balance check tile produces a diagnosis, not a computation, and keeps no download; adding one would mean deciding what a check report is.

## 2026-11-08 - [product] The result card folds: downloads under the numbers, no tier badge

**Ask.** The explainer button had gone; spreadsheet, Word and explainer should sit at the bottom of the computation container, below Key numbers; collapse Honesty, Limitations and Assumptions and capitalise the first word; delete "Custom analysis" in the upper right and everywhere else; and every tile must offer Excel, Word and the explainer.

**Did.**

- **`resultBodyHtml`** â€” the tier badge is gone; the download trio moved from the top action row to the bottom of the card, after *Key numbers* and the regression block; the explainer posts to `/api/cases/{id}/explanation`; Honesty, Limitations and Assumptions are collapsed `<details>` with the honesty keys capitalised.
- **`renderCase`** â€” same badge removal and the same folded honesty/limitations, so the case report matches the result, and its download row (Excel, Word, HTML, explainer, worksheet) moves from the top of the Report tab to the bottom, after the technical record.
- **`renderNew`** â€” "Draft work plan" is a collapsed `<details>`, which covers every tile that freezes a spec.
- **`renderAccounts`** â€” the management-accounts panel gains Download spreadsheet, Download the paper (Word) and Download the explainer beside Download financial statements.
- **Copy** â€” "custom analysis (T2)" is out of the management-accounts guide and the T1/T2 legend; the technical record keeps its Tier row.
- **Measured** â€” served page in the browser: no badge, Key numbers before the three downloads, all three `<details>` present, management-accounts panel with four buttons and handlers bound. `qa/check_page_syntax.py` 4/4; 81 page tests pass.

**Left open.** Nothing on this round: the case report's download row now sits at the bottom of its Report tab as well.

## 2026-11-07 - [product] Uploaded tile cases, automatic mapping, and Excel previews

**Ask.** Add files per subject, gate them before acceptance, choose between stored cases and system-generated problems, and choose how many problems to run. Also cover Excel in the previews.

**Did.**

- **`case_upload.py`** â€” parses JSON, CSV/TSV, XLSX (first sheet), Word, PDF, TXT and images. Tables map headers onto the method's input names automatically. The gate runs `validate_inputs` and the method itself; a case that cannot replay is rejected and never stored.
- **`case_store`** â€” the seeded case is unchanged; uploads sit beside it as `origin: uploaded`.
- **`case_runner`** â€” replays a case's own instruction and inputs (not the tile preset), and accepts `generate_count` (1â€“10) to generate and solve fresh problems in the same run.
- **`paper_batch`** â€” `format` Word / Excel / Both; each tile writes a real `.xlsx` workbook through `spreadsheets.to_xlsx`; the ZIP carries both; the case runner checks the workbook's sheets.
- **Page** â€” Format selector, per-subject tile selector + Add files, case checkboxes, a generate count (1â€“10), and Run selected.
- **Measured** â€” CSV and XLSX uploads mapped and ran; a CSV missing a required column was rejected with the method's own message; one generated problem ran and reported a real unbalanced trial balance in ~5 s.

**Left open.** XLSX is read from the first worksheet only, with no merged-cell handling; a document upload replays against the tile's published figures and says so in its instruction. Generated problems are the one part of a run that spends tokens, and only when the box is ticked.

## 2026-11-07 - [product] Tile cases and a token-free self-healing loop

**Ask.** Make the Karpathy loop recursive: a folder of cases per tile, tests that log their own errors, passing tests stored for future use, and no token waste on fixes that cannot be verified.

**Did.**

- **`case_store.py`** â€” 246 cases seeded from the published presets, one JSON per subject/tile. Each case is the prefilled instruction + declared figures + the frozen method's result. It is a fixture, so it is read, diffed and committed.
- **`case_runner.py`** â€” replays a case, compares the computation (float tolerance for Decimal trailing digits) and the required paper phrases; a fail logs one `tile-case` error with `case_id` and the instruction, and saves the failing paper under `state/case_runs/`.
- **`auto_resolve`** â€” a `case_id` error is replayed by code; a pass marks verified, a fail keeps it open. No model is called for a case replay.
- **`autoresearch`** â€” no problem and no case id: skip, no model call. Case id: code replay. Stored problem: flash â†’ pro. Metric: errors-closed %, not pytest pass rate. No open errors: replay all stored cases; stop only when they pass. One attempt per error per cycle.
- **Page** â€” Tile cases card: seed, run a subject or all, results table; failures appear in the error log.
- **Measured** â€” 246/246 cases pass; the loop ran the 246-case suite in ~56s and stopped at 100% closed with 0 model calls. A deliberately broken case failed, was logged, replayed as still failing, then verified after the expectation was repaired.

**Left open.** Four legacy `no sourced price` errors carried no stored problem, so the loop could not replay them; they were dismissed for owner review rather than guessed at. The loop cannot patch code: a case that still fails stays open until a computation-owner change lands.

## 2026-11-08 - [core] Beneish from two records; tax law deferred

**Ask.** Close Beneish; defer tax law to a jurisdiction decision.

**Did.**

- **`statements.beneish(records)`** - the eight indices (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) derived from two solved records (receivables/sales, gross margin, asset quality, sales growth, depreciation rate, SG&A intensity, leverage, accruals); a missing figure is named; the frozen `beneish_m_score` computes the formula. Route `POST /api/cases/statements/beneish`.
- **`altman_z_score` and `beneish_m_score` use Decimal constants** - the `_d` repair now returns Decimals, and the old float coefficients would raise on a Decimal input.
- **`RATIO_GAPS`** points Beneish at the two-record route.

**Left open.**

- Tax law is deferred to a jurisdiction decision (likely the US when there are enough subscribers); the declared-rate reconciliation remains the global default.

**Proof.** `tests/test_beneish.py` (4, exact score -2.0126); the suite passes; both fixtures in sync. B-242.

## 2026-11-08 - [core] Piotroski from two records; the finance `_d` repair

**Ask.** Build Piotroski.

**Did.**

- **`statements.piotroski(records, extra)`** - two solved records (prior and current), the nine inputs built from each bundle's figures, the diluted share count declared in `extra`; orders by period, refuses a same-period pair, names a missing figure, and calls the frozen `piotroski_f_score`. Route `POST /api/cases/statements/piotroski`.
- **`finance_methods._d` accepts both call shapes** - `_d(inputs, "key")` and `_d(value)`. 78 two-argument calls (Altman, Piotroski, Beneish and the rest) had been failing at runtime against a one-argument helper; this repairs the finance shelf, not just Piotroski.
- **`RATIO_GAPS`** now points Piotroski at the two-record route instead of calling it impossible.

**Left open.**

- Beneish still needs its eight indices from two periods; a form that computes them from the two records is the next step.
- Tax law remains a jurisdiction/source decision.

**Proof.** `tests/test_piotroski.py` (3); frozen contract in sync; page syntax OK. B-241.

## 2026-11-08 - [core] Three gaps: market ratios, integrated narratives, tax reconciliation

**Ask.** Close the ratio-catalogue gap, the integrated-narrative gap and the tax gap (B-052 resumed).

**Did.**

- **Ratio catalogue** - added earnings per share, book value per share, price-earnings, market-to-book, dividend payout and yield, and the Altman Z-score; `ratios(record, extra)` accepts declared share data; `RATIO_GAPS` now names only Piotroski (two periods + diluted shares), Beneish (two periods of eight indices) and the free-cash-flow amount.
- **Integrated narratives** - broadened the detector for "bought", "earned 30,000 cash sales" and "paid 5,000 rent"; de-duplicated overlapping matches (`capital_contribution` vs `equity_issuance_cash`); the transactions route now applies the adjustment parser to the same narrative, so transactions+adjustments solves with every check green; the route is tried whenever the detector has matches, not only when the parser error says "transactions".
- **Tax reconciliation (B-052 resumed)** - `tax_reconciliation` reconciles accounting profit to taxable income through non-deductible, non-taxable and allowance items, then current tax, deferred tax, total charge, effective rate and VAT payable; `statements.tax_note(record, extra)` and `POST /{id}/tax`; registered as a statement-registered helper.
- **Two concurrent-write breakages repaired** - `reconstruction.py` was missing `import re`, and `statement_extract.py`'s `stated = []` line was merged with the following `if`, which stopped the module importing.

**Left open.**

- Piotroski and Beneish still need two periods (a multi-record forensic consumer).
- Tax law, credits, thresholds, loss carryforwards and a tax return remain out of scope by design.

**Proof.** Accounting sweep 576 + 186 subtests; both fixtures in sync; page syntax OK. B-239/B-240.

## 2026-11-08 - [core] The adjustment reader and the ratio catalogue

**Ask.** Make the pipeline handle any valid accounting problem: a full adjustment narrative and a broader ratio catalogue.

**Did.**

- **`_split_tb_and_adjustments`** - an explicit "adjustments:" marker first; otherwise the balance rows and the adjustment sentences (a sentence never parses as a balance row; a balance row never carries an adjustment verb).
- **`_adjustment_specs`** now reads prepaid amortisation (payment x months expired / total), straight-line depreciation from a cost and life, bad debts at a rate of receivables, interest accrual (principal x rate x months / 12) and income tax at a rate, in addition to supplies, unearned revenue and accrued expenses. An unrecognised or under-specified clause is named `unread`.
- **A problem with only adjustments** refuses with "the unadjusted trial balance is not given" instead of "no account".
- **`column_lines`** no longer mistakes an adjustment sentence's payment and months for a comparative.
- **`_RATIOS`** gains operating cash flow ratio, cash flow margin, cash flow to debt, free cash flow margin and the accruals ratio; the bundle supplies operating cash flow and capital expenditure from a present cash flow and withholds them when the cash flow is withheld; `RATIO_GAPS` drops the ratios now computed.
- **`reconstruction.py`** (another lane's new, untracked file) was missing `import re`, which stopped `statements` importing; the one import is added.

**Left open.**

- Altman, Piotroski, Beneish and the market ratios still need inputs a single statement does not carry (a market value, two periods, a share price); they stay named gaps.
- Tax reporting stays parked (B-052).

**Proof.** Accounting sweep 572 + 186 subtests; page syntax OK; both the frozen contract and the statements record regenerate. B-238.

## 2026-11-07 - [core] The deterministic reader: bare lists, preambles, currencies, a crash

**Ask.** Fix the narrative-reader defects the handoff measured.

**Did.**

- **`parse_rows`** splits a line on `. ` sentence boundaries, so "â€¦31 December 2026. Cash 10,000. Capital 10,000." reads as two accounts. Decimals ("5.50") and dot leaders ("Cash ...... 5,000") carry no space after the period and are untouched.
- **`read_deterministic`** treats a bare list of accounts and balances as a trial balance when at least two accounts place; everything else is still refused.
- **`BLOCKED`** catches common foreign currency codes and symbols; "EUR" is now refused with the USD message instead of being read as an unplaceable account.
- **A `tier1_gaps` NameError** in `_solve_financial_computations` is fixed; a ratio question used to crash with a 5xx.
- **Trap tests** - `tests/test_statements_reader_fixes.py` (4).

**Left open.**

- An adjustments narrative (prepaid, accrual, depreciation) still needs the model reader; a deterministic adjustment reader is a separate increment.
- Tax stays parked (B-052).

**Proof.** Accounting sweep 489 + 186 subtests; page syntax OK; the frozen fixture is in sync. B-237.

## 2026-11-07 - [test] The statements core resets between test classes

**Ask.** The accounting sweep failed on `test_product_statements_api` after the new statement tests attached `build`.

**Did.**

- Added `statements.reset_core()`.
- `test_statements_figures` and `test_statements_gap_noise` call it in `tearDownClass`; the API route suite calls it at the start of `attach()`.
- No product code path calls it.

**Why.** `_CORE` is module state; a test that attaches more than the minimum leaked a builder into a later test that expected a smaller subset, so "Cash 5,000" solved where the suite meant it to refuse. The suite's own comment says it is hermetic; this makes that true.

**Proof.** Accounting sweep 485 + 186 subtests; targeted suites 337 + 8; page syntax OK; the frozen fixture is in sync. B-236.

## 2026-11-07 - [core] Contra-income closing and stated totals

**Ask.** Fix the two accounting correctness bugs: the income-statement-only refusal and the stated-total-zero.

**Did.**

- **`ledger.closing_entries`** - close on the side opposite each account's normal side (a contra income such as sales returns closes with a credit, not a debit) and balance into retained earnings whichever side the net falls on. Before, sales returns stayed open and retained earnings was over-credited by the contra amount.
- **`income_statement._classify_account` / `compute_balance_sheet_analysis`** - recognise stated totals and use one when its components are absent; components still win when both are present, so nothing is double-counted. "current liabilities 25,000" alone now gives 25,000, not 0.
- **The statements-record fixture** was regenerated by `qa/manual/make_statements_fixture.py`, because the closing entries changed and the fixture pins them byte-for-byte.
- **Trap tests** - `tests/test_accounting_correctness_traps.py` (3): a contra-income account closes and retained earnings ties; a stated total with no components; components winning over a stated total.

**Left open.**

- A stated total and its components can still disagree silently (the components win). A named warning is a separate increment.
- Tax stays parked (B-052).

**Proof.** Eighteen suites: 370 passed, 8 subtests; page syntax OK; the frozen fixture is in sync. B-235.

## 2026-11-07 - [core] Fix the finance cycle function; trend consumes several statements

**Ask.** Fix the broken `finance_methods.cash_conversion_cycle` and make trend usable from more than one statement record.

**Did.**

- **The finance function** called `_d(inputs, "dso")` against `_d(x)`, a one-argument helper; it now reads `inputs["dso"]`, `inputs["dio"]` and `inputs["dpo"]`. Direct check: DSO 40, DIO 30, DPO 25 gives 45 days. The input schema is unchanged, so the frozen contract stays in sync.
- **`statements.trend(records)`** - builds the series from two or more solved records: revenue, cost of sales, operating expenses derived from the expense breakdown, net income, and optional total assets and equity. It orders the periods by the year each statement ends, refuses two records ending in the same year, and calls the frozen `trend_analysis`.
- **`derived` gains `operating_expenses`** and its basis, so a trend separates cost of sales from the rest without re-typing the breakdown.
- **Route and UI** - `POST /api/cases/statements/trend` with `{records: [id, id]}`, and a **Trend** button that takes the other record ids.

**Left open.**

- Tax stays parked (B-052).
- Trend is annual periods only; interim periods would need a period-key change.
- The finance `cash_conversion_cycle` and `working_capital_cycle` remain two methods with similar names; the first takes the three day counts, the second computes them from balances, and each says so in its intended use.

**Proof.** `tests/test_statements_figures.py` (20) and the thirteen suites: 351 passed, 8 subtests; the frozen fixture is in sync; page syntax 4/4. B-234.

## 2026-11-07 - [core] A cycle-only method for the statements tile

**Ask.** The combined `working_capital` method needs six operating terms a statement cannot supply; add the clean cycle-only method.

**Did.**

- **`working_capital_cycle` (T1)** in `methods.py`: DSO, DIO, DPO, the cash conversion cycle and net working capital from revenue, cost of sales, inventory, receivables and payables; `days` optional (365).
- **Full contract**: impl, a second float route, four checks, profile, caveats, template, typing, intended/unsupported use, assumptions and limitations.
- **The id is `working_capital_cycle`, not `cash_conversion_cycle`** - `finance_methods` already owns a different (and broken) `cash_conversion_cycle` id and would overwrite the new method when it loads.
- **`statements.cycle(record)`**, `GET /api/cases/statements/{id}/cycle`, and a **Cash conversion cycle** button.
- **Frozen contract regenerated** with `scripts/econ_shelf.py --fixture` (210 methods, in sync). The subject guard declares the method a statement-registered helper, like `eps`.
- **No product-layer arithmetic**: the cycle is computed once, in the core; the tile only reads the result.

**Left open.**

- The finance `cash_conversion_cycle` function is broken (`_d(inputs, "dso")` against a one-argument `_d`); it is not used by the tile, but it is a real defect worth a separate fix.
- Trend still needs two or more statement records; tax parked (B-052).

**Proof.** `tests/test_statements_figures.py` (17) and the eleven statement/subject/contract suites: 270 passed, 8 subtests; `tests/test_frozen_contract.py` 3 passed; page syntax 4/4. B-233.

## 2026-11-07 - [product] DuPont and working capital consume a statement

**Ask.** Wire DuPont and the working-capital cycle to the bundle and add the pre-tax/EBIT figures the bundle lacked.

**Did.**

- **Bundle `derived` map** - `tax_expense` and `interest_expense` are read from the record's own expense groups; `pretax_income` = net income + tax and `ebit` = pre-tax + interest, each carried with the basis that produced it and never merged into the stored figures.
- **`statements.dupont(record)`** - the three-step form from revenue, net income, total assets and equity (all four always carried); the five-step form only when EBIT, pre-tax and tax are present, otherwise named as not run; a comparison period needs a second record and is never guessed.
- **`statements.working_capital(record, extra)`** - revenue, cost of sales, inventory, receivables and payables come from the statement; the six operating terms (annual demand, order cost, holding cost, discount, credit terms, discount days) are declared, and the ones that are absent are named.
- **Routes and UI** - `GET /api/cases/statements/{id}/dupont`, `POST /api/cases/statements/{id}/working-capital`, and two panel buttons: DuPont, and a Working capital form that supplies the six terms.
- **The honest limit found** - `working_capital` is monolithic (cycle + EOQ + cost of trade credit), so it cannot return the cycle without the six terms. A cycle-only frozen method would remove that requirement; that is a core addition, not a product change.

**Left open.**

- Trend needs two or more statement records; the bundle is single-period.
- Tax stays parked (B-052).
- A cycle-only method is the clean way to get the CCC from a statement alone.

**Proof.** `tests/test_statements_figures.py` (15) and the ten statement/subject suites: 265 passed, 8 subtests; page syntax 4/4. B-232.

## 2026-11-07 - [product] Calculators report to the library; ratios consume a statement

**Ask.** Build (a) the six calculator routes recorded under their accounting shelf, and (b) the first statement-consuming tile (ratios) on the shared bundle.

**Did.**

- **`subjects.accounting_group_for_method(method_id)`** - maps a frozen method to the accounting shelf the subject page shows, or `None`.
- **`statement_library.record_calculator(...)`** - records a run under that shelf; a non-accounting method returns `None` and is not logged.
- **Server hook** - the session confirm handler calls `_record_calculator_run(session)` after a calculator is confirmed; it reads the request method and objective and the delivery status, and never raises into the request path.
- **`statements.ratios(record)`** - the ratio pack computed on demand from `figures(record)`, naming every ratio the record cannot support.
- **Route and UI** - `GET /api/cases/statements/{id}/ratios`, and a **Ratios** button in the statements panel that fetches it and renders the pack.
- **One formatter** - `ratio_pack` and `ratios` share `_ratio_rows`, so the record's own ratio section and the on-demand pack cannot format differently.

**Left open.**

- The UI button is the first consumer; DuPont, trend and working-capital cards can follow the same pattern.
- The library's older records remain `unrecorded` until re-run.

**Proof.** `tests/test_statements_figures.py` (9) and the ten statement/subject suites: 259 passed, 8 subtests; `qa/check_page_syntax.py` reports 4/4 blocks parsed. B-231 records the decision.

## 2026-11-07 - [product] The statement record as a shared input; the library learns by shelf

**Ask.** Wire the solved statement record as the shared input for the other accounting tiles, and tag the learning library by accounting group so the cost/variance, ABC, sales-variance, working-capital, pro-forma and tax tiles are counted beside the statements tile.

**Did.**

- **`statements.figures(record)`** - a `bp-statements-figures/1` bundle read from the frozen record: the named figures (`revenue`, `net_income`, `current_assets`, `current_liabilities`, `inventory`, `receivables`, `payables`, `total_assets`, `total_liabilities`, `equity`, plus `retained_earnings_closing`, `cash_net` and the check counts), the structured `income_groups`, `balance_sheet_groups`, `equity`, `cash_flow`, and the named `ratio_gaps`. Nothing is recomputed: the bundle is the record's own appendix.
- **Route** - `GET /api/cases/statements/{id}/figures` returns the bundle; a refused record is a 409 naming the refusal, never an empty bundle.
- **Library group tag** - `statement_library.record(..., group=...)`, `record_problem(group, instruction, solved=..., refusal=..., problem_type=...)`, `gap_report(group=...)` and a new `by_group` key. The statements tile records as `Statements` on success, refusal and error.
- **A latent crash fixed** - `most_repeated` sliced a NULL `missing` field; it now guards it.
- **Why the bundle, not a copy** - a tile that re-types figures will disagree with the statements eventually; one bundle from the frozen record makes agreement structural.

**Left open.**

- `[computation]` The six calculator routes (`scv`, `abc`, `salesvar`, `workingcapital`, `proforma`, `tax`) still need their one-line `record_problem(group, instruction, solved, refusal)` call; the helper and the `by_group` report are in place, the routes are not yet hooked.
- `[computation]` An income statement tile that consumes the bundle can now be built without a second parser; that is a separate increment.

**Proof.** `tests/test_statements_figures.py` (5) plus the eight statement suites: 191 passed, 8 subtests. B-230 records the decision.

## 2026-11-07 - [product] The statements library: a gap was invented, not found

**Ask.** Fix the gaps the statement library reported from its own records, according to the suggested fixes.

**Did.**

- **Read the evidence before changing data.** The library held 1,304 records (919 solved, 385 unsolved, 283 distinct problems). The 51 "no adjusting entries were derived" records were almost all one-line problems such as `Issued common stock for $80,000 cash.` and `Revenue 200,000; sales returns 5,000. Required: income statement.` - nothing was missing, so the gap was a false positive that polluted the report.
- **Fixed the false positive, not the symptom.** `_solve_transactions` already returns `None` when the text carries an adjustment cue, so its `missing` note could never be true; it is gone. `_solve_narrative` now writes the note only when `_needs_adjustments(text)` is true. The cue set is one module-level tuple (`ADJUSTMENT_CUES`) and one helper, so the two sites cannot drift.
- **Fixed the gate name.** `current_ratio_equals_assets_divided_by_liabilities` checked `current_assets / current_liabilities`; it is now `current_ratio_equals_current_assets_divided_by_current_liabilities`, so the name matches the check.
- **Left the correct behaviour alone.** Header sentences ("The following trial balance was extracted at 31 December 2026") are still recorded as non-accounts with an explanation; an unbalanced trial balance is still refused with the difference named; "show only the balance sheet" is still a supported partial render. These are the system working, not gaps.
- **Did not patch the two deeper findings.** `current liabilities 25,000` given as a *total* with no components parses as 0 in `income_statement.compute_balance_sheet_analysis`; and an income-statement-only narrative ("Revenue 200,000; sales returns 5,000") still runs the full closing/rollforward gates, which fail under `retained_earnings_rollforward` and `income_expense_and_dividends_zero_after_closing`. Both are logic/core decisions (total-vs-components policy; which gates apply to a partial request) and are recorded as `[computation]` follow-ups rather than silently patched.

**Left open.**

- `[computation]` `income_statement.parse_problem` / `compute_balance_sheet_analysis`: use a stated total when its components are absent, and never double-count when both are present. Two records.
- `[computation]` `statement_plan`/`ledger`: an income-statement-only request should not be failed by balance-sheet closing/rollforward gates that the request never asked for. Two records.
- The library's older records keep the old gap text; only new solves are corrected. The gap report will show the old counts until those records age out or are re-run.

**Proof.** `tests/test_statements_gap_noise.py` (2, new) plus the six statement suites: 186 passed, 8 subtests. B-229 records the decision.

## 2026-11-07 - [product] Automated testing: a real paper per tile

**Ask.** Replace the admin Tests button row with an Automated testing section: subjects are permanent sections, subsections collapse, tiles are tickable, a tick survives a subsection switch, and the ZIP download sits at the bottom of each section. Each paper is a real writer paper generated from a prefilled instruction that shows the tile's ideal behaviour, with references.

**Did.**

- **`paper_batch.py`** - one tile -> one paper. The instruction is the published preset objective plus its declared figures; the frozen method runs once; the conductor drafts a no-framework paper; the corpus is searched by the tile's own words, and a sentence is quoted only when it is in the page returned. No match is a named gap. A run directory under `state/paper_previews/<run_id>/` holds the `.docx` papers, a combined `docx`, `instructions.md`, `manifest.json` and an index.
- **Routes** - `GET /api/ops/papers/tiles`, `POST /api/ops/papers/batch`, `GET /api/ops/papers/batch/{id}`, `GET /api/ops/papers/batch/{id}/download`, `GET /api/ops/papers/runs`.
- **Page** - the Tests card is gone. The new card renders 11 subject sections, 50 collapsible subsections and 246 usable tile checkboxes, with per-section Generate/Clear, progress, a results table and download links at the bottom. Ticks are kept in `localStorage` under `sbwPaperTicks`.
- **A real chart defect fixed** - `_chart_specs_for`/`_figure_plan` turned a result key such as `count_1` into the label "Count 1"; the figure layer refuses a digit in a label. The label now uses the declared stage name or a digit-free form, while the artifact id is unchanged.
- **Sweep** - 246 tiles with published defaults generated 246 papers with no failure; 5 tiles are named `needs_input` because they are decision frameworks or have no preset.

**Left open.** The paper is a tile report, not a strategic paper: a student run can still add a framework. References carry the corpus title and author/year where the corpus metadata has them, and `n.d.` where it does not; enriching the 159 unenriched corpus documents is the durable fix. XLSX per tile is phase 2.

## 2026-11-07 - [product] A visual layer: figures, decks, workbook charts

**Ask.** Integrate professional charts, graphs, illustrations, pitch decks, KPIs and roadmaps into the pipeline - accurate, professionally made, and better than what a raw model produces.

**Did.**

- **The principle held throughout: no model draws a chart.** A picture that cannot be checked is an invented citation. The model may draft a `bp-chart/1` spec; code validates it; the geometry and every number come from stored artifacts.
- **`figures.py`** - the record (`id`, `kind`, `spec`, `caption`, `note`, `sources`, `why`, `place`, `digest`), validation (digit-free caption and note, a mandatory `why`), staleness, and a registry. A figure is referenced by id, never copied, so a paper and a deck cannot disagree about one number.
- **`figure_plan.py`** - the auto-triggers and placement: declared series, composition, alternatives, an explicit spec, and a CPM record to a Gantt. Every proposal carries its reason; every block that drew nothing is named.
- **`renderers.py`** - the builtin SVG always runs; Plotly + kaleido draw charts; the Chrome kaleido carries rasterizes the builtin SVG; `cairosvg` is tried and skipped when its cairo DLL is absent. `dot_source()` and `mermaid_source()` turn a validated `tree` or `process` into Graphviz or Mermaid source.
- **`theme.py`** - one palette and type scale, read by Plotly, Graphviz, Mermaid, python-pptx colours and the builtin SVG.
- **`deck.py`** - a hand-built `.pptx` in the `docx.py` style (stdlib only, because the runtime rule forbids a third-party writer and python-pptx is not installed): title/claim/figure/section slides, a claim required on every content slide, figures by id, speaker notes, a fade.
- **`docx.py` / `spreadsheets.py`** - a rendered PNG becomes a real inline picture in Word and an anchored drawing in Excel; the values-table fallback keeps the paper honest when no rasterizer is present.
- **Routes and page** - `presentation` is offered and routed; `POST/GET /api/cases/{id}/figures` creates, previews and confirms a figure; the Deliverables Charts card is live with a **Save to this case** button.
- **Four errors fixed** - `set_enabled` allows a drop; the chat helper follows `current_question`; the session test tolerates methods registered by `finance_methods`.

**Left open.** Native Excel charts (`<c:chart>`, editable) are not built; auto-figures do not fire in the chat paper path because the chat state carries no bundle; the builtin SVG's font families match the tokens but are not read from them; Mermaid and Graphviz binaries are not installed, so their source is tested but not drawn.

## 2026-11-07 - [finance] Rates and FX folds, Student guide and shelf summary go

**Ask.** Four things on the Finance subject page: make the Rates and FX block at the top collapsible, delete the Student guide, delete the shelf summary, and delete the "published method" instruction under Quantitative Finance. Then: the buttons stopped working.

**Did.**

- **The Rates and FX panel is a disclosure.** `ratesPanel()` now returns `<details class="marketpanel">` with a `<summary>` header (`<h3>` "Rates and FX" plus a read-then-type hint); starts closed (no `open` attribute). The intro sentence, both `.lookupcard`s, every id (`fxbase`, `fxquote`, `fxdate`, `rfmat`, `fxlookup`, `rflookup`, `ratesout`) and the `"type it into the tool that needs it"` instruction are byte-identical. CSS is child-scoped (`.marketpanel > summary`), so the macro and securities panels keep their plain boxes. `bindRatesPanel()` defers the `/api/currencies` fill to the first `toggle` to open.
- **The Student guide is gone** from `renderSubject()` - the guidance sentence, the *Start here* path and *What this shelf does not do*.
- **The Finance shelf summary is gone** from the page. A new `shelfSummary()` helper (with `SHELVES_WITHOUT_SUMMARY = ["finance"]`) returns an empty string for that shelf, and both the subject heading and the all-subjects card skip the line when it is empty. The baked `__SBW_SUBJECTS__` block carries `"summary": ""`.
- **The "published method" instruction is gone** â€” *"These run a published method. Supply the figures and confirm; the server computes the result and its checks."* was presentational text in `renderSubject()` under the *Quantitative Finance* heading; it is removed outright. It was not catalogue data, so `src/bp/product/subjects.py` and the baked snapshots are unchanged.
- **The syntax error is fixed.** Removing the Student guide block had left a dangling `) +` in `renderSubject()` with no matching `(`. The whole inline script failed to parse, so no handler was registered and every control on the page was dead. The remnant is gone.
- **Tests.** `tests/test_market_panels.py` gains `test_rates_and_fx_is_a_disclosure_that_starts_closed`. `qa/manual/finance_page_probe.py` (new) drives headless Chromium over the DevTools Protocol to prove the script parses, no exception is raised, the Student guide and summary are absent, the panel starts closed, its header opens it, and **a click on "All subjects" really moves the view**.

**Did not move.** No method, preset, input, check, computed number or frozen-core entry changed; macro and securities panels untouched. `src/bp/product/subjects.py` and the two baked snapshots are unchanged - that is the computation owner's lane (HANDOFF Â§1.9).

**Verified.** `tests/test_web_inline_script.py` + `tests/test_market_panels.py`: 14 tests, OK. `qa/manual/finance_page_probe.py --url http://127.0.0.1:8021`: 10 checks, 0 failures. The two failures in `tests/test_web_static_snapshot.py` are pre-existing and unrelated - both compare `web/subjects.json` against `bp.product.subjects.catalogue()` and never read `web/index.html`.

### Handover to the computation owner (DeepSeek) â€” the catalogue still holds the summary

The page no longer prints the Finance shelf summary, but the **data layer still carries it**. `src/bp/product/subjects.py` and the two baked snapshots are the source of truth for the API and for the public static site, so the sentence must go there too. This is the computation owner's lane; the steps are:

1. **`src/bp/product/subjects.py` (line ~3644)** â€” in the `finance` subject record, replace
   `"summary": "Corporate finance, valuation and the investments, debt, risk and international tools a finance student needs.",`
   with `"summary": "",`.
   Keep the key. Do **not** remove it: the rail and the snapshot guard both expect the same object shape for every subject.
2. **Rebuild the baked snapshots** from `business_pipeline_v0.12/business_pipeline`:
   ```
   $env:PYTHONPATH="src"
   python scripts/build_web_subjects_snapshot.py
   ```
   This rewrites `web/subjects.json` and `web/subject-finance.json`. They are generated files - never hand-edit them.
3. **`web/index.html`, the `__SBW_SUBJECTS__` block** - already carries `"summary": ""` for finance, so it will agree with the rebuilt `web/subjects.json`. If the rebuild changes the block, prefer the rebuilt file and keep the two in step.
4. **The frontend suppression can then be simplified.** `SHELVES_WITHOUT_SUMMARY` in `web/index.html` exists so the page is correct before the catalogue catches up. Once the catalogue is blank, the helper becomes redundant; removing it is optional and safe either way - the empty summary renders no line.
5. **Run the guard:** `python -m unittest tests.test_web_static_snapshot.py -v`. It must pass: the two failures present now are pre-existing drift between the committed snapshot and the catalogue, and rebuilding is what clears them.

**Do not** touch `src/bp/methods/**`, any fixture, or `tests/fixtures/frozen_contract.json`. No method, input, check or computed number changes in this handover.

## 2026-11-06 - [statements] The tile's workbook opens in Excel

**Ask.** The statements tile's `.xlsx` download came back as a file Excel would not open - "empty content" - while the API answered with a valid base64 payload of a valid zip of valid XML, and openpyxl read it without complaint. The export had to be fixed so that the student receives a workbook Excel opens, carrying the statements the render brief asks for.

**Did.**

- **The three defects Excel was refusing, named.** `/xl/theme/theme1.xml`, `/docProps/core.xml` and `/docProps/app.xml` were declared **twice** in `[Content_Types].xml` - a part carries one content type, not two. The `Notes` sheet was written **twice** - Excel refuses a duplicate sheet name. And `<cols>` was written **after** `</sheetData>` in every worksheet, while `CT_Worksheet` requires `cols` before `sheetData`. The package was also not byte-stable: `writestr` without a timestamp writes the current time into the zip, so two exports of one record differed.
- **One writer, not two.** `spreadsheets.py` already wrote a workbook Excel accepts; `xlsx.py` wrote a second, broken one, and it was the only workbook writer in the tree that no test covered. The packaging now lives in one place, `spreadsheets.write_xlsx(sheets, places)`, and `xlsx.py` is the statements tile's adapter over it. **The case bundle's workbook is byte-identical to before** (sha256 `801218277774fd0f...`), so nothing a student already downloaded moved.
- **The workbook the student receives is the one the brief asks for.** One sheet per requested statement - `Income statement`, `Changes in equity`, `Balance sheet`, `Cash flow` - then `Working`, then `Notes`, the names the render brief gives (`docs/MINIMAX_STATEMENT_RENDER.md` section 9), so the tile's download and the case bundle's workbook agree. The amounts are **numbers** in the record's decimal places (`#,##0.00;(#,##0.00)`), so Excel totals and sorts them; the header row is frozen; column A is sized to the longest label; no cell is merged. The statement of changes in equity now carries its movement figures as numbers with the note beside them, where the old writer left the whole line as text, and the period line reads the record's period instead of `Period:  to `.
- **A figure the record only renders is not re-typed.** A record whose appendix cannot supply a statement's typed figures - the thinner record shapes the tile also stores - gets that statement as the record rendered it, verbatim. Re-reading a rendered line is how a figure stops being the record's, so the line stays text rather than becoming a number the record does not hold as a value.
- **The package is guarded now.** `tests/test_statements_xlsx_export.py` (24 tests) checks the rules Excel enforces - a part declared once, a relationship that resolves, a unique legal sheet name, the worksheet children in order - and the workbook itself: the sheet set, typed amounts, the record's places, the frozen header, no merged cell, byte-stability, and no figure the record does not hold. `qa/manual/audit_xlsx_structure.py` runs the same audit as a probe against an openpyxl reference, and `qa/manual/excel_open_check.ps1` opens the file in Excel itself.

**Did not move.** No method, preset, input, check, computed number or frozen-core entry changed. The statements, their figures and the request contract are exactly what they were; only the file the student downloads is different.

**Verified.**

- **Excel opens it.** `qa/manual/excel_open_check.ps1` opens the rendered workbook in Excel 16.0: six sheets, each with its data, and no repair. The same script on the pre-repair file fails outright - Excel refuses to open it - which is the symptom the owner reported. Excel reads an amount cell as a `Double` (a number, not text), showing `200,000.00` under the format `#,##0.00;(#,##0.00)`.
- **The audit is clean.** `qa/manual/audit_xlsx_structure.py` reports "no structural problem found": no part declared twice, every part with a content type, every relationship resolving, unique legal sheet names, and every worksheet's children in the order `CT_Worksheet` requires.
- **Byte-stability.** Two renders of the same record are the same bytes (sha256 `c250877dd61f01be...`).
- **The suite is 3899 tests.** The failures that remain are the ones recorded in `docs/OPEN_ISSUES.md` item 18 (`schedules.py` shadowing a frozen core module, and `tier1_tables.py` importing `bp.product`); they are in files this increment does not touch, and both changed files pass the product-boundary rules themselves.

## 2026-11-06 â€” [deploy] The site is published, and it stands on its own without the backend

**Ask.** The deployment has to be one line and one working URL: the whole project on `main`, published by Cloudflare
Pages, with the build settings that match a plain static tree, and a push to `main` deploys it. The site keeps every
feature it has now. The earlier deployment failed, and the reason was not a fault in the site.

**Did.**

- **The Pages project now carries a Git source.** `smart-business-writer` on the owner's Cloudflare account is bound to
  `smartbusinesswriter2026-bit/smart-businesswriter002` with `main` as the production branch, deployments on, and
  preview deployments on every branch. The project was created as a direct upload; a direct-upload project cannot be
  converted, so the Git source was attached and the project was left in place under the same name.
- **The build settings match the tree.** Build command empty, output directory `business_pipeline_v0.12/business_pipeline/web`,
  root directory empty. There is no build step: the site is plain HTML, CSS and JavaScript with no `package.json` and no
  bundler, so an empty command is the correct setting rather than a shortcut.
- **A push to `main` deploys the site.** That is the mechanism, not a manual step, so the deployment that proves this
  increment is the push that carries it.
- **The public host has no backend behind it, so the site reads what it carries.** Cloudflare Pages serves the files;
  there is no Python server answering `/api/subjects` or `/api/health`. The subject rail now falls back to
  `web/subjects.json`, a snapshot of exactly what `bp.product.subjects.catalogue()` returns, and the "the local API did
  not answer completely" banner is raised only when *some* calls failed, not when every call failed - on a static host
  every call fails, and that is not an error the reader should be shown.
- **The snapshot cannot drift.** `scripts/build_web_subjects_snapshot.py` regenerates it from the code, and
  `tests/test_web_static_snapshot.py` fails on four counts: the snapshot must equal the code's catalogue, it must carry
  the declared format, the page must keep the fallback, and the page must not report a failed local API when all calls
  fail. The file is generated, never hand-written.
- **Two small corrections in the same increment.** The Git line in `docs/HANDOFF.md` said "no remote"; the tree has a
  remote now, and `main` is the deployment branch. `docs/CONTRIBUTORS.md` still claimed 3828 tests while the suite held
  3869, which is a stale count the repo's own guard catches; it is brought back into agreement.

**Did not move.** No method, preset, input, check, computed number or frozen-core entry changed. The site keeps every
feature, string, asset and design it had: the deployment adds the one thing a host without a backend needs, and the
local backend is untouched - when it answers, the page uses it.

**Verified.**

- The public URL answers: `https://smart-business-writer.pages.dev/` returns the page, and the assets under
  `assets/` are served with their image type. The deployment that serves it was triggered by the push that carried this
  increment, and its build log shows the repository cloned and the output directory uploaded.
- The new guard passes on its own (`tests/test_web_static_snapshot.py`, four checks) and the generated snapshot is
  byte-equal to what `bp.product.subjects.catalogue()` returns.
- The suite is 3873 tests. The failures that remain are the ones recorded in `docs/OPEN_ISSUES.md` item 18, and the one
  the merge increment fixed is the count that `docs/CONTRIBUTORS.md` carried: the guard now reads the real count from
  the code and the three documents agree with it.

## 2026-11-05 â€” [integration] `origin/main` is merged in, and the branch stays the one line

**Ask.** The deployment line has to be one line: `main` must carry the whole project so the Cloudflare Pages build
publishes everything. `main` and `corpus/merge-v1` had grown apart â€” 25 commits and 317 commits, touching the same
files, with fourteen conflicts â€” so the two lines had to be folded into one without losing either side's work.

**Did.**

- **Both lines were read before they were merged.** The merge base is `4350a57` (2026-10-28). `origin/main` reached
  `f468e63` on 2026-11-02; this branch reached `c9c3ac6` on 2026-11-05. `main`'s 25 commits are the Business Calculator
  line (builds 0.74-0.76), the Portfolio Lab (builds 1.23-1.29), the institutional market-data providers, the tile
  Close (builds 1.30-1.31), the one-point font increase and the People & Organization - Strategy & Design subject.
- **This branch had already ported `main`'s Portfolio Lab.** `docs/CHANGELOG.md` build 1.59 says so in its own words:
  *"The lab was built on the main line (builds 1.23-1.29) and never reached `corpus/merge-v1` â€¦ Ported, not
  re-invented."* That is why the code conflict resolved to this branch's side in every case: `origin/main`'s
  `index.html` is 5,145 lines against this branch's 10,334, its tile Close is the older `rememberTileGroup` /
  `closeTileView` pair that this branch replaced with the tile-close shim (same behaviour, later design), its font
  sizes are this branch's plus one point on the body â€” which this branch then *reduced* by one point on the owner's
  word of 2026-11-03 and pinned in the test â€” and its `marketdata.py` is this branch's file without the third
  provider in the chain.
- **Fourteen conflicts, each resolved deliberately.** `web/index.html` (27 hunks) and `mockup/business-calculator.html`
  (18) took this branch's side; `api.py` (4), `marketdata.py` (3) and `instruments.py` (2) took this branch's side
  because it is a strict superset â€” `api.py` keeps the fail-closed unknown-route refusal and the cleanup that deletes
  an instrument whose first price could not be sourced, and `instruments.py` keeps the whole B-178 guidance, the
  reference list and the example books; `source_env.py` took **both** sides, so the allowlist carries this branch's
  payment and bundle-handoff entries *and* `main`'s two market-data keys; the six documents took this branch's side,
  because each of `main`'s entries is already superseded here (the People shelf in 1.56, the Portfolio Lab in 1.58
  and 1.59, the Close redesign in 1.66 and 1.68).
- **Two checks were ported, not dropped.** `main`'s tile-Close check now pins the shim's own pieces â€” the same
  behaviour, the later implementation. `main`'s tracked-instrument store class (`create`, `record`, the same-day
  dedupe, the returns series, readiness, the fail-closed edges, the provider selection and the routes) is kept whole
  against this branch's API, which is compatible.
- **One compatibility fix.** `main` loads the Massive key as `BP_MASSIVE_API_KEY`; this branch reads `BP_MASSIVE_KEY`.
  The allowlist keeps `main`'s name, because its test pins it, and the market-data layer now accepts either â€” so the
  key in `Backend/.env` reaches the provider under whichever name it was loaded.
- **The `.scratch/` directory is now ignored.** Two of the archives in it are 345 MB each, and GitHub refuses any blob
  over 100 MB, so a stray `git add -A` would have failed the push outright.

**Did not move.** No method, preset, input, check, computed number or frozen-core entry changed. The frozen contract
is untouched.

**Verified.**

- The merged tree runs 3869 tests: 24 failures and 1 error. The pre-merge baseline of this branch ran 3847 tests with the same 24 failures and the same 1 error, and the failing test ids are identical on the two sides - 0 only in the baseline, 0 only in the merge - so the merge added 22 tests and changed no outcome. Those failures are the ones recorded in `docs/OPEN_ISSUES.md` item 18; the suite is not green by design and was not green before the merge.
- The files `main` contributed that were missing here are present after the merge: the People & Organization -
  Strategy & Design worksheets and before-briefings (Lewin, Galbraith, Mintzberg), `catalogue/slice.json`,
  `catalogue/register.mjs`, the root `CHANGELOG.md` and `DECISIONS.md`, `tests/`, `wiring/`, `run-suite.mjs`,
  `scripts/tile_close_browser_test.py`, and the two institutional market-data keys in `Backend/.env.example` and in the
  credential allowlist.

## 2026-11-05 â€” [statements] The tile refuses what declares nothing, and the boundary import is relative

**Ask.** The statements tile answers basic accounting problems badly: it should refuse what it cannot read, not present
a set of statements. Fix what is understood, and hold the rest for the owner.

**Did.** Three defects in `src/bp/product/statements.py`, and one stale assertion corrected on the owner's instruction.

- **The boundary rule (three tests).** `solve()` imported `bp.product.income_statement` absolutely, which the product
  boundary reads as the product reaching into the frozen core. It is now `from .income_statement import ...`. The three
  boundary tests (`test_product_boundary` Ã—2, `test_product_statements_api.RouteTest`) are green.
- **A computation that computed nothing does not answer (one test).** `solve()` now records
  `computation_named = bool(fc.detect_sections(text)) and not _reads_as_trial_balance(text)` and, when the engine
  produced nothing and no transaction can be posted, raises the refusal **before** the plan layer or the model can
  answer: *"this names a financial computation, but the instruction declares none of the figures it needs; state the
  figures and the tile will compute them"*. Before the fix the same text was answered by the model as a transactions
  problem once `bp.server` had wired the tile â€” which is why the test passed alone and failed in the suite.
  `qa/manual/probe_route_test_order.py` now refuses in both configurations.
- **A sentence that declares nothing had been answered with a full set of zero statements (four tests).** With the plan
  layer attached, the workbench's configuration, `_solve_narrative` built a plan with no entries, posted it to the
  ledger, and returned statements whose every figure was zero, marked `solved`. Three shapes showed it: `"hello there"`,
  a trial-balance header with no rows, and `"Cash 5,000"`. `_solve_narrative` now refuses when no line of the extracted
  entries or adjustments carries a non-zero figure â€” *"this instruction names no transaction and declares no figure, so
  there is nothing to postâ€¦"* â€” which is the "gaps are named, never filled" rule applied to an empty reading. The four
  route tests that were red on this are green. Evidence: `qa/manual/probe_empty_instruction.py`.
- **The keypad contract (one test), on the owner's decision.** `e4184a8` removed the `management_accounts` special case
  from `web/index.html:calcFitOf` deliberately; the committed test still asserted it. The owner chose to correct the
  test, not the page: it now asserts the current fit rule, that `engagement_spec` takes the list/JSON path, and that the
  special case does not appear at all.

**Verified.**

- **The statements lane.** `tests.test_product_statements`, `â€¦_api`, `â€¦_tile`, `â€¦_council`, `test_statement_reader_seams`,
  `test_statement_plan`, `test_financial_computations`, `test_product_boundary` â†’ **198 tests, OK**;
  `tests.test_product_subjects` â†’ **54 tests, OK**.
- **The product families.** `discover -p "test_product_*.py"` â†’ 564 tests, 2 failures, both red at HEAD before this
  session (the two committed-slice drift tests).
- **The full suite, measured against HEAD `f1bb0c5`.** `Ran 3828 tests`, `FAILED (failures=19, errors=38)`; the HEAD
  measurement in `docs/OPEN_ISSUES.md` Item 18 was 27 failures / 38 errors on the same 3828 tests, so this session
  **fixes nine and adds no failure** (and the stale `unittest.loader._FailedTest.test_academic_docx` load error is gone
  too). The separation was read by test id from the two run logs, not by counting lines.
- **One flake surfaced, and it is not this session's.** `test_product_compare.CompareTest.test_the_html_export_copies_the_stored_values`
  failed in that run only because the generated case id â€” `51528e75999b` â€” contains the `'999'` the test forbids in the
  exported HTML; it passes alone (5 tests, OK). It is a name-level flake in that test, recorded in
  `docs/OPEN_ISSUES.md` Item 18 rather than fixed here.

**Not done, and named.**
- **The golden-engagement cluster** (the `accounts` preset carries a richer chart and the statement modules append their
  own accounts to a copy of it, so `chart[11]: duplicate account code 1200` follows) is older than this session and
  belongs to that lane; the fix is the fixture split, not a code change here.
- **Two committed-slice drift tests** (`test_product_calc_router.InputSliceDriftTest`,
  `test_product_explain.ContractSliceTest`) are red at HEAD and untouched here.

## 2026-11-05 â€” [computation] The measurement is re-run on pinned trees, and the documents are corrected to it (build 1.99)

**Ask.** Finish the increment: update the manual to the true current state, update CHANGELOG/WORKLOG/HOME/HANDOFF and the
build number, run the final full suite on the working tree, write the HEAD-vs-working-tree comparison, and land the
increment as one commit.

**Did.**

- **The measurement is a script, and every tree it runs on is pinned.** `qa/manual/suite_measure.ps1` builds each
  baseline with `git archive`, snapshots the working tree, and runs the suite in all three;
  `qa/manual/suite_treehash.py` proves a copy byte-exact by comparing its git tree hash with its commit's own tree
  hash; `qa/manual/suite_compare.py` turns the three runs into the separation of pre-existing from new.
  **The earlier comparison for this increment was measured on a tree that matches no commit in this history** â€” its
  `src/bp/product/statements.py` is `c4e98db`'s blob while it has no `statement_chart.py` at all â€” so the word "HEAD"
  in it was wrong by the time the suite ran, and the failure it called "new, and it is not mine" was measured against a
  tree that was never HEAD.
- **Three trees, three numbers.** The pre-increment baseline `d938095` (build 1.98), the current HEAD `f1bb0c5`, and a
  snapshot of the working tree: **3784 tests / 25 failures / 40 errors** at the baseline, **3828 tests / 27 failures /
  38 errors** at HEAD and at the working tree. The working tree is measured **in the snapshot**, so a second session
  working in the same tree cannot move the numbers underneath the measurement.
- **The increment fixes five and brings five.** Against the pre-increment baseline: **58 pre-existing**, **5 fixed** (the
  detector's `decimal.InvalidOperation` crash in two tests, the runtime's ok-path, the detector contract, and the served
  build number), **5 new**. The five new are named in `docs/OPEN_ISSUES.md` (Item 18): three are the product-boundary
  rule (`src/bp/product/statements.py:1084` imports `bp.product.income_statement` absolutely, and the boundary tests
  read that as the frozen core â€” a one-line relative import closes all three), one is the calculator's keypad contract
  (`e4184a8` changed the fit rule and the committed test still asserts the old line), and one is this increment's own
  new test, which passes alone and fails in the suite because `bp.server` wires the product module.
  **The increment adds 44 tests and five new failures.**
- **The claims that were wrong are corrected, not deleted.** The 1.99 changelog entry, the entry below, and
  `docs/FINANCIAL_COMPUTATIONS_MANUAL.md` now say what the suite does: the old comparison's "HEAD" was the
  pre-increment commit; "1 is new, and it is not mine" was wrong in both halves â€” it is this increment's, and it came
  from a committed change; "adds 44 tests and no new failure" was wrong; "`web/index.html` is not in this build" was
  wrong, `e4184a8` carried the calculator's fit-class change into it; and "a route that computes nothing does not
  answer" holds only while the product module is unwired.
- **The measurement scripts are committed, so the next one is a run and not an argument.**
  `qa/manual/suite_measure.ps1`, `qa/manual/suite_treehash.py`, `qa/manual/suite_compare.py`,
  `qa/manual/suite_count_gap.py` and `qa/manual/probe_route_test_order.py` are the evidence.

**Verified.**

- **The suite, three ways.** The numbers above, from `qa/baseline/seam-suite-comparison.txt`.
- **The docs-state contract.** `tests.test_docs_sync.py` â†’ **8 tests, OK** after the edits: the count in `docs/HOME.md`,
  `docs/HANDOFF.md` and `docs/CONTRIBUTORS.md` is the real 3828, and the build in `src/bp/build.py`, `docs/HOME.md`,
  `docs/HANDOFF.md` and the newest changelog entry is 1.99.

**Not done, and named.**

- **The five new failures** â€” `docs/OPEN_ISSUES.md` Item 18. Three of them want a one-line code change; the keypad one
  is a behaviour decision; the reader-seams one is a decision about what the route should do in the shipped
  configuration. None is fixed here.
- **The 40 golden-engagement errors are still red**, and they are older than this increment: `src/bp/server.py` and
  `src/bp/accounts.py` are unchanged by it, so the `accounts` preset that carries the richer chart â€” and the
  `chart[11]: duplicate account code 1100` that follows â€” was already there at the pre-increment baseline. The fix is a
  split of the fixture between the two families of tests, and it belongs to whoever owns that lane.

## 2026-11-04 â€” [computation] The reader stops refusing what it can read (build 1.99)

**Ask.** Finish the work in flight: (1) run the full suite on HEAD and on the working tree and separate the
pre-existing failures from the new ones; (2) update the owner's case study with the re-measured income statement;
(3) write the notebook entry; then update the manual.

**Did.**

- **The reader's seams are closed, and the measurement is a script, not a claim.** `qa/manual/reader-seams-probe.py`
  runs the seven reproductions. A narrative that opens with a transaction date gets `2025-01-01` to `2025-12-31`
  (was one day); a fiscal year whose start and end are both stated reads as one period (was two); a transaction date
  on a line is not a comparative; Salaries and Rent arrive on their own lines; a stated sales figure beside prose
  reads as Revenue; a partition the text states is proved by code and accepted; and every code a detector posts to
  has a home in the one chart (`src/bp/statement_chart.py`).
- **The deterministic reader no longer crashes on an ordinary sentence.** "paid 8,000 cash salaries" matched the
  second wording of the `salaries_payment` detector, whose template reached for the first slot, so the entry carried
  no amount and the posting died on an uncaught `decimal.InvalidOperation`. The slot that is filled wins; a line
  with no amount is a named `DetectError`. **This crash was on HEAD** â€” the suite comparison is what proved it was
  not mine â€” and it is why the notebook's claim that the narrative solved "with a model configured" was half true:
  the model was never what made that narrative work.
- **"Invested 50,000 cash in the business for shares" is read.** The detector wanted "in exchange for" or nothing,
  so the equity issue was missed, cash went negative, and the ledger refused the whole answer.
- **A trial balance keeps its route.** "â€¦and also compute the liquidity ratios" reached the balance-sheet-analysis
  engine, which printed total assets **86,900** where the trial-balance route prints **77,900**, and hid the income
  statement. The more specific reading wins now.
- **Four defects in the 128-spec computation engine, none of them visible from the source.** One spec was labelled
  **"Peso/Dollar Change"** (a home-currency name in a global product); eight input patterns captured a word instead
  of the number; the topological sort resolved nothing because it looked dependencies up by spec id while
  `depends_on` names output names; and values did not travel between sections, so seventy-two specs reported a gap
  for something already known. `tests/test_financial_computations.py` (new) holds all of it.
- **A route that computes nothing does not answer â€” while the product module is unwired.** The engine returned a record
  even when it had computed nothing, so it answered with a sheet of gaps in place of the reader's answer. It now hands
  the instruction back. **The test that proves it passes alone and fails in the suite**, because `bp.server` wires the
  product module and a wired module answers that instruction on the transactions route instead of refusing, so the test
  exercises a configuration the product never ships in. It is named in `docs/OPEN_ISSUES.md` (Item 18) and is not fixed
  here.
- **The documents are rewritten to the measurement.** The manual claimed "2 pre-existing failures only" where the
  suite has 65; claimed the narrative reader "REQUIRES a configured LLM" when the deterministic layer reads a narrative;
  and claimed the integrated case solver was "NOT BUILT" when it is six seams, all closed. The case study is
  re-measured, and its two recorded defects (ratios at 28 decimals, brought-forward retained earnings labelled
  "other") are fixed, so the case now says so.

**Verified.**

- **The suite, three ways, on trees that are pinned.** A byte-exact copy of the pre-increment commit `d938095` (build
  1.98), a byte-exact copy of the current HEAD `f1bb0c5`, and a snapshot of the working tree. A copy is proven
  byte-exact by comparing its git tree hash with its commit's own tree hash (`qa/manual/suite_treehash.py`), and the
  suite is run by `qa/manual/suite_measure.ps1`. **The pre-increment baseline: 3784 tests, 25 failures and 40 errors;
  the current HEAD: 3828 tests, 27 failures and 38 errors; the working tree: 3828 tests, 27 failures and 38 errors.**
  Against the pre-increment baseline, of the 63 tests that fail in the working tree: **58 are pre-existing** (fail on
  both), **5 are fixed by this increment** â€” the detector's `decimal.InvalidOperation` crash in two tests
  (`test_credit_sale_detected`, `test_northstar_transactions`), the runtime's ok-path, the detector contract, and
  `test_the_served_build_is_the_newest_changelog_build`, which found `bp/build.py` claiming 1.97 against a changelog at
  1.98 â€” and **5 are new**. **This increment adds 44 tests and five new failures.** The five are the three
  product-boundary failures (`src/bp/product/statements.py:1084` imports `bp.product.income_statement` absolutely, and
  the boundary rule reads that as the frozen core), the calculator's keypad contract
  (`test_the_keypad_is_off_for_list_and_worksheet_tools` â€” `e4184a8` changed the fit rule and the committed test still
  asserts the old line), and this increment's own `test_a_route_that_computed_nothing_does_not_answer`, which passes
  alone and fails in the suite because `bp.server` wires the product module. Against the **current HEAD** the working
  tree changes nothing: 0 new, 0 fixed. The 40 errors are the plan layer's golden engagements, all with the same root
  cause (`chart[11]: duplicate account code 1100`), and they are older than this increment: `src/bp/server.py` and
  `src/bp/accounts.py` are unchanged by it. The separation is in `qa/baseline/seam-suite-comparison.txt`.
- **The new tests.** `tests.test_financial_computations` â†’ 16 tests; `tests.test_statement_reader_seams` â†’ 25;
  `tests.test_statement_detect` â†’ 3 new (the two wordings of a figure, and the named failure). The increment's own
  modules: **67 tests, OK** when they are run on their own. **One of them is red in the full suite** â€”
  `test_a_route_that_computed_nothing_does_not_answer` â€” because `bp.server` wires the product module; see
  `docs/OPEN_ISSUES.md` (Item 18).
- **The case, over HTTP, with no model configured.** A five-clause transactions narrative â†’ **201 solved**, 11 of 11
  checks, the period from the text's own dates, rent and salaries on their own lines. An exam question with a
  preamble â†’ **201 solved**. A trial balance plus the ratio line â†’ **201 solved**, the three statements and 13
  ratios. An adjustments narrative â†’ 400 "no model is configured" (an honest gate, not a misleading refusal). A
  cash-flow narrative â†’ 400, naming the account that does not close, in 0.0 s (it took 16.9 s before). EUR â†’ 400,
  USD only.
- **The seams, as a script.** `python qa/manual/reader-seams-probe.py` â†’ seven of seven closed, exit 0. It did not
  run at all before: its `ROOT` pointed one directory too high, and so did the case-study script beside it.

**Not done, and named.**

- **The engine's vocabulary.** Of the 218 distinct input names the 128 specs declare, **44** can be supplied by a
  text, **50** by another spec's output, and **131 by nothing at all** â€” so 43 of the 128 specs have no reachable
  input. Closing that gap means writing a parse pattern for each of the 131 names, and **each pattern is a judgement
  about what a student writes**. That is an owner's decision, not a mechanical task, and it is now written down
  instead of implied.
- **The adjustments still need a model.** Depreciation conventions, prepaid amortisation and tax are derived by the
  plan layer's model step. A key opens that door; it does not repair the reader, which no longer needs it.
- **The plan layer's golden engagements still fail** â€” 40 errors in the bad-debt, OCI, revaluation, disposal,
  deferral and depreciation-method modules, all with the same root cause: `EngagementError: chart[11]: duplicate
  account code 1100`. The helpers in those modules build an engagement from the `accounts` preset and **append**
  `1100 Trade receivables` to its chart; the preset's chart now carries that account already, so the append
  duplicates it. It is a stale test helper, not a product defect â€” and it is **older than this increment**, because
  `src/bp/server.py` and `src/bp/accounts.py` are unchanged by it, so this increment neither caused nor fixed it. It
  is the largest group of red in the tree and somebody owns it.
- **`web/index.html` is in this build, and it carries the calculator's fit-class change.** Commit `e4184a8` brought the
  sticky shell and the `management_accounts` fit class into the tree, so the earlier note that the file "is not in this
  build" was wrong. The change itself is deliberate â€” `management_accounts` now runs the same frozen ledger kernel as any
  other method, so its `engagement_spec` input fits the "takes a list / JSON form" path â€” but the committed test still
  asserts the old line, and that is why `test_the_keypad_is_off_for_list_and_worksheet_tools` is red. It is named in
  `docs/OPEN_ISSUES.md` (Item 18).

**Learned.** Four defects in a module with no test module is not a coincidence â€” it is what "no test module" means.
The engine's formulas were complete and its behaviour was unknown, and the four defects were each invisible from
reading the code: a label, a capture group, a key used for a lookup, and a scope that stopped one value short. A
crash is also a measurement: the notebook said the narrative solved, and it did not, and the only way to know was to
run the sentence through the reader. And the routing defect was the most embarrassing of the three, because it made
**the same trial balance print two different balance sheets** â€” a confidently wrong number, which is the one thing
this repository is not allowed to do.

## 2026-11-08 â€” [computation] The open gaps close: vocabulary, classifier, opening balances, live OpenCode Go (build 1.121)

**Ask.** "close the open gaps. live mode is opencode go" â€” the four gaps the 1.119 manual named, and the live reader configured against the funded OpenCode Go account.

**Did.**

- **Vocabulary â€” closed.** Every *raw* input the 128 specs declare (168 distinct names that are never another spec's output) now has a pattern in `COMMON_PATTERNS`, added through `_EXTRA_PATTERNS` and a `_p()` helper that builds a word-bounded `label [of|is|was|:] amount` pattern. A rich sample (beginning inventory, purchases, ending inventory, accumulated depreciation, depreciation expense, other income, taxable income, dividends declared, cash receipts, debt repayments, number of years) parses all of them. Two false-positive traps found and fixed: `depreciation_expense` read "accumulated depreciation" (9000 instead of 3000) until a negative lookbehind was added, and `payments` read "repayments" until every label got a `\b` word boundary. The 42 inputs that are another spec's output (capex, gross profit, ebitda) are computed, not parsed â€” correctly.
- **Classifier â€” built.** `src/bp/product/problem_type.py` names the Tip 5 type (1â€“7) in every record as `tip5_type`. Order is specific-to-general: error correction (4), an explicit missing raw figure (2), ratio analysis (3), any other reconstruction (2), trial balance (6), cash-flow statement (5), integrated case (7, three+ transaction cues), preparing from transactions (1). Two ordering bugs were found by the tests: "Compute the current ratio" was read as a reconstruction because "equity ratio" contains "equity"; fixed by excluding ratio targets from the raw-figure check.
- **Policy layer â€” `balances` key.** The extract contract gains `balances` (opening balances stated as a list); `to_opening()` turns them into one entry marked `opening: true`, so the trial balance carries them but the cash-flow movement does not count them as a receipt. `_solve_narrative` passes it through.
- **Live reader â€” OpenCode Go.** `bp.server._load_opencode_env()` reads `Backend/.env` and maps `OPENCODE_API_KEY` â†’ `BP_OPENGO_API_KEY`, `LLM_PROVIDER` â†’ `BP_LLM_PROVIDER`, `PROSE_MODEL` â†’ `BP_LLM_MODEL`, the tier models, and the council model, when the `BP_*` names are unset. A live call returned "OK" from `deepseek-v4.1-flash`.
- **Case solver completeness.** `CaseResult.unused_amounts` names a stated figure no entry uses. When a model is configured, `solve()` runs the case solver once, and an incomplete case skips the older `_solve_transactions` path so the model reads the whole narrative instead of answering with half a ledger. Proved live: "received a government grant of 50,000 and bought a delivery van for 30,000" returned other income 50,000, total assets 50,000, 11/11 checks â€” the grant was read by the model, not dropped.
- **More patterns/relations.** Six more error-correction patterns (prepaid expensed in full, sale/purchase/interest/wages not recorded) with their signed effects; four more reconstruction relations (quick, cash, debt, equity ratios, return on common equity).
- **Fixture isolation.** `product_statements_fixture.record()` now calls `statements.reset_core()` first, so a test that imported `bp.server` (which attaches guards and the case solver) cannot leak into the frozen fixture. The fixture regenerates byte-identically.

**Verified.** `tests.test_financial_engines` â†’ **37 tests, OK** (reconstruction, error correction, case solver, guards, vocabulary, classifier). The statements sweep (13 modules) â†’ **285 + 8 subtests, OK**. `test_docs_sync` â†’ 8, OK. The frozen fixture regenerates byte-identically. Live extraction and a live `solve()` proved against OpenCode Go. Suite count **4299**.

**Not done, and named.** The classifier is cue-based, not a model reading; a text with no cue is `type=None`. The policy layer still lets the model guess at timing (a per-policy provenance tag is the remaining piece). The error/reconstruction sets are the common cases, not exhaustive. The guards G12/G16/G17 report `not_applicable` outside their context.

**Learned.** A generic label pattern is a substring trap: "depreciation" lives inside "accumulated depreciation", "payments" inside "repayments", "equity" inside "equity ratio". Word boundaries and two negative lookbehinds fixed the first two; the third was a classifier ordering bug, not a vocabulary one. And a test that imports the server pollutes the global core â€” the fixture must reset it, or the fixture's bytes depend on test order.

## 2026-11-08 â€” [computation] The four problem engines, and the guards that decide whether a record leaves the building (build 1.119)

**Ask.** "yes, build them" â€” build the four remaining capabilities that the living manual named: the reconstruction engine (Tip 5 Type 2), the error-correction engine (Tip 5 Type 4), the integrated case solver (Tip 5 Type 7 / Tip 6), and the 22 guards (Tip 7), so the tile handles any financial-statement problem without fabricating a figure.

**Did.**

- **`src/bp/product/reconstruction.py` (new).** A relation is a formula with named variables: linear (`a = b + c âˆ’ d`) solves for any variable by moving terms, ratio (`ratio = numerator / denominator`) solves for the ratio, the numerator or the denominator. `solve_for` returns the first relation that reaches the target; `solve_all` chains solved values so COGS feeds gross profit feeds gross margin; `cross_check` looks for a second relation that agrees. 20 relations cover COGS, net sales, net purchases, gross profit, net income, A = L + E, ending RE, working capital, CFO, and the common ratios. The route `_solve_reconstruction` parses "label is amount" sentences (splitting on sentence boundaries and "and", stripping connectors) into canonical knowns; a target no relation can reach is a gap.
- **`src/bp/product/error_correction.py` (new).** Six registered error patterns (equipment expensed, unearned revenue, depreciation omitted, ending inventory overstated, accrued expense omitted, capex charged to repairs) each declare the correcting debit/credit and the signed effect on net income, assets, liabilities and equity. `correct(text)` detects and builds; `correct_stated(original, correct)` computes `correct âˆ’ original`; a missing amount is a named gap. The route `_solve_error_correction` reports the correcting entry and the effect, and checks that the effect keeps the accounting equation.
- **`src/bp/case_solver.py` (new).** The nine-stage state machine INGEST â†’ PARSE â†’ DETECT â†’ RESOLVE â†’ JOURNALIZE â†’ POST â†’ ADJUST â†’ PROJECT â†’ VALIDATE. Every stage records its outcome; the first refusal returns `status="review"` naming what it expected. The deterministic template layer supplies the journal; `statement_plan.build` supplies the projection and the articulation gate. The route `_solve_case` adds the `stage_trace` to the record.
- **`src/bp/guards.py` (new).** One runner over all 22 Tip 7 guards. A guard that cannot run is `applicable=False`; a guard that raises is `ok=False`. The correctness guards (G1â€“G9, G13, G18, G21) block the record; the trust guards are recorded. Injected from `bp.server` as `_core("guards")`, so the product package imports no core module.
- **Two detector gaps found while proving the case solver, and closed with trap tests.** `sold goods for 9,500 cash` was matched by `asset_disposal` (specificity 80), whose template credits **PPE** â€” a sale of inventory recorded as a disposal of property. It is now `goods_sale_cash` (Dr Cash, Cr Revenue), and `asset_disposal` is tightened to name a real asset (equipment, machine, vehicle, land, building, furniture, plant). A bare `started the business with 20,000 cash` had **no detector at all**; it is now `capital_contribution` (Dr Cash, Cr Capital). `paid rent of 1,200` did not match `rent_payment` (which wants "paid 1,200 cash rent"); it now matches `rent_payment2`.
- **The guards found a genuine defect in the transaction record.** G14 (audit trail) failed because a transactions record carries its provenance in the journal, not in a separate `figures` list. G14 now counts the journal and the spec entries as the audit trail. G2 (decimal arithmetic) failed on non-numeric scalars (the assumption manifest, the spec); it now checks only values that look like numbers.

**Verified.** `tests.test_financial_engines` â†’ **27 tests, OK** (reconstruction, error correction, case solver, guards, plus the detector trap tests). The statements sweep (`test_statement_plan`, `test_statement_reader_seams`, `test_product_statements`, `test_product_statements_api`, `test_schedule_routes`, `test_statements_render_contract`, `test_product_boundary`, `test_financial_engines`, `test_statement_runtime`, `test_statement_detect`, `test_statement_detect_contract`) â†’ **251 + 8 subtests, OK**. The council/tile/reperform/equity/OCI modules â†’ **50, OK**. Measured end to end through the tile with the core attached: a correction ("Equipment costing $50,000 was expensed instead of capitalised") â†’ correcting entry, NI +50,000, assets +50,000, equation holds; a reconstruction ("COGS 55,000, beginning 10,000, ending 15,000, find the net purchases") â†’ net purchases 60,000; an integrated case ("started with 20,000; sold goods 9,500; paid rent 1,200") â†’ nine stages all OK, net income 8,300, total assets 28,300, **13 guards pass, 0 fail**.

**Not done, and named.** The reconstruction vocabulary is the declared relations, not every identity in the computation document; a target outside the set is a gap. The error-correction engine recognises six patterns, not every error an examiner can write; an unrecognised error is a review, not a guess. The case solver's coverage is the detector layer's coverage: a transaction with no detector is a review naming the unmatched claim. The guards are wired; the 22 are not all fully exercised by fixtures (G12 scale, G16 grading, G17 generation report `not_applicable` outside their context).

**Learned.** A detector that matches a *verb* ("sold") without a *noun class* ("goods" vs "equipment") will classify a sale as a disposal, and the template then credits the wrong account â€” the arithmetic is internally consistent and the statement is wrong. The trap test that asserts `sold goods` never matches `asset_disposal` is the cheap way to keep it fixed. And a guard runner is only a gate if a guard that cannot decide reports `applicable=False` rather than passing: the two bugs the guards found in their own debut were both "the guard was checking the wrong field".

## 2026-11-04 â€” [design] The statements workbook is a workbook (build 1.98)

**Ask.** "You own the Excel workbook the student downloads." â€” replace `_accounting_rows()` in `src/bp/product/spreadsheets.py` so each requested statement is its own sheet of typed cells (label in column A, amount as a number in column B), add the missing statement of changes in equity, give the working papers and the notes their own sheets, honour `record["requested"]`/`record["hidden"]`, keep `to_xlsx` hand-rolled and byte-identical, and hit the acceptance list in `docs/MINIMAX_STATEMENT_RENDER.md`. The computation lane is frozen; do not recompute anything.

**Did.**

- **`_accounting_rows()` is replaced.** One sheet per requested statement (`Income statement`, `Changes in equity`, `Balance sheet`, `Cash flow`), then `Working`, then `Notes`. Labels in column A, amounts as **numbers** in column B (right-aligned), detail rows indented one level, group headings bold, subtotals bold with a top rule, totals bold with a double bottom rule, a blank row between sections and never between a subtotal and its total, the header frozen, column A as wide as its longest label, no merged cells. The amount format follows the record's places: `#,##0.00;(#,##0.00)`.
- **The statement of changes in equity is a sheet**, built from `appendix["equity_statement"]` (opening balance, each movement with its kind and what it was, closing balance, per account) and not reconstructed from the balance sheet.
- **The Working sheet** carries the journal (date, description, account, debit, credit), the trial balance (account, debit, credit, totals), the checks (name, PASS/FAIL, detail), the cash-flow reconciliation and the reconciliation statement when the record carries one. The Notes sheet is the record's notes text, verbatim. No hash, no entry marker (B-199).
- **The request decides the sheets.** The appendix now carries the request's audit trail (`requested`, `hidden`, and why a cash flow was withheld), because the workbook is built from the appendix alone. A statement computed but not asked for is not a sheet; an IS-only request gives exactly one statement sheet; a withheld cash flow is absent and the working papers carry the reason.
- **A computation-lane carry, named (the one thing this lane could not do alone).** The income statement's "Operating expenses 67,500" existed in the record **only as text** â€” the record held its four accounts (38,000 + 12,000 + 5,500 + 12,000) but never their line total, so a renderer could only have produced that cell by summing the accounts above it, which is the invented figure the contract test exists to catch. So the computation lane now carries what it already computed: `ledger.income_groups()` (the income statement's lines and totals by the chart's statement line, which `report.income_statement` already printed), `appendix["engagement"]` (period, currency, places) and `appendix["cash_flow"]["opening_cash"]`/`["closing_cash"]`. `report.income_statement` reads its totals from the same place, so the figure is computed once. No figure changed, no check was loosened, the statement texts are byte-identical, and the fixture was regenerated through the one correct script.

**Verified.** `tests.test_statements_render_contract` â†’ **13 tests, OK**; `tests.test_product_boundary` â†’ **OK**; `qa/manual/demo_statements_workbook.py` (new) opens the workbook through `tests/xlsx_read.py` and proves the acceptance list end to end: typed cells on all four statement sheets, the income statement foots to the record's net income (200,000 âˆ’ 147,425 = 52,575), the balance sheet balances (75,525 + 102,575 = 178,100), **the three cash-flow reconciliations hold** (74,600 âˆ’ 60,000 + 90,000 = 104,600; the direct and indirect routes agree; ending cash 104,600 less opening 0 is the change, and it is the balance sheet's cash line), a withheld cash flow is absent with its reason on the working sheet, an IS-only request gives one statement sheet, two exports are byte-identical, and no figure on any sheet is a figure the record does not hold.

**No regression.** Every test module that touches the changed code was run twice â€” on a pristine copy of HEAD and on HEAD plus these changes â€” and the results are identical: the 31 accounting/statements/export modules give the same **4 failures** on both, and the 11 core ledger modules (period chaining, revaluation, OCI, balance-sheet sections, bad debt, deferrals, disposal, depreciation, reversals, journal view, schedules) are **OK** on both, 239 tests in all.

**Not done, and named.** The workbook is not yet wired into the tile's download: the statements export route still offers text only, and the case bundle for a statements record still has to carry the appendix for the workbook to be produced. The classic `management_accounts` download now renders the same statement sheets (its appendix is the same block), which is a change in that export's appearance, not only in the statements tile.

**Seen on the way, and not mine.** The working tree already carried uncommitted edits to `src/bp/server.py` and `src/bp/product/subjects.py` (the calculator shelf's tool order, and several presets emptied â€” `abc`, `salesvar`, `multibreakeven` and the accounts preset's inputs). They break 39 tests in the accounting/equity/t-account/acceptance/API modules **before any of this work is applied**. Verified by running the same 31 modules on a pristine copy of HEAD (4 failures) and on HEAD plus these changes (the same 4 failures) â€” so this work adds none â€” and then on the working tree (39 failures, all traceable to those two files). Those edits are somebody's in-flight work and were left untouched.

**Learned.** A record that renders a figure as text but does not hold it as a value is a trap for a renderer, and no amount of care in the renderer can get past it: the only honest options are to sum the accounts (an invented figure) or to ask the computation lane to carry what it already computed. Checking `typed_numbers(record)` against the statement's own lines *before* writing a line of code is what found it â€” and it is the check that will keep it found.

## 2026-11-04 â€” [owner tip] Tip 5 recorded: how to solve problems involving financial statements

**Ask.** The owner pasted the full problem-solving framework (universal five steps; seven problem types â€” preparing from transactions, reconstructing missing figures, ratio analysis, error correction, cash-flow statement, from a trial balance, integrated cases; common pitfalls; compact checklist) and said they might add more later.

**Did.** Appended it verbatim as **Tip 5** to `docs/TIPS_FINANCIAL_STATEMENTS.md` under a `## Tip 5` heading, with a short note that this points at a broader problem-solving *mode* the tile does not yet cover (reconstruction, ratio analysis, error correction, integrated cases), deferred until the render lane lands.

**Noted.** The tile today only prepares statements from a narrative; Tip 5 names the gap, it does not close it. No code change.

**Ask.** "a. when youre done, we will tackle handling problems in financial statements" â€” start the render lane properly: cut a frozen record and a harness so MiniMax builds against a fixed target.

**Did.**

- `tests/fixtures/statements-record.json`: one solved engagement, all four statements rendered, eleven core checks passing, net income 52,575, total assets 178,100, cash flow 104,600. Built from the golden engagement through the real plan layer with the extraction step stubbed, so it needs no key and cannot drift with the clock.
- `tests/product_statements_fixture.py`: the deterministic builder plus `typed_numbers()`, the set of figures the record holds as values (text renderings excluded).
- `qa/manual/make_statements_fixture.py`: the one correct way to regenerate it after an intended change.
- `tests/xlsx_read.py`: unzip-and-read harness (inline strings, shared strings, numeric cells), with `amount()`, `line_value()`, `statement_rows()` and `numbers_in_text()`.
- `tests/test_statements_render_contract.py`: 13 tests, including the one that matters â€” every figure in a workbook produced from the record must be a figure the record holds, so a renderer that computes its own total fails.
- Found a gap while proving it: the current Excel export **omits the statement of changes in equity**, because it copies `statements_export` and the equity text lives in `appendix.equity_statement_export`. Named in the brief, not silently patched.

**Verified.** `tests.test_statements_render_contract` â†’ **13 tests, OK**; rendered fixture regenerates byte-identically; suite count **3708**.

**Not done, and named.** The workbook itself is still the design lane's (one text sheet, no equity sheet, numbers stored as text). The fixture is a record, not a workbook: nothing here changes what the tile shows today.

**Learned.** The cheapest way to keep a hand-off contract honest is to make the fixture *regenerate* inside the test. A fixture that is only read can rot quietly; a fixture that must reproduce itself fails on the same commit that changes it.

## 2026-11-04 â€” [computation] The statements render only what the request names (build 1.96)

**Ask.** "continue" â€” finish the Financial statements tile so it can solve a request for one statement (or a subset), then hand the render layer to the design lane.

**Did.**

- **Tip 3, adopted.** Compute scope is not output scope. `present(result, problem_type, requested)` now renders only the requested statements while the ledger is always built in full. The dependency graph (`IS` stands alone; `RE` needs `IS`; `BS` needs `RE`; `CF` needs `IS` + `BS`) is declared in `statement_plan.PROJECTIONS` with `dependency_closure()` and `classify()`.
- **The request is read, conservatively.** `wants_statements()` needs a limiting word ("only", "just", "skip", "without") or a directive verb ("prepare", "show", "give me") in the same clause as the statement name; a mention is not a request. An explicit `statements` argument wins and accepts `IS/RE/BS/CF` or the record keys.
- **The record carries the audit trail.** `requested` / `computed` / `hidden` / `warnings`: a BS-only run reports `computed: ["IS", "RE", "BS"]`, `hidden: ["IS", "RE"]`. `verify_output()` refuses to freeze a record that leaks an unrequested statement or withholds the cash flow without a reason.
- **Export can be one statement.** `POST /api/cases/statements/{id}/export` accepts `{"statement": "BS"}`; a statement the record did not render is a 409 that lists what it did render, and an unknown code is a 400.
- **The boundary violation is fixed.** `statements.py` imported `bp.llm`/`bp.statement_plan` lazily; the plan layer's `extract`/`build` are now injected by `bp.server` like the rest of the core. This repaired five red boundary/scope tests that were failing at HEAD.
- **The plan layer is actually reachable.** Before this build the council reader short-circuited it; now the plan layer is tried first for a narrative, a substantive refusal there is final, and `NoModel` is the only reason to try another reader. A `StatementRefused` (two periods, two entities, a consolidation) is no longer softened into "the reading failed".
- 23 new tests: `RequestTest`, `OutputVerifierTest`, `PlanLayerTest`, and six route tests.

**Verified.** `tests.test_product_statements`, `..._api`, `..._council`, `..._tile`, `test_product_boundary`, `test_statement_plan`, `test_equity_statement`, `test_reperform_statements` â†’ **173 tests, OK** with `DEEPSEEK_API_KEY` cleared. Suite count **3695** (loaded by `TestLoader().discover`). Full-suite run (2026-11-04, build 1.97 tree): **3708 tests, 10 failures, none ours** â€” 4 `test_calculator_acceptance` + 1 `CalculatorGuardTest` from the other lane's `subjects.py` edit that removes `tbcheck` without updating the pinned 206/148 inventory; 1 `ShelfShapeTest` (accounting shelf reaches twelve methods) from the same edit; 3 slice-drift failures (`test_product_calc_router`, `test_product_explain`, and the accounting shelf) that follow from that edit; 1 `test_forecast_report` (network/fixture); 1 `test_brave_failure_falls_back_to_firecrawl` (network). The render contract (13 tests) and docs sync pass.

**Not done, and named.** The render layer is the design lane's (`docs/MINIMAX_STATEMENT_RENDER.md`): the Excel export is still a text dump in one sheet. Plug mode and comparatives are deliberately unbuilt; `classify()` names `requires_plugs` so a future caller can see the shape, and the tile never plugs. Live extraction is proved on two synthetic problems only.

**Learned.** Two readers with two grounding contracts always drift, and the weaker one silently wins if it is tried first. The fix was ordering plus a distinct `NoModel`: "nothing is configured" is retryable, "this amount is not in the instruction" is final.

## 2026-11-04 â€” [computation] Golden suite grows to twenty cases

**Ask.** "go." â€” continue the unblocked computation-lane work.

**Did.**

- Six new golden cases: reducing-balance depreciation, units-of-production depreciation, bad debt expense with a dividend, two prepaids, accrued interest with a loss, and a half-year/pro-rata mix. Every case asserts all three articulation identities. Tip 1's "build ten or twenty of these with different features ... run them on every change" is now satisfied (twenty cases).

**Verified.** `tests.test_statement_plan` â†’ **71 tests, OK**. Suite count 3672.

**Not done, and named.** Multi-period comparatives, consolidated statements, tax benefit on a loss, and the tile copy in `subjects.py` (another lane's file) remain.

**Learned.** The golden suite is the cheapest place to catch a regression in the DAG or the validators: every case is a full build, and a change that breaks any identity fails before it reaches a student.

## 2026-11-04 â€” [computation] Tax benefit on a loss is now a registered adjustment

**Ask.** "go." â€” continue the unblocked computation-lane work.

**Did.**

- **`tax_benefit_on_loss`** (new, in `src/bp/statement_plan.py`): `-pretax x rate` when pretax is negative, zero otherwise. Grounded and validated like every other function. Registered in `FUNCTIONS` and named in the extraction prompt.
- Two new tests.

**Verified.** `tests.test_statement_plan` â†’ **65 tests, OK**. Suite count 3672.

**Not done, and named.** Multi-period comparatives, consolidated statements, and the tile copy in `subjects.py` (another lane's file) remain. Tax benefit on a loss is now computable, but a carryforward policy (years, rate) is still an owner decision.

**Learned.** A loss is not a tax benefit unless the jurisdiction allows a carryback or carryforward. The function computes the arithmetic only; the policy is stated in the problem text or not at all.

## 2026-11-04 â€” [computation] Golden suite grows to thirteen cases

**Ask.** "go." â€” continue the unblocked computation-lane work.

**Did.**

- Six new golden cases in `tests/test_statement_plan.py`: reducing-balance depreciation, units-of-production depreciation, bad debt expense, a prior period carrying forward (opening balances tie to prior closing), a no-adjustment engagement, and the half-year convention. Every case asserts all three articulation identities.

**Verified.** `tests.test_statement_plan` â†’ **63 tests, OK**. Suite count 3672.

**Not done, and named.** Multi-period comparatives (side-by-side columns), consolidated statements, tax benefit on a loss, and the tile copy in `subjects.py` (another lane's file) remain.

**Learned.** The golden suite is the cheapest place to catch a regression in the DAG or the validators: every case is a full build, and a change that breaks any identity fails before it reaches a student.

## 2026-11-04 â€” [computation] Bad debt expense under the percentage-of-receivables method

**Ask.** "go." â€” continue the unblocked computation-lane work.

**Did.**

- **`bad_debt_expense`** (new, in `src/bp/statement_plan.py`): `receivables x rate - prior_allowance`, clamped at zero, grounded and validated like every other function. Registered in `FUNCTIONS` and named in the extraction prompt.
- Two new tests.

**Verified.** `tests.test_statement_plan` â†’ **57 tests, OK**. Suite count 3672.

**Not done, and named.** Multi-period comparatives, consolidated statements, tax benefit on a loss, reducing-balance and units-of-production are now registered; the tile copy in `subjects.py` still over-claims.

**Learned.** Each new adjustment is one function plus one registry entry plus one prompt line. The DAG does not care what the formula computes.

## 2026-11-04 â€” [computation] Two more depreciation methods: reducing-balance and units-of-production

**Ask.** "go." â€” continue the unblocked computation-lane work.

**Did.**

- **`reducing_balance_depreciation`** (new, in `src/bp/statement_plan.py`): declining balance, `(cost - accumulated - residual) x rate`, prorated by the declared convention. Rate defaults to double-declining (2 / life_years) when omitted; a declared rate is accepted; accumulated defaults to 0 for the first year; the result is clamped at zero. Grounded and validated like every other function.
- **`units_of_production_depreciation`** (new): `(cost - residual) x units_this_period / total_estimated_units`, refusing more units than estimated.
- Both registered in `FUNCTIONS`, both named in the extraction prompt with their parameters, both covered by five new tests.

**Verified.** `tests.test_statement_plan` â†’ **55 tests, OK**. Suite count 3672.

**Not done, and named.** Multi-period comparatives (prior-period statements side by side) and consolidated statements are still out of scope; the tile copy in `subjects.py` still over-claims.

**Learned.** A depreciation method is just another registered function: the DAG does not care whether the formula is straight-line, declining-balance or units-of-production, only that the parameters are stated and the amount is computed once, in code.

## 2026-11-04 â€” [computation] The tile now derives the adjusting entries, not only the stated ones

**Ask.** "go." â€” wire adjustment derivation into the extraction boundary so the tile computes
prepaids, depreciation, COGS and tax from the text, not only the stated transactions.

**Did.**

- **`statement_extract` now emits adjustment specs.** The contract grew a second block:
  `adjustments` (id, function, debit, credit, params, source_text) and `policy` (tax_rate,
  depreciation convention, inventory system). The prompt names the four registered functions and
  their parameters and forbids computing an amount.
- **Every parameter is grounded.** A number in `params` must appear in the source text; the only
  exceptions are declared defaults (residual 0, beginning inventory 0, total months 12). A parameter
  the model invents is refused.
- **`to_policy` normalises** the flat `depreciation_convention` a model may emit into the nested
  shape, and converts `tax_rate` to a string so the plan's `Decimal`-only rule holds.
- **`_solve_narrative` feeds the adjustments and policy into the plan**, which computes them in the
  DAG and settles tax in the second pass.
- **Entry shape is accepted two ways**: the `lines` array and the `{debit, credit, amount}` shorthand
  the model actually emits, both normalised to one side per line.

**Verified.** A synthetic 11-clause problem (capital 50,000, equipment 60,000 over 5 years, prepaid
insurance 6,000, inventory 70,000 with ending 10,000, sales 200,000, collections/payables, salaries,
rent, interest, accrued salaries, tax rate 25%) now returns depreciation 12,000, prepaid 5,500, COGS
60,000 and tax 17,400 on a pre-tax income of 69,600, with net income 52,200, assets 137,600 and all
eleven checks passing. The live smoke (`qa/manual/extract-smoke.py`) still passes on the simpler
narrative.

**Not done, and named.** Reducing-balance depreciation is refused, not approximated. A loss earns no
tax benefit. Multi-period and consolidated statements are out of scope. The tile copy in `subjects.py`
still over-claims. Tuning across many problems has not been done.

**Learned.** A model will invent a default (`residual: 0`, `beginning_inventory: 0`) and present it
as a stated figure. The grounding rule would reject it - and should - unless the default is declared
up front. Declaring the defaults is cheaper than fighting the model, and it makes the assumption
manifest accurate.

## 2026-11-04 â€” [computation] The tile now reads a narrative, not only a trial balance

**Ask.** "go." â€” wire `statement_extract` + `statement_plan` behind `POST /api/cases/statements` so a pasted
assignment, not only a trial balance, is solved.

**Did.**

- **`_solve_narrative` in `src/bp/product/statements.py` (new).** When the deterministic reader
  refuses (or is absent), the model extracts a journal from the default chart
  (`bp.statement_plan.DEFAULT_CHART`), the plan compiles it with no adjustments, and the ledger posts it.
  The record carries `reading_source: "plan"` and names the missing adjustments.
- **`solve()` now rescues a `StatementRefused`** â€” the refusal for two figures on one line or two
  periods is exactly the case the narrative path can handle; a genuinely unworkable input still raises.
- **`statement_plan.build` returns `spec`**, so the product layer can freeze the same record shape.
- **`_models_for_extraction()`** uses `bp.llm.from_env()` and falls back to `DEEPSEEK_API_KEY`.

**Verified.** A synthetic narrative ("started the business with 20,000 cash; sold 9,500 for cash; paid
rent 1,200 and salaries 2,400") returns a full statement set: net income 5,900, assets 25,900, cash
22,900, all eleven checks passing, all three identities true. The tile's existing tests
(`test_product_statements_tile`, 55) still pass; the docs-sync suite still passes.

**Not done, and named.** Adjusting-entry derivation from text (prepaid amortization, depreciation,
COGS, tax) is not wired â€” only the stated transactions are posted, and that is named in the record's
`missing`. Multi-period and consolidated statements are out of scope. The tile copy in `subjects.py`
still over-claims ("the question as you were given it") and that file is another lane's.

**Learned.** The deterministic reader's `StatementRefused` for "two figures on one line" is not a
failure of the input â€” it is a signal that the input is a narrative, which is precisely what the plan
layer exists to handle. Treating it as a fall-through trigger, rather than a dead end, is what makes
the tile solve assignments at all.

## 2026-11-04 â€” [computation] The two statement tips become code: a model reads language, the engine does arithmetic, three identities decide what may be printed

**Ask.** The owner supplied two tips on creating and solving financial statements, and asked that
they be studied, recorded so the next model can find them, and implemented generically â€” *"dont
hardcode north star text only use what is learned from it. this should be generic."* The hard rule
retained: **no invented numbers.** Prior lane rules were lifted for this work.

**Why the shape is what it is.** The tile already prepared statements from a trial balance
(`docs/HANDOFF_STATEMENTS_TILE.md`, `qa/manual/statements-case-study.md`) and refused everything else,
because its reading layer parses one trial balance and nothing more. The tips say the missing
capability is not a bigger prompt: it is a **split of responsibility** â€” the model translates language
into balanced journal lines, code computes every derived figure, and checks decide whether the answer
leaves the building.

**Did.**

- **`src/bp/statement_plan.py` (new).** The generic layer, with no engagement inside it:
  `account()`/`validate_chart()` for the chart-of-accounts table; `validate_entries()` for the strict
  journal schema (it uses the ledger's own balance rule rather than a copy); a policy registry
  (`POLICY_DEFAULTS`, `validate_policy`, `manifest`) that prints every assumption the text did not
  state; an adjustment DAG (`Node`, `toposort`, `evaluate`) with deterministic ordering, `$ref`
  dependencies and a cycle refusal; and four registered functions â€” `straight_line_depreciation`
  (full-year / half-year / pro-rata), `prepaid_amortization`, `periodic_cogs`, `tax_on_pretax`.
- **`build()` compiles, then gates.** It resolves the declared adjustments into entries, calls
  `accounts.build`, settles **tax in a second pass** after the other adjustments (tax cannot precede
  COGS), and then runs `articulation()`. A failed identity raises `PlanError` naming the check; the
  record is not returned.
- **The three identities are the ones the owner named**, including the strongest: receipts minus
  payments equals ending cash, computed independently of the accrual statements.
- **`src/bp/statement_extract.py` (new) is the only model-touching step.** The contract is stated as
  data and as a prompt; `parse()` refuses anything that is not a JSON object; `validate()` checks chart
  membership, the balance rule and a required `source_text`; and **every amount must literally appear
  in the problem text**. A derived figure is refused with a sentence saying derived amounts belong to
  the adjustment stage. `extract()` uses `bp.llm` and accepts nothing partially.
- **`tests/test_statement_plan.py` (new, 40 tests).** A golden engagement assembled from declared
  parameters, hand-derived expected figures (pre-tax 70,100.00; tax 17,525.00; net income 52,575.00;
  assets 178,100.00; liabilities 75,525.00; equity 102,575.00; operating cash flow 74,600), variants
  for dividends, perpetual inventory and a loss, and the gate proved **both ways** on doctored records.
- **`docs/TIPS_FINANCIAL_STATEMENTS.md` (new)** records both tips verbatim in substance, the mapping
  from tip to code, the measured figures, the deliberate omissions, and a pick-up block at the top.
  Linked from `AGENTS.md`, `docs/HANDOFF.md`, `docs/HOME.md` and the changelog so it is findable
  without being pointed at.
- **Version moved to 1.87** (`src/bp/build.py`), with `HOME.md` and `HANDOFF.md` updated to say so and
  the measured suite count (3672) replaced in both.

**Verified.** `python -m unittest tests.test_statement_plan` â†’ **40 tests, OK**. The golden build's
articulation checks all pass; a doctored `total_assets` fails A=L+E and a doctored `net_direct` fails
the cash check. `python -c "unittest.TestLoader().discover('tests').countTestCases()"` â†’ **3672**,
which is the number now stated in the two documents. A **live** extraction call was then made against
DeepSeek (`deepseek-flash`) on a synthetic five-transaction problem: five grounded entries, posted,
net income 5,900 and assets 25,900, all three identities true. The live run is what exposed three
gaps the unit tests could not â€” the schema-legal `{debit: 0, credit: x}` line, `code` used instead of
`account`, and a problem that states no date â€” and all three are now handled and tested.

**Not done, and named.** Extraction is proved on one synthetic problem, not tuned across many, and is
not yet wired to the tile. The tile still reads one trial balance until the extraction and plan layers
are wired behind `POST /api/cases/statements`. Reducing-balance depreciation is refused, not
approximated. A loss earns no tax benefit. Multi-period, comparative and consolidated statements are
out of scope. The two Ashgrove display defects (28-decimal ratios; "other" for brought-forward
retained earnings) remain, and are recorded in the case study.

**Learned.** The cheapest way to make "no invented numbers" survive a model is not to trust a prompt:
it is to require each proposed amount to be a substring of the source. That one rule moves every
derived figure into code by construction, which is exactly what both tips asked for.

## 2026-11-04 â€” [design] The Financial statements tile is a card, it was dead because of a brace, and it now says what it can actually do

**Ask.** The design owner's brief (`docs/MINIMAX_FINANCIAL_STATEMENTS_UI.md`, B-080): close the UI/UX gap on the
accounting shelf's statements tile. It is a service tile, not a frozen preset, so it never looked like the
other tiles; the brief asked for a real card, a canonical address, and the seven click-path proofs. The owner's
second instruction, after seeing the result: **the tile is black where every other tile is light, it floats when
the other tiles do not, and it cannot solve a basic accounting problem** â€” harmonise its colour theme with the
other tiles, make it open like "management of accounts" rather than floating, and make it able to prepare and
download financial statements. The third instruction: **decouple it from PESTEL and SWOT.**

**Why the order of the work changed.** The brief's diagnosis was that the tile "is a paragraph, not a tile" and
that the link does not respond to clicks. Both are true, and neither is the cause. The cause is that
`web/index.html` ended the `<script id="statements-tile">` block with a stray `}` and then `})();` â€” the IIFE
body was closed twice. **The whole block was a syntax error, so none of it ran**: the dialog was never built, the
click handler was never registered, and `window.openStatementsTile` was never defined. The link could not have
worked as an anchor or as a card. The first increment is therefore the brace, not the card.

**Did.**

- **The brace.** `web/index.html` â€” one `}` removed. Node's parser: `block 3 [statements-tile] -> SYNTAX ERROR:
  Unexpected token '}'` before, `SYNTAX OK` after. The router's `head === "statements"` branch had been falling
  through to its `else` on every load, registering a `load` listener that called an undefined function.
- **The card.** The service tile now renders as a `.capcard` in the same `.capgrid` as every other tile â€”
  `.caphead` (icon + title) + `.capdesc` + `.capfoot` (the honest label "One instruction", and the `Open â†’`
  affordance) â€” and the **whole card** is the link. Measured: **506Ã—149**, the same box as the other cards. The
  tile's own description paragraph is suppressed for a service tile, because the card now carries that sentence
  and the page would otherwise say it twice.
- **The address.** `#/financial-statements` is canonical; `#/statements` stays as the alias it has always been. The
  click opens the workspace **itself** rather than leaving it to the hash â€” a click on a card whose address is
  already canonical changes no hash, so no `hashchange` fires and the tile would look dead. One open per click,
  never two.
- **It no longer floats.** The tile was a `position:fixed` modal appended to `<body>` â€” a window over the shelf,
  the way a *framework record* opens, not the way a *tool* opens. It is now a real panel, `panel-statements`, in
  `PANELS` and in `SUBJECT_WORKSPACE`, with its own markup in the body: the same `.card`, `.sub`, `.field`,
  `.badge`, `.toggle` and `.btn` components every other workspace uses. A student who opens a management-account
  tool and a student who opens this are now looking at the same kind of page. "Back to the shelf" sits at the top
  next to the title; the house's own tile-close button still closes it from the bottom, as it does everywhere.
- **It no longer floats dark.** The old panel painted a navy ground (`--navy-800`, `#12161C`) while the page's
  text is near-black (`--text`, `#0C243E`) â€” about **1.2:1**, and it had never been seen by anyone because the
  syntax error meant it had never rendered. The workspace is painted with the page's own surfaces now:
  `--surface` cards, `--sunken` for the recorded text, `--border` rules, `.toggle` for the Working / Statements
  only switch, `.badge` for the type line, and the page's own amber `.banner.honesty` for the diagnosis.
- **The tile's copy now says what it can actually do.** It used to promise "the question as you were given it",
  which over-claims: the reading layer reads a **trial balance**, and only that. The copy now names the shape â€”
  one account per line, as "Cash 5,000" or "Capital 5,000 Cr" â€” and a **Use an example** button fills in a
  balanced trial balance so the student sees the shape and the answer at once, the way the trial-balance check
  page already offers one.
- **A refusal is now actionable.** The backend's own words are shown, unchanged, because the page must not
  paraphrase a refusal it does not own; under it the page says the shape the tile reads and points at the
  example. A 5xx now says the server could not answer rather than being rendered as "these figures do not build".
- **The gate that let it through is now a gate.** `qa/check_page_syntax.py` matched only `<script>` tags with no
  attributes and checked only the **last** match, so the page's two tagged blocks were never parsed. It now checks
  every inline block and names each one. Proved both ways: `3 of 3 blocks parsed` on the current page, and the same
  gate against the pre-fix page reports `FAILED in statements-tile`.
- **The backend is untouched and re-measured.** The brief's transcript reproduced exactly over HTTP: **34 of 34
  checks pass** (201 with `ni 8000`, `assets 10000`, `checks 11/11`, `checks_na 2`, `cash_flow` null with the
  withheld note, all three statements; 201 with ratios `computed 8` / `named_unsupported 7`; 422 with the 500
  difference; 400 with "two sets of balances â€¦ one set at a time"; export 200 `statements_only`; replay 200 `ok`).
  No 5xx anywhere.
- **Seven click-path proofs, in a browser.** Clicking the card opens the workspace; a cold tab on
  `#/financial-statements` opens it; `#/statements` still opens it; "Back to the shelf" returns to the accounting
  shelf and the page behind is unchanged; after six seconds the card is still the same node and a click inside the
  workspace is not replaced under the cursor; Tab reaches the card and Enter opens it; the console holds one
  informational line and no errors. **Escape no longer closes it**: that was a modal affordance and the tile is not
  a modal any more.
- **Decoupled from PESTEL and SWOT.** The tile's own code never touched the chat, the plan or a framework â€”
  measured: **0** occurrences of `chat`, `plan`, `framework`, `pestel`, `swot`, `session` or `delivery` in the
  statements block. The tie the owner saw was the **Help panel's own map**, which read *"Guided paper for a full
  PESTEL, SWOT or combined paper with sources"* first and **never mentioned the statements tile at all**. The map now
  leads with what the product can do â€” Financial statements, Subjects, Business Calculator, Check â€” and the guided
  paper is one option among seven instead of the frame around everything else.

**What the tile can actually solve, measured rather than assumed.** Seven realistic student inputs were posted to
`POST /api/cases/statements` and the answers recorded:

| the student pastes | what came back |
|---|---|
| a bare trial balance | **201 solved** â€” `ni 8000`, `assets 10000`, `checks 11/11`, cash flow withheld and named |
| a single-year transactions narrative | **400** "this carries more than one period (2026-01-01, 2026-12-31)" |
| an adjustments narrative (depreciation + accrual) | **400** "this puts two figures on one line â€¦ which is a comparative" |
| a ratio question with figures but no trial balance | **400** "an account has no code; (total assets): every asset and liability needs a section" |
| a cash-flow narrative | **16.9 s, then 400** "the chart needs exactly one retained-earnings account, found 0" |
| an exam question with a preamble before the figures | **422** "does not balance: debits 17000, credits 19026" â€” the preamble was read as account rows |
| a trial balance in EUR | **400** "this product answers in USD only" (a deliberate rule) |

**So the tile reads one trial balance, and only one.** `src/bp/product/statements.py` reads it with a deterministic
parser, and anything the parser cannot read needs the model reader â€” `bp/server.py` attaches it, and it needs
`BP_OPENGO_API_KEY`, which is not configured here: *"no model is configured (set BP_OPENGO_API_KEY), so only a trial
balance can be read."* **The owner is right that the tile cannot solve a basic accounting problem.** It can prepare
statements and the working from a trial balance; it cannot yet read a transaction narrative, an adjustments
problem, a cash-flow problem or an exam question with a preamble. The reading layer is the reason, and it is in
`src/**` â€” the computation lane's â€” so it is a request below, not a change made here.

**What the tree already had, and what I did not touch.** The working tree carried another lane's uncommitted
`src/**` edits (`PRESETS` emptied for `abc`/`salesvar`/`multibreakeven`/`accounts`, `tbcheck` pulled from the
accounting calculator group) and its own edits to `web/index.html`. Measured, not assumed: a clean `HEAD` checkout
runs these three modules **114 tests, OK**; `HEAD` **plus only those two dirty `src/**` files** reproduces the
identical **16 failures and 2 errors**; the current tree adds **none**. Those failures are `src/**`, they are
another lane's, and they are recorded in `docs/HANDOFF_STATEMENTS_TILE.md` so nobody re-derives them.

**Requests to the computation owner** (recorded, not made):

- **[computation] The reading layer is the reason the tile "cannot solve a basic accounting problem."** The seven
  reproductions in the table above are all in `src/bp/product/statements.py` (the reading), not in the page. Four
  defects:
  1. **An exam-question preamble is read as account rows.** "Prepare the income statement for the year ended
     31 December 2026 from the following trial balance, and show your working." followed by a trial balance â†’
     **422**, "does not balance: debits 17000, credits 19026" â€” the difference being the words of the question. A
     question and a trial balance pasted together is the **normal** way a student pastes an exam question.
  2. **One year is read as two periods.** A single-year transaction narrative names 1 January and 31 December and
     is refused as "more than one period". One period's start and its end are one period.
  3. **An adjustments sentence is read as a comparative.** "the equipment is depreciated at 20% a year; $1,500 of
     income is still unpaid" is refused because one line carries two figures.
  4. **Two refusals name the wrong thing.** A ratio question is refused with "an account has no code" and a
     cash-flow narrative with "the chart needs exactly one retained-earnings account, found 0" â€” neither student
     mentioned a chart. The second also takes **16.9 seconds** to refuse, which reads as a hang.

  The reading is where the widening belongs: the parser is exact on a trial balance and should stay exact, but the
  preflight has to let a preamble through and read the figures out of a narrative. **The alternative is one line of
  configuration** â€” `BP_OPENGO_API_KEY` enables the model reader, which is the path the module's own docstring
  describes ("A transaction list and an adjusting-entry narrative need the model reader"). Either fix makes the
  tile able to prepare statements from an exam question, which is what the tile is for.
- **[computation] The tile's own description over-claims.** `ACCOUNTING_TILES[0]["what"]` says "Paste the problem as
  you were given it" and `["need"]` says "The question as it was set, or the trial balance" â€” but the tile reads a
  trial balance. The page copy is now exact; these two strings are in `src/bp/product/subjects.py` and are the
  computation lane's to change. Suggested: `what` â†’ "Paste a trial balance, one account per line, and get the
  journal, the trial balance and the statements, with the full working behind one toggle."; `need` â†’ "A trial
  balance, one account per line. One instruction, no fields to fill."
- **[computation] `scripts/ci.py` carries the same page-syntax hole.** `_node_check` matches
  `re.findall(r"<script>(.*?)</script>", html, re.S)` and writes `scripts[-1]`, so the page's two tagged blocks are
  never parsed and the CI gate could not have caught D-ACC-11 either. The fix is the one line
  `qa/check_page_syntax.py` now uses: match every `<script â€¦>` block and check each. `scripts/ci.py` is the
  computation lane's file, so it has not been edited here.
- **[computation] `src/bp/build.py` is at `VERSION = "1.85"` and this entry is 1.86.** Every prior release commit
  moved the two together (`2980681`, `dda7d22`, `3dadb37`). `src/**` is the computation lane's, so the bump is
  requested rather than made â€” and D-PM-07 (the pill must report the build the server reports, from one source)
  says it should not be left behind.

**New:** `docs/HANDOFF_STATEMENTS_TILE.md`; `qa/check_page_syntax.py` rewritten; `qa/QA_DEFECTS.md` carries
D-ACC-11. `src/**` and `tests/**` untouched.


## 2026-11-03 â€” [computation] People & organisation: the last shelf gets measured, and four claims its units were making turn out to be false

**Ask.** The work order for the `people` shelf: measure it, write its manual and its acceptance suite, settle
`docs/OPEN_ISSUES.md` Items 11 and 12, and *do not* touch the core without asking. The owner's instruction when the
session closed: **"a"** â€” option A of the four offered, which is the whole core fix.

**Why the fixes are in the core and not on the page.** Three of the shelf's ten calculators are presets of core
methods (`trainingroi` â†’ `return_on_investment`, `labourtightness` â†’ `labour_market`, `programmecost` â†’
`cost_effectiveness`), so their defects are the core's â€” and every one of them was a **claim the unit made about the
number** rather than the arithmetic. An effect of 40 was labelled money; a cost *per* effect was labelled money; a
count divided by a rate was labelled a ratio; a holding period was labelled a count.

**Did.**

- **The `@unit` ordering bug, first.** `orchestrator` set `cur_here = cur if mu == "@unit"` *before* `mu` was resolved,
  so every `@unit` output took the request's currency whatever it was. The unit is resolved first now, and the currency
  follows the resolved unit through the existing exempt tuple.
- **One composite unit, in words.** `currency_per_effect` is the engine's only new unit; `Quantity.display` prints it
  as "USD 400.00 per unit of effect" and keeps the accounting parentheses for a negative ratio, because the exchange has
  no symbol for a cost per effect and printing a bare amount is exactly the error being fixed.
- **Tightness divides by people, not by a rate.** `labour_market` takes an `unemployed` count; tightness is
  `vacancies / unemployed`; a sixth declared check recomputes it; the caveat says it is a ratio of two counts; and the
  template now **states the number**, which it never did (Item 11c).
- **Ten probes, then ten traps.** Each fix was first measured with a throwaway probe (what does it print today?), then
  written as a trap that asserts the new truth. Stashing the five source files and re-running proves **10 of 11 fail on
  the old code** â€” the eleventh, E-ppl-059, is the surviving "a rate is never rescaled" rule, retargeted to the
  chi-square significance level because the labour tool no longer takes a rate.
- **The fixture was regenerated, not hand-edited.** `scripts/econ_shelf.py --fixture` wrote 142 methods and 144 presets;
  `--check` says in sync.

**Files.** `src/bp/methods.py` (cea/roi/power typing; the labour-market impl, check, profile, typing, caveat, template
and contract), `src/bp/orchestrator.py` (one block), `src/bp/quantity.py` (display), `src/bp/server.py` (the preset),
`src/bp/product/subjects.py` (one step, one tile description), `tests/fixtures/frozen_contract.json` (regenerated),
`tests/test_subject_people_acceptance.py` (85 tests), `qa/manual/people.md`, `qa/clickthrough_people.py`,
`qa/evidence/people/`, `qa/QA_DEFECTS.md`, `qa/QA_STATE.md`, `docs/OPEN_ISSUES.md`, `docs/CURRICULUM_MAP.md`,
`docs/DECISIONS.md` (B-216), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`.

**Verified.** 85 acceptance tests green; 234 in the frozen-contract, method-contract, people, economics and
entrepreneurship slice; `econ_shelf --check` in sync; `page syntax: OK`; 10 of 10 calculators delivered over HTTP on
port 8002 with 10 of 10 `.docx` downloads; one Kotter paper read against V-01â€¦V-20 (no rule failed).

**Learned.** The supply-chain session's lesson held and moved one line: a unit audit is worth more than a number audit,
because these numbers were all *arithmetically* right. And the rebase reality is real â€” the research lane changed
`_power_typing` under this session mid-flight, from `probability` to `@unit`, which resolved straight back to
`probability`; the ledger was corrected rather than the finding dropped.
## 2026-11-03 â€” [calculator] The Business Calculator is proved by launching all 148 tools, not by counting them

**Ask.** The work order: the rail panel `#panel-calculator` has a page, a route, a guard and **148
launchable tools** â€” and **no acceptance manual and no acceptance suite of its own**. Coverage was
"complete but unproved": four modules asserted membership (the union of the groups, the presetâ†”method
pairs, the method resolution), and nothing ran a tool the way the panel runs it. Prove every applicable
computation is wired, and prove it *by behaviour*.

**Started from a different tree than the order describes.** The sandbox checkout was on `main`, which
is ~5,400 files behind and measures **129** tools; the order's branch is `corpus/merge-v1`. A worktree
on that branch measures **148** â€” the order's number â€” so every figure below was re-measured there and
nothing was copied.

**Ground truth, re-measured at `05efb8f`.** `compute_tools()` **148**; `CALCULATOR_GROUPS` **8 groups /
206 entries / 148 distinct**; 0 tools missing from the calculator; 0 calculator keys off a subject page;
144 presets each running the method it claims; **4** typed tools (`kruskal_wallis`, `mann_whitney`,
`ols_robust`, `spearman`); **131 of 148** keys are not `LIBRARY` ids; 0 preset/method mismatches; one
documented composite (`case_decision`); `LIBRARY` 142 / `PRESETS` 144 / fixture 142â€“144. **One number
did not reproduce: the order says 33 keys sit in more than one group; the tree measures 31**, by two
independent counts â€” and it is now **disproved**, not merely unmatched: parsed across all 36 revisions
of `subjects.py` the count has taken 13/17/20/24/27/30/31 and has never been 33, and no alternative
reading of "shared" gives 33 either (method-sharing 31, keys-with-a-shared-method 32, subject-page
sharing 45, entriesâˆ’distinct 58). Recorded as a miscount in the work order (Â§5.1), and the taxonomy
was not touched.

**The probe, and why it had to be distrusted first.** `qa/probe_calculator.py` resolves **both**
vocabularies (key *and* method â€” the 131 trap), launches each tool through `Pipeline.run` â†’
`session_paper.docx_bytes` â†’ the text, and reads the gates on the artefact. Its first run reported three
problems, and **all three were the probe's own**: `descriptive` was flagged for `1e-9` that lives
inside the declared *limitation* "Float reference comparison tolerance is 1e-9 relative", and the two
6-dp figures were being *exempted* because they matched their declared precision. Before trusting it I
pointed it at `operations` (46-test suite green) and `research` (53-test suite green): **14/14 and 21/21,
zero problems**. Then the exemption was removed â€” because `DECISIONS.md` **B-214** had already settled
this exact conflict in favour of the six-decimal ban â€” and the two remaining findings turned out to be
real.

**What was actually broken.** `currency_convert.rate` and `real_option`'s four ratios declared
`("ratio", 6)`, so every currency paper printed `Rate: 0.920000` and every real-option paper
`Delta: 0.617058`. That is the D-RES-05 defect class, alive on two methods that no shelf suite had ever
read, precisely because the calculator had no behaviour test. On the owner's instruction ("unfreeze it
and do what you have to do to fix the error") both declarations moved to 4 dp â€” **B-217** â€” and the
papers read `Rate: 0.9200` / `Delta: 0.6171`. The frozen fixture pins `tier/metric/unit/ceiling/
test_names/inputs` and **not** precision, so it was not touched: `econ_shelf --check` still says
"frozen fixture: in sync". A third, smaller defect: an unknown calculator sub-route answered `422 case
id must be 12 lowercase hex characters` â€” a fail-closed path with the wrong reason â€” now `404 unknown
route â€¦`.

**What is now green.** 148/148 papers pass every gate; 148/148 are byte-identical across two runs; the
31 shared keys agree from every group that lists them (0 disagreements); the unit sweep finds 0
disagreements between `typing` and the declared `output_units`/`output_precision`; the four typed tools
deliver with typed figures and **block naming the missing input** when sent `{}`; the ask router never
invents a tool. Twelve wiring invariants W-01â€¦W-12 are 25 tests against the real paths, with a negative
control (`test_E_calc_024`) proving the gates can fail at all.

**Not done, deliberately.** The ask surface still answers `200 + unsupported/no_method` rather than 404
for an unknown *sentence*: it is a plan, not a lookup, it returns no tool and names why, and "what the
calculator says when a tool cannot run" is an owner decision (Â§9), so it was left alone and recorded.


## 2026-11-03 â€” [design] The bundle becomes a band below the pricing grid, and the page stops naming tiers

**Ask.** The owner, after the payment side was committed and pushed: *"i dont see teh bundle reflected
in the UI of smart business writer. the bundle should be below the initial pricing shwoing the price
if both are bundled including the features of write smarter (only for now, i will ad business
later)"*.

**Why the bundle was invisible.** Not a rendering bug â€” a **structural** one. The bundle was the
fourth card in the same four-column grid as Starter, Pro and Studio, and a fourth card in that grid
reads as *"a fourth tier of this product"*. The bundle is not that. It is **two** products at one
price, and the layout was saying the opposite. The fix is not to make the card louder; it is to stop
the layout contradicting the offer.

**Did.**

- **The three single-product tiers stay in the grid, in three columns.** Starter, Pro and Studio are
  what they were; the grid is `repeat(3, minmax(0,1fr))` now that the fourth column is gone.
- **The bundle is its own band, below the grid.** One price â€” **$99.99 a month** â€” tagged "Both
  products", with the line *"One subscription, one charge, unlimited use of both products."* and a
  **"Get the bundle"** button rather than a generic "Choose", because it is a different act.
- **The band says what the one price buys, product by product.** Write Smarter's own feature names
  are used verbatim from that product's pricing page â€” unlimited Text-Gen, unlimited Research
  Assistant, unlimited Humanizer & AI-Detector, unlimited Video, unlimited use of Source Finder â€”
  beside Smart Business Writer's unlimited exports. Two panels side by side; they stack on a narrow
  screen rather than overflowing.
- **The band follows the monthly/annual toggle**: $99.99 a month, $959.90 a year, and the wording
  changes with it ("Billed once a month" / "Billed once a year").
- **The page names no tier at all.** The catalogue now says which tiers are cards
  (`card_tiers`) and which is the band (`bundle_tier`), and carries each tier's colour (`color`). The
  page reads all of it from `/api/billing/plans`, so a price, a tier or a new rung needs **no edit to
  the page** â€” and the CSS tier-colour rules that named `starter`, `pro` and `studio` are gone.
- **The owner's "only for now, I will add business later" is respected literally.** The band names
  the two products that exist. Nothing says "and more to come", because that would be a promise about
  a decision the owner has not made.

**Verified.** 7 new tests in `tests/test_product_bundle.py`: the three card tiers and the bundle
tier are named by the catalogue and are different sets; the bundle is not one of the cards; the band
lists both products and what each gives; **no band feature line carries a digit** (the bundle grants
no limit, so no feature may quote a quota); the page renders the band **after** the grid in the
markup; the grid is three columns; and the page names no tier â€” a test that fails on the old
four-card layout and on any hard-coded tier name. The whole suite green at **3425 tests**, and
`scripts/ci.py` 3 of 3 steps passed. The dialog was rendered in Chrome and read back: three cards
(`starter`, `pro`, `studio`), then the band â€” `$99.99` / "Both products" / Write Smarter's five
features beside Smart Business Writer's two â€” at 1280 px and at 420 px, monthly and annual.

**The claim is on disk, not in a sentence.** `qa/measure_pricing_band.py` starts a workbench on its
own port, drives the machine's Chrome headless over a DevTools port with a minimal
standard-library WebSocket client (no dependency added), opens the pricing dialog, and reads back
**the rendered DOM**: how many cards are in the grid, which tiers they are, whether the band is
present, what it says, and that it comes **after** the grid. It writes three PNGs and
`qa/evidence/pricing/pricing-band.json` â€” six checks, all passing â€” so a later edit to the markup
cannot hide the band without failing the measurement.

## 2026-11-03 â€” [product] The Business Bundle: one order, one charge, and the hand-off that makes it true (B-208, B-209)

**Ask.** The owner's decision of 2026-11-03, recorded in full in
[`BUNDLE_PRICING_HANDOFF.md`](BUNDLE_PRICING_HANDOFF.md): a **$99.99/month bundle that gives
unlimited use of both products** â€” Write Smarter *and* Smart Business Writer â€” sold as **one
order**, charged **once**, with **one login** that works on both products. Smart Business Writer's
existing $99.99 tier becomes the bundle; the lower tiers keep their prices; the purchase happens
in Smart Business Writer. The owner asked for **the payment first**: settled and proved against
live PayPal before the limits, the allowance numbers and the credit refill are built.

**What was already in the tree when this session started.** The design lane had already written the
bundle tier into `billing.py`, the plan-change path into `paypal.py`, the ledger fix, the unlimited
wallet and the pricing dialog's fourth card â€” but none of it was committed, none of it was
documented, and the **seam between the two products did not exist**: nothing read PayPal's vault
id, and nothing called the other product. Without that seam the bundle would have been two
subscriptions and two charges. That seam is what this session built.

**Did.**

- **The bundle tier** (`src/bp/product/billing.py`). The `agency` key is kept â€” a PayPal plan id is
  immutable, so renaming the plan in place would have billed the old label â€” and the customer now
  reads **"Business Bundle"**. It carries an `unlimited` **flag**, not a number: the other three
  tiers still report `credits: null` and still print "to be confirmed". The card's `includes` names
  both products. `unlimited_for()` refuses an unknown tier, and a tier whose allowance is undecided
  is **not** unlimited â€” *undecided is not free*.
- **A plan change that prorates** (`paypal.change_plan`, `POST /api/billing/change`). PayPal's plan
  id is swapped on the running subscription and the difference is settled against the saved payment
  method, so there is no second approval and no lost period. PayPal's own
  `billing_info.outstanding_balance` is passed on **untouched** and described as charged, credited
  or unknown â€” never estimated. The pricing dialog now takes this path when the customer is already
  on a plan, instead of asking for a new approval.
- **The ledger records the plan change** (`billing.activate`, `_activation`, `current`). This was
  the trap in the handoff: the ledger was **first-wins on a subscription id**, so an upgrade from
  Starter to the bundle on the same PayPal subscription id would never have appeared on the account
  page, and the cancellation message would have named the tier the customer had left. The activation
  is now idempotent on the subscription id **and** the tier it carries: a tier change is recorded, a
  retried confirmation of the same tier is not, and the latest activation is what stands.
- **The hand-off â€” the seam that makes "one charge" true** (new `src/bp/product/write_smarter.py`).
  On approval, PayPal's `payment_source.vault_id` is read from the subscription and posted to the
  hosted Write Smarter service with a shared secret. That service creates **its own** subscription
  record from the same vault, switches it off, and reads it back to prove it cannot bill. Two
  independent guards: the record's plan is **$0**, and a record PayPal still calls ACTIVE fails the
  grant rather than being reported as switched off. The hand-off client **cannot take a payment** â€”
  it never calls a PayPal billing endpoint, and a test asserts that.
- **The vault id is remembered between the two calls.** PayPal names the vault id when it *creates*
  a subscription and does not always name it when the subscription is *read back* â€” so the note kept
  at creation (`state/pending_subscriptions.json`) is what the confirmation falls back on, and it is
  dropped once the subscription is confirmed. Without that, the bundle would have been granted here
  and not there, and the failure would have looked like a PayPal problem rather than a missing note.
- **A failed hand-off never undoes a real payment.** The customer paid and the subscription is
  ACTIVE, so the local grant stands. The failure is reported as a failure of the **other
  product's half**, with the reason, on the confirm reply, on the cancel reply and on the account
  page. A missing URL or secret fails closed and names **every** variable that is absent; a refused
  call, an unreachable service or a body that does not confirm the grant are all failures.
- **Cancelling one side stops both.** Cancelling here revokes the grant on the other product, and
  the other product reads the **real** subscription's status, so a cancellation made there stops
  this one too. The switched-off record is never what decides whether the customer has paid.
- **The other product's side** (Write Smarter's live `Backend`, pulled from the VPS): a new
  `bundle-entitlement.js`, two service routes (`bundle-entitlement`, `bundle-status`), and an
  unlimited pool tier in `auth.js` so the bundle carries no cap on any pool. The bundle SKU is
  deliberately **not** in the table the checkout sells from â€” a bundle SKU there would let a
  customer buy a second live subscription, which is the exact double charge the bundle exists to
  prevent.
- **The unlimited wallet.** A bundle holder never receives a 402: the export is still written to the
  ledger with a zero amount, so the trail of what was produced stays honest and the balance does not
  move. The ordinary tiers keep their meter.
- **The pricing dialog and the account page.** The fourth card reads $99.99 / $959.90 with
  **"Unlimited"** and names both products; the bundle carries **no "% off" and no "save $"** line
  against a made-up total, because "unlimited on both products" has no published sum to discount.
  The account page shows the plan, the allowance and the state of the other product's half.

**Verified.** `tests/test_product_bundle.py` â€” **37 new tests**: the hand-off carries the vault id
and the real subscription id and nothing that could take money; a missing vault id, a missing
setting, a refused call and a body that does not confirm are all failures; the client never calls a
PayPal billing endpoint; a plan change is recorded against the same subscription id and the account
page reads the new tier; a downgrade moves the tier back and drops the unlimited grant; the
adjustment reports PayPal's number untouched; the cancel route revokes on the other product and a
failed revocation is reported without undoing the cancellation; a bundle holder is never blocked by
the wallet and a tier whose allowance is undecided still is; the bundle card reads Unlimited and no
other card claims a limit. The existing `tests/test_product_billing.py` was updated for the renamed
tier (the owner renamed what the customer reads; the stable keys stayed). Write Smarter's own
`Backend/tests/bundle-entitlement.test.mjs` â€” **9 tests**: the bundle is granted here and never
bought, every pool is unlimited, a grant creates the record and switches it off, a record PayPal
still calls ACTIVE fails the grant, a missing bundle-record plan is refused rather than guessed, the
entitlement follows the real subscription and not the record, an unreadable subscription grants
nothing, and a revocation takes the grant back.

**Not done, and named as such.** **No live charge has been taken.** Every claim about PayPal's
behaviour in this path is verified against fixtures, not against the live merchant account; the
seven checks in Â§6 of the bundle handoff are still open. The **shared login is not built** â€” the
owner asked for the payment to be proved first, and the login only decides *which account* the
subscription attaches to. The lower rungs, the per-tier allowances and the per-cycle refill are
deferred by the owner (B-180a, B-180b). The Write Smarter pricing page band waits on the owner's
hosted URL.

**D1 amended (B-209).** "Local single-user v1: no accounts" no longer describes the whole product,
because one login across two products needs accounts, tenancy isolation and a per-user quota. That
is recorded as an amendment in `docs/PRODUCT_BACKEND_PLAN.md` rather than smuggled in, and
`deploy/README.md` and `web/account.html` were amended with it â€” both used to promise "no
authentication" and now say what is true: the identity work is coming, and it comes after the
payment is proved.

## 2026-11-03 â€” [computation] The grid width claim becomes a measurement, and the copy stops repeating itself

**Ask.** The owner's instruction, after the design lane's B-080 report: *"close the gap"* â€” the
one gap I had recorded as blocking acceptance was that the grid form's 390 px behaviour was
*claimed* but never *evidenced*: no screenshot of the grid form existed in
`qa/evidence/project-management/`, and no script or JSON carried the `scrollWidth` numbers, so the
next lane could not re-run the check. Two smaller findings were closed in the same pass.

- **The measurement is now a script and an artefact.** `qa/measure_pm_grid.py` starts a workbench
  in its own process (port 8013 - never the owner's 8000 or 8021), launches the machine's Chrome
  headless with a DevTools port of its choosing, and drives it over a minimal WebSocket client
  written against the standard library (no dependency added). It sets the device metrics, opens
  each of the four grids through the page's own `openWorksheet`, builds the grid, types into every
  cell, and reads `scrollWidth` against `clientWidth`. Result: **8 of 8 clean** - 1280 px reads
  1280 = 1280 with the table visible, 390 px reads 375 = 375 with the table hidden and one card per
  row. (375 because Chrome keeps a 15 px classic scrollbar inside the emulated viewport; the
  earlier hand-measurement of "390 = 390" reached the same conclusion by a different route.) The
  refusal state was measured too: banner shown, collector null, no `{}`/`template_`/`undefined` at
  either width. Five screenshots are written, including the first pictures of the grid form itself.
- **`test_E_pm_081` makes the artefact load-bearing.** It reads `grid-form.json` and asserts, for
  both widths and all four grids, that the page does not scroll sideways, that the table is the
  visible view at 1280 and the cards at 390, and that every screenshot the record cites exists -
  so the file cannot be deleted or edited to hide a regression.
- **`test_E_pm_080` now asserts the rules, not the names.** It previously checked that
  `.mxgridtablewrap`, `.mxcards` and `@media (max-width:760px)` appear somewhere; a later edit
  could have deleted `overflow-x:auto` or the whole 760 px block and stayed green. It now reads the
  rule bodies: the wide grid keeps its own scroll box, and the narrow block hides the table and
  shows the cards, in that order.
- **The columns label stops repeating the grid above it.** The first pass fixed the plumbing leak
  ("Measure field", "Map field", "Tree field", "OKR field") with "Fields for each perspective" and
  "Fields for each objective" - which left two grids reading identically and the header saying
  *"Objectives against Fields for each objective"*. Each grid now names its own four columns -
  *"Objective, measure, target and initiative"*, *"Perspective, objective, driver and measure"*,
  *"Level, metric, formula or definition and source"*, *"Key result, baseline, target and source"* -
  and the hint carries the count. `test_E_pm_075` refuses two grids that share a column label.
- **A fixed column count is printed once.** `matrixEmptyState` printed "4 to 4" for every grid
  whose columns are fixed; it now prints `4`. One line, every grid.
- **D-PM-07 ledgered, not fixed.** The served-build pill in the top bar reads **v1.45** while the
  tree is build 1.76 - a literal in `index.html` that nothing refreshes from `/api/health`. It is
  global chrome and three lanes hold edits in that file, so it is recorded for the owner rather
  than touched here.

**Measured.** Shelf acceptance **81 tests, 81 passed** (80 before, +E-pm-081); suite **3369**;
`page syntax: OK`; `frozen fixture: in sync`; `qa/manual/project-management.md` reconciled to both
new rows and the measured layout table. Its own stale counts ("62 tests, 62 passed" in two places,
the numbers from session 7) were corrected to 81 in passing.

**And one trap of the trade, found by running the full suite rather than the gate list.**
`test_E_pm_057` asserted that *"the one registry kind still declared in two forms is
`template_servqual`"* â€” an expectation written to record a known fault (D-PM-03). The marketing
lane closed that fault in `c0399e9` mid-session, so the test began failing **because the defect
was fixed**. The row was rewritten to the invariant it was reaching for â€” no template may be
declared in `CANVAS_BLOCKS` and `MATRIX_META` at once â€” and the ledger entry moved from LEDGERED to
CLOSED. That is the discipline the manual asks for: an expectation may change when the shelf
genuinely changed, and the change is recorded, never silenced. It also shows why the full suite is
part of the job: the gate list was green while this row was red.

**Then D-PM-07, which I had ledgered as "an owner call".** The owner said close it. It was smaller
than the ledger entry implied: `bp/build.py` holds the number, `/api/health` reports it, the page
paints the pill from it at boot, and the markup now carries no number at all - so a stale one
cannot be typed back in. Two tests hold it: `bp.build.VERSION` must equal the newest changelog
build (the same number HOME and HANDOFF already must state), and `test_E_pm_081` requires the
painted pill in a real browser to read `v` + that constant. Measured after the fix: **v1.80** at
1280 px and at 390 px. Build 1.80.



## 2026-11-03 â€” [design] The Project management worksheet forms, made professional to fill in

**Ask.** The owner's instruction for the Project management shelf, design lane B-080: *"DO A
PROFESSIONAL WORKSHEET. THEN ENSURE THEY WORK."* and *"USE TILES."* The four new grids (PM-01
Balanced Scorecard, PM-02 Strategy Map, PM-03 KPI Tree, PM-04 OKRs) were correct, tested and
shipped â€” the data, the checks and the paper all work. The forms the student types into were
generic, and the shelf had no tile grouping.

**What was measured before anything changed.** 18 calculators Â· 10 worksheets Â· 6 records Â·
0 theories Â· 23 glossary terms Â· **tiles: 0**. The suite ran **3185 tests with 6 failures**
(`test_the_rail_carries_the_portfolio_lab_above_the_calculator` â€” the known baseline rail
failure â€” plus `test_a_hung_dimension_becomes_a_named_gap_instead_of_blocking`,
`test_generating_a_paper_saves_it_to_the_store`, `test_every_researched_block_accepts_its_own_query`,
`test_brave_failure_falls_back_to_firecrawl` (network) and `test_documented_test_count_matches_the_real_suite`).

**The defect this session found, which the work order did not name.** Every Project management
worksheet carries a completion profile, and `worksheetForm` tested `t.completion` *before*
`t.form_kind`. So the four grids opened the **evidence** form â€” which collects `{blocks, links}`,
a shape the grid's own validator refuses with *"rows must be a list of 4 to 6 perspectives"*. A
student filled in a grid and the run was refused. `collectWorksheetInputs` had the same ordering.
Proven from the code and the live page, not inferred:

```
template_balanced_scorecard validate({'blocks': {...}, 'links': []})
  -> ["'rows' must be a list of 4 to 6 perspectives"]
template_balanced_scorecard validate(EXAMPLE['inputs'])   # {rows, columns, cells}
  -> []                                                    # delivers
```

**Changed.**

1. `src/bp/templates.py` â€” every matrix template declares a `form_copy` object beside its own
   geometry: the row label, the column label, the hint under the column label, and the sentence
   that explains what belongs in the grid. `describe()` publishes it on the template payload, and
   publishes the grid's `require_groups`, `require_rationale` and `raci` flags so the page stops
   branching on a template id.
2. `web/index.html` â€” `matrixForm` reads `t.form_copy` and keeps the three older branches as the
   floor for a grid that declares no copy. A grid opens its grid form; the grid's shape is what is
   collected. Four designed states: empty (the grid says what belongs in a cell and that an
   unfilled cell is named in the audit), loading (the panel says it is opening the worksheet),
   error (a template the server would not serve is named), refusal (the audit's reason in a
   sentence beside the form). The grid is a table inside its own scrolling box on a wide screen
   and one card per row at 760 px and below, every cell carrying a label naming its row and its
   column.
3. `src/bp/product/subjects.py` â€” `PROJECT_MANAGEMENT_TILES` (seven), the worksheet groups, and the
   tile registered on `SUBJECT_TILES`. The four calculator tiles keep the group names the shelf
   already used, so no calculator moved: **Appraise the business case**, **Compare the options**,
   **Project cost and benefit**, **Schedule and control**.
4. `web/index.html` â€” the shelf page renders the tiles; the held-group filter now covers the
   leftover section and each tile's own records, because the tile change moved the records out of
   the grouped list and the leftover section became the one place a held record could reappear.
5. `src/bp/product/subjects.py` â€” the shelf summary and guidance now say the measured truth: ten
   completing worksheets and six read-only records, and the product invents no durations,
   probabilities, weights or owners.
6. `tests/test_subject_project_management_acceptance.py` â€” seven new rows, E-pm-074â€¦080, and
   **E-pm-006 changed** because the shelf genuinely changed: `tiles: 0` became seven tiles, so the
   expectation was rewritten to the measured truth and the fallback branch was kept.

**The four labels and intros as they render.**

| framework | rows label | columns label | intro |
|---|---|---|---|
| Balanced Scorecard | Perspectives | Fields for each perspective | Write the perspectives you steer by, one per line. Then four fields for each: the objective, the measure that shows it moving, the target you are aiming at and the initiative that gets you there. A cell you cannot fill stays empty and is named in the audit. No weights, no score. |
| Strategy Map | Objectives | Fields for each objective | Write the objectives you are steering by, one per line, then the four fields for each: the perspective it belongs to, the objective itself, the objective it is meant to drive and the measure that shows it moving. A link exists only where you write it - the map does not draw arrows and does not infer a chain. A cell you cannot fill stays empty and is named in the audit. |
| KPI Tree | Metrics | Fields for each metric | Write the metrics on the tree, one per line: the outcome metric at the top, the drivers beneath it and the inputs under those. Then the four fields for each: the level it sits at, the metric itself, the formula or definition that connects it and the source the number is read from. The tree records the decomposition you declare and calculates nothing. A metric with no source stays empty and is named in the audit. |
| OKRs | Objectives | Fields for each objective | Write the objectives you commit to, one per line. Then the four fields for each: the objective itself, the key results that make it checkable, the baseline and target they run from and the source the number is read from. A key result with no baseline is named at audit, and no attainment score is produced. A field you cannot fill stays empty. |

**The tile map.** Governance â†’ PM-01, PM-02, PM-03, PM-04 (Scorecard first: the other three hang
off it) Â· Delivery documents â†’ PM-05, PM-09, PM-06 Â· People and governance roles â†’ PM-10, PM-15,
PM-16 Â· Appraise the business case â†’ npv, irr, dpayback, projectmetrics, realoption, montecarlo Â·
Compare the options â†’ scenario, case_decision, decisiontree, mcda Â· Project cost and benefit â†’
forecast Â· Schedule and control â†’ cpm, evm, leveling, crashing, calendar, multiproject, schedrisk.

**Count check: nothing is orphaned.** 10 worksheets + 18 calculators = 28 items, and the tiles
carry 10 + 18. Every item lands in exactly one tile, and each tile's key equals the `group` its
items declare (E-pm-076). The six held records land in no tile and in no leftover section
(E-pm-077).

**Verified.** `python qa/check_page_syntax.py` â†’ **page syntax: OK**.
`python -m pytest tests/test_subject_project_management_acceptance.py -q` â†’ **80 passed**
(73 before this session, seven new). `python scripts/econ_shelf.py --check` â†’ **frozen fixture: in
sync**. Live over CDP against a fresh server on port 8078: at **1280 px** the grid is a four-column
table with the framework's own column headers and `scrollWidth == clientWidth`; at **390 px** it is
one card per row with every field stacked and labelled, and `scrollWidth == clientWidth` â€” **the
page does not scroll sideways at either width**. Before this session the page scrolled to 663 px
at 390 px: the capability tile (566 px inside a 256 px grid) and the top bar were both wider than
the screen, and both now shrink. The empty state renders
*"The grid is empty â€¦ Leave a cell empty and it is named in the audit as a gap - it is never filled
in for you."*, and pressing Run on an empty grid gives *"THIS GRID CANNOT BE RUN YET â€” The grid is
empty: add the perspectives and the fields for each perspective first."*

**No number moved.** No method, preset, template contract, input, check, gate or frozen-contract
entry changed. `src/bp/methods.py` and `tests/fixtures/frozen_contract.json` were not touched.


## 2026-11-03 â€” [product] The tile is named Financial statements; the UI brief is handed to the design lane

**Ask.** The owner's instruction: rename "statements" to "financial statements"; the "Open statements
tile" link cannot be clicked and should be a tile like the other sections; and since that is a design
issue, write an instruction file for MiniMax and close the UI/UX gap and the backend check with it.

**Done here (computation lane).**

1. **Renamed.** `ACCOUNTING_TILES[0]["label"]` â†’ **"Financial statements"**. The `key` (`statements`)
   and `service` (`statements`) are untouched: the renderer, the router and three tests key off them,
   so they are contract and not copy.
2. **The brief**: [`MINIMAX_FINANCIAL_STATEMENTS_UI.md`](MINIMAX_FINANCIAL_STATEMENTS_UI.md) â€” the
   card in the same grid and idiom as `capabilityCard()`, the address `#/financial-statements` with
   `#/statements` kept as an alias, the seven click-path checks, the dialog's content contract
   (201 / 422 / 400), the route table, the live backend transcript, the runbook, the acceptance list,
   and the tests the design lane must not edit.
3. **The test is now tolerant of the address spelling** (`href="#/[a-z-]*statements"`,
   `head === "[a-z-]*statements"`), so the design lane's commit is green on its own without anyone
   touching `tests/**`.
4. **The backend was re-verified live** on 8021 while writing the brief, and the transcript is in it:
   201 solved (11/11 checks, na 2, NI 8,000, assets 10,000, cash flow withheld with its reason, 8
   ratios on request), 201 for two accounts on one statement line (assets 6,000), 422 for an
   out-of-balance trial balance (difference 500, `submitted-does-not-balance`, likely), and 400 with
   the reason for two entities, a comparative column, a consolidation and a Philippine currency.

**Verified.** `test_product_statements_tile` + `test_product_subjects` + `test_subject_accounting_acceptance`
+ `test_docs_sync` = **122 tests OK**.

**Noted for the record.** The tile's link did not respond to clicks. The cause is structural rather
than a broken handler: `subjectTiles()` renders the service tile as a paragraph with a link inside a
block that the `setInterval(decorate, 200)` shim re-decorates, so a click can land on a node that is
about to be replaced. The brief asks for a real card instead, which removes the race rather than
patching it.


**Ask.** The owner's risk, raised at close: *"if two entities' balances are pasted together, the tile
treats them as one entity â€” nothing prints 'this is not a consolidated statement'."* Explore and fix.

**Probed first, and the finding was not the risk as stated.** Two balanced entities do not merge
silently â€” they **crash**, and so does a *legitimate* trial balance with two cash-type accounts
(`Cash 5,000 / Bank 1,000 / Capital 6,000` â†’ unhandled `CheckError` â†’ 500), because `tb_rows` named
every row by its statement line, so both accounts became "Cash". The cases that did not crash were
caught by accident and explained with the wrong message.

**Fixed.**

1. `tb_rows` names each row by its own label and code, and the chart's account identity includes the
   label: two accounts may share a statement line; only a repeated account is a duplicate.
2. The diagnosis call is contained; a core refusal becomes a named refusal, and the route has a
   last-resort guard (a bug is a clean 500, never a stack trace).
3. A preflight refuses, before the chart is built and before any model is asked: a repeated account
   (two sets of balances â€” the case that *balances*), more than one period, two figures on one line,
   or a consolidation mention. A year inside a label is not mistaken for a comparative.

**The eight-case matrix, measured:** cash+bank solves (assets 6,000); two entities refused ("appears
twice â€¦ one set at a time"); two columns refused (comparative); two periods refused (2025-12-31,
2026-12-31); consolidated refused; `Loan 2026 5,000` solves (no false comparative); a normal trial
balance solves; garbage refused with the classification reason.

**Verified.** `test_product_statements` 22 OK (6 new), `test_product_statements_api` 11 OK (1 new:
eight malformed shapes, all 4xx, none 5xx), `test_product_subjects` + `test_docs_sync` 62 OK â€” after
repairing that suite's stale build-pill assertion, which the other lane's D-PM-07 change obsoleted
(the pill is painted from `bp.build.VERSION`; the test now requires the wiring, and the version stays
pinned by `test_docs_sync`).

**Also noted.** B-206 was taken by the other lane's bundle work while I wrote this, so the decision row
is **B-212**; the fix commit's message says B-206 and this records the correction.


**Closed.** The statements tile is done end to end: the ratio bridge (B-203), the tile backend and its
four routes (B-204), and the tile on the Accounting shelf (B-205). Two later commits repaired what the
increment had inherited or exposed: `E_acc_002` now pins the tiled shelf (the owner's instruction
supersedes "no tiles", and the bite moved to `test_product_statements_tile`), and billing's two stale
assertions now pin the owner's **Business Bundle** â€” with a stricter guard than before, since no
credits label may carry a digit on any tier.

**Final verification on the integrated tree** (the other lanes' merges included):

- `python -m unittest discover -s tests` â†’ **Ran 3409 tests, OK**.
- `python scripts/econ_shelf.py --check` â†’ **frozen fixture: in sync**.
- `docs_sync` â†’ 7 tests OK (counts match the measured 3409).
- The statements surface: 100 tests OK (the three contract files, the tile guard, and the accounting
  acceptance suite).
- **Live, through the real server** (`python -m bp.server 8012`): a trial balance with a ratio cue â†’
  solved, `trial_balance`, **11 of 11** checks, **13 ratios** computed, the cash-flow statement
  **withheld with its reason**, and `POST /{id}/replay` â†’ `ok: true` on hash
  `sha256:190be042f94745e2`.

**Left to the owner, by agreement:** the live model run (a *transaction list*, which is the only path
that reaches the council; a trial balance never calls a model). `BP_OPENGO_API_KEY`,
`BP_PROSE_MODEL=kimi-k3`, `BP_COUNCIL_MODEL=deepseek-v4-pro`.

**Named gaps, unchanged and printed rather than hidden:** no file-upload control on the card, `.txt`
export rather than DOCX, intangible amortisation, suspense/error correction (phase 2), consolidated
statements, comparatives/segments/multi-currency.


**Ask.** *"You write the tiles."* The owner authorised the design half of the increment in this lane
rather than handing it on, so the tile ships whole.

**Built.** `subjects.ACCOUNTING_TILES` (five tiles, the first a service), `_tiles()` passing `service`
through, one render hook in `web/index.html` for a service tile, and a self-contained
`<script id="statements-tile">` block: instruction box, Solve, the type-and-why line, the statements,
a **Working / Statements only** toggle, an inline diagnosis card for a refused problem, the withheld
cash-flow note, ratios when asked, two downloads and a replay.

**Presentation only.** Every string on the card is what the server recorded; the toggle chooses which
recorded text is shown, so it cannot change a figure. The download uses the server's own
`statements_only` / working text rather than reassembling anything in the browser.

**The trap that was avoided.** Adding a tile list to a shelf that had none flips the page from groups
to tiles, and a tool in no tile vanishes â€” the lesson the project-management shelf recorded. The four
calculator tiles are therefore keyed by the group names the shelf already used, and a new test asserts
every accounting tool lands in exactly one tile.

**Verified.** `test_product_statements_tile` 6 tests OK; `test_product_subjects` + `test_product_routes`
59 tests OK; suite discovery 3368 tests and the count digits updated in HOME/HANDOFF/CONTRIBUTORS.
No method, preset, input, check or number changed.


**Ask.** Build the accounting statements tile against [`STATEMENTS_TILE_PLAN.md`](STATEMENTS_TILE_PLAN.md):
one instruction box, no field-filling, the four problem types solved end to end, the statements from
the core, the working behind a toggle, an imbalance diagnosed and never plugged, and a frozen record.

**Built.** `statements.py` (classification, grammar, chart vocabulary, compile, present, diagnose,
derive, ratios on request, freeze, store, replay), `statements_verify.py` (six checks), and
`statements_council.py` (one model reading, a dissent on contested labels only, declared ranking).
Four routes ride on the case route, so `server.py` gained one attachment and no new route family.

**Decisions, each probed rather than assumed** (B-204):

1. **A trial balance is posted as one period entry.** As opening balances the same figures score
   7/11 with two real failures; as one entry, 9/11 with `checks_na = 2` â€” every applicable check.
2. **The cash-flow statement is withheld for a trial-balance problem**, with the reason printed: the
   core will happily render one and it is false (the whole cash balance reads as a period inflow).
3. **The verdict is ranked, not voted.** Vocabulary rule > literal standard rule > marker convention
   > dissent; the dissent is recorded and never applied. The student gets one answer.

**Bugs the verifier caught in my own reader** (both fixed, both are why the verifier exists): a
synthesised retained-earnings account with no quote; and two accounts sharing one statement line, so
equipment and its accumulated depreciation now carry distinct names and codes.

**Verified.** 41 new tests: `test_product_statements` 16 OK, `test_product_statements_council` 15 OK,
`test_product_statements_api` 10 OK. Affected set (statements + product boundary + frozen contract +
accounts) **219 tests OK**. `econ_shelf --check` â†’ "frozen fixture: in sync". No method, preset, input,
check or number changed; `tests/fixtures/frozen_contract.json` untouched.

**Noted, not fixed.** Part 1 (the ratio bridge) was committed as `d8ad274`; the shared failures in the
other lanes are recorded in [`OPEN_ISSUES.md`](OPEN_ISSUES.md) Item 16.


**Ask.** The owner's instruction for a standalone accounting statements tile, checked against the
pipeline *before* it was built. Reading the code and probing the core found nine defects in the draft
instruction (the product lane may not import the core; the reading's role and type enums did not match
`ledger.Account`; a trial balance posted as opening balances fails two invariants; a TB-derived
cash-flow statement is internally consistent and false; `schedules.amortization` is a loan; the paper
council's 2,000-token cap truncates a statement reading). The finalised instruction, with the probed
facts and the eighteen traps, is [`STATEMENTS_TILE_PLAN.md`](STATEMENTS_TILE_PLAN.md).

**Why this commit is first.** The tile may not compute. Ratios are the one place where it would have
had to: `ratio_analysis` needs `current_assets`, `cost_of_sales`, `receivables` and eleven more, and
`accounts.build` published flat statements by line but not the section totals, so a caller would have
had to add up lines itself â€” the boundary BACKEND_CONTRACT Â§4 forbids.

**Changed.**

1. `accounts.build` publishes `balance_sheet_groups` (the core's own grouping and totals).
2. `accounts.ratio_figures(pre, st, groups, j)` selects the declared inputs from numbers the core
   already computed; a figure it cannot select is left out, never estimated.
3. `accounts.RATIO_GAPS` names the ten ratios the registry does not define, with the inputs each needs.
4. A current total is published only when every line in that section is classified â€” otherwise the
   figure would be an understated total or a misleading zero.

**Verified.** `python -m unittest tests.test_accounts` â†’ **29 tests OK** (8 new in `RatioSelection`).
`python scripts/econ_shelf.py --check` â†’ "frozen fixture: in sync". `tests/fixtures/frozen_contract.json`
untouched; no method, preset, route, input, check or number changed.

**Probed before any product code exists**, and recorded as traps in the plan: a TB posted as *opening*
balances gives **7/11** with two real failures (`net_income_agrees_across_routes`,
`cash_flow_agrees_across_routes`), while the same TB posted as *one period entry* gives **9/11 with
`checks_na = 2`** â€” every applicable check passes. That single fact decides how the tile must compile
a trial balance, and it would have been an afternoon of debugging to find from the product side.

**Full suite.** `discover -s tests` = **3246 tests, 9 failures**. None is mine: the four that fail
standalone are in the in-flight design/operations lanes, two are `docs_sync` failures caused by another
lane's new document and by `HANDOFF.md` citing a historic lettered decision pair that has no row, and two
pass alone (order artefacts). All are recorded in [`OPEN_ISSUES.md`](OPEN_ISSUES.md) Item 16 with the
exact test ids. The eight new tests are counted: discovery went 3238 â†’ 3246.

**Concurrency.** At 09:50 another process wrote this tree: `src/bp/accounts.py` and
`tests/test_accounts.py` were reverted to HEAD (edits lost) while this lane's doc edits were swept into
commit `f7eba21`. The code was re-applied and re-verified after the revert, which is why the numbers
above are measured twice.


**Ask.** The work order for session 8: *"SUBJECT = operations â€¦ do not start any other shelf
â€¦ a mismatch is itself a defect"* â€” verify, debug and repair the Operations management shelf,
produce one paper per worksheet and read all eleven against V-01â€¦V-20, and fix nothing
without a trap test.

**Measured first.** `subjects.detail("operations")` â†’ 14 tools, 11 worksheets (only OPS-03
not draftable), 7 read-only records, 0 theories, 20 glossary terms, 11 profiles, every
worksheet also on `supply-chain`; `detail["worksheets"]` groups all `None`. Full suite at
the opening commit, on the tree that answered: **3184 tests, 5 failures, 4 errors** â€” and
the 4 errors were this shelf's (`ExampleTest`, `KeyError: 'template_sipoc'`), because none
of the eleven templates had a worked example. The 5th failure was a `balanced_scorecard`
cue set the project-management lane had just added, not this shelf's.

**Fixed (7 ledger rows, 4 found only by reading the produced .docx).**

1. **D-OPS-01 â€” eleven worked examples** (`templates.EXAMPLES`). Each passes its template's
   own `validate()` and every check: that is what `ExampleTest` was trying to do when it
   errored. Four errors â†’ 50 passed in `test_operations_frameworks`.
2. **D-OPS-03 â€” the auto trap** (BLOCKER, B-201). The probe that answers "what can this cell
   borrow from the brief?" was the *retrieval* cue list, which holds "change", "review",
   "cost", "quality", "flow". Before: the trap brief filled `a3.countermeasures`,
   `a3.follow_up`, `toc.subordinate`, `toc.reassess`, `root_cause.materials`,
   `sop.financial_plan`, `pdca.plan`, `pdca.check` and `pdca.act`. After: **0**. Fixed by
   declaring `quote_cues` per part (59 blocks) and matching only that when declared.
3. **D-OPS-02 â€” the conclusion ranked the parts** and named one part both strongest and
   weakest. It now states the count and says a count is not a weight.
4. **D-OPS-04 â€” every sourced cell printed its citation twice.** The block's citations were
   appended to a paragraph whose lines already carried them.
5. **D-OPS-05 â€” a `gap` cell dropped its probe**: the value stream map's two judgement
   cells said "only you can state" and not what to state.
6. **The harness** (`qa/probe_mgt_debug.py`) reported 5 problems and all five were its own;
   it is repaired (quote/gap profiles, `('` in English) and extended with a tool pass.
7. **`qa/probe_ops_shelf.py`** is new: it produced every number in the manual.

**Ledgered, not built.** G-ops-02/D-OPS-06 (no worksheet groups, one flat list), G-ops-03
(one brief sentence can fill two adjacent SIPOC parts), D-OPS-07 (a process-unit query
repeats the unit). The first is a presentation decision on a catalogue surface.

**Owner follow-up, same day â€” the eleven figures.** G-ops-01 was declared, not fixed: none of
the eleven papers drew a figure, because `matrix.LAYOUTS` names a grid for the strategy and
marketing shelves only. The owner chose to build them (*"Build the 11 figure layouts (design
lane, matrix.py): each paper gets a labelled grid built from the items already accepted â€” no
new number, no new evidence"*). Eleven layouts added (B-202), one per framework, each listing
every block of its profile exactly once in the framework's own order; A3's follow-up spans the
page, Kraljic is a quadrant on profit impact Ã— supply risk, root cause is effect â†’ six
categories â†’ supported cause. `matrix.build` still writes nothing: a cell takes the caller's
label, bullets and gap, so the figure can show only what the completion already produced.
`test_E_ops_018` was rewritten from "no figure, and that is measured" to "one labelled cell per
block, none empty, and the figure reaches the paper", so it fails if a layout drops or
mislabels a cell. The probe reports 0 problems and the shelf suite is 46 passed again.

**Owner follow-up, same day â€” the three tiles.** *"create a group for them"*: the shelf listed its
eleven worksheets in one flat list while management, people and project-management group theirs.
Three tiles added (B-206), and the keys are not a style choice â€” `_tiles()` places a calculator in
the tile whose key equals `tool["group"]`, so the keys are the shelf's own tool groups
(**Process and capacity**, **Inventory and planning**, **Quality and evidence**) and any new
vocabulary would have taken all fourteen calculators off the page. A **record map** went in with
them: without it the seven computed records are claimed by no tile, and the page's leftover
heading prints them as *"read and cite â€” no worksheet yet"* cards, which is a calculator
described as something to cite. Measured after the change: 3 tiles holding 4/2/5 worksheets,
6/4/4 calculators and 3/2/2 records, nothing dropped and nothing twice; `test_E_ops_010` asserts
it against `detail("operations")`.

**Left on purpose.** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/registry.py`, every
preset, every route family, every input schema and `tests/fixtures/frozen_contract.json` are
untouched: `scripts/econ_shelf.py --check` still says "frozen fixture: in sync".

**Test count.** 46 tests in the new acceptance suite, plus one trap test in
`test_operations_frameworks.py` (50 tests there). The documented count was set from
`unittest.TestLoader().discover("tests")` in the same commit.

## 2026-11-03 â€” [project-management] Model-assisted writing: help a student complete the framework without inventing a word of it

**Ask.** "Can you do a model assisted writing there? Provide suggestions for the user to complete
it â€” these are all important frameworks and must be done well."

**Did.** Two layers, both beside the input and neither inside it.

1. **Authored help** (`framework_profiles.ADVICE`): 36 blocks of the six project-management
   worksheets now carry two "a usable answer contains â€¦" lines and the unblocking question, in the
   framework's own vocabulary. Served on the existing `/api/templates/<id>` payload as
   `blocks[].advice` â€” no new route, no new provider, offline, deterministic.
2. **Model tailoring** (`prose.suggest_questions`): the same question reworded in the student's case
   words, only for blocks with no sourced and no student item, only when a key is configured. The
   filter (`prose.valid_suggestion`) refuses any question carrying a digit, link, DOI, "et al",
   "ibid" or template brace, over 25 words, or not ending in a question mark.
3. **The page** renders it as a `<details>` "How to write this block" panel. A suggestion is never
   written into the textarea, so it can never be submitted as the student's own evidence.

**Two real defects my own tests caught while building it:** `template_raci` had no advice at all
(it is on this shelf as PM-10, and my first authoring pass forgot it â€” `test_E_pm_064` failed until
it was written), and the tailoring never fired for the five `unit`-typed worksheets because their
blocks are pre-filled with the framework's background, so "no items" was the wrong trigger; it is
now "no sourced and no student item" â€” the cell the student is actually stuck on. A third: my first
insert of the new rows swallowed the `E-pm-063` header, collapsing two acceptance rows into one
test; the suite count exposed it and it is repaired.

**Gates.** Shelf suite **67 passed**; shelf + `docs_sync` + `frozen_contract` + `sample_papers`
green; `econ_shelf` in sync; page syntax OK; 219 shared tests green with only the known baseline
rail failure. Suite count re-measured and the three documents updated to **3162**.


## 2026-11-03 â€” [project-management] Debugging the finished paper: the token `lead`, and a correction to my own reading of the gate

**Ask.** "You must have debugging capability, you must debug project management." Inventory work was
already done; this pass hunted the artefact instead.

**Found and fixed (D-PM-05, BLOCKER).** Unzipping the produced charter paper and reading it line by
line showed paragraph 12 was the single word **`lead`**. Root cause: eight profiles (the five
project-management worksheets plus the Business Model, Lean and Value Proposition canvases) carry
`'lead': 'lead'` in their outline â€” the key repeated as its own value â€” and `complete()` printed it
verbatim under "Framework Overview", while the pipeline's own `_problems` was already reporting
"lead short". Fixed in **both layers**: `completion._lead_of()` now treats a bare token as a declared
absence (paragraph and heading omitted, "lead short" reported only for a lead that exists) so no
future stub can print, **and the eight leads are authored** â€” 56â€“86 words each, grounded on each
profile's own block labels, stating no case fact, no number and no source. The charter's framework
section now opens "A project charter authorises one project: the objective it exists to deliver â€¦".
Trap test `test_E_pm_063` covers all three layers (data authored, guard fails closed, paper prints the
paragraph). Before/after: `qa/evidence/project-management/lead-before-after.txt`. Blast radius
measured green: 139 entrepreneurship tests, 63 shelf rows, the shared contracts.

**Found, and corrected against myself (no defect).** The same paper showed all ten blocks filled from
the framework's background. I first concluded the retrieval path was dead for these five worksheets.
Instrumenting `retrieval.retrieve` disproved it: the gate requires the block's cue in a candidate's
**title**, my mocks built titles that never carried it, and a realistic title places a sourced item
(`dropped: 1, items: 1`). The manual's G-pm-01 row now records the correction â€” an agent's wrong
reading of a correct gate is itself a defect in the record, and it is now named.

**Also checked and clean:** `_unit()` treats a `unit`-field profile through the country branch (a type
confusion with no visible symptom â€” `region` comes out `Global`); the page *does* render the unit
input and posts `body.unit`, which `api.py` passes as `unit_value`, so the five worksheets are
usable from the UI; the page renders a real matrix form for `form_kind == "matrix"`.


## 2026-11-03 â€” [project-management] Delivery and governance: the inventory the owner asked for, two wiring fixes, and the V-01 reading

**Ask.** Debug the project-management shelf (session 7 of 11). Before any code, settle the scope
question: 10 delivery/governance frameworks exist only as read-only records, so the shelf teaches
governance but does not let a student *produce* it.

**Did.**

1. **The 16-item inventory, with a verdict each** (`qa/manual/project-management.md` Â§2.2): 6 of 16
   items complete from a brief, 10 are read-only, 16 of 16 are reachable from the page. Then a
   **ranked proposal** (Â§3) for which records should become completing worksheets â€” COBIT, Balanced
   Scorecard, OKRs, KPI tree, ITIL, Strategy Map â€” every one marked *SHOULD COMPLETE â€” needs owner
   approval*. **Nothing was built**: a recordâ†’worksheet conversion is a new profile and a
   design-lane B-number.
2. **D-PM-01 fixed.** The five `unit`-typed worksheets searched with `cues: ['evidence']` on every
   block and a raw-key query (`scope_in evidence`). 32 blocks now carry the framework's own
   vocabulary and a human query. Product layer only.
3. **D-PM-02 fixed.** RACI's profile said `subject: 'management'` while its id is `PM-10` and both
   the project and people pages carry it (K2). It says `project-management` now; the people page is
   unaffected because it renders from the catalogue row.
4. **The paper, read for real** (U8): `completion.complete` â†’ `draft_bytes`, unzipped, read.
   Structure passes (headings, conclusion, references, byline, 872 words, no spec footer);
   **V-01/V-12 fail at all ten H2 blocks** â€” each is filled from the framework's own background with
   no source and no gap, which is an owner instruction implemented at `completion.py:381-390` and is
   disclosed in the paper. Recorded as G-pm-01, not passed silently.
5. **K4 done by hand.** Every numeric tool was recomputed independently: NPV/MIRR/PI/payback by a
   second Decimal route, CPM by a forward/backward pass written in the test, levelling by a greedy
   simulation, calendars by a working-period simulation, the real option by a CRR lattice built in
   the test, and `project_crashing` by hand. **The crashing output looked wrong and was right** (the
   Aâ€“C path, not Aâ€“B) â€” the correction is written into the manual so the next reader does not repeat
   the mistake.
6. **62 acceptance tests** (`tests/test_subject_project_management_acceptance.py`), one per E-row,
   none skipped, none loosened.

**Gates.** Shelf suite 62/62. Shelf tests + 19 shared modules: 234 passed, 3 failed â€” all three are
baseline failures on other shelves. Full suite before: 3084 tests, 40 failures, 6 errors; after:
recorded in `qa/QA_STATE.md`. `econ_shelf --check` in sync; `check_page_syntax` OK; `docs_sync`
green.


## 2026-11-03 â€” [core] The core is unfrozen as a standing rule (B-197), and 142 of 142 methods now declare their own precision

**Ask.** The owner answered the one question session 5 put to them: *"ON QUESTION, UNFREEZE IT. KEEP
EVERYTHING UNFREEZE UNTIL I FREEZE IT AGAIN, MAKE THIS A RULE."*

**Did.**

1. **Made it a rule, not a permission.** `docs/BACKEND_CONTRACT.md` Â§3 now opens "The standing state is
   UNFROZEN (B-197)"; `docs/HANDOFF.md` Â§2 rule 10 says the same; `docs/DECISIONS.md` B-197 carries the
   four conditions that do **not** relax (frozen-contract test passes, econ_shelf in sync, no loosened
   check, a trap test per behaviour change) and the one way back (the owner says "frozen").
2. **Used it on the defect the question was about.** Four methods declared no `typing` hook, so every
   paper that printed their figures printed the Decimal as stored â€” `Npv A1: 2586.4733808644797823â€¦`.
   `npv_typing`, `_corr_typing` and `_describe_typing` now declare what the library already meant
   (money 2 dp; r/rho 3; p 4; counts 0; statistics at the request's unit, 2 dp).
3. **Closed the template gap.** `case_decision` is not a `Method`, so its `npv_A1` keys had no
   declaration; the core already records each figure's unit and precision in
   `appendix["analysis"]["artifacts"]`, and `session_paper` now reads it. The product formats; it never
   chooses a precision.
4. **Killed the Python repr** the same block printed (`Facts: {'text': â€¦}`): nested values are flattened
   into words.

**Result.** `Npv A1: 2586.47`, `Npv A2: 2136.83`, `Cross 1: 0.10`, `Facts: Text: â€¦; Provenance:
synthetic`. 142 of 142 methods declare a precision (was 138). `tests/test_frozen_contract.py` and
`scripts/econ_shelf.py --check` are green â€” the fixture is untouched, because no pinned surface moved.

**Learned.** The owner's rule is the one that fits the code: a paper cannot print a precision the core
does not declare, and a product that guesses one has started computing. Declaring it where the number is
made is the only fix that keeps one rule for all 142 methods.


## 2026-11-03 â€” [core] Management & strategy, session 4: the module imports from the repo, the nine activities have one set of names, and no paper carries a specification footer

**Ask.** The owner's standing work order: audit one subject shelf at a time, write the acceptance
manual that does not exist, prove every row with an offline test, and fix every defect in the layer that
owns it â€” without weakening a check, editing the frozen core or inventing evidence. Shelf 4 is
`management`: 1 compute tool, 31 worksheets, 0 records, 0 theories, 75 framework profiles overall.

**Did.**

1. **Baseline measured**, not assumed: `211b672` â†’ **2932 tests, 66 failures, 13 errors**, 79 distinct
   failure names (`qa/baseline/mgt-suite-err.txt`). The framework-completion slice: 539 tests, 60
   failed. One documented number did not survive measurement â€” `docs/VALIDATION_HARNESS.md` Â§7.2 said
   22 profiles are reachable from no page; the live count is **17** (D-MGT-09, doc corrected).
2. **The manual** (`qa/manual/management.md`): inventory reconciled 1:1 with the catalogue (31 rows,
   one per worksheet, plus the tool, the 0/0/0 records/theories/glossary, and every UI surface),
   **46 E-rows**, a traceability matrix, the declared gaps and the residual risk.
3. **The acceptance suite** (`tests/test_subject_management_acceptance.py`, 46 tests): every row is one
   test named `test_E_mgt_nnn__<behaviour>`, run offline, through the real paths.
4. **Read the artefacts, not only the tests.** `qa/probe_mgt_paper.py` builds a value-chain paper, a
   change paper, a no-source twin of each and the worksheet export, unzips `word/document.xml` and reads
   the sentences. Two defects were invisible to the suite and obvious in the file: â€œthat a activitie for
   which no evidence is recordedâ€ (D-MGT-10) and nine empty boxes in the value-chain figure (D-MGT-02).
5. **Fixed eleven defects** (`D-MGT-01â€¦11`), two of them outside the shelf entirely: an import-time
   `exec(open("C:/tmp/profiles_out.py"))` that made `framework_profiles` unimportable on a clean
   checkout (BLOCKER), and the specification footer still printed by `deliverables.py` (BLOCKER, P3).
   Decision **B-195** records the naming convention, the `research` fill and the prompt's unit rule.
6. **Left two BLOCKED with a pinning test each**: a frozen method with no `typing` hook prints a
   50-digit `Npv` (D-MGT-08), and the shelf page counts 28 catalogue records beside 31 worksheets
   (D-MGT-09). Both need an owner decision and both would fail a test the day they are fixed.

**Result.** Full suite **3084 tests, 40 failures, 6 errors** â€” **0 new failure names**, 33 repaired
(79 â†’ 46). Framework-completion slice 60 â†’ 27 failures, all remaining on the marketing shelf, which was
not started. `test_docs_sync` + `test_frozen_contract` 10 passed; `scripts/econ_shelf.py --check`
â€œfrozen fixture: in syncâ€.

**Learned.** A profile is a declaration, and when the declaration exists twice the file tells two
stories: the tests read one and the product ran the other. The same is true of a cue set that does not
contain the words its own query asks for â€” every mocked test passes while the live gate refuses
everything. And the artefact still finds what a green suite cannot.


## 2026-11-03 â€” [core] Entrepreneurship shelf, session 6: the marking guide reaches the plan, eight period-less presets deliver again, and a plan block's columns are proposed

**Ask.** The owner's standing work order: audit one subject shelf at a time, write the acceptance
manual that does not exist, prove every row with an offline test, and fix every defect in the layer
that owns it â€” without weakening a check, editing the frozen core or inventing evidence. Shelf 6 is
`entrepreneurship`: 46 tools, 6 worksheets, 6 records, 0 theories.

**Did.** (1) **Inventory confirmed against the live catalogue**, not the docs: 46 / 6 / 6 / 0, and
`docs/CURRICULUM_MAP.md` said "5 worksheets" (D-ENT-11). (2) **Baseline measured**: 2932 tests, 66
failures, 13 errors (`qa/baseline/ent_suite_err.txt`) â€” the documented opening state, and none of the
79 named failures is this shelf's. (3) **The manual**: `qa/manual/entrepreneurship.md`, eleven
sections, 46 per-tool contract rows, **106 E-rows**, a traceability matrix and six declared gaps.
(4) **The suite**: `tests/test_subject_entrepreneurship_acceptance.py`, **106 tests, 106 passed** â€”
one per E-row, offline, retrieval mocked, 46 of them generated per tool, 12 hand recomputations from
the student guide. (5) **The probes**: `qa/probe_ent_shelf.py` (every tool through its own preset),
`qa/probe_ent_mapping.py` (a plan block's columns through the core mapper), `qa/probe_ent_plan.py`
(the witness plan and the computation deliverable, judged against V-01â€¦V-20). (6) **Six defects
fixed**, each with a trap test and a ledger row (D-ENT-01â€¦D-ENT-05, D-ENT-11).

**The one that mattered most** was not on the work order's list: three entrepreneurship tools â€”
Trend forecast, Descriptive statistics, Chi-square â€” delivered **nothing**, with a refusal that read
`reference failure: RefMismatch('token wants n/None, artifact is n/None')`, identical on both sides
of the comma. The probe that found it is the one the economics session wrote; it took a single pass.
Root cause: a preset that declares no period hands the method's own template `None`, the template
writes that into its reference token as the **text** `None`, and `ArtifactStore.resolve` then
compares the text with a real `None`. Eight presets were blocked across accounting, research/finance
and this shelf, and `pearson` crashed outright inside the frozen `corr_template`. Fixed in the
artifact layer (the text `None` is the absence of a label) and at the template call (the period is
handed over as text), never in `methods.py`. **46 of 46 tools now deliver through their own preset**
(43 before).

**The work order's risk (b) was real.** A rubric attached to a plan was refused by signature:
`chat.start` took no `rubric`, so `paper.missing` â€” which already read `state["rubric"]` â€” could never
see one. The plan is a *second engine*, and the guide had been wired into `completion.complete` only.
Fixed across `chat.start`, the draft seam (now `chat.draft`, shared by all four plan profiles),
`api.py` and the page, and the gate got the student's own switch: a rubric can name a section no
profile carries ("Appendices"), and a permanent block with no recourse is not a gate, it is a dead
end. Two reader defects surfaced while proving it â€” a word-budget line in a **list** rubric became a
sixth weighted criterion (the tolerance's `%` read as its weight), and "Referencing" could never
match "References". Both block a finished paper for ever; both are fixed with traps.

**Also fixed.** A plan block's columns were refused by the core mapper for the shape the plan itself
asks for (list columns from a spreadsheet, drivers typed) â€” D-ENT-02; and the engine that read a
scanned brief never reached the caller or the page, though the intake record carried it â€” D-ENT-05.

**Left alone, deliberately.** `D-ECO-02`'s tightness denominator (another session's BLOCKED row), the
marketing worksheet registration failures and the strategic-positioning prompt failure: all three are
in the historical failure set, belong to other shelves' sessions, and are recorded rather than
touched. `docs/HANDOFF.md` line 12 and `docs/WORKLOG.md`'s older headings carry double-encoded em
dashes from an earlier lane; noted, not swept, because they are not this shelf's text.

**Correction, same session (B-196).** The owner reviewed the shelf's surface and ruled that the
marketing plan â€” STP and the marketing mix â€” belongs to the marketing shelf, where it already lives:
*"delete that in entrepreneurship"*. `MKT-02` is now off the entrepreneurship page (removed from
`worksheets` **and** `catalogue_ids`, so neither the worksheet nor its catalogue row is duplicated
there); the shelf carries its own five worksheets, all shared with management, and the worksheet
itself is untouched on marketing. `VALIDATION_HARNESS.md` Â§7.1 loses the row and is re-measured â€”
**30 of the 59** worksheets a subject page serves are shared, where the header still said "31 of the
55" â€” and `CURRICULUM_MAP`, `KNOWN_LIMITATIONS`, the manual (E-ent-001, E-ent-085, E-ent-091) and the
two tests that encoded the old pairing were corrected to the owner's assignment rather than loosened.
The probe also stopped assuming every `impl` returns a mapping: the core now returns a bare value for
`npv` (another lane's unfreeze, B-197), so the sweep reads typing from the headline metric instead of
crashing â€” 46 of 46 still deliver, findings none.

**Next.** `operations` (shelf 7 of 11) carries the largest worksheet surface: eleven T4 worksheets
sharing the supply-chain shelf. Its top three risks are recorded in `qa/QA_STATE.md`.

## 2026-11-03 â€” [core] Economics shelf session 2: two label defects fixed under B-190, one blocked, and the shelf's missing manual written

**Ask.** The owner's work order: audit and repair the pipeline one subject shelf at a time, writing
the acceptance manual that does not exist, then proving it with tests and fixing every defect â€”
without weakening a check or inventing evidence. The session parameter said `economics`; the
recorded order said `finance` next, so I asked, and the owner chose `economics`, reminding me that
`finance` is "doing some fixing" in another session. It stays skipped.

**Did.** (1) **Baseline measured, not assumed** â€” `ab0be0d`: 2627 tests, 66 failures, 13 errors,
634.8 s (`qa/baseline/2026-11-02-ab0be0d-suite-err.txt`). **None of the 79 named failures belongs to
economics**; they are all worksheet/framework-completion and one network test, and they carry
forward to their own shelves. (2) **The manual** â€” `qa/manual/economics.md`, ten sections, 59
generated per-tool contract rows, 84 E-rows, a scoreboard and the declared gaps. (3) **The suite** â€”
`tests/test_subject_economics_acceptance.py`, 83 tests (59 generated per tool, 24 cross-cutting),
including 23 worked examples recomputed by hand from the student guide rather than from the method.
(4) **The sweep** â€” a unit audit over all 59 tools found that `labour_market` typed a share and a
ratio as currency; a report scan over all 59 presets found that the `currency` paper mislabelled its
source amount. Both were **B-190**, fixed with trap tests. `docs/CURRICULUM_MAP.md`'s "55 tools" was
`D-ECO-08`, fixed. (5) **Two false alarms retired, not written up as defects**: `@unit` and a `None`
`typing` hook are both handled by `orchestrator.py` (lines 227, 233-234, 270), and all 151 `related`
ids resolve (131 local, 20 cross-shelf). (6) **One carried-forward claim re-tested and closed** â€”
session 1's `tax_incidence` units defect does not reproduce (`typing("producer_share")` is
`("ratio", 4)`), because B-179 renamed the duplicated hooks. (7) **A guide paragraph** on what a
student can attach, so the intake/brief/dataset/sources/rubric work is declared on this shelf.

**Left.** `D-ECO-02` â€” tightness divides a count by a rate â€” is BLOCKED on the owner choosing the
replacement definition and whether a new input enters the frozen schema; the owner has already ruled
that the absent-denominator case must refuse with a named gap, never divide by a rate. The
documented test count is re-measured in the follow-up commit, because another lane held uncommitted
edits in the five docs that carry it while this work landed.


## 2026-11-03 - [portfolio] The Portfolio Lab teaches itself: four worked cases, click by click

**Ask.** "make users understand and know how to use it by teaching and guiding them through examples. remember when i asked you for an example using a case where you explain it in simpler terms? do the same but oriented for finance students. use 3 or more different cases depending on how best it can illustrate its capability. you may add but 3 is the lowest. then guide students step by step on what to click to achieve desired result. base it on your experiences on how student use you in this particualr field only that this pipeliune is isntneded to exceed that capability as it can record multiple weeks and others. as usual, test and debug before reporting success."

**Did.** (1) **Four worked cases in the lab**, on the Portfolio landing under *Learn by example*: stock selection, one-date valuation and report, a semester mock fund with a time-weighted return, and the risk/return assignment. Each card states the assignment, what you need, numbered click steps using the page's real labels, what you should see, the sentence to write in the paper, and what it does not do. (2) **A Start button per case that only opens the right control**: the watch list with the symbol box focused, the Evaluate tab with the instrument select focused, or the create form in paper/fund mode with the name field focused. It creates no book and runs no method (pinned). (3) **A student-facing long guide**, `docs/PORTFOLIO_LAB_STUDENT_GUIDE.md`: the four cases in full, a gap-decoding table, a "what a professor can verify in your submission" list, a troubleshooting table and a glossary; indexed in `docs/HOME.md`.

**Why.** The owner's students ask for stock picks, portfolio values, fund returns and risk figures; the lab now answers each with a recorded, sourced, reproducible procedure, which is more than a one-shot chat answer can do (weeks, flows, immutable snapshots). Teaching it in the page means the student does not have to read a manual to start.

**Files:** `web/index.html`, `docs/PORTFOLIO_LAB_STUDENT_GUIDE.md`, `tests/test_portfolio_student_guide.py`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `docs/HOME.md`, `qa/evidence/portfolio/lab-worked-cases.png`.

**Decisions:** B-189.

**Verified.** `node --check` on the inline script; live headless-Chrome CDP run: four cards render (first open), each Start button lands on the intended control (`#plnewsyms`, `#plid`, `#pfname` paper, `#pfname` fund mode), the lab opens from inside a book, 0 page exceptions; `tests/test_portfolio_student_guide.py` (12) cross-checks every click label against `web/index.html` so the teaching cannot drift; full suite 2892 tests with the targeted batches green; `ui_smoke` 0 failures. The example values in the cards and the guide are live values from this machine on 2026-11-02 (AAPL 344.63 / P/E 44.90; NAV 14,541.93; TWR -0.10235 over 3 periods with a 500 flow; AAPL prefill with 24 returns), labelled as such.

**Open/next.** None. The guide's screenshots live in `qa/evidence/portfolio/`; the printed case cards show the same click path as the page.

## 2026-11-02 â€” [ui] Three launchers that behave as one, and Rates and FX as two cards

**Ask.** "MAKE THEIR APPEARANCE UNIFORM WHEN CLICKEDâ€¦ DONT DEFAULT OPEN THE BUSINESS CALCULATOR TO BOLD
BECAUSE IT IS NOT CLICKED. ANY OF THEM WILL BECOME BOLD WHEN CLICKED." Then, on the *Rates and FX*
panel: "ACT AS A PROFESSIONAL UI AND UX DESIGNER AND IMPROVE THEIR APPEARANCEâ€¦ ENSURE THAT THEIR
FUNCTIONALITIES ARE INTACT."

**Did.** (1) The launcher row was `btn sm primary` / `btn sm` / `btn sm` â€” the calculator wore
`primary`, so it read as chosen before any click, and the three did not share a shape. All three are
`btn sm quicklink` with one `.is-active` state (navy fill, weight 750), set by a single delegated
listener in the capture phase: clear the row, mark the pressed element, `aria-current="page"`.
Nothing is bold on arrival. (2) *Rates and FX* was one flex row of eight controls; the maturity
select sat beside an FX button and nothing said which button read which fields. It is now two
`.lookupcard` blocks in a `.marketgrid` â€” FX rate (Base, Quote, Date, then its own button) and
Treasury par yield (Maturity, then its own button) â€” with small-caps captions above full-width
controls and the never-auto-fill sentence moved under a rule at the foot of the panel. All seven ids
are untouched, so `bindRatesPanel` binds the same handlers and still fills the dropdowns from
`/api/currencies`.

**Why.** The row was a *pre-selected* control: `primary` is the theme's "this is the action" colour,
and using it for one of three peers states a preference the product has no basis for. And a mixed
row is a UI defect with a measurable cost â€” the reader cannot tell which fields a button consumes, so
they press *Treasury yield* with an FX base still on screen.

**Verified.** `test_product_subjects.py::test_the_three_ways_in_are_one_control_and_none_starts_chosen`
(three `quicklink`s, no `primary`, the bold state exists, one handler) and
`test_market_panels.py::test_rates_and_fx_gives_each_lookup_its_own_card` (two cards, seven ids, no
`marketrow`, the FX button ordered inside the FX card). Live on **8002**: page 200 at 782,425 bytes
with both blocks; `/api/currencies` returns the ISO list; `/api/market/fx?base=USD&quote=EUR` â†’
0.8942 (2026-11-02); `/api/market/riskfree?maturity=10Y` â†’ 0.0494 (2026-10-30) â€” both lookups answer
through the new markup. 2880 tests collected, unchanged; `test_web_inline_script` still parses the
page. The 77 failures in a full run are the framework-completion build the other session has in
flight (bcg/aida/kano/rfm/pestel/value-chain families) â€” none in a file this change touches.

**Open/next.** The active state is momentary by design: pressing a launcher navigates away and the
shelf re-renders neutral. If the owner wants "the one you last used" to persist across a return, that
is a stored preference (per shelf, in `sessionStorage`) and a decision, not a style. Still open from
the finance QA list: the PDF writer, G-fin-05 (`ols_robust` has no preset), D-FIN-12, and the
V-01â€¦V-20 paper judgement.


## 2026-11-02 â€” [rubric] A rubric can be read, and only what it states is carried

**Ask.** "i forgot something. also a rubric to be uploaded which should be followed in writing the paper"

**Did.** Built the reader that everything else depends on â€” `src/bp/product/rubric.py` (standard library
only, offline, JSON-safe) â€” which parses a marking guide in three layouts (pipe table, numbered or
bulleted list, headed criteria) into `{criteria[], sections[], word_budget, citation_style,
total_weight, problems[], confirm_required}`. Six rules stop it inventing a requirement: a weight is read
only when stated and is `None` otherwise (never an assumed `1/n`); weights that miss 100 are reported,
never rescaled; a required element comes only from an explicit column or clause, verbatim; a word budget
comes only from a stated number of words, so `8 pages` stays `None`; sections only from an explicit
structure label; a citation style only when exactly one is named (two named styles are a problem, not a
choice). An unreadable rubric is not half-read: `ok: False`, raw text preserved, `confirm_required: True`.
`qa/manual/rubric.md` is the manual (19 E-rows, all PASS) and `tests/test_product_rubric.py` is the suite
(19 tests). Decision B-187.

**Why.** The owner's rubric requirement is the one input that changes what the paper must *do* rather than
what feeds it. Reading has to be exact first: a guessed weight or an invented required element becomes a
requirement the student never wrote, and it would then be enforced against their own paper.

**Found by the reader's own probe, before the suite existed.** (1) BLOCKER â€” `WEIGHT_RE` ended in `\b`, so
`30%` at the end of a table cell never matched and **every percentage weight was silently dropped**
(`weighted: 0` on a rubric whose weights total 100). (2) MAJOR â€” an unbulleted lead-in line
("The report is marked on:") was read as a criterion. Both fixed, both trapped by tests
(`E-rub-017`, `E-rub-001`, `E-rub-016`).

**Verified.** `pytest tests/test_product_rubric.py` 19 passed; `unittest tests.test_product_rubric` 19 OK;
`qa/probe_rubric.py` on six realistic documents (table, list, no weights, prose, marks column, page limit)
shows the intended behaviour for each. Docs kept in step: B-187 in `DECISIONS.md`; the suite count
re-measured with the gate's own counter (`qa/_count.py`, which calls `test_docs_sync._suite_count()`) at
**2878**; a `1.60` changelog bullet restores the build that `HOME`/`HANDOFF` had already claimed (HEAD
said 1.60 while its newest changelog entry said 1.59 â€” that drift is fixed here). No frozen core, method,
preset, input, check, number, route family or paper rule touched; no new dependency; no network or model
call.

**Count caveat, stated plainly.** Three lanes write in this worktree at once, so the count is a snapshot:
**2878** is what the gate counts here, at this commit. It includes tests sitting in another lane's
*uncommitted* work, and a clean checkout of this commit holds ~101 fewer because several test modules need
provisioned runtime data (intake store, document index, corpus) that is not in git â€” that shortfall is a
property of the repository, not of this commit, and is worth its own session.

**Open/next.** Binding is **not built**: the outline, the word band and the required elements are not yet
driven by a parsed rubric, there is no "Rubric coverage" appendix, no export gate on a required criterion,
and no upload role or button for a rubric specifically. A scanned rubric needs the OCR chain. A rubric
cannot be scored and never will be â€” adequacy is a human judgement.


## 2026-11-02 â€” [portfolio] The Portfolio Lab is rebuilt around tasks, and a student can add any symbol

**Ask.** "I DONT SEE HERE THAT USER CAN ADD ADDITONAL SYMBOLS ASIDE FROM AAPL. ALLOW USERS TO ADD. ALSO ACT AS A PROFESSIONAL UI AND UX DESIGNER AND IMPROVE THE APPEARANCE OF PORTFOLIO LAB. YOU JUST THREW EVERYTHING THERE WITHOUT ANY SENSE OF ORGANZIATION AND DEISGN."

**Did.** (1) **Multi-symbol entry replaced the one hard-coded box.** `#plnewsyms` takes one or many tickers (comma/space/semicolon, up to 25 per press, any quoteable ticker, not just the B-178 reference list); `plAddSymbols()` normalises them, posts `{symbol, record: true, provider}` for each, reports added/failed by symbol, clears the box and refreshes the watch list; `plRemoveSymbol()` deletes a row; the prefill selects (`#plid`, `#plida`, `#plidb`, `#plidm`) are rebuilt from the tracked series so an added symbol is immediately evaluable. (2) **The lab became three tabs** - Watch list and prices / Find candidates / Evaluate - with `state.plTab`, `plShowTab()`, one provider toolbar and panels `#plpanel-watch|screen|prefill`; each tab holds one task and each blocked action names its reason. "Use my watch list" copies tracked tickers into the screening field; screening with an empty field falls back to the watch list. (3) **The landing page was re-organised**: hero, then a two-column books + create-book row sized to content, then the lab under a *Before you buy* kicker, then the six-step guide as a `<details>` card; the book workspace gained a Find candidates tab and overview quick actions; Holdings is now a card per task with the reference list, example books and paste/import inside collapsible cards.

**Why.** The symbol box showed `AAPL` and nothing else, which read as a demo rather than a tool, and the lab had been rendered as one undifferentiated stack of controls. The owner asked for both the capability and the organisation in the same breath: a student must be able to bring their own tickers and must meet the lab as a sequence of tasks.

**Verified.** `node --check` on the page script; 8 page/route tests in `tests/test_portfolio_screener_ui.py` (tabs, panels, multi-add markers, no hard-coded `AAPL` value, prefill-fills-only) plus the 14 ported module tests, all green; live on 8000 through a headless Chrome CDP run - `MSFT, NVDA` added and recorded, watch list 1 -> 3 rows, selects populated with all three series, tab swap correct, screen-from-watch-list returned AAPL/NVDA/MSFT with named gaps, no console error or page exception. Screenshots in `qa/evidence/portfolio/`. No frozen core, method, preset, check, number or endpoint changed; suite 2854 tests.

**Gate fix found in the same pass.** `scripts/ui_smoke.py` still required the marker "not teacher-approved", which the earlier clutter commit (735d849) deleted on purpose; the marker is now the honesty banner ("Honesty: what was not done"), matching `test_product_subjects.py`, and the smoke run is 0 failures.

**Open/next.** The lab still needs the Alpha Vantage / Massive keys configured server-side for live rows (without them every metric is a named gap); the watch list is global to the machine, not per book; a symbol the provider cannot resolve is reported per symbol rather than pre-validated in the box.

[product] Worksheet registration WO-2/WO-3: 32 orphan profiles registered as worksheets, 8 new profiles built, CHG-15/STR-19/STR-20 added. Proposed decision: register orphan framework profiles as T4 worksheets (structure and evidence audit only); does not change frozen core, methods, or paper claims.

## 2026-11-02 â€” [portfolio] The screening lab is ported back and surfaced in the Portfolio Lab

**Ask.** "i am checking the portfolio again and im tired of repeating myself. the portfolio must have a feature that will guide students based on common criteria on what stock to pick. i had it instructed before and spent hours for that, now i cant see it. can you check if its there. if its there, surface it in the UI and ensure they are wired correctly"

**Did.** (1) **Found it.** The feature exists â€” on `origin/main`, built as builds 1.23-1.29 (tracked-instrument price store, `screener.py`, `prefill.py`, the Finance-page UI and its tests), and never merged into `corpus/merge-v1`. This branch had only the B-178 guidance. (2) **Ported it, not re-invented it.** Brought `screener.py` (declared-criteria screening of a student-supplied candidate list, sourced rows, named gaps, no recommendation) and `prefill.py` (exact frozen inputs for risk/portfolio/CAPM, `ready` + gaps, never runs a method) into the product layer; merged the tracked-instrument price store (append-only per-symbol JSON, same-day dedupe, returns series, readiness, 30-day daily-bar seed) into `instruments.py` beside the guidance; added Massive daily bars/history, Massive and Alpha Vantage overviews, derived P/E+ROE from SEC XBRL and Massive market cap, and the fundamentals chain to `marketdata.py`; added the `/api/cases/instruments` CRUD/record/seed, `/api/cases/screen` and `/api/cases/prefill` routes to `api.py`. (3) **Surfaced it in the Portfolio Lab** â€” the panel now renders on the landing page under the How-to-choose guide and in the Holdings tab of a book: track-and-record, candidate list with sort (one-day return, mean, Sharpe, price, market cap, P/E, ROE), include-fundamentals, Help me choose, the watch list (Record/Seed/Use), and prefill into the Calculator (fields only; the student presses =).

**Why.** The owner spent hours on this feature and could not find it because it lived on a branch this line never took. Re-deriving it would repeat the work; porting the proven modules and their tests restored it in one increment, and placing it in the Portfolio Lab puts the matching tool beside the book it serves.

**Verified.** 14 ported tests (`tests/test_product_screen_prefill.py`) and 7 page/route tests (`tests/test_portfolio_screener_ui.py`); live on 8000 â€” tracked AAPL and recorded its 2026-10-30 close 344.63; screened AAPL/MSFT (344.63 / 521.91, gaps named); derived AAPL market cap 5.03T, P/E 44.90, ROE 1.519 from SEC + Massive with a response hash; the risk prefill returned `ready: false` with "record at least two price snapshots before a return exists"; headless Chrome probe confirmed the panel on the landing (buttons Track/Help me choose/Record/Seed/Use/Prefill) and in the Holdings tab, with the watch list populated. Screenshots in `qa/evidence/portfolio/`.

**Open/next.** The derived ratios are arithmetic on sourced facts, not verified profiles (a small equity base can make ROE look extreme); the shortlist needs the Alpha Vantage / Massive keys configured server-side; the panel is on the Portfolio Lab and not re-added to the Finance page (one home, no duplicate UI).

---

## 2026-11-02 â€” [finance] The wordiness, measured; and a heading restored

**Ask.** "we still need to clean up the wordiness of finance subject."

**Measured first.** `qa/probe_wordiness.py` counts words per field across the shelf: `what` mean 13.8
(max 28), each step mean 10.2 (max 23), each common mistake mean 9.4 (max 18), guidance 80. So the copy
was **not** bloated in general â€” two lines were out of line with the rest.

**Did.** Unit-economics card 28 â†’ 15 words; the long break-even step 23 â†’ 16; the shelf `guidance`
80 â†’ 58 by turning five sentences into five short clauses. Added
`test_052__the_shelf_copy_stays_short` with the measured ceilings (guidance 65, what 20, step 18,
mistake 18) so the shelf cannot drift back.

**Also fixed, honestly:** a concurrent edit to this page made the computed-tools heading dynamic
(`"Quantitative Finance"` for finance, `"With computation"` otherwise) and, in doing so, removed the
literal heading every other shelf renders â€” which broke `test_product_subjects`. Both headings are
written literally again: finance keeps its own name, everyone else keeps the plain one.


## 2026-11-02 â€” [core] B-183: the mid-year DCF check, unfrozen and fixed

**Ask.** "okay go. unfreeze and finish it."

**Did.** `_dcf_tests` now computes the convention the caller did *not* declare and asserts the
direction that convention implies, instead of always building `timing="mid"` and comparing it with
an input that may already be mid-year. One expression changed; no method, formula, number, metric,
unit, tier or `test_names` did. `econ_shelf.py --check` still says "frozen fixture: in sync", which
is the point: the pinned public contract is untouched, only an acceptance check that could never
pass was corrected.

**Result.** The `dcfmid` tile delivers. D-FIN-01 â†’ FIXED, E-fin-007 â†’ PASS, scoreboard
**48 PASS, 0 BLOCKED, 2 GAP**. `qa/check_finance_downloads.py` now reports the tile among the ones
that download a paper.

**Next.** The finance shelf's student-facing copy is the remaining complaint ("wordiness"): 35 tool
cards whose `what`, steps and common-mistake lines run to two sentences each.


## 2026-11-02 â€” [paper] Every tile downloads its paper, and the sources block is closed

**Ask.** "where will the completed paper go in finance? each tile or each function there must have
downloadable feature for user to download their paper" + "on a) close that" (the declared-sources
section I had left open).

**Found.** The result screen gave every computation a **Download spreadsheet**, but the Word paper
was conditional on `state.draft` â€” which a plain computation session never has. So all 35 finance
tiles could be run and read but not downloaded as a paper.

**Did.** `POST /api/sessions/{id}/paper` (Word or Markdown) built by the new
`bp.product.session_paper` from the delivery itself â€” report, honesty, assumptions, limitations,
checks, spec hash â€” with **409 before delivery** and **422 for an unknown format**. Two buttons on
the results screen. Declared sources finished on both paths: a section headed *"Sources you declared
(not evidence)"* with the caveat in prose (not only in the heading), and `chat.declare_sources` +
one wrapper on `draft()` so a conductor paper carries the same section exactly once.

**Why one wrapper, not six builders.** The five prose builders each assemble their own sections;
wrapping `draft()` keeps the behaviour identical everywhere and avoids six copies of the same rule.

**Verified.** `tests/test_session_paper.py` â€” 15 tests including the route's 409/200/422/404 paths
and the .docx being a real zip container. Page passes the Node `--check` gate. Suite count 2830.


## 2026-11-02 â€” [ingest] P3: the dataset leg is proven, and its provenance is no longer lost

**Found.** The dataset-to-method path was built (B-065/B-071) and refused bad mappings correctly,
but it did not survive the hand-off to a session: `to_method_inputs` returned a document-level
`provenance` object, and `orchestrator.start` reads `provenance` **per input**. So a page forwarding
the mapped request recorded every value read from the spreadsheet as `"user"` â€” the specification
said the student typed numbers that came out of a file. That is a provenance defect, not a cosmetic
one: the paper's claim about where a figure came from would have been wrong.

**Fixed (additive, product/core boundary unchanged).** The mapped request now also carries
`input_provenance` (`{input: "sourced"}`) and a `data_manifest` entry with the file name, its
SHA-256 and only the columns used. Existing callers and tests are unaffected (the keys are new, the
old ones unchanged).

**Verified.** `tests/test_ingest_pipeline.py` (11 tests): the delivered mean equals hand arithmetic
(`10.50`), the spec records `sourced`, the two-column map reaches `welch_t`, a date column stays a
date, the manifest names only used columns, and each refusal names its reason. Suite count 2815.


## 2026-11-02 â€” [intake] P2: the student's own sources are cited, never evidence

**Did.** `bp.product.sources_file` (stdlib only) reads a declared subset of `.bib`, `.ris` and
`.csv` into entries plus **named problems**; `intake` gains `SOURCES_EXT`, `kind: sources`,
`attach_sources` and `declared_sources`; `POST /api/intake/{id}/sources` reads a stored list and
`GET /api/intake/{id}/sources` returns the entries and one citation line each; the page gains a
**Show sources** action that states, on screen, that these are the student's citations and that
nothing was verified.

**The rule, from the owner (B-182).** "Cited, not evidence." A declared source never enters the
evidence Reference list, never satisfies an evidence gate (V-12) and never fills a named gap. That is
why this commit does **not** append declared sources to a paper's References: the separation is
structural, not editorial, and the review screen shows the declared list beside the paper instead.

**Still open (deliberate).** Where a declared list should *appear inside* an exported paper is a
design question for the six draft builders, each of which assembles its own References list and none
of which receives an intake id. Recorded in `qa/QA_STATE.md` as the next increment rather than
half-wired into one of them.

**Verified.** `tests/test_sources_file.py` (18 tests) and 10 new tests in
`tests/test_product_intake.py`; page passes the Node `--check` gate; frozen contract green. Suite
count 2804.


## 2026-11-02 â€” [intake] P1: an attached file becomes the instruction, and says it is unverified

**Did.** `intake.ROLES` + a `role` on the record (never guessed); `POST /api/intake/{id}/brief` reads a
**stored** file with `documents.extract_document` (the same reader the brief route uses) and returns the
text flagged `unverified: true`, recording `role: brief` and the text's SHA-256 on the record;
`_summary` exposes `role` and `brief_chars` so the list shows what a file is for. The page gains a
**Use as the instruction** button on any row whose extension a reader can open, which fills the brief
box and starts nothing; the empty-state text now says which files can be used that way.

**Why not a new brief parser.** `extract_document` already opens PDF, Word and text, and refuses the
rest with an actionable message; re-implementing it would have been a second reader to keep in step.

**Refusals kept.** A .csv/.xlsx is refused as an instruction (it is a dataset), a scan with no OCR
engine is recorded `ocr_required` rather than returning empty text, and a refused brief does not
relabel the file.

**Verified.** `tests/test_product_intake.py` â€” 28 tests in the file, 15 of them new; the page still
passes `tests/test_web_inline_script.py` (Node `--check`). Suite count 2776.


## 2026-11-02 â€” [core docs] Two decision cross-references, and the rule for a student's own sources

**Ask.** "were you able to fix the errors you found? i forgot something, like a mechanism or a button
for enabling users to add an instruction file, dataset and sources files that will be used by the
pipeline. do you think we can still add this?" â€” followed by the scope decision (instruction file,
sources file, dataset wiring) and the rule for sources: **cited, not evidence**.

**Did.** Found the mechanism already largely built: `POST /api/intake` (B-065 store), the "Attach
files" button, CSV/XLSX â†’ typed table via `bp.ingest`, table â†’ method inputs via `column_map`, and
PDF/OCR extraction (B-107, B-110). Fixed the two drifted references that made it look unfinished:
`documents.py` cited B-105 (entrepreneurship) for document reading â€” the decision is **B-107**; and
`PARKED_QUEUE.md` still described PDF/OCR as "explicitly refused by design", which B-107/B-110
overtook. Recorded **B-182** for the owner's sources rule so the coming code cites a decision rather
than a preference.

**Next.** The three legs â€” a persisted instruction file, a stdlib sources-file reader, and an
end-to-end proof of the dataset-to-method-input path â€” in that order, one commit each, with the
frozen contract re-run every time (all three are additive product-layer work; no method, preset or
route family changes).



## 2026-11-02 â€” [finance] QA session 2: the shelf's missing manual, its acceptance suite, and the paper's numbers

**Ask.** The 11-shelf QA work order, `SUBJECT = finance`: write the manual that does not exist, prove it
with an executable suite, fix every defect in the correct layer, ledger the rest.

**Read first, and one thing to note.** The work order's reading order, then `qa/QA_STATE.md` and
`qa/QA_DEFECTS.md` from session 1. The WORKLOG entry above records the owner telling the *core* session
"dont do finance yet, its doing some fixing"; that fixing is the design lane's finance UI work, landed at
`2c2ca4f` (FX dropdowns, provenance panel). No finance file was dirty when this session opened, and this
session touched no presentation file, so the two lanes did not collide.

**Did.** (1) Baseline on `ab0be0d`: 2630 tests, 66 failures, 13 errors, measured against session 1's
closing set â€” identical except one test each way (see `qa/QA_STATE.md` Â§1). (2) `qa/manual/finance.md`:
35 tools, 23 records, 22 glossary terms, 0 worksheets, 0 tiles, 50 numbered `E-fin-nnn` rows, each citing
`LIBRARY`/`detail()`/the harness rules. (3) `tests/test_subject_finance_acceptance.py`, 50 tests, one per
row. (4) **D-FIN-02 fixed** in `src/bp/product/chat.py` â€” the finance capability papers printed the core's
full `Decimal` (see `docs/CHANGELOG.md`). (5) **D-FIN-01 reported, not fixed**: the `dcfmid` tile is
undeliverable because the frozen `_dcf_tests` check `mid_year_convention_raises_the_value` compares the
input set with itself when the input already declares `timing="mid"`. The independent recomputation
(`qa/probe_dcf_midyear.py`) shows the *method* is right to 40 digits (1,750,939.14 end-year,
1,836,400.47 mid-year, ratio 1.048808848â€¦) and only the check is wrong; the fix is inside the frozen core
and needs an owner unfreeze, so it is ledgered BLOCKED with the report attached.

**Left alone deliberately.** The tree also carries the owner-approved B-179/B-180/B-181 implementation
(`src/bp/methods.py`, `orchestrator.py`, `guard.py` and one hunk of `chat.py`) from the core session,
uncommitted. This session committed only its own files; `chat.py` rides along with three lines of the
B-180 wiring, and that is stated in the commit message rather than hidden. `test_pipeline.py::
test_no_method_is_framework_only` still asserts the pre-B-181 behaviour and is the one *new* failure
against session 1's closing set; aligning it belongs with the commit that lands B-181, and the exact
change is written into `qa/QA_DEFECTS.md` (D-FIN-13) rather than made here against uncommitted code.


## 2026-11-02 â€” [core] Owner-approved unfreezes: one unit hook per method, the shelf vocabulary enforces again, an unknown method is refused

**Ask.** "1. what do you need from me? to unfreeze, yes unfreeze it. 2. implement your reco 3. yes
unfreeze. dont do finance yet, its doing some fixing" â€” i.e. approve the three blocked items from
QA session 1 and leave `finance` alone while another session works on it.

**Did.** (1) **B-179** â€” renamed the six duplicated `typing` hooks in `src/bp/methods.py`
(`_risk_metrics_typing`, `_tax_incidence_typing`, `_social_welfare_typing`,
`_social_engagement_typing`, `_schedule_risk_typing`, `_tax_declared_typing`) and re-pointed the
six `Method(...)` constructions, so `risk_metrics`, `tax_incidence` and `social_welfare` stop
answering with another method's units. The edit was applied by `qa/patch_typing_hooks.py`, which
asserts every target line before writing (and is kept as the record), and the file now has zero
duplicate definitions. (2) **B-180** â€” `guard.subject_fit()` enforces the shelf vocabulary again
with `SUBJECT_LABELS`, a named-framework carve-out (`FRAMEWORK_WORDS`) and the computation
boundary re-ordered to run first in `chat.start`, so a journal-entry brief gets the Accounting
message and a marketing brief on the management shelf gets the shelf message.
(3) **B-181** â€” `orchestrator.start` refuses a method name that is neither a frozen method nor a
template, with the reason and a pointer to `/api/methods`; the declared `framework_only` sentinel
still delivers the structure-only paper. Manual `E-acc-051â€¦053`, three trap tests, ledger rows
moved to FIXED, decisions B-179â€¦B-181 recorded, documented count 2627 â†’ 2630.

**Why.** The owner's approval converts three ledgered BLOCKED findings into fixes, and each is a
real wrong answer rather than a tidy-up: a 50-digit decimal labelled "periods", a marketing brief
refused with a sentence about the wrong thing, and a typo'd method name answered with a paper that
looks like an answer. Scope was held to the three decisions: no method, input, check, preset or
number changed, `scripts/econ_shelf.py --check` still reports "frozen fixture: in sync", and the
12 protected API route families are untouched. `finance` was not opened, per the instruction.


**Ask.** "I want to ensure the pipeline works and that it has no bugs. There is no manual for how
each subject should work. Test, debug and fix the pipeline for each subject" â€” accounting first.

**Did.** Wrote `qa/manual/accounting.md`: the manual that did not exist, 51 expectation rows
(`E-acc-001â€¦051`) each traced to `bp.methods.LIBRARY`, the shipped catalogue, the student guide or
the paper rules, plus the traceability matrix and the eight declared gaps. Wrote
`tests/test_subject_accounting_acceptance.py` (50 tests, 119 subtests) so every row is enforced;
`qa/probe_traceability.py` reconciles the two 1:1. Fixed five defects in the product layer:
(1) `chat.py` defined `_capability_lines` and `_declared_inputs_line` twice and the later
`key: value` stubs shadowed both prose formatters, so delivered papers printed 50-digit Decimals and
the internal appendix dict; (2) `_trend_lines` was defined twice and both capability entries captured
the forecast version; (3) `loan_amortization`/`tax_declared` had no formatter and plain ratios used
`_fmt_exact`, so long Decimals reached the page; (4) `chat.start` computed a refusal and then ignored
it, so a journal-entry brief became a PESTEL paper; (5) the `HOME.md` spine and `DECISIONS.md`
register were missing two documents and the drafted B-170.

**Why.** Every one of the five is a defect against a written rule, not a redesign: the paper rules
(`CONDUCTOR_MANUAL.md` Â§8, `VALIDATION_HARNESS.md` V-06/V-07), the non-negotiable "no silent framework
substitution", and the docs' own drift checks. Three findings are **ledgered, not patched**, because
they live inside the frozen core or need an owner decision: `_tax_typing` shadowing `tax_incidence`'s
unit hook (`qa/QA_DEFECTS.md` D-ACC-06), the subject-vocabulary question (D-ACC-07) and an unknown
method name being delivered as a framework-only answer (D-ACC-09). Baseline 2548 tests / 86 failures
/ 13 errors is recorded in `qa/baseline/`; the closing count is in `qa/QA_STATE.md`.


**Ask.** "the guidance to users in picking up stocks is still not there. when create a portfolio button is clicked, it says a name is required and asked to enter a portfolio name but no field is provided."

**Did.** (1) A new product module `bp/product/instruments.py`: a six-step guide (mandate, mix before names, pick from a neutral list, fit check, write the reason, snapshot and grade the decision), the principles and limits that keep it a decision aid, a fixed reference list of 20 widely held long-only US listings (11 funds, 9 companies) with a neutral line and a source link each, and three labelled example books (diversified, balanced, concentrated). Served by the additive read-only route `GET /api/portfolios/instruments` and rendered on the Portfolio landing. (2) The Holdings tab gains a chooser (filter Funds/Single companies, search, **Use** prefills the symbol and focuses shares), the example books (load editable rows into the existing import textarea; nothing saved until Import), and a **Why you hold it** field - the server and the DOCX report already stored and printed `rationale`, the page never collected it. (3) The create-portfolio handler now focuses and scrolls to the name field and names it in the banner; if the form is not on screen it re-renders the landing instead of reporting a name the student cannot type. A headless-browser probe against the live page confirmed the field exists and is visible, the empty click focuses it, the guide renders, the chooser lists 20 rows and 3 sample books, **Use** prefills AAPL, the company filter leaves 9 rows, and the probe portfolio created by the run was deleted afterwards.

**Why.** The owner asked for guidance on choosing stocks and for the system to offer choices and prefill; B-154 forbids engine advice, so the feature is a decision aid with neutral, sourced vocabulary and explicitly labelled examples. The create-name defect is real when the form is not on screen (a stale or interrupted render), so the handler repairs the state rather than showing a dead error.

**Verified.** `tests/test_product_instruments.py` (14 tests: catalogue completeness and sourcing, no advice language, example-book labelling, the guide, the global-copy rule, the read-only route and its 405, and the page contracts for the chooser, the reason field and the create flow). `scripts/ui_smoke.py --url http://127.0.0.1:8000` adds two live checks (the bundle and the page's request for it) and reports 0 failures.

**Open/next.** The example books carry no prices (the student fetches or types them), and the reference list is fixed and US-listed: a broader or region-aware list is a later increment, not a recommendation engine.

---

## 2026-11-02 â€” [design] The logo loses its white card, the favicon comes back, and the mark grows

**Ask.** "fix the logo smart business writer in home page. remove the white background around it. also restore the favicon, its lost. its now at http://127.0.0.1:8021/#/home" â€” then: "increase the size of the logo by 20% and put it a little closer to Smart Business Writer. like move it down a little because it appears far. then commit it" â€” and then, after seeing the result: "it still look off. increase the logo by 10%. the space between smart business writer and the logo should be the same with the space between smart business writer and Your reliable business writing assistant. then commit".

**Did.** (1) **The logo.** The owner's `web/assets/logo.png` is RGB with no alpha channel - the mark was flattened onto solid `#FCFCFC` paper, and the copy that went into the page carried that paper with it. On the Home hero (canvas plus a green wash) the mark therefore sat on a white card. New `scripts/generate_mark.py` cuts the mark out of `logo.png` with a real alpha channel, reusing the same cut `scripts/generate_favicons.py` already uses for the tab icons: the paper *outside* the artwork becomes transparent, the paper *inside* the book stays opaque, so the book still reads as a solid object. `web/assets/mark.png` is rewritten (168x139 RGBA, 45.5% transparent) and re-inlined as the page's four logo copies (topbar brand, Home hero, chat button, and the `MARK` constant); the file on disk is written from the same bytes that go into the page, so the two cannot drift. The resize runs premultiplied, so the edges keep the ink's own colour and leave no pale halo on the dark chat button. (2) **The favicon.** Commit `977c1cc` had pasted a scaffold document (`<!doctype html> ... <!-- Content goes here -->`) in front of the real page. A browser parses that scaffold as the document, so the real `<head>` - and with it the four icon links - was parsed into the body, where no browser reads a favicon from. The scaffold is removed and the page is one document again. (3) **The mark grows and the wordmark sits in the middle of it.** The hero mark is 103px tall (74px under 900px) - 30% larger than the 78px it started at - and it sits 6px lower (`margin-top:6px`). The space above "Smart Business Writer" now equals the space below it: 25px from the mark's ink to the wordmark's caps and 25px from the wordmark's baseline to "Your reliable business writing assistant", measured on the rendered pixels rather than on the boxes (the boxes lie: a line box carries half-leading above and below the glyphs). The owner's own comparison set that number, so `.hero h1`'s margin-top is 8px. Nothing else on the page moved: the topbar mark and the chat button keep their sizes.

**Why.** Both are presentation defects with no computation behind them, so the fix is presentation too: an asset cut with alpha, and a file that is one document instead of two. The logo cut is the owner's own PNG - no new artwork and no invented colours. The favicon needed no new icon: the 16/32/64/apple-touch set was already correct and already inlined; it had simply been pushed out of the head. The size and the gap are the owner's call on their own mark, applied as two numbers in the page's CSS.

**Verified.** Chrome's own parser was asked what it made of each version of the page: **before**, `iconLinksInHead` was **0** (the three icon links were in the body, `iconLinksAnywhere` 3); **after**, `iconLinksInHead` is **3** plus the apple-touch icon. The browser made no `/favicon.ico` request after the fix (the server 404s that path, and a browser with a page icon does not ask for it). Headless Chrome at 1280x900 shows the hero mark on the wash with no card, the topbar mark with no card, the chat button as a navy circle with the mark on its round plate, and - after the resize - the larger mark sitting close above the wordmark. The two hero gaps were measured on the rendered pixels before and after: 23px above and 25px below the wordmark before, **25px and 25px** after. The served page loads with no console error or warning. New `tests/test_web_brand_assets.py` (5 tests) reads the page and the PNG bytes with the standard library only (no imaging package in the test path): one document, the icon links in the head, the logo's corner transparent and its artwork still present, `mark.png` byte-identical to the inline copy, and no opaque corner in any favicon. The full suite is unchanged in outcome.

**Open/next.** The open request in `web/DESIGN_NOTES.md` for a `GET /assets/<path>` route stands, so the assets stay inlined as data URIs; `web/assets/mark.png` is the asset of record for the mark and `web/assets/favicon-*.png` for the icons. The chat button's round plate is now drawn by the CSS (`background:var(--canvas)`) with the mark on it, which is what the CSS always intended.

---

## 2026-11-02 â€” [design] The market-data panels are split by consumer, and the product stops naming a home market

**Ask.** "make it a rule to delete or remove and never mention any PSE names or reference to philippines. this is a global product." Then: "no, i want you to do the split" â€” do the retrieved market-data split now, while a separate accounting debug runs in another session. Accounting files were not touched.

**Did.** (1) Retired the single `marketPanel()` on the Finance shelf and split it into three panels by consumer: `ratesPanel()` (FX and Treasury risk-free, keyless â€” it feeds `fx_parity`, the CAPM risk-free rate and a currency conversion) stays on **Finance**; `securitiesPanel()` (equity quote, SEC fundamentals, SEC filings) renders in the **Portfolio Lab**'s prices view, beside the existing fetch route that reads the same module; `macroPanel()` (World Bank indicators) moves to **Economics**. Each panel has its own result region (`ratesout`, `secout`, `macroout`) and its own binding; `bindMarketPanel()` and `marketout` are gone. The never-auto-fill boundary is unchanged: value, source, as-of date, response SHA-256, and the student confirms before typing. (2) **Global product rule.** Removed the last PSE references (served page, `marketdata.py` docstring and status note, finance guide), changed the FX example from USD/PHP to USD/EUR, the macro example from PH to US, the coffee-shop brief example from a named city to a mid-sized city, and the synthetic worksheet example prices from pesos to dollars. (3) Recorded the rule as B-177 and in `CONTRIBUTORS.md` Â§1.

**Why.** The panel predates the Portfolio Lab by a day: it holds every lookup on one shelf that can use two of them, and the book workspace holds none of the securities tools it needs. The global rule is the owner's product-identity decision â€” a global product must not present one exchange or one currency as the default, and the retrieved data is already labelled, so moving the panels changes no guarantee.

**Verified.** `tests/test_market_panels.py` (9 tests: placement, per-panel regions and handlers, never-auto-fill copy, no home-market name in page/guide/limits); `tests/test_product_marketdata.py` (28, PH fixture migrated to a neutral country); the touched suites `test_business_plan_profile`, `test_product_explain`, `test_worksheet_export`, `test_sources`, `test_product_subjects` (147 tests) all green; `node --check` on the served page's inline script is clean. No preset, method, schema, check or frozen-contract entry changed; the example-currency label (`PHP`) is left for a dedicated increment.

**Open/next.** The `PHP` example currency across presets, guides and tests; the historical CHANGELOG/WORKLOG/DECISIONS entries that name the old home market are appended-to, never rewritten (repo rule), so they still contain it.

---

## 2026-11-02 â€” [design] Subject-by-subject paper validation: the harness design, and the rules that may be relaxed

**Ask.** "The pipeline has too many features and very laborious for 1 person to validate. Investigate and propose a
method or system on how I can automate the validation. What I require is that to have a complete paper for each
feature where I will not manually test them feature by feature but rather subject by subject." Then, after the
investigation: "Write them first in a handoff document named as you proposed so that future models can see them and
this is easily discoverable. Make this a living document also allowing future improvement to the method, especially on
relaxing some rules â€” some rules are counterproductive. Also, the model that should do this is OpenCode or
OpenRouter, not the DeepSeek direct API, to save on cost."

**Did.** Measured the surface: **364 distinct validation targets** (76 framework papers, 126 capability papers, 9
conductor frameworks, 5 paper profiles, 148 compute-tool deliverables). Found that the production side already exists â€”
`documents/` holds **1,781 generated `.docx` papers** from the test suite's own runs, but `paper_store.py:84` caps its
index at 200 rows, so most of them have no durable record, nothing groups them by subject and nothing judges them.
Proved both paper paths run unattended and in memory: Kano produced a 22,105-byte `.docx`; the conductor produced an
18,784-byte PESTEL+NPV paper with the export gate returning `missing: []`. Found that **125 of 126 capabilities are
already seedable from the existing `PRESETS`**, so no inputs need hand-writing. Found the blocker for "subject by
subject": there is no single subject taxonomy â€” the subject pages use 11 names, the framework profiles use 7 (with
`pestel` and `five_forces` carrying none), and the `subject` key is **empty for all 126 capabilities and all 158
catalogue records**. Wrote [`VALIDATION_HARNESS.md`](VALIDATION_HARNESS.md) as a living document: the
three-layer architecture, a **20-rule registry** seeded from `CONDUCTOR_MANUAL.md` Â§4/Â§8 with each rule's status and
its backing code, the **procedure for relaxing a counterproductive rule**, the subject crosswalk with its proposed
defaults, the evidence-fixture plan, the output contract and the build order. Recorded the owner's model instruction
and its consequence: OpenRouter is reachable today through the existing OpenAI-compatible provider with no code
change, OpenCode is an agent harness rather than a provider, and **the harness needs no model at all** because the
judgement layer is pure code over the deterministic Draft path.

**Why it is built this way.** Three layers â€” produce, judge, roll up â€” because the owner's unit of review is the
subject, not the feature: 31 of the 55 worksheets sit on two subject pages, so one paper serves both shelves. The
judgement layer reuses the product's own functions (`paper.check`, `completion.missing`, `chat._recompute_guard`,
`verify.overclaims`) so the harness cannot drift from the product's behaviour. The relaxation procedure is built on
one principle â€” **relax the alarm, never the guarantee**: the harness's verdict is a report and downgrading a rule
changes what the owner is shown, while the product's export gate stays untouched; a change to what the product asserts
would be a computation-lane change and must be requested, not made here. The crosswalk lives in the harness's own
`subject_map.json` rather than in `src/bp/product/capabilities.py`, so the whole proposal stays in the design lane
(B-080) and touches no frozen module and no test.

**State.** Nothing is built. The document is a proposal with its open questions listed in Â§12. Two findings are
recorded for the owner rather than acted on: **22 of the 76 framework profiles are not reachable from any subject
page**, and 12 profiles have a worksheet that is not marked `draftable`. The test baseline at the time of writing was
**2553 tests â†’ 84 failures + 12 errors**, the framework-completion slice being 566 tests â†’ 55 failures + 7 errors;
the dominant failure classes are already the paper rules the registry names (V-12 in ~11 frameworks, the prompt
contract in ~13, the heading contract in ~5). No source file, frozen module, test or product document was changed.

---

## 2026-11-02 â€” [product] The People & organisation shelf: ten frameworks that said "no worksheet yet" now complete

**Ask.** The People & organisation shelf listed ten change-and-organisation frameworks as read-only records and
offered a student nothing to complete on them. Diagnose the gap, then make the ten into worksheets of the same
kind the shelf already had.

**Did.** The cause was a **stale committed catalogue slice**: `registry.TEMPLATE_LINKS` had already gained the
ten links, so the engine could run every one of them, but `subjects.CATALOGUE` had been generated before that
and still said `read_only` with no template - so the shelf, which is built from the catalogue, could not offer
them. The catalogue rows for the ten now say `worksheet` and name their template; the People shelf lists them
as worksheets and places each in the tile its catalogue record already had; the Management & strategy shelf
lists them alongside the three change frameworks it already offered. Each of the ten gained a drafting schema
and a profile to the People-shelf standard (subject `people`, unit `process`, researched parts, an
interpretive note per part, an outline). Theory of Change and the Logic Model gained the **impact** part they
were missing, and the chain of change gained **assumptions**. The eight frameworks the shelf already had
gained worked examples, so every worksheet on the shelf runs and passes its own checks. The ten broken
per-framework test modules were rewritten to the shelf's standard.

**Why it is built this way.** The catalogue slice is generated data, so the fix was to regenerate it and
correct the drift, not to hand-edit a shelf. Two things were left deliberately alone: the nineteen
marketing and strategy rows whose templates have no drafting schema yet (offering them would put a button on
a shelf that can only 422), and the corrupt registry slice, which was restored to the deterministic import of
its authority catalogue because a double-encoded name is a defect and not a preference.

**State.** The People shelf test module covers all eighteen frameworks and passes (39 tests). The ten
per-framework modules pass (120 tests). Against a baseline worktree holding the state before this work, the
full suite went from **195 failures and errors to 103**, with **no new failure**; the 19 catalogue rows named
above are the one remaining disagreement between the slice and the registry, and they are recorded as an open
issue rather than papered over. The frozen core was not touched, no number was invented and no test was
weakened.

## 2026-11-01 â€” [design] Matrix figures: a grid framework reaches the paper as a grid (B-176)

**Ask.** Eight matrix and canvas frameworks reached the Word paper as four or nine headings in a row, so a
SWOT that should read as a two-by-two arrived as prose. The owner asked for the framework's own shape in the
paper, drawn by the product, with no invented content in it.

**Did.** New `src/bp/product/matrix.py` (a layout registry and a builder) and `src/bp/product/proposals.py`
(the chat's cell proposals). Changed `paper.py` (a figure slot on a section, and `figure_text()` so the
template-text gate sees the figure), `docx.py` (the Word table renderer, figure numbering and the column
arithmetic), `completion.py` (the worksheet figure and the question mode of `_suggest`), `chat.py` (the chat
figure and `accept_assist`), `api.py` (`POST /api/cases/chat/{id}/assist`) and `web/index.html` (the
proposal affordance). `scripts/build_conductor_samples.py` regenerated the Ansoff, Value Chain and VRIO
samples, which now carry their figures.

**Why it is built this way.** The geometry is data, so a new framework never means editing the renderer -
the same rule the writer and the renderer already live under. The builder writes no content: a cell carries
the student's own words, a source's title with its citation, or the named gap and the probe. A question the
model proposes is recorded as a proposal and folded into the gap, not added as an item, so a paper never
presents a question as a case assumption. A proposal carrying a number, a name or a link the student did not
write is refused.

**State.** 4 new test modules (62 tests) pass; the full suite matches the recorded baseline with no new
failure. The frozen core was not touched, no number was invented and no test was weakened.

## 2026-10-31 â€” [code] Proprietary corpus wired as pipeline layer 1 (B-172)

**Ask.** Wire the corpus database (5 documents, 96 pages, indexed in Meilisearch on :7700) into the
pipeline's retrieval engine so corpus pages can be cited as evidence, fixing the five traps that silently
discarded corpus results.

**Did.** Changes in `bp/product/sources.py` and `bp/product/retrieval.py`:
1. `_corpus()` adapter added â€” reads Meilisearch over stdlib `urllib`, fails open when down, returns
   page items with `corpus_key`, `database: "Proprietary corpus"`, `kind: "proprietary"`. Registered in
   `ADAPTERS`; `corpus` entry added to `DATABASES` (access: local).
2. Trap 1 â€” title gate no longer applies to full-text sources; one cue hit in the quoted passage is
   enough, title never sufficient alone (D-10 / B-168).
3. Trap 2 â€” dedup key prefers `corpus_key`; two pages of one book no longer collapse (Q-02).
4. Trap 3 â€” corpus items score source weight 2, equal to OpenAlex/DOAJ/Crossref (Q-03).
5. Trap 4 â€” `_credibility()` never overwritten when the adapter set a score; corpus branch added.
6. Trap 5 â€” corpus searched separately and prepended first in `retrieve()` (layer 1 before layer 2).

**Verified.** All 26 tests in `tests/test_sources.py` pass (6 new corpus tests). Live run against the
seeded corpus: corpus items reach the `items` list first; abstract-only results unchanged. No method,
preset, input, check or frozen-core entry changed.

**Files.** `src/bp/product/sources.py`, `src/bp/product/retrieval.py`, `tests/test_sources.py`,
`docs/DECISIONS.md` (B-172), `docs/CHANGELOG.md`, `docs/WORKLOG.md

## 2026-10-31 â€” [code] Corpus learning hook + student-upload path (B-173)

**Ask.** Add the learning hook so the corpus learns what searches it could not answer, and build the
student-upload path with owner-mediated approval before a student upload can be cited (D-18, D-19,
D-22, D-23, Q-19).

**Did.** Changes across `src/bp/product/retrieval.py`, `corpus-db/build/corpus_lib.py`,
`corpus-db/build/schema.sql`, `corpus-db/build/corpus_service.py`:

1. **Learning hook.** `retrieve()` POSTs each retrieval to `POST /api/corpus/log` on the corpus admin
   service (fail-soft, 1-second timeout). The learning log is a signal, not evidence: a failure there
   never breaks a paper run. The pipeline never imports `corpus_lib` across the repo boundary.

2. **Student-upload path.** `ingest_pdf()` gains `added_by` (`owner` | `student` | `harvest`). Student
   uploads (`added_by = 'student'`) are ingested as private with `enrichen_at` and
   `owner_approved_at` NULL â€” not citable until the owner approves them in the admin UI.
   `corpus_service.py` gains `POST /api/corpus/upload/student`, `POST /api/corpus/documents/approve`
   and `GET /api/corpus/documents/pending`. `index_pages()` only indexes documents with
   `enrichen_at IS NOT NULL`, so unapproved uploads never reach the search index. `documents` gains
   `added_by`, `enrichen_at`, `owner_approved_at` columns (schema.sql + migration). Student uploads
   carry `licence = NULL` and `licence_verified = 0` by default; the owner's approval is the copyright
   check (Q-19).

**Verified.** 26/26 tests in `tests/test_sources.py` pass. 55/55 corpus build tests pass. No method,
preset, input, check or frozen-core entry changed.

**Files.** `src/bp/product/retrieval.py`, `corpus-db/build/corpus_lib.py`,
`corpus-db/build/schema.sql`, `corpus-db/build/corpus_service.py`, `docs/DECISIONS.md` (B-173),
`docs/CHANGELOG.md`, `docs/WORKLOG.md`.`.



# Worklog â€” append-only record of what was done

## 2026-11-01 â€” [code] Corpus seed: 20 documents across 10 subjects (B-175)

**Ask.** Seed ~20 real documents from `D:\SMART BUSINESSWRITER\DATABASE` into the corpus database, per DATABASE.md step 11: "2 subjects deep, â‰¥1 scanned book, â‰¥1 born-digital."

**Did.** Ingested 20 documents (15 books + 5 journal-articles) covering 10 subjects: accounting, economics, finance, management, marketing, operations, people, research, entrepreneurship, supply-chain.
- 9 OCR'd/scanned (OpenStax Principles of Accounting Vol 1: 973 pages; Principles of Economics: 948; Principles of Finance: 629; Principles of Marketing: 707; Principles of Management: 605; Human Resource Management: 532; Introduction to Business: 663; Introduction to Logistics: 159; Penerapan Porter Five Forces: 20)
- 11 born-digital text layer (Operations and SCM: 186; Fundamentals of HRM: 229; Exploring Business: 940; plus 5 original journal articles)
- Licences recorded where known (CC BY, CC BY-NC-SA); unknown licences NULL per C-05.
- Duplicate protection enforced: re-ingesting any file is refused before anything is written.

**Verified.** DATABASE.md step 11 acceptance met: 20 documents, 10 subjects (â‰¥2 deep), â‰¥1 scanned book, â‰¥1 born-digital. `corpus-db/build/test_corpus_build.py`: 55 tests pass. `tests/test_sources.py`: 28/28 pass (1 pre-existing flaky test_brave test passes in isolation).

**Files.** `docs/DECISIONS.md` (B-175), `docs/CHANGELOG.md`, `docs/WORKLOG.md`. The corpus database and PDFs are gitignored data files.



## 2026-11-01 â€” [code] Q-16 per-document page cap (B-174)

**Ask.** Prevent one corpus document from supplying every dimension of a paper (Q-16). Step 11 of DATABASE.md explicitly requires the cap: "Two different pages of the same book can each fill a dimension (subject to the Q-16 cap)."

**Did.** Changes across `src/bp/product/retrieval.py`, `src/bp/product/sources.py`, `src/bp/product/completion.py`, `src/bp/product/chat.py`:

1. **Per-document page cap.** `retrieve()` gains `corpus_doc_cap` (default 3) and `corpus_doc_counts` (shared dict threaded across dimensions). When accepting a corpus item, the cap is checked against `corpus_doc_counts[doc_id]`; at the cap, additional pages from the same document are dropped and counted in `dropped`. Live academic and web sources are not capped.

2. **`doc_id` on corpus items.** `sources._corpus()` now sets `doc_id` on each corpus item so the cap can be keyed per document.

3. **Shared counter per paper.** Both `completion.complete()` and `chat.py` create one `corpus_doc_counts = {}` per paper and pass it to every dimension's retrieval, so the cap holds per-paper, not per-call.

**Verified.** 28/28 tests in `tests/test_sources.py` pass (2 new Q-16 cap tests). 55/55 corpus build tests pass. Live verification: dimension 1 gets 2 pages from one doc (cap=2), dimension 2 gets 0 pages from that doc (cap exhausted). No method, preset, input, check or frozen-core entry changed.

**Files.** `src/bp/product/retrieval.py`, `src/bp/product/sources.py`, `src/bp/product/completion.py`, `src/bp/product/chat.py`, `tests/test_sources.py`, `docs/DECISIONS.md` (B-174), `docs/CHANGELOG.md`, `docs/WORKLOG.md`.



## 2026-10-30 â€” [design] The evidence rules relaxed, and the orientation set made free and topical

**Ask.** "we ahve to relax these rules becus ethey will suffocate the pipeline: The corpus must obey the pipeline's non-negotiables (CONDUCTOR_MANUAL.md Â§4): No invented evidence â€” every claim traces to a recorded source. Gaps are named, never filled â€” a missing page number is NULL, never guessed. No silent framework substitution. update teh manual with what we are discusing. you were told not to do fixes because that might mess up the system. on this: the HBR, expand it to include other sources similar to HBR depending on topic. HBR cannot cover everything. or propose alternative to hbr that is free and fast. on page numbers, its apa and harvard, no need to mention chapter or page number unless customers ask or if its needed whcih pipeline decides."

**Did.** Four rules landed in `CONDUCTOR_MANUAL.md` and are recorded as B-169. Documentation only â€” no code, no behaviour, no number and no frozen-core entry changed.

1. **"No invented evidence" is now "no unsourced claim."** A claim may be quoted or paraphrased from its source, as long as the paraphrase does not exceed what the source says. What stays forbidden is a claim with no source behind it, or a source that says something else. **This is not a new capability.** Â§6.2.8 already has the model-assisted full paper write one call per dimension from the items, and the validator already refuses a number, citation, link or mid-sentence proper noun that is not in the items. The old Â§2 bullet â€” "never evidence paragraphs" â€” was stricter than the shipped code, so Â§2 now says what the product actually does, and the two are reconciled.
2. **Only a substantive gap is printed.** A dimension with no evidence at all is still named in the paper, because the student must know the paper is thin there. A metadata gap â€” a missing printed page number, a missing edition, an unknown ISBN, an unknown date â€” is recorded as `NULL` and does not appear in the paper; the source is cited as it stands. Nothing is filled by invention and nothing is hidden: every gap is recorded whether or not it is printed. The reference list already behaved this way, rendering a missing year as `n.d.`
3. **A framework may be substituted when the substitution is declared and recorded.** The paper says which framework it applied and why it departed from the one the brief named; PESTEL is never the silent default; a brief naming an unwired framework is still refused unless a declared, recorded substitute fits it. The word "silent" was the operative prohibition, so the record is kept and only the automatic swap is removed.
4. **Citations carry no page or chapter locator by default.** APA 7 and Harvard cite a book as `Author (Year). Title. Publisher.` and an article as `Author (Year). Title. Journal, volume(issue), pages.` â€” an article's page range is its extent, not a locator. A locator is added only when the student asks for one or when the pipeline decides the claim needs one (a quotation, a disputed figure, a passage to check), and that decision is recorded. The page a claim came from is kept in the record either way, so a locator can be produced on request without searching again.

**Also recorded â€” the orientation set is now topic-dependent and free-first.** Harvard Business Review is one candidate rather than the anchor, because most of it is paywalled. The set follows the brief's topic and prefers sources that are free, fast and open: strategy and operations practice (McKinsey Insights, BCG Perspectives, Bain Insights), technology and venture reporting (Sifted, TechCrunch), and open policy and think-tank literature (Brookings, PIIE, CEPR, VoxEU, Bruegel, and the World Bank, IMF, OECD, ECB, BIS and Federal Reserve working-paper series). A marketing brief reads the marketing set, an operations brief the operations set, a macro brief the economics and policy set.

**And the citable full-text corpus turns out to be free as well** â€” this is the useful discovery. OpenAlex now serves full text directly through its content API (`content.openalex.org/works/{id}.pdf`, filterable with `has_content.pdf:true` and CC-BY licences, and it also serves GROBID XML, which gives section structure for free). Alongside it: DOAJ, NBER, SSRN and RePEc working papers, and **OpenStax** â€” peer-reviewed, openly licensed, free-PDF business textbooks covering accounting (volumes 1 and 2), finance, economics, management, marketing, business ethics, business law, entrepreneurship and organisational behaviour, which maps almost exactly onto the pipeline's subject list. The licence is **per title** (CC BY on some, CC BY-NC-SA on others) and must be checked before ingesting. CORE is a further open-access full-text source, but its systematic PDF harvesting needs permission and its commercial terms need checking.

**Recorded.** B-169 records all five changes with the rationale for each, including which are already true of the running product and which are owed in code. Â§13 now states that split explicitly, so no future reader mistakes a declared convention for a shipped behaviour.

**Verified.** Read back in the manual: Â§2 carries the paraphrase permission and the new locator rule; Â§4 carries the three relaxed rules; Â§9 carries the topic-dependent orientation set and the open-access harvest; Â§1's evidence row now names the corpus first; Â§13 carries the not-yet-wired limit and the two-of-four split between what already ships and what is still owed.

**Files.** `docs/CONDUCTOR_MANUAL.md`, `docs/DECISIONS.md` (B-169), `docs/WORKLOG.md`, and `corpus-db/CORPUS_DB.md` outside the pipeline repo.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. Nothing was committed by this increment. Three changes are **owed in code** and are not done here: the declared framework substitution (the refusal path is unchanged), the on-request locator (`writing._in_text()` has no locator field today), and the report line that says the report quotes titles and abstracts â€” which becomes false the moment full text is retrieved. The corpus layer, the orientation pass and the open-access harvest land with the corpus build.

## 2026-10-30 â€” [design] The corpus, the full-text gate, and the orientation pass

**Ask.** "on 1. put it in the manual to discard that rule of throwing away book because of that keyword and title issue. 3. they are mix. the subjects are already in the pipeline, accounting, management, finance, economics, etch, everything about business. speaking about hybrid, ive thought about hybrid sources because not all sources would come from books in business. of course, primary sources are books and better have our own database for faster download. im also thinking including relevant journals to enrich the database up to 10 gb. now, tehre will be instances that pipeline need journal sources, so it has to use api and the research mechanism it already has. it will also research web sources needed. to relax research, im thinking of allowing it to use harvard business review and other reputable sources to run in its background to orient it just like what i did in write smarter. let me know what you think."

**Did.** Three rules were recorded in `CONDUCTOR_MANUAL.md`. Documentation only â€” no code, no behaviour, no number and no frozen-core entry changed.

1. **The source order is now layered (Â§9).** The local corpus is layer 1 and is searched first: the owner's own books and selected journals, held page by page. The live academic APIs (OpenAlex, Semantic Scholar, DOAJ; Crossref for metadata) are layer 2, and the curated web is layer 3. No layer replaces another â€” the corpus is owned, page-exact and instant; the APIs still answer what the corpus does not; the web still supplies what neither can. The corpus layer is marked **not yet wired** in the manual's current limits, with the design record at `corpus-db/CORPUS_DB.md`.
2. **The title rejection is discarded for full-text sources (Â§6.2.3, Â§6.3.3).** The title rule is a rule about *abstract-only* records, where a title and an abstract are all that exist and the title is therefore the only signal of what the source is about. A source that carries its own text â€” a book page, a chapter, a full-text article â€” is no longer rejected for lacking the dimension cue in its title. It is accepted when the cue appears in the **passage that will be quoted**, the context word appears in the text, and the geography rule still holds; one occurrence in the passage is enough, because the passage is the evidence. The title is never sufficient on its own for a full-text source. The abstract-only databases keep the title rule exactly as it is, so the pilot's precision rule is untouched. This is the rule that would otherwise have thrown away every book result without saying so: a book is titled for its subject, not for the sentence on page 143.
3. **The orientation pass (Â§9).** The product may read reputable practice and business-press sources â€” Harvard Business Review and the like â€” before retrieval, to widen the vocabulary and the framing of the brief, in the manner of Write Smarter's researcher. It is recorded as **advisory only**: it never enters the evidence list, never carries a citation, is never quoted, its failure is a notice rather than a gap in the paper, and it may never delay the retrieval pass.

**Recorded.** B-168 records all three, with the rationale for each and the boundary that keeps the orientation pass out of the citation path. The manual points at `corpus-db/CORPUS_DB.md` for the corpus design, and that living record carries the open questions, the data model, the Meilisearch index settings and the build sequence.

**Verified.** Read back in the manual: Â§6.2.3 now carries the full-text rule with the "one occurrence in the passage" clause and the explicit statement that the abstract-only path is unchanged; Â§6.3.3 lists the full-text rule as an alternative declared by source kind; Â§9 carries the three layers with the corpus marked not yet wired and the orientation pass marked advisory only; Â§13 carries the not-yet-wired limit, so no future reader mistakes the manual for a description of the running product.

**Files.** `docs/CONDUCTOR_MANUAL.md`, `docs/DECISIONS.md` (B-168), `docs/WORKLOG.md`, and `corpus-db/CORPUS_DB.md` outside the pipeline repo.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. Nothing in the working tree was committed by this increment. The manual now declares a rule the product does not yet implement: the corpus layer, the full-text gate and the orientation pass all land with the corpus build, and until then the academic and web layers answer alone. The live run that Â§6.3 requires before a gate change is recorded as still owed â€” it is attached to the corpus build, and it is the first open item in the corpus build sequence.

## 2026-10-30 â€” [design] The tile that names a tool now opens that tool

**Ask.** "in management and strategy subject, the section that with computation compare strategic options is not clickable. when i click it, it just loop me on top".

**Did.** The Management & strategy shelf's only computation tile, **Compare strategic options** (`case_decision`), opened nothing and threw the page back to the top. The tile was fine; the routing behind it was not. `createSession()` called `show("new")` **before** the session existed, and `RENDERERS.new` - the renderer added on 2026-10-29 so that a reload cannot land on an empty session page - sends a student who has no session back to the last durable screen. So the click was routed back to the subject page, the re-render of that page replaced the DOM and threw the scroll to the top, and the session that was created a moment later rendered into a panel that was by then hidden. The student saw a dead tile and a jump to the top, and the session was lost with it.

The panel is now **activated** (`activate("new")`) rather than shown while the session is created: the "Creating the session" card stays on screen, and the tool opens where it was asked for. `show("new")` is still used by the worksheet path, where a worksheet exists before the panel is shown and the renderer has something to render. One fix repairs every computation tile on every shelf - Finance's net present value took the same path and was equally dead. **Also fixed on the page the owner reached:** the "Enter the figures" panel told every method that "the engagement is declared once: the period, the chart, the opening balances, the entries and any schedules". That is the management-accounts engagement; it is false for a net-present-value comparison, so the sentence now follows the method (B-167).

**Recorded.** B-166 records the routing rule - *a control on a shelf that names a tool opens that tool*, and a renderer with nothing to show may redirect only on a reload, never in the middle of a student's own click. B-167 records the figures-panel wording rule. Both are presentation and routing: no method, preset, input, check, computed number, endpoint or frozen-core entry changed.

**Verified.** On the served page: Management & strategy â†’ **Compare strategic options** now opens the case editor with the worked example loaded (two facts, two alternatives, the rate and the decision rule), and **Apply figures and calculate** runs it to a result - the worked example's own numbers from the frozen core: NPV USD 2,586.47 for *Expand the shop* against USD 2,136.83 for *Office catering* at 8.00%, the order flipping at a 10.16% discount rate, with the limitations stated. Finance â†’ net present value opens the same way. The inline script parses (`node --check`). `scripts/ui_smoke.py` gains a marker for the routing and reports **0 failures** against the running workbench. The suite runs **2457 tests with 49 failures**; the failure list is a **subset of the list taken without this change** (captured both ways: 55 failures with this increment's files reverted to HEAD, 51 when the increment was first applied, 49 after the concurrent lane landed an edit to `src/bp/templates.py` mid-session). Every one of them is the concurrent framework-completion work - the value chain, TAM, STP, PESTEL and RFM outlines, worksheet form kinds, the operations and people page content, the documented test count and build, and one network-dependent search fallback. **No failure is new.** Two new trap tests pin the routing and the wording.

**Files.** `web/index.html`, `tests/test_product_subjects.py`, `scripts/ui_smoke.py`, `docs/DECISIONS.md` (B-166, B-167), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. For the same reason the documented test count (1847) and build (1.47) are left alone - they are already behind the real suite and the newest changelog entry (1.53), and that drift is the concurrent lane's to close. Two things are recorded here rather than changed, because both belong to the frozen core or to the concurrent lane: the recorded-value panel shows a Python repr for list inputs (`Facts [{'text': ...}]`) because the orchestrator stores every input value as `str(v)`, and the session page shows the same value again in full JSON under "The recorded values, verbatim"; and the exported result is unchanged by any of this.

## 2026-10-29 â€” [design] The Home slogan loses its final period

**Ask.** "REMOVE THE PERIOD AFTER ASSISTANT".

**Did.** One character, in the Home hero: the lead now reads "Your reliable business writing assistant", with no full stop, in both places it lives - the static markup and the `RENDERERS.home` rebuild - so the first paint and the re-render agree. Nothing else moves: the claim stays in the bold 19.8 px lead, the three proofs stay in the italic 15 px line under it with their own full stops, and the line break between them is still what separates them. The effect to look at: the lead now reads as a phrase rather than a finished sentence, with the weight step and the line break carrying the emphasis instead of the punctuation.

**Recorded.** The entry above (same day) says "the slogan is untouched" and cites B-094's clause "the slogan must not be changed" and B-162's clause "the slogan stays". Both were the owner's own guard against unasked-for edits, and the owner has now asked for this edit, so both clauses are revised rather than quietly broken: **B-164** records the change and both earlier rows point at it. The wording of the slogan is otherwise exactly as the owner wrote it.

**Verified.** On the served page the lead reads "Your reliable business writing assistant" with no trailing full stop, in the first paint and in a re-render; the proof line is unchanged. The inline script parses (`node --check`) and the full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 22; section 3's live-copy note), `docs/DECISIONS.md` (B-094 and B-162 status cells, B-164 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 â€” [design] Home drops its subject tagline

**Ask.** "DELETE THIS FROM THE HOME PAGE: BUSINESS | ACCOUNTING | ECONOMICS | FINANCE".

**Did.** The `BUSINESS | ACCOUNTING | ECONOMICS | FINANCE` line is gone from the Home hero. It lived in two places - the static markup and the `RENDERERS.home` rebuild - and both were changed, so the first paint and the re-render agree. The hero now reads logo, wordmark, slogan. The slogan is untouched ("Your reliable business writing assistant." / "Real computation. Real research. Verifiable."), so the other half of B-094 - the slogan must not be changed - still stands. The CSS that only served the line went with it (`.tagline`, `.hero .tagline`, and the narrow-layout `.topbar .tagline`, which had no other user in the page); the hero's own spacing is unchanged, so the block tightens by one line and nothing else moves.

**Recorded.** B-094 pinned that tagline ("exactly as written"). The owner set it and has now reversed it, so B-094 is marked superseded on that line and the reversal is recorded as B-162 rather than made silently.

**Verified.** The tagline text is absent from the served document, from the inline script and from the rendered hero, in the first paint and in a re-render; the slogan is still there, unchanged. The inline script parses (`node --check`) and the full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 20), `docs/DECISIONS.md` (B-094 superseded, B-162 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 â€” [design] The collapsed rail shows its icons in full

**Ask.** "recheck the side rails when they are collapsed. the icons are not fully showing. adjust their width so that icons can still be seen in full even when collapsed".

**Did.** The defect was in the collapsed rail's geometry, not in the icons. The subject list scrolls inside the rail, and a vertical scrollbar takes the scrollport's right edge: with the list scrolling, the scrollport ended at x = 30 instead of x = 40. The icon column is right-packed inside the green strip (design note 10), so every glyph sat at x = 18.5 -> 37.5 - under the scrollbar's column - and was cut at x = 30. The Accounting glyph measured 10 px of ink instead of its own 17 px: the book was cut in half. It was window-height dependent (the list only scrolls when the rail is shorter than the list), which is why a measurement at 1400x900 showed a whole glyph and hid the fault.

The fix is the width the owner asked for: the collapsed rail is now the strip plus a column for the scrollbar. `--rail-sb:16px` and `--rail-w-collapsed:calc(var(--rail-w) + var(--rail-sb))`, applied by `body:not(.rail-open) .rail{width:var(--rail-w-collapsed)}` - 61 px in the wide layout, 60 px in the narrow one (`--rail-w:44px` there). The green strip keeps its own width (`.railaccent` is still `--rail-w`), so the open rail is untouched and the new column is the white one the labels start in; the scrollbar lands there instead of on the icons. `--rail-ic-pad` did not change, so the icons did not move: the glyph is still at 18.5 -> 37.5. The collapsed toggle now hugs the strip (41 px) rather than the whole rail, and its chevron is walked back onto the icon column by hand (`translateX(calc(var(--rail-ic-pad) + var(--rail-ic-w) / 2 - (var(--rail-w) - var(--rail-pad)) / 2))`, 3.5 px), so it still sits over the icons.

**Recorded.** The owner instruction sets a geometry convention - the collapsed rail is the strip plus the scrollbar's column - so it is recorded as B-165.

**Verified.** On the served page (`127.0.0.1:8765`, Chrome, device pixel ratio 1): collapsed with the list scrolling (1400x700) the rail is 61 px, the scrollport is 4 -> 46 and the glyph 18.5 -> 37.5, fully visible - the ink of every glyph is its full width (19 px; the Accounting glyph 17 px, the shape's own width), against 10-11 px before. Collapsed in the narrow layout (760x700): rail 60 px, strip 44 px, scrollport 4 -> 45, glyph unchanged and fully visible. Open (1400x900): unchanged - strip 0 -> 45 px, glyph 18.5 -> 37.5 px, the label column and the "SUBJECTS" heading both at 55 px. `scripts/ui_smoke.py` carries the new rail-geometry markers so the column cannot be silently dropped, and passes against the served page. The full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 17), `scripts/ui_smoke.py`, `docs/DECISIONS.md` (B-165 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 - Pricing wired to PayPal, with the credits left open

**Ask.** Wire Smart BusinessWriter's pricing to PayPal at Starter $14.99, Pro $29.99, Studio $49.99 and a fourth tier at $99.99, with an annual plan cheaper than monthly, make a payment actually go through, and build the design so credit allowances can be added later â€” the owner does not know them yet.

**Did.** `bp/product/billing.py` is the one catalogue: monthly prices are written, the annual price is 12 months less a declared 20% (`143.90 / 287.90 / 479.90 / 959.90`), and every tier's `credits` is `None` so the API returns `null` and the page prints "to be confirmed" instead of inventing a number. The fourth tier is **Agency**, chosen so Starter / Pro / Studio / Agency read as one ladder of work-scale nouns. `bp/product/paypal.py` talks to PayPal with the standard library only: token, product and plan creation cached against a hash of the prices, subscription create, read-back and cancel. Routes `GET /api/billing/plans|config|status` and `POST /api/billing/subscribe|confirm|cancel`; `confirm` verifies against PayPal and refuses anything not ACTIVE, and the ledger is append-only and idempotent per subscription id. Pricing is a centred dialog inside `web/index.html`, opened by the Pricing pill, rendered from the API with no browser arithmetic; there is no separate pricing page, so the checkout exists once. `account.html` shows the real tiers and points at the dialog, and its illustrative-tier copy is corrected.

**Verified.** `tests/test_product_billing.py` (33 tests) covers the catalogue arithmetic, the annual discount, credits staying `null`, the fail-closed 503 naming the variable, the config never returning the secret, activation idempotency, the cancel keeping the paid plan, the plan cache being reused and invalidated on a price change, and a refusal surfacing rather than being swallowed. Full suite 1846 tests pass. Live, against the owner's credentials in `Backend/.env`: PayPal issued a real access token (97 characters, value never printed), the product and two plans were created for real (`PROD-5DW44156Y8351981T`, Starter monthly `P-3JX15996X3823631BNLRI7FA`, Starter annual `P-4JM98145VU694664VNLRI7FI`), and the live JS SDK rendered its buttons on `http://127.0.0.1` - so the HTTPS worry recorded in the changelog did not materialise on localhost. What remains unverified is an approved payment: no subscription was approved and nothing was charged.

**Files.** `src/bp/product/billing.py`, `src/bp/product/paypal.py`, `src/bp/product/api.py`, `src/bp/product/source_env.py`, `src/bp/server.py`, `web/index.html`, `web/account.html`, `Backend/.env.example`, `tests/test_product_billing.py`, `docs/*`.

## 2026-10-29 - Aligned Portfolio forms and a generated sample report

**Ask.** The create form paired a label with the next field's input; and a sample report with the fixed checks.

**Did.** Every Portfolio label and input is wrapped in a `fieldgroup`, so the grid places whole fields; the create form is two columns above 720 px. `scripts/build_portfolio_sample.py` generates `samples/portfolio-mock-fund-sample.docx` from simulated prices: three weekly snapshots, a contribution, a benchmark, a decision journal, a time-weighted return and "All 12 checks passed" in plain language.

**Verified.** `node --check` clean; the sample was unzipped and checked for its sections and for the absence of machine check names; the full suite 1780 tests green.

**Files.** `web/index.html`, `scripts/build_portfolio_sample.py`, `samples/portfolio-mock-fund-sample.docx`, `docs/SAMPLE_PAPERS.md`.

## 2026-10-29 - Local key file and the live QVeris contract

**Ask.** The owner supplied Alpha, Massive and QVeris keys and does not want to re-export them each session.

**Did.** `bp.server._load_local_keys` reads the gitignored `state/market_keys.json` at startup and sets only absent `BP_*` variables. QVeris is configured against Finnhub's quote capability (`result.data.c`, 1 credit) and its epoch `t` is converted to a UTC date. Verified live: Alpha 343.83 (2026-10-28), Massive 347.1 (2026-10-27), QVeris 343.83 (2026-10-28).

**Verified.** A loader test asserts a file value is set, an existing environment value wins, and a missing file is ignored. Full suite 1717 tests green.

**Files.** `src/bp/server.py`, `src/bp/product/marketdata.py`, `tests/test_product_marketdata.py`.

## 2026-10-29 - Equity quote fallbacks with internal ceilings

**Ask.** Keep Alpha Vantage primary while starting, then fall back to Massive (5 requests/minute; put the ceiling internally) and QVeris (credits, top-up).

**Did.** `equity_quote` is now a chain: Alpha Vantage, then Massive's previous close, then a declared QVeris capability. Each provider has a key env and an internal ceiling (Alpha 25/day and 5/min, Massive 5/min, QVeris 60/min), all overridable. A missing key skips the provider; a reached ceiling or vendor rate limit skips to the next; the payload records `provider` and `attempts`. `/api/market/status` lists the chain. Keys stay in the query/header and URLs are redacted. QVeris requires `BP_QVERIS_TOOL_ID` and `BP_QVERIS_PRICE_PATH`, so it cannot guess a capability schema.

**Verified.** `tests/test_product_marketdata.py` grows to 26: Alpha primary, Massive fallback after an Alpha rate limit, the internal Massive ceiling producing a named quota error, the no-key message naming every variable, status order, and QVeris staying unconfigured until its contract is declared. Full suite 1716 tests green.

**Files.** `src/bp/product/marketdata.py`, `web/index.html`, `tests/test_product_marketdata.py`.

## 2026-10-29 - Plain-language checks and a quota fallback

**Ask.** "Do we have to show this to users" (the raw check names) and "do we have a fallback if we exceeded the 25 per day limit?"

**Did.** The Word report's Checks section now reads "All 12 checks passed (6 valuation, 6 performance)" with one sentence on what the checks confirm; machine names stay in the stored snapshot, and a failure is named. `marketdata.MarketDataQuota` separates a rate-limit/daily-limit response from a bad symbol; the fetch route returns 429 with `quota: true` when nothing could be stored, keeps a successful subset and names the rest. The UI shows an honesty banner that points to manual entry or paste.

**Verified.** A market-data test asserts the quota subclass; a route test asserts 429 and the manual message; the fund export test asserts "All 12 checks passed" is present and the machine name is absent; the UI guard asserts the fallback banner. Full suite 1710 tests green.

**Files.** `src/bp/product/marketdata.py`, `src/bp/server.py`, `src/bp/product/portfolio_docx.py`, `web/index.html`, `tests/test_product_marketdata.py`, `tests/test_product_portfolios.py`, `tests/test_product_subjects.py`.

## 2026-10-29 - Optional quotes for the Portfolio Lab

**Ask.** The owner supplied an Alpha Vantage key and expected the lab to use it.

**Did.** `POST /api/portfolios/{id}/prices/fetch` reads `BP_ALPHAVANTAGE_KEY` from the server, calls the existing `marketdata.equity_quote` once per holding and stores each price with its real `as_of` and source. A failed symbol is returned in a `failed` list; a date with a snapshot is refused before any call; a missing key is refused with the variable name. `set_price` gained an `as_of` so a Friday close used for a weekend snapshot is not relabelled. The Prices tab gains a fetch button gated on `/api/market/status`, disabled until the key is configured.

**Verified.** `tests/test_product_portfolios.py` grows to 17: a fake source stores AAPL and names MSFT's failure, a missing key is refused, and a saved date is refused before fetching. UI guards assert the button and the status call. Full suite 1708 tests green.

**Files.** `src/bp/server.py`, `src/bp/product/portfolios.py`, `web/index.html`, `tests/test_product_portfolios.py`, `tests/test_product_subjects.py`.

## 2026-10-29 - The Portfolio Lab becomes a mock fund

**Ask.** Complete the Portfolio Lab: the semester mock-fund journal, a return the student can defend, and a report shaped like the assignment.

**Did.** (1) `portfolio_performance` joins the frozen core (T1, category `portfolio`): one row per period with label, start NAV, end NAV and flow, optional benchmark levels; it returns the time-weighted return, total flow, start and final NAV, best and worst period and, when complete, the benchmark and active return. The flow is declared at the start of its period. Six checks; the independent route chains `end / (start + flow)`. (2) `bp.product.portfolios` gains the journal (`journal`, `save_journal`, `remove_journal`) and records an objective, roster and per-holding rationale. (3) Routes `GET .../performance`, `GET/POST .../journal`, `DELETE .../journal/{date}`; the performance payload names a missing benchmark and refuses fewer than two snapshots. (4) Fund creation is enabled; the workspace adds a **Journal and return** tab, and both paste boxes take a CSV/TSV file. (5) The Word report is rubric-shaped: objective, summary, holdings and rationale, performance and conventions, journal, provenance, checks, limits. (6) Preset `portfolioperf`, the finance shelf, calculator group, study notes, synonyms and both slices are updated; the fixture is regenerated at 142 methods and 144 presets.

**Verified.** `tests/test_portfolio_performance.py` (7) covers chaining, flows, benchmark, a loss, the six checks and the refusals. `tests/test_product_portfolios.py` grows to 14, including the journal store, the performance route, a named missing benchmark, the two-snapshot refusal and the fund DOCX content. `tests/test_product_subjects.py` guards the fund UI. Full suite 1705 tests green.

**Files.** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/product/portfolios.py`, `src/bp/product/portfolio_docx.py`, `src/bp/product/subjects.py`, `src/bp/product/calc_router.py`, `src/bp/product/data/*.json`, `web/index.html`, `tests/test_portfolio_performance.py`, `tests/test_product_portfolios.py`, `tests/test_product_subjects.py`, `tests/fixtures/frozen_contract.json`.

## 2026-10-29 - The Portfolio Lab takes a pasted book and a pasted price list

**Ask.** Continue the Portfolio Lab with the import path students actually use: a spreadsheet or a paste, not forty rows by hand.

**Did.** `parse_holdings` and `parse_prices` in `bp.product.portfolios` read comma, tab or semicolon tables with an optional labelled header, cost basis and price source; a duplicate symbol in one paste is refused. `import_holdings` upserts in one write; `import_prices` writes one date in one write, refuses a symbol that is not a holding and refuses a date that already has a snapshot. Validation runs over every row before anything is stored, so one bad row refuses the whole paste with its row number. Two routes (`POST .../holdings/import`, `POST .../prices/import`) and a paste area in the Holdings and Prices tabs; the browser sends text and does no arithmetic.

**Verified.** `tests/test_product_portfolios.py` grows to 10 tests: header and tabbed pastes, the comma/tab paths, all-or-nothing refusal, duplicate refusal, unknown-symbol and saved-date refusal, the two routes feeding a snapshot, and the 422 on a bad paste. Focused suite 64 tests green.

**Files.** `src/bp/product/portfolios.py`, `src/bp/server.py`, `web/index.html`, `tests/test_product_portfolios.py`.

## 2026-10-29 - A Portfolio Lab values a dated portfolio and exports the report

**Ask.** "start with the build. we will do the manual later when its done" - a portfolio workspace, paper mode first, global by default, aligned to what students actually do.

**Did.** (1) New frozen T1 method `portfolio_valuation` in `methods.py`, category `portfolio`, metric `nav`: declared holdings and cash in one base currency produce NAV, invested value, cash, cash share, holding count, top weight, top-three concentration and HHI, plus a `value_<SYM>` / `weight_<SYM>` pair per holding. Six declared checks (float second route, NAV identity, weights plus cash equal one, price linearity, cash unit response, bounded concentration) and refusals for an empty book, a blank or duplicate symbol, non-positive shares or prices and negative cash. Weights are value / NAV, so cash is inside the denominator. (2) `bp.product.portfolios` stores one directory per portfolio with atomic writes, path-traversal refusal and an immutable snapshot per date; a price is refused unless the symbol is already a holding. (3) `bp.server` routes `GET/POST /api/portfolios`, `PATCH/DELETE /api/portfolios/{id}`, `POST/DELETE .../holdings`, `POST .../prices`, `GET .../snapshots`, `POST .../snapshot` and `POST .../export`; the snapshot route accepts the prices and cash in the body, runs the frozen method and refuses on a missing price or a failed check. (4) `bp.product.portfolio_docx` formats the stored snapshot only. (5) The served page gains a fourteenth rail item, **Portfolio**, above the Business Calculator, a landing page, a paper creation form and a three-tab workspace (overview, holdings, prices and snapshot) with a Home entry. No browser arithmetic. (6) Preset `portfolioval`, the finance tool list and calculator group, the study note, the calculator synonyms and both committed slices are updated; the frozen fixture is regenerated at 141 methods and 143 presets.

**Verified.** `tests/test_portfolio_valuation.py` (6) covers the numbers, the declared checks, linearity and the refusals. `tests/test_product_portfolios.py` (4) covers create/add/price/snapshot/export/delete, the unknown-holding price refusal, the full HTTP route path and the missing-price refusal. `tests/test_product_subjects.py` adds the rail and panel presence guard. `node --check` on the served script is clean. Full suite 1670 tests green.

**Files.** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/product/subjects.py`, `src/bp/product/portfolios.py`, `src/bp/product/portfolio_docx.py`, `src/bp/product/calc_router.py`, `src/bp/product/data/*.json`, `web/index.html`, `tests/test_portfolio_valuation.py`, `tests/test_product_portfolios.py`, `tests/test_product_subjects.py`, `tests/fixtures/frozen_contract.json`.

## 2026-10-29 â€” The computation explainer travels with the paper

**Ask.** "when something in the paper has computation, the explainer will automatically accompany it" and "its file name will be title-explainer_format."

**Did.** New product-layer `explain.py` and `explain_html.py`, a committed method-contract slice (`data/explain_contracts_v0_1.json`, regenerated by `scripts/generate_explain_contracts.py`), and a `render_note` renderer in `docx.py`. The explainer is a teachable document, not an audit sheet: question, why this method, the declared formula and steps from the catalogue's study notes, the declared figures, the values the frozen engine recorded (with their derivations), what the result means, the declared checks, common mistakes, the defaults applied, the limits and unsupported uses, an "If your professor asks" Q&A, and a small record appendix. Accounting cases add the recorded journal, T-accounts, trial balance, statements, reconciliation and PASS/FAIL checks.

**Packaging.** A paper with at least one delivered computation now exports as one ZIP containing `<slug>.docx` and `<slug>-explainer.docx`; a paper without a computation keeps the plain Word download. The paper export gate runs first, so an incomplete paper produces no partial ZIP. The same explainer is available alone from `POST /api/cases/{id}/explanation` and `POST /api/cases/chat/{id}/explanation`; the case page, calculator result, chat paper and plan expose the action, and the case page labels the submission download "Word + explainer" when a computation is present. Print-ready HTML is returned where the paper is HTML, so the student can print to PDF without a PDF writer.

**Verified.** `tests/test_product_explain.py` (22 tests): the contract slice matches all 140 core methods; every calculator method has a contract or a declared template; every method without notes is in the declared 10-tool gap set; the explainer imports no core module; the break-even document quotes the recorded inputs/outputs and is a deterministic valid `.docx` with a table; the accounting document contains the journal, T-accounts, trial balance and PASS checks; a paper with five computations produces one companion; a paper without a computation is refused; the ZIP contains exactly the paper and the explainer with hashes; the routes return Word, HTML, 422 for no computation and 409 for a blocked paper. Live on `http://127.0.0.1:8033/`: the calculator run produced case `5dcfb8feaf75`, "Download the explanation" returned 200, the case page labelled the submission "Word + explainer", and the download was `how-many-units-must-we-sell-to-break-even-submission.zip` with two files. No frozen method, preset, input, check, number or frozen-contract entry changed.

**Files.** `src/bp/product/explain.py`, `src/bp/product/explain_html.py`, `src/bp/product/docx.py`, `src/bp/product/api.py`, `src/bp/product/data/explain_contracts_v0_1.json`, `scripts/generate_explain_contracts.py`, `tests/test_product_explain.py`, `web/index.html`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`.

**Open/next.** Ten statistics tools still have no catalogue formula/steps note and are named as gaps; writing those notes removes them from `explain.NOTES_GAPS`. A true server-side PDF still needs a converter or a writer; the HTML path is the current print-to-PDF route.

## 2026-10-28 â€” [design] "My account": the account this product actually has

**Ask.** Take the attached hosted account page as inspiration and build one for Smart BusinessWriter, curated to this product rather than copied where it does not apply.

**Did.** `web/account.html`, served at `/account.html`. The hosted page's identity, subscription, payment history, tag manager and search-engine metadata did not survive the transfer: this product stores no identity, wires no payment system and makes no external network calls, so the page says so on its face rather than shipping an empty form. What did survive is what actually exists here â€” the machine (served build, health, case store and state directories, sandbox and model-assistance flags), the work stored on it, and the export wallet that meters exports.

**Did â€” the wallet became visible.** `src/bp/product/credits.py` already kept an append-only ledger with a derived balance, a price table and a 100-credit free tier, but nothing could read it, so the balance was invisible to the user. `GET /api/cases/credits` returns that module's own receipt unchanged â€” read-only, and it cannot charge anything. `GET /assets/<file>` serves the logo and the tab icons, so the page needs no inlined data URI and no remote asset.

**Verified.** On the served page (127.0.0.1:8766, Chromium) every figure is live: the machine's facts, the eight most recent cases with their methods and dates, the wallet balance and its ledger, the catalogue counts. Every request the page makes returns 200, and `/assets/../server.py` returns 404. The suite passes.

**Files.** `web/account.html` (new), `web/index.html` (the account pill now links to the page), `src/bp/server.py`, `src/bp/product/api.py`, `README.md`, `web/DESIGN_NOTES.md` (section 14), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-28 â€” The sample papers are generated by the product

**Ask.** The owner pointed out that an APA/Harvard formatter already existed, so the samples were not
blocked on writing. Accepted recommendation: reuse the sources already in the repo for Ansoff and Value
Chain, no external sources for VRIO and Break-even, and a short guide. Filenames: title - framework - style.

**Did â€” the builder.** `scripts/build_conductor_samples.py` drives the real conductor for each framework and
style and calls `chat.docx_bytes`, which enforces the export gate and renders `render_academic`. Eight files
in `samples/`: Ansoff, Value Chain, VRIO and Break-even, each in APA 7 and Harvard.
`scripts/sample_evidence.py` freezes nine sources already cited in the Apple-Iran paper, with the claim each
supports and the dimension it backs; nothing was newly retrieved or invented.

**Did â€” two product defects the samples exposed.** The academic renderer wrote `Author: [your name]` and
`Institution: [your institution]` on every title page, which is template text the manual forbids; the byline
is now an optional list and is omitted when empty (the samples pass an honest "Worked example for students").
A paper with no retrieval no longer ends its limitations with "The search may be incomplete" when no search
ran, and the introduction reads "the Middle East" rather than "Middle East".

**Tests.** `tests/test_sample_papers.py` (12 tests): filename convention and sanitisation, the eight builds,
the H1/H2 hierarchy for each framework, References versus Bibliography, body citations resolving to the
reference list, the byline, no template text, the named value-chain gap, the core break-even figures and byte
determinism. `tests/test_conductor_frameworks.py` was also brought back in line with the capability rewrite
that landed during this work, so its attachment tests now assert the current contract.

**Docs.** `docs/SAMPLE_PAPERS.md` records how to rebuild the samples and where the evidence comes from; the
conductor manual, known limitations, handoff and this log are updated.

## 2026-10-28 â€” Four more conductor frameworks, and a computation that travels

**Ask.** After the question "are the backend compute and frameworks done?", the answer was: compute is
broad, but the conductor composed only PESTEL, SWOT, PESTEL + SWOT, Five Forces and Five Forces + Break-even.
The owner chose all three follow-ups: wire the recommended frameworks, allow a framework + computation
generally, and keep the UI with the design lane.

**Did â€” frameworks.** `chat.py` gains Value Chain (nine activities), Ansoff (four options), VRIO (student
resources and four judgments, no external evidence) and Break-even (computation only). Each has a question
bank (`VALUE_QUESTIONS`, `ANSOFF_QUESTIONS`, `VRIO_QUESTIONS`, `BREAKEVEN_QUESTIONS`), search cues for the
evidence dimensions, plan wording (`why`, `misses`, `output`, checkpoints), a draft branch with the H1/H2
hierarchy, a Discussion integration where one applies, and limits that name what the framework cannot do.
Inference recognises the four names, and a break-even or VRIO brief is no longer refused by the subject
guard as "a computation, not a strategy".

**Did â€” computation attachment (Phase B).** `attach_computation(state, "breakeven", values)` validates
`fixed`, `price` and `variable` through the frozen `breakeven` method *before* storing them, refuses a price
below variable cost with the core's own message, and stores the inputs on the state. The draft adds the
Financial Feasibility H1 and Break-even H2 to any evidence framework, plus the integration paragraph, the
limitation and the title suffix. `POST /api/cases/chat/{id}/computation` exposes it. The Five Forces +
Break-even key, label and questions are untouched.

**Did â€” gate.** `paper.missing` now requires a VRIO paper's resources and at least one value judgment, and
names missing break-even inputs on an attached computation.

**Tests.** New `tests/test_conductor_frameworks.py` (20 tests): registration, dimension counts, the refusal
message naming the new options, inference, plan wording, the nine/four/five-section drafts, verbatim student
judgments, a named gap where evidence is empty, the core break-even figures, attachment refusals, the export
gate and the API route. Full suite: 1560 tests pass.

**Not done, and named.** APA and Harvard sample papers for the four frameworks (manual Â§5 item 10); the UI
affordance for the attach endpoint belongs to the design lane, as agreed.

## 2026-10-28 â€” [design] The last unusable Entrepreneurship tile gets its editor, and schema forms get controls

**Ask.** "How about the other features of the entrepreneurship subject? Have we built the UI?"

**Did.** Checked every one of the 46 tiles in Chromium. Forty-five launched a real method; **Compare strategic options (`case_decision`)** did not, because it is a template rather than a frozen method. The generic form looked up `/api/methods`, found nothing, said "This method declares no inputs", and Apply dropped the preset; the engine then refused with "`facts` must be a non-empty list". (1) Added a dedicated **case facts and alternatives editor** to the tool screen: facts with stable `F1..Fn` ids, provenance and source; two to five alternatives with name, description, cash flows from t=0, supported fact ids, cash-flow provenance and source; base rate, range, rate provenance, decision rule and currency; bounded add/remove rows. `collectInputs` reads it, `applyAndRun` posts the normal session and confirm pair, and the delivered result uses the existing result page. (2) The **Business Calculator** now delegates `case_decision` to that editor instead of showing an empty pad. (3) The generic schema form now renders `enum` inputs as dropdowns, `value_list`/`code_list` as comma-separated fields and `value_matrix` as an explicit JSON row editor; records, tables and maps keep their existing editors. (4) Added static page guards for the editor, the calculator delegation and the new input types.

**Verified.** Chromium on the served page: the case tile rendered 2 facts and 2 alternatives with the worked example; Apply delivered USD 2,586.47 for Expand the shop and USD 2,136.83 for Office catering with a 10.16% crossover; add/remove produced 3 facts and 3 alternatives, then 2 alternatives. The proforma tile showed `1200000, 1500000, 1800000` instead of JSON and delivered revenue 4,500,000 and net income 360,000. The depreciation method was a real `SELECT` with `straight_line` selected. The calculator's case tool opened the same editor. No console errors. `node --check` clean; full suite 1540; CI 3/3.

**Files.** `web/index.html`, `scripts/ui_smoke.py`, `tests/test_product_subjects.py`, `docs/CHANGELOG.md`, `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, `WORKLOG.md`.

**Open/next.** The remaining standalone JSON surfaces are records, tables and maps, which already have editors or intentional JSON; no tile is schema-less now.


## 2026-10-28 â€” [computation/product] A business plan is a paper profile, with all its computations

**Ask.** Add a complete business-plan capability: every computation a plan needs, brief upload, customisation, and an entry point from both the Entrepreneurship page (strict convention) and Home (open composition), without inventing a fact, a source or a number.

**Did.** (1) Four T1 methods join the frozen core, each with a float second route and five checks: `sales_from_market`, `depreciation_schedule`, `proforma_statements` and `sensitivity_table`. The projected statements build an income statement, cash flow and balance sheet from declared revenue, margin, costs, depreciation, interest and principal (or an opening loan), tax, working-capital days and opening balances; the opening balance sheet must balance and an unbalanced opening is refused with the equity that would balance it, and a loan repaid faster than it is owed is refused. Presets `depreciation`, `proforma`, `frommarket`, `sensitivity`; README list, calculator slice and frozen fixture regenerated (140 methods, 142 presets, B-148). (2) `bp.product.chat` gains `PROFILE_BUSINESS_PLAN`, `PLAN_SECTIONS`, `PLAN_FIELDS` and `COMPUTATION_BLOCKS`. A plan composes student input, evidence, computation and integration sections; the Financial Plan is one H1 with its blocks as H2s. SHS requires sales from market, break-even, depreciation, projected statements and sensitivity; college adds tax, the cap table and a cost-effectiveness impact ratio. `customise` changes level, composition or (open mode only) an optional section; `set_inputs` stores the student's words; `compute` calls the attached frozen core and stores the declared inputs and result; `draft` composes the plan and never states a figure that is not in a stored result or a supplied input. (3) `paper.missing` is profile-aware: every required field and block is named, a refused block is named with its reason, and the route returns 409 with the list. (4) `documents.extract_docx` reads `word/document.xml` with the standard library; `extract_txt` handles UTF-8, UTF-16 and Windows-1252; `extract_document` dispatches PDF, DOCX, TXT and images; the brief route returns `ocr_required` rather than guessing a scan. Intake now treats `.docx` as a document. (5) The Entrepreneurship page opens the plan in strict mode; Home opens open composition; a new Plan panel renders the proposed structure, a form per block from its declared schema, the evidence review, the draft and the export gate. (6) Entrepreneurship now exposes capacity, inventory, market concentration, ratios and cost-effectiveness on the page, with the nine new tiles grouped. (7) Tests: `tests/test_business_plan_core.py` (20) and `tests/test_business_plan_profile.py` (38), plus the four methods in the sandbox/session cases; `tests/test_business_plan_profile.py` covers the hard refusals, the readers and the routes.

**Verified.** `python scripts/generate_subjects.py` (158 records, 11 subjects, 143 compute tools), `python scripts/econ_shelf.py --fixture` (140 methods, 142 presets), `python scripts/generate_calc_inputs.py` (140 methods), full suite 1536 tests green, `python scripts/ci.py`. In-process plans: SHS draft has 11 H1s and the Financial Plan H2s in order; college adds Funding and Ownership and Social and Environmental Impact; an unbalanced opening balance gives `set opening_equity to 250000` and blocks export; the Word file is produced only when the gate passes. `node --check` on the served script is clean.

**Files.** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/product/chat.py`, `paper.py`, `api.py`, `documents.py`, `intake.py`, `subjects.py`, `src/bp/product/data/calc_inputs_v0_1.json`, `tests/fixtures/frozen_contract.json`, `src/bp/data/registry_v0_2.json`, `web/index.html`, `README.md`, `docs/CONDUCTOR_MANUAL.md`, `HANDOFF.md`, `CHANGELOG.md`, `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `CURRICULUM_MAP.md`, `ENTREPRENEURSHIP_STUDENT_GUIDE.md`, `BACKEND_CONTRACT.md`, `HOME.md`, `WORKLOG.md`, `tests/test_business_plan_core.py`, `test_business_plan_profile.py`, `test_sandbox.py`, `test_session_api.py`, `test_entrepreneurship.py`, `test_product_documents.py`.

**Open/next.** A restricted set of blocks is deliberate: no monthly pro-forma, multi-product mix, disposal, group consolidation or jurisdiction tax law. The plan's market evidence depends on the source finder; a dimension with no match stays a gap. The plan builder currently asks for every declared figure as text; structured period tables would be a presentation increment, not a new computation.

## 2026-10-28 â€” [design] The hero's promise steps up, its proof steps aside

**Ask.** On the Home page, "Your reliable business writing assistant." must be bold and slightly bigger, and "Real computation. Real research. Verifiable." must be italicised and smaller.

**Did.** The slogan paragraph now carries two spans instead of one string and a break. The promise line is 19.8 px at weight 700, up from 18.0 px regular; the proof line is 15.0 px and italic, down from 18.0 px and the size of the page's `.sub` body text. The colour is unchanged, so weight, size and slant carry the hierarchy and nothing else moves. Both copies were changed - the static markup in the served page and the string `RENDERERS.home` rebuilds on every visit - so changing one alone would have reverted the other on the next render.

**Verified.** On the served page (127.0.0.1:8765, Chromium) the Home hero shows the promise line bold at the larger size and the proof line italic at the smaller one, and the rendered DOM carries both spans with their classes.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 13), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the rail increment: the build number is in flight in the concurrent lane - the pill moved twice while this was written - and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-28 â€” [design] The rail keeps the subject marked while you work inside it

**Ask.** "continue your unfinished fix in the left rails" â€” the left rail lost its green highlight the moment a student opened a subsection of a subject, and the previous run ran out of credit before that fix was verified, recorded or committed.

**Did â€” the defect.** The rail marked the panel it was on (`a.dataset.panel === id`), and a subject's workspace is not a panel: no rail item carries `data-panel="new"`, `"results"` or `"deliver"`. Opening a worksheet, a tool, the run it produced or the deliverable therefore cleared `aria-current` from every item, so the subject the student was working in went out of the rail entirely - no green word, and nothing to click their way back to.

**Did â€” the fix.** `state.railSubject` remembers the subject the rail is holding: set when a subject page is opened, kept while the panel is one of that subject's own workspaces (`SUBJECT_WORKSPACE = ["new", "results", "deliver"]`), released by every other panel. The marking moved into one shared `markCurrentRailItem()`, called by `activate()` and by `renderRailSubjects()` after the subject list is rebuilt from the API - a mark applied before that redraw was lost with the old elements. The mark is an attribute on a link, so no behaviour, wording, number, endpoint or test changed.

**Verified.** On the served page (127.0.0.1:8765, Chromium), with a temporary log inside `markCurrentRailItem` recording the active panel, the held subject and the number of marked rail items, every transition was read back: the subject page marks the subject (1 of 14 items); a worksheet opened from it keeps the subject marked (1 of 14, with `aria-current="page"` on that link in the DOM); the Business Calculator releases it and marks the Calculator; returning to the subject marks the subject again; Home releases it and marks Home. The instrumentation was removed afterwards, and `scripts/ui_smoke.py` now carries the rail markers so the fix cannot be dropped silently.

**Suite state.** 1484 pass, 3 fail - all three from the concurrent slice and none from this change: the calculator router knows 136 methods against 140 in the catalogue, the Entrepreneurship shelf text, and the test count documented in `HOME.md`. This entry touches `web/index.html` only.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 12), `scripts/ui_smoke.py`, `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry was written: the build number is in flight in the concurrent lane (the pill is already at v1.24 with no matching entry), and the newest build in the changelog is tied by a test to the build string in `HOME.md` and `HANDOFF.md`, so writing it here would either collide with that increment or edit its lines. The changelog line for this increment belongs with the next build that carries it.

## 2026-10-28 â€” The marketing shelf finishes its assignments

**Ask.** After the RFM and media-planning increment, the owner asked what was still open for a marketing
student and chose all five items: worksheets for the read-only records, customer profitability, market share
and penetration, discounted customer value, and a sandbox guard.

**Did â€” five worksheets.** `template_customer_journey` and `template_servqual` on the declared-matrix
machinery (touchpoints against stages; service dimensions against expectation, perception and your gap), and
`template_kano`, `template_paid_media_plan` and `template_measurement_plan` on the canvas machinery. Every one
inherits the shared builder, renderer, nine- or eight-check audit and refusals: empty blocks and cells are
named, sourced items need a source, unknown blocks and cells that cite unknown rows are refused, and no score,
ranking, average, probability or verdict is produced. The Kano category and the SERVQUAL gap stay the
student's: deriving either inside the worksheet would put judgment or arithmetic in the product layer. Five
worked examples were added to `T.EXAMPLES`, so the sandbox equality test covers them too.

**Did â€” three computations.** `market_share` (share, change from a declared prior period, implied growth,
penetration, relative share), `clv_model` (discounted and undiscounted value over a horizon at constant churn
and discount, value per unit of acquisition cost, undiscounted payback only when it is reached) and
`customer_profitability` (profit, margin, profit share by segment, profitable counts, concentration count).
Each has a float second route, five frozen checks, refusals and a token-only report.

**Did â€” truth.** `QNT-MKT-07` now links to `customer_profitability`; `QNT-MKT-02` gains `market_share` and
`QNT-MKT-03` gains `clv_model`; the five worksheet records leave the read-only list. The page is 24 tiles,
6 worksheets and a 48-term glossary; no marketing record says "not built". Three presets: `marketshare`,
`clv`, `custprofit`.

**Two presentation bugs the smoke tests caught.** A payback period was formatted as currency ("PHP 7.00
periods") and two templates read badly for a count of one ("1 are not", "1 segments"); both were fixed at
source rather than in the guide.

**Tests.** `tests/test_marketing_worksheets.py` (14 tests): registration, every example passing its own named
checks, verbatim listing, gap counts, no score in the analysis, pipeline delivery and five refusal cases.
`tests/test_marketing_additions.py` gains six golden tests, sixteen refusals and the new link guards; the
session API sample inputs cover the three methods. Full suite: 1410 tests pass. Frozen fixture regenerated
(127 methods, 129 presets) under B-133.

**Deliberately not built, unchanged:** platform connectors, automated bidding, incrementality beyond a
designed A/B test, data-driven attribution, sequential tests and budget recommendations.

## 2026-10-28 â€” The Business Calculator: the main-line shell and sentence router, harmonized with this line

**Ask.** "check the calculator or business calculator, its in the main git. cline worked on it but ran out of credit. finish the job" and "harmonize it with the local file also so i can see how it works."

**Did.** Ported the main-line Business Calculator (main builds 0.74-0.76) onto `design/v0.73-rail`, where the served page had kept the older launcher. `web/index.html` gains the P1-P3 shell from `docs/proposals/BUSINESS_CALCULATOR_DESIGN.md`: tool selection stays in the panel, a display names the method and its declared inputs, a 16-key pad edits the focused field (operator keys move focus, they never evaluate), fit badges separate keypad tools from list/table tools and worksheets, and `=` posts the normal `POST /api/sessions` -> `POST /api/sessions/{id}/confirm` pair. A delivered run is recorded automatically through `recordCalcCase`, and a recording failure is reported. The panel's search is now global rather than group-only. An **Ask instead** toggle posts the sentence to the new `bp.product.calc_router` through `POST /api/cases/calculator/plan` and renders one of five declared outcomes. The router imports no core module and reads `src/bp/product/data/calc_inputs_v0_1.json`, regenerated from all **127 frozen methods** by the new `scripts/generate_calc_inputs.py`.

**Harmonization, not a copy.** The first build's vocabulary knew 36 methods; this line has 127. `SYNONYMS`, `CLUES` and `INPUT_WORDS` now cover the local shelves (tax, RFM, media planning, line balancing, marketing analytics, the economics models). Three defects the local catalogue exposed are fixed: schema inputs marked `required: false` are no longer reported as missing; a thousands separator is punctuation, so `84,000` becomes `84000` (same value) instead of the old `84`; and a `records`/`rows` input is never filled from a bare number, so "RFM segmentation for 20 customers" asks for the customer records instead of sending `[20]` as the list. `tax_declared` exists here, so VAT/income tax now routes to it rather than being refused as unsupported. Every reader-facing label says **Business Calculator**; the route, panel id and JS identifiers stay `calculator`.

**Verified.** `python -m pytest -q tests/test_product_calc_router.py` passes 18 tests, including the golden table, the "every figure is quoted" guard, the input-slice drift guard and a live `SessionManager` run for every `run` golden. Live on `http://127.0.0.1:8030/`: break-even opened in place, the keypad edited a field, `=` delivered and recorded case `e0cb4e2d32f4`; the tax preset delivered and recorded `b62cbdfd4789`; descriptive statistics ran with the keypad off; Ask parsed "break-even with 1500 fixed cost, price 25, variable 10" into the break-even plan; global search for "tax" returned 7 calculations across groups; the page produced no console errors and no browser arithmetic (`eval`, `Function`, `parseFloat`, `parseInt` absent). No frozen method, preset, input schema, computed number or frozen-contract entry changed.

**Files.** `web/index.html`, `src/bp/product/calc_router.py`, `src/bp/product/data/calc_inputs_v0_1.json`, `src/bp/product/api.py`, `src/bp/product/subjects.py` (note wording), `scripts/generate_calc_inputs.py`, `tests/test_product_calc_router.py`, `tests/test_product_subjects.py`, `docs/proposals/BUSINESS_CALCULATOR_DESIGN.md`, `mockup/business-calculator.html`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `SERVING.md`.

**Open/next.** Free-form arithmetic (decision D1) is still refused: `2 + 2` is out of scope and `=` runs a declared method, never an expression. The `calc_inputs` slice must be regenerated whenever a method's input schema changes; the drift test fails until it is.

## 2026-10-28 â€” The favicon loses its white card: true alpha from the logo, verified in a real tab

**Ask.** "continue this fix about the favicon" â€” locate the favicon sources, confirm the white-background defect, cut the book-and-bar mark out of `logo.png` with true alpha, render 16/32/64px tab icons and a 180px apple-touch icon on a transparent background, inline them into `web/index.html`, and verify in a real browser tab.

**Did â€” the defect, confirmed.** `web/assets/logo.png` is RGB (1284x1032, no alpha): the owner's PNG flattened onto solid `#FCFCFC` paper. The pre-fix inline icons (commit `a826fcf`) carried that paper with them. 25% of the 16px tile, 36% of the 32px, 41% of the 64px and 78% of the 180px were opaque white, and the apple-touch-icon was alpha 255 edge to edge â€” a solid white square. The tab icon therefore showed a white card around the mark.

**Did â€” the rebuild.** `scripts/generate_favicons.py` cuts the mark from the logo's book-and-bars block; the `Smart BusinessWriter` wordmark is deliberately left out, because a favicon must not carry it. Every pixel's coverage is keyed against the paper, and the gaps between the book's page strokes are sealed so the paper between them reads as the book's interior. The paper *outside* the artwork becomes transparent; the book's own pages stay opaque, so the book still reads as a solid object on a dark tab. Four PNGs â€” 16, 32, 64, 180 â€” are written to `web/assets/favicon-*.png` and inlined into `web/index.html` as data URIs, because the server serves only `/` and `/api/*` (`web/DESIGN_NOTES.md` open request 1). The script now writes each asset file from the same encoded bytes it inlines, so the committed PNGs are byte-for-byte the icons the page serves and cannot drift apart by a few bytes of PNG encoding; the four files are pixel-identical to the ones shipped in `8c686a6` and differ only in encoding.

**Verified.** The four inline data URIs decode byte-for-byte equal to `web/assets/favicon-*.png`; every icon has alpha 0..255 with all four corners fully transparent; the residual opaque white (0%/2%/2%/3%) is the book's own pages, not a card. In a real Chromium tab on `http://127.0.0.1:8765/` the page loads with no console errors and **no `/favicon.ico` request** â€” the browser accepting the inlined icons instead of falling back to the default path. A before/after harness renders the pre-fix and current icon sets over a simulated dark tab strip in Chromium itself, and the old set's 16px tile shows the white card pixel for pixel.

**Files.** `scripts/generate_favicons.py`, `web/assets/favicon-16.png`, `web/assets/favicon-32.png`, `web/assets/favicon-64.png`, `web/assets/favicon-180.png`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.

**Open/next.** The open request in `web/DESIGN_NOTES.md` for a `GET /assets/<path>` route is unchanged; until that route exists the favicons stay inlined. The in-page logo (`web/assets/mark.png`, still RGB on white) is unaffected: it sits on the white topbar, so it carries no card.

## 2026-10-28 â€” RFM and media planning: the two gaps a marketing student actually has

**Ask.** After the digital lane shipped, the owner asked whether the parked items â€” ad-platform and analytics
connectors, automated bidding, incrementality and holdout tests, multi-touch causal attribution, sequential
tests, budget recommendations â€” were needed by marketing students. The answer given was no for four of them and
"a concept, not a tool" for the other two, and the real gaps were RFM and media-planning arithmetic. The owner
chose both.

**Did â€” `rfm_scoring` (T1).** Quintile recency, frequency and monetary bands from a declared customer list.
Recency is ranked in reverse; ranks use competition ranking, so ties share the better band and band sizes can
differ; the eleven named segments come from a declared first-match rule set over the five-by-five grid
(`cannot_lose` first, `lost` last). Outputs are the segment sizes, the three mean scores and their sum; the
scored rows, the rule text and the label map travel in the appendix. Five frozen checks: an independent
band-boundary route built with integer ceilings, segment sizes summing to the count, bands inside one to five,
monotonic recency scoring and the combined mean as the sum of the three. Refuses fewer than five or more than
a thousand customers, duplicate names, negative recency and a frequency below one.

**Did â€” `media_plan` (T1).** Per vehicle: reach share, gross impressions, gross rating points, cost per rating
point and cost per thousand impressions; then the plan totals, a combined net reach under random duplication
and the average frequency that follows from it. Five frozen checks: a float second route, rating points as
reach share times frequency times a hundred, impressions as reach times frequency, plan points as the sum of
the vehicles', and a combined reach that lies between the largest vehicle and the sum. The report calls the
combined reach an upper bound and says the method does not recommend a buy.

**Did â€” catalogue and page.** Catalogue v0.4 appends one section-11.2 bullet, `QNT-MKT-15` (media planning), so
no existing `QNT-MKT` number moves; `MKT-08` is linked to `rfm_scoring` and is now a computed record, with
`QNT-MKT-04` still pointing at it. The Marketing shelf grows to 21 tiles in the same four groups, a 42-term
glossary (reach, reach share, average frequency, gross impressions, GRP, CPP, net reach, quintile score, RFM
segment) and two presets, `rfm` and `mediaplan`.

**One structural change.** `registry.py` used to try its link rules only for `QNT-` ids, so a quantitative
record sitting in a framework section could never be marked computed. The rules are now tried for every record
the catalogue types as `Q`, which is what `MKT-08` needed; no other record gained a link, because no other
rule matches those summaries.

**Tests.** `tests/test_marketing_additions.py` gains the RFM goldens (a ten-customer list whose bands are exact),
a rule-table test that fires all eleven segment rules, the media-plan goldens, refusals for both, and the
`MKT-08` / `QNT-MKT-15` link guards. `tests/test_session_api.py` gains sample inputs. Registry counts move to
156 records (Q 59) and catalogue version 0.4. Frozen fixture regenerated (124 methods, 126 presets) under B-121.

**Deliberately not built, and now stated in the guide:** platform connectors (import the export), automated
bidding, incrementality and holdout estimation, data-driven attribution, sequential tests and any budget
recommendation.

**Also corrected in the same pass.** Once the link rules applied to every `Q` record, two marketing records that
had been saying "not implemented" while their arithmetic existed under the quantitative section were linked:
`MKT-19` (attribution and campaign measurement) to `attribution_split`, and `MKT-20` (conversion-rate
optimisation and landing-page testing) to `ab_test_two_proportion` with `power_analysis`. `QNT-MKT-07` (customer
profitability by segment, product, channel or cohort) is now the only marketing record that says "not built",
which is true.

## 2026-10-28 â€” Line balancing and declared-rate tax; the rest named in the limitations

**Ask.** "Go. Those that are needed and will only bring issues, put it in limitation."

**Did.** Two T1 methods. `line_balancing`: tasks, precedence and a declared cycle time, packed with a
declared heuristic (longest task time or ranked positional weight), reporting station loads, the
theoretical lower bound, idle time and efficiency; a task longer than the cycle, an unknown predecessor
or a cycle is refused. `tax_declared`: income tax on positive taxable income at a declared rate, VAT
payable as output less input, deferred tax as a declared difference times a declared rate, the total
charge and after-tax income; it applies no jurisdiction's law. Operations gains line balancing under
"Process and capacity"; Accounting gets a "Tax and reporting" group; Entrepreneurship gets the tax tool
for projections. Guides, notes, glossary and the curriculum map updated; presets `linebalance` and `tax`.

**What went to the limitations instead.** A jurisdiction tax engine, audit opinion/sampling, group
consolidation, multi-echelon inventory and a shared session store. `KNOWN_LIMITATIONS.md` now has a
section that says, for each, why it is absent and what a student should do when an assignment needs it.
The distinction is deliberate: the first list is arithmetic on declared figures; the second needs a
declared legal/accounting policy or is infrastructure, and approximating it would produce a confident
wrong answer.

**Contract impact.** An approved unfreeze under B-079, recorded as B-119: 120 methods became 124 and
the preset surface 126; the fixture was regenerated. The limitations policy is B-120 and moves no number.

**Verified.** Eleven new tests (arithmetic, refusals, presets, shelf and glossary wiring); the suite and
`scripts/ci.py` remain the gate; the guides' worked examples were re-run through the methods.

## 2026-10-28 â€” Closing the deterministic gaps: schedule, EVM, OEE, SPC, ABC, sales variances, M/M/c

**Ask.** "These are in the limitations? ... they are not that hard. Can you close them without breaking
the pipeline?" The owner named scheduling, CPM/PERT, earned value, line balancing, SPC/OEE, tax, audit,
consolidation, ABC/target/life-cycle and budget/mix variances, multi-server queues, multi-echelon
inventory and the multi-instance store.

**Did.** Six T1 methods and one additive extension. `cpm_schedule` (forward/backward pass, float,
critical path, PERT expected time and critical-path variance), `earned_value` (SV/CV/SPI/CPI, two
declared EAC conventions, ETC, VAC, TCPI), `oee_analysis` (availability, performance, quality, OEE),
`process_control` (I-MR limits, out-of-control points, runs, Cp/Cpk), `abc_costing` (rates, allocations,
unit costs, every pool allocated) and `sales_variances` (price/mix/yield per product and in total).
`queue_analysis` now takes an optional `servers` and uses Erlang C; the one-server outputs are unchanged
and a limiting-case check pins them to the old formula. Project management, Accounting and Operations
pages, notes, guides, catalogue links and the curriculum map were updated.

**Why some were not done in this pass.** Tax needs a declared regime before any rate is applied;
audit is judgment plus a sampling convention, not a formula; consolidation needs a declared
group-accounting method (full goodwill versus proportionate, NCI at fair value); multi-echelon
inventory needs a model, not an identity; and the session store is infrastructure, not arithmetic.
Each is named in `KNOWN_LIMITATIONS.md` and the curriculum map, and each has a concrete convention I
would implement on request. Nothing was approximated to make the page look complete.

**Contract impact.** An approved unfreeze under B-079, recorded as B-118: 114 methods became 120 and
the preset surface 122; the queue method's test names changed to the general Erlang C identity plus a
single-server limiting case. Fixture regenerated. The docs and guide updates move no number.

**Verified.** 27 new tests (hand-checked arithmetic, refusals, presets, shelf wiring, M/M/c versus
M/M/1); the full suite and `scripts/ci.py` are the gate. The guides' worked examples were re-run
through the methods.

## 2026-10-28 â€” Marketing & customers gets the digital lane

**Ask.** "go to marketing and customers, check if everything about marketing is there. looks like it does not
include digital marketing such as analytics and related things to it." Then: "texts should also be solid to be
more readable."

**Did â€” catalogue.** The catalogue source moved to v0.3: nine framework rows `MKT-13..MKT-21` (channel mix,
SEO/content, paid media, email and lifecycle, social and influencer, measurement plan, attribution, CRO and
landing-page testing, automation and lead scoring) and seven quantitative bullets in section 11.2
(`QNT-MKT-08..14`). RFM was listed twice â€” a framework row and a bullet â€” so the bullet now reads
"RFM Segmentation." and the importer merges it into `MKT-08` with `also_listed_as: ["QNT-MKT-04"]`; the
record count stays honest at 155. The importer gained `DIGITAL_IDS`, `DIGITAL_Q_PREFIXES` and a `Q`-branch
merge, so a digital row or bullet is tagged `digital marketing` rather than the section's classical
discipline.

**Did â€” computations.** Seven additive T1 methods in `src/bp/methods.py`, each with a float second route,
exactly five frozen checks, refusals for impossible counts (clicks above impressions, conversions above
clicks, reach above impressions, a zero churn, enumerator sums that do not close) and a token-only report:
`campaign_efficiency`, `ab_test_two_proportion`, `attribution_split`, `channel_economics`,
`email_list_health`, `social_engagement`, `web_analytics`. `ab_test_two_proportion` is the only one whose
claim ceiling is `associational`; it also takes an optional declared minimum effect and reports the visitors
each arm would need. Two presentation bugs the smoke tests exposed were fixed at the source: a failed
identity check (`CPC x conversion rate` is *not* CPA â€” CPA x conversion rate is CPC), and a payback figure
that was formatted as currency rather than a period count.

**Did â€” page.** `subjects.py` gains `MARKETING_GROUPS`, `MARKETING_PERIODS`, `MARKETING_NOTES` (the seven new
tools plus the alpha note that was missing), a 33-term `MARKETING_GLOSSARY`, a `DISCIPLINE_LABELS` map and
`discipline_label` on every catalogue row, so the records table reads "Marketing frameworks", "Customer and
market analytics" and "Digital marketing" instead of internal tags. The shelf is 19 tiles in four ordered
groups with period badges and study notes; `web/index.html` retitles the section and rewrites the legend to
explain what each status actually means.

**Did â€” wiring and truth.** Presets `campaign`, `abtest`, `attribution`, `channelecon`, `email`, `social`,
`web`; `METHOD_LINK_RULES` links `QNT-MKT-08..14` with partial-coverage notes and extends
`QNT-MKT-02/03/05/06` so they no longer deny methods that now exist; the advisory power note in
`orchestrator._honesty` no longer tells a student that no sample-size calculation was reported when the
delivery reports one. Registry and the committed subject slice were regenerated; the frozen fixture was
regenerated under the approved unfreeze B-117 (114 methods, 116 presets).

**Tests.** `tests/test_marketing_additions.py` (23 tests): textbook goldens computed independently of the
float route, refusals and profile reasons, the five named checks on every preset, a delivered report with no
unresolved token, shelf grouping and glossary guards, the `QNT-MKT-08..14` links and the single RFM record.
`tests/test_session_api.py` gains sample inputs so the declared test names are still proved against real
code. Full suite: 1234 tests pass.

**Deliberately not done.** No ad-platform or analytics connector, no automated bidding, no incrementality or
holdout estimation, no multi-touch causal attribution, no sequential tests, no budget recommendation. The
method and preset contract is otherwise untouched.

## 2026-10-28 â€” Increment 3: tree, projects and weighted-matrix editors

**Ask.** "go" after Increment 2.

**Did.** The decision tree is now built from alternatives and outcome rows; multi-project from project cards with
per-project activity tables; the weighted matrix generates score rows from the criteria table with a refresh action.
Add/remove works for each. The JSON field remains for nested decision trees and any schema without a guided form.

**Verified.** Browser: decision-tree preset renders 2 alternatives, 4 outcomes, no JSON, runs to expected value
52,000; multi-project renders 2 project cards, 4 activities, runs to overall duration 8; MCDA renders the criteria
columns and 3 alternatives. No console errors; 1531 tests pass.

## 2026-10-28 â€” Result polish: key numbers and direct exports

**Ask.** "go" after Increment 1: finish the student result screen.

**Did.** The result now shows **What this means**, a method-specific **Key numbers** table and the actions Save, View the
Gantt (CPM), Download spreadsheet (XLSX), Download Gantt (SVG) and Charts and exports. Saving uses a non-navigating
persist step so the download buttons reuse the same case; the full artifact table stays under **For audit**.

**Verified.** Browser: CPM run shows duration 12, 3 critical activities and 4 activities; XLSX export wrote
`exports/<id>.xlsx`; the SVG button renders the client Gantt; no console errors. 1467 tests at the time of the
increment; the concurrent `proforma_statements`/`costeffectiveness` method wiring is not part of this change.

## 2026-10-28 â€” Student UX layer: guided Home, plain tiles, table editors

**Ask.** "increment 1 with student UX": make the UI intuitive for a business student, with guidance and explainers.

**Did.** Home now explains the three steps and links the PM worked example. The PM page leads with a six-step Start here
and states what it does not do. Tool tiles say what the student needs and whether an example is loaded; the method and
preset ids are gone from the first layer. The tool screen has a Before-you-start card, a note that the example is loaded
and a Clear action. Activities, resources, criteria, cash-flow and variable distributions are table editors with add and
remove rows; projects, decision trees and MCDA score maps keep JSON as an advanced fallback. Worksheets show their own
before-you-start line (RACI legend, risk-label rule). Results gain View the Gantt and a "For audit" technical record.

**Verified.** Browser smoke pass: Home explainer, subject start steps and 18 need lines, CPM table with four rows, run,
result, View the Gantt with arrows; no console errors. `test_product_subjects` checks the new copy fields and static
markers. 1467 tests pass at the time of the increment (the concurrent `proforma_statements` method was still being
wired by another session and is not part of this change).

## 2026-10-28 â€” Renderer extras: Gantt arrows, client SVG and XLSX bars

**Ask.** "renderer extras".

**Did.** Gantt specs accept declared `dependencies` and the server draws validated arrows; the Charts panel
renders the same spec client-side from the case's stored dates (no model, no new dependency); the XLSX Schedule
sheet adds a coloured bar strip (critical red, normal blue) when every date is a whole period. Also restored the
core-computation boundary: the chat break-even section now calls a frozen-core callable attached by the server
instead of doing the arithmetic in the product layer.

**Verified.** New tests for dependency arrows, unknown-endpoint refusal, the XLSX fill strip and the chat
boundary; the product package still imports no core module. 1467 tests pass; no method, input, check or number
changed.

**Still open.** Arbitrary-formula simulation, correlated inputs and fitted distributions; no computed PM gap
remains in the named scope.

## 2026-10-28 â€” Generic Monte Carlo for non-schedule decisions

**Ask.** "generic Monte Carlo".

**Did.** One T1 method, `monte_carlo`, with two declared models: NPV of uncertain cash flows and profit =
(price - variable cost) x volume - fixed cost. Inputs are fixed, uniform or triangular distributions; the run is
seeded and reports the mean, P10/P50/P90, range, positive share and observed input bounds. Five frozen checks,
refusals, notes and preset `montecarlo`.

**Verified.** Seeded NPV example: mean -9.20, P50 -9.63, P90 143.57, 46.5% positive. Profit example: mean
120.76, 84.2% positive. A different seed changes the sample. 1465 tests pass; frozen fixture 136 methods and
138 presets. No existing method, input, check or number changed.

**Still open.** Dependency arrows, client-side Gantt and the XLSX bar strip; no generic arbitrary-formula
simulation, correlation or fitted distributions.

## 2026-10-28 â€” Decision batch C: decision tree, real option, weighted matrix

**Ask.** "start batch C".

**Did â€” methods.** `decision_tree` (rollback of a declared decision/chance/terminal tree with loss probability and range),
`real_option` (Cox-Ross-Rubinstein call/put, European or American, with delta) and `multi_criteria` (weighted totals and
ranks from declared criteria, weights and scores). Each has a float second route, five frozen checks, refusals, notes
and a preset (`decisiontree`, `realoption`, `mcda`).

**Verified.** Hand checks: Launch EV 52 against Pilot 29.5; five-step American call 14.79 with delta 0.617; weighted
totals 7.4, 7.2, 7.0. 1454 tests pass; frozen fixture 135 methods and 137 presets. Also removed a product-layer
import of the frozen core from the chat break-even helper.

**Still open.** Generic Monte Carlo outside scheduling; dependency arrows, client-side Gantt and the XLSX bar strip.

## 2026-10-28 â€” Project scheduling batch B: multi-project and schedule risk

**Ask.** "b" after batch A.

**Did â€” methods.** `multi_project_schedule`: priority-ordered serial scheduling across shared resource capacities, with
every activity start/finish, each project finish and delay against its own CPM, and the overall duration.
`schedule_risk`: a seeded Monte Carlo over independent triangular PERT durations, with mean, median, P80/P90,
observed range, target probability and each activity's criticality index. Both have a float second route,
five and six frozen checks, refusals, notes and presets `multiproject`/`schedrisk`.

**Verified.** Hand-checked examples: two projects sharing a crew finish at 4 and 8; 1,000 seeded runs give a
mean of 7.71, P80 of 8.46 and 92.9% within nine periods. A different seed changes the sample. 1446 tests pass;
the frozen fixture is 132 methods and 134 presets. No existing method, input, check or number changed.

**Still open.** Dependency arrows, client-side Gantt and the XLSX bar strip; the decision batch (Monte Carlo
outside scheduling, decision trees, real options, multi-criteria scoring).

## 2026-10-28 â€” Project scheduling batch A: levelling, crashing and calendars

**Ask.** "start batch A" of the remaining PM computation gaps.

**Did â€” methods.** Three T1 methods, each with a float second route and five frozen checks:
- `resource_leveling`: serial non-preemptive scheduling against declared resource capacities; levelled starts and
  finishes, delays, levelled vs unconstrained duration, over-capacity periods and peak demand before/after.
- `project_crashing`: greedy one-period crashing of the cheapest critical activity with a linear crash cost;
  final durations, crash periods, per-activity and total cost to a declared target.
- `calendar_schedule`: CPM over a declared working-period list, with early/late dates, float and critical path.

**Did â€” wiring.** Presets `leveling`, `crashing`, `calendar`; PM Schedule and control tools; Calculator
Operations group; student notes; README; frozen fixture regenerated (130 methods, 132 presets).

**Verified.** New `tests/test_project_batch_a.py` covers the hand-checked examples (7 vs 5 periods after
levelling; 7 periods at cost 130 after crashing; 7 calendar periods with a two-period gap), four refusals and
the three presets through the pipeline. 1438 tests pass. No existing method, input, check or number changed.

**Still open.** Multi-project scheduling and schedule-risk simulation; dependency arrows, client-side Gantt
and the XLSX bar strip; the decision batch (Monte Carlo, decision trees, real options, multi-criteria).

## 2026-10-28 â€” Stakeholder/communication and lessons-learned worksheets

**Ask.** "close 1-3", starting with the two missing delivery documents.

**Did.** Two catalogue records (PM-15 stakeholder engagement and communication plan, PM-16 lessons learned) and two T4 canvas worksheets. The stakeholder
sheet covers stakeholders, interests, evidenced influence, engagement approach, messages, channels, timing, owner and communication risks; the lessons
sheet covers what went well and what did not, the evidenced cause, the change, its owner, the audience and the evidence. Empty blocks and assumptions
are named; no score, rank or blame is derived. Registry regenerated from the source (158 records); PM page now 9 tools, 6 worksheets, 10 read-only records.

**Verified.** `test_project_worksheets` now covers six templates; registry counts and the PM composition test updated; 1427 tests pass. No computed
method, preset, check or frozen-contract entry changed.

**Still open.** Resource levelling, crashing, calendars, multi-project scheduling, schedule-risk simulation; Monte Carlo, decision trees, real options,
multi-criteria scoring.

## 2026-10-28 â€” Project management Gantt and schedule workbook

**Ask.** "close remaining PM gaps", after the answer that a third-party model is the wrong tool for drawing.

**Did â€” chart.** New `gantt` kind in `bp.product.charts`: one bar per activity from stored `es_`/`ef_` artifacts,
critical path in red, float as a thin whisker, shared time axis, deterministic SVG, digit-free labels and
refusals for a missing artifact or a finish before the start. The Charts panel offers "gantt (CPM schedule)"
and builds the spec from the case artifacts; no model, no browser arithmetic.

**Did â€” workbook.** SpreadsheetML and XLSX exports add a `Schedule` sheet (activity, early/late start and
finish, float, critical) when CPM artifacts are present, copied from the stored strings.

**Verified.** Five new tests: stored dates and critical colour, determinism, finish-before-start, missing
artifact, digit label, and the Schedule sheet. 1426 tests pass. No method, preset, input, check, number or
frozen-contract entry changed.

**Still not built.** Resource levelling, crashing, calendars, multi-project scheduling, schedule-risk
simulation; stakeholder/communication-plan and lessons-learned worksheets.

## 2026-10-28 â€” Project management delivery worksheets: charter, WBS, RACI and risk register

**Ask.** "go." after the shelf was complete except for the delivery documents a project assignment asks for.

**Did â€” templates.** Four T4 worksheets on the existing shared builders. **Project charter** (`template_project_charter`,
canvas, `PM-05`): objective, scope in and out, deliverables, sponsor and governance, budget, milestones, success
measures, assumptions and constraints. **WBS** (`template_wbs`, canvas, `PM-09`): deliverables, work packages,
acceptance criteria and exclusions, with declared work-package-to-deliverable links. **RACI** (`template_raci`,
declared matrix, `PM-10`): activities against confirmed roles; each cell starts R, A, C or I; the builder checks
exactly one A and at least one R per activity and names empty cells. **Risk register** (`template_risk_register`,
declared matrix, `PM-06`): risks against declared likelihood and impact labels, response and owner; no probability,
expected value or score. Registry template links added; the catalogue slice was regenerated.

**Did â€” page and docs.** The PM page now shows 9 tools, 4 worksheets and 10 read-only records. The student guide
gained a worksheet table and revised limits; `KNOWN_LIMITATIONS.md`, `PRODUCT_GAP_MAP.md`, `CURRICULUM_MAP.md`,
`DECISIONS.md` (B-131) and the changelog were updated.

**Verified.** New `tests/test_project_worksheets.py` (13 tests) covers registration, forms, examples, verbatim
text, the RACI one-A/one-R checks, the invalid-letter refusal and the risk register's empty-cell and no-score
behaviour. 1366 tests pass. No method, preset, input, check, computed number or frozen-contract entry changed.

**Still not built.** Stakeholder/communication plan and lessons-learned worksheets; Gantt drawing, resource
levelling, crashing, calendars and schedule-risk simulation.

## 2026-10-28 â€” Project management joins the rail; text goes solid

**Ask.** "i think you forgot project management to add as one of the business subjects ... ensure that the
orientation is for business students ... all texts will be in solid not grayed ones." The owner chose the
subject plus borrowed tools (no new methods), all 14 PM records, and the rail slot after Management &
strategy.

**Did â€” product data.** `SUBJECT_DEFS` gains `project-management` with seven existing frozen tools
(`npv`, `irr`, `dpayback`, `projectmetrics`, `scenario`, `case_decision`, `forecast`), the whole
`PM-01..PM-14` block and no worksheets. Management & strategy loses those ids and the projects discipline
tag, so it now shows 14 worksheets, 18 read-only records and 7 theory lenses. Three presentation groups
(Appraise the business case Â· Compare the options Â· Project cost and benefit), project-life/period
badges and a 23-term glossary orient the page to an assignment; the glossary marks critical path, Gantt,
earned value and CPI/SPI as not computed yet. `DISCIPLINE_LABELS` humanises the projects tag, and both the
gallery and detail payloads carry `discipline_labels`.

**Did â€” presentation.** The rail gains the eleventh item with a Gantt-style icon and its own tones;
`--text-2` and `--text-3` both resolve to `#0C243E`, so secondary and tertiary text is solid on every page,
and the health dot keeps a green accent. Build pill v0.91.

**Verified.** `tests/test_product_subjects.py` now pins the eleven-subject order, the PM composition and
the solid-text tokens; `tests/test_product_server.py` expects eleven. The suite passes. No method, preset,
input, check or frozen fixture changed; the Calculator union is unchanged because every borrowed tool was
already grouped.

**Did â€” teaching material.** New `docs/PROJECT_MANAGEMENT_STUDENT_GUIDE.md` (conventions, a verified PHP
worked example, a practice set with answers, and the gaps), a new limitations section and rows in
`PRODUCT_GAP_MAP.md` and `CURRICULUM_MAP.md`. The guide is linked from the HOME documentation spine.

**Gaps named on the page.** No PM worksheet (charter, WBS, RACI, risk register), no earned-value, PERT or
critical-path method. Those are the next real increment, not a hidden claim.

## 2026-10-28 â€” Accounting and Operations shelves, a syllabus map, and the delivery gate

**Ask.** "Do 1-5", with one correction: a named reviewer is not wanted â€” putting a third party's name on
a student's paper is wrong. The curriculum item was therefore reduced to a coverage map that names no
one.

**Did â€” computation.** Four T1 methods: `standard_cost_variances` (material price/usage, labour
rate/efficiency, optional variable and fixed overhead; positive is unfavourable), `inventory_policy`
(EOQ, orders per year, safety stock, reorder point, annual ordering and holding cost),
`queue_analysis` (single-server M/M/1) and `capacity_analysis` (capacity per resource, bottleneck,
utilisation, gap). Each has a float second route, five frozen checks, refusals, assumptions,
limitations and a token-only report. PHP presets `scv`, `inventory`, `queue`, `capacity`.

**Did â€” shelves.** Accounting is now three groups and nine tools, including working capital, loan
amortization and trend analysis that were built but not surfaced, with notes, a 16-term glossary and a
student guide. Operations and Supply chain get the process, inventory and evidence groups, an 18-term
glossary and a joint guide. The catalogue now states partial coverage for QNT-FIN-05 and QNT-OPS-01,
-02, -04 and -08, and leaves QNT-OPS-03/-05/-06/-07 as "not implemented".

**Did â€” assurance and delivery.** `docs/CURRICULUM_MAP.md` maps each shelf to typical SHS ABM and college
courses, marks itself provisional and credits no reviewer. `scripts/ci.py` runs the suite, the shelf and
frozen-contract audit and the page syntax check behind one exit code. `scripts/bench.py` probes a running
instance on read-only endpoints. `deploy/` has a Dockerfile, an nginx example, a systemd unit and a README
that says plainly what the current server is (one process, sessions in memory) and what a multi-instance
fleet still needs.

**On the reviewer.** The correction is right: a reviewer's name on a submission is a credential the
student did not earn and the reviewer did not sign for that paper. The guides still say the material is
not teacher-approved, because that is a limitation of the tool, not a name. No document now proposes,
assigns or displays a third-party reviewer for student work.

**Contract impact.** An approved unfreeze under B-079, recorded as B-114: 109 methods became 114 (the
sixth to tenth parallel marketing additions landed in the same window) and the preset surface became
116; the fixture was regenerated. The presentation, map and delivery work is B-115 and moves no number.

**Verified.** Full suite with the four new test classes (arithmetic, checks, refusals, presets, page
groups, catalogue statuses); `scripts/econ_shelf.py --check` in sync; `scripts/ci.py` reports each step;
`node --check` on the page script; `scripts/bench.py --help` and a probe against a local instance.

## 2026-10-28 - Management & strategy: the eight worksheets and the catalogue status

**Ask.** "Check management and strategy ... they are all valid frameworks and need to be
implemented. I just don't understand the catalogue records and their status."

**Found.** The page showed 36 catalogue rows, 33 of them "not implemented", including seven
theories that the catalogue says must never become templates; three canvases appeared both as a
worksheet and as a "not implemented" row; and the 14 performance/project records the page's own
discipline tag claimed appeared on no page at all. All 140 registry records carried the same
`pipeline_status=catalogued` and `evidence_status=unreviewed`, so the status column carried no
information.

**Changed.** Eight T4 worksheets: PESTEL, Value Chain, Ansoff, Blue Ocean/ERRC, activity-system
fit (shared canvas builder); scenario planning and strategic group mapping (new declared-matrix
builder); VRIO (new resource-verdict builder, no derived verdict). The registry now derives a
`form` and a form-specific status; no framework says "not implemented". The Management page shows
14 worksheets, 32 read-only records grouped by discipline and 7 theory lenses, and `PM-01..14`
finally appear. `IMP-03..07` move to Economics. No computation changed.

## 2026-10-28 â€” Local OCR and global free data: finish the P2 retrieval/ingestion slice

**Ask.** Install a PDF renderer and Tesseract; add the free global sources the owner named (SEC
EDGAR, Alpha Vantage educational, World Bank) and require manual entry where none exists. Do not
assume a Philippine-only context.

**Installed.** `pypdfium2` 5.14 and Tesseract 5.4.0 (UB Mannheim) plus `pytesseract`. `documents.py`
resolves the binary from `BP_TESSERACT_CMD`, PATH or the usual Windows paths; a scanned PDF is
rendered at 144 dpi and OCR'd page by page, an image is OCR'd directly. New limits: 20 OCR pages,
200k characters, encrypted refused; the text remains unverified. Without the packages the file is
stored and reported `ocr_required`, as before.

**Global sources.** Added Alpha Vantage quote/fundamentals (user key in `BP_ALPHAVANTAGE_KEY`),
SEC EDGAR filings (no key) and World Bank macro (no key, CC BY 4.0), all through the same
provenance wrapper: source, as-of date, URL, response SHA-256, cache, and no automatic input.
Keys are redacted from returned URLs. The Finance panel exposes Quote, Fundamentals, Filings and
World Bank next to FX and the Treasury yield; PSE/private companies are explicitly manual.

**Why not Yahoo/PSE.** No public licence and terms that forbid scraping; the quotes are
exchange-licensed. The free usable paths are the ones above; Alpha Vantage's educational tier is
free with a key and attribution.

**Verified.** 26 market-data tests (injected fetch, no network; key redaction, rate-limit refusal,
EDGAR parsing, World Bank parsing) and 11 document tests (text layer, scanned PDF OCR, image OCR,
encrypted, limits, intake round trip). Live checks on a scratch server: SEC Apple 10-K list,
World Bank PH GDP growth 4.40% (2025), missing Alpha key refusal, and the panel rendering both
cards with provenance. Full suite 1160 tests.


## 2026-10-28 â€” The planning lane: canvases, projections, dilution, funnel, retention, demand and intent

**Ask.** "Do your recommendations" with the context that the product intends to serve hundreds of
thousands and then millions of students, so coverage must be as extensive as possible without
sacrificing correctness.

**Did â€” worksheets.** Four T4 templates on one shared builder, renderer and nine-check set: Business
Model Canvas (nine blocks), Lean Canvas (nine), Value Proposition Canvas (six, with declared links from
pain relievers and gain creators to the pains and gains they address) and a marketing plan (STP plus
the product/price/place/promotion mix, with the service extension optional). Every item is the
student's; empty blocks are named and left empty; links survive only when both ends exist; no score,
ranking or recommendation is produced. Registered to `STR-15`, `STR-16`, `STR-17` and `MKT-02` and
offered as worksheets on Entrepreneurship, Management and Marketing.

**Did â€” computation.** Six T1 methods: `sales_projection`, `cap_table_round`, `sales_funnel`,
`cohort_retention`, `demand_curve` and `purchase_intent`, each with a second float route, five frozen
checks, refusals, assumptions, limitations and a token-only report. A new `value_matrix` input type
validates the cohort rows. PHP presets for all six.

**The defect the new methods exposed.** A delivered report still contained raw `{{ref:...}}` tokens
whenever the declared period had a space in it (`point in time`, `per observation`). The draft
renderer's token pattern only accepted `\w+` in the period field. The pattern now accepts the declared
period text; this also repairs the latent case for any future method that declares such a period.

**What was deliberately not built.** Term sheets and negotiated clauses, liquidation preferences,
anti-dilution, vesting, multiple rounds, conjoint analysis, survival models, Monte Carlo valuation and
market-data retrieval. Each is legal, contractual or probabilistic rather than declared-input
arithmetic, and each is named in the guide and in `KNOWN_LIMITATIONS.md`.

**Contract impact.** An approved unfreeze under B-079, recorded as B-109: 97 methods became 103 and
the preset surface became 105; the fixture was regenerated. The templates are B-108 and touch no
number.

**Verified.** The full suite passed with 35 new tests (hand-checked arithmetic and refusals for the six methods, preset
delivery, every canvas check, verbatim listing, gap reporting, link validation, determinism, no raw
digits in a narrative, and the shelf wiring). `scripts/econ_shelf.py --check` in sync; the canvas and
marketing-plan examples deliver end to end.

## 2026-10-28 â€” Free market data and PDF reading, both fail-closed

**Ask.** After the P2 list: recommend free market data, and provide the document-upload reading
mechanism; the multi-analysis case container was dropped (B-103).

**Market data.** New `bp.product.marketdata`: Frankfurter for FX (no key, no quota) and the U.S.
Treasury par yield curve (no key). Fixed HTTPS allowlist, 20 s timeout, 1 MB cap, redirect check,
300 s cache, and a SHA-256 of the response. The Finance page has a lookup panel; the value is shown
with source, date and hash and is **never auto-filled** into a tool. Routes `/api/market/fx` and
`/api/market/riskfree`. No equities/fundamentals/PSE yet: those need a source and licensing choice.

**Documents.** New `bp.product.documents`: PDF text layer via optional `pypdf`; image OCR only when
Tesseract and `pytesseract` exist. Scanned PDFs return `ocr_required`; encrypted, >50 pages or
>200k characters are refused. Intake gains the `document` kind, `extracted`/`ocr_required`
statuses, `/extract` and `/text` routes, and the attachments strip gains Extract/Show text. The
text is written beside the payload and labelled unverified; it never enters a method input.

**Boundary.** The readers are optional and imported lazily only in `documents.py`; the product
boundary test allows exactly `pypdf`, `pytesseract` and `PIL` there. The computation core and its
fingerprint stay standard-library only; without the readers the file is stored and refused with a
reason.

**Verified.** 16 new tests (9 market-data with an injected fetch and no network, 7 document/intake
tests including the text-layer fixture, blank/scanned and encrypted PDFs). The live app was checked
on a scratch port: FX 63.986 USD/PHP, 10Y Treasury 4.99%, PDF upload -> extract -> text preview,
and the Finance panel rendered its lookup card with source, date and hash. Full suite: 1116 tests.


## 2026-10-28 â€” The Entrepreneurship shelf becomes a business plan a student can actually submit

**Ask.** "Check the entrepreneurship if all the computation needed by the subject is in the pipeline,
and ensure that this is oriented towards a student using it for their assignment." Then "go per your
preference" on the plan: wire what exists, add the missing computations, leave the canvases labelled.

**What the audit found.** The shelf had eight generic tools, one SWOT worksheet and five catalogue rows
that all read "not implemented". A feasibility study asks for market size, a price, break-even in pesos,
the capital to raise, the runway and a return; **none of those six computations existed**. `breakeven`
returned units only, so the peso break-even, the margin of safety and the target-profit volume could not
be produced. The page had no glossary, no student guide, no business-plan grouping, and five of its
twelve rows were canvases with no worksheet. The registry already said it plainly: QNT-MKT-01..03 and
QNT-FIN-07 were "not implemented".

**Did â€” computation.** Five T1 methods, each with a float second route, five frozen checks, declared
inputs, refusals, assumptions, limitations, caveats and a token-only template: `market_sizing` (TAM/SAM/
SOM), `startup_capital` (requirement less declared sources, with a surplus instead of a negative raise),
`cash_runway` (months to zero, lowest balance and funding gap; a non-burning flow blocks), `pricing_decision`
(cost-plus, target-margin, break-even and target-return prices) and `return_on_investment` (ROI and
annualised ROI). `breakeven` was **extended additively**: the quantity is unchanged, the contribution
margin and break-even revenue always appear, and the margin of safety and target-profit volume appear
only when `expected_units` or `target_profit` is declared. Five PHP presets carry worked examples.

**Did â€” presentation.** Thirty tiles in five business-plan groups, a period badge on every tile, a
20-term glossary, a guidance paragraph on the subject and a generalised `_tool()` that reads
`SUBJECT_GROUPS`/`SUBJECT_PERIODS` instead of hard-coding Finance. The tools that were already built but
unwired (project metrics, scenario, loan, working capital, DCF, multiples, equity bridge, SROI, CBA,
elasticity, cost curves, markup/Lerner, trend analysis and the survey statistics) are now on the shelf.
The catalogue links were updated so the page states partial coverage honestly (market sizing, growth,
unit economics, pricing) and still shows the canvases as "not implemented". New
`docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md`: assignment requirement â†’ tool table, conventions, six worked
examples, a practice set with an answer key, and the stated gaps.

**Two mistakes worth recording.** (1) The first draft gave the shelf four extra tool keys so that the
break-even, unit-economics, multi-product and NPV tiles could carry PHP presets. That duplicated every
one of those tiles in the Calculator and broke the union guard; the keys were removed and the shared
presets are used. (2) A PowerShell `Set-Content` round-trip on `subjects.py`, `CHANGELOG.md` and
`BACKEND_CONTRACT.md` double-encoded every non-ASCII character (en dashes, arrows, middle dots). The
catalogue guard caught it immediately; the files were repaired by inverting the encoding and the guard
now passes with zero missing characters. Do not use PowerShell text round-trips on this repository's
UTF-8 files.

**Contract impact.** An approved unfreeze under B-079, recorded as B-104: 92 methods became 97 and the
preset surface became 99; `tests/fixtures/frozen_contract.json` was regenerated. `breakeven`'s existing
output and checks are unchanged. The presentation work is B-105 and touches no number.

**Verified.** 1116 tests OK, including 29 new ones (hand-checked arithmetic, checks and refusals for all
five methods and the extension, every new preset delivering without a raw token, tile grouping and
order, notes/period/level coverage, glossary terms, catalogue partial statuses, and no Finance grouping
leak onto Economics). `scripts/econ_shelf.py --check` audits both shelves and reports the fixture in
sync. The student guide's numbers were re-run through the methods, not copied by hand.

## 2026-10-28 â€” Multi-year trend analysis, the last core Finance gap

**Ask.** "go" after the P0-3 presentation work: close the one remaining core assignment, multi-year
common-size and trend analysis, and then stop at the items that need an owner decision.

**Did.** `trend_analysis` (T1): five equal-length period lists (years, revenue, cost of sales,
operating expenses, net income) with optional total assets and equity; outputs are the revenue CAGR,
the latest period-on-period growth, a revenue index on the first period, gross/operating/net margins,
the common-size cost and expense shares, endpoint margin changes, a net-income CAGR and index when
the base is positive, and equity-to-assets and asset growth when the balance-sheet lists are given.
Six frozen checks, including the common-size identity and the CAGR compounding identity. The method
refuses unordered years, mismatched lists, non-positive revenue and a partial balance-sheet pair.

**Why this one and not the P2 list.** Multi-year trend is standard coursework and needs only declared
figures, so it fits the engine's boundary. Market-data retrieval, PDF/OCR ingestion, a multi-run case
container and named reviewer sign-off each need an owner decision (sources, dependencies, case
semantics, reviewer names); inventing any of them would break the honesty rule that made the audit
worth doing.

**Verified.** 1068 tests pass, including a new golden for the trend method (10% CAGR, 133.1 index,
16.55% net-income CAGR, 57.1% common-size cost of sales) and a refusal for mismatched period lists.
The live page was restarted after the increment; the Foundations group now carries 11 tiles and the
new study note and period badge render.


## 2026-10-28 â€” Finance gets a student front door: groups, notes, period badges and a percent guard

**Ask.** "okay do p0-3" after the Finance coverage audit: group the 32 tiles, put the study material on the page
rather than only in a file, and stop the classic percent-versus-decimal mistake.

**Did.** (1) Six ordered groups on the Finance page â€” Foundations, Corporate finance, Valuation, Investments,
Risk & derivatives, International â€” replacing one flat grid; Economics keeps its intro/intermediate/advanced
grouping. (2) Study notes for 27 Finance tools (formula, steps, common mistakes, related tools) rendered as
expandable notes, plus a 20-term glossary on the page. (3) A period badge on every Finance tile (`annual`,
`per period`, `per observation`, `spot rate`, `point in time`), so a per-period return cannot be read as annual.
(4) A delivery note whenever an output typed as a rate exceeds 100%, telling the student that rates are decimals
(6% is 0.06, not 6). The note warns; it does not refuse, because a genuine rate above 100% can exist.

**Why presentation, not computation.** The grouping and notes are presentation metadata in
`bp.product.subjects`; the numbers still come only from the frozen methods. No method, input schema, check,
preset or fixture entry changed. The one core-side line is the appended rate note in `orchestrator.py`, recorded
as B-099.

**Verified.** 1057 tests passed at this point (1063 after the economics completion), including two new ones: every Finance tool must carry a group, period, formula,
steps and mistakes in the declared group order (with no leakage onto Economics), and `rate = 6` must warn while
`rate = 0.06` must not. The live page was restarted and checked: six group headings, 32 cards, 32 study notes,
12 `per period` badges and the glossary table render with no console error. A screenshot was not possible because
the desktop window was not visible; the DOM checks stand in for it and are recorded here rather than claimed as
a visual pass.


## 2026-10-28 â€” Advanced econometrics: panel, IV, RDD and probit

**Ask.** "Go finish" after the welfare/international/behavioural release.

**Did.** Added four T1 methods: `panel_regression` (balanced within estimator), `instrumental_variables`
(just-identified IV with first-stage and OLS comparison), `regression_discontinuity` (sharp local-linear RDD) and
`probit` (binary probit with Newton-Raphson and marginal effect at the mean). Each has five frozen checks, declared
assumptions and a formula-level report. Added presets `panel`, `iv`, `rdd`, `probit` and student notes. The
Economics subject is now 55 tiles (21 intro, 21 intermediate, 13 advanced). Frozen fixture regenerated (92 methods,
94 presets) under B-100. Four new tests plus the existing table-driven suite.

**Verified.** The advanced tests pass, including the score equations for probit and the within-entity slope of 2;
the full suite passes at 1067 tests. `scripts/econ_shelf.py --check` reports 92 methods, 94 presets, 55 tools and
no missing student notes.

**Open/next.** VAR, cointegration and the remaining time-series estimators are parked; the economics catalogue
section and the diagram renderer remain product-layer gaps. The student guide is not yet teacher-reviewed.

---

## 2026-10-28 â€” Economics completed: welfare, international, development, behavioural and games

**Ask.** "Finish them all" after the macro core: the remaining economics fields, automated into the shelf.

**Did.** Added 21 T1 methods across welfare/public (`externality_pigouvian`, `public_good`, `social_welfare`,
`gini_coefficient`, `poverty_measures`, `tax_progressivity`, `optimal_pollution`, `output_gap_okun`),
international/development/behavioural (`comparative_advantage`, `tariff_welfare`, `exchange_rate_ppp`,
`interest_rate_parity`, `balance_of_payments`, `hdi`, `expected_utility`, `prospect_theory`, `labour_market`) and
electives (`price_discrimination`, `cournot_duopoly`, `difference_in_differences`, `nash_equilibrium`). Each has a
float second route, five frozen checks, declared inputs and a formula-level report. Added 21 PHP presets, student
notes for all of them, a 25-term glossary and a 51-tile Economics page (21 intro, 21 intermediate, 9 advanced).
Regenerated the frozen fixture (87 methods, 89 presets) under B-099. Six table-driven tests cover arithmetic, frozen
checks, headline values, refusals, preset delivery and page coverage.

**Verified.** The remaining-methods tests pass; the full suite passes at 1063 tests. Headline values: Pigouvian
social quantity 56 with DWL 8; Gini 0.25; headcount 50% and gap 20%; optimal emissions 18 and tax 46; output gap 5%
with a -2.5 point unemployment change; tariff DWL 50; PPP 50 and real rate 1.1; HDI 0.649; certainty equivalent 75;
Cournot price 43.33; DiD 15; one Nash equilibrium in the prisoner's dilemma.

**Open/next.** Advanced econometrics (panel, IV, RDD, probit, VAR, cointegration) remains the parked frontier lane.
The economics catalogue section and the diagram renderer are still the next product-layer increment. The student
guide is not yet teacher-reviewed.

---

## 2026-10-28 â€” Economics gets the macro core: ten methods and the firm

**Ask.** "GO" on the Phase 2 macro plan after the micro audit: national income, growth, inflation, unemployment,
money and fiscal multipliers, debt, plus cost curves, profit maximisation and market power.

**Did.** Added ten T1 methods â€” `cost_curves`, `profit_maximization`, `market_power`, `national_income`,
`growth_rate`, `inflation_cpi`, `unemployment_rate`, `money_multiplier`, `fiscal_multiplier` and `budget_debt` â€”
each with a float second route, five frozen checks, declared inputs, assumptions and a formula-level report. Added
ten PHP presets. The Economics subject grows from 20 to 30 tiles (20 intro, 5 intermediate, 5 advanced); every new
tool carries student notes, and the glossary gains GDP, GNP/NNP, CPI, CAGR, LFPR, MPC and debt-to-GDP. Extended
`docs/ECONOMICS_STUDENT_GUIDE.md` with macro conventions, worked examples and a macro practice set. Regenerated the
frozen fixture (66 methods, 68 presets) under B-098. 30 new tests.

**Verified.** The macro tests pass for arithmetic, refusals, frozen checks and pipeline delivery. The worked
examples reproduce the textbook figures: costs AC 70 / AVC 20 / MC 30; profit maximum Q 18 at P 64 with profit 710
and Lerner 0.5625; GDP 900, GNP 920, NNP 870; CAGR 7.18% with a 10.03-period doubling time; inflation 5% and real
interest 2.86%; unemployment 8%, LFPR 66.67%; money multipliers 10 and 7; fiscal multipliers 2.5, -2 and 0.5; debt
ratio 50% with a zero debt-ratio change.

**Open/next.** Welfare/public (externalities, public goods, social welfare, Gini, poverty), then
international/development, behavioural and advanced econometrics. The economics catalogue section and the diagram
renderer remain the next product-layer increment. The student guide is not yet teacher-reviewed.

---

## 2026-10-28 â€” Economics gets a micro core: five methods, student notes and an honest gap list

**Ask.** The owner asked whether Economics covers everything a student needs and said it looked very thin. The audit
found five tiles, three of them impact evaluation, no worksheets, six borrowed catalogue rows and no microeconomics.

**Did.** Added five T1 methods â€” `demand_supply_equilibrium`, `elasticity`, `tax_incidence`, `price_control` and
`market_concentration` â€” with a float second route, five frozen checks each, declared inputs and a formula-level
report. Added five PHP presets. The Economics subject now has twenty tiles, grouped into intro, intermediate and
advanced; every Economics tool carries a student note (level, formula, steps, common mistakes, related tools), and the
page renders the notes and a glossary. Added `docs/ECONOMICS_STUDENT_GUIDE.md` with conventions, worked examples and a
practice set with an answer key. Regenerated the frozen fixture (56 methods, 58 presets) under B-097. 17 new tests.

**Verified.** Targeted economics and product tests pass; the frozen-contract and subject guards pass; the full suite
passes. The five worked examples reproduce the textbook figures: equilibrium 20/60 with surplus 900/900; elasticity
-1.5 with revenue 1,000 to 1,120; tax 23/17 on 54 with revenue 324 and DWL 18; ceiling shortage 20 with DWL 50;
HHI 2,650 and CR4 90.

**Open/next.** Macro (national income, inflation, unemployment, money and fiscal multipliers, debt, growth), then
welfare/public, international/development, behavioural and advanced econometrics. The economics catalogue section and
the approved diagram renderer are the next product-layer increment. The student guide is not yet teacher-reviewed.

---

## 2026-10-28 â€” Finance is a student shelf now: fourteen methods, one approved unfreeze

**The owner's question was an audit, and the audit said no.** "Check the Finance under subjects" was answered by
reading the product catalogue rather than the marketing copy: Finance held eleven tiles (NPV, IRR, discounted
payback, WACC, DCF twice, equity bridge, unit economics, forecast, option comparison, currency) and eleven
catalogue rows, most marked "not implemented". That is the corporate-finance/valuation core, not a finance
degree: there were no bonds, no portfolio, no CAPM, no options, no VaR, no working capital, no DuPont, no
international parity, no capital-structure analysis. Two further faults were visible: ratio analysis, break-even
and the OLS/Pearson tools needed for beta were not on the Finance page at all, and nine risk records
(`RSK-01..RSK-09`) belonged to **no subject**, because "risk and decision analysis" is a discipline with no shelf.

**What was built.** Fourteen additive methods, each with its own independent second route, five to seven frozen
checks, a declared-input boundary and a template that names the formula: `time_value`, `loan_amortization`,
`bond_analysis`, `capm`, `dupont_analysis`, `multiples_valuation`, `working_capital`, `portfolio_analysis`,
`project_metrics`, `option_pricing`, `risk_metrics`, `fx_parity`, `leverage_analysis`, `scenario_analysis`.
The Finance page now carries 32 tiles and 23 catalogue rows; it also surfaces the accounting-adjacent tools a
finance student needs (`ratio_analysis`, `breakeven`, `multi_product_breakeven`) and the beta tools
(`descriptive_stats`, `pearson`, `ols`, `ols_robust`), and it absorbs `RSK-01..09` so risk management is no
longer orphaned. Fourteen presets give each method a worked starting point.

**"Appropriate for students" was treated as a testable requirement, not a tone.** Every input has a plain-language
description; every method states its intended use, an explicit unsupported use, its limitations and its caveats;
every report names the formula in words and shows intermediate values (periodic rate and periods, PV of the
explicit flows, the three DuPont components, the five Altman terms, the two Black-Scholes intermediate terms,
the three working-capital period lengths) rather than a bare answer. Nothing is prescriptive: every new method's
claim ceiling is `descriptive`, so the system cannot tell a student what to decide. Two methods are T2 because
their assumptions are genuinely contestable (peer comparability; Black-Scholes and European exercise), and the
catalogue notes say what is still missing (multi-year trend series, Monte Carlo, real options,
American exercise, more than two financing plans, credit and liquidity risk).

**The freeze was respected, not bypassed.** B-079 requires owner approval, a B-decision, code + tests + fixture in
one change. The owner's instruction is recorded as B-090; `tests/fixtures/frozen_contract.json` was regenerated
from the library and presets; the frozen-contract guard passes; and `BACKEND_CONTRACT`/`CONTRIBUTORS` state the new
counts (51 methods and 53 presets at this point; 56 and 58 after the economics increment).

**Verified.** 1023 tests passed at this point (1025 after the economics increment). Nineteen new finance tests plus a preset-delivery test were added, and the two
long-standing loops that must know every method (`test_session_api`'s declared-test-names check and
`test_sandbox`'s sandbox-parity cases) were extended. The first run of the new suite caught three real defects
before delivery: a MIRR/parity Decimal conversion bug, a multiples linearity check that ignored the net-debt
bridge, and a scenario flat-case that kept a declared forward rate. The draft audit also caught a raw digit in
the option template ("d1"/"d2"), which is exactly the guard working.

## 2026-10-28 â€” [product] The artefact decides the format, and the first look at a submission found a bug

**The owner's correction, and it was right.** A free menu of Word, PDF, Excel and PowerPoint for everything is
wrong: a slide deck of an accounting submission is not the Word file in landscape, it is a different artefact
with different content. The earlier increment had built that menu; this replaces it.

**Three layers.** *Blocks* are a fixed vocabulary assembled from the stored bundle - statements, workings,
checks, limitations, citation, headline, recorded values - and none of them computes anything. *Profiles* are
data: which blocks an artefact contains, which formats can carry it, and the default. *Renderers* are handed
the blocks.

| Artefact | Blocks | Formats |
|---|---|---|
| Assignment submission | statements Â· workings Â· checks Â· limitations Â· citation | Word, print-ready HTML |
| Working papers | statements Â· recorded values Â· citation | SpreadsheetML, CSV |
| Case presentation | headline Â· statements Â· checks Â· citation | **none yet** |

**A format is only offered when a renderer exists.** `presentation` is declared with its blocks and audience,
marked unavailable, and refused with the reason. Listing a format nobody has opened in its own application
would be the dishonesty this repository exists to remove.

**Refusals name what works:** *"Working papers cannot be produced as docx; it can be produced as
spreadsheetml or csv"*.

**Credits changed unit:** the free-first rule now applies to the artefact, so choosing PDF over Word does not
cost a student a credit; a second export of the same artefact does.

**A flake chased, not shrugged at.** One suite run failed and the next passed on identical code. The tests
were charging the repository's **real** credit ledger because `BP_STATE_DIR` was not isolated - 93 credits
left and falling, and at zero every export would have failed. `test_product_routes` now isolates the wallet,
the polluted `state/credits.jsonl` was deleted, and five consecutive runs were clean.

**The bug that only looking could find.** Rendering the first real submission for the owner produced a
document with **no statements in it**, silently: the exporter returns statements as a dict of parts and the
block assembler accepted only text, so the most important block vanished. Green tests had not caught it;
thirty seconds of looking did. Fixed to read the parts in order, with a regression test that also asserts the
combined blob is not used as a fallback (that would print every statement twice).

**Process note.** A concurrent design session was editing this tree at the same time. Its work was committed
separately and unmodified rather than folded into this commit, and this entry was deferred until that session
finished.

**Verified.** 988 tests OK, including the new profile tests and the statements-block regression.

## 2026-10-28 - [product] Home accepts attached files: intake store, routes and the Home controls

**Ask.** The owner: *"just provide intake capability to the pipeline. ill instruct you the rest. you may want to
add appropriate buttons there for uploading the needed files."*

**Did.**

1. `src/bp/product/intake.py` - a new product-layer store. Each attached file is written under `BP_INTAKE_DIR`
   (default `intake/`) as immutable bytes plus one JSON record (`bp-intake/1`): id, filename, extension, size,
   SHA-256, UTC upload time, kind (`structured` | `reference`), status (`stored` | `ingested` | `reference_only`),
   note, error and the typed table when one was read. It imports no frozen module and computes nothing.
2. `src/bp/server.py` - additive routes, wired beside the existing `/api/cases` prefix: `POST/GET /api/intake`,
   `GET/DELETE /api/intake/{id}`, `POST /api/intake/{id}/ingest`. The server, not the store, calls the frozen
   `bp.ingest`; a structured file is read on upload and can be re-read with `sheet`/`merged`. A file that cannot
   be read keeps its bytes and carries the refusal reason. All pre-existing routes are untouched.
3. `web/index.html` - **Attach files** beside the run control, drag-and-drop on the action box, and an attachments
   strip: name, size, status, and `Ingest` / `Remove`. The status is literal - `Ingested` with rows x columns,
   `Stored, not read`, `Reference only` - and any other file type is stored and labelled not read. The Data
   panel picker no longer offers legacy `.xls`, which the ingestion module refuses (`.xlsm` replaces it).
4. Tests: `tests/test_product_intake.py` (16) covers the store, the refusals, the corrupt-record visibility and
   the HTTP round trip. Build **0.75** moves the pill, its pin and the documentation counts together.

**Files:** `src/bp/product/intake.py` (new), `src/bp/product/__init__.py`, `src/bp/server.py`,
`web/index.html`, `tests/test_product_intake.py` (new), `tests/test_product_subjects.py` (the pill pin only),
`README.md`, `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, `docs/WORKLOG.md`.

**Verified.** 987 tests OK, including the product-boundary guard (the new module imports the standard library
only and no frozen core module) and the frozen-route guard (all twelve documented routes still present).

**Where this could be wrong.** The intake store deliberately has no PDF/DOCX text extraction, no
classification and no routing into a spec, a reference list or evidence items - those were excluded until the
owner directs them. `.txt` is treated as a delimited table (the ingestion module already does that), which may
surprise a user attaching prose. The 5 MB / 1,000-row / 50-column caps are inherited from ingestion and are
refusals, not truncation.

## 2026-10-28 - [ui] The left rail becomes the A1 strip: a full aqua-green bar, white labels, real coloured icons

**Ask.** The owner: another agent was changing the strip in the left rail; use A1 as the reference, but the
colour is the aqua green of the logo, only the long line behind the icons is coloured and the texts keep a white
background, and the icons must be real icons with colour, not lines. Then, on the first pass: *"not just a line
... it should be a full bar"*.

**Did.**

1. `web/index.html` - the strip behind the icons is now one full-height bar in the logo green (`#02A15E`, sampled
   from the logo PNG - the same `--green-600` the wordmark uses). The label column beside it stays white, so the
   expanded rail reads as the reference does: coloured icons on a coloured strip, and a white text panel.
2. The twelve rail icons (Home, the ten subjects, Calculator) are now solid, filled glyphs on white tiles, each
   in its subject's own colour - the Font Awesome Free 6.5.2 solid set (CC BY 4.0), not line drawings. The
   catalogue cards keep the existing line set, so `ICONS` is untouched and the rail reads from a new
   `RAIL_ICONS` map; the static rail markup carries the same glyphs, so the strip is right before the subject API
   answers.
3. Fixed a real bug carried in from the start: `all:unset` on `.railitem` and `.railtoggle` reset `box-sizing`
   to `content-box`, so the toggle's `width:100%` plus its own padding overflowed the rail and the collapse
   chevron stopped short of the right edge of the expanded panel. Both now carry `box-sizing:border-box`.
4. Build **0.74**: served markup changed, so the page pill, the pill pin in `tests/test_product_subjects.py`,
   `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md` and the README build line move together - the
   docs-state guard requires the documents and the page to agree.

**Files:** `web/index.html`, `tests/test_product_subjects.py` (the pill pin only), `docs/CHANGELOG.md`,
`docs/HOME.md`, `docs/HANDOFF.md`, `README.md`, `docs/WORKLOG.md`.

**Verified.** The full suite is green, including the 19 served-UI presence guards; the rail was checked in the
browser in both states - collapsed strip, and expanded strip with the white label column, the mint active label
and the chevron on the right edge.

**Open/next:** the bar is the brand green; if the owner wants the strip in the A1 navy instead, it is one token
(`--green-600`) in one rule. Not committed.

---

## 2026-10-28 â€” [product] Exports and credits: a real .docx, and a wallet that cannot double-charge

**Ask.** Increment B: let a student export what they have, with the first export of a report free and extra
formats charged - the price table to be supplied later, the mechanism built now.

**What already existed.** More than I assumed: the product layer had a self-contained HTML export, CSV and
SpreadsheetML 2003 XML (which opens in Excel), and a `POST /api/cases/{id}/export` route with the three
kinds. So this increment extended the surface rather than rebuilding it.

**Did.**

1. **`src/bp/product/docx.py`** - a hand-rolled Word writer: `[Content_Types].xml`, `_rels/.rels` and
   `word/document.xml` in a zip. Standard library only. The stored report is set in a monospaced face,
   because the statements are fixed-width columns and a proportional font would destroy their alignment - the
   presentation *is* the meaning here. XML is escaped explicitly, and the zip timestamps are fixed so two
   exports of the same bundle are byte-identical.
2. **`src/bp/product/credits.py`** - an append-only JSONL ledger with a **derived** balance (never a stored
   one), prices in `PRICE_TABLE` as configuration, a free-tier grant on first use, and quotes that show the
   price before anything renders.
3. **The export route** now prices first, refuses with 402 when the wallet cannot pay, renders, and charges
   **only after the file exists**; `quote_only` returns the price without rendering, for the UI's
   confirm step.

**A design flaw the tests caught, not me.** My first idempotency key was `account|report|format`, which made
*every* repeat export of the same file look like a retry - so nothing was ever charged and a student could
export forever. Corrected: deduplication happens only when the caller supplies an idempotency key, which is
what a retry carries; without one, a repeat export is a new export and is charged. The route accepts the key
from the request body.

**A boundary test that was too blunt.** `test_no_third_party_dependency...` rejected the bare substring
"docx" anywhere in the product layer - which banned the word outright, including a docstring explaining that
the writer is hand-rolled. It now reads *import statements*, still refuses a real `from docx import ...`, and
carries a self-check proving the detector still bites.

**Verified.** 965 tests OK, including 19 new ones: the wallet opening at its grant and the balance equalling
the ledger; the first export of a report free and a second charged; a different report free again; a retry
with the same key reused; insufficient credits refused; a refund appended rather than edited; an unknown kind
refused; the .docx being a valid three-part zip carrying the stored report and artifact values with the XML
escaped and well-formed; two exports byte-identical; the quote returning a price without rendering; an export
writing the file and charging; a second format charged; and an unaffordable export refused **before** a file
is written.

**What is deliberately not here yet.** PowerPoint (.pptx) is not built - it needs theme and layout parts and
carries the highest "opens but the layout is wrong" risk. True PDF is not built either: the HTML export
prints to PDF from the browser, which is exact and dependency-free. Excel remains SpreadsheetML 2003 rather
than .xlsx for the same dependency reason. All three are queued, in that order of value.

**No core change.** No method, preset, route family or frozen fixture moved. Nothing pushed.

## 2026-10-28 â€” [computation] The trial-balance check: the first feature built for the student's own homework

**Ask.** The owner's priority is a tool a student can use on their own assignment, not only on a supplied
case, and chose "check" over "compute" for the first UI work. A student arrives with a journal and a trial
balance and wants to know whether they are right.

**Did.** A new method, `trial_balance_check` (T2, the 37th method and 39th preset), compares the trial
balance a student submitted with the one their own journal rebuilds to, and reports every line that agrees,
differs, or has no counterpart - with candidate causes labelled as hints and an explicit list of what the
check cannot prove. Registered as a method rather than a new route: it rides the existing session API, gets
the sandbox, the bundle and the re-performance hash for free, and adds **no new route family**.

**Design decisions worth recording.**

1. **Matching is declared, not guessed**: by account code when both sides carry one, otherwise by name, and
   a name listed twice is refused rather than double-counted.
2. **The Ã—9 rule is only applied where the textbook applies it** - to a trial balance that does not balance
   - and the finding says "a hint about where to look, not a finding". Applying it to the difference between
   two balanced statements would have been a misuse dressed as a diagnostic.
3. **The verdicts lead with what the input allows.** With only a trial balance the verdict is: *"I can check
   that your trial balance balances, and that is all... all leave a trial balance balanced. Paste your journal
   and I can check the entries themselves."* That sentence is the teaching.
4. **It never decides which of the two figures is right.** The check locates disagreement; correctness depends
   on what the student intended.

**Two things the build itself exposed.**

1. A student listing the same account twice was silently double-counted. Found while writing the ambiguity
   test, which could not be constructed the way I expected because the chart does not allow two accounts with
   the same name - the real risk was on the *submitted* side. Now refused with a reason.
2. The delivery appendix was filed under `accounts` for every method that had one, including
   `currency_convert`, so renaming the key for the new method broke an existing test. The key is now
   unchanged for everything that already had one and `detail` only for the new check.

**Contract impact, stated deliberately.** This is an unfreeze: 36 methods became 37 and 38 presets became 39,
and `tests/fixtures/frozen_contract.json` was updated in the same commit (B-079). The change is additive -
no existing method, preset, route or check moved.

**Verified.** 946 tests OK, including 20 new ones: exact agreement and its caveat; a balance-preserving
difference located on both sides; an account only in the journal and one only in the trial balance; the
unbalanced-first ordering; the Ã—9 hint; the equal-and-opposite wrong-side hint; both single-input verdicts;
refusals for a duplicate row, a negative figure, over-precise figures, a row with no identifier and no input
at all; the partial-row schema; all five declared checks running and passing; the second route agreeing; the
appendix carrying the verdict and four `cannot_prove` items; the preset delivering under `detail`; and a trap
showing a tampered figure is never reported as agreeing.

**No UI yet.** The screen this feeds is the next increment, and the export/credit mechanism is B.

## 2026-10-27 â€” [computation] Re-performance now covers the document, not only the scalars

**Ask.** The owner asked what re-performance meant before accepting it as solid. Answering it honestly
changed the assessment: re-performance was **not** broken - a bundle using every new accounting feature
verified exactly - but it compared only the delivered scalars. A student submits a *document*; a change to
how the statements render would have left every scalar identical while the document drifted, and
re-performance would still have said `verified`.

**Did.** The delivery bundle now carries `statements_hash`, a hash of the rendered appendix (statements,
T-accounts, journal, equity statement, reconciliation), and `reperform` recomputes it from the re-run and
compares. A mismatch is reported as `statements: mismatch` and fails verification. Templates and methods
with no rendered appendix carry `None` and are unaffected, and a bundle written before the field existed
still verifies on its scalars - both are tested, because a verifier that rejects its own older bundles is
worse than one that says what it checked.

**Why the appendix and not the report text.** The appendix is the structured document the workbench renders
from, and it is what the sandbox already returns as `appendix_extra` - so the comparison uses the artefact
that exists rather than a re-rendered string that could differ for cosmetic reasons.

**Verified.** 926 tests OK, including 6 new ones: the bundle carries the hash; an untouched bundle verifies
with `statements: exact`; a tampered `statements_hash` is detected and named; a tampered scalar is still
detected; a bundle without the field still verifies and reports `statements: None`; and an ordinary method
with no appendix (NPV) carries no hash and verifies unchanged.

**What re-performance still does not do, stated plainly.** `environment_match: false` is *reported* but does
not fail verification. A bundle re-run after tonight's code changes will show the environment difference and
still verify on the numbers and the statements. That is deliberate: the figures should reproduce across a
code change, and the environment difference is how a reader learns the code moved.

**No unfreeze.** The frozen contract is untouched - `statements_hash` is bundle metadata, not a method
output. No build number. Nothing pushed.

## 2026-10-27 â€” [computation] Chaining two periods: nothing may reset at the boundary

**Why.** The verification pass named this as the most likely place for a real accounting error to hide: a
single period can be wrong in ways only a second period exposes, and period-boundary bugs show up as small
misstatements rather than failures. Every statement still balances when a reserve silently restarts.

**Did.** `accounts.build` now exposes `opening_lines_next` - the entry a case carries into its next period -
next to the `closing_balances` it already produced. That makes the handover the engine actually offers
usable, instead of leaving a student to reconstruct it. `tests/test_period_chaining.py` then chains two
quarters the way a student would: period two's `prior_closing` is period one's `closing_balances`, and its
opening entry is period one's `opening_lines_next`.

**What the second period proves.** The revaluation reserve carries forward unchanged at 600; retained
earnings goes 700 to 400, moving only by the second period's 300 loss; total equity moves 11,300 to 11,000,
which is exactly the period result and nothing else; the equipment, revalued to a gross of 7,200 with 3,600
accumulated, is depreciated against the *revalued* carrying amount to a net of 1,800; both balance sheets
balance; both periods pass all eleven checks; and a tampered prior-closing figure fails
`opening_balances_equal_prior_closing`.

**Two things this exposed, both now recorded rather than assumed.**

1. **A deferral cannot span a period boundary.** Schedule releases are confined to the engagement period, so
   a twelve-month prepayment cannot be modelled across two quarters in one schedule - the carrying balance
   must be brought in as an opening balance. That is a real constraint for students and belongs in the
   limitations.
2. **Depreciation after a revaluation must be declared by the owner.** The second period's schedule is
   written against the revalued 3,600, not the original 6,000, because the engine does not restate a
   depreciation schedule automatically. The test declares it explicitly, which is what a student must do.

**Two of my own test assumptions were wrong again, and the engine was right both times.** `closing_balances`
keeps an account whose debits and credits both exist but net to zero (dividends cleared by the close), so a
"same keys either side" assertion was false; and `build` *reports* a failed check rather than raising, with
the pipeline doing the blocking - so the tampered prior-closing test had to assert the check, not an
exception.

**Verified.** 920 tests OK. No unfreeze. No build number. Nothing pushed.

## 2026-10-27 â€” [computation] Close the two gaps the verification pass found

**Why.** The pass proved the invariants hold, and said plainly what it did not prove: there was no golden
fixture for the schedule arithmetic, and sandbox parity for the new schedule kinds had been checked by hand
once rather than permanently. Both were cheap and both were the difference between "the invariants hold"
and "the numbers are right".

**1. A golden fixture with an independent numeric route.** `tests/fixtures/generate_schedule_golden.py`
computes the expected amounts with exact `fractions.Fraction` and does **not import** `bp.schedules`; the
library computes with `Decimal`. Six cases: straight-line even and with a rounding remainder,
40% reducing balance, units of production, a three-period prepayment and a four-period deferred income.
The comparison is exact - a tolerance would hide precisely the rounding defect the fixture exists to catch.
Result: the two numeric models agree on every amount, including the 333.33 / 333.33 / 333.34 split and the
1,160.00 final reducing-balance charge.

**2. Permanent sandbox parity.** `tests/test_accounting_sandbox_parity.py` builds the combined engagement
(reversal, three depreciation methods through schedules, prepayment, deferred income, allowance and
write-off, disposal, revaluation, dividends) inside the guarded subprocess and in-process, then asserts the
eleven check results, their names, and every delivered scalar agree exactly. It agrees.

**A bug in the fixture generator, caught before it mattered.** The first depreciation cases omitted `start`
and the account codes, so the generator produced a fixture the engine could not run at all - every case
failed with "start must be YYYY-MM". Fixed by giving the depreciation cases their structural defaults; the
amounts were never affected.

**What remains unproven, stated rather than hidden:** no multi-period chaining test (closing balances
feeding the next period's opening with a revaluation reserve and deferrals carried forward), and no
re-performance run of a delivered bundle carrying the new appendix fields. Both are noted for the next
verification pass rather than assumed to be fine.

**Verified.** 909 tests OK. No unfreeze. No build number. Nothing pushed.

## 2026-10-27 â€” [computation] Verification pass over the accounting pipeline

**Why.** Every increment tonight was proven in isolation, and the suite that guards them was written
*before* these features existed - so it cannot catch interactions between them. Two concrete reasons this
was not optional: an edit deleted `check_invariants` outright while `py_compile` and the import both
passed, and several of my own test expectations were wrong until checked against printed engine figures.

**What was checked, and the result.**

| Check | Result |
|---|---|
| Everything compiles (`compileall` over `src` and `tests`) | clean |
| Every public function added tonight still exists | present: `account_ledger(s)`, `journal_view`, `changes_in_equity`, `balance_sheet_groups`, all eight schedule kinds, every report renderer |
| Frozen contract untouched since the session began | **no diff** in `tests/fixtures/frozen_contract.json` |
| Full suite | 902 tests OK |
| **One engagement using every feature at once** (reversal + three-method depreciation + prepayment + deferred income + allowance and write-off + disposal + revaluation + dividends, IFRS framework) | all eleven pipeline checks pass; balance sheet balances; both cash-flow routes agree; every T-account rolls forward; every journal entry balances; the equity statement ties to the balance sheet; OCI is separate and the reserve holds it; the deferrals and the allowance clear exactly |
| Sandbox parity for that same engagement | 11 checks pass inside the subprocess, **no scalar mismatches** against in-process |
| Determinism | identical journal, statements, equity statement and ledgers across two builds |

**Two findings, both documentation, neither arithmetic.**

1. **Pooled accumulated depreciation cannot support a per-asset disposal or revaluation.** The combined
   scenario first failed with *"the ledger holds 6000.00 of accumulated depreciation on 1210, but the
   disposal declares 0"* - because my scenario pooled two assets' depreciation into one account. The engine
   was right to refuse; it cannot know which asset a pooled balance belongs to. The consequence is recorded
   in `KNOWN_LIMITATIONS.md`: give each asset its own accumulated-depreciation account.
2. **`PRODUCT_GAP_MAP.md` still described schedules as "(depreciation/amortization/accruals)"** - the same
   class of stale claim corrected this morning in the subject catalogue. Rewritten to state what exists now,
   including T-accounts, the journal, the three depreciation methods, the five new schedule kinds, the
   statement of changes in equity, the sectioned balance sheet and the OCI route.

**One thing confirmed rather than assumed.** The indirect cash-flow route sums *all* equity movements, and
OCI now closes into equity, so a revaluation looked like it could corrupt the cash flow. It does not: the
revaluation adds +400 to equity and +400 to non-current assets, and the route adds the first and subtracts
the second, so the two cancel. Verified by both routes agreeing at -1,350, and by the check that already
guards it.

**Not found:** no arithmetic defect, no contract drift, no non-determinism, no sandbox divergence. The
flags the combined engagement raised are both legitimate - retained earnings in debit because the period
made a loss, and a disposal entry whose counterparts mix investing with an operating loss.

**No build number, nothing pushed.** 902 tests OK.

## 2026-10-27 â€” [computation] Revaluation, built on the OCI route and anchored to IAS 16

**Ask.** The increment the IAS 16 research unblocked: an asset could be depreciated but never revalued.

**Authority, and its limit.** The accounting is not a judgement call, so it was researched rather than
reasoned. The IFRS Foundation's own record of the 2013 *Annual Improvements* amendment states that the
determination of accumulated depreciation does not depend on the valuation technique and that **accumulated
depreciation is the difference between the gross and the net carrying amounts**. IAS 16.35 permits two
presentations; IAS 16.39 sends an increase to other comprehensive income and accumulates it in equity as a
revaluation surplus; IAS 16.40 sends a decrease to profit or loss except to the extent it reverses a prior
surplus. The standard's full text is licensed and was **not** read - the decision relies on the IFRS
Foundation's project summary for the amendment, and the paragraph references are cited, not paraphrased.

**Did.** New schedule kind `revaluation`:

- **`method: proportionate`** (default) - gross and accumulated are restated by the same factor so that
  gross less accumulated equals the revalued amount.
- **`method: elimination`** - accumulated is written off and gross is set to the revalued amount.
- Both satisfy the identity the amendment pins (accumulated = gross - net) and produce the **same** net
  carrying amount and the **same** surplus; only the gross and accumulated figures differ.
- An increase credits the `oci` account and closes to the `oci_reserve` equity account. A decrease is
  expensed. A declared `reverses_surplus` amount is charged against the reserve first.

**Where the engine refuses to guess.** IAS 16.40 requires the reversal of a prior surplus *on the same
asset*, and this engine keeps one pooled reserve. It therefore does not decide how much of that reserve
belongs to this asset: the owner declares `reverses_surplus`, which is validated against the decline. The
limitation is recorded in `KNOWN_LIMITATIONS.md` together with the second one: depreciation after a
revaluation is not automatically restated onto the revalued carrying amount.

**Verified.** 892 tests OK, including 14 new ones: both presentations restating gross and accumulated while
agreeing on the net and on the 400 surplus; the statement balancing either way; an increase reaching the
reserve and leaving retained earnings alone; a decrease expensed; a declared reversal splitting 150 to the
reserve and 250 to profit; and refusals for an unknown method, a negative amount, a revaluation to the
existing carrying amount ("changes nothing"), a fully depreciated asset, and a gain pointed at a non-OCI
account. The trap asserts retained earnings stays at 850 and the reserve at 400, and explicitly that
retained earnings is not 1,250 - the figure a credit-to-profit implementation would show with every entry
still balancing.

**A test of mine that was wrong twice, and why it is worth recording.** The first version asserted retained
earnings of 1,650 while the specification I had built quietly booked 800 of depreciation, so profit was
850; the second looked up the depreciation entry by list index and hit one of the preset's own entries
instead of the one it had appended. Both were faults in the test, not the engine - but they are exactly the
kind of arithmetic slip that a "the numbers look plausible" review waves through, which is why every
expectation here was replaced with one printed from the engine first.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**The core accounting build is now complete for both phases.** What remains is the UI: none of this is
visible on the page yet.

## 2026-10-27 â€” [computation] Other comprehensive income: a separate route, closing to a reserve

**Ask.** Phase 2, final increment: the route revaluation waits on. The statement model had income,
expenses, assets, liabilities and equity - nowhere for a gain that is real but is not profit.

**Did.** A new account type `oci` (credit-normal). `statements()` now carries `oci`, `total_oci`,
`profit_for_period` and `total_comprehensive_income`; `report.income_statement` presents other
comprehensive income **after** net income and adds total comprehensive income; `closing_entries` moves
the OCI balance to an equity account with role `oci_reserve` and leaves the OCI account at zero;
`changes_in_equity` classifies that movement as "other comprehensive income". A chart with an OCI account
and no reserve account is refused by `validate_spec` and again by the closing step, because there would be
nowhere for the balance to go.

**A post-closing subtlety that caught a bad test.** The appendix statement set is *post-closing*, so
`total_oci` there is zero - the OCI has already moved to the reserve. My first test asserted 1,000 against
that set and failed; the output was right and the test was wrong. The figures a reader wants are the
pre-closing ones, so `accounts.build` now also exposes a `comprehensive_income` block
(`profit_for_period`, `oci`, `total_oci`, `total_comprehensive_income`) as **data**, not only as rendered
prose - the UI cannot read a text statement.

**The property that matters, and its trap.** A revaluation must not inflate profit. Closing OCI to
retained earnings is the plausible wrong implementation: every entry still balances, but profit reads
2,650 instead of 1,650 and the reserve stays empty. The trap asserts retained earnings is 1,650, the
reserve is 1,000, and explicitly that retained earnings is *not* 2,650.

**Verified.** 878 tests OK, including 12 new ones: the comprehensive-income block carrying the right
figures; post-closing OCI equal to zero with equity at 7,650; OCI presented after net income with total
comprehensive income of 2,650; no OCI section when there are no OCI accounts; the OCI account closing to
zero; the reserve carrying 1,000; the balance sheet still balancing; the equity statement classifying it;
both refusals for a missing reserve; an unknown account type still refused; and the profit-inflation trap.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Phase 2 complete.** Revaluation can now be built on this route: IAS 16.35 allows proportionate
restatement or elimination of accumulated depreciation, the 2013 amendment pins accumulated depreciation
to gross minus net, IAS 16.39 sends an increase to OCI and IAS 16.40 sends a decrease to profit or loss
except to the extent it reverses a prior surplus. The accounting is settled; only the schedule remains.

## 2026-10-27 â€” [computation] Current/non-current balance sheet: presentation only, and it is declared

**Ask.** Phase 2, second increment: the balance sheet was flat - assets, liabilities, equity, with no
current/non-current split, so it did not look like a balance sheet a student is asked to prepare.

**Did.** Accounts may declare `section` (`current`, `non_current`, or empty). `ledger.balance_sheet_groups`
groups the signed contributions into current and non-current assets and liabilities, an explicit
`unclassified` group for accounts that declare nothing, and equity. `report.balance_sheet` presents the
sections with subtotals when anything is classified and falls back to the **previous flat layout,
unchanged**, when nothing is - so no existing specification changes its output.

**The classification is declared, never inferred.** Whether a receivable is current is a fact about the
item and the entity; the engine does not guess it from a balance. An account with no declared section is
reported as unclassified rather than being quietly forced into one.

**The safety property is that grouping moves nothing.** The subtotals derive from the same signed
contributions the flat statement uses, so reclassifying an account can only move a line between sections.
The trap test reclassifies receivables from current to non-current and asserts current assets fall from
7,500 to 5,500 and non-current rise from 1,500 to 3,500 **while the sum - total assets - is unchanged**.

**A difference the grouped layout introduces, and it is deliberate.** The flat renderer labels rows with
the account name; the grouped renderer labels them with the statement `line`, so several accounts behind
one line aggregate there. A test asserted the account name and failed, correctly: the output was right
and the test was wrong. Recorded because a reader comparing the two layouts will see this.

**Verified.** 866 tests OK, including 8 new ones: the sections and subtotals appearing; each subtotal
equal to its stated figure; total assets, total liabilities and closing equity identical to the flat
statement; the balance sheet still balancing; an unclassified account landing in its own group and still
counting toward total assets (9,400 with a 400 deposit); the flat layout preserved for an unclassified
chart with `classified` false; and the reclassification trap.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched. The
new `section` field is optional, so the specification schema is backward compatible.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Remaining in Phase 2:** the other-comprehensive-income route, then revaluation on top of it (IAS 16
settles the accounting; only the statement model was missing).

## 2026-10-27 â€” [computation] Statement of changes in equity: opening + movements = closing, and it ties to the balance sheet

**Ask.** Phase 2, first increment, in the systematic order agreed: present the books, not just keep them.
Equity could be read only as a single number on the balance sheet; nothing showed why it moved.

**Did.** `ledger.changes_in_equity(j)` returns, for every equity account: its opening balance, each
movement with a **kind**, a running balance and its closing balance, plus totals by kind and in total.
`report.statement_of_equity` renders it, and `accounts.build` exposes `equity_statement` and
`equity_statement_export` in the appendix.

**Classification is structural, never textual.** A movement is a distribution when it sits on an account
with the `dividends` role, a contribution on `capital`, and the period result when it is a closing entry
whose *counterpart accounts* are income or expense accounts. A test builds the same journal with every
closing entry re-described as a dividend and asserts the classification is unchanged - a
description-based classifier would relabel profit as a distribution there.

**Two properties carry the statement**, and both are tested: per account, opening + the movements listed
= closing; and, in total, closing equity equals the figure the balance sheet reports. The second is the
one that matters, because a statement of changes in equity that disagrees with the balance sheet is
decoration.

**A serious mistake I made and caught.** The first edit that added these functions replaced the
`def check_invariants(...)` line instead of inserting before it. Because a function body may legally
continue after a `return`, the whole of `check_invariants` was silently absorbed into `changes_in_equity`
as unreachable code: **the module still imported and `py_compile` passed**, and the function simply no
longer existed. Only an explicit `hasattr` check found it. Restored, re-verified, and the full suite is
green. Worth recording because the failure mode is invisible to a syntax check and to an import.

**Verified.** 858 tests OK, including 10 new ones: the per-account identity; the running balance ending at
the closing balance; total closing equalling the balance sheet; total movement equalling closing less
opening; profit for the period equal to net income; dividends classified and negative; capital classified;
the misleading-description test; the rendered statement carrying opening, movement, closing and the
closing marker; and a trap showing that dropping one movement breaks the per-account identity.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in Phase 2:** the current/non-current balance-sheet split (an optional per-account classification,
so existing specifications keep their behaviour), then the other-comprehensive-income route that
revaluation waits on.

## 2026-10-27 â€” [computation] Bad-debt allowance: the engine computes the movement, never the estimate

**Ask.** Phase 1, final increment: the last adjusting entry. An allowance for doubtful debts could be
created only by hand, and the write-off had nowhere to go.

**Did.** New schedule kind `bad_debt`, two operations, either or both:

- **`charge`** - books a declared expense: Dr bad-debt expense / Cr allowance.
- **`target`** - books the movement needed to reach a wanted closing balance, which needs the ledger.
  A target **below** the existing balance is a reversal: Dr allowance / Cr expense. Reducing an
  over-provided allowance is a normal adjustment, so it is posted rather than refused.
- **`write_off`** - removes a specific debt against the allowance: Dr allowance / Cr receivables.

**The estimate is the owner's.** Nothing here decides what the allowance should be; the engine only
turns a declared charge, or a declared closing balance, into the movement that achieves it.

**Ordering is deliberate and load-bearing.** The write-off is posted first, so a `target` is measured
against the allowance **after** the write-off. Measured before, the allowance closes at
`target - write_off` and every entry still balances - the kind of mistake that survives review because
everything foots. The closing balance is the only thing that catches it, so there is a test that pins
exactly that.

**A refusal I had to add after the engine taught me something.** Writing off more than the allowance
holds was originally allowed, and the engagement then failed later at period close with
*"closing with abnormal balances needs a human decision: 1110"*. That is correct doctrine but a poor
message, so the schedule now catches it first: *"the write-off of 300 is more than the allowance held
(200) and nothing restores it; raise the allowance first, or write the debt off to expense instead"*.
The check is not absolute - a declared `target` that replenishes the allowance makes a large write-off
legitimate, and that case is allowed and tested.

**Verified.** 848 tests OK, including 16 new ones: the charge method; the target method reaching the
wanted closing balance; a target below the existing balance reversing the allowance; a target equal to
the balance posting nothing; a write-off clearing the receivable; the write-off-beyond-allowance refusal
and its message; a large write-off made acceptable by a restoring target; a write-off larger than the
receivables refused; both target-and-charge and neither refused; negative amounts and a bad date
refused; the statement balancing with an allowance; net receivables reduced by both the write-off and
the allowance; and the ordering trap above.

**KNOWN_LIMITATIONS.md** listed bad-debt allowances as not covered; that became false here, so the
paragraph now names the allowance among what the schedule layer does and keeps revaluation among what
it does not.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Phase 1 of the accounting build is now complete.** The next increment is Phase 2, which changes the
statement model (statement of changes in equity, current/non-current split, and the
other-comprehensive-income route revaluation waits on) and therefore stops here for the owner.

## 2026-10-27 â€” [computation] Prepayments and deferred income: the two deferrals, and they must clear

**Ask.** Phase 1, sixth increment: adjusting entries beyond depreciation. A prepayment paid in advance
and income received before it was earned could not be represented except by hand-writing every release
entry, which is where a deferral silently fails to release and leaves a phantom asset on the balance
sheet.

**Did.** Two new schedule kinds, exact mirrors of each other:

- **`prepayment`** - on the payment date, Dr prepaid asset / Cr cash; then one release per period,
  Dr expense / Cr prepaid asset. The final release absorbs the rounding remainder.
- **`deferred_income`** - on the receipt date, Dr cash / Cr deferred income; then one recognition per
  period, Dr deferred income / Cr revenue. The final recognition absorbs the remainder.

Both therefore end their balance-sheet account at **exactly zero**. That is the load-bearing property:
a prepayment that never fully released leaves an asset that is not an asset, and deferred income that
was never recognised leaves a liability that should not be there. Neither is a rounding detail.

**Refused:** a non-positive total; a period count that is not a positive whole number; a malformed
`start` (YYYY-MM) or `date` (YYYY-MM-DD); a release per period that rounds to zero; and a payment or
receipt **dated after the first period end** - which would drive the prepaid asset, or the deferred
liability, into the opposite side of the account and mislabel a liability as an asset.

**A now-false claim, corrected.** `KNOWN_LIMITATIONS.md` said schedules had "no prepayments". That
sentence became false with this commit, so the same paragraph now lists exactly what the schedule layer
covers and what it still does not (sum-of-digits depreciation, variable-rate loans, revaluation,
bad-debt allowances).

**Verified.** 832 tests OK, including 13 new ones: payment plus one release per period; the prepaid and
deferred accounts ending at exactly zero; the expense and the revenue carrying exactly what was paid or
received; the remainder landing in the final release (1,000 over three periods gives 333.33 / 333.33 /
333.34); every refusal above; a full engagement carrying both deferrals with the balance sheet still
balancing and both accounts cleared by period end; the release being *visible* in the prepaid T-account
rather than netted away; and a trap showing that dropping the final release would leave 333.34 sitting
on the balance sheet.

**A bug I wrote and caught.** The test helper was defined as `prep` but called as `pre`, so seven tests
failed with a `NameError` before any of the accounting was exercised. Fixed in the test, not by
renaming the engine.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** bad-debt allowance (an estimate, so it needs a declared target or charge plus an
optional write-off), then Phase 2 - the statement of changes in equity, the current/non-current split,
and the other-comprehensive-income route that revaluation waits on.

## 2026-10-27 â€” [computation] Asset disposal: the one schedule that must read the books

**Ask.** Phase 1, fifth increment: an asset could be depreciated but never derecognised, so a disposal
had to be hand-written as a multi-line entry - exactly where the gain or loss gets invented.

**Did.** New schedule kind `disposal`. It produces one compound entry: Dr proceeds, Dr accumulated
depreciation, Cr the asset at cost, and the difference to a gain (credit) or a loss (debit), with net
book value = cost - accumulated and gain = proceeds - net book value. Zero-amount lines are omitted
because the ledger refuses them, and a line for nothing is noise. A scrapped asset (zero proceeds)
therefore posts only the accumulated-depreciation and loss lines.

**It is the only schedule given the journal.** `accounts.build` passes `journal=j` to this one kind, and
the declared `cost` and `accumulated` are **cross-checked against the ledger**; a mismatch is refused
("the ledger holds 3000 on 1200, but the disposal declares a cost of 3500"). A disposal that cleared
more or less than the books actually hold would leave a residue on the asset or on its accumulated
depreciation and quietly break A = L + E. The check is a refusal, never a correction: the owner must
say which figure is wrong.

**Two bugs I wrote and caught.** The first version emitted a zero-amount proceeds line for a scrap, which
the ledger refuses; and the schedule raised `ScheduleError` straight out of `build`, so callers saw an
inconsistent exception type - it is now wrapped as `EngagementError`, matching the rest of the account
layer.

**Revaluation is deliberately NOT included.** It needs a declared policy - whether accumulated
depreciation is restated proportionally or eliminated against the gross carrying amount, and where the
surplus goes (revaluation surplus in equity, or through profit or loss). Two standard treatments exist
and the choice changes the statements, so it is an owner decision rather than something to invent. It is
queued, not forgotten.

**Verified.** 819 tests OK, including 13 new ones: the gain entry (proceeds 2,500 on NBV 2,200 gives a
300 credit), the loss entry, the break-even case with no gain or loss line, a scrapped asset taking the
full net book value as a loss, the statement still balancing after a disposal, both ledger cross-checks
refused, four input refusals, and a trap showing that clearing the wrong accumulated figure leaves a
residue of exactly 300 while the schedule path refuses that same input.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** the remaining adjusting-entry types (prepayment and its release, deferred income,
bad-debt allowance), then the statements block.

## 2026-10-27 â€” [computation] Depreciation beyond straight-line: reducing balance and units of production

**Ask.** Phase 1, fourth increment: `schedules.py` could only do straight-line, so any case with an
asset depreciated against its carrying amount, or against how much it actually produced, could not be
represented at all.

**Did.** `depreciation(spec)` now dispatches on a declared `method`: `straight_line` (the default, so
every existing spec is unchanged), `reducing_balance` and `units_of_production`. All three keep the
two guarantees the straight-line implementation already made - the charge never takes the carrying
amount below the declared residual, and the schedule sums exactly to cost minus residual with the
final charge absorbing the rounding remainder - and all three emit the same Dr expense / Cr
accumulated-depreciation shape, so nothing downstream changes.

- **Reducing balance** charges a declared per-period `rate` against the carrying amount. The rate is
  declared, never derived: the choice of rate is the owner's estimate, not a fact the engine can find.
- **Units of production** spreads the depreciable amount over a declared `total_units` and charges each
  period's own usage. The rounding remainder is absorbed by the **last period that actually produced**,
  not by a trailing idle period - dumping it into a month with no production would misstate both.

**Refused:** an unknown method; a rate outside `(0, 1)`; a charge that rounds to zero while the asset is
still above its residual; units summing to more than `total_units`; negative units; all-zero units; and
`changes` on a non-straight-line method, because a revised useful life has no defined meaning there.
Refusing is deliberate - silently ignoring `changes` would post a schedule the owner did not ask for.

**A now-false claim, corrected.** `KNOWN_LIMITATIONS.md` stated that schedules cover "straight-line
depreciation ... only; no declining-balance or units-of-production depreciation". That sentence became
false the moment this landed, so it was rewritten in the same commit - the same discipline the
catalogue correction applied earlier today.

**Verified.** 806 tests OK, including 19 new ones: all three methods sum to cost minus residual and
never dip below the residual; reducing balance charges 4000/2400/1440/1160 on a 10,000 asset at 40%;
units of production charges per usage and puts the remainder in the last producing period; every
refusal above is exercised; a trap test shows the new methods genuinely differ from straight-line; and
two integration tests post a reducing-balance and a units schedule through a **full engagement**,
confirming the balance sheet still balances, the expense closes to nil and net income carries the charge.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**Still not done, and now clearly queued:** asset disposal and revaluation (a disposal closes the
accumulated depreciation against the asset and recognises the gain or loss), then the remaining
adjusting-entry types.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 â€” [computation] Reversing entries: a correction you can see, not a balance you adjust

**Ask.** Phase 1, third increment: bookkeeping corrections were only possible by hand-writing the
mirror of an earlier entry, which is exactly where a sign error hides.

**Did.** An entry may now carry `ref` (a unique name) and another entry may declare `reverses: <ref>`
instead of `lines`. `accounts.resolve_reversals` expands the reversal into the **exact mirror** of its
target - same accounts, debits and credits swapped - on the declared date, with
`reversal of <ref>` as the default description. The kernel therefore receives two ordinary balanced
entries, and both are visible in the journal and in every T-account they touch.

**Refused before anything is posted** (`_reversal_errs`): an entry that declares both `lines` and
`reverses` (which one did the ledger receive?), a duplicate `ref`, an unknown target, a **forward**
reference, and a self-reference. Forward references are refused deliberately: resolving only backwards
means the expansion always completes in one pass and can never depend on itself.

**A correction, in the accounting sense,** is a reversal plus a new entry. Both primitives now exist;
no separate `corrects` keyword was invented for it.

**Verified.** 787 tests OK, including 11 new ones: the mirror keeps the same accounts and swaps every
debit for a credit; it moves the closing cash balance by exactly the negated amount; it uses the
declared date and generates the description; it is visible in the affected T-account; all five invalid
links are refused by `validate_spec` and a refused link never reaches the ledger; and a trap test
confirms the reversal actually changes the balances, so the mirror test is not testing nothing.

**No unfreeze.** Spec-level input, not a method contract change: `management_accounts` keeps its
eleven `test_names` and the frozen fixture is untouched.

**No build number** - no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** depreciation beyond straight-line (reducing balance, units of production) and
asset disposal, then the remaining adjusting-entry types.

## 2026-10-27 â€” [computation] The journal itself: the audit trail behind every balance

**Ask.** Phase 1, second increment, in the order agreed: the ledger engine should let a reader see
the entries, not just the totals derived from them. T-accounts showed one account's movements;
nothing showed the double entry that produced them.

**Did.**

- `ledger.journal_view(j)` â€” every entry in posting order as data: date, description, opening and
  closing flags, each line named and sided with its debit or credit, the entry's own debit and credit
  totals, and the entry hash from the chain `verify_chain` checks.
- `report.journal(j)` â€” the same journal as deterministic plain text, marking opening and closing
  entries and printing each entry's totals so a line that did not balance could never read as though
  it had.
- `accounts.build` now exposes `journal` (serialised) and `journal_export` (rendered) in the appendix.
  The existing `export` field is untouched.

**Why the totals are in the view.** The kernel already refuses to post an unbalanced entry, so the
totals are redundant for the engine. They are not redundant for a *reader*: an audit trail that shows
lines without proving the entry balances asks to be trusted rather than checked.

**Verified.** 776 tests OK, including 7 new ones: the view matches the journal entry for entry
(dates, descriptions, hashes) and the chain verifies; every entry balances in the view; rebuilding
every account's debits and credits **from the view** agrees exactly with `j.balances()`, which is what
the statements are built from; every line names a chart account; opening and closing entries are
marked, never both; and a trap test that drops one entry and shows the recomputation stops agreeing.

**No unfreeze.** The method contract is untouched: `management_accounts` keeps its eleven `test_names`
and the frozen fixture is unchanged. This is additive appendix data.

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** reversing and correcting entries (a declared reversal in the spec, with validation),
then depreciation beyond straight-line, then the remaining adjusting-entry types.

## 2026-10-27 â€” [computation] T-accounts: the ledger can now be read one account at a time

**Ask.** Phase 1 of the accounting build, first increment: the owner named "no T-tree balancing" as a
missing capability, and nothing in the engine could show a single account's movement â€” only a trial
balance total and derived statements. Layout first, wiring later; this is the computation side.

**B-032 closed (owner instruction, this session).** The ledger engine is the **custom kernel for
management accounts v1**, as the provisional recommendation already on record. The Beancount arm was
never run and is recorded as not run; the decision note records that it can be revisited if an external
engine is ever wanted. Phase 1 sits directly on this decision, which is why it was closed first.

**Did.**

- `ledger.account_ledger(j, code)` â€” one account as a T-account: opening balance (from the opening
  entry), every period posting in **date order** with the **running balance on the account's normal
  side**, the movement totals, and the closing balance. Closing entries are included and marked, so an
  income account that reads zero explains why instead of hiding the close.
- `ledger.account_ledgers(j)` â€” every chart account, in chart order, including accounts with no
  postings (an empty account is information).
- `report.t_account(lg)` / `report.t_accounts(...)` â€” deterministic plain-text rendering, same
  conventions as the other statement exports (fixed width, parentheses for negatives). It renders the
  numbers it is given and recomputes nothing.
- `accounts.build` now emits `ledgers` (serialised) and `t_accounts_export` (rendered text per account)
  in the appendix, so the workbench can show a T-account without ever computing a balance itself.

**Two design decisions worth recording.**

1. The running balance is computed **in the core, not the page**, because it is a reading of the account
   rather than a presentation choice. A design-layer balance would be a derived business number, which
   Â§1A forbids.
2. The **frozen contract was deliberately not touched.** `management_accounts` is T2 with eleven
   `test_names` pinned in `tests/fixtures/frozen_contract.json`; adding a twelfth invariant to
   `check_invariants` would have forced a fixture change for no gain. The footing property is instead
   proven by `tests/test_t_account_ledger.py`, which rebuilds the journal and compares every account's
   debit and credit totals against `j.balances()`.

**A bug I wrote and caught.** The first version read `l.opening` (a line attribute that does not exist)
instead of `e.opening`, and started the running balance at zero rather than at the opening balance. Both
were caught by the new tests before any commit.

**Verified.** 769 tests OK, including 8 new ones:
every account foots to the trial balance; opening + movement = closing; the running balance recomputes
from its own rows; postings read chronologically; the close is visible and zeroes an income account; a
contra asset stays credit-normal and still reduces its section; an unposted account is present and
empty; and a trap test showing a ledger that omits the opening balance would **not** foot â€” so the
footing assertion can actually fail.

**Still not fixed, carried forward:** `multi_product_breakeven` does not flag a negative-contribution
product (needs an unfreeze because it changes `test_names`).

**No build number** â€” no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 â€” [computation] The server told browsers to cache a page it recomputes every time

**Found while verifying the catalogue fix.** After correcting the catalogue and restarting
the server, the browser still rendered the old statuses. The API was already right on the wire;
the browser had reused its cached copy. `src/bp/server.py` sent no caching header at all â€”
no `Cache-Control`, no `Pragma` â€” although CHANGELOG 0.69 states *"The page now declares
`Cache-Control: no-store` / `Pragma: no-cache`"*. That sentence was never true in the code.

**Why it matters beyond one stale row.** The build pill is the only "which page am I looking at"
signal, and it is useless until the page has actually reloaded. A cached page with an old pill
and old data is indistinguishable from a current one. This is the same failure mode as the
wrong-folder-on-8021 confusion: the owner sees something that is not what the code says.

**Did.** `_send` â€” the single exit point for every response â€” now adds `Cache-Control: no-store`
and `Pragma: no-cache` alongside the existing `X-Content-Type-Options`. Added
`tests/test_cache_headers.py` (2 tests) which starts the real `ThreadingHTTPServer` and asserts
both headers on the workbench document and on `/api/health`. The test fails on the old code:
the headers were observably absent from the live server before this change.

**Verified.** 761 tests OK. Live server confirmed sending `no-store` on both routes.

**Still no build number, for the same reason as the entry below:** no served markup changed and
the pill is pinned at `v0.73` by `tests/test_product_subjects.py`.

## 2026-10-27 â€” [computation] The catalogue told students that built accounting methods did not exist

**Ask.** Phase 0 of the accounting build: "correct those that are erroneous" before adding
anything. The owner had seen the Accounting page say *"Management accounting â€” not implemented"*
while `management_accounts` was running on that same page.

**Found.** The subject pages derive every record's `implementation_status` from
`METHOD_LINK_RULES` in `src/bp/registry.py` â€” a six-rule table that matches a record's *summary*
and returns its linked methods plus a hand-written note. Only six rules existed, all written
before IRR, discounted payback, ratio analysis, the valuation family, the ledger engagement, unit
economics and most of the statistics library shipped. Everything unmatched falls through to
`"not implemented"`. Consequences verified against the live API:

- `QNT-FIN-01` claimed IRR and payback were missing â€” both are T1 methods
- `QNT-FIN-02` claimed "break-even only" â€” `multi_product_breakeven` also exists
- `QNT-FIN-03`, `QNT-FIN-04`, `QNT-FIN-05`, `QNT-FIN-06` each read **"not implemented"** while
  `ratio_analysis`, `wacc`/`dcf_valuation`/`equity_bridge`, `management_accounts` and
  `unit_economics` respectively run
- `QNT-STA-03` claimed chi-square and ANOVA were missing; `QNT-STA-04` claimed logistic
  regression was missing â€” all present

Two of 36 methods were claimed by the catalogue; the other 34 were reachable only through the
Calculator.

**Did.** Rewrote `METHOD_LINK_RULES` so each rule matches on its record's summary prefix and
carries an accurate note and the real method list, then regenerated the committed slice with
`scripts/generate_subjects.py` â€” the documented single source of truth. `QNT-FIN-07` (pricing and
demand) stays `not implemented` because it genuinely is. `currency_convert` was deliberately **not**
claimed against `QNT-FIN-04`, whose summary does not mention currency: fixing an underclaim must
not create an overclaim.

Added `tests/test_catalogue_truth.py` (6 tests): every linked method id resolves; no record both
links methods and says "not implemented"; the accounting, finance and regression records claim the
methods the engine registers; every compute tool resolves to a real preset. Updated the test count
in `HOME.md`, `HANDOFF.md` and `CONTRIBUTORS.md` from 753 to 759.

**Verified.** 759 tests OK. Corrected rows confirmed from the live API
(`/api/cases/subjects/accounting`), not from the module.

**Not fixed, recorded as findings:**

1. `multi_product_breakeven` accepts a product with negative contribution and reports a
   break-even without flagging that one product loses money on every unit. The arithmetic is
   right under the declared mix; the absence of a warning is the gap. Adding a check would change
   `test_names` and needs an unfreeze.
2. `server.py` sends **no** `Cache-Control`/`Pragma` header, although CHANGELOG 0.69 claims it
   does. A browser served a stale catalogue during this very session until the server restarted.
   Next increment.

**No build number.** This changes API data, not page markup, and `tests/test_product_subjects.py`
pins the served pill at `v0.73`. Bumping the changelog without changing the pill would make the
documents disagree with the page the owner checks.

**Lane note.** The correction touches `src/bp/product/subjects.py`, which is the design owner's
file, because the wrong text was a *factual claim about the engine* â€” computation-owned content
(Â§1A). It was regenerated from the core rule rather than hand-edited, and the guard test lives in
`tests/`. If the design owner disagrees with that call, the revert is local and this entry records
why it was made.

## 2026-10-27 â€” [product] Clean Home: logo + unchanged slogan + chat box only (build 0.70)

**Ask:** the owner rejected the 0.69 Home as regressed and over-filled: it should be clean and contain only the chat box and its logo; the side rail is already fine; do not change the slogan; do not act without permission. Confirmed scope: remove the dropdowns too; the chat box is only the text area and up arrow.

**Did:** removed from Home the extra sentence under the slogan, the preset/method/currency selects, the preset chips, the Examples card, "Your cases", "Or choose a subject", the "Two ways in" note and the Enter hint. Kept the logo, wordmark, the tagline exactly as written, the text area and the up-arrow. Side rail, Calculator, Status pill, top bar, subject pages and backend untouched. Guarded the absence of the removed elements; guarded `startFromHome` against the removed selects (it now toasts to the rail/Calculator because Home has no method control).

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.70), `DECISIONS.md` (B-094), `DISCUSSION_NOTEBOOK.md` (entry + Status line), `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 753 tests OK; `node --check`; `<section>` counts equal; no Home markup for `preset`/`method`/`currency`/`data-example`/`hero-sub`/case or subject shelves. No computation, API, side rail or business number changed.

**Open/next:** the Home arrow cannot launch without a method; method choice lives in the subject rail and Calculator. `loadHomeShelf` is now unused. If the slogan meant the sentence under the tagline, it must be restored verbatim on request.

## 2026-10-27 â€” [product] Static-first expandable subject rail, centred chat, up-arrow Enter control (build 0.68)

**Ask:** another agent's served copy lost the subject rail; re-implement it, ensure the rail is expandable, centre the big Home chatbox with even side space without changing its length, and move Run to the right as an up arrow suggesting Enter.

**Did:** wrote the ten subject links and icons as static markup in `#railsubjects` so the rail renders before `/api/cases/subjects` and survives its absence; the live call still replaces them with full labels/counts, and a failure now appends a note instead of wiping the list. Reworked the rail toggle (hamburger collapsed, chevron + "Collapse" open, `aria-expanded`, label, title, persisted state). Added `main{margin:0 auto}` so the action box centres in the content column at unchanged width. Moved `#run` from the left of the action row to the right and replaced it with a circular up-arrow button; added Enter-to-start / Shift+Enter-newline and an inline hint. Added three static-markup presence guards in `tests/test_product_subjects.py`.

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.68), `DECISIONS.md` (B-093), `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** 753 tests OK; `node --check` on the extracted page script; `<section>` counts equal; the static rail has all ten subject ids; the panels removed in 0.67 are still absent. No computation, frozen module, fixture, API route or business number changed.

**Open/next:** static labels are shorter than the live ones and only the ten known ids are guarded. The static rail is navigation, not capability: with an old backend the subject page still 404s. The chat centring is within the content column (the rail offsets the visual centre by ~32px). No browser test exists.

## 2026-10-27 â€” [product] Catalogue and Assistant panels deleted from the UI (build 0.67)

**Ask:** "whats the use of catalogue, assistant and status? are they needed? or okay to be deleted?" followed by **"go"** for the recommendation: delete Catalogue and Assistant from the UI, keep Status behind the health pill, keep all backend routes and tests.

**Did:** removed `panel-frames` and `panel-assistant` markup, `RENDERERS.frames`, `searchFrameworks`, `loadTemplate`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, the subject-page "Browse the full method catalogue" button, the drawer's Assistant tab, the `/api/assist/config` boot call, the `state.assist` field and the unused `.dtab` CSS. The chat button now opens a single Help & about drawer; the health pill still opens Status. Kept `/api/frameworks`, `/api/frameworks/{id}`, `/api/templates`, `/api/assist` and their tests; subject catalogue-only tables, worksheet tiles and the Calculator are unchanged.

**Files:** `web/index.html`, docs: `CHANGELOG.md` (0.67), `DECISIONS.md` (B-092), `BACKEND_CONTRACT.md` Â§6, `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 750 tests OK; `node --check` on the extracted page script; zero remaining references to `panel-frames`, `panel-assistant`, `RENDERERS.frames`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, `dtab`, `state.assist` or `api/assist`; `<section>` open/close counts equal. Three UI-presence assertions in `test_assist`, `test_framework_flow` and `test_templates` were retargeted to the new surface (no backend test or assertion changed). No frozen module, fixture, route or business number changed.

**Open/next:** the backend assistant and framework/template routes are now reachable only by direct API/test call. If a provider is configured later, the assistant UI must be re-surfaced **and fixed** (use `critique`, supply facts/alternatives, send `consent`). Status remains a dev-facing panel behind the pill.

## 2026-10-27 â€” [product] Subject rail, capability tiles and Home reconciliation (build 0.66)

**Ask:** the owner's rail instruction â€” enumerate the subjects (Accounting, Finance, Economics, Management, ..., now Entrepreneurship) with icons; clicking one shows its capabilities in the centre as clickable tiles; reconcile with Home chat; delete Case, Catalogue, Assistant and Status from the rail and keep Calculator at the bottom.

**Did:** (1) `bp.product.subjects`: added Entrepreneurship as a combination shelf (8 frozen compute tools, the existing STR-18 SWOT worksheet, 5 catalogue-only canvas/innovation records) and a unique presentation `icon` key on all 10 subjects, exposed by the gallery and detail routes; added an Entrepreneurship group to the Calculator groups. (2) `web/index.html`: rail rebuilt as Home + the 10 subjects (icon, label, native tooltip, aria-current on the active subject) + Calculator pinned at the foot; the Case/Catalogue/Assistant/Status rail items removed, with their existing panels kept reachable from Home/subject pages, the subject catalogue button, the chat drawer and the health pill. (3) A subject click renders a capability **tile grid** (one tile per frozen method or worksheet, with description, preset/typed-input footer and kind icon) instead of a vertical row list; stored cases and the catalogue-only table follow. (4) Home-chat reconciliation: copy states the two routes, the same subject cards remain under the box, and every subject page links to the chat. (5) Hash routing now supports `#/subject/<id>`. (6) Two guard tests: rail order/unique icons/icon round-trip, and Entrepreneurship's tool/worksheet/canvas composition.

**Files:** `src/bp/product/subjects.py`, `web/index.html`, `tests/test_product_subjects.py`, `tests/test_product_server.py`, docs: `CHANGELOG.md` (0.66), `DECISIONS.md` (B-091), `BACKEND_CONTRACT.md` Â§6, `DISCUSSION_NOTEBOOK.md` (dated entry + Status line), `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** full suite **750 tests OK**; `node --check` on the extracted page script; a live server smoke test returned the 10-subject gallery with icons, the Entrepreneurship page (8 tools, 1 worksheet, 5 catalogue records), the 8 Calculator groups and HTTP 200 for the page. No frozen module, frozen fixture, existing route contract or business number changed.

**Open/next:** the same open items as build 0.65 (C1 multi-run cases, per-subject workbenches, free-form arithmetic, owner decisions in notebook section J). A browser-level UI test is still absent; the rail/tile checks are catalogue guards plus a JS syntax check.

## 2026-10-26 â€” [product] Subject-first navigation and the Calculator launcher (build 0.65)

**Ask:** "read discussion notebook and implement it" â€” the notebook's build brief (section G, Increment 1) plus the owner's rail Calculator instruction (section N).

**Did:** implemented the first increment, not the whole four-increment plan. **Product catalogue:** new `src/bp/product/subjects.py` is a committed, testable index of 9 subjects (Accounting, Finance, Economics, Management & strategy, Operations, Supply chain & logistics, Marketing & customers, People & organisation, Research & statistics as a cross-cutting shelf). Each subject maps to the frozen preset ids / method ids it can actually launch, the three existing T4 worksheets (STR-01 Five Forces, STR-07 and STR-18 SWOT) as structure-only, and the registry records it can only read or structure with the registry's own `implementation_status` wording. A generation helper (`scripts/generate_subjects.py`) writes the registry slice; `tests/test_product_subjects.py` re-reads the frozen fixture and registry as data and fails on any drift. **Routes (additive, `/api/cases` only):** `GET /api/cases/subjects`, `GET /api/cases/subjects/{id}`, `GET /api/cases/calculator`, and `GET /api/cases?subject=<id>` (stored cases filtered by the methods the subject can launch). **Calculator:** seven business-function groups (Finance, Accounting, Statistics, Economics, Operations, Marketing, People) built from the same compute tools; it arranges inputs and calls the existing create-then-confirm pipeline. No client-side formula, no product-layer arithmetic, no new arithmetic path; free-form expressions are named as unsupported rather than silently absent. **Served UI (`web/index.html`):** seven-item rail Home | Subjects | Calculator | Case | Catalogue | Assistant | Status; Home is a case shelf (stored cases + subject cards + the existing objective box); subject pages show tools, worksheets, stored cases and an explicit catalogue-only table; a searchable Calculator; the "Draft work plan" destination is replaced by a one-button tool screen ("Apply figures and calculate" performs the same two calls), while the phrase survives honestly in the recorded-metadata panel the frozen test asserts; `framework_suggestions` is finally rendered (informational only); the hero sub-line is no longer "To be supplied"; a malformed `</section` in the served HTML was fixed. **Not implemented, deliberately:** C1 `bp-case/2` multi-run cases, the Accounting/Finance workbenches, and the remaining subject workbenches (Increments 2â€“4); the Home copy says a run is still saved as a one-run case.

**Files:** `src/bp/product/subjects.py` (new), `scripts/generate_subjects.py` (new), `src/bp/product/api.py` (imports, subject/calculator routes, subject filter), `tests/test_product_subjects.py` (new, 14 tests), `tests/test_product_server.py` (one HTTP route test), `web/index.html`, `docs/DISCUSSION_NOTEBOOK.md` (new dated entry + brief Status line), `docs/CHANGELOG.md` (0.65), `docs/DECISIONS.md` (B-090), `docs/BACKEND_CONTRACT.md` Â§6 + test count, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, this entry.

**Verified:** full suite **748 tests OK**; `node --check` on the extracted page script; the subject drift guard confirms every launch id exists in the frozen fixture and every catalogue id in the registry; the product boundary test still shows no core import and no product-layer arithmetic. No frozen module, frozen fixture or existing test was edited.

**Commit:** `this commit`.

**Open/next:** the owner decisions in notebook section J remain open, especially (2) whether one case should hold many subject analyses (the C1 decision) and (4)/(5) whether the 131 catalogue-only records should stay visible and whether B-028 should add worksheets. Increment 2 (C1), the Accounting workbench and the Finance/DCF sheet are the next build steps, not part of this increment.

---


## 2026-10-21 â€” [documentation] Website UI brief for the design owner (plan mode)

**Ask:** write the instruction for MiniMax/OpenCode to build the website: A1.jpg as inspiration, the owner's logo as the site logo, colored feature icons on the left rail, remove the API/Enterprise top-right items, delete the "Trusted by 11 million" block and the university row, retain the circular chat button restyled to the brand, UI sans-serif except generated document text (Times New Roman), and **plan mode first** so MiniMax can ask clarifying questions before building.
**Did:** wrote `docs/UI_BRIEF.md` as the authoritative instruction: assets and where they live (logo copied into `web/assets/`, A1 as inspiration only, never shipped); the A1 structure to imitate (fixed left icon rail, centered hero with logo, large action box with an inner controls row, quick-action chips, floating chat button) and the exact removals (top-right API/Enterprise/Pricing/Login/Sign-up; the trusted-by block and university logos; no invented social proof); the nine real features for the rail mapped to the actual API routes (Home/New analysis, Cases, Data, References, Deliverables, Accounts, Frameworks & templates, Assistant & method info, Status); typography (sans-serif system stack for UI; Times New Roman for generated document text, with the note that `export.py` is a computation-owner file and must not be edited); the non-negotiables (display API values verbatim, no client-side computation, never hide caveats/honesty/limitations/tier labels, no invented content, offline/no CDNs, `web/**` write scope, backend needs requested rather than invented) and the frozen workbench strings the suite asserts. The brief's first deliverable is a **plan** (IA, screen map, wireframes, design tokens sampled from the logo, component inventory, responsive/accessibility, phased build, test-impact statement, and questions for the owner) with no code until approved.
**Files:** `docs/UI_BRIEF.md` (new), `docs/HOME.md` (spine row + build digit), `docs/HANDOFF.md` (build digit), `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **733 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax replies in plan mode with its plan/questions; the owner reviews; after approval the UI is built in `web/**` on its own branch. Nothing UI has been started by the computation lane.

---

## 2026-10-21 â€” [computation] Product slice 2c: charts, spreadsheets and business graphics (B-089)

**Ask:** "do 1" â€” the last backend item: the graphics/spreadsheets addition (B-087), then stop before the UI.
**Did:** three new product modules, all deterministic and stdlib-only, with **no model in the rendering path**. **`charts.py`**: a declarative `bp-chart/1` spec renders SVG for bar, line, stacked bar, waterfall, pie, sparkline and table; every series names a stored artifact (metric or id), a missing artifact / no recorded value / non-numeric value is refused with a reason, the spec's text fields (title, labels, axis labels, note) **may not contain digits** so only stored value strings can appear, and geometry scaling never alters the strings; same bundle + spec â†’ byte-identical SVG. **`spreadsheets.py`**: CSV of the artifact table (LF endings) and a SpreadsheetML 2003 workbook with Case/Artifacts/Report sheets where every cell is a string (so `50.00` never becomes `50.0`). **`diagrams.py`**: structure-only (T4) SVG templates â€” process, 2x2 matrix, pyramid, funnel, tree â€” from owner-supplied digit-free labels; nothing is scored or ranked. `export_html` now embeds charts/diagrams; routes `POST /api/cases/{id}/render` (SVG preview) and `POST /api/cases/{id}/export` (`csv` / `spreadsheetml` / `html`).
**Files:** `src/bp/product/charts.py`, `.spreadsheets.py`, `.diagrams.py` (new), `src/bp/product/export.py`, `src/bp/product/api.py`, `tests/test_product_charts.py`, `tests/test_product_diagrams.py`, `tests/test_product_spreadsheets.py` (new), `tests/test_product_routes.py` (extended), docs (B-089, CHANGELOG 0.63, BACKEND_CONTRACT Â§6, PRODUCT_BACKEND_PLAN 2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **733 tests OK** including the frozen-contract and docs-state guards; SVG validated as well-formed XML, determinism and number-fidelity tested (a chart cannot print a number that is not a stored value), spreadsheets checked cell-by-cell as strings, and the render/export routes exercised through the dispatch.
**Commit:** `this commit`.
**Status:** the backend product sequence is **complete** (2a, 2b, 2c). Per the owner's instruction I am **stopping before any UI/homepage/interface work** and waiting for the special UI instructions. Remaining non-backend items are decision-gated (D3 disclosure, REW R1â€“R10/B-082, tax B-052, ledger B-032, templates B-028, reviewers B-005, frontier stats B-075).

---

## 2026-10-21 â€” [computation] Product slice 2b: ops surface and the local launcher (B-088)

**Ask:** continue the backend sequence, and the owner asked "will you also build the server? i notice there is no server yet". Answer: the server already exists (`src/bp/server.py`, stdlib HTTP, `python -m bp.server`, serving the workbench and API, wired to the product routes since B-085); what was missing was the operational/deployment surface, which is this slice.
**Did:** new `src/bp/product/ops.py` â€” `health()` (case-store counts, state dir, request-log status, checks, ok/degraded), `log_request()` (JSONL: timestamp, method, query-free path, status, duration only; never a body/title/input/report; `BP_REQUEST_LOG=""` disables; best-effort), `backup()` (zip of the case store's JSON documents + manifest + SHA-256; state/logs/prior archives excluded), `restore()` (zip-slip/drive/non-JSON refusal, staging then copy, refuses overwrite unless asked), `list_backups()`. Additive core instrumentation in `server.py`: a timing hook feeding the request log, `GET /api/health` (merging sandbox/model flags), and startup lines for URL/health/log â€” no existing route, output or claim changed (frozen guard still passes). New `scripts/serve.py` launcher as the single local run path: `--port`, `--host`, `--no-sandbox`, and `--check` dry-run printing the resolved config; it adds `src` to `sys.path` so a clean checkout needs no install. Product routes `POST /api/cases/backup`, `POST /api/cases/restore`, `GET /api/cases/backups`.
**Files:** `src/bp/product/ops.py` (new), `src/bp/product/api.py`, `src/bp/server.py` (additive instrumentation), `scripts/serve.py` (new), `tests/test_product_ops.py`, `tests/test_launcher.py`, `tests/test_product_server.py` (extended), docs (B-088, CHANGELOG 0.62, BACKEND_CONTRACT Â§6, PRODUCT_BACKEND_PLAN 2b, README, HOME, HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **714 tests OK** (frozen-contract and docs-state guards included); health/backup/restore and the launcher were exercised over a real HTTP server; the request-log test asserts no report text, input body or title reaches the log.
**Commit:** `this commit`.
**Open/next:** Phase 2c (deterministic charts/SpreadsheetML/diagram templates, B-087) is the last backend task before the UI; after it I stop, per the owner's instruction to hold the interface until special instructions.

---

## 2026-10-21 â€” [computation] Product slice 2a: case versions, comparison and sign-off (B-086)

**Ask:** "continue on the sequence of backend product building. do it yourself the job you are delegating because you will not accept cline's work and still edit it." Plus the important addition about spreadsheets/charts (recorded as B-087 and planned as Phase 2c; nothing in this slice draws graphics).
**Did:** implemented slice 2a directly, in the product layer, with no frozen module touched. **`versions.py`** â€” an immutable version chain per case (`<BP_CASES_DIR>/<id>/vNNN.json`), a canonical-JSON `bundle_hash` recorded in each envelope, legacy flat cases adopted as version 1, corrupt/tampered versions refused on read, delete removes the chain. **`compare.py`** â€” Option-A comparison over stored versions: same-method rule enforced, artifact rows aligned by metric, stored values copied verbatim, a metric absent from a version reported as "not computed for this version", differences in `spec_hash`/`outputs_hash`/`method_version` listed, a disclosure naming each compared version's `bundle_hash`/`outputs_hash`, deterministic stdlib HTML rendering. **`signoff.py`** â€” append-only sign-off records carrying the owner-approved Option-A signature text, reviewer name/role/scope/decision, the signed version hashes and a tamper-evident integrity check. **Routes** added to the pure dispatch (already reachable through the server delegation, so no core edit): `GET/POST /api/cases/{id}/versions`, `GET /api/cases/{id}/versions/{n}`, `GET /api/cases/{id}/compare`, `POST/GET /api/cases/{id}/signoff`. Tests: `tests/test_product_versions.py`, `tests/test_product_compare.py`, `tests/test_product_signoff.py`, `tests/test_product_routes.py` plus an HTTP extension in `tests/test_product_server.py` (22 new tests).
**Files:** `src/bp/product/versions.py`, `src/bp/product/compare.py`, `src/bp/product/signoff.py`, `src/bp/product/api.py`, new product tests, docs (B-086/B-087, CHANGELOG 0.61, BACKEND_CONTRACT Â§6, PRODUCT_BACKEND_PLAN 2a/2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **702 tests OK** including the frozen-contract and docs-state guards; the version chain, comparison rules, sign-off wording and tamper cases are all tested; the routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** Phase 2b (ops/observability, offline packaging) then Phase 2c (deterministic charts/SpreadsheetML, B-087), then **stop before the UI** per the owner's instruction.

---

## 2026-10-21 â€” [review] Product slice 1 reviewed, wired in, and two defects fixed (B-085)

**Delivered by:** MiniMax/OpenCode on branch `opencode/product-slice-1`, commit `b411083`: new `src/bp/product/**` (case store, route dispatch, stdlib HTML export) + 51 product tests + the Â§6 rows and count/version/changelog/worklog docs.
**Review verdict: accepted with fixes.** The design is right: a local case store that treats the frozen bundle as an opaque document (atomic write via temp+rename+fsync, 12-hex id validation, path-traversal refusal, corrupt-bundle refusal, opaque load), a pure `handle(method, path, body) -> (status, payload)` dispatcher with no server edit, and an HTML export that copies the stored report and artifact values. The product tests set/restore `BP_CASES_DIR` properly and the package imports only the standard library.
**Defects found and fixed in this integration commit:**
1. **Tautological check.** `test_the_product_layer_computes_no_number` compared a set with itself (`recorded` and `shown` were the same expression), so it could never fail. Replaced with a real check: the numbers returned by the dispatch and shown by the HTML export are compared against the numbers in the bundle actually written to the store, so an invented/rounded/recomputed value now fails.
2. **Double-encoded text in four factual docs.** The slice rewrote CHANGELOG/HANDOFF/HOME/WORKLOG with cp1252â†’UTF-8 mojibake (e.g. `Ã¢â‚¬â€` for an em dash, `Ã‚Â§` for a section sign). Repaired to proper UTF-8; this is why the review diff looked much larger than the intended count/version edits.
3. **Registry portability bug (pre-existing, found because the slice was tested in a fresh worktree).** `catalogue_import` hashed raw catalogue bytes, and git's Windows checkout (`core.autocrlf=true`) turns committed LF into CRLF, so a fresh worktree hashed different bytes and `test_shipped_registry_equals_fresh_import` failed there while passing in the main checkout. The hash is now computed over LF-normalised bytes and the shipped registry was regenerated (records unchanged); a new test imports a CRLF copy and asserts the same hash.
**Wiring (the core edit the plan delegated to me):** added `from .product import api as product_api`, a GET/POST branch and a new `do_DELETE` in `src/bp/server.py`, all delegating to the product dispatcher; the product POST branch parses the body without `parse_float=Decimal` so bundles round-trip exactly. The frozen route fixture is unchanged â€” the product surface is tracked in `BACKEND_CONTRACT.md` Â§6. New `tests/test_product_server.py` (3 HTTP tests) covers list/post/get/delete, 404/422 refusals, and that existing routes are unchanged.
**Files:** `src/bp/server.py`, `src/bp/catalogue_import.py`, `src/bp/data/registry_v0_2.json`, `tests/test_product_boundary.py` (fixed check), `tests/test_product_server.py` (new), `tests/test_registry.py` (new EOL test), docs (B-085, CHANGELOG 0.60, BACKEND_CONTRACT Â§6, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **680 tests OK** including the frozen-contract and docs-state guards; the four repaired docs render correctly; the wired routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** delegate slice 2 (reviewer sign-off record with the Option-A wording, multi-period comparatives + case versions per Option A, ops/observability, offline packaging) to MiniMax; DOCX/XLSX export remains a later slice behind a declared product dependency.

---

## 2026-10-21 â€” [product] Product slice 1: durable case store, case routes, HTML export

**Ask:** owner instruction "let minimax do the product backend" (B-080) and "let's do your recommended sequence of finishing the backend product before finally doing the UI" (B-081): the first product slice over the frozen core (B-079), in the design owner's lane.
**Did:** added the new product package `src/bp/product/` â€” a local durable case store (one JSON bundle per case under `BP_CASES_DIR`, default `cases/`; atomic writes; ids refused unless 12 lowercase hex characters; path traversal refused; a corrupt bundle refuses to load with a clear message), a pure additive route dispatch for `GET /api/cases`, `POST /api/cases`, `GET /api/cases/{id}` and `DELETE /api/cases/{id}` (no `server.py` edit â€” the computation owner wires it after review), and a self-contained HTML export of a stored bundle with the delivered report text and the artifact table copied exactly. The bundle is opaque: the product layer stores, lists, copies and renders what was recorded, imports nothing from the frozen core, and computes no business number.
**Files:** `src/bp/product/__init__.py`, `src/bp/product/cases.py`, `src/bp/product/api.py`, `src/bp/product/export.py` (new), `tests/product_fixtures.py`, `tests/test_product_cases.py`, `tests/test_product_api.py`, `tests/test_product_export.py`, `tests/test_product_boundary.py` (new), `docs/BACKEND_CONTRACT.md` (Â§6 rows only), `docs/CHANGELOG.md` (0.59), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md` (count/version digits only). No frozen core module, test, fixture or factual document was edited.
**Verified:** full suite (frozen-contract guard + docs-state guard + 51 product tests) **676 tests OK**; the product boundary is checked by a test that parses the product sources and fails if they import anything but the standard library, import or shadow a frozen core module, reference a third-party package, or show a number that was not recorded.
**Commit:** `this commit`.
**Open/next:** the route dispatch still needs the computation owner to wire it into `src/bp/server.py` (an additive route table; the frozen route surface is unchanged until they do); the DOCX/XLSX export needs dependencies that are not in this slice, so it is not in this commit.

---

## 2026-10-21 â€” [computation] Sign-off wording and multi-period Option A resolved (B-084)

**Ask:** owner answered D4 and the multi-period question: **"a."** (sign-off Option A) and **"option a"** (multi-period Option A); also noted the workspace-root `A1.jpg` is a website reference for later and the logo is to be left alone.
**Did:** recorded both choices as B-084 and updated the plan: **D4 = Option A** â€” the stored signature text is now fixed and quoted in Phase 2 ("I reviewed the named case bundle and its disclosed limitations. This signature records that review; it does not assert that the inputs are true or that the analysis is correct."). **Multi-period comparatives and case versioning = Option A** â€” product-layer, no unfreeze, moved from the unfreeze queue (Phase 3) into the delegated Phase 2 slice: one frozen session per period, immutable case versions (monotonic version, spec/output hashes, method id+version), side-by-side comparison of stored bundles under declared comparability rules, missing periods shown as "not computed" and never filled, every displayed number byte-identical to its stored bundle, no arithmetic in the product layer. Phase 3 now holds only PDF/OCR ingestion and any core-lane export. Recorded `A1.jpg` as the owner's UI-phase website reference (outside the repo, not committed; logo untouched).
**Files:** `docs/DECISIONS.md` (B-084; B-083's D4 status updated), `docs/PRODUCT_BACKEND_PLAN.md` (Phase 0/2/3/5 + definition of done), `docs/BACKEND_CONTRACT.md` (Â§6 planned surface), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax's slice 1 (case store + dispatch + HTML export) to review; then delegate slice 2 (sign-off record, multi-period Option A comparison, ops/packaging). D3 disclosure remains deferred by choice.

---

## 2026-10-21 â€” [computation] Phase-0 answers, slice-1 rescope and the multi-period proposal (B-083)

**Ask:** owner answered the plan's four Phase-0 questions and said "okay do the things while waiting for minimax".
**Did:** recorded the answers as B-083 and amended the plan: **D1 accepted** (local single-user v1, to be improved after it is seen working), **D2 accepted** (cases kept until the owner deletes them, no outbound transfer, model assistance off by default), **D3 deferred** â€” the AI-use disclosure export is removed from slice 1 and returns later as its own separately-decided slice, **D4 open** â€” explanation requested; sign-off stays in Phase 2 and its record schema does not depend on the wording. Rescoped slice 1 accordingly: local case store + additive route dispatch + **stdlib HTML export** of the delivered report verbatim (no disclosure, no third-party dependency; DOCX/XLSX deferred behind a declared product-layer dependency). Wrote `docs/proposals/MULTI_PERIOD_VERSIONING.md`: multi-period comparatives and case versioning split into **Option A** (product layer, no unfreeze â€” one existing session per period stored as an immutable case version, compared side by side under declared comparability rules, recommendation) and **Option B** (core multi-period delivery: single spec with N periods, per-period artifacts and a deterministic in-delivery diff â€” a genuine unfreeze), with acceptance criteria and the owner questions.
**Files:** `docs/DECISIONS.md` (B-083), `docs/PRODUCT_BACKEND_PLAN.md`, `docs/BACKEND_CONTRACT.md` (Â§6 planned surface), `docs/proposals/MULTI_PERIOD_VERSIONING.md` (new), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** D4 wording choice (owner); A-vs-B choice for multi-period (owner); MiniMax's slice 1 to review â€” the delegation addendum says item 3 (disclosure) is deferred and must not be committed. My next computation-owner work while waiting: review slice 1 and wire the product dispatch into the server once it passes.

---

## 2026-10-21 â€” [computation] REW manual inventory refresh (v0.4, from the review queue)

**Ask:** queue item from the decision-briefs review (appendix B items 2-4): the ratified REW manual's "what exists in code today" table had gone stale.
**Did:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` Â§13 refreshed to match the code and bumped to v0.4: the durable append-only retrieval log with fail-closed writes and `reverify` (B-058), CrossrefÃ¢â€ â€™OpenAlex failover with recorded attempts and the manual drift sweep (B-064), the full verified-method library and applied methods, CSV/TSV + XLSX ingestion with sheet selection and a declared merged-cell policy (B-065/B-071/B-076), APA/Harvard citation formatting (B-059), and the AI-use disclosure export listed as a planned product-backend item (B-081). Â§16 change log records the refresh. The stage list, checkpoints, screening log and manuscript assembly remain **not built**, and R1-R10 remain proposals â€” the refresh changes only the factual inventory, not any status claim.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md`, `docs/proposals/DECISION_BRIEFS.md` (appendix B items marked fixed), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to the plan's D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 product slice. The two register-hygiene items from the briefs were fixed in this same increment: the duplicate B-031 row is marked SUPERSEDED, and the R1-R10 ratification now has the open decision row **B-082** (the row tracks it; the owner still decides it).

---

## 2026-10-21 â€” [computation] Product-backend sequence and delegation boundary (B-081)

**Ask:** "let's do your recommended sequence of finishing the backend product before finally doing the UI. delegate some work to minimax when you dont have to do it."
**Did:** wrote the sequence down as a working plan instead of ad-hoc instructions, and fixed the file-level boundary that lets both owners work in the same repo in parallel. New `docs/PRODUCT_BACKEND_PLAN.md`: **Phase 0** four owner questions (deployment model, case retention/privacy, disclosure audience, sign-off semantics) each with a slice-1-safe default; **Phase 1** delegated to MiniMax - local durable case store (`src/bp/product/**` as new files + additive `/api/cases` routes, opaque JSON bundles with atomic writes, export/restore/delete), AI-use disclosure export from recorded metadata, DOCX/XLSX export of the delivered report verbatim; **Phase 2** delegated - reviewer sign-off record, ops/observability counters (no case content in logs), offline packaging; **Phase 3** computation-owner unfreeze requests, ordered (multi-period comparatives/versioning, then PDF/OCR + SPSS ingestion, core-lane exports only if the product layer cannot host them); **Phase 4** owner-gated tracks (REW ratification, retrieval sources, tax/ledger/templates/reviewers, real-case evaluation); **Phase 5** the UI only after 1-2 are accepted. Boundary rules recorded in B-081 and in `BACKEND_CONTRACT.md` Â§4: product code and product tests are new files (`src/bp/product/**`, `tests/test_product_*.py`); per increment MiniMax may update only count/version digits in HOME/HANDOFF/CONTRIBUTORS plus one CHANGELOG and one WORKLOG `[product]` entry; the frozen core, existing tests/fixtures, `DECISIONS.md` and claim wording stay untouched; both guards must pass.
**Files:** `docs/PRODUCT_BACKEND_PLAN.md` (new), `docs/BACKEND_CONTRACT.md` (Â§4/Â§6), `docs/DECISIONS.md` (B-081), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite (including the frozen-contract and docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 slice to review; the queued REW inventory refresh is the next computation-owner item.

---

## 2026-10-21 â€” [review] Decision briefs draft (MiniMax task 3), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/decision-briefs`, commit `566a6af`: `docs/proposals/DECISION_BRIEFS.md` (369 lines) with five briefs for the open owner decisions â€” B-005 reviewers, B-028 next templates, B-032 ledger engine, B-052 taxation, REW R1-R10 â€” each giving "what it blocks today" citations, the state of the code, options with costs, one clearly labelled MiniMax recommendation, plus an OPEN-items appendix and an appendix of contradictions it found between repository documents.
**Review:** substantive and useful. I verified 55 of its `path:line` citations against the code and docs: 37 exact at master, 13 shifted by under 30 lines (later increments added lines) and 5 shifted materially by B-077's new section â€” the cited content was found in every case and **no factual claim was contradicted**. Re-checked the contradiction list: #1 (two B-031 rows with different statuses), #2-#4 (the REW manual's inventory still says "no durable log yet" / Excel ingestion not built / statistics library without the later methods), #6 (ledger engine pre-empted by B-044) and #7 (R1-R10 has no decision id of its own) are real; #5 is a wording matter (B-052 is deferred but deliberately kept on the gate list); #8 (SOURCE_INVENTORY.md missing from the HOME spine) was real and is already fixed in `5023aa4`. Annotated the draft rather than rewriting it: a review-status block states the drafting base (`c06c61f`) and that line numbers are as-of that base, the B-066 citation is fixed, #8 is marked fixed, A12 is marked resolved. The stale REW inventory (#2-#4) is **queued** as a separate REW manual refresh (not done here â€” it edits the ratified manual). The file stays a **DRAFT** in `docs/proposals/`: it changes no decision, no number and no test.
**Files:** `docs/proposals/DECISION_BRIEFS.md` (new), `docs/HOME.md` (proposals row + version), `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite **625 tests OK**; docs links resolve; docs-state guard passes.
**Commit:** `this commit`.

---

## 2026-10-21 â€” [review] Docs-state sync guard (MiniMax task 1), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/docs-sync`, commit `264fee1` "Add docs-state sync tests": a 335-line `tests/test_docs_sync.py` (7 tests) plus count updates in HOME/HANDOFF/CONTRIBUTORS.
**Review:** the design is sound and the non-tautology requirement is met â€” every expectation is read from somewhere other than the document being checked (test count from a real `TestLoader().discover`, build from the newest CHANGELOG bullet, method ids from the imported `LIBRARY`, decision rows from `DECISIONS.md`, spine coverage from the `docs/*.md` listing), a missing pattern raises instead of silently skipping, and test 7 proves the parsers actually move when a document's own digits change. I re-ran the claimed proof independently: changing `**625 tests**` to `**626 tests**` in HOME made it fail with `docs/HOME.md says 626 tests, but the suite holds 625 tests`; restoring it went green.
**What I had to reconcile:** the branch was based before B-077/B-078/B-079, so its counts (622) and build (0.51) were stale; on merge the guard correctly failed on 618 vs 625 and on one genuine gap â€” `docs/SOURCE_INVENTORY.md` had no row in the HOME documentation spine (exactly the kind of drift the guard exists to catch). Fixed the spine row and bumped the docs to build **0.53** / **625 tests**; no assertion was weakened.
**Files:** `tests/test_docs_sync.py` (new), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 7 new tests; full suite **625 tests OK**; mutation proof above; docs links resolve.
**Commit:** `this commit`.

---

## 2026-10-21 â€” [computation] Freeze the core deterministic backend, delegate the product backend (B-079, B-080)

**Ask:** "freeze the core deterministic backend. let minimax do the product backend."
**Did:** two things. **(1) Freeze, with a guard.** New `docs/BACKEND_CONTRACT.md` states exactly what is frozen (stage/flow contract, spec + hash, the 36 method contracts â€” id, tier, metric, unit, `test_names` order, claim ceiling, category, input names â€” the 38 presets, the 12 API route families, the delivery shape and the verification invariants), the unfreeze policy (owner approval Ã¢â€ â€™ computation owner writes the B-decision, changes code + tests, updates the fixture in the same commit; bug fixes restoring declared behaviour need a trap test but no unfreeze) and the product-backend lane rules. The freeze is **enforced**, not just declared: `tests/test_frozen_contract.py` compares the live library/presets/server source against `tests/fixtures/frozen_contract.json` and fails with a message naming the freeze. **(2) Ownership.** Recorded the owner directive that the product backend is the design owner's lane (B-080) â€” additive routes/modules/storage/workflows over the frozen core, with the hard boundary that MiniMax may not edit frozen modules, tests, the fixture or factual docs, may not compute or adjust any number/threshold/rating/caveat/honesty notice/claim wording, and new endpoints must delegate computation to the frozen method library (never reimplement a formula). A needed core change is an unfreeze request handled by the computation owner under B-079.
**Files:** `tests/test_frozen_contract.py` (new), `tests/fixtures/frozen_contract.json` (new), `docs/BACKEND_CONTRACT.md` (new), `docs/DECISIONS.md` (B-079, B-080), `docs/CONTRIBUTORS.md` (Â§1B, stop-and-ask, fact map), `docs/HANDOFF.md`, `docs/HOME.md`, `README.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 3 new contract tests (methods/presets/routes match the frozen fixture; route count still 12); full suite **618 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** nothing computation-side is unblocked now â€” the lane is drained and frozen. The next phase is the design owner's product backend (B-080). Open owner decisions remain B-005 (reviewers), B-028 (templates), B-032 (ledger engine), B-052 (tax), REW R1â€“R10 (ratification), plus the frontier-model lane parked in B-075. MiniMax's docs-sync test and decision-brief drafts are still awaiting the owner's go for review/merge.

---

## 2026-10-21 â€” [computation] Equity bridge and mid-year DCF timing (B-078)

**Ask:** "go" for the valuation completion â€” the last unblocked computation item.
**Did:** two linked valuation pieces. New T2 **`equity_bridge`**: takes a declared enterprise value and subtracts declared net debt (debt minus cash), minority interest and preferred equity to report an equity value, plus a per-share value only when `shares_outstanding` is declared (no dilution, options or treasury method). Negative bridge components are refused as sign errors; a non-positive share count is refused; a **negative equity value is reported** because an EV that does not cover the declared claims is a real finding, not an input error. `dcf_valuation` gained a declared **mid-year timing convention** as an optional enum (`timing: end|mid`, default `end`): under `mid`, explicit flow t and the terminal value are discounted at exponent tÃ¢Ë†â€™0.5 / nÃ¢Ë†â€™0.5, so every flow is assumed mid-period; the default leaves every existing output, golden fixture and re-performance bundle unchanged. Five frozen checks for the bridge, a sixth check for the mid-year DCF path; presets `dcfmid`/`equitybridge`; sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-078, changelog 0.51, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 6 new tests â€” bridge arithmetic against an independent float route (equity value 1570939.14; net debt 150000; per-share 15.7093914), frozen checks declared and passing with and without a share count, refusals for negative components and bad share counts, pipeline delivery (9 artifacts, USD), mid-year DCF against an independent half-period loop, mid > end, invalid timing refused, presets and determinism. Full suite **615 tests OK**.
**Commit:** `this commit`.
**Open/next:** this drains the unblocked computation lane. What remains is owner-gated (open decisions B-005/B-028/B-032/B-052, REW R1â€“R10), frontier-model parked (B-075), or backend features that need a B-decision before build (AI-use disclosure export, reviewer workflow, case workspace/retention, versioning, model pinning/drift gate). The workbench UI is the design owner's domain (B-066) and the backend contract (routes, presets, JSON) is stable for it.

---

## 2026-10-21 â€” [computation] IRR and discounted payback (B-077)

**Ask:** "now what's next for you to do?" â€” with the docs-sync guardrail at MiniMax and the decision briefs also delegated, the next unblocked computation item was the gap map's capital-budgeting completion.
**Did:** two T1 methods, both on the `npv` timing convention (first cash flow at t=0, end-of-period after that). **`irr`**: the discount rate at which the declared cash flows have zero NPV, found by bracketing the NPV function over the declared range -99.99% to 1000% and bisecting (reference route: Newton-Raphson). A cash flow that never changes sign has no IRR and is refused; a cash flow with several sign changes can have several IRRs, so the method **refuses and lists the roots** rather than choosing one. **`discounted_payback`**: cumulative present values until the initial outlay is recovered, with the recovery interpolated linearly inside the recovering period; a positive first cash flow is refused and an outlay never recovered within the horizon blocks instead of reporting a number; `rate` is optional and defaults to 0 (ordinary payback). Both have declared-unit templates (IRR as a percentage), presets `irr`/`dpayback`, sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_investment.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-077, changelog 0.50, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests â€” IRR matches its independent Newton route and the NPV-zero identity, crosses zero at the root, is scale-free; signless and multi-root cash flows refused; discounted payback matches the float route, equals the ordinary payback at rate 0, cannot shorten when the rate rises, is scale-free, and blocks when never recovered; pipeline delivery for both (percentage rendering; artifacts/test-set parity); presets and determinism. Full suite **609 tests OK**.
**Commit:** `this commit`.
**Open/next:** valuation completion remains the natural next unblocked item (equity bridge from enterprise to equity value, mid-year convention in `dcf_valuation`); everything else unblocked is either parked for the frontier-model lane (B-075) or gated on an owner decision (B-005/B-028/B-032/B-052, REW R1â€“R10).

---

## 2026-10-21 â€” [computation] XLSX sheet selection and merged-cell policy (B-076)

**Ask:** "do number 2" â€” the XLSX hardening item (multi-sheet selection + a declared merged-cell policy) from the proposed next-three list.
**Did:** `read_xlsx`/`read_table` now take `sheet` (exact case-sensitive name or 1-based position; default still the first sheet; unknown names/numbers refused listing the workbook's sheets) and report `sheets` + `sheet_index` on every XLSX table. Merged cells are **refused by default** with the ranges named and the declared alternative offered, because repeating an anchor across its range or blanking it would fabricate or lose data; `merged="top_left"` expands each range from its anchor, skips blank anchors, refuses overlapping/nested merges as malformed, and records `merged_cells` plus a provenance-note sentence calling the repetition a declared convention. `sheet`/`merged` are XLSX-only and refused for CSV/TSV. Wired through `POST /api/ingest` as optional fields and the CLI as `--sheet`/`--merged`. **Also fixed a latent bug:** the workbook relationship id was looked up with a malformed namespace, so every workbook silently fell back to `sheet1.xml` â€” harmless while only the first sheet was read, fatal for sheet selection; the fallback now applies only to the first sheet when the relationship is genuinely absent.
**Files:** `src/bp/ingest.py`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-076, changelog 0.49, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests â€” select-by-name/index with metadata, unknown/invalid sheet refusals, CSV option refusals, default merged refusal naming the range, declared expansion (values + `merged_cells` + provenance note), malformed and overlapping merge refusals, merged-header duplicate refusal, API sheet selection and merged policy (including an invalid policy); CLI exercised by hand for default/sheet-by-name/sheet-by-number/unknown-sheet/merged-refuse/merged-top_left; full suite **598 tests OK**.
**Commit:** `this commit`.
**Open/next:** **[design]** the workbench ingestion card still sends only filename+base64 â€” exposing the new optional `sheet`/`merged` fields is presentation work for the design owner (B-066). Remaining ingestion gaps stay refused/declared: PDF/OCR/SPSS, and reading several sheets into one table (needs a declared concatenation rule).

---

## 2026-10-21 â€” [documentation] Parked frontier-model queue, and a truthful HANDOFF

**Ask:** "on those computations that require deepseek pro, write or park it in the manual or notes, as we will get back to them when we have enough credits."
**Did:** created `docs/PARKED_QUEUE.md` â€” the register for the six heavy statistics items reserved for the DeepSeek Pro lane (Tukey/Dunnett/Games-Howell, unbalanced two-way/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series). Each row states the blocker, the offline oracle already installed for goldens, and the output that would be accepted; the file also separates the *non*-frontier items (imputation, standards/filings/tax retrieval, PDF/OCR/SPSS ingest, breadth templates, REW) so they are not mistaken for the parked lane, and states the un-park trigger: an explicit owner grant of the frontier lane, not a general "continue". Recorded as B-075. **Fixed the stale handoff**: `HANDOFF.md` still said build 0.40 / 510 tests and listed as unbuilt everything finished since (paired/one-sample t, factorial/post-hoc, valuation, economics, appraisal, logistic/alpha, ingestion mapping); it now reports 0.48 / 588, carries the full method list, marks section A done, restates section C with what is built vs parked, and adds section H pointing at the parked queue. `HOME.md` gained the parked-queue rows and lost its stale "DCF/WACC â€¦ not built" line; `CONTRIBUTORS.md` links the queue and lists un-parking under "stop and ask".
**Files:** `docs/PARKED_QUEUE.md` (new), `docs/HANDOFF.md`, `docs/HOME.md`, `docs/CONTRIBUTORS.md`, `docs/DECISIONS.md` (B-075), `docs/WORKLOG.md`.
**Verified:** documentation-only increment; no code, test or fixture touched. Relative links in the new/edited files resolve; the suite is unchanged at **588 tests OK**.
**Commit:** `this commit`.
**Open/next:** the computation lane is caught up on everything buildable without the frontier model or an owner decision. Remaining work is owner-gated: parked queue (B-075, needs credits), B-005 reviewers, B-028 templates, B-032 ledger engine, B-052 taxation, REW R1â€“R10 ratification. Design/presentation is MiniMax's domain (B-066).

---

## 2026-10-21 â€” [computation] Logistic regression and Cronbach's alpha (B-074)

**Ask:** "correction, finish those you can do" â€” the remaining statistics items that do not need a frontier model or a new distribution.
**Did:** two T1 methods. `logistic_regression`: binary 0/1 outcome with up to five numeric predictors, Newton-Raphson (IRLS) at 1e-10 tolerance, no regularisation, Wald standard errors/p-values, odds ratios, log-likelihood, null log-likelihood and McFadden pseudo R-squared; non-convergence/separation, single-class outcomes, non-0/1 codes and collinear designs are refused. `reliability_alpha`: Cronbach's alpha from an items column map, listwise deletion with the excluded count, the classic k/(k-1)(1 Ã¢Ë†â€™ ÃŽÂ£item variances / total variance) formula. Goldens for the logistic model generated from `statsmodels.Logit` offline; five frozen checks each; presets `logit`/`alpha`; sandbox and session coverage.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_logit_reliability.py`, `tests/fixtures/logistic_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-074, changelog 0.48, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 9 new tests â€” all statsmodels goldens matched (coefficients, SEs, p-values, log-likelihood, pseudo RÃ‚Â²), frozen checks, separation/single-class/bad-code refusals, alpha against an independently coded classic formula, refusals for single-item and zero-variance cases, pipeline delivery for both, contract/preset, determinism. **588 tests OK.**
**Commit:** `this commit`.
**Open/next (for the frontier model):** k-means clustering, factor analysis, unbalanced/ANCOVA/repeated-measures designs, Tukey/Dunnett/Games-Howell, non-linear time series. The offline oracles for these are installed (sklearn, factor_analyzer, statsmodels AnovaRM, scipy studentized_range/dunnett).

---

## 2026-10-21 â€” [computation] CBA, cost-effectiveness and SROI (B-073)

**Ask:** "go on: â€¦ CBA/CEA/SROI."
**Did:** three T2 appraisal methods. `cost_benefit`: discounted present values of declared costs and benefits, NPV and benefit-cost ratio (omitted when PV costs are zero); five frozen checks. `cost_effectiveness`: ICER for each option against the first-listed comparator, with incremental cost/effect and dominance flags; refuses a single option, negative costs and a zero effect difference. `sroi`: present value of declared social benefits over the declared investment, with net value; refuses a non-positive investment. All three are arithmetic on owner valuations â€” no effect is monetised by the system, no deadweight/additionality adjustment is invented, and no willingness-to-pay threshold is assumed.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_appraisal.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-073, changelog 0.47, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests â€” present values against an independently written discounting loop, ICER/dominance arithmetic, SROI ratio identity, frozen checks, refusals for mismatched lengths, zero-effect comparators and non-positive investments, pipeline delivery for all three, contract/preset, determinism; sandbox and session coverage. **579 tests OK.**
**Commit:** `this commit`.
**Open/next:** remaining from the batch â€” ANCOVA / repeated measures / unbalanced designs, Tukeyâ€“Dunnettâ€“Games-Howell, logistic regression, reliability/factor analysis, clustering, non-linear time series. The first three groups need either a ratified SS/design convention or distributions the standard library lacks (studentized range, multivariate t); logistic regression, reliability and clustering are feasible with declared conventions.

---

## 2026-10-21 â€” [computation] Ingestion mapping, unit economics and multi-product break-even (B-071, B-072)

**Ask:** "go on: â€¦ unit economics / multi-product break-even â€¦ ingestionÃ¢â€ â€™method mapping helper."
**Did:** `ingest.to_method_inputs` maps named columns into a method's declared inputs â€” `value_list`/`code_list` from one column, `column_map` from an object of name Ã¢â€ â€™ column, cleaned through the method's own `validate_inputs` and `profile` so a bad mapping is refused before running; only list-shaped inputs (a scalar rate cannot come from a column), and the provenance note says the file hash identifies the source, not that the data is verified. Exposed as an optional `map` on `POST /api/ingest`. Then two T1 finance methods: `unit_economics` (margin, margin rate, payback, optional period-value LTV and LTV/CAC) and `multi_product_breakeven` (mix-weighted contribution margin, break-even units and revenue, per-product units), each with five frozen checks and declared assumptions (constant churn, fixed mix, no tax/discounting).
**Files:** `src/bp/ingest.py`, `src/bp/server.py`, `src/bp/methods.py`, `tests/test_economics.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-071/B-072, changelog 0.46, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests â€” columnÃ¢â€ â€™method mapping (value and column_map shapes), refusals for text/unknown/scalar/unmapped inputs, unit-economics arithmetic and refusals, multi-product break-even arithmetic (break-even 2000 units; 1500 coffee / 500 cake; revenue 10500) and refusals, frozen checks, pipeline delivery, contract/preset, determinism; sandbox and session coverage. **568 tests OK.**
**Commit:** `this commit`.
**Open/next:** CBA/CEA/SROI, reliability (Cronbach's ÃŽÂ±), logistic regression, clustering, non-linear time series; ANCOVA/repeated-measures/unbalanced designs and Tukey/Dunnett/Games-Howell need distributional work (studentized range / multivariate t) not in the standard library.

---

## 2026-10-21 â€” [computation] Factorial two-way ANOVA and post-hoc pairwise tests (B-070)

**Ask:** "go: factorial ANOVA + post-hoc pairwise tests."
**Did:** added two T1 methods. `two_way_anova`: balanced two-way factorial ANOVA on one numeric response â€” both main effects and the interaction, sums of squares, mean squares, F tests, degrees of freedom and partial eta-squared. Unbalanced designs and empty cells are **refused** (the SS type would be an unratified convention). Five frozen checks: independent float route, SS decomposition, F = MS/MS_error, shift invariance, scale equivariance of F. `posthoc_pairwise`: every unordered pair of independent groups compared with a Welch t-test, reporting the difference, raw p and adjusted p under a **declared** correction (Holm default, Bonferroni, or explicitly `none`), with `n_pairs`, `n_rejected` and the pair design recorded. Five frozen checks: independent float route, adjusted Ã¢â€°Â¥ raw, declared correction reproduced step by step, pair count = k(kÃ¢Ë†â€™1)/2, reversing group order negates differences and keeps p. Goldens generated offline with numpy/scipy; both wired into sandbox CASES, the session input map and presets `factorial`/`posthoc`; a `records` input type was added for the factorial design.
**Files:** `src/bp/methods.py` (records input type, both methods and contracts), `src/bp/server.py` (presets), `tests/test_factorial_posthoc.py`, `tests/fixtures/two_way_golden.json`, `tests/fixtures/posthoc_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-070, changelog 0.45, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 12 new tests â€” goldens against numpy/scipy for a main-effects and an interaction design, hand-computable exact SS/F values (8/32/0/8, F 4/16/0), frozen checks declared and passing, unbalanced/broken-design refusals, Welch+Holm goldens, adjustment-method behaviour, invalid-group refusals, full pipeline delivery for both, contract/preset assertions, determinism. **557 tests OK.**
**Commit:** `this commit`.
**Open/next:** unbalanced/ANCOVA/repeated-measures designs and Tukey/Dunnett procedures; then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 â€” [computation] Multi-currency: ISO 4217 registry, per-currency precision, declared-rate conversion (B-069)

**Ask:** "also allow it to use multi-currencies that include dollar, euro, and chinese yuan and other currencies of the world."
**Did:** `src/bp/currency.py` â€” a declared ISO 4217 table of 160+ currencies with their **minor units** (0 for JPY/KRW/VND/ISK, 3 for KWD/BHD/OMR, 4 for CLF, 2 for USD/EUR/CNY and most others), code normalisation and validation, and exact Decimal conversion at a rate the owner **declares** (with provenance `user`/`sourced`/`assumption`, a mandatory source for `sourced`, and an optional declared date). Wired into the computation layer: unknown currency codes are refused at intake; money artefacts default to the currency's minor units when the request states no precision (JPY prints no cents, KWD prints three); a management-accounts spec takes its `places` default from its currency; new T1 method `currency_convert` with five frozen checks (float second route, reciprocal-rate round trip, zero, sign symmetry, linearity); `GET /api/currencies` lists the registry; preset `currency`. No exchange rate is fetched, hard-coded or verified, and one engagement stays single-currency (no consolidation or translation).
**Files:** `src/bp/currency.py`, `src/bp/methods.py` (currency and text input types + method), `src/bp/orchestrator.py` (intake validation, per-currency precision), `src/bp/accounts.py` (currency validation, places default), `src/bp/server.py` (catalog endpoint, preset), `tests/test_currency.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-069, changelog 0.44, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 14 new tests â€” major/zero/three/four-decimal currencies, 160+ code coverage, normalisation and unknown refusals, conversion arithmetic, same-currency rule, provenance rules, invalid amounts/rates, pipeline delivery with the appendix recording codes/rate/provenance/date, per-currency precision through npv (JPY 0, KWD 3, USD 2), unknown-currency intake refusal, accounts `places` defaults, `/api/currencies`, contract/preset, determinism; sandbox and session coverage via the shared maps. **545 tests OK.**
**Commit:** `this commit`.
**Open/next:** FX retrieval/verification and statement translation/consolidation remain out (they need a rate source and a translation standard); statistics backlog resumes with factorial ANOVA + post-hoc, then unit economics / CBA.

---

## 2026-10-21 â€” [computation] Valuation: WACC and DCF (B-068)

**Ask:** "go. automate everything" â€” continue the computation backlog without waiting for instruction.
**Did:** two valuation methods. `wacc` (T1): weighted average cost of capital from declared market values of equity and debt and declared costs of equity and **after-tax** debt; reports the WACC and both weights; five frozen checks (float second route, weights sum to one, WACC between the two costs, scaling both values changes nothing, a higher cost of equity raises the WACC); no tax is computed. `dcf_valuation` (T2): declared end-of-period free cash flows discounted at a declared rate, optional Gordon-growth terminal value on the last flow; reports explicit PV, terminal PV, terminal value, enterprise value, terminal share and the inputs; five frozen checks (second route, linear scaling in the cash flows, higher rate lowers value, terminal value equals the Gordon formula, no growth means no terminal value); refuses growth at or above the rate, a rate at or below -100% and an empty forecast. Both wired into sandbox `CASES`, the session input map and presets `wacc`/`dcf`.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-068, changelog 0.43, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests â€” arithmetic against an independently written discounting loop, five frozen checks each, refusals for invalid capital structures and DCF assumptions, full pipeline delivery for both with percentage/currency rendering, contract/preset assertions, determinism; sandbox parity and session coverage. **531 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA + post-hoc pairwise tests (using the existing `multiple_comparison`), then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 â€” [computation] Inference completion 1: paired and one-sample t-tests (B-067)

**Ask:** "go. automate everything" â€” work the computation backlog autonomously.
**Did:** added two T1 methods that close the manual's 9B.2 paired/one-sample gap. `paired_t`: within-pair differences (first column minus second), a pair dropped and counted when either side is missing, with mean difference, sd/se, t, df, two-sided p, confidence interval, Cohen's dz and both column means; five frozen checks (independent float route, swapping columns negates the difference and t but keeps p, shift/scale behaviour, row-order invariance, missing pairs dropped not imputed). `one_sample_t`: one mean against a declared reference `mu0`, with sd/se, t, df, p, CI, Cohen's d and excluded count; five frozen checks (second route, shift invariance, positive scale equivariance, row-order invariance, missing entries excluded not valued). Both default to two-sided, refuse constant data through the profile, and are wired into the sandbox `CASES` test, the session input map and workbench presets `paired`/`onesample`; goldens generated offline with scipy (test fixtures only).
**Files:** `src/bp/methods.py` (both methods + contracts), `src/bp/server.py` (presets), `tests/test_inference_more.py`, `tests/fixtures/inference_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-067, changelog 0.42, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests â€” scipy goldens to 1e-9, frozen checks declared and passing, constant-data and missing-reference refusals, full pipeline delivery for both, contract/preset assertions, determinism; sandbox parity and session coverage via the shared maps. **520 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA and post-hoc pairwise tests (using the existing `multiple_comparison`), then DCF + WACC.

---

**Newest first. Never rewrite an entry.** One entry per increment (not per message): the ask, what changed, what verified it, the commit, and what is next. Link to the source of truth rather than restating it â€” `CHANGELOG.md` has the build detail, `DECISIONS.md` the reasoning, this file the narrative and the sequence.

---

## 2026-10-21 â€” 9B.3 upgrade: power and minimum-effect planning (B-061)

**Ask:** "go" â€” continue closing the open statistics items (after multiple-comparison correction).
**Did:** added the T1 method `power_analysis` for a two-sample or one-sample comparison of means under the **normal approximation**: power for a stated effect, and the smallest effect that reaches a declared target power, plus standard error, non-centrality and the z critical value. Inputs declare design, effect, sample sizes, standard deviations, alpha (default 0.05), tails (two-sided default) and target power (default 0.8); one-sample designs refuse `n2`/`sd2`; invalid numbers, alpha or sizes are refused at intake. Five frozen checks: erfc-based independent second route agrees to 1e-9, zero effect gives power = alpha, power rises with effect size and with sample size, minimum effect falls with sample size. The normal approximation and its limits (no noncentral t, no proportions, no clustering/weights/repeated measures, no multiplicity) are declared in the template, caveats and appendix. Golden fixture generated offline with `scipy.stats.norm`; no scipy at runtime. The draft-audit claim checker caught the first template draft using "effect of" (intervention language) â€” reworded rather than weakening the checker.
**Files:** `src/bp/methods.py` (core, reference route, checks, profile, typing, caveats, template, contract), `src/bp/server.py` (preset `power`), `tests/test_power.py`, `tests/fixtures/power_golden.json`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-061, changelog 0.36, limitations, gap map, REW Â§10, HOME, README, CONTRIBUTORS).
**Decisions:** B-061.
**Verified:** 8 new tests â€” scipy golden values (three designs) to 1e-9 relative, zero-effect = alpha, one-sided vs two-sided ordering, sample-size movements, five invalid-input refusals, full pipeline delivery with licensed report, contract/preset, determinism; sandbox parity and session coverage via shared maps. **465 tests OK.**
**Commit:** `this commit`.
**Open/next:** missing-data mechanism modelling and survey weights are the last 9B.3 items and need a declared convention choice (extreme-bounds vs imputation; design vs frequency weights); then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 â€” [computation] Model-ownership split: computation vs design (B-066)

**Ask:** "we will divide the jobâ€¦ keep the computation part here; design/aesthetics goes to MiniMax. Put this rule in the manual that models can read that computation are exclusively your domain."
**Did:** recorded the division of labour as a binding rule in the two documents every model reads first: `docs/CONTRIBUTORS.md` **Â§1A** (new section) and `docs/HANDOFF.md` Â§2.9. Computation is exclusively the computation owner's (DeepSeek) domain â€” `src/bp/**`, `tests/**` and fixtures, the factual docs, every number/statistic/accounting figure, verification and audit logic, citation rules, type inference, claim ceilings and asserted wording, and any prompt affecting what is produced or validated. Design/aesthetics is exclusively the design owner's (MiniMax) domain â€” the workbench's presentation and look (`web/**` layout, CSS, typography, colour, spacing, iconography, responsiveness, component styling, visual report design) and behaviour-neutral interaction affordances. Boundary rules: design may not change numbers/claims/checks/schemas/tests; computation may not silently restyle (functional wiring only); neither owner edits the other's files, and cross-domain needs are noted here tagged `[computation]`/`[design]`; cross-domain features land as a computation commit then a design commit; conflicts escalate to the owner; the verification non-negotiables bind both.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` (B-066), `docs/CHANGELOG.md` (0.41). No code changed.
**Verified:** docs only; test suite untouched at 510 tests.
**Commit:** `this commit`.
**Open/next:** the computation backlog is now the only work in this conversation â€” next increment is the paired/one-sample t-test pair, then DCF + WACC.

---

## 2026-10-21 â€” Ingestion first slice: CSV/TSV and XLSX to a typed table with provenance (B-065)

**Ask:** "go" â€” the other P0 gatekeeper: ingestion.
**Did:** added `src/bp/ingest.py`, standard library only. CSV/TSV (delimiter sniffed; UTF-8/CP1252/Latin-1) and XLSX (first sheet, read as a zip of XML parts â€” `zipfile` + `xml.etree`, no third-party library) become a typed table: column names, inferred `number`/`date`/`text`/`mixed` types, present and missing counts, sample values, rows, and a table-level provenance pointer (file, SHA-256, data row i and column j, sheet) stating that nothing is imputed or retyped. Declared conventions: first non-empty row is the header; headers must be non-empty and unique; a mixed number/text column is labelled `mixed` rather than coerced; formula cells use the cached value the file stores; XLSX dates are normalised with the workbook date system (1900 leap-year adjustment); caps of 5 MB / 1000 rows / 50 columns are **refused, not truncated**. **PDF, scans, images and SPSS `.sav` are refused with explicit messages** â€” no OCR or PDF text extraction exists, so pretending to read them would be invention. Wired as `POST /api/ingest` (base64, 422 on refusal, separate request-size limit), a workbench "Data ingestion" card with file picker and summary, and `python -m bp.ingest <file>`.
**Files:** `src/bp/ingest.py`, `src/bp/server.py` (route, body size), `web/index.html`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-065, changelog 0.40, limitations, gap map, REW Â§8, HOME, README, CONTRIBUTORS).
**Decisions:** B-065.
**Verified:** 14 new tests â€” typed CSV with missing/date columns, delimiter and encoding detection, mixed-column labelling, header refusals, row cap, XLSX shared strings/numbers/date styles, corrupt and empty workbook refusals, PDF/PNG/SPSS refusals, API decoder validation, endpoint 200/422, UI card; CLI smoke printed the summary; **510 tests OK**.
**Commit:** `this commit`.
**Open/next:** ingestion remains partial by design â€” PDF/scan/OCR and SPSS are refused, multi-sheet/merged-cell handling and automatic columnÃ¢â€ â€™method-input mapping are not built. Elsewhere: imputation and complex-design inference, standards/filings/tax retrieval sources, and the owner gates (B-005 reviewers, B-028 templates, B-032 ledger engine).

---

## 2026-10-21 â€” Retrieval failover and drift sweep (B-064)

**Ask:** "go" â€” close the retrieval extras (declared source priority/failover, drift monitoring).
**Did:** two pieces. **(a) Source priority and failover**: the declared order is Crossref then OpenAlex, the API's default source is now `auto`, and every attempt is recorded in the retrieval log as `resolved` / `not_found` / `error` with the error detail. A source error is never swallowed silently; the next source is tried; if **every** source errors the lookup fails closed (502) instead of labelling the DOI "unverified". **(b) Drift sweep**: `drift_check` re-verifies the most recent logged retrievals and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable` per entry with a summary, flagging changed citations for human re-check and never rewriting the log. Exposed as `GET /api/literature/drift?limit=` (cap 25), a workbench "Check drift" button, and `python -m bp.literature drift [log] [limit]`.
**Files:** `src/bp/literature.py` (failover resolver, attempts in log records, `drift_check`, CLI), `src/bp/server.py` (auto source, sources listing with declared priority, drift endpoint, validation), `web/index.html` (drift button and output), `tests/test_literature_failover.py`, `tests/test_literature_api.py`, docs (B-064, changelog 0.39, limitations, gap map, REW Â§9 + Q7, HOME, README, WORKLOG, CONTRIBUTORS).
**Decisions:** B-064.
**Verified:** 12 new tests â€” failover on error and on not-found, all-not-found stays unverified, all-error fails closed, attempts recorded in the log, drift hash_match/hash_differs/unresolvable/unreachable, empty log, drift source order, API auto-source response, drift endpoint and limit validation, UI button; live smoke resolved a real DOI through `default_sources()` with the attempt logged and the drift sweep returning `hash_match`, plus the CLI printing the summary. **496 tests OK.**
**Commit:** `this commit`.
**Open/next:** standards/filings/tax source families (needs a source/licensing decision, not code) and extra scholarly APIs; then ingestion (the other P0), and imputation / complex-design inference for the statistics.

---

## 2026-10-21 â€” 9B.3 upgrade: weighted summaries with a declared weight kind (B-063)

**Ask:** "go" â€” close the last statistics item on the open list.
**Did:** added the T1 method `weighted_summary`: weighted mean, weighted standard deviation, total weight, **effective sample size** `(ÃŽÂ£w)Ã‚Â²/ÃŽÂ£wÃ‚Â²` and **design effect** `n/n_eff`, with an overridable weight kind â€” `reliability` (default; unbiased weighted variance) or `frequency` (observations counted). One positive weight per value including missing entries (a missing value's weight drops with it); zero, negative, mismatched-length and blank weights are refused. **No inference**: no standard error, interval or test, because that needs a declared complex design (stratification, clustering, replicate weights) that is not implemented â€” and the honesty layer now says exactly that for this method instead of the generic "weights unsupported" line. Five frozen checks: float second route agrees, unit weights reproduce the ordinary sample summary, the mean is invariant to weight scaling, extra weight on larger values raises the mean, and the design effect is 1 for equal weights. The draft-audit claim checker again caught a template phrasing ("design effect of"); the template was reworded rather than the checker weakened.
**Files:** `src/bp/methods.py` (impl, stats helper, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty wording for the weighted method), `src/bp/server.py` (preset `weighted`), `tests/test_weighted.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-063, changelog 0.38, limitations, gap map, REW Â§10, HOME, README, CONTRIBUTORS).
**Decisions:** B-063.
**Verified:** 9 new tests â€” exact weighted mean and reliability/frequency sds, equal weights equal the ordinary summary, missing values drop their weights, all frozen checks, five invalid-input refusals, full delivery with the design disclaimer, contract/preset, determinism; sandbox parity and session coverage via shared maps. **484 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 row is closed except imputation and complex-design inference (each needs its own declared model/design). Next: retrieval extras (standards/filings/tax source families, automatic failover, drift monitoring) and ingestion (the other P0).

---

## 2026-10-21 â€” 9B.3 upgrade: missing-data bounds with a declared mechanism (B-062)

**Ask:** "go" â€” continue closing the open 9B.3 statistics items.
**Did:** added the T1 method `missing_data_bounds`. It reports how much of a variable is missing and **bounds** the complete-data mean by the extreme-case convention â€” every missing value at the observed minimum (lower bound) or maximum (upper bound) â€” alongside the observed mean, observed range and bound width. The missing-data mechanism (`unknown`/`mcar`/`mar`/`mnar`) is an input the owner **declares**; it is recorded with an explicit note that the system cannot verify it from the data, and it changes no bound. No imputation and no probabilistic missing-data model. Five frozen checks: bounds bracket the observed mean, independently recomputed extreme cases agree, adding missing entries cannot narrow the bounds, the reported share is missing/total, and with no missing values the bounds collapse to the observed mean. The generic honesty layer used to append its listwise-deletion warning to this method â€” which contradicted the method's own stronger convention â€” so that notice is now suppressed for it, and the method's own disclaimer is what the delivery carries.
**Files:** `src/bp/methods.py` (impl, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty suppression), `src/bp/server.py` (preset `missing`), `tests/test_missing.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-062, changelog 0.37, limitations, gap map, REW Â§10, HOME, README, CONTRIBUTORS).
**Decisions:** B-062.
**Verified:** 10 new tests â€” exact bound arithmetic, missing codes and blanks both counted, zero-width when nothing is missing, declared mechanism changes no number and is labelled, all frozen checks, three invalid-input refusals, full delivery without the contradictory notice, contract/preset, determinism; sandbox parity and session coverage via shared maps. **475 tests OK.**
**Commit:** `this commit`.
**Open/next:** survey weights are the last 9B.3 item; then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 â€” 9B.3 upgrade: multiple-comparison correction (B-060)

**Ask:** "go on the still open, close them" â€” the statistical upgrades the honesty layer was only disclosing.
**Did:** closed the multiple-comparison item with a new T1 method `multiple_comparison`. It applies a declared correction to one family of raw p-values: **Holm** step-down (sort ascending, multiply the i-th smallest by kÃ¢Ë†â€™i+1, running maximum, cap at 1) or **Bonferroni** (kÂ·p capped at 1). Outputs are `p_adj_1..k`, `n_tests`, `n_rejected` at the declared alpha, with an appendix carrying the raw and adjusted values and the written definition. Five frozen checks: adjusted Ã¢â€°Â¥ raw, bounded in [0,1], matches the declared definition (Holm monotone/Bonferroni formula), independent second route agrees to 1e-12, and order-invariance. Invalid p-values, alpha outside (0,1), an unknown method or a family of fewer than two values are refused at intake; a new `enum` input type covers declared method choices. The honesty layer now says a correction is available instead of only "not applied", and OLS's family-wise notice points to it. Existing methods and their goldens are untouched â€” no reported p-value changed silently.
**Files:** `src/bp/methods.py` (impl, checks, profile, caveats, template, contract, `enum` validation), `src/bp/orchestrator.py` (honesty wording for the correction method and OLS pointer), `src/bp/server.py` (preset `multicomp`), `tests/test_multicomp.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-060, changelog 0.35, limitations, gap map, REW Â§10, HOME, README, CONTRIBUTORS).
**Decisions:** B-060.
**Verified:** 10 new tests â€” published Holm example reproduced exactly (0.03/0.06/0.06/0.02), Bonferroni formula, order-invariance, all frozen checks, alpha-driven rejection counts, four invalid-input refusals, full pipeline delivery with licensed report and honesty block, contract/preset, determinism; sandbox parity and session-input coverage via the shared maps. **457 tests OK.**
**Commit:** `this commit`.
**Open/next:** power/MDE calculation, missing-data mechanism modelling and survey weights are the remaining 9B.3 items and need their own declared conventions (they change what is estimated or the input contract); retrieval still lacks standards/filings/tax source families, automatic failover and drift monitoring; ingestion is the other P0.

---

## 2026-10-21 â€” Citations: APA 7 and Harvard ratified and implemented (B-059)

**Ask:** "citation styles will be apa and harvard" â€” close the open citation item.
**Did:** replaced the provisional layout with the two ratified styles. Sources now map the bibliographic metadata the citation needs: Crossref supplies structured family/given names, volume, issue, pages, publisher and type; OpenAlex supplies volume/issue/pages and a type mapping but only display names. APA 7 renders `Family, I. (Year). Title. Journal, volume(issue), pages. https://doi.org/...` with APA's `&`/serial comma; Harvard renders `Family, I. and â€¦ (Year) 'Title', Journal, volume(issue), pp. pages. doi: ...`. Books have their own layout; any other source type gets a labelled generic layout instead of pretending it is fully styled. Rendering limits are declared in every citation's notice (plain text has no italics; titles are not case-converted; names are inverted only when the source supplies family/given, with a note when it does not). Unverified references stay prefixed `[unverified user-suppliedâ€¦]` in both styles. API `cite` now accepts `apa`/`harvard`, the sources endpoint exposes both notices and the reference payload carries the new bibliographic fields; the workbench has a style selector and "Get citation".
**Files:** `src/bp/literature.py` (reference fields, source mappings, APA/Harvard formatters), `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-059, CHANGELOG 0.34, KNOWN_LIMITATIONS, REW manual Â§9 + Q9, HOME, README, CONTRIBUTORS, WORKLOG).
**Decisions:** B-059 (RESOLVED).
**Verified:** 5 new/updated tests â€” Crossref and OpenAlex field mapping, exact APA and Harvard strings, book and generic layouts, non-inverted-name note, unverified labelling in both styles, ratified style list, unknown style refused, API style selection; live smoke against Crossref rendered a real eight-author APA and Harvard citation. **447 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 statistical upgrades (multiple-comparison correction, power/MDE, missing-data mechanism modelling, survey weights), the remaining retrieval items (standards/filings/tax source families, failover policy, drift monitoring) and ingestion.

---

## 2026-10-21 â€” Retrieval layer second slice: durable log and provisional citation (B-058)

**Ask:** "GO" after the 9B.3 honesty layer â€” continue down the gap order at the P0 gatekeeper.
**Did:** two halves of the retrieval layer. **(a) Durable retrieval log**: every retrieval that reaches a source is appended to a local newline-delimited JSON file (source, DOI, supplied and resolved title, status, authors, year, container, UTC retrieval time, response SHA-256), flushed to disk **before** the reference is returned â€” an unwritable log raises and the retrieval fails closed, so an unaudited citation cannot be produced. `read_log` refuses a corrupt or unknown-format log; `reverify` re-checks a logged entry against the source and reports `hash_match` / `hash_differs` / `unresolvable_now`. **(b) Provisional citation layout**: one declared author-date format (authors as returned, year, title, container, DOI) with an explicit PROVISIONAL notice â€” no institutional style is claimed, because none has been ratified (REW Q9). Unverified references are formatted only with the `[unverified user-suppliedâ€¦]` prefix and never as if checked. Wired into the API (`cite` parameter, `GET /api/literature/log`), the workbench (citation line, retrieval-log panel with the new "Get provisional citation" and "Show retrieval log" controls), and `.gitignore` so the runtime log cannot be committed. `BP_RETRIEVAL_LOG` sets the path; empty disables it.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `.gitignore`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-058, CHANGELOG 0.33, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, REW manual Â§9 + Q9/Q10, HOME, README, CONTRIBUTORS).
**Decisions:** B-058.
**Verified:** 17 new tests â€” log fields and single-line records, unverified retrievals logged honestly with resolved title, no logging without a retrieval, unwritable log fails closed, empty/corrupt/unknown-format log handling, append-only ordering, `reverify` states, citation structure and provisional notice, unverified labelling and mismatch note, placeholders instead of invented authors/years, unknown style refused, determinism; API tests for citation, style validation, log endpoint, limit validation and disabled state; UI strings asserted. **442 tests OK.** Live smoke: real Crossref retrieval logged with a genuine sha256, citation correctly labelled unverified for a deliberately wrong title, `reverify` returned `hash_match`.
**Commit:** `this commit`.
**Open/next:** retrieval-layer remainder â€” standards/filings/tax source families, source priority and failover, a ratified citation style (Q9) and drift monitoring; then the actual 9B.3 statistical upgrades or the next gap-map item.

---

## 2026-10-21 â€” 9B.3 honesty layer: disclosure and refusal, no numbers changed (B-057)

**Ask:** the other half of Slice 1 as agreed â€” the 9B.3 honesty pass on existing statistical outputs.
**Did:** scoped it honestly rather than overclaiming. The layer **discloses** what the system does not do, in every delivery: (a) missing values are excluded listwise and the missing-data mechanism (MCAR/MAR/MNAR) was not established; (b) multiple hypotheses are not corrected, with the family-wise exposure named for OLS coefficients and "one omnibus, no post-hoc comparisons" for ANOVA/Kruskal-Wallis; (c) no power or minimum-detectable-effect is reported, so precision must be read from the interval; (d) survey weights, clustering and repeated measures are unsupported, so every observation is treated as independent. These are both machine-readable (`appendix.honesty`) and plain sentences in the report. Separately, inputs that name an unsupported structure (`weights`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are now refused with a specific reason instead of a generic unknown-input error â€” a weighted or clustered dataset can no longer be passed in and silently analysed as independent observations. **No number changed.** The actual upgrades (Holm/Bonferroni, power/MDE, missing-data modelling, survey weights) are recorded as still open, so the layer cannot be mistaken for the fix.
**Files:** `src/bp/orchestrator.py` (honesty helper, appendix block, report sentences), `src/bp/methods.py` (unsupported-structure refusal in `validate_inputs`), `tests/test_honesty.py`, docs (DECISIONS B-057, CHANGELOG 0.32, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, REW manual Â§10, CONTRIBUTORS count).
**Decisions:** B-057.
**Verified:** 10 new tests â€” appendix block present for every delivered method, descriptive/omnibus/OLS disclosures, NPV and ratio methods report not-applicable rather than blank, determinism and JSON-safety, refusal of weights/clusters/strata with the specific reason, generic unknown-input message preserved; **425 tests OK** (no existing test changed behaviour).
**Commit:** this commit.
**Open/next:** the actual 9B.3 statistical upgrades are still the open row (correction, power, missing-data modelling, weights); the P0 gatekeeper (retrieval + citation: durable retrieval log + citation formatting) is the next build target.

---

## 2026-10-21 â€” Ratio analysis: the safe half of Slice 1

**Ask:** after the documentation spine, continue with Slice 1 as agreed â€” the risk-paired first gap closures (honesty upgrades + statement ratios).
**Did:** added the T1 method `ratio_analysis` (B-056). Fifteen declared ratios across liquidity (current, quick, cash), profitability (gross/operating/net margin, return on assets, return on equity), solvency (debt to equity, equity multiplier, interest cover) and efficiency (asset turnover, receivables/inventory/payables days) computed in Decimal from figures the owner supplies. Each ratio reports its definition, inputs and unit; a ratio with a missing figure or a zero denominator is listed in the appendix as not computed **with its reason** and never estimated; a negative denominator is computed and flagged; the balance-sheet identity is checked when assets, liabilities and equity are all supplied; supplied figures are verified to be used exactly as given. No benchmark, industry average, cut-off or good/bad verdict is applied â€” the manual forbids inventing ratings. The independent second route is exact rational arithmetic (`fractions.Fraction`), and the golden fixture is generated by a separately written Fraction re-implementation, not by the method itself. Added the `ratios` workbench preset; the `days` unit is no longer given a currency in the orchestrator.
**Files:** `src/bp/methods.py` (catalogue, impl, checks, profile, caveats, template, contract), `src/bp/orchestrator.py` (unit exemption), `src/bp/server.py` (preset), `tests/test_ratio.py`, `tests/fixtures/ratio_golden.json`, `tests/test_sandbox.py` `CASES`, `tests/test_session_api.py` input map, README, docs (DECISIONS B-056, CHANGELOG 0.31, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, CONTRIBUTORS count).
**Decisions:** B-056.
**Verified:** 15 new tests covering golden values, every frozen check, scale invariance, sign behaviour, missing-figure disclosure, zero denominators, negative equity, balance-sheet identity (holds / fails / not applicable), Decimal outputs, determinism, intake blocking, preset reachability and a full pipeline delivery with a licensed report; sandbox parity via the shared `CASES` test; **415 tests OK**.
**Commit:** this commit.
**Open/next:** the other half of Slice 1 â€” the 9B.3 honesty pass on existing statistical outputs (multiple-comparison correction, power/precision statements, missing-data mechanism declaration, survey-weight/cluster detection), then retrieval + citation (P0 gatekeeper).

---

## 2026-10-21 â€” Documentation spine: contributors' manual, home map, this worklog

**Ask:** after the gap discussion, the owner asked for a log that traces the work, a manual for any model that will touch or fix the files, and an Obsidian-like map to find things â€” then "go".
**Did:** added three documents and wired them in: `docs/CONTRIBUTORS.md` (ten non-negotiables, the add-a-method checklist, bug-fix rules, boundary-change rules, the testing contract, environment traps, "where each fact belongs", rejection list, stop-and-ask list), `docs/HOME.md` (task view, module map, capability status, documentation spine, map conventions), and this `docs/WORKLOG.md`. Design choices confirmed with the owner: `CONTRIBUTORS.md` is a repo-level bridge (not part of the authority manual), `HOME.md` uses plain Markdown links rather than Obsidian wikilinks, and the worklog starts now with a backfill pointer rather than reconstructing history.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HOME.md`, `docs/WORKLOG.md`, `README.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md` (B-055).
**Verified:** docs only; suite unaffected (400 tests OK run in the previous increment). Links checked against the files present in the repo.
**Commit:** this commit.
**Open/next:** Slice 1 of the gap plan â€” the 9B.3 honesty pass on existing statistical outputs (multiple-comparison, power/precision, missing-data mechanism, weights/clusters) as the risky half, paired with the safe half: financial-statement ratio analysis (T1 arithmetic on the ledger artifacts).

---

## 2026-10-21 â€” Retrieval audit: response SHA-256 and UTC time per reference

**Ask:** "okay do 3 first" â€” the cheapest REW increment, Q10 in the living manual: make the hash-audit claim true.
**Did:** `CrossrefSource`/`OpenAlexSource` capture the raw response bytes and record `response_hash` (SHA-256 of those exact bytes) plus `retrieved_at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) on every resolved retrieval; the fields travel through `POST /api/literature/verify` and show in the workbench References panel. A reference that never reached a source (no DOI, 404, source error) carries neither, fail-closed. Clock is injectable for deterministic tests. Hash is byte-level on purpose: the same semantic record received with different whitespace hashes differently, so the audit pins what was served.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_api.py`, docs (REW manual v0.3, DECISIONS B-054, CHANGELOG 0.29, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, README).
**Decisions:** B-054 (PROVISIONAL); REW manual Q10 marked answered.
**Verified:** five new tests (byte-level pin vs parsed record, injected clock, audit survives a title mismatch, no audit without retrieval, OpenAlex parity) plus API/UI assertions; **400 tests OK**; live smoke against Crossref recorded a real sha256 for DOI `10.1038/nature12373`.
**Commit:** `3189816`.
**Open/next:** no durable retrieval log yet (documented); citation formatting is still `[OPEN]` Q9.

---

## 2026-10-21 â€” Owner ratifies R11: the REW living manual is the working authority

**Ask:** "yes to R11".
**Did:** ratified R11. The manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) is now the working authority for the Research & Evidence Workflow; B-035 (blocked on the missing Smart Researcher manuals) is closed and B-053 resolved. Manual to v0.2, stating explicitly that R11 ratifies the **document**, not its proposals â€” R1â€“R10 (stage list, checkpoints, tiers, taxonomy, etc.) remain unratified.
**Files:** REW manual, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Decisions:** B-053 RESOLVED; B-035 SUPERSEDED.
**Verified:** docs only; no code changed.
**Commit:** `7d73b6d`.
**Open/next:** cheap code increment that makes the manual honest â€” the retrieval audit (Q10).

---

## 2026-10-21 â€” Living manual for the research workflow (REW), replacing "Stage 7"

**Ask:** the owner believed Stage 7 had already been built; asked "what are these: reviewers, next templates, ledger engine, Stage 7 manuals?" and "create a living stage 7 manual and probably, rename that appropriately".
**Did:** explained the four owner asks (B-005 reviewers, B-028 next templates, B-032 ledger engine, B-035 missing research-pipeline manuals) and corrected the record: what existed was the Stage 7 **blocker** document plus the literature retrieval/verification boundary, not the workflow definition. Created `docs/RESEARCH_EVIDENCE_WORKFLOW.md` as a living manual, renamed the capability **Research & Evidence Workflow (REW)** â€” "Stage 7" was a build-order label, not a product name. Merged and removed `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md`; updated every reference. The manual refuses to pretend it is the lost Smart Researcher manual: every section is tagged `[OWNER]`, `[REPO]`, `[2ND]`, `[PROPOSAL]` (R1â€“R11) or `[OPEN]` (Q1â€“Q12), with stages R0â€“R8 proposed, three mandatory checkpoints, feasibility tiers, study taxonomy, retrieval/citation rules, claim rules, synthetic-data and AI-use policy, an honest inventory, and a ratification register.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (new), two Stage 7 docs (removed), `README.md`, `docs/DECISIONS.md` (B-035 superseded, B-040 pointer, B-053), `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`, `src/bp/literature.py` docstring.
**Decisions:** B-053 created; B-035 superseded.
**Verified:** docs only; **395 tests OK**.
**Commit:** `896372e`.
**Open/next:** owner ratification of the register (R11 asked first).

---

## 2026-10-21 â€” Product gap map

**Ask:** "what else in business have we overlooked?" (after the taxation discussion).
**Did:** wrote `docs/PRODUCT_GAP_MAP.md`: what the catalogue/manual call for versus what is built, ordered P0 gatekeepers (retrieval+citation, ingestion, decision dependencies), P1 statistics completion and finance/valuation, P2 catalogue breadth, plus the non-computational gaps in manual Â§15B/Â§16; with tier/verification notes and a recommended order.
**Files:** `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Verified:** docs only; cross-checked against `DECISIONS.md` and module inventory.
**Commit:** `8c71814`.
**Open/next:** decide which gap to close first (the recommended order was discussed, not started).

---

## 2026-10-21 â€” Taxation recorded as deferred

**Ask:** "does the jobs you did in creating the pipeline include taxation?" Ã¢â€ â€™ no; "put it in your memory".
**Did:** recorded **B-052 DEFERRED**: the manual makes tax a non-goal and a jurisdiction-specific area to keep out of the autonomous path or gate behind retrieved sources; resume conditions (VAT/GST, income tax in the accounts, after-tax appraisal, filing) and the evidence lines from the manual are in the decision.
**Files:** `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
**Decisions:** B-052.
**Verified:** read-only analysis against `docs/sources/business_pipeline_v0_3.md` and `src/bp/methods.py`.
**Commit:** `efa9404`.
**Open/next:** product gap map.

---

## Backfill â€” earlier increments (v0.13 â€¦ 0.25)

Earlier work predates this log. The full ordered record is `docs/CHANGELOG.md` (0.13â€“0.25) and the stage reports; do not duplicate it here. In short: deterministic pipeline + spec/freeze (Stage 0â€“4), method library and golden fixtures (Stage 5), catalogue registry and T4 templates (Stage 6), model-provider boundary with evaluation scaffold (B-031/B-036/B-038/B-039), literature retrieval boundary (B-040), statistics increments (B-042), forecasting (B-043), and the Stage 8 accounting chain â€” schedules, two-route cash flow, closing/rollforward, declarative engagement, reconciliation, account-mapping checkpoint, policy changes, statement exports (B-044â€“B-051). The first commit in this repository is `1ab1d05`; the last pre-worklog increment is `efa9404`.

## 2026-10-30 â€” [product] Home chat serves every subject

**Ask.** Home composer refused non-management briefs.

**Did.** Added open subject `any`; guard.detect_subject; chat.start open mode; web sends subject:any. Shelf boundary preserved.

Drafted B-170 decision text: owner instruction to make Home the open entry point accepting any subject brief and routing deterministically; changes guard/chat/web as above; does not change capabilities, frozen core, cues, or shelf refusals.

## 2026-10-31 - [docs] The manual builder stops breaking its own content

**Ask.** Owner instruction: update `DATABASE.md` and `DATABASE.docx`, make the corpus database
self-enriching, and hand back an understandable walkthrough for building it.

**Did.** Rebuilt `DATABASE.docx` from `DATABASE.md` through `scripts/build_manual_docx.py`, and found
two renderer defects by rendering the result and looking at the pages: table columns were sized in
proportion to the column's total character count, so a short-label column was squeezed and Word broke
its content mid-word (`sources.py:4` / `96`); and the inline pattern required a non-space before the
opening `*`, so `*why*` printed its asterisks instead of being emphasis. Both are fixed in the builder
and pinned by `tests/test_manual_docx.py` (B-171).

**Files:** `scripts/build_manual_docx.py`, `tests/test_manual_docx.py`, `docs/DECISIONS.md`,
`docs/CHANGELOG.md`, `docs/WORKLOG.md`.

**Decisions:** B-171. B-170 was drafted by the Home-chat increment in the worklog above and is left
to it; this entry takes the next free number so the log stays unique.

**Verified:** `python -m unittest tests.test_manual_docx` (10 tests). The corpus manual was rendered
to PDF through Word and the pages were inspected: the eight-table and the five-traps tables now keep
their identifiers whole. Coverage re-checked at 452/452 source blocks matched in order.

**Open/next:** the corpus walkthrough (`corpus-db/WALKTHROUGH.md`) and the rebuild of `DATABASE.docx`
onto its real path, which is still held open by the owner's Word.

---

## 2026-11-03 - [design] The brand name steps back, the body steps down, and the chat lines up with the Documents

**Ask.** Owner instruction on the Home page: the brand name under the logo is "too loud and big" -
reduce its font size by 2 points; in the body, reduce the font size by just 1 point; and adjust the
width of the chat container to a Codex or ChatGPT size.

A second instruction the same day reversed the width half: the narrow column "looks awkward with
the documents section" - align it to the Documents section, with equal space on both sides. The
type changes are the first instruction and stand; the column width is the second.

**Did.** The hero `h1` under the mark is 43 px (was 45 px). The topbar wordmark is untouched at
20.2 px - it sits beside the mark, not under it, so it is not the brand name the instruction named.
The body is 16.8 px (was 17.8 px), and the body copy one rung above it moved with it, so the
reduction is visible and not only structural: the hero paragraph and the slogan are 18 px and the
composer text is 18 px (both were 19 px).

The chat column - the composer and the conversation card under it - is **the width of the Documents
section below it**: the full content box, the same edges as `#homedocs`, with the same even space
on both sides, so nothing floats in the middle of the page and the page reads as one column. The
conversation card sits 16 px under the composer instead of sharing an edge with it.

A `max-width: 768px` on the composer and the conversation card was tried first, on the Codex /
ChatGPT reading of the first instruction. It measured as a narrower box floating inside a wider
page - 174 px of empty space on each side against a Documents card that ran the full width - and
the owner reversed it. The rule is gone.

The pinned body size in `tests/test_product_subjects.py` moved with the page: the assertion pins
the body rule itself at `font-size:16.8px`, with the owner's instruction and the date in a comment
beside it. It pins the whole rule because 16.8 px is also a worksheet title size, so the loose form
would have stopped guarding the body.

**Files:** `web/index.html`, `web/DESIGN_NOTES.md`, `tests/test_product_subjects.py`,
`docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`.

**Decisions:** B-188.

**Verified:** measured on the served page (Chrome, 1440x1000 viewport, rail collapsed): `.hero h1`
45 -> 43 px, `body` 17.8 -> 16.8 px, the composer text and the slogan 19 -> 18 px, and `.actionbox`,
`#chatcard` and `#homedocs` all 1116 px at the same left (185) and right (1301) - the same edges and
0 px of space inside the content box on either side. The gap composer -> conversation 16 px and
conversation -> Documents 16 px. The inline script parses (`node --check`);
`tests/test_web_inline_script.py` (2), `tests/test_web_brand_assets.py` (5) and
`tests/test_product_subjects.py` (53) pass. No behaviour, number, wording or claim changed.

**Open/next:** the build pill stays at v1.45; `tests/test_product_subjects.py` pins its shape
(`v\d+\.\d+`) and the version string is the computation owner's to move.

---

## 2026-11-03 - [design] The rail's icons sit in the middle of the green

**Ask.** Owner instruction: check the icon rails on the outermost left side of the screen - the
icons are not centred. Centre them.

**Did.** The icon column is now centred in the green strip instead of packed against its right
edge. `--rail-ic-pad` changed from the right-packing formula to
`calc((var(--rail-w) - var(--rail-ic-w)) / 2 - var(--rail-pad))` - a formula, so the narrow layout's
own `--rail-w`/`--rail-pad`/`--rail-ic-w` recompute it. The toggle's chevron walks onto the column
by hand in terms of `--rail-ic-pad`, so it moved onto the centre line with it.

Nothing else moved: the strip stays 45 px (44 px narrow), the gutter stays 10 px, and the label
column and the "SUBJECTS" heading stay on the same x (55 px; 54 px narrow).

**Files:** `web/index.html`, `web/DESIGN_NOTES.md`, `docs/WORKLOG.md`.

**Verified:** measured on the served page (Chrome, device pixel ratio 1) with a CDP probe, in both
rail states at 1280x900 and 760x900, and captured in all four. Wide: strip 0 -> 45 px (centre
22.5), glyph 18.5 -> 37.5 px before and **13 -> 32 px** after (centre 22.5), chevron 18 -> 38 px
before and **12.5 -> 32.5 px** after. The off-centre error is **0 px**, was 5.5 px. Narrow: strip
0 -> 44 px (centre 22), glyph **12.5 -> 31.5 px** and chevron **12 -> 32 px**, both centred; the
error is **0 px**, was 6 px. The glyph is still the full 19 px and is not clipped. The inline script
parses (`node --check`); `tests/test_web_inline_script.py` and `tests/test_web_brand_assets.py` pass.

**Open/next:** the glyph-to-word distance in the open rail is now 23 px, was 17.5 px - the price of
the icons being in the middle of the green. `tests/test_product_subjects.py` has one **pre-existing**
failure, `test_the_rail_carries_the_portfolio_lab_above_the_calculator`: it asserts the string
"The free quote limit is reached", which commit `8bd1e9f` removed from the page. It fails the same
way with or without this change.


---

## Session 11 of 11 â€” `research` (2026-11-03) Â· opening `6c7073c`

**Asked.** Verify, debug and repair the Research & statistics shelf, subject by subject, without
opening any other shelf. Ground truth to re-measure (not copy): 21 tools, 0 worksheets, 0 tiles,
10 records (3 computed / 7 read-only), 0 theories, 0 glossary, catalogue 10, `does_not` 3,
`start_steps` 4, cross-cutting, `LIBRARY` 142 / `PRESETS` 144 / fixture 142â€“144, and **no**
`qa/manual/research.md` and **no** `tests/test_subject_research_acceptance.py`.

**Found before measuring.** The work order's snapshot was stale: HEAD was `6c7073c` (marketing's
B-211), not `b393743`; the branch was 2 ahead of origin, not in sync; and the loader measured **3418**
tests, not the documented 3479-or-3409 the documents claimed. Everything below was re-measured.

**Did.** (1) **A probe, proved before it was trusted.** `qa/probe_research_shelf.py` prints the
inventory, resolves each tool **twice** (`key` vs `method`), reads the ten records, dumps each method's
declared contract, writes and reads one real paper per tool, and re-derives the figures with its own
arithmetic. It was pointed at `operations` first (`--subject operations --prove` â†’ 0 problems), because
warning 2 of the standing list is that a harness is a suspect until it has been pointed at a shelf you
trust. (2) **The manual**: `qa/manual/research.md`, 10 sections, 53 E-rows, a DISPUTED table and a
traceability matrix. (3) **The suite**: `tests/test_subject_research_acceptance.py`, 53 tests named
`test_E_res_nnn__â€¦`, 53 passed. (4) **Five records repaired** (D-RES-01) in both the product slice and
`registry.METHOD_LINK_RULES`, so the page and `/api/frameworks` cannot disagree. (5) **Four tiles**
(D-RES-06) from the shelf's own start steps, owner decision B-213. (6) **A paper defect fixed**
(D-RES-03): a dict input printed as a Python repr in every column-map paper. (7) **Doc drift fixed**
(D-RES-07): `BACKEND_CONTRACT.md` Â§2 said 140/142 in four places; measured 142/144; the fixture was not
touched.

**Verified.** `python -m pytest tests/test_subject_research_acceptance.py -q` â†’ **53 passed**.
`qa/probe_research_shelf.py --verify` â†’ **61 figures compared, 0 disagreements**, including
Welchâ€“Satterthwaite df 4.959 (not 5.000), the published `P(|T|>2.0 | df 10) = 0.0734`, `Ï‡Â² = 4.0 â†’
p = 0.0455`, Holm 0.01/0.03/0.04 â†’ 0.03/0.06/0.06 and the OLS slope 38/42. Blast radius re-tested:
economics + operations acceptance **129 passed**, `test_catalogue_truth` + `test_product_subjects`
**63 passed**, `test_docs_sync` + this shelf's suite **61 passed**, `scripts/econ_shelf.py --check` â†’
`methods: 142`, `presets: 144`, `frozen fixture: in sync`. The loader measured **3418** at the opening
and **3478** once this session's 53 tests landed (a live lane's two uncommitted bundle tests put the
dirty tree at 3480). The 21 papers are in `qa/evidence/research/`, docx and text.

**Left open, on purpose.** D-RES-04 (`power` and `missing` print no honesty block) and D-RES-05
(`logistic_regression` declares 6 dp, so its paper prints six decimals) are both one edit in the
unfrozen **core** and a nine-shelf blast radius; each is ledgered, explained in the manual and pinned
by a test that fails the day it changes. The nine null levels stayed null because the owner chose tiles
only (B-213). Four tools still ship with `preset: null` (typed-input mode, the same as finance's
`ols_robust`), and adding presets is an owner decision.

**Open/next.** The marketing shelf is the last subject without an acceptance manual. Its top
three risks, and the two owner decisions this session could not take, are in `qa/QA_STATE.md`. **Follow-up session after marketing:** Generic shelf-invariant suite (Option D) â€” extend `test_shelf_invariants.py` to a full report-only sweep of all 11 shelves, list findings, then choose fixes.

### Follow-up, same session â€” the owner answered "YES"

Two core questions were put; the answer was yes, and the answers are not symmetric:

**(1) D-RES-05 â€” closed.** `logistic_regression` declared six decimal places for its coefficients,
standard errors and both log-likelihoods, so every logistic paper printed `-22.806666`. It now declares
four (`_logit_typing`, **B-214**) and the paper reads `-22.8067`. Before touching it I measured the two
things that could have made it an unfreeze: the frozen fixture pins `tier`, `metric`, `unit`,
`claim_ceiling`, `test_names` and `inputs` and **not** precision (so no fixture edit, and none was
made), and `logistic_regression` is offered by this shelf alone (so no other page moves). Nothing in
`tests/` pinned the six-decimal strings. Verified: research suite + `test_honesty` + `test_missing` +
`test_frozen_contract` **77 passed**; the 21 papers regenerated, **0 precision problems**, and
`logit` no longer matches `\d\.\d{6,}`. E-res-019 now also bans six-decimal figures outright.

**(2) D-RES-04 â€” re-measured, and my first diagnosis was wrong.** I had reported that `power` and
`missing` "declare an empty `honesty` map", implying the caveats did not exist. They do:
`_power_caveats` and `_md_caveats`, and both sentences print â€” in the Result prose ("Power is a
planning property of the design, not evidence about the result"; "They are honest bounds, not
estimates"). What is absent is the *heading*: `orchestrator._honesty` fills a fixed four-field
structure (`missing_data`, `multiple_comparisons`, `power`, `weights_and_clusters`) and fills it only
for inferential methods, and both are `descriptive` with no assumption checks. `tests/test_honesty.py:37`
pins that key set and `:41` pins `missing_data: None` for the bounding method, so a fifth field is a
contract change â€” an unfreeze, not a session edit â€” and filling `power` for a method whose paper
already says it in prose would stretch that field's meaning. A census showed **94 of 142 methods** would
gain a block under the naive fix, which is exactly why it is not one. The row stays **OPEN**, with the
cause corrected in the manual, the ledger and `QA_STATE`.

**Verified after the follow-up.** `python -m pytest tests/test_subject_research_acceptance.py
tests/test_honesty.py tests/test_missing.py tests/test_frozen_contract.py -q` â†’ **77 passed**.
`qa/probe_research_shelf.py --tools` â†’ 21 papers, 21 delivered, 0 precision problems.

### Follow-up 2, same session â€” the owner said "yes" again: the honesty unfreeze (B-215)

`_honesty` could not be fixed by writing caveats, because the caveats already existed. The defect was
the *shape*: four standard fields, filled only for inferential methods. So the shape changed, under
the owner's authorisation, in the one place that keeps the change small:

- `Pipeline.run` now keeps the method's caveats in `own_caveats` (it already computed them for `notes`);
- after `_honesty` returns, **if none of the four standard fields has anything to say and the method
  declares caveats**, the block gains `this_method` = those caveats. A paper that already discloses
  something never gets it, so nothing is said twice, and the four keys are always present as before.

The artefact, read back from the `.docx`:

```
POWER    Honesty: what was not done
         this method: Power is calculated under the normal approximation â€¦ Power is a planning
         property of the design, not evidence about the result â€¦
MISSING  Honesty: what was not done
         this method: The bounds are the extreme cases â€¦ They are honest bounds, not estimates â€¦
```

Only two of the 21 evidence papers changed â€” every other method on this shelf already carried a
standard notice â€” which is the blast radius this shelf can see. The rest of the blast radius is the
other nine shelves, whose descriptive methods now also print the heading; all nine acceptance suites
were run for it.

**The pin was strengthened, not loosened.** `test_honesty` used to assert an exact key set; it now
asserts the rule (the four always present, the fifth only alone and non-empty), and
`test_ratio_analysis_is_descriptive_and_carries_no_inferential_notices` checks the four inferential
fields directly instead of "every value is None" â€” which is what its name always meant. Two of my own
first-draft expectations failed against it and were corrected, not the code: a method with no caveats
legitimately has no fifth field, and `ratio_analysis` does declare caveats.



## 2026-11-07 - [product] Manual update: automated testing, tile cases, self-healing loop

**Ask.** Update the manual of what was built today so a debugger and a future enhancer
can reference it.  Separately record the intended future work.

**Did.**

- **`docs/HANDOFF.md`** gains sections 8 (Automated testing, tile cases, and the
  self-healing loop) and 9 (Intended future work).  Section 8 covers what is built,
  the routes, how to debug a failing case, and the non-negotiables that apply to the
  subsystem.  Section 9 records the autonomous growth loop, local models, xlsx
  cell-level assertions, multi-case upload, Excel merged cells, reopen, and case
  versioning as not-yet-built.
- Sections 8.3 and 8.4 are written so a debugger can follow them without reading the
  code first.

