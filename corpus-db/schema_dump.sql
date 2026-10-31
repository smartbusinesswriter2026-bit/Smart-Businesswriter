CREATE TABLE documents (
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
, work_key TEXT)
CREATE TABLE pages (
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
)
CREATE INDEX idx_pages_doc ON pages(doc_id)
CREATE INDEX idx_pages_subject ON documents(subject)
CREATE TABLE ingest_log (
  ingested_at TEXT NOT NULL,
  doc_id      TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  method      TEXT NOT NULL,
  pages       INTEGER NOT NULL,
  status      TEXT NOT NULL               -- 'ok' | 'ocr' | 'failed' | 'skipped'
, reason TEXT)
CREATE TABLE search_log (
  search_id     TEXT PRIMARY KEY,
  searched_at   TEXT NOT NULL,
  query         TEXT NOT NULL,
  subject       TEXT,
  dimension     TEXT,
  case_id       TEXT,
  corpus_hits   INTEGER NOT NULL DEFAULT 0,
  live_hits     INTEGER NOT NULL DEFAULT 0,
  corpus_status TEXT NOT NULL DEFAULT 'ok'   -- 'ok' | 'down'
)
CREATE INDEX idx_search_time ON search_log(searched_at)
CREATE INDEX idx_search_subject ON search_log(subject)
CREATE TABLE seen_sources (
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
)
CREATE INDEX idx_seen_search ON seen_sources(search_id)
CREATE INDEX idx_seen_doi ON seen_sources(doi)
CREATE TABLE candidates (
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
, work_key TEXT)
CREATE INDEX idx_cand_status ON candidates(status, priority)
CREATE TABLE uploads (
  upload_id   TEXT PRIMARY KEY,
  uploaded_at TEXT NOT NULL,
  filename    TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  bytes       INTEGER NOT NULL,
  status      TEXT NOT NULL,                -- pending | ingested | failed | duplicate
  doc_id      TEXT,
  message     TEXT
)
CREATE TABLE web_sources (
  url           TEXT PRIMARY KEY,
  first_seen_at TEXT NOT NULL,
  last_seen_at  TEXT NOT NULL,
  title         TEXT,
  domain        TEXT,
  summary       TEXT,
  seen_count    INTEGER NOT NULL DEFAULT 1,
  snapshot      TEXT
)
CREATE UNIQUE INDEX idx_documents_sha256 ON documents(sha256)
CREATE UNIQUE INDEX idx_documents_work_key ON documents(work_key)
CREATE UNIQUE INDEX idx_candidates_work_key ON candidates(work_key)