import csv
import io
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

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

    def test_no_spreadsheet_carries_a_hash_or_an_internal_marker(self):
        """The owner's rule (B-199): a hash is the system's marker, never a student's cell."""
        for label, text in (("spreadsheetml", spreadsheets.to_spreadsheetml(bundle())),
                            ("xlsx", spreadsheets.export_xlsx(bundle(), os.path.join(
                                tempfile.mkdtemp(prefix="bp-nohash-"), "w.xlsx"))["path"])):
            if label == "xlsx":
                with zipfile.ZipFile(text) as archive:
                    text = " ".join(archive.read(name).decode("utf-8", "replace")
                                    for name in archive.namelist() if name.endswith(".xml"))
            self.assertNotIn("sha256", text, label)
            self.assertNotIn("hash", text.lower().replace("hashes", ""), label)

    def test_spreadsheetml_adds_a_schedule_sheet_for_cpm_artifacts(self):
        base = bundle()
        metrics = ("es_A", "ef_A", "ls_A", "lf_A", "float_A", "critical_A")
        base["delivery"]["appendix"]["artifacts"] = [
            [metric, [metric, "days", "entity", "base"], ""] for metric in metrics]
        base["reperform"]["outputs"] = {
            "es_A": "0", "ef_A": "3", "ls_A": "0", "lf_A": "3", "float_A": "0", "critical_A": "1"}
        text = spreadsheets.to_spreadsheetml(base)
        root = ET.fromstring(text)
        sheets = root.findall(SS + "Worksheet")
        self.assertEqual([sheet.get(SS + "Name") for sheet in sheets],
                         ["Case", "Artifacts", "Schedule", "Report"])
        cells = [cell.text for cell in sheets[2].findall(".//" + SS + "Cell/" + SS + "Data")]
        self.assertIn("Activity", cells)
        self.assertIn("A", cells)
        self.assertIn("3", cells)

    def test_xlsx_schedule_adds_a_coloured_bar_strip(self):
        import zipfile
        base = bundle()
        metrics = ("es_A", "ef_A", "ls_A", "lf_A", "float_A", "critical_A", "critical_count", "activity_count")
        base["delivery"]["appendix"]["artifacts"] = [
            [metric, [metric, "days", "entity", "base"], ""] for metric in metrics]
        base["reperform"]["outputs"] = {
            "es_A": "0", "ef_A": "3", "ls_A": "0", "lf_A": "3", "float_A": "0", "critical_A": "1",
            "critical_count": "1", "activity_count": "1"}
        data = spreadsheets.to_xlsx(base)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            schedule = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
        self.assertIn('s="3"', schedule)          # the critical bar fill
        self.assertNotIn('s="2"', schedule)       # no non-critical bar in a one-activity case
        self.assertIn(">0</t>", schedule)         # the period header is present
        self.assertNotIn(">count</t>", schedule)  # a critical_count total is not an activity row

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
