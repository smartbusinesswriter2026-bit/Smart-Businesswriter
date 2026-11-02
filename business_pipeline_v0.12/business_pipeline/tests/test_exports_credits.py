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
import json
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

    def test_the_first_export_of_an_artefact_is_free(self):
        q = credits.quote("case-a", "submission", "docx")
        self.assertEqual(q["cost"], 0)
        self.assertTrue(q["free"])
        result = credits.charge("case-a", "submission", "docx")
        self.assertFalse(result["charged"])
        self.assertEqual(result["balance"], 3)

    def test_a_second_export_of_the_same_artefact_is_charged(self):
        credits.charge("case-a", "submission", "docx")            # free
        q = credits.quote("case-a", "submission", "docx")
        self.assertFalse(q["free"], "the artefact has been produced once already")
        self.assertEqual(q["cost"], 1)
        result = credits.charge("case-a", "submission", "docx")
        self.assertTrue(result["charged"])
        self.assertEqual(result["balance"], 2)

    def test_a_different_artefact_starts_free_again(self):
        credits.charge("case-a", "submission", "docx")
        self.assertEqual(credits.quote("case-a", "workpapers", "spreadsheetml")["cost"], 0)

    def test_a_retry_is_reused_and_not_charged_twice(self):
        credits.charge("case-a", "submission", "docx")                    # free
        first = credits.charge("case-a", "submission", "docx", idem="attempt-1")
        again = credits.charge("case-a", "submission", "docx", idem="attempt-1")
        self.assertTrue(first["charged"])
        self.assertTrue(again["reused"], "the same retry key must not charge twice")
        self.assertEqual(again["balance"], first["balance"])

    def test_an_unaffordable_export_is_refused(self):
        credits.charge("case-a", "submission", "docx")      # free, artefact used
        for _ in range(3):
            credits.charge("case-a", "submission", "docx")  # 1 each
        self.assertEqual(credits.balance(), 0)
        with self.assertRaises(credits.InsufficientCredits) as ctx:
            credits.charge("case-a", "submission", "docx")
        self.assertIn("costs 1 credit", str(ctx.exception))

    def test_a_refund_is_appended_and_restores_the_balance(self):
        credits.charge("case-a", "submission", "docx")
        paid = credits.charge("case-a", "submission", "docx")
        self.assertEqual(paid["balance"], 2)
        r = credits.refund("case-a", "submission", "docx")
        self.assertTrue(r["refunded"])
        self.assertEqual(credits.balance(), 3)
        self.assertEqual(credits.entries()[-1]["kind"], "refund",
                         "a refund is a new line, never an edit of the charge")

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(credits.CreditError):
            credits.quote("case-a", "submission", "pdf-ish")

    def test_a_free_export_still_uses_up_the_artefact(self):
        credits.charge("case-a", "submission", "docx")
        self.assertIn(("case-a", "submission"), credits.exported_artefacts())


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


class DeliverableProfileTest(unittest.TestCase):
    """The artefact is primary; the format menu follows from it."""

    def setUp(self):
        from bp.product import deliverables
        self.d = deliverables
        self.root = tempfile.mkdtemp(prefix="bp-deliverables-")
        self.bundle = product_fixtures.make_bundle()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_catalogue_offers_formats_per_artefact_not_a_free_menu(self):
        catalogue = {entry["id"]: entry for entry in self.d.catalogue()}
        self.assertEqual(catalogue["submission"]["formats"], ["docx", "html"])
        self.assertEqual(catalogue["workpapers"]["formats"], ["xlsx", "spreadsheetml", "csv"])
        self.assertNotIn("docx", catalogue["workpapers"]["formats"])

    def test_a_presentation_is_declared_but_not_offered(self):
        catalogue = {entry["id"]: entry for entry in self.d.catalogue()}
        self.assertFalse(catalogue["presentation"]["available"])
        self.assertIn("PowerPoint", catalogue["presentation"]["reason"])
        with self.assertRaises(self.d.DeliverableError):
            self.d.profile("presentation")

    def test_an_impossible_pair_is_refused_and_names_what_works(self):
        with self.assertRaises(self.d.DeliverableError) as ctx:
            self.d.check_pair("workpapers", "docx")
        message = str(ctx.exception)
        self.assertIn("Working papers cannot be produced as docx", message)
        self.assertIn("spreadsheetml", message)

    def accounting_bundle(self):
        """The fixture is an NPV case; blocks about statements need an accounting appendix."""
        bundle = json.loads(json.dumps(self.bundle))
        appendix = bundle["delivery"].setdefault("appendix", {})
        appendix["accounts"] = {
            "statements_export": "BALANCE SHEET\n  Cash 100.00",
            "t_accounts_export": {"1000": "ACCOUNT 1000 Cash"},
            "journal_export": "JOURNAL 2026-01-01 to 2026-03-31",
            "checks": [["trial_balance_debits_equal_credits", True, "ok"]],
        }
        return bundle

    def test_a_dict_of_statements_is_not_silently_dropped(self):
        """The exporter returns the statements as a dict of parts, not one string.

        A text-only reader drops every statement without an error - which is exactly what happened the first
        time this document was rendered for the owner. The combined blob must not be used as a fallback when
        the parts exist, or every line would appear twice.
        """
        bundle = json.loads(json.dumps(self.bundle))
        appendix = bundle["delivery"].setdefault("appendix", {})
        appendix["accounts"] = {"statements_export": {
            "trial_balance": "TRIAL BALANCE\n  Cash 100.00",
            "income_statement": "INCOME STATEMENT\n  Net income 50.00",
            "balance_sheet": "BALANCE SHEET\n  Cash 100.00",
            "combined": "COMBINED - must not be used"}}
        lines = dict(self.d.sections(bundle, "submission"))["Statements"]
        self.assertIn("TRIAL BALANCE", lines[0])
        self.assertTrue(any("BALANCE SHEET" in line for line in lines))
        self.assertFalse(any("COMBINED" in line for line in lines),
                         "the combined blob would duplicate every statement")

    def test_the_blocks_come_from_the_stored_bundle(self):
        sections = dict(self.d.sections(self.accounting_bundle(), "submission"))
        self.assertIn("Statements", sections)
        self.assertIn("BALANCE SHEET", sections["Statements"][0])
        self.assertIn("Workings", sections)
        self.assertIn("Verification checks", sections)
        self.assertIn("PASS  trial_balance_debits_equal_credits", sections["Verification checks"])

    def test_working_papers_carry_the_recorded_values_not_the_narrative(self):
        names = [name for name, _ in self.d.sections(self.accounting_bundle(), "workpapers")]
        self.assertIn("Recorded values", names)
        self.assertNotIn("Workings", names)

    def test_each_offered_format_produces_a_file(self):
        for profile, fmt, suffix in (("submission", "docx", "docx"),
                                     ("submission", "html", "html"),
                                     ("workpapers", "csv", "csv"),
                                     ("workpapers", "spreadsheetml", "xml")):
            with self.subTest(profile=profile, fmt=fmt):
                destination = os.path.join(self.root, "%s.%s" % (profile, suffix))
                result = self.d.write_export(self.bundle, profile, fmt, destination)
                self.assertTrue(os.path.isfile(destination))
                self.assertEqual(result["deliverable"], profile)


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
        self.assertIn("no deliverable offers", payload["error"])

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
