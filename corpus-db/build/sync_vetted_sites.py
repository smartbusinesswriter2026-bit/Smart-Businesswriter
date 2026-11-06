"""Mirror the vetted-site registry into the corpus database.

    python corpus-db/build/sync_vetted_sites.py
    python corpus-db/build/sync_vetted_sites.py --dry-run
    python corpus-db/build/sync_vetted_sites.py --keep-stale

Why a mirror, not the authority.  The vetted list is product configuration:
it ships with the code, it is reviewed with the code, and the pipeline must
still run when the database is down.  `sources.py` remains the source of
truth.  This script copies it into `vetted_sites` so the owner can inspect the
directory in SQL or the admin page, and so a report can be diffed between
releases.  Editing the table does not change the pipeline; edit `sources.py`
and run this script again.

The mirror is idempotent: every row is upserted by `site_id`, and stale rows
are removed unless `--keep-stale` is passed.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(CORPUS_DIR)
PIPELINE_SRC = os.path.join(ROOT, "business_pipeline_v0.12", "business_pipeline", "src")

sys.path.insert(0, HERE)
sys.path.insert(0, PIPELINE_SRC)

import corpus_lib as lib  # noqa: E402
from bp.product import sources  # noqa: E402


SCHEMA = """
CREATE TABLE IF NOT EXISTS vetted_sites (
  site_id       TEXT PRIMARY KEY,
  label         TEXT NOT NULL,
  domain        TEXT NOT NULL UNIQUE,
  region        TEXT,
  tier          TEXT,
  category      TEXT,
  academic_fit  TEXT,
  access        TEXT,
  priority      INTEGER NOT NULL DEFAULT 0,
  topics        TEXT NOT NULL DEFAULT '[]',
  use_note      TEXT,
  updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vetted_topic ON vetted_sites(topics);
CREATE INDEX IF NOT EXISTS idx_vetted_access ON vetted_sites(access);
"""


def rows():
    """The registry as one row per site, with its topics as JSON text."""
    for site in sources._all_sites():
        yield {
            "site_id": site["id"],
            "label": site["label"],
            "domain": site["domain"].lower(),
            "region": site.get("region") or "Global",
            "tier": site.get("tier") or "",
            "category": site.get("category") or "",
            "academic_fit": site.get("academic_fit") or "",
            "access": site.get("access") or "free",
            "priority": int(site.get("priority") or 0),
            "topics": json.dumps(site.get("topics") or []),
            "use_note": site.get("use") or "",
            "updated_at": lib.now(),
        }


def sync(connection, keep_stale=False):
    connection.executescript(SCHEMA)
    records = list(rows())
    for record in records:
        connection.execute(
            "INSERT INTO vetted_sites (site_id, label, domain, region, tier, category,"
            " academic_fit, access, priority, topics, use_note, updated_at)"
            " VALUES (:site_id, :label, :domain, :region, :tier, :category,"
            " :academic_fit, :access, :priority, :topics, :use_note, :updated_at)"
            " ON CONFLICT(site_id) DO UPDATE SET"
            " label=excluded.label, domain=excluded.domain, region=excluded.region,"
            " tier=excluded.tier, category=excluded.category,"
            " academic_fit=excluded.academic_fit, access=excluded.access,"
            " priority=excluded.priority, topics=excluded.topics,"
            " use_note=excluded.use_note, updated_at=excluded.updated_at",
            record)
    removed = 0
    if not keep_stale:
        ids = [record["site_id"] for record in records]
        placeholders = ",".join("?" for _ in ids)
        removed = connection.execute(
            "DELETE FROM vetted_sites WHERE site_id NOT IN (%s)" % placeholders,
            ids).rowcount if ids else 0
    connection.commit()
    return {"sites": len(records), "removed": removed}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mirror the pipeline's vetted-site registry into the corpus database.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the sites and counts; do not write the database")
    parser.add_argument("--keep-stale", action="store_true",
                        help="do not delete rows that are no longer in the registry")
    args = parser.parse_args(argv)

    records = list(rows())
    if args.dry_run:
        for record in records:
            print("%-14s %-38s %-8s %-10s %s" % (
                record["site_id"], record["domain"], record["tier"],
                record["access"], record["topics"]))
        print("\n%d site(s). No database was touched." % len(records))
        return 0

    connection = lib.connect()
    lib.apply_schema(connection)
    try:
        result = sync(connection, keep_stale=args.keep_stale)
        by_topic = connection.execute(
            "SELECT topics, COUNT(*) AS n FROM vetted_sites GROUP BY topics"
            " ORDER BY n DESC LIMIT 5").fetchall()
        print("mirrored %d site(s); removed %d stale row(s)" % (
            result["sites"], result["removed"]))
        print("database: %s" % lib.DB_PATH)
        print("top topic groups:")
        for row in by_topic:
            print("  %-60s %d" % (row["topics"][:60], row["n"]))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
