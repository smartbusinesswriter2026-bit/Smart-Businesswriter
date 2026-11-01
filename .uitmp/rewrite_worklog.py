"""Replace the ninth-pass change-log row in corpus-db/CORPUS_DB.md.

The row was written when R2 could not be enabled. It is now replaced with the
finished truth: the bucket is live, the bytes are in it, the restore passed.
"""
import io
import os

PATH = r"D:\SMART BUSINESSWRITER\corpus-db\CORPUS_DB.md"

ROW = (
    "| 2026-11-01 | Ninth pass, after the owner commissioned **Step 13 of `DATABASE.md`** \u2014 the off-site copy of the corpus bytes on Cloudflare R2. "
    "**The lane is built, the bucket is live, the bytes are in it, and the restore is proven.** "
    "**(1) What was built.** `corpus-db/build/r2_plan.py` (the plan, the hash check, the record repair, the acceptance phrase, the index comparison), "
    "`rclone_sync.ps1` (the nightly sync), `rclone_restore_test.ps1` (the test restore), `r2_credentials.py` (the rclone remote), "
    "`finish_r2_setup.ps1` (the one command that finishes the setup), `register_r2_sync_task.ps1` (the Windows task), "
    "`R2_SETUP.md` (the owner's steps) and `rclone_corpus.env.example` (the secrets template). "
    "rclone v1.75.2 was installed under `corpus-db/build/tools/` after its published SHA-256 was checked; it is gitignored, and it is an operations tool, never a runtime dependency (C-02). "
    "**(2) Two new decisions.** **D-27**: the sync's file list is **the corpus record** (`documents.local_path`), not a directory \u2014 `corpus-db/pdfs/` holds one enrichment working copy, while the 19 documents' bytes live in the owner's own library folder and are recorded by path, never copied, so the 1.7 GB is not duplicated on disk; "
    "the R2 key is the file's own name under a `pdfs/` prefix, written back into `documents.r2_key` after a successful run. "
    "**D-28**: the sync **fails closed** \u2014 it corrects a path whose spelling differs from the file on disk and logs the correction, and it refuses to finish, without writing `r2_key`, when the bucket does not hold exactly the record's documents. "
    "**(3) A defect the run found; the record now names it.** `documents.local_path` for `bk-3861b611f0e0` read `Exploring_business.pdf` while the file on disk is `exploring_business.pdf`. "
    "Windows resolves both to one file, so nothing looked wrong; rclone's filter is case-sensitive, so the first sync moved **18 of 19** documents and said nothing about the nineteenth. "
    "The plan now resolves the on-disk name, the sync repairs the record's spelling and logs it, and the record has been corrected in place. "
    "**(4) The bucket.** The owner enabled R2 and created the bucket `smart-business-writer-corpus` (location APAC, storage class Standard). "
    "It is private, and that was **checked, not assumed**: the `r2.dev` managed domain reads `enabled: false` and there are no custom domains. "
    "The token is an Account API token with **Object Read & Write**, scoped to that one bucket. "
    "Two facts worth keeping: the connected Cloudflare app holds R2 **read** but not **write** scope, so it cannot create a bucket; "
    "and a bucket-scoped token cannot `ListBuckets` (403 `AccessDenied`), so every check probes the bucket itself. "
    "**(5) The sync ran for real.** 19 documents, 624.663 MiB, uploaded in 22 s at ~29 MiB/s; the mirror check reported 19 objects for 19 documents, none missing, no size mismatch; "
    "`documents.r2_key` was written for all 19. "
    "**(6) The restore test passed against the real bucket.** 19 of 19 restored files match `documents.sha256`; "
    "the index rebuilt from the restored record \u2014 on port 7701, in its own data directory, the live index untouched \u2014 answers the known phrase with the page the record names (`bk-11289bf8c3b8`, page 7), and the live index answers the same. "
    "The report is `corpus-db/test_restore/restore_report.md`. The nightly job (`SmartBusinessWriter Corpus R2 Sync`, 02:00) now has real credentials and runs unattended. "
    "**(7) One security note, and it is the owner's to act on.** The Access Key ID and Secret Access Key were pasted into a chat window. "
    "The secrets file is gitignored and the key was never committed, but **a key that has been in a transcript is a key that must be treated as exposed**: "
    "the owner should mint a replacement token, put the new key in `corpus-db/build/_secrets/rclone_corpus.env`, and revoke the pasted one in the dashboard. "
    "The nightly job fails loudly if the old key is revoked and the file is not updated. "
    "**(8) Two gaps are named, not filled.** The live index holds 6,705 documents against the record's 6,704 pages: "
    "the extra 97 are the 96 pages of five documents the record does not currently mark `enrichen_at`, plus `bk-722dae144926` page 1 \u2014 a document the record does not have at all. "
    "A rebuild from the record holds 6,608 pages. The index is disposable and the record is the truth (D-03); the live index was **not** emptied, because that is the owner's call. "
    "And two Meilisearch instances are listening on 127.0.0.1:7700 (`corpus-db/meili`, which holds the index, and `corpus-state/meili`, which holds none) \u2014 the restore test uses port 7701 and cannot disturb either. "
    "**(9) Deviations from `DATABASE.md`.** The source is the corpus record rather than `corpus-db/pdfs/` (D-27); "
    "the access path is a bucket-scoped API token over the S3 endpoint rather than a custom domain with Cloudflare Access, because the account has no zone to attach one to \u2014 "
    "the manual allows either that or presigned URLs, and a presigned URL for any single object can be produced on demand with `rclone link`; "
    "and the nightly job is a Windows scheduled task rather than a VPS cron, because the corpus currently lives on this machine. "
    "**Nothing else moved.** No earlier `D-` row changed status; the pipeline surface did not change, so no pipeline WORKLOG entry, CHANGELOG entry or B-number was needed (C-06). |"
)

with io.open(PATH, "r", encoding="utf-8") as handle:
    lines = handle.read().split("\n")

replaced = 0
for index, line in enumerate(lines):
    if line.startswith("| 2026-11-01 | Ninth pass,"):
        lines[index] = ROW
        replaced += 1
if replaced != 1:
    raise SystemExit("expected exactly one ninth-pass row, found %d" % replaced)

with io.open(PATH, "w", encoding="utf-8", newline="") as handle:
    handle.write("\n".join(lines))
print("ninth-pass row rewritten")
