"""Tests for the RRA's optional rendered-page reader.

Many course catalogues are rendered by JavaScript, so a plain fetch sees only
the shell.  The reader is optional in every sense: without a browser, or
without budget, the plain fetch stands and the page is named as thin.
"""
import unittest

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import render as rrender  # noqa: E402


class ThinPageTest(RelevanceTestCase):
    def test_a_page_of_markup_and_few_words_is_thin(self):
        html = ("<html><head><style>x{}</style></head><body>"
                "<div id=root></div><script>var a=1;</script></body></html>")
        self.assertTrue(rrender.is_thin(html))

    def test_a_page_with_real_text_is_not_thin(self):
        html = "<html><body><p>" + ("a real sentence about the course. " * 80) + "</p></body></html>"
        self.assertFalse(rrender.is_thin(html))

    def test_the_measure_is_the_cleaned_text_not_the_raw_bytes(self):
        """Twenty thousand characters of markup and two hundred of words is a shell."""
        html = "<html><body>" + ("<div class='x'>y</div>" * 900) + \
               "<p>Short.</p></body></html>"
        self.assertGreater(len(html), 10000)
        self.assertTrue(rrender.is_thin(html))


class RenderBudgetTest(RelevanceTestCase):
    def test_the_budget_is_spent_and_then_refuses(self):
        limit = rrender.reset_budget()
        self.assertGreater(limit, 0)
        taken = [rrender.take_render() for _ in range(limit + 2)]
        self.assertTrue(all(taken[:limit]))
        self.assertFalse(any(taken[limit:]))
        self.assertEqual(rrender.used(), limit)

    def test_a_reset_starts_the_budget_afresh(self):
        limit = rrender.reset_budget()
        for _ in range(limit):
            rrender.take_render()
        rrender.reset_budget()
        self.assertEqual(rrender.used(), 0)
        self.assertTrue(rrender.take_render())


class RenderGateTest(RelevanceTestCase):
    def test_only_an_https_host_on_the_allowlist_is_rendered(self):
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1", "type": "school"}]}
        ok, reason = rrender._allowed("http://insead.edu/mba", allowlist)
        self.assertFalse(ok)
        self.assertIn("https", reason)
        ok, reason = rrender._allowed("https://evil.com/x", allowlist)
        self.assertFalse(ok)
        ok, reason = rrender._allowed("https://www.insead.edu/mba", allowlist)
        self.assertTrue(ok, reason)

    def test_a_blocked_domain_is_never_rendered(self):
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1", "type": "school"}]}
        ok, reason = rrender._allowed("https://en.wikipedia.org/wiki/MBA", allowlist)
        self.assertFalse(ok)


class ScoutRenderTest(RelevanceTestCase):
    def test_a_thin_page_is_rendered_and_a_thick_one_is_not(self):
        from bp.product.relevance import s1_scout
        from unittest import mock
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1", "type": "school"}]}
        thin_html = "<html><body><div id=root></div></body></html>"
        thick_html = "<html><body><p>" + ("a real sentence about the course. " * 80) + "</p></body></html>"
        rrender.reset_budget()
        with mock.patch.object(s1_scout, "_fetch_url", return_value=(200, thin_html, "")):
            with mock.patch.object(rrender, "available", return_value=True):
                with mock.patch.object(rrender, "render_text",
                                       return_value=("Balanced Scorecard is taught here. " * 40, "")) as render:
                    snap = s1_scout.scout_url("https://www.insead.edu/x", allowlist=allowlist)
        self.assertTrue(snap.get("rendered"))
        render.assert_called_once()
        self.assertIn("Balanced Scorecard", snap.get("text_excerpt") or "")

        rrender.reset_budget()
        with mock.patch.object(s1_scout, "_fetch_url", return_value=(200, thick_html, "")):
            with mock.patch.object(rrender, "available", return_value=True):
                with mock.patch.object(rrender, "render_text") as render:
                    snap = s1_scout.scout_url("https://www.insead.edu/y", allowlist=allowlist)
        self.assertFalse(snap.get("rendered"))
        render.assert_not_called()

    def test_a_page_with_no_browser_stands_on_the_plain_fetch(self):
        from bp.product.relevance import s1_scout
        from unittest import mock
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1", "type": "school"}]}
        thin_html = "<html><body><div id=root></div></body></html>"
        rrender.reset_budget()
        with mock.patch.object(s1_scout, "_fetch_url", return_value=(200, thin_html, "")):
            with mock.patch.object(rrender, "available", return_value=False):
                snap = s1_scout.scout_url("https://www.insead.edu/x", allowlist=allowlist)
        self.assertFalse(snap.get("rendered"))
        self.assertIn("no headless browser", snap.get("render_note") or "")

    def test_the_orientation_excerpt_is_readable_not_markup(self):
        from bp.product.relevance import s1_scout
        from unittest import mock
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1", "type": "school"}]}
        html = "<html><head><title>T</title></head><body><h1>MBA Curriculum</h1>" \
               + ("<p>core course description</p>" * 100) + "</body></html>"
        with mock.patch.object(s1_scout, "_fetch_url", return_value=(200, html, "")):
            snap = s1_scout.scout_url("https://www.insead.edu/mba", allowlist=allowlist)
        excerpt = snap.get("text_excerpt") or ""
        self.assertNotIn("<", excerpt[:200])
        self.assertIn("MBA Curriculum", excerpt)


if __name__ == "__main__":
    unittest.main()
