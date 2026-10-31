# CORPUS BUILD — WHERE WE ARE RIGHT NOW

**Read this first if you are a person or a model picking up the corpus work.**
It is deliberately written in plain words, with no jargon, so that any model can read it
cold and continue without re-reading everything else.

Three other documents matter, in this order:

| Document | What it is |
|---|---|
| `CORPUS_DB.md` | **Why** it is built this way — the decisions, gaps and open questions. The design authority. |
| `DATABASE.md` | **How** to build it — the ordered steps, the commands, the code. The execution manual. |
| this file | **Where we are** — what is decided, what is done, what is next, and what happened. |

If this file and `DATABASE.md` ever disagree, `DATABASE.md` wins for *how*; this file only
says *how far we got*. Nothing here overrules a decision in `CORPUS_DB.md`.

---

## 1. What we are building, in plain words

The pipeline currently asks live academic websites for **abstracts**. An abstract is a short
summary — you cannot quote a sentence from it and say "page 143". It is also slow, and most of
what those websites hold is never used by anybody.

So we are building a **private library of the actual books and papers** that fills itself:

- the **PDF files** are the bytes;
- a **database with one row per page** is the record. This is the truth;
- a **search index** (Meilisearch) makes finding a page instant. It is a copy, disposable and
  rebuildable from the database at any time;
- a **learning log** records what the students kept asking for and the library could not answer,
  so the library knows what to go and get next.

The smallest unit is **one page**, because a page is the smallest thing you can point at.

The library does **not** copy the websites. It grows only towards what is actually asked for.
A document gets in because a question kept going unanswered.

---

## 2. The rules that cannot be broken

Short form. The full version is `DATABASE.md` §1 and `CORPUS_DB.md` §2.

1. **No invented evidence.** Every quote traces to a recorded page.
2. **Gaps are named, never filled.** If a page number cannot be read, it is empty (`NULL`).
   Never a guess.
3. **The core stays frozen.** The corpus never changes `src/bp/**` core. Only the product
   layer, `src/bp/product/**`, is added to.
4. **Standard library only at runtime.** The pipeline may use `sqlite3` and `urllib`. No extra
   packages. Meilisearch's plain web address satisfies this.
5. **The library adds to the live sources, it never replaces them.** Corpus first, then the
   live websites, then curated web. All three keep working.
6. **The library stays private.** The Cloudflare bucket is private, never a public address.
7. **The owner decides what enters.** Anything with a restrictive licence waits for the owner.
8. **Every act gets a log entry at the bottom of this file** — because a session can run out of
   tokens at any moment, and the next model must know what already happened.


---

## 3. Decisions locked so far

| # | Decision | Set by | Date |
|---|---|---|---|
| B-1 | Build on a **new branch `corpus/v1-build`**, cut from `design/v0.73-rail`. The corpus documents and `retrieval.py` do not exist on `main`. | owner + agent | 2026-10-31 |
| B-2 | This is **v1**. | owner | 2026-10-31 |
| B-3 | Uploads are **in v1**, not deferred to v2. *(Reading of "its still v1" — confirm before the schema is applied.)* | owner | 2026-10-31 |
| B-4 | First two subjects built deeply: **management** and **marketing**. Not spread across all eleven. | owner | 2026-10-31 |
| B-5 | Meilisearch is **tested locally first**. Nothing is deployed yet. | owner | 2026-10-31 |
| B-6 | Fixes are expected during the build. This is a build, not a deployment. | owner | 2026-10-31 |
| B-7 | **No duplication, now or in future.** The corpus holds one copy of a work. Enforced in the database itself by three unique identities — the file's `sha256`, the normalised DOI, the normalised ISBN — so no ingest, upload or harvest path can create a second copy. The enrichment queue never queues a work the corpus already owns, and never downloads one. | owner | 2026-10-31 |
| B-8 | The upload audit table may hold two rows for two upload attempts of one file; that is the audit telling the truth. What may never be duplicated is the **document**. | owner + agent | 2026-10-31 |

### Why B-3 has a consequence you must know about

If uploads are in v1, the schema as restored is **not enough**. The student-upload path needs
three columns that were lost when `CORPUS_DB.md` was damaged on 2026-10-31:

```
added_by            who uploaded the file
enrichen_at         when it was allowed to feed other students' papers
owner_approved_at   when the owner made it citable
```

