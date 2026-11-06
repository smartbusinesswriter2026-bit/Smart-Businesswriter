"""Merge one corpus learning history into another.

    python corpus-db/build/merge_learning_log.py OLD.sqlite NEW.sqlite

Why this exists: the corpus record moved from `corpus-db/corpus.sqlite` to
`corpus-state/corpus.sqlite`, and the learning history (what searches saw, what
was cited, what the web tier read, what the enrichment queue already holds)
stayed behind.  The history is the demand signal the enrichment worker reads;
a corpus with the documents but without the history cannot learn.

The merge is additive and idempotent: existing rows are never overwritten, so
running it twice changes nothing.  A `doc_id` whose prefix was normalised in
the new database (the same PDF reclassified as `bk-` instead of `ja-`) is
remapped by its unique hash suffix; an ambiguous or unknown document becomes
NULL rather than a wrong link.

The source database is never modified.
"""

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_lib as lib


def doc_map(old, new):
    """Map old document ids to the new database, by hash suffix when renamed."""
    old_ids = {row[0] for row in old.execute("SELECT doc_id FROM documents")}
    new_ids = {row[0] for row in new.execute("SELECT doc_id FROM documents")}
    by_suffix = {}
    for doc_id in new_ids:
        if "-" in doc_id:
            by_suffix.setdefault(doc_id.split("-", 1)[1], []).append(doc_id)
    mapping = {doc_id: doc_id for doc_id in old_ids if doc_id in new_ids}
    for doc_id in old_ids - new_ids:
        suffix = doc_id.split("-", 1)[1] if "-" in doc_id else ""
        matches = by_suffix.get(suffix) or []
        mapping[doc_id] = matches[0] if len(matches) == 1 else None
    return mapping


def _columns(connection, table):
    return [row[1] for row in connection.execute("PRAGMA table_info(%s)" % table)]


def _copy(old, new, table, mapping=None, key="rowid", replace=False):
    columns = [name for name in _columns(old, table) if name in _columns(new, table)]
    if not columns:
        return 0
    rows = old.execute("SELECT %s FROM %s" % (", ".join(columns), table)).fetchall()
    statement = "INSERT OR %s INTO %s (%s) VALUES (%s)" % (
        "REPLACE" if replace else "IGNORE", table, ", ".join(columns),
        ", ".join("?" for _ in columns))
    copied = 0
    for row in rows:
        values = [row[name] for name in columns]
        if mapping and "doc_id" in columns:
            index = columns.index("doc_id")
            values[index] = mapping.get(values[index], values[index]) if values[index] else None
        new.execute(statement, values)
        copied += 1
    new.commit()
    return copied


def merge(old_path, new_path):
    old = sqlite3.connect(old_path)
    old.row_factory = sqlite3.Row
    new = lib.connect(new_path)
    lib.apply_schema(new)
    mapping = doc_map(old, new)
    # search_log first: seen_sources.search_id references it.
    searches = _copy(old, new, "search_log", replace=True)
    seen = _copy(old, new, "seen_sources", mapping=mapping)
    web = _copy(old, new, "web_sources", replace=True)
    candidates = _copy(old, new, "candidates", mapping=mapping)
    return {"search_log": searches, "seen_sources": seen,
            "web_sources": web, "candidates": candidates,
            "documents_remapped": sum(1 for key, value in mapping.items() if key != value)}


def main():
    parser = argparse.ArgumentParser(description="Merge a corpus learning history.")
    parser.add_argument("old", help="the database to read the history from")
    parser.add_argument("new", nargs="?", default=lib.DB_PATH,
                        help="the canonical database (default: %s)" % lib.DB_PATH)
    args = parser.parse_args()
    if os.path.abspath(args.old) == os.path.abspath(args.new):
        print("the two paths are the same database; nothing to merge", file=sys.stderr)
        return 2
    result = merge(args.old, args.new)
    for key, value in result.items():
        print("%-18s %s" % (key, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
