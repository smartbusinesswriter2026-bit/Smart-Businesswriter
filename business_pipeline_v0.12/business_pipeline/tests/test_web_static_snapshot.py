"""Guard for the published site: the baked subject snapshots and their fallbacks.

The site is published as static files, so there is no Python backend behind it
when it is read on the public host.  The page therefore falls back to the files
baked into it - `web/subjects.json` for the subject rail, and
`web/subject-<id>.json` for each subject page - when the API cannot be
reached.

Six things can break that, and this file fails on each:

* the catalogue drifts from the code that produces it, so the public site keeps
  serving a subject list the code has already changed;
* a subject page drifts the same way, so the public site serves a shelf the
  code has already rewritten;
* a baked file is not JSON, or does not carry the format the code declares;
* the page loses the catalogue fallback, and a static host shows an empty rail;
* the page loses the subject-page fallback, and a static host cannot open a
  subject at all;
* the page reports a failed local API on a host that never had one.

It is a presence and equality guard, not a DOM test.
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.product import subjects  # noqa: E402  (path set above)


def _read_json(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as stream:
        return json.load(stream)


class WebStaticSnapshotTest(unittest.TestCase):
    """The published site must carry what the code declares."""

    maxDiff = None

    def setUp(self):
        self.catalogue = subjects.catalogue()
        self.subject_ids = [row["id"] for row in self.catalogue["subjects"]]
        with open(os.path.join(WEB, "index.html"), encoding="utf-8") as stream:
            self.html = stream.read()

    def test_the_baked_subject_snapshot_matches_the_code(self):
        self.assertEqual(
            self.catalogue,
            _read_json("subjects.json"),
            "web/subjects.json has drifted from bp.product.subjects.catalogue(); "
            "rebuild it with `python scripts/build_web_subjects_snapshot.py`",
        )

    def test_the_baked_snapshot_carries_the_format_the_code_declares(self):
        baked = _read_json("subjects.json")
        self.assertEqual(subjects.FORMAT, baked.get("format"))
        self.assertTrue(baked.get("subjects"), "the baked catalogue holds no subject")

    def test_every_subject_page_is_baked_and_matches_the_code(self):
        for subject_id in self.subject_ids:
            path = os.path.join(WEB, "subject-%s.json" % subject_id)
            self.assertTrue(os.path.exists(path), "web/subject-%s.json is missing" % subject_id)
            with open(path, encoding="utf-8") as stream:
                baked = json.load(stream)
            self.assertEqual(
                subjects.detail(subject_id),
                baked,
                "web/subject-%s.json has drifted from bp.product.subjects.detail(); "
                "rebuild it with `python scripts/build_web_subjects_snapshot.py`" % subject_id,
            )

    def test_the_baked_subject_pages_carry_the_format_the_code_declares(self):
        for subject_id in self.subject_ids:
            baked = _read_json("subject-%s.json" % subject_id)
            self.assertEqual(subjects.FORMAT, baked.get("format"))
            self.assertEqual(subject_id, baked.get("id"))

    def test_the_page_falls_back_to_the_baked_snapshots(self):
        self.assertIn('fetch("/subjects.json")', self.html)
        self.assertIn('fetch("/subject-" + encodeURIComponent(state.subjectId) + ".json")', self.html)

    def test_the_page_does_not_report_a_failed_local_api_on_a_static_host(self):
        self.assertIn("failed.length < results.length", self.html)