The design decisions behind them — `D-17` (dedup by hash plus DOI), `D-18` (private student
upload, owner-mediated), `Q-19` (what copyright check applies) — survive only as one-line
summaries. **Do not invent their text.** Ask the owner and record the answer in
`CORPUS_DB.md` §13.

---

## 4. The build, step by step, and how far we got

The order matters more than anything else. The manual's warning: build the database first and
wire it in later, and the pipeline will silently throw your library away and you will blame the
library.

| Step | What it means | Status |
|---|---|---|
| 0 | Decide the three answers (`Q-02` identity, `Q-03` weight, `Q-16` page cap) | **Partly done** — see §5 |
| 1 | Meilisearch running on your own machine (Docker) | **DONE 2026-10-31** — health returns available (Windows binary, not Docker) |
| 2 | Create the database — 8 tables from `schema.sql` | Not started *(code verified working — see §6)* |
| 3 | Read one PDF into pages; then one **scanned** book | Not started |
| 4 | Meilisearch settings, **before** any documents | Not started |
| 5 | Load the pages into the index; find a known phrase | Not started |
| 6 | The self-filling worker (`enrich.py`) | Not started |
| 7 | The owner upload page | Not started |
| 8 | Wire the library into the pipeline — **the five traps** | Not started |
| 9 | Off-site copy (Cloudflare R2) | **Deferred** — not needed to prove it works |
| 10 | Drift check — hashes still match | Not started |

---

## 5. Step 0 — the three answers

Recommended in the design record, and not yet formally confirmed by the owner:

| # | The question | Recommended | Confirmed? |
|---|---|---|---|
| Q-02 | What makes a library item unique? | `doc_id` + `pdf_page`. A citation is `doc_id` + `section_path`. | No |
| Q-03 | How strongly does a library result count? | **2** — level with OpenAlex and DOAJ. Not 3. | No |
| Q-16 | Can one book fill a whole paper? | No — cap it at **2–3 pages per document per paper**. | No |

---

## 6. What is already proven to work

Verified by running it, not by reading it (2026-10-31):

- The eight tables are created correctly by `corpus_lib.py --init`.
- The learning loop accepts a search and reports honestly: hit rate 0% on an empty library.
- The worker's steps (`collect`, `score`) run and return clean zero results on an empty library.
- The build tool's own test suite passes: **15 out of 15**.
- Foreign keys are switched on by `corpus_lib.connect()` — always use that, never a raw connect.

**What is missing on this machine, and why it does not matter yet:** the PDF reader (`pypdf`),
the scanned-page reader (`pypdfium2`) and the optical character reader (`tesseract`) are not
installed here. `ingest.py` therefore cannot run in this sandbox. They are installed on the
owner's Windows machine. They are build-time tools only — the running pipeline never needs them.

---

## 7. The honest gaps found while reading the code

1. **Nothing in the pipeline talks to the library yet.** Not one file under
   `src/bp/product/` mentions the corpus. So today: no search is recorded, nothing is learned,
   no source is added. This is *not a defect in the database* — it is the wiring in Step 8,
   which was never done. It is fixable, and it is the whole point of Step 8.
2. **The line numbers in `DATABASE.md` §12 have drifted.** The five traps are real, but the
   cited lines have moved (for example `_accept` is now at line 345, not 406). Read the code.
3. **Trap 1 is milder than the manual says.** The title gate already lets a page through when it
   matches the dimension three times in the body. The *real* blockers are trap 3 (a library
   result scores 1 instead of 2) and trap 4 (the list is sorted by a score the library can never
   win, then cut to four). Fix 3 and 4 first, or you will fix a gate that was never the problem.
4. **Where uploads are concerned, see B-3.** The schema cannot yet represent a private upload.

---

## 8. What happens next

**Next action:** run Step 2 (create the database), then `bulk_ingest.py --estimate` on the real
library, then import a small slice before the rest.

Nothing is being changed in code until the owner says go.

---

## 9. The duplication rule (locked — B-7)

One work, one document. This is enforced **in the database**, not only in the code that
happens to call it, so a second path — an upload, a harvest, a hand-run ingest, two people at
once — cannot slip a second copy in.

A document is recognised by three identities, checked in this order:

