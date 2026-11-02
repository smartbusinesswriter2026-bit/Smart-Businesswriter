"""The Portfolio Lab screening panel is surfaced and wired (ported from the design lane).

The owner asked for the stock-screening lab back after it was built on the main branch
and never reached this one: filter candidates on common criteria (one-day return,
recorded mean/volatility/Sharpe, price, market cap, P/E, ROE), keep a watch list of
tracked instruments, and prefill frozen calculator inputs. It is a sourced shortlist,
not a recommendation.

The lab is organised as three tabs (watch list and prices, find candidates, evaluate)
so one task is on screen at a time, and a student can add any ticker they choose, one
or several at a time, instead of only the demo symbol.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


class PanelPresentTest(unittest.TestCase):
    def test_the_screening_lab_is_rendered_in_the_portfolio_lab(self):
        self.assertIn("function portfolioLabPanel(initialTab)", PAGE)
        self.assertIn('id="portfoliolab"', PAGE)
        self.assertIn("Choose, track, evaluate", PAGE)
        # the panel is on the Portfolio landing and in the "Find candidates" tab of a book
        self.assertIn('portfolioLabPanel("screen")', PAGE)
        self.assertIn('if ($("#portfoliolab")) bindPortfolioLab();', PAGE)

    def test_the_lab_is_split_into_one_task_per_tab(self):
        for panel in ('id="plpanel-watch"', 'id="plpanel-screen"', 'id="plpanel-prefill"'):
            self.assertIn(panel, PAGE)
        for tab in ('["watch", "Watch list and prices"]', '["screen", "Find candidates"]',
                    '["prefill", "Evaluate"]'):
            self.assertIn(tab, PAGE)
        self.assertIn('data-pltab="', PAGE)
        self.assertIn("function plShowTab", PAGE)
        self.assertIn("panel.hidden = panel.id !== \"plpanel-\" + name", PAGE)

    def test_the_common_criteria_controls_are_present(self):
        for marker in ('id="plcands"', 'id="plsort"', 'id="plfund"', 'id="plfundprov"',
                       'id="plscreen"', 'id="plwatch"',
                       'id="plrisk"', 'id="plport"', 'id="plusewatch"'):
            self.assertIn(marker, PAGE)
        for label in ("one-day return", "mean return (needs history)", "Sharpe (needs history)",
                      "market cap", "P/E", "ROE", "Include fundamentals", "Screen these symbols"):
            self.assertIn(label, PAGE)

    def test_a_student_can_add_any_symbols_not_only_the_demo_one(self):
        # a free-text box, a button, and the add handler that records each one
        self.assertIn('id="plnewsyms"', PAGE)
        self.assertIn('id="pladdsymbols"', PAGE)
        self.assertIn("function plAddSymbols", PAGE)
        self.assertIn('placeholder="AAPL, MSFT, JPM"', PAGE)
        # several at once, provider passed through, each recorded at a sourced price
        self.assertIn('raw.split(/[\\s,;]+/)', PAGE)
        self.assertIn("{ symbol: symbol, record: true, provider: provider }", PAGE)
        self.assertIn("function plRemoveSymbol", PAGE)
        # no hardcoded demo ticker in the watch-list entry box
        self.assertNotIn('id="plsym" value="AAPL"', PAGE)

    def test_the_panel_is_wired_to_the_product_routes(self):
        for route in ("/api/cases/instruments", "/api/cases/screen", "/api/cases/prefill"):
            self.assertIn(route, PAGE)
        for function in ("plAddSymbols", "plRemoveSymbol", "plRecord", "plSeed", "plScreen",
                         "plPrefillRisk", "plPrefillPort", "plOpenInCalc", "bindPortfolioLab"):
            self.assertIn("function " + function, PAGE)

    def test_the_shortlist_is_labelled_sourced_not_a_recommendation(self):
        self.assertIn("sourced, not a recommendation", PAGE)
        self.assertIn("stays a named gap", PAGE)

    def test_prefill_only_fills_the_calculator_and_never_runs_it(self):
        self.assertIn("Opening the calculator only fills the fields; you still press = to run it",
                      PAGE)
        self.assertIn("it never runs the method", PAGE)
        self.assertIn("plOpenInCalc", PAGE)


class RoutesPresentTest(unittest.TestCase):
    def test_api_module_exposes_the_screening_routes(self):
        source = (ROOT / "src" / "bp" / "product" / "api.py").read_text(encoding="utf-8")
        for marker in ('segments == ["screen"]', 'segments == ["prefill"]',
                       'segments[0] == "instruments"', "screener.screen(",
                       "prefill_builder.risk_inputs", "instrument_store.record"):
            self.assertIn(marker, source)


class ButtonFeedbackTest(unittest.TestCase):
    """Every action in the lab and the book says what happened (B-185 follow-up).

    A click that re-renders silently leaves a student unable to tell success from a
    dropped request, so each action that changes the book now confirms itself.
    """

    def test_the_book_market_panel_no_longer_carries_the_disclaimer(self):
        self.assertNotIn("Market data for the book (retrieved, not verified)", PAGE)
        self.assertIn("Market data for the book", PAGE)

    def test_each_action_confirms_itsown_success(self):
        for marker in ("Snapshot created",
                       "Recorded today's sourced price for ",
                       "Holding \" + symbol + \" removed.",
                       "Journal entry for ",
                       "Added and recorded: ",
                       "Already on the watch list: "):
            self.assertIn(marker, PAGE)

    def test_the_in_book_controls_are_rendered_and_bound(self):
        for marker in ('id="pfaddholding"', 'data-pfremove', 'id="pfsnapshot"', 'id="pffetch"',
                       'id="pfhimportbtn"', 'id="pfpimportbtn"', 'id="pfhfile"', 'id="pfpfile"',
                       'id="pfperform"', 'id="pfsavejournal"', 'id="pfexport2"'):
            self.assertIn(marker, PAGE)
        for handler in ('$("#pfsnapshot")', '$("#pffetch")', '$("#pfhimportbtn")',
                        '$("#pfpimportbtn")', '$("#pfhfile")', '$("#pfpfile")',
                        '$("#pfperform")', '$("#pfsavejournal")', '$("#pfaddholding")'):
            self.assertIn(handler, PAGE)


if __name__ == "__main__":
    unittest.main()
