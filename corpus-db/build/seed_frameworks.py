"""Identify every framework and theory the pipeline can name, then seed the corpus.

    python corpus-db/build/seed_frameworks.py --dry-run
    python corpus-db/build/seed_frameworks.py
    python corpus-db/build/seed_frameworks.py --fetch 20
    python corpus-db/build/seed_frameworks.py --frameworks "Porter's Five Forces,Ansoff,PESTEL,SWOT"

Why this exists. The corpus only saves a future API call when it holds the work
before the next paper asks for it. The pipeline already knows which analytical
lenses it can use; this script asks the journal APIs for each lens once, stores
every work it finds in the demand queue, and optionally fetches the open full
text into the corpus. The next paper then answers from the corpus instead of the
API.

What it does, in order:

1. Reads the pipeline's own registry (`registry_v0_2.json`: frameworks, models,
   theories, and optionally quantitative methods) and its worksheet profiles
   (`framework_profiles.PROFILES`), so the lens list is the product's list, not
   a second hand-written one.
2. Builds one or two short queries per lens: the lens name plus its kind
   (`framework`, `model`, `theory`, `method`), and, when a worksheet profile
   exists, the first dimension query it already uses.
3. Searches OpenAlex, Crossref, Semantic Scholar and DOAJ through the pipeline's
   own adapters.
4. Stores each work as a candidate, deduplicated against the corpus and against
   the queue. The candidate's reason records which lens asked for it.
5. Optionally fetches the open full text of the top candidates. The licence gate
   in `enrich.fetch_one` decides: an open licence is ingested, a restrictive or
   unknown licence waits for the owner, a paywalled work stays a candidate.
6. Optionally rebuilds the Meilisearch index so the new pages are searchable.

It never invents a source, a DOI or a citation. A lens with no result is a named
gap in the report; a paywalled work is stored as metadata and is not cited.

Environment: `BP_CORPUS_DB` (default the canonical corpus), `BP_SOURCE_ENV`
(default the pipeline's `Backend/.env`), and the source keys in that file. The
script loads the OpenAlex/Crossref/Semantic Scholar keys itself, because it runs
in its own process.
"""

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(CORPUS_DIR)
PIPELINE_DIR = os.path.join(ROOT, "business_pipeline_v0.12", "business_pipeline")
PIPELINE_SRC = os.path.join(PIPELINE_DIR, "src")
REGISTRY_PATH = os.path.join(PIPELINE_SRC, "bp", "data", "registry_v0_2.json")

sys.path.insert(0, HERE)
sys.path.insert(0, PIPELINE_SRC)

import corpus_lib as lib  # noqa: E402  (the corpus tools are the local package)
import enrich  # noqa: E402

#: The journal APIs.  The corpus is deliberately absent: it is what this script
#: is filling, and searching it would only return what it already holds.
SEED_DATABASES = ["openalex", "crossref", "semanticscholar", "doaj"]

#: Names that are documents or computations, not analytical lenses.
SKIP_NAMES = {
    "no framework", "none", "break even", "breakeven", "break even point",
    "business plan", "feasibility study", "marketing plan", "project proposal",
}

KIND_WORD = {"F": "framework", "M": "model", "T": "theory", "Q": "method"}

#: Registry rows that describe a review procedure, not a lens a paper can name.
SKIP_SUFFIXES = (" review", " evidence check", " evidence-to-action review")


