"""The render contract: a frozen record, and a workbook that may only present what it holds.

Two jobs, both for the design lane's render layer:

1. **A fixture that does not move.**  `tests/fixtures/statements-record.json` is one solved
   engagement with all four statements rendered.  It is rebuilt deterministically from the golden
   engagement, so a pipeline change that alters a figure fails here and forces a deliberate
   regeneration (`python qa/manual/make_statements_fixture.py`), never a silent drift.
2. **A read-back harness.**  `tests/xlsx_read.py` unzips a workbook and returns its cells, so a
   renderer is tested on what it wrote, not on "a file exists".  These tests exercise the harness on
   the current writer and prove the three cash-flow reconciliations a renderer must preserve.
"""

import json
import os
import sys
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.join(ROOT, "src"), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp.product import spreadsheets, statements_verify, verify  # noqa: E402
import product_statements_fixture as fixture  # noqa: E402
import xlsx_read  # noqa: E402

STATEMENT_KEYS = ("income_statement", "equity", "balance_sheet", "cash_flow")


def pairs(rows):
    """The label/amount pairs of a sheet, in either workbook shape.

    A text-dump sheet writes the whole rendered line in one cell; a typed sheet writes the label and
    the amount in adjacent cells.  A renderer may produce either, and the contract is the same.
    """
    found = []
    for row in rows:
        cells = [cell for cell in row if cell != ""]
        if not cells:
            continue
        if len(cells) == 1 and isinstance(cells[0], str):
            label, value = xlsx_read.line_value(cells[0])
            if value is not None:
                found.append((label.strip(), value))
            continue
        label = next((cell for cell in cells if isinstance(cell, str) and cell.strip()), None)
        if label is None:
            continue
        rest = cells[cells.index(label) + 1:]
        value = next((cell for cell in rest if isinstance(cell, Decimal)), None)
        if value is None:
            value = next((xlsx_read.amount(cell) for cell in rest
                          if isinstance(cell, str) and xlsx_read.amount(cell) is not None), None)
        if value is not None:
            found.append((label.strip(), value))
    return found


def workbook_for(record):
    """The workbook the current writer produces for a statements record.

    The writer expects a case bundle whose `delivery.appendix.accounts` carries the accounting
    appendix; the record's `core.appendix` has exactly those keys (`statements_export`,
    `trial_balance`, `journal`, `checks`).
    """
    bundle = {"id": "fixture", "title": "Statements fixture", "method": "management_accounts",
              "tier": "T2", "created_at": "2026-11-04T00:00:00Z",
              "delivery": {"appendix": {"accounts": record["core"]["appendix"]}}}
    return spreadsheets.to_xlsx(bundle)


class FixtureTest(unittest.TestCase):
    """The committed fixture is a complete, solved, all-four-statements record."""

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()

    def test_it_is_a_solved_full_request(self):
        record = self.record
        self.assertEqual(record["format"], "bp-statements/1")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["requested"], ["IS", "RE", "BS", "CF"])
        self.assertEqual(record["computed"], ["IS", "RE", "BS", "CF"])
        self.assertEqual(record["hidden"], [])
        self.assertEqual(record["warnings"], [])

    def test_every_statement_is_rendered(self):
        for key in STATEMENT_KEYS:
            self.assertTrue(self.record["statements"][key],
                            "%s is empty; the fixture must exercise all four" % key)
        self.assertIsNone(self.record["statements"]["cash_flow_withheld_because"])

    def test_the_output_verifier_accepts_it(self):
        self.assertEqual(
            statements_verify.verify_output(self.record["statements"], self.record["requested"]), [])

    def test_it_is_frozen_and_regenerates_byte_identically(self):
        self.assertEqual(verify.freeze(dict(self.record)), self.record,
                         "the record was edited after freezing, or freeze() is not deterministic")
        fresh = fixture.record()
        self.assertEqual(json.loads(json.dumps(fresh)), self.record,
                         "the pipeline changed; regenerate only if the change was intended: "
                         "python qa/manual/make_statements_fixture.py")


