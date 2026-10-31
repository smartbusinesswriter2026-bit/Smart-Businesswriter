# Corpus Database — living design record

A proprietary evidence corpus for the Smart Business Writer pipeline: PDFs (books,
journals) that become citable, page-exact evidence.

**This is a living document.** It is the single source of truth for this discussion.
Append decisions, do not rewrite history. Use the IDs (`D-xx`, `G-xx`, `Q-xx`, `S-xx`,
`C-xx`) to refer to items across sessions.

| Field | Value |
|---|---|
| Status | Active design discussion. Architecture proposed, policy recorded, partly built. |
| Last updated | 2026-10-31 (sixth pass: the owner-facing walkthrough `corpus-db/WALKTHROUGH.md` — D-24; the corpus manual and the walkthrough rebuilt and accepted by rendering them) |
| Owner | Butch Chukoy (decisions) · model sessions implement on request |
| Corpus size target | **≤ 10 GB** (owner constraint, added 2026-10-30) |
| Corpus composition | **Mixed books and journals** (owner, 2026-10-30) |
| Subject scope | The pipeline's own subjects: accounting, finance, economics, management, project management, entrepreneurship, operations, supply chain, marketing, people, research |
| Search engine | **Meilisearch** (owner requirement, 2026-10-30) |
| Source model | **Layered**: corpus → live academic APIs → curated web (B-168) |
| Evidence rules | **Relaxed in form, not substance** (B-169): paraphrase allowed, metadata gaps recorded not printed, substitution allowed when declared |
| Citation locators | **None by default** (B-169): page/chapter locator only on the student's request or when the pipeline decides the claim needs one |
| Orientation set | **Topic-dependent and free-first** (B-169), not fixed on Harvard Business Review |
| Related repo | `business_pipeline_v0.12/business_pipeline` (the pipeline this corpus feeds) |
| Pipeline docs | `business_pipeline_v0.12/business_pipeline/docs/CONDUCTOR_MANUAL.md`, `docs/HANDOFF.md` |
| Decision record | `business_pipeline_v0.12/business_pipeline/docs/DECISIONS.md` **B-168**, **B-171** |
| Corpus documents | `DATABASE.md` (the execution manual) and `corpus-db/WALKTHROUGH.md` (the owner-facing walkthrough) — see D-24 |

---

## 0. How to pick this up

If you are a model or a person resuming this work:

1. Read §2 (constraints) and §3 (current decisions) — these are the binding facts.
2. Read §5 (integration points) — this corpus is **not** a standalone product; it feeds
   an existing retrieval pipeline whose gate and citation contracts it must satisfy.
3. Read §6 (gaps) and §8 (open questions) — these are the unresolved items. Do not guess
   them; they need an owner decision.
4. Read §9 (the orientation pass) before touching research or web search.
5. Check §14 (change log) for what moved since your last visit.
6. Append to §13 (decision log) and §14 when you settle something. Update "Last updated".

**If you are the owner rather than a builder:** read `corpus-db/WALKTHROUGH.md` (Word copy:
`corpus-db/WALKTHROUGH.docx`) first. It is this record told in plain language, and it points at
`DATABASE.md` for the commands (D-24).

**Vocabulary warning.** "Corpus" = the document collection. "Page" = one PDF page, the
retrieval and citation unit. "Hit" = one search result. "Provenance" = the recorded
chain from a claim to the exact page that supports it. "Orientation" = advisory
background read before retrieval; never citable (§9).

---

## 1. Purpose

The pipeline currently retrieves evidence from live academic APIs (OpenAlex, Semantic
Scholar, DOAJ) and curated web domains. Those sources give **abstracts**, not **text**.
The owner wants a private corpus of specialist books and journals whose full text can be
quoted, located by page, and cited with a verifiable locator.

The corpus must obey the pipeline's non-negotiables (`CONDUCTOR_MANUAL.md` §4):

1. No invented evidence — every claim traces to a recorded source.
2. Gaps are named, never filled — a missing page number is `NULL`, never guessed.
3. No silent framework substitution.
5. Computations come from the frozen core.

**The corpus does not replace the live sources.** It is the first layer of a layered
evidence base (D-09). Books are the primary evidence; the corpus also holds an owned
subset of journals for fast, page-exact retrieval; journals outside that subset come
from the live APIs, and the curated web still supplies what neither can.

**An open tension, recorded rather than resolved.** The stated driver is the owner's own
books, already on disk (S-04), because they are the specialist material the live APIs
cannot supply in full text. The harvest path that the design then sketched (D-16) is
open-access journals and open textbooks, and the first document named for ingest is an
arXiv paper (Q-08) — a born-digital article with a text layer, a DOI and clean metadata.
So v1 as sequenced does not yet exercise its own premise, and step 1's acceptance test as
written would pass on the easy case and never meet the scanned-book case that motivates
the page model. Nothing here is a rule; it is the largest coherent gap in the plan and it
is carried as **Q-14**.

---

## 2. Constraints

### 2.1 Hard constraints

| Id | Constraint | Origin | Consequence |
|---|---|---|---|
| C-01 | Corpus ≤ 10 GB | Owner, 2026-10-30 | Removes the D1 per-database ceiling as a blocker; makes a single-node design comfortably sufficient; makes R2 storage free. |
| C-02 | Stdlib only at runtime | `HANDOFF.md` rule 5 | The database client must be `sqlite3` (stdlib) or HTTP via `urllib` (stdlib). No psycopg2, no elasticsearch client, no meilisearch python SDK at runtime. Meilisearch's REST API satisfies this. |
| C-03 | Core deterministic backend is frozen (B-079) | `HANDOFF.md` rule 10 | The corpus must not require changes under `src/bp/**` core modules. Product-layer (`src/bp/product/**`) additive work is allowed under the design lane (B-080). |
| C-04 | Meilisearch required | Owner, 2026-10-30 | Meilisearch cannot run on Cloudflare Workers. It must be self-hosted or Meilisearch Cloud. |
| C-05 | No invented evidence / gaps named | `CONDUCTOR_MANUAL.md` §4 | Missing metadata (printed page number, edition, ISBN) must be `NULL` and surfaced as a gap, never inferred. |
| C-06 | Doc governance | `HANDOFF.md` rule 6 | Any change inside the pipeline repo needs tests + CHANGELOG + WORKLOG + a B-numbered DECISIONS entry. This living doc sits **outside** the pipeline repo so it does not itself trigger that gate. |
| C-07 | Corpus is mixed books **and** journals | Owner, 2026-10-30 | Both document kinds share one schema and one index. A journal article is a document with a `source_kind` of `journal-article`, `venue`, `volume`, `issue` and a DOI; a book is a document with a `publisher`, a possible `edition`, no DOI and no venue. |
| C-08 | Subject scope is the pipeline's own subjects | Owner, 2026-10-30 | The corpus taxonomy reuses the pipeline's subject ids (accounting, finance, economics, management, project-management, entrepreneurship, operations, supply-chain, marketing, people, research — `scripts/ui_smoke.py:29`). No new taxonomy is invented; the pipeline's subject ids are the corpus `subject` values. |
| C-09 | The corpus supplements, never replaces, the live sources | Owner, 2026-10-30 | The layered source order is recorded in `CONDUCTOR_MANUAL.md` §9 (B-168). A paper must still be able to draw on journal and web sources outside the corpus. |

### 2.2 Soft constraints / preferences

| Id | Preference | Note |
|---|---|---|
| S-01 | Low or zero marginal cost | Owner asked to stay within 10 GB; cost model in §10. |
| S-02 | Corpus text should not leave the owner's machine | Copyrighted books. Affects whether D1 / Meilisearch Cloud are acceptable. |
| S-03 | The corpus should be usable by the existing retriever unchanged | Minimises work in the frozen-critical path. |
| S-04 | Faster download from an owned copy | Owner's stated reason for the corpus: books and key journals are already local, so retrieval is instant and does not depend on an API. |

---

## 3. Current decisions

