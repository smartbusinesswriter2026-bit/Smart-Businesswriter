"""Tests for the RRA read path: the scout must hand the reader the page.

The RRA's controls ask a single question: **did the sweep see the
framework?**  A control holds when the framework's name appears in an
evidence excerpt.  Between build 1.145 and now the sweep read 353 pages and
saw no framework name at all, so every control failed and the measurement
withheld every gap.  The controls were right; the read path was wrong.

Four faults, all of them in the read path, and each one is pinned here:

1. **The fetch was cut too short.**  The response was read to 100,000
   characters, and a page whose header, logo and script block fill that
   space lost its body.  The owner read 400,000 characters in their own
   Phase 1 probe and read the frameworks.
2. **The User-Agent was refused.**  ``SmartBusinessWriter-RRA/1.0`` drew a
   403 from a school that answers a browser.  The name still identifies the
   reader.
3. **The render was thrown away.**  The rendered text was compared with the
   **raw markup** of the fetch, and the markup is longer, so the browser's
   reading was discarded as "no longer than the fetch".
4. **The body was capped before it was stripped.**  The cap was applied to
   raw markup, so the reader was handed the head of the document — a logo's
   ``<path>`` data and a menu — instead of the words.

And a fifth, in the reader rather than the scout:

5. **Two labels could not be matched.**  The taxonomy names a framework as
   the product knows it ("Porter's Five Forces", "Ansoff Growth Matrix"),
   but a course page writes the short name ("Five Forces", "Ansoff").  The
   page was read, the name was on it, and the control still scored zero.

The tests below are offline: no page is fetched.  They drive the scout with
a stubbed fetch and a stubbed browser.
"""
import unittest
from unittest import mock

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import s1_scout as scout  # noqa: E402
from bp.product.relevance import s2_reader as reader  # noqa: E402
from bp.product.relevance import render as scout_render  # noqa: E402


#: A body of markup whose first 20,000 characters are chrome, and whose
#: words sit after it.  This is the shape of a real course-catalogue page.
CHROME_FIRST = (
    "<html><head><style>" + ("x" * 30000) + "</style></head><body>"
    "<nav><a href='/'>Home</a><a href='/about'>About</a></nav>"
    "<p>The course covers the Business Model Canvas and the Ansoff Growth "
    "Matrix, and it is assessed with a group project.</p>"
    "</body></html>"
)

#: The page as the server sends it, with the framework named in prose.
COURSE_PAGE = (
    "<html><body><main>"
    "<h1>Strategy and Innovation</h1>"
    "<p>This course teaches the Business Model Canvas and the Ansoff Growth "
    "Matrix. Students build a venture canvas and present it to the class.</p>"
    "<p>Assessment is by group project and an individual written report.</p>"
    "</main></body></html>"
)


