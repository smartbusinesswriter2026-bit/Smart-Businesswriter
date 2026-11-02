[product] Worksheet registration WO-2/WO-3: 32 orphan profiles registered as worksheets, 8 new profiles built, CHG-15/STR-19/STR-20 added. Proposed decision: register orphan framework profiles as T4 worksheets (structure and evidence audit only); does not change frozen core, methods, or paper claims.


## 2026-11-02 — [design] The logo loses its white card, the favicon comes back, and the mark grows

**Ask.** "fix the logo smart business writer in home page. remove the white background around it. also restore the favicon, its lost. its now at http://127.0.0.1:8021/#/home" — then: "increase the size of the logo by 20% and put it a little closer to Smart Business Writer. like move it down a little because it appears far. then commit it".

**Did.** (1) **The logo.** The owner's `web/assets/logo.png` is RGB with no alpha channel - the mark was flattened onto solid `#FCFCFC` paper, and the copy that went into the page carried that paper with it. On the Home hero (canvas plus a green wash) the mark therefore sat on a white card. New `scripts/generate_mark.py` cuts the mark out of `logo.png` with a real alpha channel, reusing the same cut `scripts/generate_favicons.py` already uses for the tab icons: the paper *outside* the artwork becomes transparent, the paper *inside* the book stays opaque, so the book still reads as a solid object. `web/assets/mark.png` is rewritten (168x139 RGBA, 45.5% transparent) and re-inlined as the page's four logo copies (topbar brand, Home hero, chat button, and the `MARK` constant); the file on disk is written from the same bytes that go into the page, so the two cannot drift. The resize runs premultiplied, so the edges keep the ink's own colour and leave no pale halo on the dark chat button. (2) **The favicon.** Commit `977c1cc` had pasted a scaffold document (`<!doctype html> ... <!-- Content goes here -->`) in front of the real page. A browser parses that scaffold as the document, so the real `<head>` - and with it the four icon links - was parsed into the body, where no browser reads a favicon from. The scaffold is removed and the page is one document again. (3) **The mark grows and closes up.** The hero mark is 20% larger (`.hero img` height 78px -> 94px; 56px -> 67px under 900px), it sits 6px lower (`margin-top:6px`), and the gap to the wordmark is 6px instead of 16px (`.hero h1` margin-top 16px -> 6px), so the mark and "Smart Business Writer" read as one lockup instead of two things with a gap between them. Nothing else on the page moved: the topbar mark and the chat button keep their sizes.

**Why.** Both are presentation defects with no computation behind them, so the fix is presentation too: an asset cut with alpha, and a file that is one document instead of two. The logo cut is the owner's own PNG - no new artwork and no invented colours. The favicon needed no new icon: the 16/32/64/apple-touch set was already correct and already inlined; it had simply been pushed out of the head. The size and the gap are the owner's call on their own mark, applied as two numbers in the page's CSS.

**Verified.** Chrome's own parser was asked what it made of each version of the page: **before**, `iconLinksInHead` was **0** (the three icon links were in the body, `iconLinksAnywhere` 3); **after**, `iconLinksInHead` is **3** plus the apple-touch icon. The browser made no `/favicon.ico` request after the fix (the server 404s that path, and a browser with a page icon does not ask for it). Headless Chrome at 1280x900 shows the hero mark on the wash with no card, the topbar mark with no card, the chat button as a navy circle with the mark on its round plate, and - after the resize - the larger mark sitting close above the wordmark. The served page loads with no console error or warning. New `tests/test_web_brand_assets.py` (5 tests) reads the page and the PNG bytes with the standard library only (no imaging package in the test path): one document, the icon links in the head, the logo's corner transparent and its artwork still present, `mark.png` byte-identical to the inline copy, and no opaque corner in any favicon. The full suite is unchanged in outcome.

**Open/next.** The open request in `web/DESIGN_NOTES.md` for a `GET /assets/<path>` route stands, so the assets stay inlined as data URIs; `web/assets/mark.png` is the asset of record for the mark and `web/assets/favicon-*.png` for the icons. The chat button's round plate is now drawn by the CSS (`background:var(--canvas)`) with the mark on it, which is what the CSS always intended.

---

## 2026-11-02 — [design] Subject-by-subject paper validation: the harness design, and the rules that may be relaxed

**Ask.** "The pipeline has too many features and very laborious for 1 person to validate. Investigate and propose a
method or system on how I can automate the validation. What I require is that to have a complete paper for each
feature where I will not manually test them feature by feature but rather subject by subject." Then, after the
investigation: "Write them first in a handoff document named as you proposed so that future models can see them and
this is easily discoverable. Make this a living document also allowing future improvement to the method, especially on
relaxing some rules — some rules are counterproductive. Also, the model that should do this is OpenCode or
OpenRouter, not the DeepSeek direct API, to save on cost."

**Did.** Measured the surface: **364 distinct validation targets** (76 framework papers, 126 capability papers, 9
conductor frameworks, 5 paper profiles, 148 compute-tool deliverables). Found that the production side already exists —
`documents/` holds **1,781 generated `.docx` papers** from the test suite's own runs, but `paper_store.py:84` caps its
index at 200 rows, so most of them have no durable record, nothing groups them by subject and nothing judges them.
Proved both paper paths run unattended and in memory: Kano produced a 22,105-byte `.docx`; the conductor produced an
18,784-byte PESTEL+NPV paper with the export gate returning `missing: []`. Found that **125 of 126 capabilities are
already seedable from the existing `PRESETS`**, so no inputs need hand-writing. Found the blocker for "subject by
subject": there is no single subject taxonomy — the subject pages use 11 names, the framework profiles use 7 (with
`pestel` and `five_forces` carrying none), and the `subject` key is **empty for all 126 capabilities and all 158
catalogue records**. Wrote [`VALIDATION_HARNESS.md`](VALIDATION_HARNESS.md) as a living document: the
three-layer architecture, a **20-rule registry** seeded from `CONDUCTOR_MANUAL.md` §4/§8 with each rule's status and
its backing code, the **procedure for relaxing a counterproductive rule**, the subject crosswalk with its proposed
defaults, the evidence-fixture plan, the output contract and the build order. Recorded the owner's model instruction
and its consequence: OpenRouter is reachable today through the existing OpenAI-compatible provider with no code
change, OpenCode is an agent harness rather than a provider, and **the harness needs no model at all** because the
judgement layer is pure code over the deterministic Draft path.

**Why it is built this way.** Three layers — produce, judge, roll up — because the owner's unit of review is the
subject, not the feature: 31 of the 55 worksheets sit on two subject pages, so one paper serves both shelves. The
judgement layer reuses the product's own functions (`paper.check`, `completion.missing`, `chat._recompute_guard`,
`verify.overclaims`) so the harness cannot drift from the product's behaviour. The relaxation procedure is built on
one principle — **relax the alarm, never the guarantee**: the harness's verdict is a report and downgrading a rule
changes what the owner is shown, while the product's export gate stays untouched; a change to what the product asserts
would be a computation-lane change and must be requested, not made here. The crosswalk lives in the harness's own
`subject_map.json` rather than in `src/bp/product/capabilities.py`, so the whole proposal stays in the design lane
(B-080) and touches no frozen module and no test.

**State.** Nothing is built. The document is a proposal with its open questions listed in §12. Two findings are
recorded for the owner rather than acted on: **22 of the 76 framework profiles are not reachable from any subject
page**, and 12 profiles have a worksheet that is not marked `draftable`. The test baseline at the time of writing was
**2553 tests → 84 failures + 12 errors**, the framework-completion slice being 566 tests → 55 failures + 7 errors;
the dominant failure classes are already the paper rules the registry names (V-12 in ~11 frameworks, the prompt
contract in ~13, the heading contract in ~5). No source file, frozen module, test or product document was changed.

---

## 2026-11-02 — [product] The People & organisation shelf: ten frameworks that said "no worksheet yet" now complete

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

## 2026-11-01 — [design] Matrix figures: a grid framework reaches the paper as a grid (B-176)

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

## 2026-10-31 — [code] Proprietary corpus wired as pipeline layer 1 (B-172)

**Ask.** Wire the corpus database (5 documents, 96 pages, indexed in Meilisearch on :7700) into the
pipeline's retrieval engine so corpus pages can be cited as evidence, fixing the five traps that silently
discarded corpus results.

**Did.** Changes in `bp/product/sources.py` and `bp/product/retrieval.py`:
1. `_corpus()` adapter added — reads Meilisearch over stdlib `urllib`, fails open when down, returns
   page items with `corpus_key`, `database: "Proprietary corpus"`, `kind: "proprietary"`. Registered in
   `ADAPTERS`; `corpus` entry added to `DATABASES` (access: local).
2. Trap 1 — title gate no longer applies to full-text sources; one cue hit in the quoted passage is
   enough, title never sufficient alone (D-10 / B-168).
3. Trap 2 — dedup key prefers `corpus_key`; two pages of one book no longer collapse (Q-02).
4. Trap 3 — corpus items score source weight 2, equal to OpenAlex/DOAJ/Crossref (Q-03).
5. Trap 4 — `_credibility()` never overwritten when the adapter set a score; corpus branch added.
6. Trap 5 — corpus searched separately and prepended first in `retrieve()` (layer 1 before layer 2).

**Verified.** All 26 tests in `tests/test_sources.py` pass (6 new corpus tests). Live run against the
seeded corpus: corpus items reach the `items` list first; abstract-only results unchanged. No method,
preset, input, check or frozen-core entry changed.

**Files.** `src/bp/product/sources.py`, `src/bp/product/retrieval.py`, `tests/test_sources.py`,
`docs/DECISIONS.md` (B-172), `docs/CHANGELOG.md`, `docs/WORKLOG.md

## 2026-10-31 — [code] Corpus learning hook + student-upload path (B-173)

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
   `owner_approved_at` NULL — not citable until the owner approves them in the admin UI.
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



# Worklog — append-only record of what was done

## 2026-11-01 — [code] Corpus seed: 20 documents across 10 subjects (B-175)

**Ask.** Seed ~20 real documents from `D:\SMART BUSINESSWRITER\DATABASE` into the corpus database, per DATABASE.md step 11: "2 subjects deep, ≥1 scanned book, ≥1 born-digital."

**Did.** Ingested 20 documents (15 books + 5 journal-articles) covering 10 subjects: accounting, economics, finance, management, marketing, operations, people, research, entrepreneurship, supply-chain.
- 9 OCR'd/scanned (OpenStax Principles of Accounting Vol 1: 973 pages; Principles of Economics: 948; Principles of Finance: 629; Principles of Marketing: 707; Principles of Management: 605; Human Resource Management: 532; Introduction to Business: 663; Introduction to Logistics: 159; Penerapan Porter Five Forces: 20)
- 11 born-digital text layer (Operations and SCM: 186; Fundamentals of HRM: 229; Exploring Business: 940; plus 5 original journal articles)
- Licences recorded where known (CC BY, CC BY-NC-SA); unknown licences NULL per C-05.
- Duplicate protection enforced: re-ingesting any file is refused before anything is written.

**Verified.** DATABASE.md step 11 acceptance met: 20 documents, 10 subjects (≥2 deep), ≥1 scanned book, ≥1 born-digital. `corpus-db/build/test_corpus_build.py`: 55 tests pass. `tests/test_sources.py`: 28/28 pass (1 pre-existing flaky test_brave test passes in isolation).

**Files.** `docs/DECISIONS.md` (B-175), `docs/CHANGELOG.md`, `docs/WORKLOG.md`. The corpus database and PDFs are gitignored data files.



## 2026-11-01 — [code] Q-16 per-document page cap (B-174)

**Ask.** Prevent one corpus document from supplying every dimension of a paper (Q-16). Step 11 of DATABASE.md explicitly requires the cap: "Two different pages of the same book can each fill a dimension (subject to the Q-16 cap)."

**Did.** Changes across `src/bp/product/retrieval.py`, `src/bp/product/sources.py`, `src/bp/product/completion.py`, `src/bp/product/chat.py`:

1. **Per-document page cap.** `retrieve()` gains `corpus_doc_cap` (default 3) and `corpus_doc_counts` (shared dict threaded across dimensions). When accepting a corpus item, the cap is checked against `corpus_doc_counts[doc_id]`; at the cap, additional pages from the same document are dropped and counted in `dropped`. Live academic and web sources are not capped.

2. **`doc_id` on corpus items.** `sources._corpus()` now sets `doc_id` on each corpus item so the cap can be keyed per document.

3. **Shared counter per paper.** Both `completion.complete()` and `chat.py` create one `corpus_doc_counts = {}` per paper and pass it to every dimension's retrieval, so the cap holds per-paper, not per-call.

**Verified.** 28/28 tests in `tests/test_sources.py` pass (2 new Q-16 cap tests). 55/55 corpus build tests pass. Live verification: dimension 1 gets 2 pages from one doc (cap=2), dimension 2 gets 0 pages from that doc (cap exhausted). No method, preset, input, check or frozen-core entry changed.

**Files.** `src/bp/product/retrieval.py`, `src/bp/product/sources.py`, `src/bp/product/completion.py`, `src/bp/product/chat.py`, `tests/test_sources.py`, `docs/DECISIONS.md` (B-174), `docs/CHANGELOG.md`, `docs/WORKLOG.md`.



## 2026-10-30 — [design] The evidence rules relaxed, and the orientation set made free and topical

**Ask.** "we ahve to relax these rules becus ethey will suffocate the pipeline: The corpus must obey the pipeline's non-negotiables (CONDUCTOR_MANUAL.md §4): No invented evidence — every claim traces to a recorded source. Gaps are named, never filled — a missing page number is NULL, never guessed. No silent framework substitution. update teh manual with what we are discusing. you were told not to do fixes because that might mess up the system. on this: the HBR, expand it to include other sources similar to HBR depending on topic. HBR cannot cover everything. or propose alternative to hbr that is free and fast. on page numbers, its apa and harvard, no need to mention chapter or page number unless customers ask or if its needed whcih pipeline decides."

**Did.** Four rules landed in `CONDUCTOR_MANUAL.md` and are recorded as B-169. Documentation only — no code, no behaviour, no number and no frozen-core entry changed.

1. **"No invented evidence" is now "no unsourced claim."** A claim may be quoted or paraphrased from its source, as long as the paraphrase does not exceed what the source says. What stays forbidden is a claim with no source behind it, or a source that says something else. **This is not a new capability.** §6.2.8 already has the model-assisted full paper write one call per dimension from the items, and the validator already refuses a number, citation, link or mid-sentence proper noun that is not in the items. The old §2 bullet — "never evidence paragraphs" — was stricter than the shipped code, so §2 now says what the product actually does, and the two are reconciled.
2. **Only a substantive gap is printed.** A dimension with no evidence at all is still named in the paper, because the student must know the paper is thin there. A metadata gap — a missing printed page number, a missing edition, an unknown ISBN, an unknown date — is recorded as `NULL` and does not appear in the paper; the source is cited as it stands. Nothing is filled by invention and nothing is hidden: every gap is recorded whether or not it is printed. The reference list already behaved this way, rendering a missing year as `n.d.`
3. **A framework may be substituted when the substitution is declared and recorded.** The paper says which framework it applied and why it departed from the one the brief named; PESTEL is never the silent default; a brief naming an unwired framework is still refused unless a declared, recorded substitute fits it. The word "silent" was the operative prohibition, so the record is kept and only the automatic swap is removed.
4. **Citations carry no page or chapter locator by default.** APA 7 and Harvard cite a book as `Author (Year). Title. Publisher.` and an article as `Author (Year). Title. Journal, volume(issue), pages.` — an article's page range is its extent, not a locator. A locator is added only when the student asks for one or when the pipeline decides the claim needs one (a quotation, a disputed figure, a passage to check), and that decision is recorded. The page a claim came from is kept in the record either way, so a locator can be produced on request without searching again.

**Also recorded — the orientation set is now topic-dependent and free-first.** Harvard Business Review is one candidate rather than the anchor, because most of it is paywalled. The set follows the brief's topic and prefers sources that are free, fast and open: strategy and operations practice (McKinsey Insights, BCG Perspectives, Bain Insights), technology and venture reporting (Sifted, TechCrunch), and open policy and think-tank literature (Brookings, PIIE, CEPR, VoxEU, Bruegel, and the World Bank, IMF, OECD, ECB, BIS and Federal Reserve working-paper series). A marketing brief reads the marketing set, an operations brief the operations set, a macro brief the economics and policy set.

**And the citable full-text corpus turns out to be free as well** — this is the useful discovery. OpenAlex now serves full text directly through its content API (`content.openalex.org/works/{id}.pdf`, filterable with `has_content.pdf:true` and CC-BY licences, and it also serves GROBID XML, which gives section structure for free). Alongside it: DOAJ, NBER, SSRN and RePEc working papers, and **OpenStax** — peer-reviewed, openly licensed, free-PDF business textbooks covering accounting (volumes 1 and 2), finance, economics, management, marketing, business ethics, business law, entrepreneurship and organisational behaviour, which maps almost exactly onto the pipeline's subject list. The licence is **per title** (CC BY on some, CC BY-NC-SA on others) and must be checked before ingesting. CORE is a further open-access full-text source, but its systematic PDF harvesting needs permission and its commercial terms need checking.

**Recorded.** B-169 records all five changes with the rationale for each, including which are already true of the running product and which are owed in code. §13 now states that split explicitly, so no future reader mistakes a declared convention for a shipped behaviour.

**Verified.** Read back in the manual: §2 carries the paraphrase permission and the new locator rule; §4 carries the three relaxed rules; §9 carries the topic-dependent orientation set and the open-access harvest; §1's evidence row now names the corpus first; §13 carries the not-yet-wired limit and the two-of-four split between what already ships and what is still owed.

**Files.** `docs/CONDUCTOR_MANUAL.md`, `docs/DECISIONS.md` (B-169), `docs/WORKLOG.md`, and `corpus-db/CORPUS_DB.md` outside the pipeline repo.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. Nothing was committed by this increment. Three changes are **owed in code** and are not done here: the declared framework substitution (the refusal path is unchanged), the on-request locator (`writing._in_text()` has no locator field today), and the report line that says the report quotes titles and abstracts — which becomes false the moment full text is retrieved. The corpus layer, the orientation pass and the open-access harvest land with the corpus build.

## 2026-10-30 — [design] The corpus, the full-text gate, and the orientation pass

**Ask.** "on 1. put it in the manual to discard that rule of throwing away book because of that keyword and title issue. 3. they are mix. the subjects are already in the pipeline, accounting, management, finance, economics, etch, everything about business. speaking about hybrid, ive thought about hybrid sources because not all sources would come from books in business. of course, primary sources are books and better have our own database for faster download. im also thinking including relevant journals to enrich the database up to 10 gb. now, tehre will be instances that pipeline need journal sources, so it has to use api and the research mechanism it already has. it will also research web sources needed. to relax research, im thinking of allowing it to use harvard business review and other reputable sources to run in its background to orient it just like what i did in write smarter. let me know what you think."

**Did.** Three rules were recorded in `CONDUCTOR_MANUAL.md`. Documentation only — no code, no behaviour, no number and no frozen-core entry changed.

1. **The source order is now layered (§9).** The local corpus is layer 1 and is searched first: the owner's own books and selected journals, held page by page. The live academic APIs (OpenAlex, Semantic Scholar, DOAJ; Crossref for metadata) are layer 2, and the curated web is layer 3. No layer replaces another — the corpus is owned, page-exact and instant; the APIs still answer what the corpus does not; the web still supplies what neither can. The corpus layer is marked **not yet wired** in the manual's current limits, with the design record at `corpus-db/CORPUS_DB.md`.
2. **The title rejection is discarded for full-text sources (§6.2.3, §6.3.3).** The title rule is a rule about *abstract-only* records, where a title and an abstract are all that exist and the title is therefore the only signal of what the source is about. A source that carries its own text — a book page, a chapter, a full-text article — is no longer rejected for lacking the dimension cue in its title. It is accepted when the cue appears in the **passage that will be quoted**, the context word appears in the text, and the geography rule still holds; one occurrence in the passage is enough, because the passage is the evidence. The title is never sufficient on its own for a full-text source. The abstract-only databases keep the title rule exactly as it is, so the pilot's precision rule is untouched. This is the rule that would otherwise have thrown away every book result without saying so: a book is titled for its subject, not for the sentence on page 143.
3. **The orientation pass (§9).** The product may read reputable practice and business-press sources — Harvard Business Review and the like — before retrieval, to widen the vocabulary and the framing of the brief, in the manner of Write Smarter's researcher. It is recorded as **advisory only**: it never enters the evidence list, never carries a citation, is never quoted, its failure is a notice rather than a gap in the paper, and it may never delay the retrieval pass.

**Recorded.** B-168 records all three, with the rationale for each and the boundary that keeps the orientation pass out of the citation path. The manual points at `corpus-db/CORPUS_DB.md` for the corpus design, and that living record carries the open questions, the data model, the Meilisearch index settings and the build sequence.

**Verified.** Read back in the manual: §6.2.3 now carries the full-text rule with the "one occurrence in the passage" clause and the explicit statement that the abstract-only path is unchanged; §6.3.3 lists the full-text rule as an alternative declared by source kind; §9 carries the three layers with the corpus marked not yet wired and the orientation pass marked advisory only; §13 carries the not-yet-wired limit, so no future reader mistakes the manual for a description of the running product.

**Files.** `docs/CONDUCTOR_MANUAL.md`, `docs/DECISIONS.md` (B-168), `docs/WORKLOG.md`, and `corpus-db/CORPUS_DB.md` outside the pipeline repo.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. Nothing in the working tree was committed by this increment. The manual now declares a rule the product does not yet implement: the corpus layer, the full-text gate and the orientation pass all land with the corpus build, and until then the academic and web layers answer alone. The live run that §6.3 requires before a gate change is recorded as still owed — it is attached to the corpus build, and it is the first open item in the corpus build sequence.

## 2026-10-30 — [design] The tile that names a tool now opens that tool

**Ask.** "in management and strategy subject, the section that with computation compare strategic options is not clickable. when i click it, it just loop me on top".

**Did.** The Management & strategy shelf's only computation tile, **Compare strategic options** (`case_decision`), opened nothing and threw the page back to the top. The tile was fine; the routing behind it was not. `createSession()` called `show("new")` **before** the session existed, and `RENDERERS.new` - the renderer added on 2026-10-29 so that a reload cannot land on an empty session page - sends a student who has no session back to the last durable screen. So the click was routed back to the subject page, the re-render of that page replaced the DOM and threw the scroll to the top, and the session that was created a moment later rendered into a panel that was by then hidden. The student saw a dead tile and a jump to the top, and the session was lost with it.

The panel is now **activated** (`activate("new")`) rather than shown while the session is created: the "Creating the session" card stays on screen, and the tool opens where it was asked for. `show("new")` is still used by the worksheet path, where a worksheet exists before the panel is shown and the renderer has something to render. One fix repairs every computation tile on every shelf - Finance's net present value took the same path and was equally dead. **Also fixed on the page the owner reached:** the "Enter the figures" panel told every method that "the engagement is declared once: the period, the chart, the opening balances, the entries and any schedules". That is the management-accounts engagement; it is false for a net-present-value comparison, so the sentence now follows the method (B-167).

**Recorded.** B-166 records the routing rule - *a control on a shelf that names a tool opens that tool*, and a renderer with nothing to show may redirect only on a reload, never in the middle of a student's own click. B-167 records the figures-panel wording rule. Both are presentation and routing: no method, preset, input, check, computed number, endpoint or frozen-core entry changed.

**Verified.** On the served page: Management & strategy → **Compare strategic options** now opens the case editor with the worked example loaded (two facts, two alternatives, the rate and the decision rule), and **Apply figures and calculate** runs it to a result - the worked example's own numbers from the frozen core: NPV USD 2,586.47 for *Expand the shop* against USD 2,136.83 for *Office catering* at 8.00%, the order flipping at a 10.16% discount rate, with the limitations stated. Finance → net present value opens the same way. The inline script parses (`node --check`). `scripts/ui_smoke.py` gains a marker for the routing and reports **0 failures** against the running workbench. The suite runs **2457 tests with 49 failures**; the failure list is a **subset of the list taken without this change** (captured both ways: 55 failures with this increment's files reverted to HEAD, 51 when the increment was first applied, 49 after the concurrent lane landed an edit to `src/bp/templates.py` mid-session). Every one of them is the concurrent framework-completion work - the value chain, TAM, STP, PESTEL and RFM outlines, worksheet form kinds, the operations and people page content, the documented test count and build, and one network-dependent search fallback. **No failure is new.** Two new trap tests pin the routing and the wording.

**Files.** `web/index.html`, `tests/test_product_subjects.py`, `scripts/ui_smoke.py`, `docs/DECISIONS.md` (B-166, B-167), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`. For the same reason the documented test count (1847) and build (1.47) are left alone - they are already behind the real suite and the newest changelog entry (1.53), and that drift is the concurrent lane's to close. Two things are recorded here rather than changed, because both belong to the frozen core or to the concurrent lane: the recorded-value panel shows a Python repr for list inputs (`Facts [{'text': ...}]`) because the orchestrator stores every input value as `str(v)`, and the session page shows the same value again in full JSON under "The recorded values, verbatim"; and the exported result is unchanged by any of this.