| Id | Decision | Status | Rationale |
|---|---|---|---|
| D-01 | Split the system into **bytes layer** and **index layer**. Bytes = Cloudflare R2. Index = self-hosted on the VPS (SQLite + Meilisearch). | Accepted | R2 gives durable off-site storage with free egress; Meilisearch cannot run on Cloudflare (C-04); the index is rebuildable and disposable so it does not need cloud durability. |
| D-02 | The **canonical copy** of every PDF lives in R2; the VPS holds a working copy. | Accepted | R2 free tier is 10 GB-month storage (§12), so a ≤10 GB corpus costs **$0**. Local copy keeps extraction and page rendering fast and offline. |
| D-03 | The **system of record** is a SQLite database on the VPS. Meilisearch is a **derived, disposable index**. | Accepted | A lost or corrupt Meilisearch index is a rebuild, not a data-loss event. Rebuild source = SQLite `pages` table. |
| D-04 | Retrieval unit is **one PDF page** (`doc_id`, `pdf_page`). Not fixed-length token windows. | Accepted | A citation needs a page locator; token windows straddle page boundaries and produce uncitable offsets. |
| D-05 | `printed_page` is stored **separately** from `pdf_page` and may be `NULL`. | Accepted | Scanned books often have no recoverable printed page number. `NULL` is the honest value (C-05). |
| D-06 | Page text is stored in SQLite, not only in Meilisearch. | Accepted | Page text is the **evidence**. It must be quotable and hashable outside the search index, and must survive a Meilisearch rebuild byte-for-byte. |
| D-07 | Meilisearch indexes **pages** (one document per page), not whole books. | Accepted | Matches D-04; keeps hits page-addressable. |
| D-08 | Vector/hybrid search is **deferred**, not ruled out. | Accepted (deferred) | Meilisearch hybrid search is stable and tunable (`semanticRatio`), but an embedder is mandatory for hybrid/similar queries and **DeepSeek serves no embeddings endpoint**. Revisit only if lexical recall proves insufficient. See Q-05. |
| D-09 | **The evidence base is layered.** Corpus (layer 1) → live academic APIs (layer 2) → curated web (layer 3). No layer replaces another. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §9, B-168 | The corpus is owned, page-exact and instant (S-04); the APIs still answer what the corpus does not; the web still supplies what neither can (C-09). |
| D-10 | **The title rejection is discarded for full-text sources.** A full-text source is judged on the passage it quotes, not on its title; the title is never sufficient on its own. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §6.2.3 and §6.3.3, B-168 | The title rule is a rule about *abstract-only* records, where the title is the only signal of subject. A book page carries the passage itself, so the title test is redundant and wrong there: a book is titled for its subject, not for the sentence on page 143. Left alone it would have silently discarded every book result — the one failure mode the non-negotiables exist to prevent. The abstract-only path is unchanged. |
| D-11 | **The orientation pass is advisory only.** It may read reputable practice and business-press sources before retrieval; it never enters the evidence list, never carries a citation, is never quoted, never blocks, and its failure is a notice rather than a gap. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §9, B-168 | Orientation is genuinely useful — it tells the conductor what the field currently believes and how a case is usually framed — but practice and business-press content is not academic evidence and must never be laundered into a citation. The separation preserves "no invented evidence" while letting the model orient. See §9. |
| D-12 | **The corpus is mixed and subject-aligned.** Books and journals share one schema; the `subject` taxonomy is the pipeline's own subject ids (C-08). | Accepted (owner, 2026-10-30) | The corpus must be usable by every shelf in the product, not by one framework. Reusing the pipeline's subject ids avoids a second taxonomy that would need a permanent mapping table. |
| D-13 | **The evidence rules are relaxed in form, not in substance.** A claim may be paraphrased from its source; a metadata gap is recorded as `NULL` and not printed; a framework may be substituted when the substitution is declared and recorded. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §4, B-169 | The suffocation came from the manual being stricter than the code. §6.2.8 already has the model write one call per dimension from the items, with a validator that refuses any number, citation, link or mid-sentence proper noun not in the items — so the guarantee the rule exists to provide was already enforced in code. The relaxations restore the intended behaviour without weakening the guarantee. |
| D-14 | **Citations carry no page or chapter locator by default.** A locator is added only when the student asks for one, or when the pipeline decides the claim needs one; that decision is recorded. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §2 ("Locators are added only when they earn their place"), B-169 | APA 7 and Harvard as written: a book reference entry takes no page number, and an article's page range is its extent, not a locator. The page a claim came from stays in the record, so a locator can be produced on request without searching again. Resolves Q-06 and removes G-01 from the critical path. |
| D-15 | **The orientation source set is topic-dependent and free-first.** Harvard Business Review is one candidate, not the anchor. | **Recorded in the manual** — `CONDUCTOR_MANUAL.md` §9, B-169 | HBR cannot cover every subject and is mostly paywalled. A topical set of free, open publishers is faster and cheaper, and it is the only version of this that scales across the pipeline's eleven subjects. See §9. |
| D-16 | **The corpus is harvested from open access, not assembled by hand.** OpenAlex content API, DOAJ, NBER/SSRN/RePEc and OpenStax. | Accepted (model proposal, 2026-10-30) — recorded in `CONDUCTOR_MANUAL.md` §9 | The owner asked for a free and fast alternative to HBR. The better answer turned out to be that the *citable* corpus is free too, and the harvest can be automated against the queries the pipeline already runs. See §4.5. |

---

## 4. Target architecture

### 4.1 Component map

```
                    ┌──────────────────────────────────────────┐
                    │  VPS (self-hosted)                        │
                    │                                          │
  owner PDFs ──────►│  /corpus/pdfs/           canonical working │
        │           │  /corpus/db/corpus.sqlite system of record │
        │           │  /corpus/db/pages.sqlite (or same file)  │
        │           │  /corpus/meili/           derived index  │
        │           │           │                              │
        │           │           └── Meilisearch :7700 (Docker) │
        │           │                                          │
        │           │  pipeline ──HTTP/urllib──► Meilisearch  │
        │           │     │                                    │
        │           │     └──────sqlite3 (stdlib)──► pages     │
        │           └──────────────────────────────────────────┘
        │
        └── nightly rclone sync ──► ┌───────────────────────────┐
                                     │  Cloudflare R2 bucket     │
                                     │  (canonical bytes, $0 at  │
                                     │   10 GB free tier)        │
                                     └───────────────────────────┘
```

**Layered query path at runtime:**

```
brief
  │
  ├─ orientation pass (advisory, non-blocking, cached)   → vocabulary + framing hints
  │                                                      (never cited, never in evidence)
  ├─ layer 1: local corpus        → Meilisearch + SQLite  → page-exact hits
  ├─ layer 2: live academic APIs  → OpenAlex/S2/DOAJ/Crossref
  ├─ layer 3: curated web         → the vetted registry only
  │
  └─ gate (§6.2.3) → rank → de-duplicate → evidence list → paper
```

**Query path within the corpus:** pipeline → Meilisearch (HTTP, stdlib `urllib`) → hit
carries `doc_id` + `pdf_page` + a snippet → SQLite lookup for full page text, hash and
provenance → `_item()` dict for the existing writer/renderer.

### 4.2 Data model (SQLite)

```sql
-- One row per book or article. This is the CITATION unit.
CREATE TABLE documents (
  doc_id           TEXT PRIMARY KEY,      -- stable internal id, e.g. 'shn-0042'
  title            TEXT NOT NULL,
  authors          TEXT NOT NULL,         -- '; ' separated, family-first for APA
  year             INTEGER,               -- NULL if unknown
  publisher        TEXT,                  -- books
  edition          TEXT,                  -- NULL if unknown (never inferred)
  isbn             TEXT,
  doi              TEXT,                  -- journals
  venue            TEXT,                  -- journals
  volume           TEXT,                  -- journals
  issue            TEXT,                  -- journals
  source_kind      TEXT NOT NULL,         -- 'book' | 'journal-article'
  subject          TEXT,                  -- the pipeline's subject id (C-08)
  local_path       TEXT NOT NULL,         -- path on the VPS
  r2_key           TEXT,                  -- object key in R2
  source_url       TEXT,                  -- where the file came from; NULL for the owner's own scan
  sha256           TEXT NOT NULL,         -- SHA-256 of the PDF bytes
  pages_total      INTEGER,
  text_method      TEXT NOT NULL,         -- 'pdf_text_layer' | 'ocr'
  licence          TEXT,                  -- e.g. 'CC BY 4.0'; NULL when unknown, never assumed
  licence_verified INTEGER NOT NULL DEFAULT 0,
  metadata_source  TEXT,                  -- 'openlibrary' | 'crossref' | 'manual'
  metadata_verified INTEGER NOT NULL DEFAULT 0,
  added_at         TEXT NOT NULL          -- ISO-8601 UTC
);

-- One row per PDF page. This is the RETRIEVAL and QUOTE unit.
CREATE TABLE pages (
  doc_id       TEXT NOT NULL REFERENCES documents(doc_id),
  doc_version  INTEGER NOT NULL DEFAULT 1,  -- which ingest generation this row belongs to (Q-15)
  pdf_page     INTEGER NOT NULL,          -- 1-based index into the PDF
  printed_page TEXT,                      -- NULL when not recoverable
  section_path TEXT,                      -- e.g. 'Chapter 4 > Competitive Dynamics'
  text         TEXT NOT NULL,
  text_sha256  TEXT NOT NULL,
  chars        INTEGER NOT NULL,
  text_method  TEXT NOT NULL DEFAULT 'pdf_text_layer',  -- per page: a scan can sit inside a born-digital book
  PRIMARY KEY (doc_id, doc_version, pdf_page)
);
CREATE INDEX idx_pages_doc ON pages(doc_id);
CREATE INDEX idx_pages_subject ON documents(subject);

-- Audit of every ingest, for replay and for the drift check.
CREATE TABLE ingest_log (
  ingested_at TEXT NOT NULL,
  doc_id      TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  method      TEXT NOT NULL,
  pages       INTEGER NOT NULL,
  status      TEXT NOT NULL               -- 'ok' | 'ocr' | 'failed' | 'skipped'
);
```

**Why both page tables:** `documents` holds bibliography (what gets cited). `pages` holds
the quoted text (what gets evidenced). They are separated so a retriever can return a
quote plus its bibliographic parent without joining on every hit.

**Column notes.** Five columns are here because other parts of this document already
depend on them, and the schema could not hold them before:

- `licence` / `licence_verified` — G-17 and step 8's acceptance both require the licence
  recorded per title, and Q-12 asks which classes may enter. Without the columns, step 8
  cannot be accepted by construction.
- `source_url` — the `_item()` shape (§5.2) carries `url`. A journal article has its DOI
  and a harvested file has a landing page; the owner's own scan has neither, so the field
  is nullable.
- `pages.text_method` — G-05 promises "mark OCR'd pages". A document-level flag alone
  mislabels a born-digital book with a scanned appendix.
- `pages.doc_version` — re-ingesting a corrected PDF would otherwise leave orphaned rows
  with no way to tell which generation is current. Whether the old generation is deleted
  or retained is Q-15, not decided here.