| # | Identity | Stored as | Refuses |
|---|---|---|---|
| 1 | the bytes | `documents.sha256`, unique | the same file again, whatever it is called |
| 2 | the work (article) | `documents.doi_norm`, unique when known | the same article as a different download |
| 3 | the work (book) | `documents.isbn_norm`, unique when known | the same book as a different scan or edition spelling |

**Spelling is normalised first**, so one work has one identity:
`https://doi.org/10.1000/ABC` → `10.1000/abc`; `978-0-13-235088-4` → `9780132350884`.

**An unknown identity is a gap, not a match.** A book with no ISBN stores an empty value and
therefore collides with nothing. Two unknown-ISBN books are two books — we do not guess that
they are the same one. This is the "gaps are named, never filled" rule applied to identity.

**Three more guards in the worker:**
- a work the corpus already owns is never added to the enrichment queue (`upsert_candidate`);
- a candidate that has been queued anyway is checked **before** any download (`fetch_one`);
- the queue counts one candidate per work, whatever spelling reached it, and rises its
  `seen_count` instead of creating a second row.

**What is deliberately not deduplicated:** the `uploads` audit table. If you upload the same
file twice, it records two attempts, the second marked `duplicate`. That is the log telling
the truth, and deleting it would hide the fact that you tried. The *document* is still one.

**Tests that hold this** (`corpus-db/build/test_corpus_build.py`, class `DuplicationTest`, 9
tests): same file twice; same DOI from different bytes; same ISBN spelled differently; an
unknown ISBN never colliding; the database itself refusing a duplicate hash; the database
itself refusing a duplicate DOI; one candidate per work across DOI spellings; an owned work
never queued; and no download attempted for an owned work.

---

## 10. Loading a whole library — `bulk_ingest.py` (new, 2026-10-31)

`DATABASE.md` step 3 teaches the build on **one** PDF, on purpose: that is how you meet the
hard case before the easy ones. It is not how you load 294 books. `ingest.py` takes one file and
four facts typed by hand; a library of hundreds cannot be typed.

So there is a second tool, `corpus-db/build/bulk_ingest.py`:

```
python corpus-db/build/bulk_ingest.py "D:\SMART BUSINESSWRITER\DATABASE" --subject management --estimate
python corpus-db/build/bulk_ingest.py "..." --subject management --dry-run
python corpus-db/build/bulk_ingest.py "..." --subject management --threads 3
```

What it does, and what it refuses to do:

- **Walks a folder** for `.pdf` files, at any depth.
- **Takes what the file name says**: `Author_Year_title-slug.pdf` → author, year, title. Only
  the year is parsed strictly. Initials are dropped rather than guessed.
- **Records the metadata as unverified.** Every document it writes carries
  `metadata_source = 'filename'` and `metadata_verified = 0`, because a file name is not a
  catalogue record. That is the honest state, and it can be improved later without re-ingesting.
- **Never invents a subject.** It guesses from the title, and if the guess is not one of the
  eleven pipeline subject ids it stores nothing rather than a category of its own.
- **Cannot duplicate** — it calls the same `ingest_pdf()` as everything else, so the three
  unique identities refuse a second copy. Re-running it over the same folder is safe and is the
  intended way to resume an interrupted import.
- **Writes a report** of what it did per file (`status`, `doc_id`, `pages`, `subject`, `year`,
  `title`, `message`) so a failure is a named row, never a silent skip.

`--estimate` is the important one: it reads a few pages of every PDF and tells you how many
pages have text (cheap) and how many need optical character reading (expensive), then stops.
**Run it before you spend hours.** It costs seconds.

### Honest timing, corrected

An earlier answer in this session said "30–60 minutes per book". That figure was wrong as a
throughput number — it described the *first* book, done by hand with the result checked against
the PDF page by page. At scale the arithmetic is completely different:

| Work | Cost |
|---|---|
| a page with a text layer (born-digital PDF) | fractions of a second |
| a page that must be read from the image (scan) | seconds, and this is the whole cost |
| a 300-page scanned book, one core | roughly 5–15 minutes |
| 294 books, if most are scans, one core | **a day or more**, and this is what G-06 warns about |

The database is never the bottleneck; reading the image is. That is why `--threads` exists (each
scan is read by a separate program, so 2–4 at once genuinely helps) and why `--estimate` comes
first. The manual's warning stands: OCR throughput is the real schedule risk, not the schema.

