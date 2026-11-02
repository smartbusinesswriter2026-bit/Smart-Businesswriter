"""The corpus-wide cue trap: every researched block must accept evidence for its own question.

D-MGT-12/D-MGT-13 were one defect in one file, repeated: blocks whose cue list did not contain
the words their own query uses. A block like that can never carry evidence — it is silently an
always-gap cell — and no per-shelf test noticed, because each shelf only tested its own cells.
This loads all 75 profiles once and drives every researched block with a source whose title is
that block's own query.

Run:  PYTHONPATH=src python -m pytest tests/test_product_profile_cues.py -q
"""

import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.product import framework_profiles, retrieval  # noqa: E402

INDUSTRY = "grocery retail"


def echo(query, databases=None, limit=10, year_from=None):
    return {"results": [{"title": query[:120],
                         "abstract": "Evidence on " + query[:110] + ".",
                         "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"],
                         "year": 2024, "venue": "Journal", "dblp": None,
                         "doi": "10.1/" + str(abs(hash(query)) % 999983),
                         "url": "https://doi.org/10.1/x", "database": "OpenAlex"}],
            "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


class ProfileCueReachabilityTest(unittest.TestCase):
    def test_every_researched_block_accepts_its_own_query(self):
        checked, refused = 0, []
        for template, profile in sorted(framework_profiles.PROFILES.items()):
            gate = retrieval.gate_of(profile.get("gate"))
            context = retrieval.context_words(INDUSTRY)
            for block in profile["blocks"]:
                if framework_profiles.fill_of(block) not in ("research", "auto"):
                    continue
                checked += 1
                query = retrieval.build_query((block.get("queries") or [""])[0], INDUSTRY, "Global")
                with mock.patch("bp.product.sources.search_academic", side_effect=echo), \
                        mock.patch("bp.product.sources.search_web", side_effect=web), \
                        mock.patch("bp.product.retrieval._log_learning", return_value=None):
                    found = retrieval.retrieve(key=block["key"],
                                               cues=block.get("cues"), queries=[query],
                                               context=context, geography="Global", gate=gate)
                if not found["items"]:
                    refused.append("%s/%s (cues=%r, query=%r)"
                                   % (template, block["key"], block.get("cues"), query))
        self.assertGreater(checked, 300, "the sweep did not run")
        self.assertEqual(refused, [], "blocks that can never accept evidence for their own "
                                      "question:\n  " + "\n  ".join(refused))

    def test_no_block_declares_the_placeholder_cue(self):
        for template, profile in framework_profiles.PROFILES.items():
            for block in profile["blocks"]:
                if framework_profiles.fill_of(block) not in ("research", "auto"):
                    continue
                words = retrieval.cue_words_of(block.get("cues"))
                self.assertTrue(words, "%s/%s declares no cue at all" % (template, block["key"]))
                self.assertNotEqual(words, {"evidence"},
                                    "%s/%s still declares the placeholder" % (template, block["key"]))


if __name__ == "__main__":
    unittest.main()