class ScoutReadPathTest(RelevanceTestCase):
    """The scout must hand the reader the page's words."""

    def _allow(self):
        return {"allowed": [{"domain": "www.example-school.edu", "tier": "T1"}]}

    def _stub_fetch(self, html, status=200):
        return mock.patch.object(scout, "_fetch_url", return_value=(status, html, ""))

    def test_the_fetch_reads_far_enough_to_hold_the_body(self):
        """A 100,000-character read cut the body off.  The read is longer."""
        self.assertGreater(scout.FETCH_CAP_CHARS, 100000)
        # The cap is applied to the response, and the body is inside it.
        self.assertGreater(scout.FETCH_CAP_CHARS, len(CHROME_FIRST))

    def test_the_user_agent_names_the_reader_and_still_reads(self):
        """A school that refuses one agent may accept a browser.  Both."""
        agent = scout._USER_AGENT
        self.assertIn("SmartBusinessWriter", agent)
        # A browser-compatible prefix: the fetch is not refused outright.
        self.assertTrue(agent.startswith("Mozilla/5.0"), agent)

    def test_the_body_is_stripped_and_then_capped(self):
        """The reader is given the words, not the head of the document."""
        with self._stub_fetch(CHROME_FIRST):
            snap = scout.scout_url("https://www.example-school.edu/course",
                                   allowlist=self._allow())
        stored = snap.get("_text") or ""
        self.assertNotIn("<path", stored)
        self.assertNotIn("xxxx", stored)
        self.assertIn("Business Model Canvas", stored)
        # The cap counts readable characters, not markup.
        self.assertLessEqual(len(stored), scout.MAX_TEXT_CHARS)

    def test_a_render_is_kept_when_it_is_longer_than_the_fetch(self):
        """The browser's reading must survive the comparison."""
        rendered_text = "The course teaches the Business Model Canvas in depth."

        with self._stub_fetch("<html><body><nav>Menu</nav></body></html>"):
            with mock.patch.object(scout_render, "available", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "take_render", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "render_text",
                                   staticmethod(lambda url, allowlist=None, timeout_ms=None:
                                                (rendered_text, ""))):
                snap = scout.scout_url("https://www.example-school.edu/course",
                                       allowlist=self._allow())
        self.assertTrue(snap.get("rendered"))
        self.assertIn("Business Model Canvas", snap.get("_text") or "")

    def test_a_render_is_not_kept_when_it_says_less(self):
        """A render that adds nothing does not replace the fetch."""
        with self._stub_fetch(COURSE_PAGE):
            with mock.patch.object(scout_render, "available", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "take_render", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "render_text",
                                   staticmethod(lambda url, allowlist=None, timeout_ms=None:
                                                ("Menu", ""))):
                snap = scout.scout_url("https://www.example-school.edu/course",
                                       allowlist=self._allow())
        self.assertFalse(snap.get("rendered"))
        self.assertIn("Business Model Canvas", snap.get("_text") or "")

    def test_a_failed_fetch_is_offered_to_the_browser(self):
        """A 403 has no text, so the browser is the only path to the page."""
        with mock.patch.object(scout, "_fetch_url", return_value=(403, "", "HTTP 403")):
            with mock.patch.object(scout_render, "available", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "take_render", staticmethod(lambda: True)), \
                 mock.patch.object(scout_render, "render_text",
                                   staticmethod(lambda url, allowlist=None, timeout_ms=None:
                                                ("This course teaches the Business Model Canvas.", ""))):
                snap = scout.scout_url("https://www.example-school.edu/course",
                                       allowlist=self._allow())
        self.assertTrue(snap.get("rendered"))
        self.assertIn("Business Model Canvas", snap.get("_text") or "")

    def test_a_bot_check_is_not_stored_as_the_page(self):
        """A challenge page is not the school's words about the framework."""
        challenge = ("<html><body><h1>Confirm you are human</h1>"
                     "<p>This step verifies you are human.</p></body></html>")
        with mock.patch.object(scout, "_fetch_url", return_value=(202, challenge, "")):
            snap = scout.scout_url("https://www.example-school.edu/course",
                                   allowlist=self._allow())
        self.assertEqual(snap.get("_text") or "", "")
        self.assertTrue(snap.get("error"))

    def test_a_challenge_is_detected_by_its_own_words(self):
        self.assertTrue(scout._detect_challenge("Confirm you are human", 202))
        self.assertTrue(scout._detect_challenge("Checking your browser before access", 429))
        self.assertFalse(scout._detect_challenge("A normal course page", 200))
        self.assertFalse(scout._detect_challenge("", 202))


class ReaderLabelTest(RelevanceTestCase):
    """A page that names the framework must record the framework."""

    def test_the_short_name_of_a_framework_is_matched(self):
        """The taxonomy names it long; a course page writes it short."""
        found = reader._named_topics(
            "This course teaches Five Forces analysis of the competitive market.")
        self.assertIn("Porter's Five Forces", found)

    def test_the_short_name_of_ansoff_is_matched(self):
        found = reader._named_topics("Students use Ansoff to pick a growth direction.")
        self.assertIn("Ansoff Growth Matrix", found)

    def test_the_long_name_still_matches(self):
        found = reader._named_topics("The course covers Porter's Five Forces analysis.")
        self.assertIn("Porter's Five Forces", found)

    def test_a_page_that_names_nothing_records_nothing(self):
        self.assertEqual(reader._named_topics("Nothing relevant here."), [])

    def test_the_alias_is_data_and_not_a_special_case(self):
        """The spelling lives in the owner-edited taxonomy."""
        from bp.product.relevance import s0_scope
        taxonomy = s0_scope.load_taxonomy() or {}
        by_id = {t.get("id"): t for t in taxonomy.get("topics", [])}
        self.assertIn("Five Forces", by_id["framework_five_forces"].get("aliases", []))
        self.assertIn("Ansoff", by_id["framework_ansoff"].get("aliases", []))


