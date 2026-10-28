"""Document text extraction for attached PDFs and images (B-105).

The reader is **optional and fail-closed**:

* PDF **text layer** extraction uses ``pypdf`` when it is installed.  A PDF with no text
  layer (a scan) is rendered with ``pypdfium2`` and OCR'd with a local Tesseract when both
  are available; otherwise it is reported as ``ocr_required``.  Text is never guessed.
* Image OCR uses ``pytesseract`` plus a local Tesseract binary when both are installed.
  Otherwise the file is reported as ``ocr_required``.
* OCR is capped at 20 pages (rendering every page is slow); the text-layer route is capped
  at 50 pages and 200,000 characters.  Encrypted PDFs are refused.

Limits are refused, not truncated.  The extracted text is **unverified**: it must be checked
against the document by the user.  Nothing here imports the frozen method library or computes
a business number.
"""

import importlib.util
import io
import os
import re
import shutil

MAX_PAGES = 50
MAX_OCR_PAGES = 20
MAX_CHARS = 200_000
MIN_CHARS = 5
RENDER_SCALE = 2.0   # about 144 dpi, enough for body text and kind to CPU time

_TESSERACT = None


class DocumentError(Exception):
    """The document cannot be read; the message says why."""


def pypdf_available():
    return importlib.util.find_spec("pypdf") is not None


def pdf_renderer_available():
    return importlib.util.find_spec("pypdfium2") is not None


def _tesseract_cmd():
    """The local Tesseract binary: an explicit env var, PATH, then the usual Windows locations."""
    global _TESSERACT
    if _TESSERACT is not None: return _TESSERACT or None
    candidates = [os.environ.get("BP_TESSERACT_CMD"), shutil.which("tesseract"),
                  r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe")]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            _TESSERACT = candidate; return candidate
    _TESSERACT = ""; return None


def ocr_available():
    return (_tesseract_cmd() is not None
            and importlib.util.find_spec("pytesseract") is not None
            and importlib.util.find_spec("PIL") is not None)


def pdf_ocr_available():
    return ocr_available() and pdf_renderer_available()


def _pytesseract():
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
    return pytesseract


def _ocr_image(image):
    text = _pytesseract().image_to_string(image) or ""
    return _clean(text)


def _clean(text):
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def extract_pdf(raw):
    """Extract the text layer of a PDF.  Returns a status dictionary, never invented text."""
    if not pypdf_available():
        raise DocumentError("PDF text extraction needs the optional 'pypdf' package; install it, or save the document as CSV/TSV/TXT")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
    except Exception as exc:
        raise DocumentError("this file could not be opened as a PDF (%s)" % type(exc).__name__)
    if getattr(reader, "is_encrypted", False):
        raise DocumentError("the PDF is encrypted; remove the password and attach it again")
    try:
        pages = len(reader.pages)
    except Exception:
        raise DocumentError("the PDF page count could not be read")
    if pages > MAX_PAGES:
        raise DocumentError("the PDF has %d pages; the limit is %d, so split it first" % (pages, MAX_PAGES))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    text = _clean("\n".join(parts))
    if len(text) < MIN_CHARS:
        if pdf_ocr_available():
            return _ocr_pdf(raw, pages)
        return {"status": "ocr_required", "pages": pages, "chars": len(text),
                "reason": "the PDF has no usable text layer (it looks scanned); OCR needs pypdfium2 and a local Tesseract, which are not installed"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit; split the document" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": pages, "chars": len(text), "method": "pdf_text_layer"}


def _ocr_pdf(raw, pages):
    """Render a scanned PDF with pdfium and OCR each page with the local Tesseract."""
    if pages > MAX_OCR_PAGES:
        raise DocumentError("the scanned PDF has %d pages; OCR is limited to %d, so split it first" % (pages, MAX_OCR_PAGES))
    try:
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(raw)
    except Exception as exc:
        raise DocumentError("this PDF could not be rendered for OCR (%s)" % type(exc).__name__)
    parts = []
    try:
        for index in range(pages):
            page = document[index]
            try:
                bitmap = page.render(scale=RENDER_SCALE)
                try:
                    parts.append(_ocr_image(bitmap.to_pil()))
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        document.close()
    text = _clean("\n".join(parts))
    if len(text) < MIN_CHARS:
        return {"status": "ocr_required", "pages": pages, "chars": len(text),
                "reason": "OCR ran but found no usable text in this PDF"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the OCR text is longer than the %d-character limit; split the document" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": pages, "chars": len(text), "method": "pdf_ocr"}


def extract_image(raw, ext):
    """OCR one image when a local Tesseract is available; otherwise report that it is required."""
    if not ocr_available():
        return {"status": "ocr_required", "pages": 1, "chars": 0,
                "reason": "image OCR needs Tesseract and 'pytesseract' on this machine; install Tesseract, or paste the text yourself"}
    try:
        from PIL import Image
        text = _ocr_image(Image.open(io.BytesIO(raw)))
    except Exception as exc:
        raise DocumentError("the image could not be read (%s)" % type(exc).__name__)
    if len(text) < 5:
        return {"status": "ocr_required", "pages": 1, "chars": len(text),
                "reason": "the OCR engine found no usable text in this image"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": 1, "chars": len(text), "method": "image_ocr"}
