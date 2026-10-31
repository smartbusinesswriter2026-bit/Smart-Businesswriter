# The corpus walkthrough — how to build a library that fills itself

## 0. What you are building, in one page

You are building a **private library of books and papers, held one page at a time, that gets
fuller every time somebody uses the product.**

Today the product finds evidence by asking live academic APIs (OpenAlex, Semantic Scholar, DOAJ)
and a curated web tier. That works, and it is slow, and most of what those APIs hold is never
needed. A corpus inverts the economics: the API's full text is pulled **once**, into a page you
own and can quote with a page number, and every later question is answered from your own shelf
instead of from someone else's server.

The important word is **fills itself**. A library you have to feed by hand stops growing the
moment you stop. This one has three paths into it, and all three are built:

1. **What the product searched for.** Every retrieval is written down: the question, the subject,
   how many hits the corpus gave, and which sources were seen anyway. A question the corpus could
   not answer becomes a **candidate** — a request for full text.
2. **What you upload.** A page where you drop a PDF. It is ingested and searchable in seconds,
   with your own metadata, and it never waits for approval.
3. **What the system researches.** The worker takes the unanswered questions, searches the
   open-access literature, checks the licence, and ingests what is genuinely open. What is
   ambiguous waits for you.

Everything the corpus proposes, **you dispose**. The system may only add a document on its own
when the licence needs no decision from anyone (CC0, CC BY, CC BY-SA, public domain). Everything
else lands in a queue with a reason attached.

This walkthrough is the *narrative*. The exact commands, the schema, the adapter code and the
five traps live in `DATABASE.md` (Word copy: `DATABASE.docx`), and the reasoning behind every
decision lives in `CORPUS_DB.md`. Read this first, then `DATABASE.md`, then build.

## 1. What already exists, so you do not rebuild it

The build is further along than it looks. These are written, tested and working today:

| Piece | What it is | Where |
|---|---|---|
| The schema | Eight tables: three hold the corpus, five hold the learning loop | `corpus-db/build/schema.sql` |
| The shared library | Schema, page extraction, ingest, indexing, the learning loop | `corpus-db/build/corpus_lib.py` |
| The ingest tool | One PDF into the corpus, with a hash and an audit row | `corpus-db/build/ingest.py` |
| The worker | The four-step enrichment loop: collect, score, research, fetch | `corpus-db/build/enrich.py` |
| The admin service | The local API behind the page | `corpus-db/build/corpus_service.py` |
| The admin page | Your cockpit: upload, queue, gaps, searches | `corpus-db/build/admin.html` |
| The search settings | How the index is configured | `corpus-db/build/meili_settings.json` |
| The regression tests | 15 tests over the build tools, including the five defects that used to silently discard results | `corpus-db/build/test_corpus_build.py` |

The one thing that is **not** built is the last mile: the corpus is not yet wired into the
paper pipeline, and that work is Step 8 of `DATABASE.md`. Until it is, the corpus is a shelf
you can fill and search, not something a paper draws on.

## 2. The three paths, and how they close the loop

```
        the product searches
                 │
                 ▼
      ┌──────────────────────┐
      │   search_log         │  what was asked, and did the corpus answer it?
      │   seen_sources       │  what the API and the web returned anyway
      └──────────┬───────────┘
                 │  a question the corpus could not answer
                 ▼
      ┌──────────────────────┐
      │   candidates         │  the demand queue: what to pull full text for
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │   research           │  find that document in the open literature
      │   fetch              │  download it, check its licence, ingest it
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │   documents + pages  │  the corpus grows, by page, with a hash
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │   Meilisearch index  │  the corpus answers more of the next search
      └──────────────────────┘
```

**Path 1 — the searches become part of the database.** This is the path that makes the system
self-aware. Every retrieval is recorded with the query, the subject, the dimension, the case,
how many hits the corpus gave and how many the live APIs gave. The sources that were seen are
recorded too, **used or not**. When the corpus answers badly on a subject, the subject is marked
**thin**, and thin subjects push their candidates up the queue.

**Path 1 also covers the websites.** The web tier's output is not thrown away: every URL the
tier saw is recorded in `web_sources`, with a running count of how often it was seen and a
snapshot of what was retrieved. The web tier is not the corpus — the corpus is books and papers
— but the record stops the same site being fetched and re-read for every student, and it gives
you a running map of what the product is actually reading.