class VerbatimExcerptTest(RelevanceTestCase):
    """The excerpt a person quotes must be the passage the page carries.

    The model copies a passage as it reads it, and it reads a list as one
    line.  The page carries the items on separate lines.  The passage is the
    same passage, so the check may not throw it away — but the check is
    still done by code, and still refuses anything the page does not say.
    """

    def test_a_passage_copied_across_a_line_break_is_accepted(self):
        page = ("Assessment:\n\n Partial written exam: 40%\n\n"
                " End-of-term written exam: 40%\n\n Group project: 20%")
        excerpt = "Partial written exam: 40% End-of-term written exam: 40% Group project: 20%"
        self.assertTrue(reader._verify_excerpt_verbatim(excerpt, page))

    def test_a_passage_the_page_does_not_carry_is_refused(self):
        page = ("Assessment:\n\n Partial written exam: 40%\n\n"
                " End-of-term written exam: 40%\n\n Group project: 20%")
        self.assertFalse(reader._verify_excerpt_verbatim(
            "Partial written exam: 60% Group project: 40%", page))
        self.assertFalse(reader._verify_excerpt_verbatim(
            "The final grade is 100% coursework.", page))

    def test_a_paraphrase_is_refused(self):
        """The words must be the page's, in the page's order."""
        page = "The final grade consists of a written exam and a group project."
        self.assertFalse(reader._verify_excerpt_verbatim(
            "The grade is made of an exam and a project.", page))

    def test_an_empty_excerpt_is_refused(self):
        self.assertFalse(reader._verify_excerpt_verbatim("", "some text here"))

    def test_the_excerpt_the_model_chose_is_kept(self):
        """The reader must not fall back to the navigation menu."""
        page = ("Strategy and Innovation\n\n"
                " This course teaches the Business Model Canvas and the Ansoff "
                "Growth Matrix.\n\n"
                " Partial written exam: 40%\n\n"
                " End-of-term written exam: 40%\n\n"
                " Group project: 20%")
        excerpt = "Partial written exam: 40% End-of-term written exam: 40% Group project: 20%"
        record, error = reader.snapshot_to_evidence(
            {"url": "https://www.example-school.edu/course",
             "domain": "www.example-school.edu",
             "fetched_at": "2026-11-10T00:00:00+00:00",
             "sha256": "0" * 64,
             "paywalled": False,
             "_text": page},
            excerpt=excerpt, use_model=False)
        self.assertEqual(error, "")
        self.assertIsNotNone(record)
        self.assertIn("Partial written exam", record.excerpt)
        self.assertNotIn("Skip to main content", record.excerpt)


class ControlSeesThePageTest(RelevanceTestCase):
    """The control set must hold when the sweep read the name."""

    def _rows(self):
        from bp.product.relevance import s3_mapper
        taxonomy = __import__("bp.product.relevance.s0_scope", fromlist=["x"]).load_taxonomy()
        return s3_mapper.map_coverage(taxonomy, evidence_records=[])

    def test_a_framework_control_holds_when_the_name_was_read(self):
        """The whole point: read the name, hold the control."""
        from bp.product.relevance import controls as rcontrols
        evidence = [{
            "excerpt": "This course teaches Five Forces analysis of the market.",
            "mentions": ["Porter's Five Forces"],
        }]
        result = rcontrols.check(self._rows(), evidence_records=evidence)
        held = {h.get("id") for h in (result.get("held_items") or [])}
        self.assertIn("ctrl_five_forces", held)
        self.assertNotIn("ctrl_five_forces",
                         {m.get("id") for m in (result.get("missing_items") or [])})

    def test_a_control_still_fails_when_nothing_was_read(self):
        """A control that scores zero is evidence about the method."""
        from bp.product.relevance import controls as rcontrols
        result = rcontrols.check(self._rows(), evidence_records=[])
        missing = {m.get("id") for m in (result.get("missing_items") or [])}
        self.assertIn("ctrl_five_forces", missing)
        self.assertFalse(result.get("passed"))


if __name__ == "__main__":
    unittest.main()
