"""The corpus admin service: the API behind admin.html.

    python corpus-db/build/corpus_service.py --port 7710

Then open http://127.0.0.1:7710/

This is an **owner tool**. It binds to localhost only and has no login: it
exposes upload and enrichment, which must never be reachable from the internet.
If it ever needs to run off-box, put it behind an authenticating proxy first.

It does not touch the pipeline. The pipeline reads the corpus through
Meilisearch and SQLite directly; this service is only for the owner.
"""

import argparse
import base64
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib
import enrich

HERE = os.path.dirname(os.path.abspath(__file__))
ADMIN_HTML = os.path.join(HERE, "admin.html")


def _candidates(connection, status="new", limit=100):
    rows = connection.execute(
        "SELECT * FROM candidates WHERE (? = 'all' OR status = ?)"
        " ORDER BY priority DESC, seen_count DESC LIMIT ?",
        (status, status, limit)).fetchall()
    return [dict(row) for row in rows]


def _searches(connection, limit=50):
    rows = connection.execute(
        "SELECT * FROM search_log ORDER BY searched_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def _gaps(connection):
    """The subjects the corpus answers badly, with the questions that were missed."""
    thin = lib.thin_subjects(connection)
    rows = connection.execute(
        "SELECT query, subject, COUNT(*) AS times FROM search_log"
        " WHERE corpus_hits = 0 AND searched_at >= ?"
        " GROUP BY query, subject ORDER BY times DESC LIMIT 50",
        (lib.days_ago(30),)).fetchall()
    return {"thin_subjects": thin,
            "unanswered": [{"query": row["query"], "subject": row["subject"], "times": row["times"]}
                           for row in rows]}


def handle(verb, path, body):
    """One admin request. Returns (status_code, payload).

    `path` may carry a query string; it is parsed here, so a caller may pass
    the raw request path unchanged.
    """
    parsed = urllib.parse.urlparse(path)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    query = urllib.parse.parse_qs(parsed.query)
    if parts[:2] == ["api", "corpus"]:
        parts = parts[2:]
    else:
        return 404, {"error": "not a corpus route"}

    connection = lib.connect()
    lib.apply_schema(connection)
    try:
        if parts == ["log"] and verb == "POST":
            # The pipeline writes its learning log here. It is the only write
            # path the pipeline uses, and it is deliberately fail-soft: a
            # learning-log failure must never break a paper run.
            body = body or {}
            search_id = lib.record_search(
                connection,
                query=body.get("query") or "",
                subject=body.get("subject"),
                dimension=body.get("dimension"),
                case_id=body.get("case_id"),
                corpus_hits=body.get("corpus_hits") or 0,
                live_hits=body.get("live_hits") or 0,
                corpus_status=body.get("corpus_status") or "ok",
                sources=body.get("sources") or [])
            for web in body.get("web_sources") or []:
                lib.record_web_source(connection, web)
            if search_id is None:
                return 503, {"error": "the learning log could not be written"}
            return 200, {"search_id": search_id}

        if parts == ["stats"] and verb == "GET":
            return 200, lib.stats(connection)

        if parts == ["candidates"] and verb == "GET":
            status = query.get("status", ["new"])[0]
            limit = int(query.get("limit", ["100"])[0])
            return 200, {"candidates": _candidates(connection, status, limit)}

        if parts == ["candidates", "approve"] and verb == "POST":
            candidate_id = (body or {}).get("candidate_id")
            row = connection.execute(
                "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            if not row:
                return 404, {"error": "no such candidate"}
            outcome = enrich.fetch_one(connection, row)
            return 200, {"status": outcome}

        if parts == ["candidates", "reject"] and verb == "POST":
            candidate_id = (body or {}).get("candidate_id")
            reason = (body or {}).get("reason") or "rejected by the owner"
            connection.execute(
                "UPDATE candidates SET status = 'rejected', reason = ? WHERE candidate_id = ?",
                (reason, candidate_id))
            connection.commit()
            return 200, {"status": "rejected"}

        if parts == ["upload"] and verb == "POST":
            body = body or {}
            encoded = body.get("data")
            filename = body.get("filename") or "upload.pdf"
            if not isinstance(encoded, str) or not encoded.strip():
                return 422, {"error": "attach the file as base64 'data'"}
            try:
                raw = base64.b64decode(encoded, validate=True)
            except Exception:
                return 422, {"error": "the file could not be decoded"}
            if not raw.startswith(b"%PDF"):
                return 422, {"error": "that file is not a PDF"}
            meta = {
                "title": body.get("title") or filename,
                "authors": body.get("authors") or "",
                "year": body.get("year"), "publisher": body.get("publisher"),
                "edition": body.get("edition"), "isbn": body.get("isbn"),
                "doi": body.get("doi"), "venue": body.get("venue"),
                "volume": body.get("volume"), "issue": body.get("issue"),
                "kind": body.get("kind") or "book",
                "subject": body.get("subject"), "licence": body.get("licence"),
                "source_url": body.get("source_url"), "metadata_source": "manual",
            }
            path = lib.save_pdf(raw, filename)
            status, doc_id, message = lib.ingest_pdf(connection, raw, meta, local_path=path)
            connection.execute(
                "INSERT INTO uploads (upload_id, uploaded_at, filename, sha256, bytes, status,"
                " doc_id, message) VALUES (?,?,?,?,?,?,?,?)",
                (lib.sha256_text(filename + lib.now())[:16], lib.now(), filename,
                 lib.sha256_bytes(raw), len(raw), status, doc_id, message))
            connection.commit()
            if status == "ingested":
                try:
                    lib.index_pages(connection)
                except Exception:
                    pass
            return 200, {"status": status, "doc_id": doc_id, "message": message}

        if parts == ["uploads"] and verb == "GET":
            rows = connection.execute(
                "SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT 50").fetchall()
            return 200, {"uploads": [dict(row) for row in rows]}

        if parts == ["searches"] and verb == "GET":
            limit = int(query.get("limit", ["50"])[0])
            return 200, {"searches": _searches(connection, limit)}

        if parts == ["gaps"] and verb == "GET":
            return 200, _gaps(connection)

        if parts == ["enrich"] and verb == "POST":
            limit = int((body or {}).get("limit") or 5)
            seen, added = enrich.collect(connection)
            ranked = enrich.score(connection)
            found = enrich.research(connection, limit)
            outcomes = enrich.fetch(connection, limit)
            return 200, {"collected": added, "ranked": ranked, "researched": found,
                         "fetched": outcomes}

        return 404, {"error": "unknown corpus route"}
    finally:
        connection.close()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        payload = body if isinstance(body, bytes) else json.dumps(body, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/admin.html"):
            try:
                with open(ADMIN_HTML, "rb") as page:
                    return self._send(200, page.read(), "text/html; charset=utf-8")
            except OSError:
                return self._send(500, {"error": "admin.html is missing"})
        code, payload = handle("GET", self.path, None)
        return self._send(code, payload)

    def do_POST(self):
        code, payload = handle("POST", self.path, self._body())
        return self._send(code, payload)

    def log_message(self, fmt, *args):
        sys.stderr.write("corpus-service %s\n" % (fmt % args))


def main():
    parser = argparse.ArgumentParser(description="The corpus admin service.")
    parser.add_argument("--port", type=int, default=7710)
    parser.add_argument("--host", default="127.0.0.1",
                        help="localhost only. Changing this needs an authenticating proxy.")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("corpus admin on http://%s:%d/  (database: %s)" % (args.host, args.port, lib.DB_PATH))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
