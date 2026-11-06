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
import difflib
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
#: HTTP statuses that mean "try again later", not "this work does not exist".
RETRYABLE = {429, 500, 502, 503, 504}


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
    """The OpenAlex record for a DOI, or None.

    A rate limit or an outage is **raised**, because it is not the same answer
    as "this DOI is not in OpenAlex": the candidate must stay retryable rather
    than be rejected for a reason that was never measured.
    """
    try:
        return _get_json("%s/works/https://doi.org/%s" % (OPENALEX, urllib.parse.quote(doi, safe="")),
                         _openalex_params())
    except urllib.error.HTTPError as error:
        if error.code in RETRYABLE:
            raise
        return None
    except Exception:
        return None


def work_by_title(title, year=None):
    """The OpenAlex record that best matches a title, or None.

    A source the pipeline saw may carry only a title (a corpus hit, or a web
    page).  The title is searched here so the candidate can still be resolved
    to an open full text.  A title that cannot be matched stays a candidate;
    the corpus never guesses an identity from a partial match.  A rate limit is
    raised, never mistaken for "no such work".
    """
    title = " ".join(str(title or "").split())
    if len(title) < 8:
        return None
    params = {
        "search": title, "per-page": "5",
        "select": "id,doi,display_name,title,publication_year,has_content,"
                  "best_oa_location,authorships,primary_location",
    }
    params.update(_openalex_params())
    try:
        payload = _get_json("%s/works" % OPENALEX, params)
    except urllib.error.HTTPError as error:
        if error.code in RETRYABLE:
            raise
        return None
    except Exception:
        return None
    wanted = lib.norm_title(title)
    best, best_score = None, 0.0
    for work in payload.get("results") or []:
        found = lib.norm_title(work.get("title") or work.get("display_name") or "")
        if not found:
            continue
        score = difflib.SequenceMatcher(None, wanted, found).ratio()
        if year and work.get("publication_year"):
            try:
                if abs(int(work["publication_year"]) - int(year)) <= 1:
                    score += 0.05
            except (TypeError, ValueError):
                pass
        if score > best_score:
            best, best_score = work, score
    return best if best_score >= 0.90 else None



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
    """Every source a recent search saw becomes a candidate.

    A source does not need a DOI or a URL to enter the queue: a corpus hit or
    a web page may carry only a title, and that title is still something the
    pipeline needed and the corpus did not hold.  The title is the identity
    when it is specific enough; `fetch` resolves it to a DOI later.
    """
    rows = connection.execute(
        "SELECT s.title, s.doi, s.url, s.venue, s.year, s.source, s.abstract,"
        "       l.search_id, l.subject, l.corpus_hits"
        "  FROM seen_sources s JOIN search_log l ON l.search_id = s.search_id"
        " WHERE l.searched_at >= ?"
        "   AND (COALESCE(s.doi, '') != '' OR COALESCE(s.url, '') != ''"
        "        OR LENGTH(COALESCE(s.title, '')) >= 12)",
        (lib.days_ago(since_days),)).fetchall()
    added = 0
    for row in rows:
        source = (row["source"] or "").lower()
        # The corpus already holds its own pages; background reading is not
        # evidence and is never ingested.  Neither belongs in the demand queue.
        if source in ("proprietary corpus", "orientation web"):
            continue
        # A source the corpus already holds is not a gap.  It belongs in the
        # document record, not in the demand queue, so the queue is only what
        # the pipeline needed and the corpus could not answer.
        if lib.find_document_for(connection, doi=row["doi"], url=row["url"],
                                 title=row["title"], year=row["year"]):
            continue
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
    """Queries the corpus could not answer, and that came up more than once.

    The framework seeds are excluded: that worker has already asked the journal
    APIs for every lens, so re-researching the same query would only repeat it.
    """
    rows = connection.execute(
        "SELECT query, subject, COUNT(*) AS times, MAX(searched_at) AS last_at"
        "  FROM search_log WHERE corpus_hits = 0"
        "   AND (dimension IS NULL OR dimension != 'framework_seed')"
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
    """Pull the open full text of the top candidates and ingest them.

    A `failed` candidate is retried: the failure may have been a rate limit or a
    dropped download, and the reason is recorded on the row.  A rejection or an
    owner decision is never retried automatically.
    """
    candidates = connection.execute(
        "SELECT * FROM candidates WHERE status IN ('new', 'failed')"
        " ORDER BY status = 'failed', priority DESC, seen_count DESC LIMIT ?",
        (limit,)).fetchall()
    outcomes = {"ingested": 0, "duplicate": 0, "needs_decision": 0, "rejected": 0, "failed": 0}
    for candidate in candidates:
        outcome = fetch_one(connection, candidate)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return outcomes


def fetch_one(connection, candidate, approved=False):
    """Fetch one candidate.

    `approved` is the owner's explicit decision: it skips the licence refusal
    for that one work.  The nightly `fetch` never sets it, so an unattended run
    still obeys the licence gate; the admin approve button does, because the
    owner has seen the work and accepted it.
    """
    candidate_id = candidate["candidate_id"]
    doi = lib.norm_doi(candidate["doi"])
    url = candidate["url"]
    title = candidate["title"]
    year = candidate["year"]
    # A work the corpus already holds is not fetched again. The corpus is the
    # citation unit: the same paper held twice would be cited twice for one
    # source, and the download is wasted either way.  This check runs before
    # any network call, so a duplicate whose DOI is already on the candidate
    # costs nothing.
    existing = lib.find_document_for(connection, doi=doi, url=url,
                                      title=title, year=year)
    if existing:
        message = "the corpus already holds this work as %s" % existing
        connection.execute(
            "UPDATE candidates SET status = 'ingested', doc_id = ?, reason = ? WHERE candidate_id = ?",
            (existing, message, candidate_id))
        connection.commit()
        return "duplicate"
    # A candidate may have arrived with only a title (a corpus hit, a web page,
    # or a session that never saw a DOI).  It is resolved once, here: the title
    # is searched in OpenAlex and, when it matches, the DOI and landing page are
    # written back onto the candidate so the next cycle does not search again.
    try:
        work = work_by_doi(doi) if doi else None
        if not work and title:
            work = work_by_title(title, year)
    except urllib.error.HTTPError as error:
        connection.execute(
            "UPDATE candidates SET status = 'failed', reason = ? WHERE candidate_id = ?",
            ("OpenAlex is rate-limited or unavailable (HTTP %s); retry next cycle"
             % error.code, candidate_id))
        connection.commit()
        return "failed"
    if work:
        doi = lib.norm_doi(work.get("doi")) or doi
        url = url or ((work.get("primary_location") or {}).get("landing_page_url"))
        connection.execute(
            "UPDATE candidates SET doi = COALESCE(doi, ?), url = COALESCE(url, ?)"
            " WHERE candidate_id = ?", (doi, url, candidate_id))
        connection.commit()
        # The resolved work may be one the corpus already holds.
        existing = lib.find_document_for(connection, doi=doi, url=url,
                                          title=title, year=year)
        if existing:
            message = "the corpus already holds this work as %s" % existing
            connection.execute(
                "UPDATE candidates SET status = 'ingested', doc_id = ?, reason = ?"
                " WHERE candidate_id = ?", (existing, message, candidate_id))
            connection.commit()
            return "duplicate"
    if not doi and not url and not work:
        # The title-only queue is the point of the learning loop: the work was
        # needed, but it cannot be resolved to an open full text from a title
        # alone.  It stays visible for the owner instead of being invented.
        connection.execute(
            "UPDATE candidates SET status = 'needs_decision', reason = ? WHERE candidate_id = ?",
            ("title only: no DOI or URL, and OpenAlex found no matching work", candidate_id))
        connection.commit()
        return "needs_decision"
    pdf_url, licence = open_access_pdf(work)
    if not pdf_url:
        connection.execute(
            "UPDATE candidates SET status = 'rejected', reason = ? WHERE candidate_id = ?",
            ("no open full text at the API content endpoint", candidate_id))
        connection.commit()
        return "rejected"
    if not licence and not approved:
        # A PDF that carries no licence is not automatically open.  The gate is
        # the whole safety mechanism, so an unknown licence waits for the owner
        # instead of being treated as permission.
        connection.execute(
            "UPDATE candidates SET status = 'needs_decision', reason = ? WHERE candidate_id = ?",
            ("no licence recorded; approve it in the admin page to ingest", candidate_id))
        connection.commit()
        return "needs_decision"
    if licence and licence not in OPEN_LICENCES and not approved:
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
    except urllib.error.HTTPError as error:
        connection.execute(
            "UPDATE candidates SET status = 'failed', reason = ? WHERE candidate_id = ?",
            ("the PDF could not be downloaded (HTTP %s)" % error.code, candidate_id))
        connection.commit()
        return "failed"
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

    # The paper server loads Backend/.env at startup; this worker runs in its
    # own process, so it loads the few source keys it needs itself.  Names are
    # printed, never values.
    credentials = lib.load_source_credentials()
    if credentials["loaded"]:
        print("source credentials: " + ", ".join(credentials["loaded"])
              + " (from %s)" % credentials["path"], file=sys.stderr)

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