## 2026-10-29 — [design] The Home slogan loses its final period

**Ask.** "REMOVE THE PERIOD AFTER ASSISTANT".

**Did.** One character, in the Home hero: the lead now reads "Your reliable business writing assistant", with no full stop, in both places it lives - the static markup and the `RENDERERS.home` rebuild - so the first paint and the re-render agree. Nothing else moves: the claim stays in the bold 19.8 px lead, the three proofs stay in the italic 15 px line under it with their own full stops, and the line break between them is still what separates them. The effect to look at: the lead now reads as a phrase rather than a finished sentence, with the weight step and the line break carrying the emphasis instead of the punctuation.

**Recorded.** The entry above (same day) says "the slogan is untouched" and cites B-094's clause "the slogan must not be changed" and B-162's clause "the slogan stays". Both were the owner's own guard against unasked-for edits, and the owner has now asked for this edit, so both clauses are revised rather than quietly broken: **B-164** records the change and both earlier rows point at it. The wording of the slogan is otherwise exactly as the owner wrote it.

**Verified.** On the served page the lead reads "Your reliable business writing assistant" with no trailing full stop, in the first paint and in a re-render; the proof line is unchanged. The inline script parses (`node --check`) and the full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 22; section 3's live-copy note), `docs/DECISIONS.md` (B-094 and B-162 status cells, B-164 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 — [design] Home drops its subject tagline

**Ask.** "DELETE THIS FROM THE HOME PAGE: BUSINESS | ACCOUNTING | ECONOMICS | FINANCE".

**Did.** The `BUSINESS | ACCOUNTING | ECONOMICS | FINANCE` line is gone from the Home hero. It lived in two places - the static markup and the `RENDERERS.home` rebuild - and both were changed, so the first paint and the re-render agree. The hero now reads logo, wordmark, slogan. The slogan is untouched ("Your reliable business writing assistant." / "Real computation. Real research. Verifiable."), so the other half of B-094 - the slogan must not be changed - still stands. The CSS that only served the line went with it (`.tagline`, `.hero .tagline`, and the narrow-layout `.topbar .tagline`, which had no other user in the page); the hero's own spacing is unchanged, so the block tightens by one line and nothing else moves.

**Recorded.** B-094 pinned that tagline ("exactly as written"). The owner set it and has now reversed it, so B-094 is marked superseded on that line and the reversal is recorded as B-162 rather than made silently.

