r"""Bulk research keywords from a Word file and enrich the corpus.

Reads backtick-quoted search phrases from a .docx, searches the local
academic source API (http://localhost:4001/api/sources/search) for each,
tries to download the PDF from the DOI URL or Unpaywall, ingests into corpus,
indexes to Meilisearch. Stops before 8 GB.

    python corpus-db/build/bulk_research_keywords.py C:\Users\Roderick\Downloads\SEARCH_KEYWORDS_BY_SUBJECT.docx [limit_per_keyword=5]
"""

import os
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib

LOCAL_API_URL = 'http://localhost:4001/api/sources/search'
UNPAYWALL_URL = 'https://api.unpaywall.org/v2/{doi}?email=research@example.com'

MAX_TOTAL_GB = 8.0
RESERVE_GB = 2.0
MAX_INGEST_GB = MAX_TOTAL_GB - RESERVE_GB
REQUEST_DELAY = 1.0
UNPAYWALL_DELAY = 0.5
MAX_RETRIES = 3


def read_docx_keywords(path):
    """Extract backtick-quoted search phrases from a .docx document."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    phrases = []
    for para in root.findall(".//w:p", ns):
        text = "".join(t.text or "" for t in para.findall(".//w:t", ns))
        found = re.findall(r"`([^`]+)`", text)
        phrases.extend(found)
    seen = set()
    unique = []
    for p in phrases:
        p = p.strip().strip('"').strip()
        if not p or len(p) < 3:
            continue
        if "/" in p or "\\" in p or p.endswith(".py") or p.endswith(".md") or p.endswith(".html"):
            continue
        if p.count(".") > 2:
            continue
        if p.startswith("http") or p.startswith("www"):
            continue
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
    return unique


def current_total_gb(connection):
    total = 0
    for row in connection.execute("SELECT local_path FROM documents"):
        try:
            total += os.path.getsize(row[0])
        except OSError:
            pass
    return total / (1024 ** 3)


def search_local_api(keyword, limit):
    """Search the local academic source API for one keyword."""
    payload = json.dumps({"topic": keyword, "maxResults": limit}).encode('utf-8')
    req = urllib.request.Request(LOCAL_API_URL, data=payload,
                                 headers={'Content-Type': 'application/json'},
                                 method='POST')
    for attempt in range(MAX_RETRIES):
        try:
            response = urllib.request.urlopen(req, timeout=30)
            result = json.loads(response.read().decode('utf-8'))
            return result.get("sources", [])
        except Exception as e:
            msg = str(e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print("  API error for %r: %s" % (keyword, msg))
            return []
    return []


def get_unpaywall_pdf(doi):
    """Query Unpaywall for an open-access PDF URL."""
    if not doi:
        return None, None
    url = UNPAYWALL_URL.format(doi=doi)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=30)
        data = json.loads(response.read().decode('utf-8'))
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf")
        licence = best.get("license")
        return pdf_url, licence
    except Exception:
        return None, None


def download_pdf(url):
    """Download a PDF from a URL."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response = urllib.request.urlopen(req, timeout=60)
        raw = response.read()
        if raw.startswith(b'%PDF'):
            return raw
        return None
    except Exception:
        return None


def research_and_ingest(keyword, limit, connection):
    """Search the local API for one keyword, ingest open-access PDFs found."""
    results = search_local_api(keyword, limit)

    ingested = 0
    skipped = 0
    for item in results:
        try:
            current_gb = current_total_gb(connection)
        except Exception:
            current_gb = 0
        if current_gb >= MAX_INGEST_GB:
            print("  STOP: 8 GB limit reached (%.2f GB used)" % current_gb)
            return ingested, skipped

        title = item.get("title") or ""
        doi = item.get("doi") or ""
        url = item.get("url") or ""
        year = item.get("year")
        authors = item.get("authors") or ""
        venue = item.get("venue") or ""

        # Try Unpaywall first to find an open-access PDF URL
        pdf_url, licence = get_unpaywall_pdf(doi)
        if not pdf_url:
            # Fallback: try the DOI URL directly (some DOIs serve PDFs)
            if doi and doi.startswith("https://doi.org/"):
                pdf_url = doi
                licence = None
            elif doi and doi.startswith("10."):
                pdf_url = "https://doi.org/" + doi
                licence = None

        if not pdf_url:
            skipped += 1
            continue

        # Download the PDF
        try:
            raw = download_pdf(pdf_url)
        except Exception:
            skipped += 1
            continue

        if not raw:
            skipped += 1
            continue

        meta = {
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "doi": doi,
            "kind": "journal-article",
            "subject": lib.classify_subject(title),
            "licence": licence,
            "licence_verified": 1 if licence else 0,
            "source_url": url,
            "metadata_source": "local_api+unpaywall",
            "metadata_verified": 1,
        }
        status, doc_id, message = lib.ingest_pdf(
            connection, raw, meta,
            filename="%s.pdf" % (doi or url.replace("/", "_")))
        if status == "ingested":
            ingested += 1
            print("  OK: %s (%s)" % (title[:60], licence or "unknown"))
        else:
            skipped += 1

        time.sleep(UNPAYWALL_DELAY)

    return ingested, skipped


def main():
    if len(sys.argv) < 2:
        print("Usage: python bulk_research_keywords.py keywords.docx [limit_per_keyword=5]")
        return 1
    docx_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print("Reading keywords from: %s" % docx_path)
    keywords = read_docx_keywords(docx_path)
    print("Found %d keyword(s)" % len(keywords))

    connection = lib.connect()
    lib.apply_schema(connection)

    start_gb = current_total_gb(connection)
    print("Current corpus size: %.2f GB" % start_gb)
    print("Target ceiling: %.2f GB (reserve %.2f GB)" % (MAX_TOTAL_GB, RESERVE_GB))

    total_ingested = 0
    total_skipped = 0

    for i, kw in enumerate(keywords, 1):
        try:
            current_gb = current_total_gb(connection)
        except Exception:
            current_gb = 0
        if current_gb >= MAX_INGEST_GB:
            print("\nSTOP: 8 GB limit reached (%.2f GB used). Halting enrichment." % current_gb)
            break

        print("\n[%d/%d] Researching: %s" % (i, len(keywords), kw))
        try:
            ing, skip = research_and_ingest(kw, limit, connection)
        except Exception as error:
            print("  ERROR: %s" % error)
            continue
        total_ingested += ing
        total_skipped += skip
        print("  -> ingested: %d, skipped: %d (total ingested: %d)" % (ing, skip, total_ingested))

        time.sleep(REQUEST_DELAY)

    try:
        count = lib.index_pages(connection)
        print("\nIndexed %d pages to Meilisearch" % count)
    except Exception as error:
        print("Indexing skipped (Meilisearch may be down): %s" % error)

    connection.close()

    print("\n=== DONE ===")
    print("Total ingested: %d" % total_ingested)
    print("Total skipped: %d" % total_skipped)
    print("Run rclone sync to copy new PDFs to R2:")
    print('  rclone sync "D:\\SMART BUSINESSWRITER\\corpus-db\\pdfs" "corpus-r2:smart-business-writer-corpus/pdfs"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
