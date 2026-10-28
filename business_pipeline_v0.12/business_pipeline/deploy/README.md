# Serving the workbench outside a laptop

This directory holds a deployment slice for the workbench: a container, a reverse-proxy example and a
systemd unit. Read the constraints before pointing students at it.

## What the current server is

`scripts/serve.py` starts a **single Python process** (`ThreadingHTTPServer`) with:

- **sessions in memory** — a run exists only inside the process that created it;
- a **case store on disk** (`BP_CASES_DIR`, default `cases/`) with one JSON bundle per case;
- the **sandbox on by default** — every computation spawns a guarded child process;
- no authentication, tenancy or per-user quota.

That shape is fine for a class pilot on one machine and is **not** a horizontally scalable fleet. Two
processes behind a load balancer will lose each other's sessions, so the first deployment must be
**one process per instance, many threads**, with the reverse proxy sending all of a student's requests
to the same instance (or a single instance total).

## Recommended first deployment

```
client ── TLS ── nginx ── 127.0.0.1:8000 ── serve.py (one process, threads)
```

1. Build and run the container (context is the repository root, not `deploy/`):

   ```
   docker build -f deploy/Dockerfile -t smart-businesswriter .
   docker run --rm -p 127.0.0.1:8000:8000 -v bp-data:/data smart-businesswriter
   ```

2. Put nginx in front with `deploy/nginx.conf` (TLS terminated there, a body limit above the 5 MB
   ingestion cap, and a generous read timeout for the sandbox).

3. Run `python scripts/ci.py` in CI before every deploy. It fails on a broken test, a frozen-contract
   drift or a page syntax error.

4. Back up the case store before any change: `POST /api/cases/backup`, then copy the archive off the
   instance. Restore with `POST /api/cases/restore`.

5. Watch `GET /api/health` (cases, state directory, sandbox and model flags, request-log status). Turn on
   the request log with `BP_REQUEST_LOG=/data/request.log` — it records method, path, status and
   duration only, never a body or a case title.

6. Probe capacity with `python scripts/bench.py --url http://127.0.0.1:8000`. It reports read-only
   endpoints; a real run additionally pays for the sandbox child process.

## Environment

| Variable | Default | Use |
|---|---|---|
| `BP_CASES_DIR` | `cases/` | durable case store; put it on a volume |
| `BP_STATE_DIR` | `state/` | credits and other local state |
| `BP_INTAKE_DIR` | `intake/` | uploaded files |
| `BP_REQUEST_LOG` | off | JSONL request log (method, path, status, ms) |
| `BP_RETRIEVAL_LOG` | `retrieval_log.jsonl` | literature retrieval audit; empty disables |
| `BP_LLM_*` | off | optional model assistance; keep off unless a provider is configured |

## What must change before a multi-instance fleet

- **Session store**: move in-memory sessions to a shared, durable store (or make each run resumable from
  its stored bundle). Until then, sessions are pinned to one process.
- **Per-user isolation and auth**: the local build has none; add it before exposing student work.
- **Retention and deletion**: decide how long cases and intake files are kept, and how a student deletes
  them.
- **Sandbox economics**: one child process per computation is the safe default; measure it under load and
  decide whether a worker pool is needed.
- **Rate limits and quotas**: the export credit ledger is local; a hosted deployment needs an abuse
  control at the proxy or the app.
- **Backups and restore drills**: the backup format exists; schedule it and test the restore.

This file does not claim those are done. It is the list that decides whether the app can serve hundreds
of thousands of students, and the computation layer is deliberately independent of it.