**Status:** written and tested on 2026-10-31 (8 tests). Not yet run against the real library —
it has never seen the owner's PDFs, and `pypdf` is not installed in the agent's sandbox.

---

## 11. Where things live on the owner's machine (recorded 2026-10-31)

These are the owner's actual paths. Record them; several later steps depend on them.

| What | Path | Notes |
|---|---|---|
| **The PDF library** | `D:\SMART BUSINESSWRITER\DATABASE` | ~294 files, ~1.7 GB. The owner's own collection. **Gitignored** — it is a working collection, not source. This is the folder `bulk_ingest.py` is pointed at. |
| **The database (the truth)** | `D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite` | Created **2026-10-31** by `corpus_lib.py --init`. Gitignored: rebuildable from the PDFs. |
| **The search index** | `D:\SMART BUSINESSWRITER\corpus-db\meili` | Meilisearch data directory. Disposable; rebuild from SQLite any time. |
| **Working copies of PDFs** | `D:\SMART BUSINESSWRITER\corpus-db\pdfs` | Only used by `enrich.py` for documents it downloads. `bulk_ingest.py` does **not** copy files here — it records `local_path` as the original location, so the 1.7 GB is never duplicated on disk. |
| **The Meilisearch program** | `D:\SMART BUSINESSWRITER\corpus-db\meilisearch.exe` | The Windows binary, not Docker. Started with `--db-path ...\meili --http-addr 127.0.0.1:7700`. |
| **Bulk import report** | `D:\SMART BUSINESSWRITER\corpus-db\bulk_ingest_report.csv` | Runtime output, gitignored, regenerated by re-running the tool. |
| **The repo** | `D:\SMART BUSINESSWRITER\` | Contains `business_pipeline_v0.12\` and `corpus-db\`. |

**The Python that runs these tools** is the owner's Python 3.x with `pypdf 6.19.0` installed
(verified 2026-10-31). `pypdfium2` and `pytesseract` are not yet confirmed — they are only
needed if `--estimate` reports scanned pages.

### The schema on the owner's machine is a different lineage, not a broken one

On **2026-10-31** the owner's `corpus.sqlite` was dumped. It is a **coherent design of its own**:

```sql
CREATE UNIQUE INDEX idx_documents_sha256   ON documents(sha256);
CREATE UNIQUE INDEX idx_documents_work_key ON documents(work_key);
CREATE UNIQUE INDEX idx_candidates_work_key ON candidates(work_key);
```

`documents` and `candidates` both carry an added `work_key` column (added by ALTER, which is why
it appears last in the table SQL). **Both indexes are UNIQUE.** An earlier entry in this file
guessed the sha index might be non-unique because it is named `idx_` rather than `ux_` — **that
guess was wrong, and this is the correction.** The `ux_`/`idx_` prefix is a convention, not a
guarantee; only the DDL proves it, and the DDL says UNIQUE.

**So the duplication guard is active on that machine**, by a different mechanism: one normalised
`work_key` per document and per candidate, plus the file hash.

What that design does **not** enforce, compared with branch `corpus/v1-build`:

- no separate `doi_norm` / `isbn_norm` columns, so a work is protected on **one** identity chosen
  when `work_key` was computed, not on hash **and** DOI **and** ISBN at once;
- how `work_key` is computed is not yet known — if it is the sha256 alone, then it is a duplicate
  of the sha index and the DOI/ISBN protection is absent; if it is `doi:`/`isbn:`/`sha:` chosen in
  that order, then the protection is close to complete. **Unknown until the local `corpus_lib.py`
  is read.**

`work_key` exists in **no branch and no commit of this repository** (every ref searched
2026-10-31), so the owner's `corpus-db\build\` is uncommitted local work from a different session.

**Consequences:**

1. `bulk_ingest.py` and the `pages=` argument live on `corpus/v1-build`, which that checkout has
   not taken — that is why the three commands failed with "No such file or directory".
2. That local work is **unversioned and one overwrite away from being lost.** The project has
   already lost a 764-line document that way (§15 of `CORPUS_DB.md`). **Preserve it in git before
   merging anything.**
3. Do not `git pull` or switch branches there until it is preserved.

**Reconciliation sequence:** (a) owner commits the local folder to a backup branch and pushes;
(b) read that branch's `corpus_lib.py` to learn how `work_key` is computed; (c) merge the two
designs into one schema — keeping `work_key` (it is the better idea: one identity, one index) and
adding the hash/DOI/ISBN guarantees — with a test proving uniqueness; (d) rebuild the empty
`corpus.sqlite` in seconds, since nothing has been imported yet.

---

## 12. Log — one entry per act, newest at the bottom

Each entry: what was done, what it proved, what is next. Append, never rewrite.

### 2026-10-31 — reading and verification (no code changed)
- Read `DATABASE.md`, `CORPUS_DB.md`, `schema.sql`, and every build tool.
- Ran the corpus build tests: 15/15 pass.
- Created the database in a scratch directory: 8 tables confirmed.
- Ran the learning loop by hand: a search records correctly; hit rate reports honestly.
- Checked whether the pipeline writes to the library: **it does not** — see §7.1.
- Confirmed the database file, the PDF working copies and the search index are kept out of git
  by `.gitignore`; the catalogue that describes the library is committed instead.
- **Next:** owner confirms §5 and B-3; then Step 1 (Meilisearch locally) and Step 2 (create DB).

### 2026-10-31 — branch prepared for handoff
- Created branch `corpus/v1-build` from `design/v0.73-rail`.
- Added this file, and pointed `AGENTS.md` at it, so any model can resume from here.
- **No code changed.** Schema, tools and pipeline are exactly as committed in `4618ff3`.

### 2026-10-31 — duplication made impossible (code changed, 9 new tests)
- Owner instruction: assume nothing is duplicated today, and make sure no future upload or
  enrichment can duplicate anything. Recorded as B-7 and B-8.
- Three unique identities now enforced **by the database**: the file hash, the normalised DOI,
  the normalised ISBN. `documents.doi_norm` and `documents.isbn_norm` are new columns.
- Two normalisers added (`norm_doi`, `norm_isbn`) so one work has one identity whatever
  spelling arrives. An unknown identity stays empty and collides with nothing.
- `find_existing()` is now the single place that asks "do we already own this?", checked in the
  order hash → DOI → ISBN, and used by ingest, by the queue and by the downloader.
- The enrichment queue no longer queues a work the corpus already owns, and `fetch_one` checks
  before downloading instead of after (no wasted bandwidth).
- An `IntegrityError` is caught and reported as a duplicate with a clean rollback, so a race
  cannot leave half a document behind.
- **An older database is migrated automatically** on `apply_schema()`: the two columns are
  added before `schema.sql` runs, because `schema.sql` creates an index over them. Verified on
  a database built the old way, and `apply_schema()` twice in a row is safe.
- Tests: **24 pass** (15 before + 9 new in `DuplicationTest`).
- **Next:** unchanged — Step 1 (Meilisearch on the owner's machine) and Step 2 (create the DB).

### 2026-10-31 — owner's Docker attempt failed (nothing changed in the repo)
- `docker run ... getmeili/meilisearch:v1.12` returned `500 Internal Server Error` on
  `dockerDesktopLinuxEngine/_ping`. That is Docker Desktop's engine not running, not a problem
  with the command or with the corpus.
- Two ways forward given in the conversation: restart Docker Desktop, or skip Docker entirely
  and run the Meilisearch binary directly on Windows.

### 2026-10-31 — Step 1 is blocked on a missing download, not a broken machine
- `meilisearch.exe` is not in `D:\SMART BUSINESSWRITER\corpus-db`, so Windows said
  "'meilisearch.exe' is not recognized". The binary had not been downloaded, or was downloaded
  under its release name `meilisearch-windows-amd64.exe`, or landed in `Downloads`.
- The exact asset for v1.12.0 is `meilisearch-windows-amd64.exe` (119,958,016 bytes), at
  `https://github.com/meilisearch/meilisearch/releases/download/v1.12.0/meilisearch-windows-amd64.exe`
  (verified against the GitHub releases API on 2026-10-31, not quoted from memory).
