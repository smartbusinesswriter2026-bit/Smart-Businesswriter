# Agent instructions

Before working on the business writer chat, read:

- `business_pipeline_v0.12/business_pipeline/docs/CONDUCTOR_MANUAL.md` — the goal, paper model, framework/computation rules and extension checklist.
- `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md` — current build, tests and open work.
- `corpus-db/CORPUS_DB.md` — living design record for the proprietary PDF evidence corpus
  (R2 bytes + SQLite/Meilisearch index). Read before any corpus, retrieval or citation-format
  work; it carries the binding constraints, open questions and build sequence.
- `DATABASE.md` — **the step-by-step build manual for the corpus database** (Word copy:
  `DATABASE.docx`, rebuilt by `business_pipeline_v0.12/business_pipeline/scripts/build_manual_docx.py`
  through `corpus-db/build/build_corpus_docx.py`). If the request is
  "build the corpus", "build the database", "add the PDF library", "set up Meilisearch",
  "ingest books", or any corpus-database work: read this first and execute it in order. It has
  the working schema, the ingest script, the Meilisearch settings, the adapter code and the
  five traps that silently discard corpus results. `CORPUS_DB.md` is the *why*; `DATABASE.md`
  is the *how*.
- `corpus-db/WALKTHROUGH.md` — **the owner-facing walkthrough for that build** (Word copy:
  `corpus-db/WALKTHROUGH.docx`). Read it when the request is "explain how to build this",
  "walk me through the corpus", or when you need the shape of the build without the code:
  what you are building, the three ways the corpus fills itself, the build in order with
  "you do / you see / it means", what it costs, and what it cannot do. It points at
  `DATABASE.md` for the exact commands and at `CORPUS_DB.md` for the reasoning.

The chat is the macro conductor: it owns the decision, thesis, framework stack,
computation blocks and paper plan. Subject modules provide frameworks and
computations; the writer and DOCX renderer only format. Do not add a framework
by editing the sample builder or renderer.

Non-negotiables:

- no invented evidence, sources, numbers or citations;
- gaps are named, never filled;
- student inputs stay student inputs;
- no silent framework substitution;
- computations come from the frozen core;
- a paper never contains template instructions;
- export is blocked when the paper is incomplete;
- the product is global: no PSE/PSEi name, no Philippine place name and no Philippine-specific
  example, currency or market claim. A global product never names a home exchange or a home
  country; examples use neutral places and USD (decision B-177).