class ArticulationTest(unittest.TestCase):
    """The figures the renderer must present, checked against the core's own statements."""

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()
        cls.scalars = cls.record["core"]["scalars"]
        cls.cash = cls.record["core"]["appendix"]["cash_flow"]

    def test_every_core_check_passes(self):
        self.assertEqual([check["name"] for check in self.record["checks"] if not check["ok"]], [])
        self.assertEqual(self.scalars["checks_na"], "2",
                         "the two reconciliation checks need inputs this engagement does not declare")

    def test_the_balance_sheet_balances(self):
        self.assertEqual(Decimal(self.scalars["total_assets"]),
                         Decimal(self.scalars["total_liabilities"]) + Decimal(self.scalars["total_equity"]))
        self.assertEqual(Decimal(self.scalars["total_assets"]), Decimal("178100"))
        self.assertEqual(Decimal(self.scalars["net_income"]), Decimal("52575"))

    def test_the_three_cash_flow_reconciliations_hold(self):
        operating, investing, financing = (Decimal(self.cash["operating"]),
                                           Decimal(self.cash["investing"]),
                                           Decimal(self.cash["financing"]))
        net = Decimal(self.cash["net_direct"])
        self.assertEqual(operating + investing + financing, net)
        self.assertEqual(Decimal(self.cash["net_indirect"]), net)
        self.assertEqual(net, Decimal(self.scalars["cash_net"]))
        self.assertEqual([name for name, ok, _detail in self.cash["checks"] if not ok], [])

    def test_the_ending_cash_matches_the_balance_sheet(self):
        groups = self.record["core"]["appendix"]["balance_sheet_groups"]["groups"]
        self.assertEqual(Decimal(groups["current_assets"]["Cash"]),
                         Decimal(self.cash["net_direct"]))

    def test_retained_earnings_rolls_forward(self):
        equity = self.record["core"]["appendix"]["equity_statement"]
        self.assertEqual(Decimal(equity["by_kind"]["profit for the period"]),
                         Decimal(self.scalars["net_income"]))
        self.assertEqual(Decimal(self.scalars["retained_earnings_closing"]),
                         Decimal(self.scalars["net_income"]),
                         "no opening retained earnings and no dividend in this engagement")


class WorkbookTest(unittest.TestCase):
    """The harness reads a real workbook, and every figure on it is a figure the record holds."""

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()
        cls.data = workbook_for(cls.record)
        cls.sheets = xlsx_read.read(cls.data)

    def test_the_workbook_opens_and_carries_the_statements(self):
        """The three statements the current writer emits; the equity sheet is the render lane's gap.

        `spreadsheets._accounting_rows()` copies `statements_export`, which does not carry the
        statement of changes in equity (it lives in `appendix.equity_statement_export`).  The render
        layer adds that sheet; this test does not pin its absence, it pins what exists today.
        """
        self.assertTrue(self.sheets, "the workbook has no sheets")
        text = "\n".join(str(cell) for rows in self.sheets.values() for row in rows for cell in row)
        for heading in ("INCOME STATEMENT", "BALANCE SHEET", "CASH FLOW STATEMENT"):
            self.assertIn(heading, text)
        self.assertTrue(self.record["statements"]["equity"],
                        "the record renders the equity statement even though the export omits it")

    def test_the_figures_the_statements_must_show_are_there(self):
        shown = {}
        for rows in self.sheets.values():
            for label, value in pairs(rows):
                shown.setdefault(label.lower(), value)
        expected = {
            "revenue": Decimal("200000"),
            "total expenses": Decimal("147425"),
            "net income": Decimal("52575"),
            "total assets": Decimal("178100"),
            "total liabilities": Decimal("75525"),
            "total equity": Decimal("102575"),
            "total operating activities": Decimal("74600"),
            "net change in cash": Decimal("104600"),
            "cash at end of period": Decimal("104600"),
        }
        for label, value in expected.items():
            self.assertIn(label, shown, "the workbook has no '%s' row" % label)
            self.assertEqual(shown[label], value, "%s reads %s" % (label, shown[label]))

    def test_no_figure_is_invented_by_the_renderer(self):
        held = fixture.typed_numbers(self.record)
        rendered = set()
        for rows in self.sheets.values():
            rendered.update(xlsx_read.numbers(rows))
            rendered.update(xlsx_read.numbers_in_text(rows))
        invented = sorted(value for value in rendered if value not in held)
        self.assertEqual(invented, [], "the workbook shows figures the record does not hold")

    def test_two_exports_of_the_same_record_are_identical(self):
        self.assertEqual(workbook_for(self.record), workbook_for(self.record))
