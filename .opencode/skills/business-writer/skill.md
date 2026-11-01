# Skill: business-writer

Auto-loaded project skill for the Smart Business Writer corpus pipeline.
Provides context about the conductor manual, corpus build rules, and agent
division so any session starts already briefed on project conventions.

## 1. What this project does

The Smart Business Writer builds a page-exact proprietary PDF evidence corpus
(SQLite + Meilisearch + Cloudflare R2) and wires it into a business-writer
pipeline as layer 1 retrieval (searched first, fast, no API calls). Live journal
APIs (OpenAlex/DOAJ/Semantic Scholar) are layer 2; curated web is layer 3.

## 2. Division of responsibility

- **Chat (you)**: owns the decision, thesis, framework stack, computation blocks,
  paper plan, and the export gate.
- **Researcher agent**: corpus search, enrichment, ingestion, R2 sync, proof
  counts. Never invents evidence; names gaps.
- **Verifier agent**: verifies claims against recorded pages, checks citation
  completeness, enforces "no invented evidence."
- **Writer / renderer**: only format. Never decide headings, sections, or order.
  Never invent numbers, citations, or sources.

## 3. Non-negotiable rules (never skip)

1. No invented evidence, sources, numbers or citations.
2. Gaps are named, never filled.
3. Student inputs stay student inputs.
4. No silent framework substitution.
5. Computations come from the frozen core (`src/bp/**`).
6. A paper never contains template instructions.
7. Export is blocked when the paper is incomplete.
8. Corpus R2 bucket stays private — no `r2.dev` subdomain.

## 4. Corpus quick facts (current, from `corpus.sqlite`)

- Documents: 159
- Pages indexed: 27,791
- Size: 1.59 GB of 8 GB limit (2 GB reserved for later enrichment)
- Meilisearch: running on `http://127.0.0.1:7700`
- R2 bucket: `smart-business-writer-corpus` (~161 PDFs)

## 5. Key paths

| Item | Path |
|---|---|
| Corpus DB | `D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite` |
| Build scripts | `D:\SMART BUSINESSWRITER\corpus-db\build\corpus_lib.py` |
| Keyword enricher | `D:\SMART BUSINESSWRITER\corpus-db\build\bulk_research_keywords.py` |
| R2 binary | `D:\R2 REMOTE\rclone-v1.75.2-windows-amd64\rclone.exe` |
| R2 remote | `corpus-r2` → bucket `smart-business-writer-corpus` |
| Local API | `http://localhost:4001/api/sources/search` |
| Conductor manual | `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\CONDUCTOR_MANUAL.md` |
| Corpus build manual | `D:\SMART BUSINESSWRITER\DATABASE.md` |
| Handoff notes | `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\HANDOFF.md` |

## 6. Useful commands (cmd.exe for spaced paths)

```cmd
:: Check corpus counts
python -c "import sqlite3; c=sqlite3.connect(r'D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite'); print('Documents:', c.execute('SELECT count(*) FROM documents').fetchone()[0]); print('Pages:', c.execute('SELECT count(*) FROM pages').fetchone()[0])"

:: Run keyword enrichment (local API, unfriendly delays)
cmd /c "cd /d D:\SMART BUSINESSWRITER\corpus-db\build && python bulk_research_keywords.py C:\Users\Roderick\Downloads\SEARCH_KEYWORDS_BY_SUBJECT.docx 3"

:: Re-index Meilisearch
python corpus-db/build/corpus_lib.py --index

:: Sync PDFs to R2 (after ingesting new ones)
cmd /c "cd /d D:\R2 REMOTE\rclone-v1.75.2-windows-amd64 && rclone.exe sync D:\SMART BUSINESSWRITER\DATABASE corpus-r2:smart-business-writer-corpus/database-backup"
```

## 7. Proof format

When reporting corpus state, always give exact counts from a command — never
estimates. Use `SELECT count(*) FROM documents` / `pages`, sum file sizes for
GB, and `rclone lsf | find /c /v ""` for R2 object counts.