**Verified.** The tagline text is absent from the served document, from the inline script and from the rendered hero, in the first paint and in a re-render; the slogan is still there, unchanged. The inline script parses (`node --check`) and the full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 20), `docs/DECISIONS.md` (B-094 superseded, B-162 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 — [design] The collapsed rail shows its icons in full

**Ask.** "recheck the side rails when they are collapsed. the icons are not fully showing. adjust their width so that icons can still be seen in full even when collapsed".

**Did.** The defect was in the collapsed rail's geometry, not in the icons. The subject list scrolls inside the rail, and a vertical scrollbar takes the scrollport's right edge: with the list scrolling, the scrollport ended at x = 30 instead of x = 40. The icon column is right-packed inside the green strip (design note 10), so every glyph sat at x = 18.5 -> 37.5 - under the scrollbar's column - and was cut at x = 30. The Accounting glyph measured 10 px of ink instead of its own 17 px: the book was cut in half. It was window-height dependent (the list only scrolls when the rail is shorter than the list), which is why a measurement at 1400x900 showed a whole glyph and hid the fault.

The fix is the width the owner asked for: the collapsed rail is now the strip plus a column for the scrollbar. `--rail-sb:16px` and `--rail-w-collapsed:calc(var(--rail-w) + var(--rail-sb))`, applied by `body:not(.rail-open) .rail{width:var(--rail-w-collapsed)}` - 61 px in the wide layout, 60 px in the narrow one (`--rail-w:44px` there). The green strip keeps its own width (`.railaccent` is still `--rail-w`), so the open rail is untouched and the new column is the white one the labels start in; the scrollbar lands there instead of on the icons. `--rail-ic-pad` did not change, so the icons did not move: the glyph is still at 18.5 -> 37.5. The collapsed toggle now hugs the strip (41 px) rather than the whole rail, and its chevron is walked back onto the icon column by hand (`translateX(calc(var(--rail-ic-pad) + var(--rail-ic-w) / 2 - (var(--rail-w) - var(--rail-pad)) / 2))`, 3.5 px), so it still sits over the icons.

**Recorded.** The owner instruction sets a geometry convention - the collapsed rail is the strip plus the scrollbar's column - so it is recorded as B-165.

**Verified.** On the served page (`127.0.0.1:8765`, Chrome, device pixel ratio 1): collapsed with the list scrolling (1400x700) the rail is 61 px, the scrollport is 4 -> 46 and the glyph 18.5 -> 37.5, fully visible - the ink of every glyph is its full width (19 px; the Accounting glyph 17 px, the shape's own width), against 10-11 px before. Collapsed in the narrow layout (760x700): rail 60 px, strip 44 px, scrollport 4 -> 45, glyph unchanged and fully visible. Open (1400x900): unchanged - strip 0 -> 45 px, glyph 18.5 -> 37.5 px, the label column and the "SUBJECTS" heading both at 55 px. `scripts/ui_smoke.py` carries the new rail-geometry markers so the column cannot be silently dropped, and passes against the served page. The full suite passes. No `src/bp/**`, `tests/**`, fixture, number, claim or endpoint changed.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 17), `scripts/ui_smoke.py`, `docs/DECISIONS.md` (B-165 added), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier design increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-29 - Pricing wired to PayPal, with the credits left open

**Ask.** Wire Smart BusinessWriter's pricing to PayPal at Starter $14.99, Pro $29.99, Studio $49.99 and a fourth tier at $99.99, with an annual plan cheaper than monthly, make a payment actually go through, and build the design so credit allowances can be added later — the owner does not know them yet.

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

## 2026-10-29 — The computation explainer travels with the paper

**Ask.** "when something in the paper has computation, the explainer will automatically accompany it" and "its file name will be title-explainer_format."

**Did.** New product-layer `explain.py` and `explain_html.py`, a committed method-contract slice (`data/explain_contracts_v0_1.json`, regenerated by `scripts/generate_explain_contracts.py`), and a `render_note` renderer in `docx.py`. The explainer is a teachable document, not an audit sheet: question, why this method, the declared formula and steps from the catalogue's study notes, the declared figures, the values the frozen engine recorded (with their derivations), what the result means, the declared checks, common mistakes, the defaults applied, the limits and unsupported uses, an "If your professor asks" Q&A, and a small record appendix. Accounting cases add the recorded journal, T-accounts, trial balance, statements, reconciliation and PASS/FAIL checks.

**Packaging.** A paper with at least one delivered computation now exports as one ZIP containing `<slug>.docx` and `<slug>-explainer.docx`; a paper without a computation keeps the plain Word download. The paper export gate runs first, so an incomplete paper produces no partial ZIP. The same explainer is available alone from `POST /api/cases/{id}/explanation` and `POST /api/cases/chat/{id}/explanation`; the case page, calculator result, chat paper and plan expose the action, and the case page labels the submission download "Word + explainer" when a computation is present. Print-ready HTML is returned where the paper is HTML, so the student can print to PDF without a PDF writer.

**Verified.** `tests/test_product_explain.py` (22 tests): the contract slice matches all 140 core methods; every calculator method has a contract or a declared template; every method without notes is in the declared 10-tool gap set; the explainer imports no core module; the break-even document quotes the recorded inputs/outputs and is a deterministic valid `.docx` with a table; the accounting document contains the journal, T-accounts, trial balance and PASS checks; a paper with five computations produces one companion; a paper without a computation is refused; the ZIP contains exactly the paper and the explainer with hashes; the routes return Word, HTML, 422 for no computation and 409 for a blocked paper. Live on `http://127.0.0.1:8033/`: the calculator run produced case `5dcfb8feaf75`, "Download the explanation" returned 200, the case page labelled the submission "Word + explainer", and the download was `how-many-units-must-we-sell-to-break-even-submission.zip` with two files. No frozen method, preset, input, check, number or frozen-contract entry changed.

**Files.** `src/bp/product/explain.py`, `src/bp/product/explain_html.py`, `src/bp/product/docx.py`, `src/bp/product/api.py`, `src/bp/product/data/explain_contracts_v0_1.json`, `scripts/generate_explain_contracts.py`, `tests/test_product_explain.py`, `web/index.html`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`.

**Open/next.** Ten statistics tools still have no catalogue formula/steps note and are named as gaps; writing those notes removes them from `explain.NOTES_GAPS`. A true server-side PDF still needs a converter or a writer; the HTML path is the current print-to-PDF route.

## 2026-10-28 — [design] "My account": the account this product actually has

**Ask.** Take the attached hosted account page as inspiration and build one for Smart BusinessWriter, curated to this product rather than copied where it does not apply.

**Did.** `web/account.html`, served at `/account.html`. The hosted page's identity, subscription, payment history, tag manager and search-engine metadata did not survive the transfer: this product stores no identity, wires no payment system and makes no external network calls, so the page says so on its face rather than shipping an empty form. What did survive is what actually exists here — the machine (served build, health, case store and state directories, sandbox and model-assistance flags), the work stored on it, and the export wallet that meters exports.

**Did — the wallet became visible.** `src/bp/product/credits.py` already kept an append-only ledger with a derived balance, a price table and a 100-credit free tier, but nothing could read it, so the balance was invisible to the user. `GET /api/cases/credits` returns that module's own receipt unchanged — read-only, and it cannot charge anything. `GET /assets/<file>` serves the logo and the tab icons, so the page needs no inlined data URI and no remote asset.

**Verified.** On the served page (127.0.0.1:8766, Chromium) every figure is live: the machine's facts, the eight most recent cases with their methods and dates, the wallet balance and its ledger, the catalogue counts. Every request the page makes returns 200, and `/assets/../server.py` returns 404. The suite passes.

**Files.** `web/account.html` (new), `web/index.html` (the account pill now links to the page), `src/bp/server.py`, `src/bp/product/api.py`, `README.md`, `web/DESIGN_NOTES.md` (section 14), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the earlier increments: the build number is in flight in the concurrent lane, and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-28 — The sample papers are generated by the product

**Ask.** The owner pointed out that an APA/Harvard formatter already existed, so the samples were not
blocked on writing. Accepted recommendation: reuse the sources already in the repo for Ansoff and Value
Chain, no external sources for VRIO and Break-even, and a short guide. Filenames: title - framework - style.

**Did — the builder.** `scripts/build_conductor_samples.py` drives the real conductor for each framework and
style and calls `chat.docx_bytes`, which enforces the export gate and renders `render_academic`. Eight files
in `samples/`: Ansoff, Value Chain, VRIO and Break-even, each in APA 7 and Harvard.
`scripts/sample_evidence.py` freezes nine sources already cited in the Apple-Iran paper, with the claim each
supports and the dimension it backs; nothing was newly retrieved or invented.

**Did — two product defects the samples exposed.** The academic renderer wrote `Author: [your name]` and
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

## 2026-10-28 — Four more conductor frameworks, and a computation that travels

**Ask.** After the question "are the backend compute and frameworks done?", the answer was: compute is
broad, but the conductor composed only PESTEL, SWOT, PESTEL + SWOT, Five Forces and Five Forces + Break-even.
The owner chose all three follow-ups: wire the recommended frameworks, allow a framework + computation
generally, and keep the UI with the design lane.

**Did — frameworks.** `chat.py` gains Value Chain (nine activities), Ansoff (four options), VRIO (student
resources and four judgments, no external evidence) and Break-even (computation only). Each has a question
bank (`VALUE_QUESTIONS`, `ANSOFF_QUESTIONS`, `VRIO_QUESTIONS`, `BREAKEVEN_QUESTIONS`), search cues for the
evidence dimensions, plan wording (`why`, `misses`, `output`, checkpoints), a draft branch with the H1/H2
hierarchy, a Discussion integration where one applies, and limits that name what the framework cannot do.
Inference recognises the four names, and a break-even or VRIO brief is no longer refused by the subject
guard as "a computation, not a strategy".

**Did — computation attachment (Phase B).** `attach_computation(state, "breakeven", values)` validates
`fixed`, `price` and `variable` through the frozen `breakeven` method *before* storing them, refuses a price
below variable cost with the core's own message, and stores the inputs on the state. The draft adds the
Financial Feasibility H1 and Break-even H2 to any evidence framework, plus the integration paragraph, the
limitation and the title suffix. `POST /api/cases/chat/{id}/computation` exposes it. The Five Forces +
Break-even key, label and questions are untouched.

**Did — gate.** `paper.missing` now requires a VRIO paper's resources and at least one value judgment, and
names missing break-even inputs on an attached computation.

**Tests.** New `tests/test_conductor_frameworks.py` (20 tests): registration, dimension counts, the refusal
message naming the new options, inference, plan wording, the nine/four/five-section drafts, verbatim student
judgments, a named gap where evidence is empty, the core break-even figures, attachment refusals, the export
gate and the API route. Full suite: 1560 tests pass.

**Not done, and named.** APA and Harvard sample papers for the four frameworks (manual §5 item 10); the UI
affordance for the attach endpoint belongs to the design lane, as agreed.

## 2026-10-28 — [design] The last unusable Entrepreneurship tile gets its editor, and schema forms get controls

**Ask.** "How about the other features of the entrepreneurship subject? Have we built the UI?"

**Did.** Checked every one of the 46 tiles in Chromium. Forty-five launched a real method; **Compare strategic options (`case_decision`)** did not, because it is a template rather than a frozen method. The generic form looked up `/api/methods`, found nothing, said "This method declares no inputs", and Apply dropped the preset; the engine then refused with "`facts` must be a non-empty list". (1) Added a dedicated **case facts and alternatives editor** to the tool screen: facts with stable `F1..Fn` ids, provenance and source; two to five alternatives with name, description, cash flows from t=0, supported fact ids, cash-flow provenance and source; base rate, range, rate provenance, decision rule and currency; bounded add/remove rows. `collectInputs` reads it, `applyAndRun` posts the normal session and confirm pair, and the delivered result uses the existing result page. (2) The **Business Calculator** now delegates `case_decision` to that editor instead of showing an empty pad. (3) The generic schema form now renders `enum` inputs as dropdowns, `value_list`/`code_list` as comma-separated fields and `value_matrix` as an explicit JSON row editor; records, tables and maps keep their existing editors. (4) Added static page guards for the editor, the calculator delegation and the new input types.

**Verified.** Chromium on the served page: the case tile rendered 2 facts and 2 alternatives with the worked example; Apply delivered USD 2,586.47 for Expand the shop and USD 2,136.83 for Office catering with a 10.16% crossover; add/remove produced 3 facts and 3 alternatives, then 2 alternatives. The proforma tile showed `1200000, 1500000, 1800000` instead of JSON and delivered revenue 4,500,000 and net income 360,000. The depreciation method was a real `SELECT` with `straight_line` selected. The calculator's case tool opened the same editor. No console errors. `node --check` clean; full suite 1540; CI 3/3.

**Files.** `web/index.html`, `scripts/ui_smoke.py`, `tests/test_product_subjects.py`, `docs/CHANGELOG.md`, `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, `WORKLOG.md`.

**Open/next.** The remaining standalone JSON surfaces are records, tables and maps, which already have editors or intentional JSON; no tile is schema-less now.


## 2026-10-28 — [computation/product] A business plan is a paper profile, with all its computations

**Ask.** Add a complete business-plan capability: every computation a plan needs, brief upload, customisation, and an entry point from both the Entrepreneurship page (strict convention) and Home (open composition), without inventing a fact, a source or a number.

**Did.** (1) Four T1 methods join the frozen core, each with a float second route and five checks: `sales_from_market`, `depreciation_schedule`, `proforma_statements` and `sensitivity_table`. The projected statements build an income statement, cash flow and balance sheet from declared revenue, margin, costs, depreciation, interest and principal (or an opening loan), tax, working-capital days and opening balances; the opening balance sheet must balance and an unbalanced opening is refused with the equity that would balance it, and a loan repaid faster than it is owed is refused. Presets `depreciation`, `proforma`, `frommarket`, `sensitivity`; README list, calculator slice and frozen fixture regenerated (140 methods, 142 presets, B-148). (2) `bp.product.chat` gains `PROFILE_BUSINESS_PLAN`, `PLAN_SECTIONS`, `PLAN_FIELDS` and `COMPUTATION_BLOCKS`. A plan composes student input, evidence, computation and integration sections; the Financial Plan is one H1 with its blocks as H2s. SHS requires sales from market, break-even, depreciation, projected statements and sensitivity; college adds tax, the cap table and a cost-effectiveness impact ratio. `customise` changes level, composition or (open mode only) an optional section; `set_inputs` stores the student's words; `compute` calls the attached frozen core and stores the declared inputs and result; `draft` composes the plan and never states a figure that is not in a stored result or a supplied input. (3) `paper.missing` is profile-aware: every required field and block is named, a refused block is named with its reason, and the route returns 409 with the list. (4) `documents.extract_docx` reads `word/document.xml` with the standard library; `extract_txt` handles UTF-8, UTF-16 and Windows-1252; `extract_document` dispatches PDF, DOCX, TXT and images; the brief route returns `ocr_required` rather than guessing a scan. Intake now treats `.docx` as a document. (5) The Entrepreneurship page opens the plan in strict mode; Home opens open composition; a new Plan panel renders the proposed structure, a form per block from its declared schema, the evidence review, the draft and the export gate. (6) Entrepreneurship now exposes capacity, inventory, market concentration, ratios and cost-effectiveness on the page, with the nine new tiles grouped. (7) Tests: `tests/test_business_plan_core.py` (20) and `tests/test_business_plan_profile.py` (38), plus the four methods in the sandbox/session cases; `tests/test_business_plan_profile.py` covers the hard refusals, the readers and the routes.

**Verified.** `python scripts/generate_subjects.py` (158 records, 11 subjects, 143 compute tools), `python scripts/econ_shelf.py --fixture` (140 methods, 142 presets), `python scripts/generate_calc_inputs.py` (140 methods), full suite 1536 tests green, `python scripts/ci.py`. In-process plans: SHS draft has 11 H1s and the Financial Plan H2s in order; college adds Funding and Ownership and Social and Environmental Impact; an unbalanced opening balance gives `set opening_equity to 250000` and blocks export; the Word file is produced only when the gate passes. `node --check` on the served script is clean.

**Files.** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/product/chat.py`, `paper.py`, `api.py`, `documents.py`, `intake.py`, `subjects.py`, `src/bp/product/data/calc_inputs_v0_1.json`, `tests/fixtures/frozen_contract.json`, `src/bp/data/registry_v0_2.json`, `web/index.html`, `README.md`, `docs/CONDUCTOR_MANUAL.md`, `HANDOFF.md`, `CHANGELOG.md`, `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `CURRICULUM_MAP.md`, `ENTREPRENEURSHIP_STUDENT_GUIDE.md`, `BACKEND_CONTRACT.md`, `HOME.md`, `WORKLOG.md`, `tests/test_business_plan_core.py`, `test_business_plan_profile.py`, `test_sandbox.py`, `test_session_api.py`, `test_entrepreneurship.py`, `test_product_documents.py`.

**Open/next.** A restricted set of blocks is deliberate: no monthly pro-forma, multi-product mix, disposal, group consolidation or jurisdiction tax law. The plan's market evidence depends on the source finder; a dimension with no match stays a gap. The plan builder currently asks for every declared figure as text; structured period tables would be a presentation increment, not a new computation.

## 2026-10-28 — [design] The hero's promise steps up, its proof steps aside

**Ask.** On the Home page, "Your reliable business writing assistant." must be bold and slightly bigger, and "Real computation. Real research. Verifiable." must be italicised and smaller.

**Did.** The slogan paragraph now carries two spans instead of one string and a break. The promise line is 19.8 px at weight 700, up from 18.0 px regular; the proof line is 15.0 px and italic, down from 18.0 px and the size of the page's `.sub` body text. The colour is unchanged, so weight, size and slant carry the hierarchy and nothing else moves. Both copies were changed - the static markup in the served page and the string `RENDERERS.home` rebuilds on every visit - so changing one alone would have reverted the other on the next render.

**Verified.** On the served page (127.0.0.1:8765, Chromium) the Home hero shows the promise line bold at the larger size and the proof line italic at the smaller one, and the rendered DOM carries both spans with their classes.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 13), `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry, for the same reason as the rail increment: the build number is in flight in the concurrent lane - the pill moved twice while this was written - and the changelog's newest build is tied by a test to the build string in `HOME.md` and `HANDOFF.md`.

## 2026-10-28 — [design] The rail keeps the subject marked while you work inside it

**Ask.** "continue your unfinished fix in the left rails" — the left rail lost its green highlight the moment a student opened a subsection of a subject, and the previous run ran out of credit before that fix was verified, recorded or committed.

**Did — the defect.** The rail marked the panel it was on (`a.dataset.panel === id`), and a subject's workspace is not a panel: no rail item carries `data-panel="new"`, `"results"` or `"deliver"`. Opening a worksheet, a tool, the run it produced or the deliverable therefore cleared `aria-current` from every item, so the subject the student was working in went out of the rail entirely - no green word, and nothing to click their way back to.

**Did — the fix.** `state.railSubject` remembers the subject the rail is holding: set when a subject page is opened, kept while the panel is one of that subject's own workspaces (`SUBJECT_WORKSPACE = ["new", "results", "deliver"]`), released by every other panel. The marking moved into one shared `markCurrentRailItem()`, called by `activate()` and by `renderRailSubjects()` after the subject list is rebuilt from the API - a mark applied before that redraw was lost with the old elements. The mark is an attribute on a link, so no behaviour, wording, number, endpoint or test changed.

**Verified.** On the served page (127.0.0.1:8765, Chromium), with a temporary log inside `markCurrentRailItem` recording the active panel, the held subject and the number of marked rail items, every transition was read back: the subject page marks the subject (1 of 14 items); a worksheet opened from it keeps the subject marked (1 of 14, with `aria-current="page"` on that link in the DOM); the Business Calculator releases it and marks the Calculator; returning to the subject marks the subject again; Home releases it and marks Home. The instrumentation was removed afterwards, and `scripts/ui_smoke.py` now carries the rail markers so the fix cannot be dropped silently.

**Suite state.** 1484 pass, 3 fail - all three from the concurrent slice and none from this change: the calculator router knows 136 methods against 140 in the catalogue, the Entrepreneurship shelf text, and the test count documented in `HOME.md`. This entry touches `web/index.html` only.

**Files.** `web/index.html`, `web/DESIGN_NOTES.md` (section 12), `scripts/ui_smoke.py`, `docs/WORKLOG.md`.

**Open/next.** No `docs/CHANGELOG.md` entry was written: the build number is in flight in the concurrent lane (the pill is already at v1.24 with no matching entry), and the newest build in the changelog is tied by a test to the build string in `HOME.md` and `HANDOFF.md`, so writing it here would either collide with that increment or edit its lines. The changelog line for this increment belongs with the next build that carries it.

## 2026-10-28 — The marketing shelf finishes its assignments

**Ask.** After the RFM and media-planning increment, the owner asked what was still open for a marketing
student and chose all five items: worksheets for the read-only records, customer profitability, market share
and penetration, discounted customer value, and a sandbox guard.

**Did — five worksheets.** `template_customer_journey` and `template_servqual` on the declared-matrix
machinery (touchpoints against stages; service dimensions against expectation, perception and your gap), and
`template_kano`, `template_paid_media_plan` and `template_measurement_plan` on the canvas machinery. Every one
inherits the shared builder, renderer, nine- or eight-check audit and refusals: empty blocks and cells are
named, sourced items need a source, unknown blocks and cells that cite unknown rows are refused, and no score,
ranking, average, probability or verdict is produced. The Kano category and the SERVQUAL gap stay the
student's: deriving either inside the worksheet would put judgment or arithmetic in the product layer. Five
worked examples were added to `T.EXAMPLES`, so the sandbox equality test covers them too.

**Did — three computations.** `market_share` (share, change from a declared prior period, implied growth,
penetration, relative share), `clv_model` (discounted and undiscounted value over a horizon at constant churn
and discount, value per unit of acquisition cost, undiscounted payback only when it is reached) and
`customer_profitability` (profit, margin, profit share by segment, profitable counts, concentration count).
Each has a float second route, five frozen checks, refusals and a token-only report.

**Did — truth.** `QNT-MKT-07` now links to `customer_profitability`; `QNT-MKT-02` gains `market_share` and
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

## 2026-10-28 — The Business Calculator: the main-line shell and sentence router, harmonized with this line

**Ask.** "check the calculator or business calculator, its in the main git. cline worked on it but ran out of credit. finish the job" and "harmonize it with the local file also so i can see how it works."

**Did.** Ported the main-line Business Calculator (main builds 0.74-0.76) onto `design/v0.73-rail`, where the served page had kept the older launcher. `web/index.html` gains the P1-P3 shell from `docs/proposals/BUSINESS_CALCULATOR_DESIGN.md`: tool selection stays in the panel, a display names the method and its declared inputs, a 16-key pad edits the focused field (operator keys move focus, they never evaluate), fit badges separate keypad tools from list/table tools and worksheets, and `=` posts the normal `POST /api/sessions` -> `POST /api/sessions/{id}/confirm` pair. A delivered run is recorded automatically through `recordCalcCase`, and a recording failure is reported. The panel's search is now global rather than group-only. An **Ask instead** toggle posts the sentence to the new `bp.product.calc_router` through `POST /api/cases/calculator/plan` and renders one of five declared outcomes. The router imports no core module and reads `src/bp/product/data/calc_inputs_v0_1.json`, regenerated from all **127 frozen methods** by the new `scripts/generate_calc_inputs.py`.

**Harmonization, not a copy.** The first build's vocabulary knew 36 methods; this line has 127. `SYNONYMS`, `CLUES` and `INPUT_WORDS` now cover the local shelves (tax, RFM, media planning, line balancing, marketing analytics, the economics models). Three defects the local catalogue exposed are fixed: schema inputs marked `required: false` are no longer reported as missing; a thousands separator is punctuation, so `84,000` becomes `84000` (same value) instead of the old `84`; and a `records`/`rows` input is never filled from a bare number, so "RFM segmentation for 20 customers" asks for the customer records instead of sending `[20]` as the list. `tax_declared` exists here, so VAT/income tax now routes to it rather than being refused as unsupported. Every reader-facing label says **Business Calculator**; the route, panel id and JS identifiers stay `calculator`.

**Verified.** `python -m pytest -q tests/test_product_calc_router.py` passes 18 tests, including the golden table, the "every figure is quoted" guard, the input-slice drift guard and a live `SessionManager` run for every `run` golden. Live on `http://127.0.0.1:8030/`: break-even opened in place, the keypad edited a field, `=` delivered and recorded case `e0cb4e2d32f4`; the tax preset delivered and recorded `b62cbdfd4789`; descriptive statistics ran with the keypad off; Ask parsed "break-even with 1500 fixed cost, price 25, variable 10" into the break-even plan; global search for "tax" returned 7 calculations across groups; the page produced no console errors and no browser arithmetic (`eval`, `Function`, `parseFloat`, `parseInt` absent). No frozen method, preset, input schema, computed number or frozen-contract entry changed.

**Files.** `web/index.html`, `src/bp/product/calc_router.py`, `src/bp/product/data/calc_inputs_v0_1.json`, `src/bp/product/api.py`, `src/bp/product/subjects.py` (note wording), `scripts/generate_calc_inputs.py`, `tests/test_product_calc_router.py`, `tests/test_product_subjects.py`, `docs/proposals/BUSINESS_CALCULATOR_DESIGN.md`, `mockup/business-calculator.html`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `SERVING.md`.

**Open/next.** Free-form arithmetic (decision D1) is still refused: `2 + 2` is out of scope and `=` runs a declared method, never an expression. The `calc_inputs` slice must be regenerated whenever a method's input schema changes; the drift test fails until it is.

## 2026-10-28 — The favicon loses its white card: true alpha from the logo, verified in a real tab

**Ask.** "continue this fix about the favicon" — locate the favicon sources, confirm the white-background defect, cut the book-and-bar mark out of `logo.png` with true alpha, render 16/32/64px tab icons and a 180px apple-touch icon on a transparent background, inline them into `web/index.html`, and verify in a real browser tab.

**Did — the defect, confirmed.** `web/assets/logo.png` is RGB (1284x1032, no alpha): the owner's PNG flattened onto solid `#FCFCFC` paper. The pre-fix inline icons (commit `a826fcf`) carried that paper with them. 25% of the 16px tile, 36% of the 32px, 41% of the 64px and 78% of the 180px were opaque white, and the apple-touch-icon was alpha 255 edge to edge — a solid white square. The tab icon therefore showed a white card around the mark.

**Did — the rebuild.** `scripts/generate_favicons.py` cuts the mark from the logo's book-and-bars block; the `Smart BusinessWriter` wordmark is deliberately left out, because a favicon must not carry it. Every pixel's coverage is keyed against the paper, and the gaps between the book's page strokes are sealed so the paper between them reads as the book's interior. The paper *outside* the artwork becomes transparent; the book's own pages stay opaque, so the book still reads as a solid object on a dark tab. Four PNGs — 16, 32, 64, 180 — are written to `web/assets/favicon-*.png` and inlined into `web/index.html` as data URIs, because the server serves only `/` and `/api/*` (`web/DESIGN_NOTES.md` open request 1). The script now writes each asset file from the same encoded bytes it inlines, so the committed PNGs are byte-for-byte the icons the page serves and cannot drift apart by a few bytes of PNG encoding; the four files are pixel-identical to the ones shipped in `8c686a6` and differ only in encoding.

**Verified.** The four inline data URIs decode byte-for-byte equal to `web/assets/favicon-*.png`; every icon has alpha 0..255 with all four corners fully transparent; the residual opaque white (0%/2%/2%/3%) is the book's own pages, not a card. In a real Chromium tab on `http://127.0.0.1:8765/` the page loads with no console errors and **no `/favicon.ico` request** — the browser accepting the inlined icons instead of falling back to the default path. A before/after harness renders the pre-fix and current icon sets over a simulated dark tab strip in Chromium itself, and the old set's 16px tile shows the white card pixel for pixel.

**Files.** `scripts/generate_favicons.py`, `web/assets/favicon-16.png`, `web/assets/favicon-32.png`, `web/assets/favicon-64.png`, `web/assets/favicon-180.png`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.

**Open/next.** The open request in `web/DESIGN_NOTES.md` for a `GET /assets/<path>` route is unchanged; until that route exists the favicons stay inlined. The in-page logo (`web/assets/mark.png`, still RGB on white) is unaffected: it sits on the white topbar, so it carries no card.

## 2026-10-28 — RFM and media planning: the two gaps a marketing student actually has

**Ask.** After the digital lane shipped, the owner asked whether the parked items — ad-platform and analytics
connectors, automated bidding, incrementality and holdout tests, multi-touch causal attribution, sequential
tests, budget recommendations — were needed by marketing students. The answer given was no for four of them and
"a concept, not a tool" for the other two, and the real gaps were RFM and media-planning arithmetic. The owner
chose both.

**Did — `rfm_scoring` (T1).** Quintile recency, frequency and monetary bands from a declared customer list.
Recency is ranked in reverse; ranks use competition ranking, so ties share the better band and band sizes can
differ; the eleven named segments come from a declared first-match rule set over the five-by-five grid
(`cannot_lose` first, `lost` last). Outputs are the segment sizes, the three mean scores and their sum; the
scored rows, the rule text and the label map travel in the appendix. Five frozen checks: an independent
band-boundary route built with integer ceilings, segment sizes summing to the count, bands inside one to five,
monotonic recency scoring and the combined mean as the sum of the three. Refuses fewer than five or more than
a thousand customers, duplicate names, negative recency and a frequency below one.

**Did — `media_plan` (T1).** Per vehicle: reach share, gross impressions, gross rating points, cost per rating
point and cost per thousand impressions; then the plan totals, a combined net reach under random duplication
and the average frequency that follows from it. Five frozen checks: a float second route, rating points as
reach share times frequency times a hundred, impressions as reach times frequency, plan points as the sum of
the vehicles', and a combined reach that lies between the largest vehicle and the sum. The report calls the
combined reach an upper bound and says the method does not recommend a buy.

**Did — catalogue and page.** Catalogue v0.4 appends one section-11.2 bullet, `QNT-MKT-15` (media planning), so
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

## 2026-10-28 — Line balancing and declared-rate tax; the rest named in the limitations

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

## 2026-10-28 — Closing the deterministic gaps: schedule, EVM, OEE, SPC, ABC, sales variances, M/M/c

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

## 2026-10-28 — Marketing & customers gets the digital lane

**Ask.** "go to marketing and customers, check if everything about marketing is there. looks like it does not
include digital marketing such as analytics and related things to it." Then: "texts should also be solid to be
more readable."

**Did — catalogue.** The catalogue source moved to v0.3: nine framework rows `MKT-13..MKT-21` (channel mix,
SEO/content, paid media, email and lifecycle, social and influencer, measurement plan, attribution, CRO and
landing-page testing, automation and lead scoring) and seven quantitative bullets in section 11.2
(`QNT-MKT-08..14`). RFM was listed twice — a framework row and a bullet — so the bullet now reads
"RFM Segmentation." and the importer merges it into `MKT-08` with `also_listed_as: ["QNT-MKT-04"]`; the
record count stays honest at 155. The importer gained `DIGITAL_IDS`, `DIGITAL_Q_PREFIXES` and a `Q`-branch
merge, so a digital row or bullet is tagged `digital marketing` rather than the section's classical
discipline.

**Did — computations.** Seven additive T1 methods in `src/bp/methods.py`, each with a float second route,
exactly five frozen checks, refusals for impossible counts (clicks above impressions, conversions above
clicks, reach above impressions, a zero churn, enumerator sums that do not close) and a token-only report:
`campaign_efficiency`, `ab_test_two_proportion`, `attribution_split`, `channel_economics`,
`email_list_health`, `social_engagement`, `web_analytics`. `ab_test_two_proportion` is the only one whose
claim ceiling is `associational`; it also takes an optional declared minimum effect and reports the visitors
each arm would need. Two presentation bugs the smoke tests exposed were fixed at the source: a failed
identity check (`CPC x conversion rate` is *not* CPA — CPA x conversion rate is CPC), and a payback figure
that was formatted as currency rather than a period count.

**Did — page.** `subjects.py` gains `MARKETING_GROUPS`, `MARKETING_PERIODS`, `MARKETING_NOTES` (the seven new
tools plus the alpha note that was missing), a 33-term `MARKETING_GLOSSARY`, a `DISCIPLINE_LABELS` map and
`discipline_label` on every catalogue row, so the records table reads "Marketing frameworks", "Customer and
market analytics" and "Digital marketing" instead of internal tags. The shelf is 19 tiles in four ordered
groups with period badges and study notes; `web/index.html` retitles the section and rewrites the legend to
explain what each status actually means.

**Did — wiring and truth.** Presets `campaign`, `abtest`, `attribution`, `channelecon`, `email`, `social`,
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

## 2026-10-28 — Increment 3: tree, projects and weighted-matrix editors

**Ask.** "go" after Increment 2.

**Did.** The decision tree is now built from alternatives and outcome rows; multi-project from project cards with
per-project activity tables; the weighted matrix generates score rows from the criteria table with a refresh action.
Add/remove works for each. The JSON field remains for nested decision trees and any schema without a guided form.

**Verified.** Browser: decision-tree preset renders 2 alternatives, 4 outcomes, no JSON, runs to expected value
52,000; multi-project renders 2 project cards, 4 activities, runs to overall duration 8; MCDA renders the criteria
columns and 3 alternatives. No console errors; 1531 tests pass.

## 2026-10-28 — Result polish: key numbers and direct exports

**Ask.** "go" after Increment 1: finish the student result screen.

**Did.** The result now shows **What this means**, a method-specific **Key numbers** table and the actions Save, View the
Gantt (CPM), Download spreadsheet (XLSX), Download Gantt (SVG) and Charts and exports. Saving uses a non-navigating
persist step so the download buttons reuse the same case; the full artifact table stays under **For audit**.

**Verified.** Browser: CPM run shows duration 12, 3 critical activities and 4 activities; XLSX export wrote
`exports/<id>.xlsx`; the SVG button renders the client Gantt; no console errors. 1467 tests at the time of the
increment; the concurrent `proforma_statements`/`costeffectiveness` method wiring is not part of this change.

## 2026-10-28 — Student UX layer: guided Home, plain tiles, table editors

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

## 2026-10-28 — Renderer extras: Gantt arrows, client SVG and XLSX bars

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

## 2026-10-28 — Generic Monte Carlo for non-schedule decisions

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

## 2026-10-28 — Decision batch C: decision tree, real option, weighted matrix

**Ask.** "start batch C".

**Did — methods.** `decision_tree` (rollback of a declared decision/chance/terminal tree with loss probability and range),
`real_option` (Cox-Ross-Rubinstein call/put, European or American, with delta) and `multi_criteria` (weighted totals and
ranks from declared criteria, weights and scores). Each has a float second route, five frozen checks, refusals, notes
and a preset (`decisiontree`, `realoption`, `mcda`).

**Verified.** Hand checks: Launch EV 52 against Pilot 29.5; five-step American call 14.79 with delta 0.617; weighted
totals 7.4, 7.2, 7.0. 1454 tests pass; frozen fixture 135 methods and 137 presets. Also removed a product-layer
import of the frozen core from the chat break-even helper.

**Still open.** Generic Monte Carlo outside scheduling; dependency arrows, client-side Gantt and the XLSX bar strip.

## 2026-10-28 — Project scheduling batch B: multi-project and schedule risk

**Ask.** "b" after batch A.

**Did — methods.** `multi_project_schedule`: priority-ordered serial scheduling across shared resource capacities, with
every activity start/finish, each project finish and delay against its own CPM, and the overall duration.
`schedule_risk`: a seeded Monte Carlo over independent triangular PERT durations, with mean, median, P80/P90,
observed range, target probability and each activity's criticality index. Both have a float second route,
five and six frozen checks, refusals, notes and presets `multiproject`/`schedrisk`.

**Verified.** Hand-checked examples: two projects sharing a crew finish at 4 and 8; 1,000 seeded runs give a
mean of 7.71, P80 of 8.46 and 92.9% within nine periods. A different seed changes the sample. 1446 tests pass;
the frozen fixture is 132 methods and 134 presets. No existing method, input, check or number changed.

**Still open.** Dependency arrows, client-side Gantt and the XLSX bar strip; the decision batch (Monte Carlo
outside scheduling, decision trees, real options, multi-criteria scoring).

## 2026-10-28 — Project scheduling batch A: levelling, crashing and calendars

**Ask.** "start batch A" of the remaining PM computation gaps.

**Did — methods.** Three T1 methods, each with a float second route and five frozen checks:
- `resource_leveling`: serial non-preemptive scheduling against declared resource capacities; levelled starts and
  finishes, delays, levelled vs unconstrained duration, over-capacity periods and peak demand before/after.
- `project_crashing`: greedy one-period crashing of the cheapest critical activity with a linear crash cost;
  final durations, crash periods, per-activity and total cost to a declared target.
- `calendar_schedule`: CPM over a declared working-period list, with early/late dates, float and critical path.

**Did — wiring.** Presets `leveling`, `crashing`, `calendar`; PM Schedule and control tools; Calculator
Operations group; student notes; README; frozen fixture regenerated (130 methods, 132 presets).

**Verified.** New `tests/test_project_batch_a.py` covers the hand-checked examples (7 vs 5 periods after
levelling; 7 periods at cost 130 after crashing; 7 calendar periods with a two-period gap), four refusals and
the three presets through the pipeline. 1438 tests pass. No existing method, input, check or number changed.

**Still open.** Multi-project scheduling and schedule-risk simulation; dependency arrows, client-side Gantt
and the XLSX bar strip; the decision batch (Monte Carlo, decision trees, real options, multi-criteria).

## 2026-10-28 — Stakeholder/communication and lessons-learned worksheets

**Ask.** "close 1-3", starting with the two missing delivery documents.

**Did.** Two catalogue records (PM-15 stakeholder engagement and communication plan, PM-16 lessons learned) and two T4 canvas worksheets. The stakeholder
sheet covers stakeholders, interests, evidenced influence, engagement approach, messages, channels, timing, owner and communication risks; the lessons
sheet covers what went well and what did not, the evidenced cause, the change, its owner, the audience and the evidence. Empty blocks and assumptions
are named; no score, rank or blame is derived. Registry regenerated from the source (158 records); PM page now 9 tools, 6 worksheets, 10 read-only records.

**Verified.** `test_project_worksheets` now covers six templates; registry counts and the PM composition test updated; 1427 tests pass. No computed
method, preset, check or frozen-contract entry changed.

**Still open.** Resource levelling, crashing, calendars, multi-project scheduling, schedule-risk simulation; Monte Carlo, decision trees, real options,
multi-criteria scoring.

## 2026-10-28 — Project management Gantt and schedule workbook

**Ask.** "close remaining PM gaps", after the answer that a third-party model is the wrong tool for drawing.

**Did — chart.** New `gantt` kind in `bp.product.charts`: one bar per activity from stored `es_`/`ef_` artifacts,
critical path in red, float as a thin whisker, shared time axis, deterministic SVG, digit-free labels and
refusals for a missing artifact or a finish before the start. The Charts panel offers "gantt (CPM schedule)"
and builds the spec from the case artifacts; no model, no browser arithmetic.

**Did — workbook.** SpreadsheetML and XLSX exports add a `Schedule` sheet (activity, early/late start and
finish, float, critical) when CPM artifacts are present, copied from the stored strings.

**Verified.** Five new tests: stored dates and critical colour, determinism, finish-before-start, missing
artifact, digit label, and the Schedule sheet. 1426 tests pass. No method, preset, input, check, number or
frozen-contract entry changed.

**Still not built.** Resource levelling, crashing, calendars, multi-project scheduling, schedule-risk
simulation; stakeholder/communication-plan and lessons-learned worksheets.

## 2026-10-28 — Project management delivery worksheets: charter, WBS, RACI and risk register

**Ask.** "go." after the shelf was complete except for the delivery documents a project assignment asks for.

**Did — templates.** Four T4 worksheets on the existing shared builders. **Project charter** (`template_project_charter`,
canvas, `PM-05`): objective, scope in and out, deliverables, sponsor and governance, budget, milestones, success
measures, assumptions and constraints. **WBS** (`template_wbs`, canvas, `PM-09`): deliverables, work packages,
acceptance criteria and exclusions, with declared work-package-to-deliverable links. **RACI** (`template_raci`,
declared matrix, `PM-10`): activities against confirmed roles; each cell starts R, A, C or I; the builder checks
exactly one A and at least one R per activity and names empty cells. **Risk register** (`template_risk_register`,
declared matrix, `PM-06`): risks against declared likelihood and impact labels, response and owner; no probability,
expected value or score. Registry template links added; the catalogue slice was regenerated.

**Did — page and docs.** The PM page now shows 9 tools, 4 worksheets and 10 read-only records. The student guide
gained a worksheet table and revised limits; `KNOWN_LIMITATIONS.md`, `PRODUCT_GAP_MAP.md`, `CURRICULUM_MAP.md`,
`DECISIONS.md` (B-131) and the changelog were updated.

**Verified.** New `tests/test_project_worksheets.py` (13 tests) covers registration, forms, examples, verbatim
text, the RACI one-A/one-R checks, the invalid-letter refusal and the risk register's empty-cell and no-score
behaviour. 1366 tests pass. No method, preset, input, check, computed number or frozen-contract entry changed.

**Still not built.** Stakeholder/communication plan and lessons-learned worksheets; Gantt drawing, resource
levelling, crashing, calendars and schedule-risk simulation.

## 2026-10-28 — Project management joins the rail; text goes solid

**Ask.** "i think you forgot project management to add as one of the business subjects ... ensure that the
orientation is for business students ... all texts will be in solid not grayed ones." The owner chose the
subject plus borrowed tools (no new methods), all 14 PM records, and the rail slot after Management &
strategy.

**Did — product data.** `SUBJECT_DEFS` gains `project-management` with seven existing frozen tools
(`npv`, `irr`, `dpayback`, `projectmetrics`, `scenario`, `case_decision`, `forecast`), the whole
`PM-01..PM-14` block and no worksheets. Management & strategy loses those ids and the projects discipline
tag, so it now shows 14 worksheets, 18 read-only records and 7 theory lenses. Three presentation groups
(Appraise the business case · Compare the options · Project cost and benefit), project-life/period
badges and a 23-term glossary orient the page to an assignment; the glossary marks critical path, Gantt,
earned value and CPI/SPI as not computed yet. `DISCIPLINE_LABELS` humanises the projects tag, and both the
gallery and detail payloads carry `discipline_labels`.

**Did — presentation.** The rail gains the eleventh item with a Gantt-style icon and its own tones;
`--text-2` and `--text-3` both resolve to `#0C243E`, so secondary and tertiary text is solid on every page,
and the health dot keeps a green accent. Build pill v0.91.

**Verified.** `tests/test_product_subjects.py` now pins the eleven-subject order, the PM composition and
the solid-text tokens; `tests/test_product_server.py` expects eleven. The suite passes. No method, preset,
input, check or frozen fixture changed; the Calculator union is unchanged because every borrowed tool was
already grouped.

**Did — teaching material.** New `docs/PROJECT_MANAGEMENT_STUDENT_GUIDE.md` (conventions, a verified PHP
worked example, a practice set with answers, and the gaps), a new limitations section and rows in
`PRODUCT_GAP_MAP.md` and `CURRICULUM_MAP.md`. The guide is linked from the HOME documentation spine.

**Gaps named on the page.** No PM worksheet (charter, WBS, RACI, risk register), no earned-value, PERT or
critical-path method. Those are the next real increment, not a hidden claim.

## 2026-10-28 — Accounting and Operations shelves, a syllabus map, and the delivery gate

**Ask.** "Do 1-5", with one correction: a named reviewer is not wanted — putting a third party's name on
a student's paper is wrong. The curriculum item was therefore reduced to a coverage map that names no
one.

**Did — computation.** Four T1 methods: `standard_cost_variances` (material price/usage, labour
rate/efficiency, optional variable and fixed overhead; positive is unfavourable), `inventory_policy`
(EOQ, orders per year, safety stock, reorder point, annual ordering and holding cost),
`queue_analysis` (single-server M/M/1) and `capacity_analysis` (capacity per resource, bottleneck,
utilisation, gap). Each has a float second route, five frozen checks, refusals, assumptions,
limitations and a token-only report. PHP presets `scv`, `inventory`, `queue`, `capacity`.

**Did — shelves.** Accounting is now three groups and nine tools, including working capital, loan
amortization and trend analysis that were built but not surfaced, with notes, a 16-term glossary and a
student guide. Operations and Supply chain get the process, inventory and evidence groups, an 18-term
glossary and a joint guide. The catalogue now states partial coverage for QNT-FIN-05 and QNT-OPS-01,
-02, -04 and -08, and leaves QNT-OPS-03/-05/-06/-07 as "not implemented".

**Did — assurance and delivery.** `docs/CURRICULUM_MAP.md` maps each shelf to typical SHS ABM and college
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

## 2026-10-28 — Local OCR and global free data: finish the P2 retrieval/ingestion slice

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


## 2026-10-28 — The planning lane: canvases, projections, dilution, funnel, retention, demand and intent

**Ask.** "Do your recommendations" with the context that the product intends to serve hundreds of
thousands and then millions of students, so coverage must be as extensive as possible without
sacrificing correctness.

**Did — worksheets.** Four T4 templates on one shared builder, renderer and nine-check set: Business
Model Canvas (nine blocks), Lean Canvas (nine), Value Proposition Canvas (six, with declared links from
pain relievers and gain creators to the pains and gains they address) and a marketing plan (STP plus
the product/price/place/promotion mix, with the service extension optional). Every item is the
student's; empty blocks are named and left empty; links survive only when both ends exist; no score,
ranking or recommendation is produced. Registered to `STR-15`, `STR-16`, `STR-17` and `MKT-02` and
offered as worksheets on Entrepreneurship, Management and Marketing.

**Did — computation.** Six T1 methods: `sales_projection`, `cap_table_round`, `sales_funnel`,
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

## 2026-10-28 — Free market data and PDF reading, both fail-closed

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


## 2026-10-28 — The Entrepreneurship shelf becomes a business plan a student can actually submit

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

**Did — computation.** Five T1 methods, each with a float second route, five frozen checks, declared
inputs, refusals, assumptions, limitations, caveats and a token-only template: `market_sizing` (TAM/SAM/
SOM), `startup_capital` (requirement less declared sources, with a surplus instead of a negative raise),
`cash_runway` (months to zero, lowest balance and funding gap; a non-burning flow blocks), `pricing_decision`
(cost-plus, target-margin, break-even and target-return prices) and `return_on_investment` (ROI and
annualised ROI). `breakeven` was **extended additively**: the quantity is unchanged, the contribution
margin and break-even revenue always appear, and the margin of safety and target-profit volume appear
only when `expected_units` or `target_profit` is declared. Five PHP presets carry worked examples.

**Did — presentation.** Thirty tiles in five business-plan groups, a period badge on every tile, a
20-term glossary, a guidance paragraph on the subject and a generalised `_tool()` that reads
`SUBJECT_GROUPS`/`SUBJECT_PERIODS` instead of hard-coding Finance. The tools that were already built but
unwired (project metrics, scenario, loan, working capital, DCF, multiples, equity bridge, SROI, CBA,
elasticity, cost curves, markup/Lerner, trend analysis and the survey statistics) are now on the shelf.
The catalogue links were updated so the page states partial coverage honestly (market sizing, growth,
unit economics, pricing) and still shows the canvases as "not implemented". New
`docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md`: assignment requirement → tool table, conventions, six worked
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

## 2026-10-28 — Multi-year trend analysis, the last core Finance gap

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


## 2026-10-28 — Finance gets a student front door: groups, notes, period badges and a percent guard

**Ask.** "okay do p0-3" after the Finance coverage audit: group the 32 tiles, put the study material on the page
rather than only in a file, and stop the classic percent-versus-decimal mistake.

**Did.** (1) Six ordered groups on the Finance page — Foundations, Corporate finance, Valuation, Investments,
Risk & derivatives, International — replacing one flat grid; Economics keeps its intro/intermediate/advanced
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


## 2026-10-28 — Advanced econometrics: panel, IV, RDD and probit

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

## 2026-10-28 — Economics completed: welfare, international, development, behavioural and games

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

## 2026-10-28 — Economics gets the macro core: ten methods and the firm

**Ask.** "GO" on the Phase 2 macro plan after the micro audit: national income, growth, inflation, unemployment,
money and fiscal multipliers, debt, plus cost curves, profit maximisation and market power.

**Did.** Added ten T1 methods — `cost_curves`, `profit_maximization`, `market_power`, `national_income`,
`growth_rate`, `inflation_cpi`, `unemployment_rate`, `money_multiplier`, `fiscal_multiplier` and `budget_debt` —
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

## 2026-10-28 — Economics gets a micro core: five methods, student notes and an honest gap list

**Ask.** The owner asked whether Economics covers everything a student needs and said it looked very thin. The audit
found five tiles, three of them impact evaluation, no worksheets, six borrowed catalogue rows and no microeconomics.

**Did.** Added five T1 methods — `demand_supply_equilibrium`, `elasticity`, `tax_incidence`, `price_control` and
`market_concentration` — with a float second route, five frozen checks each, declared inputs and a formula-level
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

## 2026-10-28 — Finance is a student shelf now: fourteen methods, one approved unfreeze

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

## 2026-10-28 — [product] The artefact decides the format, and the first look at a submission found a bug

**The owner's correction, and it was right.** A free menu of Word, PDF, Excel and PowerPoint for everything is
wrong: a slide deck of an accounting submission is not the Word file in landscape, it is a different artefact
with different content. The earlier increment had built that menu; this replaces it.

**Three layers.** *Blocks* are a fixed vocabulary assembled from the stored bundle - statements, workings,
checks, limitations, citation, headline, recorded values - and none of them computes anything. *Profiles* are
data: which blocks an artefact contains, which formats can carry it, and the default. *Renderers* are handed
the blocks.

| Artefact | Blocks | Formats |
|---|---|---|
| Assignment submission | statements · workings · checks · limitations · citation | Word, print-ready HTML |
| Working papers | statements · recorded values · citation | SpreadsheetML, CSV |
| Case presentation | headline · statements · checks · citation | **none yet** |

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

## 2026-10-28 — [product] Exports and credits: a real .docx, and a wallet that cannot double-charge

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

## 2026-10-28 — [computation] The trial-balance check: the first feature built for the student's own homework

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
2. **The ×9 rule is only applied where the textbook applies it** - to a trial balance that does not balance
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
unbalanced-first ordering; the ×9 hint; the equal-and-opposite wrong-side hint; both single-input verdicts;
refusals for a duplicate row, a negative figure, over-precise figures, a row with no identifier and no input
at all; the partial-row schema; all five declared checks running and passing; the second route agreeing; the
appendix carrying the verdict and four `cannot_prove` items; the preset delivering under `detail`; and a trap
showing a tampered figure is never reported as agreeing.

**No UI yet.** The screen this feeds is the next increment, and the export/credit mechanism is B.

## 2026-10-27 — [computation] Re-performance now covers the document, not only the scalars

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

## 2026-10-27 — [computation] Chaining two periods: nothing may reset at the boundary

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

## 2026-10-27 — [computation] Close the two gaps the verification pass found

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

## 2026-10-27 — [computation] Verification pass over the accounting pipeline

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

## 2026-10-27 — [computation] Revaluation, built on the OCI route and anchored to IAS 16

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**The core accounting build is now complete for both phases.** What remains is the UI: none of this is
visible on the page yet.

## 2026-10-27 — [computation] Other comprehensive income: a separate route, closing to a reserve

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Phase 2 complete.** Revaluation can now be built on this route: IAS 16.35 allows proportionate
restatement or elimination of accumulated depreciation, the 2013 amendment pins accumulated depreciation
to gross minus net, IAS 16.39 sends an increase to OCI and IAS 16.40 sends a decrease to profit or loss
except to the extent it reverses a prior surplus. The accounting is settled; only the schedule remains.

## 2026-10-27 — [computation] Current/non-current balance sheet: presentation only, and it is declared

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Remaining in Phase 2:** the other-comprehensive-income route, then revaluation on top of it (IAS 16
settles the accounting; only the statement model was missing).

## 2026-10-27 — [computation] Statement of changes in equity: opening + movements = closing, and it ties to the balance sheet

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in Phase 2:** the current/non-current balance-sheet split (an optional per-account classification,
so existing specifications keep their behaviour), then the other-comprehensive-income route that
revaluation waits on.

## 2026-10-27 — [computation] Bad-debt allowance: the engine computes the movement, never the estimate

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Phase 1 of the accounting build is now complete.** The next increment is Phase 2, which changes the
statement model (statement of changes in equity, current/non-current split, and the
other-comprehensive-income route revaluation waits on) and therefore stops here for the owner.

## 2026-10-27 — [computation] Prepayments and deferred income: the two deferrals, and they must clear

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** bad-debt allowance (an estimate, so it needs a declared target or charge plus an
optional write-off), then Phase 2 - the statement of changes in equity, the current/non-current split,
and the other-comprehensive-income route that revaluation waits on.

## 2026-10-27 — [computation] Asset disposal: the one schedule that must read the books

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** the remaining adjusting-entry types (prepayment and its release, deferred income,
bad-debt allowance), then the statements block.

## 2026-10-27 — [computation] Depreciation beyond straight-line: reducing balance and units of production

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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 — [computation] Reversing entries: a correction you can see, not a balance you adjust

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

## 2026-10-27 — [computation] The journal itself: the audit trail behind every balance

**Ask.** Phase 1, second increment, in the order agreed: the ledger engine should let a reader see
the entries, not just the totals derived from them. T-accounts showed one account's movements;
nothing showed the double entry that produced them.

**Did.**

- `ledger.journal_view(j)` — every entry in posting order as data: date, description, opening and
  closing flags, each line named and sided with its debit or credit, the entry's own debit and credit
  totals, and the entry hash from the chain `verify_chain` checks.
- `report.journal(j)` — the same journal as deterministic plain text, marking opening and closing
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

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** reversing and correcting entries (a declared reversal in the spec, with validation),
then depreciation beyond straight-line, then the remaining adjusting-entry types.

## 2026-10-27 — [computation] T-accounts: the ledger can now be read one account at a time

**Ask.** Phase 1 of the accounting build, first increment: the owner named "no T-tree balancing" as a
missing capability, and nothing in the engine could show a single account's movement — only a trial
balance total and derived statements. Layout first, wiring later; this is the computation side.

**B-032 closed (owner instruction, this session).** The ledger engine is the **custom kernel for
management accounts v1**, as the provisional recommendation already on record. The Beancount arm was
never run and is recorded as not run; the decision note records that it can be revisited if an external
engine is ever wanted. Phase 1 sits directly on this decision, which is why it was closed first.

**Did.**

- `ledger.account_ledger(j, code)` — one account as a T-account: opening balance (from the opening
  entry), every period posting in **date order** with the **running balance on the account's normal
  side**, the movement totals, and the closing balance. Closing entries are included and marked, so an
  income account that reads zero explains why instead of hiding the close.
- `ledger.account_ledgers(j)` — every chart account, in chart order, including accounts with no
  postings (an empty account is information).
- `report.t_account(lg)` / `report.t_accounts(...)` — deterministic plain-text rendering, same
  conventions as the other statement exports (fixed width, parentheses for negatives). It renders the
  numbers it is given and recomputes nothing.
- `accounts.build` now emits `ledgers` (serialised) and `t_accounts_export` (rendered text per account)
  in the appendix, so the workbench can show a T-account without ever computing a balance itself.

**Two design decisions worth recording.**

1. The running balance is computed **in the core, not the page**, because it is a reading of the account
   rather than a presentation choice. A design-layer balance would be a derived business number, which
   §1A forbids.
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
empty; and a trap test showing a ledger that omits the opening balance would **not** foot — so the
footing assertion can actually fail.

**Still not fixed, carried forward:** `multi_product_breakeven` does not flag a negative-contribution
product (needs an unfreeze because it changes `test_names`).

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 — [computation] The server told browsers to cache a page it recomputes every time

**Found while verifying the catalogue fix.** After correcting the catalogue and restarting
the server, the browser still rendered the old statuses. The API was already right on the wire;
the browser had reused its cached copy. `src/bp/server.py` sent no caching header at all —
no `Cache-Control`, no `Pragma` — although CHANGELOG 0.69 states *"The page now declares
`Cache-Control: no-store` / `Pragma: no-cache`"*. That sentence was never true in the code.

**Why it matters beyond one stale row.** The build pill is the only "which page am I looking at"
signal, and it is useless until the page has actually reloaded. A cached page with an old pill
and old data is indistinguishable from a current one. This is the same failure mode as the
wrong-folder-on-8021 confusion: the owner sees something that is not what the code says.

**Did.** `_send` — the single exit point for every response — now adds `Cache-Control: no-store`
and `Pragma: no-cache` alongside the existing `X-Content-Type-Options`. Added
`tests/test_cache_headers.py` (2 tests) which starts the real `ThreadingHTTPServer` and asserts
both headers on the workbench document and on `/api/health`. The test fails on the old code:
the headers were observably absent from the live server before this change.

**Verified.** 761 tests OK. Live server confirmed sending `no-store` on both routes.

**Still no build number, for the same reason as the entry below:** no served markup changed and
the pill is pinned at `v0.73` by `tests/test_product_subjects.py`.

## 2026-10-27 — [computation] The catalogue told students that built accounting methods did not exist

**Ask.** Phase 0 of the accounting build: "correct those that are erroneous" before adding
anything. The owner had seen the Accounting page say *"Management accounting — not implemented"*
while `management_accounts` was running on that same page.

**Found.** The subject pages derive every record's `implementation_status` from
`METHOD_LINK_RULES` in `src/bp/registry.py` — a six-rule table that matches a record's *summary*
and returns its linked methods plus a hand-written note. Only six rules existed, all written
before IRR, discounted payback, ratio analysis, the valuation family, the ledger engagement, unit
economics and most of the statistics library shipped. Everything unmatched falls through to
`"not implemented"`. Consequences verified against the live API:

- `QNT-FIN-01` claimed IRR and payback were missing — both are T1 methods
- `QNT-FIN-02` claimed "break-even only" — `multi_product_breakeven` also exists
- `QNT-FIN-03`, `QNT-FIN-04`, `QNT-FIN-05`, `QNT-FIN-06` each read **"not implemented"** while
  `ratio_analysis`, `wacc`/`dcf_valuation`/`equity_bridge`, `management_accounts` and
  `unit_economics` respectively run
- `QNT-STA-03` claimed chi-square and ANOVA were missing; `QNT-STA-04` claimed logistic
  regression was missing — all present

Two of 36 methods were claimed by the catalogue; the other 34 were reachable only through the
Calculator.

**Did.** Rewrote `METHOD_LINK_RULES` so each rule matches on its record's summary prefix and
carries an accurate note and the real method list, then regenerated the committed slice with
`scripts/generate_subjects.py` — the documented single source of truth. `QNT-FIN-07` (pricing and
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
file, because the wrong text was a *factual claim about the engine* — computation-owned content
(§1A). It was regenerated from the core rule rather than hand-edited, and the guard test lives in
`tests/`. If the design owner disagrees with that call, the revert is local and this entry records
why it was made.

## 2026-10-27 — [product] Clean Home: logo + unchanged slogan + chat box only (build 0.70)

**Ask:** the owner rejected the 0.69 Home as regressed and over-filled: it should be clean and contain only the chat box and its logo; the side rail is already fine; do not change the slogan; do not act without permission. Confirmed scope: remove the dropdowns too; the chat box is only the text area and up arrow.

**Did:** removed from Home the extra sentence under the slogan, the preset/method/currency selects, the preset chips, the Examples card, "Your cases", "Or choose a subject", the "Two ways in" note and the Enter hint. Kept the logo, wordmark, the tagline exactly as written, the text area and the up-arrow. Side rail, Calculator, Status pill, top bar, subject pages and backend untouched. Guarded the absence of the removed elements; guarded `startFromHome` against the removed selects (it now toasts to the rail/Calculator because Home has no method control).

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.70), `DECISIONS.md` (B-094), `DISCUSSION_NOTEBOOK.md` (entry + Status line), `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 753 tests OK; `node --check`; `<section>` counts equal; no Home markup for `preset`/`method`/`currency`/`data-example`/`hero-sub`/case or subject shelves. No computation, API, side rail or business number changed.

**Open/next:** the Home arrow cannot launch without a method; method choice lives in the subject rail and Calculator. `loadHomeShelf` is now unused. If the slogan meant the sentence under the tagline, it must be restored verbatim on request.

## 2026-10-27 — [product] Static-first expandable subject rail, centred chat, up-arrow Enter control (build 0.68)

**Ask:** another agent's served copy lost the subject rail; re-implement it, ensure the rail is expandable, centre the big Home chatbox with even side space without changing its length, and move Run to the right as an up arrow suggesting Enter.

**Did:** wrote the ten subject links and icons as static markup in `#railsubjects` so the rail renders before `/api/cases/subjects` and survives its absence; the live call still replaces them with full labels/counts, and a failure now appends a note instead of wiping the list. Reworked the rail toggle (hamburger collapsed, chevron + "Collapse" open, `aria-expanded`, label, title, persisted state). Added `main{margin:0 auto}` so the action box centres in the content column at unchanged width. Moved `#run` from the left of the action row to the right and replaced it with a circular up-arrow button; added Enter-to-start / Shift+Enter-newline and an inline hint. Added three static-markup presence guards in `tests/test_product_subjects.py`.

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.68), `DECISIONS.md` (B-093), `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** 753 tests OK; `node --check` on the extracted page script; `<section>` counts equal; the static rail has all ten subject ids; the panels removed in 0.67 are still absent. No computation, frozen module, fixture, API route or business number changed.

**Open/next:** static labels are shorter than the live ones and only the ten known ids are guarded. The static rail is navigation, not capability: with an old backend the subject page still 404s. The chat centring is within the content column (the rail offsets the visual centre by ~32px). No browser test exists.

## 2026-10-27 — [product] Catalogue and Assistant panels deleted from the UI (build 0.67)

**Ask:** "whats the use of catalogue, assistant and status? are they needed? or okay to be deleted?" followed by **"go"** for the recommendation: delete Catalogue and Assistant from the UI, keep Status behind the health pill, keep all backend routes and tests.

**Did:** removed `panel-frames` and `panel-assistant` markup, `RENDERERS.frames`, `searchFrameworks`, `loadTemplate`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, the subject-page "Browse the full method catalogue" button, the drawer's Assistant tab, the `/api/assist/config` boot call, the `state.assist` field and the unused `.dtab` CSS. The chat button now opens a single Help & about drawer; the health pill still opens Status. Kept `/api/frameworks`, `/api/frameworks/{id}`, `/api/templates`, `/api/assist` and their tests; subject catalogue-only tables, worksheet tiles and the Calculator are unchanged.

**Files:** `web/index.html`, docs: `CHANGELOG.md` (0.67), `DECISIONS.md` (B-092), `BACKEND_CONTRACT.md` §6, `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 750 tests OK; `node --check` on the extracted page script; zero remaining references to `panel-frames`, `panel-assistant`, `RENDERERS.frames`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, `dtab`, `state.assist` or `api/assist`; `<section>` open/close counts equal. Three UI-presence assertions in `test_assist`, `test_framework_flow` and `test_templates` were retargeted to the new surface (no backend test or assertion changed). No frozen module, fixture, route or business number changed.

