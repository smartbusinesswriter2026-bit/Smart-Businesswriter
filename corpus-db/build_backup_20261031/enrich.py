"""The enrichment worker: the corpus that fills itself.

    python corpus-db/build/enrich.py collect     # learning log -> candidate queue
    python corpus-db/build/enrich.py score       # rank the queue by need
    python corpus-db/build/enrich.py research     # unanswered questions -> candidates
    python corpus-db/build/enrich.py fetch       # pull full text for the top candidates
    python corpus-db/build/enrich.py run         # all four, in order
    python corpus-db/build/enrich.py status      # what the corpus looks like now

Why this exists: the API layer is extensive but slow, and most of what it holds
is never needed. So the corpus does not mirror the API. It keeps a **demand**
queue. A candidate enters the queue because users kept searching for something
the corpus could not answer, and it rises in priority the more often it comes
up and the thinner its subject is.

The owner decides what actually enters the corpus: `fetch` only ingests open
licences that need no decision; everything else is marked `needs_decision` and
waits in the admin UI.

Environment: BP_OPENALEX_API_KEY, BP_OPENALEX_EMAIL, CORPUS_MEILI_URL,
CORPUS_MEILI_KEY, BP_CORPUS_DB.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib

OPENALEX = "https://api.openalex.org"
OPENALEX_CONTENT = "https://content.openalex.org"

#: Licences that may enter the corpus without an owner decision.
OPEN_LICENCES = {"cc0", "cc-by", "cc-by-sa", "public-domain", "pd"}
#: Licences that constrain use or derivatives: the owner decides (G-17).
NEEDS_DECISION = {"cc-by-nc", "cc-by-nc-sa", "cc-by-nd", "cc-by-nc-nd"}


def _openalex_params():
    params = {}
    key = os.environ.get("BP_OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
    mail = os.environ.get("BP_OPENALEX_EMAIL")
    if mail:
        params["mailto"] = mail
    return params


def _get_json(url, params=None, timeout=30):
    if params:
        url = "%s?%s" % (url, urllib.parse.urlencode(params))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_bytes(url, timeout=120):
    request = urllib.request.Request(url, headers={"User-Agent": "smart-business-writer-corpus/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def work_by_doi(doi):
    """The OpenAlex record for a DOI, or None."""
    try:
        return _get_json("%s/works/https://doi.org/%s" % (OPENALEX, urllib.parse.quote(doi, safe="")),
                         _openalex_params())
    except Exception:
        return None


def open_access_pdf(work):
    """The open-access PDF URL and licence for an OpenAlex work.

    Uses the **content** endpoint, not `locations[].pdf_url`: that field is the
    publisher's URL and keying off it produces a lossy, inferred match.
    """
    if not work:
        return None, None
    content = work.get("has_content") or {}
    if not content.get("pdf"):
        return None, None
    identifier = (work.get("id") or "").rsplit("/", 1)[-1]
    if not identifier:
        return None, None
    location = work.get("best_oa_location") or {}
    licence = (location.get("license") or "").lower() or None
    return "%s/works/%s.pdf" % (OPENALEX_CONTENT, identifier), licence


def authors_of(work):
    names = []
    for authorship in (work.get("authorships") or [])[:20]:
        name = ((authorship.get("author") or {}).get("display_name") or "").strip()
        if name:
            names.append(name)
    return names


# ── step 1: collect ─────────────────────────────────────────────────────────

def collect(connection, since_days=30):
    """Every source a recent search saw becomes a candidate."""
    rows = connection.execute(
        "SELECT s.title, s.doi, s.url, s.venue, s.year, s.source, s.abstract,"
        "       l.search_id, l.subject, l.corpus_hits"
        "  FROM seen_sources s JOIN search_log l ON l.search_id = s.search_id"
        " WHERE l.searched_at >= ?"
        "   AND (s.doi IS NOT NULL AND s.doi != '' OR s.url IS NOT NULL AND s.url != '')",
        (lib.days_ago(since_days),)).fetchall()
    added = 0
    for row in rows:
        item = {"title": row["title"], "doi": row["doi"], "url": row["url"],
                "venue": row["venue"], "year": row["year"], "source": row["source"]}
        if lib.upsert_candidate(connection, item):
            added += 1
    return len(rows), added


# ── step 2: score ───────────────────────────────────────────────────────────

def score(connection):
    return lib.rescore_candidates(connection)


# ── step 3: research ────────────────────────────────────────────────────────

def unanswered_queries(connection, since_days=30, min_times=2):
    """Queries the corpus could not answer, and that came up more than once."""
    rows = connection.execute(
        "SELECT query, subject, COUNT(*) AS times, MAX(searched_at) AS last_at"
        "  FROM search_log WHERE corpus_hits = 0"
        "   AND searched_at >= ?"
        " GROUP BY query, subject HAVING times >= ? ORDER BY times DESC",
        (lib.days_ago(since_days), min_times)).fetchall()
    return [{"query": row["query"], "subject": row["subject"], "times": row["times"]}
            for row in rows]


def research(connection, limit=10):
    """Search the open-access literature for what the corpus is missing."""
    found = 0
    for gap in unanswered_queries(connection)[:limit]:
        try:
            params = {"search": gap["query"], "filter": "has_content.pdf:true",
                      "per-page": "10"}
            params.update(_openalex_params())
            payload = _get_json("%s/works" % OPENALEX, params)
        except Exception as error:
            print("research failed for %r (%s)" % (gap["query"], error), file=sys.stderr)
            continue
        for work in payload.get("results") or []:
            location = work.get("primary_location") or {}
            item = {
                "title": work.get("title") or work.get("display_name"),
                "doi": work.get("doi"),
                "url": location.get("landing_page_url"),
                "venue": (location.get("source") or {}).get("display_name"),
                "year": work.get("publication_year"),
                "source": "openalex",
            }
            if lib.upsert_candidate(connection, item):
                found += 1
    return found


# ── step 4: fetch ───────────────────────────────────────────────────────────

def fetch(connection, limit=10):
    """Pull the open full text of the top candidates and ingest them."""
    candidates = connection.execute(
        "SELECT * FROM candidates WHERE status = 'new' ORDER BY priority DESC, seen_count DESC LIMIT ?",
        (limit,)).fetchall()
    outcomes = {"ingested": 0, "duplicate": 0, "needs_decision": 0, "rejected": 0, "failed": 0}
    for candidate in candidates:
        outcome = fetch_one(connection, candidate)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return outcomes


def fetch_one(connection, candidate):
    candidate_id = candidate["candidate_id"]
    doi = candidate["doi"]
    # A work the corpus already holds is not fetched again. The corpus is the
    # citation unit: the same paper held twice would be cited twice for one
    # source, and the download is wasted either way.
    existing = lib.find_document_for(connection, doi=doi, url=candidate["url"],
                                      title=candidate["title"], year=candidate["year"])
    if existing:
        message = "the corpus already holds this work as %s" % existing
        connection.execute(
            "UPDATE candidates SET status = 'ingested', doc_id = ?, reason = ? WHERE candidate_id = ?",
            (existing, message, candidate_id))
        connection.commit()
        return "duplicate"
    work = work_by_doi(doi) if doi else None
    pdf_url, licence = open_access_pdf(work)
    if not pdf_url:
        connection.execute(
            "UPDATE candidates SET status = 'rejected', reason = ? WHERE candidate_id = ?",
            ("no open full text at the API content endpoint", candidate_id))
        connection.commit()
        return "rejected"
    if licence and licence not in OPEN_LICENCES:
        status = "needs_decision" if licence in NEEDS_DECISION else "rejected"
        reason = ("licence %s needs an owner decision" % licence) if status == "needs_decision" \
            else ("licence %s is not an open licence" % licence)
        connection.execute(
            "UPDATE candidates SET status = ?, reason = ? WHERE candidate_id = ?",
            (status, reason, candidate_id))
        connection.commit()
        return status
    try:
        raw = _get_bytes(pdf_url)
    except Exception as error:
        connection.execute(
            "UPDATE candidates SET status = 'failed', reason = ? WHERE candidate_id = ?",
            ("the PDF could not be downloaded (%s)" % type(error).__name__, candidate_id))
        connection.commit()
        return "failed"
    if not raw.startswith(b"%PDF"):
        connection.execute(
            "UPDATE candidates SET status = 'failed', reason = ? WHERE candidate_id = ?",
            ("the download was not a PDF", candidate_id))
        connection.commit()
        return "failed"

    location = (work or {}).get("primary_location") or {}
    meta = {
        "title": (work or {}).get("title") or candidate["title"],
        "authors": "; ".join(authors_of(work)) if work else "",
        "year": (work or {}).get("publication_year") or candidate["year"],
        "venue": ((location.get("source") or {}).get("display_name")) or candidate["venue"],
        "doi": doi, "kind": "journal-article",
        "subject": lib.classify_subject((work or {}).get("title") or candidate["title"] or ""),
        "licence": licence, "licence_verified": 1,
        "source_url": candidate["url"],
        "metadata_source": "openalex", "metadata_verified": 1,
    }
    # The file is written only once the duplicate check has passed, so a
    # refused download leaves nothing behind.
    status, doc_id, message = lib.ingest_pdf(connection, raw, meta,
                                             filename="%s.pdf" % (doi or candidate_id))
    if status == "ingested":
        connection.execute(
            "UPDATE candidates SET status = 'ingested', doc_id = ?, reason = ? WHERE candidate_id = ?",
            (doc_id, message, candidate_id))
    elif status == "duplicate":
        connection.execute(
            "UPDATE candidates SET status = 'ingested', doc_id = ?, reason = ? WHERE candidate_id = ?",
            (doc_id, message, candidate_id))
    else:
        connection.execute(
            "UPDATE candidates SET status = 'failed', reason = ? WHERE candidate_id = ?",
            (message, candidate_id))
    connection.commit()
    return status


# ── the whole loop ──────────────────────────────────────────────────────────

def run(connection):
    seen, added = collect(connection)
    print("collect   %d sources seen, %d candidates touched" % (seen, added))
    print("score     %d candidates ranked" % score(connection))
    print("research  %d new candidates from the open literature" % research(connection))
    print("fetch     %s" % fetch(connection))
    try:
        print("index     %d pages pushed to Meilisearch" % lib.index_pages(connection))
    except Exception as error:
        print("index     skipped (%s)" % error, file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(description="The self-enriching corpus worker.")
    parser.add_argument("job", choices=["collect", "score", "research", "fetch", "run", "status"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    connection = lib.connect()
    lib.apply_schema(connection)
    if args.job == "collect":
        seen, added = collect(connection)
        print("%d sources seen, %d candidates touched" % (seen, added))
    elif args.job == "score":
        print("%d candidates ranked" % score(connection))
    elif args.job == "research":
        print("%d new candidates" % research(connection, args.limit))
    elif args.job == "fetch":
        print(fetch(connection, args.limit))
    elif args.job == "status":
        print(json.dumps(lib.stats(connection), indent=2))
    else:
        run(connection)
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
