"""Ingest one PDF into the corpus.

    python corpus-db/build/ingest.py book.pdf --title "Financial Accounting" \
        --authors "Weygandt; Kimmel" --year 2019 --subject accounting --kind book \
        --publisher "Wiley" --edition "9th"

Requires: pypdf. Scanned books also need pypdfium2 and pytesseract plus a local
Tesseract binary.

Nothing is inferred. `printed_page` is NULL in v1, a missing edition is NULL, a
missing licence is NULL. A PDF that is already in the corpus is refused rather
than ingested twice, because the re-ingest policy (Q-15) is still open.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib


def main():
    parser = argparse.ArgumentParser(description="Ingest one PDF into the corpus database.")
    parser.add_argument("pdf")
    parser.add_argument("--title", required=True)
    parser.add_argument("--authors", required=True, help="'; ' separated, family first")
    parser.add_argument("--year", type=int)
    parser.add_argument("--subject", required=True, help="a pipeline subject id")
    parser.add_argument("--kind", choices=sorted(lib.KIND_PREFIX), required=True)
    parser.add_argument("--publisher")
    parser.add_argument("--edition")
    parser.add_argument("--isbn")
    parser.add_argument("--doi")
    parser.add_argument("--venue")
    parser.add_argument("--volume")
    parser.add_argument("--issue")
    parser.add_argument("--licence")
    parser.add_argument("--source-url")
    parser.add_argument("--no-index", action="store_true", help="skip the Meilisearch push")
    args = parser.parse_args()

    with open(args.pdf, "rb") as handle:
        raw = handle.read()

    meta = {
        "title": args.title, "authors": args.authors, "year": args.year,
        "publisher": args.publisher, "edition": args.edition, "isbn": args.isbn,
        "doi": args.doi, "venue": args.venue, "volume": args.volume, "issue": args.issue,
        "kind": args.kind, "subject": args.subject, "licence": args.licence,
        "source_url": args.source_url, "metadata_source": "manual",
    }
    connection = lib.connect()
    lib.apply_schema(connection)
    status, doc_id, message = lib.ingest_pdf(connection, raw, meta, local_path=os.path.abspath(args.pdf))
    if status == "ingested" and not args.no_index:
        try:
            count = lib.index_pages(connection)
            print("indexed %d pages" % count)
        except Exception as error:
            print("WARNING: the pages were ingested but not indexed (%s)" % error, file=sys.stderr)
    connection.close()
    print("%s  %s  %s" % (status, doc_id or "-", message))
    return 0 if status in ("ingested", "duplicate") else 1


if __name__ == "__main__":
    raise SystemExit(main())