**Open/next:** the backend assistant and framework/template routes are now reachable only by direct API/test call. If a provider is configured later, the assistant UI must be re-surfaced **and fixed** (use `critique`, supply facts/alternatives, send `consent`). Status remains a dev-facing panel behind the pill.

## 2026-10-27 — [product] Subject rail, capability tiles and Home reconciliation (build 0.66)

**Ask:** the owner's rail instruction — enumerate the subjects (Accounting, Finance, Economics, Management, ..., now Entrepreneurship) with icons; clicking one shows its capabilities in the centre as clickable tiles; reconcile with Home chat; delete Case, Catalogue, Assistant and Status from the rail and keep Calculator at the bottom.

**Did:** (1) `bp.product.subjects`: added Entrepreneurship as a combination shelf (8 frozen compute tools, the existing STR-18 SWOT worksheet, 5 catalogue-only canvas/innovation records) and a unique presentation `icon` key on all 10 subjects, exposed by the gallery and detail routes; added an Entrepreneurship group to the Calculator groups. (2) `web/index.html`: rail rebuilt as Home + the 10 subjects (icon, label, native tooltip, aria-current on the active subject) + Calculator pinned at the foot; the Case/Catalogue/Assistant/Status rail items removed, with their existing panels kept reachable from Home/subject pages, the subject catalogue button, the chat drawer and the health pill. (3) A subject click renders a capability **tile grid** (one tile per frozen method or worksheet, with description, preset/typed-input footer and kind icon) instead of a vertical row list; stored cases and the catalogue-only table follow. (4) Home-chat reconciliation: copy states the two routes, the same subject cards remain under the box, and every subject page links to the chat. (5) Hash routing now supports `#/subject/<id>`. (6) Two guard tests: rail order/unique icons/icon round-trip, and Entrepreneurship's tool/worksheet/canvas composition.