- **Next:** owner puts that file in `corpus-db\` as `meilisearch.exe`, starts it, and reports
  `http://127.0.0.1:7700/health`. Then Step 2 (create the database) can run.


### 2026-10-31 — Step 1 done; a bulk importer built because per-book typing does not scale
- Owner reported `{"status":"available"}` — **Meilisearch is running locally.** Step 1 complete
  (running the Windows binary, not Docker).
- Owner asked whether the 30–60 minutes per book can be automated. It must be, and the figure
  was corrected: that was the *first* book checked by hand, not a throughput number.
- `ingest_pdf()` gained an optional `pages=` argument, so a PDF can be read in a thread and the
  database still written by one connection. Backwards compatible; the old callers are untouched.
- Added `corpus-db/build/bulk_ingest.py`: walk a folder, parse `Author_Year_title.pdf`, import,
  report per file, refuse to invent a subject, record metadata as unverified, and resume safely
  because duplicates are refused by the database.
- Added `--estimate`: pages with text vs pages needing OCR, with a time estimate, before the
  owner commits hours. Measured nothing on the real library yet — it has not seen those files.
- Report file is gitignored; it is runtime output, regenerated by re-running the tool.
- Tests: **32 pass** (24 before + 8 new in `BulkIngestTest`).
- Discovered while checking: `catalogue/manifest.csv` is a **50-source harvest record**
  (37 saved, 23 PDFs), not a catalogue of the owner's 294-file library. The 294 files have
  metadata **only in their file names**. That is why name parsing matters here.
