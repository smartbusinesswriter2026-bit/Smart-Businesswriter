# DATABASE.md — how to build the self-enriching corpus database

**This is the execution manual.** Read it before touching the corpus. It is written so that a
model or a person who has never seen this project can start at Step 0 and finish with a
working corpus that fills itself.

- **This file** = what to do, in order, with working code.
- `corpus-db/CORPUS_DB.md` = why it is designed this way (the design record: decisions, gaps,
  open questions, cost model). **Do not re-derive decisions from it — read them there.**
- `corpus-db/SEARCH_KEYWORDS_BY_SUBJECT.md` = the per-subject harvest queries.

If the two disagree, `CORPUS_DB.md` is the design authority and this file is the how-to. Fix
this file.

## 0. What you are building, in plain language

Right now the pipeline finds evidence by asking live academic APIs (OpenAlex, Semantic Scholar,
DOAJ) for **abstracts**. An abstract cannot be quoted with a page number. It is also slow, and
most of what those APIs hold is never needed by anyone.

You are building a **private library** that **fills itself**:

| Piece | What it is | Where it runs |
|---|---|---|
| **The bytes** | The PDF files themselves | Cloudflare R2 (off-site copy) + a working copy on the VPS |
| **The record** | A SQLite database: one row per document, one row per **page** | The VPS. **This is the truth.** |
| **The search index** | Meilisearch: one record per page, for fast search | The VPS. **Disposable — rebuild it from SQLite any time.** |
| **The learning log** | What the pipeline asked for, what it was given, what was missing | The same SQLite database. **This is what makes the corpus self-enriching.** |

**The unit is one PDF page.** Not a chapter, not a chunk of text. A page is the smallest thing
you can point at and say "it is on page 143".

**The corpus is not a mirror of the API.** The API is extensive, slow, and mostly unnecessary.
A corpus that copies the API is expensive, slow to update, and still misses what a particular
brief needs. So the corpus keeps a **demand queue** instead: a document enters the corpus
because someone kept searching for something the corpus could not answer, and it rises in
priority the more often that comes up. The corpus grows to cover what is actually asked for.

**The order of the work matters more than anything else in this document.** If you build the
database first and wire it into the pipeline later, the pipeline will **silently throw your
corpus away** and you will conclude the corpus is bad. That exact mistake is called out in
Step 8. Do not skip it.

## 1. The rules that cannot be broken

These come from the project's non-negotiables. Breaking one is worse than shipping nothing.

1. **No invented evidence.** Every quote traces to a recorded page.
2. **Gaps are named, never filled.** A printed page number you cannot read is `NULL`, not a
   guess. A missing edition is `NULL`. A missing ISBN is `NULL`. Never infer one.
3. **Computations come from the frozen core.** The corpus never touches `src/bp/**` core
   modules. Only the product layer (`src/bp/product/**`) changes.
4. **Stdlib only at runtime.** The pipeline may only use `sqlite3` and `urllib` from the
   standard library. No psycopg2, no elasticsearch client, no Meilisearch SDK. Meilisearch's REST
   API satisfies this. (Build-time tools like `ingest.py` **may** use `pypdf` — they are not the
   runtime.)
5. **The corpus supplements the live sources; it never replaces them.** Layer 1 corpus, layer 2
   live academic APIs, layer 3 curated web. All three must still work. The corpus grows to
   **answer first**; it does not delete the other layers.
6. **The corpus stays private.** The R2 bucket is private. Never use an `r2.dev` subdomain — it
   is a public URL. Use a custom domain with Cloudflare Access, or presigned URLs.
7. **Any change inside the pipeline repo** needs tests + CHANGELOG + WORKLOG + a B-numbered
   `docs/DECISIONS.md` entry. (This manual lives outside the pipeline repo, so it does not.)
8. **Never invent a number.** If the cost, the count, the licence or the date is not known, it
   is `NULL` and the gap is named.
9. **The owner decides what enters the corpus.** An automatic pass may ingest only a licence
   that needs no decision. Everything else waits in the admin queue for the owner to approve or
   reject. The system proposes; the owner disposes.
10. **The corpus never holds the same thing twice.** One document per work. A file that repeats
    something already in the corpus — the same bytes, or another copy of a book or paper already
    there — is refused before anything is written, and the refusal is recorded with its reason.
    It is never ingested twice, and it never becomes a second document.

## 2. Where things live

