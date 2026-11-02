"""Intake store and its routes (product layer, B-080, B-105).

The store accepts a file, hashes it and records what kind of file it is. Structured
files are read by the frozen ingest module through the server; PDFs and images are
stored and read only on an explicit extract request; every other file is stored as
`reference_only`.
"""

import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from bp.product import intake  # noqa: E402


CSV = b"region,sales\nnorth,10\nsouth,20\n"
XLS_LEGACY = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1legacy workbook bytes"


class IntakeStoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-intake-test-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_structured_file_is_stored_with_its_hash(self):
        record = intake.save("sales.csv", CSV)
        self.assertRegex(record["id"], r"^[0-9a-f]{12}$")
        self.assertEqual(record["kind"], "structured")
        self.assertEqual(record["status"], "stored")
        self.assertEqual(record["bytes"], len(CSV))
        self.assertEqual(record["sha256"], intake.hashlib.sha256(CSV).hexdigest())
        self.assertEqual(intake.payload(record["id"]), ("sales.csv", CSV))
        self.assertEqual(intake.load(record["id"])["filename"], "sales.csv")

    def test_a_document_is_stored_and_read_only_on_request(self):
        record = intake.save("brief.pdf", b"%PDF-1.4 not really a pdf")
        self.assertEqual(record["kind"], "document")
        self.assertEqual(record["status"], "stored")
        self.assertIn("Extract text", record["note"])
        with self.assertRaises(intake.IntakeError):
            intake.extract(record["id"])
        self.assertEqual(intake.load(record["id"])["status"], "reference_only")

    def test_a_legacy_xls_is_not_claimed_as_readable(self):
        record = intake.save("old.xls", XLS_LEGACY)
        self.assertEqual(record["kind"], "reference")
        self.assertEqual(record["status"], "reference_only")
        self.assertIn(".xlsx", record["note"])

    def test_a_json_upload_does_not_overwrite_its_own_record(self):
        record = intake.save("notes.json", b'{"a": 1}')
        self.assertEqual(intake.load(record["id"])["filename"], "notes.json")
        self.assertEqual(intake.payload(record["id"])[1], b'{"a": 1}')

    def test_a_table_can_be_attached_and_makes_the_file_ingested(self):
        record = intake.save("sales.csv", CSV)
        table = {"n_rows": 2, "n_cols": 2, "columns": [{"name": "region"}, {"name": "sales"}], "rows": []}
        updated = intake.attach_table(record["id"], table)
        self.assertEqual(updated["status"], "ingested")
        self.assertEqual(updated["table"]["n_rows"], 2)
        listed = intake.list_files()
        self.assertEqual(listed[0]["status"], "ingested")
        self.assertEqual(listed[0]["n_rows"], 2)
        self.assertEqual(listed[0]["columns"], ["region", "sales"])

    def test_a_failed_read_keeps_the_file_stored_with_the_reason(self):
        record = intake.save("sales.csv", CSV)
        updated = intake.fail(record["id"], "the header row is empty")
        self.assertEqual(updated["status"], "stored")
        self.assertEqual(updated["error"], "the header row is empty")
        self.assertIn("header row", intake.list_files()[0]["error"])

    def test_listing_is_newest_first_and_deletion_removes_both_files(self):
        first = intake.save("a.csv", CSV)
        second = intake.save("b.pdf", b"%PDF-1.4")
        self.assertEqual([row["id"] for row in intake.list_files()], [second["id"], first["id"]])
        self.assertTrue(intake.delete(first["id"]))
        self.assertEqual([row["id"] for row in intake.list_files()], [second["id"]])
        self.assertFalse(os.path.exists(os.path.join(self.root, first["id"] + ".csv")))
        with self.assertRaises(intake.IntakeNotFound):
            intake.load(first["id"])

    def test_names_that_could_escape_the_store_are_refused(self):
        for name in ("", "   ", "..", "a\x00b.csv"):
            with self.assertRaises(ValueError):
                intake.save(name, CSV)
        with self.assertRaises(ValueError):
            intake.save(None, CSV)

    def test_empty_and_oversize_files_are_refused(self):
        with self.assertRaises(ValueError):
            intake.save("empty.csv", b"")
        with self.assertRaises(ValueError):
            intake.save("big.csv", b"x" * (intake.MAX_BYTES + 1))

    def test_an_id_that_is_not_twelve_hex_characters_is_refused(self):
        for bad in ("../../etc/passwd", "ABC", "0" * 11, "../" + "0" * 12):
            with self.assertRaises(ValueError):
                intake.load(bad)

    def test_a_corrupt_record_is_listed_not_hidden(self):
        file_id = "0123456789ab"
        with open(os.path.join(self.root, file_id + ".json"), "w", encoding="utf-8") as stream:
            stream.write("{not json")
        listed = intake.list_files()
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0]["corrupt"])
        self.assertIn("not readable JSON", listed[0]["error"])