- **Next:** Step 2 — create the database with `corpus_lib.py --init`. Then `--estimate` on the
  real library, then a first small import.


### 2026-10-31 — Step 2 done, but the machine's schema is a different lineage
- Owner ran `corpus_lib.py --init` → `schema applied: D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite`.
  Eight tables exist (documents, pages, ingest_log, search_log, seen_sources, candidates, uploads,
  web_sources). **Step 2 is done.** `pypdf 6.19.0` is installed on that machine.
- Recorded the owner's paths (new §11), including the PDF library at
  `D:\SMART BUSINESSWRITER\DATABASE` (294 files, ~1.7 GB).
- **Divergence found:** the owner's database carries `idx_documents_work_key`,
  `idx_candidates_work_key`, `idx_documents_sha256`. `work_key` exists in **no ref of this
  repository**, and the repo's `ux_documents_sha256` / `ux_documents_doi_norm` /
  `ux_documents_isbn_norm` are **absent** from that database. So that machine is running a
  locally-edited, uncommitted schema of a different design.
- **What this means:** the duplicate refusal added here (B-7) may not be protecting that
  database. `idx_` names suggest a plain index, which refuses nothing. Unverified — must be
  checked, not assumed.
- **Second consequence:** `bulk_ingest.py` does not exist on that machine (it lives on
  `corpus/v1-build`, not yet in that checkout), which is why the three commands failed with
  "No such file or directory".
- **Deliberately did not** tell the owner to `git pull`: that could overwrite the local schema
  edits or collide with them. Asked for the actual DDL first.
- **Next:** owner dumps `sqlite_master` and reports `git branch` / `git status`; then reconcile the
  two schemas into one, with the uniqueness guarantee proven by a test before any import.


### 2026-10-31 — owner's DDL read: the guard is real, and my earlier suspicion was wrong
- The owner dumped `sqlite_master`. The three guards are `UNIQUE`: `idx_documents_sha256`,
  `idx_documents_work_key`, `idx_candidates_work_key`. `documents` and `candidates` both carry a
  `work_key` column added by ALTER.
- **Correction recorded above:** the previous entry suspected `idx_documents_sha256` was a plain
  index because of its `idx_` prefix. It is UNIQUE. Prefix naming is a convention; only the DDL
  decides, and the DDL was checked.
- The owner's design is sound and in one respect better than mine: one identity column, one unique
  index, instead of three. What is still unknown is **how `work_key` is computed** — that decides
  whether DOI and ISBN protection actually exists or only the file hash is protected twice.
- The dump was partial: `documents`, `pages` and `search_log` DDL and the `work_key` computation
  are still missing, so the reconciliation cannot be completed yet.