```
D:\SMART BUSINESSWRITER\
├── DATABASE.md                        ← this manual
├── corpus-db\
│   ├── CORPUS_DB.md                   ← the design record (the "why")
│   ├── SEARCH_KEYWORDS_BY_SUBJECT.md  ← harvest queries per subject
│   ├── corpus.sqlite                  ← THE DATABASE (created in Step 2)
│   ├── pdfs\                          ← working copies of the PDFs
│   ├── meili\                         ← Meilisearch data directory
│   └── build\
│       ├── schema.sql                 ← Step 2  (8 tables: 3 corpus + 5 learning)
│       ├── corpus_lib.py              ← shared library (schema, ingest, index, learning loop)
│       ├── ingest.py                  ← Step 3  (one PDF → corpus)
│       ├── enrich.py                  ← Step 6  (the self-enriching worker)
│       ├── corpus_service.py          ← Step 7  (the admin API)
│       ├── admin.html                 ← Step 7  (the owner upload UI)
│       ├── meili_settings.json        ← Step 4
│       └── test_corpus_build.py       ← the regression tests for the build tools
└── business_pipeline_v0.12\business_pipeline\
    └── src\bp\product\
        ├── sources.py                 ← the adapter goes here (Step 8)
        └── retrieval.py               ← the contract fixes and the learning hook go here (Step 8)
```

**Eight tables, not three.** The first three hold the corpus. The other five are the learning
loop, and they are what make the corpus self-enriching. A build that creates only the first
three produces a library that has to be fed by hand forever.

| Table | Holds | Consequence if it is missing |
|---|---|---|
| `documents` | one row per book or article — the CITATION unit | nothing can be cited |
| `pages` | one row per PDF page — the RETRIEVAL and QUOTE unit | nothing can be quoted |
| `ingest_log` | an audit of every ingest, for replay and drift | a corrupt file is undetectable |
| `search_log` | every retrieval, and how the corpus answered it | **the corpus cannot learn what it is missing** |
| `seen_sources` | every source a search saw, used or not | a source that keeps recurring never becomes a candidate |
| `candidates` | the enrichment queue: what to pull full text for, and why | the queue must be built by hand |
| `uploads` | files the owner uploaded through the admin UI | an upload is not auditable |
| `web_sources` | the rolling record of what the web tier saw | the same site is fetched and re-read for every student |

## 3. The three enrichment paths, and how they close the loop

This is the heart of the design. Three paths feed the corpus, and all three are already
supported by the schema and the build tools.

```
        the pipeline searches
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

**Path 1 — the pipeline writes the learning log.** Every retrieval is recorded: the query, the
subject, the dimension, the case, how many hits the corpus gave and how many the live APIs
gave. The sources that were seen are recorded too, whether or not the paper used them. This is
the only path that tells the corpus what it is missing. It is wired in Step 8.

**Path 2 — the owner uploads a file.** The admin page takes a PDF, ingests it immediately, and
indexes it. The owner's own books and the papers they care about go in here, with the owner's
own metadata, and they never wait for an approval cycle. Wired in Step 7.

**Path 3 — the system researches the API databases and fetches what is open.** A repeated
unanswered question becomes a candidate; the worker searches the open-access literature for it,
downloads the full text where the licence permits, and ingests it. Anything with a licence
that constrains use waits for the owner. Wired in Step 6.

**Path 3 is where the API's value is kept.** The live APIs stay in the pipeline as layer 2 —
they still answer what the corpus does not, and the pipeline still works without the corpus.
But the corpus **harvests** them: the full text they already hold is pulled once, into a page
that can be quoted, instead of being re-fetched as an abstract on every run.

## 4. Step 0 — Lock the answers (15 minutes, no code)

Write these down before you start. Each has a recommended answer in the design record; take the
recommendation unless you have a reason not to, and record the reason in `CORPUS_DB.md` §13.

| # | Question | Recommended answer | Why it matters |
|---|---|---|---|
| **Q-02** | What identifies a corpus item so that "one source cannot fill two dimensions" works? | Identity = `doc_id + pdf_page`. Citation identity = `doc_id + section_path`. | If every page of a book shares one key, all but one page disappears. |
| **Q-03** | What weight does a corpus result carry? | **2** — the same as OpenAlex / DOAJ / Crossref. Not 3 (that is for official statistics). | At weight 1 the corpus loses every near-tie and looks broken. |
| **Q-16** | Can one book fill every dimension of a paper? | **No — cap it at 2–3 pages per document per paper.** | Without the cap a single textbook quietly supplies the whole paper. |

**Also decide now: is the student-upload path in v1?**
The design record's **D-18** (private student uploads that an owner can promote to citable) and
**Q-19** (what copyright check applies) were lost when an earlier revision of `CORPUS_DB.md` was
destroyed — only one-line summaries survive. If student uploads are in v1 you also need three
columns that are **not** in the schema below: `added_by`, `enrichen_at`, `owner_approved_at`.
If uploads are v2, say so and ignore them for now.

## 5. Step 1 — Get Meilisearch running locally

Docker, on your machine. Nothing leaves the machine yet.

```powershell
docker run -d --name corpus-meili -p 7700:7700 `
  -v "D:\SMART BUSINESSWRITER\corpus-db\meili:/meili_data" `
  getmeili/meilisearch:v1.12