**Path 2 — you upload.** Your own books and the papers you care about go in through the admin
page with your own metadata. They are ingested and indexed immediately. Nothing waits.

**Path 3 — the system researches the API databases.** A repeated unanswered question becomes a
candidate. The worker searches OpenAlex's open-access content for it, downloads the full text
where the licence permits, and ingests it. This is where the API's value is kept rather than
thrown away: the live APIs stay in the pipeline as the second layer, and the corpus *harvests*
them — the full text they already hold is pulled once into a quotable page, instead of being
re-fetched as an abstract on every run.

## 3. Before you start: three things to install, four answers to lock

**Three things you need:**

- **Python 3.11+** with `pypdf`. Add `pypdfium2` and `pytesseract` plus a local Tesseract if any
  of your books are scans — without them a scanned page is ingested with empty text and the
  corpus quietly cannot see it.
- **Docker**, for Meilisearch. Nothing leaves your machine during the build.
- **A private object store** (Cloudflare R2) for the off-site copy of the PDFs, once the corpus
  is live. The bucket is private and never gets an `r2.dev` subdomain; that subdomain is a public
  URL and would expose copyrighted text.

**Four answers to lock before writing any code.** Each has a recommended answer in
`CORPUS_DB.md`; take the recommendation unless you have a reason not to, and record the reason
there.

| # | Question | Recommended answer |
|---|---|---|
| Q-02 | What identifies a corpus item, so one source cannot fill two dimensions? | Identity = `doc_id + pdf_page`. Citation identity = `doc_id + section_path`. |
| Q-03 | What weight does a corpus result carry? | **2** — the same as OpenAlex, DOAJ and Crossref. Not 3, which is for official statistics. |
| Q-16 | Can one book fill every dimension of a paper? | **No — cap it at 2–3 pages per document per paper.** |
| — | Is the student-upload path in v1? | Decide now. If yes, three extra columns are needed (`added_by`, `enrichen_at`, `owner_approved_at`). If v2, say so and ignore them. |

**One rule that governs everything:** the owner decides what enters the corpus. The system
proposes; the owner disposes. Every automatic path is bounded by the licence gate, and the gate
is not to be relaxed to make a queue drain faster.

## 4. The build, in order

Each step below gives you **what you do**, **what you should see**, and **what it means**. The
full command, with every argument spelled out, is in `DATABASE.md`.

### Step A — Start the search engine

*You do:* run Meilisearch in Docker, with its data directory inside `corpus-db\meili\`.

*You see:* `{"status":"available"}` from `http://127.0.0.1:7700/health`.

*It means:* the index is up and local. If the port is ever reachable from anywhere but your
machine, set a master key and treat it as a secret. An open index on a public VPS exposes
copyrighted text.

### Step B — Create the database

*You do:* `python corpus-db\build\corpus_lib.py --init`

*You see:* `schema applied:` and a `corpus.sqlite` with eight tables.

*It means:* the shelf and the learning loop both exist. **Eight tables, not three.** The first
three hold the corpus; the other five are what make it self-enriching. A build with only the
first three produces a library you must feed by hand forever.

*Always open the database through `corpus_lib.connect()`*, which turns `PRAGMA foreign_keys = ON`
for you. SQLite ignores `REFERENCES` otherwise, and a page can then outlive its document without
complaint.

### Step C — Ingest one PDF

*You do:* `python corpus-db\build\ingest.py <file.pdf> --title ... --authors ... --subject ... --kind ...`

*You see:* `ingested  bk-<hash>  212 pages, method=pdf_text_layer`, then `indexed 212 pages`.

*It means:* one row per **PDF page**, not one row per book. That is the whole design: the unit
you can quote is the page. Do it twice — once on a born-digital PDF and once on a **scanned
book**. The easy case proves the extractor; the scanned book proves the page model.

*Done when:* the page count matches the PDF, the first pages show real text, the stored hash
matches `Get-FileHash` of the file, and the ingest log shows `ok` or `ocr` — never silence.

*If you already have the file:* the shelf refuses it. The corpus holds **one document per work**,
so a file whose bytes are already there is refused by its `sha256`, and another copy of a book or
paper already in the shelf is refused by the work itself — its DOI, or its title, first author and
year. The refusal happens before anything is written: no second document, no second copy of the
file on disk, and one line in the ingest log naming what it repeats. Ingest the same file twice
and you get the same document back, not two of them.