- Their local `corpus-db\build\` is uncommitted work from another session. It must be pushed
  before anything is merged over it.
- **Next:** owner pushes the local folder to a backup branch and prints the signature of
  `ingest_pdf` plus how `work_key` is built. Then the two designs merge into one.

### 2026-10-31 — how the owner's `work_key` is built (partial read)
- `corpus_lib.work_key_for(meta)` at line 149. Duplicate check at line 374:
  `SELECT doc_id FROM documents WHERE work_key = ?`. Insert at line 499 records
  `work_key_for(meta)`.
- `backfill_work_keys()` (line 238) runs from `apply_schema()`, so a database made before the
  column existed is migrated. `documents` and `candidates` both carry `work_key` (columns list
  confirmed; `documents` has no `doi_norm` / `isbn_norm`).
- **Decisive evidence about what the key contains:** the backfill calls
  `work_key_for({"title", "authors", "year", "doi"})` — **no sha256, no isbn**. So `work_key` is
  derived from *metadata*, not from the file. That means:
  - the same DOI is caught by `work_key`, whatever the bytes (the "second download" case) ✔
  - the same file is caught by the separate unique `sha256` index ✔
  - **a book with no DOI whose scans differ in title spelling and whose bytes differ is NOT
    caught** — no ISBN in the key. This is the one real gap versus B-7.
- The body of `work_key_for` itself (lines 149–170) has not been read yet; only its callers.
- **Next:** owner pushes the local folder to a backup branch so it can be read in full; the merge
  then keeps `work_key` (extended to carry the ISBN) and keeps the three identity guarantees.

### 2026-10-31 — correction: nothing is hiding the files; they are simply uncommitted
- Owner ran `git ls-files -v corpus-db/build`: **every file shows `H`** — tracked, normal, no
  `assume-unchanged` (`h`) and no `skip-worktree` (`S`).
- `.git\info\exclude` is the **stock template**, unmodified. No nested `corpus-db\.git` was found
  (the individual files are listed by the outer repo, which a nested repo would prevent).
- **So no hiding mechanism exists.** The previous entry concluded git was being told to ignore the
  files; that conclusion does **not** hold and is superseded here. With `H` flags and an empty
  exclude, a differing file *must* appear in `git status`.
- The ordinary explanation stands: the owner's `corpus-db/build/` holds **uncommitted local
  edits** (807+ line `corpus_lib.py` against 513 in `4618ff3`), and the `git status --short` output
  was never pasted, so it could not be read.
- **Action:** commit those edits on a fresh branch and push them, then read them from origin. No
  console output needs to be pasted; the commit itself carries the content to somewhere readable.
- Still unanswered: whether another agent session is writing to that folder. Nothing force-edits;
  a normal commit on a new branch cannot clobber the working tree either way.

#### The evidence that prompted that alarm, kept so it is not repeated
- `HEAD` = `4618ff3`, identical to `origin/design/v0.73-rail`. Verified against it:
  `git grep work_key 4618ff3 -- corpus-db/build/` returns **nothing** (exit 1), `corpus_lib.py`
  there is **513 lines**, and line 149 is `count = len(reader.pages)`; `schema.sql` has no
  `work_key`.
- The owner's disk has `def work_key_for(meta):` at line **149** and content past line **807**.
- The first alarm came from reading "`git status --short` printed nothing" as fact. It was not
  established — the output was simply absent from the paste. **Lesson: an absent line of output is
  not evidence of absence; ask for the fact explicitly before drawing a conclusion from it.**
- **Direction of the merge is unaffected and still correct:** the owner's `corpus_lib.py` (807+
  lines) is a **superset** of the 513-line version here. Merge *into theirs*: add the ISBN to
  `work_key_for`, add the optional `pages=` argument, and add `bulk_ingest.py`. Never replace it.

### 2026-10-31 — push rejected: the Meilisearch binary is not source
- The owner's snapshot commit was pushed and **rejected by GitHub's pre-receive hook**:
  `corpus-db/meilisearch.exe is 114.40 MB; this exceeds GitHub's file size limit of 100.00 MB`
  (`GH001`). `git add -A` had swept the downloaded program into the commit.
- Nothing was lost: the remote **never accepted** the branch, so the commit is still local only
  and can be rewritten safely. **No force-push is involved** — there is nothing on the remote to
  overwrite.
- Fix, in this order: ignore the binary, unstage it, amend the local commit, push again.
- `.gitignore` on `corpus/v1-build` now carries `corpus-db/meilisearch.exe` and `corpus-db/*.exe`,
  so no future `git add -A` can repeat this. The owner also adds it to `.git/info/exclude` so the
  same mistake is blocked before the branch arrives here.
- **Rule this establishes:** a downloaded program is not source. `corpus-db/corpus.sqlite`, the
  PDF working copies, the `meili/` index and this `.exe` are all runtime, all rebuildable, all out
  of git. Only the catalogue, the schema, the code and the tests belong in the repository.