```

Check it:

```powershell
Invoke-RestMethod http://127.0.0.1:7700/health
```

**Done when:** it returns `{"status":"available"}`.

**Note:** set a master key if the port is reachable from anywhere but your machine
(`docker run -e MEILI_MASTER_KEY=...`). Treat the key as a secret. An open index on a public VPS
exposes copyrighted text.

## 6. Step 2 — Create the database

`corpus-db/build/schema.sql` already exists and holds all eight tables. It is applied with one
command, and it is safe to run repeatedly:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\corpus_lib.py --init
```

**Done when:** `corpus.sqlite` exists and has eight tables.

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite'); print(sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")))"
```

**Always open the database with** `PRAGMA foreign_keys = ON`. SQLite ignores `REFERENCES`
otherwise, and a page can then outlive its document without complaint. `corpus_lib.connect()`
does this for you — always use it rather than calling `sqlite3.connect` directly.

## 7. Step 3 — Ingest one PDF

**Important discovery, already verified in the code:** `bp/product/documents.py` `extract_pdf()`
returns the **whole document as one string**. The corpus needs **one row per page**. So
`corpus_lib.extract_pages()` does its own per-page extraction. It reuses the same idea as
`documents.py` (pypdf for the text layer, pdfium + Tesseract for scans) but keeps the pages
apart.

The tool exists. Run it on one real document — a born-digital one to start:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\ingest.py "D:\SMART BUSINESSWRITER\DATABASE\A.-Bonini_2024_the-relationship-between-leadership-and-adaptive-performance-a-systematic-review.pdf" `
  --title "The relationship between leadership and adaptive performance: a systematic review" `
  --authors "Bonini" --year 2024 --subject people --kind journal-article
```

The metadata above is what the **file name** tells you. The four values the tool insists on —
`--title`, `--authors`, `--subject` and `--kind` — come from your own catalogue; everything else
is optional, and a value you do not know is recorded as `NULL`, never invented.

Then **also run it on a scanned book** — the hard case. The design record insists on this before
bulk work (Q-14): the easy case proves the extractor, the scanned book proves the page model.

**Done when:**
- `SELECT count(*) FROM pages;` returns the page count of the PDF.
- `SELECT pdf_page, chars, text_method FROM pages LIMIT 5;` shows real text.
- `SELECT sha256 FROM documents;` matches `Get-FileHash` of the PDF.
- `SELECT * FROM ingest_log;` shows the ingest as `ok` or `ocr`, never a silent failure.

### The corpus never takes the same thing twice

The corpus holds **one document per work**. Before anything is written, an ingest asks two
questions:

| Question | The key that answers it | What it catches |
|---|---|---|
| Is this the same file? | the `sha256` of the bytes | the same PDF, twice |
| Is this the same work? | the DOI, or the title + the first author's family name + the year | another copy of a book or paper already in the corpus |

A "yes" to either one is a **refusal**, and the refusal happens before anything is written:

- no second row in `documents`, and no second set of rows in `pages`;
- no second copy of the file in `corpus-db\pdfs\`;
- one row in `ingest_log` with `status = 'skipped'` and the reason, recorded **once** however
  many times the file arrives;
- one row in `uploads`, naming the `doc_id` of the document it repeats.

The database enforces this too, not only the code: `UNIQUE` on `documents.sha256`,
`documents.work_key` and `candidates.work_key`, in `corpus-db/build/schema.sql`. Two uploads that
arrive at the same moment cannot both get in.

**The one case that is not a refusal.** If the corpus already holds the work *and* that document's
own file has been lost, the same file arriving again **puts the file back** — one document, one
file, no second row. That is `restore_missing_file()`.

**What is still open.** This does not close Q-15 (the re-ingest policy). A work that comes back in
a **later year** — a reissue, a new edition — is still a separate document today, because the year
is part of the work key. If the owner wants a reissue to replace the old one, that is a decision to
make and record, not a guess to make in code.

To check what the corpus already holds before you ingest:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\corpus_lib.py --status
```

