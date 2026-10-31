"""Plan, verify and record the corpus <-> Cloudflare R2 mapping.

Standard library only (C-02): this is a build-time and operations tool, and
nothing in it is imported by the pipeline runtime.

The corpus database is the system of record (D-03). Nothing here decides what
to upload. It reads the record, works out the byte layout the record implies,
and checks that what comes back from R2 is the same bytes the record
describes. A gap is named, never filled: a missing file, a document outside
the source root, a hash that does not match - each one stops the run and says
which document it was.

Subcommands
    plan         read the database, write the rclone file list and the plan JSON
    verify       hash the bytes in a directory against documents.sha256
    relink       point a restored database copy at the restored files
    record       write the R2 object key back into documents.r2_key
    phrase       find a phrase that identifies exactly one page
    compare      compare two Meilisearch instances on that phrase and on the
                 whole document set
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import urllib.request

PREFIX = "pdfs/"

STOPWORDS = set(
    """the and for that with this from have has had are was were will would could
    should can may might must not but they them their there these those which
    when what where while more most other into over under about after before
    than then also been being such some any each per its his her our your you
    we us our i me my one two three first second new used using use however
    therefore because within without between during each other others many much
    may might must shall upon among across both few more most other own same
    too very via yet""".split())


class PlanError(Exception):
    """A named gap in the plan. The message says which document and why."""


def connect(db_path):
    """Open the corpus database the way the corpus opens it."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def read_documents(db_path):
    """Every document the record holds, in the order the record lists them."""
    connection = connect(db_path)
    try:
        rows = connection.execute(
            "SELECT doc_id, title, local_path, sha256, pages_total, r2_key"
            "  FROM documents ORDER BY doc_id").fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def sha256_of(path, chunk=1024 * 1024):
    """The SHA-256 of a file, read in blocks so a large PDF costs no memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def on_disk_name(path):
    """The real name of a file, when the record spells it with a different case.

    Windows resolves `Exploring_business.pdf` and `exploring_business.pdf` to
    one file, so the record can carry a spelling that is not the name on disk.
    R2 object keys are case-sensitive and rclone's filters are too, so the
    real name is what the plan must use. Returns (path, corrected).
    """
    absolute = os.path.abspath(path)
    parent = os.path.dirname(absolute)
    base = os.path.basename(absolute)
    if not os.path.isdir(parent):
        return absolute, False
    try:
        names = os.listdir(parent)
    except OSError:
        return absolute, False
    if base in names:
        return absolute, False
    matches = [name for name in names if name.lower() == base.lower()]
    if len(matches) == 1:
        return os.path.join(parent, matches[0]), True
    return absolute, False


def repair_paths(db_path):
    """Write the on-disk spelling back into documents.local_path.

    Only the spelling changes; the file, and therefore the bytes, are the
    same. The documents that are changed are named.
    """
    connection = connect(db_path)
    try:
        rows = connection.execute("SELECT doc_id, local_path FROM documents").fetchall()
        changes = []
        for row in rows:
            recorded = row["local_path"]
            if not recorded:
                continue
            resolved, corrected = on_disk_name(recorded)
            if corrected and resolved != recorded:
                connection.execute("UPDATE documents SET local_path = ? WHERE doc_id = ?",
                                   (resolved, row["doc_id"]))
                changes.append({"doc_id": row["doc_id"], "recorded": recorded,
                                "on_disk": resolved})
        connection.commit()
    finally:
        connection.close()
    return changes


def build_plan(db_path):
    """Work out the byte layout the record implies.

    Returns a dict with the source root and one entry per document. Raises
    PlanError, naming the document, when the record cannot be turned into a
    layout - a missing file, a file outside a common root, two documents
    pointing at one path.
    """
    documents = read_documents(db_path)
    if not documents:
        raise PlanError("the database holds no documents: %s" % db_path)

    missing = [doc for doc in documents if not doc["local_path"]]
    if missing:
        raise PlanError("documents with no local_path: %s"
                        % ", ".join(doc["doc_id"] for doc in missing))

    resolved_paths = []
    for document in documents:
        resolved, _corrected = on_disk_name(document["local_path"])
        resolved_paths.append(os.path.abspath(resolved))
    absent = [(doc["doc_id"], doc["local_path"]) for doc, resolved in zip(documents, resolved_paths)
              if not os.path.isfile(resolved)]
    if absent:
        raise PlanError("files recorded but not on disk: %s"
                        % "; ".join("%s -> %s" % pair for pair in absent))

    try:
        # The root is the common ancestor of the documents' *directories*.
        # commonpath over the files themselves would return the file when
        # the corpus holds one document, and a file is not a source root.
        root = os.path.commonpath([os.path.dirname(path) for path in resolved_paths])
    except ValueError:
        raise PlanError("the documents do not share one source root: %s"
                        % ", ".join(resolved_paths))
    if not os.path.isdir(root):
        raise PlanError("the source root is not a directory: %s" % root)

    entries = []
    seen = {}
    for document in documents:
        resolved, corrected = on_disk_name(document["local_path"])
        absolute = os.path.abspath(resolved)
        relative = os.path.relpath(absolute, root)
        if relative.startswith(".."):
            raise PlanError("%s is outside the source root %s"
                            % (document["doc_id"], root))
        if relative in seen:
            raise PlanError("two documents share one file: %s and %s (%s)"
                            % (seen[relative], document["doc_id"], relative))
        seen[relative] = document["doc_id"]
        entries.append({
            "doc_id": document["doc_id"],
            "title": document["title"],
            "rel_path": relative.replace(os.sep, "/"),
            "key": PREFIX + relative.replace(os.sep, "/"),
            "local_path": absolute,
            "recorded_path": document["local_path"],
            "case_corrected": bool(corrected),
            "sha256": (document["sha256"] or "").lower(),
            "size": os.path.getsize(absolute),
        })

    return {
        "db": os.path.abspath(db_path),
        "source_root": root,
        "prefix": PREFIX,
        "entries": entries,
        "total_bytes": sum(entry["size"] for entry in entries),
    }


def write_files_from(plan, path):
    """Write the rclone file list: one relative path per line, UTF-8."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for entry in plan["entries"]:
            handle.write(entry["rel_path"] + "\n")
    return len(plan["entries"])


