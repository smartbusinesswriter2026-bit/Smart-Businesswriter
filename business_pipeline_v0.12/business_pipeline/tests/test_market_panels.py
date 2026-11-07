"""The retrieved market-data panels are split by the consumer of each lookup (B-177).

The product is global. A panel that names a home exchange or a home country is a
product-identity defect, not a style choice: rates and FX belong to the finance
shelf, securities data belongs with the portfolio book, and macro data belongs to
economics. Every panel keeps the same boundary: it displays a value with its
source, date and response hash, and nothing is written into a tool automatically.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp.product import marketdata  # noqa: E402

PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "FINANCE_STUDENT_GUIDE.md").read_text(encoding="utf-8")
LIMITS = (ROOT / "docs" / "KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")


def _function(name):
    """The body of one page function, from its definition to the next blank line after a close."""
    start = PAGE.index("function %s(" % name)
    return PAGE[start:start + 6000]


class PanelSplitTest(unittest.TestCase):
    def test_three_panels_are_defined_and_the_single_panel_is_gone(self):
        for name in ("ratesPanel", "securitiesPanel", "macroPanel"):
            self.assertIn("function %s()" % name, PAGE)
        self.assertNotIn("function marketPanel", PAGE)
        self.assertNotIn('id="marketout"', PAGE)

    def test_each_panel_has_its_own_result_region(self):
        for marker in ('id="ratesout"', 'id="secout"', 'id="macroout"'):
            self.assertIn(marker, PAGE)

    def test_finance_gets_rates_and_economics_gets_macro(self):
        self.assertIn('if (s.id === "finance") html += ratesPanel();', PAGE)
        self.assertIn('if (s.id === "economics") html += macroPanel();', PAGE)
        self.assertNotIn("html += securitiesPanel();", PAGE)
        self.assertNotIn('if (s.id === "finance") html += macroPanel();', PAGE)

    def test_the_securities_panel_renders_inside_the_portfolio_book(self):
        book = PAGE.split("function pfData(", 1)[1].split("function addHolding(", 1)[0]
        self.assertIn("securitiesPanel()", book)

    def test_each_panel_binds_its_own_handlers(self):
        self.assertIn('if (s.id === "finance") bindRatesPanel();', PAGE)
        self.assertIn('if (s.id === "economics") bindMacroPanel();', PAGE)
        workspace = PAGE.split("function renderPortfolioWorkspace(", 1)[1].split("function pfTone(", 1)[0]
        self.assertIn("bindSecuritiesPanel();", workspace)

    def test_each_handler_writes_to_its_own_panel(self):
        for function, region in (("lookupFx", "ratesout"), ("lookupRiskfree", "ratesout"),
                                 ("lookupEquity", "secout"), ("lookupSec", "secout"),
                                 ("lookupMacro", "macroout")):
            body = PAGE.split("async function %s(" % function, 1)[1].split("\n\n", 1)[0]
            self.assertIn('$("#%s")' % region, body, function)

    def test_the_served_page_names_no_home_exchange_or_home_country(self):
        for forbidden in ("PSE", "Philippines", "Philippine", "Filipino", "Cebu", "PHP", "peso"):
            self.assertNotIn(forbidden, PAGE, "the page must stay global: " + forbidden)

    def test_the_never_auto_fill_boundary_survives_without_a_standing_sentence(self):
        """The owner deleted the Rates and FX foot line; the boundary did not go with it.

        It said "Both are published figures, not verified evidence: cite the date you
        read them. Nothing is auto-filled." True, but said twice: the panel's own intro
        tells the student to read a value, confirm it and type it in, and every result
        renders `marketFoot` - the publisher's name, an as-of date and a link to the
        source - so the citation travels with the figure. Securities keeps
        its sentence because it invites a bulk read of filings.
        """
        rates = _function("ratesPanel").split("\nfunction ", 1)[0]
        self.assertNotIn("Nothing is auto-filled.", rates, "the owner deleted this line")
        self.assertIn("type it into the tool that needs it", rates,
                      "the read-then-type instruction is what makes the boundary real")
        self.assertIn("nothing is auto-filled", _function("securitiesPanel"))
        foot = PAGE.split("function marketFoot(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("data.source", foot, "the result names its publisher")

    def test_rates_and_fx_is_a_disclosure_that_starts_closed(self):
        body = _function("ratesPanel").split("\nfunction ", 1)[0]
        self.assertIn('<details class="marketpanel">', body, "the panel is a disclosure")
        self.assertNotIn('<details class="marketpanel" open>', body,
                         "the shelf opens on its tiles, not the panel")
        self.assertIn("<summary>", body)
        self.assertLess(body.index("<summary>"), body.index('<div class="marketgrid">'),
                        "the cards sit inside the body, not the header")

    def test_rates_and_fx_gives_each_lookup_its_own_card(self):
        """Eight controls in one row left the reader guessing which button read which field."""
        body = _function("ratesPanel").split("\nfunction ", 1)[0]
        self.assertIn('<div class="marketgrid">', body)
        self.assertEqual(body.count('<div class="lookupcard">'), 2, "one card per lookup")
        for marker in ('id="fxbase"', 'id="fxquote"', 'id="fxdate"', 'id="rfmat"',
                       'id="fxlookup"', 'id="rflookup"', 'id="ratesout"'):
            self.assertIn(marker, body, "the handler binds this id: " + marker)
        self.assertNotIn('class="marketrow"', body, "the single mixed row is gone")
        # each button follows the fields it actually reads
        self.assertLess(body.index('id="fxdate"'), body.index('id="fxlookup"'))
        self.assertLess(body.index('id="rfmat"'), body.index('id="rflookup"'))
        self.assertLess(body.index('id="fxlookup"'), body.index('id="rfmat"'),
                        "the FX button must not sit inside the Treasury card")


class GlobalProductCopyTest(unittest.TestCase):
    def test_the_market_data_status_note_is_global(self):
        note = marketdata.status()["note"]
        for forbidden in ("PSE", "Philippines", "Philippine"):
            self.assertNotIn(forbidden, note)

    def test_the_student_guide_and_limits_name_no_home_market(self):
        for text, label in ((GUIDE, "FINANCE_STUDENT_GUIDE"), (LIMITS, "KNOWN_LIMITATIONS")):
            for forbidden in ("PSE", "Philippines", "Philippine"):
                self.assertNotIn(forbidden, text, label + " must stay global: " + forbidden)


if __name__ == "__main__":
    unittest.main()
