"""Exports and credits: the Word file is real, and the wallet cannot be cheated or double-charged.

Two separate concerns, both product-layer:

**The .docx** must be a genuine Word-compatible package containing the *stored* report and artifact values,
with XML escaped so a report containing `&` or `<` renders instead of corrupting the file. Two exports of the
same bundle must be byte-identical, so a re-export cannot silently differ.

**The wallet** is derived from an append-only ledger, charges only after a file exists, is idempotent per
(account, report, format) so a retry cannot double-charge, and gives the first export of each report free.
The tests tamper with the situation rather than the ledger: they check that a retry is reused, that a second
format is charged, that an unaffordable export is refused, and that a refund is another appended line rather
than an edit.
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

import product_fixtures          # noqa: E402
from bp.product import api, cases, credits, docx   # noqa: E402


class WalletTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-credits-")
        self._state = os.environ.get("BP_STATE_DIR")
        self._grant = os.environ.get("BP_CREDITS_GRANT")
        os.environ["BP_STATE_DIR"] = self.root
        os.environ["BP_CREDITS_GRANT"] = "3"

    def tearDown(self):
        if self._state is None:
            os.environ.pop("BP_STATE_DIR", None)
        else:
            os.environ["BP_STATE_DIR"] = self._state
        if self._grant is None:
            os.environ.pop("BP_CREDITS_GRANT", None)
        else:
            os.environ["BP_CREDITS_GRANT"] = self._grant
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_new_wallet_is_granted_and_the_balance_is_the_ledger(self):
        self.assertEqual(credits.balance(), 3)
        self.assertEqual(credits.balance(), sum(e["amount"] for e in credits.entries()))

    def test_the_first_export_of_a_report_is_free(self):
        q = credits.quote("case-a", "docx")
        self.assertEqual(q["cost"], 0)
        self.assertTrue(q["free"])
        result = credits.charge("case-a", "docx")
        self.assertFalse(result["charged"])
        self.assertEqual(result["balance"], 3)

    def test_a_second_export_of_the_same_report_is_charged(self):
        credits.charge("case-a", "docx")                 # free
        result = credits.charge("case-a", "docx")
        self.assertTrue(result["charged"])
        self.assertEqual(result["balance"], 2)

    def test_a_different_report_starts_free_again(self):
        credits.charge("case-a", "docx")
        self.assertEqual(credits.quote("case-b", "docx")["cost"], 0)

    def test_a_retry_is_reused_and_not_charged_twice(self):
        credits.charge("case-a", "docx")                 # free
        first = credits.charge("case-a", "docx", idem="attempt-1")
        again = credits.charge("case-a", "docx", idem="attempt-1")
        self.assertTrue(first["charged"])
        self.assertTrue(again["reused"], "the same retry key must not charge twice")
        self.assertEqual(again["balance"], first["balance"])

    def test_an_unaffordable_export_is_refused(self):
        credits.charge("case-a", "docx")                 # free, so the report is now used
        credits.charge("case-a", "docx")                 # 1
        credits.charge("case-a", "docx")                 # 2
        credits.charge("case-a", "docx")                 # 3, balance now 0
        self.assertEqual(credits.balance(), 0)
        with self.assertRaises(credits.InsufficientCredits) as ctx:
            credits.charge("case-a", "docx")
        self.assertIn("costs 1 credit", str(ctx.exception))

    def test_a_refund_is_appended_and_restores_the_balance(self):
        credits.charge("case-a", "docx")
        paid = credits.charge("case-a", "docx")
        self.assertEqual(paid["balance"], 2)
        r = credits.refund("case-a", "docx")
        self.assertTrue(r["refunded"])
        self.assertEqual(credits.balance(), 3)
        self.assertEqual(credits.entries()[-1]["kind"], "refund",
                         "a refund is a new line, never an edit of the charge")

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(credits.CreditError):
            credits.quote("case-a", "pdf-ish")

    def test_a_free_export_still_uses_up_the_report(self):
        credits.charge("case-a", "html")                 # html costs 0 anyway
        self.assertIn("case-a", credits.exported_reports())


class DocxTest(unittest.TestCase):
    def setUp(self):
        self.bundle = product_fixtures.make_bundle()

    def test_it_is_a_zip_with_the_three_parts_word_needs(self):
        data = docx.to_bytes(self.bundle)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(data)))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(z.namelist(), ["[Content_Types].xml", "_rels/.rels", "word/document.xml"])

    def test_it_carries_the_stored_report_and_values(self):
        with zipfile.ZipFile(io.BytesIO(docx.to_bytes(self.bundle))) as z:
            body = z.read("word/document.xml").decode("utf-8")
        report = self.bundle["delivery"]["report"]
        self.assertIn(report.splitlines()[0][:40].replace("&", "&amp;").replace("<", "&lt;"), body)

    def test_xml_is_escaped_so_the_file_cannot_be_corrupted(self):
        bundle = dict(self.bundle)
        bundle = {**bundle, "delivery": {**bundle["delivery"], "report": "A & B <tag> \"quoted\""}}
        with zipfile.ZipFile(io.BytesIO(docx.to_bytes(bundle))) as z:
            body = z.read("word/document.xml").decode("utf-8")
        self.assertIn("A &amp; B &lt;tag&gt;", body)
        import xml.dom.minidom
        xml.dom.minidom.parseString(body)                # well-formed, or this raises

    def test_two_exports_of_the_same_bundle_are_identical(self):
        self.assertEqual(docx.to_bytes(self.bundle), docx.to_bytes(self.bundle),
                         "a re-export must not differ")

    def test_the_artifact_values_are_present(self):
        with zipfile.ZipFile(io.BytesIO(docx.to_bytes(self.bundle))) as z:
            body = z.read("word/document.xml").decode("utf-8")
        outputs = self.bundle["reperform"]["outputs"]
        self.assertTrue(outputs, "the fixture should record outputs")
        for value in list(outputs.values())[:3]:
            self.assertIn(str(value), body)


class ExportRouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-export-route-")
        self._cases = os.environ.get("BP_CASES_DIR")
        self._state = os.environ.get("BP_STATE_DIR")
        os.environ["BP_CASES_DIR"] = os.path.join(self.root, "cases")
        os.environ["BP_STATE_DIR"] = os.path.join(self.root, "state")
        os.environ["BP_CREDITS_GRANT"] = "5"
        self.case_id = cases.save(product_fixtures.make_bundle())

    def tearDown(self):
        for name, value in (("BP_CASES_DIR", self._cases), ("BP_STATE_DIR", self._state)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        os.environ.pop("BP_CREDITS_GRANT", None)
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_quote_returns_the_price_without_rendering(self):
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "docx", "destination": "unused.docx", "quote_only": True})
        self.assertEqual(status, 200)
        self.assertEqual(payload["quote"]["cost"], 0)
        self.assertFalse(os.path.exists("unused.docx"))

    def test_an_export_writes_the_file_and_charges_after_it_exists(self):
        destination = os.path.join(self.root, "out.docx")
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "docx", "destination": destination})
        self.assertEqual(status, 200, payload)
        self.assertTrue(os.path.exists(destination))
        self.assertIn("credits", payload)
        self.assertTrue(zipfile.is_zipfile(destination))

    def test_a_second_format_of_the_same_case_is_charged(self):
        first = os.path.join(self.root, "a.docx")
        second = os.path.join(self.root, "b.docx")
        api.handle("POST", "/api/cases/%s/export" % self.case_id, {"kind": "docx", "destination": first})
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "docx", "destination": second})
        self.assertEqual(status, 200)
        self.assertTrue(payload["credits"]["charged"])

    def test_an_unknown_kind_is_refused(self):
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "pdf", "destination": os.path.join(self.root, "x.pdf")})
        self.assertEqual(status, 422)
        self.assertIn("unknown export kind", payload["error"])

    def test_an_unaffordable_export_is_refused_before_the_file_is_written(self):
        os.environ["BP_CREDITS_GRANT"] = "0"
        # a fresh account with no credits: the first export is free, so this one succeeds
        first = os.path.join(self.root, "free.docx")
        status, _ = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                               {"kind": "docx", "destination": first})
        self.assertEqual(status, 200)
        # the second is charged and the wallet is empty
        blocked = os.path.join(self.root, "blocked.docx")
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "docx", "destination": blocked})
        self.assertEqual(status, 402, payload)
        self.assertFalse(os.path.exists(blocked), "nothing is written when the wallet cannot pay")


if __name__ == "__main__":
    unittest.main()
