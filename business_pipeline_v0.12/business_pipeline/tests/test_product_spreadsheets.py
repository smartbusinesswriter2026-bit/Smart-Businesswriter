import csv
import io
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import spreadsheets  # noqa: E402

SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def bundle():
    base = product_fixtures.make_bundle()
    base["delivery"]["appendix"]["artifacts"] = [
        ["npv", ["npv", "annual", "entity", "base"], "npv = sum(cf / (1 + rate) ** t)"],
    ]
    base["reperform"]["outputs"] = {"npv": "50.00"}
    return base


class SpreadsheetTest(unittest.TestCase):
    def test_csv_copies_the_stored_strings_exactly(self):
        text = spreadsheets.to_csv(bundle())
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[0], list(spreadsheets.CSV_HEADER))
        self.assertIn(["npv", "npv", "", "", "50.00", "npv = sum(cf / (1 + rate) ** t)"], rows)
        self.assertIn("50.00", text)                                 # two places, not 50.0
        self.assertEqual(text.count("\r"), 0)                        # deterministic LF endings

    def test_spreadsheetml_is_a_three_sheet_workbook_of_strings(self):
        text = spreadsheets.to_spreadsheetml(bundle())
        root = ET.fromstring(text)
        sheets = root.findall(SS + "Worksheet")
        self.assertEqual([sheet.get(SS + "Name") for sheet in sheets], ["Case", "Artifacts", "Report"])
        cells = sheets[1].findall(".//" + SS + "Cell/" + SS + "Data")
        self.assertTrue(all(cell.get(SS + "Type") == "String" for cell in cells))
        self.assertIn("50.00", [cell.text for cell in cells])
        self.assertIn("The net present value is 50.00 currency.", [cell.text for cell in sheets[2].findall(".//" + SS + "Data")])
        self.assertIn("sha256:spec-abc", [cell.text for cell in sheets[0].findall(".//" + SS + "Data")])

    def test_writing_spreadsheets_is_deterministic(self):
        self.assertEqual(spreadsheets.to_csv(bundle()), spreadsheets.to_csv(bundle()))
        self.assertEqual(spreadsheets.to_spreadsheetml(bundle()), spreadsheets.to_spreadsheetml(bundle()))

    def test_export_writes_the_files(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = spreadsheets.export_csv(bundle(), os.path.join(folder, "artifacts.csv"))
            xml_path = spreadsheets.export_spreadsheetml(bundle(), os.path.join(folder, "case.xml"))
            self.assertTrue(os.path.isfile(csv_path)); self.assertTrue(os.path.isfile(xml_path))
            self.assertIn("50.00", open(csv_path, encoding="utf-8").read())
            ET.fromstring(open(xml_path, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
