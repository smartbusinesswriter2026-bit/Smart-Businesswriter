"""Bulk ingest every PDF in D:\SMART BUSINESSWRITER\DATABASE\ into the corpus database.

Usage:
    python corpus-db/build/bulk_ingest_dir.py

No per-file input required. Metadata defaults:
  - title: from filename (cleaned)
  - authors: "Unknown" (you can edit later in the admin UI)
  - year: NULL
  - subject: guessed from filename keywords, else "management"
  - kind: "book"
  - licence: NULL (recorded as unknown, never guessed)

Duplicates are refused automatically by ingest_pdf() (same file or same work).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib


SUBJECT_HINTS = {
    "accounting": ["accounting", "financial", "managerial"],
    "finance": ["finance", "investment", "portfolio"],
    "economics": ["economics", "economic", "macro", "micro"],
    "management": ["management", "leadership", "strategy", "organizational"],
    "marketing": ["marketing", "consumer", "brand"],
    "operations": ["operations", "supply chain", "logistics", "scm"],
    "people": ["human resource", "hrm", "employee", "workforce"],
    "research": ["research", "study", "analysis", "theory"],
    "entrepreneurship": ["entrepreneur", "startup", "venture", "msme"],
    "supply-chain": ["supply chain", "procurement", "supplier"],
    "project-management": ["project management", "pmp", "schedule"],
}


def guess_subject(filename):
    lowered = filename.lower()
    for subject, keywords in SUBJECT_HINTS.items():
        if any(kw in lowered for kw in keywords):
            return subject
    return "management"


def clean_title(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def main():
    database_dir = r"D:\SMART BUSINESSWRITER\DATABASE"
    if not os.path.isdir(database_dir):
        print(f"ERROR: directory not found: {database_dir}")
        return 1

    pdf_files = sorted(
        f for f in os.listdir(database_dir)
        if f.lower().endswith(".pdf")
    )

    if not pdf_files:
        print("No PDF files found in", database_dir)
        return 0

    print(f"Found {len(pdf_files)} PDF(s). Starting bulk ingest...\n")

    connection = lib.connect()
    lib.apply_schema(connection)

    ingested = 0
    skipped = 0
    failed = 0

    for filename in pdf_files:
        filepath = os.path.join(database_dir, filename)
        title = clean_title(filename)
        subject = guess_subject(filename)
        meta = {
            "title": title,
            "authors": "Unknown",
            "year": None,
            "publisher": None,
            "edition": None,
            "isbn": None,
            "doi": None,
            "venue": None,
            "volume": None,
            "issue": None,
            "kind": "book",
            "subject": subject,
            "licence": None,
            "source_url": None,
            "metadata_source": "manual",
        }

        try:
            with open(filepath, "rb") as fh:
                raw = fh.read()
        except Exception as error:
            print(f"  FAIL (read): {filename} - {error}")
            failed += 1
            continue

        status, doc_id, message = lib.ingest_pdf(connection, raw, meta, local_path=filepath)

        safe_filename = filename.encode("ascii", errors="replace").decode("ascii")
        safe_message = message.encode("ascii", errors="replace").decode("ascii")
        if status == "ingested":
            print(f"  OK: {safe_filename} -> {doc_id} ({safe_message})")
            ingested += 1
        elif status == "duplicate":
            print(f"  SKIP (duplicate): {safe_filename} - {safe_message}")
            skipped += 1
        else:
            print(f"  FAIL (ingest): {safe_filename} - {safe_message}")
            failed += 1

    connection.close()

    print(f"\nDone. Ingested: {ingested}, Skipped (duplicates): {skipped}, Failed: {failed}, Total: {len(pdf_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
