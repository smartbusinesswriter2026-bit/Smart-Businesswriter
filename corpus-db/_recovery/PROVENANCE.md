# Recovery provenance — corpus-db/CORPUS_DB.md

Date of recovery: **2026-10-31**. Owner of the file: Butch Chukoy. Recovered by a MiniMax Code
session at the owner's request ("recall all the notes and discussions about building our database").

## The damage

`corpus-db/CORPUS_DB.md` was overwritten at **2026-10-31 03:02:11 +0800** with a 730-byte
payload. The file had been 764 lines; only its last ten lines survived, re-rendered with
line-number prefixes. The file was untracked in git at the time, so nothing flagged the
overwrite.

## The restored version

`corpus-db/CORPUS_DB.md` now holds git blob
`a97402ee84e870896ca71a63242651989d05c232` (69,327 bytes, 677 lines) from commit
`df5cdcc00de57f17338b0908b6cb3f94387ce81a` ("untracked files on cline checkpoint",
2026-10-30 18:14:50 +0800), plus the §15 recovery note (the file is now 763 lines).

Independent cross-check: the MiniMax Code session logs under
`%USERPROFILE%\.minimax\v2\sessions\2026\10\29\21-51-40-541-session_...` hold the full
write/edit history of this file — one write of 31,316 chars, one write of 44,595 chars, and
13 `edit` operations. Replaying those 13 edits onto the 44,595-char write reproduces an
**earlier** state than the git blob, so the git blob is authoritative. The replay is the
reason the recovery is a *restore*, not a guess: two independent sources agree on the
content up to the point where git is newer.

## Why this directory exists

Two files, and only two, are kept here:

- `RECOVERED_TAIL_755-764.txt` — the verbatim surviving fragment of the destroyed 764-line
  fifth-pass revision, with its provenance and the stores it was checked against.
- `PROVENANCE.md` — this file.

Everything else that was extracted during the search (candidate blobs, replayed writes,
per-edit diffs) was scratch and has been removed.

## The gap

The fifth-pass revision added **D-17** (sha256+DOI dedup), **D-18** (student-upload private /
owner-mediated enrichment) and **Q-19** (open: non-model-answer upload qualification +
copyright check), plus three schema columns — `added_by`, `enrichen_at`, `owner_approved_at` —
that the restored §4.2 schema does not carry.

It was searched for and **not found** in: all git refs and all 3,799 blobs in the object
database; VS Code local history (587 folders, no entry for this path); the Cline session logs
(`%USERPROFILE%\.cline\data\sessions`); and 10,273 files swept across
`%USERPROFILE%\.minimax`.

**Do not reconstruct D-17 / D-18 / Q-19 from their one-line summaries.** Summaries are in
`business_pipeline_v0.12/business_pipeline/docs/CONTINUATION_NOTE.md` line 7; the surviving
tail is in `RECOVERED_TAIL_755-764.txt`. Their full text is an open item for the owner.

## Related file

`corpus-db/SEARCH_KEYWORDS_BY_SUBJECT.md` — intact, 283 lines, and references this design
record at §4.5. It was not damaged.
