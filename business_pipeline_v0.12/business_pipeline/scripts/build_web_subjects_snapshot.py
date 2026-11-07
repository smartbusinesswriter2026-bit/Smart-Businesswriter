"""Bake the subject catalogue and the subject pages into the site.

The published site is a static tree: Cloudflare Pages serves
`business_pipeline_v0.12/business_pipeline/web` as files, with no Python
backend behind it.  When `/api/subjects` or `/api/cases/subjects/<id>`
cannot be reached, the page falls back to the files baked here, so they must
hold exactly what the backend would serve.

Two kinds of file are written:

* `web/subjects.json` - the catalogue, for the subject rail;
* `web/subject-<id>.json` - one file per subject, for the subject page.

Run it after anything changes a subject, a shelf or a count:

    python scripts/build_web_subjects_snapshot.py

The guard in `tests/test_web_static_snapshot.py` fails if a committed file and
the code disagree, so a snapshot cannot drift unnoticed.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.product import subjects  # noqa: E402  (path set above)

WEB = os.path.join(ROOT, "web")
CATALOGUE = os.path.join(WEB, "subjects.json")


def dumps(payload):
    """The one serialization every baked file uses.

    ASCII-escaped and without a trailing newline: the files are read by
    `fetch(...).json()`, so the bytes only have to parse - but they have to
    parse the same way every time, or a regeneration would churn the tree.
    """
    return json.dumps(payload, ensure_ascii=True)


def write(path, payload):
    """Write one baked file."""
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(dumps(payload))


def build():
    """Every baked file, as a mapping of path to payload."""
    files = {CATALOGUE: subjects.catalogue()}
    for subject_id in [row["id"] for row in subjects.catalogue()["subjects"]]:
        files[os.path.join(WEB, "subject-%s.json" % subject_id)] = subjects.detail(subject_id)
    return files


def main():
    files = build()
    for path, payload in files.items():
        write(path, payload)
        print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