class IntakeBriefTest(unittest.TestCase):
    """E-intake-01: a stored file can become the paper's instruction, and says it is unverified."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-intake-brief-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_text_file_can_be_used_as_the_brief(self):
        body = b"Compare the two expansion options for the bakery and recommend one."
        record = intake.save("instructions.txt", body, role="brief")
        used = intake.use_as_brief(record["id"])
        self.assertEqual(used["role"], "brief")
        self.assertTrue(used["unverified"], "brief text from a file is never presented as verified")
        self.assertIn("Compare the two expansion options", used["text"])
        self.assertEqual(used["chars"], len(used["text"]))
        stored = intake.load(record["id"])
        self.assertEqual(stored["role"], "brief")
        self.assertEqual(stored["status"], "extracted")
        self.assertEqual(stored["brief"]["chars"], len(used["text"]))
        self.assertEqual(stored["brief"]["text_sha256"], intake.hashlib.sha256(
            used["text"].encode("utf-8")).hexdigest())
        self.assertIn("unverified", stored["note"])

    def test_a_pdf_with_a_text_layer_can_be_used_as_the_brief(self):
        with open(os.path.join(HERE, "fixtures", "hello_finance.pdf"), "rb") as stream:
            raw = stream.read()
        record = intake.save("brief.pdf", raw)
        self.assertIsNone(record["role"], "a role is never guessed from an extension")
        used = intake.use_as_brief(record["id"])
        self.assertIn("Hello finance student", used["text"])
        self.assertTrue(used["unverified"])

    def test_a_file_with_no_reader_is_refused_as_a_brief(self):
        record = intake.save("sales.csv", CSV)
        with self.assertRaises(intake.IntakeError) as caught:
            intake.use_as_brief(record["id"])
        self.assertIn("attach a PDF", str(caught.exception))
        self.assertEqual(intake.load(record["id"])["role"], None,
                         "a refused brief must not relabel the file")

    def test_a_missing_file_cannot_be_used_as_a_brief(self):
        with self.assertRaises(intake.IntakeNotFound):
            intake.use_as_brief("0" * 12)

    def test_a_role_is_recorded_only_when_the_caller_says_it(self):
        plain = intake.save("data.csv", CSV)
        self.assertIsNone(plain["role"])
        declared = intake.save("dataset.csv", CSV, role="dataset")
        self.assertEqual(declared["role"], "dataset")
        roles = {row["filename"]: row["role"] for row in intake.list_files()}
        self.assertEqual(roles, {"data.csv": None, "dataset.csv": "dataset"})

    def test_a_role_outside_the_declared_set_is_refused(self):
        with self.assertRaises(ValueError):
            intake.save("memo.txt", b"hello", role="memo")

    def test_a_record_with_an_unknown_role_is_listed_not_hidden(self):
        record = intake.save("memo.txt", b"hello")
        path = os.path.join(self.root, record["id"] + ".json")
        with open(path, encoding="utf-8") as stream:
            document = json.load(stream)
        document["role"] = "memo"
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(document, stream)
        listed = intake.list_files()
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0]["corrupt"])
        self.assertIn("unknown role", listed[0]["error"])


class IntakeRoutesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        from bp import server

        cls.dir = tempfile.mkdtemp(prefix="bp-intake-routes-")
        cls.prev = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = cls.dir
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        if cls.prev is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = cls.prev
        shutil.rmtree(cls.dir, ignore_errors=True)

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request) as stream:
                return stream.status, json.loads(stream.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def upload(self, filename, raw, role=None):
        payload = {"filename": filename, "content_base64": base64.b64encode(raw).decode()}
        if role is not None:
            payload["role"] = role
        return self.call("POST", "/api/intake", payload)

    def test_a_csv_is_accepted_and_read_into_a_table(self):
        status, record = self.upload("sales.csv", CSV)
        self.assertEqual(status, 201)
        self.assertEqual(record["kind"], "structured")
        self.assertEqual(record["status"], "ingested")
        self.assertEqual((record["table"]["n_rows"], record["table"]["n_cols"]), (2, 2))
        self.assertEqual([c["name"] for c in record["table"]["columns"]], ["region", "sales"])

    def test_a_pdf_is_stored_and_extracted_on_request(self):
        with open(os.path.join(HERE, "fixtures", "hello_finance.pdf"), "rb") as stream:
            raw = stream.read()
        status, record = self.upload("brief.pdf", raw)
        self.assertEqual(status, 201)
        self.assertEqual(record["kind"], "document")
        self.assertEqual(record["status"], "stored")
        self.assertIsNone(record["table"])
        status, refused = self.call("POST", "/api/intake/%s/ingest" % record["id"], {})
        self.assertEqual(status, 422)
        self.assertIn("no reader", refused["error"])
        status, extracted = self.call("POST", "/api/intake/%s/extract" % record["id"], {})
        self.assertEqual(status, 200)
        self.assertEqual(extracted["status"], "extracted")
        status, text = self.call("GET", "/api/intake/%s/text?limit=200" % record["id"])
        self.assertEqual(status, 200)
        self.assertIn("Hello finance student", text["text"])

    def test_the_list_get_and_delete_routes_round_trip(self):
        status, record = self.upload("sales.csv", CSV)
        self.assertEqual(status, 201)
        status, listed = self.call("GET", "/api/intake")
        self.assertEqual(status, 200)
        self.assertIn(record["id"], [row["id"] for row in listed["files"]])
        status, loaded = self.call("GET", "/api/intake/" + record["id"])
        self.assertEqual((status, loaded["filename"]), (200, "sales.csv"))
        status, deleted = self.call("DELETE", "/api/intake/" + record["id"])
        self.assertEqual((status, deleted), (200, {"deleted": record["id"]}))
        self.assertEqual(self.call("GET", "/api/intake/" + record["id"])[0], 404)

    def test_a_structured_file_can_be_read_again_with_options(self):
        status, record = self.upload("sales.csv", CSV)
        self.assertEqual(status, 201)
        status, read = self.call("POST", "/api/intake/%s/ingest" % record["id"], {"merged": "refuse"})
        self.assertEqual(status, 200)
        self.assertEqual(read["status"], "ingested")
        status, refused = self.call("POST", "/api/intake/%s/ingest" % record["id"], {"merged": "drop"})
        self.assertEqual(status, 422)

    def test_malformed_uploads_are_refused(self):
        self.assertEqual(self.call("POST", "/api/intake", {"filename": "a.csv"})[0], 400)
        self.assertEqual(self.call("POST", "/api/intake", {"filename": "a.csv", "content_base64": "!!"})[0], 400)
        self.assertEqual(self.call("POST", "/api/intake", {"content_base64": "YQ=="})[0], 400)
        self.assertEqual(self.call("POST", "/api/intake", {"filename": "a.csv", "content_base64": ""})[0], 400)
        self.assertEqual(self.call("GET", "/api/intake/" + "0" * 12)[0], 404)
        self.assertEqual(self.call("DELETE", "/api/intake/" + "0" * 12)[0], 404)


    def test_a_pdf_can_be_used_as_the_brief_over_the_route(self):
        with open(os.path.join(HERE, "fixtures", "hello_finance.pdf"), "rb") as stream:
            raw = stream.read()
        status, record = self.upload("instructions.pdf", raw)
        self.assertEqual(status, 201)
        self.assertIsNone(record["role"], "an upload does not claim a role the student did not give")
        status, used = self.call("POST", "/api/intake/%s/brief" % record["id"], {})
        self.assertEqual(status, 200)
        self.assertEqual(used["role"], "brief")
        self.assertTrue(used["unverified"])
        self.assertIn("Hello finance student", used["text"])
        status, listed = self.call("GET", "/api/intake")
        self.assertEqual(status, 200)
        row = next(item for item in listed["files"] if item["id"] == record["id"])
        self.assertEqual(row["role"], "brief")
        self.assertEqual(row["brief_chars"], used["chars"])

    def test_an_upload_can_declare_its_role(self):
        status, record = self.upload("data.csv", CSV, role="dataset")
        self.assertEqual(status, 201)
        self.assertEqual(record["role"], "dataset")

    def test_a_role_outside_the_declared_set_is_a_400(self):
        status, body = self.upload("memo.txt", b"hello", role="memo")
        self.assertEqual(status, 400)
        self.assertIn("role must be one of", body["error"])

    def test_a_file_with_no_reader_is_422_as_a_brief(self):
        status, record = self.upload("sales.csv", CSV)
        self.assertEqual(status, 201)
        status, refused = self.call("POST", "/api/intake/%s/brief" % record["id"], {})
        self.assertEqual(status, 422)
        self.assertIn("attach a PDF", refused["error"])

    def test_a_missing_file_is_404_as_a_brief(self):
        self.assertEqual(self.call("POST", "/api/intake/" + "0" * 12 + "/brief", {})[0], 404)


class IntakePageContractTest(unittest.TestCase):
    """E-intake-02: the page offers the instruction action and starts nothing by itself."""

    def setUp(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            self.page = stream.read()

    def test_the_page_carries_the_use_as_instruction_action(self):
        self.assertIn("Use as the instruction", self.page)
        self.assertIn('data-brief="', self.page)
        self.assertIn('$$("[data-brief]"', self.page)
        self.assertIn('"/brief"', self.page)

    def test_the_instruction_action_fills_the_brief_box_and_starts_nothing(self):
        start = self.page.index("async function useAsBrief(")
        end = self.page.index("async function ingestAttachment(")
        handler = self.page[start:end]
        self.assertIn('$("#objective")', handler)
        self.assertIn("unverified", handler)
        self.assertNotIn("/api/sessions", handler, "reading an instruction must not start a paper")
        self.assertNotIn("startChat", handler, "reading an instruction must not start a paper")

    def test_the_action_is_only_offered_where_a_reader_exists(self):
        block = self.page[self.page.index("function canBeBrief("):self.page.index("function intakeRow(")]
        for ext in (".pdf", ".docx", ".txt"):
            self.assertIn('"%s"' % ext, block)
        self.assertNotIn('".csv"', block, "a spreadsheet is a dataset, not an instruction")


if __name__ == "__main__":
    unittest.main()


