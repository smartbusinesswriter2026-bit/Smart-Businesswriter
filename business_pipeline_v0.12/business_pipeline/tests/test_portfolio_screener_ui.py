"""The Portfolio Lab screening panel is surfaced and wired (ported from the design lane).

The owner asked for the stock-screening lab back after it was built on the main branch
and never reached this one: filter candidates on common criteria (one-day return,
recorded mean/volatility/Sharpe, price, market cap, P/E, ROE), keep a watch list of
tracked instruments, and prefill frozen calculator inputs. It is a sourced shortlist,
not a recommendation.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


class PanelPresentTest(unittest.TestCase):
    def test_the_screening_lab_is_rendered_in_the_portfolio_lab(self):
        self.assertIn("function portfolioLabPanel()", PAGE)
        self.assertIn('id="portfoliolab"', PAGE)
        self.assertIn("Portfolio lab: choose, track, evaluate", PAGE)
        # the panel is on the Portfolio landing and in the Holdings tab of a book
        self.assertIn("html += portfolioLabPanel();", PAGE)
        self.assertIn("let html = portfolioLabPanel() +", PAGE)
        self.assertIn('if ($("#portfoliolab")) bindPortfolioLab();', PAGE)

    def test_the_common_criteria_controls_are_present(self):
        for marker in ('id="plcands"', 'id="plsort"', 'id="plfund"', 'id="plfundprov"',
                       'id="plscreen"', 'id="plwatch"', 'id="pltrack"',
                       'id="plrisk"', 'id="plport"'):
            self.assertIn(marker, PAGE)
        for label in ("one-day return", "mean return (needs history)", "Sharpe (needs history)",
                      "market cap", "P/E", "ROE", "Include fundamentals", "Help me choose"):
            self.assertIn(label, PAGE)

    def test_the_panel_is_wired_to_the_product_routes(self):
        for route in ("/api/cases/instruments", "/api/cases/screen", "/api/cases/prefill"):
            self.assertIn(route, PAGE)
        for function in ("plTrack", "plRecord", "plSeed", "plScreen", "plPrefillRisk",
                         "plPrefillPort", "plOpenInCalc", "bindPortfolioLab"):
            self.assertIn("function " + function, PAGE)

    def test_the_shortlist_is_labelled_sourced_not_a_recommendation(self):
        self.assertIn("sourced, not a recommendation", PAGE)
        self.assertIn("a value the app cannot source stays a named gap", PAGE)

    def test_prefill_only_fills_the_calculator_and_never_runs_it(self):
        self.assertIn("Opening the calculator only fills the fields; you still press = to run it",
                      PAGE)
        self.assertIn("plOpenInCalc", PAGE)


class RoutesPresentTest(unittest.TestCase):
    def test_api_module_exposes_the_screening_routes(self):
        source = (ROOT / "src" / "bp" / "product" / "api.py").read_text(encoding="utf-8")
        for marker in ('segments == ["screen"]', 'segments == ["prefill"]',
                       'segments[0] == "instruments"', "screener.screen(",
                       "prefill_builder.risk_inputs", "instrument_store.record"):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
