"""Acceptance suite for the vision-model OCR lane (E-ocr-001…010).

The lane is optional and fail-closed, like the prose lane: with no key and no model id
it does nothing and touches no socket, and with both it reads a page and records which
engine read it.  Every test here is offline; the endpoint is mocked.
"""

import io
import json
import os
import sys
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp.product import documents, ocr  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200


def _docx_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            "<w:body><w:p><w:r><w:t>Revenue for the year was recorded.</w:t></w:r></w:p>"
            "</w:body></w:document>")
    return buffer.getvalue()


def _reply(content):
    """A urlopen() stand-in answering like an OpenAI-compatible endpoint."""
    payload = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return payload

    return Response()


def _configured():
    return mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": "test-key",
                                        "BP_OCR_MODEL": "vision-test-1"}, clear=False)


def _unconfigured():
    return mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": "", "BP_OCR_MODEL": "",
                                        "BP_OCR_KEY": "", "BP_VISION_MODEL": ""}, clear=False)


def _no_local_ocr():
    """Pretend no local Tesseract is installed, so the model is the only engine left.

    This is what a fresh student machine looks like, and it makes the test independent
    of whatever happens to be installed on the machine running it.
    """
    return mock.patch.multiple("bp.product.documents", ocr_available=lambda: False,
                               pdf_ocr_available=lambda: False)


class OcrLaneTest(unittest.TestCase):
    def test_e_ocr_001__without_a_key_the_lane_is_off_and_no_socket_opens(self):
        with _unconfigured(), _no_local_ocr():
            self.assertFalse(ocr.available())
            self.assertEqual(ocr.describe(), {"engine": "none", "model": ""})
            with mock.patch("bp.product.ocr.urllib.request.urlopen",
                            side_effect=AssertionError("no socket may open")):
                result = documents.extract_image(PNG, ".png")
        self.assertEqual(result["status"], "ocr_required")
        self.assertIn("BP_OCR_MODEL", result["reason"])
        self.assertIn("Tesseract", result["reason"])

    def test_e_ocr_008__a_key_without_a_model_id_is_not_available(self):
        with mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": "test-key", "BP_OCR_MODEL": "",
                                          "BP_VISION_MODEL": ""}, clear=False):
            self.assertFalse(ocr.available(), "a model id is never assumed")
            with self.assertRaises(ocr.OcrError) as refused:
                ocr.read(PNG)
        self.assertIn("BP_OCR_MODEL", str(refused.exception))

    def test_e_ocr_002__a_configured_model_reads_an_image_and_is_recorded(self):
        with _configured(), _no_local_ocr(), mock.patch("bp.product.ocr.urllib.request.urlopen",
                                       return_value=_reply("  Statement of financial position\n")):
            result = documents.extract_image(PNG, ".png")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["method"], "image_ocr_model")
        self.assertEqual(result["engine"], "vision-test-1",
                         "the record says which engine read the page")
        self.assertIn("Statement of financial position", result["text"])

    def test_e_ocr_003__the_request_names_the_model_the_page_and_a_literal_prompt(self):
        captured = {}

        def capture(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.headers.get("Authorization")
            return _reply("Balance sheet as at 31 December\n")

        with _configured(), mock.patch("bp.product.ocr.urllib.request.urlopen", side_effect=capture):
            ocr.read(PNG, "image/png")
        body = captured["body"]
        self.assertEqual(body["model"], "vision-test-1")
        self.assertEqual(body["temperature"], 0, "transcription is not creative")
        parts = body["messages"][0]["content"]
        self.assertEqual(parts[1]["image_url"]["url"][:22], "data:image/png;base64,")
        self.assertIn("Do not summarise", parts[0]["text"])
        self.assertIn("transcribe", parts[0]["text"].lower())
    def test_e_ocr_004__an_http_error_is_reported_with_its_status(self):
        import urllib.error
        with _configured(), _no_local_ocr(), mock.patch(
                "bp.product.ocr.urllib.request.urlopen",
                side_effect=urllib.error.HTTPError("u", 500, "boom", {}, io.BytesIO(b""))):
            with self.assertRaises(documents.DocumentError) as refused:
                documents.extract_image(PNG, ".png")
        self.assertIn("HTTP 500", str(refused.exception))

    def test_e_ocr_005__an_empty_answer_is_a_refusal_not_an_empty_page(self):
        with _configured(), _no_local_ocr(), mock.patch(
                "bp.product.ocr.urllib.request.urlopen", return_value=_reply("   ")):
            with self.assertRaises(documents.DocumentError) as refused:
                documents.extract_image(PNG, ".png")
        self.assertIn("read no text", str(refused.exception))

    def test_e_ocr_006__an_unreachable_endpoint_says_so(self):
        with _configured(), _no_local_ocr(), mock.patch(
                "bp.product.ocr.urllib.request.urlopen",
                side_effect=OSError("connection refused")):
            with self.assertRaises(documents.DocumentError) as refused:
                documents.extract_image(PNG, ".png")
        self.assertIn("could not be reached", str(refused.exception))

    def test_e_ocr_007__an_oversized_page_is_refused_by_name(self):
        with _configured():
            with self.assertRaises(ocr.OcrError) as refused:
                ocr.read(b"x" * (ocr.MAX_IMAGE_BYTES + 1))
        self.assertIn("larger than", str(refused.exception))

    def test_e_ocr_009__a_document_with_its_own_text_never_reaches_the_model(self):
        with _configured(), mock.patch("bp.product.ocr.read",
                                       side_effect=AssertionError("the model must not be called")):
            result = documents.extract_docx(_docx_bytes())
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["method"], "docx_text")
        self.assertIn("Revenue for the year", result["text"])

    def test_e_ocr_010__the_engine_is_named_only_when_a_model_read_the_page(self):
        with _configured():
            self.assertEqual(ocr.describe(), {"engine": "vision_model", "model": "vision-test-1"})
        plain = documents.extract_docx(_docx_bytes())
        self.assertNotIn("engine", plain,
                         "a page the text layer read is not credited to a model")


if __name__ == "__main__":
    unittest.main()