def verify_bytes(db_path, source_root, restored_root):
    """Hash the restored bytes and compare them with documents.sha256.

    Returns a report. `ok` is False when any document is missing, unreadable
    or has a different hash - the gap is named, never repaired.
    """
    documents = read_documents(db_path)
    results = []
    for document in documents:
        local = document["local_path"]
        if not local:
            results.append({"doc_id": document["doc_id"], "status": "no_path",
                            "expected": document["sha256"], "actual": None})
            continue
        resolved, _corrected = on_disk_name(local)
        relative = os.path.relpath(os.path.abspath(resolved), os.path.abspath(source_root))
        restored = os.path.join(restored_root, relative)
        expected = (document["sha256"] or "").lower()
        if not os.path.isfile(restored):
            results.append({"doc_id": document["doc_id"], "status": "missing",
                            "expected": expected, "actual": None,
                            "path": restored})
            continue
        actual = sha256_of(restored)
        status = "ok" if (expected and actual == expected) else "hash_mismatch"
        results.append({"doc_id": document["doc_id"], "status": status,
                        "expected": expected, "actual": actual,
                        "path": restored})
    report = {
        "documents": len(results),
        "ok": all(result["status"] == "ok" for result in results),
        "results": results,
    }
    return report


def relink(db_path, source_root, restored_root):
    """Point the database at the restored files.

    The copy of the database that the restore test works with still names the
    original paths. The restored bytes are the ones under test, so the copy is
    made to name them.
    """
    connection = connect(db_path)
    try:
        rows = connection.execute(
            "SELECT doc_id, local_path FROM documents").fetchall()
        changed = 0
        for row in rows:
            local = row["local_path"]
            if not local:
                continue
            relative = os.path.relpath(os.path.abspath(local),
                                       os.path.abspath(source_root))
            new_path = os.path.join(restored_root, relative)
            if os.path.isfile(new_path):
                connection.execute(
                    "UPDATE documents SET local_path = ? WHERE doc_id = ?",
                    (new_path, row["doc_id"]))
                changed += 1
        connection.commit()
    finally:
        connection.close()
    return changed


def record_keys(db_path, plan):
    """Write the R2 object key of every document into documents.r2_key."""
    connection = connect(db_path)
    try:
        changed = 0
        for entry in plan["entries"]:
            connection.execute(
                "UPDATE documents SET r2_key = ? WHERE doc_id = ?",
                (entry["key"], entry["doc_id"]))
            changed += 1
        connection.commit()
    finally:
        connection.close()
    return changed