**Files:** `src/bp/product/subjects.py`, `web/index.html`, `tests/test_product_subjects.py`, `tests/test_product_server.py`, docs: `CHANGELOG.md` (0.66), `DECISIONS.md` (B-091), `BACKEND_CONTRACT.md` §6, `DISCUSSION_NOTEBOOK.md` (dated entry + Status line), `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** full suite **750 tests OK**; `node --check` on the extracted page script; a live server smoke test returned the 10-subject gallery with icons, the Entrepreneurship page (8 tools, 1 worksheet, 5 catalogue records), the 8 Calculator groups and HTTP 200 for the page. No frozen module, frozen fixture, existing route contract or business number changed.

**Open/next:** the same open items as build 0.65 (C1 multi-run cases, per-subject workbenches, free-form arithmetic, owner decisions in notebook section J). A browser-level UI test is still absent; the rail/tile checks are catalogue guards plus a JS syntax check.

## 2026-10-26 — [product] Subject-first navigation and the Calculator launcher (build 0.65)

**Ask:** "read discussion notebook and implement it" — the notebook's build brief (section G, Increment 1) plus the owner's rail Calculator instruction (section N).

**Did:** implemented the first increment, not the whole four-increment plan. **Product catalogue:** new `src/bp/product/subjects.py` is a committed, testable index of 9 subjects (Accounting, Finance, Economics, Management & strategy, Operations, Supply chain & logistics, Marketing & customers, People & organisation, Research & statistics as a cross-cutting shelf). Each subject maps to the frozen preset ids / method ids it can actually launch, the three existing T4 worksheets (STR-01 Five Forces, STR-07 and STR-18 SWOT) as structure-only, and the registry records it can only read or structure with the registry's own `implementation_status` wording. A generation helper (`scripts/generate_subjects.py`) writes the registry slice; `tests/test_product_subjects.py` re-reads the frozen fixture and registry as data and fails on any drift. **Routes (additive, `/api/cases` only):** `GET /api/cases/subjects`, `GET /api/cases/subjects/{id}`, `GET /api/cases/calculator`, and `GET /api/cases?subject=<id>` (stored cases filtered by the methods the subject can launch). **Calculator:** seven business-function groups (Finance, Accounting, Statistics, Economics, Operations, Marketing, People) built from the same compute tools; it arranges inputs and calls the existing create-then-confirm pipeline. No client-side formula, no product-layer arithmetic, no new arithmetic path; free-form expressions are named as unsupported rather than silently absent. **Served UI (`web/index.html`):** seven-item rail Home | Subjects | Calculator | Case | Catalogue | Assistant | Status; Home is a case shelf (stored cases + subject cards + the existing objective box); subject pages show tools, worksheets, stored cases and an explicit catalogue-only table; a searchable Calculator; the "Draft work plan" destination is replaced by a one-button tool screen ("Apply figures and calculate" performs the same two calls), while the phrase survives honestly in the recorded-metadata panel the frozen test asserts; `framework_suggestions` is finally rendered (informational only); the hero sub-line is no longer "To be supplied"; a malformed `</section` in the served HTML was fixed. **Not implemented, deliberately:** C1 `bp-case/2` multi-run cases, the Accounting/Finance workbenches, and the remaining subject workbenches (Increments 2–4); the Home copy says a run is still saved as a one-run case.

**Files:** `src/bp/product/subjects.py` (new), `scripts/generate_subjects.py` (new), `src/bp/product/api.py` (imports, subject/calculator routes, subject filter), `tests/test_product_subjects.py` (new, 14 tests), `tests/test_product_server.py` (one HTTP route test), `web/index.html`, `docs/DISCUSSION_NOTEBOOK.md` (new dated entry + brief Status line), `docs/CHANGELOG.md` (0.65), `docs/DECISIONS.md` (B-090), `docs/BACKEND_CONTRACT.md` §6 + test count, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, this entry.

**Verified:** full suite **748 tests OK**; `node --check` on the extracted page script; the subject drift guard confirms every launch id exists in the frozen fixture and every catalogue id in the registry; the product boundary test still shows no core import and no product-layer arithmetic. No frozen module, frozen fixture or existing test was edited.

**Commit:** `this commit`.

**Open/next:** the owner decisions in notebook section J remain open, especially (2) whether one case should hold many subject analyses (the C1 decision) and (4)/(5) whether the 131 catalogue-only records should stay visible and whether B-028 should add worksheets. Increment 2 (C1), the Accounting workbench and the Finance/DCF sheet are the next build steps, not part of this increment.

---


## 2026-10-21 — [documentation] Website UI brief for the design owner (plan mode)

**Ask:** write the instruction for MiniMax/OpenCode to build the website: A1.jpg as inspiration, the owner's logo as the site logo, colored feature icons on the left rail, remove the API/Enterprise top-right items, delete the "Trusted by 11 million" block and the university row, retain the circular chat button restyled to the brand, UI sans-serif except generated document text (Times New Roman), and **plan mode first** so MiniMax can ask clarifying questions before building.
**Did:** wrote `docs/UI_BRIEF.md` as the authoritative instruction: assets and where they live (logo copied into `web/assets/`, A1 as inspiration only, never shipped); the A1 structure to imitate (fixed left icon rail, centered hero with logo, large action box with an inner controls row, quick-action chips, floating chat button) and the exact removals (top-right API/Enterprise/Pricing/Login/Sign-up; the trusted-by block and university logos; no invented social proof); the nine real features for the rail mapped to the actual API routes (Home/New analysis, Cases, Data, References, Deliverables, Accounts, Frameworks & templates, Assistant & method info, Status); typography (sans-serif system stack for UI; Times New Roman for generated document text, with the note that `export.py` is a computation-owner file and must not be edited); the non-negotiables (display API values verbatim, no client-side computation, never hide caveats/honesty/limitations/tier labels, no invented content, offline/no CDNs, `web/**` write scope, backend needs requested rather than invented) and the frozen workbench strings the suite asserts. The brief's first deliverable is a **plan** (IA, screen map, wireframes, design tokens sampled from the logo, component inventory, responsive/accessibility, phased build, test-impact statement, and questions for the owner) with no code until approved.
**Files:** `docs/UI_BRIEF.md` (new), `docs/HOME.md` (spine row + build digit), `docs/HANDOFF.md` (build digit), `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **733 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax replies in plan mode with its plan/questions; the owner reviews; after approval the UI is built in `web/**` on its own branch. Nothing UI has been started by the computation lane.

---

## 2026-10-21 — [computation] Product slice 2c: charts, spreadsheets and business graphics (B-089)

**Ask:** "do 1" — the last backend item: the graphics/spreadsheets addition (B-087), then stop before the UI.
**Did:** three new product modules, all deterministic and stdlib-only, with **no model in the rendering path**. **`charts.py`**: a declarative `bp-chart/1` spec renders SVG for bar, line, stacked bar, waterfall, pie, sparkline and table; every series names a stored artifact (metric or id), a missing artifact / no recorded value / non-numeric value is refused with a reason, the spec's text fields (title, labels, axis labels, note) **may not contain digits** so only stored value strings can appear, and geometry scaling never alters the strings; same bundle + spec → byte-identical SVG. **`spreadsheets.py`**: CSV of the artifact table (LF endings) and a SpreadsheetML 2003 workbook with Case/Artifacts/Report sheets where every cell is a string (so `50.00` never becomes `50.0`). **`diagrams.py`**: structure-only (T4) SVG templates — process, 2x2 matrix, pyramid, funnel, tree — from owner-supplied digit-free labels; nothing is scored or ranked. `export_html` now embeds charts/diagrams; routes `POST /api/cases/{id}/render` (SVG preview) and `POST /api/cases/{id}/export` (`csv` / `spreadsheetml` / `html`).
**Files:** `src/bp/product/charts.py`, `.spreadsheets.py`, `.diagrams.py` (new), `src/bp/product/export.py`, `src/bp/product/api.py`, `tests/test_product_charts.py`, `tests/test_product_diagrams.py`, `tests/test_product_spreadsheets.py` (new), `tests/test_product_routes.py` (extended), docs (B-089, CHANGELOG 0.63, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **733 tests OK** including the frozen-contract and docs-state guards; SVG validated as well-formed XML, determinism and number-fidelity tested (a chart cannot print a number that is not a stored value), spreadsheets checked cell-by-cell as strings, and the render/export routes exercised through the dispatch.
**Commit:** `this commit`.
**Status:** the backend product sequence is **complete** (2a, 2b, 2c). Per the owner's instruction I am **stopping before any UI/homepage/interface work** and waiting for the special UI instructions. Remaining non-backend items are decision-gated (D3 disclosure, REW R1–R10/B-082, tax B-052, ledger B-032, templates B-028, reviewers B-005, frontier stats B-075).

---

## 2026-10-21 — [computation] Product slice 2b: ops surface and the local launcher (B-088)

**Ask:** continue the backend sequence, and the owner asked "will you also build the server? i notice there is no server yet". Answer: the server already exists (`src/bp/server.py`, stdlib HTTP, `python -m bp.server`, serving the workbench and API, wired to the product routes since B-085); what was missing was the operational/deployment surface, which is this slice.
**Did:** new `src/bp/product/ops.py` — `health()` (case-store counts, state dir, request-log status, checks, ok/degraded), `log_request()` (JSONL: timestamp, method, query-free path, status, duration only; never a body/title/input/report; `BP_REQUEST_LOG=""` disables; best-effort), `backup()` (zip of the case store's JSON documents + manifest + SHA-256; state/logs/prior archives excluded), `restore()` (zip-slip/drive/non-JSON refusal, staging then copy, refuses overwrite unless asked), `list_backups()`. Additive core instrumentation in `server.py`: a timing hook feeding the request log, `GET /api/health` (merging sandbox/model flags), and startup lines for URL/health/log — no existing route, output or claim changed (frozen guard still passes). New `scripts/serve.py` launcher as the single local run path: `--port`, `--host`, `--no-sandbox`, and `--check` dry-run printing the resolved config; it adds `src` to `sys.path` so a clean checkout needs no install. Product routes `POST /api/cases/backup`, `POST /api/cases/restore`, `GET /api/cases/backups`.
**Files:** `src/bp/product/ops.py` (new), `src/bp/product/api.py`, `src/bp/server.py` (additive instrumentation), `scripts/serve.py` (new), `tests/test_product_ops.py`, `tests/test_launcher.py`, `tests/test_product_server.py` (extended), docs (B-088, CHANGELOG 0.62, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2b, README, HOME, HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **714 tests OK** (frozen-contract and docs-state guards included); health/backup/restore and the launcher were exercised over a real HTTP server; the request-log test asserts no report text, input body or title reaches the log.
**Commit:** `this commit`.
**Open/next:** Phase 2c (deterministic charts/SpreadsheetML/diagram templates, B-087) is the last backend task before the UI; after it I stop, per the owner's instruction to hold the interface until special instructions.

---

## 2026-10-21 — [computation] Product slice 2a: case versions, comparison and sign-off (B-086)

**Ask:** "continue on the sequence of backend product building. do it yourself the job you are delegating because you will not accept cline's work and still edit it." Plus the important addition about spreadsheets/charts (recorded as B-087 and planned as Phase 2c; nothing in this slice draws graphics).
**Did:** implemented slice 2a directly, in the product layer, with no frozen module touched. **`versions.py`** — an immutable version chain per case (`<BP_CASES_DIR>/<id>/vNNN.json`), a canonical-JSON `bundle_hash` recorded in each envelope, legacy flat cases adopted as version 1, corrupt/tampered versions refused on read, delete removes the chain. **`compare.py`** — Option-A comparison over stored versions: same-method rule enforced, artifact rows aligned by metric, stored values copied verbatim, a metric absent from a version reported as "not computed for this version", differences in `spec_hash`/`outputs_hash`/`method_version` listed, a disclosure naming each compared version's `bundle_hash`/`outputs_hash`, deterministic stdlib HTML rendering. **`signoff.py`** — append-only sign-off records carrying the owner-approved Option-A signature text, reviewer name/role/scope/decision, the signed version hashes and a tamper-evident integrity check. **Routes** added to the pure dispatch (already reachable through the server delegation, so no core edit): `GET/POST /api/cases/{id}/versions`, `GET /api/cases/{id}/versions/{n}`, `GET /api/cases/{id}/compare`, `POST/GET /api/cases/{id}/signoff`. Tests: `tests/test_product_versions.py`, `tests/test_product_compare.py`, `tests/test_product_signoff.py`, `tests/test_product_routes.py` plus an HTTP extension in `tests/test_product_server.py` (22 new tests).
**Files:** `src/bp/product/versions.py`, `src/bp/product/compare.py`, `src/bp/product/signoff.py`, `src/bp/product/api.py`, new product tests, docs (B-086/B-087, CHANGELOG 0.61, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2a/2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **702 tests OK** including the frozen-contract and docs-state guards; the version chain, comparison rules, sign-off wording and tamper cases are all tested; the routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** Phase 2b (ops/observability, offline packaging) then Phase 2c (deterministic charts/SpreadsheetML, B-087), then **stop before the UI** per the owner's instruction.

---

## 2026-10-21 — [review] Product slice 1 reviewed, wired in, and two defects fixed (B-085)

**Delivered by:** MiniMax/OpenCode on branch `opencode/product-slice-1`, commit `b411083`: new `src/bp/product/**` (case store, route dispatch, stdlib HTML export) + 51 product tests + the §6 rows and count/version/changelog/worklog docs.
**Review verdict: accepted with fixes.** The design is right: a local case store that treats the frozen bundle as an opaque document (atomic write via temp+rename+fsync, 12-hex id validation, path-traversal refusal, corrupt-bundle refusal, opaque load), a pure `handle(method, path, body) -> (status, payload)` dispatcher with no server edit, and an HTML export that copies the stored report and artifact values. The product tests set/restore `BP_CASES_DIR` properly and the package imports only the standard library.
**Defects found and fixed in this integration commit:**
1. **Tautological check.** `test_the_product_layer_computes_no_number` compared a set with itself (`recorded` and `shown` were the same expression), so it could never fail. Replaced with a real check: the numbers returned by the dispatch and shown by the HTML export are compared against the numbers in the bundle actually written to the store, so an invented/rounded/recomputed value now fails.
2. **Double-encoded text in four factual docs.** The slice rewrote CHANGELOG/HANDOFF/HOME/WORKLOG with cp1252→UTF-8 mojibake (e.g. `â€”` for an em dash, `Â§` for a section sign). Repaired to proper UTF-8; this is why the review diff looked much larger than the intended count/version edits.
3. **Registry portability bug (pre-existing, found because the slice was tested in a fresh worktree).** `catalogue_import` hashed raw catalogue bytes, and git's Windows checkout (`core.autocrlf=true`) turns committed LF into CRLF, so a fresh worktree hashed different bytes and `test_shipped_registry_equals_fresh_import` failed there while passing in the main checkout. The hash is now computed over LF-normalised bytes and the shipped registry was regenerated (records unchanged); a new test imports a CRLF copy and asserts the same hash.
**Wiring (the core edit the plan delegated to me):** added `from .product import api as product_api`, a GET/POST branch and a new `do_DELETE` in `src/bp/server.py`, all delegating to the product dispatcher; the product POST branch parses the body without `parse_float=Decimal` so bundles round-trip exactly. The frozen route fixture is unchanged — the product surface is tracked in `BACKEND_CONTRACT.md` §6. New `tests/test_product_server.py` (3 HTTP tests) covers list/post/get/delete, 404/422 refusals, and that existing routes are unchanged.
**Files:** `src/bp/server.py`, `src/bp/catalogue_import.py`, `src/bp/data/registry_v0_2.json`, `tests/test_product_boundary.py` (fixed check), `tests/test_product_server.py` (new), `tests/test_registry.py` (new EOL test), docs (B-085, CHANGELOG 0.60, BACKEND_CONTRACT §6, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **680 tests OK** including the frozen-contract and docs-state guards; the four repaired docs render correctly; the wired routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** delegate slice 2 (reviewer sign-off record with the Option-A wording, multi-period comparatives + case versions per Option A, ops/observability, offline packaging) to MiniMax; DOCX/XLSX export remains a later slice behind a declared product dependency.

---

## 2026-10-21 — [product] Product slice 1: durable case store, case routes, HTML export

**Ask:** owner instruction "let minimax do the product backend" (B-080) and "let's do your recommended sequence of finishing the backend product before finally doing the UI" (B-081): the first product slice over the frozen core (B-079), in the design owner's lane.
**Did:** added the new product package `src/bp/product/` — a local durable case store (one JSON bundle per case under `BP_CASES_DIR`, default `cases/`; atomic writes; ids refused unless 12 lowercase hex characters; path traversal refused; a corrupt bundle refuses to load with a clear message), a pure additive route dispatch for `GET /api/cases`, `POST /api/cases`, `GET /api/cases/{id}` and `DELETE /api/cases/{id}` (no `server.py` edit — the computation owner wires it after review), and a self-contained HTML export of a stored bundle with the delivered report text and the artifact table copied exactly. The bundle is opaque: the product layer stores, lists, copies and renders what was recorded, imports nothing from the frozen core, and computes no business number.
**Files:** `src/bp/product/__init__.py`, `src/bp/product/cases.py`, `src/bp/product/api.py`, `src/bp/product/export.py` (new), `tests/product_fixtures.py`, `tests/test_product_cases.py`, `tests/test_product_api.py`, `tests/test_product_export.py`, `tests/test_product_boundary.py` (new), `docs/BACKEND_CONTRACT.md` (§6 rows only), `docs/CHANGELOG.md` (0.59), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md` (count/version digits only). No frozen core module, test, fixture or factual document was edited.
**Verified:** full suite (frozen-contract guard + docs-state guard + 51 product tests) **676 tests OK**; the product boundary is checked by a test that parses the product sources and fails if they import anything but the standard library, import or shadow a frozen core module, reference a third-party package, or show a number that was not recorded.
**Commit:** `this commit`.
**Open/next:** the route dispatch still needs the computation owner to wire it into `src/bp/server.py` (an additive route table; the frozen route surface is unchanged until they do); the DOCX/XLSX export needs dependencies that are not in this slice, so it is not in this commit.

---

## 2026-10-21 — [computation] Sign-off wording and multi-period Option A resolved (B-084)

**Ask:** owner answered D4 and the multi-period question: **"a."** (sign-off Option A) and **"option a"** (multi-period Option A); also noted the workspace-root `A1.jpg` is a website reference for later and the logo is to be left alone.
**Did:** recorded both choices as B-084 and updated the plan: **D4 = Option A** — the stored signature text is now fixed and quoted in Phase 2 ("I reviewed the named case bundle and its disclosed limitations. This signature records that review; it does not assert that the inputs are true or that the analysis is correct."). **Multi-period comparatives and case versioning = Option A** — product-layer, no unfreeze, moved from the unfreeze queue (Phase 3) into the delegated Phase 2 slice: one frozen session per period, immutable case versions (monotonic version, spec/output hashes, method id+version), side-by-side comparison of stored bundles under declared comparability rules, missing periods shown as "not computed" and never filled, every displayed number byte-identical to its stored bundle, no arithmetic in the product layer. Phase 3 now holds only PDF/OCR ingestion and any core-lane export. Recorded `A1.jpg` as the owner's UI-phase website reference (outside the repo, not committed; logo untouched).
**Files:** `docs/DECISIONS.md` (B-084; B-083's D4 status updated), `docs/PRODUCT_BACKEND_PLAN.md` (Phase 0/2/3/5 + definition of done), `docs/BACKEND_CONTRACT.md` (§6 planned surface), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax's slice 1 (case store + dispatch + HTML export) to review; then delegate slice 2 (sign-off record, multi-period Option A comparison, ops/packaging). D3 disclosure remains deferred by choice.

---

## 2026-10-21 — [computation] Phase-0 answers, slice-1 rescope and the multi-period proposal (B-083)

**Ask:** owner answered the plan's four Phase-0 questions and said "okay do the things while waiting for minimax".
**Did:** recorded the answers as B-083 and amended the plan: **D1 accepted** (local single-user v1, to be improved after it is seen working), **D2 accepted** (cases kept until the owner deletes them, no outbound transfer, model assistance off by default), **D3 deferred** — the AI-use disclosure export is removed from slice 1 and returns later as its own separately-decided slice, **D4 open** — explanation requested; sign-off stays in Phase 2 and its record schema does not depend on the wording. Rescoped slice 1 accordingly: local case store + additive route dispatch + **stdlib HTML export** of the delivered report verbatim (no disclosure, no third-party dependency; DOCX/XLSX deferred behind a declared product-layer dependency). Wrote `docs/proposals/MULTI_PERIOD_VERSIONING.md`: multi-period comparatives and case versioning split into **Option A** (product layer, no unfreeze — one existing session per period stored as an immutable case version, compared side by side under declared comparability rules, recommendation) and **Option B** (core multi-period delivery: single spec with N periods, per-period artifacts and a deterministic in-delivery diff — a genuine unfreeze), with acceptance criteria and the owner questions.
**Files:** `docs/DECISIONS.md` (B-083), `docs/PRODUCT_BACKEND_PLAN.md`, `docs/BACKEND_CONTRACT.md` (§6 planned surface), `docs/proposals/MULTI_PERIOD_VERSIONING.md` (new), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** D4 wording choice (owner); A-vs-B choice for multi-period (owner); MiniMax's slice 1 to review — the delegation addendum says item 3 (disclosure) is deferred and must not be committed. My next computation-owner work while waiting: review slice 1 and wire the product dispatch into the server once it passes.

---

## 2026-10-21 — [computation] REW manual inventory refresh (v0.4, from the review queue)

**Ask:** queue item from the decision-briefs review (appendix B items 2-4): the ratified REW manual's "what exists in code today" table had gone stale.
**Did:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` §13 refreshed to match the code and bumped to v0.4: the durable append-only retrieval log with fail-closed writes and `reverify` (B-058), Crossrefâ†’OpenAlex failover with recorded attempts and the manual drift sweep (B-064), the full verified-method library and applied methods, CSV/TSV + XLSX ingestion with sheet selection and a declared merged-cell policy (B-065/B-071/B-076), APA/Harvard citation formatting (B-059), and the AI-use disclosure export listed as a planned product-backend item (B-081). §16 change log records the refresh. The stage list, checkpoints, screening log and manuscript assembly remain **not built**, and R1-R10 remain proposals — the refresh changes only the factual inventory, not any status claim.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md`, `docs/proposals/DECISION_BRIEFS.md` (appendix B items marked fixed), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to the plan's D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 product slice. The two register-hygiene items from the briefs were fixed in this same increment: the duplicate B-031 row is marked SUPERSEDED, and the R1-R10 ratification now has the open decision row **B-082** (the row tracks it; the owner still decides it).

---

## 2026-10-21 — [computation] Product-backend sequence and delegation boundary (B-081)

**Ask:** "let's do your recommended sequence of finishing the backend product before finally doing the UI. delegate some work to minimax when you dont have to do it."
**Did:** wrote the sequence down as a working plan instead of ad-hoc instructions, and fixed the file-level boundary that lets both owners work in the same repo in parallel. New `docs/PRODUCT_BACKEND_PLAN.md`: **Phase 0** four owner questions (deployment model, case retention/privacy, disclosure audience, sign-off semantics) each with a slice-1-safe default; **Phase 1** delegated to MiniMax - local durable case store (`src/bp/product/**` as new files + additive `/api/cases` routes, opaque JSON bundles with atomic writes, export/restore/delete), AI-use disclosure export from recorded metadata, DOCX/XLSX export of the delivered report verbatim; **Phase 2** delegated - reviewer sign-off record, ops/observability counters (no case content in logs), offline packaging; **Phase 3** computation-owner unfreeze requests, ordered (multi-period comparatives/versioning, then PDF/OCR + SPSS ingestion, core-lane exports only if the product layer cannot host them); **Phase 4** owner-gated tracks (REW ratification, retrieval sources, tax/ledger/templates/reviewers, real-case evaluation); **Phase 5** the UI only after 1-2 are accepted. Boundary rules recorded in B-081 and in `BACKEND_CONTRACT.md` §4: product code and product tests are new files (`src/bp/product/**`, `tests/test_product_*.py`); per increment MiniMax may update only count/version digits in HOME/HANDOFF/CONTRIBUTORS plus one CHANGELOG and one WORKLOG `[product]` entry; the frozen core, existing tests/fixtures, `DECISIONS.md` and claim wording stay untouched; both guards must pass.
**Files:** `docs/PRODUCT_BACKEND_PLAN.md` (new), `docs/BACKEND_CONTRACT.md` (§4/§6), `docs/DECISIONS.md` (B-081), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite (including the frozen-contract and docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 slice to review; the queued REW inventory refresh is the next computation-owner item.

---

## 2026-10-21 — [review] Decision briefs draft (MiniMax task 3), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/decision-briefs`, commit `566a6af`: `docs/proposals/DECISION_BRIEFS.md` (369 lines) with five briefs for the open owner decisions — B-005 reviewers, B-028 next templates, B-032 ledger engine, B-052 taxation, REW R1-R10 — each giving "what it blocks today" citations, the state of the code, options with costs, one clearly labelled MiniMax recommendation, plus an OPEN-items appendix and an appendix of contradictions it found between repository documents.
**Review:** substantive and useful. I verified 55 of its `path:line` citations against the code and docs: 37 exact at master, 13 shifted by under 30 lines (later increments added lines) and 5 shifted materially by B-077's new section — the cited content was found in every case and **no factual claim was contradicted**. Re-checked the contradiction list: #1 (two B-031 rows with different statuses), #2-#4 (the REW manual's inventory still says "no durable log yet" / Excel ingestion not built / statistics library without the later methods), #6 (ledger engine pre-empted by B-044) and #7 (R1-R10 has no decision id of its own) are real; #5 is a wording matter (B-052 is deferred but deliberately kept on the gate list); #8 (SOURCE_INVENTORY.md missing from the HOME spine) was real and is already fixed in `5023aa4`. Annotated the draft rather than rewriting it: a review-status block states the drafting base (`c06c61f`) and that line numbers are as-of that base, the B-066 citation is fixed, #8 is marked fixed, A12 is marked resolved. The stale REW inventory (#2-#4) is **queued** as a separate REW manual refresh (not done here — it edits the ratified manual). The file stays a **DRAFT** in `docs/proposals/`: it changes no decision, no number and no test.
**Files:** `docs/proposals/DECISION_BRIEFS.md` (new), `docs/HOME.md` (proposals row + version), `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite **625 tests OK**; docs links resolve; docs-state guard passes.
**Commit:** `this commit`.

---

## 2026-10-21 — [review] Docs-state sync guard (MiniMax task 1), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/docs-sync`, commit `264fee1` "Add docs-state sync tests": a 335-line `tests/test_docs_sync.py` (7 tests) plus count updates in HOME/HANDOFF/CONTRIBUTORS.
**Review:** the design is sound and the non-tautology requirement is met — every expectation is read from somewhere other than the document being checked (test count from a real `TestLoader().discover`, build from the newest CHANGELOG bullet, method ids from the imported `LIBRARY`, decision rows from `DECISIONS.md`, spine coverage from the `docs/*.md` listing), a missing pattern raises instead of silently skipping, and test 7 proves the parsers actually move when a document's own digits change. I re-ran the claimed proof independently: changing `**625 tests**` to `**626 tests**` in HOME made it fail with `docs/HOME.md says 626 tests, but the suite holds 625 tests`; restoring it went green.
**What I had to reconcile:** the branch was based before B-077/B-078/B-079, so its counts (622) and build (0.51) were stale; on merge the guard correctly failed on 618 vs 625 and on one genuine gap — `docs/SOURCE_INVENTORY.md` had no row in the HOME documentation spine (exactly the kind of drift the guard exists to catch). Fixed the spine row and bumped the docs to build **0.53** / **625 tests**; no assertion was weakened.
**Files:** `tests/test_docs_sync.py` (new), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 7 new tests; full suite **625 tests OK**; mutation proof above; docs links resolve.
**Commit:** `this commit`.

---

## 2026-10-21 — [computation] Freeze the core deterministic backend, delegate the product backend (B-079, B-080)

**Ask:** "freeze the core deterministic backend. let minimax do the product backend."
**Did:** two things. **(1) Freeze, with a guard.** New `docs/BACKEND_CONTRACT.md` states exactly what is frozen (stage/flow contract, spec + hash, the 36 method contracts — id, tier, metric, unit, `test_names` order, claim ceiling, category, input names — the 38 presets, the 12 API route families, the delivery shape and the verification invariants), the unfreeze policy (owner approval â†’ computation owner writes the B-decision, changes code + tests, updates the fixture in the same commit; bug fixes restoring declared behaviour need a trap test but no unfreeze) and the product-backend lane rules. The freeze is **enforced**, not just declared: `tests/test_frozen_contract.py` compares the live library/presets/server source against `tests/fixtures/frozen_contract.json` and fails with a message naming the freeze. **(2) Ownership.** Recorded the owner directive that the product backend is the design owner's lane (B-080) — additive routes/modules/storage/workflows over the frozen core, with the hard boundary that MiniMax may not edit frozen modules, tests, the fixture or factual docs, may not compute or adjust any number/threshold/rating/caveat/honesty notice/claim wording, and new endpoints must delegate computation to the frozen method library (never reimplement a formula). A needed core change is an unfreeze request handled by the computation owner under B-079.
**Files:** `tests/test_frozen_contract.py` (new), `tests/fixtures/frozen_contract.json` (new), `docs/BACKEND_CONTRACT.md` (new), `docs/DECISIONS.md` (B-079, B-080), `docs/CONTRIBUTORS.md` (§1B, stop-and-ask, fact map), `docs/HANDOFF.md`, `docs/HOME.md`, `README.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 3 new contract tests (methods/presets/routes match the frozen fixture; route count still 12); full suite **618 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** nothing computation-side is unblocked now — the lane is drained and frozen. The next phase is the design owner's product backend (B-080). Open owner decisions remain B-005 (reviewers), B-028 (templates), B-032 (ledger engine), B-052 (tax), REW R1–R10 (ratification), plus the frontier-model lane parked in B-075. MiniMax's docs-sync test and decision-brief drafts are still awaiting the owner's go for review/merge.

---

## 2026-10-21 — [computation] Equity bridge and mid-year DCF timing (B-078)

**Ask:** "go" for the valuation completion — the last unblocked computation item.
**Did:** two linked valuation pieces. New T2 **`equity_bridge`**: takes a declared enterprise value and subtracts declared net debt (debt minus cash), minority interest and preferred equity to report an equity value, plus a per-share value only when `shares_outstanding` is declared (no dilution, options or treasury method). Negative bridge components are refused as sign errors; a non-positive share count is refused; a **negative equity value is reported** because an EV that does not cover the declared claims is a real finding, not an input error. `dcf_valuation` gained a declared **mid-year timing convention** as an optional enum (`timing: end|mid`, default `end`): under `mid`, explicit flow t and the terminal value are discounted at exponent tâˆ’0.5 / nâˆ’0.5, so every flow is assumed mid-period; the default leaves every existing output, golden fixture and re-performance bundle unchanged. Five frozen checks for the bridge, a sixth check for the mid-year DCF path; presets `dcfmid`/`equitybridge`; sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-078, changelog 0.51, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 6 new tests — bridge arithmetic against an independent float route (equity value 1570939.14; net debt 150000; per-share 15.7093914), frozen checks declared and passing with and without a share count, refusals for negative components and bad share counts, pipeline delivery (9 artifacts, USD), mid-year DCF against an independent half-period loop, mid > end, invalid timing refused, presets and determinism. Full suite **615 tests OK**.
**Commit:** `this commit`.
**Open/next:** this drains the unblocked computation lane. What remains is owner-gated (open decisions B-005/B-028/B-032/B-052, REW R1–R10), frontier-model parked (B-075), or backend features that need a B-decision before build (AI-use disclosure export, reviewer workflow, case workspace/retention, versioning, model pinning/drift gate). The workbench UI is the design owner's domain (B-066) and the backend contract (routes, presets, JSON) is stable for it.

---

## 2026-10-21 — [computation] IRR and discounted payback (B-077)

**Ask:** "now what's next for you to do?" — with the docs-sync guardrail at MiniMax and the decision briefs also delegated, the next unblocked computation item was the gap map's capital-budgeting completion.
**Did:** two T1 methods, both on the `npv` timing convention (first cash flow at t=0, end-of-period after that). **`irr`**: the discount rate at which the declared cash flows have zero NPV, found by bracketing the NPV function over the declared range -99.99% to 1000% and bisecting (reference route: Newton-Raphson). A cash flow that never changes sign has no IRR and is refused; a cash flow with several sign changes can have several IRRs, so the method **refuses and lists the roots** rather than choosing one. **`discounted_payback`**: cumulative present values until the initial outlay is recovered, with the recovery interpolated linearly inside the recovering period; a positive first cash flow is refused and an outlay never recovered within the horizon blocks instead of reporting a number; `rate` is optional and defaults to 0 (ordinary payback). Both have declared-unit templates (IRR as a percentage), presets `irr`/`dpayback`, sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_investment.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-077, changelog 0.50, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — IRR matches its independent Newton route and the NPV-zero identity, crosses zero at the root, is scale-free; signless and multi-root cash flows refused; discounted payback matches the float route, equals the ordinary payback at rate 0, cannot shorten when the rate rises, is scale-free, and blocks when never recovered; pipeline delivery for both (percentage rendering; artifacts/test-set parity); presets and determinism. Full suite **609 tests OK**.
**Commit:** `this commit`.
**Open/next:** valuation completion remains the natural next unblocked item (equity bridge from enterprise to equity value, mid-year convention in `dcf_valuation`); everything else unblocked is either parked for the frontier-model lane (B-075) or gated on an owner decision (B-005/B-028/B-032/B-052, REW R1–R10).

---

## 2026-10-21 — [computation] XLSX sheet selection and merged-cell policy (B-076)

**Ask:** "do number 2" — the XLSX hardening item (multi-sheet selection + a declared merged-cell policy) from the proposed next-three list.
**Did:** `read_xlsx`/`read_table` now take `sheet` (exact case-sensitive name or 1-based position; default still the first sheet; unknown names/numbers refused listing the workbook's sheets) and report `sheets` + `sheet_index` on every XLSX table. Merged cells are **refused by default** with the ranges named and the declared alternative offered, because repeating an anchor across its range or blanking it would fabricate or lose data; `merged="top_left"` expands each range from its anchor, skips blank anchors, refuses overlapping/nested merges as malformed, and records `merged_cells` plus a provenance-note sentence calling the repetition a declared convention. `sheet`/`merged` are XLSX-only and refused for CSV/TSV. Wired through `POST /api/ingest` as optional fields and the CLI as `--sheet`/`--merged`. **Also fixed a latent bug:** the workbook relationship id was looked up with a malformed namespace, so every workbook silently fell back to `sheet1.xml` — harmless while only the first sheet was read, fatal for sheet selection; the fallback now applies only to the first sheet when the relationship is genuinely absent.
**Files:** `src/bp/ingest.py`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-076, changelog 0.49, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — select-by-name/index with metadata, unknown/invalid sheet refusals, CSV option refusals, default merged refusal naming the range, declared expansion (values + `merged_cells` + provenance note), malformed and overlapping merge refusals, merged-header duplicate refusal, API sheet selection and merged policy (including an invalid policy); CLI exercised by hand for default/sheet-by-name/sheet-by-number/unknown-sheet/merged-refuse/merged-top_left; full suite **598 tests OK**.
**Commit:** `this commit`.
**Open/next:** **[design]** the workbench ingestion card still sends only filename+base64 — exposing the new optional `sheet`/`merged` fields is presentation work for the design owner (B-066). Remaining ingestion gaps stay refused/declared: PDF/OCR/SPSS, and reading several sheets into one table (needs a declared concatenation rule).

---

## 2026-10-21 — [documentation] Parked frontier-model queue, and a truthful HANDOFF

**Ask:** "on those computations that require deepseek pro, write or park it in the manual or notes, as we will get back to them when we have enough credits."
**Did:** created `docs/PARKED_QUEUE.md` — the register for the six heavy statistics items reserved for the DeepSeek Pro lane (Tukey/Dunnett/Games-Howell, unbalanced two-way/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series). Each row states the blocker, the offline oracle already installed for goldens, and the output that would be accepted; the file also separates the *non*-frontier items (imputation, standards/filings/tax retrieval, PDF/OCR/SPSS ingest, breadth templates, REW) so they are not mistaken for the parked lane, and states the un-park trigger: an explicit owner grant of the frontier lane, not a general "continue". Recorded as B-075. **Fixed the stale handoff**: `HANDOFF.md` still said build 0.40 / 510 tests and listed as unbuilt everything finished since (paired/one-sample t, factorial/post-hoc, valuation, economics, appraisal, logistic/alpha, ingestion mapping); it now reports 0.48 / 588, carries the full method list, marks section A done, restates section C with what is built vs parked, and adds section H pointing at the parked queue. `HOME.md` gained the parked-queue rows and lost its stale "DCF/WACC … not built" line; `CONTRIBUTORS.md` links the queue and lists un-parking under "stop and ask".
**Files:** `docs/PARKED_QUEUE.md` (new), `docs/HANDOFF.md`, `docs/HOME.md`, `docs/CONTRIBUTORS.md`, `docs/DECISIONS.md` (B-075), `docs/WORKLOG.md`.
**Verified:** documentation-only increment; no code, test or fixture touched. Relative links in the new/edited files resolve; the suite is unchanged at **588 tests OK**.
**Commit:** `this commit`.
**Open/next:** the computation lane is caught up on everything buildable without the frontier model or an owner decision. Remaining work is owner-gated: parked queue (B-075, needs credits), B-005 reviewers, B-028 templates, B-032 ledger engine, B-052 taxation, REW R1–R10 ratification. Design/presentation is MiniMax's domain (B-066).

---

## 2026-10-21 — [computation] Logistic regression and Cronbach's alpha (B-074)

**Ask:** "correction, finish those you can do" — the remaining statistics items that do not need a frontier model or a new distribution.
**Did:** two T1 methods. `logistic_regression`: binary 0/1 outcome with up to five numeric predictors, Newton-Raphson (IRLS) at 1e-10 tolerance, no regularisation, Wald standard errors/p-values, odds ratios, log-likelihood, null log-likelihood and McFadden pseudo R-squared; non-convergence/separation, single-class outcomes, non-0/1 codes and collinear designs are refused. `reliability_alpha`: Cronbach's alpha from an items column map, listwise deletion with the excluded count, the classic k/(k-1)(1 âˆ’ Î£item variances / total variance) formula. Goldens for the logistic model generated from `statsmodels.Logit` offline; five frozen checks each; presets `logit`/`alpha`; sandbox and session coverage.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_logit_reliability.py`, `tests/fixtures/logistic_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-074, changelog 0.48, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 9 new tests — all statsmodels goldens matched (coefficients, SEs, p-values, log-likelihood, pseudo RÂ²), frozen checks, separation/single-class/bad-code refusals, alpha against an independently coded classic formula, refusals for single-item and zero-variance cases, pipeline delivery for both, contract/preset, determinism. **588 tests OK.**
**Commit:** `this commit`.
**Open/next (for the frontier model):** k-means clustering, factor analysis, unbalanced/ANCOVA/repeated-measures designs, Tukey/Dunnett/Games-Howell, non-linear time series. The offline oracles for these are installed (sklearn, factor_analyzer, statsmodels AnovaRM, scipy studentized_range/dunnett).

---

## 2026-10-21 — [computation] CBA, cost-effectiveness and SROI (B-073)

**Ask:** "go on: … CBA/CEA/SROI."
**Did:** three T2 appraisal methods. `cost_benefit`: discounted present values of declared costs and benefits, NPV and benefit-cost ratio (omitted when PV costs are zero); five frozen checks. `cost_effectiveness`: ICER for each option against the first-listed comparator, with incremental cost/effect and dominance flags; refuses a single option, negative costs and a zero effect difference. `sroi`: present value of declared social benefits over the declared investment, with net value; refuses a non-positive investment. All three are arithmetic on owner valuations — no effect is monetised by the system, no deadweight/additionality adjustment is invented, and no willingness-to-pay threshold is assumed.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_appraisal.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-073, changelog 0.47, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — present values against an independently written discounting loop, ICER/dominance arithmetic, SROI ratio identity, frozen checks, refusals for mismatched lengths, zero-effect comparators and non-positive investments, pipeline delivery for all three, contract/preset, determinism; sandbox and session coverage. **579 tests OK.**
**Commit:** `this commit`.
**Open/next:** remaining from the batch — ANCOVA / repeated measures / unbalanced designs, Tukey–Dunnett–Games-Howell, logistic regression, reliability/factor analysis, clustering, non-linear time series. The first three groups need either a ratified SS/design convention or distributions the standard library lacks (studentized range, multivariate t); logistic regression, reliability and clustering are feasible with declared conventions.

---

## 2026-10-21 — [computation] Ingestion mapping, unit economics and multi-product break-even (B-071, B-072)

**Ask:** "go on: … unit economics / multi-product break-even … ingestionâ†’method mapping helper."
**Did:** `ingest.to_method_inputs` maps named columns into a method's declared inputs — `value_list`/`code_list` from one column, `column_map` from an object of name â†’ column, cleaned through the method's own `validate_inputs` and `profile` so a bad mapping is refused before running; only list-shaped inputs (a scalar rate cannot come from a column), and the provenance note says the file hash identifies the source, not that the data is verified. Exposed as an optional `map` on `POST /api/ingest`. Then two T1 finance methods: `unit_economics` (margin, margin rate, payback, optional period-value LTV and LTV/CAC) and `multi_product_breakeven` (mix-weighted contribution margin, break-even units and revenue, per-product units), each with five frozen checks and declared assumptions (constant churn, fixed mix, no tax/discounting).
**Files:** `src/bp/ingest.py`, `src/bp/server.py`, `src/bp/methods.py`, `tests/test_economics.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-071/B-072, changelog 0.46, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — columnâ†’method mapping (value and column_map shapes), refusals for text/unknown/scalar/unmapped inputs, unit-economics arithmetic and refusals, multi-product break-even arithmetic (break-even 2000 units; 1500 coffee / 500 cake; revenue 10500) and refusals, frozen checks, pipeline delivery, contract/preset, determinism; sandbox and session coverage. **568 tests OK.**
**Commit:** `this commit`.
**Open/next:** CBA/CEA/SROI, reliability (Cronbach's Î±), logistic regression, clustering, non-linear time series; ANCOVA/repeated-measures/unbalanced designs and Tukey/Dunnett/Games-Howell need distributional work (studentized range / multivariate t) not in the standard library.

---

## 2026-10-21 — [computation] Factorial two-way ANOVA and post-hoc pairwise tests (B-070)

**Ask:** "go: factorial ANOVA + post-hoc pairwise tests."
**Did:** added two T1 methods. `two_way_anova`: balanced two-way factorial ANOVA on one numeric response — both main effects and the interaction, sums of squares, mean squares, F tests, degrees of freedom and partial eta-squared. Unbalanced designs and empty cells are **refused** (the SS type would be an unratified convention). Five frozen checks: independent float route, SS decomposition, F = MS/MS_error, shift invariance, scale equivariance of F. `posthoc_pairwise`: every unordered pair of independent groups compared with a Welch t-test, reporting the difference, raw p and adjusted p under a **declared** correction (Holm default, Bonferroni, or explicitly `none`), with `n_pairs`, `n_rejected` and the pair design recorded. Five frozen checks: independent float route, adjusted â‰¥ raw, declared correction reproduced step by step, pair count = k(kâˆ’1)/2, reversing group order negates differences and keeps p. Goldens generated offline with numpy/scipy; both wired into sandbox CASES, the session input map and presets `factorial`/`posthoc`; a `records` input type was added for the factorial design.
**Files:** `src/bp/methods.py` (records input type, both methods and contracts), `src/bp/server.py` (presets), `tests/test_factorial_posthoc.py`, `tests/fixtures/two_way_golden.json`, `tests/fixtures/posthoc_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-070, changelog 0.45, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 12 new tests — goldens against numpy/scipy for a main-effects and an interaction design, hand-computable exact SS/F values (8/32/0/8, F 4/16/0), frozen checks declared and passing, unbalanced/broken-design refusals, Welch+Holm goldens, adjustment-method behaviour, invalid-group refusals, full pipeline delivery for both, contract/preset assertions, determinism. **557 tests OK.**
**Commit:** `this commit`.
**Open/next:** unbalanced/ANCOVA/repeated-measures designs and Tukey/Dunnett procedures; then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Multi-currency: ISO 4217 registry, per-currency precision, declared-rate conversion (B-069)

**Ask:** "also allow it to use multi-currencies that include dollar, euro, and chinese yuan and other currencies of the world."
**Did:** `src/bp/currency.py` — a declared ISO 4217 table of 160+ currencies with their **minor units** (0 for JPY/KRW/VND/ISK, 3 for KWD/BHD/OMR, 4 for CLF, 2 for USD/EUR/CNY and most others), code normalisation and validation, and exact Decimal conversion at a rate the owner **declares** (with provenance `user`/`sourced`/`assumption`, a mandatory source for `sourced`, and an optional declared date). Wired into the computation layer: unknown currency codes are refused at intake; money artefacts default to the currency's minor units when the request states no precision (JPY prints no cents, KWD prints three); a management-accounts spec takes its `places` default from its currency; new T1 method `currency_convert` with five frozen checks (float second route, reciprocal-rate round trip, zero, sign symmetry, linearity); `GET /api/currencies` lists the registry; preset `currency`. No exchange rate is fetched, hard-coded or verified, and one engagement stays single-currency (no consolidation or translation).
**Files:** `src/bp/currency.py`, `src/bp/methods.py` (currency and text input types + method), `src/bp/orchestrator.py` (intake validation, per-currency precision), `src/bp/accounts.py` (currency validation, places default), `src/bp/server.py` (catalog endpoint, preset), `tests/test_currency.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-069, changelog 0.44, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 14 new tests — major/zero/three/four-decimal currencies, 160+ code coverage, normalisation and unknown refusals, conversion arithmetic, same-currency rule, provenance rules, invalid amounts/rates, pipeline delivery with the appendix recording codes/rate/provenance/date, per-currency precision through npv (JPY 0, KWD 3, USD 2), unknown-currency intake refusal, accounts `places` defaults, `/api/currencies`, contract/preset, determinism; sandbox and session coverage via the shared maps. **545 tests OK.**
**Commit:** `this commit`.
**Open/next:** FX retrieval/verification and statement translation/consolidation remain out (they need a rate source and a translation standard); statistics backlog resumes with factorial ANOVA + post-hoc, then unit economics / CBA.

---

## 2026-10-21 — [computation] Valuation: WACC and DCF (B-068)

**Ask:** "go. automate everything" — continue the computation backlog without waiting for instruction.
**Did:** two valuation methods. `wacc` (T1): weighted average cost of capital from declared market values of equity and debt and declared costs of equity and **after-tax** debt; reports the WACC and both weights; five frozen checks (float second route, weights sum to one, WACC between the two costs, scaling both values changes nothing, a higher cost of equity raises the WACC); no tax is computed. `dcf_valuation` (T2): declared end-of-period free cash flows discounted at a declared rate, optional Gordon-growth terminal value on the last flow; reports explicit PV, terminal PV, terminal value, enterprise value, terminal share and the inputs; five frozen checks (second route, linear scaling in the cash flows, higher rate lowers value, terminal value equals the Gordon formula, no growth means no terminal value); refuses growth at or above the rate, a rate at or below -100% and an empty forecast. Both wired into sandbox `CASES`, the session input map and presets `wacc`/`dcf`.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-068, changelog 0.43, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — arithmetic against an independently written discounting loop, five frozen checks each, refusals for invalid capital structures and DCF assumptions, full pipeline delivery for both with percentage/currency rendering, contract/preset assertions, determinism; sandbox parity and session coverage. **531 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA + post-hoc pairwise tests (using the existing `multiple_comparison`), then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Inference completion 1: paired and one-sample t-tests (B-067)

**Ask:** "go. automate everything" — work the computation backlog autonomously.
**Did:** added two T1 methods that close the manual's 9B.2 paired/one-sample gap. `paired_t`: within-pair differences (first column minus second), a pair dropped and counted when either side is missing, with mean difference, sd/se, t, df, two-sided p, confidence interval, Cohen's dz and both column means; five frozen checks (independent float route, swapping columns negates the difference and t but keeps p, shift/scale behaviour, row-order invariance, missing pairs dropped not imputed). `one_sample_t`: one mean against a declared reference `mu0`, with sd/se, t, df, p, CI, Cohen's d and excluded count; five frozen checks (second route, shift invariance, positive scale equivariance, row-order invariance, missing entries excluded not valued). Both default to two-sided, refuse constant data through the profile, and are wired into the sandbox `CASES` test, the session input map and workbench presets `paired`/`onesample`; goldens generated offline with scipy (test fixtures only).
**Files:** `src/bp/methods.py` (both methods + contracts), `src/bp/server.py` (presets), `tests/test_inference_more.py`, `tests/fixtures/inference_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-067, changelog 0.42, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — scipy goldens to 1e-9, frozen checks declared and passing, constant-data and missing-reference refusals, full pipeline delivery for both, contract/preset assertions, determinism; sandbox parity and session coverage via the shared maps. **520 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA and post-hoc pairwise tests (using the existing `multiple_comparison`), then DCF + WACC.

---

**Newest first. Never rewrite an entry.** One entry per increment (not per message): the ask, what changed, what verified it, the commit, and what is next. Link to the source of truth rather than restating it — `CHANGELOG.md` has the build detail, `DECISIONS.md` the reasoning, this file the narrative and the sequence.

---

## 2026-10-21 — 9B.3 upgrade: power and minimum-effect planning (B-061)

**Ask:** "go" — continue closing the open statistics items (after multiple-comparison correction).
**Did:** added the T1 method `power_analysis` for a two-sample or one-sample comparison of means under the **normal approximation**: power for a stated effect, and the smallest effect that reaches a declared target power, plus standard error, non-centrality and the z critical value. Inputs declare design, effect, sample sizes, standard deviations, alpha (default 0.05), tails (two-sided default) and target power (default 0.8); one-sample designs refuse `n2`/`sd2`; invalid numbers, alpha or sizes are refused at intake. Five frozen checks: erfc-based independent second route agrees to 1e-9, zero effect gives power = alpha, power rises with effect size and with sample size, minimum effect falls with sample size. The normal approximation and its limits (no noncentral t, no proportions, no clustering/weights/repeated measures, no multiplicity) are declared in the template, caveats and appendix. Golden fixture generated offline with `scipy.stats.norm`; no scipy at runtime. The draft-audit claim checker caught the first template draft using "effect of" (intervention language) — reworded rather than weakening the checker.
**Files:** `src/bp/methods.py` (core, reference route, checks, profile, typing, caveats, template, contract), `src/bp/server.py` (preset `power`), `tests/test_power.py`, `tests/fixtures/power_golden.json`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-061, changelog 0.36, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-061.
**Verified:** 8 new tests — scipy golden values (three designs) to 1e-9 relative, zero-effect = alpha, one-sided vs two-sided ordering, sample-size movements, five invalid-input refusals, full pipeline delivery with licensed report, contract/preset, determinism; sandbox parity and session coverage via shared maps. **465 tests OK.**
**Commit:** `this commit`.
**Open/next:** missing-data mechanism modelling and survey weights are the last 9B.3 items and need a declared convention choice (extreme-bounds vs imputation; design vs frequency weights); then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — [computation] Model-ownership split: computation vs design (B-066)

**Ask:** "we will divide the job… keep the computation part here; design/aesthetics goes to MiniMax. Put this rule in the manual that models can read that computation are exclusively your domain."
**Did:** recorded the division of labour as a binding rule in the two documents every model reads first: `docs/CONTRIBUTORS.md` **§1A** (new section) and `docs/HANDOFF.md` §2.9. Computation is exclusively the computation owner's (DeepSeek) domain — `src/bp/**`, `tests/**` and fixtures, the factual docs, every number/statistic/accounting figure, verification and audit logic, citation rules, type inference, claim ceilings and asserted wording, and any prompt affecting what is produced or validated. Design/aesthetics is exclusively the design owner's (MiniMax) domain — the workbench's presentation and look (`web/**` layout, CSS, typography, colour, spacing, iconography, responsiveness, component styling, visual report design) and behaviour-neutral interaction affordances. Boundary rules: design may not change numbers/claims/checks/schemas/tests; computation may not silently restyle (functional wiring only); neither owner edits the other's files, and cross-domain needs are noted here tagged `[computation]`/`[design]`; cross-domain features land as a computation commit then a design commit; conflicts escalate to the owner; the verification non-negotiables bind both.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` (B-066), `docs/CHANGELOG.md` (0.41). No code changed.
**Verified:** docs only; test suite untouched at 510 tests.
**Commit:** `this commit`.
**Open/next:** the computation backlog is now the only work in this conversation — next increment is the paired/one-sample t-test pair, then DCF + WACC.

---

## 2026-10-21 — Ingestion first slice: CSV/TSV and XLSX to a typed table with provenance (B-065)

**Ask:** "go" — the other P0 gatekeeper: ingestion.
**Did:** added `src/bp/ingest.py`, standard library only. CSV/TSV (delimiter sniffed; UTF-8/CP1252/Latin-1) and XLSX (first sheet, read as a zip of XML parts — `zipfile` + `xml.etree`, no third-party library) become a typed table: column names, inferred `number`/`date`/`text`/`mixed` types, present and missing counts, sample values, rows, and a table-level provenance pointer (file, SHA-256, data row i and column j, sheet) stating that nothing is imputed or retyped. Declared conventions: first non-empty row is the header; headers must be non-empty and unique; a mixed number/text column is labelled `mixed` rather than coerced; formula cells use the cached value the file stores; XLSX dates are normalised with the workbook date system (1900 leap-year adjustment); caps of 5 MB / 1000 rows / 50 columns are **refused, not truncated**. **PDF, scans, images and SPSS `.sav` are refused with explicit messages** — no OCR or PDF text extraction exists, so pretending to read them would be invention. Wired as `POST /api/ingest` (base64, 422 on refusal, separate request-size limit), a workbench "Data ingestion" card with file picker and summary, and `python -m bp.ingest <file>`.
**Files:** `src/bp/ingest.py`, `src/bp/server.py` (route, body size), `web/index.html`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-065, changelog 0.40, limitations, gap map, REW §8, HOME, README, CONTRIBUTORS).
**Decisions:** B-065.
**Verified:** 14 new tests — typed CSV with missing/date columns, delimiter and encoding detection, mixed-column labelling, header refusals, row cap, XLSX shared strings/numbers/date styles, corrupt and empty workbook refusals, PDF/PNG/SPSS refusals, API decoder validation, endpoint 200/422, UI card; CLI smoke printed the summary; **510 tests OK**.
**Commit:** `this commit`.
**Open/next:** ingestion remains partial by design — PDF/scan/OCR and SPSS are refused, multi-sheet/merged-cell handling and automatic columnâ†’method-input mapping are not built. Elsewhere: imputation and complex-design inference, standards/filings/tax retrieval sources, and the owner gates (B-005 reviewers, B-028 templates, B-032 ledger engine).

---

## 2026-10-21 — Retrieval failover and drift sweep (B-064)

**Ask:** "go" — close the retrieval extras (declared source priority/failover, drift monitoring).
**Did:** two pieces. **(a) Source priority and failover**: the declared order is Crossref then OpenAlex, the API's default source is now `auto`, and every attempt is recorded in the retrieval log as `resolved` / `not_found` / `error` with the error detail. A source error is never swallowed silently; the next source is tried; if **every** source errors the lookup fails closed (502) instead of labelling the DOI "unverified". **(b) Drift sweep**: `drift_check` re-verifies the most recent logged retrievals and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable` per entry with a summary, flagging changed citations for human re-check and never rewriting the log. Exposed as `GET /api/literature/drift?limit=` (cap 25), a workbench "Check drift" button, and `python -m bp.literature drift [log] [limit]`.
**Files:** `src/bp/literature.py` (failover resolver, attempts in log records, `drift_check`, CLI), `src/bp/server.py` (auto source, sources listing with declared priority, drift endpoint, validation), `web/index.html` (drift button and output), `tests/test_literature_failover.py`, `tests/test_literature_api.py`, docs (B-064, changelog 0.39, limitations, gap map, REW §9 + Q7, HOME, README, WORKLOG, CONTRIBUTORS).
**Decisions:** B-064.
**Verified:** 12 new tests — failover on error and on not-found, all-not-found stays unverified, all-error fails closed, attempts recorded in the log, drift hash_match/hash_differs/unresolvable/unreachable, empty log, drift source order, API auto-source response, drift endpoint and limit validation, UI button; live smoke resolved a real DOI through `default_sources()` with the attempt logged and the drift sweep returning `hash_match`, plus the CLI printing the summary. **496 tests OK.**
**Commit:** `this commit`.
**Open/next:** standards/filings/tax source families (needs a source/licensing decision, not code) and extra scholarly APIs; then ingestion (the other P0), and imputation / complex-design inference for the statistics.

---

## 2026-10-21 — 9B.3 upgrade: weighted summaries with a declared weight kind (B-063)

**Ask:** "go" — close the last statistics item on the open list.
**Did:** added the T1 method `weighted_summary`: weighted mean, weighted standard deviation, total weight, **effective sample size** `(Î£w)Â²/Î£wÂ²` and **design effect** `n/n_eff`, with an overridable weight kind — `reliability` (default; unbiased weighted variance) or `frequency` (observations counted). One positive weight per value including missing entries (a missing value's weight drops with it); zero, negative, mismatched-length and blank weights are refused. **No inference**: no standard error, interval or test, because that needs a declared complex design (stratification, clustering, replicate weights) that is not implemented — and the honesty layer now says exactly that for this method instead of the generic "weights unsupported" line. Five frozen checks: float second route agrees, unit weights reproduce the ordinary sample summary, the mean is invariant to weight scaling, extra weight on larger values raises the mean, and the design effect is 1 for equal weights. The draft-audit claim checker again caught a template phrasing ("design effect of"); the template was reworded rather than the checker weakened.
**Files:** `src/bp/methods.py` (impl, stats helper, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty wording for the weighted method), `src/bp/server.py` (preset `weighted`), `tests/test_weighted.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-063, changelog 0.38, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-063.
**Verified:** 9 new tests — exact weighted mean and reliability/frequency sds, equal weights equal the ordinary summary, missing values drop their weights, all frozen checks, five invalid-input refusals, full delivery with the design disclaimer, contract/preset, determinism; sandbox parity and session coverage via shared maps. **484 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 row is closed except imputation and complex-design inference (each needs its own declared model/design). Next: retrieval extras (standards/filings/tax source families, automatic failover, drift monitoring) and ingestion (the other P0).

---

## 2026-10-21 — 9B.3 upgrade: missing-data bounds with a declared mechanism (B-062)

**Ask:** "go" — continue closing the open 9B.3 statistics items.
**Did:** added the T1 method `missing_data_bounds`. It reports how much of a variable is missing and **bounds** the complete-data mean by the extreme-case convention — every missing value at the observed minimum (lower bound) or maximum (upper bound) — alongside the observed mean, observed range and bound width. The missing-data mechanism (`unknown`/`mcar`/`mar`/`mnar`) is an input the owner **declares**; it is recorded with an explicit note that the system cannot verify it from the data, and it changes no bound. No imputation and no probabilistic missing-data model. Five frozen checks: bounds bracket the observed mean, independently recomputed extreme cases agree, adding missing entries cannot narrow the bounds, the reported share is missing/total, and with no missing values the bounds collapse to the observed mean. The generic honesty layer used to append its listwise-deletion warning to this method — which contradicted the method's own stronger convention — so that notice is now suppressed for it, and the method's own disclaimer is what the delivery carries.
**Files:** `src/bp/methods.py` (impl, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty suppression), `src/bp/server.py` (preset `missing`), `tests/test_missing.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-062, changelog 0.37, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-062.
**Verified:** 10 new tests — exact bound arithmetic, missing codes and blanks both counted, zero-width when nothing is missing, declared mechanism changes no number and is labelled, all frozen checks, three invalid-input refusals, full delivery without the contradictory notice, contract/preset, determinism; sandbox parity and session coverage via shared maps. **475 tests OK.**
**Commit:** `this commit`.
**Open/next:** survey weights are the last 9B.3 item; then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — 9B.3 upgrade: multiple-comparison correction (B-060)

**Ask:** "go on the still open, close them" — the statistical upgrades the honesty layer was only disclosing.
**Did:** closed the multiple-comparison item with a new T1 method `multiple_comparison`. It applies a declared correction to one family of raw p-values: **Holm** step-down (sort ascending, multiply the i-th smallest by kâˆ’i+1, running maximum, cap at 1) or **Bonferroni** (k·p capped at 1). Outputs are `p_adj_1..k`, `n_tests`, `n_rejected` at the declared alpha, with an appendix carrying the raw and adjusted values and the written definition. Five frozen checks: adjusted â‰¥ raw, bounded in [0,1], matches the declared definition (Holm monotone/Bonferroni formula), independent second route agrees to 1e-12, and order-invariance. Invalid p-values, alpha outside (0,1), an unknown method or a family of fewer than two values are refused at intake; a new `enum` input type covers declared method choices. The honesty layer now says a correction is available instead of only "not applied", and OLS's family-wise notice points to it. Existing methods and their goldens are untouched — no reported p-value changed silently.
**Files:** `src/bp/methods.py` (impl, checks, profile, caveats, template, contract, `enum` validation), `src/bp/orchestrator.py` (honesty wording for the correction method and OLS pointer), `src/bp/server.py` (preset `multicomp`), `tests/test_multicomp.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-060, changelog 0.35, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-060.
**Verified:** 10 new tests — published Holm example reproduced exactly (0.03/0.06/0.06/0.02), Bonferroni formula, order-invariance, all frozen checks, alpha-driven rejection counts, four invalid-input refusals, full pipeline delivery with licensed report and honesty block, contract/preset, determinism; sandbox parity and session-input coverage via the shared maps. **457 tests OK.**
**Commit:** `this commit`.
**Open/next:** power/MDE calculation, missing-data mechanism modelling and survey weights are the remaining 9B.3 items and need their own declared conventions (they change what is estimated or the input contract); retrieval still lacks standards/filings/tax source families, automatic failover and drift monitoring; ingestion is the other P0.

---

## 2026-10-21 — Citations: APA 7 and Harvard ratified and implemented (B-059)

**Ask:** "citation styles will be apa and harvard" — close the open citation item.
**Did:** replaced the provisional layout with the two ratified styles. Sources now map the bibliographic metadata the citation needs: Crossref supplies structured family/given names, volume, issue, pages, publisher and type; OpenAlex supplies volume/issue/pages and a type mapping but only display names. APA 7 renders `Family, I. (Year). Title. Journal, volume(issue), pages. https://doi.org/...` with APA's `&`/serial comma; Harvard renders `Family, I. and … (Year) 'Title', Journal, volume(issue), pp. pages. doi: ...`. Books have their own layout; any other source type gets a labelled generic layout instead of pretending it is fully styled. Rendering limits are declared in every citation's notice (plain text has no italics; titles are not case-converted; names are inverted only when the source supplies family/given, with a note when it does not). Unverified references stay prefixed `[unverified user-supplied…]` in both styles. API `cite` now accepts `apa`/`harvard`, the sources endpoint exposes both notices and the reference payload carries the new bibliographic fields; the workbench has a style selector and "Get citation".
**Files:** `src/bp/literature.py` (reference fields, source mappings, APA/Harvard formatters), `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-059, CHANGELOG 0.34, KNOWN_LIMITATIONS, REW manual §9 + Q9, HOME, README, CONTRIBUTORS, WORKLOG).
**Decisions:** B-059 (RESOLVED).
**Verified:** 5 new/updated tests — Crossref and OpenAlex field mapping, exact APA and Harvard strings, book and generic layouts, non-inverted-name note, unverified labelling in both styles, ratified style list, unknown style refused, API style selection; live smoke against Crossref rendered a real eight-author APA and Harvard citation. **447 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 statistical upgrades (multiple-comparison correction, power/MDE, missing-data mechanism modelling, survey weights), the remaining retrieval items (standards/filings/tax source families, failover policy, drift monitoring) and ingestion.

---

## 2026-10-21 — Retrieval layer second slice: durable log and provisional citation (B-058)

**Ask:** "GO" after the 9B.3 honesty layer — continue down the gap order at the P0 gatekeeper.
**Did:** two halves of the retrieval layer. **(a) Durable retrieval log**: every retrieval that reaches a source is appended to a local newline-delimited JSON file (source, DOI, supplied and resolved title, status, authors, year, container, UTC retrieval time, response SHA-256), flushed to disk **before** the reference is returned — an unwritable log raises and the retrieval fails closed, so an unaudited citation cannot be produced. `read_log` refuses a corrupt or unknown-format log; `reverify` re-checks a logged entry against the source and reports `hash_match` / `hash_differs` / `unresolvable_now`. **(b) Provisional citation layout**: one declared author-date format (authors as returned, year, title, container, DOI) with an explicit PROVISIONAL notice — no institutional style is claimed, because none has been ratified (REW Q9). Unverified references are formatted only with the `[unverified user-supplied…]` prefix and never as if checked. Wired into the API (`cite` parameter, `GET /api/literature/log`), the workbench (citation line, retrieval-log panel with the new "Get provisional citation" and "Show retrieval log" controls), and `.gitignore` so the runtime log cannot be committed. `BP_RETRIEVAL_LOG` sets the path; empty disables it.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `.gitignore`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-058, CHANGELOG 0.33, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, REW manual §9 + Q9/Q10, HOME, README, CONTRIBUTORS).
**Decisions:** B-058.
**Verified:** 17 new tests — log fields and single-line records, unverified retrievals logged honestly with resolved title, no logging without a retrieval, unwritable log fails closed, empty/corrupt/unknown-format log handling, append-only ordering, `reverify` states, citation structure and provisional notice, unverified labelling and mismatch note, placeholders instead of invented authors/years, unknown style refused, determinism; API tests for citation, style validation, log endpoint, limit validation and disabled state; UI strings asserted. **442 tests OK.** Live smoke: real Crossref retrieval logged with a genuine sha256, citation correctly labelled unverified for a deliberately wrong title, `reverify` returned `hash_match`.
**Commit:** `this commit`.
**Open/next:** retrieval-layer remainder — standards/filings/tax source families, source priority and failover, a ratified citation style (Q9) and drift monitoring; then the actual 9B.3 statistical upgrades or the next gap-map item.

---

## 2026-10-21 — 9B.3 honesty layer: disclosure and refusal, no numbers changed (B-057)

**Ask:** the other half of Slice 1 as agreed — the 9B.3 honesty pass on existing statistical outputs.
**Did:** scoped it honestly rather than overclaiming. The layer **discloses** what the system does not do, in every delivery: (a) missing values are excluded listwise and the missing-data mechanism (MCAR/MAR/MNAR) was not established; (b) multiple hypotheses are not corrected, with the family-wise exposure named for OLS coefficients and "one omnibus, no post-hoc comparisons" for ANOVA/Kruskal-Wallis; (c) no power or minimum-detectable-effect is reported, so precision must be read from the interval; (d) survey weights, clustering and repeated measures are unsupported, so every observation is treated as independent. These are both machine-readable (`appendix.honesty`) and plain sentences in the report. Separately, inputs that name an unsupported structure (`weights`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are now refused with a specific reason instead of a generic unknown-input error — a weighted or clustered dataset can no longer be passed in and silently analysed as independent observations. **No number changed.** The actual upgrades (Holm/Bonferroni, power/MDE, missing-data modelling, survey weights) are recorded as still open, so the layer cannot be mistaken for the fix.
**Files:** `src/bp/orchestrator.py` (honesty helper, appendix block, report sentences), `src/bp/methods.py` (unsupported-structure refusal in `validate_inputs`), `tests/test_honesty.py`, docs (DECISIONS B-057, CHANGELOG 0.32, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, REW manual §10, CONTRIBUTORS count).
**Decisions:** B-057.
**Verified:** 10 new tests — appendix block present for every delivered method, descriptive/omnibus/OLS disclosures, NPV and ratio methods report not-applicable rather than blank, determinism and JSON-safety, refusal of weights/clusters/strata with the specific reason, generic unknown-input message preserved; **425 tests OK** (no existing test changed behaviour).
**Commit:** this commit.
**Open/next:** the actual 9B.3 statistical upgrades are still the open row (correction, power, missing-data modelling, weights); the P0 gatekeeper (retrieval + citation: durable retrieval log + citation formatting) is the next build target.

---

## 2026-10-21 — Ratio analysis: the safe half of Slice 1

**Ask:** after the documentation spine, continue with Slice 1 as agreed — the risk-paired first gap closures (honesty upgrades + statement ratios).
**Did:** added the T1 method `ratio_analysis` (B-056). Fifteen declared ratios across liquidity (current, quick, cash), profitability (gross/operating/net margin, return on assets, return on equity), solvency (debt to equity, equity multiplier, interest cover) and efficiency (asset turnover, receivables/inventory/payables days) computed in Decimal from figures the owner supplies. Each ratio reports its definition, inputs and unit; a ratio with a missing figure or a zero denominator is listed in the appendix as not computed **with its reason** and never estimated; a negative denominator is computed and flagged; the balance-sheet identity is checked when assets, liabilities and equity are all supplied; supplied figures are verified to be used exactly as given. No benchmark, industry average, cut-off or good/bad verdict is applied — the manual forbids inventing ratings. The independent second route is exact rational arithmetic (`fractions.Fraction`), and the golden fixture is generated by a separately written Fraction re-implementation, not by the method itself. Added the `ratios` workbench preset; the `days` unit is no longer given a currency in the orchestrator.
**Files:** `src/bp/methods.py` (catalogue, impl, checks, profile, caveats, template, contract), `src/bp/orchestrator.py` (unit exemption), `src/bp/server.py` (preset), `tests/test_ratio.py`, `tests/fixtures/ratio_golden.json`, `tests/test_sandbox.py` `CASES`, `tests/test_session_api.py` input map, README, docs (DECISIONS B-056, CHANGELOG 0.31, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, CONTRIBUTORS count).
**Decisions:** B-056.
**Verified:** 15 new tests covering golden values, every frozen check, scale invariance, sign behaviour, missing-figure disclosure, zero denominators, negative equity, balance-sheet identity (holds / fails / not applicable), Decimal outputs, determinism, intake blocking, preset reachability and a full pipeline delivery with a licensed report; sandbox parity via the shared `CASES` test; **415 tests OK**.
**Commit:** this commit.
**Open/next:** the other half of Slice 1 — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison correction, power/precision statements, missing-data mechanism declaration, survey-weight/cluster detection), then retrieval + citation (P0 gatekeeper).

---

## 2026-10-21 — Documentation spine: contributors' manual, home map, this worklog

**Ask:** after the gap discussion, the owner asked for a log that traces the work, a manual for any model that will touch or fix the files, and an Obsidian-like map to find things — then "go".
**Did:** added three documents and wired them in: `docs/CONTRIBUTORS.md` (ten non-negotiables, the add-a-method checklist, bug-fix rules, boundary-change rules, the testing contract, environment traps, "where each fact belongs", rejection list, stop-and-ask list), `docs/HOME.md` (task view, module map, capability status, documentation spine, map conventions), and this `docs/WORKLOG.md`. Design choices confirmed with the owner: `CONTRIBUTORS.md` is a repo-level bridge (not part of the authority manual), `HOME.md` uses plain Markdown links rather than Obsidian wikilinks, and the worklog starts now with a backfill pointer rather than reconstructing history.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HOME.md`, `docs/WORKLOG.md`, `README.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md` (B-055).
**Verified:** docs only; suite unaffected (400 tests OK run in the previous increment). Links checked against the files present in the repo.
**Commit:** this commit.
**Open/next:** Slice 1 of the gap plan — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison, power/precision, missing-data mechanism, weights/clusters) as the risky half, paired with the safe half: financial-statement ratio analysis (T1 arithmetic on the ledger artifacts).

---

## 2026-10-21 — Retrieval audit: response SHA-256 and UTC time per reference

**Ask:** "okay do 3 first" — the cheapest REW increment, Q10 in the living manual: make the hash-audit claim true.
**Did:** `CrossrefSource`/`OpenAlexSource` capture the raw response bytes and record `response_hash` (SHA-256 of those exact bytes) plus `retrieved_at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) on every resolved retrieval; the fields travel through `POST /api/literature/verify` and show in the workbench References panel. A reference that never reached a source (no DOI, 404, source error) carries neither, fail-closed. Clock is injectable for deterministic tests. Hash is byte-level on purpose: the same semantic record received with different whitespace hashes differently, so the audit pins what was served.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_api.py`, docs (REW manual v0.3, DECISIONS B-054, CHANGELOG 0.29, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, README).
**Decisions:** B-054 (PROVISIONAL); REW manual Q10 marked answered.
**Verified:** five new tests (byte-level pin vs parsed record, injected clock, audit survives a title mismatch, no audit without retrieval, OpenAlex parity) plus API/UI assertions; **400 tests OK**; live smoke against Crossref recorded a real sha256 for DOI `10.1038/nature12373`.
**Commit:** `3189816`.
**Open/next:** no durable retrieval log yet (documented); citation formatting is still `[OPEN]` Q9.

---

## 2026-10-21 — Owner ratifies R11: the REW living manual is the working authority

**Ask:** "yes to R11".
**Did:** ratified R11. The manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) is now the working authority for the Research & Evidence Workflow; B-035 (blocked on the missing Smart Researcher manuals) is closed and B-053 resolved. Manual to v0.2, stating explicitly that R11 ratifies the **document**, not its proposals — R1–R10 (stage list, checkpoints, tiers, taxonomy, etc.) remain unratified.
**Files:** REW manual, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Decisions:** B-053 RESOLVED; B-035 SUPERSEDED.
**Verified:** docs only; no code changed.
**Commit:** `7d73b6d`.
**Open/next:** cheap code increment that makes the manual honest — the retrieval audit (Q10).

---

## 2026-10-21 — Living manual for the research workflow (REW), replacing "Stage 7"

**Ask:** the owner believed Stage 7 had already been built; asked "what are these: reviewers, next templates, ledger engine, Stage 7 manuals?" and "create a living stage 7 manual and probably, rename that appropriately".
**Did:** explained the four owner asks (B-005 reviewers, B-028 next templates, B-032 ledger engine, B-035 missing research-pipeline manuals) and corrected the record: what existed was the Stage 7 **blocker** document plus the literature retrieval/verification boundary, not the workflow definition. Created `docs/RESEARCH_EVIDENCE_WORKFLOW.md` as a living manual, renamed the capability **Research & Evidence Workflow (REW)** — "Stage 7" was a build-order label, not a product name. Merged and removed `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md`; updated every reference. The manual refuses to pretend it is the lost Smart Researcher manual: every section is tagged `[OWNER]`, `[REPO]`, `[2ND]`, `[PROPOSAL]` (R1–R11) or `[OPEN]` (Q1–Q12), with stages R0–R8 proposed, three mandatory checkpoints, feasibility tiers, study taxonomy, retrieval/citation rules, claim rules, synthetic-data and AI-use policy, an honest inventory, and a ratification register.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (new), two Stage 7 docs (removed), `README.md`, `docs/DECISIONS.md` (B-035 superseded, B-040 pointer, B-053), `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`, `src/bp/literature.py` docstring.
**Decisions:** B-053 created; B-035 superseded.
**Verified:** docs only; **395 tests OK**.
**Commit:** `896372e`.
**Open/next:** owner ratification of the register (R11 asked first).

---

## 2026-10-21 — Product gap map

**Ask:** "what else in business have we overlooked?" (after the taxation discussion).
**Did:** wrote `docs/PRODUCT_GAP_MAP.md`: what the catalogue/manual call for versus what is built, ordered P0 gatekeepers (retrieval+citation, ingestion, decision dependencies), P1 statistics completion and finance/valuation, P2 catalogue breadth, plus the non-computational gaps in manual §15B/§16; with tier/verification notes and a recommended order.
**Files:** `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Verified:** docs only; cross-checked against `DECISIONS.md` and module inventory.
**Commit:** `8c71814`.
**Open/next:** decide which gap to close first (the recommended order was discussed, not started).

---

## 2026-10-21 — Taxation recorded as deferred

**Ask:** "does the jobs you did in creating the pipeline include taxation?" â†’ no; "put it in your memory".
**Did:** recorded **B-052 DEFERRED**: the manual makes tax a non-goal and a jurisdiction-specific area to keep out of the autonomous path or gate behind retrieved sources; resume conditions (VAT/GST, income tax in the accounts, after-tax appraisal, filing) and the evidence lines from the manual are in the decision.
**Files:** `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
**Decisions:** B-052.
**Verified:** read-only analysis against `docs/sources/business_pipeline_v0_3.md` and `src/bp/methods.py`.
**Commit:** `efa9404`.
**Open/next:** product gap map.

---

## Backfill — earlier increments (v0.13 … 0.25)

Earlier work predates this log. The full ordered record is `docs/CHANGELOG.md` (0.13–0.25) and the stage reports; do not duplicate it here. In short: deterministic pipeline + spec/freeze (Stage 0–4), method library and golden fixtures (Stage 5), catalogue registry and T4 templates (Stage 6), model-provider boundary with evaluation scaffold (B-031/B-036/B-038/B-039), literature retrieval boundary (B-040), statistics increments (B-042), forecasting (B-043), and the Stage 8 accounting chain — schedules, two-route cash flow, closing/rollforward, declarative engagement, reconciliation, account-mapping checkpoint, policy changes, statement exports (B-044–B-051). The first commit in this repository is `1ab1d05`; the last pre-worklog increment is `efa9404`.

## 2026-10-30 — [product] Home chat serves every subject

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

