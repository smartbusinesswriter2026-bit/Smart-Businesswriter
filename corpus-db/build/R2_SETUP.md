# R2 setup — R2 is on; one step left, then one command

The off-site copy of the corpus PDF bytes (DATABASE.md step 13). The scripts are
written, tested and scheduled, and **R2 is enabled on the account**: the API
answers, and the bucket list is empty.

## What is left

**1. The bucket.** Two ways:

- *In the dashboard* (fastest): R2 → **Create bucket** → name
  `smart-business-writer-corpus` → location **Automatic** → storage class
  **Standard** → Create.
- *By me*, once the token exists: the S3 endpoint can create the bucket, and
  `finish_r2_setup.ps1` does it. The connected Cloudflare app cannot — it
  holds R2 **read** but not **write** scope, so the bucket-create call is
  refused with "not granted a scope this endpoint accepts".

**2. The API token.** R2 → **Manage R2 API Tokens → Create Account API token**:

| Setting | Value |
|---|---|
| Permission | **Object Read & Write** |
| Bucket | `smart-business-writer-corpus` only |
| TTL | the longest you are comfortable with |

The dashboard shows an **Access Key ID** and a **Secret Access Key**.

**3. The two values in the secrets file.** `corpus-db\build\_secrets\rclone_corpus.env`
already has the account id and the bucket filled in; two lines are left:

```
R2_ACCESS_KEY_ID=<the Access Key ID>
R2_SECRET_ACCESS_KEY=<the Secret Access Key>
```

The `_secrets` folder is gitignored. **Do not paste the key into a chat
window** — put it in the file.

The same file also accepts `R2_API_TOKEN_ID` and `R2_API_TOKEN_VALUE` instead
of the pair above; the script then derives the S3 secret as the SHA-256 of the
token value, which is what Cloudflare's own recipe says to do.

## Then one command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\finish_r2_setup.ps1
```

It writes the rclone remote, creates the bucket if it is not there, uploads
the 19 documents (625 MB), checks that the bucket holds exactly the record,
then proves it: every restored file is hashed against `documents.sha256`, a
search index is rebuilt from the restored record on its own port, and both
indexes are asked the same question. The report lands in
`corpus-db\test_restore\restore_report.md`.

## The nightly job

Already registered on this machine:

| | |
|---|---|
| Task | `SmartBusinessWriter Corpus R2 Sync` |
| When | every night at 02:00 |
| Runs | `corpus-db\build\rclone_sync.ps1` |
| Log | `corpus-db\build\_logs\rclone_sync.log` |
| Re-register | `powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\register_r2_sync_task.ps1` |
| Remove | the same command with `-Remove` |

Until the credentials exist the job stops with a named line in the log
(`no usable R2 credentials`) and moves nothing. It never half-finishes.

## What this lane does and does not do

- It puts **PDF bytes** in R2. Not `corpus.sqlite`, not the Meilisearch data
  directory, not the build artefacts. The database is the system of record and
  stays on this machine; the search index is disposable and rebuildable.
- It is **one way**: local to R2. `rclone sync` mirrors the record, so a
  document that leaves the record leaves the bucket on the next run, and an
  object the record does not name is removed and logged.
- It backs up **the corpus**: the 19 documents the record names. The other
  275 files in `D:\SMART BUSINESSWRITER\DATABASE` are not in the record yet,
  so they are not in the bucket. That gap is deliberate and named — a
  harvested document enters the bucket the night it enters the record.
- The bucket is reached through the **S3 endpoint** with a bucket-scoped
  token, never through an `r2.dev` subdomain — that subdomain is a public URL
  and would expose copyrighted text (G-07). A presigned URL for any single
  object can be produced on demand with `rclone link`.
- `rclone` is a build and operations tool (C-02). The pipeline runtime never
  touches R2. The binary is `corpus-db\build\tools\rclone.exe` (v1.75.2,
  SHA-256 checked against rclone's published sums) and it is gitignored.