def find_phrase(db_path, limit=400):
    """Find a phrase that identifies exactly one page of the corpus.

    The phrase is used as the acceptance query: the restored index has to
    answer it with the page the record names. It is chosen deterministically
    from the record, so the same phrase is used every run.
    """
    import re
    connection = connect(db_path)
    try:
        rows = connection.execute(
            "SELECT p.doc_id, p.pdf_page, p.text FROM pages p"
            "  JOIN documents d ON d.doc_id = p.doc_id"
            " WHERE d.enrichen_at IS NOT NULL AND length(p.text) BETWEEN 700 AND 4000"
            " ORDER BY (p.text_method = 'pdf_text_layer') DESC, p.doc_id, p.pdf_page"
            " LIMIT ?", (limit,)).fetchall()
        for row in rows:
            text = row["text"] or ""
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                words = re.findall(r"[A-Za-z][A-Za-z'\-]+", sentence)
                if len(words) < 9:
                    continue
                for start in range(0, min(8, len(words) - 6)):
                    phrase_words = words[start:start + 5]
                    terms = [word.lower() for word in phrase_words]
                    if any(term in STOPWORDS for term in terms):
                        continue
                    if len(set(terms)) < 4:
                        continue
                    phrase = " ".join(phrase_words)
                    count = connection.execute(
                        "SELECT COUNT(*) FROM pages WHERE lower(text) LIKE ?",
                        ("%" + phrase.lower() + "%",)).fetchone()[0]
                    if count == 1:
                        return {"phrase": phrase, "doc_id": row["doc_id"],
                                "pdf_page": row["pdf_page"]}
    finally:
        connection.close()
    raise PlanError("no phrase that identifies exactly one page could be found")


