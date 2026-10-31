-- corpus-db/build/schema.sql
-- The corpus database schema. Applied with:
--     python corpus-db/build/corpus_lib.py --init
--
-- Three tables hold the corpus itself:
--   documents  one row per book or article. This is the CITATION unit.
--   pages      one row per PDF page. This is the RETRIEVAL and QUOTE unit.
--   ingest_log an audit of every ingest, for replay and for the drift check.
--
-- Five more tables make the corpus SELF-ENRICHING. They record what the pipeline
-- asked for, what it was given, and what is still missing:
--   search_log    every retrieval the pipeline ran, and how the corpus answered it
--   seen_sources  every source a search saw, used or not
--   candidates    the enrichment queue: what to pull full text for, and why
--   uploads       files the owner uploaded through the admin UI
--   web_sources   the rolling record of what the web tier saw
--
-- Rule: a value that cannot be read is NULL. Never a guess.

-- ── the corpus ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
  doc_id           TEXT PRIMARY KEY,      -- stable internal id, e.g. 'bk-1a2b3c4d5e6f'
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
  subject          TEXT,                  -- the pipeline's subject id
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

CREATE TABLE IF NOT EXISTS pages (
  doc_id       TEXT NOT NULL REFERENCES documents(doc_id),
  doc_version  INTEGER NOT NULL DEFAULT 1,  -- which ingest generation this row belongs to
  pdf_page     INTEGER NOT NULL,          -- 1-based index into the PDF
  printed_page TEXT,                      -- NULL when not recoverable
  section_path TEXT,                      -- e.g. 'Chapter 4 > Competitive Dynamics'
  text         TEXT NOT NULL,
  text_sha256  TEXT NOT NULL,
  chars        INTEGER NOT NULL,
  text_method  TEXT NOT NULL DEFAULT 'pdf_text_layer',  -- per page
  PRIMARY KEY (doc_id, doc_version, pdf_page)
);
CREATE INDEX IF NOT EXISTS idx_pages_doc ON pages(doc_id);
CREATE INDEX IF NOT EXISTS idx_pages_subject ON documents(subject);

CREATE TABLE IF NOT EXISTS ingest_log (
  ingested_at TEXT NOT NULL,
  doc_id      TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  method      TEXT NOT NULL,
  pages       INTEGER NOT NULL,
  status      TEXT NOT NULL               -- 'ok' | 'ocr' | 'failed' | 'skipped'
);

-- ── the learning loop ───────────────────────────────────────────────────────

-- Every retrieval the pipeline ran. This is the signal that drives enrichment:
-- a search the corpus could not answer is a gap, and a repeated gap is a
-- request for a document the corpus does not have.
CREATE TABLE IF NOT EXISTS search_log (
  search_id     TEXT PRIMARY KEY,
  searched_at   TEXT NOT NULL,
  query         TEXT NOT NULL,
  subject       TEXT,
  dimension     TEXT,
  case_id       TEXT,
  corpus_hits   INTEGER NOT NULL DEFAULT 0,
  live_hits     INTEGER NOT NULL DEFAULT 0,
  corpus_status TEXT NOT NULL DEFAULT 'ok'   -- 'ok' | 'down'
);
CREATE INDEX IF NOT EXISTS idx_search_time ON search_log(searched_at);
CREATE INDEX IF NOT EXISTS idx_search_subject ON search_log(subject);

-- Every source a search saw, whether or not the paper used it. A source that
-- keeps appearing is a candidate for the corpus.
CREATE TABLE IF NOT EXISTS seen_sources (
  seen_id   TEXT PRIMARY KEY,
  search_id TEXT NOT NULL REFERENCES search_log(search_id),
  source    TEXT NOT NULL,                  -- 'openalex' | 'crossref' | 'doaj' | 'web'
  title     TEXT,
  doi       TEXT,
  url       TEXT,
  venue     TEXT,
  year      INTEGER,
  abstract  TEXT,
  used      INTEGER NOT NULL DEFAULT 0,     -- 1 when the paper cited it
  doc_id    TEXT                            -- set once it becomes a corpus document
);
CREATE INDEX IF NOT EXISTS idx_seen_search ON seen_sources(search_id);
CREATE INDEX IF NOT EXISTS idx_seen_doi ON seen_sources(doi);

-- The enrichment queue. Nothing is here because someone listed it. A candidate
-- exists because users kept searching for something and the corpus could not
-- answer, and the more often it comes up the higher it rises.
CREATE TABLE IF NOT EXISTS candidates (
  candidate_id  TEXT PRIMARY KEY,
  first_seen_at TEXT NOT NULL,
  last_seen_at  TEXT NOT NULL,
  title         TEXT,
  doi           TEXT,
  url           TEXT,
  source        TEXT,
  year          INTEGER,
  venue         TEXT,
  seen_count    INTEGER NOT NULL DEFAULT 1,
  priority      INTEGER NOT NULL DEFAULT 0,  -- seen_count x subject need
  status        TEXT NOT NULL DEFAULT 'new',  -- new | fetching | fetched | ingested | rejected | needs_decision
  reason        TEXT,
  doc_id        TEXT
);
CREATE INDEX IF NOT EXISTS idx_cand_status ON candidates(status, priority);

-- Files the owner uploaded through the admin UI.
CREATE TABLE IF NOT EXISTS uploads (
  upload_id   TEXT PRIMARY KEY,
  uploaded_at TEXT NOT NULL,
  filename    TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  bytes       INTEGER NOT NULL,
  status      TEXT NOT NULL,                -- pending | ingested | failed | duplicate
  doc_id      TEXT,
  message     TEXT
);

-- The web tier's sites, rolling. Not the corpus: the corpus is books and papers.
-- This is the record of what the web layer saw, so the same site is not
-- fetched and re-read for every student.
CREATE TABLE IF NOT EXISTS web_sources (
  url           TEXT PRIMARY KEY,
  first_seen_at TEXT NOT NULL,
  last_seen_at  TEXT NOT NULL,
  title         TEXT,
  domain        TEXT,
  summary       TEXT,
  seen_count    INTEGER NOT NULL DEFAULT 1,
  snapshot      TEXT
);
