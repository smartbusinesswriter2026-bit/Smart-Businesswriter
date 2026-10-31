"""Bulk-import a folder of PDFs into the corpus (build-time tool).

    python corpus-db/build/bulk_ingest.py "D:\\SMART BUSINESSWRITER\\DATABASE" --subject management
    python corpus-db/build/bulk_ingest.py "..." --subject management --estimate
    python corpus-db/build/bulk_ingest.py "..." --subject management --dry-run

Why this exists
---------------
`ingest.py` takes ONE file and four facts typed by hand. A library of hundreds
cannot be typed. This tool walks a folder, takes what the file name actually
says, and refuses to guess the rest: a gap stays NULL.

The file name is read as `Author_Year_title-slug.pdf`, the pattern most
reference managers export. Only the year is parsed strictly. The author and the
title are best-effort, and they are recorded as `metadata_source = 'filename'`
with `metadata_verified = 0`, because a file name is not a catalogue record.
Every document therefore carries, in the database, the fact that its metadata
was never verified. That is the point: a gap you can see, not a fact you cannot.

`--estimate` costs a few seconds and tells you the real work before you spend
hours on it: how many pages there are, how many need optical character reading,
and roughly how long that will take.

Nothing here is imported by the pipeline. It is a build-time tool, so it may use
`pypdf`; the running product still uses the standard library only.
"""

import argparse
import csv
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus_lib as lib

#: The pipeline's own subject ids (CORPUS_DB.md C-08). A build that invents a
#: twelfth subject would need a mapping table forever, so it is refused here.
SUBJECTS = ("accounting", "finance", "economics", "management", "project-management",
            "entrepreneurship", "operations", "supply-chain", "marketing", "people",
            "research")

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

#: A rough cost, used only by `--estimate`. A page with a text layer is nearly
#: free; a scanned page is the expensive one. Measured on a normal laptop CPU,
#: and deliberately pessimistic so the estimate is not a promise it cannot keep.
SECONDS_PER_OCR_PAGE = 2.0
SECONDS_PER_TEXT_PAGE = 0.02


