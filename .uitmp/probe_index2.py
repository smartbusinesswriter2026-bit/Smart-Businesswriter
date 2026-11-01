"""Second probe: the stale index document, the phrase, and the two on-disk index copies."""
import json
import os
import re
import sqlite3
import urllib.request

DB = r"D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite"
MEILI = "http://127.0.0.1:7700"


def get(path):
    with urllib.request.urlopen(MEILI + path, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def search(payload):
    request = urllib.request.Request(
        MEILI + "/indexes/pages/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


connection = sqlite3.connect(DB)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

print("--- documents table ---")
for row in cursor.execute("SELECT doc_id, title, pages_total, added_at FROM documents ORDER BY added_at"):
    print("  ", row["doc_id"], "| pages_total", row["pages_total"], "|", (row["title"] or "")[:45])

print("--- is bk-722dae144926 in the database? ---")
print("  documents:", cursor.execute("SELECT COUNT(*) FROM documents WHERE doc_id='bk-722dae144926'").fetchone()[0])
print("  pages:", cursor.execute("SELECT COUNT(*) FROM pages WHERE doc_id='bk-722dae144926'").fetchone()[0])
print("  pages with version>1:", cursor.execute("SELECT COUNT(*) FROM pages WHERE doc_version>1").fetchone()[0])

print("--- full index document list via the documents API (paginated) ---")
pairs = []
offset = 0
while True:
    batch = get("/indexes/pages/documents?limit=1000&offset=%d&fields=doc_id,pdf_page" % offset)
    if isinstance(batch, dict):
        print("  documents API returned:", json.dumps(batch)[:200])
        break
    if not batch:
        break
    pairs.extend((doc["doc_id"], doc["pdf_page"]) for doc in batch)
    offset += len(batch)
    if len(batch) < 1000:
        break
db_pairs = {(r["doc_id"], r["pdf_page"]) for r in cursor.execute("SELECT doc_id, pdf_page FROM pages")}
index_pairs = set(pairs)
print("  index documents:", len(pairs), "| unique:", len(index_pairs), "| db pages:", len(db_pairs))
print("  only in index:", sorted(index_pairs - db_pairs)[:10])
print("  only in db:", sorted(db_pairs - index_pairs)[:10])

print("--- a clean known phrase ---")
stop = set(
    """the and for that with this from have has had are was were will would could
    should can may might must not but they them their there these those which
    when what where while more most other into over under about after before
    than then also been being such some any each per its his her our your you
    we us our i me my one two three first second new used using use""".split()
)
best = None
for row in cursor.execute("SELECT doc_id, pdf_page, text FROM pages WHERE length(text) BETWEEN 700 AND 2500"):
    text = row["text"]
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", sentence)
        if len(words) < 9:
            continue
        for start in range(0, min(6, len(words) - 6)):
            phrase_words = words[start:start + 5]
            terms = [w.lower() for w in phrase_words]
            if any(term in stop for term in terms):
                continue
            if len(set(terms)) < 4:
                continue
            phrase = " ".join(phrase_words)
            count = cursor.execute(
                "SELECT COUNT(*) FROM pages WHERE lower(text) LIKE ?", ("%" + phrase.lower() + "%",)
            ).fetchone()[0]
            if count == 1:
                best = (row["doc_id"], row["pdf_page"], phrase)
                break
        if best:
            break
    if best:
        break
print("  phrase:", best)
if best:
    result = search({"q": best[2], "limit": 5})
    for hit in result["hits"][:5]:
        print("   hit:", hit["doc_id"], "pdf_page", hit["pdf_page"], "|", hit["title"][:45])
    top = result["hits"][0]
    print("  top hit == database page:", top["doc_id"] == best[0] and top["pdf_page"] == best[1])

print("--- on-disk index copies ---")
for root in [r"D:\SMART BUSINESSWRITER\corpus-db\meili", r"D:\SMART BUSINESSWRITER\corpus-state\meili"]:
    print("  ", root, os.path.isdir(root))
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, "indexes")):
            depth = dirpath[len(root):].count(os.sep)
            if depth <= 2:
                print("      ", dirpath[len(root):], sorted(filenames)[:4])