## 8. Step 4 — Meilisearch settings

`corpus-db/build/meili_settings.json` holds the settings (verbatim from `CORPUS_DB.md` §4.3):

```json
{
  "searchableAttributes": ["text", "section_path", "title", "authors"],
  "filterableAttributes": ["doc_id", "authors", "year", "publisher", "edition",
                            "venue", "subject", "source_kind", "pdf_page",
                            "printed_page", "text_method"],
  "sortableAttributes": ["year", "title", "authors"],
  "typoTolerance": {
    "enabled": true,
    "disableOnNumbers": true
  },
  "pagination": { "maxTotalHits": 1000 }
}
```

**Three fields this payload once carried are gone, and one is version-dependent.** A settings
patch is refused **in full** when it meets a field the server does not know, so one wrong field
means the corpus never indexes at all — and the failure looks like a success, because the ingest
still reports its page count.

| Field | Status | Why |
|---|---|---|
| `disableOnNumbers` | **v1.15+ only** | Added in Meilisearch v1.15 (June 2025). A v1.12 server refuses the patch. `corpus_lib.apply_settings()` drops **that one field** on an older server and prints that the protection is off. |
| `maxQueryTerms` | **removed** | Not an index setting in any current Meilisearch. Exact-quote verification uses a phrase query. |
| `primaryKey` | **not a setting** | The primary key belongs to the index. It is set when the index is created, never patched. |

Two things to understand, because they look like mistakes and are not:

- `text` **comes first on purpose.** The book's title repeats on every page. If `title` led,
  Meilisearch would reward a book whose **title** matches over the page whose **passage** matches —
  backwards for a page-exact evidence index.
- `disableOnNumbers: true` **stops the year** `1974` matching `1971`, and stops an ISBN's digits
  transposing. That is citation integrity, not a preference. **On a server older than v1.15 it
  cannot be set**, and the corpus says so in the build output rather than dropping it silently.

**Settings before documents.** Changing searchable/filterable/sortable attributes, stop words,
synonyms or typo tolerance triggers a **full reindex** of every document. Set them first.

## 9. Step 5 — Load the pages into Meilisearch