def meili_get(url, path, timeout=30):
    with urllib.request.urlopen(url + path, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def meili_search(url, index, phrase, limit=5, timeout=30):
    request = urllib.request.Request(
        "%s/indexes/%s/search" % (url, index),
        data=json.dumps({"q": phrase, "limit": limit}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def meili_documents(url, index):
    """Every document the index holds, as (doc_id, pdf_page) pairs."""
    pairs = []
    offset = 0
    while True:
        batch = meili_get(url, "/indexes/%s/documents?limit=1000&offset=%d&fields=doc_id,pdf_page"
                          % (index, offset))
        if isinstance(batch, dict):
            batch = batch.get("results", [])
        if not batch:
            break
        pairs.extend((document["doc_id"], document["pdf_page"]) for document in batch)
        offset += len(batch)
        if len(batch) < 1000:
            break
    return pairs


def compare_indexes(live_url, rebuilt_url, index, phrase, expected=None, db_path=None):
    """Compare the live index with a rebuilt one.

    Both must answer the phrase with the same page. The document sets are
    compared as well, and the difference is named: a page the live index holds
    and the record does not is a stale page in a disposable index, and a
    document the record does not have at all is named as such.
    """
    live_hits = meili_search(live_url, index, phrase)
    rebuilt_hits = meili_search(rebuilt_url, index, phrase)
    live_top = (live_hits["hits"][0]["doc_id"], live_hits["hits"][0]["pdf_page"]) \
        if live_hits.get("hits") else None
    rebuilt_top = (rebuilt_hits["hits"][0]["doc_id"], rebuilt_hits["hits"][0]["pdf_page"]) \
        if rebuilt_hits.get("hits") else None

    live_documents = set(meili_documents(live_url, index))
    rebuilt_documents = set(meili_documents(rebuilt_url, index))

    only_live = live_documents - rebuilt_documents
    only_rebuilt = rebuilt_documents - live_documents

    result = {
        "phrase": phrase,
        "expected": expected,
        "live_top": list(live_top) if live_top else None,
        "rebuilt_top": list(rebuilt_top) if rebuilt_top else None,
        "same_top_hit": live_top == rebuilt_top,
        "live_documents": len(live_documents),
        "rebuilt_documents": len(rebuilt_documents),
        "only_in_live_count": len(only_live),
        "only_in_rebuilt_count": len(only_rebuilt),
        "only_in_live": sorted([list(pair) for pair in only_live])[:200],
        "only_in_rebuilt": sorted([list(pair) for pair in only_rebuilt])[:200],
        "live_hits": [{"doc_id": hit["doc_id"], "pdf_page": hit["pdf_page"]}
                      for hit in live_hits.get("hits", [])[:5]],
        "rebuilt_hits": [{"doc_id": hit["doc_id"], "pdf_page": hit["pdf_page"]}
                         for hit in rebuilt_hits.get("hits", [])[:5]],
    }

    by_document = {}
    for doc_id, page in only_live:
        by_document.setdefault(doc_id, []).append(page)
    result["only_in_live_by_document"] = {
        doc_id: {"pages": len(pages), "first_page": min(pages), "last_page": max(pages)}
        for doc_id, pages in sorted(by_document.items())}

    if db_path:
        connection = connect(db_path)
        try:
            known = {row["doc_id"] for row in connection.execute("SELECT doc_id FROM documents")}
            pages_in_record = connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            enrichable = connection.execute(
                "SELECT COUNT(*) FROM pages p JOIN documents d ON d.doc_id = p.doc_id"
                " WHERE d.enrichen_at IS NOT NULL").fetchone()[0]
        finally:
            connection.close()
        result["record_pages"] = pages_in_record
        result["record_enrichable_pages"] = enrichable
        result["in_index_but_not_in_record"] = sorted(
            doc_id for doc_id in by_document if doc_id not in known)

    result["same_document_set"] = not only_live and not only_rebuilt
    if expected:
        result["rebuilt_matches_record"] = (
            list(rebuilt_top) == list(expected) if rebuilt_top else False)
        result["live_matches_record"] = (
            list(live_top) == list(expected) if live_top else False)
    result["ok"] = bool(result["same_top_hit"] and result["rebuilt_top"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    plan_parser = sub.add_parser("plan", help="write the file list and the plan JSON")
    plan_parser.add_argument("--db", required=True)
    plan_parser.add_argument("--files-from", required=True)
    plan_parser.add_argument("--json", dest="json_path", required=True)

    verify_parser = sub.add_parser("verify", help="hash bytes against documents.sha256")
    verify_parser.add_argument("--db", required=True)
    verify_parser.add_argument("--source-root", required=True)
    verify_parser.add_argument("--root", required=True)
    verify_parser.add_argument("--json", dest="json_path", required=True)

    relink_parser = sub.add_parser("relink", help="point a database copy at restored files")
    relink_parser.add_argument("--db", required=True)
    relink_parser.add_argument("--source-root", required=True)
    relink_parser.add_argument("--root", required=True)

    record_parser = sub.add_parser("record", help="write documents.r2_key")
    record_parser.add_argument("--db", required=True)
    record_parser.add_argument("--plan", required=True)

    phrase_parser = sub.add_parser("phrase", help="find a phrase that names one page")
    phrase_parser.add_argument("--db", required=True)

    repair_parser = sub.add_parser("repair-paths",
                                    help="write the on-disk spelling into local_path")
    repair_parser.add_argument("--db", required=True)

    compare_parser = sub.add_parser("compare", help="compare two Meilisearch instances")
    compare_parser.add_argument("--live", required=True)
    compare_parser.add_argument("--rebuilt", required=True)
    compare_parser.add_argument("--index", default="pages")
    compare_parser.add_argument("--phrase", required=True)
    compare_parser.add_argument("--db", default="")
    compare_parser.add_argument("--expect-doc", dest="expect_doc", default="")
    compare_parser.add_argument("--expect-page", dest="expect_page", type=int, default=0)
    compare_parser.add_argument("--json", dest="json_path", default="")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            plan = build_plan(args.db)
            count = write_files_from(plan, args.files_from)
            with open(args.json_path, "w", encoding="utf-8") as handle:
                json.dump(plan, handle, indent=2, ensure_ascii=False)
            print(json.dumps({
                "documents": count,
                "source_root": plan["source_root"],
                "total_bytes": plan["total_bytes"],
                "files_from": args.files_from,
                "plan": args.json_path,
            }, indent=2))
            return 0

        if args.command == "verify":
            report = verify_bytes(args.db, args.source_root, args.root)
            with open(args.json_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            broken = [r for r in report["results"] if r["status"] != "ok"]
            print(json.dumps({
                "documents": report["documents"],
                "ok": report["ok"],
                "not_ok": [{"doc_id": r["doc_id"], "status": r["status"]} for r in broken],
            }, indent=2))
            return 0 if report["ok"] else 1

        if args.command == "relink":
            changed = relink(args.db, args.source_root, args.root)
            print(json.dumps({"relinked": changed}, indent=2))
            return 0

        if args.command == "record":
            with open(args.plan, "r", encoding="utf-8") as handle:
                plan = json.load(handle)
            changed = record_keys(args.db, plan)
            print(json.dumps({"r2_keys_written": changed}, indent=2))
            return 0

        if args.command == "phrase":
            print(json.dumps(find_phrase(args.db), indent=2))
            return 0

        if args.command == "repair-paths":
            changes = repair_paths(args.db)
            print(json.dumps({"repaired": len(changes), "changes": changes}, indent=2))
            return 0

        if args.command == "compare":
            expected = None
            if args.expect_doc and args.expect_page:
                expected = [args.expect_doc, args.expect_page]
            result = compare_indexes(args.live, args.rebuilt, args.index,
                                     args.phrase, expected, args.db or None)
            if args.json_path:
                with open(args.json_path, "w", encoding="utf-8") as handle:
                    json.dump(result, handle, indent=2)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
    except PlanError as error:
        print("PLAN ERROR: %s" % error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