- Also worth noting: the pack was 125 MiB of which 114 MiB was that one file, so the pushed tree is
  small once it is excluded.

### 2026-10-31 — MERGED: the two lineages are one branch (`corpus/merge-v1`)
- Read the owner's whole `corpus_lib.py` from `corpus/local-workkey-backup` (955 lines). It is
  **better than the version on `corpus/v1-build`** and is now the base: `work_key_for`,
  `candidate_key`, `register_functions` (norm rules taught to SQLite), `migrate` + `MIGRATIONS`,
  `find_duplicate`, `restore_missing_file`, `find_document_for`, `record_refusal`, `record_upload`.
- Its best judgement, kept: `work_key_for` returns **None** when the metadata cannot name a work,
  because "a key that is too weak would merge two different books and lose one of them, which is
  worse than a duplicate slipping through".
- **Added — the one real gap: an ISBN now names a book.** `norm_isbn()` accepts ISBN-10 or
  ISBN-13, verifies the checksum and returns one ISBN-13, so `0132350882` and
  `978-0-13-235088-4` are the same book. A number that fails its checksum names **nothing**, so a
  mistyped ISBN cannot refuse a genuinely different book. Key order is now DOI → ISBN →
  title|author|year.
- **`backfill_work_keys()` now re-keys**, not merely fills NULLs. When the rule improves, a row
  keyed under the old rule would never gain the better identity. Two rows that now look like one
  work are **not merged**: the second is given no key and falls back to the file check, leaving
  the decision to the owner.
- **Added `pages=` to `ingest_pdf`**, so a bulk importer can read PDFs in parallel while one
  connection writes. Backwards compatible; every existing caller is unchanged.
- **Added `bulk_ingest.py`** against the owner's API: walks a folder, reads
  `Author_Year_title-slug.pdf`, takes a **checksum-validated** ISBN from the name when present,
  records metadata as `metadata_source='filename'` / `metadata_verified=0`, refuses to invent a
  subject, writes a per-file report, and resumes safely because duplicates are refused.
  `--estimate` and `--dry-run` included.
- `.gitignore` on this branch also excludes `corpus-db/meilisearch.exe` and `corpus-db/*.exe`.
- **Tests: 44 all pass** — the owner's 30 plus 14 new (`IsbnIdentityTest`, `BulkIngestTest`).
  Verified here only with a **temporary stand-in for `pypdf`** (the sandbox cannot install it);
  the stand-in is not committed. On the owner's machine the real `pypdf 6.19.0` runs them.
- **Next:** owner checks out `corpus/merge-v1`, deletes the empty `corpus.sqlite` (the schema did
  not change, so this is optional), then runs `bulk_ingest.py --estimate` on
  `D:\SMART BUSINESSWRITER\DATABASE`.

### 2026-10-31 — the first real measurement of the owner's library
- `bulk_ingest.py --estimate` on `D:\SMART BUSINESSWRITER\DATABASE` **completed**:
  - **148 PDF files** (not 294 — that figure counts every file in the collection, not the PDFs)
  - **26,897 pages with a text layer** (fast: fractions of a second each)
  - **1,484 pages needing OCR** (5.2% of pages) — the only slow part
  - **roughly 1.0 hour on one core**, and the estimate is deliberately pessimistic
- **Conclusion: OCR is not the schedule risk here that G-06 warns about.** 95% of the library is
  born-digital. The whole library is about an hour of machine time, not days.
- The run looked like a hang because pypdf printed `Ignoring wrong pointing object N 0 (offset 0)`
  hundreds of times — a recoverable warning about a malformed cross-reference table in some of the
  scanned PDFs, not an error.
- **Fixed:** `bulk_ingest.py` now sets `logging.getLogger("pypdf")` to ERROR, prints progress every
  ten files during `--estimate`, and offers `--sample N` (measure N files and scale up, labelled as
  a sample) so a full measurement is never needed to answer the question.
- One new test (`test_a_sample_is_scaled_up_and_labelled_as_one`). **45 tests pass** with the
  pypdf stand-in; the same 9 remain environmental without it.
- **Open question for the owner:** the collection holds ~146 files that are **not PDF**. The corpus
  reads PDF only, so those cannot be ingested — what are they (EPUB, DJVU, notes)?