**Connection note.** Enable `PRAGMA foreign_keys = ON` on every connection. SQLite ignores
`REFERENCES` otherwise, which would make the `pages` → `documents` link decorative and let
a page outlive its document silently.

**Books vs journals in one schema:** a book leaves `doi`, `venue`, `volume` and `issue`
`NULL`; a journal article leaves `publisher` and `edition` `NULL`. `source_kind` says
which. The citation renderer branches on it (§5.4, G-02).

### 4.3 Meilisearch index settings

Configure settings **before** loading documents. Changing searchable/filterable/sortable
attributes, stop words, synonyms or typo tolerance triggers a **full reindex** of every
document (Meilisearch indexing guide, §12).

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
  "maxQueryTerms": 64,
  "pagination": { "maxTotalHits": 1000 }
}
```

Setting notes:

- `text` leads the searchable attributes on purpose. On a page-level index the book's
  title repeats on every page, so leading with `title` lets the `attribute` ranking rule
  reward a book whose *title* matches the query over the page whose *passage* does — the
  reverse of what a page-exact evidence index is for. Title and authors stay searchable,
  just not first.
- `disableOnNumbers: true` stops a year `1974` matching `1971`, and stops an ISBN's digits
  transposing. Directly relevant to citation integrity.
- `maxQueryTerms` is raised from the default 10 because **exact-quote verification** may
  need a 15–25 word phrase (§6, G-04).
- `disableOnWords` should list author surnames and domain terms where a near-miss would be
  wrong. Configure per corpus once the actual surname list is known.
- Keep the default 6 ranking rules. The last one, `exactness`, already promotes documents
  containing the exact query phrase — that is the desired behaviour for quoting.
- `subject` is filterable so a query can be scoped to one pipeline subject (C-08).

### 4.4 Discovery through Meilisearch, verification through SQLite

| Mode | Purpose | Where it runs |
|---|---|---|
| **Discovery** | "What does the corpus say about substitute threats in pharma?" | Meilisearch, default typo tolerance, `matchingStrategy` default. |
| **Verification** | "Does this exact sentence appear on this page?" | **SQLite** — `SELECT ... FROM pages WHERE instr(text, ?) > 0`. |

**Proposal, not binding: verification does not belong in Meilisearch.** An earlier draft
put both modes over one index — typo tolerance off, `matchingStrategy: "all"` — for
verification. That is the wrong tool for a question with an exact answer. Meilisearch adds
ranking rules, stop words, tokenisation and `maxQueryTerms` to a test that needs none of
them; SQLite already holds the page text (D-06), so `instr()` returns a yes or a no. G-04
is left open rather than closed, because the choice is the owner's, but the recommendation
is that the verification mode is retired rather than configured.

**Normalise before comparing.** Raw extracted text does not match a typed quote: line-break
hyphenation, ligatures, running heads, column order and stray whitespace all produce false
mismatches. Define one normalisation — de-hyphenate across line breaks, fold ligatures,
collapse whitespace — and compare normalised to normalised. Note the honest limit: the
page hash validates the stored page, not the quoted span. A span-level guarantee would
need character offsets, which are not stored, so a quote is verified as a substring of
normalised page text plus the page's hash, not as a hash of the quote.

### 4.5 Harvesting the corpus from open access

The corpus does not have to be assembled by hand. The free open-access literature maps
onto the pipeline's subjects, and the harvest can be automated against the same filters
the pipeline already runs.

| Source | What it gives | Cost and terms |
|---|---|---|
| **OpenAlex content API** | Full text for open-access works: `content.openalex.org/works/{id}.pdf`, and **GROBID XML**, which carries section structure and so gives `section_path` without parsing a PDF. Filter with `has_content.pdf:true`; `best_oa_location.license` selects CC-BY. | Free API key. Downloads are metered, but the free daily allowance covers a batch. Use the content endpoint, **not** `locations[].pdf_url` — that field is the publisher's URL and keying off it produces a lossy, inferred match. |
| **DOAJ** | Open-access journal articles. Already layer 2 of the live sources. | Free. |
| **NBER, SSRN, RePEc** | Working papers in economics, finance and management — the grey literature the live APIs under-index. | Free to read. |
| **OpenStax** | Peer-reviewed open textbooks: accounting (vol. 1 financial, vol. 2 managerial), finance, economics, management, marketing, business ethics, business law, entrepreneurship, organisational behaviour. Free PDF download. Maps onto most of the pipeline's subjects (C-08). | Open licence, **per title** — CC BY on some, CC BY-NC-SA on others. Check the title before ingesting. |
| **CORE** | 483M free-to-read full texts; 57M PDFs hosted by CORE itself. | Free key; free tier is ~5 single requests per 10 s. **Systematic PDF harvesting needs permission**, and the commercial terms need checking. |

**Harvest order for v1:** OpenStax first (bounded, hand-checkable, covers most subjects),
then the OpenAlex content API filtered by the pipeline's own subject/topic filters, then
DOAJ, then NBER and SSRN for economics and finance.

**Note on the GROBID XML.** It is a better ingest source than the PDF for an
open-access article: it is already structured, already extracted, and already
section-labelled. OCR (G-05, G-06) is then only needed for genuinely scanned documents.

---

## 5. Integration points in the pipeline

All line references are `business_pipeline_v0.12/business_pipeline/src/bp/`.

### 5.1 Where the corpus attaches

| File / line | What it does | Corpus impact |
|---|---|---|
| `product/sources.py:39` `DATABASES` | Registry of academic databases (id, label, kind, access, enabled). | Add a `corpus` entry: `kind: "proprietary"`, `access: "local"`, `enabled: True`. |
| `product/sources.py:364` `ADAPTERS` | `{"openalex": _openalex, "crossref": _crossref, ...}` | Add `"corpus": _corpus`. The adapter signature is `(text, limit, year_from) -> list[item]`. It runs under the shared `_NETWORK` semaphore and the shared response cache, so a local HTTP call to Meilisearch is safe there. |
| `product/sources.py:239` `_item()` | Builds the dict every downstream consumer expects. | The corpus adapter must return dicts in exactly this shape. |
| `product/sources.py:223` `_credibility()` | Transparent quality signal, capped 100. | Corpus items should carry a `credibility` value, or they score 0 and lose ties. |
| `product/retrieval.py:24` `DATABASES` | `["openalex", "semanticscholar", "doaj"]` — which databases the retriever searches. | Add `"corpus"`. |
| `product/retrieval.py:444` `retrieve()` | Searches, gates, ranks, de-duplicates; returns `{items, dropped, errors, skipped, ...}`. | No change needed if the adapter conforms. The layered order (corpus first) is a change to the **order** this function searches in, not to its contract. |
| `product/literature.py:26` `Reference` | The citation dataclass. `reference_type` already documents `"journal-article / book"`. | Corpus items map onto this. |

### 5.2 The `_item()` shape the corpus adapter must return

```python
{
  "title": str, "authors": str, "authors_list": list[str], "year": int | None,
  "venue": str, "volume": str, "issue": str, "pages": str, "publisher": str,
  "item_type": str,            # "book" | "journalArticle"
  "doi": str | None, "url": str | None,
  "abstract": str,             # ← the corpus adapter puts the PAGE TEXT here
  "database": str,             # "Proprietary corpus"
  "kind": str,                 # "proprietary"
  "retrieved_at": str,         # ISO-8601 UTC
  "credibility": int,          # optional, used by rank_item
  "tier": str,                 # optional, "official"/"data" weight 3
}
```

For a **book**: `venue`, `volume`, `issue` and `pages` are empty; `publisher` carries the
publisher and `edition` needs adding to the shape (G-03). For a **journal article**:
`venue`, `volume`, `issue` and `pages` are populated and `doi` is the article's DOI.

### 5.3 The three traps in the existing retrieval contract

**Trap 1 — the title gate and books. POLICY RESOLVED, CODE OUTSTANDING.**
`_accept()` (`product/retrieval.py:406`) requires a dimension cue in the **title** (or
three cue hits in the body), the context word in the body, and the geography word in the
body. A book's title signals the *book's* topic, not the *page's*, so the gate would have
dropped every book result silently.

D-10 / B-168 now record the rule: **a full-text source is judged on the passage it
quotes.** The code change that implements it is still owed and lands with the corpus
build. Concretely, `_accept()` needs a source-kind branch — for a full-text source, one
cue occurrence in the body (the quoted passage) satisfies the cue requirement, and the
title is never sufficient on its own; for an abstract-only source, the existing title rule
is untouched. Until that lands, the manual declares a rule the product does not yet
implement (§13 note).

**Trap 2 — the de-duplication key.** `key_of()` (`product/retrieval.py:435`) uses the DOI
else the title as the identity of a source. The rule "one source cannot fill two
dimensions" is enforced against that key. Corpus items have no DOI (books) or a real one
(journals). If the title is the book title, every page of that book collapses to one key
and pages silently vanish; if the title is book + section, the key is chapter-granular.
**Q-02.**

**Trap 3 — source weighting.** `_source_weight()` (`product/retrieval.py:297`) returns 2
for OpenAlex / Semantic Scholar / DOAJ / Crossref, 3 for `official`/`data` tiers, else 1.
A corpus item without a `tier` scores 1 and loses every near-tie against a live academic
result. **Q-03.**

### 5.4 Citation-format gaps the corpus will hit

| Gap | Location | Detail |
|---|---|---|
| G-01 | `product/writing.py:110` `_in_text()` | Builds `(Who, year)`. **No locator.** Not needed by default any more (D-14), but the on-request path — `(Author, 2020, p. 143)` — is still owed in code. Downgraded from high to medium. |
| G-02 | `product/writing.py:126` `_reference()` | The APA branch renders `title. venue, volume(issue), pages.` when `venue` is set, else `title. publisher.` For a **book**, `venue` must be empty and `pages` must be empty — the page belongs in the in-text locator, not the book reference entry. |
| G-03 | `product/writing.py:126` `_reference()` | **No edition support.** APA 7 book references require `(3rd ed.)`. A book corpus needs it. |
| G-04 | `product/writing.py` | `verify.py`'s exact-quote catalogue needs long-phrase lookup. Meilisearch `maxQueryTerms` defaults to 10 (§4.3). |

---

## 6. Gaps and risks

| Id | Gap / risk | Severity | Mitigation |
|---|---|---|---|
| G-01 | No in-text locator support (page, section). | Medium (was High) | Not needed by default — D-14 takes the locator out of the default citation. Extend `_in_text()` with an optional locator field so the on-request path exists. Product layer (B-080); needs a test. |
| G-02 | Reference rendering for `item_type: "book"` needs an explicit shape. | High | Emit books with empty `venue` and empty `pages`; add edition support. |
| G-03 | No edition field in the reference renderer. | Medium | Add `edition` to `_reference()`. |
| G-04 | Long-phrase verification vs Meilisearch `maxQueryTerms` default of 10. | Medium | Raise `maxQueryTerms` (configurable in settings) **or** retire the verification mode to SQLite (§4.4). Proposed but not closed: if verification moves to SQLite, this gap disappears and `maxQueryTerms` returns to the default. |
| G-05 | **OCR quality.** Scanned books produce unreliable page numbers and garbled text. | High | Store `text_method` per document; mark OCR'd pages; treat `printed_page` as `NULL` when unreadable; run the quote check against the OCR'd text and flag it as OCR-derived, never as exact. |
| G-06 | **OCR throughput.** 10 GB of scans is the real schedule risk, not infrastructure. | Medium | `documents.py` already has the toolchain (`pypdf` text layer; `pypdfium2` + Tesseract for scans). Budget CPU time, or rent a GPU for the OCR pass. |
| G-07 | **Copyright.** Books are copyrighted; the corpus is private. Practice and business-press content must never be ingested into the corpus (D-11). | Medium | Keep the R2 bucket private. **Never use an `r2.dev` subdomain** — it is a public URL. Use a custom domain with Cloudflare Access, or presigned URLs. |
| G-08 | **Metadata sourcing.** Bibliography for books (ISBN, edition, publisher) is not available from Crossref; journals are. | Medium | Books from Open Library / Google Books, journals from Crossref; cache it; record `metadata_source` + `metadata_verified` per document. Never infer an edition. |
| G-09 | **Corpus drift.** The index and the PDF bytes can disagree. | Medium | Hash the PDF (`documents.sha256`) and each page text (`pages.text_sha256`). A mismatched hash invalidates the quote. |
| G-10 | **Embedding provider gap.** Meilisearch hybrid/similar requires an embedder; DeepSeek does not serve embeddings. | Low (deferred) | Use a local Ollama/OpenAI-compatible embedder, or stay lexical (D-08). |
| G-11 | **Single-node failure domain.** One VPS holds the working corpus. | Low | R2 holds the canonical bytes (D-02); SQLite is the system of record; Meilisearch is rebuildable. |
| G-12 | **The live run owed for the gate change.** `CONDUCTOR_MANUAL.md` §6.3 requires a live run before a gate change is recorded, and B-168 records the gate rule as policy with the live run still outstanding. | Medium | The live run is build step 5 (§11) and is recorded against B-168 when it lands. Until then B-168 is provisional. |
| G-13 | **Orientation leaking into the evidence path.** The orientation pass reads reputable practice sources; if its output is allowed near the evidence list, a practice claim can be paraphrased into the paper and read as sourced. | High | Hard separation: orientation output never enters the evidence list, never carries a citation, is never quoted, and is stored apart from the evidence. Enforce in code, not by prompt alone (§9). |
| G-14 | **Orientation blocking the run.** The paper run has a bounded budget (`BP_RESEARCH_DEADLINE`, and the run is 40–70 s). An orientation pass that waits on slow paywalled sites would blow the deadline. | High | Non-blocking, cached, own short timeout, fail-closed to "no orientation". The run must never wait on it (§9). |
| G-15 | **Orientation paywalls.** HBR and comparable sites are paywalled; a search-and-scrape pass often returns titles and snippets only. | Medium | Orientation works on headlines, teasers and abstracts — that is enough to widen vocabulary. Do not attempt full-text retrieval from paywalled sites. The free-first set (D-15) removes most of this problem. |
| G-16 | **Declared framework substitution not implemented.** B-169 permits a substitution that is declared and recorded; the code's refusal path is unchanged, so an unwired framework is still refused outright. | Medium | Code change owed in the framework inference path: refuse only when no declared substitute fits, and record the substitution in the run. |
| G-17 | **Licence is per title, not per source.** OpenStax books carry CC BY on some titles and CC BY-NC-SA on others, and NC-SA constrains commercial use and derivatives. | High for a commercial product | Record the licence per ingested document alongside `metadata_source`. Never assume a source's licence from its publisher. A NC-SA title in a commercial corpus needs an owner decision before ingestion. |
| G-18 | **OpenAlex content downloads are metered.** The free daily allowance covers a batch, not an unbounded harvest. | Low | Track downloads against the allowance; the harvest order (§4.5) starts with the bounded OpenStax set precisely so the metered source is used only for what needs it. |
| G-19 | **CORE bulk harvesting needs permission**, and its commercial terms need checking before a commercial product depends on it. | Low (CORE is not in the v1 harvest order) | Use CORE as a discovery/fallback source, not a harvest source, unless permission is obtained. |
| G-20 | **Meilisearch availability and exposure.** The corpus is layer 1, so an unresponsive `:7700` sits in front of every run. Separately, a self-hosted instance with no master key on a public VPS binds an open index; G-07 protects R2 only. | Medium (proposed, not locked) | Corpus adapter fails open to layer 2 and records a notice — never fails the run. Bind to localhost or set a master key, and treat the API key as a secret. The fallback path needs a test, so a stopped container degrades rather than errors. |
| G-21 | **Page hash cannot validate a quote.** `pages.text_sha256` covers the whole stored page; the quoted span is not covered, and raw text differs from typed text on hyphenation, ligatures and running heads. | Medium (proposed, not locked) | Verify as a normalised substring test plus the page hash (§4.4). Record the normalisation so a later verifier reproduces it. A span-level guarantee would need character offsets, which are not stored. |

---

## 7. Options considered and rejected

| Option | Verdict | Why |
|---|---|---|
| All-Cloudflare (R2 + D1 + Vectorize) | Rejected | Vectorize has no lexical search, and its filterable string metadata is capped at the **first 64 bytes**, which cannot express page ranges. D1's 10 GB per-database ceiling cannot be raised. With C-01 (≤10 GB) D1 would now *fit* the metadata, but Meilisearch (C-04) cannot run on Workers, so this cannot be a complete Cloudflare-only design regardless. |
| Managed Postgres + pgvector | Rejected | C-02 forbids a non-stdlib client at runtime. Over HTTP (PostgREST) it is workable but adds a paid dependency and loses pgvector ergonomics. At ≤10 GB it is over-provisioned. |
| Meilisearch Cloud | Rejected (default) | From $20/month; the usage-based "Build" plan is $30/month (100K documents, 50K searches, then $0.40/1K searches). A ≤10 GB corpus on a self-hosted VPS costs $0 and keeps copyrighted text local (S-02). Revisit if the VPS becomes unreliable. |
| Elasticsearch / OpenSearch | Rejected | JVM overhead, fuzzy matching is dangerous for a citation system, and C-02 blocks the client. Meilisearch has an exactness ranking rule built in. |
| SQLite FTS5 only, no Meilisearch | Rejected | Viable and was the earlier proposal, but the owner requires Meilisearch (C-04), and Meilisearch's typo tolerance, facets, ranking rules and rebuild-from-source behaviour are a better fit. FTS5 is not needed alongside it. |
| Whole-corpus per document (one Meilisearch doc per book) | Rejected | Loses page-level addressing and makes quoting exact. Pages are the unit (D-07). |
| Corpus replaces the live APIs | Rejected | The owner requires journal sources beyond the corpus to come from the APIs and the existing research mechanism (C-09). The corpus is layer 1, not the whole base. |
| Ingest practice / business-press content into the corpus | Rejected | Licensing, and it would blur the evidence line. Orientation reads such sources ephemerally and separately (D-11, G-07). |
| Make the orientation pass a citable tier | Rejected (default) | Practice content is not academic evidence; citing it as such would break "no invented evidence". If the owner wants practice sources *cited*, that is a separate decision with its own reference type — see Q-09. |

---

## 8. Open questions

| Id | Question | Options | Recommendation |
|---|---|---|---|
| Q-01 | How does a corpus result pass the title gate? | — | **RESOLVED at policy level.** D-10 / B-168: a full-text source is judged on the quoted passage; the title is never sufficient on its own; abstract-only unchanged. **Implementation and the live run are still owed** (G-12, build step 5). |
| Q-02 | What is the de-duplication key for a corpus item? | (a) `doc_id` (book granularity); (b) `doc_id + section_path`; (c) `doc_id + pdf_page` | **(c)** for the "one source cannot fill two dimensions" rule, with **(b)** as the citation identity. Needs a `key_of()` extension that recognises a corpus id prefix. **Reservation (2026-10-30):** a page-level key is unique per page, so the rule stops constraining anything once the source is a book — one book becomes eligible for every dimension. Key (c) is still right for identity; the rule needs a companion cap, which is **Q-16**. |
| Q-03 | What weight does a corpus result carry? | (a) `tier: "official"` → weight 3; (b) explicit `database` entry → weight 2; (c) leave at 1 | **(b)** — the corpus is curated and specialised, comparable to a vetted academic database, not to an official statistics source. |
| Q-04 | Is the corpus single-node (self-hosted) or hosted? | (a) VPS-only + R2 mirror; (b) VPS + R2 + D1 mirror of metadata; (c) fully hosted | **(a)** for now. **(b)** only if the corpus must be queried off-box. |
| Q-05 | Are embeddings wanted, and from which provider? | (a) none (lexical only); (b) Meilisearch hybrid with a local OpenAI-compatible embedder | **(a)** now. Revisit only if lexical recall measurably misses. |
| Q-06 | Citation granularity: page, section, or both? | — | **RESOLVED.** D-14 / B-169: **no locator by default** in APA or Harvard. A locator appears only when the student asks for one, or when the pipeline decides the claim needs one, and that decision is recorded. The page stays in the record either way, so a locator can be produced on request without searching again. The on-request path is still owed in code (G-01, now medium). |
| Q-07 | Corpus subject boundary | — | **RESOLVED.** The pipeline's own 11 subjects (C-08). |
| Q-08 | First document to ingest | — | `D:\SMART BUSINESSWRITER\important for business and RA pipeline-hybrid reasonning agents.pdf` (9.5 MB, arXiv:2610.18861) is already in the workspace and is a natural first test case: it is a real paper with a text layer, a DOI, and known metadata. **Reservation (2026-10-30):** it is a good *smoke test* — it proves the extractor, the hashes and the adapter on the easy path — but it is the wrong document to accept step 1 against, because it has none of the properties the page model was built for (scanned pages, no printed page number, no edition, no ISBN). Step 1 needs a scanned book as well; see Q-14. |
| Q-09 | May practice / business-press sources ever be **cited**? | (a) no, orientation only; (b) yes, with a `reference_type` of "trade article" and its own tier | **(a)** still, and D-15 makes the orientation set broad and free rather than small and paywalled, which reduces the pressure to cite them. **(b)** is a larger change: it needs a reference type, a tier, a citation format and a credibility rule, and it touches the "no invented evidence" line, so it is the owner's call, not a default. |
| Q-12 | Which licence classes may enter a commercial corpus? | (a) CC BY only; (b) CC BY + CC BY-NC-SA with attribution and share-alike; (c) any open licence | **(a) for the v1 harvest**, then widen once the licence handling is built. NC-SA constrains derivatives and commercial use, so an NC-SA textbook in a commercial corpus needs the owner to decide deliberately (G-17). |
| Q-13 | Which orientation sources belong to which pipeline subject? | (a) one global set; (b) a per-subject map | **(b)** — D-15 makes the set topical, so it needs the map. The map is the only new artefact the orientation pass requires, and it is small: eleven subjects, a handful of sources each. |
| Q-10 | Which subject gets corpus coverage first? | (a) spread thinly across all 11; (b) one or two subjects deeply | **(b)** — the corpus earns its keep where the live APIs are thin. Pick 2 subjects, ingest ~100 documents, prove the pipeline end to end, then widen. |
| Q-11 | Which journals enter the corpus, and by what rule? | (a) the ones the pipeline already returns most; (b) the owner's own subscriptions; (c) the highest-cited in the covered subjects | Owner to decide. (b) and (c) can be combined: it sets both the metadata source and the licensing position. |
| Q-14 | Which stream fills the corpus first — the owner's existing book library, or the open-access harvest? | (a) owner's library first; (b) harvest first; (c) both, as separate ingest streams | **(c)**, but the sequencing matters more than the answer: the owner's library is its own ingest stream and **step 1's acceptance runs on a scanned book**, not the arXiv PDF, so the metadata-hard case is exercised before bulk ingest rather than after. As written, the plan risks a corpus that is cheap to fill and irrelevant to the brief. |
| Q-15 | How does re-ingesting a corrected PDF work? | (a) delete and rewrite that `doc_id`'s pages; (b) keep generations and point at the current one | **(b)** if the owner's library will be re-scanned or re-OCR'd, since a deleted generation cannot be compared against; **(a)** otherwise. `pages.doc_version` is in the schema for this; whether it stays in the primary key and whether old generations are pruned is the open part. |
| Q-16 | Should "one source cannot fill two dimensions" carry a per-document cap for the corpus? | (a) no cap — Q-02's page key is enough; (b) cap pages per `doc_id` per paper (2–3); (c) cap the corpus share of any one dimension | **(b)**. Without a cap, the rule protects against duplicate *records* but not against a single textbook quietly supplying every dimension of the paper, which is the diversity failure the rule exists to prevent. The cap is a small change to `retrieve()`'s `exclude` handling. |
| Q-17 | Locators for verbatim quotations, and for sources that have no page? | (a) D-14 as written, no locator ever by default; (b) paraphrase never needs one, a verbatim quote always does; (c) locator whenever the source has one | **(b) and (c) together.** APA 7 requires a page or paragraph locator for a direct quotation, not merely on request, so "no locator by default" is correct for paraphrase (D-13 allows it) and incorrect the moment the paper quotes. Second half: layer-2 records are abstract-only, so they have no page to give — an on-request locator for a non-corpus source cannot be produced. Under "gaps are named, never filled" that needs an explicit rule: the quote is not used, or the gap is named. |

---

## 9. The orientation pass (advisory layer)

**What it is.** Before the main retrieval, the product reads reputable practice and
business-press sources — Harvard Business Review and the like — to learn what the field
currently believes, how the case is usually framed, and what vocabulary the domain uses.
It is the Write Smarter researcher, carried forward.

**Why it is worth having.** The academic layer returns abstracts about a narrow question.
A case like "should a regional grocer vertically integrate its supply chain" is framed
differently in the trade literature than in a journal article, and the trade vocabulary
(shrinkflation, slotting, dark stores) is often what a student recognises. Orientation
widens the queries the retriever issues and gives the plan a sense of the live debate.

**Why it must be separated.** Practice content is not academic evidence. If orientation
output can reach the evidence list, a claim from HBR can be paraphrased into the paper
and read as sourced — the exact thing "no invented evidence" forbids. So orientation is
**advisory only** (D-11, B-168):

| Orientation may | Orientation may not |
|---|---|
| Widen or rewrite the **queries** sent to the retrieval layers | Enter the evidence list |
| Supply framing and vocabulary hints to the plan and the worksheet | Carry a citation or appear in the reference list |
| Suggest which dimensions look relevant for the case | Be quoted in the paper |
| Be cached and reused across runs | Delay or block the retrieval pass |
| Fail silently to a notice | Produce a named gap in the paper |

### 9.1 The source set is topical and free-first (D-15, B-169)

Harvard Business Review is **one candidate, not the anchor**. Two reasons: it cannot
cover every subject, and most of it is paywalled, which makes it slow and gives little
text. The set is chosen by the brief's subject and prefers sources that are **free,
fast and open**.

| Subject | Orientation set (free and open) |
|---|---|
| Management, strategy, operations | McKinsey Insights, BCG Perspectives, Bain Insights, HBR (where readable) |
| Marketing, technology, venture | Sifted, TechCrunch, plus the marketing set |
| Economics, macro, policy | Brookings, PIIE, CEPR, VoxEU, Bruegel, and the World Bank, IMF, OECD, ECB, BIS and Federal Reserve working-paper series |
| Accounting, finance | The finance and macro sets; the central-bank and working-paper series |
| People, research methods | The management set plus the academic open-access set |

This map is the only new artefact the orientation pass needs (Q-13), and it is small:
eleven subjects, a handful of sources each.

**Mechanism sketch.** A new tier in the vetted web registry (`tier: "practice"`,
`academic_fit: "background"`), distinct from `news` and from the academic databases. The
pass runs once per brief, concurrently with the retrieval layers, with its own short
timeout, and writes to a separate cache. It is never merged into the retrieval result
object. Its failure is swallowed and recorded as a notice.

**Risks.** G-13 (leaking into evidence), G-14 (blocking the run), G-15 (paywalls return
teasers only). The separation, the non-blocking design and the advisory framing handle
all three. The free-first set removes most of G-15 at source.

**Open.** Whether practice sources may ever be *cited* rather than only orient — Q-09.

### 9.2 The citable corpus is free too

See §4.5. The harvest sources (OpenAlex content API, DOAJ, NBER, SSRN, RePEc, OpenStax)
are **citable evidence**, not orientation, and they enter layer 1 of the source order
like any other corpus document.

---

## 10. Cost model

At the 10 GB ceiling, self-hosted, all figures verified 2026-10-30 (§12).

| Item | Cost |
|---|---|
| Cloudflare R2 storage, 10 GB | **$0** (10 GB-month free tier) |
| R2 operations | **$0** (1M Class A + 10M Class B free per month) |
| R2 egress | **$0** (free, all storage classes) |
| Meilisearch | **$0** (MIT licence, self-hosted) |
| SQLite | **$0** (stdlib) |
| VPS | already paid |
| **Marginal monthly cost** | **$0** |

Headroom: R2 Standard storage is $0.015/GB-month beyond the free tier, so a corpus that
grows to 30 GB costs about **$0.30/month**. Egress stays free, which is what makes R2
preferable to S3/B2 for this workload.

Comparison points at the same corpus size: Meilisearch Cloud from **$20/month**; managed
Postgres + pgvector from **$25/month**; a hosted vector database in the same band.

**What the $0 does not cover (sizing, not a commitment).** The 10 GB ceiling bounds the
*PDF bytes*, which is what R2 charges for; it does not bound the VPS, and three of the
inputs there are larger than the PDFs: Meilisearch's own guidance is 10× the raw dataset in
disk (§12), the page text is stored twice (SQLite and index), and the OCR pass is CPU-days
or a rental — G-06 calls it the real schedule risk, yet §10 prices it at zero. The
arithmetic at this ceiling: ~5 MB average per PDF gives roughly 2,000 documents; a few
hundred pages each gives a high six-figure page count, which neither SQLite nor Meilisearch
is remotely strained by. The binding resource is VPS disk, not rows, so price the disk
before the ingest, not after.

The orientation pass adds no licence cost: it reads the same public pages the curated web
tier already reads, and ingests nothing into the corpus.

---

## 11. Build sequence

Ordered. Each step has an acceptance condition. Do not start step N+1 until step N's
acceptance condition is met.

| Step | Work | Acceptance |
|---|---|---|
| 1 | Ingest one document end to end: extract pages, write `documents` + `pages`, compute hashes, verify against the PDF by hand. At least one of these must be a **scanned book** (Q-14), so the metadata-hard case is met before bulk ingest. | One book in SQLite; every `pdf_page` row matches the corresponding PDF page; hashes stable on re-run; `printed_page` and `edition` are `NULL` where they are genuinely unrecoverable rather than guessed. |
| 2 | Meilisearch container on the VPS; load that document's pages; configure **settings before** documents. | Search for a phrase from a known page returns that page first, with the right `pdf_page`. |
| 3 | Corpus adapter: `_corpus()` in `sources.py`, `ADAPTERS` entry, `DATABASES` entries in both files, and the corpus placed **first** in the retrieval order (D-09). | `retrieval.retrieve()` returns corpus items in the same shape as OpenAlex items, ahead of the live results; the rest of the pipeline is unchanged. |
| 4 | Resolve Q-02 and Q-03 (key, weight), then seed ~20 real documents — mixed kinds, at least one scanned and one born-digital — before measuring anything. | Two different pages of the same book can each fill a dimension (subject to Q-16's cap); a corpus item ties with an OpenAlex item on equal relevance. **Ordering note:** this step ran after the live gate run in the first version, which would have measured a corpus at weight 1 — structurally unable to win a tie — and drawn the wrong conclusion from the result. |
| 5 | Implement the full-text gate (D-10) and run it live. Record the live-run result against B-168. | A corpus item reaches the `items` list where the old title rule would have dropped it; the abstract-only result set is unchanged on the same briefs, so no layer-2 precision regression is introduced; G-12 closes. |
| 6 | Citation rendering: locator support (G-01), book reference shape (G-02), edition (G-03). | An APA 7 sample and a Harvard sample from a corpus source, with page locator, both reviewed by the owner. |
| 7 | Orientation pass: `practice` tier, advisory-only output, non-blocking, cached, plus the per-subject source map (Q-13). | The run completes with and without the pass; the evidence list and reference list are byte-identical either way; the pass never delays retrieval. |
| 8 | Bulk ingest in the §4.5 harvest order — OpenStax, then the OpenAlex content API filtered by the pipeline's subject filters, then DOAJ, then NBER/SSRN — with the **licence recorded per title** (G-17). OCR pass for scanned documents only; metadata from Open Library (books) and Crossref (journals). | Ingest log complete; every document either `ok` or `ocr`, none silently failed; `metadata_source` **and licence** recorded for every document; no NC-SA title ingested without an owner decision. |
| 9 | R2 mirror: `rclone sync`, nightly, private bucket, custom domain + Cloudflare Access. | A test restore from R2 reproduces the SQLite system of record and rebuilds the Meilisearch index. |
| 10 | Drift check: re-hash PDFs and page text; report mismatches. | Drift sweep reports zero mismatches; a deliberately corrupted file is reported. |

---

## 12. Verified facts and sources

All verified 2026-10-30 unless stated otherwise.

| Fact | Source |
|---|---|
| R2 Standard storage $0.015/GB-month; Infrequent Access $0.01/GB-month with $0.01/GB retrieval and 30-day minimum | <https://developers.cloudflare.com/r2/pricing/> |
| R2 free tier: 10 GB-month storage, 1M Class A, 10M Class B ops/month; egress free on all storage classes | <https://developers.cloudflare.com/r2/pricing/> |
| R2 Class A $4.50/M (writes, lists); Class B $0.36/M (reads) | <https://developers.cloudflare.com/r2/pricing/> |
| R2 storage billed on average peak storage per day over the month | <https://developers.cloudflare.com/r2/pricing/> |
| D1 maximum database size 10 GB (Workers Paid) / 500 MB (Free); **the 10 GB limit cannot be increased** | <https://developers.cloudflare.com/d1/platform/limits/> |
| D1 is single-threaded per database; large migrations must be batched | <https://developers.cloudflare.com/d1/reference/faq/> |
| Vectorize: up to 20M vectors per index, 1536 dimensions at 32-bit; 10KiB metadata per vector; max 10 metadata indexes; string metadata indexed on the **first 64 bytes** | <https://developers.cloudflare.com/changelog/post/2026-08-04-index-capacity-20-million/>, <https://developers.cloudflare.com/vectorize/platform/limits/> |
| Meilisearch is MIT-licensed, self-hostable, needs ≥256 MB RAM as a starting point; storage is disk with memory mapping, not RAM-limited | <https://www.meilisearch.com/docs/resources/self_hosting/overview>, <https://www.meilisearch.com/docs/resources/help/faq> |
| Meilisearch self-host guidance: provision at least 10× the raw dataset in disk; size RAM to the index | <https://www.meilisearch.com/docs/resources/help/faq> |
| Meilisearch limits: ~4.3B documents per index, ~80 TiB index, 65,536 attributes per document, **10 query words default (configurable)**, 1,000 results default | <https://www.meilisearch.com/docs/resources/help/faq> |
| Typo tolerance is on by default; no typo under 5 characters, 1 typo at 5–8, 2 typos at 9+; `enabled`, `disableOnWords`, `disableOnAttributes`, `disableOnNumbers`, `minWordSizeForTypos` | <https://www.meilisearch.com/docs/capabilities/full_text_search/relevancy/typo_tolerance_settings> |
| Changing searchable / filterable / sortable attributes, stop words, synonyms, typo tolerance, embedder config or dictionary triggers a **full reindex** — configure settings before loading documents | <https://www.meilisearch.com/blog/indexing-optimization-guide> |
| Hybrid search (full-text + semantic) is stable; `semanticRatio` tunable; `hybrid.embedder` is mandatory for hybrid and `similar` requests | <https://www.meilisearch.com/docs/changelog/changelog>, <https://www.meilisearch.com/llms.txt> |
| Vector store is built in with a DiskANN backend (experimental `vectorStoreSetting`, binary quantization) | <https://www.meilisearch.com/docs/changelog/changelog> |
| Default maximum payload size 100 MB, raisable when self-hosting; task queue caps at 1M tasks | <https://www.meilisearch.com/blog/indexing-optimization-guide>, <https://www.meilisearch.com/docs/changelog/changelog> |
| Meilisearch Cloud pricing: from $20/month; "Build" usage plan $30/month (100K docs, 50K searches, then $0.40/1K searches and $0.30/1K docs); resource-based XS $18/month + disk (32 GB minimum @ $0.165/GiB) + bandwidth $0.15/GB | <https://www.meilisearch.com/pricing>, <https://www.meilisearch.com/docs/capabilities/platform/billing/pricing_model> |
| OpenAlex serves full text directly: `content.openalex.org/works/{work_id}.pdf` and GROBID XML, filterable with `has_content.pdf:true` and `best_oa_location.license`; free API key, downloads metered against usage; `content_urls` is API-only | <https://help.openalex.org/access/fulltext/> |
| OpenAlex warns: do **not** map work IDs to archive objects via `locations[].pdf_url` — that is the publisher URL and keying off it produces a lossy, inferred match | <https://help.openalex.org/access/fulltext/> |
| OpenStax publishes peer-reviewed, openly licensed business textbooks with free PDF download: Principles of Accounting vol. 1 and 2, Principles of Finance, Principles of Management, Principles of Marketing, Principles of Economics, Business Ethics, Business Law, Entrepreneurship, Organizational Behavior | <https://openstax.org/subjects/business> |
| OpenStax licences are **per title** — CC BY on some (Principles of Finance) and CC BY-NC-SA on others (Principles of Management, Principles of Marketing) | <https://openstax.org/books/principles-management/pages/preface>, <https://openstax.org/details/books/principles-finance-2e> |
| CORE: free API key; ~483M free-to-read full texts with 57M PDFs hosted by CORE; free tier ~1 batch or 5 single requests per 10 s; **systematic PDF harvesting is restricted** and commercial terms need assessment | <https://core.ac.uk/services/api>, <https://core.ac.uk/data>, <https://core.ac.uk/faq> |
| Pipeline: stdlib only at runtime | `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md` §2 rule 5 |
| Pipeline: core frozen (B-079); design lane for additive product work (B-080) | `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md` §2 rules 9–10 |
| Pipeline: the 11 subjects the corpus taxonomy reuses | `business_pipeline_v0.12/business_pipeline/scripts/ui_smoke.py:29` |
| Pipeline: evidence gate, item shape, citation rendering | `src/bp/product/retrieval.py`, `src/bp/product/sources.py`, `src/bp/product/writing.py`, `src/bp/literature.py` (see §5) |
| Pipeline: the layered source order, the full-text gate rule and the advisory orientation pass | `business_pipeline_v0.12/business_pipeline/docs/CONDUCTOR_MANUAL.md` §9, §6.2.3, §6.3.3 — B-168 |

---

## 13. Decision log

Append new rows. Do not edit earlier rows.

| Date | Id | Decision | Decided by |
|---|---|---|---|
| 2026-10-30 | D-01 | Split bytes (R2) from index (VPS: SQLite + Meilisearch) | Model proposal, owner-approved direction (Meilisearch + 10 GB confirmed by owner) |
| 2026-10-30 | D-02 | R2 holds the canonical PDF bytes; VPS holds a working copy | Model proposal |
| 2026-10-30 | D-03 | SQLite is the system of record; Meilisearch is a disposable derived index | Model proposal |
| 2026-10-30 | D-04 | Retrieval unit is one PDF page | Model proposal |
| 2026-10-30 | D-05 | `printed_page` stored separately from `pdf_page`, may be `NULL` | Model proposal |
| 2026-10-30 | D-06 | Page text lives in SQLite, not only in the search index | Model proposal |
| 2026-10-30 | D-07 | Meilisearch indexes pages, not whole books | Model proposal |
| 2026-10-30 | D-08 | Vector/hybrid search deferred pending a lexical-recall test | Model proposal |
| 2026-10-30 | D-09 | The evidence base is layered: corpus → academic APIs → curated web | **Owner** (B-168, recorded in `CONDUCTOR_MANUAL.md` §9) |
| 2026-10-30 | D-10 | The title rejection is discarded for full-text sources; the quoted passage decides | **Owner** (B-168, recorded in `CONDUCTOR_MANUAL.md` §6.2.3, §6.3.3) |
| 2026-10-30 | D-11 | The orientation pass is advisory only and never citable | **Owner**, with the model's segregation safeguard (B-168, recorded in `CONDUCTOR_MANUAL.md` §9) |
| 2026-10-30 | D-12 | The corpus is mixed books and journals, scoped to the pipeline's own subjects | **Owner** |
| 2026-10-30 | D-13 | The evidence rules are relaxed in form, not in substance: paraphrase allowed, metadata gaps recorded not printed, substitution allowed when declared | **Owner** (B-169, recorded in `CONDUCTOR_MANUAL.md` §4) |
| 2026-10-30 | D-14 | Citations carry no page or chapter locator by default; a locator only on request or when the pipeline decides the claim needs one | **Owner** (B-169, recorded in `CONDUCTOR_MANUAL.md` §2) |
| 2026-10-30 | D-15 | The orientation source set is topic-dependent and free-first, not fixed on HBR | **Owner** (B-169, recorded in `CONDUCTOR_MANUAL.md` §9) |
| 2026-10-30 | D-16 | The corpus is harvested from open access (OpenAlex content API, DOAJ, NBER/SSRN/RePEc, OpenStax), not assembled by hand | Model proposal, owner-approved direction |
| 2026-10-31 | D-19 | The corpus is **self-enriching**: it grows from what the pipeline actually asked for, not from a bulk pre-harvest. The live academic APIs stay in the pipeline as layer 2 and become the corpus's **research source** — full text is pulled once, into a quotable page, instead of being re-fetched as an abstract on every run | **Owner** (2026-10-31 instruction: "the database to be self-enriching") |
| 2026-10-31 | D-20 | The corpus is a **demand queue, not a mirror of the API**. The API is extensive but slow, and most of what it holds is never needed. A document enters the corpus because a question kept going unanswered, and rises in priority the more often that comes up | **Owner** (2026-10-31 instruction: the API database "is extensive but very slow and many file is not needed") |
| 2026-10-31 | D-21 | The owner can update the corpus by uploading files **seamlessly, through a separate UI** (the admin page), with no CLI and no approval cycle for the owner's own material. The owner does not wait on the pipeline to harvest what they already have | **Owner** (2026-10-31 instruction: "I can upload files seamlessly, ideally there's a separate UI ... like admin.html") |
| 2026-10-31 | D-22 | Three enrichment paths feed the corpus and all three are first-class: **(1)** the pipeline's own searches and the sources they saw become corpus candidates — including the websites the web tier saw; **(2)** owner uploads; **(3)** the system researches the API databases and possibly websites itself for what it is missing | **Owner** (2026-10-31 instruction, three named paths) |
| 2026-10-31 | D-23 | The pipeline writes its learning log through **one** HTTP route on the admin service (`POST /api/corpus/log`), never by importing `corpus_lib` across the repo boundary, and never as a hard dependency of a paper run | Model proposal, owner-approved direction (D-19, D-22) |
| 2026-10-31 | D-24 | The corpus build ships **two** documents and each is accepted by **rendering it and looking at the pages**. `DATABASE.md` is the execution manual — the exact commands, the schema, the adapter code, the five traps. `corpus-db/WALKTHROUGH.md` is the owner-facing narrative — what you are building, the three ways the corpus fills itself, the build in order as *you do / you see / it means*, what it costs, what it cannot do, and what is still open. The acceptance gate for both is a rendered check, not an XML check | **Owner** (2026-10-31 instruction: "provide an understandable walkthrough to build it") |

---

## 14. Change log

| Date | Change |
|---|---|
| 2026-10-30 | Document created. Captures the first discussion: architecture options for a proprietary PDF corpus, the "bytes vs index" split, R2 vs D1 vs Vectorize vs VPS, the three retrieval-contract traps, and the citation-format gaps. Owner then constrained the corpus to ≤10 GB and required Meilisearch; both were folded in (D-01, and the Meilisearch index design in §4.3). Q-01 remained the blocking item for an end-to-end run. |
| 2026-10-30 | Second pass, after the owner's answers. (1) **D-10 / B-168**: the title rejection is discarded for full-text sources and recorded in `CONDUCTOR_MANUAL.md` §6.2.3 and §6.3.3, with the abstract-only path explicitly unchanged; Q-01 closes at policy level, leaving the code change and the live run as build steps 4 and G-12. (2) **D-09 / B-168**: the source order is layered — corpus first, live academic APIs second, curated web third — recorded in `CONDUCTOR_MANUAL.md` §9; the corpus layer is marked *not yet wired* in §13 so the manual never claims a behaviour the product lacks. (3) **D-11 / B-168**: the orientation pass over practice and business-press sources is recorded as advisory only. (4) The corpus is mixed books and journals and reuses the pipeline's own 11 subject ids as its taxonomy (D-12, C-07, C-08), so the corpus is usable by every shelf. (5) New risks G-12 to G-15, new questions Q-09 to Q-11, a new §9 on the orientation pass, and the build sequence extended to ten steps. The manual change is recorded in `docs/DECISIONS.md` (B-168) and `docs/WORKLOG.md`; no changelog entry and no build bump, because the build number is in flight in the concurrent lane. |
| 2026-10-30 | Third pass, after the owner said the non-negotiables were suffocating the pipeline. (1) **D-13 / B-169**: the evidence rules are relaxed in form, not in substance — paraphrase allowed, only substantive gaps printed, framework substitution allowed when declared and recorded. The finding that matters: the suffocation came from the **manual being stricter than the code**; §6.2.8 already had the model write dimension paragraphs from the items with a validator that refuses any number, citation, link or proper noun not in the items, so the guarantee the rule exists to provide was already enforced. (2) **D-14 / B-169**: no page or chapter locator by default in APA or Harvard; a locator only on request or when the pipeline decides the claim needs one — this resolves Q-06 and downgrades G-01 from high to medium. (3) **D-15 / B-169**: the orientation source set is topic-dependent and free-first rather than fixed on Harvard Business Review, with a per-subject map (§9.1, Q-13). (4) **D-16**: the citable corpus is free as well and can be harvested rather than hand-assembled (§4.5) — OpenAlex now serves full text and GROBID XML directly, alongside DOAJ, NBER, SSRN, RePEc and the peer-reviewed OpenStax business textbooks. (5) New risks G-16 to G-19 (the framework substitution and on-request locator are owed in code; the per-title licence, metered downloads and CORE harvesting permission), new questions Q-12 and Q-13, and build steps 7 and 8 re-specified. The manual change is recorded in `docs/DECISIONS.md` (B-169) and `docs/WORKLOG.md`; §13 of the manual now states exactly which of the four relaxations already ship and which are owed in code. |
| 2026-10-30 | Fourth pass, after an evaluation of the design record against the pipeline code and the cited facts. **Nothing here is binding, and no `D-` row changed status.** (1) **Schema can now hold what the other sections demand.** `documents` gains `licence`, `licence_verified` and `source_url` (G-17 and step 8 require a per-title licence that the table had nowhere to store; `_item()` requires `url`); `pages` gains its own `text_method` (G-05 promises page-level OCR marking) and `doc_version` (re-ingest otherwise orphans rows, Q-15). A connection note records that `PRAGMA foreign_keys = ON` is required per connection or every `REFERENCES` clause is decorative. (2) **Verification demoted out of Meilisearch** (§4.4, G-04, G-21): since D-06 already stores page text in SQLite, exact-quote checking is an `instr()` test, not a ranking problem — proposed, not closed. Adds the normalisation rule and the honest limit that a page hash validates the page, not the quoted span. (3) **`searchableAttributes` reordered** so `text` leads; on a page-level index a leading `title` repeats on every page and rewards title matches over passage matches. (4) **Build order corrected**: Q-02/Q-03 and a ~20-document seed set now precede the live gate run, because measuring a corpus at weight 1 cannot show whether the corpus works; step 1's acceptance now requires a scanned book, and step 5's requires the abstract-only result set to be unchanged. (5) **Purpose tension named** in §1 and carried as Q-14: the design's stated driver is the owner's own books while the sequenced harvest is open-access journals and one arXiv PDF. (6) New questions Q-14 to Q-17 (ingest stream, re-ingest, per-document page cap, quoted-material locators), a reservation appended to Q-02, new risks G-20 (Meilisearch availability and key exposure) and G-21 (page hash vs quote), and a sizing note under §10 that separates the R2 ceiling from VPS disk and OCR. |
| 2026-10-31 | Fifth pass, after the owner's instruction to make the database **self-enriching** and to update it by uploading new files. (1) **D-19 to D-23** record the new shape: the corpus grows from what the pipeline actually asked for (D-19); it is a demand queue rather than a mirror of the API (D-20); the owner updates it seamlessly through a separate admin UI with no CLI and no approval cycle for their own material (D-21); the three enrichment paths — the pipeline's own searches and the sources they saw including websites, owner uploads, and the system's own research on the API databases and possibly websites — are all first-class (D-22); and the pipeline writes its learning log through one HTTP route rather than importing `corpus_lib` across the repo boundary (D-23). **No earlier `D-` row changed status**, and D-09's layering is untouched: the corpus is layer 1, the live APIs remain layer 2, and the corpus does not replace them. (2) The manual `DATABASE.md` was rewritten around the three enrichment paths and the build order that makes the learning loop real (the adapter must be in before the live gate can measure anything). (3) Four defects in the existing corpus build tools were found by running the code, not by reading it, and fixed: `days_ago()` raised `NameError` because `timedelta` was never imported; the 30-day window compared the stored `...T...Z` timestamps against SQLite's `datetime('now', ?)`, whose space separator sorts *below* 'T', so a row that had expired was still counted as inside the window; the admin service bound the name `handle` to a file object inside `do_GET`, shadowing the module's `handle()` function, so every API GET raised `UnboundLocalError` and the admin page could not load its data; and the admin service dropped the query string, so `?status=all` and `?limit=` were silently ignored and the enrichment queue showed only `new`. (4) Two gaps were closed so the manual describes working code: `POST /api/corpus/log` now exists as the pipeline's single write path, and `corpus_lib.record_web_source()` now records what the web tier saw into the `web_sources` table, which until then had no writer at all. (5) `corpus-db/build/test_corpus_build.py` is new: 15 tests, stdlib only, each pinning one of these behaviours against a throwaway database, so none of them can silently return. (6) `stats()["bytes"]` reported a page count under a key that claims bytes; it now reports the real size on disk. (7) The DOCX builder gained `--header` and `--subtitle`, because a corpus manual rendered with the conductor manual's running header was wrong on every page; the conductor manual's own output is unchanged. |

| 2026-10-31 | Sixth pass, after the owner asked for **an understandable walkthrough to build it**. **(1) D-24**: the corpus build now ships two documents — `DATABASE.md`, the execution manual, and `corpus-db/WALKTHROUGH.md`, the owner-facing narrative (what you are building, the three ways the corpus fills itself, the build in order as *you do / you see / it means*, what it costs, what it cannot do, what is still open). Both have Word copies. **(2) The acceptance gate for the corpus documents became a rendered check.** Rebuilding `DATABASE.docx` and rendering it through Word exposed two defects in the shared renderer that no XML check could see: table columns were sized in proportion to the column's total character count, so a short-label column was squeezed and Word broke its content mid-word (`sources.py:4` on one line, `96` on the next — no longer a file reference); and the inline pattern required a non-space before the opening `*`, so `*why*` printed its asterisks instead of being emphasis. Both are fixed in `business_pipeline_v0.12/business_pipeline/scripts/build_manual_docx.py` and pinned by `tests/test_manual_docx.py` (B-171). The corpus documents are now checked by `corpus-db/build/verify_manual_docx.py`, which uses the renderer's own parser as the oracle, and by looking at the rendered pages. **(3) The build tools were exercised rather than only read.** The 15 regression tests pass; the admin service was started and its routes answered (`/`, `/api/corpus/stats`, `/api/corpus/candidates?status=all`, `/api/corpus/gaps`), and a real PDF was uploaded through `POST /api/corpus/upload` against a throwaway copy of the database — it returned `ingested`, the upload row was recorded, and the page count rose by one. **(4) Nothing else moved.** No `D-` row changed status; D-09's layering, D-19's self-enrichment and the licence gate are untouched, and the corpus is still not wired into the pipeline — Step 8 of `DATABASE.md` is still owed. |

---

## 15. Recovery note (2026-10-31)

**This section is a record of damage and an open gap. It is not a decision, and nothing in it
changes a `D-` row.**

### 15.1 What happened

On **2026-10-31 at 03:02:11 +0800**, `corpus-db/CORPUS_DB.md` was overwritten with a 730-byte
payload. The file had been 764 lines; what survived on disk was its **last ten lines only**,
re-rendered with line-number prefixes. The file was untracked in git at that moment, so the
damage was not caught by a diff.

### 15.2 What was restored, and from where

This document is now the content of git blob `a97402ee84e870896ca71a63242651989d05c232`
(69,327 bytes, 677 lines), committed in `df5cdcc` ("untracked files on cline checkpoint",
2026-10-30 18:14:50 +0800). That is the **fourth pass** recorded in §14 — the newest version
that survives anywhere. It was cross-checked against an independent replay of the session-log
write and edit history (write of 44,595 chars + 13 edits); the replay reconstructs an earlier
state, and the git blob is the later of the two, so the git blob wins.

The restored content is complete and internally consistent: C-01…C-09, S-01…S-04,
D-01…D-16, G-01…G-21, Q-01…Q-17, §4.1–§4.5, §5.1–§5.4, §6, §7, §9, §10, §11, §12, §13, §14.

### 15.3 The gap that could not be closed

A **fifth-pass revision existed** and is **not recoverable in full**. It was 764 lines and
added at least `D-17`, `D-18` and `Q-19`, plus three schema columns (`added_by`,
`enrichen_at`, `owner_approved_at`) that the restored §4.2 schema does not carry.

Where it was checked and not found:

| Store | Result |
|---|---|
| Git (all refs, all 3,799 blobs) | Only `a168c438` (58,191 bytes) and `a97402ee` (69,327 bytes) exist. No 764-line blob. |
| VS Code local history (`%APPDATA%\Code\User\History`, 587 folders) | No entry for `CORPUS_DB.md`. |
| Cline session logs (`%USERPROFILE%\.cline\data\sessions\*`) | Three most recent sessions checked; no `D-17`/`D-18`/`Q-19` text. |
| MiniMax Code session logs (`.minimax\v2\sessions`, 10,273 files swept) | The write/edit history for this file was recovered in full; the newest write is the 44,595-char one, not the 764-line revision. |

**What survives of it, verbatim** — the last ten lines, saved at
`corpus-db/_recovery/RECOVERED_TAIL_755-764.txt`:

> 755:    `added_by` is cleared or anonymised, and the document enters the public Meilisearch index.
> 756: 2. **Explicit owner tag:** the owner, reviewing the ingest log, marks the upload as citable
> 757:    (`enrichen_at` timestamp set, `owner_approved_at` populated). Same flip.
> 758:
> 759: **What is still open (Q-19):** whether an upload that is accepted *for use in a paper* but is
> 760: *not* a model-answer-tagged paper still qualifies for enrichment, and what copyright check
> 761: is performed before a cross-student reuse (G-07 protects the R2 bucket, but the licence of a
> 762: student-uploaded PDF is rarely recoverable — `licence` is `NULL` and `licence_verified = 0`
> 763: by default).

**And from `docs/CONTINUATION_NOTE.md` line 7**, which cites the destroyed revision by ID:

> D-17 (sha256+DOI dedup), D-18 (student-upload private / owner-mediated enrichment),
> Q-19 (open: non-model-answer upload qualification + copyright check),
> schema (`source_kind`, `added_by`, `licence`, `licence_verified`).

### 15.4 What this means before you build

- **D-17, D-18 and Q-19 are named but not written down.** Their one-line summaries are the
  most that exists. Do not reconstruct their text from these summaries — that would be
  inventing a decision.
- **The student-upload path (D-18) is the part most affected.** The restored §4.2 schema has
  no `added_by`, `enrichen_at` or `owner_approved_at`, so a build that follows §4.2 as
  written **cannot represent a private student upload flipping to citable**. If you are
  building the upload path at all, these three columns are needed and D-18 must be re-decided
  or reconstructed with the owner.
- **The three options already discussed** (A = corpus scope expansion for the written-analysis
  assignment sections; B = a separate computation-verification layer for the modelling and
  quantitative sections; C = both with named exclusions) live in `docs/CONTINUATION_NOTE.md`
  lines 14–15, not here, and were never decided.
- **Q-19 is an owner decision**, and `CONTINUATION_NOTE.md` line 15 makes it a precondition:
  *"Before any redesign action: resolve Q-19 … confirm target (HANDOFF.md vs CORPUS_DB.md);
  confirm option (A/B/C)."*

### 15.5 Guard against a repeat

This file is untracked in git, which is why a 730-byte destructive overwrite went unnoticed.
**Commit it.** `git add corpus-db/CORPUS_DB.md` — it is outside the pipeline repo, so C-06 does
not trigger the tests + CHANGELOG + WORKLOG + B-number gate for it; but a plain commit gives
the next revision a recoverable ancestor.

