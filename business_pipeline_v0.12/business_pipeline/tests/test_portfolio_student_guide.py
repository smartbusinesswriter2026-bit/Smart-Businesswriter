"""The Portfolio Lab teaches itself: four worked cases, and the labels they tell you to click.

The owner asked for a student-facing walkthrough in the terms a finance student uses -
"pick my stocks", "value my book", "run my fund for the term", "compute the risk" - with the
exact clicks. Those instructions are only honest if every label they name exists on the page,
so this file pins the guide's cases and cross-checks its click labels against `web/index.html`.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "PORTFOLIO_LAB_STUDENT_GUIDE.md").read_text(encoding="utf-8")

CASE_TITLES = (
    "Case 1 — \"Which stocks should I put in my portfolio paper?\"",
    "Case 2 — \"Value my portfolio on one date and hand in the report\"",
    "Case 3 — \"Run a mock fund for the semester and report a time-weighted return\"",
    "Case 4 — \"Compute the risk and return of my stock (and a two-asset portfolio)\"",
)

# The labels the guide tells a student to click or type into. Each must exist on the page.
CLICK_LABELS = (
    "Add symbols",
    "Use my watch list",
    "Screen these symbols",
    "Include fundamentals",
    "Add a holding",
    "Why you hold it",
    "Create portfolio",
    "Fetch prices (Alpha Vantage)",
    "Create the snapshot",
    "Download the report (.docx)",
    "Export the report",
    "Compute the return",
    "Save the entry",
    "Seed 30 days",
    "Record price",
    "Prefill single-asset risk",
    "Prefill two-asset portfolio",
    "Open in the Business Calculator",
    "Snapshot date",
    "Risk-free rate (decimal)",
)

ADVICE_PHRASES = (
    "we recommend", "you should buy", "will rise", "guaranteed return",
    "target price", "buy now", "top pick", "expected return of",
)
GLOBAL_WORDS = ("PSE", "Philippines", "Philippine", "Filipino", "peso")


class GuideContentTest(unittest.TestCase):
    def test_the_guide_carries_four_worked_cases(self):
        for title in CASE_TITLES:
            self.assertIn(title, GUIDE)

    def test_each_case_names_the_assignment_the_clicks_and_the_write_up(self):
        sections = GUIDE.split("## Case ")[1:]
        self.assertEqual(len(sections), 4)
        for section in sections:
            for marker in ("**The assignment.**", "**You need:**", "**Click by click**",
                           "**You should see**", "**Write this in your paper.**",
                           "**What it does not do.**"):
                self.assertIn(marker, section, section[:60])

    def test_the_guide_numbered_steps_are_really_numbered(self):
        body = GUIDE.split("**Click by click**")[1]
        self.assertIn("\n1. ", body)
        self.assertIn("\n2. ", body)

    def test_the_guide_shows_the_gap_rule_and_its_own_limits(self):
        self.assertIn("named gap", GUIDE)
        self.assertIn("not a recommendation", GUIDE)
        self.assertIn("It does not recommend a stock", GUIDE)
        for phrase in ("no fees", "tax", "dividends", "FX", "long-only"):
            self.assertIn(phrase, GUIDE, phrase)

    def test_the_guide_does_not_read_as_advice_or_forecast(self):
        text = GUIDE.lower()
        for phrase in ADVICE_PHRASES:
            self.assertNotIn(phrase, text, "the teaching guide must not advise: " + phrase)

    def test_the_guide_stays_global(self):
        for word in GLOBAL_WORDS:
            self.assertNotIn(word, GUIDE, "the portfolio guide must stay global: " + word)


class ClickLabelsExistOnThePageTest(unittest.TestCase):
    def test_every_label_the_guide_tells_you_to_click_is_on_the_page(self):
        missing = [label for label in CLICK_LABELS if label not in PAGE]
        self.assertEqual(missing, [], "the guide names controls the page does not have: " + repr(missing))

    def test_the_guide_and_the_page_share_the_tab_names(self):
        for tab in ("Watch list and prices", "Find candidates", "Evaluate",
                    "Holdings", "Prices and snapshot", "Journal and return"):
            self.assertIn(tab, PAGE, tab)
            self.assertIn(tab, GUIDE, tab)


class InAppCasesTest(unittest.TestCase):
    def test_the_landing_renders_the_worked_cases(self):
        self.assertIn("function pfWorkedCases", PAGE)
        self.assertIn('id="pfworkedcases"', PAGE)
        self.assertIn("pfWorkedCases() +", PAGE)
        self.assertIn("Four worked cases, click by click", PAGE)

    def test_the_four_cases_are_present_with_start_buttons(self):
        for go in ("data-pfcase=\"' + esc(item.go)", '"paper"', '"fund"', '"screen"', '"risk"'):
            self.assertIn(go, PAGE, go)
        for cta in ("Start this case: open the watch list",
                    "Start this case: create the paper book",
                    "Start this case: create the fund book",
                    "Start this case: open Evaluate"):
            self.assertIn(cta, PAGE, cta)

    def test_a_start_button_only_opens_the_right_control_and_creates_nothing(self):
        self.assertIn("async function pfStartCase(name)", PAGE)
        self.assertIn("$$(\"[data-pfcase]\", out)", PAGE)
        start = PAGE.split("async function pfStartCase(name) {")[1].split("function pfGuidanceCard()")[0]
        self.assertIn("plShowTab(", start)
        self.assertIn("field.focus()", start)
        # It navigates and focuses; it never posts, creates a book or runs a method.
        for forbidden in ("post(", "api(", "plScreen(", "plRisk("):
            self.assertNotIn(forbidden, start, "pfStartCase must not " + forbidden)

    def test_the_cases_name_the_same_four_assignments_as_the_guide(self):
        for phrase in ("Pick candidates for a stock-selection paper",
                       "Value the book on one date and hand in the report",
                       "Run a mock fund for the semester and report the time-weighted return",
                       "Compute the risk and return of a stock and of a two-asset portfolio"):
            self.assertIn(phrase, PAGE, phrase)


if __name__ == "__main__":
    unittest.main()
