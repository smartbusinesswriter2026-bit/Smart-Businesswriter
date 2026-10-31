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
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus_lib as lib

#: Some PDFs carry a broken cross-reference table and pypdf says so, once per bad
#: pointer - hundreds of lines that bury the result and make the tool look stuck.
#: They are recoverable warnings about the file, not errors in the run.
logging.getLogger("pypdf").setLevel(logging.ERROR)

#: The pipeline's own subject ids (CORPUS_DB.md C-08). A build that invents a
#: twelfth subject would need a mapping table forever, so it is refused here.
SUBJECTS = ("accounting", "finance", "economics", "management", "project-management",
            "entrepreneurship", "operations", "supply-chain", "marketing", "people",
            "research")

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

#: A DOI as it is printed in a document or a file name.
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")

#: A DOI whose "/" was replaced by a file-name sanitiser: '10.2139-ssrn.7556958'.
#: This is enough to prove the document is an article, but the mangled form is
#: NOT stored as the identifier, because it is not the identifier.
DOI_MANGLED_RE = re.compile(r"10\.\d{4,9}[-_][-._;()/:A-Za-z0-9]+")


def _doi_in(text):
    """The first DOI printed in `text`, in the corpus's canonical form, or None.

    A file extension is not part of a DOI, but the pattern would swallow it
    ('10.1000/abc.1.pdf'), so it is stripped before the value is kept.
    """
    match = DOI_RE.search(text or "")
    if not match:
        return None
    value = re.sub(r"\.(?:pdf|html?|txt|docx?)$", "", match.group(0), flags=re.IGNORECASE)
    return lib.norm_doi(value.rstrip(".,;"))


def resolve_kind(name, pages, wanted):
    """(kind, doi, where the kind was decided) for one file.

    `wanted` is what the run asked for. 'auto' decides from the document:

        1. a DOI written properly in the file name      -> article, that DOI
        2. a DOI printed on the first page               -> article, that DOI
        3. a DOI in the name with its '/' mangled to '-' -> article, no DOI stored
        4. nothing                                       -> book

    A journal article and a book are shaped differently in a citation, so
    recording an article as a book produces a wrong reference. Case 3 matters
    because a file name cannot contain '/', so the owner's exported names carry
    '10.2139-ssrn.7556958' where the article says '10.2139/ssrn.7556958'. That is
    enough to know it is an article, and not enough to state the DOI: the page
    text still gets the chance to supply the real one, and if it does not, the
    field stays empty rather than carrying a repaired identifier as if read.
    """
    if wanted != "auto":
        return wanted, None, "asked-for"
    doi = _doi_in(name)
    if doi:
        return "journal-article", doi, "filename"
    if pages:
        doi = _doi_in((pages[0][1] or "")[:800])
        if doi:
            return "journal-article", doi, "page-text"
    if DOI_MANGLED_RE.search(os.path.basename(name or "")):
        return "journal-article", None, "filename-hint"
    return "book", None, None



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


def estimate(folder, sample=None, progress=None):
    """How much work the folder really is, before doing it.

    `sample` measures only the first N files and scales the answer up. A full
    measurement of a large library is itself an hour of reading, which defeats
    the point of measuring before you commit; a sample of 15 files answers the
    same question in a minute and is labelled as a sample.

    `progress` is called every ten files, because a tool that prints nothing for
    ten minutes is indistinguishable from one that has hung.
    """
    files = find_pdfs(folder)
    if not files:
        return {"files": 0, "measured": 0, "text_pages": 0, "ocr_pages": 0,
                "unreadable": 0, "seconds": 0.0, "sampled": False}
    measured = files[:sample] if sample else files
    text_pages = ocr_pages = unreadable = 0
    for index, path in enumerate(measured, start=1):
        try:
            total, needs_ocr = probe(path)
        except Exception:
            unreadable += 1
            continue
        ocr_pages += needs_ocr
        text_pages += total - needs_ocr
        if progress and index % 10 == 0:
            progress(index, len(measured))
    scale = float(len(files)) / len(measured)
    seconds = (text_pages * SECONDS_PER_TEXT_PAGE
               + ocr_pages * SECONDS_PER_OCR_PAGE) * scale
    return {"files": len(files), "measured": len(measured),
            "text_pages": int(text_pages * scale), "ocr_pages": int(ocr_pages * scale),
            "unreadable": unreadable, "seconds": seconds, "sampled": bool(sample)}




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