*One repair worth knowing:* if a document is in the shelf but its PDF has been lost from disk, and
that exact file arrives again, the shelf **puts the file back** instead of refusing it. The
document row stays the one document it always was.

### Step D — Load the pages into the index

*You do:* run `corpus_lib.index_pages()`. It runs automatically after each ingest; run it by hand
after a bulk load.

*You see:* `212 pages indexed`.

*It means:* the pages are now findable. Note the order of operations inside: **settings first,
then documents**, because changing the searchable attributes, stop words, synonyms or typo
tolerance triggers a full reindex of every document.

*Done when:* searching for a phrase you know is on a particular page returns that page first,
with the right `pdf_page`.

### Step E — Turn on the learning loop

*You do:* `python corpus-db\build\enrich.py run` (or the four steps one at a time: `collect`,
`score`, `research`, `fetch`).

*You see:* a line per step — `collect 184 sources seen, 96 candidates touched`, `score 96
candidates ranked`, `research 12 new candidates from the open literature`, `fetch {'ingested': 3,
'duplicate': 1, 'needs_decision': 2, 'rejected': 4, 'failed': 0}`.

*It means:* the loop is alive. `collect` never fetches anything. `score` ranks by need, not by
fame. `research` only finds. **`fetch` is the step that downloads, and the licence decides what
happens:**

- An open licence (CC0, CC BY, CC BY-SA, public domain) is **ingested**.
- A restrictive licence (NC, ND, NC-SA) becomes **`needs_decision`** and waits for you.
- No licence known becomes **`rejected`**, with the reason recorded.

*A run that reports only `rejected` with the reason "no open full text at the API content
endpoint" is a correct result, not a failure.* It means the literature for that question is not
open. Nothing is ever guessed.

*Note:* `research` and `fetch` call OpenAlex. `BP_OPENALEX_API_KEY` and `BP_OPENALEX_EMAIL` make
the requests faster and less likely to be rate-limited. Neither is required.

### Step F — Open your cockpit

*You do:* `python corpus-db\build\corpus_service.py --port 7710`, then open
http://127.0.0.1:7710/.

*You see:* the page, with the corpus statistics across the top.

*It means:* you can now work without touching the command line. The page gives you:

- **Upload a document** — drop a PDF, fill in what you know, and it is ingested and indexed
  immediately. A duplicate upload is refused by SHA-256 with the existing `doc_id` named, so
  nothing is ingested twice.
- **The enrichment queue** — candidates ranked by how often they were asked for and how thin
  their subject is, each with **Approve** and **Reject**. Approve fetches the full text; Reject
  records the reason and closes it.
- **What the product asked for** — recent searches with the query, the subject, and whether the
  corpus answered it.
- **Gaps** — the questions the corpus could not answer, counted.
- **Uploads** — every file you have uploaded, with its status.

**This is an owner tool.** It binds to localhost only and has no login, because it exposes upload
and enrichment. If it ever has to run off this machine, put it behind an authenticating proxy
first.

### Step G — Let the product write the learning log

*You do:* wire the retrieval path to post every search to `/api/corpus/log`.

*You see:* the Searches panel filling up with real queries.

*It means:* Path 1 is live. Without this the corpus cannot know what it is missing, and the
enrichment queue is guesswork. This is the one write path the product uses, and it is
deliberately **fail-soft**: a learning-log failure must never break a paper run.

### Step H — Wire the corpus into retrieval

*You do:* the adapter work in Step 8 of `DATABASE.md`.

*You see:* a corpus result appearing in the evidence list, quoted with its page number.

*It means:* the shelf is now part of the product. **Do not skip this step's traps.** Five places
in the existing retrieval contract silently discard corpus results — none of them raises an
error, so the corpus simply looks broken and it is not the corpus's fault. `DATABASE.md` Step 8
names all five, where they are, and how to fix each. Read it before you wire anything.

## 5. How it plugs into the paper

The evidence order becomes three layers, and no layer replaces another:

1. **Your corpus** — owned, page-exact, instant. Searched first.
2. **The live academic APIs** — OpenAlex, Semantic Scholar, DOAJ; Crossref for metadata. They
   still answer what the corpus does not, and the pipeline still works with no corpus at all.