This is `corpus_lib.index_pages()`. It creates the index if it is not there, applies the settings,
then pushes the documents in batches of 500 and waits for each batch to land. It is called
automatically by `ingest.py` and by the admin service; run it by hand after a bulk ingest:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\corpus_lib.py --index
```

`--index` **empties the index first**, so the index holds exactly the pages the database holds
and cannot return a page the corpus no longer has. That is the "no duplicates" rule applied to
the search side as well as the database side.

A **document identifier** may hold alphanumerics, a hyphen and an underscore, and nothing else —
so the page identifier is `<doc_id>-<pdf_page>` (`ja-612e409fc587-10`), not a colon. A refused
document means that page is silently missing from the index.

**Done when:** searching Meilisearch for a phrase you know is on a specific page returns that
page first, with the right `pdf_page`.

```powershell
$body = @{ q = "a phrase from the page"; limit = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:7700/indexes/pages/search `
  -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 4
```

## 10. Step 6 — The self-enriching worker

`corpus-db/build/enrich.py` is the worker. It has four steps and one status command:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py collect     # learning log → candidate queue
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py score       # rank the queue by need
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py research     # unanswered questions → candidates
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py fetch       # pull full text for the top candidates
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py run         # all four, in order
python D:\SMART BUSINESSWRITER\corpus-db\build\enrich.py status      # what the corpus looks like now
```

**What each step does, and the rule it obeys:**

| Step | Does | Rule |
|---|---|---|
| `collect` | Every source a recent search saw becomes a candidate. A source seen twice is one candidate with `seen_count = 2`, not two candidates. A source needs no DOI or URL: a title of at least 12 characters is enough to enter the queue, which is how a corpus hit or a web page becomes demand. The corpus's own pages and the orientation pages are skipped. | Never fetches anything. |
| `score` | Priority = `seen_count` × how badly the corpus needs that subject. A subject the corpus answers less than half the time is **thin**, and a thin subject multiplies its candidates' priority. | A hint about need, never a fact. |
| `research` | Searches the open-access literature for the questions the corpus could not answer, and adds what it finds to the queue. | **Finds only.** Nothing is downloaded yet. |
| `fetch` | Downloads the full text of the top candidates and ingests them. A title-only candidate is resolved through OpenAlex first; when no work matches, it is marked `needs_decision` with the reason, never given a guessed DOI. | **The licence decides.** An open licence (CC0, CC BY, CC BY-SA, public domain) is ingested directly. A restrictive licence (NC, ND, NC-SA) or **no recorded licence** becomes `needs_decision` and waits for the owner. Nothing is ever guessed. |

**The fetch step** is the one that makes the corpus self-enriching, and it is also the one
that can do damage if it is wrong — it downloads copyrighted work into a library the owner did
not license. The licence gate is the whole safety mechanism. It is not optional and it must not
be relaxed to make the queue drain faster.

**Note on the API key.** `research` and `fetch` call OpenAlex. Set
`BP_OPENALEX_API_KEY` and `BP_OPENALEX_EMAIL` if you have them — OpenAlex's polite pool is
faster and less likely to be rate-limited. Neither is required.

**Done when:** `enrich.py status` shows a non-zero `candidates` count, and `fetch` reports at
least one `ingested` or a named `needs_decision` / `rejected` with a reason. A run that reports
only `rejected` with the reason "no open full text at the API content endpoint" is a correct
result, not a failure — it means the literature for that question is not open.

**The one database.** Every build tool reads `BP_CORPUS_DB` and falls back to
`corpus-db/corpus.sqlite`. This machine's canonical database is
`corpus-state/corpus.sqlite` (set in the environment), and it holds the documents, the search
history and the candidate queue together. Two databases that each hold half the record are the
trap: the enrichment worker then learns from a history the pipeline never wrote. To move a
history into the canonical database without duplicating it:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\merge_learning_log.py OLD.sqlite NEW.sqlite
```

**Nightly operations.** The cycle is a batch file, not a scheduler dependency:

```powershell
D:\SMART BUSINESSWRITER\corpus-db\start_corpus_services.bat   # Meilisearch + admin service, only if down
D:\SMART BUSINESSWRITER\corpus-db\build\enrich_cycle.bat      # collect + score + research + fetch + index
D:\SMART BUSINESSWRITER\corpus-db\build\enrich_cycle.bat fast # collect + score only
```

`build/register_enrich_task.ps1` registers the optional daily 03:00 task. A stopped task or a
stopped machine does not break a paper run; the corpus simply learns more slowly.

**A gap that must be named.** OpenAlex's shared, keyless daily budget can be exhausted
(HTTP 429). When that happens the journal-API fallback and title resolution are unavailable and
the pipeline says so; set a free `BP_OPENALEX_API_KEY` to give the corpus its own budget.


## 11. Step 7 — The owner upload UI

Two files, already written: `corpus-db/build/corpus_service.py` (the API) and
`corpus-db/build/admin.html` (the page).

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\corpus_service.py --port 7710
```

Then open http://127.0.0.1:7710/.

**This is an owner tool.** It binds to localhost only and has no login: it exposes upload and
enrichment, which must never be reachable from the internet. If it ever needs to run off-box,
put it behind an authenticating proxy first.

What the page gives the owner:

- **Upload a document** — drop a PDF, fill in what you know (title, authors, year, kind,
  subject, publisher, edition, ISBN, DOI, licence), and it is ingested and indexed immediately.
  A duplicate is refused by SHA-256 **or** by the work it names (the DOI, or the title + first
  author + year), with the existing `doc_id` named, not ingested twice. The refusal happens
  before the file is written, so a repeat upload leaves no second copy on disk.
- **The enrichment queue** — candidates ranked by how often they were asked for and how thin
  their subject is, each with an **Approve** and a **Reject** button. Approve fetches the full
  text; Reject records the reason and closes it.
- **What the pipeline asked for** — the recent searches, with the query, the subject and
  whether the corpus answered it.
- **Gaps** — the questions the corpus could not answer, counted.
- **Uploads** — every file the owner has uploaded, with its status.

**The API surface**, if you want to script it:

| Route | Verb | Does |
|---|---|---|
| `/api/corpus/stats` | GET | the numbers the page shows |
| `/api/corpus/candidates?status=all` | GET | the queue; `status` may be `new`, `needs_decision`, `ingested`, `rejected` or `all`; `limit` caps the rows |
| `/api/corpus/candidates/approve` | POST | fetch the full text for one candidate |
| `/api/corpus/candidates/reject` | POST | close one candidate with a reason |
| `/api/corpus/upload` | POST | ingest one PDF (base64 in `data`) |
| `/api/corpus/uploads` | GET | the upload audit |
| `/api/corpus/searches?limit=50` | GET | the learning log |
| `/api/corpus/gaps` | GET | the thin subjects and the missed questions |
| `/api/corpus/enrich` | POST | run one enrichment pass |
| `/api/corpus/log` | POST | **the pipeline writes its learning log here** — the only write path the pipeline uses |

**Done when:** the page loads, the stats strip shows the document count, and an uploaded PDF
appears in the Uploads table with status `ingested`.

## 12. Step 8 — The five traps and the adapter (READ THIS BEFORE WIRING IT IN)

These are verified against the current code. Each one **silently discards** corpus results. None
of them raises an error. If you skip this section, the corpus will look broken and it will not
be your corpus's fault.

| # | Trap | Where | What happens | Fix |
|---|---|---|---|---|
| **1** | The title gate | `retrieval.py:406` `_accept()` | The gate wants a dimension cue in the **title**. A book's title describes the **book**, not the **page**. Every book result is dropped. | Add a source-kind branch: for a full-text source, one cue hit in the body (the quoted passage) is enough, and the title is never sufficient on its own. The abstract-only path stays exactly as it is. |
| **2** | The dedup key (twice!) | `retrieval.py:435` `key_of()` **and** `sources.py:496` | Both key on DOI-or-title. Every page of a book shares the title, so all pages collapse into one and only the first survives. **Two separate places** need fixing. | Give each corpus page a unique `corpus_key` (e.g. `corpus:bk-1a2b3c4d5e6f:143`) and make both sites prefer it. |
| **3** | The source weight | `retrieval.py:297` `_source_weight()` | Anything not in the known list scores **1**. The corpus loses every near-tie to a live result. | Corpus items score **2** (Q-03). |
| **4** | The credibility overwrite | `sources.py:498` `item["credibility"] = _credibility(item)` | The merged list is **sorted by credibility and truncated to the limit**. A corpus page with a low credibility is cut before the gate ever sees it. The adapter cannot fix this — the value is overwritten. | Give `_credibility()` a corpus branch (a corpus page has a stable identifier, so it earns the same points a DOI earns). |
| **5** | The merged limit | `sources.py:501` `merged[:limit]`, and `retrieve()` calls it with `academic_limit=4` | Only four academic items survive per query, chosen by credibility. | Fixing trap 4 fixes this. Alternatively call the corpus adapter **separately** in `retrieve()` and prepend its items, so the corpus is genuinely first (layer 1) instead of competing for four slots. |

**On trap 5, the recommended shape.** `search_academic()` queries every database at once and
merges by credibility, so "the corpus is searched first" cannot be expressed inside it. Instead,
in `retrieve()`:

```python
# corpus first (layer 1), then the live academic APIs (layer 2)
corpus_items = source_finder.search_academic(query, databases=["corpus"], limit=corpus_limit,
                                             year_from=year_from).get("results") or []
academic = source_finder.search_academic(query, databases=DATABASES, limit=academic_limit,
                                         year_from=year_from)
found.extend(corpus_items)      # corpus items go in first
found.extend(academic.get("results") or [])
```

and give the corpus its own limit (4 is a reasonable start) so it is not squeezed out.

### The adapter

Add to `src/bp/product/sources.py`. It reads Meilisearch over `urllib` (stdlib only — rule 4),
fails **open** if the corpus is down (a corpus outage is a notice, never a failed run), and
returns the exact `_item()` shape every consumer expects.

```python
CORPUS_MEILI_URL = os.environ.get("CORPUS_MEILI_URL", "http://127.0.0.1:7700").rstrip("/")
CORPUS_MEILI_KEY = os.environ.get("CORPUS_MEILI_KEY", "")
CORPUS_INDEX = os.environ.get("CORPUS_INDEX", "pages")


def _corpus(query, limit, year_from):
    """The proprietary corpus: page-exact evidence from the local index.

    Fails open. A corpus outage is a notice, never a failed run.
    """
    body = json.dumps({"q": query, "limit": limit}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if CORPUS_MEILI_KEY:
        headers["Authorization"] = "Bearer " + CORPUS_MEILI_KEY
    request = urllib.request.Request(
        "%s/indexes/%s/search" % (CORPUS_MEILI_URL, CORPUS_INDEX),
        data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=2.0) as response:
            hits = json.loads(response.read().decode("utf-8")).get("hits", [])
    except Exception:
        return []
    items = []
    for hit in hits:
        if year_from and (hit.get("year") or 0) < year_from:
            continue
        authors = [name.strip() for name in (hit.get("authors") or "").split(";") if name.strip()]
        item = _item(
            title=hit.get("title") or "",
            authors="; ".join(authors),
            authors_list=authors,
            year=hit.get("year"),
            abstract=hit.get("text") or "",       # the page text lives here
            doi=hit.get("doi"),
            url=hit.get("url"),
            venue=hit.get("venue") or "",
            database="Proprietary corpus",
            kind="proprietary",
            volume=hit.get("volume") or "",
            issue=hit.get("issue") or "",
            pages=hit.get("printed_page") or "",
            publisher=hit.get("publisher") or "",
            item_type="book" if hit.get("source_kind") == "book" else "journalArticle")
        # The unique page key. Both dedup sites must prefer it (traps 2).
        item["corpus_key"] = "corpus:%s:%d" % (hit.get("doc_id"), hit.get("pdf_page"))
        item["source_kind"] = hit.get("source_kind")
        item["pdf_page"] = hit.get("pdf_page")
        item["subject"] = hit.get("subject")
        items.append(item)
    return items
```

Register it in two places in `sources.py`:

```python
# DATABASES (around line 39)
{"id": "corpus", "label": "Proprietary corpus", "kind": "proprietary", "access": "local",
 "enabled": True},

# ADAPTERS (around line 364)
ADAPTERS = {"openalex": _openalex, "crossref": _crossref, "semanticscholar": _semanticscholar,
            "doaj": _doaj, "corpus": _corpus, ...}
```

And add `"corpus"` to `retrieval.py:24` `DATABASES` **if** you follow the "separate call"
shape in trap 5. If you fold the corpus into the single `search_academic()` call instead, do
**not** add it to `retrieval.py` `DATABASES` — that list is what the live call searches.

**Two things to know about** `_item()`:

- It truncates `abstract` to **1200 characters**. For a page that is longer, the pipeline sees
  the first 1200 characters. That is enough for the gate (which looks for cue words) but it means
  the quoted passage is the page's opening, not the whole page. If a quote needs more, raise the
  limit in `_item()` — that is a product-layer change with a test.
- It lowercases `doi` and turns a missing DOI into `None`. Do not put a synthetic value in
  `doi`; it would be rendered in the paper's reference list. Use `corpus_key`.

**Done when:** calling `source_finder.search_academic("your query", databases=["corpus"])`
returns page items.

### The learning hook — the part that makes it self-enriching

An adapter alone gives you a corpus. The **learning hook** gives you a corpus that fills itself.
Without it, `search_log` stays empty, `collect` finds nothing, and the corpus never grows on
its own.

`corpus_lib.record_search()` already exists and is fail-soft. It must be called from
`retrieve()` in `retrieval.py`, once per retrieval, with what the corpus returned and what the
live APIs returned:

```python
# in retrieve(), after the items are ranked
corpus_hits = sum(1 for item in items if item.get("corpus_key"))
live_hits = len(items) - corpus_hits
lib.record_search(
    connection,
    query=queries[0] if queries else "",
    subject=subject,          # the pipeline's subject id
    dimension=key,            # the dimension key
    case_id=case_id,
    corpus_hits=corpus_hits,
    live_hits=live_hits,
    sources=[...],            # every source seen, used or not
)
```

`corpus_lib` **is outside the pipeline repo**, so the pipeline must not import it directly. Write
the learning log through the admin service instead, over HTTP, with a short timeout and a
fail-soft path — the same shape as the corpus adapter:

- `POST /api/corpus/log` on the admin service takes the search record and writes it with
  `corpus_lib.record_search()`. It also records any `web_sources` in the payload through
  `corpus_lib.record_web_source()`.
- The pipeline calls it with a 1-second timeout and ignores any failure. A learning-log outage
  must never break a paper run.

**Record the sources that were seen, not only the ones used.** `seen_sources.used` says whether
the paper cited it; a source that keeps appearing and is never used is still a signal — it is a
document the corpus does not have. This is what makes `collect` work. Send the web tier's pages
in `web_sources` too, so the rolling record of what the web layer saw is complete.

**Done when:** one real paper run leaves a row in `search_log` with `corpus_hits` and
`live_hits`, rows in `seen_sources`, and rows in `web_sources`; `enrich.py collect` then produces
candidates from it.

## 13. Step 9 — Fix the contract, then run the live gate

Apply the trap fixes (Step 8), then run the real pipeline against a real brief and read the
`items` list.

**The acceptance test has two halves, and the second half is the one people skip:**

1. A corpus page **reaches** the `items` list — the gate accepts a full-text source on its
   passage, not on its title.
2. The abstract-only result set is **byte-identical** to what the same briefs produced before
   the change. If the live results moved, the gate change broke layer 2 and B-168 is not yet
   proven. This is the `G-12` obligation in `CORPUS_DB.md`.

Record the live-run result against B-168 in `docs/DECISIONS.md` and `docs/WORKLOG.md` when it
passes.

**Remember the governance gate.** Steps 8 and 9 change files inside the pipeline repo, so they
need tests + `CHANGELOG.md` + `WORKLOG.md` + a B-numbered `docs/DECISIONS.md` entry. The
corpus build files (`corpus-db/build/**`) sit outside the pipeline repo and do not.

## 14. Steps 10–16 (later, after the slice works)

| Step | Work | Done when |
|---|---|---|
| **10** | Extract at scale. pypdf for the text layer, Tesseract **only** for scans. | Every document is `ok` or `ocr` in `ingest_log`. Nothing failed silently. |
| **11** | Seed ~20 real documents: 2 subjects deep, ≥1 scanned book, ≥1 born-digital. | Two different pages of the same book can each fill a dimension (subject to the Q-16 cap). |
| **12** | Meilisearch on the VPS, with a master key bound to localhost. | A stopped container degrades to layer 2 instead of erroring. |
| **13** | R2 bucket: private, custom domain + Cloudflare Access, nightly `rclone sync`. | A test restore reproduces the database and rebuilds the index. **Never** expose the bucket
through an `r2.dev` subdomain. |
| **14** | Bulk harvest, in the §4.5 order: **OpenStax → OpenAlex content API → DOAJ → NBER/SSRN**. | `licence` and `metadata_source` recorded on every document. No NC-SA title ingested without an owner decision. |
| **15** | Orientation pass: advisory only, non-blocking, cached, never citable. | The evidence list is byte-identical with and without the pass. |
| **16** | Drift check: re-hash the PDFs and the page text. | Zero mismatches; a deliberately corrupted file is reported. |

**Step 14 is the one the owner can shortcut.** The owner already has books and papers. Those do
not need a harvest, a licence check or a wait — they go in through the admin page (Step 7) with
the owner's own metadata, today. The harvest is for the long tail.

## 15. Do not do these

- Do not build the schema beyond what is in `schema.sql`. It is finished.
- Do not set up R2 or a VPS before Step 11 proves the contract works.
- Do not run the live gate test before the adapter returns correct items. Measuring a corpus at
  weight 1 cannot show whether the corpus works — the design record re-ordered the build for
  exactly this reason.
- Do not harvest in bulk before the 20-document seed.
- Do not OCR a whole corpus at once. OCR throughput is the real schedule risk, not infrastructure.
- Do not let the corpus replace the live APIs. It is layer 1.
- **Do not relax the licence gate to drain the queue faster.** It lives in `enrich.fetch`, and a
  restrictive licence is a decision for the owner, not an obstacle to route around.
- Do not invent a printed page number, an edition, an ISBN or a licence to make a row look
  complete. `NULL` and a named gap is the correct output.
- Do not change anything under `src/bp/**` core modules. Product layer only.
- Do not make the learning hook a hard dependency of a paper run. It is a signal, not evidence.

## 16. Where the truth lives

| Question | File |
|---|---|
| Why is it built this way? | `corpus-db/CORPUS_DB.md` §4 (architecture), §6 (risks), §7 (rejected options) |
| What is decided? | `corpus-db/CORPUS_DB.md` §3 and §13 (D-01…D-16) |
| What is still open? | `corpus-db/CORPUS_DB.md` §8 (Q-01…Q-17) and `docs/CONTINUATION_NOTE.md` (D-17, D-18, Q-19) |
| What does it cost? | `corpus-db/CORPUS_DB.md` §10 |
| Which facts were verified, and where? | `corpus-db/CORPUS_DB.md` §12 |
| What is the harvest query per subject? | `corpus-db/SEARCH_KEYWORDS_BY_SUBJECT.md` |
| How is the pipeline's source order and gate rule worded? | `docs/CONDUCTOR_MANUAL.md` §9 and §6.2.3, and `docs/DECISIONS.md` B-168 / B-169 |
| What is the pipeline's current build? | `docs/HANDOFF.md` |
| Do the build tools still behave? | `corpus-db/build/test_corpus_build.py` |

**Record what you decide.** Every decision you make goes in `corpus-db/CORPUS_DB.md` §13 (decision
log) and §14 (change log), and every change inside the pipeline repo gets a B-number in
`docs/DECISIONS.md`. Append; do not rewrite history.
