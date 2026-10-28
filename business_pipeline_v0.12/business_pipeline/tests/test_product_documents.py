"""PDF text-layer extraction and the intake extract path (B-105)."""

import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import documents, intake  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "hello_finance.pdf")


def _fixture_bytes():
    with open(FIXTURE, "rb") as stream:
        return stream.read()


def _blank_pdf():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    out = io.BytesIO(); writer.write(out)
    return out.getvalue()


def _encrypted_pdf():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    out = io.BytesIO(); writer.write(out)
    return out.getvalue()


@unittest.skipUnless(documents.pypdf_available(), "pypdf is not installed")
class PdfTextTest(unittest.TestCase):
    def test_a_text_layer_pdf_is_extracted_and_labelled(self):
        result = documents.extract_pdf(_fixture_bytes())
        self.assertEqual(result["status"], "extracted")
        self.assertIn("Hello finance student", result["text"])
        self.assertGreaterEqual(result["pages"], 1)
        self.assertEqual(result["method"], "pdf_text_layer")

    def test_a_pdf_with_no_text_layer_asks_for_ocr_instead_of_guessing(self):
        result = documents.extract_pdf(_blank_pdf())
        self.assertEqual(result["status"], "ocr_required")
        self.assertIn("OCR", result["reason"])

    def test_an_encrypted_pdf_is_refused(self):
        with self.assertRaises(documents.DocumentError):
            documents.extract_pdf(_encrypted_pdf())

    def test_a_non_pdf_is_refused_with_a_clear_message(self):
        with self.assertRaises(documents.DocumentError):
            documents.extract_pdf(b"not a pdf at all")


@unittest.skipUnless(documents.ocr_available(), "Tesseract/pytesseract are not installed")
class ImageOcrTest(unittest.TestCase):
    def _png(self):
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (800, 220), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", 40)
        draw.text((30, 40), "INVOICE 2026-001", font=font, fill="black")
        draw.text((30, 120), "Total due 1,250.00", font=font, fill="black")
        out = io.BytesIO(); image.save(out, "PNG")
        return out.getvalue()

    def test_an_image_is_read_with_the_local_ocr_engine(self):
        result = documents.extract_image(self._png(), ".png")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["method"], "image_ocr")
        self.assertIn("INVOICE", result["text"])

    @unittest.skipUnless(documents.pdf_ocr_available(), "pdfium is not installed")
    def test_a_scanned_pdf_is_rendered_and_read(self):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
        except ImportError:
            self.skipTest("reportlab is not installed for the fixture")
        buf = io.BytesIO()
        pdf = canvas.Canvas(buf, pagesize=(800, 220))
        pdf.drawImage(ImageReader(io.BytesIO(self._png())), 0, 0, width=800, height=220)
        pdf.showPage(); pdf.save()
        result = documents.extract_pdf(buf.getvalue())
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["method"], "pdf_ocr")
        self.assertIn("INVOICE", result["text"])


class IntakeExtractTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-intake-pdf-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    @unittest.skipUnless(documents.pypdf_available(), "pypdf is not installed")
    def test_upload_extract_read_and_delete_a_pdf(self):
        record = intake.save("case.pdf", _fixture_bytes())
        self.assertEqual(record["kind"], "document")
        self.assertEqual(record["status"], "stored")
        updated = intake.extract(record["id"])
        self.assertEqual(updated["status"], "extracted")
        self.assertGreater(updated["extraction"]["chars"], 20)
        preview = intake.extracted_text(record["id"])
        self.assertIn("Hello finance student", preview["text"])
        self.assertFalse(preview["truncated"])
        intake.delete(record["id"])
        self.assertEqual(intake.list_files(), [])

    @unittest.skipUnless(documents.pdf_ocr_available(), "pdfium/Tesseract are not installed")
    def test_a_scanned_pdf_is_extracted_through_the_intake_store(self):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
        except ImportError:
            self.skipTest("reportlab is not installed for the fixture")
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (800, 220), "white"); draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", 40)
        draw.text((30, 40), "INVOICE 2026-001", font=font, fill="black")
        png = io.BytesIO(); image.save(png, "PNG")
        buf = io.BytesIO(); pdf = canvas.Canvas(buf, pagesize=(800, 220))
        pdf.drawImage(ImageReader(io.BytesIO(png.getvalue())), 0, 0, width=800, height=220)
        pdf.showPage(); pdf.save()
        record = intake.save("scan.pdf", buf.getvalue())
        updated = intake.extract(record["id"])
        self.assertEqual(updated["status"], "extracted")
        self.assertEqual(updated["extraction"]["method"], "pdf_ocr")
        self.assertIn("INVOICE", intake.extracted_text(record["id"])["text"])

    def test_extracting_a_structured_file_is_refused(self):
        record = intake.save("data.csv", b"a,b\n1,2\n")
        with self.assertRaises(intake.IntakeError):
            intake.extract(record["id"])

    @unittest.skipUnless(documents.pypdf_available(), "pypdf is not installed")
    def test_a_scanned_pdf_is_marked_ocr_required_and_not_read(self):
        record = intake.save("scan.pdf", _blank_pdf())
        updated = intake.extract(record["id"])
        self.assertEqual(updated["status"], "ocr_required")
        self.assertIn("OCR", updated["note"])
        with self.assertRaises(intake.IntakeNotFound):
            intake.extracted_text(record["id"])

    def test_a_reference_only_file_cannot_be_read(self):
        record = intake.save("slides.pptx", b"PK\x03\x04 not really a deck")
        self.assertEqual(record["status"], "reference_only")
        with self.assertRaises(intake.IntakeError):
            intake.extract(record["id"])


if __name__ == "__main__":
    unittest.main()
