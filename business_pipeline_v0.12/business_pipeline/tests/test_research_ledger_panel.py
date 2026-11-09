"""The research ledger panel: the page reads the ledger the server stored.

The panel is presentation only.  It must show what the server recorded - what
was cited for each part, and why every other candidate was refused - and it
must not fetch, decide or invent anything of its own.
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = open(os.path.join(HERE, "..", "web", "index.html"), encoding="utf-8").read()

#: Every reason the server can record for a refused candidate.
REASONS = ("no_cue", "no_geography", "tier_missing", "blocked_domain",
           "below_floor", "duplicate", "full_text_cue_missing")

#: Every source tier the server can require.
TIERS = ("official", "data", "research", "news")


def _function_body(name):
    """The body of one function in the page's inline script."""
    start = PAGE.index("function %s(" % name)
    depth = 0
    for index in range(start, len(PAGE)):
        if PAGE[index] == "{":
            depth += 1
        elif PAGE[index] == "}":
            depth -= 1
            if depth == 0:
                return PAGE[start:index + 1]
    raise AssertionError("the function %s never closes" % name)


class ResearchLedgerPanelTest(unittest.TestCase):
    def test_the_page_carries_the_research_ledger_renderer(self):
        self.assertIn("function researchLedgerHtml(", PAGE)

    def test_the_completion_review_shows_the_ledger_the_server_stored(self):
        self.assertIn("researchLedgerHtml(result.research || [], ledgerLabels)", PAGE)

    def test_the_chat_review_shows_the_ledger_the_server_stored(self):
        self.assertIn("researchLedgerHtml(c.research_ledger || [], labels)", PAGE)

    def test_every_refusal_reason_the_server_can_record_has_a_label(self):
        for reason in REASONS:
            self.assertIn(reason + ":", PAGE, reason)

    def test_every_source_tier_the_server_can_require_is_named(self):
        for tier in TIERS:
            self.assertIn(tier + ":", PAGE, tier)

    def test_the_panel_reads_the_record_and_never_fetches_its_own_sources(self):
        body = _function_body("researchLedgerHtml")
        self.assertNotIn("fetch(", body)
        self.assertNotIn("post(", body)
        self.assertNotIn("XMLHttpRequest", body)

    def test_the_panel_says_a_refusal_is_not_a_finding(self):
        body = _function_body("researchLedgerHtml")
        self.assertIn("never a finding", body)

    def test_the_panel_marks_a_background_paragraph_as_not_cited(self):
        body = _function_body("researchLedgerHtml")
        self.assertIn("not cited", body)


if __name__ == "__main__":
    unittest.main()