def parse_name(filename):
    """What the file name says, and nothing it does not.

    'A.-Bonini_2024_the-relationship-...-review.pdf'
        -> authors 'Bonini', year 2024, title 'The relationship ... review'

    No year in the name means year is None, not a guess from the title.

    An ISBN is taken from the name only when the digits are a real ISBN — the
    checksum is verified, so a page range or a year in the name cannot be
    mistaken for one.
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    parts = [part for part in re.split(r"[_]+", stem) if part.strip()]
    isbn = _isbn_in(stem)
    year = None
    for index, part in enumerate(parts):
        if YEAR_RE.match(part.strip()):
            year = int(part.strip())
            authors = _authors(" ".join(parts[:index]))
            title = " ".join(parts[index + 1:])
            return {"authors": authors, "year": year, "title": _tidy(title) or stem,
                    "isbn": isbn}
    return {"authors": "", "year": None, "title": _tidy(stem), "isbn": isbn}


def _isbn_in(text):
    """The first run of digits in `text` that is a valid ISBN, or None."""
    for run in re.findall(r"[0-9][0-9Xx\-\s]{8,16}[0-9Xx]", text or ""):
        digits = lib.norm_isbn(run)
        if digits:
            return digits
    return None


def _authors(text):
    """'A.-Bonini' -> 'Bonini'. Initials are dropped: they are not certain."""
    tokens = [token for token in re.split(r"[-_\s]+", text or "") if token.strip()]
    kept = [token for token in tokens if not re.fullmatch(r"[A-Z]\.?", token)]
    return " ".join(kept).strip()


def _tidy(slug):
    """'the-relationship-between-x' -> 'The relationship between x'."""
    text = re.sub(r"[-_]+", " ", slug or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:] if text else ""


def probe(path):
    """(pages, pages_without_text) for one PDF. Costs seconds, not minutes."""
    from pypdf import PdfReader
    reader = PdfReader(path)
    total = len(reader.pages)
    blank = 0
    for page in reader.pages[:3]:
        try:
            if len((page.extract_text() or "").strip()) < lib.MIN_PAGE_CHARS:
                blank += 1
        except Exception:
            blank += 1
    scanned = blank > 0 and blank == min(3, total)
    return total, (total if scanned else 0)


def find_pdfs(folder):
    found = []
    for root, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if name.lower().endswith(".pdf"):
                found.append(os.path.join(root, name))
    return found


def estimate(folder):
    """How much work the folder really is, before doing it."""
    files = find_pdfs(folder)
    text_pages = ocr_pages = unreadable = 0
    for path in files:
        try:
            total, needs_ocr = probe(path)
        except Exception:
            unreadable += 1
            continue
        ocr_pages += needs_ocr
        text_pages += total - needs_ocr
    seconds = text_pages * SECONDS_PER_TEXT_PAGE + ocr_pages * SECONDS_PER_OCR_PAGE
    return {"files": len(files), "text_pages": text_pages, "ocr_pages": ocr_pages,
            "unreadable": unreadable, "seconds": seconds}



def _iter_prepared(files, threads):
    """Yield (path, raw, pages, error) with at most `threads` PDFs being read at once.

    Extraction — especially optical character reading — is the slow part and it
    runs outside Python, so threads do help here. The window is bounded so a
    1.7 GB library is never held in memory at the same time.
    """
    if threads <= 1:
        for path in files:
            yield _prepare(path)
        return
    with ThreadPoolExecutor(max_workers=threads) as pool:
        window = []
        waiting = iter(files)
        for path in waiting:
            window.append(pool.submit(_prepare, path))
            if len(window) >= threads * 2:
                break
        while window:
            future = window.pop(0)
            yield future.result()
            following = next(waiting, None)
            if following is not None:
                window.append(pool.submit(_prepare, following))


def _prepare(path):
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as error:
        return path, None, None, "the file could not be read (%s)" % error
    try:
        return path, raw, lib.extract_pages(raw), None
    except Exception as error:
        return path, raw, None, "the PDF could not be read (%s)" % type(error).__name__


def import_folder(connection, folder, subject=None, kind="book", default_year=None,
                  dry_run=False, threads=1, limit=None, report_path=None, progress=None):
    """Import every PDF in a folder. Returns the report rows."""
    files = find_pdfs(folder)
    if limit:
        files = files[:limit]
    rows = []
    for index, (path, raw, pages, error) in enumerate(_iter_prepared(files, threads), start=1):
        meta = parse_name(path)
        meta.update({"kind": kind, "metadata_source": "filename", "metadata_verified": 0,
                     "local_path": path})
        if default_year and not meta["year"]:
            meta["year"] = default_year
        guessed = subject or lib.classify_subject(meta["title"])
        meta["subject"] = guessed if guessed in SUBJECTS else None
        if dry_run:
            status, doc_id = "would_ingest", None
            message = "%s pages" % (len(pages) if pages else 0)
        elif error:
            status, doc_id, message = "failed", None, error
        else:
            status, doc_id, message = lib.ingest_pdf(
                connection, raw, meta, local_path=path, pages=pages)
        rows.append({"file": os.path.basename(path), "status": status, "doc_id": doc_id or "",
                     "pages": len(pages) if pages else 0, "subject": meta["subject"] or "",
                     "year": meta["year"] or "", "title": meta["title"],
                     "message": message})
        if progress and index % 10 == 0:
            progress(index, len(files))
    if report_path and not dry_run:
        write_report(report_path, rows)
    return rows


def write_report(path, rows):
    fields = ["file", "status", "doc_id", "pages", "subject", "year", "title", "message"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarise(rows):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts



def main():
    parser = argparse.ArgumentParser(description="Import a folder of PDFs into the corpus.")
    parser.add_argument("folder", help="the folder to walk for .pdf files")
    parser.add_argument("--subject", choices=SUBJECTS, help="default subject (else guessed)")
    parser.add_argument("--kind", choices=sorted(lib.KIND_PREFIX), default="book")
    parser.add_argument("--year", type=int, help="year to use when the name has none")
    parser.add_argument("--limit", type=int, help="stop after this many files")
    parser.add_argument("--threads", type=int, default=1,
                        help="PDFs read at once (default 1; 2-4 is sensible)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the names and report, write nothing")
    parser.add_argument("--estimate", action="store_true",
                        help="measure pages and OCR need, then stop")
    parser.add_argument("--report", default=os.path.join(lib.CORPUS_DIR, "bulk_ingest_report.csv"))
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print("no such folder: %s" % args.folder)
        return 2

    if args.estimate:
        result = estimate(args.folder)
        hours = result["seconds"] / 3600.0
        print("files             : %d" % result["files"])
        print("pages with text   : %d (fast)" % result["text_pages"])
        print("pages needing OCR : %d (slow)" % result["ocr_pages"])
        if result["unreadable"]:
            print("unreadable        : %d" % result["unreadable"])
        print("roughly           : %.1f h on one core, %.1f h with %d threads"
              % (hours, hours / max(1, args.threads), args.threads))
        print("(an estimate, not a promise: SECONDS_PER_OCR_PAGE is a pessimistic guess)")
        return 0

    connection = lib.connect()
    started = time.time()
    rows = import_folder(
        connection, args.folder, subject=args.subject, kind=args.kind, default_year=args.year,
        dry_run=args.dry_run, threads=args.threads, limit=args.limit, report_path=args.report,
        progress=lambda done, total: print("  %d/%d" % (done, total)))
    connection.close()

    print("")
    print("done in %.1f s" % (time.time() - started))
    for status, count in sorted(summarise(rows).items()):
        print("  %-14s %d" % (status, count))
    if args.dry_run:
        for row in rows[:10]:
            print("  %s | %s | %s" % (row["year"] or "----", row["title"][:60], row["file"][:40]))
        print("  (dry run: nothing was written)")
    else:
        print("report: %s" % args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