def import_folder(connection, folder, subject=None, kind="auto", default_year=None,
                  dry_run=False, threads=1, limit=None, report_path=None, progress=None,
                  index=False, index_rebuild=False):
    """Import every PDF in a folder. Returns the report rows.

    `index` pushes the whole corpus into Meilisearch once at the end, which is
    what makes the imported pages findable. It is done once for the run rather
    than once per file: the index is rebuilt from the database, so a hundred
    separate pushes would do the same work a hundred times.
    """
    files = find_pdfs(folder)
    if limit:
        files = files[:limit]
    rows = []
    for position, (path, raw, pages, error) in enumerate(_iter_prepared(files, threads), start=1):
        meta = parse_name(path)
        meta.update({"kind": kind, "metadata_source": "filename", "metadata_verified": 0,
                     "local_path": path})
        file_kind, found_doi, doi_from = resolve_kind(os.path.basename(path), pages, kind)
        meta["kind"] = file_kind
        if found_doi and not meta.get("doi"):
            meta["doi"] = found_doi
            # Say where each fact came from: the DOI was read out of the document,
            # not inferred, and nothing here is verified against a catalogue.
            meta["metadata_source"] = ("filename+%s" % doi_from
                                       if doi_from == "page-text" else "filename")
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
                     "kind": meta["kind"], "doi": meta.get("doi") or "",
                     "pages": len(pages) if pages else 0, "subject": meta["subject"] or "",
                     "year": meta["year"] or "", "title": meta["title"],
                     "message": message})
        if progress and position % 10 == 0:
            progress(position, len(files))
    if report_path and not dry_run:
        write_report(report_path, rows)
    if index and not dry_run:
        try:
            lib.index_pages(connection, rebuild=index_rebuild)
        except Exception as error:
            # The pages are in the database, which is the truth; only the copy
            # is missing. Say so rather than failing the import.
            print("WARNING: the pages were ingested but not indexed (%s)" % error,
                  file=sys.stderr)
    return rows


def write_report(path, rows):
    fields = ["file", "status", "doc_id", "kind", "doi", "pages", "subject", "year", "title",
              "message"]
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
    parser.add_argument("--kind", choices=["auto"] + sorted(lib.KIND_PREFIX), default="auto",
                        help="auto (the default) reads a DOI from the file name or the first "
                             "page: a DOI means journal-article, none means book")
    parser.add_argument("--year", type=int, help="year to use when the name has none")
    parser.add_argument("--limit", type=int, help="stop after this many files")
    parser.add_argument("--threads", type=int, default=1,
                        help="PDFs read at once (default 1; 2-4 is sensible)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the names and report, write nothing")
    parser.add_argument("--estimate", action="store_true",
                        help="measure pages and OCR need, then stop")
    parser.add_argument("--sample", type=int,
                        help="with --estimate: measure only the first N files and scale up")
    parser.add_argument("--no-index", action="store_true",
                        help="do not push the pages into Meilisearch after importing")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="empty the search index before filling it, so it holds exactly "
                             "the pages the database holds and no stale ones")
    parser.add_argument("--report", default=os.path.join(lib.CORPUS_DIR, "bulk_ingest_report.csv"))
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print("no such folder: %s" % args.folder)
        return 2

    if args.estimate:
        print("reading %d file(s); progress prints every 10" % args.sample
              if args.sample else "reading every PDF; progress prints every 10")
        result = estimate(args.folder, sample=args.sample,
                          progress=lambda done, total: print("  %d/%d" % (done, total)))
        hours = result["seconds"] / 3600.0
        if result["sampled"]:
            print("measured          : %d of %d files (a sample, scaled up)"
                  % (result["measured"], result["files"]))
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
        progress=lambda done, total: print("  %d/%d" % (done, total)),
        index=not args.no_index, index_rebuild=args.rebuild_index)
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
        print("index : %s" % ("skipped (--no-index)" if args.no_index
                              else "pushed to Meilisearch"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

