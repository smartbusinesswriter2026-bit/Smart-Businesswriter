"""Probe the live Meilisearch index against the corpus database.

Answers three questions the restore test depends on:
  1. Which document set does the live index hold (is it exactly the pages table)?
  2. Is there a known phrase that resolves to one doc_id + pdf_page?
  3. Does the live index answer that phrase the same way the database says it should?
"""
import json
import re
import sqlite3
import urllib.request

DB = r"D:\SMART BUSINESSWRITER\corpus-db\corpus.sqlite"
MEILI = "http://127.0.0.1:7700"


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

db_rows = cursor.execute(
    "SELECT doc_id, doc_version, pdf_page FROM pages ORDER BY doc_id, pdf_page"
).fetchall()
db_set = {(row["doc_id"], row["pdf_page"]) for row in db_rows}
print("pages in database:", len(db_rows), "distinct (doc_id, pdf_page):", len(db_set))

hits = search({"q": "", "limit": 20000})
index_pairs = [(hit["doc_id"], hit["pdf_page"]) for hit in hits["hits"]]
print("documents in live index:", len(index_pairs))
print("estimated total hits:", hits.get("estimatedTotalHits"))
only_index = sorted(set(index_pairs) - db_set)
only_db = sorted(db_set - set(index_pairs))
print("in index but not in db:", only_index[:10])
print("in db but not in index:", only_db[:10])

# A phrase that is distinctive enough to resolve to a single page.
stop = set(
    """the and for that with this from have has had are was were will would could
    should can may might must not but they them their there these those which
    when what where while more most other into over under about after before
    than then also been being were been such some any each per its it's his her
    our your our you we us i me my""".split()
)
candidate = None
for row in db_rows:
    page = cursor.execute(
        "SELECT text FROM pages WHERE doc_id=? AND pdf_page=?", (row["doc_id"], row["pdf_page"])
    ).fetchone()
    text = page["text"] or ""
    if len(text) < 600:
        continue
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 60]
    for sentence in sentences:
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", sentence)
        if len(words) < 6:
            continue
        phrase = " ".join(words[1:6])
        terms = [w.lower() for w in words[1:6]]
        if any(term in stop for term in terms):
            continue
        count = cursor.execute(
            "SELECT COUNT(*) FROM pages WHERE lower(text) LIKE ?", ("%" + phrase.lower() + "%",)
        ).fetchone()[0]
        if count == 1:
            candidate = (row["doc_id"], row["pdf_page"], phrase)
            break
    if candidate:
        break

print("candidate phrase:", candidate)
if candidate:
    doc_id, pdf_page, phrase = candidate
    result = search({"q": phrase, "limit": 5})
    print("live index hits for the phrase:")
    for hit in result["hits"][:5]:
        print("   ", hit["doc_id"], "pdf_page", hit["pdf_page"], "|", hit["title"][:50])
    top = result["hits"][0]
    print("top hit matches the database page:", top["doc_id"] == doc_id and top["pdf_page"] == pdf_page)