3. **The curated web** — what neither of the first two can supply.

Two rules make the corpus safe to quote:

- **A full-text source is judged on the passage it will quote**, not on its title. A book page
  carries the evidence, so the cue must appear in the passage.
- **A corpus result carries weight 2**, the same as the live APIs, and one document may fill
  at most 2–3 pages of a paper.

## 6. What it costs

The cost model in `CORPUS_DB.md` §10 is the honest version. In short:

- **Storage.** The PDFs are the expensive part, and they grow as you harvest. The ceiling is
  **10 GB measured in bytes**, not in page count.
- **Search.** Meilisearch on a small VPS is cheap. The corpus is fast because it is small and
  local, which is the whole point.
- **Harvesting.** The open-access literature is free to search. The download step is bounded by
  the licence gate, so the cost is bandwidth and disk, not licence fees.
- **Your time.** The queue exists so that your time goes to the decisions that need a human:
  the licences that constrain use, and the documents you want.

## 7. What it cannot do

Honesty here is part of the design, because a corpus that looks more capable than it is will be
trusted when it should not be.

- **It does not make a paper cite a source the reader can check**, unless the page number is
  real. Every page row carries the PDF page it came from; the printed page number is recorded
  as `NULL` until something establishes it.
- **It does not read a scanned book without OCR.** Without Tesseract installed, those pages are
  ingested with empty text — visible in the `text_method` column, but silent in search.
- **It does not guess a licence.** Unknown means `rejected` with a reason, never "probably fine".
- **It does not replace the live APIs.** The pipeline is designed to work with the corpus absent.
- **It does not decide what is true.** It stores what you gave it and what it fetched under a
  licence that permits it. The reading, the argument and the claim are still the paper's job.
- **It does not know that two editions are one book.** The shelf refuses the same file twice, and
  refuses another copy of a work it already holds — but a reissue in a **later year** is a
  different work key, so it becomes a second document. That is the open re-ingest policy (Q-15),
  and it is a decision for you rather than a guess for the code.

## 8. How you know it is working

Four checks, in increasing depth:

| Check | Command | What a good answer looks like |
|---|---|---|
| The corpus exists | `python corpus-db\build\corpus_lib.py --status` | A document count above zero, a page count, and `meili: true` |
| The tools are sound | `python corpus-db\build\test_corpus_build.py` | 15 tests, all passing |
| The loop is turning | `python corpus-db\build\enrich.py status` | A non-zero candidate count, and a hit rate that rises as the corpus fills |
| The shelf answers | Search Meilisearch for a phrase you know is on a specific page | That page first, with the right `pdf_page` |

The regression tests are worth running after every change to the build tools. They pin the five
defects that used to discard corpus results without complaining, and the two rules that keep the
corpus honest: a document's pages are never shared under one key, and a page never outlives its
document.

## 9. What is still open

Named, not hidden. These are recorded in `CORPUS_DB.md` with their owners and resume conditions.

- **Q-15 — the re-ingest policy.** A PDF that is already in the corpus is refused rather than
  ingested again. What happens when a document is *replaced* by a corrected edition is not
  decided.
- **Q-19 — the copyright check for student uploads.** If student uploads are in v1, this decides
  what may be promoted to a citable document.
- **D-18 — private student uploads an owner can promote.** The design is lost; only a summary
  survives.
- **The printed page number.** `printed_page` is `NULL` in v1. Until something establishes it,
  a citation points at the PDF page and says so.
- **The corpus layer is not yet in the product.** Step H is the last mile and it is not done.
- **The off-site copy.** R2 holds the bytes, but the private-bucket wiring and the custom domain
  are not in place.

## 10. Where the truth lives

| File | What it is |
|---|---|
| `DATABASE.md` (Word: `DATABASE.docx`) | The step-by-step build manual: the exact commands, the schema, the adapter code, the five traps |
| `corpus-db/CORPUS_DB.md` | The design record: the decisions, the gaps, the rejected options, the cost model, the change log |
| `corpus-db/WALKTHROUGH.md` (Word: `corpus-db/WALKTHROUGH.docx`) | This document |
| `corpus-db/build/` | The build tools and the regression tests |
| `corpus-db/build/admin.html` | Your cockpit |

If the two disagree, `CORPUS_DB.md` is the design authority and `DATABASE.md` is the how-to.
Fix the how-to.