def _norm(value):
    """The identity of a lens name for de-duplication, not for display."""
    text = str(value or "").replace("\u2019", "'").lower()
    text = re.sub(r"['\u2019]s\b", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _split_name(name):
    """One registry row may name two lenses: `SWOT / TOWS` is two."""
    parts = re.split(r"\s+/\s+|\s+or\s+|\s+\+\s+|\s+&\s+", str(name or ""))
    return [part.strip(" .;:") for part in parts if part.strip(" .;:")]


def _theory_head(name):
    """The shared noun of a theory bundle (`... leadership`, `... theory`)."""
    words = re.findall(r"[A-Za-z][A-Za-z-]+", str(name or ""))
    for word in reversed(words):
        if word.lower() in ("leadership", "theory", "model", "view", "economics", "framework"):
            return word.lower()
    return ""


def _read_registry():
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as stream:
            return json.load(stream).get("records") or []
    except (OSError, ValueError):
        return []


def _profiles():
    """The worksheet profiles, or an empty map when the pipeline is absent."""
    try:
        from bp.product import framework_profiles
        return framework_profiles.PROFILES
    except Exception:
        return {}


def load_lenses(include_methods=False):
    """Every lens the pipeline can name, with its kind and its best queries.

    The registry is the catalogue; the profiles are the worksheets that have
    already decided a query for each dimension.  The result is sorted so the
    conductor's main frameworks come first, then the rest by name.
    """
    lenses = {}

    def add(name, kind, discipline="", queries=None, source=""):
        for part in _split_name(name):
            key = _norm(part)
            if not key or key in SKIP_NAMES:
                continue
            if key.endswith(SKIP_SUFFIXES):
                continue
            row = lenses.get(key)
            if row is None:
                lenses[key] = {
                    "name": part, "kind": kind, "discipline": discipline or "",
                    "queries": list(queries or []), "source": source or "",
                }
            else:
                for query in queries or []:
                    if query not in row["queries"]:
                        row["queries"].append(query)

    for record in _read_registry():
        record_type = record.get("type")
        if record_type not in ("F", "M", "T") and not (include_methods and record_type == "Q"):
            continue
        kind = KIND_WORD.get(record_type, "framework")
        discipline = (record.get("disciplines") or [""])[0]
        members = record.get("members") if record_type == "T" else []
        if members:
            # A theory row is a bundle: the members are the lenses a paper can
            # actually name.  A bare adjective or surname ("Transformational",
            # "Maslow") borrows the bundle's shared noun so the query is
            # "Transformational leadership theory", not "Transformational".
            head = _theory_head(record.get("name"))
            for member in members:
                name = member
                if head and not re.search(
                        r"\b(theory|model|view|framework|economics|leadership)\b",
                        str(member), re.I):
                    name = "%s %s" % (member, head)
                add(name, kind, discipline, source=record.get("id"))
        else:
            add(record.get("name"), kind, discipline, source=record.get("id"))

    for template, profile in _profiles().items():
        label = profile.get("label") or profile.get("key")
        if not label:
            continue
        block_queries = []
        for block in profile.get("blocks") or []:
            for query in block.get("queries") or []:
                if query not in block_queries:
                    block_queries.append(query)
        add(label, "framework", profile.get("subject") or "",
            queries=block_queries, source=template)

    order = {"framework": 0, "model": 1, "theory": 2, "method": 3}
    return sorted(lenses.values(),
                  key=lambda row: (order.get(row["kind"], 9), _norm(row["name"])))


def build_queries(lens, max_queries=2):
    """One or two short queries for one lens.

    The first is the lens and its kind.  It is deliberately short: the source
    finder's relevance filter needs at least two query terms to appear in a
    title or abstract, and a long sentence would reject a correct paper that
    uses only the lens name.  The second is the first dimension query the
    worksheet profile already uses, which adds the vocabulary of the lens.
    """
    name = str(lens.get("name") or "").strip()
    if not name:
        return []
    kind = KIND_WORD.get(str(lens.get("kind") or "").upper()) or lens.get("kind") or "framework"
    # "AMO Framework framework" reads badly and wastes a query term.  The
    # display name keeps its own word; the query does not repeat it.
    base = re.sub(r"\s+(framework|model|theory|method)$", "", name, flags=re.I).strip() or name
    queries = ["%s %s" % (base, kind)]
    for block_query in lens.get("queries") or []:
        candidate = "%s %s" % (base, block_query)
        if len(candidate) <= 140 and _norm(candidate) not in {_norm(q) for q in queries}:
            queries.append(candidate)
        if len(queries) >= max_queries:
            break
    if len(queries) < max_queries:
        review = "%s review" % base
        if _norm(review) not in {_norm(q) for q in queries}:
            queries.append(review)
    return queries[:max(1, int(max_queries))]


def _search(query, databases=None, limit=5, year_from=None):
    """The pipeline's own academic adapters.  Imported lazily, never copied."""
    from bp.product import sources
    return sources.search_academic(query, databases=databases or SEED_DATABASES,
                                   limit=limit, year_from=year_from)


def _source_row(item):
    """One `seen_sources` row: the work, the layer that saw it, never used."""
    return {
        "title": item.get("title"),
        "doi": item.get("doi"),
        "url": item.get("url"),
        "venue": item.get("venue"),
        "year": item.get("year"),
        "abstract": item.get("abstract"),
        "source": item.get("database") or "api",
        "used": 0,
    }


def seed(connection, lenses, search=None, limit=5, since=0, max_queries=2,
         delay=0.0, log=None):
    """Search each lens once, store every work in the demand queue.

    `search` is injectable so the test suite can prove the storage contract
    without touching the network.  The report is returned, not printed only.
    """
    search = search or _search
    report = {
        "format": "bp-framework-seed/1",
        "started_at": lib.now(),
        "finished_at": None,
        "lenses": [],
        "totals": {"lenses": 0, "queries": 0, "results": 0, "candidates_new": 0,
                   "candidates_existing": 0, "already_in_corpus": 0, "errors": 0},
    }
    for index, lens in enumerate(lenses):
        queries = build_queries(lens, max_queries=max_queries)
        row = {"name": lens["name"], "kind": lens["kind"],
               "discipline": lens.get("discipline") or "",
               "queries": queries, "results": 0, "candidates_new": 0,
               "candidates_existing": 0, "already_in_corpus": 0, "errors": []}
        lens_seen = set()
        for query in queries:
            try:
                payload = search(query, databases=SEED_DATABASES, limit=limit,
                                 year_from=since or None)
            except Exception as error:  # one API failure is a report row, not a stop
                row["errors"].append({"query": query, "error": str(error)[:200]})
                continue
            results = payload.get("results") or []
            row["results"] += len(results)
            seen_rows = []
            for item in results:
                key = (lib.norm_doi(item.get("doi")) or lib.norm_url(item.get("url"))
                       or lib.norm_title(item.get("title")))
                if not key or key in lens_seen:
                    continue
                lens_seen.add(key)
                if lib.find_document_for(connection, doi=item.get("doi"), url=item.get("url"),
                                         title=item.get("title"), year=item.get("year")):
                    row["already_in_corpus"] += 1
                    continue
                existing = lib.find_candidate(connection, item)
                record = dict(item)
                record["source"] = item.get("database") or "api"
                record["reason"] = "framework seed: " + lens["name"]
                record["framework"] = lens["name"]
                candidate_id = lib.upsert_candidate(connection, record)
                if candidate_id:
                    if existing:
                        row["candidates_existing"] += 1
                    else:
                        row["candidates_new"] += 1
                seen_rows.append(_source_row(item))
            for error in payload.get("errors") or []:
                row["errors"].append({"query": query, "error": str(error)[:200]})
            # Record the seed search in the same learning log the pipeline uses,
            # so the dashboard shows the demand and the corpus hit rate is honest.
            lib.record_search(
                connection, query=query, subject=lens.get("discipline") or None,
                dimension="framework_seed", corpus_hits=0, live_hits=len(results),
                sources=seen_rows)
        report["lenses"].append(row)
        for key in ("queries", "results", "candidates_new", "candidates_existing",
                    "already_in_corpus"):
            report["totals"][key] += len(row[key]) if key == "queries" else row[key]
        report["totals"]["lenses"] += 1
        report["totals"]["errors"] += len(row["errors"])
        if log:
            log("%3d/%d  %-42s new=%-3d existing=%-3d corpus=%-3d errors=%d" % (
                index + 1, len(lenses), row["name"][:42], row["candidates_new"],
                row["candidates_existing"], row["already_in_corpus"], len(row["errors"])))
        if delay and index + 1 < len(lenses):
            time.sleep(delay)
    report["finished_at"] = lib.now()
    return report


def fetch_seeded(connection, limit=10, pause=1.5, log=None):
    """Fetch the open full text of the top framework-seeded candidates."""
    rows = connection.execute(
        "SELECT * FROM candidates WHERE status IN ('new', 'failed')"
        " AND framework IS NOT NULL"
        " ORDER BY status = 'failed', priority DESC, seen_count DESC LIMIT ?",
        (int(limit),)).fetchall()
    outcomes = {"ingested": 0, "duplicate": 0, "needs_decision": 0,
                "rejected": 0, "failed": 0}
    for index, row in enumerate(rows):
        outcome = enrich.fetch_one(connection, row)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if log:
            log("fetch  %-60s -> %s" % (str(row["title"] or "")[:60], outcome))
        if pause and index + 1 < len(rows):
            time.sleep(pause)
    return outcomes


def _filter_lenses(lenses, wanted):
    if not wanted:
        return lenses
    needles = [_norm(part) for part in str(wanted).split(",") if _norm(part)]
    selected = [lens for lens in lenses
                if any(needle in _norm(lens["name"]) for needle in needles)]
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Seed the corpus from every framework and theory the pipeline can name.")
    parser.add_argument("--dry-run", action="store_true",
                        help="list the lenses and their queries; no database, no network")
    parser.add_argument("--include-methods", action="store_true",
                        help="also seed the 59 quantitative methods (off by default)")
    parser.add_argument("--frameworks", default="",
                        help="comma-separated names or fragments to seed (default: all)")
    parser.add_argument("--max-frameworks", type=int, default=0,
                        help="stop after this many lenses (0 = all)")
    parser.add_argument("--limit", type=int, default=5,
                        help="results per query (default 5)")
    parser.add_argument("--max-queries", type=int, default=2,
                        help="queries per lens (default 2)")
    parser.add_argument("--since", type=int, default=0,
                        help="only works from this year onward (0 = no limit)")
    parser.add_argument("--delay", type=float, default=0.4,
                        help="seconds between lenses (default 0.4)")
    parser.add_argument("--fetch", type=int, default=10,
                        help="fetch the open full text of this many seeded candidates (0 = metadata only)")
    parser.add_argument("--no-index", action="store_true",
                        help="do not rebuild Meilisearch after a fetch")
    parser.add_argument("--report", default=os.path.join(ROOT, "corpus-state",
                                                         "framework_seed_report.json"),
                        help="where to write the JSON report")
    args = parser.parse_args(argv)

    # A zero limit would ask the API for nothing and look like an outage.
    args.limit = max(1, int(args.limit))
    args.max_queries = max(1, int(args.max_queries))
    args.fetch = max(0, int(args.fetch))
    args.max_frameworks = max(0, int(args.max_frameworks))

    lenses = _filter_lenses(load_lenses(args.include_methods), args.frameworks)
    if args.max_frameworks and args.max_frameworks > 0:
        lenses = lenses[:args.max_frameworks]
    if not lenses:
        print("No lens matched. Try --dry-run to see the names.", file=sys.stderr)
        return 2

    if args.dry_run:
        for lens in lenses:
            print("%-12s %-42s | %s" % (lens["kind"], lens["name"],
                                         " ; ".join(build_queries(lens, args.max_queries))))
        print("\n%d lens(es). No database or network was touched." % len(lenses))
        return 0

    # The worker runs in its own process, so it loads the keys itself.
    credentials = lib.load_source_credentials()
    if credentials["loaded"]:
        print("source credentials: " + ", ".join(credentials["loaded"])
              + " (from %s)" % credentials["path"], file=sys.stderr)

    connection = lib.connect()
    lib.apply_schema(connection)
    try:
        report = seed(connection, lenses, limit=args.limit, since=args.since,
                      max_queries=args.max_queries, delay=args.delay,
                      log=lambda line: print(line, flush=True))
        report["ranked"] = lib.rescore_candidates(connection)
        if args.fetch and args.fetch > 0:
            report["fetch"] = fetch_seeded(connection, args.fetch,
                                           log=lambda line: print(line, flush=True))
            if not args.no_index and report["fetch"].get("ingested"):
                try:
                    report["indexed_pages"] = lib.index_pages(connection)
                except Exception as error:
                    report["index_error"] = str(error)[:200]
        report["database"] = lib.DB_PATH
        with open(args.report, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
        totals = report["totals"]
        print("\n%d lens(es), %d queries, %d results: %d new candidate(s), "
              "%d already queued, %d already in the corpus, %d error(s)." % (
                  totals["lenses"], totals["queries"], totals["results"],
                  totals["candidates_new"], totals["candidates_existing"],
                  totals["already_in_corpus"], totals["errors"]))
        print("%d candidate(s) ranked by demand." % report.get("ranked", 0))
        if "fetch" in report:
            print("fetch: " + json.dumps(report["fetch"]))
        if "indexed_pages" in report:
            print("indexed pages: %d" % report["indexed_pages"])
        elif report.get("index_error"):
            print("index skipped: %s" % report["index_error"], file=sys.stderr)
        print("report: %s" % args.report)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
