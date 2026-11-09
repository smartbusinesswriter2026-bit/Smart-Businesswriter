r"""Research the journal API and fill the corpus (and Cloudflare R2).

Run this from cmd after the journal API is up:

    python "D:\SMART BUSINESSWRITER\corpus-db\build\research_framework_topics.py"

What it does, in order:

1. Reads the harvest phrases from ``corpus-db/SEARCH_KEYWORDS_BY_SUBJECT.md``
   and adds the framework-aware phrases the new research layer routes to.
2. Asks the journal API for each phrase
   (``POST {JOURNAL_API_URL} {"topic": phrase, "maxResults": N}``).
3. Downloads the open-access PDF (Unpaywall first, then the DOI URL).
4. Ingests it into the local corpus (SQLite) with ``added_by="harvest"``.
   Duplicates are refused by the corpus, never written twice.
5. Indexes the new pages into Meilisearch.
6. With ``--sync-r2``, copies the PDFs to Cloudflare R2 with rclone.

The corpus database is the record; R2 is the off-site copy of the bytes.  The
script never invents metadata: a missing DOI, licence or year stays blank.

Examples
--------
    # preview only, no download, no write
    python research_framework_topics.py --dry-run

    # run, 5 results per phrase, stop at 6 GB
    python research_framework_topics.py --limit 5 --max-gb 6

    # run and copy the new PDFs to Cloudflare R2
    python research_framework_topics.py --limit 5 --sync-r2

    # one phrase only
    python research_framework_topics.py --query "porter five forces industry analysis"

Environment
-----------
    JOURNAL_API_URL   default http://localhost:4001/api/sources/search
    BP_CORPUS_DB      default corpus-db/corpus.sqlite
    BP_CORPUS_PDFS    default corpus-db/pdfs
    CORPUS_MEILI_URL  default http://127.0.0.1:7700
    CORPUS_MEILI_KEY  default empty
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import corpus_lib as lib  # noqa: E402

DEFAULT_API = os.environ.get("JOURNAL_API_URL", "http://localhost:4001/api/sources/search")
UNPAYWALL_URL = "https://api.unpaywall.org/v2/{doi}?email=research@example.com"
KEYWORDS_FILE = os.path.join(CORPUS_DIR, "SEARCH_KEYWORDS_BY_SUBJECT.md")
R2_CONFIG = os.path.join(HERE, "_secrets", "rclone_corpus.conf")
R2_REMOTE = "corpus-r2"
R2_BUCKET = "smart-business-writer-corpus"

#: The phrases the new framework-aware research layer routes to.  They mirror
#: the profile `queries` fields, so the corpus answers the same questions the
#: pipeline later searches for.
FRAMEWORK_QUERIES = [
    # PESTEL
    "government policy regulation trade sanctions",
    "economic growth inflation exchange rate demand",
    "demographics consumer behaviour labour market",
    "technology adoption digital infrastructure innovation",
    "climate emissions energy sustainability",
    "legislation compliance licensing regulation law",
    # Five Forces
    "competition intensity market share",
    "entry barriers new entrants",
    "substitute products switching",
    "buyer power consumer demand",
    "supplier power supply chain",
    # Business plan
    "market size growth demand industry spending",
    "consumer behaviour demand survey customers",
    "competition market share rival entrant",
    "regulation policy licence compliance permits",
    # Quality
    "workplace organisation and sorting",
    "root cause analysis process defect",
    "failure modes effects analysis fmea",
    "plan do check act improvement",
    # Portfolio / canvas
    "bcg growth share matrix portfolio",
    "ge mckinsey attractiveness business strength",
    "blue ocean strategy value innovation",
    "business model canvas customer segments",
    # Strategy / management
    "porter generic strategies cost leadership differentiation",
    "porter diamond national competitive advantage",
    "porter value chain primary support activities",
    "swot analysis strengths weaknesses opportunities threats",
    "scenario planning drivers signposts",
    "strategic groups mobility barriers",
    # Marketing
    "segmentation targeting positioning stp",
    "customer journey awareness consideration purchase",
    "marketing funnel conversion",
    "brand equity awareness loyalty",
    "digital marketing owned earned paid",
    # People / change
    "adkar change management awareness desire",
    "kotter eight steps change",
    "team development forming storming norming",
    "mckinsey 7s framework",
    # Project / operations
    "work breakdown structure project",
    "raci matrix responsibility",
    "risk register project response",
    "sipoc process mapping",
    "theory of constraints bottleneck",
    "sales and operations planning",
    # Leadership / culture / ethics
    "transformational leadership theory",
    "hofstede cultural dimensions",
    "ethical dilemma utilitarianism deontology",
    "stakeholder theory corporate social responsibility",
]


def read_markdown_keywords(path):
    """Every backtick-quoted phrase in the harvest document, deduplicated."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    phrases = re.findall(r"`([^`]+)`", text)
    seen, out = set(), []
    for phrase in phrases:
        phrase = phrase.strip().strip('"').strip()
        if len(phrase) < 4 or phrase in seen:
            continue
        if phrase.startswith(("http", "www")):
            continue
        if "/" in phrase or "\\" in phrase:
            continue
        if phrase.endswith((".py", ".md", ".html", ".json", ".csv", ".sql",
                            ".docx", ".bat", ".ps1", ".txt")):
            continue
        if "_" in phrase or ":" in phrase or "(" in phrase or ")" in phrase:
            continue
        # The harvest table holds phrases; a single token is a code name.
        if " " not in phrase:
            continue
        seen.add(phrase)
        out.append(phrase)
    return out


def all_queries(subject=None):
    """The markdown harvest phrases plus the framework phrases."""
    phrases = read_markdown_keywords(KEYWORDS_FILE)
    phrases.extend(FRAMEWORK_QUERIES)
    if subject:
        needle = subject.lower()
        phrases = [phrase for phrase in phrases if needle in phrase.lower()]
    seen, out = set(), []
    for phrase in phrases:
        if phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return out


def corpus_gb(connection):
    total = 0
    for row in connection.execute("SELECT local_path FROM documents"):
        try:
            total += os.path.getsize(row[0])
        except OSError:
            pass
    return total / (1024 ** 3)


def search_journal(api_url, phrase, limit, timeout=30):
    """POST one phrase to the journal API; return the source list."""
    payload = json.dumps({"topic": phrase, "maxResults": limit}).encode("utf-8")
    request = urllib.request.Request(
        api_url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as error:
        raise SystemExit(
            "The journal API did not answer at %s (%s).\n"
            "Start the journal API first, or set JOURNAL_API_URL to its search route."
            % (api_url, error))
    return data.get("sources") or []


def unpaywall_pdf(doi):
    """The open-access PDF URL for a DOI, or (None, None)."""
    if not doi:
        return None, None
    url = UNPAYWALL_URL.format(doi=doi)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        best = data.get("best_oa_location") or {}
        return best.get("url_for_pdf"), best.get("license")
    except Exception:
        return None, None


def download_pdf(url):
    """The PDF bytes, or None when the URL is not a PDF."""
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        return raw if raw.startswith(b"%PDF") else None
    except Exception:
        return None


def pdf_url_for(item):
    """The first URL that might serve the PDF, and its licence."""
    doi = str(item.get("doi") or "").strip()
    pdf_url, licence = unpaywall_pdf(doi)
    if pdf_url:
        return pdf_url, licence
    if doi.startswith("https://doi.org/"):
        return doi, None
    if doi.startswith("10."):
        return "https://doi.org/" + doi, None
    url = str(item.get("url") or "").strip()
    if url.lower().endswith(".pdf"):
        return url, None
    return None, None


def ingest_one(connection, item, dry_run=False):
    """Download and ingest one journal result. Returns 'ingested'/'skipped'."""
    title = str(item.get("title") or "").strip()
    doi = str(item.get("doi") or "").strip()
    url, licence = pdf_url_for(item)
    if not url:
        return "skipped", "no open full text"
    if dry_run:
        return "would ingest", title[:70]
    raw = download_pdf(url)
    if not raw:
        return "skipped", "not a PDF at %s" % url[:80]
    meta = {
        "title": title or "Untitled",
        "authors": item.get("authors") or "",
        "year": item.get("year"),
        "venue": item.get("venue") or "",
        "doi": doi,
        "kind": "journal-article",
        "subject": lib.classify_subject(title),
        "licence": licence,
        "licence_verified": 1 if licence else 0,
        "source_url": item.get("url") or "",
        "metadata_source": "journal_api+unpaywall",
        "metadata_verified": 1,
    }
    filename = "%s.pdf" % (re.sub(r"[^A-Za-z0-9._-]+", "_", doi or title)[:120] or "article")
    status, _doc_id, message = lib.ingest_pdf(connection, raw, meta, filename=filename,
                                              added_by="harvest")
    return status, message


def sync_r2(pdf_dir):
    """Copy the PDFs to Cloudflare R2 with the existing rclone config."""
    rclone = os.path.join(HERE, "tools", "rclone.exe")
    if not os.path.isfile(rclone):
        rclone = "rclone"
    if not os.path.isfile(R2_CONFIG):
        print("R2 sync skipped: no rclone config at %s" % R2_CONFIG)
        print("Create it with: python corpus-db/build/r2_credentials.py write")
        return False
    target = "%s:%s/pdfs" % (R2_REMOTE, R2_BUCKET)
    command = [rclone, "--config", R2_CONFIG, "sync", pdf_dir, target, "--progress"]
    print("R2 sync: %s -> %s" % (pdf_dir, target))
    try:
        return subprocess.call(command) == 0
    except OSError as error:
        print("R2 sync skipped: %s" % error)
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default=DEFAULT_API, help="journal API search URL")
    parser.add_argument("--query", action="append", default=[],
                        help="one phrase (repeatable); overrides the file")
    parser.add_argument("--subject", default=None, help="only phrases containing this word")
    parser.add_argument("--limit", type=int, default=5, help="results per phrase (default 5)")
    parser.add_argument("--max-gb", type=float, default=6.0, help="stop at this corpus size")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between phrases")
    parser.add_argument("--dry-run", action="store_true", help="list, download nothing")
    parser.add_argument("--sync-r2", action="store_true", help="copy the PDFs to Cloudflare R2")
    args = parser.parse_args(argv)

    queries = args.query or all_queries(args.subject)
    if not queries:
        print("No phrases to research. Check %s." % KEYWORDS_FILE)
        return 1

    connection = lib.connect()
    lib.apply_schema(connection)
    start_gb = corpus_gb(connection)
    print("Journal API : %s" % args.api)
    print("Corpus      : %s" % lib.DB_PATH)
    print("Phrases     : %d" % len(queries))
    print("Corpus size : %.2f GB (stop at %.2f GB)" % (start_gb, args.max_gb))
    if args.dry_run:
        print("DRY RUN: nothing will be downloaded or written.\n")

    ingested = skipped = 0
    for index, phrase in enumerate(queries, 1):
        if corpus_gb(connection) >= args.max_gb:
            print("\nSTOP: %.2f GB limit reached." % args.max_gb)
            break
        print("\n[%d/%d] %s" % (index, len(queries), phrase))
        try:
            results = search_journal(args.api, phrase, args.limit)
        except SystemExit:
            connection.close()
            raise
        if not results:
            print("  no results")
            continue
        for item in results:
            status, message = ingest_one(connection, item, dry_run=args.dry_run)
            if status in ("ingested", "would ingest"):
                ingested += 1
                print("  %s: %s" % (status, message))
            else:
                skipped += 1
                print("  %s: %s" % (status, message))
        time.sleep(args.delay)

    if not args.dry_run:
        try:
            pages = lib.index_pages(connection)
            print("\nIndexed %d pages into Meilisearch." % pages)
        except Exception as error:
            print("\nMeilisearch indexing skipped: %s" % error)

    final_gb = corpus_gb(connection)
    connection.close()
    print("\n=== DONE ===")
    print("Ingested: %d   Skipped: %d   Corpus: %.2f GB" % (ingested, skipped, final_gb))

    if args.sync_r2 and not args.dry_run:
        sync_r2(lib.PDF_DIR)
    elif not args.dry_run:
        print("\nCopy the new PDFs to Cloudflare R2 with:")
        print('  python "%s" --sync-r2' % os.path.abspath(__file__))
        print("or run rclone directly with the config in %s" % R2_CONFIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
