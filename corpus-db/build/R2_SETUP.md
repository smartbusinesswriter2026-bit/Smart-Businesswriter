# R2 setup — the last two steps, then one command

This is the off-site copy of the corpus PDF bytes (DATABASE.md step 13). The
scripts are written, tested and scheduled. Two things need the owner's
Cloudflare account, and only the owner can do them:

## Step 1 — enable R2 for the account

Cloudflare's API refuses every R2 call on this account with
`10042 NotEntitled` ("Account not entitled to this feature"), because the
account has no R2 subscription yet. There is no API for this; it is a
dashboard action.

1. Sign in at <https://dash.cloudflare.com> and open **R2** in the sidebar.
2. Follow the prompts to enable R2 for the account
   (`127515e9310b9d256df686b85a889907`, "Smart.businesswriter.2026@gmail.com's Account").
   Cloudflare asks for a payment method even on the free tier; the first
   10 GB-month of storage and all egress out of it are $0.
3. Create the bucket **smart-business-writer-corpus** (private, no public
   access, **no `r2.dev` subdomain** — that subdomain is a public URL and
   would expose copyrighted text).

   The bucket can also be created from the API once R2 is enabled; the sync
   script expects it to exist and named exactly that.

## Step 2 — create a bucket-scoped API token

In the same R2 page: **Manage R2 API Tokens → Create Account API token**.

| Setting | Value |
|---|---|
| Permission | **Object Read & Write** |
| Bucket | `smart-business-writer-corpus` only |
| TTL | the longest you are comfortable with |

The dashboard shows an **Access Key ID** and a **Secret Access Key**.

## Step 3 — put the two values in the secrets file

Copy the template and fill it in:

```powershell
Copy-Item corpus-db\build\rclone_corpus.env.example corpus-db\build\_secrets\rclone_corpus.env
notepad corpus-db\build\_secrets\rclone_corpus.env
```

```
R2_ACCOUNT_ID=127515e9310b9d256df686b85a889907
R2_BUCKET=smart-business-writer-corpus
R2_ACCESS_KEY_ID=<the Access Key ID>
R2_SECRET_ACCESS_KEY=<the Secret Access Key>
```

The `_secrets` folder is gitignored, so the values never reach the repository.
**Do not paste the key into a chat window** — put it in the file.

The same file also accepts `R2_API_TOKEN_ID` and `R2_API_TOKEN_VALUE` instead
of the pair above; the script then derives the S3 secret as the SHA-256 of the
token value, which is what Cloudflare's own recipe says to do.

## Step 4 — run it

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\rclone_sync.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\rclone_restore_test.ps1
```

The first command uploads 19 documents (625 MB) and writes the object key of
each one into `documents.r2_key`. The second proves the copy: it restores the
bytes, checks every SHA-256 against `documents.sha256`, rebuilds a search
index from the restored record and asks both indexes the same question. Its
report lands in `corpus-db\test_restore\restore_report.md`.

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
  token, never through an `r2.dev` subdomain. A presigned URL for any single
  object can be produced on demand with `rclone link`.
- `rclone` is a build and operations tool (C-02). The pipeline runtime never
  touches R2. The binary is `corpus-db\build\tools\rclone.exe` (v1.75.2,
  SHA-256 checked against rclone's published sums) and it is gitignored.
